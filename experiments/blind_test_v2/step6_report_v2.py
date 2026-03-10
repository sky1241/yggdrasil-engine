#!/usr/bin/env python3
"""
Blind Test V2 — Step 6: Final Report
======================================
Compiles all results into FINAL_REPORT_V2.json.

Input:
  blind_test_v2/meta_2015.json
  blind_test_v2/scoring_results_v2.json
  blind_test_v2/ground_truth_v2.json
  blind_test_v2/species_matrix.json
  blind_test_v2/p4_predictions_v1.json
  blind_test_v2/p4_predictions_v2.json

Output:
  blind_test_v2/FINAL_REPORT_V2.json
"""
import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))


def load_json(filename):
    path = os.path.join(BASE, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print("Blind Test V2 — Step 6: Final Report")
    print("=" * 60)

    # Load all results
    meta = load_json("meta_2015.json")
    scoring = load_json("scoring_results_v2.json")
    ground_truth = load_json("ground_truth_v2.json")
    species_matrix = load_json("species_matrix.json")
    pred_v1 = load_json("p4_predictions_v1.json")
    pred_v2 = load_json("p4_predictions_v2.json")

    v1 = scoring["v1_baseline"]
    v2 = scoring["v2_species"]

    # Build verdict
    verdicts = []

    # Signal detection
    if v1["p_value"] < 0.001:
        verdicts.append(f"SIGNAL DETECTED (V1 p={v1['p_value']:.6f})")
    elif v1["p_value"] < 0.05:
        verdicts.append(f"WEAK SIGNAL (V1 p={v1['p_value']:.4f})")
    else:
        verdicts.append(f"NO SIGNAL (V1 p={v1['p_value']:.4f})")

    # Species bonus effect
    delta = scoring["comparison"]["delta_recall_100"]
    if delta > 0:
        verdicts.append(f"Species bonus IMPROVES recall@100 by {delta:+.0%}")
    elif delta < 0:
        verdicts.append(f"Species bonus WORSENS recall@100 by {delta:+.0%}")
    else:
        verdicts.append("Species bonus has NO EFFECT on recall@100")

    # Scale comparison with V1
    verdicts.append(f"Scale: 65K concepts (vs 100 in V1)")

    verdict_str = " | ".join(verdicts)

    # Compile report
    report = {
        "meta": {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": "P4 structural holes (Uzzi z-score)",
            "n_concepts": meta["n_concepts"],
            "n_active_concepts": meta["n_active_concepts"],
            "n_pairs_scored": pred_v1["meta"]["n_pairs_scored"],
            "cutoff_year": 2015,
            "total_works_2015": meta["total_works_2015"],
            "scan_chunks": meta["n_chunks_scanned"],
            "species_source": "spectral clustering K=9 on 2015 data ONLY (no look-ahead)",
            "scan_time_sec": meta["scan_time_sec"],
        },
        "comparison": {
            "v1_baseline": {
                "recall_100": v1["recall_100"],
                "recall_1000": v1["recall_1000"],
                "recall_10000": v1["recall_10000"],
                "median_rank": v1["median_rank"],
                "mean_rank": v1["mean_rank"],
                "p_value": v1["p_value"],
                "effect_size_r": v1["effect_size_r"],
                "cohens_d": v1["cohens_d"],
                "mann_whitney_U": v1["mann_whitney_U"],
            },
            "v2_species": {
                "recall_100": v2["recall_100"],
                "recall_1000": v2["recall_1000"],
                "recall_10000": v2["recall_10000"],
                "median_rank": v2["median_rank"],
                "mean_rank": v2["mean_rank"],
                "p_value": v2["p_value"],
                "effect_size_r": v2["effect_size_r"],
                "cohens_d": v2["cohens_d"],
                "mann_whitney_U": v2["mann_whitney_U"],
            },
        },
        "ground_truth": ground_truth["breakthroughs"],
        "predictions_top1000_v1": pred_v1["predictions"][:1000],
        "predictions_top1000_v2": pred_v2["predictions"][:1000],
        "species_matrix_p4": species_matrix["matrix_p4_top1000"],
        "species_collision_zones": species_matrix["collision_zones"][:20],
        "verdict": verdict_str,
    }

    # Save
    output_path = os.path.join(BASE, "FINAL_REPORT_V2.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    sz = os.path.getsize(output_path)

    # Print summary
    print()
    print("=" * 60)
    print("BLIND TEST V2 — FINAL REPORT")
    print("=" * 60)
    print()
    print(f"  Concepts:     {meta['n_concepts']:,} total, "
          f"{meta['n_active_concepts']:,} active <=2015")
    print(f"  Pairs scored: {pred_v1['meta']['n_pairs_scored']:,}")
    print(f"  Ground truth: {ground_truth['meta']['n_matched']} matched breakthroughs")
    print()
    print(f"  {'Metric':<20s} {'V1 (baseline)':>15s} {'V2 (species)':>15s}")
    print(f"  {'─'*20} {'─'*15} {'─'*15}")
    print(f"  {'Recall@100':<20s} {v1['recall_100']:>14.1%} {v2['recall_100']:>14.1%}")
    print(f"  {'Recall@1000':<20s} {v1['recall_1000']:>14.1%} {v2['recall_1000']:>14.1%}")
    print(f"  {'Recall@10000':<20s} {v1['recall_10000']:>14.1%} {v2['recall_10000']:>14.1%}")
    print(f"  {'Median rank':<20s} {v1['median_rank']:>15,.0f} {v2['median_rank']:>15,.0f}")
    print(f"  {'p-value':<20s} {v1['p_value']:>15.6f} {v2['p_value']:>15.6f}")
    print(f"  {'Effect (r)':<20s} {v1['effect_size_r']:>15.4f} {v2['effect_size_r']:>15.4f}")
    print(f"  {'Cohens d':<20s} {v1['cohens_d']:>15.4f} {v2['cohens_d']:>15.4f}")
    print()
    print(f"  VERDICT: {verdict_str}")
    print()
    print(f"  Saved: {output_path} ({sz/1024:.0f} KB)")
    print()
    print("=" * 60)
    print("BLIND TEST V2 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
