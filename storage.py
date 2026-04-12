import json
import os
import shutil
from dataclasses import asdict
from typing import List, Optional

from models import Garment, OutfitFeedback, UsedOutfit


# =========================================================
# HELPERS GENERALES
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


def read_json_file(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(file_path: str, data) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def backup_file_if_exists(file_path: str) -> None:
    if os.path.exists(file_path):
        shutil.copy(file_path, file_path + ".bak")


# =========================================================
# NORMALIZADORES / FACTORIES
# =========================================================

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

def save_wardrobe(data_file: str, wardrobe: List[Garment]) -> None:
    backup_file_if_exists(data_file)
    write_json_file(data_file, [asdict(g) for g in wardrobe])


def _load_wardrobe_from_path(file_path: str) -> List[Garment]:
    data = read_json_file(file_path)

    if not data:
        return []

    wardrobe = []

    for item in data:
        try:
            wardrobe.append(garment_from_dict(item))
        except Exception as e:
            print(f"Error cargando prenda: {item} -> {e}")

    return wardrobe


def load_wardrobe(data_file: str, default_items: List[Garment]) -> List[Garment]:
    if not os.path.exists(data_file):
        save_wardrobe(data_file, default_items)
        return default_items

    try:
        return _load_wardrobe_from_path(data_file)

    except Exception as e:
        print(f"Error cargando closet.json: {e}")

        backup_file = data_file + ".bak"
        if os.path.exists(backup_file):
            print("Intentando recuperar desde backup...")

            try:
                wardrobe = _load_wardrobe_from_path(backup_file)
                print("Backup cargado correctamente.")
                return wardrobe
            except Exception as e2:
                print(f"Error cargando backup: {e2}")

        return []


# =========================================================
# FEEDBACK
# =========================================================

def save_feedback(feedback_file: str, feedback_list: List[OutfitFeedback]) -> None:
    backup_file_if_exists(feedback_file)
    write_json_file(feedback_file, [asdict(fb) for fb in feedback_list])


def _load_feedback_from_path(file_path: str) -> List[OutfitFeedback]:
    data = read_json_file(file_path)

    if not data:
        return []

    feedback_list = []

    for item in data:
        try:
            feedback_list.append(feedback_from_dict(item))
        except Exception as e:
            print(f"Error cargando feedback: {item} -> {e}")

    return feedback_list


def load_feedback(feedback_file: str) -> List[OutfitFeedback]:
    if not os.path.exists(feedback_file):
        return []

    try:
        return _load_feedback_from_path(feedback_file)

    except Exception as e:
        print(f"Error cargando feedback.json: {e}")

        backup_file = feedback_file + ".bak"
        if os.path.exists(backup_file):
            print("Intentando recuperar feedback desde backup...")

            try:
                feedback_list = _load_feedback_from_path(backup_file)
                print("Feedback backup cargado correctamente.")
                return feedback_list
            except Exception as e2:
                print(f"Error cargando backup de feedback: {e2}")

        return []


def feedback_signature(feedback: OutfitFeedback):
    return (
        tuple(sorted(feedback.garment_ids)),
        bool(feedback.liked),
        feedback.occasion,
        feedback.mood,
        feedback.activity,
        feedback.weather_tag,
    )


def add_feedback(feedback_file: str, new_feedback: OutfitFeedback) -> None:
    feedback_list = load_feedback(feedback_file)
    new_sig = feedback_signature(new_feedback)

    unique_feedback = []
    seen = set()

    for fb in feedback_list:
        sig = feedback_signature(fb)
        if sig not in seen:
            seen.add(sig)
            unique_feedback.append(fb)

    if new_sig in seen:
        save_feedback(feedback_file, unique_feedback)
        return

    unique_feedback.append(new_feedback)
    save_feedback(feedback_file, unique_feedback)


# =========================================================
# USED OUTFITS / HISTORIAL
# =========================================================

def save_used_outfits(history_file: str, used_outfits: List[UsedOutfit]) -> None:
    backup_file_if_exists(history_file)
    write_json_file(history_file, [asdict(item) for item in used_outfits])


def _load_used_outfits_from_path(file_path: str) -> List[UsedOutfit]:
    data = read_json_file(file_path)

    if not data:
        return []

    used_outfits = []

    for item in data:
        try:
            used_outfits.append(used_outfit_from_dict(item))
        except Exception as e:
            print(f"Error cargando used outfit: {item} -> {e}")

    return used_outfits


def load_used_outfits(history_file: str) -> List[UsedOutfit]:
    if not os.path.exists(history_file):
        return []

    try:
        return _load_used_outfits_from_path(history_file)

    except Exception as e:
        print(f"Error cargando historial de outfits: {e}")

        backup_file = history_file + ".bak"
        if os.path.exists(backup_file):
            print("Intentando recuperar historial desde backup...")

            try:
                used_outfits = _load_used_outfits_from_path(backup_file)
                print("Historial backup cargado correctamente.")
                return used_outfits
            except Exception as e2:
                print(f"Error cargando backup de historial: {e2}")

        return []


def used_outfit_signature(item: UsedOutfit):
    return (
        tuple(sorted(item.garment_ids)),
        item.used_at,
        item.occasion,
        item.mood,
        item.activity,
        item.weather_tag,
    )


def add_used_outfit(history_file: str, new_used_outfit: UsedOutfit) -> None:
    used_outfits = load_used_outfits(history_file)
    new_sig = used_outfit_signature(new_used_outfit)

    unique_used_outfits = []
    seen = set()

    for item in used_outfits:
        sig = used_outfit_signature(item)
        if sig not in seen:
            seen.add(sig)
            unique_used_outfits.append(item)

    if new_sig in seen:
        save_used_outfits(history_file, unique_used_outfits)
        return

    unique_used_outfits.append(new_used_outfit)
    save_used_outfits(history_file, unique_used_outfits)


def get_next_used_outfit_id(used_outfits: List[UsedOutfit]) -> int:
    if not used_outfits:
        return 1
    return max(safe_int(item.id, 0) for item in used_outfits) + 1