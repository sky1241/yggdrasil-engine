#!/usr/bin/env python3
"""
YGGDRASIL — CANON UNIVERSEL : TIR DEPUIS L'ESPACE
═══════════════════════════════════════════════════════
12 axes, ~100 concepts, matrice complète.
P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|

Cibles: God's Number, P vs NP, Ramsey R(5,5)
Méthode: intersection de contraintes multi-sources orthogonales

Sky × Claude — 20 Mars 2026, Versoix
"""

import json
import os
import sys
import io
import time
import gc
import numpy as np
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
PRED_DIR = os.path.join(REPO, "experiments", "predictions_2025")
N_CONCEPTS = 65026

# ══════════════════════════════════════════════
# 12 AXES — LA BALLE COMPLÈTE
# ══════════════════════════════════════════════

AXES = {
    "AXE01_CAYLEY": {
        "Cayley graph": 3217,
        "Wreath product": 64319,
        "Permutation group": 63903,
        "Symmetric group": 4492,
        "Semidirect product": 61178,
        "Simple group": 57573,
        "CFSG": 59370,
        "Normal subgroup": 917,
        "Nilpotent group": 16592,
        "Coset": 62772,
        "Commutator subgroup": 6423,
        "Group theory": 62210,
        "Cayley's theorem": 54928,
    },
    "AXE02_SPECTRAL": {
        "Spectral gap": 28454,
        "Expander graph": 8508,
        "Markov chain mixing time": 64555,
        "Eigenvalues and eigenvectors": 9157,
        "Laplacian matrix": 2429,
        "Random walk": 3378,
        "Expander code": 1378,
    },
    "AXE03_BRIDGES": {
        "Knot theory": 6795,
        "Unknot": 38541,
        "Coding theory": 2234,
        "Sphere packing": 13095,
        "Sorting network": 59567,
        "Quantum walk": 6307,
        "Percolation theory": 2489,
        "Combinatorial optimization": 57247,
        "Braid group": 53818,
        "Mapping class group": 15045,
    },
    "AXE04_CANNON": {
        "Constraint satisfaction problem": 15562,
        "PSPACE": 15276,
        "Inverse problem": 5503,
        "Interval arithmetic": 14255,
        "Sensitivity analysis": 11886,
        "Phase transition": 7678,
        "Complexity of CSP": 5038,
    },
    "AXE05_PHYSIQUE": {
        "Entropy": 1033,
        "Statistical mechanics": 65006,
        "Ising model": 56807,
        "Spin glass": 7925,
        "Partition function (QFT)": 29774,
        "Potts model": 64855,
        "Spin model": 38170,
        "Renormalization": 10319,
        "Renormalization group": 60204,
        "Critical exponent": 10021,
        "Percolation threshold": 17933,
        "Percolation critical exponents": 9140,
        "Boltzmann entropy formula": 53836,
        "Resistance distance": 59049,
        "Electrical network": 15129,
        "Cellular automaton": 54073,
        "Simulated annealing": 4263,
        "Reversible computing": 16053,
        "Gibbs free energy": 7259,
        "Helmholtz free energy": 17989,
    },
    "AXE06_INFORMATION": {
        "Information theory": 57221,
        "Kolmogorov complexity": 34208,
        "Data compression": 61733,
        "Entropy thermo+info": 7582,
        "Quantum information": 10891,
        "Quantum computer": 58566,
        "Quantum error correction": 56695,
    },
    "AXE07_ESPACE": {
        "Cosmology": 17790,
        "Holographic principle": 13175,
        "Penrose tiling": 61412,
        "Fractal": 54881,
        "Self-similarity": 3102,
        "Fractal dimension": 17805,
    },
    "AXE08_PvsNP": {
        "P versus NP problem": 13541,
        "Computational complexity theory": 12499,
        "Boolean satisfiability": 60347,
        "NP-complete": 3609,
        "Complexity class": 54722,
        "Proof complexity": 933,
        "Circuit complexity": 63572,
        "Turing machine": 47107,
        "Halting problem": 5866,
        "Undecidable problem": 14370,
        "Decidability": 8312,
        "Godel incompleteness": 12665,
        "Parameterized complexity": 10214,
        "Quantum Turing machine": 14375,
        "Quantum complexity theory": 63770,
    },
    "AXE09_RAMSEY": {
        "Ramsey theory": 1997,
        "Ramsey's theorem": 55433,
        "Proof complexity": 933,
        "Decidability": 8312,
        "Aperiodic graph": 711,
    },
    "AXE10_FIBONACCI": {
        "Fibonacci number": 11524,
        "Golden ratio": 13737,
        "Penrose tiling": 61412,
    },
    "AXE11_TOPOLOGIE": {
        "Braid group": 53818,
        "Mapping class group": 15045,
        "Knot theory": 6795,
    },
    "AXE12_BIO_FITNESS": {
        "Fitness landscape": 63747,
        "Protein folding": 16301,
        "Ergodic theory": 3508,
        "Ergodicity": 15885,
        "Power law": 63029,
        "Scale-free network": 17674,
        "Zipf's law": 4116,
        "Monte Carlo method": 14854,
        "Genetic algorithm": 63295,
        "Markov chain": 64837,
        "Stationary distribution": 64863,
    },
}

