#!/usr/bin/env python3
"""
YGGDRASIL — SCAN GOD'S NUMBER (pour Muninn)
════════════════════════════════════════════════
Extrait les rangées des concepts liés à:
- Cayley graph diameter / God's Number
- Rubik / permutation puzzles
- Constraint intersection method (le "cannon")
- Cross-domain bridges (knots, codes, Waring, genome, etc.)

Même moteur que scan_philippe_v2.py / scan_muninn.py.
P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|

Sky × Claude — 14 Mars 2026, Versoix
Requête: Muninn b42 — God's Number, Constraint Cannons, Cayley Graph Diameter
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
# GOD'S NUMBER — CORE CONCEPTS (indices in 65K matrix)
# ══════════════════════════════════════════════
# AXE 1: Cayley graph diameter / permutation groups
# AXE 2: Spectral theory / expansion
# AXE 3: Isomorphic problems (knots, codes, genomes, puzzles)
# AXE 4: Constraint methods (CSP, intervals, inverse problems)

GN_CORE = {
    # === AXE 1: Cayley graph + permutation groups ===
    "Cayley graph":                     3217,   # THE central concept
    "Wreath product":                  64319,   # Z_k wr S_n = Rubik structure
    "Permutation group":               63903,   # G <= S_n
    "Symmetric group":                  4492,   # S_n
    "Semidirect product":              61178,   # N ⋊ H
    "Simple group":                    57573,   # Babai conjecture target
    "Classification of finite simple groups": 59370,
    "Normal subgroup":                   917,   # group structure
    "Nilpotent group":                 16592,   # subgroup structure
    "Coset":                           62772,   # Kociemba two-phase
    "Commutator subgroup":              6423,   # commutator width ~ diameter
    "Group theory":                    62210,   # umbrella
    # === AXE 2: Spectral theory / expansion ===
    "Spectral gap":                    28454,   # λ₂ → diameter
    "Expander graph":                   8508,   # Cayley + expansion
    "Markov chain mixing time":        64555,   # mixing ~ diameter
    "Eigenvalues and eigenvectors":     9157,   # spectral methods
    "Laplacian matrix":                 2429,   # graph Laplacian
    "Random walk":                      3378,   # on Cayley graph
    # === AXE 3: Isomorphic problems / bridges ===
    "Knot theory":                      6795,   # unknotting number ~ GN
    "Unknot":                          38541,   # unknotting number
    "Coding theory":                    2234,   # covering radius ~ GN
    "Sphere packing":                  13095,   # codes + packing
    "Sorting network":                 59567,   # permutation sorting
    "Quantum walk":                     6307,   # quantum Cayley walk
    "Percolation theory":               2489,   # bootstrap percolation
    "Combinatorial optimization":      57247,   # diameter as optimization
    # === AXE 4: Constraint methods / cannon ===
    "Constraint satisfaction problem":  15562,   # CSP
    "PSPACE":                          15276,   # hardness of diameter
    "Inverse problem":                  5503,   # discrete inverse problem
    "Interval arithmetic":             14255,   # interval propagation
    "Sensitivity analysis":            11886,   # sensitivity to removing constraint
    "Phase transition":                 7678,   # CSP threshold
}
GN_IDXS = set(GN_CORE.values())

# Extended "known" (concepts that are obvious neighbors — skip for novelty)
ALL_KNOWN = GN_IDXS | {
    128622974 % N_CONCEPTS,  # placeholder for overlaps
}


def extract_gn_pairs():
    """Two-phase extraction from CSR matrix (upper triangular).
    Same approach as scan_philippe_v2.py.
    """
    print("[1] Extracting God's Number pairs from snapshot_full.npz...")
    t0 = time.time()

    npz_path = os.path.join(PRED_DIR, "snapshot_full.npz")

    # ── PHASE 1: Load indptr + indices ──
    print("  Phase 1: Loading indptr + indices (~413 MB)...")
    npz = np.load(npz_path, allow_pickle=False)
    indptr = npz['indptr'].copy()
    all_indices = npz['indices']
    npz.close()

    core_idxs = sorted(GN_IDXS)

    all_positions = []
    all_meta = []

    # A) Row scan
    row_count = 0
    for pi in core_idxs:
        start, end = int(indptr[pi]), int(indptr[pi + 1])
        if end <= start:
            continue
        cols = all_indices[start:end]
        for j, c in enumerate(cols):
            c = int(c)
            if c != pi:
                all_positions.append(start + j)
                all_meta.append((pi, c))
                row_count += 1

    # B) Column scan
    print(f"  Column scan ({len(core_idxs)} passes)...")
    mask = np.zeros(len(all_indices), dtype=np.bool_)
    for pi in core_idxs:
        mask |= (all_indices == pi)
    hit_flat = np.where(mask)[0]
    hit_cols = all_indices[hit_flat].copy()
    del mask; gc.collect()

    hit_rows = np.searchsorted(indptr, hit_flat, side='right') - 1

    col_count = 0
    for i in range(len(hit_flat)):
        r, c = int(hit_rows[i]), int(hit_cols[i])
        if r != c:
            all_positions.append(int(hit_flat[i]))
            all_meta.append((r, c))
            col_count += 1

    del all_indices, hit_flat, hit_cols, hit_rows
    gc.collect()

    print(f"  Row pairs: {row_count:,}, Column pairs: {col_count:,}")
    print(f"  Total positions to extract: {len(all_positions):,}")

    # ── PHASE 2: Extract data via mmap ──
    print("  Phase 2: Extracting data.npy to disk for mmap access...")
    import zipfile, tempfile, shutil
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(npz_path) as zf:
            zf.extract('data.npy', tmpdir)
        data_path = os.path.join(tmpdir, 'data.npy')
        data = np.load(data_path, mmap_mode='r')
        positions_arr = np.array(all_positions, dtype=np.int64)
        del all_positions; gc.collect()
        values = data[positions_arr].copy()
        del data, positions_arr; gc.collect()
        print(f"  Got {len(values):,} values via mmap")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    pairs = {}
    for i, (r, c) in enumerate(all_meta):
        pair = (min(r, c), max(r, c))
        if pair not in pairs:
            pairs[pair] = float(values[i])

    del values, all_meta
    gc.collect()

    print(f"  Unique pairs: {len(pairs):,}")
    print(f"  Done in {time.time()-t0:.1f}s")
    return pairs


def main():
    t0 = time.time()
    print("=" * 100)
    print("SCAN GOD'S NUMBER — 65K concepts, P4 Uzzi z-scores")
    print("Hunting: Cayley diameter, spectral gap, wreath products, constraint cannons,")
    print("         knot theory bridges, covering radius, genome rearrangement analogs")
    print("=" * 100)

    # === 1. Extract co-occurrence ===
    cooc = extract_gn_pairs()

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

        E = wa * wb / total_works_sum
        pa, pb = wa / total_works_sum, wb / total_works_sum
        std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
        z = (observed - E) / std

        an = max(min((wa - act_min) / (act_max - act_min), 1.0), 0.0)
        bn = max(min((wb - act_min) / (act_max - act_min), 1.0), 0.0)

        gap = 1.0 - observed / cooc_max
        p4 = an * bn * gap * abs(z)

        if idx_a in GN_IDXS:
            gn_idx, other_idx = idx_a, idx_b
        else:
            gn_idx, other_idx = idx_b, idx_a

        gn_sp = species_map.get(gn_idx, -1)
        other_sp = species_map.get(other_idx, -1)
        other_lvl = idx_to_level.get(other_idx, -1)

        # Skip level 0-1 (too generic)
        if other_lvl < 2:
            continue

        results.append({
            "gn_name": idx_to_name.get(gn_idx, f"?{gn_idx}"),
            "gn_idx": gn_idx,
            "other_name": idx_to_name.get(other_idx, f"?{other_idx}"),
            "other_idx": other_idx,
            "other_level": other_lvl,
            "cooc": observed,
            "z": z,
            "p4": p4,
            "gn_sp": gn_sp,
            "other_sp": other_sp,
            "gn_sp_name": species_names.get(str(gn_sp), "?"),
            "other_sp_name": species_names.get(str(other_sp), "?"),
            "cross": gn_sp != other_sp and gn_sp >= 0 and other_sp >= 0,
            "known": other_idx in ALL_KNOWN,
        })

    results.sort(key=lambda x: x["p4"], reverse=True)
    print(f"  {len(results):,} pairs scored")

    # === 5. Display ===
    cross_unknown = [r for r in results if r["cross"] and not r["known"]]
    intra_unknown = [r for r in results if not r["cross"] and not r["known"]]
    holes = sorted([r for r in cross_unknown if r["z"] < 0], key=lambda x: x["z"])

    print(f"\n{'='*100}")
    print(f"TOP 150 P4 — CROSS-SPECIES, UNKNOWN BRIDGES")
    print(f"= Concepts from OTHER scientific continents that connect to God's Number concepts =")
    print(f"{'='*100}")
    for i, r in enumerate(cross_unknown[:150]):
        zs = "+" if r["z"] > 0 else ""
        print(f"  {i+1:3d}. P4={r['p4']:8.4f} | z={zs}{r['z']:8.1f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['gn_name'][:25]:25s} x {r['other_name'][:35]}"
              f" | [{r['gn_sp_name'][:12]}x{r['other_sp_name'][:12]}]")

    print(f"\n{'='*100}")
    print(f"TOP 100 STRUCTURAL HOLES (z < 0, cross-species)")
    print(f"= Fewer co-occurrences than expected = REAL holes = where hidden bridges live =")
    print(f"{'='*100}")
    for i, r in enumerate(holes[:100]):
        print(f"  {i+1:3d}. z={r['z']:9.1f} | P4={r['p4']:.4f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['gn_name'][:25]:25s} x {r['other_name'][:35]}"
              f" | [{r['gn_sp_name'][:12]}x{r['other_sp_name'][:12]}]")

    print(f"\n{'='*100}")
    print(f"TOP 50 INTRA-SPECIES SURPRISES (same continent, unexpected)")
    print(f"{'='*100}")
    for i, r in enumerate(intra_unknown[:50]):
        zs = "+" if r["z"] > 0 else ""
        print(f"  {i+1:3d}. P4={r['p4']:8.4f} | z={zs}{r['z']:8.1f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['gn_name'][:25]:25s} x {r['other_name'][:35]}"
              f" | [{r['other_sp_name']}]")

    # === 6. By axis ===
    print(f"\n{'='*100}")
    print("RESULTS BY MUNINN QUERY AXIS")
    print(f"{'='*100}")

    axis_map = {
        "AXE 1 — Cayley/Permutation": {3217, 64319, 63903, 4492, 61178, 57573, 59370, 917, 16592, 62772, 6423, 62210},
        "AXE 2 — Spectral/Expansion": {28454, 8508, 64555, 9157, 2429, 3378},
        "AXE 3 — Isomorphic/Bridges": {6795, 38541, 2234, 13095, 59567, 6307, 2489, 57247},
        "AXE 4 — Cannon/Constraints": {15562, 15276, 5503, 14255, 11886, 7678},
    }

    for axis_name, axis_idxs in axis_map.items():
        axis_results = [r for r in cross_unknown if r["gn_idx"] in axis_idxs]
        axis_holes = [r for r in axis_results if r["z"] < 0]
        print(f"\n  --- {axis_name} ({len(axis_results)} cross-species, {len(axis_holes)} holes) ---")
        for i, r in enumerate(axis_results[:20]):
            zs = "+" if r["z"] > 0 else ""
            tag = "HOLE" if r["z"] < 0 else "P4  "
            print(f"    {i+1:2d}. {tag} P4={r['p4']:.4f} z={zs}{r['z']:.1f}"
                  f" | {r['gn_name'][:20]:20s} x {r['other_name'][:35]}"
                  f" | [{r['other_sp_name'][:15]}]")

    # === 7. Internal co-occurrences (between GN core concepts) ===
    print(f"\n{'='*100}")
    print("INTERNAL CO-OCCURRENCES (between God's Number core concepts)")
    print("= Which of Muninn's query concepts co-occur in literature? =")
    print(f"{'='*100}")
    internal = []
    for (idx_a, idx_b), observed in cooc.items():
        if idx_a in GN_IDXS and idx_b in GN_IDXS:
            wa, wb = activity[idx_a], activity[idx_b]
            if wa == 0 or wb == 0:
                continue
            E = wa * wb / total_works_sum
            pa, pb = wa / total_works_sum, wb / total_works_sum
            std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
            z = (observed - E) / std
            internal.append({
                "a": idx_to_name.get(idx_a, f"?{idx_a}"),
                "b": idx_to_name.get(idx_b, f"?{idx_b}"),
                "cooc": observed,
                "z": z,
            })
    internal.sort(key=lambda x: x["cooc"], reverse=True)
    print(f"  {'Concept A':30s} x {'Concept B':30s} | {'cooc':>10s} | {'z':>8s}")
    print(f"  {'-'*30} x {'-'*30} | {'-'*10} | {'-'*8}")
    for r in internal:
        zs = "+" if r["z"] > 0 else ""
        tag = " ***HOLE***" if r["z"] < -2 else (" COLD" if r["cooc"] < 100 else "")
        print(f"  {r['a'][:30]:30s} x {r['b'][:30]:30s} | {r['cooc']:10.1f} | {zs}{r['z']:7.1f}{tag}")

    # === 8. Summary ===
    print(f"\n{'='*100}")
    print("SUMMARY")
    print(f"{'='*100}")
    print(f"  Total pairs: {len(results):,}")
    print(f"  Cross-species unknown: {len(cross_unknown):,}")
    print(f"  Structural holes (z<0, cross): {len(holes):,}")
    print(f"  Intra-species unknown: {len(intra_unknown):,}")
    print(f"  Internal (core x core): {len(internal)}")

    print(f"\n  TOP 15 other-species by P4 sum (top 300):")
    sp_counts = {}
    for r in cross_unknown[:300]:
        sp = r["other_sp_name"]
        if sp not in sp_counts:
            sp_counts[sp] = {"count": 0, "p4_sum": 0.0, "holes": 0}
        sp_counts[sp]["count"] += 1
        sp_counts[sp]["p4_sum"] += r["p4"]
        if r["z"] < 0:
            sp_counts[sp]["holes"] += 1
    for sp, v in sorted(sp_counts.items(), key=lambda x: -x[1]["p4_sum"])[:15]:
        print(f"    {sp:35s} | {v['count']:3d} pairs | {v['holes']:2d} holes | P4={v['p4_sum']:.2f}")

    # === 9. Save ===
    os.makedirs(os.path.join(REPO, "data", "results"), exist_ok=True)
    outfile = os.path.join(REPO, "data", "results", "scan_gods_number.json")
    summary = {
        "scan": "gods_number_v1",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "query": "Muninn b42 — God's Number, Constraint Cannons, Cayley Graph Diameter",
        "n_pairs_total": len(results),
        "n_cross_unknown": len(cross_unknown),
        "n_holes": len(holes),
        "gn_concepts": list(GN_CORE.keys()),
        "all_cross_unknown": cross_unknown[:500],
        "top_100_holes": holes[:100],
        "top_50_intra": intra_unknown[:50],
        "internal_cooc": internal,
        "species_distribution": sp_counts,
        "cooc_max": cooc_max,
        "act_min": float(act_min),
        "act_max": float(act_max),
    }
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")
    print(f"Total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
