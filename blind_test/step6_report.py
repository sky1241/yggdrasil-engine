"""
ÉTAPE 6 — Rapport final
========================
Agrège tous les résultats en un seul JSON propre.
"""

import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print("ÉTAPE 6 — Rapport final")
print("=" * 60)

# Load all results
with open(os.path.join(BASE, "data_2015_frozen.json"), "r", encoding="utf-8") as f:
    frozen = json.load(f)

with open(os.path.join(BASE, "p4_predictions_2015.json"), "r", encoding="utf-8") as f:
    predictions = json.load(f)

with open(os.path.join(BASE, "ground_truth.json"), "r", encoding="utf-8") as f:
    ground_truth = json.load(f)

with open(os.path.join(BASE, "scoring_results.json"), "r", encoding="utf-8") as f:
    scoring = json.load(f)

with open(os.path.join(BASE, "control_results.json"), "r", encoding="utf-8") as f:
    control = json.load(f)

metrics = scoring["metrics"]
test = control["test"]

# ══════════════════════════════════════════════════════════
# Build final report
# ══════════════════════════════════════════════════════════

# Determine verdict
recall_pass = metrics["recall_at_100"] >= 0.50
mw_pass = test["p_value_greater"] < 0.05
verdict = "PASS" if recall_pass and mw_pass else "FAIL"

reason_parts = []
if recall_pass:
    reason_parts.append(f"recall@100={metrics['recall_at_100']:.0%} >= 50%")
else:
    reason_parts.append(f"recall@100={metrics['recall_at_100']:.0%} < 50%")
if mw_pass:
    reason_parts.append(f"Mann-Whitney p={test['p_value_greater']:.4f} < 0.05")
else:
    reason_parts.append(f"Mann-Whitney p={test['p_value_greater']:.4f} >= 0.05")

verdict_str = f"{verdict}: {' ET '.join(reason_parts)}"

report = {
    "meta": {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": "semi-blind 2015->2025",
        "n_concepts": frozen["meta"]["n_concepts"],
        "n_pairs": frozen["meta"]["n_pairs"],
        "cutoff_year": 2015,
        "p4_formula": "activity_A * activity_B * (1 - cooc_norm) * |z_uzzi|",
        "null_model": "analytical independence E = N_a * N_b / N_total",
    },
    "predictions": predictions["predictions_top100"],
    "ground_truth": [
        {
            "breakthrough": bt["breakthrough"],
            "year": bt["year"],
            "concept_a": bt.get("matched_concept_a_name", "?"),
            "concept_b": bt.get("matched_concept_b_name", "?"),
            "rank_in_p4": next(
                (r["rank"] for r in scoring["breakthrough_results"]
                 if r["breakthrough"] == bt["breakthrough"]),
                None
            ),
            "p4_score": next(
                (r["p4_score"] for r in scoring["breakthrough_results"]
                 if r["breakthrough"] == bt["breakthrough"]),
                None
            ),
        }
        for bt in ground_truth["breakthroughs"]
    ],
    "metrics": {
        "recall_at_100": metrics["recall_at_100"],
        "precision_at_50": metrics["precision_at_50"],
        "mean_rank": metrics["mean_rank"],
        "median_rank": metrics["median_rank"],
    },
    "control": {
        "random_mean_score": control["summary"]["random_mean"],
        "breakthrough_mean_score": control["summary"]["breakthrough_mean"],
        "mann_whitney_U": test["U_statistic"],
        "mann_whitney_p": test["p_value_greater"],
        "effect_size": test["effect_size_r"],
        "cohens_d": test["cohens_d"],
    },
    "verdict": verdict_str,
}

OUTPUT = os.path.join(BASE, "FINAL_REPORT.json")
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

sz = os.path.getsize(OUTPUT)

# ══════════════════════════════════════════════════════════
# Print summary
# ══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("RÉSULTAT FINAL — TEST SEMI-AVEUGLE 2015→2025")
print("=" * 60)
print()
print(f"  Concepts:       {frozen['meta']['n_concepts']}")
print(f"  Paires:         {frozen['meta']['n_pairs']}")
print(f"  Cutoff:         2015 (ZÉRO post-2015)")
print()
print(f"  Recall@100:     {metrics['recall_at_100']:.0%}  ({metrics['hits_in_top100']}/{len(ground_truth['breakthroughs'])} percées dans top 100)")
print(f"  Precision@50:   {metrics['precision_at_50']:.0%}  ({metrics['hits_in_top50']}/50)")
print(f"  Rang moyen:     {metrics['mean_rank']:.0f} / {frozen['meta']['n_pairs']}")
print()
print(f"  Contrôle:")
print(f"    Percées mean P4:   {control['summary']['breakthrough_mean']:.6f}")
print(f"    Random mean P4:    {control['summary']['random_mean']:.6f}")
print(f"    Mann-Whitney p:    {test['p_value_greater']:.6f}")
print(f"    Effect size:       {test['effect_size_r']:.3f}")
print()
print(f"  ╔══════════════════════════════════════╗")
print(f"  ║  VERDICT: {verdict_str:<28s}║")
print(f"  ╚══════════════════════════════════════╝")
print()
print(f"  → {OUTPUT} ({sz:,} bytes)")
print()
print("PIPELINE TERMINÉ.")
