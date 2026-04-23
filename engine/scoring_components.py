#scoring_components.py
from typing import List

from models import Garment
from utils.garment_utils import garment_has_style, all_styles, is_shoe_heel


def dress_score(dress_level: str, occasion: str) -> int:
    matrix = {
        "deporte": {
            "relajado": 18,
            "flexible": 12,
            "arreglado": 4,
            "elegante": 0,
        },
        "casual": {
            "relajado": 15,
            "flexible": 18,
            "arreglado": 10,
            "elegante": 4,
        },
        "trabajo": {
            "relajado": 4,
            "flexible": 16,
            "arreglado": 18,
            "elegante": 14,
        },
        "cita": {
            "relajado": 6,
            "flexible": 14,
            "arreglado": 18,
            "elegante": 17,
        },
        "salida nocturna": {
            "relajado": 3,
            "flexible": 16,
            "arreglado": 18,
            "elegante": 14,
        },
        "matrimonio": {
            "relajado": 0,
            "flexible": 4,
            "arreglado": 15,
            "elegante": 20,
        },
        "gala": {
            "relajado": 0,
            "flexible": 2,
            "arreglado": 10,
            "elegante": 20,
        },
    }

    return matrix.get(occasion, {}).get(dress_level, 0)

def weather_score(garment: Garment, temp: int, rain: bool, occasion: str = "", mood: str = "", items: List[Garment] = None) -> int:
    score = 0

    # Un outerwear impermeable es siempre válido con lluvia; se diferencia por warmth según temp
    if rain and garment.category == "outerwear" and garment.waterproof:
        if temp <= 10:
            warmth_bonus = {"frio": 5, "medio": 2, "caluroso": -5}.get(garment.warmth, 0)
        elif temp <= 20:
            warmth_bonus = {"frio": 2, "medio": 5, "caluroso": 0}.get(garment.warmth, 0)
        else:
            warmth_bonus = {"frio": -5, "medio": 2, "caluroso": 5}.get(garment.warmth, 0)
        return 15 + warmth_bonus

    if temp <= 10:
        if garment.warmth == "frio":
            score += 18
        elif garment.warmth == "medio":
            base_warmth = 8
            if garment.category == "outerwear" and items is not None:
                has_cold_midlayer = any(
                    g.category == "midlayer" and g.warmth == "frio"
                    for g in items
                    if g is not garment
                )
                if has_cold_midlayer:
                    penalty = 18 - base_warmth  # 10 puntos de penalización
                    base_warmth += penalty * 0.90  # reducir 90% de la penalización
            score += base_warmth
        else:  # caluroso
            score -= 12

    elif 11 <= temp <= 20:
        if garment.warmth == "medio":
            score += 18
        elif garment.warmth in ["frio", "caluroso"]:
            score += 6

    else:  # calor
        if garment.warmth == "caluroso":
            score += 18
        elif garment.warmth == "medio":
            score += 8
        else:  # frio
            score -= 12

    # Boost a jeans con frío por ocasión y mood
    if temp <= 10 and garment.category == "bottom" and garment.subcategory == "jeans":
        cold_moods = ["relajado", "urbano", "comodo"]
        if occasion in ["casual", "salida nocturna"]:
            score += 10
        elif occasion in ["cita", "trabajo"] and mood in cold_moods:
            score += 8
        if temp <= 8:
            score += 15

    # lluvia
    if rain:
        if garment.category == "outerwear" and garment.waterproof:
            score += 15
        elif garment.category == "shoes":
            score += 8
        else:
            score -= 2
    else:
        score += 5

    # Boost a parkas con frío sin lluvia en salida nocturna
    if (
        not rain
        and temp <= 8
        and occasion == "salida nocturna"
        and garment.category == "outerwear"
        and garment.subcategory in ["parka"]
        and garment.dress_level in ["flexible", "arreglado", "elegante"]
    ):
        score += 10

    return score


