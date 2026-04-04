#!/usr/bin/env python3
"""
YGGDRASIL — CANON UNIVERSEL v2 : TROUS TYPÉS A/B/C
════════════════════════════════════════════════════════
Même scan que v1 mais avec classification correcte des trous:

TYPE A (Technique): Le pont EXISTE et est ACTIF, mais RIEN de nouveau n'en sort.
  → cooc élevée, z ≈ 0 (exactement attendu), production haute
  → Score_A = production × stagnation × (1 - disruption)
  → Proxy: high cooc + z petit positif = developmental/stagnant
  → Exemple: Poincaré (tout le monde savait, personne pouvait)

TYPE B (Conceptuel): Personne n'a l'IDÉE de connecter. Vide INVISIBLE.
  → cooc = 0 ou très basse, z négatif, activité des deux côtés haute
  → Score_B = activity_a × activity_b × void × |z|
  → Proxy: low cooc + negative z = hidden bridge
  → Exemple: GANs (game theory × deep learning avant Goodfellow)

TYPE C (Perceptuel): Le pont EXISTE mais est IGNORÉ ou SOUS-ÉVALUÉ.
  → cooc > 0 mais << attendue, z significativement négatif
  → Score_C = activity × disruption_potential × ignored_ratio
  → Proxy: cooc exists but way below expected = Karikó situation
  → Exemple: mRNA vaccines (Karikó publiait mais personne ne lisait)

Sky × Claude — 20 Mars 2026, Versoix
"""

import json
import os
import sys
import io
import time
import gc
import sqlite3
import numpy as np
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
PRED_DIR = os.path.join(REPO, "experiments", "predictions_2025")

# ══════════════════════════════════════════════
# 12 AXES — identique à v1
# ══════════════════════════════════════════════

AXES = {
    "AXE01_CAYLEY": {
        "Cayley graph": 3217, "Wreath product": 64319, "Permutation group": 63903,
        "Symmetric group": 4492, "Semidirect product": 61178, "Simple group": 57573,
        "CFSG": 59370, "Normal subgroup": 917, "Nilpotent group": 16592,
        "Coset": 62772, "Commutator subgroup": 6423, "Group theory": 62210,
        "Cayley's theorem": 54928,
    },
    "AXE02_SPECTRAL": {
        "Spectral gap": 28454, "Expander graph": 8508, "Markov chain mixing time": 64555,
        "Eigenvalues and eigenvectors": 9157, "Laplacian matrix": 2429, "Random walk": 3378,
        "Expander code": 1378,
    },
    "AXE03_BRIDGES": {
        "Knot theory": 6795, "Unknot": 38541, "Coding theory": 2234,
        "Sphere packing": 13095, "Sorting network": 59567, "Quantum walk": 6307,
        "Percolation theory": 2489, "Combinatorial optimization": 57247,
        "Braid group": 53818, "Mapping class group": 15045,
    },
    "AXE04_CANNON": {
        "Constraint satisfaction problem": 15562, "PSPACE": 15276, "Inverse problem": 5503,
        "Interval arithmetic": 14255, "Sensitivity analysis": 11886, "Phase transition": 7678,
        "Complexity of CSP": 5038,
    },
    "AXE05_PHYSIQUE": {
        "Entropy": 1033, "Statistical mechanics": 65006, "Ising model": 56807,
        "Spin glass": 7925, "Partition function (QFT)": 29774, "Potts model": 64855,
        "Spin model": 38170, "Renormalization": 10319, "Renormalization group": 60204,
        "Critical exponent": 10021, "Percolation threshold": 17933,
        "Percolation critical exponents": 9140, "Boltzmann entropy formula": 53836,
        "Resistance distance": 59049, "Electrical network": 15129,
        "Cellular automaton": 54073, "Simulated annealing": 4263,
        "Reversible computing": 16053, "Gibbs free energy": 7259,
        "Helmholtz free energy": 17989,
    },
    "AXE06_INFORMATION": {
        "Information theory": 57221, "Kolmogorov complexity": 34208,
        "Data compression": 61733, "Entropy thermo+info": 7582,
        "Quantum information": 10891, "Quantum computer": 58566,
        "Quantum error correction": 56695,
    },
    "AXE07_ESPACE": {
        "Cosmology": 17790, "Holographic principle": 13175, "Penrose tiling": 61412,
        "Fractal": 54881, "Self-similarity": 3102, "Fractal dimension": 17805,
    },
    "AXE08_PvsNP": {
        "P versus NP problem": 13541, "Computational complexity theory": 12499,
        "Boolean satisfiability": 60347, "NP-complete": 3609,
        "Complexity class": 54722, "Proof complexity": 933,
        "Circuit complexity": 63572, "Turing machine": 47107,
        "Halting problem": 5866, "Undecidable problem": 14370,
        "Decidability": 8312, "Godel incompleteness": 12665,
        "Parameterized complexity": 10214, "Quantum Turing machine": 14375,
        "Quantum complexity theory": 63770,
    },
    "AXE09_RAMSEY": {
        "Ramsey theory": 1997, "Ramsey's theorem": 55433,
        "Proof complexity": 933, "Decidability": 8312, "Aperiodic graph": 711,
    },
    "AXE10_FIBONACCI": {
        "Fibonacci number": 11524, "Golden ratio": 13737, "Penrose tiling": 61412,
    },
    "AXE11_TOPOLOGIE": {
        "Braid group": 53818, "Mapping class group": 15045, "Knot theory": 6795,
    },
    "AXE12_BIO_FITNESS": {
        "Fitness landscape": 63747, "Protein folding": 16301,
        "Ergodic theory": 3508, "Ergodicity": 15885, "Power law": 63029,
        "Scale-free network": 17674, "Zipf's law": 4116,
        "Monte Carlo method": 14854, "Genetic algorithm": 63295,
        "Markov chain": 64837, "Stationary distribution": 64863,
    },
}

