#!/usr/bin/env python3
"""
YGGDRASIL — SCAN NAVIER-STOKES
════════════════════════════════════════════════
Mapper structurel : Navier-Stokes × 7 continents scientifiques.
Trouve les TROUS STRUCTURELS (Pattern 4 OPEN HOLE).

P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|

Inputs:
  - experiments/predictions_2025/snapshot_full.npz  (CSR 65K×65K)
  - experiments/predictions_2025/activity_full.json
  - experiments/predictions_2025/species_full.json
  - experiments/predictions_2025/collision_matrix_full.json
  - data/scan/concepts_65k.json

Outputs:
  - data/results/scan_navier_stokes.json

Sky × Claude — 29 Mars 2026
"""

import json
import os
import sys
import time
import gc
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
PRED_DIR = os.path.join(REPO, "experiments", "predictions_2025")
N_CONCEPTS = 65026

# ══════════════════════════════════════════════
# NAVIER-STOKES CORE (indices in 65K matrix)
# ══════════════════════════════════════════════
NS_CORE = {
    # === The equation itself ===
    "Navier–Stokes equations":              43017,
    "Reynolds-averaged Navier–Stokes eq.":  53587,
    "Hagen–Poiseuille flow (NS)":           59890,
    "Non-dim. & scaling of NS":             63289,
    # === Fluid dynamics core ===
    "Fluid dynamics":                       63508,
    "Fluid mechanics":                      55268,
    "Computational fluid dynamics":          9884,
    "Incompressible flow":                  56500,
    "Compressible flow":                    56999,
    # === Key operators & quantities ===
    "Turbulence":                           15100,
    "Reynolds number":                      12926,
    "Viscosity":                             4289,
    "Vorticity":                            15635,
    "Vortex":                                6414,
    "Boundary layer":                        1884,
    "Pressure gradient":                    64747,
    "Dissipation":                           5522,
    "Enstrophy":                            12351,
    "Helicity":                             18154,
    # === Math backbone ===
    "Partial differential equation":        64038,
    "Sobolev space":                        64985,
    "Weak solution":                        55591,
    "Euler equations":                      54512,
    "Heat equation":                        16064,
    "Diffusion equation":                   58421,
    "Existence theorem":                    21302,
}
NS_IDXS = set(NS_CORE.values())

