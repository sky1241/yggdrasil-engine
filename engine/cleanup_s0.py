#!/usr/bin/env python3
"""
🧹 CLEANUP S0 — Yggdrasil Engine
Toutes les corrections data en un seul script:
  1. Ajouter works_count=0 aux 794 symboles originaux (pas minés)
  2. Reclassifier 13 suspects: C1 → C2 (2 vers S3, 11 restent S0)
  3. Fix Hagen-Poiseuille: domain "droit" → "fluides"
  4. Déplacer 17 C2 minés de S0 → S3 (leur vraie strate)
  5. Poincaré conjecture: C2 → C1
  6. Calculer Q1 par domaine + flag vivant/musée

Sky × Claude — 21 février 2026, Versoix
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent

print("=" * 60)
print("🧹 CLEANUP S0 — Yggdrasil Engine")
print("=" * 60)

# ══════════════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════════════
with open(ROOT / 'data' / 'strates_export_v2.json', encoding='utf-8') as f:
    data = json.load(f)

strates = data['strates']
s0_syms = strates[0]['symbols']
print(f"\nChargé: {len(s0_syms)} symboles S0")
print(f"Strates: {len(strates)}")
for st in strates:
    print(f"  S{st['id']}: {len(st['symbols'])} symboles")

# ══════════════════════════════════════════════════════════
# 1. works_count=0 pour les 794 originaux
# ══════════════════════════════════════════════════════════
print(f"\n[1] Ajouter works_count aux originaux...")
n_original = 0
n_already = 0
for sym in s0_syms:
    if 'works_count' not in sym:
        sym['works_count'] = 0
        n_original += 1
    else:
        n_already += 1
print(f"  Originaux sans works_count: {n_original} → ajouté 0")
print(f"  Déjà avec works_count: {n_already}")

# ══════════════════════════════════════════════════════════
# 2. Reclassifier 13 suspects C1 → C2
# ══════════════════════════════════════════════════════════
print(f"\n[2] Reclassifier 13 suspects...")

# 2 vont à S3, 11 restent S0 mais deviennent C2
SUSPECTS_TO_S3 = {
    "Black hole information paradox",
    "Homotopy hypothesis",
}

SUSPECTS_TO_S0_C2 = {
    "Non-standard cosmology",
    "Unparticle physics",
    "Multiple chemical sensitivity",
    "Group selection",
    "International Linear Collider",
    "Neocolonialism",
    "Creative class",
    "Bertrand paradox (economics)",
    "Ridge push",
    "Phylogenetic nomenclature",
    "Superselection",
}

ALL_SUSPECTS = SUSPECTS_TO_S3 | SUSPECTS_TO_S0_C2

# Find and reclassify in S0
moved_to_s3 = []
reclassed_c2 = 0
found_suspects = set()

new_s0 = []
for sym in s0_syms:
    name = sym['from']
    if name in SUSPECTS_TO_S3:
        sym['class'] = 'C2'
        moved_to_s3.append(sym)
        found_suspects.add(name)
        print(f"  → S3 C2: {name}")
    elif name in SUSPECTS_TO_S0_C2:
        sym['class'] = 'C2'
        new_s0.append(sym)
        found_suspects.add(name)
        reclassed_c2 += 1
        print(f"  → S0 C2: {name}")
    else:
        new_s0.append(sym)

# Add moved suspects to S3
if moved_to_s3:
    strates[3]['symbols'].extend(moved_to_s3)
    print(f"  Déplacés vers S3: {len(moved_to_s3)}")

not_found = ALL_SUSPECTS - found_suspects
if not_found:
    print(f"  ⚠️ Non trouvés: {not_found}")

print(f"  Reclassés C2 dans S0: {reclassed_c2}")

s0_syms = new_s0  # update reference

# ══════════════════════════════════════════════════════════
# 3. Fix Hagen-Poiseuille: domain "droit" → "fluides"
# ══════════════════════════════════════════════════════════
print(f"\n[3] Fix Hagen-Poiseuille...")
hp_fixed = 0
for sym in s0_syms:
    if 'Hagen' in sym['from'] and 'Poiseuille' in sym['from']:
        old_dom = sym['domain']
        sym['domain'] = 'fluides'
        print(f"  {sym['from']}: {old_dom} → fluides")
        hp_fixed += 1
print(f"  Corrigés: {hp_fixed}")

# ══════════════════════════════════════════════════════════
# 4. Déplacer C2 minés de S0 → leur vraie strate
#    Utilise concept_id pour croiser avec mined_concepts.json
# ══════════════════════════════════════════════════════════
print(f"\n[4] Déplacer C2 minés vers leur vraie strate...")

# Load mined_concepts to get correct strate per concept_id
with open(ROOT / 'data' / 'mined_concepts.json', encoding='utf-8') as f:
    mined = json.load(f)

# Build lookup: concept_id → correct strate
cid_to_strate = {}
for c in mined['concepts']:
    cid_to_strate[c['concept_id']] = c['strate']

# ALL C2 in S0 are hypotheses/conjectures → they belong in S3 (Motif)
# The 13 suspects reclassed to C2 in step 2 also go to S3
moved_c2 = []
new_s0_2 = []
for sym in s0_syms:
    if sym.get('class') == 'C2':
        moved_c2.append(sym)
        print(f"  → S3: {sym['from']} (domain={sym['domain']}, wc={sym.get('works_count', '?')})")
    else:
        new_s0_2.append(sym)

if moved_c2:
    strates[3]['symbols'].extend(moved_c2)
print(f"  C2 déplacés S0→S3: {len(moved_c2)}")

s0_syms = new_s0_2

# ══════════════════════════════════════════════════════════
# 5. Poincaré conjecture: C2 → C1
# ══════════════════════════════════════════════════════════
print(f"\n[5] Poincaré conjecture: C2 → C1...")
poincare_fixed = False

# Check all strates (might have been moved to S3 above)
for st in strates:
    for sym in st['symbols']:
        if 'Poincaré' in sym.get('from', '') and 'conjecture' in sym.get('from', '').lower():
            old_class = sym.get('class', 'none')
            sym['class'] = 'C1'
            print(f"  {sym['from']}: {old_class} → C1 (Perelman 2003, résolu)")
            poincare_fixed = True

if not poincare_fixed:
    print(f"  ⚠️ Poincaré conjecture non trouvé!")

# ══════════════════════════════════════════════════════════
# 6. Calculer Q1 par domaine + flag vivant/musée
# ══════════════════════════════════════════════════════════
print(f"\n[6] Calculer Q1 par domaine + vivant/musée...")

# Update s0 reference in strates
strates[0]['symbols'] = s0_syms

# Collect works_count per domain for S0 only
domain_wc = defaultdict(list)
for sym in s0_syms:
    dom = sym.get('domain', 'unknown')
    wc = sym.get('works_count', 0)
    domain_wc[dom].append(wc)

# Calculate Q1 (25th percentile) per domain
import statistics

domain_q1 = {}
for dom, wcs in sorted(domain_wc.items(), key=lambda x: -len(x[1])):
    wcs_sorted = sorted(wcs)
    n = len(wcs_sorted)
    if n >= 4:
        # Q1 = value at 25th percentile
        q1_idx = n // 4
        q1 = wcs_sorted[q1_idx]
    else:
        q1 = 0  # Not enough data
    domain_q1[dom] = q1

print(f"\n  Q1 PAR DOMAINE (top 20):")
for dom in sorted(domain_q1, key=lambda d: -len(domain_wc[d]))[:20]:
    q1 = domain_q1[dom]
    n = len(domain_wc[dom])
    print(f"    {dom:25s} Q1={q1:>10,}  (n={n})")

# Apply vivant/musée flag
n_vivant = 0
n_musee = 0
n_original_vivant = 0

for sym in s0_syms:
    dom = sym.get('domain', 'unknown')
    wc = sym.get('works_count', 0)
    q1 = domain_q1.get(dom, 0)

    if not sym.get('mined'):
        # Original 794: always vivant (foundational notation)
        sym['cube'] = 'vivant'
        n_original_vivant += 1
        n_vivant += 1
    elif wc >= q1:
        sym['cube'] = 'vivant'
        n_vivant += 1
    else:
        sym['cube'] = 'musee'
        n_musee += 1

print(f"\n  Résultat vivant/musée:")
print(f"    Vivant: {n_vivant} ({n_vivant/len(s0_syms)*100:.1f}%)")
print(f"    Musée:  {n_musee} ({n_musee/len(s0_syms)*100:.1f}%)")
print(f"    (dont {n_original_vivant} originaux forcés vivant)")

# ══════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════
print(f"\n[SAVE] Écriture strates_export_v2.json...")

# Update meta
data['meta']['cleanup'] = {
    'date': '2026-02-21',
    'suspects_reclassed': reclassed_c2 + len(moved_to_s3),
    'hp_fixed': hp_fixed,
    'c2_moved_to_s3': len(moved_c2),
    'poincare_c1': poincare_fixed,
    'vivant': n_vivant,
    'musee': n_musee,
    'domain_q1': {k: int(v) for k, v in domain_q1.items()}
}

# Final counts
print(f"\n  ÉTAT FINAL:")
for st in strates:
    n_c1 = sum(1 for s in st['symbols'] if s.get('class') != 'C2')
    n_c2 = sum(1 for s in st['symbols'] if s.get('class') == 'C2')
    print(f"    S{st['id']}: {len(st['symbols'])} symboles ({n_c1} C1, {n_c2} C2)")

with open(ROOT / 'data' / 'strates_export_v2.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print(f"\n✅ CLEANUP TERMINÉ")
print(f"=" * 60)
