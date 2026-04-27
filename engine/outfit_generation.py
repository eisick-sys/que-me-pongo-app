#outfit_generation.py
import random
from typing import Any, List, Optional

from models import Garment, OutfitFeedback

from engine.recommender import (
    rank_garments,
    outfit_score,
)

from utils.user_profile import build_user_style_profile

from engine.occasion_rules import (
    build_required_categories,
    garment_allowed_for_occasion,
)

from engine.category_rules import should_include_accessory

from engine.compatibility import invalid_pattern_combo

from utils.garment_utils import garment_has_style

def get_missing_categories(top_candidates, required):
    missing = []
    for cat in required:
        if cat == "top":
            has_top = bool(top_candidates.get("top")) or bool(top_candidates.get("one_piece"))
            if not has_top:
                missing.append("top")
        elif not top_candidates.get(cat):
            missing.append(cat)
    return missing


def _generate_matrimonio_elegante(
    garments, temp, rain, mood, activity,
    top_n, feedback_list, recent_outfits, user_profile,
    selected_garment=None, ignore_selected=False
):
    from engine.category_rules import should_include_accessory

    # --- POOLS ---
    vestidos = [
        g for g in garments
        if g.category == "one_piece"
        and g.subcategory in ["vestido_elegante", "vestido_coctel"]
    ]

    calzado = [
        g for g in garments
        if g.category == "shoes"
        and g.subcategory in ["taco_alto", "taco_bajo", "sandalia"]
    ]

    blazers = [
        g for g in garments
        if g.category == "midlayer"
        and g.subcategory == "blazer"
        and (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
        and g.dress_level in ["arreglado", "elegante"]
    ]

    abrigos = [
        g for g in garments
        if g.category == "outerwear"
        and g.subcategory in ["abrigo", "trench"]
        and g.style not in ["sport", "urbano", "casual"]
    ]

    accesorios = [
        g for g in garments
        if g.category == "accessory"
        and g.dress_level in ["arreglado", "elegante"]
        and g.subcategory not in ["gorro", "gorra"]
    ]

    if selected_garment is not None:
        cat = selected_garment.category
        sub = getattr(selected_garment, "subcategory", None)
        if cat == "one_piece" and sub in ["vestido_elegante", "vestido_coctel"]:
            vestidos = [selected_garment]
        elif cat == "shoes" and sub in ["taco_alto", "taco_bajo", "sandalia"]:
            calzado = [selected_garment]
        elif cat == "midlayer" and sub == "blazer":
            blazers = [selected_garment] + [g for g in blazers if g.id != selected_garment.id]
        elif cat == "outerwear" and sub in ["abrigo", "trench"]:
            abrigos = [selected_garment] + [g for g in abrigos if g.id != selected_garment.id]
        elif cat == "accessory":
            accesorios = [selected_garment] + [g for g in accesorios if g.id != selected_garment.id]
        elif not ignore_selected:
            return [], []

    if not calzado:
        return [], []

    if not vestidos:
        return generate_outfits(
            garments=garments,
            occasion="matrimonio",
            temp=temp,
            rain=rain,
            mood="sexy",
            activity=activity,
            top_n=top_n,
            feedback_list=feedback_list,
            recent_outfits=recent_outfits,
        )

    # --- TEMPERATURA: decidir capas ---
    usar_blazer = temp <= 25
    usar_abrigo = temp <= 15

    if temp >= 22:
        blazers = [g for g in blazers if g.warmth in ["caluroso", "medio"]]
    elif temp >= 13:
        blazers = [g for g in blazers if g.warmth in ["frio", "medio"]]

    # --- SCORING simple para ordenar pools ---
    def score_garment(g):
        from engine.scoring_components import weather_score, dress_score
        return weather_score(g, temp, rain) + dress_score(g.dress_level, "matrimonio")

    if len(vestidos) > 1:
        random.shuffle(vestidos)
    vestidos = sorted(vestidos, key=score_garment, reverse=True)
    calzado = sorted(calzado, key=score_garment, reverse=True)
    blazers = sorted(blazers, key=score_garment, reverse=True)
    abrigos = sorted(abrigos, key=score_garment, reverse=True)
    random.shuffle(accesorios)

    # --- GENERAR COMBOS ---
    outfits = []

    for i in range(min(top_n, len(vestidos))):
        vestido = vestidos[i % len(vestidos)]
        taco = calzado[i % len(calzado)]
        if 24 <= temp <= 25:
            blazers_calor = [g for g in blazers if g.warmth in ["caluroso", "medio"]]
            omitir_blazer = (i != 0 or not blazers_calor)
            blazer = blazers_calor[0] if not omitir_blazer else None
        else:
            omitir_blazer = (20 <= temp <= 23 and i == 2)
            blazer = blazers[i % len(blazers)] if usar_blazer and blazers and not omitir_blazer else None
        abrigo = abrigos[i % len(abrigos)] if usar_abrigo and abrigos else None
        acc = accesorios[i % len(accesorios)] if accesorios else None

        combo = [vestido, taco]
        if blazer:
            combo.append(blazer)
        if abrigo:
            combo.append(abrigo)
        if acc:
            combo.append(acc)
        outfits.append(combo)

    # Asignar score real a cada combo
    result = []
    for combo in outfits:
        from engine.recommender import outfit_score
        score = outfit_score(
            combo, "matrimonio", temp, rain, mood, activity,
            feedback_list, user_profile=user_profile,
            recent_outfits=recent_outfits
        )
        result.append((score, combo))

    result = [(s, c) for s, c in result if s > -999]
    if not result:
        return generate_outfits(
            garments=garments,
            occasion="matrimonio",
            temp=temp,
            rain=rain,
            mood="sexy",
            activity=activity,
            top_n=top_n,
            feedback_list=feedback_list,
            recent_outfits=recent_outfits,
        )
    result.sort(key=lambda x: x[0], reverse=True)
    return result[:top_n], []


def _generate_gala(
    garments, temp, rain, mood, activity,
    top_n, feedback_list, recent_outfits, user_profile,
    selected_garment=None, ignore_selected=False
):
    """
    Genera outfits para gala. Reglas:
    - Solo vestido_elegante o vestido_coctel. Sin top+bottom, sin enterito.
    - Calzado:
        - elegante/sexy/urbano: taco_alto, taco_bajo, sandalia
        - comodo: taco_bajo, sandalia (sin taco_alto)
    - Midlayer: NUNCA (ni blazer ni cardigan).
    - Abrigo: solo abrigo/trench elegante, preferir warmth medio en temperaturas intermedias.
      Sin parka, sin impermeable. Lluvia → mismo abrigo + tip paraguas.
    - Sin fallback a top+bottom. Sin vestidos si no hay → warning + "Mostrar de todos modos"
      que deriva a _generate_matrimonio_elegante.
    - Mood urbano: vestido_coctel + zapatilla_urbana arreglada/elegante.
    - Mood relajado: bloqueado (ya manejado en occasion_rules).
    """
    from engine.category_rules import should_include_accessory

    if mood == "relajado":
        return [], []

    # --- POOLS base ---
    vestidos = [
        g for g in garments
        if g.category == "one_piece"
        and g.subcategory in ["vestido_elegante", "vestido_coctel"]
    ]

    # Calzado según mood
    if mood == "comodo":
        calzado = [
            g for g in garments
            if g.category == "shoes"
            and g.subcategory in ["taco_bajo", "sandalia"]
        ]
    elif mood == "urbano":
        calzado = [
            g for g in garments
            if g.category == "shoes"
            and (
                g.subcategory in ["taco_alto", "taco_bajo", "sandalia"]
                or (g.subcategory == "zapatilla_urbana" and g.dress_level in ["arreglado", "elegante"])
            )
        ]
    else:  # elegante, sexy
        calzado = [
            g for g in garments
            if g.category == "shoes"
            and g.subcategory in ["taco_alto", "taco_bajo", "sandalia"]
        ]

    # Excluir sandalia en frío extremo antes de que consuma un slot con score -999
    calzado = [g for g in calzado if not (g.subcategory == "sandalia" and temp <= 10)]

    # Abrigos: abrigo/chaqueta/bolero elegante o formal, sin impermeable
    abrigos_todos = [
        g for g in garments
        if g.category == "outerwear"
        and g.subcategory in ["abrigo", "chaqueta", "bolero"]
        and (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
        and not g.waterproof
    ]
    if mood == "urbano":
        abrigos_todos += [
            g for g in garments
            if g.category == "outerwear"
            and g.subcategory == "trench"
            and not g.waterproof
        ]

    accesorios = [
        g for g in garments
        if g.category == "accessory"
        and g.dress_level in ["arreglado", "elegante"]
        and g.subcategory not in ["gorro", "gorra"]
    ]

    # --- selected_garment ---
    if selected_garment is not None:
        cat = selected_garment.category
        sub = getattr(selected_garment, "subcategory", None)
        if cat == "one_piece" and sub in ["vestido_elegante", "vestido_coctel"]:
            vestidos = [selected_garment]
        elif cat == "shoes":
            calzado = [selected_garment]
        elif cat == "outerwear" and sub in ["abrigo", "chaqueta", "bolero"]:
            abrigos_todos = [selected_garment] + [g for g in abrigos_todos if g.id != selected_garment.id]
        elif cat == "outerwear" and sub == "trench" and mood == "urbano":
            abrigos_todos = [selected_garment] + [g for g in abrigos_todos if g.id != selected_garment.id]
        elif cat == "accessory":
            accesorios = [selected_garment] + [g for g in accesorios if g.id != selected_garment.id]
        elif not ignore_selected:
            return [], []

    if not calzado:
        return [], []

    # Sin vestidos → retorna vacío; la UI mostrará warning y derivará a _generate_matrimonio_elegante
    if not vestidos:
        return [], []

    # --- Selección de abrigos según temperatura ---
    # Sin abrigo si calor; preferir warmth medio en rango intermedio
    usar_abrigo = temp <= 18
    if usar_abrigo:
        if 13 <= temp <= 18:
            # Preferir warmth medio; si no hay, aceptar frio
            abrigos_pref = [g for g in abrigos_todos if g.warmth == "medio"]
            if not abrigos_pref:
                abrigos_pref = [g for g in abrigos_todos if g.warmth in ["medio", "frio"]]
            abrigos = abrigos_pref
        else:  # temp <= 12: frío real, cualquier abrigo elegante
            abrigos = abrigos_todos
    else:
        abrigos = []

    # --- Scoring para ordenar pools ---
    def score_g(g):
        from engine.scoring_components import weather_score, dress_score
        return weather_score(g, temp, rain) + dress_score(g.dress_level, "gala")

    if len(vestidos) > 1:
        random.shuffle(vestidos)
    vestidos = sorted(vestidos, key=score_g, reverse=True)
    calzado = sorted(calzado, key=score_g, reverse=True)
    abrigos = sorted(abrigos, key=score_g, reverse=True)
    if selected_garment is not None and selected_garment.category == "outerwear":
        abrigos = [selected_garment] + [g for g in abrigos if g.id != selected_garment.id]
    random.shuffle(accesorios)

    # --- Scoring boost: priorizar vestido_coctel en sexy/urbano ---
    if mood in ["sexy", "urbano"]:
        vestidos = sorted(
            vestidos,
            key=lambda g: (0 if g.subcategory == "vestido_coctel" else 1, -score_g(g))
        )

    # --- Generar combos ---
    outfits = []
    for i in range(top_n):
        vestido = vestidos[i % len(vestidos)]
        zapato = calzado[i % len(calzado)]
        abrigo = abrigos[i % len(abrigos)] if usar_abrigo and abrigos else None
        acc = accesorios[i % len(accesorios)] if accesorios else None

        combo = [vestido, zapato]
        if abrigo:
            combo.append(abrigo)
        if acc:
            combo.append(acc)
        outfits.append(combo)

    # --- Score real ---
    result = []
    for combo in outfits:
        from engine.recommender import outfit_score
        score = outfit_score(
            combo, "gala", temp, rain, mood, activity,
            feedback_list, user_profile=user_profile,
            recent_outfits=recent_outfits
        )
        result.append((score, combo))

    result = [(s, c) for s, c in result if s > -999]
    result.sort(key=lambda x: x[0], reverse=True)
    return result[:top_n], []


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

    if occasion == "matrimonio" and mood == "elegante":
        return _generate_matrimonio_elegante(
            garments=garments,
            temp=temp,
            rain=rain,
            mood=mood,
            activity=activity,
            top_n=top_n,
            feedback_list=feedback_list,
            recent_outfits=recent_outfits,
            user_profile=build_user_style_profile(feedback_list, garments),
        )

    if occasion == "gala":
        return _generate_gala(
            garments=garments,
            temp=temp,
            rain=rain,
            mood=mood,
            activity=activity,
            top_n=top_n,
            feedback_list=feedback_list,
            recent_outfits=recent_outfits,
            user_profile=build_user_style_profile(feedback_list, garments),
        )

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
    outer_limit = 3
    accessory_limit = 1

    if occasion in ["matrimonio", "gala", "cita", "salida nocturna"]:
        base_top_limit = 6
        base_bottom_limit = 6
        base_shoes_limit = 5
        accessory_limit = 2

    if activity == "caminar" or rain:
        base_shoes_limit = 5
        outer_limit = 3

    if top_n >= 8:
        base_top_limit += 1
        base_bottom_limit += 1

    top_candidates = {
        "top": [g for _, g in ranked["top"][:base_top_limit]],
        "bottom": [g for _, g in ranked["bottom"][:base_bottom_limit]],
        "shoes": [g for _, g in ranked["shoes"][:base_shoes_limit]],
        "midlayer": [g for _, g in ranked["midlayer"][:4]],
        "one_piece": [g for _, g in ranked["one_piece"][:base_top_limit]],
    }
    # Shuffle impermeables para rotar cuál aparece primero y evitar siempre el mismo
    if rain:
        _waterproof_outer = [g for _, g in ranked["outerwear"] if g.waterproof]
        _non_waterproof_outer = [g for _, g in ranked["outerwear"] if not g.waterproof]
        if occasion == "matrimonio":
            _waterproof_outer = [
                g for g in _waterproof_outer
                if g.style not in ["sport"]
                and g.dress_level not in ["relajado"]
            ]
        random.shuffle(_waterproof_outer)
        top_candidates["outerwear"] = (_waterproof_outer + _non_waterproof_outer)[:4]
    else:
        top_candidates["outerwear"] = [g for _, g in ranked["outerwear"]][:4]
    # Shuffle accesorios para rotar cuál aparece en cada tanda y evitar siempre el mismo
    _accessories = [g for _, g in ranked["accessory"][:max(accessory_limit + 3, 5)]]
    random.shuffle(_accessories)
    top_candidates["accessory"] = _accessories  # pool completo; la rotación se maneja en la selección

    if occasion == "matrimonio":
        if mood == "sexy":
            _all_op = [g for _, g in ranked["one_piece"]]
            _enteritos = [g for g in _all_op if g.subcategory == "enterito"]
            _existing_ids = {g.id for g in top_candidates["one_piece"]}
            for g in _enteritos:
                if g.id not in _existing_ids:
                    top_candidates["one_piece"].append(g)

        _corte = 5 if mood == "sexy" else 4
        _sorted_one_piece = sorted(
            top_candidates["one_piece"],
            key=lambda g: (
                -1 if (g.subcategory == "enterito" and mood == "sexy") else
                0 if g.subcategory in ["vestido_elegante", "vestido_coctel"] else
                1 if g.subcategory == "vestido_casual" else 2
            )
        )[:_corte]

        if mood == "urbano":
            _existing_ids = {g.id for g in _sorted_one_piece}
            _urbano_extra = [
                g for _, g in ranked["one_piece"]
                if g.id not in _existing_ids and garment_has_style(g, "urbano")
            ]
            top_candidates["one_piece"] = _sorted_one_piece + _urbano_extra
        elif mood == "comodo":
            top_candidates["one_piece"] = [
                g for g in _sorted_one_piece
                if g.subcategory in ["vestido_casual", "enterito"]
            ]
        else:
            top_candidates["one_piece"] = _sorted_one_piece

        if top_candidates["one_piece"]:
            if mood == "urbano":
                top_candidates["top"] = [
                    g for g in top_candidates["top"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal") or garment_has_style(g, "urbano"))
                    and g.dress_level in ["arreglado", "elegante"]
                ][:3]
                top_candidates["bottom"] = [
                    g for g in top_candidates["bottom"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal") or garment_has_style(g, "urbano"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                    and g.subcategory not in ["buzo", "jogger", "legging", "short_casual", "jeans"]
                ][:3]
            elif mood == "comodo":
                top_candidates["top"] = [
                    g for g in top_candidates["top"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                ][:3]
                top_candidates["bottom"] = [
                    g for g in top_candidates["bottom"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                    and g.subcategory not in ["buzo", "jogger", "legging", "short_casual", "jeans"]
                ][:3]
            else:
                top_candidates["top"] = [
                    g for g in top_candidates["top"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                ][:3]
                top_candidates["bottom"] = [
                    g for g in top_candidates["bottom"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                    and g.subcategory not in ["buzo", "jogger", "legging", "short_casual", "jeans"]
                ][:3]

        if mood == "urbano":
            top_candidates["shoes"] = [
                g for g in top_candidates["shoes"]
                if g.subcategory not in ["zapatilla_urbana", "zapatilla_deporte"]
                or (g.subcategory == "zapatilla_urbana" and g.dress_level in ["arreglado", "elegante"])
            ]
        elif mood == "comodo":
            _shoes_pool = [
                g for _, g in ranked["shoes"]
                if g.subcategory not in ["taco_alto", "zapatilla_deporte"]
                or (g.subcategory == "zapatilla_urbana" and g.dress_level in ["arreglado", "elegante"])
            ]
            _seen_subs = {}
            for g in _shoes_pool:
                sub = g.subcategory or "otro"
                if sub not in _seen_subs:
                    _seen_subs[sub] = g
            top_candidates["shoes"] = list(_seen_subs.values())
            random.shuffle(top_candidates["shoes"])
        else:
            top_candidates["shoes"] = [
                g for g in top_candidates["shoes"]
                if g.subcategory not in ["mocasin", "botin", "bota", "zapatilla_urbana", "zapatilla_deporte"]
            ]

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
        if occasion == "matrimonio" and mood in ["urbano", "sexy"]:
            if temp > 25:
                top_candidates["midlayer"] = []
            else:
                top_candidates["midlayer"] = [
                    g for g in top_candidates["midlayer"]
                    if g.subcategory == "blazer" and g.warmth != "frio"
                ][:2]
        else:
            top_candidates["midlayer"] = [
                g for g in top_candidates["midlayer"] if g.warmth == "caluroso"
            ][:2]

    elif temp >= 16 and not rain:
        top_candidates["outerwear"] = []
        _mid_no_frio = [g for g in top_candidates["midlayer"] if g.warmth != "frio"]
        if occasion == "matrimonio":
            top_candidates["midlayer"] = _mid_no_frio[:4]
        else:
            top_candidates["midlayer"] = _mid_no_frio[:1]

    elif temp >= 13 and not rain:
        top_candidates["outerwear"] = [
            g for g in top_candidates["outerwear"]
            if g.warmth != "frio" and not g.waterproof
        ][:1]

    elif rain and temp >= 16:
        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"] if g.warmth != "frio"
        ][:1]
        top_candidates["outerwear"] = [
            g for g in top_candidates["outerwear"]
        ][:2]

    else:
        top_candidates["midlayer"] = top_candidates["midlayer"][:mid_limit]
        top_candidates["outerwear"] = top_candidates["outerwear"][:outer_limit]

    missing = get_missing_categories(top_candidates, required)
    if missing:
        return [], missing

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
            g.id for g in combo if g.category in ["top", "bottom", "one_piece", "shoes", "midlayer", "accessory"]
        ))

        if core_ids not in unique or score > unique[core_ids][0]:
            unique[core_ids] = (score, combo)

    for top in top_candidates["top"]:
        if occasion == "matrimonio":
            if mood not in ["urbano", "comodo"]:
                if not (
                    garment_has_style(top, "elegante") or garment_has_style(top, "formal")
                ):
                    continue
            else:
                if not (
                    (garment_has_style(top, "elegante") or garment_has_style(top, "formal") or garment_has_style(top, "urbano"))
                    and top.dress_level in ["arreglado", "elegante", "flexible"]
                ):
                    continue
        top_name = top.name.lower()
        top_is_outer_like = any(
            x in top_name
            for x in ["chaqueta", "blazer", "abrigo", "parka", "jacket"]
        )

        for bottom in top_candidates["bottom"]:
            if occasion == "matrimonio":
                if mood not in ["urbano", "comodo"]:
                    if not (
                        garment_has_style(bottom, "elegante") or garment_has_style(bottom, "formal")
                    ):
                        continue
                else:
                    if not (
                        (garment_has_style(bottom, "elegante") or garment_has_style(bottom, "formal") or garment_has_style(bottom, "urbano"))
                        and bottom.dress_level in ["arreglado", "elegante", "flexible"]
                    ):
                        continue
            for shoes in top_candidates["shoes"]:
                base = [top, bottom, shoes]
                include_accessory = occasion in ["matrimonio", "gala"] or random.random() < 0.6

                outerwear_required = "outerwear" in required and not top_is_outer_like

                if outerwear_required:
                    if "midlayer" in optional:
                        for mid in top_candidates["midlayer"]:
                            if top_candidates["outerwear"]:
                                for outer in top_candidates["outerwear"]:
                                    combo2 = base + [mid, outer]
                                    register_combo(combo2)

                                    if "accessory" in optional and include_accessory:
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

                            if "accessory" in optional and include_accessory:
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

                _force_mid = (
                    occasion == "matrimonio" and mood == "comodo"
                    and temp <= 15 and top_candidates["midlayer"]
                )
                _force_mid_outer = (
                    occasion == "matrimonio"
                    and temp <= 12 and top_candidates["midlayer"] and top_candidates["outerwear"]
                )
                _force_outer_only = (
                    occasion == "matrimonio"
                    and temp <= 12 and not top_candidates["midlayer"] and top_candidates["outerwear"]
                )
                if not _force_mid and not _force_outer_only and not _force_mid_outer:
                    register_combo(base)

                # Midlayer sin outerwear: permitido en matrimonio+urbano con calor
                if (
                    occasion == "matrimonio"
                    and mood == "urbano"
                    and temp >= 24
                ):
                    for mid in top_candidates["midlayer"]:
                        combo_mid = base + [mid]
                        register_combo(combo_mid)
                        if "accessory" in optional and include_accessory:
                            for acc in top_candidates["accessory"]:
                                combo_mid_acc = base + [mid, acc]
                                if should_include_accessory(
                                    acc, occasion, mood, activity, temp, rain, combo_mid
                                ):
                                    register_combo(combo_mid_acc)

                if "midlayer" in optional:
                    midlayer_candidates = top_candidates["midlayer"]

                    if temp >= 26:
                        midlayer_candidates = []
                    
                    for mid in midlayer_candidates:
                        combo = base + [mid]
                        if not _force_mid_outer:
                            register_combo(combo)

                        if "accessory" in optional and include_accessory and not _force_mid_outer:
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

                                if "accessory" in optional and include_accessory:
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

                if "outerwear" in optional and not top_is_outer_like and not _force_mid_outer:
                    for outer in top_candidates["outerwear"]:
                        combo = base + [outer]
                        register_combo(combo)

                if "accessory" in optional and include_accessory and not _force_mid_outer:
                    for acc in top_candidates["accessory"]:
                        combo = base + [acc]
                        if should_include_accessory(
                            acc, occasion, mood, activity, temp, rain, base
                        ):
                            register_combo(combo)

                if (
                    "outerwear" in optional
                    and "accessory" in optional and include_accessory
                    and not top_is_outer_like
                    and not _force_mid_outer
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
            include_accessory = occasion in ["matrimonio", "gala"] or random.random() < 0.6

            outerwear_required = "outerwear" in required and not one_piece_is_outer_like

            if outerwear_required:
                if "midlayer" in optional:
                    for mid in top_candidates["midlayer"]:
                        if top_candidates["outerwear"]:
                            for outer in top_candidates["outerwear"]:
                                combo2 = base + [mid, outer]
                                register_combo(combo2)

                                if "accessory" in optional and include_accessory:
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

                        if "accessory" in optional and include_accessory:
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

                if (
                    occasion == "matrimonio"
                    and mood in ["urbano", "sexy"]
                    and temp >= 24
                    and top_candidates["midlayer"]
                ):
                    for mid in top_candidates["midlayer"]:
                        combo_mid = base + [mid]
                        register_combo(combo_mid)
                        if "accessory" in optional and include_accessory:
                            for acc in top_candidates["accessory"]:
                                combo_mid_acc = base + [mid, acc]
                                if should_include_accessory(acc, occasion, mood, activity, temp, rain, base + [mid]):
                                    register_combo(combo_mid_acc)

                continue

            _force_mid = (
                occasion == "matrimonio" and mood == "comodo"
                and temp <= 15 and top_candidates["midlayer"]
            )
            _force_mid_outer = (
                occasion == "matrimonio"
                and temp <= 12 and top_candidates["midlayer"] and top_candidates["outerwear"]
            )
            _force_outer_only = (
                occasion == "matrimonio"
                and temp <= 12 and not top_candidates["midlayer"] and top_candidates["outerwear"]
            )
            if not _force_mid and not _force_outer_only and not _force_mid_outer:
                register_combo(base)

            if "midlayer" in optional and (
                occasion not in ["matrimonio", "gala", "salida nocturna", "cita"]
                or (occasion == "matrimonio" and mood in ["urbano", "sexy", "comodo"] and top_candidates["midlayer"])
            ):
                for mid in top_candidates["midlayer"]:
                    combo = base + [mid]
                    if not _force_mid_outer:
                        register_combo(combo)

                    if "accessory" in optional and include_accessory and not _force_mid_outer:
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

                            if "accessory" in optional and include_accessory:
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

            if "outerwear" in optional and not one_piece_is_outer_like and not _force_mid_outer:
                for outer in top_candidates["outerwear"]:
                    combo = base + [outer]
                    register_combo(combo)

            if "accessory" in optional and include_accessory and not _force_mid_outer:
                for acc in top_candidates["accessory"]:
                    combo = base + [acc]
                    if should_include_accessory(
                        acc, occasion, mood, activity, temp, rain, base
                    ):
                        register_combo(combo)

            if (
                "outerwear" in optional
                and "accessory" in optional and include_accessory
                and not one_piece_is_outer_like
                and not _force_mid_outer
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

    if not unique:
        return [], []

    final_outfits = sorted(unique.values(), key=lambda x: x[0], reverse=True)

    if occasion == "matrimonio" and mood not in ["urbano", "comodo"]:
        _vestido_outfits = sorted(
            [(s, c) for s, c in final_outfits if any(g.category == "one_piece" for g in c)],
            key=lambda x: x[0], reverse=True
        )
        _resto_outfits = sorted(
            [(s, c) for s, c in final_outfits if not any(g.category == "one_piece" for g in c)],
            key=lambda x: x[0], reverse=True
        )
        if len(_vestido_outfits) >= 2:
            final_outfits = _vestido_outfits[:2] + _resto_outfits + _vestido_outfits[2:]
        elif len(_vestido_outfits) == 1:
            final_outfits = _vestido_outfits + _resto_outfits
        else:
            final_outfits = _resto_outfits

    def is_too_similar(c1, c2):
        ow1 = next((g for g in c1 if g.category == "outerwear"), None)
        ow2 = next((g for g in c2 if g.category == "outerwear"), None)
        if ow1 and ow2 and ow1.id != ow2.id:
            return False

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
        # Excepción: si ambos combos tienen outerwear distinto, no son demasiado similares
        ow1 = ids1.get("outerwear")
        ow2 = ids2.get("outerwear")
        different_outerwear = (ow1 is not None and ow2 is not None and ow1 != ow2)
        if same_bottom_type and same_shoes_type and not different_outerwear:
            return True

        # reglas existentes (más suaves)
        if same_top and same_bottom:
            return True

        if same_top and same_shoes:
            return True

        if same_top and same_one_piece:
            return True

        if same_one_piece and same_shoes:
            return True

        if same_one_piece and ids1.get("one_piece") is not None:
            return True

        return False

    diverse_outfits = []
    midlayer_outfits_count = 0
    if occasion == "matrimonio":
        max_midlayer_outfits = 1 if temp >= 24 else top_n
    else:
        max_midlayer_outfits = 1 if 24 <= temp < 26 else top_n
    top_usage = {}
    shoes_usage = {}
    midlayer_usage = {}
    one_piece_usage = {}
    outerwear_usage = {}
    accessory_usage_in_batch = {}
    accessory_outfits_count = 0
    max_accessory_outfits = top_n if occasion in ["matrimonio", "gala"] else random.choice([1, 1, 2])
    max_same_top = 1 if occasion in ["matrimonio", "gala"] else (2 if top_n >= 3 else 1)
    if occasion == "matrimonio" and mood == "comodo":
        max_same_shoes = 1
    elif occasion == "matrimonio":
        max_same_shoes = 2
    else:
        max_same_shoes = 2 if top_n >= 3 else 1
    _n_blazers = sum(1 for g in top_candidates["midlayer"] if g.subcategory == "blazer")
    if occasion == "matrimonio":
        if _n_blazers >= 3:
            max_same_midlayer = 1
        elif _n_blazers >= 2:
            max_same_midlayer = 2
        else:
            max_same_midlayer = top_n
    elif 24 <= temp <= 25:
        max_same_midlayer = 1
    else:
        max_same_midlayer = min(2, top_n)
    _n_one_pieces = len(top_candidates.get("one_piece", []))
    max_same_one_piece = 1 if _n_one_pieces >= 2 else top_n
    if occasion in ["cita", "salida nocturna"]:
        elegant_shoes = [g for g in top_candidates["shoes"]
                         if g.subcategory in ["taco_alto", "taco_bajo", "sandalia"]]
        if len(elegant_shoes) >= 2:
            max_same_shoes = 1
    _n_waterproof_outer = sum(1 for g in top_candidates["outerwear"] if g.waterproof)
    if not rain:
        max_same_outerwear = 1
    elif _n_waterproof_outer >= 3:
        max_same_outerwear = 1
    elif _n_waterproof_outer == 2:
        max_same_outerwear = 2
    elif _n_waterproof_outer == 1:
        max_same_outerwear = 3
    else:
        max_same_outerwear = 2
    remaining_outfits = list(final_outfits)

    # Para matrimonio: forzar vestidos — solo para moods que no sean urbano
    if occasion == "matrimonio" and mood not in ["urbano", "comodo"]:
        _max_forced_vestidos = 3 if mood == "sexy" else 2
        _all_vestido_outfits = [(s, c) for s, c in remaining_outfits if any(g.category == "one_piece" for g in c)]
        # Intercalar: tomar el mejor combo de cada vestido distinto en orden round-robin
        _vestido_by_id = {}
        for s, c in _all_vestido_outfits:
            op = next((g for g in c if g.category == "one_piece"), None)
            if op and op.id not in _vestido_by_id:
                _vestido_by_id[op.id] = (s, c)
        # Ordenar los vestidos disponibles por score de su mejor combo
        _vestidos_remaining = sorted(_vestido_by_id.values(), key=lambda x: x[0], reverse=True)
        # Agregar combos adicionales del mismo vestido al final (por si no hay 3 vestidos distintos)
        _seen = set(_vestido_by_id.keys())
        for s, c in _all_vestido_outfits:
            op = next((g for g in c if g.category == "one_piece"), None)
            if op and op.id in _seen and (s, c) not in _vestidos_remaining:
                _vestidos_remaining.append((s, c))
        _resto_remaining = [(s, c) for s, c in remaining_outfits if not any(g.category == "one_piece" for g in c)]

        matrimonio_forced = []
        _used_one_piece_ids = set()
        for s, c in _vestidos_remaining:
            if len(matrimonio_forced) >= _max_forced_vestidos:
                break
            one_piece = next((g for g in c if g.category == "one_piece"), None)
            if one_piece and one_piece.id in _used_one_piece_ids:
                continue
            if one_piece:
                _used_one_piece_ids.add(one_piece.id)
            mid = next((g for g in c if g.category == "midlayer"), None)
            if mid and midlayer_usage.get(mid.id, 0) >= max_same_midlayer:
                continue
            one_piece_id = next((g.id for g in c if g.category == "one_piece"), None)
            if one_piece_id is not None and one_piece_usage.get(one_piece_id, 0) >= max_same_one_piece:
                continue
            shoes = next((g for g in c if g.category == "shoes"), None)
            if shoes and shoes_usage.get(shoes.id, 0) >= max_same_shoes:
                continue
            outer = next((g for g in c if g.category == "outerwear"), None)
            if outer and outerwear_usage.get(outer.id, 0) >= max_same_outerwear:
                continue
            if s < 0:
                continue
            if mid:
                midlayer_usage[mid.id] = midlayer_usage.get(mid.id, 0) + 1
            if one_piece_id is not None:
                one_piece_usage[one_piece_id] = one_piece_usage.get(one_piece_id, 0) + 1
            if shoes:
                shoes_usage[shoes.id] = shoes_usage.get(shoes.id, 0) + 1
            if outer:
                outerwear_usage[outer.id] = outerwear_usage.get(outer.id, 0) + 1
            matrimonio_forced.append((s, c))

        for s, c in matrimonio_forced:
            remaining_outfits.remove((s, c))
            diverse_outfits.append((s, c))
            ids = {g.category: g.id for g in c}
            top_id = ids.get("top")
            acc_id = ids.get("accessory")
            if top_id: top_usage[top_id] = top_usage.get(top_id, 0) + 1
            if acc_id:
                accessory_outfits_count += 1
                accessory_usage_in_batch[acc_id] = accessory_usage_in_batch.get(acc_id, 0) + 1
            if any(g.category == "midlayer" for g in c):
                midlayer_outfits_count += 1

    while len(diverse_outfits) < top_n and remaining_outfits:
        best_idx = None
        best_effective = float('-inf')

        for i, (score, combo) in enumerate(remaining_outfits):
            if occasion == "matrimonio" and mood == "sexy":
                if not any(g.category == "one_piece" for g in combo):
                    continue
            if score < 0:
                continue
            ids = {g.category: g.id for g in combo}
            has_midlayer = any(g.category == "midlayer" for g in combo)
            top_id = ids.get("top")
            shoes_id = ids.get("shoes")
            midlayer_id = ids.get("midlayer")
            outerwear_id = ids.get("outerwear")
            acc_id = ids.get("accessory")

            if has_midlayer and midlayer_outfits_count >= max_midlayer_outfits:
                continue
            if midlayer_id is not None and midlayer_usage.get(midlayer_id, 0) >= max_same_midlayer:
                continue
            one_piece_id = ids.get("one_piece")
            if one_piece_id is not None and one_piece_usage.get(one_piece_id, 0) >= max_same_one_piece:
                continue
            if top_id is not None and top_usage.get(top_id, 0) >= max_same_top:
                continue
            if shoes_id is not None and shoes_usage.get(shoes_id, 0) >= max_same_shoes:
                continue
            if outerwear_id is not None and outerwear_usage.get(outerwear_id, 0) >= max_same_outerwear:
                continue
            if acc_id is not None and accessory_outfits_count >= max_accessory_outfits:
                continue

            too_similar = False
            for _, existing in diverse_outfits:
                ids_ex = {g.category: g.id for g in existing}
                if is_too_similar(combo, existing):
                    too_similar = True
                    break
                if ids.get("one_piece") is not None and ids.get("one_piece") == ids_ex.get("one_piece"):
                    if occasion not in ["matrimonio", "gala"]:
                        too_similar = True
                        break
                if ids.get("bottom") == ids_ex.get("bottom") and ids.get("shoes") == ids_ex.get("shoes"):
                    too_similar = True
                    break
            if too_similar:
                continue

            penalty = 30 * accessory_usage_in_batch.get(acc_id, 0) if acc_id else 0
            effective = score - penalty

            if effective > best_effective:
                best_effective = effective
                best_idx = i

        if best_idx is None:
            break

        score, combo = remaining_outfits.pop(best_idx)
        ids = {g.category: g.id for g in combo}
        has_midlayer = any(g.category == "midlayer" for g in combo)
        top_id = ids.get("top")
        shoes_id = ids.get("shoes")
        midlayer_id = ids.get("midlayer")
        outerwear_id = ids.get("outerwear")
        acc_id = ids.get("accessory")

        diverse_outfits.append((score, combo))

        if has_midlayer:
            midlayer_outfits_count += 1
        if top_id is not None:
            top_usage[top_id] = top_usage.get(top_id, 0) + 1
        if shoes_id is not None:
            shoes_usage[shoes_id] = shoes_usage.get(shoes_id, 0) + 1
        if midlayer_id is not None:
            midlayer_usage[midlayer_id] = midlayer_usage.get(midlayer_id, 0) + 1
        if one_piece_id is not None:
            one_piece_usage[one_piece_id] = one_piece_usage.get(one_piece_id, 0) + 1
        if outerwear_id is not None:
            outerwear_usage[outerwear_id] = outerwear_usage.get(outerwear_id, 0) + 1
        if acc_id is not None:
            accessory_outfits_count += 1
            accessory_usage_in_batch[acc_id] = accessory_usage_in_batch.get(acc_id, 0) + 1

    # Fallback: si no llegamos a 3 outfits, segunda pasada sin filtro is_too_similar
    min_outfits = min(3, top_n)
    if len(diverse_outfits) < min_outfits:
        existing_ids = {id(combo) for _, combo in diverse_outfits}
        for score, combo in sorted(remaining_outfits, key=lambda x: x[0], reverse=True):
            if len(diverse_outfits) >= min_outfits:
                break
            if id(combo) in existing_ids:
                continue
            if occasion == "matrimonio" and mood == "sexy":
                if not any(g.category == "one_piece" for g in combo):
                    continue
            ids = {g.category: g.id for g in combo}
            outerwear_id = ids.get("outerwear")
            top_id = ids.get("top")
            shoes_id = ids.get("shoes")
            midlayer_id = ids.get("midlayer")
            one_piece_id = ids.get("one_piece")
            if top_id is not None and top_usage.get(top_id, 0) >= max_same_top:
                continue
            if shoes_id is not None and shoes_usage.get(shoes_id, 0) >= max_same_shoes:
                continue
            if midlayer_id is not None and midlayer_usage.get(midlayer_id, 0) >= max_same_midlayer:
                continue
            if one_piece_id is not None and one_piece_usage.get(one_piece_id, 0) >= max_same_one_piece:
                continue
            if outerwear_id is not None and outerwear_usage.get(outerwear_id, 0) >= max_same_outerwear:
                continue
            if score < 0:
                continue
            diverse_outfits.append((score, combo))
            existing_ids.add(id(combo))
            if top_id is not None:
                top_usage[top_id] = top_usage.get(top_id, 0) + 1
            if shoes_id is not None:
                shoes_usage[shoes_id] = shoes_usage.get(shoes_id, 0) + 1
            if midlayer_id is not None:
                midlayer_usage[midlayer_id] = midlayer_usage.get(midlayer_id, 0) + 1
            if one_piece_id is not None:
                one_piece_usage[one_piece_id] = one_piece_usage.get(one_piece_id, 0) + 1
            if outerwear_id is not None:
                outerwear_usage[outerwear_id] = outerwear_usage.get(outerwear_id, 0) + 1

    # Tercera pasada: relajar max_same_outerwear si el outerwear disponible es escaso
    if len(diverse_outfits) < min_outfits:
        existing_ids = {id(combo) for _, combo in diverse_outfits}
        all_remaining = sorted(
            [(s, c) for s, c in final_outfits if id(c) not in existing_ids],
            key=lambda x: x[0],
            reverse=True,
        )
        best_score = diverse_outfits[0][0] if diverse_outfits else 0
        for score, combo in all_remaining:
            if len(diverse_outfits) >= min_outfits:
                break
            if id(combo) in existing_ids:
                continue
            if occasion == "matrimonio" and mood == "sexy":
                if not any(g.category == "one_piece" for g in combo):
                    continue
            ids = {g.category: g.id for g in combo}
            top_id = ids.get("top")
            shoes_id = ids.get("shoes")
            midlayer_id = ids.get("midlayer")
            one_piece_id = ids.get("one_piece")
            if top_id is not None and top_usage.get(top_id, 0) >= max_same_top:
                continue
            if shoes_id is not None and shoes_usage.get(shoes_id, 0) >= max_same_shoes:
                continue
            if midlayer_id is not None and midlayer_usage.get(midlayer_id, 0) >= max_same_midlayer:
                continue
            if one_piece_id is not None and one_piece_usage.get(one_piece_id, 0) >= max_same_one_piece:
                continue
            outerwear_id = ids.get("outerwear")
            _outerwear_limit = (
                max_same_outerwear + 1
                if occasion == "matrimonio" and len(diverse_outfits) < min_outfits
                else max_same_outerwear
            )
            if outerwear_id is not None and outerwear_usage.get(outerwear_id, 0) >= _outerwear_limit:
                continue
            # max_same_outerwear relajado: permitir repetir outerwear cuando es el único disponible
            # Umbral mínimo: solo aplicar cuando ya hay 2+ outfits aceptados
            if len(diverse_outfits) >= 2 and best_score > 0:
                threshold = best_score * (0.20 if occasion == "matrimonio" else 0.35)
                if score < threshold:
                    continue
            if score < 0:
                continue
            diverse_outfits.append((score, combo))
            existing_ids.add(id(combo))
            if top_id is not None:
                top_usage[top_id] = top_usage.get(top_id, 0) + 1
            if shoes_id is not None:
                shoes_usage[shoes_id] = shoes_usage.get(shoes_id, 0) + 1
            if midlayer_id is not None:
                midlayer_usage[midlayer_id] = midlayer_usage.get(midlayer_id, 0) + 1
            if one_piece_id is not None:
                one_piece_usage[one_piece_id] = one_piece_usage.get(one_piece_id, 0) + 1

    return diverse_outfits[:top_n], []


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
    required = rules["required"]
    optional = rules["optional"]

    if not ignore_occasion_for_selected:
        selected_allowed, _ = garment_allowed_for_occasion(selected_garment, occasion, rain, mood, temp)
        if not selected_allowed:
            return [], []

    if occasion == "matrimonio" and mood == "elegante" and not ignore_occasion_for_selected:
        return _generate_matrimonio_elegante(
            garments=garments,
            temp=temp,
            rain=rain,
            mood=mood,
            activity=activity,
            top_n=top_n,
            feedback_list=feedback_list,
            recent_outfits=recent_outfits,
            user_profile=build_user_style_profile(feedback_list, garments),
            selected_garment=selected_garment,
        )

    if occasion == "gala" and not ignore_occasion_for_selected:
        return _generate_gala(
            garments=garments,
            temp=temp,
            rain=rain,
            mood=mood,
            activity=activity,
            top_n=top_n,
            feedback_list=feedback_list,
            recent_outfits=recent_outfits,
            user_profile=build_user_style_profile(feedback_list, garments),
            selected_garment=selected_garment,
        )

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
    outer_limit = 3
    accessory_limit = 1

    if occasion in ["matrimonio", "gala", "cita", "salida nocturna"]:
        base_top_limit = 6
        base_bottom_limit = 6
        base_shoes_limit = 5
        accessory_limit = 2

    if activity == "caminar" or rain:
        base_shoes_limit = 5
        outer_limit = 3

    top_candidates = {
        "top": [g for _, g in ranked["top"][:base_top_limit]],
        "bottom": [g for _, g in ranked["bottom"][:base_bottom_limit]],
        "shoes": [g for _, g in ranked["shoes"][:base_shoes_limit]],
        "midlayer": [g for _, g in ranked["midlayer"][:4]],
        "accessory": [g for _, g in ranked["accessory"][:accessory_limit]],
        "one_piece": [g for _, g in ranked["one_piece"][:base_top_limit]],
    }
    if rain:
        _waterproof_outer = [g for _, g in ranked["outerwear"] if g.waterproof]
        _non_waterproof_outer = [g for _, g in ranked["outerwear"] if not g.waterproof]
        if occasion == "matrimonio":
            _waterproof_outer = [
                g for g in _waterproof_outer
                if g.style not in ["sport"]
                and g.dress_level not in ["relajado"]
            ]
        random.shuffle(_waterproof_outer)
        top_candidates["outerwear"] = (_waterproof_outer + _non_waterproof_outer)[:4]
    else:
        top_candidates["outerwear"] = [g for _, g in ranked["outerwear"]][:4]

    # =========================================================
    # FILTROS DE CLIMA — ordenados correctamente
    # =========================================================
    if temp >= 24:
        top_candidates["outerwear"] = []
        if occasion == "matrimonio" and mood in ["urbano", "sexy"]:
            if temp > 25:
                top_candidates["midlayer"] = []
            else:
                top_candidates["midlayer"] = [
                    g for g in top_candidates["midlayer"]
                    if g.subcategory == "blazer" and g.warmth != "frio"
                ][:2]
        else:
            top_candidates["midlayer"] = [
                g for g in top_candidates["midlayer"] if g.warmth == "caluroso"
            ][:2]

    elif temp >= 16 and not rain:
        top_candidates["outerwear"] = []
        _mid_no_frio = [g for g in top_candidates["midlayer"] if g.warmth != "frio"]
        if occasion == "matrimonio":
            top_candidates["midlayer"] = _mid_no_frio[:4]
        else:
            top_candidates["midlayer"] = _mid_no_frio[:1]

    elif temp >= 13 and not rain:
        top_candidates["outerwear"] = [
            g for g in top_candidates["outerwear"]
            if g.warmth != "frio" and not g.waterproof
        ][:1]

    elif rain and temp >= 16:
        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"] if g.warmth != "frio"
        ][:1]
        top_candidates["outerwear"] = [
            g for g in top_candidates["outerwear"]
        ][:2]

    else:
        top_candidates["midlayer"] = top_candidates["midlayer"][:mid_limit]
        top_candidates["outerwear"] = top_candidates["outerwear"][:outer_limit]

    # Filtros especiales por ocasión — igual que generate_outfits
    if occasion == "matrimonio":
        _sorted_one_piece = sorted(
            top_candidates["one_piece"],
            key=lambda g: (
                0 if g.subcategory in ["vestido_elegante", "vestido_coctel"] else
                0 if (g.subcategory == "enterito" and mood == "sexy") else
                1 if g.subcategory == "vestido_casual" else 2
            )
        )[:4]

        if mood == "urbano":
            _existing_ids = {g.id for g in _sorted_one_piece}
            _urbano_extra = [
                g for _, g in ranked["one_piece"]
                if g.id not in _existing_ids and garment_has_style(g, "urbano")
            ]
            top_candidates["one_piece"] = _sorted_one_piece + _urbano_extra
        elif mood == "comodo":
            top_candidates["one_piece"] = [
                g for g in _sorted_one_piece
                if g.subcategory in ["vestido_casual", "enterito"]
            ]
        else:
            top_candidates["one_piece"] = _sorted_one_piece

        if top_candidates["one_piece"]:
            if mood == "urbano":
                top_candidates["top"] = [
                    g for g in top_candidates["top"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal") or garment_has_style(g, "urbano"))
                    and g.dress_level in ["arreglado", "elegante"]
                ][:3]
                top_candidates["bottom"] = [
                    g for g in top_candidates["bottom"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal") or garment_has_style(g, "urbano"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                    and g.subcategory not in ["buzo", "jogger", "legging", "short_casual", "jeans"]
                ][:3]
            elif mood == "comodo":
                top_candidates["top"] = [
                    g for g in top_candidates["top"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                ][:3]
                top_candidates["bottom"] = [
                    g for g in top_candidates["bottom"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                    and g.subcategory not in ["buzo", "jogger", "legging", "short_casual", "jeans"]
                ][:3]
            else:
                top_candidates["top"] = [
                    g for g in top_candidates["top"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                ][:3]
                top_candidates["bottom"] = [
                    g for g in top_candidates["bottom"]
                    if (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
                    and g.dress_level in ["arreglado", "elegante", "flexible"]
                    and g.subcategory not in ["buzo", "jogger", "legging", "short_casual", "jeans"]
                ][:3]

        top_candidates["midlayer"] = [
            g for g in top_candidates["midlayer"]
            if g.subcategory == "blazer"
            and (garment_has_style(g, "elegante") or garment_has_style(g, "formal"))
            and g.dress_level in ["arreglado", "elegante"]
        ][:3]

        if mood == "urbano":
            top_candidates["shoes"] = [
                g for g in top_candidates["shoes"]
                if g.subcategory not in ["zapatilla_urbana", "zapatilla_deporte"]
                or (g.subcategory == "zapatilla_urbana" and g.dress_level in ["arreglado", "elegante"])
            ]
        elif mood == "comodo":
            _shoes_pool = [
                g for _, g in ranked["shoes"]
                if g.subcategory not in ["taco_alto", "zapatilla_deporte"]
                or (g.subcategory == "zapatilla_urbana" and g.dress_level in ["arreglado", "elegante"])
            ]
            _seen_subs = {}
            for g in _shoes_pool:
                sub = g.subcategory or "otro"
                if sub not in _seen_subs:
                    _seen_subs[sub] = g
            top_candidates["shoes"] = list(_seen_subs.values())
            random.shuffle(top_candidates["shoes"])
        else:
            top_candidates["shoes"] = [
                g for g in top_candidates["shoes"]
                if g.subcategory not in ["mocasin", "botin", "bota", "zapatilla_urbana", "zapatilla_deporte"]
            ]

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

    tc_for_check = dict(top_candidates)
    sel_cat = selected_garment.category
    if sel_cat == "one_piece":
        tc_for_check["top"] = [selected_garment] + tc_for_check.get("top", [])
        tc_for_check["one_piece"] = [selected_garment] + tc_for_check.get("one_piece", [])
    else:
        tc_for_check[sel_cat] = [selected_garment] + tc_for_check.get(sel_cat, [])
    missing = get_missing_categories(tc_for_check, required)
    if missing:
        return [], missing

    outfits = []
    selected_category = selected_garment.category

    def add_combo(combo: List[Garment]):
        if invalid_pattern_combo(combo):
            return

        for g in combo:
            if g.id == selected_garment.id:
                continue
            allowed, _ = garment_allowed_for_occasion(g, occasion, rain, mood, temp)
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
        include_accessory = occasion in ["matrimonio", "gala"] or random.random() < 0.6
        top_is_outer_like = False
        if top_item is not None:
            top_name = top_item.name.lower()
            top_is_outer_like = any(
                x in top_name for x in ["chaqueta", "blazer", "abrigo", "parka", "jacket"]
            )

        has_midlayer = any(g.category == "midlayer" for g in base)
        has_outerwear = any(g.category == "outerwear" for g in base)
        has_accessory = any(g.category == "accessory" for g in base)

        outerwear_required = "outerwear" in required and not has_outerwear and not top_is_outer_like

        if outerwear_required:
            if "midlayer" in optional and not has_midlayer:
                for mid in top_candidates["midlayer"][:3]:
                    for outer in top_candidates["outerwear"][:4]:
                        add_combo(base + [mid, outer])
            for outer in top_candidates["outerwear"][:3]:
                add_combo(base + [outer])
                if "accessory" in optional and include_accessory and not has_accessory:
                    for acc in top_candidates["accessory"][:2]:
                        if should_include_accessory(
                            acc, occasion, mood, activity, temp, rain, base + [outer]
                        ):
                            add_combo(base + [outer, acc])
            return

        _force_mid = (
            occasion == "matrimonio" and mood == "comodo"
            and temp <= 15 and top_candidates["midlayer"]
        )
        _force_mid_outer = (
            occasion == "matrimonio"
            and temp <= 12 and top_candidates["midlayer"] and top_candidates["outerwear"]
        )
        _force_outer_only = (
            occasion == "matrimonio"
            and temp <= 12 and not top_candidates["midlayer"] and top_candidates["outerwear"]
        )
        if not _force_mid and not _force_outer_only and not _force_mid_outer:
            add_combo(base)

        has_one_piece = any(g.category == "one_piece" for g in base)

        matrimonio_midlayer_allowed = (
            occasion == "matrimonio"
            and mood in ["urbano", "sexy", "comodo"]
            and temp >= 24
        )
        if (
            "midlayer" in optional
            and not has_midlayer
            and (
                _force_mid
                or not (has_one_piece and occasion in ["matrimonio", "gala", "salida nocturna", "cita"] and not matrimonio_midlayer_allowed)
            )
        ):
            for mid in top_candidates["midlayer"][:3]:
                combo_mid = base + [mid]
                if not _force_mid_outer:
                    add_combo(combo_mid)

                if "outerwear" in optional and not has_outerwear and not top_is_outer_like:
                    for outer in top_candidates["outerwear"][:4]:
                        combo_mid_outer = combo_mid + [outer]
                        add_combo(combo_mid_outer)

                if "accessory" in optional and include_accessory and not has_accessory and not _force_mid_outer:
                    for acc in top_candidates["accessory"][:4]:
                        combo_mid_acc = combo_mid + [acc]
                        if should_include_accessory(
                            acc, occasion, mood, activity, temp, rain, combo_mid
                        ):
                            add_combo(combo_mid_acc)

        if "outerwear" in optional and not has_outerwear and not top_is_outer_like and not _force_mid_outer:
            for outer in top_candidates["outerwear"][:3]:
                combo_outer = base + [outer]
                add_combo(combo_outer)

                if "accessory" in optional and include_accessory and not has_accessory:
                    for acc in top_candidates["accessory"][:2]:
                        combo_outer_acc = combo_outer + [acc]
                        if should_include_accessory(
                            acc, occasion, mood, activity, temp, rain, combo_outer
                        ):
                            add_combo(combo_outer_acc)

        if "accessory" in optional and include_accessory and not has_accessory and not _force_mid_outer:
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
            if occasion == "matrimonio" or (occasion == "cita" and mood == "elegante"):
                if not (occasion == "matrimonio" and mood in ["urbano", "comodo"]):
                    if not (garment_has_style(top, "elegante") or garment_has_style(top, "formal")):
                        continue
                else:
                    if not (
                        (garment_has_style(top, "elegante") or garment_has_style(top, "formal") or garment_has_style(top, "urbano"))
                        and top.dress_level in ["arreglado", "elegante", "flexible"]
                    ):
                        continue
            for bottom in top_candidates["bottom"]:
                if occasion == "matrimonio" or (occasion == "cita" and mood == "elegante"):
                    if not (occasion == "matrimonio" and mood in ["urbano", "comodo"]):
                        if not (garment_has_style(bottom, "elegante") or garment_has_style(bottom, "formal")):
                            continue
                    else:
                        if not (
                            (garment_has_style(bottom, "elegante") or garment_has_style(bottom, "formal") or garment_has_style(bottom, "urbano"))
                            and bottom.dress_level in ["arreglado", "elegante", "flexible"]
                        ):
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
                    include_accessory = occasion in ["matrimonio", "gala"] or random.random() < 0.6
                    add_combo(base)

                    if "midlayer" in optional:
                        for mid in top_candidates["midlayer"][:3]:
                            combo = [top, bottom, shoes, mid, selected_garment]
                            add_combo(combo)

                    if "accessory" in optional and include_accessory:
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
                include_accessory = occasion in ["matrimonio", "gala"] or random.random() < 0.6
                add_combo(base)

                if "midlayer" in optional:
                    for mid in top_candidates["midlayer"][:3]:
                        combo = [one_piece, shoes, mid, selected_garment]
                        add_combo(combo)

                if "accessory" in optional and include_accessory:
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

    if not outfits:
        return [], []

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
        ow1 = next((g for g in c1 if g.category == "outerwear"), None)
        ow2 = next((g for g in c2 if g.category == "outerwear"), None)
        if ow1 and ow2 and ow1.id != ow2.id:
            return False

        ids1 = {g.category: g.id for g in c1}
        ids2 = {g.category: g.id for g in c2}

        same_top = ids1.get("top") == ids2.get("top")
        same_bottom = ids1.get("bottom") == ids2.get("bottom")
        same_one_piece = ids1.get("one_piece") == ids2.get("one_piece")
        same_shoes = ids1.get("shoes") == ids2.get("shoes")

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

        ow1 = ids1.get("outerwear")
        ow2 = ids2.get("outerwear")
        different_outerwear = (ow1 is not None and ow2 is not None and ow1 != ow2)
        if same_bottom_type and same_shoes_type and not different_outerwear:
            return True

        if same_top and same_bottom:
            return True

        if same_top and same_shoes:
            return True

        if same_top and same_one_piece:
            return True

        if same_one_piece and same_shoes:
            return True

        if same_one_piece and ids1.get("one_piece") is not None:
            return True

        return False

    diverse = []
    for score, combo in final_outfits:
        too_similar = any(is_too_similar(combo, c) for _, c in diverse)
        if not too_similar:
            diverse.append((score, combo))
        if len(diverse) >= top_n:
            break

    return diverse[:top_n], []


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

        outfits, _ = generate_outfits(
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
            outfits, _ = generate_outfits(
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