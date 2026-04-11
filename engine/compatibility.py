#compatibility.py
from typing import List

from models import Garment
from utils.garment_utils import all_styles


# =========================================================
# NORMALIZACIÓN / HELPERS DE COLOR
# =========================================================

def normalize_color(color: str) -> str:
    from constants import COLOR_ALIASES

    if not color:
        return "negro"

    c = color.strip().lower()
    return COLOR_ALIASES.get(c, c)


def color_family(color: str) -> str:
    c = normalize_color(color)

    families = {
        "negro": "neutral_dark",
        "gris": "neutral_mid",
        "blanco": "neutral_light",
        "beige": "neutral_light",
        "café": "earth",
        "azul": "blue",
        "azul marino": "blue_dark",
        "verde": "green",
        "verde oliva": "earth_green",
        "rojo": "red",
        "rosado": "pink",
        "amarillo": "yellow",
        "naranjo": "orange",
        "morado": "purple",
    }

    return families.get(c, c)


def garment_colors(garment: Garment) -> List[str]:
    colors = []

    main_color = normalize_color(getattr(garment, "color", "negro"))
    colors.append(main_color)

    secondary = getattr(garment, "secondary_colors", []) or []
    for c in secondary:
        normalized = normalize_color(c)
        if normalized not in colors:
            colors.append(normalized)

    return colors


# =========================================================
# COMPATIBILIDAD DE COLOR
# =========================================================

def color_compatibility(color1: str, color2: str) -> int:
    c1 = normalize_color(color1)
    c2 = normalize_color(color2)

    neutral_colors = {"blanco", "negro", "gris", "beige", "café"}
    strong_bad_pairs = {
        ("rojo", "verde"),
        ("verde", "rosado"),
        ("naranjo", "rosado"),
        ("amarillo", "rosado"),
        ("morado", "verde"),
        ("rojo", "azul"),
        ("rojo", "azul marino"),
        ("burdeo", "verde"),
        ("burdeo", "azul"),
        ("naranjo", "morado"),
        ("amarillo", "burdeo"),
    }

    good_pairs = {
        ("blanco", "azul"),
        ("blanco", "azul marino"),
        ("azul", "café"),
        ("azul", "beige"),
        ("azul marino", "beige"),
        ("azul marino", "blanco"),
        ("negro", "blanco"),
        ("negro", "gris"),
        ("amarillo", "negro"),
        ("amarillo", "azul marino"),
        ("amarillo", "blanco"),
        ("amarillo", "gris"),
        ("amarillo", "beige"),
        ("verde oliva", "beige"),
        ("verde oliva", "blanco"),
        ("verde oliva", "café"),
        ("rojo", "blanco"),
        ("rojo", "negro"),
        ("rosado", "blanco"),
        ("rosado", "gris"),
        ("morado", "blanco"),
        ("morado", "gris"),
        ("burdeo", "negro"),
        ("burdeo", "blanco"),
        ("burdeo", "beige"),
        ("burdeo", "gris"),
        ("rosado", "café"),
        ("rosado", "azul marino"),
        ("verde oliva", "negro"),
        ("verde oliva", "azul marino"),
        ("amarillo", "café"),
        ("celeste", "blanco"),
        ("celeste", "azul marino"),
        ("celeste", "gris"),
    }

    if c1 == c2:
        return 18

    if (c1, c2) in strong_bad_pairs or (c2, c1) in strong_bad_pairs:
        return -10

    if c1 in neutral_colors or c2 in neutral_colors:
        return 15

    if color_family(c1) == color_family(c2):
        return 14

    if (c1, c2) in good_pairs or (c2, c1) in good_pairs:
        return 14

    return 8

def is_multicolor(garment: Garment) -> bool:
    return len(garment_colors(garment)) >= 3

def garment_color_compatibility(g1: Garment, g2: Garment) -> int:
    colors1 = garment_colors(g1)
    colors2 = garment_colors(g2)

    scores = [color_compatibility(c1, c2) for c1 in colors1 for c2 in colors2]

    if not scores:
        return 0

    best_score = max(scores)
    worst_score = min(scores)

    overlap = set(colors1) & set(colors2)

    # =========================================================
    # NUEVA LÓGICA CLAVE
    # =========================================================

    # Caso 1: overlap real fuerte (color principal compartido)
    if g1.color in overlap or g2.color in overlap:
        return best_score + 2

    # Caso 2: overlap débil (solo secundarios)
    if overlap:
        return best_score - 2

    # Caso 3: choque fuerte sin compensación
    if worst_score <= -10:
        return -8

    if is_multicolor(g1) and is_multicolor(g2):
        if not overlap:
            return -10
    
    return best_score


