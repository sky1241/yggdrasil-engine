#!/usr/bin/env python3
"""
Predictions 2025 — Step 5: Collision Matrix
============================================
Which scientific continents will interact most?

Input:
  predictions_2025/p4_predictions_INTER.json
  predictions_2025/species_full.json

Output:
  predictions_2025/collision_matrix_full.json
"""
import json
import os
import time
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
K = 9


def main():
    print("Predictions 2025 — Step 5: Collision Matrix")
    print("=" * 60)

    # Load
    with open(os.path.join(BASE, "p4_predictions_INTER.json"), 'r', encoding='utf-8') as f:
        inter_data = json.load(f)
    with open(os.path.join(BASE, "species_full.json"), 'r', encoding='utf-8') as f:
        species_data = json.load(f)

    predictions = inter_data["predictions"]

    # Build species names from top concepts
    species_tops = {}
    for url, info in species_data["concepts"].items():
        sp = info["species"]
        deg = info.get("degree", 0)
        if sp not in species_tops:
            species_tops[sp] = []
        species_tops[sp].append((info["name"], deg, info["level"]))

    species_names = {}
    for sp, entries in species_tops.items():
        entries.sort(key=lambda x: -x[1])
        top = [e[0] for e in entries if e[2] <= 1][:2]
        if not top:
            top = [e[0] for e in entries[:2]]
        species_names[sp] = "/".join(top)

    # Build matrix for top 1000
    matrix_1000 = np.zeros((K, K), dtype=int)
    for p in predictions[:1000]:
        sa, sb = p["species_a"], p["species_b"]
        if 0 <= sa < K and 0 <= sb < K:
            lo, hi = min(sa, sb), max(sa, sb)
            matrix_1000[lo, hi] += 1

    # Build matrix for top 100
    matrix_100 = np.zeros((K, K), dtype=int)
    for p in predictions[:100]:
        sa, sb = p["species_a"], p["species_b"]
        if 0 <= sa < K and 0 <= sb < K:
            lo, hi = min(sa, sb), max(sa, sb)
            matrix_100[lo, hi] += 1

    # Build cumulative P4 by species pair (top 1000)
    matrix_p4_sum = np.zeros((K, K), dtype=np.float64)
    for p in predictions[:1000]:
        sa, sb = p["species_a"], p["species_b"]
        if 0 <= sa < K and 0 <= sb < K:
            lo, hi = min(sa, sb), max(sa, sb)
            matrix_p4_sum[lo, hi] += p["p4_score"]

    # Display
    print(f"\n--- Collision matrix (top 1000 inter-species predictions) ---\n")
    header = f"{'':>18s}"
    for j in range(K):
        sn = species_names.get(j, f"S{j}")[:8]
        header += f" S{j}({sn:6s})"
    print(header)

    for i in range(K):
        sn = species_names.get(i, f"S{i}")[:12]
        row = f"  S{i}({sn:12s})"
        for j in range(K):
            lo, hi = min(i, j), max(i, j)
            v = matrix_1000[lo, hi]
            if i == j:
                row += f" {'—':>10s}"
            elif v > 0:
                row += f" {v:>10d}"
            else:
                row += f" {'.':>10s}"
        print(row)

    # Collision zones
    zones = []
    for i in range(K):
        for j in range(i + 1, K):
            if matrix_1000[i, j] > 0:
                zones.append({
                    "species_a": i,
                    "species_b": j,
                    "species_a_name": species_names.get(i, f"S{i}"),
                    "species_b_name": species_names.get(j, f"S{j}"),
                    "count_top1000": int(matrix_1000[i, j]),
                    "count_top100": int(matrix_100[i, j]),
                    "p4_sum_top1000": round(float(matrix_p4_sum[i, j]), 2),
                })
    zones.sort(key=lambda x: -x["count_top1000"])

    print(f"\n--- Top 15 collision zones (future interactions) ---")
    print(f"  {'Species bridge':<40s} {'Top 100':>8s} {'Top 1000':>9s} {'P4 sum':>10s}")
    print(f"  {'─'*40} {'─'*8} {'─'*9} {'─'*10}")
    for z in zones[:15]:
        bridge = f"S{z['species_a']}({z['species_a_name'][:15]}) × S{z['species_b']}({z['species_b_name'][:15]})"
        print(f"  {bridge:<40s} {z['count_top100']:>8d} {z['count_top1000']:>9d} {z['p4_sum_top1000']:>10.1f}")

    # Save
    output = {
        "meta": {
            "k": K,
            "species_names": species_names,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "matrix_top1000": matrix_1000.tolist(),
        "matrix_top100": matrix_100.tolist(),
        "matrix_p4_sum_top1000": matrix_p4_sum.tolist(),
        "collision_zones": zones,
    }

    out_path = os.path.join(BASE, "collision_matrix_full.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")
    print("Step 5 DONE")


if __name__ == "__main__":
    main()
