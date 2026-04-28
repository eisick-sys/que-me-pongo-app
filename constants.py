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
        "bolero",
    ],
    "bottom": [
        "jeans",
        "pantalon",
        "falda_corta",
        "falda_midi",
        "falda_larga",
        "short_casual",
        "short_elegante",
        "legging",
        "buzo",
        "jogger",
    ],
    "one_piece": [
        "vestido_casual",
        "vestido_elegante",
        "vestido_coctel",
        "enterito",
    ],
    "shoes": [
        "zapatilla_urbana",
        "zapatilla_deporte",
        "zapato",
        "botin",
        "bota",
        "sandalia",
        "taco_bajo",
        "taco_alto",
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
    "verde oliva": "verde olivo",
    "blue": "azul",
    "red": "rojo",
    "white": "blanco",
    "black": "negro",

    "gray": "gris",
    "grey": "gris",

    "blanca": "blanco",
    "negra": "negro",
    "roja": "rojo",
    "rosada": "rosado",
    "morada": "morado",
    "amarilla": "amarillo",

    # Femeninos faltantes
    "dorada": "dorado",
    "plateada": "plateado",

    # Chilenismos y variantes comunes
    "naranjo": "naranja",
    "anaranjado": "naranja",
    "anaranjada": "naranja",
    "salmon": "naranja",
    "salmón": "naranja",
    "coral": "rosado",
    "terracota": "café",
    "tierra": "café",
    "camel": "beige",
    "arena": "beige",
    "tostado": "beige",
    "tostada": "beige",
    "hueso": "crema",
    "nude": "crema",
    "champagne": "crema",
    "perla": "crema",
    "palo de rosa": "rosado",
    "rose": "rosado",
    "magenta": "fucsia",
    "violeta": "morado",
    "lavanda": "lila",
    "lavender": "lila",
    "ciruela": "morado",
    "berenjena": "morado",
    "khaki": "verde olivo",
    "kaki": "verde olivo",
    "militar": "verde olivo",
    "oliva": "verde olivo",
    "ocre": "mostaza",
    "miel": "mostaza",
    "cobre": "dorado",
    "bronce": "dorado",
    "carbon": "gris oscuro",
    "carbón": "gris oscuro",
    "antracita": "gris oscuro",
    "grafito": "gris oscuro",
    "indigo": "azul marino",
    "índigo": "azul marino",
    "cobalto": "azul",
    "petróleo": "azul marino",
    "petroleo": "azul marino",
    "granate": "burdeo",
    "turquesa": "celeste",
    "turquoise": "celeste",
    "aguamarina": "celeste",
}

# =========================================================
# ESTILOS Y OTROS
# =========================================================

STYLE_OPTIONS = ["casual", "formal", "urbano", "sport", "elegante"]

STYLE_LABELS_ES = {
    "casual": "Casual",
    "formal": "Formal",
    "urbano": "Urbano",
    "sport": "Deporte",
    "elegante": "Elegante",
    "mixto": "Mixto",
}

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
    "lunares",
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

MOOD_OPTIONS = ["relajado", "urbano", "elegante", "comodo", "sexy", "formal"]

ACTIVITY_OPTIONS = ["normal", "caminar", "entrenar"]

THERMAL_ACCESSORIES = ["bufanda", "pañuelo", "gorro", "guantes"]

# =========================================================
# ETIQUETAS EN ESPAÑOL PARA SUBCATEGORÍAS
# =========================================================

CHILEAN_CITIES = [
    "Arica", "Iquique", "Alto Hospicio", "Antofagasta", "Calama",
    "Copiapó", "La Serena", "Coquimbo", "Ovalle", "Vallenar",
    "Viña del Mar", "Valparaíso", "Quilpué", "Villa Alemana",
    "San Antonio", "Rancagua", "Machalí", "San Fernando",
    "Curicó", "Talca", "Linares", "Constitución",
    "Chillán", "Los Ángeles", "Concepción", "Talcahuano",
    "Hualpén", "Coronel", "Lota", "San Pedro de la Paz",
    "Temuco", "Padre Las Casas", "Angol", "Victoria",
    "Valdivia", "Osorno", "Puerto Montt", "Castro", "Ancud",
    "Coyhaique", "Puerto Aysén",
    "Punta Arenas", "Puerto Natales", "Porvenir",
    "Santiago", "Puente Alto", "Maipú", "La Florida",
    "Las Condes", "Ñuñoa", "Providencia", "San Bernardo",
    "Peñalolén", "Lo Barnechea",
]

SUBCATEGORY_LABELS_ES = {
    # top
    "polera": "Polera",
    "blusa": "Blusa",
    "camisa": "Camisa",
    "top": "Top",
    "body": "Body",
    "crop_top": "Crop top",
    "peto": "Peto",
    # midlayer
    "sweater": "Sweater",
    "cardigan": "Cárdigan",
    "chaleco": "Chaleco",
    "blazer": "Blazer",
    "hoodie": "Hoodie",
    "polar": "Polar",
    # outerwear
    "chaqueta": "Chaqueta",
    "abrigo": "Abrigo",
    "parka": "Parka",
    "trench": "Trench",
    "impermeable": "Impermeable",
    "poncho": "Poncho",
    "bolero": "Bolero",
    # bottom
    "jeans": "Jeans",
    "pantalon": "Pantalón",
    "falda_corta": "Falda corta",
    "falda_midi": "Falda midi",
    "falda_larga": "Falda larga",
    "short_casual": "Short casual",
    "short_elegante": "Short elegante",
    "legging": "Legging",
    "buzo": "Buzo/Jogging",
    "jogger": "Jogger",
    # one_piece
    "vestido_casual": "Vestido casual",
    "vestido_elegante": "Vestido elegante",
    "vestido_coctel": "Vestido cóctel",
    "enterito": "Enterito",
    # shoes
    "zapatilla_urbana": "Zapatilla urbana",
    "zapatilla_deporte": "Zapatilla deporte",
    "zapato": "Zapato",
    "botin": "Botín",
    "bota": "Bota",
    "sandalia": "Sandalia",
    "taco_bajo": "Taco bajo",
    "taco_alto": "Taco alto",
    "mocasin": "Mocasín",
    # accessory
    "reloj": "Reloj",
    "collar": "Collar",
    "pulsera": "Pulsera",
    "anillo": "Anillo",
    "aros": "Aros",
    "cinturon": "Cinturón",
    "bolso": "Bolso",
    "cartera": "Cartera",
    "bufanda": "Bufanda",
    "pañuelo": "Pañuelo",
    "gorro": "Gorro",
    "guantes": "Guantes",
}