# =========================================================
# COMPATIBILIDAD DE ESTILO
# =========================================================

def style_compatibility(garment1: Garment, garment2: Garment) -> int:
    styles1 = all_styles(garment1)
    styles2 = all_styles(garment2)

    # =========================================================
    # PENALIZACIONES POR COMBINACIONES INCOHERENTES
    # =========================================================

    if {garment1.category, garment2.category} == {"bottom", "shoes"}:
        bottom = garment1 if garment1.category == "bottom" else garment2
        shoes = garment1 if garment1.category == "shoes" else garment2

        bottom_styles = all_styles(bottom)
        shoes_styles = all_styles(shoes)

        bottom_name = bottom.name.lower()
        shoes_name = shoes.name.lower()

        bottom_is_sport = (
            "sport" in bottom_styles
            or "buzo" in bottom_name
            or "jogger" in bottom_name
            or "jogging" in bottom_name
        )

        bottom_is_formalish = (
            "formal" in bottom_styles
            or "elegante" in bottom_styles
            or bottom.dress_level in ["arreglado", "elegante"]
            or "falda" in bottom_name
        )

        shoes_are_heels_or_very_formal = (
            "taco" in shoes_name
            or "tacón" in shoes_name
            or "heel" in shoes_name
            or "heels" in shoes_name
            or "stiletto" in shoes_name
            or (
                ("formal" in shoes_styles or "elegante" in shoes_styles)
                and "zapatilla" not in shoes_name
            )
        )

        shoes_are_very_casual = (
            "urbano" in shoes_styles
            or "sport" in shoes_styles
            or "casual" in shoes_styles
            or "zapatilla" in shoes_name
            or "converse" in shoes_name
            or "sneaker" in shoes_name
        )

        if bottom_is_sport and shoes_are_heels_or_very_formal:
            return -28

        if bottom_is_formalish and shoes_are_very_casual:
            return -14
        
        shoes_are_sport = "sport" in shoes_styles or "deporte" in shoes_name

        if bottom_is_formalish and shoes_are_sport:
            return -22

    if {garment1.category, garment2.category} == {"top", "shoes"}:
        top = garment1 if garment1.category == "top" else garment2
        shoes = garment1 if garment1.category == "shoes" else garment2

        top_styles = all_styles(top)
        shoes_styles = all_styles(shoes)

        top_name = top.name.lower()
        shoes_name = shoes.name.lower()

        top_is_very_relaxed = (
            "sport" in top_styles
            or "casual" in top_styles
            or "polera" in top_name
            or "buzo" in top_name
        )

        shoes_are_heels = (
            "taco" in shoes_name
            or "tacón" in shoes_name
            or "heel" in shoes_name
            or "heels" in shoes_name
            or "stiletto" in shoes_name
        )

        if top_is_very_relaxed and shoes_are_heels:
            return -18

    if {garment1.category, garment2.category} in [{"bottom", "midlayer"}, {"bottom", "outerwear"}]:
        bottom = garment1 if garment1.category == "bottom" else garment2
        layer = garment1 if garment1.category in ["midlayer", "outerwear"] else garment2

        bottom_styles = all_styles(bottom)
        layer_styles = all_styles(layer)

        bottom_name = bottom.name.lower()
        layer_name = layer.name.lower()

        bottom_is_sport = (
            "sport" in bottom_styles
            or "buzo" in bottom_name
            or "jogger" in bottom_name
            or "jogging" in bottom_name
        )

        layer_is_elegant = (
            "formal" in layer_styles
            or "elegante" in layer_styles
            or layer.dress_level in ["arreglado", "elegante"]
            or "blazer" in layer_name
            or "abrigo" in layer_name
        )

        if bottom_is_sport and layer_is_elegant:
            return -20

    if {garment1.category, garment2.category} in [{"shoes", "midlayer"}, {"shoes", "outerwear"}]:
        shoes = garment1 if garment1.category == "shoes" else garment2
        layer = garment1 if garment1.category in ["midlayer", "outerwear"] else garment2

        shoes_styles = all_styles(shoes)
        layer_styles = all_styles(layer)

        shoes_name = shoes.name.lower()
        layer_name = layer.name.lower()

        shoes_are_sport = (
            "sport" in shoes_styles
            or "zapatilla" in shoes_name
            or "sneaker" in shoes_name
        )

        layer_is_elegant = (
            "formal" in layer_styles
            or "elegante" in layer_styles
            or layer.dress_level in ["arreglado", "elegante"]
            or "blazer" in layer_name
            or "abrigo" in layer_name
        )

        if shoes_are_sport and layer_is_elegant:
            return -20

    # =========================================================
    # BLOQUE NUEVO: PROTEGER INTENCIÓN ELEGANTE / SEXY
    # =========================================================

    if {garment1.category, garment2.category} == {"midlayer", "one_piece"}:
        mid = garment1 if garment1.category == "midlayer" else garment2
        base = garment1 if garment1.category == "one_piece" else garment2

        base_styles = all_styles(base)
        mid_styles = all_styles(mid)

        base_is_elegant_or_sexy = (
            "elegante" in base_styles
            or base.dress_level in ["arreglado", "elegante"]
            or getattr(base, "sexiness", 0) >= 2
        )

        mid_is_casual_or_urban = (
            "casual" in mid_styles
            or "urbano" in mid_styles
        )

        if base_is_elegant_or_sexy and mid_is_casual_or_urban:
            return -18

    # =========================================================
    # RECOMPENSAS NORMALES
    # =========================================================

    if any(s1 == s2 for s1 in styles1 for s2 in styles2):
        return 18

    allowed = {
        ("casual", "urbano"),
        ("elegante", "casual"),
        ("elegante", "urbano"),
        ("casual", "sport"),
        ("sport", "urbano"),
        ("formal", "elegante"),
        ("formal", "casual"),
        ("formal", "urbano"),
    }

    for s1 in styles1:
        for s2 in styles2:
            if (s1, s2) in allowed or (s2, s1) in allowed:
                return 12

    return 4

