#!/usr/bin/env python3
"""
Blind Test V2 — Step 4: Scoring
================================
Computes recall, precision, median rank, Mann-Whitney U test.
Compares V1 baseline vs V2 species-bonus predictions.

For ground truth pairs NOT in top 10K: recomputes P4 from sparse matrix.

Input:
  blind_test_v2/p4_predictions_v1.json
  blind_test_v2/p4_predictions_v2.json
  blind_test_v2/ground_truth_v2.json
  blind_test_v2/snapshot_2015_65k.npz    (for recomputing missing pairs)
  blind_test_v2/activity_2015.json
  blind_test_v2/species_2015.json

Output:
  blind_test_v2/scoring_results_v2.json
"""
import json
import os
import time
import numpy as np
from scipy.sparse import load_npz
from scipy.stats import mannwhitneyu

BASE = os.path.dirname(os.path.abspath(__file__))
N_CONCEPTS = 65026


def compute_p4_for_pair(i, j, mat, activity, total_works_sum, act_min, act_max,
                        cooc_max, species_map=None):
    """Compute P4 score for a single pair (i, j)."""
    # Get co-occurrence (matrix is upper triangular)
    lo, hi = min(i, j), max(i, j)
    cooc = mat[lo, hi]

    act_a = activity[i]
    act_b = activity[j]

    if act_a == 0 or act_b == 0:
        return {"p4_v1": 0, "p4_v2": 0, "z": 0, "cooc": float(cooc)}

    # Z-score
    E = act_a * act_b / total_works_sum
    p_a = act_a / total_works_sum
    p_b = act_b / total_works_sum
    std = max(1.0, np.sqrt(E * (1 - p_a) * (1 - p_b)))
    z = (cooc - E) / std

    # Normalized activity
    act_a_norm = max(0, min(1, (act_a - act_min) / (act_max - act_min)))
    act_b_norm = max(0, min(1, (act_b - act_min) / (act_max - act_min)))

    # Gap
    gap = 1.0 - cooc / cooc_max if cooc_max > 0 else 1.0

    p4_v1 = act_a_norm * act_b_norm * gap * abs(z)

    # Species bonus
    p4_v2 = p4_v1
    if species_map is not None:
        sp_a = species_map[i]
        sp_b = species_map[j]
        if sp_a >= 0 and sp_b >= 0 and sp_a != sp_b:
            p4_v2 = p4_v1 * 1.5

    return {
        "p4_v1": p4_v1,
        "p4_v2": p4_v2,
        "z": z,
        "cooc": float(cooc),
        "gap": gap,
    }


