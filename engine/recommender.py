#recommender.py============================================
# LIBRERÍAS ESTÁNDAR
# =========================================================

from typing import Any, Dict, List, Optional
from unicodedata import category


# =========================================================
# MODELOS
# =========================================================

from models import Garment, OutfitFeedback


# =========================================================
# UTILS (helpers de prendas)
# =========================================================

from utils.garment_utils import garment_has_style
from utils.garment_utils import all_styles

# =========================================================
# ENGINE - REGLAS Y LÓGICA
# =========================================================

from engine.occasion_rules import garment_allowed_for_occasion, get_weather_tag

from engine.category_rules import (
    category_context_bonus,
    category_context_penalty,
    outfit_accessory_penalty,
)

from engine.scoring_components import (
    activity_bonus,
    coherence_penalty,
    dress_score,
    mood_bonus,
    practicality_penalty,
    sexiness_bonus,
    weather_score,
)

from engine.history_utils import repetition_penalty

from engine.compatibility import (
    garment_color_compatibility,
    pattern_compatibility,
    style_compatibility,
)

# =========================================================
# PERFIL DE USUARIO / PERSONALIZACIÓN
# =========================================================

from engine.user_profile import (
    calculate_feedback_bonus,
    user_style_bonus,
)

# =========================================================
# MOTOR DE RECOMENDACIONES
# =========================================================

def garment_base_score(
    g: Garment,
    category: str,
    occasion: str,
    temp: int,
    rain: bool,
    mood: str,
    activity: str,
    user_profile: Optional[Dict[str, Dict[str, int]]] = None,
) -> float:
    score = 0

    # Componentes base
    score += dress_score(g.dress_level, occasion)
    score += weather_score(g, temp, rain)
    score += activity_bonus(g, activity, occasion)

    # Reglas específicas por categoría
    score += category_context_bonus(g, occasion, mood, activity, temp, rain)
    score -= category_context_penalty(g, occasion, mood, activity, temp, rain)

    # Ajuste por mood general
    if occasion == "trabajo":
        score += mood_bonus(g, mood) * 0.2
    elif occasion == "salida nocturna":
        score += mood_bonus(g, mood) * 0.8
    elif occasion == "cita":
        score += mood_bonus(g, mood) * 0.6
    else:
        score += mood_bonus(g, mood) * 0.5

    # Refinamiento extra para mood urbano
    if mood == "urbano":
        if garment_has_style(g, "urbano"):
            score += 10
        elif garment_has_style(g, "casual"):
            score += 4

        if garment_has_style(g, "elegante") or garment_has_style(g, "formal"):
            score -= 12

        if category == "bottom" and (
            garment_has_style(g, "elegante") or garment_has_style(g, "formal")
        ):
            score -= 10

        if g.dress_level == "elegante":
            score -= 8

        if category == "shoes" and (
            garment_has_style(g, "elegante") or garment_has_style(g, "formal")
        ) and not garment_has_style(g, "urbano"):
            score -= 6

    # Refinamiento extra para mood relajado
    if mood == "relajado":
        if garment_has_style(g, "casual"):
            score += 8

        if garment_has_style(g, "sport"):
            score += 4

        if garment_has_style(g, "elegante") or garment_has_style(g, "formal"):
            score -= 10

        if g.dress_level == "elegante":
            score -= 8

        if g.dress_level == "arreglado":
            score -= 4

    # Sexy y perfil histórico
    score += sexiness_bonus(g, mood, occasion, activity)
    score += user_style_bonus(g, user_profile)

    # Ajustes especiales para trabajo
    if occasion == "trabajo":
        if g.dress_level == "relajado":
            score -= 10

        if garment_has_style(g, "sport"):
            score -= 10

        if garment_has_style(g, "casual") and not (
            garment_has_style(g, "formal") or garment_has_style(g, "elegante")
        ):
            score -= 4

        if garment_has_style(g, "casual") and (
            garment_has_style(g, "formal") or garment_has_style(g, "elegante")
        ):
            score += 4

        name = g.name.lower()

        if g.category == "bottom":
            if "jeans" in name:
                score -= 4

            if any(x in name for x in ["ajust", "skinny", "tight"]):
                score -= 6

    # shoe_formal_priority_matrimonio_gala
    if category == "shoes":
        lower_name = g.name.lower()

        is_heel_like = any(x in lower_name for x in ["taco", "tacón", "tacon", "heel"])
        is_sandal_like = any(x in lower_name for x in ["sandalia", "sandalias"])
        is_boot_like = any(x in lower_name for x in ["botin", "botín", "bota", "bototo", "boot"])

        if occasion in ["matrimonio", "gala"]:
            if is_heel_like:
                score += 60

            if is_sandal_like and (garment_has_style(g, "elegante") or garment_has_style(g, "formal")):
                score += 50

            if is_boot_like:
                score -= 25

    if category == "one_piece":
        score += 18

        if occasion == "matrimonio":
            score += 40

            if garment_has_style(g, "elegante") or garment_has_style(g, "formal"):
                score += 20

            if g.dress_level == "elegante":
                score += 20
            elif g.dress_level == "arreglado":
                score += 10

        elif occasion == "gala":
            score += 30

            if garment_has_style(g, "elegante") or garment_has_style(g, "formal"):
                score += 16

        elif occasion in ["cita", "salida nocturna"]:
            score += 12

    return score

