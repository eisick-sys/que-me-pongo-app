#models.py
from dataclasses import dataclass, field
from typing import List, Optional


# =========================================================
# GARMENT
# =========================================================
@dataclass
class Garment:
    """
    Representa una prenda dentro del clóset.
    """
    id: int
    name: str

    # clasificación
    category: str        # top, midlayer, outerwear, bottom, one_piece, shoes, accessory
    color: str
    style: str           # casual, formal, urbano, sport, elegante
    subcategory: Optional[str] = None
    secondary_colors: List[str] = field(default_factory=list)
    secondary_styles: List[str] = field(default_factory=list)
    pattern: str = "liso"   # liso, rayas, cuadros, estampado, animal_print, floral, grafico

    # características físicas
    warmth: str = "medio"      # frio, medio, caluroso
    waterproof: bool = False

    # nivel de formalidad
    dress_level: str = "flexible"     # relajado, flexible, arreglado, elegante

    # nivel sexy
    sexiness: int = 0

    # subtipo de accesorio
    accessory_type: Optional[str] = None

    # imagen asociada
    image_name: Optional[str] = None

    # etiqueta de prenda recién agregada
    is_new: bool = False


# =========================================================
# FEEDBACK DE OUTFITS
# =========================================================
@dataclass
class OutfitFeedback:
    """
    Guarda si un outfit recomendado gustó o no gustó,
    junto con el contexto en que fue mostrado.
    """
    id: int
    garment_ids: List[int]

    liked: bool

    occasion: str
    mood: str
    activity: str
    weather_tag: str


# =========================================================
# OUTFITS REALMENTE USADOS
# =========================================================
@dataclass
class UsedOutfit:
    """
    Guarda un outfit que el usuario realmente decidió usar,
    no solo uno que fue recomendado.
    """
    id: int
    garment_ids: List[int]

    occasion: str
    mood: str
    activity: str
    weather_tag: str

    used_at: str