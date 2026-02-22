#!/usr/bin/env python3
"""
YGGDRASIL Phase 4 — Analyse post-PLUIE
Valide la matrice de co-occurrence et extrait les métriques réseau.

Usage:
    python analyze_pluie.py
    python analyze_pluie.py --compare-blind   # compare avec blind test 100 concepts
"""

import json
import os
import argparse
import numpy as np
from scipy import sparse
from scipy.stats import pearsonr, spearmanr
from pathlib import Path

PLUIE_DIR = Path(os.environ.get("YGG_OUTPUT", "data/pluie"))
MATRIX_PATH = PLUIE_DIR / "cooccurrence_matrix.npz"
INDEX_PATH = PLUIE_DIR / "matrix_index.json"
STRATES_PATH = Path(os.environ.get("YGG_STRATES", "data/core/strates_export_v2.json"))
ESCALIERS_PATH = Path("data/topology/escaliers_spectraux.json")


def load_matrix():
    """Charge matrice + index."""
    matrix = sparse.load_npz(str(MATRIX_PATH))
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index = json.load(f)
    return matrix, index


def basic_stats(matrix, index):
    """Statistiques de base."""
    n = matrix.shape[0]
    nnz = matrix.nnz
    
    # Symétrique → ne compter que triangle supérieur
    upper = sparse.triu(matrix, k=1)
    n_edges = upper.nnz
    max_edges = n * (n - 1) // 2
    density = n_edges / max_edges * 100
    
    diag = matrix.diagonal()
    total_papers_per_concept = diag.sum()
    
    print("═" * 60)
    print("📊 STATISTIQUES MATRICE PLUIE")
    print("═" * 60)
    print(f"  Concepts:              {n:>10,}")
    print(f"  Arêtes (paires > 0):   {n_edges:>10,}")
    print(f"  Arêtes max possibles:  {max_edges:>10,}")
    print(f"  Densité:               {density:>9.2f}%")
    print(f"  Éléments non-nuls:     {nnz:>10,}")
    print()
    
    # Distribution des poids
    weights = upper.data
    print("  Distribution co-occurrences (triangle sup):")
    print(f"    Min:     {weights.min():>12,}")
    print(f"    Médiane: {int(np.median(weights)):>12,}")
    print(f"    Moyenne: {weights.mean():>12,.1f}")
    print(f"    Max:     {weights.max():>12,}")
    print(f"    Std:     {weights.std():>12,.1f}")
    
    # Percentiles
    for p in [90, 95, 99, 99.9]:
        val = np.percentile(weights, p)
        print(f"    P{p:<5}: {val:>12,.0f}")
    print()
    
    return upper


def degree_analysis(matrix, index):
    """Analyse des degrés (connectivité par concept)."""
    idx_to_symbol = index["idx_to_symbol"]
    
    # Degré pondéré (somme des co-occurrences)
    degrees_weighted = np.array(matrix.sum(axis=1)).flatten()
    # Degré non-pondéré (nombre de voisins)
    binary = (matrix > 0).astype(int)
    degrees_unweighted = np.array(binary.sum(axis=1)).flatten()
    
    print("═" * 60)
    print("🔗 ANALYSE DES DEGRÉS")
    print("═" * 60)
    
    # Top 30 par degré pondéré
    print("\nTop 30 concepts (degré pondéré):")
    top_w = np.argsort(degrees_weighted)[-30:][::-1]
    for rank, idx in enumerate(top_w, 1):
        sym = idx_to_symbol.get(str(idx), f"?{idx}")
        print(f"  {rank:>3}. {degrees_weighted[idx]:>12,.0f} | {degrees_unweighted[idx]:>5} voisins | {sym}")
    
    # Concepts isolés ou faiblement connectés
    isolated = np.sum(degrees_unweighted == 0)
    weak = np.sum(degrees_unweighted <= 5)
    print(f"\n  Concepts isolés (0 voisin): {isolated}")
    print(f"  Concepts faibles (≤5 voisins): {weak}")
    
    # Distribution des degrés
    print(f"\n  Degré non-pondéré:")
    print(f"    Min:     {degrees_unweighted.min():>8}")
    print(f"    Médiane: {int(np.median(degrees_unweighted)):>8}")
    print(f"    Moyenne: {degrees_unweighted.mean():>8.1f}")
    print(f"    Max:     {degrees_unweighted.max():>8}")
    print()
    
    return degrees_weighted, degrees_unweighted