# ══════════════════════════════════════════════
# 7 CONTINENTS — domain concept groups for Q1-Q5
# ══════════════════════════════════════════════
CONTINENTS = {
    "Math Pures": {
        64038,  # Partial differential equation
        64985,  # Sobolev space
        55591,  # Weak solution
        54512,  # Euler equations
        16064,  # Heat equation
        58421,  # Diffusion equation
        21302,  # Existence theorem
        13544,  # Parabolic partial differential equation
        62659,  # Stochastic partial differential equation
        1886,   # Hyperbolic partial differential equation
        57646,  # Elliptic partial differential equation
        13328,  # Sobolev inequality
        10292,  # Sobolev spaces for planar domains
        290,    # Separable partial differential equation
        1432,   # Dispersive partial differential equation
        63282,  # Viscosity solution
        16148,  # p-Laplacian
        18386,  # Fractional Laplacian
        2429,   # Laplacian matrix
        9401,   # Divergence theorem
        55577,  # Peano existence theorem
        17884,  # Yang–Mills existence and mass gap
    },
    "Physique Fluides": {
        15100,  # Turbulence
        12926,  # Reynolds number
        4289,   # Viscosity
        63508,  # Fluid dynamics
        55268,  # Fluid mechanics
        56500,  # Incompressible flow
        56999,  # Compressible flow
        15635,  # Vorticity
        6414,   # Vortex
        1884,   # Boundary layer
        64747,  # Pressure gradient
        5522,   # Dissipation
        18154,  # Helicity
        12351,  # Enstrophy
        43017,  # Navier–Stokes equations
        53587,  # RANS
        7371,   # Reynolds stress
        8542,   # Turbulence kinetic energy
        16343,  # Turbulence modeling
        7913,   # K-epsilon turbulence model
        13928,  # K-omega turbulence model
        33784,  # Homogeneous isotropic turbulence
        63676,  # Vortex stretching
        9686,   # Vorticity equation
        8946,   # Reynolds equation
        14353,  # Stokes flow
        33199,  # Fluid–structure interaction
        47150,  # Newtonian fluid
        62622,  # Non-Newtonian fluid
        59449,  # Reynolds decomposition
    },
    "Electrotechnique": {
        12246,  # Electrical impedance
        59034,  # Impedance matching
        2837,   # Joule heating
        6022,   # Ohmic contact
        10380,  # Ohm's law
        53525,  # Ohm
        60223,  # Joule–Thomson effect
        1111,   # Joule effect
        13558,  # Kirchhoff's diffraction formula
        63544,  # Kirchhoff integral theorem
        11274,  # Focused Impedance Measurement
        53823,  # Bioelectrical impedance analysis
        17764,  # Input impedance
        58578,  # Output impedance
        11607,  # High impedance
        2248,   # Impedance parameters
        9271,   # Mechanical impedance
        27850,  # Impedance control
        8609,   # Electrical impedance tomography
        11364,  # Characteristic impedance
        64856,  # Acoustic impedance
        60013,  # Wave impedance
        61545,  # Negative impedance converter
        64589,  # Dissipation factor
        8596,   # Image impedance
        63874,  # Impedance bridging
        59058,  # Quarter-wave impedance transformer
        63847,  # Transimpedance amplifier
        31541,  # Radiation impedance
        14343,  # Electrical impedance myography
        18683,  # Impedance cardiography
    },
    "IA / Numerique": {
        9884,   # Computational fluid dynamics
        56582,  # Artificial neural network
        62166,  # Convolutional neural network
        5562,   # Finite element method
        16545,  # Finite difference method
        56527,  # Finite volume method
        47610,  # Deep neural networks
        7367,   # Recurrent neural network
        47142,  # Residual neural network
        56010,  # Feedforward neural network
        37228,  # Hybrid neural network
        2752,   # Spiking neural network
        62148,  # Cellular neural network
        5355,   # Probabilistic neural network
        53807,  # Physical neural network
        53671,  # Random neural network
        42317,  # Modular neural network
        12719,  # Finite difference
        6963,   # Mixed finite element method
        17556,  # Extended finite element method
        48372,  # Finite difference scheme
        4296,   # Volume of fluid method
        64690,  # Numerical partial differential equations
        256,    # Numerical solution of convection–diffusion equation
    },
    "Finance / Stochastique": {
        62362,  # Stochastic process
        4325,   # Stochastic modelling
        57012,  # Stochastic differential equation
        5921,   # Stochastic programming
        14756,  # Stochastic optimization
        2009,   # Brownian motion
        1444,   # Fractional Brownian motion
        311,    # Geometric Brownian motion
        4802,   # Brownian dynamics
        62785,  # Stochastic volatility
        10968,  # Stochastic control
        59357,  # Stochastic calculus
        48142,  # Stochastic integral
        56210,  # Dynamic stochastic general equilibrium
        34211,  # Stochastic frontier analysis
        53698,  # Stochastic discount factor
        9130,   # Continuous-time stochastic process
        47473,  # Stochastic dynamics
        53711,  # Stochastic dominance
        806,    # Finite difference methods for option pricing
        56303,  # Stochastic matrix
    },
    "Bio / Hemodynamique": {
        12336,  # Hemodynamics
        9182,   # Blood flow
        15769,  # Rheology
        9011,   # Cerebral blood flow
        6631,   # Renal blood flow
        50778,  # Blood viscosity
        61728,  # Hemorheology
        53866,  # Microrheology
        52879,  # Blood flow restriction
        53823,  # Bioelectrical impedance analysis
        18683,  # Impedance cardiography
    },
    "Chimie / Rheologie": {
        15769,  # Rheology
        47150,  # Newtonian fluid
        62622,  # Non-Newtonian fluid
        9309,   # Apparent viscosity
        17780,  # Intrinsic viscosity
        10915,  # Relative viscosity
        49926,  # Shear viscosity
        3982,   # Inherent viscosity
        36094,  # Extensional viscosity
        44192,  # Hyperviscosity
        452,    # Carreau fluid
        14250,  # Herschel–Bulkley fluid
        56811,  # Generalized Newtonian fluid
        56003,  # Power-law fluid
        29671,  # Magnetorheological elastomer
        42602,  # Magnetorheological damper
        1400,   # Magnetorheological fluid
        9648,   # Electrorheological fluid
        53866,  # Microrheology
    },
}

# All continent concept indices (flat set)
ALL_CONTINENT_IDXS = set()
for v in CONTINENTS.values():
    ALL_CONTINENT_IDXS |= v

# Concept >> continent(s) mapping
IDX_TO_CONTINENTS = {}
for cname, cidxs in CONTINENTS.items():
    for idx in cidxs:
        IDX_TO_CONTINENTS.setdefault(idx, []).append(cname)


