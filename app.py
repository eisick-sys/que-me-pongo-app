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
    load_user_profile_cloud, save_user_profile_cloud,
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
    if st.sidebar.button("⚙️ Mi perfil", key="open_profile", type="tertiary"):
        st.session_state["show_profile"] = not st.session_state.get("show_profile", False)

    if st.sidebar.button("❓ ¿Qué es Lookia?", key="open_about", type="tertiary"):
        st.session_state["show_about"] = not st.session_state.get("show_about", False)

from models import Garment, OutfitFeedback, UsedOutfit, UserProfile
from weather import format_weather_label, get_current_weather, get_week_forecast

from engine.occasion_rules import garment_allowed_for_occasion, get_weather_tag
from engine.recommender import (
    explain_outfit_score,
    generate_outfits,
    generate_outfits_from_selected_garment,
    generate_week_plan,
)

from constants import (
    ACTIVITY_OPTIONS,
    CATEGORY_LABELS_ES,
    CATEGORY_OPTIONS,
    CHILEAN_CITIES,
    COLOR_ALIASES,
    COLOR_OPTIONS,
    DRESS_LEVEL_OPTIONS,
    MOOD_OPTIONS,
    OCCASION_OPTIONS,
    PATTERN_OPTIONS,
    STYLE_LABELS_ES,
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
            return "Mocasín con estilo deporte — ¿querías decir casual o formal?"

    # Outerwear
    if garment.category == "outerwear":
        if garment.waterproof and "sport" in all_s and dl in ["relajado", "flexible"]:
            return "Impermeable deporte — quedará bloqueado en citas y salidas elegantes"
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
        return "Estilo deporte + nivel elegante — posible contradicción"

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


def render_garment_image(garment: Garment, user_id: str, width: int = 120):
    if not garment.image_name:
        st.caption("Sin foto")
        return

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
            st.session_state["pending_toast"] = ("Guardado. Tendré en cuenta que este outfit te gustó.", "👍")
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
            st.session_state["pending_toast"] = ("Guardado. Evitaré priorizar este outfit en contextos parecidos.", "👎")
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


# =========================================================
# BASE INICIAL DE PRENDAS
# =========================================================


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



def garment_color_label(g) -> str:
    secondary = getattr(g, "secondary_colors", []) or []
    secondary = [str(c).strip() for c in secondary if c and str(c).strip()]
    if secondary:
        return f"{g.color} + {', '.join(secondary)}"
    return str(getattr(g, "color", "negro"))

# =========================================================
# ESTADO DE LA APLICACIÓN (SESSION STATE)
# =========================================================

if "user_profile" not in st.session_state:
    st.session_state.user_profile = load_user_profile_cloud(user_id)

if "show_profile" not in st.session_state:
    st.session_state["show_profile"] = False

if "show_about" not in st.session_state:
    st.session_state["show_about"] = False

if "photo_uploader_key" not in st.session_state:
    st.session_state.photo_uploader_key = 0

if "selected_garment_id" not in st.session_state:
    st.session_state.selected_garment_id = None

if "wardrobe" not in st.session_state or st.session_state.get("just_logged_in"):
    st.session_state.wardrobe = load_wardrobe_cloud(user_id)
    st.session_state["just_logged_in"] = False

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

if "missing_categories" not in st.session_state:
    st.session_state.missing_categories = []

if "week_plan" not in st.session_state:
    st.session_state.week_plan = None

if "week_weather" not in st.session_state:
    st.session_state.week_weather = {}

if "session_shown_outfits" not in st.session_state:
    st.session_state.session_shown_outfits = []  # lista de listas de garment IDs


def is_recent_outfit(combo):
    outfit_ids = sorted([g.id for g in combo])
    return outfit_ids in get_recent_outfit_memory()


# =========================================================
# ONBOARDING PERFIL DEL CLÓSET
# =========================================================

if st.session_state.user_profile is None:
    st.subheader("¡Bienvenida a Lookia! 👋")
    st.caption("Cuéntanos un poco sobre ti para personalizar tus recomendaciones.")

    with st.form("onboarding_form"):
        display_name = st.text_input("¿Cómo te llamamos?", placeholder="Tu nombre o apodo")

        closet_type = st.radio(
            "¿Cómo describirías tu clóset?",
            ["femenino", "masculino", "mixto"],
            horizontal=True,
        )

        city = st.selectbox(
            "Ciudad",
            options=CHILEAN_CITIES,
            index=CHILEAN_CITIES.index("Punta Arenas"),
        )

        frequent_occasions = st.multiselect(
            "¿Para qué ocasiones te vistes más seguido?",
            OCCASION_OPTIONS,
        )

        dominant_style = st.selectbox(
            "¿Cuál es tu estilo dominante?",
            ["casual", "formal", "elegante", "urbano", "sport", "mixto"],
            format_func=lambda s: STYLE_LABELS_ES.get(s, s),
        )

        submitted = st.form_submit_button("Empezar →", use_container_width=True)

    if submitted:
        profile = UserProfile(
            user_id=user_id,
            display_name=display_name.strip(),
            closet_type=closet_type,
            city=city.strip() or "Punta Arenas",
            frequent_occasions=frequent_occasions,
            dominant_style=dominant_style,
        )
        save_user_profile_cloud(profile)
        st.session_state.user_profile = profile
        st.rerun()

    st.stop()


# =========================================================
# UI
# =========================================================

profile = st.session_state.user_profile
greeting = f"Hola, {profile.display_name} 👋" if profile.display_name else "Hola 👋"
st.caption(greeting)
if os.getenv("LOOKIA_ENV") != "production":
    debug_mode = st.toggle("🔧 Modo debug", value=False, key="debug_mode")
else:
    debug_mode = False

if "pending_toast" in st.session_state:
    msg, icon = st.session_state.pop("pending_toast")
    st.toast(msg, icon=icon)

if st.session_state.get("show_profile"):
    profile = st.session_state.user_profile
    st.subheader("⚙️ Mi perfil")

    with st.form("profile_form"):
        display_name = st.text_input("Nombre o apodo", value=profile.display_name)

        closet_type = st.radio(
            "Tipo de clóset",
            ["femenino", "masculino", "mixto"],
            index=["femenino", "masculino", "mixto"].index(profile.closet_type),
            horizontal=True,
        )

        city = st.selectbox(
            "Ciudad",
            options=CHILEAN_CITIES,
            index=CHILEAN_CITIES.index(profile.city) if profile.city in CHILEAN_CITIES else 0,
        )

        frequent_occasions = st.multiselect(
            "Ocasiones frecuentes",
            OCCASION_OPTIONS,
            default=profile.frequent_occasions,
        )

        dominant_style = st.selectbox(
            "Estilo dominante",
            ["casual", "formal", "elegante", "urbano", "sport", "mixto"],
            index=["casual", "formal", "elegante", "urbano", "sport", "mixto"].index(profile.dominant_style),
            format_func=lambda s: STYLE_LABELS_ES.get(s, s),
        )

        col_save, col_cancel = st.columns(2)
        with col_save:
            saved = st.form_submit_button("Guardar cambios", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("Cancelar", use_container_width=True)

    if saved:
        updated = UserProfile(
            user_id=user_id,
            display_name=display_name.strip(),
            closet_type=closet_type,
            city=city.strip() or "Punta Arenas",
            frequent_occasions=frequent_occasions,
            dominant_style=dominant_style,
        )
        if save_user_profile_cloud(updated):
            st.session_state.user_profile = updated
            st.session_state["show_profile"] = False
            st.session_state["pending_toast"] = ("Perfil actualizado.", "✅")
            st.rerun()
        else:
            st.error("No se pudo guardar. Intenta de nuevo.")

    if cancelled:
        st.session_state["show_profile"] = False
        st.rerun()

    st.stop()

if st.session_state.get("show_about"):
    st.subheader("❓ ¿Qué es Lookia?")
    st.markdown(
        """
        **Lookia** es tu asistente personal de estilo. Te sugiere outfits de tu propio clóset
        según la ocasión, tu estado de ánimo, la actividad del día y el clima real de tu ciudad.

        **Cómo funciona:**
        - 👗 **Agrega tus prendas** en *Mi clóset* — solo ponle nombre o sube una foto, puedes subir hasta 5 fotos de una vez (en este modo lo ideal es que las fotos tengan el nombre y algunas características de la prenda), también puedes agregar sólo una prenda y editar tu misma.
        y Lookia infiere automáticamente el color, categoría y estilo, mientras más descripciones agregues, más características se inferirán. Recuerda que estamos en fase beta, ya vienen los reconocimientos con IA.
        - Tus prendas quedan guardadas!, en tu próxima sesion puedes revisarlas. Recuerda que no es necesario subir tu closet completo de una vez, puedes ir subiendo de a poco.
        - Si quieres editar una prenda, solo clickea el boton y dirígete al final de la pantalla, ahí estará tu prenda (no olvides guardar!). En fases siguientes será más fácil -sin scrolear-
        - ✨ **Pide recomendaciones** eligiendo ocasión, mood y actividad. El motor reconoce el clima real, si deseas cambiarlo para planificar para otro día u otro momento, solo clickea y puedes manejarlo. 
        - 👍 **Dale feedback** a los outfits — Lookia aprende de tus gustos con el tiempo. Si vas a usar una recomendación... clickea!, Lookia lo recordará para no recomendartelo inmediatamente.
        - 📅 **Planifica tu semana** para no repetir looks. Puedes dejar ocasion, mood y actividad para toda la semana, si deseas cambiar uno o más días específicos, lo puedes hacer fácilmente.

        Tu perfil le ayuda a Lookia a entender mejor tu estilo y darte sugerencias más precisas.
        """
    )
    if st.button("Cerrar", key="close_about"):
        st.session_state["show_about"] = False
        st.rerun()
    st.stop()

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
        _actividades_disponibles = ["normal"]
        if mood in ["relajado", "urbano", "comodo"] or occasion in ["casual", "deporte"]:
            _actividades_disponibles.append("caminar")
        if occasion == "deporte":
            _actividades_disponibles.append("entrenar")
        activity = st.selectbox("Actividad", _actividades_disponibles)
        use_real_weather = st.toggle("Usar clima real", value=True)

        if use_real_weather:
            _weather_city = st.session_state.user_profile.city if st.session_state.get("user_profile") else DEFAULT_CITY
            weather_data = get_current_weather(_weather_city, WEATHER_API_KEY)
            if weather_data:
                temp = weather_data["temp"]
                rain = weather_data["rain"]
                st.success(f"{_weather_city} · {format_weather_label(weather_data)}")
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
        selected_allowed, reason = garment_allowed_for_occasion(selected_garment, occasion, rain, mood=mood, temp=temp, activity=activity)
        if not selected_allowed:
            st.warning(reason)

        if selected_garment is not None and occasion == "matrimonio" and mood == "elegante":
            cat = selected_garment.category
            sub = getattr(selected_garment, "subcategory", None)
            es_compatible = (
                (cat == "one_piece" and sub in ["vestido_elegante", "vestido_coctel"]) or
                (cat == "shoes" and sub in ["taco_alto", "taco_bajo", "sandalia"]) or
                (cat == "midlayer" and sub == "blazer") or
                (cat == "outerwear" and sub in ["abrigo", "trench"]) or
                cat == "accessory"
            )
            if not es_compatible:
                st.warning(f"{selected_garment.name} no es la elección típica para un matrimonio elegante — pero tú decides.")
                selected_allowed = False

        if selected_garment is not None and occasion == "gala":
            cat = selected_garment.category
            sub = getattr(selected_garment, "subcategory", None)
            _calzado_ok_gala = (
                sub in ["taco_alto", "taco_bajo", "sandalia"]
                if mood != "comodo"
                else sub in ["taco_bajo", "sandalia"]
            )
            if cat == "shoes" and sub == "zapatilla_urbana":
                _calzado_ok_gala = True  # urbano puede usar zapatilla arreglada
            es_compatible_gala = (
                (cat == "one_piece" and sub in ["vestido_elegante", "vestido_coctel"]) or
                (cat == "shoes" and _calzado_ok_gala) or
                (cat == "outerwear" and sub in ["abrigo", "chaqueta", "bolero"]) or
                (cat == "outerwear" and sub == "trench" and mood == "urbano") or
                cat == "accessory"
            )
            if not es_compatible_gala:
                if cat == "outerwear" and sub == "trench" and mood != "urbano":
                    st.warning(f"{selected_garment.name} no va con gala {mood} — pero tú decides.")
                else:
                    st.warning(f"{selected_garment.name} no es la elección típica para gala — pero tú decides.")
                selected_allowed = False

        # Advertencia de clima para prenda forzada
        if selected_garment.category == "outerwear" and temp >= 24:
            st.warning(f"{selected_garment.name} puede ser demasiado abrigada para {temp}°C — pero tú decides.")

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    generate_clicked = col_btn1.button("✨ ¿Qué me pongo?", use_container_width=True)
    surprise_clicked = col_btn2.button("🎲 Outfit sorpresa", use_container_width=True)

    show_anyway_clicked = False
    if selected_garment:
        show_anyway_clicked = col_btn3.button("💪 Mostrar de todos modos", use_container_width=True)
    elif occasion == "gala":
        show_anyway_clicked = col_btn3.button("💪 Mostrar de todos modos", use_container_width=True)

    outfits = st.session_state.get("last_outfits", [])
    recent_memory = get_recent_outfit_memory()
    _recent = list(recent_memory or [])
    _session = list(st.session_state.get("session_shown_outfits", []) or [])
    combined_recent = (_recent + _session)[-10:]

    if generate_clicked or show_anyway_clicked:
        if selected_garment:
            outfits, _missing = generate_outfits_from_selected_garment(
                garments=st.session_state.wardrobe,
                selected_garment=selected_garment,
                occasion=occasion,
                temp=temp,
                rain=rain,
                mood=mood,
                activity=activity,
                top_n=3,
                feedback_list=st.session_state.feedback,
                recent_outfits=combined_recent,
                ignore_occasion_for_selected=show_anyway_clicked,
            )
            st.session_state.missing_categories = _missing
        else:
            # Gala sin vestidos + "Mostrar de todos modos" → derivar a motor matrimonio elegante
            if occasion == "gala" and show_anyway_clicked:
                from engine.outfit_generation import _generate_matrimonio_elegante
                from utils.user_profile import build_user_style_profile
                outfits, _missing = _generate_matrimonio_elegante(
                    garments=st.session_state.wardrobe,
                    temp=temp,
                    rain=rain,
                    mood="elegante",
                    activity=activity,
                    top_n=3,
                    feedback_list=st.session_state.feedback,
                    recent_outfits=combined_recent,
                    user_profile=build_user_style_profile(st.session_state.feedback, st.session_state.wardrobe),
                )
                st.session_state.missing_categories = []
            else:
                outfits, _missing = generate_outfits(
                    garments=st.session_state.wardrobe,
                    occasion=occasion,
                    temp=temp,
                    rain=rain,
                    mood=mood,
                    activity=activity,
                    top_n=3,
                    feedback_list=st.session_state.feedback,
                    recent_outfits=combined_recent,
                )
                st.session_state.missing_categories = _missing

            # Si es interior con frío, forzar al menos 1 outfit sin outerwear
            if indoor_outdoor == "interior" and temp <= 14:
                tiene_sin_abrigo = any(
                    not any(g.category == "outerwear" for g in combo)
                    for _, combo in outfits
                )

                if not tiene_sin_abrigo and len(outfits) >= 2:
                    outfits_sin_abrigo, _ = generate_outfits(
                        garments=st.session_state.wardrobe,
                        occasion=occasion,
                        temp=temp + 6,
                        rain=False,
                        mood=mood,
                        activity=activity,
                        top_n=3,
                        feedback_list=st.session_state.feedback,
                        recent_outfits=combined_recent,
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
        st.session_state.has_generated_outfits = True
        for _, combo in outfits:
            combo_ids = [g.id for g in combo]
            if combo_ids not in st.session_state.session_shown_outfits:
                st.session_state.session_shown_outfits.append(combo_ids)
        st.session_state.session_shown_outfits = st.session_state.session_shown_outfits[-6:]

    elif surprise_clicked:
        surprise_candidates = [
            g for g in st.session_state.wardrobe
            if garment_allowed_for_occasion(g, occasion, rain, mood=mood, temp=temp, activity=activity)[0]
        ]

        if surprise_candidates:
            forced = random.choice(surprise_candidates)

            outfits, _missing = generate_outfits_from_selected_garment(
                garments=st.session_state.wardrobe,
                selected_garment=forced,
                occasion=occasion,
                temp=temp,
                rain=rain,
                mood=mood,
                activity=activity,
                top_n=3,
                feedback_list=st.session_state.feedback,
                recent_outfits=combined_recent,
            )
            st.session_state.missing_categories = _missing
        else:
            outfits = []
            st.session_state.missing_categories = []

        remember_shown_outfits(outfits)
        st.session_state.last_outfits = outfits
        st.session_state.has_generated_outfits = True
        for _, combo in outfits:
            combo_ids = [g.id for g in combo]
            if combo_ids not in st.session_state.session_shown_outfits:
                st.session_state.session_shown_outfits.append(combo_ids)
        st.session_state.session_shown_outfits = st.session_state.session_shown_outfits[-6:]

    st.markdown("## Resultados")

    if not outfits and st.session_state.has_generated_outfits:
        missing_cats = st.session_state.get("missing_categories", [])
        cat_labels = {
            "top": "una parte de arriba (polera, blusa, etc.)",
            "bottom": "una parte de abajo (pantalón, falda, etc.)",
            "shoes": "calzado",
            "outerwear": "un abrigo o chaqueta",
            "midlayer": "una prenda intermedia (blazer, sweater, etc.)",
        }
        if occasion == "gala" and not missing_cats:
            if mood == "relajado":
                st.warning(
                    "Una gala, por definición, no es relajada. "
                    "Si igual quieres ver opciones con lo que tienes, presiona 💪 **Mostrar de todos modos**."
                )
            else:
                st.warning(
                    "Para una gala necesitas un **vestido elegante o cóctel** en tu clóset. "
                    "¿Tienes uno? Agrégalo primero. Si igual quieres ver opciones con lo que tienes, "
                    "presiona 💪 **Mostrar de todos modos**."
                )
        elif missing_cats:
            faltantes = ", ".join(cat_labels.get(c, c) for c in missing_cats)
            st.warning(f"No tengo prendas suficientes para armar este outfit. Te falta agregar: **{faltantes}**.")
        else:
            st.warning("Tienes las prendas pero ninguna combinación pasó los filtros para esta ocasión. Intenta cambiar el mood o la actividad.")
    else:
        for idx, (score, combo) in enumerate(outfits, start=1):
            if debug_mode:
                st.markdown(f"### Outfit {idx} · Score {score}")
            else:
                st.markdown(f"### Outfit {idx}")        
            
            if st.session_state.get("outfit_used_message_idx") == idx:
                st.toast(st.session_state.get("outfit_used_message_text", "Outfit guardado como usado."), icon="✅")
                del st.session_state["outfit_used_message_idx"]
                del st.session_state["outfit_used_message_text"]

            cols = st.columns(len(combo))

            for col, g in zip(cols, combo):
                with col:
                    with st.container():
                        st.markdown(f"**{g.name}**")
                        st.caption(f"{CATEGORY_LABELS_ES.get(g.category, g.category)} · {garment_color_label(g)}")
                        render_garment_image(g, user_id=user_id, width=140)

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

            if rain:
                has_non_waterproof_outer = any(
                    g.category == "outerwear" and not g.waterproof
                    for g in combo
                )
                if has_non_waterproof_outer:
                    st.info("☂️ Si eliges este outfit, no olvides llevar tu paraguas.")

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

        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])

        with col_f1:
            filter_category = st.selectbox(
                "Filtrar por categoría",
                ["todas"] + CATEGORY_OPTIONS,
                key="filter_category_tab2",
                format_func=lambda c: "Todas" if c == "todas" else CATEGORY_LABELS_ES.get(c, c)
            )

        with col_f3:
            st.markdown("<div style='margin-top: 1.9rem;'></div>", unsafe_allow_html=True)
            filter_new_only = st.checkbox("🆕 Nuevas", key="filter_new_only_tab2")

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

        if filter_new_only:
            filtered_wardrobe = [g for g in filtered_wardrobe if getattr(g, "is_new", False)]

        if not filtered_wardrobe:
            st.info("No hay prendas que coincidan con ese filtro.")
        else:
            cols = st.columns(5)

            for i, g in enumerate(filtered_wardrobe):
                with cols[i % 5]:
                    with st.container(border=True):
                        render_garment_image(g, user_id=user_id, width=120)
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
                        current_url = get_garment_image_url(user_id, garment.image_name)
                        if current_url:
                            st.image(current_url, caption=garment.name, width=260)
                        else:
                            st.warning(f"No se encontró la imagen: {garment.image_name}")
                    else:
                        st.info("Esta prenda aún no tiene foto.")

                    garment_color = normalize_color_name(getattr(garment, "color", "blanco"))

                    style = st.selectbox(
                        "Estilo principal",
                        STYLE_OPTIONS,
                        index=STYLE_OPTIONS.index(st.session_state.get(f"edit_style_{garment.id}", garment.style)) if st.session_state.get(f"edit_style_{garment.id}", garment.style) in STYLE_OPTIONS else 0,
                        key=f"edit_style_{garment.id}",
                        format_func=lambda s: STYLE_LABELS_ES.get(s, s),
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
                        key=secondary_styles_key,
                        format_func=lambda s: STYLE_LABELS_ES.get(s, s),
                    )

                    current_pattern = st.session_state.get(f"edit_pattern_{garment.id}", getattr(garment, "pattern", "liso"))
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

                    def _reinfer_from_edit_name():
                        _name = st.session_state.get(f"edit_name_{garment.id}", "").strip()
                        if not _name or len(_name) < 3:
                            return
                        _inferred = infer_attributes_from_name(_name)

                        _new_cat = None
                        if _inferred.get("category") in CATEGORY_OPTIONS:
                            st.session_state[f"edit_category_{garment.id}"] = _inferred["category"]
                            _new_cat = _inferred["category"]

                        if _new_cat:
                            _inferred_sub = _inferred.get("subcategory")
                            _valid_subs = SUBCATEGORY_OPTIONS.get(_new_cat, [])
                            if _inferred_sub in _valid_subs:
                                st.session_state[f"edit_sub_{garment.id}_{_new_cat}"] = _inferred_sub

                        if _inferred.get("color") in COLOR_OPTIONS:
                            st.session_state[f"edit_color_{garment.id}"] = _inferred["color"]

                        if _inferred.get("pattern") in PATTERN_OPTIONS:
                            st.session_state[f"edit_pattern_{garment.id}"] = _inferred["pattern"]

                        if _inferred.get("warmth") in WARMTH_OPTIONS:
                            st.session_state[f"edit_warmth_{garment.id}"] = _inferred["warmth"]

                        if _inferred.get("dress_level") in DRESS_LEVEL_OPTIONS:
                            st.session_state[f"edit_dress_level_{garment.id}"] = _inferred["dress_level"]

                        if _inferred.get("sexiness") is not None:
                            st.session_state[f"edit_sexiness_{garment.id}"] = _inferred["sexiness"]

                        if _inferred.get("style") in STYLE_OPTIONS:
                            st.session_state[f"edit_style_{garment.id}"] = _inferred["style"]

                    st.markdown("""
<div style="background-color: #fff0f3; padding: 12px 16px; border-radius: 8px; margin-bottom: 8px;">
    <p style="margin: 0 0 4px 0; font-weight: 600; font-size: 0.95rem;">Nombre de la prenda</p>
    <p style="margin: 0; font-size: 0.8rem; color: #666;">💡 Lookia infiere la categoría, color y otros atributos desde el nombre — mientras más descriptivo, mejor</p>
</div>
""", unsafe_allow_html=True)
                    name = st.text_input("Nombre", value=garment.name, key=f"edit_name_{garment.id}", label_visibility="collapsed", on_change=_reinfer_from_edit_name)

                    _init_cat = st.session_state.get(f"edit_category_{garment.id}", garment.category)
                    category = st.selectbox(
                        "Categoría",
                        CATEGORY_OPTIONS,
                        index=CATEGORY_OPTIONS.index(_init_cat) if _init_cat in CATEGORY_OPTIONS else 0,
                        key=f"edit_category_{garment.id}",
                        format_func=lambda c: CATEGORY_LABELS_ES.get(c, c)
                    )

                    current_subcategory = st.session_state.get(f"edit_sub_{garment.id}_{category}", getattr(garment, "subcategory", None))

                    edit_cat_key = f"edit_cat_{garment.id}"
                    if st.session_state.get(edit_cat_key) != category:
                        st.session_state[edit_cat_key] = category

                    subcategory_options = ["— ninguna —"] + SUBCATEGORY_OPTIONS.get(category, [])

                    safe_index = (
                        subcategory_options.index(current_subcategory)
                        if current_subcategory in subcategory_options else 0
                    )

                    subcategory = st.selectbox(
                        "Subcategoría",
                        subcategory_options,
                        index=safe_index,
                        key=f"edit_sub_{garment.id}_{category}",
                        format_func=lambda x: "— ninguna —" if x == "— ninguna —" else SUBCATEGORY_LABELS_ES.get(x, x)
                    )

                    if subcategory == "— ninguna —":
                        subcategory = None

                    warmth = "medio"
                    show_warmth = (
                        category in ["top", "midlayer", "outerwear", "bottom", "shoes", "one_piece"]
                        or (category == "accessory" and subcategory in THERMAL_ACCESSORIES)
                    )

                    if show_warmth:
                        current_warmth = st.session_state.get(f"edit_warmth_{garment.id}", garment.warmth if garment.warmth in WARMTH_OPTIONS else "medio")
                        warmth = st.selectbox(
                            "Tipo térmico",
                            WARMTH_OPTIONS,
                            index=WARMTH_OPTIONS.index(current_warmth),
                            key=f"edit_warmth_{garment.id}"
                        )

                    show_functional_fields = (
                        category != "accessory"
                        or (subcategory in THERMAL_ACCESSORIES)
                    )

                    if show_functional_fields:
                        waterproof = st.checkbox("Impermeable", value=garment.waterproof, key=f"edit_waterproof_{garment.id}")
                    else:
                        waterproof = False

                    _init_dl = st.session_state.get(f"edit_dress_level_{garment.id}", garment.dress_level)
                    dress_level = st.selectbox(
                        "Nivel de formalidad",
                        DRESS_LEVEL_OPTIONS,
                        index=DRESS_LEVEL_OPTIONS.index(_init_dl) if _init_dl in DRESS_LEVEL_OPTIONS else 0,
                        key=f"edit_dress_level_{garment.id}"
                    )

                    if show_functional_fields:
                        sexiness = st.slider(
                            "Nivel sexy",
                            min_value=0,
                            max_value=3,
                            value=st.session_state.get(f"edit_sexiness_{garment.id}", getattr(garment, "sexiness", 0)),
                            key=f"edit_sexiness_{garment.id}",
                            help="0 = nada sexy, 1 = bajo, 2 = medio, 3 = alto"
                        )
                    else:
                        sexiness = 0

                    new_uploaded_file = st.file_uploader(
                        "Agregar o reemplazar foto de esta prenda",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"edit_photo_{garment.id}"
                    )

                    if new_uploaded_file:
                        st.image(new_uploaded_file, caption="Nueva foto", width=260)

                    col_save, col_delete = st.columns(2)

                    with col_save:
                        save_changes = st.button("Guardar cambios", key=f"save_{garment.id}", type="primary")

                    with col_delete:
                        with st.popover("🗑️ Eliminar prenda", use_container_width=True):
                            st.caption(f"¿Segura que quieres eliminar **{garment.name}**? Esta acción no se puede deshacer.")
                            if st.button("Sí, eliminar definitivamente", key=f"confirm_delete_edit_{garment.id}", type="primary", use_container_width=True):
                                delete_garment_cloud(user_id, garment.id)
                                st.session_state.wardrobe = [
                                    g for g in st.session_state.wardrobe if g.id != garment.id
                                ]
                                st.session_state.next_id = get_next_id(st.session_state.wardrobe)
                                st.session_state.selected_garment_id = None
                                st.rerun()

                    col_cancel_left, col_cancel_right = st.columns([1, 3])
                    with col_cancel_left:
                        cancel_edit = st.button("Cancelar edición", key=f"cancel_edit_{garment.id}")

                    if save_changes:
                        if not name.strip():
                            st.error("La prenda debe tener nombre.")
                        else:
                            garment.name = name.strip().capitalize()
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
                            garment.accessory_type = None
                            garment.is_new = False

                            if new_uploaded_file:
                                uploaded_image_name = upload_garment_image(user_id, garment.id, new_uploaded_file, access_token=st.session_state.get("access_token"))
                                if uploaded_image_name:
                                    garment.image_name = uploaded_image_name

                            update_garment_cloud(user_id, garment)
                            st.session_state["edit_saved_message"] = garment.id
                            st.success("Edición guardada.")

                    if cancel_edit:
                        st.session_state.selected_garment_id = None
                        if "edit_saved_message" in st.session_state:
                            del st.session_state["edit_saved_message"]
                        st.rerun()

    st.markdown("---")
    st.subheader("📊 Estadísticas de tu clóset")

    used_outfits = st.session_state.get("used_outfits", [])
    wardrobe = st.session_state.wardrobe
    garment_map = {g.id: g for g in wardrobe}

    # --- Métricas principales (siempre visibles) ---
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Prendas en clóset", len(wardrobe))

    # --- Desglose por categoría y subcategoría ---
    from collections import Counter, defaultdict

    category_counts = Counter(g.category for g in wardrobe)
    subcategory_counts = defaultdict(Counter)
    for g in wardrobe:
        if g.subcategory:
            subcategory_counts[g.category][g.subcategory] += 1

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown("#### Prendas por categoría")

    cat_order = ["top", "midlayer", "outerwear", "bottom", "one_piece", "shoes", "accessory"]
    for cat in cat_order:
        count = category_counts.get(cat, 0)
        label = CATEGORY_LABELS_ES.get(cat, cat)
        with st.expander(f"{label} — {count} prenda{'s' if count != 1 else ''}", expanded=False):
            subs = subcategory_counts.get(cat, {})
            valid_subs = SUBCATEGORY_OPTIONS.get(cat, [])
            if subs:
                for sub in valid_subs:
                    n = subs.get(sub, 0)
                    sub_label = SUBCATEGORY_LABELS_ES.get(sub, sub)
                    if n == 0:
                        st.markdown(f"- {sub_label}: **0** — ⚠️ *No tienes ninguna*")
                    elif n == 1:
                        st.markdown(f"- {sub_label}: **1** — 💡 *Tienes muy pocas*")
                    else:
                        st.markdown(f"- {sub_label}: **{n}**")
            else:
                st.caption("Sin prendas registradas en esta categoría.")

    st.markdown("---")

    if not used_outfits:
        st.info("Aún no has registrado outfits usados. Las estadísticas de uso aparecerán aquí a medida que uses Lookia.")
        col_m2.metric("Outfits registrados", 0)
        col_m3.metric("Estilo dominante", "—")
    else:
        garment_counter = Counter()
        style_counter = Counter()
        occasion_counter = Counter()

        for ou in used_outfits:
            for gid in ou.garment_ids:
                garment_counter[gid] += 1
                g = garment_map.get(gid)
                if g:
                    style_counter[g.style] += 1
            occasion_counter[ou.occasion] += 1

        top_style = STYLE_LABELS_ES.get(style_counter.most_common(1)[0][0], "—") if style_counter else "—"

        col_m2.metric("Outfits registrados", len(used_outfits))
        col_m3.metric("Estilo dominante", top_style)

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

        col_s, col_o = st.columns(2)

        with col_s:
            st.markdown("#### Prendas más usadas")
            top_garments = garment_counter.most_common(5)
            if top_garments:
                for gid, count in top_garments:
                    g = garment_map.get(gid)
                    name = g.name if g else f"Prenda #{gid}"
                    cat = CATEGORY_LABELS_ES.get(g.category, g.category) if g else ""
                    st.markdown(f"- **{name}** ({cat}) — {count} {'vez' if count == 1 else 'veces'}")
            else:
                st.caption("Sin datos suficientes.")

        with col_o:
            st.markdown("#### Ocasiones más frecuentes")
            for occasion, count in occasion_counter.most_common(5):
                st.markdown(f"- **{occasion.capitalize()}** — {count} {'vez' if count == 1 else 'veces'}")

# =========================================================
# TAB 3: AGREGAR PRENDA
# =========================================================
with tab3:
    st.subheader("➕ Agregar prenda")

    if "form_name" not in st.session_state:
        st.session_state.form_name = ""

    if "form_category" not in st.session_state:
        st.session_state.form_category = "top"

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
    

    if "form_subcategory" not in st.session_state:
        st.session_state.form_subcategory = None

    if "form_inferred_done" not in st.session_state:
        st.session_state.form_inferred_done = False

    if st.session_state.get("reset_add_form"):
        st.session_state.form_name = ""
        st.session_state.form_category = "top"
        st.session_state.form_subcategory = None
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
    st.markdown("### 📸 Subida rápida")
    st.caption("Sube hasta 5 fotos y Lookia detecta los atributos automáticamente desde el nombre del archivo")

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

    if bulk_files and len(bulk_files) > 5:
        st.warning("El límite es 5 fotos por tanda.")
        bulk_files = bulk_files[:5]

    if bulk_files:

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
                image_name = upload_garment_image(user_id, next_id, uf, access_token=st.session_state.get("access_token"))

                garment = Garment(
                    id=next_id,
                    name=suggested.strip().capitalize(),
                    category=cat,
                    subcategory=sub,
                    accessory_type=None,
                    color=normalize_color_name(color_val),
                    secondary_colors=[],
                    pattern=pattern_val,
                    style=style_val,
                    secondary_styles=[],
                    warmth=warmth_val,
                    waterproof=waterproof_val,
                    sexiness=inferred.get("sexiness") if isinstance(inferred.get("sexiness"), int) else 0,
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
    st.markdown("### ✏️ Agregar con formulario")
    st.caption("Llena los campos tú misma para mayor precisión")

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

    def _reinfer_category_from_name():
        name = st.session_state.form_name.strip()
        if not name or len(name) < 3:
            return
        inferred = infer_attributes_from_name(name)

        if inferred.get("category") in CATEGORY_OPTIONS:
            st.session_state.form_category = inferred["category"]

            inferred_subcategory = inferred.get("subcategory")
            valid_subcategories = SUBCATEGORY_OPTIONS.get(inferred["category"], [])
            if inferred_subcategory in valid_subcategories:
                st.session_state.form_subcategory = inferred_subcategory
            else:
                st.session_state.form_subcategory = None

    st.markdown("""
<div style="background-color: #fff0f3; padding: 12px 16px; border-radius: 8px; margin-bottom: 8px;">
    <p style="margin: 0 0 4px 0; font-weight: 600; font-size: 0.95rem;">Nombre de la prenda</p>
    <p style="margin: 0; font-size: 0.8rem; color: #666;">💡 Lookia infiere la categoría, color y otros atributos desde el nombre — mientras más descriptivo, mejor</p>
</div>
""", unsafe_allow_html=True)
    name = st.text_input("Nombre de la prenda", label_visibility="collapsed", key="form_name", on_change=_reinfer_category_from_name)

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

    if category in SUBCATEGORY_OPTIONS:
        subcategory = st.selectbox(
            "Subcategoría",
            [None] + SUBCATEGORY_OPTIONS[category],
            key="form_subcategory",
            format_func=lambda x: "— ninguna —" if x is None else SUBCATEGORY_LABELS_ES.get(x, x)
        )
    else:
        subcategory = None

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
        key="form_style",
        format_func=lambda s: STYLE_LABELS_ES.get(s, s),
    )

    available_secondary_styles = [s for s in STYLE_OPTIONS if s != style]

    st.session_state.form_secondary_styles = [
        s for s in st.session_state.form_secondary_styles
        if s in available_secondary_styles
    ]

    secondary_styles = st.multiselect(
        "Estilos secundarios",
        available_secondary_styles,
        key="form_secondary_styles",
        format_func=lambda s: STYLE_LABELS_ES.get(s, s),
    )

    with st.form("add_garment_form", clear_on_submit=True):
        show_functional_fields = (
            category != "accessory"
            or (subcategory in THERMAL_ACCESSORIES)
        )

        if show_functional_fields:
            warmth = st.selectbox("Nivel térmico", WARMTH_OPTIONS, key="form_warmth")
        else:
            warmth = "medio"

        if show_functional_fields:
            waterproof = st.checkbox("¿Es impermeable?", key="form_waterproof")
        else:
            waterproof = False

        if show_functional_fields:
            sexiness = st.slider("Nivel sexy", min_value=0, max_value=3, key="form_sexiness_add")
        else:
            sexiness = 0

        dress_level = st.selectbox(
            "Nivel de formalidad",
            DRESS_LEVEL_OPTIONS,
            key="form_dress_level"
        )

        submitted = st.form_submit_button("Guardar prenda")

    if submitted:
        if uploaded_file is None and not name.strip():
            st.warning("Para agregar tu prenda, sube una foto o ponle un nombre.")
            st.stop()
        name = name.strip().capitalize()
        next_id = max([g.id for g in st.session_state.wardrobe], default=0) + 1
        image_name = None

        if uploaded_file is not None:
            image_name = upload_garment_image(user_id, next_id, uploaded_file, access_token=st.session_state.get("access_token"))

        garment = Garment(
            id=next_id,
            name=name,
            category=category,
            subcategory=subcategory,
            accessory_type=None,
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
        st.session_state["reset_add_form"] = True
        st.session_state.form_uploader_key += 1
        st.session_state["add_saved_message"] = True
        st.rerun()

    if st.session_state.pop("add_saved_message", False):
        st.success("✅ Tu prenda quedó guardada.")
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
        _actividades_base = ["normal"]
        if base_mood in ["relajado", "urbano", "comodo"] or base_occasion in ["casual", "deporte"]:
            _actividades_base.append("caminar")
        if base_occasion == "deporte":
            _actividades_base.append("entrenar")
        base_activity = st.selectbox(
            "Actividad base",
            _actividades_base,
            index=0,
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
                _actividades_dia = ["normal"]
                if mood in ["relajado", "urbano", "comodo"] or occasion in ["casual", "deporte"]:
                    _actividades_dia.append("caminar")
                if occasion == "deporte":
                    _actividades_dia.append("entrenar")
                activity = st.selectbox(
                    "Actividad",
                    _actividades_dia,
                    index=_actividades_dia.index(base_activity) if base_activity in _actividades_dia else 0,
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

    generate_week = st.button("📅 Generar semana", use_container_width=True, type="primary")

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
                    render_garment_image(g, user_id=user_id, width=120)
                    st.caption(g.name)