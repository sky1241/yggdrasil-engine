"""Tests for engine.core.scisci — Science of Science formulas.

Tests the published formulas: Wang-Barabási fitness, D-index, Uzzi z-score,
Q-factor, co-occurrence strength, graph Laplacian, Fiedler vector.
All pure math — no data files needed.
"""
import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.core.scisci import (
    fitness_wang_barabasi,
    disruption_index,
    uzzi_zscore,
    q_factor_sinatra,
    co_occurrence_strength,
    graph_laplacian,
    fiedler_vector,
)


# ─── disruption_index ─────────────────────────────────────────────────

class TestDisruptionIndex:
    """Wu, Wang & Evans 2019 — D = (n_i - n_j) / (n_i + n_j + n_k)."""

    def test_purely_disruptive(self):
        """All citers cite focal only → D = 1."""
        assert disruption_index(100, 0, 0) == 1.0

    def test_purely_developmental(self):
        """All citers cite both focal and refs → D = -1."""
        assert disruption_index(0, 100, 0) == -1.0

    def test_neutral(self):
        """Equal n_i and n_j → D = 0."""
        assert disruption_index(50, 50, 0) == 0.0

    def test_mixed(self):
        """Known calculation: D = (50-30)/(50+30+20) = 0.2."""
        assert disruption_index(50, 30, 20) == pytest.approx(0.2)

    def test_zero_total(self):
        """No citers → D = 0."""
        assert disruption_index(0, 0, 0) == 0.0

    def test_range(self):
        """D is always in [-1, 1]."""
        for n_i in range(0, 20, 5):
            for n_j in range(0, 20, 5):
                for n_k in range(0, 20, 5):
                    d = disruption_index(n_i, n_j, n_k)
                    assert -1.0 <= d <= 1.0


# ─── uzzi_zscore ───────────────────────────────────────────────────────

class TestUzziZscore:
    """Uzzi et al. 2013 — z = (observed - μ) / σ."""

    def test_typical(self):
        """Observed equals mean → z = 0."""
        assert uzzi_zscore(5.0, 5.0, 1.0) == 0.0

    def test_atypical_negative(self):
        """Observed below mean → z < 0 (novel)."""
        z = uzzi_zscore(1.0, 5.0, 2.0)
        assert z == pytest.approx(-2.0)

    def test_conventional_positive(self):
        """Observed above mean → z > 0 (conventional)."""
        z = uzzi_zscore(10.0, 5.0, 2.5)
        assert z == pytest.approx(2.0)

    def test_zero_std(self):
        """Zero standard deviation → z = 0 (edge case)."""
        assert uzzi_zscore(5.0, 3.0, 0.0) == 0.0

    def test_negative_std(self):
        """Negative std → z = 0 (defensive)."""
        assert uzzi_zscore(5.0, 3.0, -1.0) == 0.0


# ─── fitness_wang_barabasi ─────────────────────────────────────────────

class TestFitnessWangBarabasi:
    """Wang, Song & Barabási 2013 — fitness ηᵢ."""

    def test_no_citations(self):
        """Zero citations → fitness 0."""
        assert fitness_wang_barabasi([], 2000, 2020) == 0.0

    def test_zero_age(self):
        """Published same year → fitness 0."""
        assert fitness_wang_barabasi([10], 2020, 2020) == 0.0

    def test_future_pub(self):
        """Publication in the future → fitness 0."""
        assert fitness_wang_barabasi([10], 2025, 2020) == 0.0

    def test_positive_fitness(self):
        """Real citation sequence → positive fitness."""
        citations = [0, 1, 3, 5, 8, 12, 15, 10, 7, 5]
        f = fitness_wang_barabasi(citations, 2010, 2020)
        assert f > 0

    def test_more_citations_higher_fitness(self):
        """More citations → higher fitness (same age)."""
        low = fitness_wang_barabasi([1, 1, 1], 2017, 2020)
        high = fitness_wang_barabasi([10, 20, 30], 2017, 2020)
        assert high > low


# ─── q_factor_sinatra ──────────────────────────────────────────────────

class TestQFactorSinatra:
    """Sinatra et al. 2016 — Q ≈ median(log(citations+1))."""

    def test_empty(self):
        """No papers → Q = 0."""
        assert q_factor_sinatra([]) == 0.0

    def test_single_paper(self):
        """One paper with 10 citations → Q = log(10)."""
        q = q_factor_sinatra([10])
        assert q == pytest.approx(np.log(10))

    def test_median_behavior(self):
        """Q is median-based, robust to outliers."""
        # [1, 2, 3, 100] → median of log values ≈ log(2.5)
        q = q_factor_sinatra([1, 2, 3, 100])
        # median of log([1,2,3,100]) = median([0, 0.69, 1.10, 4.61]) ≈ 0.89
        assert 0.5 < q < 2.0

    def test_zero_citations(self):
        """Papers with 0 citations → Q uses max(c,1) → log(1) = 0."""
        q = q_factor_sinatra([0, 0, 0])
        assert q == pytest.approx(0.0)