ALL_CONCEPTS = {}
for ax_name, ax_dict in AXES.items():
    for name, idx in ax_dict.items():
        ALL_CONCEPTS[name] = idx
ALL_IDXS = set(ALL_CONCEPTS.values())
IDX_TO_AXES = defaultdict(set)
for ax_name, ax_dict in AXES.items():
    for name, idx in ax_dict.items():
        IDX_TO_AXES[idx].add(ax_name)


def classify_hole(cooc, z, expected, activity_a_norm, activity_b_norm, cooc_max):
    """
    Classify a pair into Type A, B, or C hole.
    Returns (type, score, explanation).
    """
    cooc_norm = cooc / cooc_max if cooc_max > 0 else 0

    # Thresholds
    COOC_LOW = 1.0        # below this = no real bridge
    COOC_MED = 10.0       # below this = weak bridge
    Z_NEGATIVE = -0.5     # significantly below expected

    if cooc <= COOC_LOW and z <= 0:
        # TYPE B — Conceptual: void, nobody thought to connect
        void = 1.0 - min(cooc_norm, 1.0)
        atypicality = min(abs(z), 10.0) / 10.0
        score = activity_a_norm * activity_b_norm * void * atypicality
        return "B", score, "void_invisible"

    elif cooc > COOC_LOW and z < Z_NEGATIVE:
        # TYPE C — Perceptual: bridge exists but way below expected
        if expected > 0:
            ignored_ratio = max(0, 1.0 - (cooc / expected))
        else:
            ignored_ratio = 0.0
        disruption_potential = min(abs(z), 10.0) / 10.0
        score = activity_a_norm * activity_b_norm * disruption_potential * ignored_ratio
        return "C", score, "ignored_bridge"

    elif cooc > COOC_MED and abs(z) < 2.0:
        # TYPE A — Technical: bridge active but stagnant (z ≈ 0 = exactly as expected)
        production = cooc_norm
        stagnation = 1.0 - min(abs(z) / 5.0, 1.0)  # closer to 0 = more stagnant
        score = production * stagnation * activity_a_norm * activity_b_norm
        return "A", score, "stuck_bridge"

    elif cooc > COOC_LOW and z > 0:
        # HOT — not a hole, it's a known bridge with MORE than expected
        score = 0.0
        return "HOT", score, "active_bridge"

    else:
        # WARM — exists but unremarkable
        score = 0.0
        return "WARM", score, "unremarkable"


