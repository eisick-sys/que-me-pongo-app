# CATEGORY_RULES.py
from typing import List

from models import Garment
from utils.garment_utils import (
    all_styles,
    garment_has_style,
    is_shoe_heel,
    is_shoe_boot_like,
    is_shoe_sneaker_like,
    is_bottom_skirt,
    is_bottom_short_or_light,
    is_bottom_jeans,
    is_bottom_pants,
    is_accessory_scarf_like,
    is_accessory_cap_like,
    is_accessory_winter_hat_like,
    is_outerwear_rain_like,
    is_outerwear_formal_friendly,
    is_top_too_sporty,
    is_midlayer_formal_friendly,
    is_shoe_ballet_flat,
)

# =========================================================
# TOP
# =========================================================

def top_context_penalty(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "top":
        return 0

    penalty = 0

    if occasion in ["trabajo", "cita", "salida nocturna"]:
        if is_top_too_sporty(garment):
            penalty += 10

    if occasion == "trabajo" and mood == "elegante":
        if "polera" in garment.name.lower() or "tshirt" in garment.name.lower():
            penalty += 18

    if occasion in ["gala", "matrimonio"]:
        if garment_has_style(garment, "casual"):
            penalty += 12
        if garment_has_style(garment, "sport"):
            penalty += 20

    if mood == "urbano":
        if garment_has_style(garment, "formal") and not garment_has_style(garment, "urbano"):
            penalty += 8

    if temp >= 26 and garment.warmth == "frio":
        penalty += 10

    if garment.subcategory == "polera_deporte":
        if occasion not in ["deporte", "casual"]:
            penalty += 20

    return penalty
#---------------------------------------------------------------

def top_context_bonus(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "top":
        return 0

    bonus = 0
    name = garment.name.lower()

    if occasion == "salida nocturna":
        if garment_has_style(garment, "urbano"):
            bonus += 5
        if garment_has_style(garment, "elegante"):
            bonus += 4

    if occasion == "trabajo":
        if garment_has_style(garment, "formal") or garment_has_style(garment, "elegante"):
            bonus += 5

    if mood == "urbano":
        if garment_has_style(garment, "urbano"):
            bonus += 6
        if garment_has_style(garment, "casual"):
            bonus += 2

    if mood == "relajado":
        if garment_has_style(garment, "casual"):
            bonus += 5
        if garment_has_style(garment, "sport"):
            bonus += 2

    if temp >= 24:
        if garment.warmth == "caluroso":
            bonus += 5
        elif garment.warmth == "medio":
            bonus += 2

    if any(x in name for x in ["camisa", "blusa"]) and occasion in ["trabajo", "cita"]:
        bonus += 3

    if garment.subcategory == "polera_deporte":
        if occasion == "deporte":
            bonus += 12
        if activity in ["entrenar", "caminar"]:
            bonus += 8

    return bonus

# =========================================================
# BOTTOM
# =========================================================

def bottom_context_penalty(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "bottom":
        return 0

    name = garment.name.lower()
    styles = all_styles(garment)

    is_skirt = is_bottom_skirt(garment)
    is_short_or_light = is_bottom_short_or_light(garment)
    is_jeans = is_bottom_jeans(garment)
    is_relaxed_context = occasion == "casual" and mood in ["relajado", "comodo"]

    is_jogger_like = (
        "buzo" in name
        or "jogger" in name
        or "joggers" in name
        or garment_has_style(garment, "sport")
        or (
            garment.dress_level in ["relajado", "flexible"]
            and any(s in styles for s in ["sport"])
        )
    )

    penalty = 0

    # Reglas por actividad/clima ya existentes
    if activity == "caminar":
        if is_skirt:
            penalty += 10

        if rain and is_skirt:
            penalty += 14

        if temp <= 10 and is_skirt:
            penalty += 10

    if rain and temp <= 10:
        if is_skirt:
            penalty += 8

        if is_short_or_light:
            penalty += 8

    if is_relaxed_context and activity == "caminar":
        if is_skirt:
            penalty += 6

    if occasion == "casual" and mood == "elegante":
        if is_skirt:
            penalty += 6
    
    if occasion == "casual" and mood == "elegante":
        if is_short_or_light:
            penalty += 12

    if occasion == "trabajo" and mood == "elegante":
        if is_short_or_light:
            penalty += 25
    
    if occasion == "trabajo" and mood == "sexy" and is_short_or_light:
        penalty += 8

    if occasion == "trabajo" and mood == "sexy" and is_jeans:
        penalty += 12

    if occasion == "trabajo" and is_skirt:
        if garment.dress_level in ["relajado", "flexible"] and garment.sexiness >= 3:
            penalty += 14

    if is_jogger_like:
        if occasion == "trabajo":
            penalty += 22

        if occasion == "cita":
            penalty += 24

        if occasion == "casual" and mood == "urbano":
            penalty += 14
            
            if temp <= 10:
                penalty += 6

        if occasion == "casual" and mood == "elegante":
            penalty += 10

        if occasion == "casual" and mood == "sexy":
            penalty += 18

        if occasion == "salida nocturna" and mood in ["elegante", "sexy"]:
            penalty += 26
        elif occasion == "salida nocturna" and mood == "urbano":
            penalty += 14
        elif occasion == "salida nocturna" and mood == "comodo":
            penalty += 18
        elif occasion == "salida nocturna":
            penalty += 20

        if occasion == "salida nocturna" and activity == "caminar":
            penalty -= 4

        if mood == "elegante":
            penalty += 10

    return penalty
#---------------------------------------------------------------

def bottom_context_bonus(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "bottom":
        return 0

    is_jeans = is_bottom_jeans(garment)
    is_pants = is_bottom_pants(garment)
    is_skirt = is_bottom_skirt(garment)
    
    bonus = 0

    if activity == "caminar":
        if is_jeans:
            bonus += 10

        if is_pants:
            bonus += 6

        if rain and is_jeans:
            bonus += 8

    if temp <= 10:
        if is_jeans:
            bonus += 6

        if is_pants:
            bonus += 4

    if occasion == "casual" and mood in ["relajado", "comodo"]:
        if is_jeans:
            bonus += 6
    
    if occasion == "casual" and mood == "urbano":
        if is_jeans:
            bonus += 10

        if is_pants:
            bonus += 6
    
    if occasion == "trabajo" and mood == "urbano":
        if is_jeans:
            bonus += 12

        if is_pants:
            bonus += 4
    
    if occasion == "trabajo" and mood == "elegante":
        if is_pants:
            bonus += 10
        if is_skirt:
            bonus += 6
    
    if occasion == "trabajo" and mood == "sexy" and is_skirt:
        bonus += 6
    
    return bonus


# =========================================================
# ONE PIECE
# =========================================================

def one_piece_context_penalty(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "one_piece":
        return 0

    penalty = 0

    if occasion in ["matrimonio", "gala"]:
        if garment_has_style(garment, "casual"):
            penalty += 12
        if garment_has_style(garment, "sport"):
            penalty += 20
        if garment.dress_level == "relajado":
            penalty += 18

    if occasion == "trabajo":
        if garment_has_style(garment, "sport"):
            penalty += 12

    if occasion == "salida nocturna":
        if garment_has_style(garment, "sport"):
            penalty += 12

    if mood == "urbano":
        if garment_has_style(garment, "formal") and not garment_has_style(garment, "urbano"):
            penalty += 8

    if temp <= 10 and garment.warmth == "caluroso":
        penalty += 8

    if temp >= 26 and garment.warmth == "frio":
        penalty += 10

    if garment.category == "one_piece":
        if occasion == "casual" and mood == "elegante":
            if garment.dress_level == "elegante":
                penalty += 18

    return penalty
#---------------------------------------------------------------

def one_piece_context_bonus(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "one_piece":
        return 0

    bonus = 0

    if occasion in ["matrimonio", "gala"]:
        if garment_has_style(garment, "elegante") or garment_has_style(garment, "formal"):
            bonus += 12

        if garment.dress_level == "elegante":
            bonus += 10
        elif garment.dress_level == "arreglado":
            bonus += 6

    if occasion == "matrimonio":
        if garment_has_style(garment, "elegante") or garment_has_style(garment, "formal"):
            bonus += 12

        if garment.dress_level == "elegante":
            bonus += 8
        elif garment.dress_level == "arreglado":
            bonus += 4

    if occasion == "cita":
        if garment_has_style(garment, "elegante"):
            bonus += 6
        if garment.dress_level in ["arreglado", "elegante"]:
            bonus += 4

    if occasion == "salida nocturna":
        if garment_has_style(garment, "elegante"):
            bonus += 6
        if garment_has_style(garment, "urbano"):
            bonus += 4

    if occasion == "trabajo":
        if garment_has_style(garment, "formal") or garment_has_style(garment, "elegante"):
            bonus += 5

    if mood == "elegante":
        if garment_has_style(garment, "elegante") or garment_has_style(garment, "formal"):
            bonus += 8

    if mood == "sexy":
        if garment.sexiness >= 2:
            bonus += 4

    if mood == "relajado":
        if garment_has_style(garment, "casual"):
            bonus += 4

    if mood == "urbano":
        if garment_has_style(garment, "urbano"):
            bonus += 5

    if temp >= 24:
        if garment.warmth == "caluroso":
            bonus += 5
        elif garment.warmth == "medio":
            bonus += 2

    subcategory = getattr(garment, "subcategory", None)
    if subcategory in ["vestido_elegante", "vestido_coctel"]:
        occasion_match = occasion in ["cita", "salida nocturna"]
        mood_match = mood in ["elegante", "sexy"]
        if occasion_match and mood_match:
            bonus += 25
        elif occasion_match and mood not in ["comodo", "relajado"]:
            bonus += 12
        if mood_match:
            bonus += 20

    return bonus


# =========================================================
# SHOES
# =========================================================

def shoe_context_penalty(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "shoes":
        return 0

    is_heel = is_shoe_heel(garment)
    is_boot_like = is_shoe_boot_like(garment)
    is_sneaker_like = is_shoe_sneaker_like(garment)

    is_very_formal = (
        garment_has_style(garment, "formal")
        or garment_has_style(garment, "elegante")
        or garment.dress_level == "elegante"
    )

    is_casual_friendly = (
        garment_has_style(garment, "casual")
        or garment_has_style(garment, "urbano")
        or garment_has_style(garment, "sport")
        or is_sneaker_like
        or is_boot_like
    )

    penalty = 0

    if occasion == "casual":
        if is_heel:
            penalty += 30

        if mood == "relajado" and is_heel:
            penalty += 20

        if mood == "relajado" and is_very_formal and not is_casual_friendly:
            penalty += 18

        if activity == "normal" and is_very_formal and not is_casual_friendly:
            penalty += 10

        if mood == "urbano" and garment_has_style(garment, "sport") and not garment_has_style(garment, "urbano"):
            penalty += 8

        if mood == "urbano" and activity == "normal" and garment_has_style(garment, "sport") and not garment_has_style(garment, "urbano"):
            penalty += 4

        if mood == "sexy" and is_sneaker_like:
            penalty += 10

    if occasion == "trabajo" and mood == "elegante":
        if is_sneaker_like:
            penalty += 10

    if occasion == "trabajo" and is_sneaker_like:
        penalty += 25

    if occasion == "trabajo" and mood == "sexy" and is_sneaker_like:
        penalty += 10
    
    if activity in ["caminar", "normal"]:
        if is_heel:
            if occasion in ["matrimonio", "gala"]:
                penalty += 5
            elif occasion == "trabajo" and mood in ["elegante", "formal"] and activity == "normal":
                penalty += 14
            else:
                penalty += 25

        if rain and is_heel:
            penalty += 20

        if rain and is_sneaker_like:
            penalty += 8

        if temp <= 10 and is_sneaker_like:
            penalty += 4

    if rain:
        if is_heel:
            penalty += 20
        elif is_very_formal and not is_casual_friendly:
            penalty += 10

        if is_sneaker_like:
            penalty += 6

    if temp <= 10:
        if is_heel:
            penalty += 10
        elif is_very_formal and not is_casual_friendly:
            penalty += 6

        if is_sneaker_like:
            penalty += 4

        if temp <= 10 and occasion == "casual" and mood == "elegante":
            if is_sneaker_like:
                penalty += 6

    if mood == "sexy" and rain and temp <= 10:
        if is_sneaker_like:
            penalty += 18

    if is_boot_like and rain and activity in ["caminar", "normal"]:
        penalty -= 8

    if is_boot_like and temp <= 10:
        penalty -= 4

    if occasion in ["cita", "matrimonio", "gala"]:
        if is_boot_like and garment_has_style(garment, "sport"):
            penalty += 12

    if occasion == "salida nocturna":
        if is_boot_like and mood in ["elegante", "sexy"] and not garment_has_style(garment, "urbano") and not garment_has_style(garment, "elegante"):
            penalty += 10

        if is_sneaker_like:
            if mood in ["elegante", "sexy"]:
                penalty += 22
            elif mood in ["urbano", "comodo"]:
                penalty += 8
            else:
                penalty += 14

            if is_sneaker_like and not garment_has_style(garment, "urbano"):
                penalty += 6

            if garment_has_style(garment, "sport") and mood in ["elegante", "sexy", "formal"]:
                penalty += 10

    if occasion in ["matrimonio", "gala"]:
        if is_sneaker_like:
            penalty += 25

        if is_boot_like:
            penalty += 28

        if is_boot_like and not (
            garment_has_style(garment, "elegante") or garment_has_style(garment, "formal")
        ):
            penalty += 14

        if is_boot_like and (
            garment_has_style(garment, "elegante") or garment_has_style(garment, "formal")
        ):
            penalty += 8

        if not is_heel and not (
            garment_has_style(garment, "elegante") or garment_has_style(garment, "formal")
        ):
            penalty += 10

    if occasion == "trabajo" and mood == "urbano":

        if is_heel:
            penalty += 18
            if temp >= 24:
                penalty += 18
        
        if is_boot_like and garment_has_style(garment, "elegante"):
            penalty += 6

        if is_sneaker_like:
            penalty -= 10
    
    if occasion == "trabajo" and mood == "sexy":
        if is_sneaker_like:
            if garment_has_style(garment, "sport"):
                penalty += 22
            else:
                penalty += 14

    if temp >= 24:
        if is_boot_like:
            penalty += 30

            if occasion == "trabajo" and mood == "urbano":
                penalty += 12

    return max(penalty, 0)

#---------------------------------------------------------------

def shoe_context_bonus(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "shoes":
        return 0

    bonus = 0
    is_boot_like = is_shoe_boot_like(garment)
    is_heel = is_shoe_heel(garment)
    is_sneaker_like = is_shoe_sneaker_like(garment)

    if is_boot_like and rain:
        bonus += 4

    if is_boot_like and temp <= 10:
        bonus += 3

    if occasion == "salida nocturna":
        if garment_has_style(garment, "urbano"):
            bonus += 3
        if garment_has_style(garment, "elegante"):
            bonus += 3

        if mood in ["elegante", "sexy"] and is_boot_like and not garment_has_style(garment, "elegante"):
            bonus -= 3

    if occasion in ["matrimonio", "gala"]:
        if garment_has_style(garment, "elegante") or garment_has_style(garment, "formal"):
            bonus += 12

        if is_heel:
            bonus += 10

        if not is_boot_like and not is_sneaker_like and (
            garment_has_style(garment, "elegante") or garment_has_style(garment, "formal")
        ):
            bonus += 8

    if occasion in ["cita", "salida nocturna"]:
        subcategory = getattr(garment, "subcategory", None)
        if subcategory in ["taco_alto", "taco_bajo", "sandalia"]:
            bonus += 35
        elif subcategory == "mocasin":
            bonus -= 20

    if is_shoe_ballet_flat(garment):
        if occasion in ["cita", "salida nocturna"]:
            bonus += 6
        if occasion == "trabajo" and mood in ["elegante", "formal"]:
            bonus += 5
        if mood == "comodo":
            bonus += 8

    return bonus

# =========================================================
# MIDLAYER
# =========================================================

def midlayer_context_penalty(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "midlayer":
        return 0

    penalty = 0

    if temp >= 26:
        penalty += 25

    elif temp >= 22:
        if garment.warmth == "frio":
            penalty += 18
        elif garment.warmth == "medio":
            penalty += 10

    if occasion in ["gala", "matrimonio"]:
        if garment_has_style(garment, "sport"):
            penalty += 16

    return penalty
#---------------------------------------------------------------

def midlayer_context_bonus(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "midlayer":
        return 0

    bonus = 0

    if occasion in ["trabajo", "cita", "matrimonio", "gala"]:
        if is_midlayer_formal_friendly(garment):
            bonus += 6

    if temp <= 14:
        if garment.warmth in ["medio", "frio"]:
            bonus += 5

    if occasion == "salida nocturna":
        if garment_has_style(garment, "urbano") or garment_has_style(garment, "elegante"):
            bonus += 4

    return bonus



# =========================================================
# OUTERWEAR
# =========================================================

def outerwear_context_bonus(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "outerwear":
        return 0

    bonus = 0

    if rain and garment.waterproof:
        bonus += 10

    if temp <= 10:
        if garment.warmth == "frio":
            bonus += 8
        elif garment.warmth == "medio":
            bonus += 4

    if occasion in ["trabajo", "cita", "salida nocturna"]:
        if is_outerwear_formal_friendly(garment):
            bonus += 4

            if rain and garment.waterproof:
                bonus += 4

    if rain and garment.waterproof:
        bonus += 12

    if garment.subcategory == "impermeable_deporte":
        if occasion == "deporte":
            bonus += 10
        if activity in ["entrenar", "caminar"] and rain:
            bonus += 8

    # Boost parka abrigada en frío extremo con mood relajado/cómodo
    if (
        garment.subcategory == "parka"
        and garment.warmth == "frio"
        and temp <= 8
        and mood in ["relajado", "comodo"]
        and occasion == "salida nocturna"
    ):
        bonus += 10

    return bonus
#---------------------------------------------------------------

def outerwear_context_penalty(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "outerwear":
        return 0

    penalty = 0

    if occasion in ["matrimonio", "gala"]:
        if is_outerwear_rain_like(garment):
            penalty += 35

        if garment_has_style(garment, "urbano") and garment.dress_level in ["flexible", "relajado"]:
            penalty += 15

    if temp >= 26:
        penalty += 40

    elif temp >= 22:
        if garment.warmth == "frio":
            penalty += 25
        elif garment.warmth == "medio":
            penalty += 16
        else:
            penalty += 10

    if not rain:
        is_rain_functional = garment.subcategory in ["impermeable", "parka"]
        if garment.waterproof and (is_rain_functional or not is_outerwear_formal_friendly(garment)):
            penalty += 18

        if temp >= 16:
            penalty += 12

    is_formal_coat = (
        garment.subcategory in ["abrigo", "trench"]
        and (garment_has_style(garment, "elegante") or garment_has_style(garment, "formal"))
        and garment.dress_level in ["arreglado", "elegante"]
    )

    if is_formal_coat:
        if occasion == "casual" and mood in ["relajado", "comodo", "urbano"]:
            penalty += 28
        if occasion == "trabajo" and mood in ["relajado", "comodo", "urbano"]:
            penalty += 22
        if occasion == "deporte":
            penalty += 40

    if garment.subcategory == "impermeable_deporte":
        if occasion not in ["deporte", "casual"]:
            penalty += 18
        if mood in ["elegante", "formal"]:
            penalty += 15

    return penalty

# =========================================================
# ACCESSORY
# =========================================================

def accessory_context_bonus(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    if garment.category != "accessory":
        return 0

    bonus = 0

    is_scarf = is_accessory_scarf_like(garment)
    is_cap = is_accessory_cap_like(garment)
    is_winter_hat = is_accessory_winter_hat_like(garment)

    is_night_friendly = (
        garment_has_style(garment, "urbano")
        or garment_has_style(garment, "elegante")
        or garment_has_style(garment, "formal")
    )

    if is_scarf:
        if temp <= 10:
            bonus += 8
        elif temp <= 13:
            bonus += 4

        if rain:
            bonus += 2

        if temp >= 18:
            bonus -= 12

    if is_cap:
        if rain:
            bonus += 2
        else:
            bonus += 3

        if mood in ["relajado", "urbano", "comodo"]:
            bonus += 3

        if activity == "caminar":
            bonus += 2

        if occasion == "casual":
            bonus += 4

        if occasion in ["trabajo", "gala", "matrimonio"]:
            bonus -= 12

    if is_winter_hat:
        if temp <= 10:
            bonus += 6
        elif temp <= 13:
            bonus += 3

        if rain:
            bonus += 2

        if temp >= 18:
            bonus -= 12

    if occasion == "salida nocturna":
        if is_night_friendly:
            bonus += 4

        if is_cap and mood not in ["urbano", "relajado"]:
            bonus -= 4

    if occasion == "trabajo" and mood == "sexy":
        if garment_has_style(garment, "elegante") and garment.dress_level in ["arreglado", "elegante"]:
            bonus += 10
    
    if occasion == "cita":
        if is_night_friendly:
            bonus += 3

        if is_cap:
            bonus -= 3

    return bonus


def should_include_accessory(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
    current_combo: List[Garment],
) -> bool:
    if garment.category != "accessory":
        return False

    is_scarf = is_accessory_scarf_like(garment)
    is_cap = is_accessory_cap_like(garment)
    is_winter_hat = is_accessory_winter_hat_like(garment)

    layer_count = sum(
        1 for g in current_combo if g.category in ["midlayer", "outerwear"]
    )

    if len(current_combo) >= 5:
        return False

    if is_scarf:
        if temp >= 18:
            return False
        if temp >= 16 and not rain:
            return False
        return temp <= 13 or rain

    if is_cap:
        if occasion != "casual":
            return False

        if mood not in ["relajado", "urbano", "comodo"]:
            return False

        if temp >= 22:
            return False
        if activity != "caminar" and not rain:
            return False

        if layer_count >= 2:
            return False

        has_sport_bottom = any(
            g.category == "bottom" and garment_has_style(g, "sport")
            for g in current_combo
        )

        has_boot_like_shoes = any(
            g.category == "shoes" and is_shoe_boot_like(g)
            for g in current_combo
        )

        has_rain_outerwear = any(
            g.category == "outerwear" and is_outerwear_rain_like(g)
            for g in current_combo
        )

        if has_sport_bottom and has_boot_like_shoes:
            return False

        if has_sport_bottom and has_rain_outerwear:
            return False

        has_formal_shoes = any(
            g.category == "shoes" and (
                garment_has_style(g, "formal")
                or garment_has_style(g, "elegante")
                or g.dress_level == "elegante"
            )
            for g in current_combo
        )

        has_formal_outerwear = any(
            g.category == "outerwear" and is_outerwear_formal_friendly(g)
            for g in current_combo
        )

        if has_formal_shoes and has_formal_outerwear:
            return False
        return True

    if is_winter_hat:
        if temp >= 18:
            return False
        if temp >= 16 and not rain:
            return False
        return temp <= 12 or rain

    if occasion in ["salida nocturna", "cita", "matrimonio", "gala"]:
        return True
    if occasion == "trabajo" and mood in ["sexy", "elegante"]:
        return True
    
    return False


def accessory_relevance_penalty(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
    current_combo: List[Garment],
) -> int:
    if garment.category != "accessory":
        return 0

    is_scarf = is_accessory_scarf_like(garment)
    is_cap = is_accessory_cap_like(garment)
    is_winter_hat = is_accessory_winter_hat_like(garment)

    has_midlayer = any(g.category == "midlayer" for g in current_combo)
    has_outerwear = any(g.category == "outerwear" for g in current_combo)
    layer_count = sum(
        1 for g in current_combo if g.category in ["midlayer", "outerwear"]
    )

    penalty = 0

    if len(current_combo) >= 5:
        penalty += 18

    if is_scarf:
        if temp >= 18 and not rain:
            penalty += 22
        elif temp >= 15 and not rain:
            penalty += 14
        elif temp >= 13 and not rain:
            penalty += 8

        if has_midlayer and has_outerwear and temp >= 12 and not rain:
            penalty += 10

    if is_cap:
        if temp >= 22:
            penalty += 40
        elif temp >= 16 and not rain:
            penalty += 18

        if occasion in ["trabajo", "gala", "matrimonio"]:
            penalty += 25

        if mood not in ["relajado", "urbano", "comodo"] and activity != "caminar" and not rain:
            penalty += 14

        if layer_count >= 2:
            penalty += 10

        has_formal_outerwear = any(
            g.category == "outerwear" and is_outerwear_formal_friendly(g)
            for g in current_combo
        )

        has_boot_like = any(
            g.category == "shoes" and is_shoe_boot_like(g)
            for g in current_combo
        )

        has_sport_bottom = any(
            g.category == "bottom" and garment_has_style(g, "sport")
            for g in current_combo
        )

        has_sneaker_like = any(
            g.category == "shoes" and is_shoe_sneaker_like(g)
            for g in current_combo
        )

        has_sport_top = any(
            g.category == "top" and garment_has_style(g, "sport")
            for g in current_combo
        )

        if has_formal_outerwear and has_boot_like:
            penalty += 20

        if not has_sport_bottom and not has_sneaker_like and not has_sport_top:
            penalty += 18

        if has_sport_bottom and has_outerwear and not rain:
            penalty += 10

    if is_winter_hat:
        if temp >= 18:
            penalty += 40

    if not is_scarf and not is_cap and not is_winter_hat:
        if occasion not in ["salida nocturna", "cita", "matrimonio", "gala"]:
           if not (occasion == "trabajo" and mood in ["sexy", "elegante"]):
                penalty += 14

        if has_midlayer and has_outerwear:
            penalty += 8

    return penalty

def outfit_accessory_penalty(
    items: List[Garment],
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    accessories = [g for g in items if g.category == "accessory"]

    if not accessories:
        return 0

    penalty = 0

    if len(accessories) > 1:
        penalty += 25 * (len(accessories) - 1)

    # NUEVO: incluso 1 accesorio tiene un costo base
    penalty += 8 * len(accessories)

    non_accessories = [g for g in items if g.category != "accessory"]

    for acc in accessories:
        penalty += accessory_relevance_penalty(
            acc,
            occasion,
            mood,
            activity,
            temp,
            rain,
            non_accessories,
        )

    return penalty

# =========================================================
# AGREGADORES GENERALES POR CATEGORÍA
# =========================================================

def category_context_bonus(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    return (
        top_context_bonus(garment, occasion, mood, activity, temp, rain)
        + bottom_context_bonus(garment, occasion, mood, activity, temp, rain)
        + one_piece_context_bonus(garment, occasion, mood, activity, temp, rain)
        + shoe_context_bonus(garment, occasion, mood, activity, temp, rain)
        + midlayer_context_bonus(garment, occasion, mood, activity, temp, rain)
        + outerwear_context_bonus(garment, occasion, mood, activity, temp, rain)
        + accessory_context_bonus(garment, occasion, mood, activity, temp, rain)
    )


def category_context_penalty(
    garment: Garment,
    occasion: str,
    mood: str,
    activity: str,
    temp: int,
    rain: bool,
) -> int:
    return (
        top_context_penalty(garment, occasion, mood, activity, temp, rain)
        + bottom_context_penalty(garment, occasion, mood, activity, temp, rain)
        + one_piece_context_penalty(garment, occasion, mood, activity, temp, rain)
        + shoe_context_penalty(garment, occasion, mood, activity, temp, rain)
        + midlayer_context_penalty(garment, occasion, mood, activity, temp, rain)
        + outerwear_context_penalty(garment, occasion, mood, activity, temp, rain)
    )