# ─── co_occurrence_strength ────────────────────────────────────────────

class TestCoOccurrenceStrength:
    """PMI-like ratio: observed / expected."""

    def test_independent_domains(self):
        """Independent domains → ratio ≈ 1."""
        # P(A)=0.1, P(B)=0.1, expected_AB = 0.01*1000 = 10
        ratio = co_occurrence_strength(100, 100, 10, 1000)
        assert ratio == pytest.approx(1.0)

    def test_correlated_domains(self):
        """High co-occurrence → ratio > 1."""
        ratio = co_occurrence_strength(100, 100, 50, 1000)
        assert ratio > 1.0

    def test_anti_correlated(self):
        """Low co-occurrence → ratio < 1."""
        ratio = co_occurrence_strength(100, 100, 1, 1000)
        assert ratio < 1.0

    def test_zero_total(self):
        """Zero total papers → 0."""
        assert co_occurrence_strength(10, 10, 5, 0) == 0.0

    def test_zero_domain(self):
        """Zero papers in a domain → 0."""
        assert co_occurrence_strength(0, 100, 0, 1000) == 0.0


# ─── graph_laplacian ───────────────────────────────────────────────────

class TestGraphLaplacian:
    """L = D - A."""

    def test_two_nodes(self):
        """Simple 2-node graph."""
        A = np.array([[0, 1], [1, 0]], dtype=float)
        L = graph_laplacian(A)
        expected = np.array([[1, -1], [-1, 1]], dtype=float)
        np.testing.assert_array_equal(L, expected)

    def test_isolated_node(self):
        """Isolated node has zero row/column."""
        A = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=float)
        L = graph_laplacian(A)
        assert L[2, 2] == 0  # isolated node degree = 0

    def test_row_sum_zero(self):
        """Each row of the Laplacian sums to zero."""
        A = np.array([[0, 1, 1], [1, 0, 1], [1, 1, 0]], dtype=float)
        L = graph_laplacian(A)
        row_sums = L.sum(axis=1)
        np.testing.assert_array_almost_equal(row_sums, 0)

    def test_symmetric(self):
        """Laplacian of symmetric adjacency is symmetric."""
        A = np.random.rand(5, 5)
        A = (A + A.T) / 2
        np.fill_diagonal(A, 0)
        L = graph_laplacian(A)
        np.testing.assert_array_almost_equal(L, L.T)


# ─── fiedler_vector ────────────────────────────────────────────────────

class TestFiedlerVector:
    """2nd smallest eigenvector of Laplacian."""

    def test_two_nodes(self):
        """Two connected nodes → Fiedler separates them."""
        A = np.array([[0, 1], [1, 0]], dtype=float)
        fiedler = fiedler_vector(A)
        assert fiedler.shape == (2,)
        # Signs should be opposite (one positive, one negative)
        assert fiedler[0] * fiedler[1] < 0

    def test_single_node(self):
        """Single node → trivial."""
        A = np.array([[0]], dtype=float)
        fiedler = fiedler_vector(A)
        assert len(fiedler) == 1

    def test_barbell_graph(self):
        """Two clusters connected by single edge → clear partition."""
        # Cluster 1: nodes 0,1,2 fully connected
        # Cluster 2: nodes 3,4,5 fully connected
        # Bridge: 2-3
        A = np.zeros((6, 6))
        for i in range(3):
            for j in range(3):
                if i != j:
                    A[i, j] = 1.0
        for i in range(3, 6):
            for j in range(3, 6):
                if i != j:
                    A[i, j] = 1.0
        A[2, 3] = A[3, 2] = 1.0

        fiedler = fiedler_vector(A)
        # Nodes 0,1,2 should have same sign, 3,4,5 opposite
        signs_cluster1 = [np.sign(fiedler[i]) for i in range(3)]
        signs_cluster2 = [np.sign(fiedler[i]) for i in range(3, 6)]
        assert len(set(signs_cluster1)) == 1, "Cluster 1 should be same sign"
        assert len(set(signs_cluster2)) == 1, "Cluster 2 should be same sign"
        assert signs_cluster1[0] != signs_cluster2[0], "Clusters should have opposite signs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
