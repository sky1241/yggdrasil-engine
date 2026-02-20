#!/usr/bin/env python3
"""
gen_viz_v2.py — Génère les données inline JS pour yggdrasil_rain_v2.html
Fusionne strates_export_v2.json (5459 symboles) avec les conjectures C2 existantes.

IMPORTANT: Utilise les positions ORIGINALES du HTML pour les 794 symboles d'origine,
et les positions de strates_export_v2.json UNIQUEMENT pour les symboles minés.
"""
import json, math, os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2_PATH   = os.path.join(ROOT, 'data', 'strates_export_v2.json')
HTML_PATH = os.path.join(ROOT, 'viz', 'yggdrasil_rain_v2.html')

# ── Load v2 data ──
with open(V2_PATH, 'r', encoding='utf-8') as f:
    v2 = json.load(f)

# ── Get ORIGINAL HTML from git (with correct positions) ──
result = subprocess.run(
    ['git', 'show', 'ffcd4af:viz/yggdrasil_rain_v2.html'],
    capture_output=True, text=True, encoding='utf-8',
    cwd=ROOT
)
original_html = result.stdout

# Extract original ST_C1 and ST_C2 from the original HTML
m1 = re.search(r'const ST_C1=(\[.*?\]);\s*\n', original_html)
m2 = re.search(r'const ST_C2=(\[.*?\]);\s*\n', original_html)
if not m1 or not m2:
    raise ValueError("Cannot extract ST_C1/ST_C2 from original HTML")

ORIGINAL_C1 = json.loads(m1.group(1))
ORIGINAL_C2 = json.loads(m2.group(1))

print(f"Original C1: {sum(len(s['sy']) for s in ORIGINAL_C1)} symbols in {len(ORIGINAL_C1)} strates")
print(f"Original C2: {sum(len(s['sy']) for s in ORIGINAL_C2)} conjectures in {len(ORIGINAL_C2)} strates")

# ── Build lookup: strate_idx → {symbol_name: [px, pz]} for original positions ──
ORIG_POS = []
for strate in ORIGINAL_C1:
    pos_map = {}
    for sym in strate['sy']:
        # sym format: [name, px, pz, isCentre, domain]
        pos_map[sym[0]] = (sym[1], sym[2])
    ORIG_POS.append(pos_map)

# ── Strate metadata ──
STRATE_META = [
    {"n":"SOL · Δ⁰₀ · Décidable","sh":"Δ⁰₀ SOL","f":"R(x) — tout se calcule en temps fini",
     "de_c1":"Arithmétique, algèbre, analyse, physique, chimie — toute formule calculable.",
     "de_c2":"Conjectures calculables. Hypothèses ouvertes sur objets décidables.",
     "c":[74,222,128],"yr":-0.44,"op":0.18},
    {"n":"NUAGE 1 · Σ⁰₁ · Halting Problem","sh":"Σ⁰₁ HALTING","f":"∃y R(x, y) — il existe, mais on sait pas quand",
     "de_c1":"Semi-décidable. On peut dire oui, jamais non.",
     "de_c2":"Semi-décidable. Conjectures d'existence.",
     "c":[96,165,250],"yr":-0.26,"op":0.16},
    {"n":"NUAGE 2 · Σ⁰₂ · Limite","sh":"Σ⁰₂ LIMITE","f":"∃y ∀z R(x,y,z) — deviner, corriger, jamais sûr",
     "de_c1":"Ensembles limites. TOT, FIN, COF.",
     "de_c2":"Ensembles limites. Conjectures de convergence.",
     "c":[167,139,250],"yr":-0.1,"op":0.14},
    {"n":"NUAGE n · Σ⁰ₙ · Motif","sh":"Σ⁰ₙ MOTIF","f":"∃∀∃∀… n alternances",
     "de_c1":"Chaque alternance = un étage. Post 1944.",
     "de_c2":"Alternances quantificateurs. Conjectures structurelles.",
     "c":[244,114,182],"yr":0.06,"op":0.13},
    {"n":"CIEL · AH = ∪ₙ Σ⁰ₙ","sh":"AH CIEL","f":"Tout le ciel arithmétique",
     "de_c1":"L'union de tous les nuages. Tarski.",
     "de_c2":"Conjectures au-delà de la hiérarchie finie.",
     "c":[251,191,36],"yr":0.2,"op":0.13},
    {"n":"HYPERARITHMÉTIQUE","sh":"HYP ω₁ᶜᵏ","f":"∅⁽α⁾ pour α < ω₁^CK",
     "de_c1":"Kleene, Church-Kleene. Le transfini.",
     "de_c2":"Transfini. Conjectures hyperarithmétiques.",
     "c":[251,146,60],"yr":0.34,"op":0.16},
    {"n":"PLAFOND · Turing 1936","sh":"∞ PLAFOND","f":"∄ M décidant l'arrêt — Prouvé.",
     "de_c1":"Gödel · Church · Turing. BB(n). Le mur.",
     "de_c2":"Indécidable. Conjectures sur les limites absolues.",
     "c":[239,68,68],"yr":0.46,"op":0.24},
]

