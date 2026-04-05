# constants.py=============================================
# CATEGORÍAS
# =========================================================

CATEGORY_OPTIONS = ["top", "midlayer", "outerwear", "bottom", "one_piece", "shoes", "accessory"]
CATEGORY_LABELS_ES = {
    "top": "Arriba",
    "midlayer": "Prenda intermedia",
    "outerwear": "Abrigos",
    "bottom": "Abajo",
    "one_piece": "Una pieza",
    "shoes": "Calzado",
    "accessory": "Accesorios",
}

SUBCATEGORY_OPTIONS = {
    "top": [
        "polera",
        "blusa",
        "camisa",
        "top",
        "body",
        "crop_top",
        "peto",
    ],
    "midlayer": [
        "sweater",
        "cardigan",
        "chaleco",
        "blazer",
        "hoodie",
        "polar",
    ],
    "outerwear": [
        "chaqueta",
        "abrigo",
        "parka",
        "trench",
        "impermeable",
        "poncho",
    ],
    "bottom": [
        "jeans",
        "pantalon",
        "falda",
        "short",
        "legging",
    ],
    "one_piece": [
        "vestido",
        "enterito",
    ],
    "shoes": [
        "zapatilla",
        "zapato",
        "botin",
        "bota",
        "sandalia",
        "taco",
        "mocasin",
    ],
    "accessory": [
        "reloj",
        "collar",
        "pulsera",
        "anillo",
        "aros",
        "cinturon",
        "bolso",
        "cartera",
        "bufanda",
        "pañuelo",
        "gorro",
        "guantes",
    ],
}

# =========================================================
# COLORES
# =========================================================

COLOR_OPTIONS = [
    "blanco",
    "negro",

    "gris",
    "gris claro",
    "gris oscuro",

    "azul",
    "azul marino",
    "celeste",

    "verde",
    "verde oliva",
    "verde olivo",
    "verde oscuro",

    "rojo",
    "burdeo",

    "rosado",
    "fucsia",

    "morado",
    "lila",

    "amarillo",
    "mostaza",

    "naranja",

    "café",
    "beige",
    "crema",

    "plateado",
    "dorado",

    "multicolor",
]


# =========================================================
# NORMALIZACIÓN DE COLORES (alias)
# =========================================================

COLOR_ALIASES = {
    "azul oscuro": "azul marino",
    "navy": "azul marino",

    "cafe": "café",
    "café": "café",
    "marron": "café",
    "marrón": "café",
    "brown": "café",

    "bordo": "burdeo",
    "bordó": "burdeo",
    "vino": "burdeo",

    "off white": "crema",
    "off-white": "crema",
    "ivory": "crema",

    "gold": "dorado",
    "silver": "plateado",

    "pink": "rosado",
    "purple": "morado",

    "orange": "naranja",
    "yellow": "amarillo",
    "green": "verde",
    "verde olivo" : "verde oliva",
    "blue": "azul",
    "red": "rojo",
    "white": "blanco",
    "black": "negro",

    "gray": "gris",
    "grey": "gris",
}

# =========================================================
# ESTILOS Y OTROS
# =========================================================

STYLE_OPTIONS = ["casual", "formal", "urbano", "sport", "elegante"]

WARMTH_OPTIONS = ["caluroso", "medio", "frio"]

DRESS_LEVEL_OPTIONS = ["relajado", "flexible", "arreglado", "elegante"]

PATTERN_OPTIONS = [
    "liso",
    "rayas",
    "cuadros",
    "estampado",
    "animal_print",
    "floral",
    "grafico",
]

ACCESSORY_TYPE_OPTIONS = [
    "reloj",
    "collar",
    "pulsera",
    "anillo",
    "aros",
    "cinturón",
    "bolso/cartera",
    "bufanda",
    "pañuelo",
    "gorro",
    "guantes",
]

OCCASION_OPTIONS = [
    "casual",
    "trabajo",
    "cita",
    "salida nocturna",
    "matrimonio",
    "gala",
    "deporte",
]

MOOD_OPTIONS = ["relajado", "urbano", "elegante", "sexy", "comodo"]

ACTIVITY_OPTIONS = ["normal", "caminar", "formal", "entrenar"]

THERMAL_ACCESSORIES = ["bufanda", "pañuelo", "gorro", "guantes"]