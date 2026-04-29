#attribute_inference.py
import os
import re
import unicodedata
from typing import Dict, Optional

from constants import (
    CATEGORY_OPTIONS,
    COLOR_ALIASES,
    COLOR_OPTIONS,
    PATTERN_OPTIONS,
    ACCESSORY_TYPE_OPTIONS,
    SUBCATEGORY_OPTIONS,
)


def normalize_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


def infer_color_from_name(name: str) -> Optional[str]:
    text = normalize_text(name)

    alias_map = {
        normalize_text(alias): value
        for alias, value in COLOR_ALIASES.items()
    }

    color_map = {
        normalize_text(color): color
        for color in COLOR_OPTIONS
    }

    # Buscar primero aliases
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if alias in text:
            normalized = alias_map.get(alias)
            if normalized in COLOR_OPTIONS:
                return normalized

    # Luego colores oficiales
    for normalized_color in sorted(color_map.keys(), key=len, reverse=True):
        if normalized_color in text:
            return color_map[normalized_color]

    return None


def infer_pattern_from_name(name: str) -> Optional[str]:
    text = normalize_text(name)

    pattern_keywords = {
        "animal_print": [
            "animal print", "animal", "leopardo", "leopard", "zebra", "cebra",
            "snake", "serpiente", "piton", "vaca"
        ],
        "floral": [
            "floral", "floreada", "flores", "flower"
        ],
        "rayas": [
            "rayas", "rayada", "rayado", "striped", "stripe"
        ],
        "cuadros": [
            "cuadros", "cuadrille", "cuadriculado", "tartan", "plaid"
        ],
        "grafico": [
            "grafico", "formas", "estampado grafico", "dibujos"
        ],
        "estampado": [
            "estampado", "estampada"
        ],
        "lunares": [
            "lunares", "lunar", "puntos", "polka", "polka dot", "dots"
        ],
        "liso": [
            "liso", "lisa", "basica", "basico"
        ],
    }

    for pattern, keywords in pattern_keywords.items():
        if pattern not in PATTERN_OPTIONS:
            continue
        for keyword in keywords:
            if normalize_text(keyword) in text:
                return pattern

    return None


def infer_category_from_name(name: str) -> Optional[str]:
    text = normalize_text(name)

    category_keywords = {
        "one_piece": [
            "vestido", "enterito", "mono", "jumpsuit", "overall"
        ],
        "top": [
            "polera", "camiseta", "remera", "top", "blusa", "camisa",
            "body", "crop top", "beatle", "tank", "musculosa", "peto"
        ],
        "midlayer": [
            "blazer", "cardigan", "chaleco", "sweater", "sueter",
            "tejido", "hoodie", "polar", "camisón", "camison",
        ],
        "outerwear": [
            "chaqueta", "abrigo", "parka", "impermeable", "trench",
            "cortaviento", "anorak", "poncho"
        ],
        "bottom": [
            "jeans", "pantalon", "falda", "short", "shorts",
            "calza", "leggings", "legging", "buzo", "palazzo", "mini", "minifalda",
            "jardinera", "overol",
        ],
        "shoes": [
            "zapatillas", "zapatilla", "zapatos", "zapato", "botines",
            "botin", "botas", "bota", "sandalias", "sandalia",
            "mocasines", "mocasin", "tacos", "taco", "mocasin",
            "stiletto", "stilettos", "ballarina", "ballerina", "balerina", "ballet",
        ],
        "accessory": [
            "reloj", "collar", "pulsera", "anillo", "aros", "cinturon",
            "bolso", "cartera", "bufanda", "panuelo",
            "gorro", "guantes", "lentes", "jockey", "gorra", "cap", "visera"
        ],
    }

    for category, keywords in category_keywords.items():
        if category not in CATEGORY_OPTIONS:
            continue
        for keyword in keywords:
            if normalize_text(keyword) in text:
                return category

    return None