def activity_bonus(garment: Garment, activity: str, occasion: str = "") -> int:
    lower_name = garment.name.lower()

    if activity == "caminar":
        if occasion == "salida nocturna":
            if garment.category == "shoes":
                if (
                    "zapatilla" in lower_name
                    or "bota" in lower_name
                    or garment_has_style(garment, "urbano")
                    or garment_has_style(garment, "sport")
                ):
                    return 10

                if "taco" in lower_name or "heel" in lower_name:
                    return 6

                return 6

            if garment.category == "bottom":
                if "jean" in lower_name or "jeans" in lower_name:
                    return 8
                if "buzo" in lower_name or "jogger" in lower_name or garment.subcategory in ["buzo", "jogger"]:
                    return 2
                return 5

            if garment.category == "outerwear":
                return 5

            return 4

        if garment.category == "shoes" and (
            "zapatilla" in lower_name
            or garment_has_style(garment, "sport")
            or garment_has_style(garment, "urbano")
        ):
            return 10
        return 4

    if activity == "normal":
        if occasion in ["matrimonio", "gala"]:
            if garment_has_style(garment, "elegante") or garment_has_style(
                garment, "formal"
            ):
                return 8
            if garment.dress_level in ["arreglado", "elegante"]:
                return 6
            return 1

        if occasion == "salida nocturna":
            if garment_has_style(garment, "urbano") or garment_has_style(
                garment, "sexy"
            ):
                return 8
            if garment.dress_level in ["flexible", "arreglado"]:
                return 7
            if garment_has_style(garment, "sport"):
                return 2
            return 5

        return 6

    if activity == "formal":
        if garment_has_style(garment, "elegante") or garment_has_style(
            garment, "formal"
        ):
            return 10
        return 3

    if activity == "entrenar":
        if garment_has_style(garment, "sport"):
            return 12
        return 0

    return 0


def mood_bonus(garment: Garment, mood: str) -> int:
    garment_styles = all_styles(garment)

    mood_map = {
        "relajado": {
            "strong": ["casual", "sport"],
            "soft": ["urbano", "formal"],
        },
        "urbano": {
            "strong": ["urbano"],
            "soft": ["casual", "sport", "elegante"],
        },
        "elegante": {
            "strong": ["elegante", "formal"],
            "soft": ["urbano"],
        },
        "sexy": {
            "strong": ["elegante", "formal", "sexy"],
            "soft": ["urbano"],
        },
        "comodo": {
            "strong": ["casual", "sport"],
            "soft": ["urbano"],
        },
    }

    config = mood_map.get(mood, {"strong": [], "soft": []})

    strong_hits = sum(1 for s in config["strong"] if s in garment_styles)
    soft_hits = sum(1 for s in config["soft"] if s in garment_styles)

    if strong_hits >= 2:
        base = 10
    elif strong_hits == 1:
        base = 8
    elif soft_hits >= 1:
        base = 5
    else:
        base = 2

    if mood == "urbano":
        urban_prints = ["animal_print", "estampado", "grafico", "floral"]
        urban_colors = ["fucsia", "rojo", "mostaza", "verde olivo", "burdeo", "naranja"]
        if getattr(garment, "pattern", None) in urban_prints:
            base += 15
        if getattr(garment, "color", None) in urban_colors:
            base += 3

    return base


def sexiness_bonus(garment: Garment, mood: str, occasion: str, activity: str) -> int:
    if mood != "sexy":
        return 0

    base_map = {
        0: 0,
        1: 4,
        2: 8,
        3: 12,
    }

    score = base_map.get(garment.sexiness, 0)

    if occasion in ["cita", "matrimonio"]:
        score += 2

    if occasion in ["trabajo", "deporte"]:
        score -= 3

    if garment.category == "accessory":
        score = max(0, score - 3)

    if garment_has_style(garment, "sport"):
        if activity == "deporte":
            score = max(score - 2, 0)
        else:
            score -= 10

    # 🔥 NUEVO: penalización específica para zapatillas
    if garment.category == "shoes":
        name = garment.name.lower()
        if "zapatilla" in name or "sneaker" in name:
            if occasion in ["cita", "salida nocturna", "casual"]:
                score -= 6

    return max(score, 0)