def extract_ns_pairs():
    """Extract all co-occurrence pairs touching NS_CORE from WT3 SQLite (cooc_global).
    69M rows total — we query only rows where concept_a or concept_b is in NS_IDXS.
    """
    import sqlite3
    print("[1] Extracting Navier-Stokes pairs from WT3 (cooc_global)...")
    t0 = time.time()

    db_path = os.path.join(REPO, "data", "wt3.db")
    conn = sqlite3.connect(db_path)

    ns_list = sorted(NS_IDXS)
    placeholders = ",".join(str(x) for x in ns_list)

    query = f"""
        SELECT concept_a, concept_b, weight
        FROM cooc_global
        WHERE concept_a IN ({placeholders})
           OR concept_b IN ({placeholders})
    """
    print(f"  Querying {len(ns_list)} NS core indices against 69M rows...")

    pairs = {}
    row_count = 0
    cursor = conn.execute(query)
    while True:
        batch = cursor.fetchmany(100_000)
        if not batch:
            break
        for a, b, w in batch:
            pair = (min(a, b), max(a, b))
            if pair not in pairs:
                pairs[pair] = float(w)
            row_count += len(batch)

    conn.close()
    print(f"  Unique pairs: {len(pairs):,}")
    print(f"  Done in {time.time()-t0:.1f}s")
    return pairs