def infer_subcategory_from_name(name: str, category: Optional[str] = None) -> Optional[str]:
    text = normalize_text(name)

    subcategory_keywords = {
        "top": {
            "polera_deporte": ["polera deporte", "polera deportiva", "camiseta deporte", "camiseta deportiva", "running top", "dry fit", "dri fit"],
            "polera": ["polera", "camiseta", "remera", "t-shirt"],
            "blusa": ["blusa"],
            "camisa": ["camisa"],
            "top": ["top"],
            "body": ["body"],
            "crop_top": ["crop top", "crop"],
            "peto": ["peto"],
        },
        "midlayer": {
            "sweater": ["sweater", "sueter"],
            "cardigan": ["cardigan"],
            "chaleco": ["chaleco", "chaleca"],
            "blazer": ["blazer"],
            "hoodie": ["hoodie"],
            "polar": ["polar"],
            "camisón": ["camisón", "camison", "camiseta larga"],
        },
        "outerwear": {
            "chaqueta": ["chaqueta"],
            "abrigo": ["abrigo"],
            "parka": ["parka"],
            "trench": ["trench"],
            "impermeable_deporte": ["impermeable deporte", "impermeable deportivo", "cortaviento deporte", "cortaviento deportivo", "rain jacket", "running jacket"],
            "impermeable": ["impermeable", "cortaviento"],
            "poncho": ["poncho"],
            "bolero": ["bolero"],
        },
        "bottom": {
            # más específicas primero para que no caigan en el fallback
            "falda_corta": ["minifalda", "falda corta", "mini"],
            "falda_larga": ["falda larga", "maxi falda", "maxi"],
            "falda_midi": ["falda midi", "midi falda", "falda"],  # fallback genérico
            "short_elegante": ["short elegante", "short formal"],
            "short_casual": ["short", "shorts"],  # fallback genérico
            "jeans": ["jeans", "jean", "denim", "bluejeans"],
            "pantalon": ["pantalon"],
            "legging": ["legging", "leggings", "calza", "calzas"],
            "buzo": ["buzo", "jogging", "pantalon de buzo"],
            "jogger": ["jogger", "joggers"],
            "jardinera": ["jardinera", "overol peto", "peto jardinero"],
        },
        "one_piece": {
            "vestido_elegante": ["vestido elegante", "vestido formal", "vestido de noche"],
            "vestido_coctel": ["vestido coctel", "vestido cóctel", "vestido fiesta", "coctel"],
            "vestido_casual": ["vestido casual", "vestido basico", "vestido"],  # fallback genérico
            "enterito": ["enterito", "mono", "jumpsuit", "overall"],
        },
        "shoes": {
            # más específicas primero
            "zapatilla_deporte": ["zapatilla deporte", "zapatillas deporte", "running", "training"],
            "zapatilla_urbana": ["zapatilla", "zapatillas", "sneaker", "sneakers"],  # fallback genérico
            "zapato": ["zapato", "zapatos"],
            "botin": ["botin", "botines"],
            "bota": ["bota", "botas"],
            "sandalia": ["sandalia", "sandalias"],
            "taco_bajo": ["taco bajo", "kitten heel", "kitten", "tacón bajo"],
            "taco_alto": ["taco", "tacos", "tacon", "tacones", "heel", "heels", "stiletto", "stilettos"],
            "ballarina": ["ballarina", "ballerina", "balerina", "zapato ballet", "ballet flat"],
            "mocasin": ["mocasin", "mocasines", "loafer", "loafers"],
        },
        "accessory": {
            "reloj": ["reloj"],
            "collar": ["collar"],
            "pulsera": ["pulsera", "brazalete"],
            "anillo": ["anillo"],
            "aros": ["aros", "aretes"],
            "cinturon": ["cinturon", "cinturón"],
            "bolso": ["bolso", "bolsa"],
            "cartera": ["cartera"],
            "bufanda": ["bufanda"],
            "pañuelo": ["panuelo", "pañuelo"],
            "gorro": ["gorro", "beanie", "jockey", "gorra", "cap", "visera"],
            "guantes": ["guantes", "guante"],
        },
    }

    categories_to_check = [category] if category else list(subcategory_keywords.keys())

    for current_category in categories_to_check:
        if current_category not in subcategory_keywords:
            continue

        valid_subcategories = SUBCATEGORY_OPTIONS.get(current_category, [])

        for subcategory, keywords in subcategory_keywords[current_category].items():
            if subcategory not in valid_subcategories:
                continue
            for keyword in keywords:
                if normalize_text(keyword) in text:
                    return subcategory

    return None


