# storage_cloud.py
import io
from dataclasses import asdict
from typing import List, Optional

from PIL import Image, ImageOps

from models import Garment, OutfitFeedback, UsedOutfit, UserProfile
from supabase_client import get_supabase, get_supabase_for_user


# =========================================================
# HELPERS
# =========================================================

def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def ensure_list(value) -> list:
    if isinstance(value, list):
        return value
    return []


def garment_from_dict(item: dict) -> Garment:
    return Garment(
        id=safe_int(item.get("id"), 0),
        name=str(item.get("name", "")),
        category=str(item.get("category", "top")),
        subcategory=item.get("subcategory", None),
        color=str(item.get("color", "negro")),
        secondary_colors=[
            str(x).strip()
            for x in ensure_list(item.get("secondary_colors", []))
            if x and str(x).strip()
        ],
        style=str(item.get("style", "casual")),
        secondary_styles=[str(x) for x in ensure_list(item.get("secondary_styles", []))],
        pattern=str(item.get("pattern", "liso")),
        warmth=str(item.get("warmth", "medio")),
        waterproof=bool(item.get("waterproof", False)),
        dress_level=str(item.get("dress_level", "flexible")),
        sexiness=safe_int(item.get("sexiness"), 0),
        accessory_type=item.get("accessory_type", None),
        image_name=item.get("image_name", None),
        is_new=bool(item.get("is_new", False)),
    )


def feedback_from_dict(item: dict) -> OutfitFeedback:
    return OutfitFeedback(
        id=safe_int(item.get("id"), 0),
        garment_ids=[safe_int(x) for x in ensure_list(item.get("garment_ids", []))],
        liked=bool(item.get("liked", True)),
        occasion=str(item.get("occasion", "casual")),
        mood=str(item.get("mood", "relajado")),
        activity=str(item.get("activity", "normal")),
        weather_tag=str(item.get("weather_tag", "templado")),
    )


def used_outfit_from_dict(item: dict) -> UsedOutfit:
    return UsedOutfit(
        id=safe_int(item.get("id"), 0),
        garment_ids=[safe_int(x) for x in ensure_list(item.get("garment_ids", []))],
        occasion=str(item.get("occasion", "casual")),
        mood=str(item.get("mood", "relajado")),
        activity=str(item.get("activity", "normal")),
        weather_tag=str(item.get("weather_tag", "templado")),
        used_at=str(item.get("used_at", "")),
    )


# =========================================================
# WARDROBE
# =========================================================

def load_wardrobe_cloud(user_id: str) -> List[Garment]:
    try:
        sb = get_supabase()
        response = sb.table("garments").select("*").eq("user_id", user_id).execute()
        return [garment_from_dict(item) for item in (response.data or [])]
    except Exception as e:
        print(f"Error cargando closet desde Supabase: {e}")
        return []


def save_garment_cloud(user_id: str, garment: Garment) -> Optional[int]:
    """
    Inserta una prenda nueva y devuelve el id generado por Supabase.
    """
    try:
        sb = get_supabase()
        data = asdict(garment)
        data.pop("id", None)  # Supabase genera el id
        data["user_id"] = user_id

        response = sb.table("garments").insert(data).execute()
        if response.data:
            return response.data[0]["id"]
        return None
    except Exception as e:
        print(f"Error guardando prenda: {e}")
        return None


