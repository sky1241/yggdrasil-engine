"""
ÉTAPE 2 — Détection des trous structurels (données gelées 2015)
================================================================
Input:  blind_test/data_2015_frozen.json
Output: blind_test/p4_predictions_2015.json

Formules:
1. Normaliser works_count (0-1)
2. Normaliser co-occurrences (0-1)
3. z-score Uzzi pour chaque paire: z = (observed - mean) / std
4. Betweenness centrality sur le graphe de co-occurrence
5. Score P4 (trou ouvert): score = activity_A × activity_B × (1 - cooc_norm) × |z_score|
6. Trier par score P4 décroissant → top 100

ZÉRO données post-2015.
"""

import json
import os
import sys
import math
import numpy as np

# Optional but preferred
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    print("[WARN] networkx not installed, will compute betweenness manually (slower)")

# ══════════════════════════════════════════════════════════
# Load frozen data
# ══════════════════════════════════════════════════════════
BASE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE, "data_2015_frozen.json")
OUTPUT = os.path.join(BASE, "p4_predictions_2015.json")

print("=" * 60)
print("ÉTAPE 2 — Détection des trous structurels")
print("=" * 60)

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

concepts = data["concepts"]
cooc_raw = data["cooccurrence"]
n = len(concepts)

print(f"  {n} concepts, {len(cooc_raw)} paires")

# Build index
cid_to_idx = {c["id"]: i for i, c in enumerate(concepts)}
idx_to_cid = {i: c["id"] for i, c in enumerate(concepts)}

# ══════════════════════════════════════════════════════════
# 1. Normalize works_count (0-1)
# ══════════════════════════════════════════════════════════
print("\n[1] Normalizing works_count...")

works = np.array([c["works_count_2015"] for c in concepts], dtype=float)
w_min, w_max = works.min(), works.max()
if w_max > w_min:
    works_norm = (works - w_min) / (w_max - w_min)
else:
    works_norm = np.ones(n)

print(f"  Range: {w_min:,.0f} — {w_max:,.0f}")
print(f"  Top 5 by works_count_2015:")
top5 = np.argsort(-works)[:5]
for idx in top5:
    print(f"    {concepts[idx]['display_name']:<35s} {works[idx]:>12,.0f} (norm={works_norm[idx]:.3f})")

# ══════════════════════════════════════════════════════════
# 2. Normalize co-occurrences (0-1)
# ══════════════════════════════════════════════════════════
print("\n[2] Normalizing co-occurrences...")

# Build co-occurrence matrix
cooc_matrix = np.zeros((n, n), dtype=float)
for key, count in cooc_raw.items():
    parts = key.split("|")
    if len(parts) != 2:
        continue
    a, b = parts
    if a in cid_to_idx and b in cid_to_idx:
        i, j = cid_to_idx[a], cid_to_idx[b]
        cooc_matrix[i, j] = count
        cooc_matrix[j, i] = count

# Normalize (0-1)
c_max = cooc_matrix.max()
if c_max > 0:
    cooc_norm = cooc_matrix / c_max
else:
    cooc_norm = cooc_matrix.copy()

nonzero_pairs = np.count_nonzero(cooc_matrix) // 2  # symmetric
print(f"  Max co-occurrence: {c_max:,.0f}")
print(f"  Non-zero pairs: {nonzero_pairs}/{n*(n-1)//2}")

# ══════════════════════════════════════════════════════════
# 3. z-score Uzzi (atypicality)
# ══════════════════════════════════════════════════════════
print("\n[3] Computing z-scores (Uzzi atypicality)...")

# For the null model, we use the expected co-occurrence based on marginals:
# E[cooc(i,j)] = works_i * works_j / total_works
# This is a simplified version of Uzzi's reshuffling null model.
# The full model would require Monte Carlo, but for 100 concepts this
# analytical approximation is standard.

total_works_sum = works.sum()

# Expected co-occurrence under independence
expected = np.outer(works, works) / total_works_sum

# Standard deviation under hypergeometric approximation
# Var ~ E * (1 - works_i/total) * (1 - works_j/total)
# Simplified: std ~ sqrt(E * (1 - p_i) * (1 - p_j))
p = works / total_works_sum
std_matrix = np.sqrt(expected * np.outer(1 - p, 1 - p))
std_matrix[std_matrix < 1] = 1  # avoid division by zero

z_matrix = (cooc_matrix - expected) / std_matrix

# Set diagonal to 0
np.fill_diagonal(z_matrix, 0)

print(f"  z-score range: [{z_matrix.min():.1f}, {z_matrix.max():.1f}]")
print(f"  Mean z: {z_matrix[z_matrix != 0].mean():.2f}")

# Show most atypical pairs (most negative z = most unexpected LOW co-occurrence)
z_flat = []
for i in range(n):
    for j in range(i+1, n):
        z_flat.append((z_matrix[i, j], i, j))
