#!/usr/bin/env python3
"""
Blind Test V2 — Step 7: Inter-Species Filter Analysis
=====================================================
Tests Sky's theory: P4 bridges BETWEEN species (continents)
are the real prediction mechanism.

Two analyses:
  A) Quick: filter existing top 10K to inter-species, re-rank, re-score
  B) Full: reload sparse matrix, compute P4 for ALL 48M+ inter-species
     pairs, take proper top 10K, score against ground truth

Input:
  blind_test_v2/p4_predictions_v1.json  (existing top 10K)
  blind_test_v2/ground_truth_v2.json
  blind_test_v2/snapshot_2015_65k.npz   (for full recomputation)
  blind_test_v2/activity_2015.json
  blind_test_v2/species_2015.json

Output:
  blind_test_v2/inter_species_analysis.json
  blind_test_v2/p4_predictions_inter.json  (top 10K inter-species only)
"""
import json
import os
import sys
import time
import gc
import numpy as np
from scipy.sparse import load_npz
from scipy.stats import mannwhitneyu

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
N_CONCEPTS = 65026
TOP_K = 10000


def load_json(filename):
    path = os.path.join(BASE, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    t0 = time.time()
    print("Blind Test V2 — Step 7: Inter-Species Filter")
    print("=" * 60)
    print("THEORY: P4 bridges BETWEEN species predict discoveries")
    print("=" * 60)

    # ============================================================
    # PART A: Quick analysis with existing top 10K
    # ============================================================
    print("\n" + "=" * 60)
    print("PART A: Quick filter on existing top 10K predictions")
    print("=" * 60)

    pred_v1 = load_json("p4_predictions_v1.json")
    ground_truth = load_json("ground_truth_v2.json")
    species_data = load_json("species_2015.json")

    preds = pred_v1["predictions"]
    gt_list = ground_truth["breakthroughs"]

    # Get species for ground truth concepts
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        concepts_data = json.load(f)

    # Build species map by index
    species_by_idx = {}
    for url, info in species_data["concepts"].items():
        if url in concepts_data["concepts"]:
            idx = concepts_data["concepts"][url]["idx"]
            species_by_idx[idx] = info["species"]

    # Species names (from step1b)
    species_names = {
        0: "CS/Engineering",
        1: "ChemMat",
        2: "TerGeo",
        3: "MedClinical",
        4: "Physics",
        5: "HumEco",
        6: "BioClinical",
        7: "MathStat",
        8: "HumArts",
    }

    # === Ground truth species analysis ===
    print("\n[A1] Ground truth — species assignments:")
    gt_inter_count = 0
    gt_intra_count = 0
    for gt in gt_list:
        sp_a = species_by_idx.get(gt["concept_a_idx"], -1)
        sp_b = species_by_idx.get(gt["concept_b_idx"], -1)
        inter = sp_a != sp_b and sp_a >= 0 and sp_b >= 0
        marker = "INTER" if inter else "INTRA"
        if inter:
            gt_inter_count += 1
        else:
            gt_intra_count += 1
        sp_a_name = species_names.get(sp_a, f"?{sp_a}")
        sp_b_name = species_names.get(sp_b, f"?{sp_b}")
        print(f"  {marker:5s} | S{sp_a}({sp_a_name:13s}) × S{sp_b}({sp_b_name:13s}) | "
              f"{gt['concept_a_name'][:20]:20s} × {gt['concept_b_name'][:20]:20s} | "
              f"{gt['name']}")
    print(f"\n  Summary: {gt_inter_count} INTER / {gt_intra_count} INTRA out of {len(gt_list)}")

    # === Filter predictions to inter-species ===
    print("\n[A2] Filtering predictions to inter-species only...")
    inter_preds = [p for p in preds if p["inter_species"]]
    intra_preds = [p for p in preds if not p["inter_species"]]
    print(f"  Total predictions:     {len(preds):,}")
    print(f"  Inter-species:         {len(inter_preds):,} ({100*len(inter_preds)/len(preds):.1f}%)")
    print(f"  Intra-species removed: {len(intra_preds):,}")

    # Re-rank inter-species predictions
    for new_rank, p in enumerate(inter_preds, 1):
        p["rank_inter"] = new_rank

    # === Score filtered predictions against ground truth ===
    print("\n[A3] Scoring inter-species predictions against ground truth...")

    # Build lookup: pair_key -> rank_inter
    inter_lookup = {}
    for p in inter_preds:
        # Normalize the pair key (sort indices)
        idx_pair = sorted([p["concept_a_idx"], p["concept_b_idx"]])
        key = f"{idx_pair[0]}|{idx_pair[1]}"
        inter_lookup[key] = p["rank_inter"]

    # Also build lookup for original V1 predictions
    v1_lookup = {}
    for p in preds:
        idx_pair = sorted([p["concept_a_idx"], p["concept_b_idx"]])
        key = f"{idx_pair[0]}|{idx_pair[1]}"
        v1_lookup[key] = p["rank"]

    # Score each ground truth
    quick_results = []
    for gt in gt_list:
        idx_pair = sorted([gt["concept_a_idx"], gt["concept_b_idx"]])
        key = f"{idx_pair[0]}|{idx_pair[1]}"
        sp_a = species_by_idx.get(gt["concept_a_idx"], -1)
        sp_b = species_by_idx.get(gt["concept_b_idx"], -1)
        is_inter = sp_a != sp_b and sp_a >= 0 and sp_b >= 0

        v1_rank = v1_lookup.get(key, 10001)
        inter_rank = inter_lookup.get(key, len(inter_preds) + 1)

        quick_results.append({
            "name": gt["name"],
            "concept_a": gt["concept_a_name"],
            "concept_b": gt["concept_b_name"],
            "species_a": sp_a,
            "species_b": sp_b,
            "species_a_name": species_names.get(sp_a, "?"),
            "species_b_name": species_names.get(sp_b, "?"),
            "is_inter_species": is_inter,
            "v1_rank": v1_rank,
            "inter_rank": inter_rank,
            "rank_improved": v1_rank - inter_rank if inter_rank <= len(inter_preds) else 0,
        })

    # Print table
    print(f"\n  {'Breakthrough':<25s} {'V1 rank':>8s} {'Inter rank':>10s} {'Improve':>8s} {'Species':>20s}")
    print(f"  {'─'*25} {'─'*8} {'─'*10} {'─'*8} {'─'*20}")
    for r in quick_results:
        v1_str = f"{r['v1_rank']:,}" if r['v1_rank'] <= 10000 else ">10K"
        if r['inter_rank'] <= len(inter_preds):
            inter_str = f"{r['inter_rank']:,}"
        else:
            inter_str = ">INTER" if not r['is_inter_species'] else ">10K"
        imp_str = f"+{r['rank_improved']:,}" if r['rank_improved'] > 0 else "—"
        sp_str = f"S{r['species_a']}×S{r['species_b']}"
        print(f"  {r['name']:<25s} {v1_str:>8s} {inter_str:>10s} {imp_str:>8s} {sp_str:>20s}")

    # Recall metrics
    n_gt = len(gt_list)
    n_inter = len(inter_preds)

    for cutoff_label, cutoff in [("100", 100), ("1000", 1000), ("5000", 5000)]:
        v1_hits = sum(1 for r in quick_results if r['v1_rank'] <= int(cutoff_label))
        inter_hits = sum(1 for r in quick_results
                         if r['inter_rank'] <= int(cutoff_label)
                         and r['inter_rank'] <= n_inter)
        print(f"\n  Recall@{cutoff_label}:  V1={v1_hits}/{n_gt} ({100*v1_hits/n_gt:.0f}%)  "
              f"  InterFilter={inter_hits}/{n_gt} ({100*inter_hits/n_gt:.0f}%)")
        if int(cutoff_label) <= n_inter:
            prec_v1 = v1_hits / int(cutoff_label) * 100
            prec_inter = inter_hits / int(cutoff_label) * 100
            print(f"  Precision@{cutoff_label}: V1={prec_v1:.3f}%   InterFilter={prec_inter:.3f}%")

    # ============================================================
    # PART B: Full recomputation — proper top 10K inter-species
    # ============================================================
    print("\n\n" + "=" * 60)
    print("PART B: Full recomputation — inter-species P4 from scratch")
    print("=" * 60)

    t1 = time.time()

    # Load sparse matrix
    print("\n[B1] Loading sparse matrix...")
    mat = load_npz(os.path.join(BASE, "snapshot_2015_65k.npz"))
    print(f"  Matrix: {mat.shape}, nnz={mat.nnz:,}")

    # Activity
    act_data = load_json("activity_2015.json")
    activity = np.array(act_data["activity"], dtype=np.float64)
    total_works_sum = float(activity.sum())

    # Species map (numpy)
    species_map = np.full(N_CONCEPTS, -1, dtype=np.int32)
    for url, info in species_data["concepts"].items():
        if url in concepts_data["concepts"]:
            idx = concepts_data["concepts"][url]["idx"]
            species_map[idx] = info["species"]

    # Concept names
    idx_to_name = {}
    idx_to_url = {}
    for url, info in concepts_data["concepts"].items():
        idx_to_name[info["idx"]] = info["name"]
        idx_to_url[info["idx"]] = url

    # Extract sparse entries
    print("\n[B2] Extracting sparse entries...")
    mat_coo = mat.tocoo()
    rows = mat_coo.row.astype(np.int32)
    cols = mat_coo.col.astype(np.int32)
    data = mat_coo.data.astype(np.float64)
    n_pairs = len(data)
    del mat_coo
    gc.collect()

    # Filter: both active
    active_mask = (activity[rows] > 0) & (activity[cols] > 0)
    rows = rows[active_mask]
    cols = cols[active_mask]
    data = data[active_mask]
    n_pairs = len(data)
    del active_mask
    gc.collect()
    print(f"  Active pairs: {n_pairs:,}")

    # === INTER-SPECIES FILTER ===
    print("\n[B3] Applying inter-species filter...")
    sp_r = species_map[rows]
    sp_c = species_map[cols]
    inter_mask = (sp_r != sp_c) & (sp_r >= 0) & (sp_c >= 0)
    n_inter_total = int(np.sum(inter_mask))
    n_intra_total = n_pairs - n_inter_total
    print(f"  Inter-species: {n_inter_total:,} ({100*n_inter_total/n_pairs:.1f}%)")
    print(f"  Intra-species: {n_intra_total:,} (REMOVED)")

    # Keep species info for output
    sp_r_inter = sp_r[inter_mask]
    sp_c_inter = sp_c[inter_mask]
    del sp_r, sp_c
    gc.collect()

    # Apply filter
    rows_i = rows[inter_mask]
    cols_i = cols[inter_mask]
    data_i = data[inter_mask]
    del rows, cols, data, inter_mask
    gc.collect()
    print(f"  Filtered pairs: {len(rows_i):,}")

    # === Compute z-score (memory-optimized) ===
    print("\n[B4] Computing z-scores (Uzzi) for inter-species pairs...")

    act_r = activity[rows_i]
    act_c = activity[cols_i]

    E = act_r * act_c
    E /= total_works_sum

    p_r = act_r / total_works_sum
    p_c = act_c / total_works_sum

    std = E * (1.0 - p_r)
    del p_r; gc.collect()
    std *= (1.0 - p_c)
    del p_c; gc.collect()
    np.sqrt(std, out=std)
    np.maximum(std, 1.0, out=std)

    z = data_i - E
    del E; gc.collect()
    z /= std
    del std; gc.collect()

    print(f"  z range: [{z.min():.1f}, {z.max():.1f}]")
    print(f"  Negative z (holes): {int(np.sum(z < 0)):,} / {len(z):,}")

    # === Compute P4 (memory-optimized) ===
    print("\n[B5] Computing P4 scores...")

    active_values = activity[activity > 0]
    act_min = float(active_values.min())
    act_max = float(active_values.max())
    del active_values

    act_r -= act_min
    act_r /= (act_max - act_min)
    np.clip(act_r, 0, 1, out=act_r)

    act_c -= act_min
    act_c /= (act_max - act_min)
    np.clip(act_c, 0, 1, out=act_c)

    cooc_max = float(data_i.max())

    act_r *= act_c
    del act_c; gc.collect()

    np.abs(z, out=z)
    act_r *= z
    del z; gc.collect()

    gap = data_i / cooc_max
    gap *= -1
    gap += 1

    act_r *= gap
    del gap; gc.collect()

    P4_inter = act_r  # rename
    print(f"  P4 range: [{P4_inter.min():.8f}, {P4_inter.max():.6f}]")

    # === Extract top K ===
    print(f"\n[B6] Extracting top {TOP_K:,} inter-species predictions...")
    k = min(TOP_K, len(P4_inter))
    top_idx = np.argpartition(-P4_inter, k)[:k]
    top_idx = top_idx[np.argsort(-P4_inter[top_idx])]

    # Recompute z and gap for top K (detailed output)
    def recompute_z_gap(indices):
        r = rows_i[indices]
        c = cols_i[indices]
        ar = activity[r]
        ac = activity[c]
        E = ar * ac / total_works_sum
        p_r = ar / total_works_sum
        p_c = ac / total_works_sum
        std = np.sqrt(E * (1 - p_r) * (1 - p_c))
        std = np.maximum(std, 1.0)
        z_sub = (data_i[indices] - E) / std
        gap_sub = 1.0 - data_i[indices] / cooc_max
        return z_sub, gap_sub

    z_top, gap_top = recompute_z_gap(top_idx)

    predictions_inter = []
    for rank_i, (i, z_val, gap_val) in enumerate(zip(top_idx, z_top, gap_top)):
        r, c = int(rows_i[i]), int(cols_i[i])
        pair_key = f"{idx_to_url.get(r, '')}|{idx_to_url.get(c, '')}"
        predictions_inter.append({
            "rank": rank_i + 1,
            "concept_a_idx": r,
            "concept_b_idx": c,
            "concept_a_name": idx_to_name.get(r, f"?{r}"),
            "concept_b_name": idx_to_name.get(c, f"?{c}"),
            "concept_a_url": idx_to_url.get(r, ""),
            "concept_b_url": idx_to_url.get(c, ""),
            "pair_key": pair_key,
            "p4_score": round(float(P4_inter[i]), 10),
            "z_score": round(float(z_val), 4),
            "cooc_weight": round(float(data_i[i]), 6),
            "gap": round(float(gap_val), 6),
            "activity_a": int(activity[r]),
            "activity_b": int(activity[c]),
            "species_a": int(sp_r_inter[i]),
            "species_b": int(sp_c_inter[i]),
            "species_a_name": species_names.get(int(sp_r_inter[i]), "?"),
            "species_b_name": species_names.get(int(sp_c_inter[i]), "?"),
        })

    # Save predictions
    threshold = float(P4_inter[top_idx[-1]]) if len(top_idx) > 0 else 0
    inter_out = {
        "meta": {
            "method": "P4 = act_A * act_B * (1-cooc_norm) * |z_uzzi| — INTER-SPECIES ONLY",
            "filter": "inter_species_only (sp_A != sp_B, both >= 0)",
            "n_concepts": N_CONCEPTS,
            "n_total_pairs_scored": n_pairs,
            "n_inter_species_pairs": n_inter_total,
            "n_intra_removed": n_intra_total,
            "inter_species_fraction": round(n_inter_total / n_pairs, 4),
            "top_k": TOP_K,
            "p4_threshold_top_k": threshold,
            "cutoff_year": 2015,
            "total_works_sum": total_works_sum,
            "cooc_max": cooc_max,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "predictions": predictions_inter,
    }
    inter_path = os.path.join(BASE, "p4_predictions_inter.json")
    with open(inter_path, 'w', encoding='utf-8') as f:
        json.dump(inter_out, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {inter_path}")

    # Top 15 inter-species predictions
    print(f"\n  Top 15 inter-species predictions:")
    print(f"  {'#':>5s} {'P4':>10s} {'z':>8s} {'Species':>20s} {'Concept A':>25s} {'Concept B':>25s}")
    print(f"  {'─'*5} {'─'*10} {'─'*8} {'─'*20} {'─'*25} {'─'*25}")
    for p in predictions_inter[:15]:
        sp_str = f"S{p['species_a']}({p['species_a_name'][:6]})×S{p['species_b']}({p['species_b_name'][:6]})"
        print(f"  {p['rank']:5d} {p['p4_score']:10.4f} {p['z_score']:+8.1f} "
              f"{sp_str:>20s} {p['concept_a_name'][:25]:>25s} {p['concept_b_name'][:25]}")

    # === Score against ground truth ===
    print(f"\n[B7] Scoring inter-species predictions against ground truth...")

    # Build lookup
    inter_pred_lookup = {}
    inter_p4_scores = []
    for p in predictions_inter:
        idx_pair = sorted([p["concept_a_idx"], p["concept_b_idx"]])
        key = f"{idx_pair[0]}|{idx_pair[1]}"
        inter_pred_lookup[key] = {
            "rank": p["rank"],
            "p4_score": p["p4_score"],
        }
        inter_p4_scores.append(p["p4_score"])
    inter_p4_scores = np.array(inter_p4_scores)

    # Also reload original V1 predictions for comparison
    v1_pred_lookup = {}
    v1_p4_scores = []
    for p in pred_v1["predictions"]:
        idx_pair = sorted([p["concept_a_idx"], p["concept_b_idx"]])
        key = f"{idx_pair[0]}|{idx_pair[1]}"
        v1_pred_lookup[key] = {
            "rank": p["rank"],
            "p4_score": p["p4_score"],
        }
        v1_p4_scores.append(p["p4_score"])
    v1_p4_scores = np.array(v1_p4_scores)

    # Recompute P4 for GT pairs not found in predictions
    def compute_p4_single(idx_a, idx_b):
        lo, hi = min(idx_a, idx_b), max(idx_a, idx_b)
        cooc = mat[lo, hi]
        ar = activity[idx_a]
        ab = activity[idx_b]
        if ar == 0 or ab == 0:
            return 0.0
        E = ar * ab / total_works_sum
        p_a = ar / total_works_sum
        p_b = ab / total_works_sum
        std_val = max(1.0, np.sqrt(E * (1 - p_a) * (1 - p_b)))
        z_val = (cooc - E) / std_val
        ar_n = max(0, min(1, (ar - act_min) / (act_max - act_min)))
        ab_n = max(0, min(1, (ab - act_min) / (act_max - act_min)))
        gap_val = 1.0 - cooc / cooc_max if cooc_max > 0 else 1.0
        return ar_n * ab_n * gap_val * abs(z_val)

    # Score each GT pair
    gt_scores_inter = []
    gt_scores_v1 = []
    full_results = []

    for gt in gt_list:
        idx_a = gt["concept_a_idx"]
        idx_b = gt["concept_b_idx"]
        idx_pair = sorted([idx_a, idx_b])
        key = f"{idx_pair[0]}|{idx_pair[1]}"
        sp_a = species_by_idx.get(idx_a, -1)
        sp_b = species_by_idx.get(idx_b, -1)
        is_inter = sp_a != sp_b and sp_a >= 0 and sp_b >= 0

        # V1 rank & score
        if key in v1_pred_lookup:
            v1_rank = v1_pred_lookup[key]["rank"]
            v1_p4 = v1_pred_lookup[key]["p4_score"]
        else:
            v1_p4 = compute_p4_single(idx_a, idx_b)
            higher = int(np.sum(v1_p4_scores > v1_p4))
            v1_rank = higher + 1
            if v1_rank > TOP_K:
                v1_rank = TOP_K + 1

        # Inter rank & score
        if not is_inter:
            # Intra-species GT pair — excluded by filter
            inter_rank = -1  # N/A
            inter_p4 = v1_p4  # same P4 (no bonus), but excluded
        elif key in inter_pred_lookup:
            inter_rank = inter_pred_lookup[key]["rank"]
            inter_p4 = inter_pred_lookup[key]["p4_score"]
        else:
            inter_p4 = compute_p4_single(idx_a, idx_b)
            higher = int(np.sum(inter_p4_scores > inter_p4))
            inter_rank = higher + 1
            if inter_rank > TOP_K:
                inter_rank = TOP_K + 1

        gt_scores_inter.append(inter_p4)
        gt_scores_v1.append(v1_p4)

        full_results.append({
            "name": gt["name"],
            "concept_a": gt["concept_a_name"],
            "concept_b": gt["concept_b_name"],
            "species_a": sp_a,
            "species_b": sp_b,
            "species_a_name": species_names.get(sp_a, "?"),
            "species_b_name": species_names.get(sp_b, "?"),
            "is_inter_species": is_inter,
            "v1_rank": v1_rank,
            "v1_p4": round(v1_p4, 10),
            "inter_rank": inter_rank,
            "inter_p4": round(inter_p4, 10),
            "rank_improvement": v1_rank - inter_rank if inter_rank > 0 and inter_rank <= TOP_K else None,
        })

    # Print full results table
    print(f"\n  {'Breakthrough':<25s} {'V1 rank':>8s} {'Inter rank':>10s} {'Improve':>8s} {'Type':>5s} {'Species bridge':>25s}")
    print(f"  {'─'*25} {'─'*8} {'─'*10} {'─'*8} {'─'*5} {'─'*25}")
    for r in full_results:
        v1_str = f"{r['v1_rank']:,}" if r['v1_rank'] <= TOP_K else ">10K"
        if r['inter_rank'] == -1:
            inter_str = "EXCL"
        elif r['inter_rank'] <= TOP_K:
            inter_str = f"{r['inter_rank']:,}"
        else:
            inter_str = ">10K"
        imp = r['rank_improvement']
        imp_str = f"+{imp:,}" if imp is not None and imp > 0 else "—"
        type_str = "INTER" if r['is_inter_species'] else "INTRA"
        sp_str = f"S{r['species_a']}×S{r['species_b']}"
        print(f"  {r['name']:<25s} {v1_str:>8s} {inter_str:>10s} {imp_str:>8s} {type_str:>5s} {sp_str:>25s}")

    # Recall metrics comparison
    n_gt = len(gt_list)
    n_gt_inter = sum(1 for r in full_results if r['is_inter_species'])

    print(f"\n  Ground truth: {n_gt} total, {n_gt_inter} inter-species, {n_gt - n_gt_inter} intra-species")

    print(f"\n  {'Metric':<20s} {'V1 (all pairs)':>15s} {'Inter-only':>15s} {'Delta':>10s}")
    print(f"  {'─'*20} {'─'*15} {'─'*15} {'─'*10}")

    for cutoff in [100, 500, 1000, 5000, 10000]:
        v1_hits = sum(1 for r in full_results if r['v1_rank'] <= cutoff)
        inter_hits = sum(1 for r in full_results
                         if r['inter_rank'] > 0 and r['inter_rank'] <= cutoff)
        v1_recall = v1_hits / n_gt
        inter_recall = inter_hits / n_gt
        delta = inter_recall - v1_recall
        delta_str = f"{delta:+.0%}" if delta != 0 else "="
        print(f"  {'Recall@'+str(cutoff):<20s} {v1_recall:>14.0%} {inter_recall:>14.0%} {delta_str:>10s}")

    # Precision comparison (hits per N examined)
    print(f"\n  {'Metric':<20s} {'V1 precision':>15s} {'Inter precision':>15s} {'Improvement':>12s}")
    print(f"  {'─'*20} {'─'*15} {'─'*15} {'─'*12}")
    for cutoff in [100, 500, 1000, 5000, 10000]:
        v1_hits = sum(1 for r in full_results if r['v1_rank'] <= cutoff)
        inter_hits = sum(1 for r in full_results
                         if r['inter_rank'] > 0 and r['inter_rank'] <= cutoff)
        v1_prec = v1_hits / cutoff * 100
        inter_prec = inter_hits / cutoff * 100
        if v1_prec > 0:
            imp = (inter_prec - v1_prec) / v1_prec * 100
            imp_str = f"{imp:+.0f}%"
        else:
            imp_str = "N/A" if inter_prec == 0 else "+inf"
        print(f"  {'Prec@'+str(cutoff):<20s} {v1_prec:>14.4f}% {inter_prec:>14.4f}% {imp_str:>12s}")

    # === Mann-Whitney U test: inter-only ===
    print(f"\n[B8] Mann-Whitney U test (inter-species predictions vs random)...")

    # Sample random INTER-SPECIES pairs from sparse matrix
    rng = np.random.RandomState(42)
    n_random = 2000

    # We need random inter-species pairs from the matrix
    # Reload CSR for random sampling
    mat_csr = load_npz(os.path.join(BASE, "snapshot_2015_65k.npz"))
    random_inter_p4 = []
    attempts = 0
    while len(random_inter_p4) < n_random and attempts < n_random * 10:
        flat_idx = rng.randint(0, mat_csr.nnz)
        row = int(np.searchsorted(mat_csr.indptr, flat_idx, side='right') - 1)
        col = int(mat_csr.indices[flat_idx])
        sp_row = species_map[row]
        sp_col = species_map[col]
        attempts += 1
        if sp_row >= 0 and sp_col >= 0 and sp_row != sp_col:
            p4 = compute_p4_single(row, col)
            random_inter_p4.append(p4)
    del mat_csr
    gc.collect()

    random_inter_p4 = np.array(random_inter_p4)
    gt_p4_array = np.array(gt_scores_inter)

    # Only use inter-species GT for the test
    gt_inter_mask = [r['is_inter_species'] for r in full_results]
    gt_inter_p4 = gt_p4_array[gt_inter_mask]

    if len(gt_inter_p4) > 0 and len(random_inter_p4) > 0:
        U, p_val = mannwhitneyu(gt_inter_p4, random_inter_p4, alternative='greater')
        n1, n2 = len(gt_inter_p4), len(random_inter_p4)
        effect_r = 1 - 2 * U / (n1 * n2)
        pooled_std = np.sqrt(
            (np.var(gt_inter_p4) * (n1 - 1) + np.var(random_inter_p4) * (n2 - 1))
            / (n1 + n2 - 2)
        ) if (n1 + n2 > 2) else 1
        cohens_d = (np.mean(gt_inter_p4) - np.mean(random_inter_p4)) / pooled_std if pooled_std > 0 else 0
    else:
        U, p_val, effect_r, cohens_d = 0, 1, 0, 0

    print(f"  GT inter-species P4:    n={len(gt_inter_p4)}, mean={float(np.mean(gt_inter_p4)):.6f}")
    print(f"  Random inter-species P4: n={len(random_inter_p4)}, mean={float(np.mean(random_inter_p4)):.6f}")
    print(f"  Mann-Whitney U: {U:.0f}")
    print(f"  p-value:        {p_val:.2e}")
    print(f"  Effect size r:  {effect_r:.4f}")
    print(f"  Cohen's d:      {cohens_d:.4f}")

    # === Species collision matrix for top 1000 inter-species ===
    print(f"\n[B9] Species collision matrix (top 1000 inter-species):")
    collision_matrix = np.zeros((9, 9), dtype=int)
    for p in predictions_inter[:1000]:
        sa, sb = p["species_a"], p["species_b"]
        collision_matrix[sa][sb] += 1
        collision_matrix[sb][sa] += 1

    print(f"\n  {'':>15s}", end="")
    for i in range(9):
        print(f" S{i:1d}({species_names[i][:4]:4s})", end="")
    print()
    for i in range(9):
        print(f"  S{i}({species_names[i][:10]:10s})", end="")
        for j in range(9):
            v = collision_matrix[i][j]
            if i == j:
                print(f" {'—':>10s}", end="")
            elif v > 0:
                print(f" {v:>10d}", end="")
            else:
                print(f" {'.':>10s}", end="")
        print()

    # Top collision zones
    zones = []
    for i in range(9):
        for j in range(i+1, 9):
            if collision_matrix[i][j] > 0:
                zones.append({
                    "species_a": i,
                    "species_b": j,
                    "species_a_name": species_names[i],
                    "species_b_name": species_names[j],
                    "count": int(collision_matrix[i][j]),
                })
    zones.sort(key=lambda x: -x["count"])

    print(f"\n  Top 10 collision zones:")
    for z in zones[:10]:
        print(f"    S{z['species_a']}({z['species_a_name']}) × S{z['species_b']}({z['species_b_name']}): "
              f"{z['count']} pairs")

    # === Save complete analysis ===
    total_time = time.time() - t0

    analysis = {
        "meta": {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "theory": "P4 inter-species bridges predict discoveries",
            "method": "P4 baseline filtered to inter-species pairs only",
            "cutoff_year": 2015,
            "n_total_pairs": n_pairs,
            "n_inter_species_pairs": n_inter_total,
            "n_intra_removed": n_intra_total,
            "inter_fraction": round(n_inter_total / n_pairs, 4),
            "n_ground_truth": n_gt,
            "n_ground_truth_inter": n_gt_inter,
            "computation_time_sec": round(total_time, 1),
        },
        "ground_truth_species": full_results,
        "scoring": {
            "v1_baseline": {
                "recall_100": sum(1 for r in full_results if r['v1_rank'] <= 100) / n_gt,
                "recall_1000": sum(1 for r in full_results if r['v1_rank'] <= 1000) / n_gt,
                "recall_5000": sum(1 for r in full_results if r['v1_rank'] <= 5000) / n_gt,
                "recall_10000": sum(1 for r in full_results if r['v1_rank'] <= 10000) / n_gt,
            },
            "inter_species_filter": {
                "recall_100": sum(1 for r in full_results if r['inter_rank'] > 0 and r['inter_rank'] <= 100) / n_gt,
                "recall_1000": sum(1 for r in full_results if r['inter_rank'] > 0 and r['inter_rank'] <= 1000) / n_gt,
                "recall_5000": sum(1 for r in full_results if r['inter_rank'] > 0 and r['inter_rank'] <= 5000) / n_gt,
                "recall_10000": sum(1 for r in full_results if r['inter_rank'] > 0 and r['inter_rank'] <= 10000) / n_gt,
            },
            "mann_whitney_inter": {
                "U": float(U),
                "p_value": float(p_val),
                "effect_size_r": round(float(effect_r), 4),
                "cohens_d": round(float(cohens_d), 4),
                "n_gt_inter": len(gt_inter_p4),
                "n_random_inter": len(random_inter_p4),
                "gt_mean_p4": round(float(np.mean(gt_inter_p4)), 8) if len(gt_inter_p4) > 0 else 0,
                "random_mean_p4": round(float(np.mean(random_inter_p4)), 8),
            },
        },
        "collision_matrix": collision_matrix.tolist(),
        "top_collision_zones": zones[:20],
        "verdict": "",  # filled below
    }

    # Verdict
    v1_recall_10k = analysis["scoring"]["v1_baseline"]["recall_10000"]
    inter_recall_10k = analysis["scoring"]["inter_species_filter"]["recall_10000"]
    verdicts = []
    if inter_recall_10k >= v1_recall_10k:
        verdicts.append(f"Inter-species filter MAINTAINS recall@10K ({inter_recall_10k:.0%} vs {v1_recall_10k:.0%})")
    else:
        verdicts.append(f"Inter-species filter LOSES recall@10K ({inter_recall_10k:.0%} vs {v1_recall_10k:.0%})")

    if n_gt_inter == n_gt:
        verdicts.append(f"ALL {n_gt} ground truth breakthroughs are INTER-SPECIES")
    else:
        verdicts.append(f"{n_gt_inter}/{n_gt} GT are inter-species, {n_gt - n_gt_inter} INTRA lost")

    if p_val < 0.001:
        verdicts.append(f"STRONG SIGNAL (p={p_val:.2e}, d={cohens_d:.2f})")
    elif p_val < 0.05:
        verdicts.append(f"SIGNAL (p={p_val:.4f})")
    else:
        verdicts.append(f"NO SIGNAL (p={p_val:.4f})")

    verdict_str = " | ".join(verdicts)
    analysis["verdict"] = verdict_str

    out_path = os.path.join(BASE, "inter_species_analysis.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # ============================================================
    # FINAL SUMMARY
    # ============================================================
    print(f"\n\n{'=' * 60}")
    print("STEP 7 — FINAL VERDICT")
    print("=" * 60)
    print(f"\n  {verdict_str}")
    print(f"\n  Total pairs:        {n_pairs:,}")
    print(f"  Inter-species:      {n_inter_total:,} ({100*n_inter_total/n_pairs:.1f}%)")
    print(f"  Intra removed:      {n_intra_total:,}")
    print(f"  GT inter-species:   {n_gt_inter}/{n_gt}")
    print(f"  Mann-Whitney p:     {p_val:.2e}")
    print(f"  Cohen's d:          {cohens_d:.2f}")
    print(f"\n  Saved: {out_path}")
    print(f"  Saved: {inter_path}")
    print(f"\n  Time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print("=" * 60)


if __name__ == "__main__":
    main()
