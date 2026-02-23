"""
YGGDRASIL ENGINE — Holes Detection Module
3 types de trous structurels: Technique (A), Conceptuel (B), Perceptuel (C)

Formules basées sur:
- Wang & Barabási 2013 (fitness ηᵢ)
- Uzzi et al. 2013 (z-scores atypicité)
- Wu & Evans 2019 (D-index disruption)
- Sinatra et al. 2016 (Q-model)
"""
import numpy as np
from typing import Optional


def score_technical(production: float, delta_fitness: float, d_index: float) -> float:
    """
    TYPE A — TROU TECHNIQUE
    Tout le monde SAIT où aller, personne ne PEUT.
    
    Détection: Production élevée MAIS fitness stagnante AVEC D-index bas.
    Exemples: Poincaré (Hamilton bloqué 20 ans), Higgs (besoin du LHC), Cryo-EM.
    
    Score_A = Production(t) × (1 - Δfitness/Δt) × (1 - |D-index|)
    
    Args:
        production: nombre de papers dans le domaine (normalisé 0-1)
        delta_fitness: changement de fitness sur la période (0 = stagnant)
        d_index: disruption index (-1 à 1, bas = developmental)
    """
    stagnation = 1.0 - min(abs(delta_fitness), 1.0)
    developmental = 1.0 - abs(d_index)
    return production * stagnation * developmental


def score_conceptual(activity_a: float, activity_b: float, 
                     co_occurrence: float, z_score: float) -> float:
    """
    TYPE B — TROU CONCEPTUEL
    Personne n'a l'IDÉE de connecter. Le vide est INVISIBLE.
    
    Détection: Deux domaines actifs SANS co-occurrence AVEC z-score très négatif.
    Exemples: GANs (game theory × deep learning), CRISPR, AlphaFold.
    
    Score_B = Activity(A) × Activity(B) × (1 - CoOcc(A,B)) × |z_score|
    
    Args:
        activity_a: activité du domaine A (normalisé 0-1)
        activity_b: activité du domaine B (normalisé 0-1)
        co_occurrence: co-occurrence entre A et B (0 = jamais vu ensemble)
        z_score: Uzzi z-score (négatif = atypique)
    """
    void_size = 1.0 - min(co_occurrence, 1.0)
    atypicality = min(abs(z_score), 10.0) / 10.0  # normalize
    return activity_a * activity_b * void_size * atypicality


def score_perceptual(fitness: float, d_index: float, 
                     citations: float, expected_citations: float) -> float:
    """
    TYPE C — TROU PERCEPTUEL
    L'outil EXISTE, personne n'y CROIT.
    
    Détection: Fitness élevée AVEC D-index élevé MAIS citations << attendues.
    Exemples: mRNA (Karikó rejetée 30 ans), H. pylori, Quasicristaux.
    
    Score_C = ηᵢ × |D_index| × (1 / cᵢ(t))
    
    Args:
        fitness: Wang-Barabási fitness parameter
        d_index: disruption index (high = disruptive)
        citations: actual citations received
        expected_citations: expected citations given fitness
    """
    if expected_citations <= 0:
        return 0.0
    
    ignored_ratio = max(0, 1.0 - (citations / expected_citations))
    return fitness * abs(d_index) * ignored_ratio