def score_version(predictions, ground_truth, version_key, mat, activity,
                  total_works_sum, act_min, act_max, cooc_max, species_map):
    """Score one version (V1 or V2) against ground truth."""
    # Build lookup: idx_key -> rank and P4 score
    pred_lookup = {}
    p4_scores_all = []
    for p in predictions:
        idx_pair = sorted([p["concept_a_idx"], p["concept_b_idx"]])
        key = f"{idx_pair[0]}|{idx_pair[1]}"
        pred_lookup[key] = {
            "rank": p["rank"],
            "p4_score": p["p4_score"],
        }
        p4_scores_all.append(p["p4_score"])

    p4_scores_all = np.array(p4_scores_all)

    # Score each ground truth pair
    gt_results = []
    gt_p4_scores = []  # for Mann-Whitney
    matched_gt = [g for g in ground_truth if g.get("matched")]

    for gt in matched_gt:
        idx_a = gt["concept_a_idx"]
        idx_b = gt["concept_b_idx"]
        idx_pair = sorted([idx_a, idx_b])
        idx_key = f"{idx_pair[0]}|{idx_pair[1]}"

        if idx_key in pred_lookup:
            rank = pred_lookup[idx_key]["rank"]
            p4 = pred_lookup[idx_key]["p4_score"]
        else:
            # Recompute P4 for this pair
            result = compute_p4_for_pair(
                idx_a, idx_b, mat, activity, total_works_sum,
                act_min, act_max, cooc_max, species_map
            )
            p4 = result[f"p4_{version_key.lower()}"]

            # Find approximate rank (count how many predictions have higher P4)
            higher = int(np.sum(p4_scores_all > p4))
            rank = higher + 1  # conservative: at least this rank
            if rank > len(predictions):
                rank = len(predictions) + 1  # beyond top K

        gt_results.append({
            "name": gt["name"],
            "year": gt["year"],
            "source": gt["source"],
            "concept_a": gt["concept_a_name"],
            "concept_b": gt["concept_b_name"],
            "rank": rank,
            "p4_score": p4,
            "in_top_100": rank <= 100,
            "in_top_1000": rank <= 1000,
            "in_top_10000": rank <= 10000,
        })
        gt_p4_scores.append(p4)

    gt_p4_scores = np.array(gt_p4_scores)
    n_matched = len(matched_gt)

    # Metrics
    recall_100 = sum(1 for g in gt_results if g["in_top_100"]) / n_matched if n_matched > 0 else 0
    recall_1000 = sum(1 for g in gt_results if g["in_top_1000"]) / n_matched if n_matched > 0 else 0
    recall_10000 = sum(1 for g in gt_results if g["in_top_10000"]) / n_matched if n_matched > 0 else 0

    precision_100 = sum(1 for g in gt_results if g["in_top_100"]) / 100
    precision_1000 = sum(1 for g in gt_results if g["in_top_1000"]) / 1000

    ranks = [g["rank"] for g in gt_results]
    median_rank = float(np.median(ranks)) if ranks else 0
    mean_rank = float(np.mean(ranks)) if ranks else 0

    # Mann-Whitney U test: ground truth P4 vs RANDOM pairs from sparse matrix
    # Sample random pairs from the sparse matrix (not the top 10K — that's biased)
    # Use CSR format directly to avoid memory-heavy COO conversion
    rng = np.random.RandomState(42)
    n_total_pairs = mat.nnz
    n_random = min(2000, n_total_pairs)
    random_flat_indices = rng.choice(n_total_pairs, size=n_random, replace=False)

    random_p4 = []
    for flat_idx in random_flat_indices:
        # Find row from CSR indptr (binary search)
        row = int(np.searchsorted(mat.indptr, flat_idx, side='right') - 1)
        col = int(mat.indices[flat_idx])
        result = compute_p4_for_pair(
            row, col, mat, activity, total_works_sum,
            act_min, act_max, cooc_max, species_map
        )
        random_p4.append(result[f"p4_{version_key.lower()}"])
    random_p4 = np.array(random_p4)

    if len(gt_p4_scores) > 0 and len(random_p4) > 0:
        U, p_value = mannwhitneyu(gt_p4_scores, random_p4, alternative='greater')
        n1, n2 = len(gt_p4_scores), len(random_p4)
        effect_r = 1 - 2 * U / (n1 * n2)
        # Cohen's d approximation
        pooled_std = np.sqrt(
            (np.var(gt_p4_scores) * (n1 - 1) + np.var(random_p4) * (n2 - 1))
            / (n1 + n2 - 2)
        ) if (n1 + n2 > 2) else 1
        cohens_d = (np.mean(gt_p4_scores) - np.mean(random_p4)) / pooled_std if pooled_std > 0 else 0
    else:
        U, p_value, effect_r, cohens_d = 0, 1, 0, 0

    return {
        "n_ground_truth": n_matched,
        "recall_100": round(recall_100, 4),
        "recall_1000": round(recall_1000, 4),
        "recall_10000": round(recall_10000, 4),
        "precision_100": round(precision_100, 6),
        "precision_1000": round(precision_1000, 6),
        "median_rank": median_rank,
        "mean_rank": round(mean_rank, 1),
        "mann_whitney_U": float(U),
        "p_value": float(p_value),
        "effect_size_r": round(float(effect_r), 4),
        "cohens_d": round(float(cohens_d), 4),
        "gt_p4_mean": round(float(np.mean(gt_p4_scores)), 8) if len(gt_p4_scores) > 0 else 0,
        "random_p4_mean": round(float(np.mean(random_p4)), 8) if len(random_p4) > 0 else 0,
        "per_breakthrough": gt_results,
    }


