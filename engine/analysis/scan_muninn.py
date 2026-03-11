#!/usr/bin/env python3
"""
YGGDRASIL — SCAN MUNINN
════════════════════════════════════════════════
Extrait les rangées des concepts Muninn depuis snapshot_full.npz
Même approche que scan_philippe_v2.py.

P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|

Sky × Claude — 10 Mars 2026, Versoix
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
# MUNINN'S CORE FORMULAS (indices in 65K matrix)
# ══════════════════════════════════════════════
# F1  Ebbinghaus: 2^(-delta/h), adaptive half-life
# F7  NCD: (C(a+b)-min(C(a),C(b)))/max(C(a),C(b))
# F8  TF-IDF + Cosine similarity
# F11 Novelty scoring (Predictive coding, Rao & Ballard 1999)
# F13 Boot scoring (Park et al. 2023, Generative Agents)
# F19 Exponential Moving Average (usefulness feedback)
# F28 Bit-shift decay (co-occurrence halving, t½=30 days)
# F29 Zone-IDF: count × log(1 + N_zones/k_zones)
# F31 Spreading activation (Collins & Loftus 1975)
# F32 Fusion threshold (co-occurrence count >= 5)
# F38 Normalized Laplacian + Spectral clustering

MUNINN_CORE = {
    # === Direct formula matches ===
    "Exponential decay":              12550,  # F1, F28
    "Half-life":                      54681,  # F1, F28
    "Information theory":             57221,  # F7 NCD backbone
    "Data compression":               61733,  # F7 NCD
    "Kolmogorov complexity":          34208,  # F7 NCD theoretical basis
    "Exponential smoothing":           5237,  # F19 EMA
    "Moving average":                 11819,  # F19 EMA
    "Laplacian matrix":                2429,  # F38 spectral
    "Eigenvalues and eigenvectors":    9157,  # F38 spectral
    "Spectral clustering":              934,  # F38 spectral
    "Semantic network":               62789,  # F31 spreading activation
    "Co-occurrence":                   8467,  # F32 fusion / mycélium
    "Cosine similarity":              40678,  # F8 TF-IDF
    "Predictive coding":              28203,  # F11 novelty
    "Novelty detection":              32258,  # F11 novelty
    "Forgetting":                     60649,  # F1 Ebbinghaus
    # === Structural math tools ===
    "Exponential function":            8014,  # 2^x structure
    "Logarithm":                      54757,  # log in IDF
    "Graph theory":                   63207,  # mycélium backbone
    "Random walk":                     3378,  # spreading activation related
    "Markov chain":                   64837,  # memory state transitions
}
MUNINN_IDXS = set(MUNINN_CORE.values())

# Muninn's extended neighborhood (concepts it already "knows" — skip these)
ALL_KNOWN = MUNINN_IDXS | {
    332,     # Conditional entropy
    16972,   # Collocation method
    2484,    # Cache
    3162,    # Machine learning
    1389,    # Deep learning
    449,     # Fourier transform
    715,     # Signal processing
    9389,    # Bayesian inference
    2752,    # Spiking neural network
}


def extract_muninn_pairs():
    """Two-phase extraction from CSR matrix (upper triangular).
    Same approach as scan_philippe_v2.py.
    """
    print("[1] Extracting Muninn's pairs from snapshot_full.npz...")
    t0 = time.time()

    npz_path = os.path.join(PRED_DIR, "snapshot_full.npz")

    # ── PHASE 1: Load indptr + indices ──
    print("  Phase 1: Loading indptr + indices (~413 MB)...")
    npz = np.load(npz_path, allow_pickle=False)
    indptr = npz['indptr'].copy()
    all_indices = npz['indices']
    npz.close()

    core_idxs = sorted(MUNINN_IDXS)

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
    print("=" * 95)
    print("SCAN MUNINN — 65K concepts, P4 Uzzi z-scores")
    print("Hunting cross-domain structural analogs for Muninn's 42 formulas")
    print("=" * 95)

    # === 1. Extract co-occurrence ===
    cooc = extract_muninn_pairs()

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

        if idx_a in MUNINN_IDXS:
            mun_idx, other_idx = idx_a, idx_b
        else:
            mun_idx, other_idx = idx_b, idx_a

        mun_sp = species_map.get(mun_idx, -1)
        other_sp = species_map.get(other_idx, -1)
        other_lvl = idx_to_level.get(other_idx, -1)

        # Skip level 0-1 (too generic)
        if other_lvl < 2:
            continue

        results.append({
            "mun_name": idx_to_name.get(mun_idx, f"?{mun_idx}"),
            "mun_idx": mun_idx,
            "other_name": idx_to_name.get(other_idx, f"?{other_idx}"),
            "other_idx": other_idx,
            "other_level": other_lvl,
            "cooc": observed,
            "z": z,
            "p4": p4,
            "mun_sp": mun_sp,
            "other_sp": other_sp,
            "mun_sp_name": species_names.get(str(mun_sp), "?"),
            "other_sp_name": species_names.get(str(other_sp), "?"),
            "cross": mun_sp != other_sp and mun_sp >= 0 and other_sp >= 0,
            "known": other_idx in ALL_KNOWN,
        })

    results.sort(key=lambda x: x["p4"], reverse=True)
    print(f"  {len(results):,} pairs scored")

    # === 5. Display ===
    cross_unknown = [r for r in results if r["cross"] and not r["known"]]
    intra_unknown = [r for r in results if not r["cross"] and not r["known"]]
    holes = sorted([r for r in cross_unknown if r["z"] < 0], key=lambda x: x["z"])

    print(f"\n{'='*95}")
    print(f"TOP 100 P4 — CROSS-SPECIES, UNKNOWN TO MUNINN")
    print(f"= Bridges between Muninn's math and OTHER scientific continents =")
    print(f"{'='*95}")
    for i, r in enumerate(cross_unknown[:100]):
        zs = "+" if r["z"] > 0 else ""
        print(f"  {i+1:3d}. P4={r['p4']:8.4f} | z={zs}{r['z']:8.1f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['mun_name'][:25]:25s} × {r['other_name'][:35]}"
              f" | [{r['mun_sp_name'][:12]}×{r['other_sp_name'][:12]}]")

    print(f"\n{'='*95}")
    print(f"TOP 50 STRUCTURAL HOLES (z < 0, cross-species, unknown)")
    print(f"= Fewer co-occurrences than expected → REAL holes → Muninn formula analogs hiding here =")
    print(f"{'='*95}")
    for i, r in enumerate(holes[:50]):
        print(f"  {i+1:3d}. z={r['z']:9.1f} | P4={r['p4']:.4f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['mun_name'][:25]:25s} × {r['other_name'][:35]}"
              f" | [{r['mun_sp_name'][:12]}×{r['other_sp_name'][:12]}]")

    print(f"\n{'='*95}")
    print(f"TOP 50 INTRA-SPECIES SURPRISES (same continent, unknown)")
    print(f"{'='*95}")
    for i, r in enumerate(intra_unknown[:50]):
        zs = "+" if r["z"] > 0 else ""
        print(f"  {i+1:3d}. P4={r['p4']:8.4f} | z={zs}{r['z']:8.1f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['mun_name'][:25]:25s} × {r['other_name'][:35]}"
              f" | [{r['other_sp_name']}]")

    # === 6. Summary ===
    print(f"\n{'='*95}")
    print("SUMMARY")
    print(f"{'='*95}")
    print(f"  Total pairs: {len(results):,}")
    print(f"  Cross-species unknown: {len(cross_unknown):,}")
    print(f"  Structural holes (z<0, cross): {len(holes):,}")
    print(f"  Intra-species unknown: {len(intra_unknown):,}")

    print(f"\n  TOP 10 other-species by P4 sum (top 200):")
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
        print(f"    {sp:35s} | {v['count']:3d} pairs | {v['holes']:2d} holes | P4={v['p4_sum']:.2f}")

    # === 7. Muninn-specific: Group by formula family ===
    print(f"\n{'='*95}")
    print("RESULTS BY MUNINN FORMULA FAMILY")
    print(f"{'='*95}")

    formula_families = {
        "F1/F28 Ebbinghaus+Decay": {12550, 54681, 60649, 8014},
        "F7 NCD/Compression": {57221, 61733, 34208},
        "F8/F29 TF-IDF+IDF": {40678, 54757},
        "F11 Predictive Coding": {28203, 32258},
        "F19 EMA": {5237, 11819},
        "F31 Spreading Activation": {62789, 3378, 63207},
        "F38 Spectral/Laplacian": {934, 2429, 9157, 64837},
        "F32 Co-occurrence/Fusion": {8467},
    }

    for family_name, family_idxs in formula_families.items():
        family_results = [r for r in cross_unknown if r["mun_idx"] in family_idxs]
        if not family_results:
            continue
        print(f"\n  --- {family_name} ({len(family_results)} cross-species matches) ---")
        for i, r in enumerate(family_results[:15]):
            zs = "+" if r["z"] > 0 else ""
            tag = "HOLE" if r["z"] < 0 else "P4  "
            print(f"    {i+1:2d}. {tag} P4={r['p4']:.4f} z={zs}{r['z']:.1f}"
                  f" | {r['mun_name'][:20]:20s} × {r['other_name'][:30]}"
                  f" | [{r['other_sp_name'][:15]}]")

    # === 8. Save ===
    os.makedirs(os.path.join(REPO, "data", "results"), exist_ok=True)
    outfile = os.path.join(REPO, "data", "results", "scan_muninn.json")
    summary = {
        "scan": "muninn_formulas_v2",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_pairs_total": len(results),
        "n_cross_unknown": len(cross_unknown),
        "n_holes": len(holes),
        "muninn_concepts": list(MUNINN_CORE.keys()),
        "all_cross_unknown": cross_unknown[:500],   # top 500 cross-species
        "top_100_holes": holes[:100],
        "top_50_intra": intra_unknown[:50],
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