class DomainPair:
    """Paire de domaines avec métriques de co-occurrence."""
    
    def __init__(self, domain_a: str, domain_b: str):
        self.domain_a = domain_a
        self.domain_b = domain_b
        self.co_occurrence = 0.0
        self.z_score = 0.0
        self.common_neighbors = 0
        self.activity_a = 0.0
        self.activity_b = 0.0
        
        # Scores
        self._score_a: Optional[float] = None
        self._score_b: Optional[float] = None
    
    @property
    def score_a(self) -> float:
        """Score de trou technique (nécessite production, delta_fitness, d_index)."""
        if self._score_a is None:
            self._score_a = 0.0  # calculé via set_technical_score()
        return self._score_a

    def set_technical_score(self, production: float, delta_fitness: float, d_index: float):
        """Calcule et cache le score technique (Type A)."""
        self._score_a = score_technical(production, delta_fitness, d_index)

    @property
    def score_b(self) -> float:
        """Score de trou conceptuel."""
        if self._score_b is None:
            self._score_b = score_conceptual(
                self.activity_a, self.activity_b,
                self.co_occurrence, self.z_score
            )
        return self._score_b
    
    @property
    def is_cold(self) -> bool:
        """Paire froide = potentiel trou conceptuel."""
        return self.co_occurrence < 0.1 and self.activity_a > 0.3 and self.activity_b > 0.3
    
    def to_dict(self):
        return {
            "pair": f"{self.domain_a} × {self.domain_b}",
            "co_occurrence": self.co_occurrence,
            "z_score": self.z_score,
            "common_neighbors": self.common_neighbors,
            "score_B": round(self.score_b, 4),
            "is_cold": self.is_cold,
        }
    
    def __repr__(self):
        return f"DomainPair({self.domain_a} × {self.domain_b}, cooc={self.co_occurrence:.2f}, B={self.score_b:.3f})"


class HoleDetector:
    """Détecteur de trous structurels dans le réseau Yggdrasil."""
    
    def __init__(self, domains: list[str]):
        self.domains = domains
        self.pairs: dict[tuple, DomainPair] = {}
        
        # Create all pairs
        for i, a in enumerate(domains):
            for b in domains[i+1:]:
                key = tuple(sorted([a, b]))
                self.pairs[key] = DomainPair(a, b)
    
    def get_pair(self, a: str, b: str) -> Optional[DomainPair]:
        """Récupère une paire de domaines."""
        key = tuple(sorted([a, b]))
        return self.pairs.get(key)
    
    def cold_pairs(self, threshold: float = 0.1) -> list[DomainPair]:
        """Retourne les paires froides (potentiels trous conceptuels)."""
        return sorted(
            [p for p in self.pairs.values() if p.co_occurrence < threshold],
            key=lambda p: p.score_b,
            reverse=True
        )
    
    def hot_pairs(self, threshold: float = 0.5) -> list[DomainPair]:
        """Retourne les paires chaudes (ponts existants)."""
        return sorted(
            [p for p in self.pairs.values() if p.co_occurrence >= threshold],
            key=lambda p: p.co_occurrence,
            reverse=True
        )
    
    def summary(self) -> dict:
        """Résumé de l'analyse des trous."""
        cold = self.cold_pairs()
        hot = self.hot_pairs()
        return {
            "total_pairs": len(self.pairs),
            "cold_pairs": len(cold),
            "hot_pairs": len(hot),
            "top_conceptual_holes": [p.to_dict() for p in cold[:10]],
            "strongest_bridges": [p.to_dict() for p in hot[:10]],
        }


# Continent mapping (profession → domains)
CONTINENTS = {
    "Finance & Économie": [
        "finance", "économie", "statistiques", "probabilités", "stochastique", "optimisation"
    ],
    "Ingénierie & Électricité": [
        "électromagn", "signal", "contrôle", "fluides", "EDP", "thermo", "mécanique",
        "mécanique analytique", "optique"
    ],
    "Physique Fondamentale": [
        "quantique", "relativité", "QFT", "particules", "cosmologie", "gravitation",
        "nucléaire", "mécanique stat", "astronomie"
    ],
    "Informatique & IA": [
        "calculabilité", "complexité", "automates", "ML", "crypto", "information",
        "combinatoire"
    ],
    "Biologie & Médecine": [
        "biologie"
    ],
    "Chimie": [
        "chimie"
    ],
    "Mathématiques Pures": [
        "algèbre", "algèbre lin", "analyse", "analyse fonctionnelle", "topologie",
        "géométrie", "géom diff", "géom algébrique", "nb théorie", "nb premiers",
        "nombres", "catégories", "ensembles", "logique", "descriptive", "mesure",
        "complexes", "arithmétique", "trigonométrie", "ordinaux"
    ],
}


def map_symbol_to_continents(domain: str) -> list[str]:
    """Mappe un domaine de symbole vers ses continents (métiers)."""
    continents = []
    for continent, domains in CONTINENTS.items():
        if domain in domains:
            continents.append(continent)
    return continents if continents else ["Non classé"]