# ── Center symbols ──
CTR_C1 = ['=','K','FIN','COF','Th(ℕ)','O_Kl','HALT']
CTR_C2 = ['RH','P≠NP','ACE','Collatz','SCH','AD?','BB5']

def compute_shells(n_symbols):
    """Compute shell radii based on symbol count."""
    if n_symbols <= 25:
        return [round(0.7 + i * 0.6, 3) for i in range(2)]
    elif n_symbols <= 50:
        return [round(0.5 + i * 0.35, 3) for i in range(3)]
    elif n_symbols <= 150:
        n = min(6, max(3, int(math.sqrt(n_symbols) / 3)))
        inner, outer = 0.45, 1.8
        return [round(inner + (outer - inner) * i / (n - 1), 3) for i in range(n)]
    else:
        # Large strate (especially S0 with 5000+)
        n = min(10, max(4, int(math.sqrt(n_symbols) / 7)))
        inner, outer = 0.35, min(2.5, 0.35 + math.sqrt(n_symbols) * 0.03)
        return [round(inner + (outer - inner) * i / (n - 1), 3) for i in range(n)]

# ── Import depth_map for logical-depth placement ──
from depth_map import (
    get_symbol_depth, estimate_mined_depth,
    depth_to_radius, place_symbol
)

# ── Load mined concepts data (for level info) ──
MINED_PATH = os.path.join(ROOT, 'data', 'mined_concepts.json')
with open(MINED_PATH, 'r', encoding='utf-8') as f:
    mined_data = json.load(f)
# Build lookup: truncated_name → concept
MINED_LOOKUP = {}
for c in mined_data['concepts']:
    MINED_LOOKUP[c['name'][:20]] = c

GOLDEN_ANGLE = 2.399963229728653  # for sub-spreading within depth rings

# ── Build ST_C1 from v2 data ──
ST_C1 = []
total_c1 = 0
orig_found = 0
mined_count = 0
for i, strate in enumerate(v2['strates']):
    meta = STRATE_META[i]

    # Separate original and mined C1 symbols
    original_syms = []
    mined_syms = []
    for sym in strate['symbols']:
        sym_class = sym.get('class', 'C1')
        if sym_class != 'C1':
            continue
        if sym.get('mined', False):
            mined_syms.append(sym)
        else:
            original_syms.append(sym)

    c1_symbols = []

    if i == 0:
        # ═══ S0: PLACEMENT PAR PROFONDEUR LOGIQUE ═══
        # Tous les symboles S0 (originaux + minés) sont placés par depth_map
        from collections import defaultdict

        # Compute depth for all symbols
        all_with_depth = []
        for sym in original_syms:
            name = sym['s']
            depth = get_symbol_depth(name)
            all_with_depth.append((sym, depth, False))
            orig_found += 1

        for sym in mined_syms:
            name = sym['s']
            concept = MINED_LOOKUP.get(name, {})
            depth = estimate_mined_depth(concept) if concept else 8
            all_with_depth.append((sym, depth, True))
            mined_count += 1

        # Group by (depth, domain) for angular spreading
        groups = defaultdict(list)
        for sym, depth, is_mined in all_with_depth:
            key = (depth, sym['domain'])
            groups[key].append(sym)

        # Place each group
        for (depth, domain), syms in groups.items():
            for idx, sym in enumerate(syms):
                name = sym['s']
                if name in CTR_C1:
                    c1_symbols.append([name, 0, 0, 1, domain])
                else:
                    px, pz = place_symbol(depth, domain, idx, len(syms))
                    c1_symbols.append([name, px, pz, 0, domain])

    else:
        # ═══ S1-S6: Garder positions originales + spirale pour minés ═══
        for sym in original_syms:
            name = sym['s']
            is_centre = 1 if name in CTR_C1 else 0
            if is_centre:
                c1_symbols.append([name, 0, 0, 1, sym['domain']])
            elif i < len(ORIG_POS) and name in ORIG_POS[i]:
                px, pz = ORIG_POS[i][name]
                c1_symbols.append([name, round(px, 3), round(pz, 3), 0, sym['domain']])
            else:
                c1_symbols.append([name, round(sym['px'], 3), round(sym['pz'], 3), 0, sym['domain']])
            orig_found += 1

        # Mined S1-S6: golden spiral by works_count
        sorted_mined = sorted(mined_syms, key=lambda s: -s.get('works_count', 0))
        for idx, sym in enumerate(sorted_mined):
            angle = idx * GOLDEN_ANGLE
            radius = 0.4 + 0.15 * math.sqrt(idx)
            px = round(radius * math.cos(angle), 3)
            pz = round(radius * math.sin(angle), 3)
            c1_symbols.append([sym['s'], px, pz, 0, sym['domain']])
            mined_count += 1

    shells = compute_shells(len(c1_symbols))
    total_c1 += len(c1_symbols)

    ST_C1.append({
        "n": meta["n"], "sh": meta["sh"], "f": meta["f"],
        "de": meta["de_c1"], "c": meta["c"], "yr": meta["yr"], "op": meta["op"],
        "sy": c1_symbols, "shells": shells
    })

