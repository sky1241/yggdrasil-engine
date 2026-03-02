#!/usr/bin/env python3
"""
YGGDRASIL — SCAN PHILIPPE V2
════════════════════════════════════════════════
Extrait les rangées de Philippe depuis snapshot_full.npz
(charge seulement indptr + slices ciblés de data/indices).

P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|

Sky × Claude — 1 Mars 2026, Versoix
"""

import json
import os
import sys
import time
import gc
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
PRED_DIR = os.path.join(REPO, "predictions_2025")
N_CONCEPTS = 65026

# ══════════════════════════════════════════════
# PHILIPPE'S CORE TOOLS (indices in 65K matrix)
# ══════════════════════════════════════════════
PHILIPPE_CORE = {
    "H-infinity methods in control theory": 59994,
    "Robust control": 53433,
    "Convex optimization": 9037,
    "Frequency response": 62860,
    "Linear matrix inequality": 15898,
    "System identification": 3068,
    "PID controller": 55897,
    "Transfer function": 62157,
    "Optimal control": 63699,
    "Lyapunov function": 58937,
    "Lyapunov stability": 22574,
    "Adaptive control": 1209,
    "Feedback control": 51931,
}
PHILIPPE_IDXS = set(PHILIPPE_CORE.values())

# Philippe's extended neighborhood (concepts he already knows)
ALL_KNOWN = PHILIPPE_IDXS | {
    47589,   # Feedback controller
    17140,   # Nonlinear system identification
    15773,   # Control-Lyapunov function
    17705,   # Lyapunov equation
    270,     # Lyapunov optimization
    54454,   # Lyapunov redesign
    9153,    # Closed-loop transfer function
    14478,   # Nonlinear control
    57584,   # Sliding mode control
    60254,   # State observer
    14780,   # Controllability
    59068,   # Observability
    55136,   # State space
    62539,   # Pole placement
    61920,   # Bode plot
    62098,   # Nyquist stability criterion
    60888,   # Root locus
    15524,   # Model predictive control
    60028,   # Kalman filter
    59882,   # Linear-quadratic regulator
    27649,   # Backstepping
    58410,   # Internal model
    63277,   # Stability theory
    64133,   # Control system
    64602,   # Control engineering
    64849,   # Automation
}