def coherence_penalty(items: List[Garment], occasion: str) -> int:
    penalty = 0
    styles = []
    dress_levels = []

    for g in items:
        styles.extend(all_styles(g))
        dress_levels.append(g.dress_level)

    if len(set(styles)) > 4:
        penalty += 10

    if "relajado" in dress_levels and "elegante" in dress_levels:
        penalty += 12

    if "sport" in styles and ("formal" in styles or "elegante" in styles):
        penalty += 10

    if occasion in ["gala", "matrimonio"]:
        for g in items:
            if g.category == "shoes":
                if "zapatilla" in g.name.lower() or garment_has_style(g, "sport"):
                    penalty += 8

    # =========================================================
    # PRENDA BOLD VS BASE DEMASIADO RELAJADA
    # =========================================================
    bold_items = []
    relaxed_base_count = 0

    for g in items:
        name = g.name.lower()
        styles = all_styles(g)
        pattern = getattr(g, "pattern", "liso")

        is_bold = (
            pattern in ["animal_print", "grafico"]
            or getattr(g, "sexiness", 0) >= 2
        )

        if is_bold:
            bold_items.append(g)

        is_relaxed_base = (
            "sport" in styles
            or "casual" in styles
            or any(x in name for x in [
                "buzo", "jogger", "jogging", "polar", "fleece",
                "zapatilla", "sneaker", "converse",
                "gorro", "beanie"
            ])
            or g.subcategory in ["buzo", "jogger"]
        )

        if is_relaxed_base:
            relaxed_base_count += 1

    if bold_items and relaxed_base_count >= 2:
        penalty += 18

    if bold_items and relaxed_base_count >= 3:
        penalty += 10

    # Penalización por exceso de colores distintos
    unique_colors = {g.color for g in items if getattr(g, "color", None)}
    if len(unique_colors) >= 4:
        if occasion in ["cita", "salida nocturna", "matrimonio", "gala"]:
            penalty += 35
        else:
            penalty += 20

    return penalty