def rank_garments(
    garments: List[Garment],
    category: str,
    occasion: str,
    temp: int,
    rain: bool,
    mood: str,
    activity: str,
    user_profile: Optional[Dict[str, Dict[str, int]]] = None,
):
    filtered = [g for g in garments if g.category == category]

    if occasion == "deporte":
        filtered = [g for g in filtered if garment_has_style(g, "sport")]

    scored = []

    for g in filtered:
        allowed, _ = garment_allowed_for_occasion(g, occasion, rain)
        if not allowed:
            continue

        score = garment_base_score(
            g,
            category,
            occasion,
            temp,
            rain,
            mood,
            activity,
            user_profile,
        )

        scored.append((score, g))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

def outfit_structure_penalty(items: List[Garment]) -> int:
    penalty = 0

    bottom = next((g for g in items if g.category == "bottom"), None)
    shoes = next((g for g in items if g.category == "shoes"), None)

    if not bottom or not shoes:
        return 0

    bottom_name = bottom.name.lower()
    shoes_name = shoes.name.lower()
    bottom_styles = all_styles(bottom)

    bottom_is_jogger_like = (
        "sport" in bottom_styles
        or any(x in bottom_name for x in ["buzo", "jogger", "jogging", "calza", "legging"])
    )

    shoes_are_boot_like = any(
        x in shoes_name for x in ["bota", "botin", "botín", "bototo", "boot"]
    )

    shoes_are_heavy_boots = any(
        x in shoes_name for x in ["bototo", "combat", "chunky"]
    )

    if bottom_is_jogger_like and shoes_are_boot_like:
        if shoes_are_heavy_boots:
            penalty += 35
        else:
            penalty += 24

    return penalty