def extract_philippe_pairs():
    """Two-phase extraction from CSR matrix (upper triangular).

    Phase 1 (indices only, ~413 MB):
      - Row scan: Philippe as row → collect flat positions + col indices
      - Column scan: Philippe as col → np.isin → collect flat positions + row indices
      → saves list of (flat_pos, row, col), then frees indices

    Phase 2 (data only, ~826 MB):
      - Extract values at saved positions
      → builds pairs dict, then frees data
    """
    print("[1] Extracting Philippe's pairs from snapshot_full.npz...")
    t0 = time.time()

    npz_path = os.path.join(PRED_DIR, "snapshot_full.npz")

    # ── PHASE 1: Load indptr + indices ──
    print("  Phase 1: Loading indptr + indices (~413 MB)...")
    npz = np.load(npz_path, allow_pickle=False)
    indptr = npz['indptr'].copy()       # ~260 KB — kept throughout
    all_indices = npz['indices']          # ~413 MB int32
    npz.close()

    phil_idxs = sorted(PHILIPPE_IDXS)

    # Collect ALL needed flat positions in one pass
    all_positions = []   # flat positions in data array
    all_meta = []        # (row_idx, col_idx) for each position

    # A) Row scan: Philippe index = row (smaller index in upper triangular)
    row_count = 0
    for pi in phil_idxs:
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

    # B) Column scan: Philippe index = col (larger index in upper triangular)
    #    Loop over 13 indices instead of np.isin (avoids 789 MB int64 temp)
    print("  Column scan (13 passes)...")
    mask = np.zeros(len(all_indices), dtype=np.bool_)
    for pi in phil_idxs:
        mask |= (all_indices == pi)
    hit_flat = np.where(mask)[0]
    hit_cols = all_indices[hit_flat].copy()
    del mask; gc.collect()

    # Resolve rows via binary search on indptr
    hit_rows = np.searchsorted(indptr, hit_flat, side='right') - 1

    col_count = 0
    for i in range(len(hit_flat)):
        r, c = int(hit_rows[i]), int(hit_cols[i])
        if r != c:
            all_positions.append(int(hit_flat[i]))
            all_meta.append((r, c))
            col_count += 1

    # Free indices — ~413 MB released
    del all_indices, hit_flat, hit_cols, hit_rows
    gc.collect()

    print(f"  Row pairs: {row_count:,}, Column pairs: {col_count:,}")
    print(f"  Total positions to extract: {len(all_positions):,}")

    # ── PHASE 2: Extract data.npy from zip → disk, then mmap (zero RAM) ──
    print("  Phase 2: Extracting data.npy to disk for mmap access...")
    import zipfile, tempfile, shutil
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(npz_path) as zf:
            zf.extract('data.npy', tmpdir)
        data_path = os.path.join(tmpdir, 'data.npy')
        data = np.load(data_path, mmap_mode='r')  # memory-mapped, ~0 RAM
        positions_arr = np.array(all_positions, dtype=np.int64)
        del all_positions; gc.collect()
        values = data[positions_arr].copy()  # only ~736 KB copied
        del data, positions_arr; gc.collect()
        print(f"  Got {len(values):,} values via mmap")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Build pairs dict (deduplicate: row scan and col scan may overlap)
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
    print("=" * 80)
    print("SCAN PHILIPPE V2 — 65K concepts, P4 Uzzi z-scores")
    print("=" * 80)

    # === 1. Extract co-occurrence ===
    cooc = extract_philippe_pairs()

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
    # Species names from collision matrix
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

        # Identify Philippe's side
        if idx_a in PHILIPPE_IDXS:
            phil_idx, other_idx = idx_a, idx_b
        else:
            phil_idx, other_idx = idx_b, idx_a

        phil_sp = species_map.get(phil_idx, -1)
        other_sp = species_map.get(other_idx, -1)
        other_lvl = idx_to_level.get(other_idx, -1)

        # Skip level 0-2 concepts (too generic: "Sample", "Population", etc.)
        if other_lvl < 3:
            continue

        results.append({
            "phil_name": idx_to_name.get(phil_idx, f"?{phil_idx}"),
            "phil_idx": phil_idx,
            "other_name": idx_to_name.get(other_idx, f"?{other_idx}"),
            "other_idx": other_idx,
            "other_level": idx_to_level.get(other_idx, -1),
            "cooc": observed,
            "z": z,
            "p4": p4,
            "phil_sp": phil_sp,
            "other_sp": other_sp,
            "phil_sp_name": species_names.get(str(phil_sp), "?"),
            "other_sp_name": species_names.get(str(other_sp), "?"),
            "cross": phil_sp != other_sp and phil_sp >= 0 and other_sp >= 0,
            "known": other_idx in ALL_KNOWN,
        })

    results.sort(key=lambda x: x["p4"], reverse=True)
    print(f"  {len(results):,} pairs scored")

    # === 5. Display ===
    cross_unknown = [r for r in results if r["cross"] and not r["known"]]
    intra_unknown = [r for r in results if not r["cross"] and not r["known"]]

    print(f"\n{'='*95}")
    print(f"TOP 100 P4 — CROSS-SPECIES, UNKNOWN TO PHILIPPE")
    print(f"= Bridges between Philippe's control theory and OTHER scientific continents =")
    print(f"{'='*95}")
    for i, r in enumerate(cross_unknown[:100]):
        zs = "+" if r["z"] > 0 else ""
        print(f"  {i+1:3d}. P4={r['p4']:8.4f} | z={zs}{r['z']:8.1f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['phil_name'][:25]:25s} × {r['other_name'][:35]}"
              f" | [{r['phil_sp_name'][:12]}×{r['other_sp_name'][:12]}]")

    print(f"\n{'='*95}")
    print(f"TOP 50 STRUCTURAL HOLES (z < 0, cross-species, unknown)")
    print(f"= Fewer co-occurrences than expected → REAL holes → where to look =")
    print(f"{'='*95}")
    holes = sorted([r for r in cross_unknown if r["z"] < 0], key=lambda x: x["z"])
    for i, r in enumerate(holes[:50]):
        print(f"  {i+1:3d}. z={r['z']:9.1f} | P4={r['p4']:.4f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['phil_name'][:25]:25s} × {r['other_name'][:35]}"
              f" | [{r['phil_sp_name'][:12]}×{r['other_sp_name'][:12]}]")

    print(f"\n{'='*95}")
    print(f"TOP 50 INTRA-SPECIES SURPRISES (same continent, unknown)")
    print(f"{'='*95}")
    for i, r in enumerate(intra_unknown[:50]):
        zs = "+" if r["z"] > 0 else ""
        print(f"  {i+1:3d}. P4={r['p4']:8.4f} | z={zs}{r['z']:8.1f} | cooc={r['cooc']:10.1f}"
              f" | L{r['other_level']} {r['phil_name'][:25]:25s} × {r['other_name'][:35]}"
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

    # === 7. Save ===
    outfile = os.path.join(REPO, "data", "scan_philippe_v2.json")
    summary = {
        "scan": "philippe_schuchert_v2",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_pairs_total": len(results),
        "n_cross_unknown": len(cross_unknown),
        "n_holes": len(holes),
        "philippe_concepts": list(PHILIPPE_CORE.keys()),
        "top_100_cross_unknown": [{k: v for k, v in r.items()}
                                   for r in cross_unknown[:100]],
        "top_50_holes": [{k: v for k, v in r.items()}
                         for r in holes[:50]],
        "species_distribution": sp_counts,
    }
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")
    print(f"Total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