# =========================================================
# COMPATIBILIDAD DE PATRONES
# =========================================================

def get_pattern_weight(pattern: str) -> int:
    """
    0 = liso
    1 = light (rayas, cuadros)
    2 = medium (floral, estampado)
    3 = bold (animal print, gráfico)
    """
    if pattern == "liso":
        return 0
    if pattern in ["rayas", "cuadros"]:
        return 1
    if pattern in ["floral", "estampado"]:
        return 2
    if pattern in ["animal_print", "grafico"]:
        return 3
    return 1


def pattern_compatibility(g1: Garment, g2: Garment) -> int:
    p1 = getattr(g1, "pattern", "liso")
    p2 = getattr(g2, "pattern", "liso")

    w1 = get_pattern_weight(p1)
    w2 = get_pattern_weight(p2)

    if w1 == 0 and w2 == 0:
        return 12

    if (w1 >= 2 and w2 == 0) or (w2 >= 2 and w1 == 0):
        return 10

    if (w1 == 1 and w2 == 0) or (w2 == 1 and w1 == 0):
        return 9

    if w1 == 1 and w2 == 1:
        return 6

    if w1 == 2 and w2 == 2:
        return -6

    if (w1 == 2 and w2 == 3) or (w2 == 2 and w1 == 3):
        return -10

    if w1 == 3 and w2 == 3:
        return -18

    return 2


def normalize_pattern(pattern: str) -> str:
    if not pattern:
        return "liso"
    return pattern.strip().lower()


def get_pattern_weight_simple(garment: Garment) -> int:
    pattern = normalize_pattern(getattr(garment, "pattern", "liso"))

    if any(x in pattern for x in ["leop", "zebr", "cebr", "animal"]):
        return 3

    if any(x in pattern for x in ["camufl", "graf", "print"]):
        return 3

    if any(x in pattern for x in ["floral", "estamp", "abstract"]):
        return 2

    if any(x in pattern for x in ["ray", "cuadr", "punt", "text"]):
        return 1

    if pattern == "liso":
        return 0

    return 1


def invalid_pattern_combo(combo: List[Garment]) -> bool:
    top_item = next((g for g in combo if g.category == "top"), None)
    bottom_item = next((g for g in combo if g.category == "bottom"), None)

    if not top_item or not bottom_item:
        return False

    top_weight = get_pattern_weight_simple(top_item)
    bottom_weight = get_pattern_weight_simple(bottom_item)

    if top_weight >= 2 and bottom_weight >= 2:
        return True

    top_pattern = normalize_pattern(getattr(top_item, "pattern", "liso"))
    bottom_pattern = normalize_pattern(getattr(bottom_item, "pattern", "liso"))

    top_is_animal = (
        "animal" in top_pattern
        or "leop" in top_pattern
        or "zebr" in top_pattern
        or "cebr" in top_pattern
    )
    bottom_is_animal = (
        "animal" in bottom_pattern
        or "leop" in bottom_pattern
        or "zebr" in bottom_pattern
        or "cebr" in bottom_pattern
    )

    if top_is_animal and bottom_weight > 0:
        return True

    if bottom_is_animal and top_weight > 0:
        return True

    return False