def outfit_score(
    items: List[Garment],
    occasion: str,
    temp: int,
    rain: bool,
    mood: str,
    activity: str,
    feedback_list: Optional[List[OutfitFeedback]] = None,
    user_profile: Optional[Dict[str, Dict[str, int]]] = None,
    recent_outfits: Optional[List[Any]] = None,
    forced_garment_id: Optional[int] = None,
    ignore_occasion_for_forced: bool = False,
) -> int:
    if not items:
        return 0

    if feedback_list is None:
        feedback_list = []

    score = 0

    for g in items:
        if ignore_occasion_for_forced and forced_garment_id is not None and g.id == forced_garment_id:
            allowed = True
        else:
            allowed, _ = garment_allowed_for_occasion(g, occasion, rain)

        if not allowed:
            return -999

        score += garment_base_score(
            g,
            g.category,
            occasion,
            temp,
            rain,
            mood,
            activity,
            user_profile,
        )

    has_one_piece = any(g.category == "one_piece" for g in items)

    if has_one_piece:
        if occasion == "matrimonio":
            score += 40
        elif occasion == "gala":
            score += 30
        elif occasion == "cita":
            score += 6
        elif occasion == "salida nocturna":
            if mood == "relajado":
                score -= 4
            elif mood in ["elegante", "sexy"]:
                score += 6
            else:
                score += 2

    if has_one_piece:
        one_piece_item = next((g for g in items if g.category == "one_piece"), None)

        if one_piece_item and (
            one_piece_item.dress_level in ["arreglado", "elegante"]
            or garment_has_style(one_piece_item, "elegante")
            or garment_has_style(one_piece_item, "formal")
        ):
            has_utilitarian_layer = False

            for g in items:
                name = g.name.lower()

                if g.category == "midlayer":
                    if (
                        g.warmth == "frio"
                        or garment_has_style(g, "sport")
                        or any(x in name for x in ["polar", "fleece", "sweater grueso"])
                    ):
                        has_utilitarian_layer = True

                if g.category == "outerwear":
                    if any(x in name for x in ["impermeable", "parka", "rain"]):
                        has_utilitarian_layer = True

            if has_utilitarian_layer:
                score -= 45
    # =========================================================
    # 🔥 NUEVO: BONUS POR PRENDA FORZADA
    # =========================================================
    if forced_garment_id is not None:
        forced_item = next((g for g in items if g.id == forced_garment_id), None)

        if forced_item:
            for g in items:
                if g.id == forced_garment_id:
                    continue

                # compensar nivel en trabajo
                if occasion == "trabajo":
                    if g.dress_level in ["arreglado", "elegante"]:
                        score += 4

                # compensar en cita / salida
                if occasion in ["cita", "salida nocturna"]:
                    if g.dress_level in ["arreglado", "elegante"]:
                        score += 3

                # evitar exceso de casualidad
                if forced_item.dress_level == "relajado":
                    if g.dress_level in ["flexible", "arreglado"]:
                        score += 2

                # coherencia de estilo
                if g.style == forced_item.style:
                    score += 2

    # =========================================================
    # COMPATIBILIDAD ENTRE PRENDAS
    # =========================================================
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            score += garment_color_compatibility(items[i], items[j])
            score += style_compatibility(items[i], items[j])
            score += pattern_compatibility(items[i], items[j])

    # =========================================================
    # CONTROL FUERTE DE PATRONES
    # =========================================================
    pattern_info = []
    top_weight = 0
    bottom_weight = 0
    top_pattern = "liso"
    bottom_pattern = "liso"

    for g in items:
        p = getattr(g, "pattern", "liso")

        if p == "liso":
            w = 0
        elif p in ["rayas", "cuadros"]:
            w = 1
        elif p in ["floral", "estampado"]:
            w = 2
        elif p in ["animal_print", "grafico"]:
            w = 3
        else:
            w = 1

        pattern_info.append((g.category, w))

        if g.category == "top":
            top_weight = w
            top_pattern = p
        elif g.category == "bottom":
            bottom_weight = w
            bottom_pattern = p

    strong = [w for _, w in pattern_info if w >= 2]
    bold = [w for _, w in pattern_info if w >= 3]
    patterned = [w for _, w in pattern_info if w >= 1]

    top_is_patterned = top_pattern != "liso"
    bottom_is_patterned = bottom_pattern != "liso"
    top_is_animal = top_pattern == "animal_print"
    bottom_is_animal = bottom_pattern == "animal_print"

    if top_weight >= 2 and bottom_weight >= 2:
        return -999

    if top_is_animal and bottom_is_patterned:
        return -999

    if bottom_is_animal and top_is_patterned:
        return -999

    if len(strong) >= 2:
        score -= 50

    if len(bold) >= 2:
        score -= 30

    if len(patterned) >= 3:
        score -= 20

    # =========================================================
    # AJUSTE SEXY
    # =========================================================
    if mood == "sexy":
        sexy_items = [g for g in items if g.sexiness >= 2]

        if len(sexy_items) == 1:
            score += 4
        elif len(sexy_items) >= 2:
            score += 8

        if all(g.sexiness == 0 for g in items):
            score -= 10
    # =========================================================
    # 🔥 COHERENCIA SEXY (OUTFIT COMPLETO)
    # =========================================================
    if mood == "sexy" and occasion in ["cita", "salida nocturna"]:

        has_sneakers = any(
            g.category == "shoes" and
            ("zapatilla" in g.name.lower() or "sneaker" in g.name.lower())
            for g in items
        )

        has_mini_or_short = any(
            ("mini" in g.name.lower() or "falda" in g.name.lower() or "vestido" in g.name.lower())
            and g.category in ["bottom", "dress"]
            for g in items
        )

        sexy_items = [g for g in items if g.sexiness >= 2]

        # caso 1: outfit claramente sexy
        if has_sneakers and len(sexy_items) >= 2:
            score -= 12

        # caso 2: mini / vestido corto + sneakers (clave)
        if has_sneakers and has_mini_or_short:
            score -= 10
    
    # =========================================================
    # PENALIZACIÓN POR CAPAS OPCIONALES (CONTROL DE SOBRECARGA)
    # =========================================================
    optional_layers = [
        g for g in items if g.category in ["midlayer", "outerwear"]
    ]

    # Penalización base por agregar capas
    if optional_layers:
        score -= 6 * len(optional_layers)

    # Penalización adicional en clima templado-cálido
    if 24 <= temp < 26:
        score -= 12 * len(optional_layers)

    # Penalización fuerte en calor real (backup por si pasan filtros)
    if temp >= 26:
        score -= 12 * len(optional_layers)
    
    # =========================================================
    # PENALIZACIONES
    # =========================================================
    score -= coherence_penalty(items, occasion)
    score -= practicality_penalty(items, occasion, temp, rain)
    score -= outfit_accessory_penalty(items, occasion, mood, activity, temp, rain)
    has_one_piece = any(g.category == "one_piece" for g in items)

    if has_one_piece:
        score -= max(outfit_structure_penalty(items) - 15, 0)
    else:
        score -= outfit_structure_penalty(items)

    # =========================================================
    # FEEDBACK
    # =========================================================
    weather_tag = get_weather_tag(temp, rain)
    score += calculate_feedback_bonus(
        items,
        feedback_list,
        occasion,
        mood,
        activity,
        weather_tag,
    )

    # =========================================================
    # REPETICIÓN
    # =========================================================
    if recent_outfits:
        score -= repetition_penalty(items, recent_outfits)

    return int(score)

