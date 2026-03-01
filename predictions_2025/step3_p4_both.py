#!/usr/bin/env python3
"""
Predictions 2025 — Step 3: P4 Two Layers (inter + intra)
========================================================
Memory-optimized: ALL 108M-pair arrays in float32 with pre-allocated out=.
Species loaded AFTER P4 to minimize peak memory.
Top-K recomputed in float64 for output precision.

P4 = activity_A * activity_B * (1 - cooc_norm) * |z_uzzi|
"""
import json
import os
import sys
import time
import gc
import numpy as np
from scipy.sparse import load_npz

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
N_CONCEPTS = 65026
TOP_K = 10000


def main():
    t0 = time.time()
    print("Predictions 2025 — Step 3: P4 Two Layers")
    print("=" * 60)

    # === Load activity (small, 65K floats) ===
    print("[1] Loading activity...")
    with open(os.path.join(BASE, "activity_full.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)
    total_works = act_data["total_works"]
    n_active = int(np.sum(activity > 0))
    del act_data; gc.collect()
    print(f"  Active: {n_active:,}, total_works={total_works:,}")

    # === Extract COO arrays (free CSR ASAP) ===
    print("\n[2] Loading matrix -> COO...")
    mat = load_npz(os.path.join(BASE, "snapshot_full.npz"))
    print(f"  CSR: {mat.shape}, nnz={mat.nnz:,}")
    mat_coo = mat.tocoo()
    del mat; gc.collect()

    rows = mat_coo.row.copy()
    cols = mat_coo.col.copy()
    data = mat_coo.data.astype(np.float32)  # float32 saves 413 MB
    del mat_coo; gc.collect()

    n_pairs = len(data)
    print(f"  Pairs: {n_pairs:,}")
    print(f"  Base: rows({rows.nbytes//1e6:.0f}MB) + cols({cols.nbytes//1e6:.0f}MB) + data({data.nbytes//1e6:.0f}MB) = {(rows.nbytes+cols.nbytes+data.nbytes)/1e6:.0f}MB")

    # === Compute z-scores (all float32, all out= to avoid temps) ===
    print("\n[3] Computing z-scores (Uzzi, float32, zero-alloc)...")
    total_works_sum = float(activity.sum())
    S = np.float32(total_works_sum)
    print(f"  S = {total_works_sum:,.0f}")

    # Pre-allocate working arrays (reused throughout)
    act_r = activity[rows].astype(np.float32)  # 413 MB
    act_c = activity[cols].astype(np.float32)  # 413 MB
    buf1 = np.empty(n_pairs, dtype=np.float32)  # 413 MB - reusable buffer

    # E = act_r * act_c / S  (store in buf1, rename to E)
    np.multiply(act_r, act_c, out=buf1)
    buf1 /= S
    E = buf1  # E is now buf1

    # std = (1 - act_r/S) * (1 - act_c/S) * E
    buf2 = np.empty(n_pairs, dtype=np.float32)  # 413 MB - another buffer
    np.divide(act_r, S, out=buf2)
    np.subtract(np.float32(1.0), buf2, out=buf2)  # buf2 = 1 - p_r

    std = np.empty(n_pairs, dtype=np.float32)    # 413 MB
    np.divide(act_c, S, out=std)
    np.subtract(np.float32(1.0), std, out=std)    # std = 1 - p_c

    std *= buf2                                    # std = (1-p_r)*(1-p_c)
    del buf2; gc.collect()

    std *= E                                       # std = E*(1-p_r)*(1-p_c)
    np.maximum(std, np.float32(0.0), out=std)
    np.sqrt(std, out=std)
    np.maximum(std, np.float32(1.0), out=std)

    # z = (data - E) / std  (reuse E array for z)
    np.subtract(data, E, out=E)                    # E = data - E = observed - expected
    E /= std                                       # E = z
    del std; gc.collect()
    z = E                                          # z is now in the E buffer

    print(f"  z range: [{z.min():.1f}, {z.max():.1f}]")
    print(f"  Negative z (holes): {int(np.sum(z < 0)):,}")

    # === Compute P4 (reuse act_r for final P4) ===
    print("\n[4] Computing P4 scores...")
    active_values = activity[activity > 0]
    act_min = np.float32(active_values.min())
    act_max = np.float32(active_values.max())
    del active_values

    # Normalize act_r, act_c to [0,1]
    act_r -= act_min
    act_r /= (act_max - act_min)
    np.clip(act_r, 0, 1, out=act_r)

    act_c -= act_min
    act_c /= (act_max - act_min)
    np.clip(act_c, 0, 1, out=act_c)

    cooc_max = float(data.max())

    # P4 = act_r * act_c * |z| * (1 - data/cooc_max)
    act_r *= act_c
    del act_c; gc.collect()

    np.abs(z, out=z)
    act_r *= z
    del z; gc.collect()

    # gap = 1 - data/cooc_max  (reuse a buffer)
    gap = np.empty(n_pairs, dtype=np.float32)
    np.divide(data, np.float32(cooc_max), out=gap)
    np.subtract(np.float32(1.0), gap, out=gap)

    act_r *= gap
    del gap; gc.collect()

    P4 = act_r  # P4 scores (float32)
    print(f"  P4 range: [{P4.min():.8f}, {P4.max():.4f}]")

    # === Load species + concepts (P4 is done, less memory pressure) ===
    print("\n[5] Loading species + concepts...")

    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        concepts_data = json.load(f)
    idx_to_name = {}
    idx_to_url = {}
    url_to_idx = {}
    for url, info in concepts_data["concepts"].items():
        idx_to_name[info["idx"]] = info["name"]
        idx_to_url[info["idx"]] = url
        url_to_idx[url] = info["idx"]

    with open(os.path.join(BASE, "species_full.json"), 'r', encoding='utf-8') as f:
        species_data = json.load(f)
    species_map = np.full(N_CONCEPTS, -1, dtype=np.int8)
    for url, info in species_data["concepts"].items():
        if url in url_to_idx:
            species_map[url_to_idx[url]] = info["species"]
    del species_data, concepts_data, url_to_idx; gc.collect()

    sp_r = species_map[rows]  # int8, tiny: 108 MB
    sp_c = species_map[cols]  # int8, tiny: 108 MB

    inter_mask = (sp_r != sp_c) & (sp_r >= 0) & (sp_c >= 0)
    intra_mask = (sp_r == sp_c) & (sp_r >= 0)
    n_inter = int(np.sum(inter_mask))
    n_intra = int(np.sum(intra_mask))
    print(f"  Inter-species: {n_inter:,} ({100*n_inter/n_pairs:.1f}%)")
    print(f"  Intra-species: {n_intra:,} ({100*n_intra/n_pairs:.1f}%)")

    # === Helper: recompute z/gap in float64 for top K ===
    def recompute_z_gap(indices):
        r = rows[indices]
        c = cols[indices]
        ar = activity[r]
        ac = activity[c]
        Ev = ar * ac / total_works_sum
        pr = ar / total_works_sum
        pc = ac / total_works_sum
        sv = np.sqrt(Ev * (1 - pr) * (1 - pc))
        sv = np.maximum(sv, 1.0)
        d_f64 = data[indices].astype(np.float64)
        z_sub = (d_f64 - Ev) / sv
        gap_sub = 1.0 - d_f64 / cooc_max
        return z_sub, gap_sub

    # === Extract top K for each layer ===
    # Strategy: zero out P4 for non-layer pairs, find top-K on full array
    # This avoids materializing a 66M-element layer_indices array
    P4_orig = P4.copy()  # keep original for second layer

    for layer_name, mask, out_name, restore in [
        ("INTER", inter_mask, "p4_predictions_INTER.json", True),
        ("INTRA", intra_mask, "p4_predictions_INTRA.json", False),
    ]:
        print(f"\n[6] Extracting top {TOP_K:,} {layer_name} predictions...")
        n_layer = int(np.sum(mask))

        # Zero non-layer entries so argpartition ignores them
        P4[~mask] = np.float32(0.0)

        k = min(TOP_K, n_layer)
        # argpartition on full P4 (108M) but only top K matter
        top_global = np.argpartition(P4, -k)[-k:]
        top_global = top_global[np.argsort(-P4[top_global])]
        top_global = top_global.astype(np.int32)

        # Restore P4 for next layer
        if restore:
            np.copyto(P4, P4_orig)

        z_top, gap_top = recompute_z_gap(top_global)

        predictions = []
        for rank_i, (gi, z_val, gap_val) in enumerate(zip(top_global, z_top, gap_top)):
            r, c = int(rows[gi]), int(cols[gi])
            predictions.append({
                "rank": rank_i + 1,
                "concept_a_idx": r,
                "concept_b_idx": c,
                "concept_a_name": idx_to_name.get(r, f"?{r}"),
                "concept_b_name": idx_to_name.get(c, f"?{c}"),
                "concept_a_url": idx_to_url.get(r, ""),
                "concept_b_url": idx_to_url.get(c, ""),
                "pair_key": f"{idx_to_url.get(r, '')}|{idx_to_url.get(c, '')}",
                "p4_score": round(float(P4[gi]), 10),
                "z_score": round(float(z_val), 4),
                "cooc_weight": round(float(data[gi]), 6),
                "gap": round(float(gap_val), 6),
                "activity_a": int(activity[r]),
                "activity_b": int(activity[c]),
                "species_a": int(sp_r[gi]),
                "species_b": int(sp_c[gi]),
            })

        threshold = float(P4[top_global[-1]]) if len(top_global) > 0 else 0

        result = {
            "meta": {
                "layer": layer_name,
                "method": f"P4 = act_A * act_B * (1-cooc_norm) * |z_uzzi| — {layer_name} ONLY",
                "n_concepts": N_CONCEPTS,
                "n_active": n_active,
                "n_total_pairs": n_pairs,
                "n_layer_pairs": n_layer,
                "top_k": TOP_K,
                "p4_threshold": threshold,
                "total_works_sum": total_works_sum,
                "cooc_max": cooc_max,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "predictions": predictions,
        }

        out_path = os.path.join(BASE, out_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  Saved: {out_name} (threshold={threshold:.6f})")

        print(f"\n  Top 10 {layer_name}:")
        for p in predictions[:10]:
            sp_str = f"S{p['species_a']}xS{p['species_b']}"
            print(f"    #{p['rank']:4d}  P4={p['p4_score']:.4f}  z={p['z_score']:+8.1f}  "
                  f"{sp_str:8s}  "
                  f"{p['concept_a_name'][:25]:25s} x {p['concept_b_name'][:25]}")

        del top_global
        gc.collect()

    total_time = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"STEP 3 DONE — {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"  Inter: {n_inter:,} pairs | Intra: {n_intra:,} pairs")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