# Build the complete set
ALL_CONCEPTS = {}
for ax_name, ax_dict in AXES.items():
    for name, idx in ax_dict.items():
        ALL_CONCEPTS[name] = idx
ALL_IDXS = set(ALL_CONCEPTS.values())

# Concept → axes membership
IDX_TO_AXES = defaultdict(set)
for ax_name, ax_dict in AXES.items():
    for name, idx in ax_dict.items():
        IDX_TO_AXES[idx].add(ax_name)


def extract_all_pairs():
    """Extract co-occurrences from WT3 cooc_global (69M pairs, SQLite)."""
    import sqlite3
    print("[1] Extracting pairs from WT3 cooc_global...")
    t0 = time.time()

    db_path = os.path.join(REPO, "data", "wt3.db")
    db = sqlite3.connect(db_path)
    cursor = db.cursor()

    core_idxs = sorted(ALL_IDXS)
    placeholders = ",".join(str(i) for i in core_idxs)

    # Get ALL pairs where at least one concept is in our set
    query = f"""
        SELECT concept_a, concept_b, weight
        FROM cooc_global
        WHERE concept_a IN ({placeholders}) OR concept_b IN ({placeholders})
    """
    print(f"  Querying {len(core_idxs)} concepts against 69M pairs...")
    cursor.execute(query)

    pairs = {}
    row_count = 0
    while True:
        rows = cursor.fetchmany(500000)
        if not rows:
            break
        for a, b, w in rows:
            pair = (min(a, b), max(a, b))
            if pair not in pairs:
                pairs[pair] = float(w)
        row_count += len(rows)
        print(f"    fetched {row_count:,} rows...", end="\r")

    db.close()
    print(f"\n  Unique pairs: {len(pairs):,} in {time.time()-t0:.1f}s")
    return pairs


