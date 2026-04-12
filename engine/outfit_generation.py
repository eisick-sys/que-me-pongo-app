#outfit_generation.py
import random
from typing import Any, List, Optional

from models import Garment, OutfitFeedback

from engine.recommender import (
    rank_garments,
    outfit_score,
)

from engine.user_profile import build_user_style_profile

from engine.occasion_rules import (
    build_required_categories,
    garment_allowed_for_occasion,
)

from engine.category_rules import should_include_accessory

from engine.compatibility import invalid_pattern_combo

from utils.garment_utils import garment_has_style

def generate_outfits(
    garments: List[Garment],
    occasion: str,
    temp: int,
    rain: bool,
    mood: str,
    activity: str,
    top_n: int = 5,
    feedback_list: Optional[List[OutfitFeedback]] = None,
    recent_outfits: Optional[List[Any]] = None,
):
    if feedback_list is None:
        feedback_list = []

    user_profile = build_user_style_profile(feedback_list, garments)

    rules = build_required_categories(occasion, rain, temp)
    required = rules["required"]
    optional = rules["optional"]

    ranked = {
        cat: rank_garments(
            garments,
            cat,
            occasion,
            temp,
            rain,
            mood,
            activity,
            user_profile=user_profile,
        )
        for cat in ["top", "midlayer", "outerwear", "bottom", "shoes", "accessory", "one_piece"]
    }

    base_top_limit = 5
    base_bottom_limit = 5
    base_shoes_limit = 4
    mid_limit = 2
    outer_limit = 2
    accessory_limit = 1

    if occasion in ["matrimonio", "gala", "cita", "salida nocturna"]:
        base_top_limit = 6
        base_bottom_limit = 6
        base_shoes_limit = 5
        accessory_limit = 2

    if activity == "caminar" or rain:
        base_shoes_limit = 5
        outer_limit = 2

    if top_n >= 8:
        base_top_limit += 1
        base_bottom_limit += 1

    top_candidates = {
        "top": [g for _, g in ranked["top"][:base_top_limit]],
        "bottom": [g for _, g in ranked["bottom"][:base_bottom_limit]],
        "shoes": [g for _, g in ranked["shoes"][:base_shoes_limit]],
        "midlayer": [g for _, g in ranked["midlayer"][:4]],
        "accessory": [g for _, g in ranked["accessory"][:accessory_limit]],
        "one_piece": [g for _, g in ranked["one_piece"][:base_top_limit]],
    }
    # Shuffle impermeables para rotar cuál aparece primero y evitar siempre el mismo
    _waterproof_outer = [g for _, g in ranked["outerwear"] if g.waterproof]
    _non_waterproof_outer = [g for _, g in ranked["outerwear"] if not g.waterproof]
    random.shuffle(_waterproof_outer)
    top_candidates["outerwear"] = (_waterproof_outer + _non_waterproof_outer)[:4]

    if occasion == "matrimonio" and top_candidates["one_piece"]:
        top_candidates["top"] = [
            g for g in top_candidates["top"]
            if garment_has_style(g, "elegante") or garment_has_style(g, "formal")
        ][:2]

        top_candidates["bottom"] = [
            g for g in top_candidates["bottom"]
            if garment_has_style(g, "elegante") or garment_has_style(g, "formal")
        ][:2]

    if occasion == "cita" and mood == "elegante":
        top_candidates["top"] = [
            g for g in top_candidates["top"]
            if garment_has_style(g, "elegante") or garment_has_style(g, "formal")
        ]

        top_candidates["bottom"] = [
            g for g in top_candidates["bottom"]
            if (
                garment_has_style(g, "elegante")
                or garment_has_style(g, "formal")
            )
            and not any(x in g.name.lower() for x in ["short", "jean", "buzo"])
        ]

        top_candidates["shoes"] = [
            g for g in top_candidates["shoes"]
            if not any(x in g.name.lower() for x in ["zapatilla", "converse"])
        ]

    if temp >= 24:
        top_candidates["outerwear"] = []
        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"] if g.warmth == "caluroso"
        ][:2]

    elif temp >= 22 and not rain:
        top_candidates["outerwear"] = []
        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"] if g.warmth != "frio"
        ][:1]

    elif temp >= 16 and not rain:
        top_candidates["outerwear"] = []
        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"] if g.warmth != "frio"
        ][:1]

    elif temp >= 13 and not rain:
        top_candidates["outerwear"] = [
            g for g in top_candidates["outerwear"]
            if g.warmth != "frio" and not g.waterproof
        ][:1]

    else:
        top_candidates["midlayer"] = top_candidates["midlayer"][:mid_limit]
        top_candidates["outerwear"] = top_candidates["outerwear"][:outer_limit]

    unique = {}

    def register_combo(combo: List[Garment]):
        if invalid_pattern_combo(combo):
            return

        score = outfit_score(
            combo,
            occasion,
            temp,
            rain,
            mood,
            activity,
            feedback_list,
            user_profile=user_profile,
            recent_outfits=recent_outfits,
        )
        if recent_outfits:
            combo_ids = [g.id for g in combo]

            for recent in recent_outfits:
                overlap = len(set(combo_ids) & set(recent))

                if overlap >= 3:
                    score -= 20
                elif overlap == 2:
                    score -= 10
                elif overlap == 1:
                    score -= 3

        if score <= -999:
            return

        core_ids = tuple(sorted(
            g.id for g in combo if g.category in ["top", "bottom", "one_piece", "shoes", "midlayer"]
        ))

        if core_ids not in unique or score > unique[core_ids][0]:
            unique[core_ids] = (score, combo)

    for top in top_candidates["top"]:
        if occasion in ["matrimonio", "gala"]:
            if not (
                garment_has_style(top, "elegante") or garment_has_style(top, "formal")
            ):
                continue

        top_name = top.name.lower()
        top_is_outer_like = any(
            x in top_name
            for x in ["chaqueta", "blazer", "abrigo", "parka", "jacket"]
        )

        for bottom in top_candidates["bottom"]:
            if occasion in ["matrimonio", "gala"]:
                if not (
                    garment_has_style(bottom, "elegante") or garment_has_style(bottom, "formal")
                ):
                    continue

            for shoes in top_candidates["shoes"]:
                base = [top, bottom, shoes]

                outerwear_required = "outerwear" in required and not top_is_outer_like

                if outerwear_required:
                    if "midlayer" in optional:
                        for mid in top_candidates["midlayer"]:
                            if top_candidates["outerwear"]:
                                for outer in top_candidates["outerwear"]:
                                    combo2 = base + [mid, outer]
                                    register_combo(combo2)

                                    if "accessory" in optional:
                                        for acc in top_candidates["accessory"]:
                                            combo3 = base + [mid, outer, acc]
                                            if should_include_accessory(
                                                acc,
                                                occasion,
                                                mood,
                                                activity,
                                                temp,
                                                rain,
                                                base + [mid, outer],
                                            ):
                                                register_combo(combo3)

                    if top_candidates["outerwear"]:
                        for outer in top_candidates["outerwear"]:
                            combo = base + [outer]
                            register_combo(combo)

                            if "accessory" in optional:
                                for acc in top_candidates["accessory"]:
                                    combo_outer_acc = base + [outer, acc]
                                    if should_include_accessory(
                                        acc,
                                        occasion,
                                        mood,
                                        activity,
                                        temp,
                                        rain,
                                        base + [outer],
                                    ):
                                        register_combo(combo_outer_acc)

                    continue

                register_combo(base)

                if "midlayer" in optional:
                    midlayer_candidates = top_candidates["midlayer"]

                    if temp >= 26:
                        midlayer_candidates = []
                    
                    for mid in midlayer_candidates:
                        combo = base + [mid]
                        register_combo(combo)

                        if "accessory" in optional:
                            for acc in top_candidates["accessory"]:
                                combo_mid_acc = base + [mid, acc]
                                if should_include_accessory(
                                    acc,
                                    occasion,
                                    mood,
                                    activity,
                                    temp,
                                    rain,
                                    base + [mid],
                                ):
                                    register_combo(combo_mid_acc)

                        if "outerwear" in optional and not top_is_outer_like:
                            for outer in top_candidates["outerwear"]:
                                combo2 = base + [mid, outer]
                                register_combo(combo2)

                                if "accessory" in optional:
                                    for acc in top_candidates["accessory"]:
                                        combo3 = base + [mid, outer, acc]
                                        if should_include_accessory(
                                            acc,
                                            occasion,
                                            mood,
                                            activity,
                                            temp,
                                            rain,
                                            base + [mid, outer],
                                        ):
                                            register_combo(combo3)

                if "outerwear" in optional and not top_is_outer_like:
                    for outer in top_candidates["outerwear"]:
                        combo = base + [outer]
                        register_combo(combo)

                if "accessory" in optional:
                    for acc in top_candidates["accessory"]:
                        combo = base + [acc]
                        if should_include_accessory(
                            acc, occasion, mood, activity, temp, rain, base
                        ):
                            register_combo(combo)

                if (
                    "outerwear" in optional
                    and "accessory" in optional
                    and not top_is_outer_like
                ):
                    for outer in top_candidates["outerwear"]:
                        for acc in top_candidates["accessory"]:
                            combo = base + [outer, acc]
                            if should_include_accessory(
                                acc,
                                occasion,
                                mood,
                                activity,
                                temp,
                                rain,
                                base + [outer],
                            ):
                                register_combo(combo)

    for one_piece in top_candidates["one_piece"]:
        one_piece_name = one_piece.name.lower()
        one_piece_is_outer_like = any(
            x in one_piece_name
            for x in ["chaqueta", "blazer", "abrigo", "parka", "jacket"]
        )

        for shoes in top_candidates["shoes"]:
            base = [one_piece, shoes]

            outerwear_required = "outerwear" in required and not one_piece_is_outer_like

            if outerwear_required:
                if "midlayer" in optional:
                    for mid in top_candidates["midlayer"]:
                        if top_candidates["outerwear"]:
                            for outer in top_candidates["outerwear"]:
                                combo2 = base + [mid, outer]
                                register_combo(combo2)

                                if "accessory" in optional:
                                    for acc in top_candidates["accessory"]:
                                        combo3 = base + [mid, outer, acc]
                                        if should_include_accessory(
                                            acc,
                                            occasion,
                                            mood,
                                            activity,
                                            temp,
                                            rain,
                                            base + [mid, outer],
                                        ):
                                            register_combo(combo3)

                if top_candidates["outerwear"]:
                    for outer in top_candidates["outerwear"]:
                        combo = base + [outer]
                        register_combo(combo)

                        if "accessory" in optional:
                            for acc in top_candidates["accessory"]:
                                combo_outer_acc = base + [outer, acc]
                                if should_include_accessory(
                                    acc,
                                    occasion,
                                    mood,
                                    activity,
                                    temp,
                                    rain,
                                    base + [outer],
                                ):
                                    register_combo(combo_outer_acc)

                continue

            register_combo(base)

            if "midlayer" in optional and occasion not in ["matrimonio", "gala", "salida nocturna", "cita"]:
                for mid in top_candidates["midlayer"]:
                    combo = base + [mid]
                    register_combo(combo)

                    if "accessory" in optional:
                        for acc in top_candidates["accessory"]:
                            combo_mid_acc = base + [mid, acc]
                            if should_include_accessory(
                                acc,
                                occasion,
                                mood,
                                activity,
                                temp,
                                rain,
                                base + [mid],
                            ):
                                register_combo(combo_mid_acc)

                    if "outerwear" in optional and not one_piece_is_outer_like:
                        for outer in top_candidates["outerwear"]:
                            combo2 = base + [mid, outer]
                            register_combo(combo2)

                            if "accessory" in optional:
                                for acc in top_candidates["accessory"]:
                                    combo3 = base + [mid, outer, acc]
                                    if should_include_accessory(
                                        acc,
                                        occasion,
                                        mood,
                                        activity,
                                        temp,
                                        rain,
                                        base + [mid, outer],
                                    ):
                                        register_combo(combo3)

            if "outerwear" in optional and not one_piece_is_outer_like:
                for outer in top_candidates["outerwear"]:
                    combo = base + [outer]
                    register_combo(combo)

            if "accessory" in optional:
                for acc in top_candidates["accessory"]:
                    combo = base + [acc]
                    if should_include_accessory(
                        acc, occasion, mood, activity, temp, rain, base
                    ):
                        register_combo(combo)

            if (
                "outerwear" in optional
                and "accessory" in optional
                and not one_piece_is_outer_like
            ):
                for outer in top_candidates["outerwear"]:
                    for acc in top_candidates["accessory"]:
                        combo = base + [outer, acc]
                        if should_include_accessory(
                            acc,
                            occasion,
                            mood,
                            activity,
                            temp,
                            rain,
                            base + [outer],
                        ):
                            register_combo(combo)

    final_outfits = sorted(unique.values(), key=lambda x: x[0], reverse=True)

    def is_too_similar(c1, c2):
        ids1 = {g.category: g.id for g in c1}
        ids2 = {g.category: g.id for g in c2}

        same_top = ids1.get("top") == ids2.get("top")
        same_bottom = ids1.get("bottom") == ids2.get("bottom")
        same_one_piece = ids1.get("one_piece") == ids2.get("one_piece")
        same_shoes = ids1.get("shoes") == ids2.get("shoes")

        # 🔥 NUEVO: detectar mismo tipo de combinacion
        bottom1 = next((g for g in c1 if g.category == "bottom"), None)
        bottom2 = next((g for g in c2 if g.category == "bottom"), None)

        shoes1 = next((g for g in c1 if g.category == "shoes"), None)
        shoes2 = next((g for g in c2 if g.category == "shoes"), None)

        same_bottom_type = False
        same_shoes_type = False

        if bottom1 and bottom2:
            name1 = bottom1.name.lower()
            name2 = bottom2.name.lower()

            same_bottom_type = (
                ("buzo" in name1 and "buzo" in name2) or
                ("jean" in name1 and "jean" in name2) or
                ("short" in name1 and "short" in name2)
            )

        if shoes1 and shoes2:
            name1 = shoes1.name.lower()
            name2 = shoes2.name.lower()

            same_shoes_type = (
                ("zapatilla" in name1 and "zapatilla" in name2)
            )

        # 🔥 regla fuerte: mismo tipo de bottom + mismo tipo de calzado
        if same_bottom_type and same_shoes_type:
            return True

        # reglas existentes (más suaves)
        if same_top and same_bottom:
            return True

        if same_top and same_shoes:
            return True

        return False

    diverse_outfits = []
    midlayer_outfits_count = 0
    max_midlayer_outfits = 1 if 24 <= temp < 26 else top_n
    top_usage = {}
    shoes_usage = {}
    outerwear_usage = {}
    max_same_top = 2 if top_n >= 3 else 1
    max_same_shoes = 2 if top_n >= 3 else 1
    _n_waterproof_outer = sum(1 for g in top_candidates["outerwear"] if g.waterproof)
    if _n_waterproof_outer >= 3:
        max_same_outerwear = 1
    elif _n_waterproof_outer == 2:
        max_same_outerwear = 2
    elif _n_waterproof_outer == 1:
        max_same_outerwear = 3
    else:
        max_same_outerwear = 2

    for score, combo in final_outfits:
        ids = {g.category: g.id for g in combo}
        has_midlayer = any(g.category == "midlayer" for g in combo)

        if has_midlayer and midlayer_outfits_count >= max_midlayer_outfits:
            continue

        top_id = ids.get("top")
        shoes_id = ids.get("shoes")
        outerwear_id = ids.get("outerwear")

        if top_id is not None and top_usage.get(top_id, 0) >= max_same_top:
            continue

        if shoes_id is not None and shoes_usage.get(shoes_id, 0) >= max_same_shoes:
            continue

        if outerwear_id is not None and outerwear_usage.get(outerwear_id, 0) >= max_same_outerwear:
            continue

        too_similar = False

        for _, existing in diverse_outfits:
            ids2 = {g.category: g.id for g in existing}

            if is_too_similar(combo, existing):
                too_similar = True
                break

            if ids.get("one_piece") is not None and ids.get("one_piece") == ids2.get("one_piece"):
                too_similar = True
                break

            if ids.get("bottom") == ids2.get("bottom") and ids.get("shoes") == ids2.get("shoes"):
                too_similar = True
                break

        if not too_similar:
            diverse_outfits.append((score, combo))

            if has_midlayer:
                midlayer_outfits_count += 1

            if top_id is not None:
                top_usage[top_id] = top_usage.get(top_id, 0) + 1

            if shoes_id is not None:
                shoes_usage[shoes_id] = shoes_usage.get(shoes_id, 0) + 1

            if outerwear_id is not None:
                outerwear_usage[outerwear_id] = outerwear_usage.get(outerwear_id, 0) + 1

        if len(diverse_outfits) >= top_n:
            break

    # Fallback: si no llegamos a 3 outfits, segunda pasada sin filtro is_too_similar
    min_outfits = min(3, top_n)
    if len(diverse_outfits) < min_outfits:
        existing_ids = {id(combo) for _, combo in diverse_outfits}
        for score, combo in final_outfits:
            if len(diverse_outfits) >= min_outfits:
                break
            if id(combo) in existing_ids:
                continue
            ids = {g.category: g.id for g in combo}
            outerwear_id = ids.get("outerwear")
            top_id = ids.get("top")
            shoes_id = ids.get("shoes")
            if top_id is not None and top_usage.get(top_id, 0) >= max_same_top:
                continue
            if shoes_id is not None and shoes_usage.get(shoes_id, 0) >= max_same_shoes:
                continue
            if outerwear_id is not None and outerwear_usage.get(outerwear_id, 0) >= max_same_outerwear:
                continue
            diverse_outfits.append((score, combo))
            existing_ids.add(id(combo))
            if top_id is not None:
                top_usage[top_id] = top_usage.get(top_id, 0) + 1
            if shoes_id is not None:
                shoes_usage[shoes_id] = shoes_usage.get(shoes_id, 0) + 1
            if outerwear_id is not None:
                outerwear_usage[outerwear_id] = outerwear_usage.get(outerwear_id, 0) + 1

    return diverse_outfits[:top_n]