def main():
    t0 = time.time()
    print("Blind Test V2 — Step 4: Scoring")
    print("=" * 60)

    # Load ground truth
    with open(os.path.join(BASE, "ground_truth_v2.json"), 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    ground_truth = gt_data["breakthroughs"]
    matched_gt = [g for g in ground_truth if g.get("matched")]
    print(f"Ground truth: {len(matched_gt)} matched breakthroughs")

    # Load predictions
    with open(os.path.join(BASE, "p4_predictions_v1.json"), 'r', encoding='utf-8') as f:
        pred_v1 = json.load(f)
    with open(os.path.join(BASE, "p4_predictions_v2.json"), 'r', encoding='utf-8') as f:
        pred_v2 = json.load(f)
    print(f"Predictions V1: {len(pred_v1['predictions']):,}")
    print(f"Predictions V2: {len(pred_v2['predictions']):,}")

    # Load sparse matrix + activity for recomputing missing pairs
    print("Loading sparse matrix for pair recomputation...")
    mat = load_npz(os.path.join(BASE, "snapshot_2015_65k.npz"))
    with open(os.path.join(BASE, "activity_2015.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)

    # Load species (2015-only)
    with open(os.path.join(BASE, "species_2015.json"), 'r', encoding='utf-8') as f:
        species_data = json.load(f)

    # Build species map
    concepts_path = os.path.join(os.path.dirname(BASE), "data", "scan", "concepts_65k.json")
    with open(concepts_path, 'r', encoding='utf-8') as f:
        c65 = json.load(f)
    species_map = np.full(N_CONCEPTS, -1, dtype=np.int32)
    for url, info in species_data["concepts"].items():
        if url in c65["concepts"]:
            species_map[c65["concepts"][url]["idx"]] = info["species"]

    # Get normalization params from predictions meta
    total_works_sum = pred_v1["meta"]["total_works_sum"]
    cooc_max = pred_v1["meta"]["cooc_max"]
    active_vals = activity[activity > 0]
    act_min = float(active_vals.min()) if len(active_vals) > 0 else 0
    act_max = float(active_vals.max()) if len(active_vals) > 0 else 1

    # Score V1
    print("\n--- Scoring V1 (baseline) ---")
    results_v1 = score_version(
        pred_v1["predictions"], ground_truth, "V1",
        mat, activity, total_works_sum, act_min, act_max, cooc_max, None
    )
    print(f"  Recall@100:  {results_v1['recall_100']:.2%} "
          f"({int(results_v1['recall_100'] * results_v1['n_ground_truth'])}"
          f"/{results_v1['n_ground_truth']})")
    print(f"  Recall@1000: {results_v1['recall_1000']:.2%}")
    print(f"  Median rank: {results_v1['median_rank']:.0f}")
    print(f"  p-value:     {results_v1['p_value']:.6f}")
    print(f"  Effect (r):  {results_v1['effect_size_r']:.4f}")
    print(f"  Cohen's d:   {results_v1['cohens_d']:.4f}")

    # Score V2
    print("\n--- Scoring V2 (species bonus) ---")
    results_v2 = score_version(
        pred_v2["predictions"], ground_truth, "V2",
        mat, activity, total_works_sum, act_min, act_max, cooc_max, species_map
    )
    print(f"  Recall@100:  {results_v2['recall_100']:.2%} "
          f"({int(results_v2['recall_100'] * results_v2['n_ground_truth'])}"
          f"/{results_v2['n_ground_truth']})")
    print(f"  Recall@1000: {results_v2['recall_1000']:.2%}")
    print(f"  Median rank: {results_v2['median_rank']:.0f}")
    print(f"  p-value:     {results_v2['p_value']:.6f}")
    print(f"  Effect (r):  {results_v2['effect_size_r']:.4f}")
    print(f"  Cohen's d:   {results_v2['cohens_d']:.4f}")

    # Comparison
    print(f"\n{'=' * 60}")
    print("COMPARISON V1 vs V2:")
    print(f"  Recall@100:  V1={results_v1['recall_100']:.2%} "
          f"vs V2={results_v2['recall_100']:.2%}")
    print(f"  Recall@1000: V1={results_v1['recall_1000']:.2%} "
          f"vs V2={results_v2['recall_1000']:.2%}")
    print(f"  Median rank: V1={results_v1['median_rank']:.0f} "
          f"vs V2={results_v2['median_rank']:.0f}")
    print(f"  p-value:     V1={results_v1['p_value']:.6f} "
          f"vs V2={results_v2['p_value']:.6f}")

    delta_recall = results_v2["recall_100"] - results_v1["recall_100"]
    if delta_recall > 0:
        verdict_species = "Species bonus IMPROVES recall"
    elif delta_recall < 0:
        verdict_species = "Species bonus WORSENS recall"
    else:
        verdict_species = "Species bonus has NO EFFECT on recall"
    print(f"  Verdict: {verdict_species}")

    # Per-breakthrough detail
    print(f"\n--- Per-breakthrough ranks ---")
    print(f"  {'Breakthrough':<30s} {'V1 rank':>8s} {'V2 rank':>8s} {'Source':>6s}")
    print(f"  {'─'*30} {'─'*8} {'─'*8} {'─'*6}")
    for g1, g2 in zip(results_v1["per_breakthrough"], results_v2["per_breakthrough"]):
        r1 = f"{g1['rank']:,}" if g1['rank'] <= 10000 else ">10K"
        r2 = f"{g2['rank']:,}" if g2['rank'] <= 10000 else ">10K"
        print(f"  {g1['name']:<30s} {r1:>8s} {r2:>8s} {g1['source']:>6s}")

    # Save
    output_path = os.path.join(BASE, "scoring_results_v2.json")
    result = {
        "meta": {
            "n_ground_truth_matched": len(matched_gt),
            "n_ground_truth_total": len(ground_truth),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "v1_baseline": results_v1,
        "v2_species": results_v2,
        "comparison": {
            "delta_recall_100": round(delta_recall, 4),
            "verdict": verdict_species,
        },
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    total_time = time.time() - t0
    print(f"\nSaved: {output_path}")
    print(f"STEP 4 DONE — {total_time:.0f}s")


if __name__ == "__main__":
    main()
