#!/usr/bin/env python3
"""
Blind Test V2 — Step 5: Species Interaction Matrix
====================================================
Builds a 9×9 matrix counting how many top-1000 P4 pairs
bridge each pair of species. Highlights "continental collision zones."

Input:
  blind_test_v2/p4_predictions_v2.json
  blind_test_v2/species_2015.json
  blind_test_v2/ground_truth_v2.json

Output:
  blind_test_v2/species_matrix.json
"""
import json
import os
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
K = 9  # number of species

# Species names from the prompt
SPECIES_NAMES = {
    0: "ChiMat",
    1: "TerGeo",
    2: "BioCli",
    3: "HumEco",
    4: "InfMat",
    5: "TerBio",
    6: "HumArt",
    7: "BioLab",
    8: "Physiq",
}


def main():
    print("Blind Test V2 — Step 5: Species Interaction Matrix")
    print("=" * 60)

    # Load predictions V2
    with open(os.path.join(BASE, "p4_predictions_v2.json"), 'r', encoding='utf-8') as f:
        pred = json.load(f)
    predictions = pred["predictions"]
    print(f"Predictions loaded: {len(predictions):,}")

    # Load ground truth
    with open(os.path.join(BASE, "ground_truth_v2.json"), 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    matched_gt = [g for g in gt_data["breakthroughs"] if g.get("matched")]

    # Build ground truth idx_key set
    gt_keys = set()
    for g in matched_gt:
        gt_keys.add(g["idx_key"])

    # === Matrix from top 1000 predictions ===
    top_1000 = predictions[:1000]
    matrix_p4 = np.zeros((K, K), dtype=int)
    matrix_gt = np.zeros((K, K), dtype=int)  # ground truth hits

    for p in top_1000:
        sa = p["species_a"]
        sb = p["species_b"]
        if 0 <= sa < K and 0 <= sb < K:
            lo, hi = min(sa, sb), max(sa, sb)
            matrix_p4[lo, hi] += 1

    # Check which ground truth pairs are in top 1000
    for p in top_1000:
        idx_pair = sorted([p["concept_a_idx"], p["concept_b_idx"]])
        idx_key = f"{idx_pair[0]}|{idx_pair[1]}"
        if idx_key in gt_keys:
            sa = p["species_a"]
            sb = p["species_b"]
            if 0 <= sa < K and 0 <= sb < K:
                lo, hi = min(sa, sb), max(sa, sb)
                matrix_gt[lo, hi] += 1

    # Display
    print(f"\n--- P4 top-1000 by species pair ---")
    # Note: species names might not match 2015 clusters (ordering differs)
    # We use cluster numbers; names are indicative from full-data analysis
    header = "        " + "".join(f"  S{i:d}    " for i in range(K))
    print(header)
    for i in range(K):
        row = f"  S{i:d}  "
        for j in range(K):
            val = matrix_p4[min(i,j), max(i,j)] if i != j else matrix_p4[i, i]
            if val > 0:
                row += f" {val:5d}  "
            else:
                row += "     .  "
        print(row)

    # Inter vs intra species
    intra = sum(matrix_p4[i, i] for i in range(K))
    inter = matrix_p4.sum() - intra
    print(f"\n  Intra-species: {intra:,} ({100*intra/1000:.1f}%)")
    print(f"  Inter-species: {inter:,} ({100*inter/1000:.1f}%)")

    # Top collision zones
    print(f"\n--- Top 10 collision zones (inter-species) ---")
    zones = []
    for i in range(K):
        for j in range(i + 1, K):
            if matrix_p4[i, j] > 0:
                zones.append((matrix_p4[i, j], i, j, matrix_gt[i, j]))
    zones.sort(reverse=True)

    for count, i, j, gt_count in zones[:10]:
        gt_str = f" ({gt_count} GT hits)" if gt_count > 0 else ""
        print(f"  S{i} × S{j}: {count:4d} pairs in top 1000{gt_str}")

    # Ground truth in matrix
    if matrix_gt.sum() > 0:
        print(f"\n--- Ground truth hits in top 1000 by species pair ---")
        for i in range(K):
            for j in range(i, K):
                if matrix_gt[i, j] > 0:
                    print(f"  S{i} × S{j}: {matrix_gt[i, j]} breakthroughs")

    # Save
    output_path = os.path.join(BASE, "species_matrix.json")
    result = {
        "meta": {
            "k": K,
            "top_n": 1000,
            "species_source": "species_2015.json (NO look-ahead)",
            "note": "Species numbers from 2015 clustering may differ from full-data labels",
            "timestamp": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        },
        "matrix_p4_top1000": matrix_p4.tolist(),
        "matrix_gt_top1000": matrix_gt.tolist(),
        "intra_species_count": int(intra),
        "inter_species_count": int(inter),
        "collision_zones": [
            {"species_a": int(i), "species_b": int(j),
             "p4_count": int(c), "gt_hits": int(g)}
            for c, i, j, g in zones
        ],
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"\nSaved: {output_path}")
    print("STEP 5 DONE")


if __name__ == "__main__":
    main()