def main():
    t0 = time.time()
    print("=" * 120)
    print("CANON UNIVERSEL — TIR DEPUIS L'ESPACE")
    print(f"12 axes, {len(ALL_IDXS)} concepts uniques, P4 Uzzi z-scores")
    print("Cibles: God's Number / P vs NP / Ramsey R(5,5)")
    print("=" * 120)

    # === 1. Extract co-occurrences ===
    cooc = extract_all_pairs()

    # === 2. Activity ===
    print("\n[2] Loading activity...")
    with open(os.path.join(PRED_DIR, "activity_full.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)
    total_works = float(activity.sum())
    del act_data
    gc.collect()

    # === 3. Concepts + species ===
    print("[3] Loading concepts + species...")
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

    # === 4. P4 scoring ===
    print("\n[4] Computing P4 for ALL pairs...")
    active_mask = activity > 0
    act_min = float(activity[active_mask].min())
    act_max = float(activity[active_mask].max())
    cooc_vals = list(cooc.values())
    cooc_max = max(cooc_vals) if cooc_vals else 1.0

    results = []
    for (idx_a, idx_b), observed in cooc.items():
        wa, wb = activity[idx_a], activity[idx_b]
        if wa == 0 or wb == 0:
            continue

        E = wa * wb / total_works
        pa, pb = wa / total_works, wb / total_works
        std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
        z = (observed - E) / std

        an = max(min((wa - act_min) / (act_max - act_min), 1.0), 0.0)
        bn = max(min((wb - act_min) / (act_max - act_min), 1.0), 0.0)
        gap = 1.0 - observed / cooc_max
        p4 = an * bn * gap * abs(z)

        # Determine axes for each concept
        a_axes = IDX_TO_AXES.get(idx_a, set())
        b_axes = IDX_TO_AXES.get(idx_b, set())
        a_in = idx_a in ALL_IDXS
        b_in = idx_b in ALL_IDXS

        sp_a = species_map.get(idx_a, -1)
        sp_b = species_map.get(idx_b, -1)
        lv_a = idx_to_level.get(idx_a, -1)
        lv_b = idx_to_level.get(idx_b, -1)

        # Skip level 0-1 for non-core concepts
        if not a_in and lv_a < 2:
            continue
        if not b_in and lv_b < 2:
            continue

        cross_species = (sp_a != sp_b and sp_a >= 0 and sp_b >= 0)
        cross_axes = bool(a_axes and b_axes and not (a_axes & b_axes))
        both_core = a_in and b_in

        results.append({
            "a_name": idx_to_name.get(idx_a, f"?{idx_a}"),
            "b_name": idx_to_name.get(idx_b, f"?{idx_b}"),
            "a_idx": idx_a,
            "b_idx": idx_b,
            "a_axes": sorted(a_axes),
            "b_axes": sorted(b_axes),
            "cooc": observed,
            "z": z,
            "p4": p4,
            "sp_a": sp_a,
            "sp_b": sp_b,
            "sp_a_name": species_names.get(str(sp_a), "?"),
            "sp_b_name": species_names.get(str(sp_b), "?"),
            "cross_species": cross_species,
            "cross_axes": cross_axes,
            "both_core": both_core,
        })

    results.sort(key=lambda x: x["p4"], reverse=True)
    print(f"  {len(results):,} pairs scored")

    # === 5. MATRICE 12×12 CROSS-AXE ===
    print(f"\n{'='*120}")
    print("MATRICE 12×12 — CO-OCCURRENCES INTER-AXES")
    print("= Chaque cellule = nombre de paires internes, somme cooc, z moyen =")
    print(f"{'='*120}")

    ax_names = sorted(AXES.keys())
    # Internal pairs between axes
    ax_matrix_count = defaultdict(int)
    ax_matrix_cooc = defaultdict(float)
    ax_matrix_z_sum = defaultdict(float)
    ax_matrix_holes = defaultdict(int)  # z < 0

    for (idx_a, idx_b), observed in cooc.items():
        a_ax = IDX_TO_AXES.get(idx_a, set())
        b_ax = IDX_TO_AXES.get(idx_b, set())
        if not a_ax or not b_ax:
            continue

        wa, wb = activity[idx_a], activity[idx_b]
        if wa == 0 or wb == 0:
            continue
        E = wa * wb / total_works
        pa, pb = wa / total_works, wb / total_works
        std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
        z = (observed - E) / std

        for aa in a_ax:
            for bb in b_ax:
                key = (min(aa, bb), max(aa, bb))
                ax_matrix_count[key] += 1
                ax_matrix_cooc[key] += observed
                ax_matrix_z_sum[key] += z
                if z < 0:
                    ax_matrix_holes[key] += 1

    # Print matrix
    short = {n: n.replace("AXE", "").replace("_", " ")[:12] for n in ax_names}
    print(f"\n{'':>14s}", end="")
    for n in ax_names:
        print(f" {short[n]:>12s}", end="")
    print()

    for i, ni in enumerate(ax_names):
        print(f"  {short[ni]:>12s}", end="")
        for j, nj in enumerate(ax_names):
            key = (min(ni, nj), max(ni, nj))
            cnt = ax_matrix_count.get(key, 0)
            if cnt > 0:
                avg_z = ax_matrix_z_sum[key] / cnt
                holes = ax_matrix_holes.get(key, 0)
                if holes > cnt * 0.5:
                    tag = f"{cnt:3d}H{holes:2d}"
                else:
                    tag = f"{cnt:5d}"
                print(f" {tag:>12s}", end="")
            else:
                print(f" {'---':>12s}", end="")
        print()

    # === 6. DÉSERTS — paires core×core à cooc=0 ===
    print(f"\n{'='*120}")
    print("DÉSERTS ABSOLUS — paires core×core sans AUCUNE co-occurrence")
    print("= Le canon tire ICI — vecteurs parfaitement orthogonaux =")
    print(f"{'='*120}")

    core_list = sorted(ALL_IDXS)
    deserts = []
    for i, idx_a in enumerate(core_list):
        for idx_b in core_list[i+1:]:
            pair = (min(idx_a, idx_b), max(idx_a, idx_b))
            if pair not in cooc:
                a_ax = IDX_TO_AXES.get(idx_a, set())
                b_ax = IDX_TO_AXES.get(idx_b, set())
                # Only interesting if cross-axis
                if a_ax and b_ax and not (a_ax & b_ax):
                    wa = float(activity[idx_a])
                    wb = float(activity[idx_b])
                    deserts.append({
                        "a_name": idx_to_name.get(idx_a, f"?{idx_a}"),
                        "b_name": idx_to_name.get(idx_b, f"?{idx_b}"),
                        "a_idx": idx_a,
                        "b_idx": idx_b,
                        "a_axes": sorted(a_ax),
                        "b_axes": sorted(b_ax),
                        "works_product": wa * wb,
                    })

    # Sort by works product (most surprising deserts first — big concepts, zero cooc)
    deserts.sort(key=lambda x: -x["works_product"])
    print(f"  Total cross-axis deserts (cooc=0): {len(deserts):,}")

    for i, d in enumerate(deserts[:100]):
        wp = d["works_product"]
        ax_a = d["a_axes"][0][:12] if d["a_axes"] else "?"
        ax_b = d["b_axes"][0][:12] if d["b_axes"] else "?"
        print(f"  {i+1:3d}. {d['a_name'][:30]:30s} × {d['b_name'][:30]:30s}"
              f" | works={wp:14,.0f} | {ax_a} × {ax_b}")

    # === 7. AXES-SPÉCIFIQUES — Trous les plus profonds par axe ===
    print(f"\n{'='*120}")
    print("TROUS PAR AXE — Top structural holes (z < 0) rattachés à chaque axe")
    print(f"{'='*120}")

    for ax_name in ax_names:
        ax_idxs = set(AXES[ax_name].values())
        ax_results = [r for r in results
                      if (r["a_idx"] in ax_idxs or r["b_idx"] in ax_idxs)
                      and r["z"] < 0 and not r["both_core"]]
        ax_results.sort(key=lambda x: x["z"])
        print(f"\n  --- {ax_name} ({len(ax_results)} holes) ---")
        for i, r in enumerate(ax_results[:15]):
            core_name = r["a_name"] if r["a_idx"] in ax_idxs else r["b_name"]
            other_name = r["b_name"] if r["a_idx"] in ax_idxs else r["a_name"]
            print(f"    {i+1:2d}. z={r['z']:9.1f} P4={r['p4']:.4f}"
                  f" | {core_name[:25]:25s} × {other_name[:30]}"
                  f" | [{r['sp_a_name'][:10]}×{r['sp_b_name'][:10]}]")

    # === 8. CIBLE P vs NP — Tout ce qui touche concept 13541 ===
    print(f"\n{'='*120}")
    print("CIBLE: P versus NP (concept 13541)")
    print(f"{'='*120}")
    pvsnp_idx = 13541
    pvsnp_pairs = [r for r in results if r["a_idx"] == pvsnp_idx or r["b_idx"] == pvsnp_idx]
    pvsnp_pairs.sort(key=lambda x: x["p4"], reverse=True)
    print(f"  Total pairs touching P vs NP: {len(pvsnp_pairs)}")

    # P vs NP × other core concepts
    pvsnp_core = [r for r in pvsnp_pairs if r["both_core"]]
    pvsnp_external = [r for r in pvsnp_pairs if not r["both_core"]]
    pvsnp_holes = [r for r in pvsnp_pairs if r["z"] < 0]

    print(f"  Core connections: {len(pvsnp_core)}")
    print(f"  External connections: {len(pvsnp_external)}")
    print(f"  Structural holes (z<0): {len(pvsnp_holes)}")

    print(f"\n  P vs NP × Core concepts (co-occurrence dans la littérature):")
    for r in pvsnp_core[:30]:
        other = r["b_name"] if r["a_idx"] == pvsnp_idx else r["a_name"]
        other_ax = r["b_axes"] if r["a_idx"] == pvsnp_idx else r["a_axes"]
        zs = "+" if r["z"] > 0 else ""
        print(f"    z={zs}{r['z']:8.1f} cooc={r['cooc']:10.1f} P4={r['p4']:.4f}"
              f" | {other[:40]} | {other_ax}")

    print(f"\n  P vs NP × External (top 30 by P4):")
    for i, r in enumerate(pvsnp_external[:30]):
        other = r["b_name"] if r["a_idx"] == pvsnp_idx else r["a_name"]
        zs = "+" if r["z"] > 0 else ""
        tag = "HOLE" if r["z"] < 0 else "    "
        print(f"    {i+1:2d}. {tag} z={zs}{r['z']:8.1f} P4={r['p4']:.4f}"
              f" | {other[:45]} | [{r['sp_a_name'][:10]}×{r['sp_b_name'][:10]}]")

    # P vs NP deserts
    pvsnp_deserts = [d for d in deserts if d["a_idx"] == pvsnp_idx or d["b_idx"] == pvsnp_idx]
    print(f"\n  P vs NP — DÉSERTS ABSOLUS (cooc=0 avec concepts core):")
    for d in pvsnp_deserts[:30]:
        other = d["b_name"] if d["a_idx"] == pvsnp_idx else d["a_name"]
        other_ax = d["b_axes"] if d["a_idx"] == pvsnp_idx else d["a_axes"]
        print(f"    {other[:45]:45s} | {other_ax}")

    # === 9. CIBLE RAMSEY ===
    print(f"\n{'='*120}")
    print("CIBLE: Ramsey theory (concepts 1997, 55433)")
    print(f"{'='*120}")
    ramsey_idxs = {1997, 55433}
    ramsey_pairs = [r for r in results if r["a_idx"] in ramsey_idxs or r["b_idx"] in ramsey_idxs]
    ramsey_pairs.sort(key=lambda x: x["p4"], reverse=True)
    print(f"  Total pairs touching Ramsey: {len(ramsey_pairs)}")

    ramsey_core = [r for r in ramsey_pairs if r["both_core"]]
    print(f"\n  Ramsey × Core concepts:")
    for r in ramsey_core[:30]:
        ram = r["a_name"] if r["a_idx"] in ramsey_idxs else r["b_name"]
        other = r["b_name"] if r["a_idx"] in ramsey_idxs else r["a_name"]
        other_ax = r["b_axes"] if r["a_idx"] in ramsey_idxs else r["a_axes"]
        zs = "+" if r["z"] > 0 else ""
        print(f"    z={zs}{r['z']:8.1f} cooc={r['cooc']:10.1f}"
              f" | {ram[:20]} × {other[:35]} | {other_ax}")

    ramsey_deserts = [d for d in deserts if d["a_idx"] in ramsey_idxs or d["b_idx"] in ramsey_idxs]
    print(f"\n  Ramsey — DÉSERTS ({len(ramsey_deserts)}):")
    for d in ramsey_deserts[:30]:
        other = d["b_name"] if d["a_idx"] in ramsey_idxs else d["a_name"]
        other_ax = d["b_axes"] if d["a_idx"] in ramsey_idxs else d["a_axes"]
        print(f"    {other[:45]:45s} | {other_ax}")

    # === 10. TOP GLOBAL — Paires les plus surprenantes ===
    print(f"\n{'='*120}")
    print("TOP 200 GLOBAL — Paires cross-axes avec P4 le plus haut")
    print(f"{'='*120}")
    cross_ax = [r for r in results if r["cross_axes"]]
    for i, r in enumerate(cross_ax[:200]):
        zs = "+" if r["z"] > 0 else ""
        tag = "HOLE" if r["z"] < 0 else "    "
        ax_a = r["a_axes"][0][:12] if r["a_axes"] else "?"
        ax_b = r["b_axes"][0][:12] if r["b_axes"] else "?"
        print(f"  {i+1:3d}. {tag} P4={r['p4']:8.4f} z={zs}{r['z']:8.1f}"
              f" | {r['a_name'][:28]:28s} × {r['b_name'][:28]:28s}"
              f" | {ax_a}×{ax_b}")

    # === 11. Z-SCORE D'INDÉPENDANCE — pour le canon ===
    print(f"\n{'='*120}")
    print("Z-SCORES D'INDÉPENDANCE — Axes physiques vs axes mathématiques")
    print("= z ~ 0 ou négatif = orthogonal = bon pour le canon =")
    print(f"{'='*120}")

    math_axes = {"AXE01_CAYLEY", "AXE02_SPECTRAL", "AXE03_BRIDGES", "AXE04_CANNON"}
    phys_axes = {"AXE05_PHYSIQUE", "AXE06_INFORMATION", "AXE07_ESPACE", "AXE12_BIO_FITNESS"}

    for pax in sorted(phys_axes):
        for max_ in sorted(math_axes):
            key = (min(pax, max_), max(pax, max_))
            cnt = ax_matrix_count.get(key, 0)
            if cnt > 0:
                avg_z = ax_matrix_z_sum[key] / cnt
                holes = ax_matrix_holes.get(key, 0)
                total_cooc = ax_matrix_cooc.get(key, 0)
                zs = "+" if avg_z > 0 else ""
                print(f"  {pax:20s} × {max_:20s} | pairs={cnt:4d}"
                      f" | avg_z={zs}{avg_z:8.1f} | holes={holes:3d}/{cnt:3d}"
                      f" | cooc_sum={total_cooc:12,.0f}")
            else:
                print(f"  {pax:20s} × {max_:20s} | DÉSERT TOTAL (0 paires)")

    # === 12. SUMMARY + SAVE ===
    print(f"\n{'='*120}")
    print("SYNTHÈSE CANON UNIVERSEL")
    print(f"{'='*120}")
    print(f"  Concepts uniques: {len(ALL_IDXS)}")
    print(f"  Paires totales scorées: {len(results):,}")
    print(f"  Paires cross-axes: {len(cross_ax):,}")
    print(f"  Déserts absolus cross-axes: {len(deserts):,}")
    holes_all = [r for r in results if r["z"] < 0]
    print(f"  Trous structurels (z<0): {len(holes_all):,}")
    print(f"  Temps total: {time.time()-t0:.0f}s")

    # Species distribution for cross-axis pairs
    sp_dist = defaultdict(lambda: {"count": 0, "holes": 0, "p4_sum": 0.0})
    for r in cross_ax[:500]:
        key = f"{r['sp_a_name']} × {r['sp_b_name']}"
        sp_dist[key]["count"] += 1
        sp_dist[key]["p4_sum"] += r["p4"]
        if r["z"] < 0:
            sp_dist[key]["holes"] += 1

    print(f"\n  Top 20 species collisions (cross-axis):")
    for k, v in sorted(sp_dist.items(), key=lambda x: -x[1]["p4_sum"])[:20]:
        print(f"    {k:50s} | {v['count']:3d} pairs | {v['holes']:2d} holes | P4={v['p4_sum']:.2f}")

    # Save
    os.makedirs(os.path.join(REPO, "data", "results"), exist_ok=True)
    outfile = os.path.join(REPO, "data", "results", "scan_cannon_universal.json")
    save_data = {
        "scan": "cannon_universal_v1",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "query": "Canon Universel — Tir depuis l'espace — God's Number + P vs NP + Ramsey",
        "n_concepts": len(ALL_IDXS),
        "n_axes": len(AXES),
        "axes": {k: list(v.keys()) for k, v in AXES.items()},
        "n_pairs_total": len(results),
        "n_cross_axes": len(cross_ax),
        "n_deserts": len(deserts),
        "n_holes": len(holes_all),
        "top_200_cross_axes": cross_ax[:200],
        "top_100_deserts": deserts[:100],
        "pvsnp_pairs": pvsnp_pairs[:50],
        "pvsnp_deserts": pvsnp_deserts[:30],
        "ramsey_pairs": ramsey_pairs[:50],
        "ramsey_deserts": ramsey_deserts[:30],
        "axis_matrix": {
            f"{k[0]}×{k[1]}": {
                "count": ax_matrix_count[k],
                "cooc_sum": ax_matrix_cooc[k],
                "z_avg": ax_matrix_z_sum[k] / ax_matrix_count[k] if ax_matrix_count[k] > 0 else 0,
                "holes": ax_matrix_holes.get(k, 0),
            }
            for k in ax_matrix_count
        },
        "independence_scores": {},
    }

    # Independence scores
    for pax in sorted(phys_axes):
        for max_ in sorted(math_axes):
            key = (min(pax, max_), max(pax, max_))
            cnt = ax_matrix_count.get(key, 0)
            avg_z = ax_matrix_z_sum[key] / cnt if cnt > 0 else None
            save_data["independence_scores"][f"{pax}×{max_}"] = {
                "pairs": cnt,
                "avg_z": avg_z,
                "holes": ax_matrix_holes.get(key, 0),
                "verdict": "ORTHOGONAL" if avg_z is not None and avg_z <= 0 else
                           "CORRELATED" if avg_z is not None and avg_z > 5 else
                           "DESERT" if cnt == 0 else "WEAK"
            }

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")


if __name__ == "__main__":
    main()
