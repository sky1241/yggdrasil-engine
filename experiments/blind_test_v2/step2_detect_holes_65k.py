#!/usr/bin/env python3
"""
Blind Test V2 — Step 2: Detect structural holes (P4 scores)
============================================================
Computes P4 for all non-zero co-occurrence pairs.
Two versions: V1 (baseline) and V2 (with species bonus from 2015 clustering).

P4 = activity_A * activity_B * (1 - cooc_norm) * |z_uzzi|
P4_v2 = P4 * species_bonus  (1.5 if inter-species, 1.0 if same)

Input:
  blind_test_v2/snapshot_2015_65k.npz
  blind_test_v2/activity_2015.json
  blind_test_v2/species_2015.json       (from step 1b — NO look-ahead)
  data/scan/concepts_65k.json

Output:
  blind_test_v2/p4_predictions_v1.json  (top 10K P4 baseline)
  blind_test_v2/p4_predictions_v2.json  (top 10K P4 with species bonus)
"""
import json
import os
import sys
import time
import numpy as np
from scipy.sparse import load_npz

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
N_CONCEPTS = 65026
TOP_K = 10000


def main():
    t0 = time.time()
    print("Blind Test V2 — Step 2: Detect Structural Holes")
    print("=" * 60)

    # === Load data ===
    print("[1] Loading data...")

    # Sparse matrix (upper triangular)
    mat = load_npz(os.path.join(BASE, "snapshot_2015_65k.npz"))
    print(f"  Matrix: {mat.shape}, nnz={mat.nnz:,}")

    # Activity
    with open(os.path.join(BASE, "activity_2015.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)
    total_works = act_data["total_works"]
    n_active = int(np.sum(activity > 0))
    print(f"  Activity: {n_active:,} active concepts")
    print(f"  Total works <= 2015: {total_works:,}")

    # Concepts (for names)
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        concepts_data = json.load(f)
    idx_to_name = {}
    idx_to_url = {}
    for url, info in concepts_data["concepts"].items():
        idx_to_name[info["idx"]] = info["name"]
        idx_to_url[info["idx"]] = url

    # Species (from 2015-only clustering — NO look-ahead)
    with open(os.path.join(BASE, "species_2015.json"), 'r', encoding='utf-8') as f:
        species_data = json.load(f)
    species_map = np.full(N_CONCEPTS, -1, dtype=np.int32)
    for url, info in species_data["concepts"].items():
        if url in concepts_data["concepts"]:
            idx = concepts_data["concepts"][url]["idx"]
            species_map[idx] = info["species"]
    n_species_mapped = int(np.sum(species_map >= 0))
    print(f"  Species (2015-only): {n_species_mapped:,} mapped")

    # === Extract sparse entries ===
    print("\n[2] Extracting sparse entries...")
    mat_coo = mat.tocoo()
    rows = mat_coo.row.astype(np.int32)
    cols = mat_coo.col.astype(np.int32)
    data = mat_coo.data.astype(np.float64)
    n_pairs = len(data)
    print(f"  Total pairs (non-zero cooc): {n_pairs:,}")
    del mat, mat_coo

    # Filter: both concepts must have activity > 0
    # (concepts with zero activity <= 2015 don't exist in the blind test)
    active_mask = (activity[rows] > 0) & (activity[cols] > 0)
    n_filtered = int(np.sum(~active_mask))
    if n_filtered > 0:
        rows = rows[active_mask]
        cols = cols[active_mask]
        data = data[active_mask]
        n_pairs = len(data)
        print(f"  After filtering inactive concepts: {n_pairs:,} "
              f"(removed {n_filtered:,})")

    # === Compute z-score Uzzi (memory-optimized) ===
    print("\n[3] Computing z-scores (Uzzi atypicality)...")
    import gc

    total_works_sum = float(activity.sum())
    print(f"  total_works_sum (activity.sum): {total_works_sum:,.0f}")

    act_r = activity[rows]
    act_c = activity[cols]

    # z = (observed - E) / std  where E = act_r*act_c/total, std = sqrt(E*(1-p_r)*(1-p_c))
    # Compute in-place to save memory
    E = act_r * act_c
    E /= total_works_sum

    p_r = act_r / total_works_sum
    p_c = act_c / total_works_sum

    # std = sqrt(E * (1-p_r) * (1-p_c))
    std = E * (1.0 - p_r)
    del p_r; gc.collect()
    std *= (1.0 - p_c)
    del p_c; gc.collect()
    np.sqrt(std, out=std)
    np.maximum(std, 1.0, out=std)

    z = data - E
    del E; gc.collect()
    z /= std
    del std; gc.collect()

    print(f"  z range: [{z.min():.1f}, {z.max():.1f}]")
    print(f"  z mean: {z.mean():.2f}")
    print(f"  Negative z (structural holes): {int(np.sum(z < 0)):,} / {n_pairs:,}")

    # === Compute P4 (memory-optimized) ===
    print("\n[4] Computing P4 scores...")

    # Activity normalization (min-max)
    active_values = activity[activity > 0]
    act_min = float(active_values.min())
    act_max = float(active_values.max())
    del active_values

    # Normalize act_r in-place
    act_r -= act_min
    act_r /= (act_max - act_min)
    np.clip(act_r, 0, 1, out=act_r)

    # Normalize act_c in-place
    act_c -= act_min
    act_c /= (act_max - act_min)
    np.clip(act_c, 0, 1, out=act_c)

    # Co-occurrence gap
    cooc_max = float(data.max())

    # P4 V1: reuse act_r array for final result to avoid new allocation
    # P4 = act_r_norm * act_c_norm * gap * |z|
    act_r *= act_c       # act_r now = act_r_norm * act_c_norm
    del act_c; gc.collect()

    np.abs(z, out=z)     # z now = |z|
    act_r *= z            # act_r now = act_r_norm * act_c_norm * |z|
    del z; gc.collect()

    # gap = 1 - cooc/cooc_max ; multiply in-place
    gap = data / cooc_max
    gap *= -1
    gap += 1              # gap = 1 - data/cooc_max

    act_r *= gap          # act_r now = full P4_v1
    del gap; gc.collect()

    P4_v1 = act_r  # rename for clarity (no copy)

    # P4 V2 (species bonus)
    sp_r = species_map[rows]
    sp_c = species_map[cols]
    inter_mask = (sp_r != sp_c) & (sp_r >= 0) & (sp_c >= 0)
    n_inter = int(np.sum(inter_mask))

    P4_v2 = P4_v1.copy()
    P4_v2[inter_mask] *= 1.5

    print(f"  P4 V1 range: [{P4_v1.min():.8f}, {P4_v1.max():.6f}]")
    print(f"  P4 V2 range: [{P4_v2.min():.8f}, {P4_v2.max():.6f}]")
    print(f"  Inter-species pairs (bonus=1.5): {n_inter:,} / {n_pairs:,} "
          f"({100*n_inter/n_pairs:.1f}%)")

    # === Save top K for each version ===
    print(f"\n[5] Extracting top {TOP_K:,} predictions...")

    # Helper: recompute z and gap for a small subset of indices
    def recompute_z_gap(indices):
        """Recompute z-score and gap for specific pair indices (memory-safe)."""
        r = rows[indices]
        c = cols[indices]
        ar = activity[r]
        ac = activity[c]
        E = ar * ac / total_works_sum
        p_r = ar / total_works_sum
        p_c = ac / total_works_sum
        std = np.sqrt(E * (1 - p_r) * (1 - p_c))
        std = np.maximum(std, 1.0)
        z_sub = (data[indices] - E) / std
        gap_sub = 1.0 - data[indices] / cooc_max
        return z_sub, gap_sub

    for version, P4, out_name in [
        ("V1", P4_v1, "p4_predictions_v1.json"),
        ("V2", P4_v2, "p4_predictions_v2.json"),
    ]:
        k = min(TOP_K, len(P4))
        top_idx = np.argpartition(-P4, k)[:k]
        top_idx = top_idx[np.argsort(-P4[top_idx])]

        # Recompute z and gap only for top K (saves ~1.2 GB vs keeping full arrays)
        z_top, gap_top = recompute_z_gap(top_idx)

        predictions = []
        for rank_i, (i, z_val, gap_val) in enumerate(zip(top_idx, z_top, gap_top)):
            r, c = int(rows[i]), int(cols[i])
            pair_key = f"{idx_to_url.get(r, '')}|{idx_to_url.get(c, '')}"
            predictions.append({
                "rank": rank_i + 1,
                "concept_a_idx": r,
                "concept_b_idx": c,
                "concept_a_name": idx_to_name.get(r, f"?{r}"),
                "concept_b_name": idx_to_name.get(c, f"?{c}"),
                "concept_a_url": idx_to_url.get(r, ""),
                "concept_b_url": idx_to_url.get(c, ""),
                "pair_key": pair_key,
                "p4_score": round(float(P4[i]), 10),
                "z_score": round(float(z_val), 4),
                "cooc_weight": round(float(data[i]), 6),
                "gap": round(float(gap_val), 6),
                "activity_a": int(activity[r]),
                "activity_b": int(activity[c]),
                "species_a": int(species_map[r]),
                "species_b": int(species_map[c]),
                "inter_species": bool(inter_mask[i]),
            })

        # Also save the P4 threshold (min in top K) for step 4
        threshold = float(P4[top_idx[-1]]) if len(top_idx) > 0 else 0

        out_path = os.path.join(BASE, out_name)
        result = {
            "meta": {
                "version": version,
                "method": ("P4 = act_A * act_B * (1-cooc_norm) * |z_uzzi|"
                           + (" * species_bonus(1.5)" if version == "V2" else "")),
                "species_source": "species_2015.json (NO look-ahead)",
                "n_concepts": N_CONCEPTS,
                "n_active_concepts": n_active,
                "n_pairs_scored": n_pairs,
                "top_k": TOP_K,
                "p4_threshold_top_k": threshold,
                "cutoff_year": 2015,
                "total_works_sum": total_works_sum,
                "cooc_max": cooc_max,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "predictions": predictions,
        }
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n  {version} saved: {out_name} (threshold={threshold:.8f})")
        print(f"  Top 10 {version}:")
        for p in predictions[:10]:
            sp_info = f"S{p['species_a']}×S{p['species_b']}" if p['inter_species'] else f"S{p['species_a']}"
            print(f"    #{p['rank']:4d}  P4={p['p4_score']:.6f}  z={p['z_score']:+8.1f}  "
                  f"{sp_info:8s}  "
                  f"{p['concept_a_name'][:22]:22s} × {p['concept_b_name'][:22]}")

    total_time = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"STEP 2 DONE — {total_time:.0f}s ({total_time/60:.1f} min)")


if __name__ == "__main__":
    main()