def generate_outfits_from_selected_garment(
    garments: List[Garment],
    selected_garment: Garment,
    occasion: str,
    temp: int,
    rain: bool,
    mood: str,
    activity: str,
    top_n: int = 5,
    feedback_list: Optional[List[OutfitFeedback]] = None,
    recent_outfits: Optional[List[Any]] = None,
    ignore_occasion_for_selected: bool = False,
):
    if feedback_list is None:
        feedback_list = []

    user_profile = build_user_style_profile(feedback_list, garments)

    rules = build_required_categories(occasion, rain, temp)
    optional = rules["optional"]

    if not ignore_occasion_for_selected:
        selected_allowed, _ = garment_allowed_for_occasion(selected_garment, occasion, rain)
        if not selected_allowed:
            return []

    garments_by_category = {
        "top": [g for g in garments if g.category == "top" and g.id != selected_garment.id],
        "midlayer": [g for g in garments if g.category == "midlayer" and g.id != selected_garment.id],
        "bottom": [g for g in garments if g.category == "bottom" and g.id != selected_garment.id],
        "shoes": [g for g in garments if g.category == "shoes" and g.id != selected_garment.id],
        "outerwear": [g for g in garments if g.category == "outerwear" and g.id != selected_garment.id],
        "accessory": [g for g in garments if g.category == "accessory" and g.id != selected_garment.id],
        "one_piece": [g for g in garments if g.category == "one_piece" and g.id != selected_garment.id],
    }

    ranked = {
        cat: rank_garments(
            garments_by_category[cat],
            cat,
            occasion if not ignore_occasion_for_selected else "casual",
            temp,
            rain,
            mood,
            activity,
            user_profile=user_profile,
        )
        for cat in garments_by_category
    }

    # =========================================================
    # FILTROS DE CANDIDATOS — igual que generate_outfits
    # =========================================================
    base_top_limit = 5
    base_bottom_limit = 5
    base_shoes_limit = 4
    mid_limit = 2
    outer_limit = 2
    accessory_limit = 1

    if occasion in ["matrimonio", "gala", "cita", "salida nocturna"]:
        base_top_limit = 6
        base_bottom_limit = 6
        base_shoes_limit = 5
        accessory_limit = 2

    if activity == "caminar" or rain:
        base_shoes_limit = 5
        outer_limit = 2

    top_candidates = {
        "top": [g for _, g in ranked["top"][:base_top_limit]],
        "bottom": [g for _, g in ranked["bottom"][:base_bottom_limit]],
        "shoes": [g for _, g in ranked["shoes"][:base_shoes_limit]],
        "midlayer": [g for _, g in ranked["midlayer"][:4]],
        "outerwear": [g for _, g in ranked["outerwear"][:4]],
        "accessory": [g for _, g in ranked["accessory"][:accessory_limit]],
        "one_piece": [g for _, g in ranked["one_piece"][:base_top_limit]],
    }

    # =========================================================
    # FILTROS DE CLIMA — ordenados correctamente
    # =========================================================
    if temp >= 24:
        top_candidates["outerwear"] = []
        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"] if g.warmth == "caluroso"
        ][:2]

    elif temp >= 22 and not rain:
        top_candidates["outerwear"] = []
        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"] if g.warmth != "frio"
        ][:1]

    elif temp >= 16 and not rain:
        top_candidates["outerwear"] = []
        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"] if g.warmth != "frio"
        ][:1]

    elif temp >= 13 and not rain:
        top_candidates["outerwear"] = [
            g for g in top_candidates["outerwear"]
            if g.warmth != "frio" and not g.waterproof
        ][:1]

    else:
        top_candidates["midlayer"] = top_candidates["midlayer"][:mid_limit]
        top_candidates["outerwear"] = top_candidates["outerwear"][:outer_limit]

    # Filtros especiales por ocasión — igual que generate_outfits
    if occasion == "matrimonio" and top_candidates["one_piece"]:
        top_candidates["top"] = [
            g for g in top_candidates["top"]
            if garment_has_style(g, "elegante") or garment_has_style(g, "formal")
        ][:2]
        top_candidates["bottom"] = [
            g for g in top_candidates["bottom"]
            if garment_has_style(g, "elegante") or garment_has_style(g, "formal")
        ][:2]

    if occasion == "cita" and mood == "elegante":
        top_candidates["top"] = [
            g for g in top_candidates["top"]
            if garment_has_style(g, "elegante") or garment_has_style(g, "formal")
        ]
        top_candidates["bottom"] = [
            g for g in top_candidates["bottom"]
            if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
            and not any(x in g.name.lower() for x in ["short", "jean", "buzo"])
        ]
        top_candidates["shoes"] = [
            g for g in top_candidates["shoes"]
            if not any(x in g.name.lower() for x in ["zapatilla", "converse"])
        ]

    outfits = []
    selected_category = selected_garment.category

    def add_combo(combo: List[Garment]):
        if invalid_pattern_combo(combo):
            return

        for g in combo:
            if g.id == selected_garment.id:
                continue
            # FIX: pasar rain correctamente
            allowed, _ = garment_allowed_for_occasion(g, occasion, rain)
            if not allowed:
                return

        score = outfit_score(
            combo,
            occasion,
            temp,
            rain,
            mood,
            activity,
            feedback_list,
            user_profile=user_profile,
            recent_outfits=recent_outfits,
            forced_garment_id=selected_garment.id,
            ignore_occasion_for_forced=ignore_occasion_for_selected,
        )

        if recent_outfits:
            combo_ids = [g.id for g in combo]
            for recent in recent_outfits:
                overlap = len(set(combo_ids) & set(recent))
                if overlap >= 3:
                    score -= 20
                elif overlap == 2:
                    score -= 10
                elif overlap == 1:
                    score -= 3

        if score <= -999:
            return

        outfits.append((score, combo))

    def maybe_add_extras(base: List[Garment], top_item: Optional[Garment] = None):
        top_is_outer_like = False
        if top_item is not None:
            top_name = top_item.name.lower()
            top_is_outer_like = any(
                x in top_name for x in ["chaqueta", "blazer", "abrigo", "parka", "jacket"]
            )

        has_midlayer = any(g.category == "midlayer" for g in base)
        has_outerwear = any(g.category == "outerwear" for g in base)
        has_accessory = any(g.category == "accessory" for g in base)

        add_combo(base)

        has_one_piece = any(g.category == "one_piece" for g in base)

        if (
            "midlayer" in optional
            and not has_midlayer
            and not (has_one_piece and occasion in ["matrimonio", "gala", "salida nocturna", "cita"])
        ):
            for mid in top_candidates["midlayer"][:3]:
                combo_mid = base + [mid]
                add_combo(combo_mid)

                if "outerwear" in optional and not has_outerwear and not top_is_outer_like:
                    for outer in top_candidates["outerwear"][:4]:
                        combo_mid_outer = combo_mid + [outer]
                        add_combo(combo_mid_outer)

                if "accessory" in optional and not has_accessory:
                    for acc in top_candidates["accessory"][:4]:
                        combo_mid_acc = combo_mid + [acc]
                        if should_include_accessory(
                            acc, occasion, mood, activity, temp, rain, combo_mid
                        ):
                            add_combo(combo_mid_acc)

        if "outerwear" in optional and not has_outerwear and not top_is_outer_like:
            for outer in top_candidates["outerwear"][:3]:
                combo_outer = base + [outer]
                add_combo(combo_outer)

                if "accessory" in optional and not has_accessory:
                    for acc in top_candidates["accessory"][:2]:
                        combo_outer_acc = combo_outer + [acc]
                        if should_include_accessory(
                            acc, occasion, mood, activity, temp, rain, combo_outer
                        ):
                            add_combo(combo_outer_acc)

        if "accessory" in optional and not has_accessory:
            for acc in top_candidates["accessory"][:2]:
                combo_acc = base + [acc]
                if should_include_accessory(
                    acc, occasion, mood, activity, temp, rain, base
                ):
                    add_combo(combo_acc)

    if selected_category == "top":
        top_item = selected_garment
        for bottom in top_candidates["bottom"]:
            for shoes in top_candidates["shoes"]:
                base = [top_item, bottom, shoes]
                maybe_add_extras(base, top_item=top_item)

    elif selected_category == "bottom":
        for top in top_candidates["top"]:
            for shoes in top_candidates["shoes"]:
                base = [top, selected_garment, shoes]
                maybe_add_extras(base, top_item=top)

    elif selected_category == "one_piece":
        for shoes in top_candidates["shoes"]:
            base = [selected_garment, shoes]
            maybe_add_extras(base)

    elif selected_category == "shoes":
        for top in top_candidates["top"]:
            if occasion in ["matrimonio", "gala"] or (occasion == "cita" and mood == "elegante"):
                if not (garment_has_style(top, "elegante") or garment_has_style(top, "formal")):
                    continue
            for bottom in top_candidates["bottom"]:
                if occasion in ["matrimonio", "gala"] or (occasion == "cita" and mood == "elegante"):
                    if not (garment_has_style(bottom, "elegante") or garment_has_style(bottom, "formal")):
                        continue
                base = [top, bottom, selected_garment]
                maybe_add_extras(base, top_item=top)

        for one_piece in top_candidates["one_piece"]:
            base = [one_piece, selected_garment]
            maybe_add_extras(base)

    elif selected_category == "midlayer":
        for top in top_candidates["top"]:
            for bottom in top_candidates["bottom"]:
                for shoes in top_candidates["shoes"]:
                    base = [top, bottom, shoes, selected_garment]
                    maybe_add_extras(base, top_item=top)

        for one_piece in top_candidates["one_piece"]:
            for shoes in top_candidates["shoes"]:
                base = [one_piece, shoes, selected_garment]
                maybe_add_extras(base)

    elif selected_category == "outerwear":
        for top in top_candidates["top"]:
            for bottom in top_candidates["bottom"]:
                for shoes in top_candidates["shoes"]:
                    base = [top, bottom, shoes, selected_garment]
                    add_combo(base)

                    if "midlayer" in optional:
                        for mid in top_candidates["midlayer"][:3]:
                            combo = [top, bottom, shoes, mid, selected_garment]
                            add_combo(combo)

                    if "accessory" in optional:
                        base_outer = [top, bottom, shoes, selected_garment]
                        for acc in top_candidates["accessory"][:2]:
                            combo = base_outer + [acc]
                            if should_include_accessory(
                                acc, occasion, mood, activity, temp, rain, base_outer
                            ):
                                add_combo(combo)

        for one_piece in top_candidates["one_piece"]:
            for shoes in top_candidates["shoes"]:
                base = [one_piece, shoes, selected_garment]
                add_combo(base)

                if "midlayer" in optional:
                    for mid in top_candidates["midlayer"][:3]:
                        combo = [one_piece, shoes, mid, selected_garment]
                        add_combo(combo)

                if "accessory" in optional:
                    base_outer = [one_piece, shoes, selected_garment]
                    for acc in top_candidates["accessory"][:2]:
                        combo = base_outer + [acc]
                        if should_include_accessory(
                            acc, occasion, mood, activity, temp, rain, base_outer
                        ):
                            add_combo(combo)

    elif selected_category == "accessory":
        for top in top_candidates["top"]:
            for bottom in top_candidates["bottom"]:
                for shoes in top_candidates["shoes"]:
                    base = [top, bottom, shoes, selected_garment]
                    maybe_add_extras(base, top_item=top)

        for one_piece in top_candidates["one_piece"]:
            for shoes in top_candidates["shoes"]:
                base = [one_piece, shoes, selected_garment]
                maybe_add_extras(base)

    # =========================================================
    # DEDUPLICAR Y ORDENAR — igual que generate_outfits
    # =========================================================
    unique = {}
    for score, combo in outfits:
        if score <= -999:
            continue
        key = tuple(sorted(g.id for g in combo))
        if key not in unique or score > unique[key][0]:
            unique[key] = (score, combo)

    final_outfits = sorted(unique.values(), key=lambda x: x[0], reverse=True)

    def is_too_similar(c1, c2):
        ids1 = {g.category: g.id for g in c1}
        ids2 = {g.category: g.id for g in c2}

        same_top = ids1.get("top") == ids2.get("top")
        same_bottom = ids1.get("bottom") == ids2.get("bottom")
        same_shoes = ids1.get("shoes") == ids2.get("shoes")

        if same_bottom and same_shoes:
            return True
        if same_top and same_bottom:
            return True
        return False

    diverse = []
    for score, combo in final_outfits:
        too_similar = any(is_too_similar(combo, c) for _, c in diverse)
        if not too_similar:
            diverse.append((score, combo))
        if len(diverse) >= top_n:
            break

    return diverse[:top_n]


