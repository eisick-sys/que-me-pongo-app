#garments_utils.py
from typing import List

from models import Garment


# =========================================================
# ESTILOS
# =========================================================

def all_styles(garment: Garment) -> List[str]:
    styles = [garment.style]
    if garment.secondary_styles:
        styles.extend(garment.secondary_styles)
    return styles


def garment_has_style(garment: Garment, style: str) -> bool:
    return style in all_styles(garment)


# =========================================================
# DETECTORES DE PRENDAS
# =========================================================

def is_shoe_heel(garment: Garment) -> bool:
    sub = getattr(garment, "subcategory", None)
    if sub in ["taco_bajo", "taco_alto"]:
        return True
    name = garment.name.lower()
    return any(x in name for x in ["taco", "tacón", "heel", "heels", "stiletto"])


def is_shoe_high_heel(garment: Garment) -> bool:
    """Taco alto específicamente (stiletto, 7cm+)."""
    sub = getattr(garment, "subcategory", None)
    if sub == "taco_alto":
        return True
    if sub == "taco_bajo":
        return False
    name = garment.name.lower()
    return any(x in name for x in ["taco", "tacón", "heel", "heels", "stiletto"])


def is_shoe_low_heel(garment: Garment) -> bool:
    """Taco bajo específicamente (kitten heel, 3-5cm)."""
    sub = getattr(garment, "subcategory", None)
    return sub == "taco_bajo"


def is_shoe_boot_like(garment: Garment) -> bool:
    sub = getattr(garment, "subcategory", None)
    if sub in ["botin", "bota"]:
        return True
    name = garment.name.lower()
    return any(x in name for x in ["bota", "botín", "botin", "bototo"])


def is_shoe_sneaker_like(garment: Garment) -> bool:
    sub = getattr(garment, "subcategory", None)
    if sub in ["zapatilla_urbana", "zapatilla_deporte"]:
        return True
    name = garment.name.lower()
    return any(x in name for x in ["zapatilla", "sneaker", "converse"])


def is_shoe_sport_sneaker(garment: Garment) -> bool:
    """Zapatilla de deporte específicamente (running, training)."""
    sub = getattr(garment, "subcategory", None)
    if sub == "zapatilla_deporte":
        return True
    if sub == "zapatilla_urbana":
        return False
    name = garment.name.lower()
    return any(x in name for x in ["zapatilla deporte", "zapatillas deporte", "running", "training"])


def is_bottom_skirt(garment: Garment) -> bool:
    sub = getattr(garment, "subcategory", None)
    if sub in ["falda_corta", "falda_midi", "falda_larga"]:
        return True
    name = garment.name.lower()
    return any(x in name for x in ["falda", "skirt", "mini", "midi"])


def is_bottom_short_or_light(garment: Garment) -> bool:
    """Falda corta (mini) o short — prendas que exponen las piernas."""
    sub = getattr(garment, "subcategory", None)
    if sub in ["falda_corta", "short_casual", "short_elegante"]:
        return True
    name = garment.name.lower()
    return any(x in name for x in ["mini", "corta", "short", "shorts"])


def is_bottom_short(garment: Garment) -> bool:
    """Short (no falda)."""
    sub = getattr(garment, "subcategory", None)
    if sub in ["short_casual", "short_elegante"]:
        return True
    if sub in ["falda_corta", "falda_midi", "falda_larga"]:
        return False
    name = garment.name.lower()
    return any(x in name for x in ["short", "shorts"])


def is_bottom_jeans(garment: Garment) -> bool:
    name = garment.name.lower()
    return "jean" in name or "denim" in name


def is_bottom_pants(garment: Garment) -> bool:
    name = garment.name.lower()
    return "pantalon" in name or "pantalón" in name


def is_accessory_scarf_like(garment: Garment) -> bool:
    accessory_type = getattr(garment, "accessory_type", None)
    name = garment.name.lower()

    if accessory_type in ["bufanda", "pañuelo"]:
        return True

    return any(x in name for x in ["bufanda", "scarf", "pañuelo"])


def is_accessory_cap_like(garment: Garment) -> bool:
    accessory_type = getattr(garment, "accessory_type", None)
    name = garment.name.lower()

    if accessory_type == "cap":
        return True

    return any(x in name for x in ["jockey", "gorra", "cap"])

def is_accessory_winter_hat_like(garment: Garment) -> bool:
    accessory_type = getattr(garment, "accessory_type", None)
    name = garment.name.lower()

    if accessory_type == "gorro":
        return True

    return any(x in name for x in ["lana", "beanie", "gorro"])


def is_outerwear_rain_like(garment: Garment) -> bool:
    name = garment.name.lower()
    return any(x in name for x in ["impermeable", "parka", "rain", "agua"])


def is_outerwear_formal_friendly(garment: Garment) -> bool:
    return garment_has_style(garment, "formal") or garment_has_style(garment, "elegante")


def is_top_too_sporty(garment: Garment) -> bool:
    name = garment.name.lower()
    styles = all_styles(garment)
    return "sport" in styles or any(x in name for x in ["buzo", "jersey deportivo", "running"])


def is_midlayer_formal_friendly(garment: Garment) -> bool:
    name = garment.name.lower()
    return (
        garment_has_style(garment, "formal")
        or garment_has_style(garment, "elegante")
        or any(x in name for x in ["blazer", "chaleco vestir"])
    )