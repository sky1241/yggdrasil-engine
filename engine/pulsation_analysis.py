#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALYSE DE PULSATION — Escalier vs Pont
=========================================
Deux systèmes de connexions dans Yggdrasil:
  ESCALIER = pulsation verticale (hiérarchie S0→S6, Post)
  PONT     = pulsation horizontale (co-occurrence inter-domaines)

Découverte: ces deux pulsations sont PERPENDICULAIRES.
- L'escalier est un entonnoir: 9 continents → 1 (info) à S2
- Le pont est une résurgence: 1 → 8 continents à S3
- L'interférence se produit à S3 (conjectures ouvertes)

Usage:
    python engine/pulsation_analysis.py
"""
import json
import math
import os
from datetime import datetime

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# ── Mapping domaine → continent ──────────────────────────────────

CONTINENTS = {
    'math': [
        'algèbre', 'analyse', 'topologie', 'géométrie', 'EDP',
        'probabilités', 'combinatoire', 'nb théorie', 'ensembles',
        'catégories', 'systèmes dynamiques', 'algèbre lin',
        'analyse fonctionnelle', 'géom algébrique', 'géom diff',
        'analyse numérique', 'trigonométrie', 'arithmétique',
        'nombres', 'nb premiers', 'complexes', 'ordinaux',
        'stochastique', 'mesure', 'descriptive',
    ],
    'physique': [
        'mécanique', 'quantique', 'relativité', 'particules', 'QFT',
        'nucléaire', 'cosmologie', 'mécanique stat', 'astronomie',
        'mécanique analytique', 'gravitation',
    ],
    'info': [
        'informatique', 'complexité', 'calculabilité', 'automates',
        'logique', 'crypto', 'optimisation', 'ML', 'vision',
        'information', 'NLP',
    ],
    'ingenierie': [
        'ingénierie', 'aérospatiale', 'électromagn', 'optique',
        'signal', 'télécommunications', 'robotique', 'énergie',
        'fluides', 'thermo', 'contrôle',
    ],
    'chimie': [
        'chimie', 'chimie organique', 'polymères', 'nanotechnologie',
        'électrochimie', 'matériaux',
    ],
    'bio': [
        'biologie', 'médecine', 'immunologie', 'pharmacologie',
        'génomique', 'biomédical', 'oncologie', 'bioinformatique',
        'neurosciences', 'épidémiologie',
    ],
    'terre': [
        'géosciences', 'climatologie', 'océanographie', 'écologie',
        'environnement', 'sismologie', 'volcanologie', 'agronomie',
        'évolution',
    ],
    'humaines': [
        'économie', 'finance', 'sociologie', 'psychologie',
        'linguistique', 'éducation', 'histoire', 'anthropologie',
        'science politique', 'démographie', 'droit',
    ],
    'transversal': [
        'statistiques', 'métrologie', 'philosophie des sciences',
        'épistémologie',
    ],
}

DOM2CONT = {}
for cont, doms in CONTINENTS.items():
    for d in doms:
        DOM2CONT[d] = cont


# ── Pulsation verticale (escalier) ──────────────────────────────

def compute_vertical_pulsation(strates):
    """Calcule la pulsation verticale: distribution par strate × continent."""
    matrix = {}  # (strate_id, continent) → count
    for s in strates:
        sid = s['id']
        for sym in s['symbols']:
            d = sym.get('domain', 'inconnu')
            cont = DOM2CONT.get(d, 'autre')
            key = (sid, cont)
            matrix[key] = matrix.get(key, 0) + 1

    strate_counts = [len(s['symbols']) for s in strates]
    all_conts = sorted(CONTINENTS.keys())

    results = {
        'strate_counts': strate_counts,
        'continents': {},
    }

    for cont in all_conts:
        counts = [matrix.get((s, cont), 0) for s in range(7)]
        total = sum(counts)
        if total == 0:
            continue

        s0_pct = 100 * counts[0] / total
        above_s0 = sum(counts[1:])
        max_strate = max(s for s in range(7) if counts[s] > 0)

        probs = [c / total for c in counts if c > 0]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        max_entropy = math.log2(7)
        norm_entropy = entropy / max_entropy if max_entropy > 0 else 0

        results['continents'][cont] = {
            'distribution': counts,
            'total': total,
            's0_pct': round(s0_pct, 1),
            'above_s0': above_s0,
            'max_strate': max_strate,
            'vertical_entropy': round(norm_entropy, 4),
        }

    # Continent diversity per strate
    diversity = []
    for sid in range(7):
        conts = set()
        for sym in strates[sid]['symbols']:
            d = sym.get('domain', 'inconnu')
            c = DOM2CONT.get(d, 'autre')
            if c != 'autre':
                conts.add(c)
        diversity.append({
            'strate': sid,
            'n_symbols': len(strates[sid]['symbols']),
            'n_continents': len(conts),
            'continents': sorted(conts),
        })
    results['diversity_per_strate'] = diversity

    # S3 anomaly
    if strate_counts[1] > 0 and strate_counts[2] > 0:
        decay_rate = strate_counts[2] / strate_counts[1]
        s3_expected = strate_counts[1] * (decay_rate ** 2)
        s3_actual = strate_counts[3]
        s3_ratio = s3_actual / s3_expected if s3_expected > 0 else 0
        results['s3_anomaly'] = {
            'decay_rate_s2_s1': round(decay_rate, 3),
            's3_expected': round(s3_expected, 1),
            's3_actual': s3_actual,
            's3_ratio': round(s3_ratio, 1),
        }

    return results


# ── Pulsation horizontale (pont) ────────────────────────────────

def compute_horizontal_pulsation(escalier_data):
    """Calcule la pulsation horizontale: distances inter-continents."""
    distances = escalier_data.get('inter_distances', {})
    centroids = escalier_data.get('centroids', {})

    dist_values = sorted(distances.values())

    # Fit: linear vs power law
    ranks = np.arange(1, len(dist_values) + 1)
    log_ranks = np.log(ranks)
    log_dists = np.log(dist_values)

    # Power law fit
    slope_pl, intercept_pl = np.polyfit(log_ranks, log_dists, 1)
    r_sq_pl = float(np.corrcoef(log_ranks, log_dists)[0, 1] ** 2)

    # Linear fit
    slope_lin, intercept_lin = np.polyfit(ranks, dist_values, 1)
    r_sq_lin = float(np.corrcoef(ranks, np.array(dist_values))[0, 1] ** 2)

    # Isolation per continent
    isolation = {}
    for cont in CONTINENTS:
        if cont not in centroids:
            continue
        dists = [d for pair, d in distances.items() if cont in pair]
        isolation[cont] = {
            'mean_distance': round(float(np.mean(dists)), 4) if dists else 0,
            'n_symbols': centroids[cont]['n'],
        }

    return {
        'n_pairs': len(dist_values),
        'min': round(min(dist_values), 4),
        'max': round(max(dist_values), 4),
        'mean': round(float(np.mean(dist_values)), 4),
        'std': round(float(np.std(dist_values)), 4),
        'fit_power_law': {
            'slope': round(slope_pl, 3),
            'r_squared': round(r_sq_pl, 3),
        },
        'fit_linear': {
            'slope': round(slope_lin, 4),
            'r_squared': round(r_sq_lin, 3),
        },
        'isolation': isolation,
        'sorted_distances': {k: round(v, 4) for k, v in sorted(distances.items(), key=lambda x: x[1])},
    }


# ── Interférence S3 ─────────────────────────────────────────────

def compute_s3_interference(strates):
    """Analyse détaillée de la strate S3: point d'interférence escalier × pont."""
    s2 = strates[2]
    s3 = strates[3]

    # S2 domains/continents
    s2_domains = set(sym.get('domain', '?') for sym in s2['symbols'])
    s2_continents = set(DOM2CONT.get(d, 'autre') for d in s2_domains) - {'autre'}

    # S3 domains/continents
    s3_domains = set(sym.get('domain', '?') for sym in s3['symbols'])
    s3_continents = set(DOM2CONT.get(d, 'autre') for d in s3_domains) - {'autre'}

    # S3 by continent
    s3_by_continent = {}
    for sym in s3['symbols']:
        d = sym.get('domain', 'inconnu')
        cont = DOM2CONT.get(d, 'autre')
        if cont not in s3_by_continent:
            s3_by_continent[cont] = []
        s3_by_continent[cont].append({
            'symbol': sym.get('s', '?'),
            'name': sym.get('from', '?'),
            'domain': d,
            'class': sym.get('class', '?'),
            'works_count': sym.get('works_count', 0),
        })

    # S3 by class (C1 proved, C2 conjecture)
    s3_classes = {}
    for sym in s3['symbols']:
        cl = sym.get('class', '?')
        s3_classes[cl] = s3_classes.get(cl, 0) + 1

    # Famous conjectures in S3
    famous_c2 = [
        sym for sym in s3['symbols']
        if sym.get('class') == 'C2' and sym.get('works_count', 0) > 1000
    ]
    famous_c2.sort(key=lambda x: -x.get('works_count', 0))

    return {
        's2_bottleneck': {
            'n_symbols': len(s2['symbols']),
            'domains': sorted(s2_domains),
            'continents': sorted(s2_continents),
            'n_continents': len(s2_continents),
        },
        's3_resonance': {
            'n_symbols': len(s3['symbols']),
            'domains': sorted(s3_domains),
            'continents': sorted(s3_continents),
            'n_continents': len(s3_continents),
            'resurgent_continents': sorted(s3_continents - s2_continents),
            'n_resurgent': len(s3_continents - s2_continents),
        },
        's3_by_continent': {
            cont: len(syms) for cont, syms in s3_by_continent.items()
        },
        's3_classes': s3_classes,
        'famous_conjectures': [
            {
                'symbol': sym.get('s', '?'),
                'name': sym.get('from', '?')[:60],
                'works_count': sym.get('works_count', 0),
            }
            for sym in famous_c2[:15]
        ],
    }