def infer_accessory_type_from_name(name: str) -> Optional[str]:
    text = normalize_text(name)

    mapping = {
        "reloj": ["reloj"],
        "collar": ["collar"],
        "pulsera": ["pulsera", "brazalete"],
        "anillo": ["anillo"],
        "aros": ["aros", "aretes"],
        "cinturón": ["cinturon"],
        "bolso/cartera": ["bolso", "cartera"],
        "bufanda": ["bufanda"],
        "pañuelo": ["pañuelo", "panuelo"],
        "gorro": ["gorro", "beanie"],
        "guantes": ["guantes", "guante"],
    }

    for accessory_type, keywords in mapping.items():
        if accessory_type not in ACCESSORY_TYPE_OPTIONS:
            continue
        for keyword in keywords:
            if normalize_text(keyword) in text:
                return accessory_type

    return None


def infer_waterproof_from_name(name: str) -> Optional[bool]:
    text = normalize_text(name)

    waterproof_keywords = [
        "impermeable", "waterproof", "rain", "lluvia", "cortaviento"
    ]

    for keyword in waterproof_keywords:
        if normalize_text(keyword) in text:
            return True

    return None


def infer_warmth_from_name(name: str) -> Optional[str]:
    text = normalize_text(name)

    cold_keywords = [
        "abrigo", "parka", "polar", "poncho", "bufanda", "guantes", "gorro",
        "sweater grueso", "chaleco grueso", "lana"
    ]
    hot_keywords = [
        "polera", "top", "crop top", "musculosa", "tank", "short", "shorts"
    ]

    for keyword in cold_keywords:
        if normalize_text(keyword) in text:
            return "frio"

    for keyword in hot_keywords:
        if normalize_text(keyword) in text:
            return "caluroso"

    return None


def infer_attributes_from_subcategory(subcategory: str, current_attrs: dict) -> dict:
    """
    Complementa atributos inferidos aplicando reglas deterministas por subcategoría.
    Solo sobreescribe si el atributo no fue inferido por nombre (es None).
    """
    result = dict(current_attrs)

    warmth_map = {
        "parka": "frio",
        "abrigo": "frio",
        "polar": "frio",
        "poncho": "frio",
        "sweater": "frio",
        "cardigan": "medio",
        "chaleco": "medio",
        "blazer": "medio",
        "hoodie": "medio",
        "chaqueta": "medio",
        "trench": "medio",
        "impermeable": "medio",
        "impermeable_deporte": "medio",
        "polera": "caluroso",
        "polera_deporte": "caluroso",
        "top": "caluroso",
        "blusa": "caluroso",
        "camisa": "caluroso",
        "body": "caluroso",
        "crop_top": "caluroso",
        "sandalia": "caluroso",
        "taco_alto": "caluroso",
        "taco_bajo": "caluroso",
        "falda_corta": "caluroso",
        "short_casual": "caluroso",
        "short_elegante": "caluroso",
        "jardinera": "caluroso",
        "camisón": "medio",
        "ballarina": "caluroso",
    }

    dress_level_map = {
        "vestido_elegante": "elegante",
        "vestido_coctel": "elegante",
        "blazer": "arreglado",
        "trench": "arreglado",
        "falda_midi": "arreglado",
        "vestido_casual": "flexible",
        "camisa": "flexible",
        "pantalon": "flexible",
        "botin": "flexible",
        "zapato": "flexible",
        "mocasin": "flexible",
        "impermeable_deporte": "relajado",
        "buzo": "relajado",
        "jogger": "relajado",
        "hoodie": "relajado",
        "polar": "relajado",
        "zapatilla_urbana": "relajado",
        "zapatilla_deporte": "relajado",
        "short_casual": "relajado",
        "legging": "relajado",
        "gorro": "relajado",
        "jardinera": "relajado",
        "camisón": "relajado",
        "ballarina": "flexible",
    }

    sexiness_map = {
        "vestido_coctel": 2,
        "vestido_elegante": 1,
        "taco_alto": 1,
        "crop_top": 1,
        "falda_corta": 1,
    }

    style_map = {
        "vestido_elegante": "elegante",
        "vestido_coctel": "elegante",
        "blazer": "formal",
        "trench": "formal",
        "polera_deporte": "sport",
        "impermeable_deporte": "sport",
        "buzo": "sport",
        "jogger": "sport",
        "polar": "sport",
        "zapatilla_deporte": "sport",
        "hoodie": "casual",
        "jardinera": "casual",
        "camisón": "casual",
    }

    if subcategory:
        if result.get("warmth") is None and subcategory in warmth_map:
            result["warmth"] = warmth_map[subcategory]

        if result.get("dress_level") is None and subcategory in dress_level_map:
            result["dress_level"] = dress_level_map[subcategory]

        if result.get("sexiness") is None and subcategory in sexiness_map:
            result["sexiness"] = sexiness_map[subcategory]

        if result.get("style") is None and subcategory in style_map:
            result["style"] = style_map[subcategory]

    return result


