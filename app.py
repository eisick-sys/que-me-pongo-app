# app.py
import os
import re
import random
from datetime import date
from typing import List, Optional

from PIL import Image, ImageOps
import streamlit as st

from utils.garment_utils import is_bottom_skirt
from auth_ui import render_auth_screen, logout
from storage_cloud import (
    load_wardrobe_cloud, save_garment_cloud, update_garment_cloud,
    delete_garment_cloud, load_feedback_cloud, add_feedback_cloud,
    load_used_outfits_cloud, add_used_outfit_cloud, get_next_used_outfit_id,
    upload_garment_image, get_garment_image_url,
)

st.set_page_config(
    page_title="Lookia",
    page_icon="👕",
    layout="wide"
)

# =========================================================
# HEADER
# =========================================================
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.image("logo.png", width="stretch")

st.markdown(
    """
    <p style='text-align: center; font-size: 1.1rem; margin-top: 0.4rem; color: #444;'>
        Tu asistente para armar outfits según clima, ocasión y estilo
    </p>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='margin-top: 0.3rem;'></div>", unsafe_allow_html=True)
# ========================================================

# Verificar autenticación
if not render_auth_screen():
    st.stop()

user_id = st.session_state["user"].id

with st.sidebar:
    st.caption(f"👤 {st.session_state['user'].email}")
    st.caption("─────────────────")
    if st.button("↩ cerrar sesión", key="logout_btn", type="tertiary"):
        logout()

from models import Garment, OutfitFeedback, UsedOutfit
from weather import format_weather_label, get_current_weather, get_week_forecast

from engine.occasion_rules import garment_allowed_for_occasion, get_weather_tag
from engine.recommender import (
    explain_outfit_score,
    generate_outfits,
    generate_outfits_from_selected_garment,
    generate_week_plan,
)

from constants import (
    ACCESSORY_TYPE_OPTIONS,
    ACTIVITY_OPTIONS,
    CATEGORY_LABELS_ES,
    CATEGORY_OPTIONS,
    COLOR_ALIASES,
    COLOR_OPTIONS,
    DRESS_LEVEL_OPTIONS,
    MOOD_OPTIONS,
    OCCASION_OPTIONS,
    PATTERN_OPTIONS,
    STYLE_OPTIONS,
    SUBCATEGORY_LABELS_ES,
    SUBCATEGORY_OPTIONS,
    THERMAL_ACCESSORIES,
    WARMTH_OPTIONS,
)
from utils.attribute_inference import infer_attributes_from_name, suggest_name_from_filename

# =========================================================
# CONFIGURACIÓN BASE
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "closet.json")
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.json")
USED_OUTFITS_FILE = os.path.join(BASE_DIR, "used_outfits.json")
IMAGES_DIR = os.path.join(BASE_DIR, "wardrobe_images")

from dotenv import load_dotenv
load_dotenv()
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
DEFAULT_CITY = os.getenv("LOOKIA_CITY", "Punta Arenas")

# Crear carpeta de imágenes si no existe
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR, exist_ok=True)


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def detect_garment_issues(garment: Garment) -> Optional[str]:
    """Retorna un mensaje corto si detecta inconsistencia, None si está ok."""
    name = garment.name.lower()
    style = garment.style
    secondary = garment.secondary_styles or []
    all_s = [style] + secondary
    sub = garment.subcategory or ""
    dl = garment.dress_level

    # Calzado
    if garment.category == "shoes":
        if sub in ["taco_alto", "taco_bajo"] and dl == "relajado":
            return "Nivel de formalidad 'relajado' — para citas cambia a 'arreglado'"
        if sub == "zapatilla_deporte" and dl in ["elegante", "arreglado"]:
            return "Zapatilla deporte con nivel formal alto — ¿es correcto?"
        if sub == "mocasin" and style == "sport":
            return "Mocasín con estilo sport — ¿querías decir casual o formal?"

    # Outerwear
    if garment.category == "outerwear":
        if garment.waterproof and "sport" in all_s and dl in ["relajado", "flexible"]:
            return "Impermeable sport — quedará bloqueado en citas y salidas elegantes"
        if any(x in name for x in ["parka", "celeste", "impermeable"]) and dl == "elegante":
            return "Parka marcada como elegante — ¿es correcto?"

    # Bottoms
    if garment.category == "bottom":
        if sub in ["buzo", "jogger"] and dl in ["elegante", "arreglado"]:
            return "Buzo/jogger con nivel formal alto — cambia a 'relajado'"
        if sub in ["short_casual"] and dl == "elegante":
            return "Short casual marcado como elegante — ¿querías decir flexible?"

    # General
    if "sport" in all_s and dl == "elegante":
        return "Estilo sport + nivel elegante — posible contradicción"

    # Inconsistencias térmicas
    if garment.category == "bottom":
        if sub in ["short_casual", "short_elegante", "falda_corta"] and garment.warmth == "frio":
            return "Short/mini marcado como 'frío' — ¿querías decir 'caluroso'?"

    if garment.category in ["top", "one_piece"]:
        name_lower = garment.name.lower()
        is_light = any(x in name_lower for x in ["polera", "top", "body", "crop", "musculosa", "tank"])
        if is_light and garment.warmth == "frio":
            return "Top liviano marcado como 'frío' — ¿querías decir 'caluroso'?"

    if garment.category in ["outerwear", "midlayer"]:
        name_lower = garment.name.lower()
        is_warm = any(x in name_lower for x in ["abrigo", "parka", "polar", "sweater grueso", "lana"])
        if is_warm and garment.warmth == "caluroso":
            return "Prenda abrigada marcada como 'caluroso' — ¿querías decir 'frío'?"

    if garment.category == "outerwear":
        name_lower = garment.name.lower()
        if "impermeable" in name_lower and not garment.waterproof:
            return "Tiene 'impermeable' en el nombre pero no está marcado como impermeable — ¿falta activar esa opción?"

    return None


def normalize_color_name(color: str) -> str:
    from constants import COLOR_ALIASES

    if not color:
        return "negro"

    c = color.strip().lower()
    return COLOR_ALIASES.get(c, c)


def save_square_image(uploaded_file, output_path, size=(300, 300)):
    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    square_image = ImageOps.fit(
        image,
        size,
        Image.Resampling.LANCZOS
    )
    square_image.save(output_path, format="JPEG", quality=85)


@st.cache_data
def load_cached_image(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img


def render_garment_image(garment: Garment, width: int = 120):
    if not garment.image_name:
        st.caption("Sin foto")
        return

    user_id = st.session_state["user"].id
    url = get_garment_image_url(user_id, garment.image_name)
    if url:
        st.image(url, width=width)
    else:
        st.caption("Sin imagen")


def render_feedback_buttons(combo, outfit_index, ctx, weather_tag, section="tab1"):
    col_like, col_dislike = st.columns(2)

    combo_key = "_".join(str(g.id) for g in combo)
    context_key = (
        f"{ctx['occasion']}_{ctx['mood']}_{ctx['activity']}_{ctx['temp']}_{ctx['rain']}"
    )

    with col_like:
        if st.button(
            "👍 Me gusta",
            key=f"like_{section}_{outfit_index}_{combo_key}_{context_key}",
            use_container_width=True
        ):
            new_feedback = OutfitFeedback(
                id=get_next_feedback_id(st.session_state.feedback),
                garment_ids=[g.id for g in combo],
                liked=True,
                occasion=ctx["occasion"],
                mood=ctx["mood"],
                activity=ctx["activity"],
                weather_tag=weather_tag
            )
            user_id = st.session_state["user"].id
            add_feedback_cloud(user_id, new_feedback)
            st.session_state.feedback = load_feedback_cloud(user_id)
            st.success("Guardado. Tendré en cuenta que este outfit te gustó.")
            st.rerun()

    with col_dislike:
        if st.button(
            "👎 No me gusta",
            key=f"dislike_{section}_{outfit_index}_{combo_key}_{context_key}",
            use_container_width=True
        ):
            new_feedback = OutfitFeedback(
                id=get_next_feedback_id(st.session_state.feedback),
                garment_ids=[g.id for g in combo],
                liked=False,
                occasion=ctx["occasion"],
                mood=ctx["mood"],
                activity=ctx["activity"],
                weather_tag=weather_tag
            )
            user_id = st.session_state["user"].id
            add_feedback_cloud(user_id, new_feedback)
            st.session_state.feedback = load_feedback_cloud(user_id)
            st.warning("Guardado. Evitaré priorizar este outfit en contextos parecidos.")
            st.rerun()


def dedupe_outfit_history(history_lists, max_items=30):
    unique_history = []
    seen = set()

    for outfit_ids in history_lists:
        key = tuple(sorted(int(x) for x in outfit_ids))
        if key not in seen:
            seen.add(key)
            unique_history.append(list(key))

    return unique_history[-max_items:]


def remember_outfit(combo):
    outfit_ids = sorted([g.id for g in combo])
    merged = st.session_state.outfit_history + [outfit_ids]
    st.session_state.outfit_history = dedupe_outfit_history(merged, max_items=20)


def remember_shown_outfits(outfits):
    if not outfits:
        return

    shown_history = st.session_state.get("shown_outfit_history", [])

    for _, combo in outfits:
        shown_history.append(sorted([g.id for g in combo]))

    st.session_state.shown_outfit_history = dedupe_outfit_history(
        shown_history,
        max_items=12
    )


def get_recent_outfit_memory():
    """
    Prioriza outfits realmente usados.
    Los mostrados solo aportan una memoria corta para evitar repetición inmediata,
    pero sin dominar el motor.
    """
    used_history = st.session_state.get("outfit_history", [])
    shown_history = st.session_state.get("shown_outfit_history", [])

    reduced_shown_history = shown_history[-3:]

    combined = used_history + reduced_shown_history
    return dedupe_outfit_history(combined, max_items=24)


def normalize_existing_images():
    for filename in os.listdir(IMAGES_DIR):
        file_path = os.path.join(IMAGES_DIR, filename)

        try:
            image = Image.open(file_path)
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGB")
            square_image = ImageOps.fit(image, (300, 300), Image.Resampling.LANCZOS)
            square_image.save(file_path, format="JPEG", quality=85)
        except Exception as e:
            print(f"Error procesando {filename}: {e}")


# normalize_existing_images()


# =========================================================
# BASE INICIAL DE PRENDAS
# =========================================================

def default_wardrobe() -> List[Garment]:
    return [
        Garment(
            id=1,
            name="Camisa blanca ML con rayas",
            category="top",
            color="blanco",
            style="elegante",
            secondary_styles=[],
            warmth="medio",
            waterproof=False,
            dress_level="arreglado",
            image_name=None
        ),
        Garment(
            id=2,
            name="Camisa celeste ML lisa",
            category="top",
            color="celeste",
            style="elegante",
            secondary_styles=[],
            warmth="medio",
            waterproof=False,
            dress_level="arreglado",
            image_name=None
        ),
        Garment(
            id=3,
            name="Polera negra básica",
            category="top",
            color="negro",
            style="casual",
            secondary_styles=[],
            warmth="caluroso",
            waterproof=False,
            dress_level="relajado",
            image_name=None
        ),
        Garment(
            id=4,
            name="Polera blanca básica",
            category="top",
            color="blanco",
            style="casual",
            secondary_styles=[],
            warmth="caluroso",
            waterproof=False,
            dress_level="relajado",
            image_name=None
        ),
        Garment(
            id=5,
            name="Jeans ajustados",
            category="bottom",
            color="azul",
            style="urbano",
            secondary_styles=[],
            warmth="medio",
            waterproof=False,
            dress_level="flexible",
            image_name=None
        ),
        Garment(
            id=6,
            name="Jeans anchos",
            category="bottom",
            color="azul",
            style="casual",
            secondary_styles=[],
            warmth="medio",
            waterproof=False,
            dress_level="relajado",
            image_name=None
        ),
        Garment(
            id=7,
            name="Pantalón de tela azul marino",
            category="bottom",
            color="azul marino",
            style="elegante",
            secondary_styles=[],
            warmth="medio",
            waterproof=False,
            dress_level="arreglado",
            image_name=None
        ),
        Garment(
            id=8,
            name="Zapatillas urbanas negras",
            category="shoes",
            color="negro",
            style="urbano",
            secondary_styles=[],
            warmth="medio",
            waterproof=False,
            dress_level="flexible",
            image_name=None
        ),
        Garment(
            id=9,
            name="Zapatos de cuero",
            category="shoes",
            color="negro",
            style="elegante",
            secondary_styles=[],
            warmth="medio",
            waterproof=False,
            dress_level="elegante",
            image_name=None
        ),
        Garment(
            id=10,
            name="Chaqueta liviana café",
            category="outerwear",
            color="café",
            style="casual",
            secondary_styles=[],
            warmth="frio",
            waterproof=False,
            dress_level="flexible",
            image_name=None
        ),
        Garment(
            id=11,
            name="Chaqueta impermeable negra",
            category="outerwear",
            color="negro",
            style="urbano",
            secondary_styles=[],
            warmth="frio",
            waterproof=True,
            dress_level="flexible",
            image_name=None
        ),
        Garment(
            id=12,
            name="Blazer azul marino",
            category="midlayer",
            color="azul marino",
            style="elegante",
            secondary_styles=["formal"],
            warmth="medio",
            waterproof=False,
            dress_level="elegante",
            image_name=None
        ),
        Garment(
            id=13,
            name="Reloj plateado",
            category="accessory",
            color="plateado",
            style="elegante",
            secondary_styles=[],
            warmth="medio",
            waterproof=False,
            dress_level="arreglado",
            image_name=None
        ),
    ]


def get_next_id(wardrobe: List[Garment]) -> int:
    if not wardrobe:
        return 1
    return max(g.id for g in wardrobe) + 1


def get_next_feedback_id(feedback_list: List[OutfitFeedback]) -> int:
    if not feedback_list:
        return 1
    return max(fb.id for fb in feedback_list) + 1


# =========================================================
# UTILIDADES
# =========================================================

def normalize_text(text: str) -> str:
    return text.strip().lower()


def infer_from_filename(filename: str):
    name = normalize_text(filename)

    category = "top"
    color = "negro"
    style = "casual"
    warmth = "medio"
    waterproof = False
    dress_level = "flexible"

    garment_name = (
        filename
        .rsplit(".", 1)[0]
        .replace("_", " ")
        .replace("-", " ")
        .title()
    )

    if any(x in name for x in ["camisa", "polera", "blusa", "top", "shirt"]):
        category = "top"
    elif any(x in name for x in ["jean", "pantalon", "falda", "short", "bottom", "jogger"]):
        category = "bottom"
    elif any(x in name for x in ["zapato", "zapatilla", "bota", "shoe", "sneaker"]):
        category = "shoes"
    elif any(x in name for x in ["blazer", "chaleco", "sweater", "sueter", "cardigan", "cárdigan"]):
        category = "midlayer"
    elif any(x in name for x in ["chaqueta", "abrigo", "parka", "impermeable", "jacket"]):
        category = "outerwear"
    elif any(x in name for x in ["reloj", "collar", "cinturon", "cinturón", "accesorio", "accessory"]):
        category = "accessory"

    sorted_colors = sorted(COLOR_OPTIONS + list(COLOR_ALIASES.keys()), key=len, reverse=True)

    for c in sorted_colors:
        if c in name:
            color = normalize_color_name(c)
            break

    if any(x in name for x in ["elegante", "formal", "blazer"]):
        style = "elegante"
        dress_level = "elegante"
    elif any(x in name for x in ["urbano", "street"]):
        style = "urbano"
        dress_level = "flexible"
    elif any(x in name for x in ["sport", "deporte", "running", "gym", "buzo"]):
        style = "sport"
        dress_level = "relajado"
    else:
        style = "casual"

    if any(x in name for x in ["polar", "parka", "abrigo", "invierno", "lana"]):
        warmth = "frio"
    elif any(x in name for x in ["polera", "short", "verano", "liviano"]):
        warmth = "caluroso"
    else:
        warmth = "medio"

    if any(x in name for x in ["impermeable", "rain", "agua"]):
        waterproof = True

    return {
        "name": garment_name,
        "category": category,
        "color": color,
        "style": style,
        "secondary_styles": [],
        "warmth": warmth,
        "waterproof": waterproof,
        "dress_level": dress_level,
        "image_name": filename,
    }

def garment_color_label(g) -> str:
    secondary = getattr(g, "secondary_colors", []) or []
    secondary = [str(c).strip() for c in secondary if c and str(c).strip()]
    if secondary:
        return f"{g.color} + {', '.join(secondary)}"
    return str(getattr(g, "color", "negro"))

# =========================================================
# ESTADO DE LA APLICACIÓN (SESSION STATE)
# =========================================================

if "closet_profile" not in st.session_state:
    st.session_state.closet_profile = None

if "photo_uploader_key" not in st.session_state:
    st.session_state.photo_uploader_key = 0

if "selected_garment_id" not in st.session_state:
    st.session_state.selected_garment_id = None

if "wardrobe" not in st.session_state:
    st.session_state.wardrobe = load_wardrobe_cloud(user_id)

if "feedback" not in st.session_state:
    st.session_state.feedback = load_feedback_cloud(user_id)

if "used_outfits" not in st.session_state:
    st.session_state.used_outfits = load_used_outfits_cloud(user_id)

if "outfit_history" not in st.session_state:
    st.session_state.outfit_history = [
        sorted(item.garment_ids) for item in st.session_state.used_outfits
    ][-20:]

if "shown_outfit_history" not in st.session_state:
    st.session_state.shown_outfit_history = []

if "last_outfits" not in st.session_state:
    st.session_state.last_outfits = []

if "last_context" not in st.session_state:
    st.session_state.last_context = None

if "next_id" not in st.session_state:
    st.session_state.next_id = get_next_id(st.session_state.wardrobe)

if "last_detected" not in st.session_state:
    st.session_state.last_detected = None

if "garment_just_saved" not in st.session_state:
    st.session_state.garment_just_saved = False

if "has_generated_outfits" not in st.session_state:
    st.session_state.has_generated_outfits = False

if "week_plan" not in st.session_state:
    st.session_state.week_plan = None

if "week_weather" not in st.session_state:
    st.session_state.week_weather = {}


def is_recent_outfit(combo):
    outfit_ids = sorted([g.id for g in combo])
    return outfit_ids in get_recent_outfit_memory()


# =========================================================
# ONBOARDING PERFIL DEL CLÓSET
# =========================================================

if st.session_state.closet_profile is None:
    st.subheader("Configura tu clóset")

    profile = st.radio(
        "¿Cómo describirías tu clóset?",
        ["mayormente femenino", "mayormente masculino", "mixto"],
        horizontal=True,
        key="closet_profile_radio"
    )

    if st.button("Guardar perfil del clóset", key="save_closet_profile"):
        st.session_state.closet_profile = profile
        st.rerun()

    st.stop()


# =========================================================
# UI
# =========================================================

st.caption(f"Perfil del clóset: {st.session_state.closet_profile}")
debug_mode = st.toggle("🔧 Modo debug", value=False, key="debug_mode")

tab1, tab2, tab3, tab4 = st.tabs([
    "🌤️ Hoy",
    "👕 Mi clóset",
    "➕ Agregar prenda",
    "📅 Planificador semanal"
])


# =========================================================
# TAB 1: RECOMENDADOR
# =========================================================
with tab1:
    st.subheader("Recomiéndame algo para hoy")

    col1, col2, col3 = st.columns(3)
    with col1:
        occasion = st.selectbox("Ocasión", OCCASION_OPTIONS)
        mood = st.selectbox("Mood / estilo deseado", MOOD_OPTIONS)
        
    with col2:
        activity = st.selectbox("Actividad", ACTIVITY_OPTIONS)
        use_real_weather = st.toggle("Usar clima real", value=True)

        if use_real_weather:
            weather_data = get_current_weather(DEFAULT_CITY, WEATHER_API_KEY)
            if weather_data:
                temp = weather_data["temp"]
                rain = weather_data["rain"]
                st.success(f"{DEFAULT_CITY} · {format_weather_label(weather_data)}")
            else:
                st.warning("No se pudo obtener el clima. Usa ajuste manual.")
                temp = st.slider("Temperatura (°C)", 0, 35, 16)
                rain = st.toggle("¿Llueve?")
        else:
            temp = st.slider("Temperatura (°C)", 0, 35, 16)
            rain = st.toggle("¿Llueve?")

    # Variables por defecto — sin ajuste
    thermal_sensitivity = "normal"
    indoor_outdoor = "exterior"
    manual_sky = "despejado"
    expander_active = False

    with st.expander("Ajuste manual opcional", expanded=False):
        expander_active = True

        col_manual_1, col_manual_2 = st.columns(2)

        with col_manual_1:
            thermal_sensitivity = st.selectbox(
                "Sensibilidad térmica",
                ["normal", "friolento/a", "caluroso/a"],
                key="thermal_sensitivity"
            )

        with col_manual_2:
            indoor_outdoor = st.selectbox(
                "¿Dónde estarás?",
                ["exterior", "interior"],
                key="indoor_outdoor"
            )

        if indoor_outdoor == "exterior":
            manual_sky = st.selectbox(
                "Cielo",
                ["despejado", "nublado"],
                key="manual_sky"
            )
        else:
            manual_sky = "despejado"

        temp_ajustada = temp

        if thermal_sensitivity == "friolento/a":
            temp_ajustada -= 2
        elif thermal_sensitivity == "caluroso/a":
            temp_ajustada += 3

        if indoor_outdoor == "interior":
            temp_ajustada += 4
        elif indoor_outdoor == "exterior" and manual_sky == "nublado":
            temp_ajustada -= 2

        temp = temp_ajustada

        temp = temp_ajustada


    st.markdown("### Usar una prenda específica (opcional)")

    wardrobe_sorted = sorted(
        st.session_state.wardrobe,
        key=lambda g: (
            str(getattr(g, "name", "")).lower(),
            str(getattr(g, "category", "")).lower(),
            garment_color_label(g).lower(),
        ),
    )

    selected_garment = st.selectbox(
        "Elige una prenda que quieras usar",
        options=[None] + wardrobe_sorted,
        format_func=lambda g: (
            "— Ninguna —"
            if g is None
            else f"{g.name} ({CATEGORY_LABELS_ES.get(g.category, g.category)}, {garment_color_label(g)})"
        ),
    )

    selected_allowed = True

    if selected_garment is not None:
        selected_allowed, reason = garment_allowed_for_occasion(selected_garment, occasion, rain, mood=mood, temp=temp)
        if not selected_allowed:
            st.warning(reason)

        # Advertencia de clima para prenda forzada
        if selected_garment.category == "outerwear" and temp >= 24:
            st.warning(f"{selected_garment.name} puede ser demasiado abrigada para {temp}°C — pero tú decides.")

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    generate_clicked = col_btn1.button("✨ ¿Qué me pongo?", use_container_width=True)
    surprise_clicked = col_btn2.button("🎲 Outfit sorpresa", use_container_width=True)

    show_anyway_clicked = False
    if selected_garment:
        show_anyway_clicked = col_btn3.button("Mostrar de todos modos", use_container_width=True)

    outfits = st.session_state.get("last_outfits", [])
    recent_memory = get_recent_outfit_memory()

    if generate_clicked or show_anyway_clicked:
        if selected_garment:
            outfits = generate_outfits_from_selected_garment(
                garments=st.session_state.wardrobe,
                selected_garment=selected_garment,
                occasion=occasion,
                temp=temp,
                rain=rain,
                mood=mood,
                activity=activity,
                top_n=3,
                feedback_list=st.session_state.feedback,
                recent_outfits=recent_memory,
                ignore_occasion_for_selected=show_anyway_clicked,
            )
        else:
            outfits = generate_outfits(
                garments=st.session_state.wardrobe,
                occasion=occasion,
                temp=temp,
                rain=rain,
                mood=mood,
                activity=activity,
                top_n=3,
                feedback_list=st.session_state.feedback,
                recent_outfits=recent_memory,
            )

            # Si es interior con frío, forzar al menos 1 outfit sin outerwear
            if indoor_outdoor == "interior" and temp <= 14:
                tiene_sin_abrigo = any(
                    not any(g.category == "outerwear" for g in combo)
                    for _, combo in outfits
                )

                if not tiene_sin_abrigo and len(outfits) >= 2:
                    outfits_sin_abrigo = generate_outfits(
                        garments=st.session_state.wardrobe,
                        occasion=occasion,
                        temp=temp + 6,
                        rain=False,
                        mood=mood,
                        activity=activity,
                        top_n=3,
                        feedback_list=st.session_state.feedback,
                        recent_outfits=recent_memory,
                    )

                    sin_abrigo = [
                        (score, combo) for score, combo in outfits_sin_abrigo
                        if not any(g.category == "outerwear" for g in combo)
                    ]

                    if sin_abrigo:
                        outfits = list(outfits)
                        outfits[-1] = sin_abrigo[0]

        remember_shown_outfits(outfits)
        st.session_state.last_outfits = outfits
    
    elif surprise_clicked:
        surprise_candidates = [
            g for g in st.session_state.wardrobe
            if garment_allowed_for_occasion(g, occasion, rain, mood=mood, temp=temp)[0]
        ]

        if surprise_candidates:
            forced = random.choice(surprise_candidates)

            outfits = generate_outfits_from_selected_garment(
                garments=st.session_state.wardrobe,
                selected_garment=forced,
                occasion=occasion,
                temp=temp,
                rain=rain,
                mood=mood,
                activity=activity,
                top_n=3,
                feedback_list=st.session_state.feedback,
                recent_outfits=recent_memory,
            )
        else:
            outfits = []

        remember_shown_outfits(outfits)
        st.session_state.last_outfits = outfits

    st.markdown("## Resultados")

    if not outfits and st.session_state.has_generated_outfits:
        st.info("No hay prendas suficientes para armar este outfit.")
    else:
        for idx, (score, combo) in enumerate(outfits, start=1):
            if debug_mode:
                st.markdown(f"### Outfit {idx} · Score {score}")
            else:
                st.markdown(f"### Outfit {idx}")        
            
            if st.session_state.get("outfit_used_message_idx") == idx:
                st.success(st.session_state.get("outfit_used_message_text", "Outfit guardado como usado."))
                del st.session_state["outfit_used_message_idx"]
                del st.session_state["outfit_used_message_text"]

            cols = st.columns(len(combo))

            for col, g in zip(cols, combo):
                with col:
                    with st.container():
                        st.markdown(f"**{g.name}**")
                        st.caption(f"{CATEGORY_LABELS_ES.get(g.category, g.category)} · {garment_color_label(g)}")
                        render_garment_image(g, width=140)

            explanation = explain_outfit_score(
                combo,
                occasion,
                temp,
                rain,
                mood,
                activity,
                feedback_list=st.session_state.feedback,
                recent_outfits=get_recent_outfit_memory(),
            )

            if explanation:
                st.markdown(
                    " &nbsp;|&nbsp; ".join(explanation),
                    unsafe_allow_html=True
                )

            has_skirt = any(g.category == "bottom" and is_bottom_skirt(g) for g in combo)
            has_short = any(
                g.category == "bottom" and "short" in g.name.lower()
                for g in combo
            )

            if has_skirt and (rain or temp <= 12):
                st.info("❄️ Tip: si usas falda con este clima, no olvides tus pantys.")
            elif has_short and (rain or temp <= 12):
                st.info("❄️ Tip: si usas short con este clima, considera unas pantys o medias.")

            ctx = {
                "occasion": occasion,
                "mood": mood,
                "activity": activity,
                "temp": temp,
                "rain": rain,
            }

            weather_tag = get_weather_tag(temp, rain)

            render_feedback_buttons(
                combo,
                outfit_index=idx,
                ctx=ctx,
                weather_tag=weather_tag,
                section="tab1"
            )

            if st.button("💃 lo usaré", key=f"use_{idx}", use_container_width=True):
                remember_outfit(combo)

                current_used_outfits = st.session_state.get("used_outfits", [])

                new_used_outfit = UsedOutfit(
                    id=get_next_used_outfit_id(current_used_outfits),
                    garment_ids=[g.id for g in combo],
                    used_at=str(date.today()),
                    occasion=ctx["occasion"],
                    mood=ctx["mood"],
                    activity=ctx["activity"],
                    weather_tag=weather_tag,
                )

                add_used_outfit_cloud(user_id, new_used_outfit)
                st.session_state.used_outfits = load_used_outfits_cloud(user_id)

                st.session_state["outfit_used_message_idx"] = idx
                st.session_state["outfit_used_message_text"] = "Outfit guardado como usado."
                st.rerun()

            st.divider()

        if st.session_state.has_generated_outfits:
            if len(outfits) == 0:
                st.info("No encontré outfits para estos parámetros. Prueba cambiando la ocasión, mood o clima, o agrega más prendas a tu clóset.")
            elif len(outfits) == 1:
                st.info("Solo encontré 1 combinación para estos parámetros. Para ver más opciones, prueba cambiar algún parámetro o agrega más prendas.")
            elif len(outfits) == 2:
                st.info("Solo encontré 2 combinaciones para estos parámetros. Para ver más opciones, prueba cambiar algún parámetro o agrega más prendas.")

# =========================================================
# TAB 2: MI CLÓSET
# =========================================================
with tab2:
    st.subheader("Mi clóset")

    wardrobe = sorted(st.session_state.wardrobe, key=lambda g: g.name.lower())

    if not wardrobe:
        st.warning("No hay prendas cargadas.")
    else:
        st.markdown("### Galería de prendas")

        col_f1, col_f2 = st.columns(2)

        with col_f1:
            filter_category = st.selectbox(
                "Filtrar por categoría",
                ["todas"] + CATEGORY_OPTIONS,
                key="filter_category_tab2",
                format_func=lambda c: "Todas" if c == "todas" else CATEGORY_LABELS_ES.get(c, c)
            )

        with col_f2:
            color_icons = {
                "amarillo": "🟡",
                "azul": "🔵",
                "azul marino": "🔵",
                "beige": "🟤",
                "blanco": "⚪",
                "burdeo": "🔴",
                "café": "🟤",
                "celeste": "🔵",
                "crema": "⚪",
                "dorado": "🟡",
                "fucsia": "🟣",
                "gris": "⚪",
                "gris claro": "⚪",
                "gris oscuro": "⚫",
                "lila": "🟣",
                "morado": "🟣",
                "mostaza": "🟡",
                "multicolor": "🌈",
                "naranja": "🟠",
                "negro": "⚫",
                "plateado": "⚪",
                "rojo": "🔴",
                "rosado": "🟣",
                "verde": "🟢",
                "verde olivo": "🟢",
                "verde oscuro": "🟢",
            }

            sorted_color_options = sorted(COLOR_OPTIONS)

            filter_color = st.selectbox(
                "Filtrar por color",
                ["todos"] + sorted_color_options,
                key="filter_color_tab2",
                format_func=lambda c: "— todos —" if c == "todos" else f"{color_icons.get(c, '⬜')} {c}"
            )

        filtered_wardrobe = wardrobe

        if filter_category != "todas":
            filtered_wardrobe = [g for g in filtered_wardrobe if g.category == filter_category]

        if filter_color != "todos":
            filtered_wardrobe = [g for g in filtered_wardrobe if normalize_color_name(g.color) == filter_color]

        if not filtered_wardrobe:
            st.info("No hay prendas que coincidan con ese filtro.")
        else:
            cols = st.columns(5)

            for i, g in enumerate(filtered_wardrobe):
                with cols[i % 5]:
                    with st.container(border=True):
                        render_garment_image(g, width=120)
                        st.markdown(f"**{g.name[:18]}**")
                        if getattr(g, "is_new", False):
                            st.caption("🆕 Nueva")
                        issue = detect_garment_issues(g)
                        if issue and not st.session_state.get(f"issue_ignored_{g.id}", False):
                            st.caption(f"⚠️ {issue}")
                            col_ignore, col_edit = st.columns(2)
                            with col_ignore:
                                if st.button("Ignorar", key=f"ignore_issue_{g.id}", use_container_width=True):
                                    st.session_state[f"issue_ignored_{g.id}"] = True
                                    st.rerun()
                            with col_edit:
                                if st.button("✏️ Revisar", key=f"review_issue_{g.id}", use_container_width=True):
                                    st.session_state.selected_garment_id = g.id
                                    st.rerun()
                        color_icons = {
                            "amarillo": "🟡",
                            "azul": "🔵",
                            "azul marino": "🔵",
                            "beige": "🟤",
                            "blanco": "⚪",
                            "burdeo": "🔴",
                            "café": "🟤",
                            "celeste": "🔵",
                            "crema": "⚪",
                            "dorado": "🟡",
                            "fucsia": "🟣",
                            "gris": "⚪",
                            "gris claro": "⚪",
                            "gris oscuro": "⚫",
                            "lila": "🟣",
                            "morado": "🟣",
                            "mostaza": "🟡",
                            "multicolor": "🌈",
                            "naranja": "🟠",
                            "negro": "⚫",
                            "plateado": "⚪",
                            "rojo": "🔴",
                            "rosado": "🟣",
                            "verde": "🟢",
                            "verde olivo": "🟢",
                            "verde oscuro": "🟢",
                        }

                        color_label = normalize_color_name(g.color)

                        st.caption(
                            f"{CATEGORY_LABELS_ES.get(g.category, g.category)} · {color_icons.get(color_label, '⬜')} {color_label}"
                        )

                        pattern_label = getattr(g, "pattern", "liso")

                        if pattern_label != "liso":
                            st.caption(f"Patrón: {pattern_label}")

                        if st.button("✏️ Editar", key=f"edit_card_{g.id}", use_container_width=True):
                            st.session_state.selected_garment_id = g.id
                            st.rerun()

        st.markdown("---")
        st.markdown("### Editar prenda")

        if st.session_state.selected_garment_id is None:
            st.info("Haz clic en ✏️ Editar sobre una prenda de la galería.")
        else:
            garment = next(
                (g for g in wardrobe if g.id == st.session_state.selected_garment_id),
                None
            )

            if garment is None:
                st.warning("La prenda seleccionada no existe.")
                st.session_state.selected_garment_id = None
            else:
                st.caption(f"Prenda seleccionada: {garment.name}")

                with st.container(border=True):
                    st.markdown(f"#### Editando: {garment.name}")

                    if st.session_state.get("edit_saved_message") == garment.id:
                        st.success("Edición guardada.")
                        del st.session_state["edit_saved_message"]

                    st.markdown("##### Imagen actual")

                    if garment.image_name:
                        current_image_path = os.path.join(IMAGES_DIR, garment.image_name)
                        if os.path.exists(current_image_path):
                            st.image(current_image_path, caption=garment.name, width=260)
                        else:
                            st.warning(f"No se encontró la imagen: {garment.image_name}")
                    else:
                        st.info("Esta prenda aún no tiene foto.")

                    garment_color = normalize_color_name(getattr(garment, "color", "blanco"))

                    style = st.selectbox(
                        "Estilo principal",
                        STYLE_OPTIONS,
                        index=STYLE_OPTIONS.index(garment.style) if garment.style in STYLE_OPTIONS else 0,
                        key=f"edit_style_{garment.id}"
                    )

                    available_secondary_styles = [s for s in STYLE_OPTIONS if s != style]

                    current_secondary_styles = getattr(garment, "secondary_styles", [])

                    secondary_styles_key = f"secondary_styles_{garment.id}"
                    if secondary_styles_key not in st.session_state:
                        st.session_state[secondary_styles_key] = [
                            s for s in current_secondary_styles if s in available_secondary_styles
                        ]

                    st.session_state[secondary_styles_key] = [
                        s for s in st.session_state[secondary_styles_key]
                        if s in available_secondary_styles
                    ]

                    secondary_styles = st.multiselect(
                        "Estilos secundarios",
                        available_secondary_styles,
                        key=secondary_styles_key
                    )

                    current_pattern = getattr(garment, "pattern", "liso")
                    pattern_options_base = [
                        "liso",
                        "rayas",
                        "cuadros",
                        "estampado",
                        "animal_print",
                        "floral",
                        "grafico",
                    ]

                    pattern_options_edit = [current_pattern] + [p for p in pattern_options_base if p != current_pattern]

                    pattern = st.selectbox(
                        "Patrón / diseño",
                        pattern_options_edit,
                        index=0,
                        key=f"edit_pattern_{garment.id}"
                    )
                    
                    color_key = f"edit_color_{garment.id}"
                    if color_key not in st.session_state:
                        st.session_state[color_key] = garment_color if garment_color in COLOR_OPTIONS else COLOR_OPTIONS[0]

                    color_icons = {
                        "blanco": "⚪",
                        "negro": "⚫",
                        "gris": "⚪",
                        "gris claro": "⚪",
                        "gris oscuro": "⚫",
                        "azul": "🔵",
                        "azul marino": "🔵",
                        "celeste": "🔵",
                        "verde": "🟢",
                        "verde olivo": "🟢",
                        "verde oscuro": "🟢",
                        "rojo": "🔴",
                        "burdeo": "🔴",
                        "rosado": "🟣",
                        "fucsia": "🟣",
                        "morado": "🟣",
                        "lila": "🟣",
                        "amarillo": "🟡",
                        "mostaza": "🟡",
                        "naranja": "🟠",
                        "café": "🟤",
                        "beige": "🟤",
                        "crema": "⚪",
                        "plateado": "⚪",
                        "dorado": "🟡",
                        "multicolor": "🌈",
                    }   

                    sorted_colors = sorted(COLOR_OPTIONS)

                    color = st.selectbox(
                        "Color principal",
                        sorted_colors,
                        key=color_key,
                        format_func=lambda c: f"{color_icons.get(c, '⬜')} {c}"
                    )

                    current_secondary_colors = [
                        normalize_color_name(c)
                        for c in getattr(garment, "secondary_colors", [])
                    ]

                    key_sc = f"secondary_colors_{garment.id}"

                    if pattern != "liso":
                        available_secondary_colors = [c for c in COLOR_OPTIONS if c != color]

                        if key_sc not in st.session_state:
                            st.session_state[key_sc] = [
                                c for c in current_secondary_colors if c in available_secondary_colors
                            ]
                        else:
                            st.session_state[key_sc] = [
                                c for c in st.session_state[key_sc] if c in available_secondary_colors
                            ]

                        secondary_colors = st.multiselect(
                            "Colores secundarios",
                            available_secondary_colors,
                            key=key_sc,
                            help="Selecciona colores presentes en estampados, rayas, floral, animal print, etc."
                        )
                    else:
                        if key_sc in st.session_state:
                            st.session_state[key_sc] = []
                        secondary_colors = []

                    with st.form(f"edit_garment_{garment.id}"):
                        name = st.text_input("Nombre", value=garment.name)

                        category = st.selectbox(
                            "Categoría",
                            CATEGORY_OPTIONS,
                            index=CATEGORY_OPTIONS.index(garment.category) if garment.category in CATEGORY_OPTIONS else 0,
                            format_func=lambda c: CATEGORY_LABELS_ES.get(c, c)
                        )

                        current_subcategory = getattr(garment, "subcategory", None)

                        subcategory_options = ["— ninguna —"] + SUBCATEGORY_OPTIONS.get(category, [])

                        subcategory = st.selectbox(
                            "Subcategoría",
                            subcategory_options,
                            index=subcategory_options.index(current_subcategory)
                            if current_subcategory in subcategory_options else 0,
                            format_func=lambda x: "— ninguna —" if x == "— ninguna —" else SUBCATEGORY_LABELS_ES.get(x, x)
                        )

                        if subcategory == "— ninguna —":
                            subcategory = None

                        accessory_type = None
                        if category == "accessory":
                            current_accessory_type = getattr(garment, "accessory_type", None) or "reloj"
                            accessory_type = st.selectbox(
                                "Tipo de accesorio",
                                ACCESSORY_TYPE_OPTIONS,
                                index=ACCESSORY_TYPE_OPTIONS.index(current_accessory_type)
                                if current_accessory_type in ACCESSORY_TYPE_OPTIONS else 0
                            )
                        
                        warmth = "medio"
                        show_warmth = (
                            category in ["top", "midlayer", "outerwear", "bottom", "shoes"]
                            or (category == "accessory" and accessory_type in THERMAL_ACCESSORIES)
                        )

                        if show_warmth:
                            current_warmth = garment.warmth if garment.warmth in WARMTH_OPTIONS else "medio"
                            warmth = st.selectbox(
                                "Tipo térmico",
                                WARMTH_OPTIONS,
                                index=WARMTH_OPTIONS.index(current_warmth)
                            )

                        waterproof = st.checkbox("Impermeable", value=garment.waterproof)

                        dress_level = st.selectbox(
                            "Nivel de formalidad",
                            DRESS_LEVEL_OPTIONS,
                            index=DRESS_LEVEL_OPTIONS.index(garment.dress_level)
                            if garment.dress_level in DRESS_LEVEL_OPTIONS else 0
                        )
                        
                        sexiness = st.slider(
                            "Nivel sexy",
                            min_value=0,
                            max_value=3,
                            value=getattr(garment, "sexiness", 0),
                            key=f"edit_sexiness_{garment.id}",
                            help="0 = nada sexy, 1 = bajo, 2 = medio, 3 = alto"
                        )

                        new_uploaded_file = st.file_uploader(
                            "Agregar o reemplazar foto de esta prenda",
                            type=["jpg", "jpeg", "png", "webp"],
                            key=f"edit_photo_{garment.id}"
                        )

                        if new_uploaded_file:
                            st.image(new_uploaded_file, caption="Nueva foto", width=260)

                        col_save, col_delete = st.columns(2)

                        with col_save:
                            save_changes = st.form_submit_button("Guardar cambios")

                        with col_delete:
                            delete_garment = st.form_submit_button("Eliminar prenda")

                    col_cancel_left, col_cancel_right = st.columns([1, 3])
                    with col_cancel_left:
                        cancel_edit = st.button("Cancelar edición", key=f"cancel_edit_{garment.id}")

                    if save_changes:
                        if not name.strip():
                            st.error("La prenda debe tener nombre.")
                        else:
                            garment.name = name.strip()
                            garment.category = category
                            garment.subcategory = subcategory
                            garment.color = normalize_color_name(color)
                            garment.secondary_colors = [normalize_color_name(c) for c in secondary_colors]
                            garment.style = style
                            garment.secondary_styles = secondary_styles
                            garment.pattern = pattern
                            garment.warmth = warmth
                            garment.waterproof = waterproof
                            garment.dress_level = dress_level
                            garment.sexiness = sexiness
                            garment.accessory_type = accessory_type if category == "accessory" else None
                            garment.is_new = False

                            if new_uploaded_file:
                                image_name = upload_garment_image(user_id, garment.id, new_uploaded_file)
                                garment.image_name = image_name

                            update_garment_cloud(user_id, garment)
                            st.session_state["edit_saved_message"] = garment.id
                            st.success("Edición guardada.")

                    if delete_garment:
                        delete_garment_cloud(user_id, garment.id)

                        st.session_state.wardrobe = [
                            g for g in st.session_state.wardrobe if g.id != garment.id
                        ]
                        st.session_state.next_id = get_next_id(st.session_state.wardrobe)
                        st.session_state.selected_garment_id = None
                        st.rerun()

                    if cancel_edit:
                        st.session_state.selected_garment_id = None
                        if "edit_saved_message" in st.session_state:
                            del st.session_state["edit_saved_message"]
                        st.rerun()
# =========================================================
# TAB 3: AGREGAR PRENDA
# =========================================================
with tab3:
    st.subheader("➕ Agregar prenda")

    if "form_name" not in st.session_state:
        st.session_state.form_name = ""

    if "form_category" not in st.session_state:
        st.session_state.form_category = "top"

    if "form_accessory_type" not in st.session_state:
        st.session_state.form_accessory_type = "reloj"

    if "form_color" not in st.session_state:
        st.session_state.form_color = "negro"

    if "form_secondary_color" not in st.session_state:
        st.session_state.form_secondary_color = "ninguno"

    if "form_pattern" not in st.session_state:
        st.session_state.form_pattern = "liso"

    if "form_style" not in st.session_state:
        st.session_state.form_style = "casual"

    if "form_secondary_styles" not in st.session_state:
        st.session_state.form_secondary_styles = []

    if "form_warmth" not in st.session_state:
        st.session_state.form_warmth = "medio"

    if "form_waterproof" not in st.session_state:
        st.session_state.form_waterproof = False

    if "form_dress_level" not in st.session_state:
        st.session_state.form_dress_level = "flexible"

    if "form_uploader_key" not in st.session_state:
        st.session_state.form_uploader_key = 0
    
    if st.session_state.get("add_saved_message"):
        st.success(st.session_state["add_saved_message"])
        del st.session_state["add_saved_message"]

    if "form_subcategory" not in st.session_state:
        st.session_state.form_subcategory = None

    if "form_inferred_done" not in st.session_state:
        st.session_state.form_inferred_done = False

    if st.session_state.get("reset_add_form"):
        st.session_state.form_name = ""
        st.session_state.form_category = "top"
        st.session_state.form_subcategory = None
        st.session_state.form_accessory_type = "reloj"
        st.session_state.form_color = "negro"
        st.session_state.form_secondary_color = "ninguno"
        st.session_state.form_pattern = "liso"
        st.session_state.form_style = "casual"
        st.session_state.form_secondary_styles = []
        st.session_state.form_warmth = "medio"
        st.session_state.form_waterproof = False
        st.session_state.form_sexiness_add = 0
        st.session_state.form_dress_level = "flexible"
        st.session_state.form_inferred_done = False
        del st.session_state["reset_add_form"]

    # =========================================================
    # SECCIÓN: SUBIDA MÚLTIPLE DE FOTOS
    # =========================================================
    st.markdown("### 📸 Agregar fotos")
    st.caption("Puedes subir hasta 5 prendas a la vez")

    if "bulk_uploader_key" not in st.session_state:
        st.session_state.bulk_uploader_key = 0

    if st.session_state.get("bulk_saved_summary"):
        summary = st.session_state.pop("bulk_saved_summary")
        st.success(summary["message"])
        for item in summary["items"]:
            st.markdown(f"- **{item['name']}** — {item['attrs']}")

    bulk_files = st.file_uploader(
        "Selecciona hasta 5 fotos",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=f"bulk_uploader_{st.session_state.bulk_uploader_key}"
    )

    if bulk_files:
        if len(bulk_files) > 5:
            st.warning("Solo se procesarán las primeras 5 fotos.")
            bulk_files = bulk_files[:5]

        if st.button("Agregar prendas automáticamente", key="bulk_add_btn"):
            added_items = []
            for uf in bulk_files:
                suggested = suggest_name_from_filename(uf.name)
                if not suggested:
                    base = os.path.splitext(uf.name)[0]
                    suggested = re.sub(r"[_\-]+", " ", base).strip() or uf.name

                inferred = infer_attributes_from_name(suggested)

                cat = inferred.get("category") if inferred.get("category") in CATEGORY_OPTIONS else "top"
                sub = inferred.get("subcategory")
                if sub not in SUBCATEGORY_OPTIONS.get(cat, []):
                    sub = None
                acc_type = inferred.get("accessory_type") if inferred.get("accessory_type") in ACCESSORY_TYPE_OPTIONS else None

                raw_color = COLOR_ALIASES.get(
                    str(inferred.get("color", "")).strip().lower(),
                    str(inferred.get("color", "")).strip().lower()
                )
                color_val = raw_color if raw_color in COLOR_OPTIONS else "negro"
                pattern_val = inferred.get("pattern") if inferred.get("pattern") in PATTERN_OPTIONS else "liso"
                warmth_val = inferred.get("warmth") if inferred.get("warmth") in WARMTH_OPTIONS else "medio"
                waterproof_val = inferred.get("waterproof") if isinstance(inferred.get("waterproof"), bool) else False
                dress_level_val = inferred.get("dress_level") if inferred.get("dress_level") in DRESS_LEVEL_OPTIONS else "flexible"
                style_val = inferred.get("style") if inferred.get("style") in STYLE_OPTIONS else "casual"

                next_id = max([g.id for g in st.session_state.wardrobe], default=0) + 1
                image_name = upload_garment_image(user_id, next_id, uf)

                garment = Garment(
                    id=next_id,
                    name=suggested,
                    category=cat,
                    subcategory=sub,
                    accessory_type=acc_type,
                    color=normalize_color_name(color_val),
                    secondary_colors=[],
                    pattern=pattern_val,
                    style=style_val,
                    secondary_styles=[],
                    warmth=warmth_val,
                    waterproof=waterproof_val,
                    sexiness=0,
                    dress_level=dress_level_val,
                    image_name=image_name,
                    is_new=True,
                )
                st.session_state.wardrobe.append(garment)
                save_garment_cloud(user_id, garment)

                attrs_parts = [CATEGORY_LABELS_ES.get(cat, cat)]
                if garment.color:
                    attrs_parts.append(garment.color)
                if pattern_val != "liso":
                    attrs_parts.append(pattern_val)
                if style_val != "casual":
                    attrs_parts.append(style_val)

                added_items.append({"name": suggested, "attrs": " · ".join(attrs_parts)})
            st.session_state.bulk_uploader_key += 1
            st.session_state["bulk_saved_summary"] = {
                "message": f"Se agregaron {len(added_items)} prenda(s) al clóset.",
                "items": added_items
            }
            st.rerun()

    st.divider()
    st.markdown("### ➕ Agregar prenda manualmente")

    uploaded_file = st.file_uploader(
        "Sube una foto de la prenda",
        type=["jpg", "jpeg", "png", "webp"],
        key=f"form_uploader_{st.session_state.form_uploader_key}"
    )

    suggested_name = ""
    inferred = {}

    if uploaded_file is not None:
        suggested_name = suggest_name_from_filename(uploaded_file.name)
        inferred = infer_attributes_from_name(suggested_name)

        if not st.session_state.form_name:
            st.session_state.form_name = suggested_name

        if not st.session_state.form_inferred_done:
            if inferred.get("category") in CATEGORY_OPTIONS:
                st.session_state.form_category = inferred["category"]

            inferred_subcategory = inferred.get("subcategory")
            current_category = st.session_state.form_category
            valid_subcategories = SUBCATEGORY_OPTIONS.get(current_category, [])

            if st.session_state.form_subcategory not in valid_subcategories:
                st.session_state.form_subcategory = None

            if st.session_state.form_subcategory is None and inferred_subcategory in valid_subcategories:
                st.session_state.form_subcategory = inferred_subcategory

            if inferred.get("accessory_type") in ACCESSORY_TYPE_OPTIONS:
                st.session_state.form_accessory_type = inferred["accessory_type"]

            inferred_color = COLOR_ALIASES.get(
                str(inferred.get("color", "")).strip().lower(),
                str(inferred.get("color", "")).strip().lower()
            )
            if inferred_color in COLOR_OPTIONS:
                st.session_state.form_color = inferred_color

            inferred_secondary_color = COLOR_ALIASES.get(
                str(inferred.get("secondary_color", "")).strip().lower(),
                str(inferred.get("secondary_color", "")).strip().lower()
            )
            if inferred_secondary_color in COLOR_OPTIONS:
                st.session_state.form_secondary_color = inferred_secondary_color

            if inferred.get("pattern") in PATTERN_OPTIONS:
                st.session_state.form_pattern = inferred["pattern"]

            if inferred.get("style") in STYLE_OPTIONS:
                st.session_state.form_style = inferred["style"]

            inferred_secondary_styles = [
                s for s in inferred.get("secondary_styles", [])
                if s in STYLE_OPTIONS and s != st.session_state.form_style
            ]
            if inferred_secondary_styles:
                st.session_state.form_secondary_styles = inferred_secondary_styles

            if inferred.get("warmth") in WARMTH_OPTIONS:
                st.session_state.form_warmth = inferred["warmth"]

            if isinstance(inferred.get("waterproof"), bool):
                st.session_state.form_waterproof = inferred["waterproof"]

            if isinstance(inferred.get("sexiness"), int):
                st.session_state.form_sexiness = inferred["sexiness"]

            if inferred.get("dress_level") in DRESS_LEVEL_OPTIONS:
                st.session_state.form_dress_level = inferred["dress_level"]

            st.session_state.form_inferred_done = True

    if uploaded_file is not None:
        preview = Image.open(uploaded_file)
        preview = ImageOps.exif_transpose(preview)
        st.image(preview, caption="Vista previa", width=220)
# manual_name_inference_tab3
    if uploaded_file is None and st.session_state.form_name.strip():
        inferred = infer_attributes_from_name(st.session_state.form_name.strip())

        if not st.session_state.form_inferred_done:
            if inferred.get("category") in CATEGORY_OPTIONS:
                st.session_state.form_category = inferred["category"]

            inferred_subcategory = inferred.get("subcategory")
            current_category = st.session_state.form_category
            valid_subcategories = SUBCATEGORY_OPTIONS.get(current_category, [])

            if st.session_state.form_subcategory not in valid_subcategories:
                st.session_state.form_subcategory = None

            if st.session_state.form_subcategory is None and inferred_subcategory in valid_subcategories:
                st.session_state.form_subcategory = inferred_subcategory

            if inferred.get("accessory_type") in ACCESSORY_TYPE_OPTIONS:
                st.session_state.form_accessory_type = inferred["accessory_type"]

            inferred_color = COLOR_ALIASES.get(
                str(inferred.get("color", "")).strip().lower(),
                str(inferred.get("color", "")).strip().lower()
            )
            if inferred_color in COLOR_OPTIONS:
                st.session_state.form_color = inferred_color

            if inferred.get("pattern") in PATTERN_OPTIONS:
                st.session_state.form_pattern = inferred["pattern"]

            if inferred.get("warmth") in WARMTH_OPTIONS:
                st.session_state.form_warmth = inferred["warmth"]

            st.session_state.form_inferred_done = True

    category = st.selectbox(
        "Categoría",
        CATEGORY_OPTIONS,
        key="form_category",
        format_func=lambda c: CATEGORY_LABELS_ES.get(c, c)
    )
    subcategory = None

    if category in SUBCATEGORY_OPTIONS and category != "accessory":
        subcategory = st.selectbox(
            "Subcategoría",
            [None] + SUBCATEGORY_OPTIONS[category],
            key="form_subcategory",
            format_func=lambda x: "— ninguna —" if x is None else SUBCATEGORY_LABELS_ES.get(x, x)
        )
    else:
        subcategory = None
    
    name = st.text_input("Nombre de la prenda", key="form_name")

    if category == "accessory":
        accessory_type = st.selectbox(
            "Tipo de accesorio",
            ACCESSORY_TYPE_OPTIONS,
            key="form_accessory_type"
        )
    else:
        accessory_type = None

    color_icons = {
        "amarillo": "🟡",
        "azul": "🔵",
        "azul marino": "🔵",
        "beige": "🟤",
        "blanco": "⚪",
        "burdeo": "🔴",
        "café": "🟤",
        "celeste": "🔵",
        "crema": "⚪",
        "dorado": "🟡",
        "fucsia": "🟣",
        "gris": "⚪",
        "gris claro": "⚪",
        "gris oscuro": "⚫",
        "lila": "🟣",
        "morado": "🟣",
        "mostaza": "🟡",
        "multicolor": "🌈",
        "naranja": "🟠",
        "negro": "⚫",
        "plateado": "⚪",
        "rojo": "🔴",
        "rosado": "🟣",
        "verde": "🟢",
        "verde olivo": "🟢",
        "verde oscuro": "🟢",
    }

    sorted_color_options = sorted(COLOR_OPTIONS)

    color = st.selectbox(
        "Color principal",
        sorted_color_options,
        key="form_color",
        format_func=lambda c: f"{color_icons.get(c, '⬜')} {c}"
    )

    pattern = st.selectbox(
        "Patrón",
        PATTERN_OPTIONS,
        key="form_pattern"
    )

    if pattern != "liso":
        secondary_color = st.selectbox(
            "Color secundario",
            ["ninguno"] + sorted_color_options,
            key="form_secondary_color",
            format_func=lambda c: "— ninguno —" if c == "ninguno" else f"{color_icons.get(c, '⬜')} {c}"
        )
    else:
        if st.session_state.form_secondary_color != "ninguno":
            st.session_state.form_secondary_color = "ninguno"
        secondary_color = "ninguno"

    style = st.selectbox(
        "Estilo principal",
        STYLE_OPTIONS,
        key="form_style"
    )

    available_secondary_styles = [s for s in STYLE_OPTIONS if s != style]

    st.session_state.form_secondary_styles = [
        s for s in st.session_state.form_secondary_styles
        if s in available_secondary_styles
    ]

    secondary_styles = st.multiselect(
        "Estilos secundarios",
        available_secondary_styles,
        key="form_secondary_styles"
    )

    with st.form("add_garment_form", clear_on_submit=True):
        warmth = st.selectbox(
            "Nivel térmico",
            WARMTH_OPTIONS,
            key="form_warmth"
        )

        waterproof = st.checkbox(
            "¿Es impermeable?",
            key="form_waterproof"
        )
        
        sexiness = st.slider(
            "Nivel sexy",
            min_value=0,
            max_value=3,
            key="form_sexiness_add"
        )

        dress_level = st.selectbox(
            "Nivel de formalidad",
            DRESS_LEVEL_OPTIONS,
            key="form_dress_level"
        )

        submitted = st.form_submit_button("Guardar prenda")

    if submitted:
        next_id = max([g.id for g in st.session_state.wardrobe], default=0) + 1
        image_name = None

        if uploaded_file is not None:
            image_name = upload_garment_image(user_id, next_id, uploaded_file)

        garment = Garment(
            id=next_id,
            name=name,
            category=category,
            subcategory=subcategory,
            accessory_type=accessory_type,
            color=normalize_color_name(color),
            secondary_colors=[normalize_color_name(secondary_color)] if secondary_color != "ninguno" else [],
            pattern=pattern,
            style=style,
            secondary_styles=secondary_styles,
            warmth=warmth,
            waterproof=waterproof,
            sexiness=sexiness,
            dress_level=dress_level,
            image_name=image_name,
            is_new=True,
        )

        st.session_state.wardrobe.append(garment)
        save_garment_cloud(user_id, garment)
        st.session_state["add_saved_message"] = "Tu prenda quedó guardada."
        st.session_state["reset_add_form"] = True
        st.session_state.form_uploader_key += 1
        st.rerun()
# =========================================================
# TAB 4: PLANIFICADOR SEMANAL
# =========================================================

with tab4:
    st.subheader("Planificador semanal 📅")
    st.caption("Genera combinaciones equilibradas para la semana evitando repetir prendas.")

    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    st.markdown("### Configuración base semanal")

    base_col1, base_col2, base_col3 = st.columns(3)

    with base_col1:
        base_options = list(OCCASION_OPTIONS)

        base_occasion = st.selectbox(
            "Ocasión base",
            base_options,
            index=base_options.index("trabajo"),
            key="base_week_occasion"
        )

    with base_col2:
        base_mood = st.selectbox(
            "Mood base",
            MOOD_OPTIONS,
            index=MOOD_OPTIONS.index("elegante"),
            key="base_week_mood"
        )

    with base_col3:
        base_activity = st.selectbox(
            "Actividad base",
            ACTIVITY_OPTIONS,
            index=ACTIVITY_OPTIONS.index("normal"),
            key="base_week_activity"
        )

    planner_use_real_weather = st.toggle(
        "Usar clima real en la semana",
        value=True,
        key="weekly_use_real_weather"
    )

    planner_city = st.text_input(
        "Ciudad para pronóstico semanal",
        value=DEFAULT_CITY,
        key="weekly_weather_city"
    )

    default_week_weather = {
        "Lunes": {"temp": 15, "rain": False, "description": "templado"},
        "Martes": {"temp": 14, "rain": False, "description": "nublado"},
        "Miércoles": {"temp": 12, "rain": True, "description": "lluvia"},
        "Jueves": {"temp": 11, "rain": False, "description": "frío"},
        "Viernes": {"temp": 16, "rain": False, "description": "despejado"},
    }

    if planner_use_real_weather:
        if WEATHER_API_KEY != "TU_API_KEY_AQUI":
            real_week_weather = get_week_forecast(planner_city, WEATHER_API_KEY)

            if real_week_weather:
                week_weather = {**default_week_weather, **real_week_weather}
                st.success(f"Pronóstico semanal cargado para {planner_city}")
            else:
                week_weather = st.session_state.week_weather or default_week_weather
                st.warning("No se pudo cargar el pronóstico semanal. Se usarán datos guardados o por defecto.")
        else:
            week_weather = st.session_state.week_weather or default_week_weather
            st.info("Agrega tu API key de OpenWeather para usar clima real.")
    else:
        week_weather = st.session_state.week_weather or default_week_weather

    week_context = {}
    edited_week_weather = {}

    for d in days:
        day_weather = week_weather.get(d, {})
        day_temp = int(day_weather.get("temp", 15))
        day_rain = bool(day_weather.get("rain", False))

        st.markdown(f"### {d}")
        st.caption(format_weather_label(day_weather))

        use_base_config = st.checkbox(
            "Usar configuración base",
            value=True,
            key=f"{d}_use_base"
        )

        if use_base_config:
            occasion = base_occasion
            mood = base_mood
            activity = base_activity

            st.caption(f"Configuración usada: {occasion} · {mood} · {activity}")
        else:
            col1, col2, col3 = st.columns(3)

            with col1:
                occasion = st.selectbox(
                    "Ocasión",
                    OCCASION_OPTIONS,
                    index=OCCASION_OPTIONS.index(base_occasion),
                    key=f"{d}_occ"
                )

            with col2:
                mood = st.selectbox(
                    "Mood",
                    MOOD_OPTIONS,
                    index=MOOD_OPTIONS.index(base_mood),
                    key=f"{d}_mood"
                )

            with col3:
                activity = st.selectbox(
                    "Actividad",
                    ACTIVITY_OPTIONS,
                    index=ACTIVITY_OPTIONS.index(base_activity),
                    key=f"{d}_act"
                )

        col4, col5 = st.columns(2)

        with col4:
            temp = st.number_input(
                "Temp °C",
                min_value=-5,
                max_value=40,
                value=day_temp,
                step=1,
                key=f"{d}_temp"
            )

        with col5:
            rain = st.checkbox(
                "Lluvia",
                value=day_rain,
                key=f"{d}_rain"
            )

        week_context[d] = {
            "occasion": occasion,
            "mood": mood,
            "activity": activity
        }

        edited_week_weather[d] = {
            "temp": temp,
            "rain": rain,
            "description": day_weather.get("description", "sin datos")
        }

    generate_week = st.button("Generar semana", use_container_width=True)

    if generate_week:
        if not st.session_state.wardrobe:
            st.warning("No hay prendas cargadas.")
            st.session_state.week_plan = None
        else:
            st.session_state.week_plan = generate_week_plan(
                st.session_state.wardrobe,
                week_context,
                edited_week_weather,
                feedback_list=st.session_state.feedback
            )

            st.session_state.week_weather = edited_week_weather

    if st.session_state.week_plan:
        st.markdown("---")

        for day, outfit in st.session_state.week_plan.items():
            day_weather = st.session_state.week_weather.get(day, {})

            st.markdown(f"### {day}")
            st.caption(format_weather_label(day_weather))

            if not outfit:
                st.info("No se pudo generar outfit para este día.")
                continue

            cols = st.columns(len(outfit))

            for i, g in enumerate(outfit):
                with cols[i]:
                    render_garment_image(g, width=120)
                    st.caption(g.name)