def strate_analysis(matrix, index):
    """Analyse par strate — densité intra vs inter strate."""
    idx_to_symbol = index["idx_to_symbol"]
    
    # Charger strates
    with open(STRATES_PATH, "r", encoding="utf-8") as f:
        strates_data = json.load(f)
    
    # Construire mapping symbol → strate
    symbol_to_strate = {}
    if isinstance(strates_data, list):
        for entry in strates_data:
            if isinstance(entry, dict) and "from" in entry and "strate" in entry:
                symbol_to_strate[entry["from"]] = entry["strate"]
    
    if not symbol_to_strate:
        print("⚠️  Impossible d'extraire les strates — structure non reconnue")
        return
    
    # Mapper idx → strate
    idx_to_strate = {}
    for idx_str, symbol in idx_to_symbol.items():
        if symbol in symbol_to_strate:
            idx_to_strate[int(idx_str)] = symbol_to_strate[symbol]
    
    strates = sorted(set(idx_to_strate.values()))
    print("═" * 60)
    print("🏔️  ANALYSE PAR STRATE")
    print("═" * 60)
    print(f"  Strates trouvées: {strates}")
    print(f"  Concepts avec strate: {len(idx_to_strate)}/{matrix.shape[0]}")
    print()
    
    # Matrice de densité inter-strates
    strate_indices = {s: [] for s in strates}
    for idx, s in idx_to_strate.items():
        strate_indices[s].append(idx)
    
    print("  Taille par strate:")
    for s in strates:
        print(f"    S{s}: {len(strate_indices[s])} concepts")
    print()
    
    # Densité moyenne de connexion entre chaque paire de strates
    print("  Co-occurrence moyenne entre strates:")
    print(f"  {'':>6}", end="")
    for s2 in strates:
        print(f"  S{s2:>6}", end="")
    print()
    
    for s1 in strates:
        print(f"  S{s1:>4} ", end="")
        for s2 in strates:
            if not strate_indices[s1] or not strate_indices[s2]:
                print(f"  {'N/A':>6}", end="")
                continue
            
            # Sous-matrice
            sub = matrix[np.ix_(strate_indices[s1], strate_indices[s2])]
            if s1 == s2:
                # Intra-strate: triangle supérieur seulement
                sub_upper = sparse.triu(sub, k=1)
                mean_val = sub_upper.sum() / max(sub_upper.nnz, 1)
            else:
                mean_val = sub.sum() / max(sub.nnz, 1)
            
            print(f"  {mean_val:>6.0f}", end="")
        print()
    print()


def structural_holes(matrix, index, top_n=30):
    """
    Identifie les TROUS STRUCTURELS — paires avec co-occurrence 
    anormalement basse par rapport aux degrés individuels.
    Ce sont les PRÉDICTIONS de découvertes futures.
    """
    idx_to_symbol = index["idx_to_symbol"]
    n = matrix.shape[0]
    
    print("═" * 60)
    print("🕳️  TROUS STRUCTURELS (prédictions Yggdrasil)")
    print("═" * 60)
    
    # Degrés pondérés
    degrees = np.array(matrix.sum(axis=1)).flatten().astype(float)
    total = degrees.sum()
    
    if total == 0:
        print("  ⚠️  Matrice vide")
        return
    
    # Pour chaque paire connectée, calculer le ratio observé/attendu
    # Attendu = degree_i * degree_j / total (modèle nul)
    # On cherche les paires avec degré élevé mais co-occurrence faible
    
    # Prendre les concepts avec degré suffisant (top 500)
    top_concepts = np.argsort(degrees)[-500:]
    
    holes = []
    dense = matrix.toarray() if n < 10000 else None
    
    for i_pos, i in enumerate(top_concepts):
        if degrees[i] == 0:
            continue
        for j in top_concepts[i_pos+1:]:
            if degrees[j] == 0:
                continue
            
            observed = matrix[i, j] if dense is None else dense[i, j]
            expected = (degrees[i] * degrees[j]) / total
            
            if expected < 10:  # Ignorer les attendus trop faibles
                continue
            
            ratio = observed / expected
            
            # TROU = ratio très bas (sous-connecté par rapport aux degrés)
            if ratio < 0.1 and observed < expected * 0.05:
                holes.append({
                    "i": int(i), "j": int(j),
                    "sym_i": idx_to_symbol.get(str(i), f"?{i}"),
                    "sym_j": idx_to_symbol.get(str(j), f"?{j}"),
                    "observed": float(observed),
                    "expected": float(expected),
                    "ratio": float(ratio),
                    "gap": float(expected - observed)
                })
    
    # Trier par gap (plus grand gap = plus grand potentiel)
    holes.sort(key=lambda h: h["gap"], reverse=True)
    
    print(f"\n  {len(holes)} trous structurels détectés (top {top_n}):\n")
    print(f"  {'Gap':>10} | {'Obs':>8} | {'Att':>10} | {'Ratio':>6} | Paire")
    print(f"  {'-'*10}-+-{'-'*8}-+-{'-'*10}-+-{'-'*6}-+-{'-'*40}")
    
    for h in holes[:top_n]:
        print(
            f"  {h['gap']:>10,.0f} | {h['observed']:>8,.0f} | "
            f"{h['expected']:>10,.0f} | {h['ratio']:>5.3f} | "
            f"{h['sym_i']} ↔ {h['sym_j']}"
        )
    
    # Sauvegarder
    holes_path = PLUIE_DIR / "structural_holes.json"
    with open(holes_path, "w", encoding="utf-8") as f:
        json.dump(holes[:200], f, indent=2, ensure_ascii=False)
    print(f"\n  💾 Top 200 trous sauvegardés: {holes_path}")
    print()
    
    return holes


def main():
    parser = argparse.ArgumentParser(description="Analyse post-PLUIE")
    parser.add_argument("--compare-blind", action="store_true",
                        help="Comparer avec le blind test 100 concepts")
    args = parser.parse_args()
    
    print()
    print("🌧️  YGGDRASIL — ANALYSE POST-PLUIE")
    print()
    
    matrix, index = load_matrix()
    
    basic_stats(matrix, index)
    degrees_w, degrees_uw = degree_analysis(matrix, index)
    strate_analysis(matrix, index)
    structural_holes(matrix, index)
    
    print("═" * 60)
    print("✅ Analyse complète")
    print("═" * 60)


if __name__ == "__main__":
    main()