def infer_style_from_name(name: str) -> Optional[str]:
    text = normalize_text(name)

    style_keywords = {
        "elegante": ["elegante", "formal", "vestir", "fino", "fina", "gala", "de gala", "coctel", "de noche", "noche elegante"],
        "formal": ["formal", "traje", "sastre"],
        "urbano": ["urbano", "urbana", "street", "streetwear"],
        "sport": ["sport", "deportivo", "deportiva", "running", "training", "gym"],
        "casual": ["casual", "diario", "everyday"],
    }

    for style, keywords in style_keywords.items():
        for keyword in keywords:
            if normalize_text(keyword) in text:
                return style

    return None


def infer_attributes_from_name(name: str) -> Dict[str, Optional[object]]:
    inferred_category = infer_category_from_name(name)
    inferred_accessory_type = infer_accessory_type_from_name(name)

    # Si se detecta tipo de accesorio, reforzar categoría
    if inferred_accessory_type:
        inferred_category = "accessory"

    inferred_subcategory = infer_subcategory_from_name(name, inferred_category)

    result = {
        "category": inferred_category,
        "subcategory": inferred_subcategory,
        "pattern": infer_pattern_from_name(name),
        "color": infer_color_from_name(name),
        "waterproof": infer_waterproof_from_name(name),
        "warmth": infer_warmth_from_name(name),
        "accessory_type": inferred_accessory_type,
        "dress_level": None,
        "sexiness": None,
        "style": infer_style_from_name(name),
    }

    # Aplicar inferencia cruzada por subcategoría
    inferred_subcategory = result.get("subcategory") or inferred_subcategory
    if inferred_subcategory:
        result = infer_attributes_from_subcategory(inferred_subcategory, result)

    # Inferencia cruzada: dress_level desde estilo cuando no fue inferido por subcategoría
    if result.get("dress_level") is None:
        inferred_style = result.get("style")
        if inferred_style == "elegante":
            result["dress_level"] = "arreglado"
        elif inferred_style == "formal":
            result["dress_level"] = "arreglado"
    elif result.get("dress_level") == "flexible" and result.get("style") == "elegante":
        result["dress_level"] = "arreglado"

    return result


def suggest_name_from_filename(filename: str) -> str:
    if not filename:
        return ""

    name = filename.lower()

    # quitar extensión
    name = os.path.splitext(name)[0]

    # reemplazar separadores por espacio
    name = re.sub(r"[_\-]+", " ", name)

    # limpiar patrones típicos tipo IMG_1234
    name = re.sub(r"\bimg\s*\d+\b", "", name)
    name = re.sub(r"\b\d{3,}\b", "", name)

    name = name.strip()

    # fallback
    if len(name) < 3:
        return ""

    return name