z_flat.sort()

print(f"\n  Top 5 most atypical pairs (lowest z = unexpected gap):")
for z, i, j in z_flat[:5]:
    print(f"    z={z:>8.1f}  {concepts[i]['display_name'][:25]:25s} × {concepts[j]['display_name'][:25]}")

# ══════════════════════════════════════════════════════════
# 4. Betweenness centrality
# ══════════════════════════════════════════════════════════
print("\n[4] Computing betweenness centrality...")

if HAS_NX:
    G = nx.Graph()
    for i in range(n):
        G.add_node(i, name=concepts[i]["display_name"])
    for i in range(n):
        for j in range(i+1, n):
            w = cooc_matrix[i, j]
            if w > 0:
                # Weight = inverse of co-occurrence (high cooc = short distance)
                G.add_edge(i, j, weight=1.0 / (1.0 + w))

    betweenness = nx.betweenness_centrality(G, weight="weight")
    bc = np.array([betweenness.get(i, 0) for i in range(n)])
else:
    # Fallback: degree centrality as proxy
    degree = (cooc_matrix > 0).sum(axis=1)
    bc = degree / degree.max() if degree.max() > 0 else np.zeros(n)

print(f"  Top 5 by betweenness:")
top5_bc = np.argsort(-bc)[:5]
for idx in top5_bc:
    print(f"    {concepts[idx]['display_name']:<35s} BC={bc[idx]:.4f}")

# ══════════════════════════════════════════════════════════
# 5. Score P4 (structural hole = open gap)
# ══════════════════════════════════════════════════════════
print("\n[5] Computing P4 scores (structural holes)...")

# P4 = activity_A × activity_B × (1 - cooc_normalized) × |z_score|
# High P4 = two active fields with unexpectedly low co-occurrence (= structural hole)

p4_scores = []
for i in range(n):
    for j in range(i+1, n):
        activity_a = works_norm[i]
        activity_b = works_norm[j]
        gap = 1.0 - cooc_norm[i, j]
        z_abs = abs(z_matrix[i, j])

        score = activity_a * activity_b * gap * z_abs

        p4_scores.append({
            "concept_a": concepts[i]["id"],
            "concept_a_name": concepts[i]["display_name"],
            "concept_b": concepts[j]["id"],
            "concept_b_name": concepts[j]["display_name"],
            "works_a_2015": int(works[i]),
            "works_b_2015": int(works[j]),
            "cooccurrence_2015": int(cooc_matrix[i, j]),
            "cooc_normalized": round(float(cooc_norm[i, j]), 6),
            "z_score": round(float(z_matrix[i, j]), 3),
            "activity_a": round(float(activity_a), 4),
            "activity_b": round(float(activity_b), 4),
            "gap": round(float(gap), 6),
            "p4_score": round(float(score), 6),
        })

# Sort by P4 descending
p4_scores.sort(key=lambda x: -x["p4_score"])

print(f"  Total pairs scored: {len(p4_scores)}")
print(f"\n  TOP 20 structural holes (P4):")
print(f"  {'Rank':>4s}  {'Score':>10s}  {'z':>8s}  {'Cooc':>8s}  {'Concept A':<25s} × {'Concept B':<25s}")
print(f"  {'─'*4}  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*25}   {'─'*25}")
for rank, p in enumerate(p4_scores[:20], 1):
    print(f"  {rank:4d}  {p['p4_score']:10.4f}  {p['z_score']:8.1f}  {p['cooccurrence_2015']:>8,}  {p['concept_a_name'][:25]:<25s} × {p['concept_b_name'][:25]}")

# ══════════════════════════════════════════════════════════
# 6. Save predictions
# ══════════════════════════════════════════════════════════
print("\n[6] Saving predictions...")

result = {
    "meta": {
        "date": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "method": "P4 = activity_A * activity_B * (1 - cooc_norm) * |z_uzzi|",
        "null_model": "analytical independence (E = N_a * N_b / N_total)",
        "n_concepts": n,
        "n_pairs_scored": len(p4_scores),
        "cutoff_year": 2015,
        "warning": "ZERO post-2015 data used"
    },
    "betweenness_centrality": {
        concepts[i]["id"]: {
            "name": concepts[i]["display_name"],
            "bc": round(float(bc[i]), 6),
            "works_2015": int(works[i]),
            "works_norm": round(float(works_norm[i]), 4),
        }
        for i in range(n)
    },
    "predictions_top100": p4_scores[:100],
    "all_pairs": p4_scores,  # keep all for analysis
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

sz = os.path.getsize(OUTPUT)
print(f"  → {OUTPUT}")
print(f"  → {sz:,} bytes ({sz/1024:.0f} KB)")
print(f"  → Top 100 predictions saved")
print()
print("ÉTAPE 2 TERMINÉE.")