def generate_week_plan(
    garments,
    week_context,
    week_weather,
    feedback_list: Optional[List[OutfitFeedback]] = None,
):
    if feedback_list is None:
        feedback_list = []

    ordered_days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    available_days = [day for day in ordered_days if day in week_context]

    week_plan = {}
    used_counts = {}
    used_by_category = {
        "top": {},
        "bottom": {},
        "shoes": {},
        "outerwear": {},
        "midlayer": {},
        "accessory": {},
    }

    for day in available_days:
        context = week_context[day]
        day_weather = week_weather.get(day, {})
        day_temp = day_weather.get("temp", 15)
        day_rain = day_weather.get("rain", False)

        synthetic_recent_outfits = [
            [g.id for g in planned_combo]
            for planned_combo in week_plan.values()
        ]

        outfits = generate_outfits(
            garments=garments,
            occasion=context["occasion"],
            temp=day_temp,
            rain=day_rain,
            mood=context["mood"],
            activity=context["activity"],
            top_n=8,
            feedback_list=feedback_list,
            recent_outfits=synthetic_recent_outfits,
        )

        if not outfits:
            outfits = generate_outfits(
                garments=garments,
                occasion=context["occasion"],
                temp=day_temp,
                rain=day_rain,
                mood=context["mood"],
                activity=context["activity"],
                top_n=5,
                feedback_list=feedback_list,
                recent_outfits=[],
            )

        if not outfits:
            week_plan[day] = []
            continue

        best_combo = None
        best_adjusted_score = None

        for score, combo in outfits:
            repetition_penalty_value = 0

            combo_ids = [g.id for g in combo]

            for g in combo:
                times_used_total = used_counts.get(g.id, 0)
                repetition_penalty_value += times_used_total * 12

                cat_used = used_by_category.get(g.category, {})
                times_used_in_category = cat_used.get(g.id, 0)

                if g.category == "top":
                    repetition_penalty_value += times_used_in_category * 14
                elif g.category == "bottom":
                    repetition_penalty_value += times_used_in_category * 12
                elif g.category == "shoes":
                    repetition_penalty_value += times_used_in_category * 16
                elif g.category == "outerwear":
                    repetition_penalty_value += times_used_in_category * 24
                elif g.category == "midlayer":
                    repetition_penalty_value += times_used_in_category * 9
                else:
                    repetition_penalty_value += times_used_in_category * 7

            for planned_combo in week_plan.values():
                planned_ids = [g.id for g in planned_combo]
                overlap = len(set(combo_ids) & set(planned_ids))

                if overlap >= 3:
                    repetition_penalty_value += 18
                elif overlap == 2:
                    repetition_penalty_value += 10
                elif overlap == 1:
                    repetition_penalty_value += 4

            if day != available_days[0]:
                previous_day = available_days[available_days.index(day) - 1]
                previous_combo = week_plan.get(previous_day, [])
                previous_by_category = {g.category: g.id for g in previous_combo}

                for g in combo:
                    if previous_by_category.get(g.category) == g.id:
                        if g.category in ["top", "bottom", "shoes", "outerwear"]:
                            repetition_penalty_value += 16
                        else:
                            repetition_penalty_value += 6

            adjusted_score = score - repetition_penalty_value

            if best_combo is None or adjusted_score > best_adjusted_score:
                best_combo = combo
                best_adjusted_score = adjusted_score

        if best_combo:
            week_plan[day] = best_combo

            for g in best_combo:
                used_counts[g.id] = used_counts.get(g.id, 0) + 1

                if g.category not in used_by_category:
                    used_by_category[g.category] = {}

                used_by_category[g.category][g.id] = (
                    used_by_category[g.category].get(g.id, 0) + 1
                )
        else:
            week_plan[day] = []

    return week_plan