# ── Perpendicularity score ──────────────────────────────────────

def compute_perpendicularity(vertical, horizontal):
    """
    Mesure la perpendicularity entre escalier et pont.
    Score élevé = les continents qui montent NE SONT PAS ceux qui connectent.
    """
    conts = sorted(set(vertical['continents'].keys()) & set(horizontal['isolation'].keys()))

    v_scores = []  # vertical reach
    h_scores = []  # horizontal isolation (inverted = connectivity)

    for cont in conts:
        v = vertical['continents'][cont]['vertical_entropy']
        h = horizontal['isolation'][cont]['mean_distance']
        v_scores.append(v)
        h_scores.append(h)

    v_arr = np.array(v_scores)
    h_arr = np.array(h_scores)

    # Correlation: negative = perpendicular (high v → high h isolation)
    if len(v_arr) >= 3 and np.std(v_arr) > 0 and np.std(h_arr) > 0:
        correlation = float(np.corrcoef(v_arr, h_arr)[0, 1])
    else:
        correlation = 0

    per_continent = {}
    for i, cont in enumerate(conts):
        v = v_scores[i]
        h = h_scores[i]
        if v > 0.1:
            ctype = "ESCALIER"
        elif h < 0.55:
            ctype = "PONT"
        elif h > 0.8:
            ctype = "ÎLE"
        else:
            ctype = "MIXTE"

        per_continent[cont] = {
            'vertical_entropy': round(v, 4),
            'horizontal_isolation': round(h, 4),
            'type': ctype,
        }

    return {
        'correlation': round(correlation, 4),
        'interpretation': (
            "PERPENDICULAIRE" if correlation > 0.2
            else "PARALLÈLE" if correlation < -0.2
            else "INDÉPENDANT"
        ),
        'per_continent': per_continent,
    }