def main():
    t0 = time.time()
    print("=" * 120)
    print("CANON UNIVERSEL v2 — TROUS TYPÉS A/B/C")
    print(f"101 concepts, 12 axes, classification Wang-Barabási / Uzzi / Wu-Evans")
    print("=" * 120)

    # === 1. Extract from WT3 ===
    print("\n[1] Extracting from WT3...")
    db = sqlite3.connect(os.path.join(REPO, "data", "wt3.db"))
    cursor = db.cursor()
    placeholders = ",".join(str(i) for i in sorted(ALL_IDXS))
    cursor.execute(f"""
        SELECT concept_a, concept_b, weight
        FROM cooc_global
        WHERE concept_a IN ({placeholders}) OR concept_b IN ({placeholders})
    """)
    cooc = {}
    while True:
        rows = cursor.fetchmany(500000)
        if not rows:
            break
        for a, b, w in rows:
            pair = (min(a, b), max(a, b))
            if pair not in cooc:
                cooc[pair] = float(w)
        print(f"    {len(cooc):,} pairs...", end="\r")
    db.close()
    print(f"\n  {len(cooc):,} pairs extracted")

    # === 2. Activity + concepts ===
    print("[2] Loading activity + concepts + species...")
    with open(os.path.join(PRED_DIR, "activity_full.json"), 'r', encoding='utf-8') as f:
        activity = np.array(json.load(f)["activity"], dtype=np.float64)
    total_works = float(activity.sum())

    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"), 'r', encoding='utf-8') as f:
        cdata = json.load(f)
    idx_to_name = {}
    idx_to_level = {}
    url_to_idx = {}
    for url, info in cdata["concepts"].items():
        idx_to_name[info["idx"]] = info["name"]
        idx_to_level[info["idx"]] = info.get("level", -1)
        url_to_idx[url] = info["idx"]

    with open(os.path.join(PRED_DIR, "species_full.json"), 'r', encoding='utf-8') as f:
        sp_data = json.load(f)
    with open(os.path.join(PRED_DIR, "collision_matrix_full.json"), 'r', encoding='utf-8') as f:
        col_data = json.load(f)
    species_names = col_data["meta"]["species_names"]
    species_map = {}
    for url, info in sp_data["concepts"].items():
        if url in url_to_idx:
            species_map[url_to_idx[url]] = info["species"]
    del sp_data, col_data, cdata, url_to_idx
    gc.collect()

    # === 3. Concept births (temporal) ===
    print("[3] Loading concept births...")
    births_path = os.path.join(REPO, "data", "scan", "concept_births.json")
    births = {}
    if os.path.exists(births_path):
        with open(births_path, 'r', encoding='utf-8') as f:
            births_raw = json.load(f)
        for k, v in births_raw.items():
            births[int(k)] = int(v)
        print(f"  {len(births)} concept births loaded")

    # === 4. Classify ALL pairs ===
    print("\n[4] Classifying all pairs (A/B/C)...")
    active_mask = activity > 0
    act_min = float(activity[active_mask].min())
    act_max = float(activity[active_mask].max())
    cooc_vals = list(cooc.values())
    cooc_max = max(cooc_vals) if cooc_vals else 1.0

    type_a = []  # Technical — stuck bridges
    type_b = []  # Conceptual — invisible voids
    type_c = []  # Perceptual — ignored bridges
    hot = []     # Not holes — active bridges
    all_scored = []

    for (idx_a, idx_b), observed in cooc.items():
        wa, wb = float(activity[idx_a]), float(activity[idx_b])
        if wa == 0 or wb == 0:
            continue

        # Skip level 0-1 for non-core
        a_in = idx_a in ALL_IDXS
        b_in = idx_b in ALL_IDXS
        lv_a = idx_to_level.get(idx_a, -1)
        lv_b = idx_to_level.get(idx_b, -1)
        if not a_in and lv_a < 2:
            continue
        if not b_in and lv_b < 2:
            continue

        # Compute z-score
        E = wa * wb / total_works
        pa, pb = wa / total_works, wb / total_works
        std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
        z = (observed - E) / std

        # Normalize activities
        an = max(min((wa - act_min) / (act_max - act_min), 1.0), 0.0)
        bn = max(min((wb - act_min) / (act_max - act_min), 1.0), 0.0)

        # Classify
        htype, score, reason = classify_hole(observed, z, E, an, bn, cooc_max)

        a_axes = IDX_TO_AXES.get(idx_a, set())
        b_axes = IDX_TO_AXES.get(idx_b, set())
        sp_a = species_map.get(idx_a, -1)
        sp_b = species_map.get(idx_b, -1)
        cross_axes = bool(a_axes and b_axes and not (a_axes & b_axes))
        cross_species = (sp_a != sp_b and sp_a >= 0 and sp_b >= 0)
        both_core = a_in and b_in

        birth_a = births.get(idx_a, 0)
        birth_b = births.get(idx_b, 0)

        entry = {
            "a_name": idx_to_name.get(idx_a, f"?{idx_a}"),
            "b_name": idx_to_name.get(idx_b, f"?{idx_b}"),
            "a_idx": idx_a, "b_idx": idx_b,
            "a_axes": sorted(a_axes), "b_axes": sorted(b_axes),
            "cooc": observed, "expected": E, "z": z, "score": score,
            "type": htype, "reason": reason,
            "sp_a": sp_a, "sp_b": sp_b,
            "sp_a_name": species_names.get(str(sp_a), "?"),
            "sp_b_name": species_names.get(str(sp_b), "?"),
            "cross_axes": cross_axes, "cross_species": cross_species,
            "both_core": both_core,
            "birth_a": birth_a, "birth_b": birth_b,
            "works_a": wa, "works_b": wb,
        }

        if htype == "A":
            type_a.append(entry)
        elif htype == "B":
            type_b.append(entry)
        elif htype == "C":
            type_c.append(entry)
        elif htype == "HOT":
            hot.append(entry)

        all_scored.append(entry)

    # Also add desert pairs (cooc=0 between core concepts)
    print("  Adding deserts (core×core, cooc=0)...")
    core_list = sorted(ALL_IDXS)
    desert_count = 0
    for i, idx_a in enumerate(core_list):
        for idx_b in core_list[i+1:]:
            pair = (min(idx_a, idx_b), max(idx_a, idx_b))
            if pair in cooc:
                continue
            a_axes = IDX_TO_AXES.get(idx_a, set())
            b_axes = IDX_TO_AXES.get(idx_b, set())
            if not (a_axes and b_axes and not (a_axes & b_axes)):
                continue

            wa, wb = float(activity[idx_a]), float(activity[idx_b])
            if wa == 0 or wb == 0:
                continue
            E = wa * wb / total_works
            an = max(min((wa - act_min) / (act_max - act_min), 1.0), 0.0)
            bn = max(min((wb - act_min) / (act_max - act_min), 1.0), 0.0)

            # z for cooc=0
            pa, pb = wa / total_works, wb / total_works
            std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
            z = (0 - E) / std

            # All deserts are Type B by definition
            void = 1.0
            atypicality = min(abs(z), 10.0) / 10.0
            score = an * bn * void * atypicality

            sp_a = species_map.get(idx_a, -1)
            sp_b = species_map.get(idx_b, -1)
            birth_a = births.get(idx_a, 0)
            birth_b = births.get(idx_b, 0)

            entry = {
                "a_name": idx_to_name.get(idx_a, f"?{idx_a}"),
                "b_name": idx_to_name.get(idx_b, f"?{idx_b}"),
                "a_idx": idx_a, "b_idx": idx_b,
                "a_axes": sorted(a_axes), "b_axes": sorted(b_axes),
                "cooc": 0.0, "expected": E, "z": z, "score": score,
                "type": "B", "reason": "desert_absolute",
                "sp_a": sp_a, "sp_b": sp_b,
                "sp_a_name": species_names.get(str(sp_a), "?"),
                "sp_b_name": species_names.get(str(sp_b), "?"),
                "cross_axes": True, "cross_species": (sp_a != sp_b and sp_a >= 0 and sp_b >= 0),
                "both_core": True,
                "birth_a": birth_a, "birth_b": birth_b,
                "works_a": wa, "works_b": wb,
            }
            type_b.append(entry)
            desert_count += 1

    # Sort each type by score
    type_a.sort(key=lambda x: -x["score"])
    type_b.sort(key=lambda x: -x["score"])
    type_c.sort(key=lambda x: -x["score"])
    hot.sort(key=lambda x: -x["cooc"])

    print(f"\n  TYPE A (Technique — stuck):     {len(type_a):,}")
    print(f"  TYPE B (Conceptuel — invisible): {len(type_b):,}")
    print(f"  TYPE C (Perceptuel — ignoré):    {len(type_c):,}")
    print(f"  HOT (ponts actifs):              {len(hot):,}")
    print(f"  Déserts ajoutés:                 {desert_count:,}")

    # ══════════════════════════════════════════════
    # DISPLAY
    # ══════════════════════════════════════════════

    def show_entries(title, entries, n=60):
        print(f"\n{'='*120}")
        print(title)
        print(f"{'='*120}")
        for i, e in enumerate(entries[:n]):
            ax_a = e["a_axes"][0][:8] if e["a_axes"] else "?"
            ax_b = e["b_axes"][0][:8] if e["b_axes"] else "?"
            tag = "DESERT" if e["reason"] == "desert_absolute" else e["reason"][:12]
            core = "*" if e["both_core"] else " "
            yr_a = e["birth_a"] if e["birth_a"] else "?"
            yr_b = e["birth_b"] if e["birth_b"] else "?"
            print(f"  {i+1:3d}.{core} score={e['score']:.6f} z={e['z']:8.1f}"
                  f" cooc={e['cooc']:10.1f} E={e['expected']:10.1f}"
                  f" | {e['a_name'][:28]:28s} × {e['b_name'][:28]:28s}"
                  f" | {ax_a}×{ax_b} | {tag}"
                  f" | born:{yr_a}/{yr_b}")

    # === TYPE A ===
    show_entries(
        "TYPE A — TECHNIQUE : le pont existe, tout le monde sait, PERSONNE NE PEUT\n"
        "= Production haute, innovation zéro, z ≈ 0 = exactement attendu = STAGNANT =\n"
        "= C'est le Poincaré : le problème est connu, les outils manquent =",
        type_a, 60
    )

    # Cross-axis Type A
    type_a_cross = [e for e in type_a if e["cross_axes"]]
    show_entries(
        f"TYPE A CROSS-AXES ({len(type_a_cross)} ponts bloqués entre axes différents)\n"
        "= Paires où les deux domaines SAVENT mais ne PEUVENT PAS =",
        type_a_cross, 40
    )

    # === TYPE B ===
    show_entries(
        "TYPE B — CONCEPTUEL : personne n'a l'IDÉE de connecter\n"
        "= Cooc ≈ 0, z négatif, activité haute des deux côtés = VIDE INVISIBLE =\n"
        "= C'est le GAN : game theory × deep learning avant Goodfellow =",
        type_b, 60
    )

    # Cross-axis Type B
    type_b_cross = [e for e in type_b if e["cross_axes"]]
    show_entries(
        f"TYPE B CROSS-AXES ({len(type_b_cross)} vides invisibles entre axes)\n"
        "= LE TERRAIN DE CHASSE DU CANON =",
        type_b_cross, 60
    )

    # Type B touching P vs NP specifically
    pvsnp = 13541
    type_b_pvsnp = [e for e in type_b if e["a_idx"] == pvsnp or e["b_idx"] == pvsnp]
    show_entries(
        f"TYPE B — P vs NP ({len(type_b_pvsnp)} vides invisibles autour de P≠NP)",
        type_b_pvsnp, 30
    )

    # Type B touching Ramsey
    ramsey_idxs = {1997, 55433}
    type_b_ramsey = [e for e in type_b if e["a_idx"] in ramsey_idxs or e["b_idx"] in ramsey_idxs]
    show_entries(
        f"TYPE B — RAMSEY ({len(type_b_ramsey)} vides invisibles autour de Ramsey)",
        type_b_ramsey, 30
    )

    # === TYPE C ===
    show_entries(
        "TYPE C — PERCEPTUEL : le pont EXISTE mais est IGNORÉ\n"
        "= Cooc > 0 mais << attendue, z très négatif = LA CONNEXION EST LÀ MAIS PERSONNE NE REGARDE =\n"
        "= C'est le mRNA Karikó : l'outil existe, le monde l'ignore =",
        type_c, 60
    )

    # Cross-axis Type C
    type_c_cross = [e for e in type_c if e["cross_axes"]]
    show_entries(
        f"TYPE C CROSS-AXES ({len(type_c_cross)} ponts ignorés entre axes)\n"
        "= ATTENTION : la réponse est peut-être ICI =",
        type_c_cross, 60
    )

    # Type C touching P vs NP
    type_c_pvsnp = [e for e in type_c if e["a_idx"] == pvsnp or e["b_idx"] == pvsnp]
    show_entries(
        f"TYPE C — P vs NP ({len(type_c_pvsnp)} ponts ignorés autour de P≠NP)\n"
        "= Quelqu'un a DÉJÀ fait le lien mais le monde s'en fout =",
        type_c_pvsnp, 30
    )

    # Type C touching Ramsey
    type_c_ramsey = [e for e in type_c if e["a_idx"] in ramsey_idxs or e["b_idx"] in ramsey_idxs]
    show_entries(
        f"TYPE C — RAMSEY ({len(type_c_ramsey)} ponts ignorés autour de Ramsey)",
        type_c_ramsey, 30
    )

    # === HOT (existing bridges) ===
    hot_cross = [e for e in hot if e["cross_axes"]]
    show_entries(
        f"PONTS CHAUDS CROSS-AXES ({len(hot_cross)} — les connexions qui MARCHENT)\n"
        "= Ces ponts existent et sont actifs = le canon ne tire PAS ici =",
        hot_cross, 30
    )

    # === MATRICE par type ===
    print(f"\n{'='*120}")
    print("MATRICE 12×12 PAR TYPE DE TROU")
    print(f"{'='*120}")

    ax_names = sorted(AXES.keys())
    short = {n: n[5:13] for n in ax_names}  # "01_CAYLE", etc.

    for htype, hlist, hlabel in [("A", type_a, "TECHNIQUE"), ("B", type_b, "CONCEPTUEL"), ("C", type_c, "PERCEPTUEL")]:
        print(f"\n  --- TYPE {htype} ({hlabel}) ---")
        counts = defaultdict(int)
        scores = defaultdict(float)
        for e in hlist:
            for aa in e["a_axes"]:
                for bb in e["b_axes"]:
                    if aa != bb:
                        key = (min(aa, bb), max(aa, bb))
                        counts[key] += 1
                        scores[key] += e["score"]

        print(f"  {'':>10s}", end="")
        for n in ax_names:
            print(f" {short[n]:>8s}", end="")
        print()
        for ni in ax_names:
            print(f"  {short[ni]:>10s}", end="")
            for nj in ax_names:
                key = (min(ni, nj), max(ni, nj))
                c = counts.get(key, 0)
                if c > 0:
                    print(f" {c:8d}", end="")
                else:
                    print(f" {'·':>8s}", end="")
            print()

    # === SYNTHÈSE FINALE ===
    print(f"\n{'='*120}")
    print("SYNTHÈSE — OÙ TIRER ?")
    print(f"{'='*120}")

    print(f"\n  TYPE A (Technique — stuck): {len(type_a):,} ponts")
    print(f"    → Cross-axes: {len(type_a_cross):,}")
    print(f"    → Le problème est CONNU mais les outils MANQUENT")
    if type_a_cross:
        print(f"    → Top: {type_a_cross[0]['a_name']} × {type_a_cross[0]['b_name']}")

    print(f"\n  TYPE B (Conceptuel — invisible): {len(type_b):,} vides")
    print(f"    → Cross-axes: {len(type_b_cross):,}")
    print(f"    → Personne n'a PENSÉ à connecter")
    if type_b_cross:
        print(f"    → Top: {type_b_cross[0]['a_name']} × {type_b_cross[0]['b_name']}")

    print(f"\n  TYPE C (Perceptuel — ignoré): {len(type_c):,} ponts")
    print(f"    → Cross-axes: {len(type_c_cross):,}")
    print(f"    → Le pont EXISTE mais est SOUS-ÉVALUÉ")
    if type_c_cross:
        print(f"    → Top: {type_c_cross[0]['a_name']} × {type_c_cross[0]['b_name']}")

    print(f"\n  P vs NP:")
    print(f"    → Type B (vides): {len(type_b_pvsnp)}")
    print(f"    → Type C (ignorés): {len(type_c_pvsnp)}")

    print(f"\n  Ramsey:")
    print(f"    → Type B (vides): {len(type_b_ramsey)}")
    print(f"    → Type C (ignorés): {len(type_c_ramsey)}")

    print(f"\n  Temps: {time.time()-t0:.0f}s")

    # === SAVE ===
    os.makedirs(os.path.join(REPO, "data", "results"), exist_ok=True)
    outfile = os.path.join(REPO, "data", "results", "scan_cannon_typed.json")
    save = {
        "scan": "cannon_typed_v1",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_concepts": len(ALL_IDXS),
        "n_type_a": len(type_a),
        "n_type_b": len(type_b),
        "n_type_c": len(type_c),
        "n_hot": len(hot),
        "type_a_top100": type_a[:100],
        "type_a_cross_top50": type_a_cross[:50],
        "type_b_top100": type_b[:100],
        "type_b_cross_top50": type_b_cross[:50],
        "type_b_pvsnp": type_b_pvsnp[:30],
        "type_b_ramsey": type_b_ramsey[:30],
        "type_c_top100": type_c[:100],
        "type_c_cross_top50": type_c_cross[:50],
        "type_c_pvsnp": type_c_pvsnp[:30],
        "type_c_ramsey": type_c_ramsey[:30],
        "hot_cross_top30": hot_cross[:30],
    }
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(save, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")


if __name__ == "__main__":
    main()