def main():
    t0 = time.time()
    print("=" * 90)
    print("SCAN NAVIER-STOKES — 65K concepts, P4 Uzzi z-scores, 7 continents")
    print("=" * 90)

    # === 1. Extract co-occurrence ===
    cooc = extract_ns_pairs()

    # === 2. Load activity ===
    print("\n[2] Loading activity...")
    with open(os.path.join(PRED_DIR, "activity_full.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)
    total_works_sum = float(activity.sum())
    del act_data; gc.collect()
    print(f"  total_works_sum = {total_works_sum:,.0f}")

    # === 3. Load concepts + species ===
    print("\n[3] Loading concepts + species...")
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        concepts_data = json.load(f)
    idx_to_name = {}
    idx_to_level = {}
    url_to_idx = {}
    for url, info in concepts_data["concepts"].items():
        idx_to_name[info["idx"]] = info["name"]
        idx_to_level[info["idx"]] = info.get("level", -1)
        url_to_idx[url] = info["idx"]

    with open(os.path.join(PRED_DIR, "species_full.json"), 'r', encoding='utf-8') as f:
        species_data = json.load(f)
    with open(os.path.join(PRED_DIR, "collision_matrix_full.json"), 'r', encoding='utf-8') as f:
        collision_data = json.load(f)
    species_names = collision_data["meta"]["species_names"]
    del collision_data
    species_map = {}
    for url, info in species_data["concepts"].items():
        if url in url_to_idx:
            species_map[url_to_idx[url]] = info["species"]
    del species_data, concepts_data, url_to_idx; gc.collect()

    # === 4. Compute P4 ===
    print("\n[4] Computing P4 Uzzi z-scores...")
    active_mask = activity > 0
    act_min = activity[active_mask].min()
    act_max = activity[active_mask].max()
    cooc_values = list(cooc.values())
    cooc_max = max(cooc_values) if cooc_values else 1.0

    results = []
    for (idx_a, idx_b), observed in cooc.items():
        wa, wb = activity[idx_a], activity[idx_b]
        if wa == 0 or wb == 0:
            continue

        # Uzzi z-score
        E = wa * wb / total_works_sum
        pa, pb = wa / total_works_sum, wb / total_works_sum
        std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
        z = (observed - E) / std

        # Normalize activity
        an = max(min((wa - act_min) / (act_max - act_min), 1.0), 0.0)
        bn = max(min((wb - act_min) / (act_max - act_min), 1.0), 0.0)

        # Gap + P4
        gap = 1.0 - observed / cooc_max
        p4 = an * bn * gap * abs(z)

        # Identify NS side
        if idx_a in NS_IDXS:
            ns_idx, other_idx = idx_a, idx_b
        else:
            ns_idx, other_idx = idx_b, idx_a

        ns_sp = species_map.get(ns_idx, -1)
        other_sp = species_map.get(other_idx, -1)
        other_lvl = idx_to_level.get(other_idx, -1)

        if other_lvl < 3:
            continue

        results.append({
            "ns_name": idx_to_name.get(ns_idx, f"?{ns_idx}"),
            "ns_idx": ns_idx,
            "other_name": idx_to_name.get(other_idx, f"?{other_idx}"),
            "other_idx": other_idx,
            "other_level": other_lvl,
            "cooc": observed,
            "z": z,
            "p4": p4,
            "ns_sp": ns_sp,
            "other_sp": other_sp,
            "ns_sp_name": species_names.get(str(ns_sp), "?"),
            "other_sp_name": species_names.get(str(other_sp), "?"),
            "cross": ns_sp != other_sp and ns_sp >= 0 and other_sp >= 0,
            "known": other_idx in NS_IDXS,
            "continent": IDX_TO_CONTINENTS.get(other_idx, []),
        })

    results.sort(key=lambda x: x["p4"], reverse=True)
    print(f"  {len(results):,} pairs scored")

    # === 5. DOMAIN × DOMAIN CO-OCCURRENCE MATRIX ===
    print("\n[5] Building domain × domain co-occurrence matrix...")
    cont_names = list(CONTINENTS.keys())
    n_cont = len(cont_names)
    domain_matrix = np.zeros((n_cont, n_cont), dtype=np.float64)
    domain_pairs_count = np.zeros((n_cont, n_cont), dtype=np.int64)

    for (idx_a, idx_b), observed in cooc.items():
        ca = IDX_TO_CONTINENTS.get(idx_a, [])
        cb = IDX_TO_CONTINENTS.get(idx_b, [])
        for da in ca:
            for db in cb:
                i, j = cont_names.index(da), cont_names.index(db)
                domain_matrix[i][j] += observed
                domain_matrix[j][i] += observed
                domain_pairs_count[i][j] += 1
                domain_pairs_count[j][i] += 1

    print(f"\n  {'':25s}", end="")
    for cn in cont_names:
        print(f" {cn[:10]:>10s}", end="")
    print()
    for i, cn in enumerate(cont_names):
        print(f"  {cn:25s}", end="")
        for j in range(n_cont):
            v = domain_matrix[i][j]
            if v > 0:
                print(f" {v:10.0f}", end="")
            else:
                print(f" {'---':>10s}", end="")
        print()

    # === 6. Q1-Q5 SPECIFIC CHECKS ===
    print(f"\n{'='*90}")
    print("Q1-Q5 — SPECIFIC STRUCTURAL HOLE CHECKS")
    print(f"{'='*90}")

    # Helper: total cooc between two domain groups
    def cross_cooc(d1, d2):
        total = 0.0
        count = 0
        for (a, b), v in cooc.items():
            if (a in CONTINENTS.get(d1, set()) and b in CONTINENTS.get(d2, set())) or \
               (b in CONTINENTS.get(d1, set()) and a in CONTINENTS.get(d2, set())):
                total += v
                count += 1
        return total, count

    # Q1: Electrotechnique × Physique Fluides
    q1_total, q1_count = cross_cooc("Electrotechnique", "Physique Fluides")
    phys_total = sum(v for (a, b), v in cooc.items()
                     if a in CONTINENTS["Physique Fluides"] or b in CONTINENTS["Physique Fluides"])
    q1_pct = (q1_total / phys_total * 100) if phys_total > 0 else 0
    print(f"\n  Q1 — TROU ELECTRIQUE")
    print(f"  Electrotechnique × Physique Fluides: {q1_total:,.0f} cooc, {q1_count} paires")
    print(f"  % du total Physique Fluides: {q1_pct:.2f}%")
    print(f"  >> {'TROU CONFIRME' if q1_pct < 5 else 'Connexion existe'}")

    # Q2: Dissipation/Thermo × Math Pures (regularity)
    q2_total, q2_count = cross_cooc("Electrotechnique", "Math Pures")
    print(f"\n  Q2 — TROU THERMIQUE")
    print(f"  Electrotechnique (Joule/dissipation) × Math Pures: {q2_total:,.0f} cooc, {q2_count} paires")

    # Q3: Finance/Stochastique × Physique Fluides
    q3_total, q3_count = cross_cooc("Finance / Stochastique", "Physique Fluides")
    print(f"\n  Q3 — TROU STOCHASTIQUE")
    print(f"  Finance/Stochastique × Physique Fluides: {q3_total:,.0f} cooc, {q3_count} paires")

    # Q4: Bio/Hemodynamique × Math Pures
    q4_total, q4_count = cross_cooc("Bio / Hemodynamique", "Math Pures")
    print(f"\n  Q4 — TROU BIOLOGIQUE")
    print(f"  Bio/Hemodynamique × Math Pures: {q4_total:,.0f} cooc, {q4_count} paires")

    # Q5: IA/Numerique × Math Pures (proof-level)
    q5_total, q5_count = cross_cooc("IA / Numerique", "Math Pures")
    print(f"\n  Q5 — TROU MACHINE LEARNING")
    print(f"  IA/Numerique × Math Pures: {q5_total:,.0f} cooc, {q5_count} paires")

    # === 7. Display top results ===
    cross_unknown = [r for r in results if r["cross"] and not r["known"]]
    holes = sorted([r for r in cross_unknown if r["z"] < 0], key=lambda x: x["z"])

    print(f"\n{'='*100}")
    print(f"TOP 100 P4 — CROSS-SPECIES, OUTSIDE NS CORE")
    print(f"= Bridges between Navier-Stokes and OTHER scientific continents =")
    print(f"{'='*100}")
    for i, r in enumerate(cross_unknown[:100]):
        zs = "+" if r["z"] > 0 else ""
        cont = ",".join(r["continent"][:2]) if r["continent"] else ""
        print(f"  {i+1:3d}. P4={r['p4']:8.4f} | z={zs}{r['z']:8.1f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['ns_name'][:22]:22s} × {r['other_name'][:30]:30s}"
              f" | [{r['ns_sp_name'][:10]}×{r['other_sp_name'][:10]}]"
              f" {cont}")

    print(f"\n{'='*100}")
    print(f"TOP 50 STRUCTURAL HOLES (z < 0, cross-species)")
    print(f"= FEWER co-occurrences than expected >> REAL gaps >> angles d'attaque =")
    print(f"{'='*100}")
    for i, r in enumerate(holes[:50]):
        cont = ",".join(r["continent"][:2]) if r["continent"] else ""
        print(f"  {i+1:3d}. z={r['z']:9.1f} | P4={r['p4']:.4f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['ns_name'][:22]:22s} × {r['other_name'][:30]:30s}"
              f" | [{r['ns_sp_name'][:10]}×{r['other_sp_name'][:10]}]"
              f" {cont}")

    # === 8. Species distribution ===
    print(f"\n{'='*100}")
    print("SPECIES DISTRIBUTION (top 200 cross-species pairs)")
    print(f"{'='*100}")
    sp_counts = {}
    for r in cross_unknown[:200]:
        sp = r["other_sp_name"]
        if sp not in sp_counts:
            sp_counts[sp] = {"count": 0, "p4_sum": 0.0, "holes": 0}
        sp_counts[sp]["count"] += 1
        sp_counts[sp]["p4_sum"] += r["p4"]
        if r["z"] < 0:
            sp_counts[sp]["holes"] += 1
    for sp, v in sorted(sp_counts.items(), key=lambda x: -x[1]["p4_sum"]):
        print(f"  {sp:35s} | {v['count']:3d} pairs | {v['holes']:2d} holes | P4={v['p4_sum']:.2f}")

    # === 9. Summary ===
    print(f"\n{'='*100}")
    print("SUMMARY")
    print(f"{'='*100}")
    print(f"  Total pairs: {len(results):,}")
    print(f"  Cross-species (outside core): {len(cross_unknown):,}")
    print(f"  Structural holes (z<0, cross): {len(holes):,}")
    print(f"  Total time: {time.time()-t0:.0f}s")

    # === 10. Save ===
    outfile = os.path.join(REPO, "data", "results", "scan_navier_stokes.json")
    os.makedirs(os.path.dirname(outfile), exist_ok=True)

    # Domain matrix as serializable dict
    dm = {}
    for i, ci in enumerate(cont_names):
        for j, cj in enumerate(cont_names):
            if domain_matrix[i][j] > 0:
                key = f"{ci} × {cj}"
                dm[key] = {"cooc": float(domain_matrix[i][j]),
                           "pairs": int(domain_pairs_count[i][j])}

    summary = {
        "scan": "navier_stokes",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_pairs_total": len(results),
        "n_cross_unknown": len(cross_unknown),
        "n_holes": len(holes),
        "ns_core_concepts": list(NS_CORE.keys()),
        "questions": {
            "Q1_electrique": {"cooc": q1_total, "pairs": q1_count, "pct_physique": q1_pct},
            "Q2_thermique": {"cooc": q2_total, "pairs": q2_count},
            "Q3_stochastique": {"cooc": q3_total, "pairs": q3_count},
            "Q4_biologique": {"cooc": q4_total, "pairs": q4_count},
            "Q5_ml": {"cooc": q5_total, "pairs": q5_count},
        },
        "domain_matrix": dm,
        "top_100_cross": [{k: v for k, v in r.items()} for r in cross_unknown[:100]],
        "top_50_holes": [{k: v for k, v in r.items()} for r in holes[:50]],
        "species_distribution": sp_counts,
    }
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")


if __name__ == "__main__":
    main()
