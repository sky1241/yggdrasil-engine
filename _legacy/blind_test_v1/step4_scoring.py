"""
ÉTAPE 4 — Scoring: comparer prédictions P4 vs vérité terrain
=============================================================
Input:  blind_test/p4_predictions_2015.json
        blind_test/ground_truth.json
Output: blind_test/scoring_results.json

Métriques:
- Recall@100: sur 12 percées, combien ont leur paire dans le top 100 P4?
- Precision@50: sur les top 50 P4, combien matchent une vraie percée?
- Rang moyen: les percées réelles sont classées à quel rang moyen?
"""

import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_FILE = os.path.join(BASE, "p4_predictions_2015.json")
GT_FILE = os.path.join(BASE, "ground_truth.json")
OUTPUT = os.path.join(BASE, "scoring_results.json")

print("=" * 60)
print("ÉTAPE 4 — Scoring")
print("=" * 60)

with open(PRED_FILE, "r", encoding="utf-8") as f:
    pred = json.load(f)

with open(GT_FILE, "r", encoding="utf-8") as f:
    gt = json.load(f)

all_pairs = pred["all_pairs"]
breakthroughs = gt["breakthroughs"]

# Build lookup: pair_key → rank (1-indexed)
pair_to_rank = {}
for rank, p in enumerate(all_pairs, 1):
    # Normalize pair key (both orderings)
    k1 = f"{p['concept_a']}|{p['concept_b']}"
    k2 = f"{p['concept_b']}|{p['concept_a']}"
    pair_to_rank[k1] = rank
    pair_to_rank[k2] = rank

n_total = len(all_pairs)
print(f"  {n_total} pairs ranked by P4 score")
print(f"  {len(breakthroughs)} breakthroughs to evaluate")

# ══════════════════════════════════════════════════════════
# Match each breakthrough to its rank
# ══════════════════════════════════════════════════════════
print(f"\n  {'Breakthrough':<25s} {'Rank':>6s}  {'P4 Score':>10s}  {'Status':<12s}")
print(f"  {'─'*25} {'─'*6}  {'─'*10}  {'─'*12}")

results = []
for bt in breakthroughs:
    if not bt["matched"]:
        results.append({**bt, "rank": None, "p4_score": None, "in_top100": False, "in_top50": False})
        print(f"  {bt['breakthrough']:<25s} {'N/A':>6s}  {'N/A':>10s}  NOT MATCHED")
        continue

    pk = bt["pair_key"]
    rank = pair_to_rank.get(pk)

    if rank is None:
        # Try reversed
        parts = pk.split("|")
        pk_rev = f"{parts[1]}|{parts[0]}"
        rank = pair_to_rank.get(pk_rev)

    if rank is not None:
        p4 = all_pairs[rank - 1]["p4_score"]
        in100 = rank <= 100
        in50 = rank <= 50
        status = f"TOP {rank}" if in100 else f"rank {rank}"
        results.append({**bt, "rank": rank, "p4_score": p4, "in_top100": in100, "in_top50": in50})
        print(f"  {bt['breakthrough']:<25s} {rank:6d}  {p4:10.4f}  {status}")
    else:
        results.append({**bt, "rank": None, "p4_score": None, "in_top100": False, "in_top50": False})
        print(f"  {bt['breakthrough']:<25s} {'???':>6s}  {'???':>10s}  PAIR NOT FOUND")

# ══════════════════════════════════════════════════════════
# Compute metrics
# ══════════════════════════════════════════════════════════
print()

matched_bts = [r for r in results if r["rank"] is not None]
n_matched = len(matched_bts)

# Recall@100
in_top100 = sum(1 for r in matched_bts if r["in_top100"])
recall_100 = in_top100 / len(breakthroughs) if breakthroughs else 0

# Precision@50
gt_pairs = set()
for bt in breakthroughs:
    if bt["matched"] and bt["pair_key"]:
        pk = bt["pair_key"]
        gt_pairs.add(pk)
        parts = pk.split("|")
        gt_pairs.add(f"{parts[1]}|{parts[0]}")

hits_top50 = 0
for p in all_pairs[:50]:
    k1 = f"{p['concept_a']}|{p['concept_b']}"
    k2 = f"{p['concept_b']}|{p['concept_a']}"
    if k1 in gt_pairs or k2 in gt_pairs:
        hits_top50 += 1

precision_50 = hits_top50 / 50

# Mean rank
ranks = [r["rank"] for r in matched_bts]
mean_rank = sum(ranks) / len(ranks) if ranks else float("inf")
median_rank = sorted(ranks)[len(ranks) // 2] if ranks else float("inf")

print(f"  RECALL@100:    {in_top100}/{len(breakthroughs)} = {recall_100:.1%}")
print(f"  PRECISION@50:  {hits_top50}/50 = {precision_50:.1%}")
print(f"  MEAN RANK:     {mean_rank:.1f} / {n_total}")
print(f"  MEDIAN RANK:   {median_rank} / {n_total}")

# ══════════════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════════════
output = {
    "meta": {
        "date": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "n_breakthroughs": len(breakthroughs),
        "n_matched_to_pairs": n_matched,
        "n_total_pairs": n_total,
    },
    "metrics": {
        "recall_at_100": round(recall_100, 4),
        "precision_at_50": round(precision_50, 4),
        "mean_rank": round(mean_rank, 1),
        "median_rank": median_rank,
        "hits_in_top100": in_top100,
        "hits_in_top50": hits_top50,
    },
    "breakthrough_results": results,
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n  → {OUTPUT}")
print("ÉTAPE 4 TERMINÉE.")