def explain_outfit_score(
    items: List[Garment],
    occasion: str,
    temp: int,
    rain: bool,
    mood: str,
    activity: str,
    feedback_list: Optional[List[OutfitFeedback]] = None,
    recent_outfits: Optional[List[Any]] = None,
) -> List[str]:
    if feedback_list is None:
        feedback_list = []

    reasons = []
    weather_tag = get_weather_tag(temp, rain)

    weather_points = sum(weather_score(g, temp, rain) for g in items)
    if weather_points >= len(items) * 15:
        reasons.append("✅ Muy adecuado para el clima")

    mood_points = sum(mood_bonus(g, mood) for g in items)
    if mood_points >= len(items) * 6:
        reasons.append(f"✅ Va bien con el mood '{mood}'")

    activity_points = sum(activity_bonus(g, activity, occasion) for g in items)
    if activity_points >= len(items) * 6:
        reasons.append(f"✅ Funciona bien para la actividad '{activity}'")

    dress_points = sum(dress_score(g.dress_level, occasion) for g in items)
    if dress_points >= len(items) * 12:
        reasons.append(f"✅ Tiene buena formalidad para '{occasion}'")

    category_bonus = sum(
        category_context_bonus(g, occasion, mood, activity, temp, rain)
        for g in items
    )
    if category_bonus >= 12:
        reasons.append("✨ Las prendas encajan bien con el contexto y su categoría")

    category_penalty = sum(
        category_context_penalty(g, occasion, mood, activity, temp, rain)
        for g in items
    )
    if category_penalty >= 12:
        reasons.append("⚠️ Algunas prendas encajan peor con el contexto")

    pattern_points = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            pattern_points += pattern_compatibility(items[i], items[j])

    if pattern_points >= 12:
        reasons.append("🎨 Buena armonía visual entre lisos y estampados")
    elif pattern_points <= -10:
        reasons.append("⚠️ La mezcla de patrones puede verse demasiado cargada")

    feedback_bonus = calculate_feedback_bonus(
        items, feedback_list, occasion, mood, activity, weather_tag
    )
    if feedback_bonus >= 12:
        reasons.append("💚 Favorecido por feedback positivo previo")
    elif feedback_bonus <= -12:
        reasons.append("⚠️ Penalizado por feedback negativo previo")

    coherence = coherence_penalty(items, occasion)
    if coherence >= 10:
        reasons.append("⚠️ Mezcla de estilos menos coherente")

    practicality = practicality_penalty(items, occasion, temp, rain)
    if practicality >= 15:
        reasons.append("⚠️ Menos práctico para este contexto")

    accessory_pen = outfit_accessory_penalty(
        items, occasion, mood, activity, temp, rain
    )
    if accessory_pen >= 12:
        reasons.append("⚠️ Los accesorios cargan demasiado el outfit")

    repeat_pen = repetition_penalty(items, recent_outfits)
    if repeat_pen >= 20:
        reasons.append("🔁 Se penalizó por repetición reciente de prendas")

    if not reasons:
        reasons.append("ℹ️ Recomendación equilibrada según contexto general")

    return reasons[:3]


from engine.outfit_generation import (
    generate_outfits as generate_outfits,
)
from engine.outfit_generation import (
    generate_outfits_from_selected_garment as generate_outfits_from_selected_garment,
)
from engine.outfit_generation import generate_week_plan as generate_week_plan