def practicality_penalty(
    items: List[Garment], occasion: str, temp: int, rain: bool, mood: str = ""
) -> int:
    penalty = 0

    for g in items:
        name = g.name.lower()
        styles = all_styles(g)

        if occasion in ["matrimonio", "gala"]:
            if g.category == "outerwear":
                if any(x in name for x in ["impermeable", "parka", "rain", "agua"]):
                    penalty += 35

                if "urbano" in styles and g.dress_level in ["flexible", "relajado"]:
                    penalty += 15

        if occasion == "trabajo":
            if g.category == "shoes":
                if "converse" in name:
                    penalty += 120
                elif "zapatilla" in name or garment_has_style(g, "sport"):
                    if g.dress_level == "relajado":
                        penalty += 45
        if mood == "comodo":
            if g.category == "shoes":
                if is_shoe_heel(g):
                    penalty += 50
        if rain:
            if g.category == "outerwear":
                if not g.waterproof:
                    penalty += 25

        if g.category == "bottom":
            if "short" in name:
                if rain or temp <= 14:
                    penalty += 60
            if temp <= 8 and g.subcategory in ["falda_midi", "falda_larga"]:
                penalty += 35
            if temp <= 8 and g.subcategory == "pantalon":
                if g.warmth == "caluroso":
                    penalty += 25
                elif g.warmth == "medio":
                    penalty += 12
                elif g.warmth == "frio":
                    penalty -= 15
            if g.subcategory == "jeans":
                if temp >= 30:
                    penalty += 80
                elif temp >= 28:
                    penalty += 50
                elif temp >= 24:
                    penalty += 20
                if mood == "elegante" and g.dress_level == "relajado":
                    penalty += 55
                if mood in ["elegante", "sexy"] and g.subcategory == "jeans" and getattr(g, "sexiness", 0) == 0:
                    if g.dress_level == "relajado":
                        penalty += 85
                    elif g.dress_level == "flexible":
                        penalty += 40
        if rain:
            if g.category == "shoes":
                if is_shoe_heel(g):
                    penalty += 35
                if g.subcategory == "mocasin":
                    penalty += 60

        if occasion == "salida nocturna" and g.category == "shoes" and g.subcategory == "mocasin":
            if mood in ["relajado", "comodo"]:
                penalty += 45
            elif mood in ["urbano", "elegante", "sexy"]:
                penalty += 55

        if occasion == "salida nocturna" and g.category == "shoes" and g.subcategory == "zapatilla_urbana":
            if mood in ["relajado", "comodo"]:
                penalty -= 45
                if temp >= 24:
                    penalty -= 15

        if occasion == "salida nocturna" and mood == "relajado" and g.category == "shoes":
            if g.subcategory == "taco_alto":
                penalty += 35
            elif g.subcategory == "taco_bajo":
                penalty += 15

        if occasion == "salida nocturna" and mood == "urbano" and g.category == "shoes":
            if g.subcategory == "taco_alto":
                penalty += 35
            elif g.subcategory == "taco_bajo":
                penalty += 20
            elif g.subcategory == "zapatilla_urbana":
                penalty -= 50
                if rain and not g.waterproof:
                    light_colors = {"blanco", "crema", "beige", "celeste", "gris claro", "amarillo", "rosado", "lila"}
                    if getattr(g, "color", None) and g.color.lower() in light_colors:
                        penalty += 30
                    else:
                        penalty += 15

        if occasion == "matrimonio" and mood == "urbano":
            if g.category == "shoes":
                if g.subcategory == "taco_alto":
                    penalty += 50
                elif g.subcategory in ["botin", "zapato", "mocasin"]:
                    penalty -= 40
                elif g.subcategory == "zapatilla_urbana" and g.dress_level in ["arreglado", "elegante"]:
                    penalty -= 40

        if temp >= 26:
            if g.category == "outerwear":
                penalty += 40

            if g.category == "midlayer":
                penalty += 25

            if g.category == "shoes" and g.subcategory == "taco_alto":
                penalty += 20

            if (
                g.category == "one_piece"
                and g.subcategory in ["vestido_elegante", "vestido_coctel"]
                and g.warmth == "frio"
                and occasion == "matrimonio"
            ):
                penalty += 60

        elif temp >= 22:
            if g.category == "outerwear":
                if g.warmth == "frio":
                    penalty += 25
                elif g.warmth == "medio":
                    penalty += 16
                else:
                    penalty += 10

            if g.category == "midlayer":
                if g.warmth == "frio":
                    penalty += 18
                elif g.warmth == "medio":
                    penalty += 10

        if (
            occasion == "matrimonio"
            and mood != "urbano"
            and g.category == "shoes"
            and g.subcategory == "zapato"
        ):
            penalty += 999  # hard block — zapato derby nunca en matrimonio elegante

        if not rain:
            if g.category == "outerwear" and g.waterproof:
                penalty += 28

        if not rain and temp >= 16:
            if g.category == "outerwear":
                if occasion == "matrimonio" and mood == "elegante" and temp <= 23:
                    penalty += 45
                else:
                    penalty += 20

        if (
            occasion == "matrimonio"
            and mood == "elegante"
            and 13 <= temp <= 23
            and g.category == "outerwear"
        ):
            penalty += 80

        if (
            mood == "relajado"
            and g.category == "one_piece"
            and g.subcategory in ["vestido_elegante", "vestido_coctel"]
        ):
            penalty += 80

        if (
            mood == "urbano"
            and g.category == "one_piece"
            and g.subcategory in ["vestido_elegante", "vestido_coctel"]
        ):
            penalty += 150

        # Bonus outerwear abrigado en salida nocturna mood relajado con frío extremo
        if (
            occasion == "salida nocturna"
            and mood in ["relajado", "comodo"]
            and temp <= 8
            and g.category == "outerwear"
            and g.warmth == "frio"
            and g.subcategory in ["parka", "chaqueta"]
        ):
            penalty -= 10

        if (
            mood in ["elegante", "sexy"]
            and g.category == "bottom"
            and g.subcategory in ["falda_midi", "falda_larga", "pantalon"]
            and g.dress_level in ["arreglado", "elegante"]
        ):
            penalty -= 50

        if (
            temp >= 24
            and occasion == "matrimonio"
            and g.category == "midlayer"
            and g.subcategory == "blazer"
        ):
            has_one_piece = any(x.category == "one_piece" for x in items)
            if has_one_piece:
                one_piece = next(x for x in items if x.category == "one_piece")
                if one_piece.warmth != "caluroso" and g.warmth != "caluroso":
                    penalty += 999

    # Vestido elegante/cóctel: solo calzado formal y capas elegantes (una vez por outfit)
    has_vestido_elegante = any(
        g.category == "one_piece"
        and g.subcategory in ["vestido_elegante", "vestido_coctel"]
        for g in items
    )
    if has_vestido_elegante:
        for g in items:
            if g.category == "shoes":
                if g.subcategory in ["botin", "bota"]:
                    penalty += 999  # hard block: botas no van con vestido elegante/cóctel
                elif g.subcategory not in ["taco_alto", "taco_bajo", "sandalia"]:
                    penalty += 80
            if g.category == "midlayer":
                if g.subcategory not in ["blazer"]:
                    penalty += 70
            if g.category == "outerwear":
                if g.subcategory not in ["abrigo", "trench"]:
                    penalty += 70
            if g.category == "accessory":
                if g.subcategory in ["gorro", "gorra"] or g.accessory_type in ["gorro", "gorra"]:
                    penalty += 80
                if g.subcategory in ["bufanda", "pañuelo", "cartera", "bolso"]:
                    if g.style not in ["elegante", "formal"]:
                        penalty += 80

    # Boost vestido elegante/cóctel en salida nocturna mood elegante o sexy (una vez por outfit)
    if (
        has_vestido_elegante
        and occasion == "salida nocturna"
        and mood in ["elegante", "sexy"]
    ):
        penalty -= 60

    layer_count = sum(1 for g in items if g.category in ["midlayer", "outerwear"])

    if temp >= 26 and layer_count >= 1:
        penalty += 30

    if temp >= 22 and layer_count >= 2:
        penalty += 25
    
    has_one_piece_elegante = any(
        g.category == "one_piece"
        and (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
        for g in items
    )

    if has_one_piece_elegante and occasion in ["matrimonio", "gala"]:
        penalty = max(penalty - 40, 0)

    # Boost fuerte a vestidos elegantes/cóctel en matrimonio
    if occasion == "matrimonio":
        for g in items:
            if g.category == "one_piece" and g.subcategory in ["vestido_elegante", "vestido_coctel"]:
                penalty -= 160
            elif g.category == "one_piece" and g.subcategory == "vestido_casual":
                penalty -= 60
            elif g.category == "one_piece" and g.subcategory == "enterito" and mood == "sexy":
                penalty -= 160

    # Boost a outfit con prenda muy sexy cuando mood es sexy
    # Solo en ocasiones donde sexy es apropiado
    if mood == "sexy" and occasion in ["matrimonio", "salida nocturna", "cita"]:
        max_sexiness = max((getattr(g, "sexiness", 0) for g in items), default=0)
        if max_sexiness >= 3:
            penalty -= 70
        elif max_sexiness == 2:
            penalty -= 25

    return penalty