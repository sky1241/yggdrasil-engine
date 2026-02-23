"""
YGGDRASIL ENGINE — Science of Science Formulas
Implémentation des formules publiées pour la détection de trous structurels.

Sources:
- Wang, Song & Barabási 2013: "Quantifying Long-term Scientific Impact"
- Uzzi et al. 2013: "Atypical Combinations and Scientific Impact"  
- Wu, Wang & Evans 2019: "Large Teams Develop, Small Teams Disrupt"
- Sinatra et al. 2016: "Quantifying the Evolution of Individual Scientific Impact"
"""
import numpy as np
from typing import Optional


def fitness_wang_barabasi(citations_t: list[float], t_pub: int, 
                          t_now: int, mu: float = 1.0) -> float:
    """
    Fitness parameter ηᵢ (Wang-Barabási 2013).
    
    Mesure la qualité intrinsèque d'un paper/concept indépendamment de l'âge.
    
    cᵢ(t) = ηᵢ × m × Σ(cⱼ + 1) × Pᵢ(t - tᵢ)
    
    où Pᵢ(t) ~ log-normal aging:
        Pᵢ(t) = (1/t) × exp(-(ln(t) - μᵢ)² / (2σᵢ²))
    
    Simplified estimation: ηᵢ ≈ total_citations / expected_citations(age)
    
    Args:
        citations_t: citations par année depuis publication
        t_pub: année de publication
        t_now: année courante
        mu: log-normal center parameter
    """
    age = t_now - t_pub
    if age <= 0 or not citations_t:
        return 0.0
    
    total_citations = sum(citations_t)
    
    # Expected citations based on log-normal aging
    sigma = 1.0
    expected = 0.0
    for t in range(1, age + 1):
        p_t = (1.0 / t) * np.exp(-(np.log(t) - mu)**2 / (2 * sigma**2))
        expected += p_t
    
    if expected <= 0:
        return 0.0
    
    return total_citations / expected


def disruption_index(n_i: int, n_j: int, n_k: int) -> float:
    """
    D-index (Wu, Wang & Evans 2019 / Funk & Owen-Smith 2017).
    
    Mesure si un paper est disruptif (remplace) ou developmental (étend).
    
    D = (nᵢ - nⱼ) / (nᵢ + nⱼ + nₖ)
    
    où:
        nᵢ = papers citant le focal MAIS PAS ses références
        nⱼ = papers citant le focal ET ses références
        nₖ = papers citant PAS le focal mais citant ses références
    
    D → +1: disruptif (nouveau paradigme)
    D → -1: developmental (extension)
    D ≈ 0: neutre
    
    Args:
        n_i: citing focal only
        n_j: citing both focal and references
        n_k: citing references only
    """
    total = n_i + n_j + n_k
    if total == 0:
        return 0.0
    return (n_i - n_j) / total


def uzzi_zscore(observed: float, mean_random: float, std_random: float) -> float:
    """
    Z-score d'atypicité (Uzzi et al. 2013).
    
    Compare les combinaisons de journaux/domaines observées vs aléatoires.
    
    z = (observed - μ_random) / σ_random
    
    z << 0: combinaison très atypique (novel)
    z >> 0: combinaison très conventionnelle
    
    Les papers à haut impact ont tendance à avoir un z-score médian 
    conventionnel MAIS au moins une paire très atypique (z << 0).
    
    Args:
        observed: fréquence observée de la paire
        mean_random: fréquence moyenne dans le modèle nul
        std_random: écart-type dans le modèle nul
    """
    if std_random <= 0:
        return 0.0
    return (observed - mean_random) / std_random


def q_factor_sinatra(impact_sequence: list[float]) -> float:
    """
    Q-factor (Sinatra et al. 2016).
    
    Le Q-model sépare chance (p) et qualité (Q):
    log(cᵢ) = log(Qᵢ) + log(pᵢ)
    
    Q est constant pour un scientifique → son meilleur paper peut 
    venir à n'importe quel moment de sa carrière.
    
    Estimation simplifiée: Q ≈ median(log(citations + 1))
    
    Args:
        impact_sequence: citations de chaque paper d'un auteur
    """
    if not impact_sequence:
        return 0.0
    log_impacts = [np.log(max(c, 1)) for c in impact_sequence]
    return float(np.median(log_impacts))


def co_occurrence_strength(papers_a: int, papers_b: int, 
                           papers_ab: int, total_papers: int) -> float:
    """
    Force de co-occurrence entre deux domaines.

    PMI-like ratio: observed / expected

    Expected = P(A) × P(B) × total
    Ratio = papers_ab / expected

    Ratio > 1: co-occurrence plus fréquente qu'attendu
    Ratio < 1: co-occurrence moins fréquente qu'attendu
    
    Args:
        papers_a: papers dans domaine A
        papers_b: papers dans domaine B
        papers_ab: papers dans A ET B
        total_papers: total papers dans le corpus
    """
    if total_papers <= 0 or papers_a <= 0 or papers_b <= 0:
        return 0.0
    
    # PMI-like ratio: observed / expected
    p_a = papers_a / total_papers
    p_b = papers_b / total_papers
    expected = p_a * p_b * total_papers

    if expected <= 0:
        return 0.0

    return papers_ab / expected


def graph_laplacian(adjacency_matrix: np.ndarray) -> np.ndarray:
    """
    Laplacien du graphe pour identifier les communautés.
    
    L = D - A
    
    Les valeurs propres de L donnent la structure communautaire.
    Le vecteur de Fiedler (2ème plus petite valeur propre) donne 
    le meilleur cut bipartite → frontière entre deux continents.
    
    Args:
        adjacency_matrix: matrice d'adjacence (symétrique)
    """
    degree = np.diag(adjacency_matrix.sum(axis=1))
    return degree - adjacency_matrix


def fiedler_vector(adjacency_matrix: np.ndarray) -> np.ndarray:
    """
    Vecteur de Fiedler — 2ème plus petit vecteur propre du Laplacien.
    
    Identifie la frontière naturelle dans le réseau.
    Signe du vecteur = partition optimale en 2 groupes.
    
    Args:
        adjacency_matrix: matrice d'adjacence
    """
    if adjacency_matrix.shape[0] < 2:
        return np.array([0.0])
    L = graph_laplacian(adjacency_matrix)
    eigenvalues, eigenvectors = np.linalg.eigh(L)
    # 2nd smallest eigenvalue (first is always 0)
    return eigenvectors[:, 1]