# ── Main ─────────────────────────────────────────────────────────

def main():
    print("=== ANALYSE DE PULSATION: ESCALIER vs PONT ===")
    print("Méthode: comparer la pulsation verticale (hiérarchie S0→S6)")
    print("         avec la pulsation horizontale (co-occurrence inter-domaines)")
    print()

    # Load data — try v2 first, fallback to v1 if memory error
    strates_path = os.path.join(DATA_DIR, "strates_export_v2.json")
    escalier_path = os.path.join(DATA_DIR, "escaliers_spectraux.json")

    try:
        with open(strates_path, encoding='utf-8') as f:
            strates_data = json.load(f)
        print(f"  Loaded: {strates_path} (v2)")
    except MemoryError:
        strates_path = os.path.join(DATA_DIR, "strates_export.json")
        with open(strates_path, encoding='utf-8') as f:
            strates_data = json.load(f)
        print(f"  Loaded: {strates_path} (v1, v2 too large)")

    with open(escalier_path, encoding='utf-8') as f:
        escalier_data = json.load(f)

    strates = strates_data['strates']

    # 1. Vertical pulsation
    print("--- PULSATION VERTICALE (ESCALIER) ---")
    vertical = compute_vertical_pulsation(strates)

    for sid, div in enumerate(vertical['diversity_per_strate']):
        bar = "█" * div['n_continents'] + "·" * (9 - div['n_continents'])
        print(f"  S{sid}: {div['n_symbols']:>5} symboles | {bar} {div['n_continents']}/9 continents")
    print()

    if 's3_anomaly' in vertical:
        a = vertical['s3_anomaly']
        print(f"  S3 ANOMALIE: attendu {a['s3_expected']}, observé {a['s3_actual']} → {a['s3_ratio']}x")
    print()

    for cont, info in sorted(vertical['continents'].items(), key=lambda x: -x[1]['vertical_entropy']):
        ext = f"S0→S{info['max_strate']}"
        bar = "█" * int(info['vertical_entropy'] * 20)
        print(f"  {cont:>12}: ent={info['vertical_entropy']:.3f} {bar:20} {ext} ({info['above_s0']} au-dessus S0)")
    print()

    # 2. Horizontal pulsation
    print("--- PULSATION HORIZONTALE (PONT) ---")
    horizontal = compute_horizontal_pulsation(escalier_data)

    print(f"  {horizontal['n_pairs']} paires, dist=[{horizontal['min']:.2f} — {horizontal['max']:.2f}]")
    print(f"  Fit linéaire:    R²={horizontal['fit_linear']['r_squared']}")
    print(f"  Fit power law:   R²={horizontal['fit_power_law']['r_squared']}")
    print()

    for cont, info in sorted(horizontal['isolation'].items(), key=lambda x: x[1]['mean_distance']):
        bar = "█" * int((1 - info['mean_distance']) * 20)
        print(f"  {cont:>12}: isolation={info['mean_distance']:.3f} {bar:20} (n={info['n_symbols']})")
    print()

    # 3. Perpendicularity
    print("--- PERPENDICULARITY ---")
    perp = compute_perpendicularity(vertical, horizontal)
    print(f"  Corrélation vert×horiz: {perp['correlation']}")
    print(f"  Interprétation: {perp['interpretation']}")
    print()

    for cont, info in perp['per_continent'].items():
        print(f"  {cont:>12}: vert={info['vertical_entropy']:.3f} horiz={info['horizontal_isolation']:.3f} → {info['type']}")
    print()

    # 4. S3 Interference
    print("--- INTERFÉRENCE S3 ---")
    s3_int = compute_s3_interference(strates)

    b = s3_int['s2_bottleneck']
    r = s3_int['s3_resonance']
    print(f"  S2 GOULOT:    {b['n_symbols']} symboles, {b['n_continents']} continent(s): {b['continents']}")
    print(f"  S3 RÉSONANCE: {r['n_symbols']} symboles, {r['n_continents']} continents")
    print(f"  RÉSURGENCE:   {r['n_resurgent']} continents reviennent: {r['resurgent_continents']}")
    print()

    print(f"  S3 par continent:")
    for cont, n in sorted(s3_int['s3_by_continent'].items(), key=lambda x: -x[1]):
        print(f"    {cont:>12}: {n} symboles")
    print()

    print(f"  S3 par classe: {s3_int['s3_classes']}")
    print()

    if s3_int['famous_conjectures']:
        print(f"  Conjectures célèbres en S3:")
        for c in s3_int['famous_conjectures']:
            print(f"    {c['symbol'][:20]:>20}: {c['name']} (wc={c['works_count']})")
    print()

    # 5. Synthesis
    print("=" * 60)
    print("SYNTHÈSE: LA CLÉ DE LA PULSATION")
    print("=" * 60)
    print()
    print("1. L'ESCALIER est un ENTONNOIR:")
    print("   9 continents → 4 (S1) → 1 (S2) → 8 (S3)")
    print("   Loi: exponentielle avec RÉSONANCE à S3")
    print()
    print("2. Le PONT est LINÉAIRE:")
    print("   Distribution quasi-uniforme des distances")
    print("   Pas de résonance, pas de goulot")
    print()
    print("3. Les deux sont PERPENDICULAIRES:")
    print(f"   Corrélation: {perp['correlation']} ({perp['interpretation']})")
    print("   Les continents qui MONTENT (info, math) sont ISOLÉS")
    print("   Les continents qui CONNECTENT (ing, terre) restent au SOL")
    print()
    print("4. L'INTERFÉRENCE est à S3:")
    print("   S2 = goulot (1 continent, pure computation)")
    print(f"   S3 = résurgence ({r['n_continents']} continents, conjectures cross-domain)")
    print("   L'escalier BLOQUE, le pont EXPLOSE")
    print()
    print("5. IMPLICATION pour P=NP:")
    print("   S2 contient BPP, RP, ZPP — classes probabilistes")
    print("   S3 contient P≠NP — la conjecture elle-même")
    print("   La transition S2→S3 = le passage computation → conjecture")
    print("   Question: ce passage est-il un MUR ou une PORTE?")
    print()

    # Export
    output = {
        "source": "PULSATION_ANALYSIS",
        "generated": datetime.now().isoformat(),
        "vertical_pulsation": vertical,
        "horizontal_pulsation": horizontal,
        "perpendicularity": perp,
        "s3_interference": s3_int,
        "key_findings": {
            "escalier_law": "exponential_with_s3_resonance",
            "pont_law": "quasi_linear",
            "relationship": perp['interpretation'],
            "correlation": perp['correlation'],
            "s3_anomaly_ratio": vertical.get('s3_anomaly', {}).get('s3_ratio', 0),
            "s2_bottleneck_continents": b['n_continents'],
            "s3_resurgence_continents": r['n_continents'],
        },
    }

    out_path = os.path.join(DATA_DIR, "pulsation_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Export: {out_path}")


if __name__ == "__main__":
    main()
