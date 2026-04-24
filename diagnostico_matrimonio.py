"""
Diagnóstico generate_outfits — ocasión matrimonio
Todas las combinaciones mood x temp, rain=False (+ segunda pasada comodo rain=True)
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

from models import Garment
from engine.recommender import generate_outfits

# ─────────────────────────────────────────────
# ARMARIO SINTÉTICO
# ─────────────────────────────────────────────
def G(id, name, category, style, subcategory=None,
      warmth="medio", waterproof=False, dress_level="flexible",
      sexiness=0, secondary_styles=None):
    return Garment(
        id=id, name=name, category=category, color="negro",
        style=style, subcategory=subcategory,
        warmth=warmth, waterproof=waterproof, dress_level=dress_level,
        sexiness=sexiness, secondary_styles=secondary_styles or [],
    )

garments = [
    # ── TOPS elegantes/formales ──
    G(1,  "Blusa seda blanca",        "top",      "elegante",  "blusa",       dress_level="elegante"),
    G(2,  "Camisa formal blanca",     "top",      "formal",    "camisa",      dress_level="arreglado"),
    G(3,  "Top lentejuelas dorado",   "top",      "elegante",  "top",         dress_level="elegante", sexiness=3),
    G(4,  "Blusa satén nude",         "top",      "elegante",  "blusa",       dress_level="arreglado"),
    G(5,  "Blusa urbana arreglada",   "top",      "urbano",    "blusa",       dress_level="arreglado"),
    G(6,  "Camiseta urbana negra",    "top",      "urbano",    "camiseta",    dress_level="flexible"),

    # ── BOTTOMS elegantes/formales ──
    G(10, "Falda midi satén",         "bottom",   "elegante",  "falda_larga", dress_level="elegante"),
    G(11, "Pantalón formal negro",    "bottom",   "formal",    "pantalon",    dress_level="arreglado"),
    G(12, "Pantalón palazzo",         "bottom",   "elegante",  "pantalon",    dress_level="elegante"),
    G(13, "Falda lápiz negra",        "bottom",   "formal",    "falda_lapiz", dress_level="arreglado"),
    G(14, "Pantalón urbano gris",     "bottom",   "urbano",    "pantalon",    dress_level="arreglado"),
    G(15, "Jean skinny negro",        "bottom",   "casual",    "jeans",       dress_level="flexible"),

    # ── ONE PIECE ──
    G(20, "Vestido elegante negro",   "one_piece","elegante",  "vestido_elegante", dress_level="elegante", sexiness=2),
    G(21, "Vestido cóctel azul",      "one_piece","elegante",  "vestido_coctel",   dress_level="elegante", sexiness=2),
    G(22, "Vestido casual floral",    "one_piece","casual",    "vestido_casual",   dress_level="flexible"),
    G(23, "Enterito negro",           "one_piece","elegante",  "enterito",         dress_level="arreglado", sexiness=3),
    G(24, "Vestido urbano midi",      "one_piece","urbano",    "vestido_casual",   dress_level="arreglado"),

    # ── MIDLAYER ──
    G(30, "Blazer elegante negro",    "midlayer", "elegante",  "blazer",      warmth="medio",   dress_level="elegante"),
    G(31, "Blazer formal gris",       "midlayer", "formal",    "blazer",      warmth="frio",    dress_level="arreglado"),
    G(32, "Blazer urbano azul",       "midlayer", "urbano",    "blazer",      warmth="medio",   dress_level="arreglado"),
    G(33, "Blazer casual beige",      "midlayer", "casual",    "blazer",      warmth="caluroso",dress_level="flexible"),

    # ── OUTERWEAR ──
    G(40, "Abrigo largo negro",       "outerwear","elegante",  "abrigo",      warmth="frio",    dress_level="elegante"),
    G(41, "Trench beige",             "outerwear","elegante",  "trench",      warmth="medio",   dress_level="arreglado"),
    G(42, "Abrigo midi gris",         "outerwear","formal",    "abrigo",      warmth="frio",    dress_level="arreglado"),
    G(43, "Impermeable sport",        "outerwear","sport",     "impermeable", warmth="medio",   waterproof=True, dress_level="relajado"),
    G(44, "Impermeable elegante",     "outerwear","elegante",  "impermeable", warmth="medio",   waterproof=True, dress_level="arreglado"),
    G(45, "Parka urbana",             "outerwear","urbano",    "parka",       warmth="frio",    dress_level="flexible"),

    # ── SHOES ──
    G(50, "Taco alto negro",          "shoes",    "elegante",  "taco_alto",   dress_level="elegante"),
    G(51, "Taco bajo nude",           "shoes",    "elegante",  "taco_bajo",   dress_level="arreglado"),
    G(52, "Sandalia dorada",          "shoes",    "elegante",  "sandalia",    dress_level="elegante"),
    G(53, "Zapatilla urbana blanca",  "shoes",    "urbano",    "zapatilla_urbana", dress_level="arreglado"),
    G(54, "Botín negro",              "shoes",    "urbano",    "botin",       dress_level="arreglado"),
    G(55, "Mocasín cuero",            "shoes",    "formal",    "mocasin",     dress_level="arreglado"),
    G(56, "Zapatilla deporte",        "shoes",    "sport",     "zapatilla_deporte", dress_level="relajado"),

    # ── ACCESSORIES ──
    G(60, "Collar perlas",            "accessory","elegante",  None,          dress_level="elegante"),
    G(61, "Clutch dorado",            "accessory","elegante",  None,          dress_level="elegante"),
    G(62, "Cinturón cuero",           "accessory","formal",    None,          dress_level="arreglado"),
    G(63, "Gorro lana gris",          "accessory","casual",    "gorro",       dress_level="relajado"),
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fmt_outfit(score, combo):
    cats = {g.category: g.name for g in combo}
    has_mid = any(g.category == "midlayer" for g in combo)
    has_outer = any(g.category == "outerwear" for g in combo)

    prendas = []
    for cat in ["top", "one_piece", "bottom", "shoes"]:
        if cat in cats:
            prendas.append(f"{cats[cat]} ({cat})")
    extras = []
    if has_mid:
        extras.append(f"+ {cats['midlayer']} [MID]")
    if has_outer:
        extras.append(f"+ {cats['outerwear']} [OUTER]")
    if "accessory" in cats:
        extras.append(f"+ {cats['accessory']} [ACC]")

    return f"    score {score:5.1f}: {', '.join(prendas)} {' '.join(extras)}"


def run_combo(mood, temp, rain=False):
    outfits, missing = generate_outfits(
        garments=garments,
        occasion="matrimonio",
        temp=temp,
        rain=rain,
        mood=mood,
        activity="parado",
        top_n=3,
    )
    tag = f"[{mood.upper()} {temp}°{'☔' if rain else ''}]"
    print(f"\n{tag}")
    if missing:
        print(f"  ⚠ Faltan categorías: {missing}")
        return
    if not outfits:
        print("  ❌ Sin outfits generados")
        return
    for i, (score, combo) in enumerate(outfits, 1):
        print(f"  Outfit {i}{fmt_outfit(score, combo)}")


# ─────────────────────────────────────────────
# PASADA 1: rain=False, todos los moods
# ─────────────────────────────────────────────
moods   = ["elegante", "urbano", "comodo", "sexy", "relajado"]
temps   = [3, 7, 13, 16, 20, 24, 28]

print("=" * 70)
print("PASADA 1 — rain=False")
print("=" * 70)

results = {}  # (mood, temp) -> list of (score, combo)

for mood in moods:
    for temp in temps:
        outfits, _ = generate_outfits(
            garments=garments,
            occasion="matrimonio",
            temp=temp,
            rain=False,
            mood=mood,
            activity="parado",
            top_n=3,
        )
        results[(mood, temp)] = outfits
        tag = f"[{mood.upper()} {temp}°]"
        print(f"\n{tag}")
        if not outfits:
            print("  ❌ Sin outfits generados")
            continue
        for i, (score, combo) in enumerate(outfits, 1):
            print(f"  Outfit {i}{fmt_outfit(score, combo)}")

# ─────────────────────────────────────────────
# TABLA COMPARATIVA
# ─────────────────────────────────────────────
print("\n\n" + "=" * 70)
print("TABLA COMPARATIVA")
print("=" * 70)

def has_blazer(outfits):
    return any(any(g.category == "midlayer" for g in combo) for _, combo in outfits)

def has_outerwear(outfits):
    return any(any(g.category == "outerwear" for g in combo) for _, combo in outfits)

def all_have_outerwear(outfits):
    return outfits and all(any(g.category == "outerwear" for g in combo) for _, combo in outfits)

def all_have_blazer(outfits):
    return outfits and all(any(g.category == "midlayer" for g in combo) for _, combo in outfits)

def elegant_vestidos_dominant(outfits):
    if not outfits:
        return False
    count = sum(
        1 for _, combo in outfits
        if any(g.category == "one_piece" and g.subcategory in ["vestido_elegante", "vestido_coctel"] for g in combo)
    )
    return count >= 2

def shoe_variety(outfits):
    if not outfits:
        return False
    shoes = [next((g for g in combo if g.category == "shoes"), None) for _, combo in outfits]
    ids = [s.id for s in shoes if s]
    return len(set(ids)) >= min(2, len(ids))

def outer_variety(outfits):
    outers = [next((g for g in combo if g.category == "outerwear"), None) for _, combo in outfits]
    outers = [o for o in outers if o]
    if len(outers) < 2:
        return None  # no aplica
    return len({o.id for o in outers}) >= 2

checks = [
    ("Blazer consistente temp<=15?",   lambda m, t: all_have_blazer(results[(m,t)]) if t <= 15 else None),
    ("Outerwear consistente temp<=10?", lambda m, t: all_have_outerwear(results[(m,t)]) if t <= 10 else None),
    ("Vestidos elegantes dominan?",    lambda m, t: elegant_vestidos_dominant(results[(m,t)]) if m in ["elegante","sexy"] else None),
    ("Variedad calzado?",              lambda m, t: shoe_variety(results[(m,t)])),
    ("Variedad outerwear?",            lambda m, t: outer_variety(results[(m,t)])),
]

def sym(val):
    if val is None:  return "  —  "
    if val is True:  return "  ✅  "
    if val is False: return "  ❌  "

col_w = 8
header = f"{'Check':<35}" + "".join(f"{m[:6]:>{col_w}}" for m in moods)
print(header)
print("-" * len(header))

for label, fn in checks:
    for temp in temps:
        row = f"{label+' '+str(temp)+'°':<35}"
        skip = True
        vals = []
        for mood in moods:
            v = fn(mood, temp)
            vals.append(v)
            if v is not None:
                skip = False
        if skip:
            continue
        row += "".join(sym(v) for v in vals)
        print(row)

# ─────────────────────────────────────────────
# PASADA 2: comodo + rain=True, temps fríos
# ─────────────────────────────────────────────
print("\n\n" + "=" * 70)
print("PASADA 2 — mood=comodo, rain=True")
print("=" * 70)

for temp in [3, 7, 13]:
    outfits, missing = generate_outfits(
        garments=garments,
        occasion="matrimonio",
        temp=temp,
        rain=True,
        mood="comodo",
        activity="parado",
        top_n=3,
    )
    tag = f"[COMODO {temp}°☔]"
    print(f"\n{tag}")
    if missing:
        print(f"  ⚠ Faltan categorías: {missing}")
        continue
    if not outfits:
        print("  ❌ Sin outfits")
        continue
    for i, (score, combo) in enumerate(outfits, 1):
        outers = [g for g in combo if g.category == "outerwear"]
        outer_info = ""
        if outers:
            o = outers[0]
            sport = "sport" in (o.style or "")
            relajado = o.dress_level == "relajado"
            flag = " ❌sport/relajado" if (sport or relajado) else " ✅elegante"
            outer_info = f"  outer={o.name}{flag}"
        print(f"  Outfit {i}{fmt_outfit(score, combo)}{outer_info}")
