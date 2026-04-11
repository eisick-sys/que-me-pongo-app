#occasion_rules.py
from models import Garment
from utils.garment_utils import all_styles, garment_has_style


def get_weather_tag(temp: int, rain: bool) -> str:
    if rain:
        return "lluvia"
    if temp <= 10:
        return "frio"
    if temp <= 20:
        return "templado"
    return "calor"


def build_required_categories(occasion: str, rain: bool = False, temp: int = 15):
    rules = {
        "deporte": {
            "required": ["top", "bottom", "shoes"],
            "optional": [],
        },
        "casual": {
            "required": ["top", "bottom", "shoes"],
            "optional": ["midlayer", "outerwear", "accessory"],
        },
        "trabajo": {
            "required": ["top", "bottom", "shoes"],
            "optional": ["midlayer", "outerwear", "accessory"],
        },
        "cita": {
            "required": ["top", "bottom", "shoes"],
            "optional": ["midlayer", "outerwear", "accessory"],
        },
        "salida nocturna": {
            "required": ["top", "bottom", "shoes"],
            "optional": ["midlayer", "outerwear", "accessory"],
        },
        "matrimonio": {
            "required": ["top", "bottom", "shoes"],
            "optional": ["accessory", "outerwear"],
        },
        "gala": {
            "required": ["top", "bottom", "shoes"],
            "optional": ["accessory", "outerwear"],
        },
    }

    base = rules.get(occasion, rules["casual"])

    required = list(base["required"])
    optional = list(base["optional"])

    if occasion == "deporte" and (rain or temp <= 12):
        if "outerwear" not in required:
            required.append("outerwear")

    if rain:
        if occasion not in ["gala", "matrimonio"]:
            if "outerwear" not in required:
                required.append("outerwear")
            if "outerwear" in optional:
                optional.remove("outerwear")

    return {
        "required": required,
        "optional": optional,
    }


def is_animal_print(garment: Garment) -> bool:
    pattern = str(getattr(garment, "pattern", "liso") or "").strip().lower()
    return any(x in pattern for x in ["animal", "leop", "zebr", "cebr"])


def garment_allowed_for_occasion(garment: Garment, occasion: str, rain: bool = False, mood: str = "", temp: int = 15):
    garment_styles = all_styles(garment)
    lower_name = garment.name.lower()

    # =========================================================
    # REGLAS GLOBALES (aplican a todas las ocasiones)
    # =========================================================

    blocked_by_occasion = {
        "matrimonio": ["relajado"],
        "gala": ["relajado"],
        "trabajo": [],
        "cita": [],
        "casual": [],
        "salida nocturna": [],
        "deporte": ["arreglado", "elegante"],
    }

    if garment.dress_level in blocked_by_occasion.get(occasion, []):
        return False, f"No te recomiendo usar {garment.name} para {occasion}."

    if garment.category == "bottom":
        if any(x in lower_name for x in ["short", "shorts", "mini", "minifalda"]):
            if rain:
                return False, f"{garment.name} no es adecuada para lluvia."
            if temp <= 10:
                return False, f"{garment.name} no es adecuada para este frío."

    # =========================================================
    # MATRIMONIO Y GALA
    # =========================================================

    if occasion in ["matrimonio", "gala"]:
        if garment.category == "outerwear":
            if any(x in lower_name for x in ["impermeable", "parka", "rain", "agua"]):
                if garment_has_style(garment, "sport") or garment.dress_level in ["relajado", "flexible"]:
                    return False, f"No te recomiendo usar {garment.name} para {occasion}."

        if garment.category == "bottom":
            if any(x in lower_name for x in ["short", "shorts"]):
                return False, f"{garment.name} no va con un {occasion}."
            if any(x in lower_name for x in ["buzo", "jogger", "joggers"]):
                return False, f"{garment.name} no va con un {occasion}."
            if "jean" in lower_name or "jeans" in lower_name:
                return False, f"{garment.name} no va con un {occasion}."

        if garment.category == "shoes":
            if "zapatilla" in lower_name:
                return False, f"{garment.name} no va con un {occasion}."

        if garment.category == "accessory":
            if any(x in lower_name for x in ["gorro", "beanie", "lana", "gorra", "jockey"]):
                return False, f"{garment.name} no va con un {occasion}."

        if "sport" in garment_styles:
            return False, f"{garment.name} no va con un {occasion} porque es demasiado sport."

    # =========================================================
    # TRABAJO
    # =========================================================

    if occasion == "trabajo":
        if garment.category == "bottom":
            if any(x in lower_name for x in ["mini", "minifalda"]) and garment.sexiness >= 3:
                return False, f"{garment.name} puede ser demasiado atrevida para trabajo — pero tú decides."

        if "sport" in garment_styles and garment.category != "shoes":
            return False, f"{garment.name} no es ideal para trabajo."

        if garment.category in ["top", "bottom", "midlayer", "outerwear", "one_piece"]:
            if is_animal_print(garment):
                return False, f"{garment.name} no es adecuada para trabajo formal."

        if occasion == "trabajo" and mood == "comodo":
            if garment.dress_level == "elegante" and garment.category == "one_piece":
                return False, f"{garment.name} es demasiado elegante para un día cómodo de trabajo."

    # =========================================================
    # CITA
    # =========================================================

    if occasion == "cita" and mood != "urbano":
        if garment.category == "bottom":
            if any(x in lower_name for x in ["buzo", "jogger", "joggers"]):
                return False, f"{garment.name} no va para una cita."

        if garment.category == "shoes":
            if any(x in lower_name for x in ["zapatilla deporte", "zapatillas deporte", "running", "training"]):
                return False, f"{garment.name} no va para una cita."

    # =========================================================
    # DEPORTE
    # =========================================================

    if occasion == "deporte":
        if garment.category in ["top", "bottom", "shoes", "one_piece"]:
            if "sport" not in garment_styles:
                return False, f"{garment.name} no es adecuada para deporte."

    # =========================================================
    # SALIDA NOCTURNA
    # =========================================================

    if occasion == "salida nocturna":
        if "sport" in garment_styles and garment.category != "shoes":
            return False, f"{garment.name} es demasiado sport para salida nocturna."

        if garment.category == "shoes":
            if (
                "zapatilla" in lower_name
                or "sneaker" in lower_name
                or "sport" in garment_styles
            ):
                return False, f"{garment.name} no va con una salida nocturna."

    return True, ""