def update_garment_cloud(user_id: str, garment: Garment) -> bool:
    try:
        sb = get_supabase()
        data = asdict(garment)
        data.pop("id", None)
        data["user_id"] = user_id
        sb.table("garments").update(data).eq("id", garment.id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error actualizando prenda: {e}")
        return False


def delete_garment_cloud(user_id: str, garment_id: int) -> bool:
    try:
        sb = get_supabase()
        sb.table("garments").delete().eq("id", garment_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error eliminando prenda: {e}")
        return False


# =========================================================
# IMÁGENES
# =========================================================

def upload_garment_image(user_id: str, garment_id: int, uploaded_file, access_token: str = None) -> Optional[str]:
    """
    Sube imagen a Supabase Storage y devuelve el nombre del archivo (image_name).
    Las imágenes se guardan en: garment-images/{user_id}/garment_{garment_id}.jpg
    """
    try:
        sb = get_supabase_for_user(access_token) if access_token else get_supabase()

        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        square = ImageOps.fit(image, (300, 300), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        square.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        image_name = f"garment_{garment_id}.jpg"
        storage_path = f"{user_id}/{image_name}"

        sb.storage.from_("garment-images").upload(
            storage_path,
            buffer.read(),
            {"content-type": "image/jpeg", "upsert": "true"}
        )

        return image_name

    except Exception as e:
        print(f"Error subiendo imagen: {e}")
        return None


def get_garment_image_url(user_id: str, image_name: str) -> Optional[str]:
    """
    Devuelve la URL pública de la imagen de una prenda.
    """
    if not image_name:
        return None
    try:
        sb = get_supabase()
        storage_path = f"{user_id}/{image_name}"
        result = sb.storage.from_("garment-images").get_public_url(storage_path)
        return result
    except Exception as e:
        print(f"Error obteniendo URL de imagen: {e}")
        return None


def delete_garment_image(user_id: str, image_name: str) -> bool:
    if not image_name:
        return True
    try:
        sb = get_supabase()
        storage_path = f"{user_id}/{image_name}"
        sb.storage.from_("garment-images").remove([storage_path])
        return True
    except Exception as e:
        print(f"Error eliminando imagen: {e}")
        return False


# =========================================================
# FEEDBACK
# =========================================================

def load_feedback_cloud(user_id: str) -> List[OutfitFeedback]:
    try:
        sb = get_supabase()
        response = sb.table("outfit_feedback").select("*").eq("user_id", user_id).execute()
        return [feedback_from_dict(item) for item in (response.data or [])]
    except Exception as e:
        print(f"Error cargando feedback: {e}")
        return []


def add_feedback_cloud(user_id: str, feedback: OutfitFeedback) -> bool:
    try:
        sb = get_supabase()
        data = asdict(feedback)
        data.pop("id", None)
        data["user_id"] = user_id

        sb.table("outfit_feedback").insert(data).execute()
        return True
    except Exception as e:
        print(f"Error guardando feedback: {e}")
        return False


# =========================================================
# USED OUTFITS / HISTORIAL
# =========================================================

def load_used_outfits_cloud(user_id: str) -> List[UsedOutfit]:
    try:
        sb = get_supabase()
        response = sb.table("used_outfits").select("*").eq("user_id", user_id).execute()
        return [used_outfit_from_dict(item) for item in (response.data or [])]
    except Exception as e:
        print(f"Error cargando historial: {e}")
        return []


def add_used_outfit_cloud(user_id: str, used_outfit: UsedOutfit) -> bool:
    try:
        sb = get_supabase()
        data = asdict(used_outfit)
        data.pop("id", None)
        data["user_id"] = user_id

        sb.table("used_outfits").insert(data).execute()
        return True
    except Exception as e:
        print(f"Error guardando outfit usado: {e}")
        return False


def get_next_used_outfit_id(used_outfits: List[UsedOutfit]) -> int:
    if not used_outfits:
        return 1
    return max(safe_int(item.id, 0) for item in used_outfits) + 1


def load_user_profile_cloud(user_id: str) -> Optional[UserProfile]:
    try:
        sb = get_supabase()
        response = sb.table("user_profiles").select("*").eq("user_id", user_id).execute()
        if response.data:
            item = response.data[0]
            return UserProfile(
                user_id=user_id,
                display_name=str(item.get("display_name") or ""),
                closet_type=str(item.get("closet_type") or "mixto"),
                city=str(item.get("city") or "Punta Arenas"),
                frequent_occasions=list(item.get("frequent_occasions") or []),
                dominant_style=str(item.get("dominant_style") or "casual"),
            )
        return None
    except Exception as e:
        print(f"Error cargando perfil: {e}")
        return None


def save_user_profile_cloud(profile: UserProfile) -> bool:
    try:
        sb = get_supabase()
        data = {
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "closet_type": profile.closet_type,
            "city": profile.city,
            "frequent_occasions": profile.frequent_occasions,
            "dominant_style": profile.dominant_style,
            "updated_at": "now()",
        }
        sb.table("user_profiles").upsert(data).execute()
        return True
    except Exception as e:
        print(f"Error guardando perfil: {e}")
        return False


# =========================================================
# IGNORED BADGES
# =========================================================

def load_ignored_badges_cloud(user_id: str) -> set:
    try:
        sb = get_supabase()
        response = sb.table("ignored_badges").select("garment_id").eq("user_id", user_id).execute()
        return {item["garment_id"] for item in (response.data or [])}
    except Exception as e:
        print(f"Error cargando ignored badges: {e}")
        return set()


def add_ignored_badge_cloud(user_id: str, garment_id: int) -> bool:
    try:
        sb = get_supabase()
        sb.table("ignored_badges").upsert({
            "user_id": user_id,
            "garment_id": garment_id,
        }).execute()
        return True
    except Exception as e:
        print(f"Error guardando ignored badge: {e}")
        return False
