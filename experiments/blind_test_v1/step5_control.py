"""
ÉTAPE 5 — Contrôle négatif (Mann-Whitney)
==========================================
Input:  blind_test/p4_predictions_2015.json
        blind_test/ground_truth.json
Output: blind_test/control_results.json

1. 50 paires de concepts ALÉATOIRES
2. Calcul de leur score P4
3. Mann-Whitney: scores percées réelles vs scores aléatoires
4. Si p < 0.05 → le moteur détecte un vrai signal
"""

import json
import os
import random
import numpy as np
from scipy import stats

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_FILE = os.path.join(BASE, "p4_predictions_2015.json")
GT_FILE = os.path.join(BASE, "ground_truth.json")
OUTPUT = os.path.join(BASE, "control_results.json")

print("=" * 60)
print("ÉTAPE 5 — Contrôle négatif")
print("=" * 60)

with open(PRED_FILE, "r", encoding="utf-8") as f:
    pred = json.load(f)

with open(GT_FILE, "r", encoding="utf-8") as f:
    gt = json.load(f)

all_pairs = pred["all_pairs"]
breakthroughs = gt["breakthroughs"]

# Build score lookup
pair_to_score = {}
for p in all_pairs:
    k1 = f"{p['concept_a']}|{p['concept_b']}"
    k2 = f"{p['concept_b']}|{p['concept_a']}"
    pair_to_score[k1] = p["p4_score"]
    pair_to_score[k2] = p["p4_score"]

# ══════════════════════════════════════════════════════════
# Get breakthrough P4 scores
# ══════════════════════════════════════════════════════════
bt_scores = []
for bt in breakthroughs:
    if bt["matched"] and bt["pair_key"]:
        score = pair_to_score.get(bt["pair_key"])
        if score is None:
            parts = bt["pair_key"].split("|")
            score = pair_to_score.get(f"{parts[1]}|{parts[0]}")
        if score is not None:
            bt_scores.append(score)

print(f"  Breakthrough scores: {len(bt_scores)} values")
print(f"  Mean: {np.mean(bt_scores):.6f}, Median: {np.median(bt_scores):.6f}")

# ══════════════════════════════════════════════════════════
# Random control: 50 random pairs
# ══════════════════════════════════════════════════════════
print(f"\n  Generating 50 random pairs...")

# Seed for reproducibility
random.seed(2015)  # Thematic seed :)

# Get all available pair keys
all_pair_keys = [f"{p['concept_a']}|{p['concept_b']}" for p in all_pairs]

# Exclude breakthrough pairs
bt_pairs = set()
for bt in breakthroughs:
    if bt["pair_key"]:
        bt_pairs.add(bt["pair_key"])
        parts = bt["pair_key"].split("|")
        bt_pairs.add(f"{parts[1]}|{parts[0]}")

available = [k for k in all_pair_keys if k not in bt_pairs]
random_pairs = random.sample(available, min(50, len(available)))

random_scores = []
random_details = []
for pk in random_pairs:
    score = pair_to_score.get(pk, 0)
    random_scores.append(score)
    parts = pk.split("|")
    # Find names
    p_match = next((p for p in all_pairs if p["concept_a"] == parts[0] and p["concept_b"] == parts[1]), None)
    name_a = p_match["concept_a_name"] if p_match else parts[0]
    name_b = p_match["concept_b_name"] if p_match else parts[1]
    random_details.append({
        "pair": pk,
        "name_a": name_a,
        "name_b": name_b,
        "p4_score": score,
    })

print(f"  Random scores: {len(random_scores)} values")
print(f"  Mean: {np.mean(random_scores):.6f}, Median: {np.median(random_scores):.6f}")

# ══════════════════════════════════════════════════════════
# Mann-Whitney U test
# ══════════════════════════════════════════════════════════
print(f"\n  Mann-Whitney U test:")

bt_arr = np.array(bt_scores)
rd_arr = np.array(random_scores)

# One-sided: breakthroughs should have HIGHER P4 scores
stat, p_value_two = stats.mannwhitneyu(bt_arr, rd_arr, alternative="two-sided")
_, p_value_greater = stats.mannwhitneyu(bt_arr, rd_arr, alternative="greater")

effect_size = stat / (len(bt_arr) * len(rd_arr))  # rank-biserial correlation approximation

print(f"  U statistic:      {stat:.1f}")
print(f"  p-value (2-sided): {p_value_two:.6f}")
print(f"  p-value (greater): {p_value_greater:.6f}")
print(f"  Effect size (r):   {effect_size:.3f}")

# Also compute Cohen's d for reference
d = (np.mean(bt_arr) - np.mean(rd_arr)) / np.sqrt((np.var(bt_arr) + np.var(rd_arr)) / 2) if np.var(bt_arr) + np.var(rd_arr) > 0 else 0
print(f"  Cohen's d:         {d:.3f}")

if p_value_greater < 0.05:
    verdict = "SIGNAL DETECTED (p < 0.05)"
elif p_value_greater < 0.10:
    verdict = "MARGINAL SIGNAL (p < 0.10)"
else:
    verdict = "NO SIGNAL (p >= 0.10)"
print(f"\n  >>> {verdict}")

# ══════════════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════════════
result = {
    "meta": {
        "date": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "random_seed": 2015,
        "n_random_pairs": len(random_scores),
        "n_breakthrough_scores": len(bt_scores),
    },
    "breakthrough_scores": bt_scores,
    "random_scores": random_scores,
    "random_pairs": random_details,
    "test": {
        "method": "Mann-Whitney U",
        "U_statistic": round(float(stat), 1),
        "p_value_two_sided": round(float(p_value_two), 8),
        "p_value_greater": round(float(p_value_greater), 8),
        "effect_size_r": round(float(effect_size), 4),
        "cohens_d": round(float(d), 4),
        "verdict": verdict,
    },
    "summary": {
        "breakthrough_mean": round(float(np.mean(bt_arr)), 6),
        "breakthrough_median": round(float(np.median(bt_arr)), 6),
        "random_mean": round(float(np.mean(rd_arr)), 6),
        "random_median": round(float(np.median(rd_arr)), 6),
    },
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\n  → {OUTPUT}")
print("ÉTAPE 5 TERMINÉE.")