print(f"\n=== GENERATION VIZ V2 ===")
print(f"C1: {total_c1} symboles ({orig_found} original positions, {mined_count} mined positions)")
for i, s in enumerate(ST_C1):
    print(f"  S{i}: {len(s['sy'])} symboles, {len(s['shells'])} shells")

# Verify centers
for i, s in enumerate(ST_C1):
    for sym in s['sy']:
        if sym[3] == 1:
            print(f"  CENTER S{i}: '{sym[0]}' at ({sym[1]}, {sym[2]})")

# ── Build ST_C2: existing conjectures + mined C2 ──
ST_C2 = []
total_c2_mined = 0
for i, strate in enumerate(v2['strates']):
    meta = STRATE_META[i]

    # Keep existing C2 symbols (already have correct positions)
    existing_syms = ORIGINAL_C2[i]['sy'] if i < len(ORIGINAL_C2) else []

    # Add mined C2 symbols (use their v2 positions)
    mined_c2 = []
    for sym in strate['symbols']:
        if sym.get('class') == 'C2' and sym.get('mined'):
            mined_c2.append([sym['s'], round(sym['px'], 3), round(sym['pz'], 3), 0, sym['domain']])

    total_c2_mined += len(mined_c2)
    all_c2 = existing_syms + mined_c2

    shells = ORIGINAL_C2[i]['shells'] if i < len(ORIGINAL_C2) else compute_shells(len(all_c2))
    if len(mined_c2) > 5:
        shells = compute_shells(len(all_c2))

    ST_C2.append({
        "n": meta["n"], "sh": meta["sh"], "f": meta["f"],
        "de": meta["de_c2"], "c": meta["c"], "yr": meta["yr"], "op": meta["op"],
        "sy": all_c2, "shells": shells
    })

total_c2 = sum(len(s['sy']) for s in ST_C2)
print(f"C2: {total_c2} conjectures ({total_c2_mined} mined added)")
for i, s in enumerate(ST_C2):
    print(f"  S{i}: {len(s['sy'])} conjectures")

# ── Generate compact JSON ──
def compact_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',',':'))

st_c1_js = compact_json(ST_C1)
st_c2_js = compact_json(ST_C2)

# ── Read CURRENT HTML (already modified) and update ──
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

lines = html.split('\n')

new_data_lines = [
    f'const ST_C1={st_c1_js};',
    f"const CTR_C1={compact_json(CTR_C1)};",
    f'const ST_C2={st_c2_js};',
    f"const CTR_C2={compact_json(CTR_C2)};",
    'let currentST=ST_C1,currentCTR=CTR_C1,isC2=false,isC3=false;',
]

# Find the data block
start_idx = None
end_idx = None
for idx, line in enumerate(lines):
    if line.startswith('const ST_C1='):
        start_idx = idx
    if 'let currentST=ST_C1' in line:
        end_idx = idx
        break

if start_idx is None or end_idx is None:
    raise ValueError(f"Cannot find data block (start={start_idx}, end={end_idx})")

print(f"\nReplacing lines {start_idx+1}-{end_idx+1}")

# Update subtitle lines
for idx, line in enumerate(lines):
    if '5442 symboles' in line or '794 symboles' in line:
        old = line
        lines[idx] = line.replace('5442 symboles · 4918 concepts OpenAlex',
                                   f'{total_c1} symboles · 4918 concepts OpenAlex')
        lines[idx] = lines[idx].replace('794 symboles · 466 concepts OpenAlex',
                                         f'{total_c1} symboles · 4918 concepts OpenAlex')
        if lines[idx] != old:
            print(f"  Updated line {idx+1}")

# Replace data block
new_lines = lines[:start_idx] + new_data_lines + lines[end_idx+1:]

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

html_size = len('\n'.join(new_lines))
print(f"\nHTML written: {html_size:,} bytes ({html_size/1024:.0f} KB)")
print("Done!")
