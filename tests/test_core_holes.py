"""Tests for engine.core.holes — Structural hole detection.

Tests the 3 types of holes (Technical, Conceptual, Perceptual),
DomainPair, HoleDetector, and continent mapping.
All pure math — no data files needed.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.core.holes import (
    score_technical,
    score_conceptual,
    score_perceptual,
    DomainPair,
    HoleDetector,
    map_symbol_to_continents,
    CONTINENTS,
)


# ─── score_technical (Type A) ──────────────────────────────────────────

class TestScoreTechnical:
    """Type A — Production high, fitness stagnant, D-index low."""

    def test_perfect_hole(self):
        """High production, zero delta, zero disruption → high score."""
        score = score_technical(production=1.0, delta_fitness=0.0, d_index=0.0)
        assert score == pytest.approx(1.0)

    def test_no_production(self):
        """Zero production → score 0 regardless."""
        score = score_technical(production=0.0, delta_fitness=0.0, d_index=0.0)
        assert score == 0.0

    def test_high_fitness_change(self):
        """Rapidly improving fitness → low score (not stuck)."""
        score = score_technical(production=1.0, delta_fitness=1.0, d_index=0.0)
        assert score == pytest.approx(0.0)

    def test_high_disruption(self):
        """High disruption → low score (already disrupted)."""
        score = score_technical(production=1.0, delta_fitness=0.0, d_index=1.0)
        assert score == pytest.approx(0.0)

    def test_range(self):
        """Score always in [0, 1]."""
        import random
        random.seed(42)
        for _ in range(100):
            p = random.random()
            df = random.uniform(-2, 2)
            di = random.uniform(-1, 1)
            s = score_technical(p, df, di)
            assert 0.0 <= s <= 1.0


# ─── score_conceptual (Type B) ─────────────────────────────────────────

class TestScoreConceptual:
    """Type B — Two active domains, no co-occurrence, atypical z-score."""

    def test_perfect_void(self):
        """Active domains, zero co-occurrence, very atypical → high score."""
        score = score_conceptual(
            activity_a=1.0, activity_b=1.0,
            co_occurrence=0.0, z_score=-10.0
        )
        assert score == pytest.approx(1.0)

    def test_high_cooccurrence(self):
        """High co-occurrence → low score (bridge exists)."""
        score = score_conceptual(
            activity_a=1.0, activity_b=1.0,
            co_occurrence=1.0, z_score=-5.0
        )
        assert score == pytest.approx(0.0)

    def test_inactive_domain(self):
        """Inactive domain → low score."""
        score = score_conceptual(
            activity_a=0.0, activity_b=1.0,
            co_occurrence=0.0, z_score=-5.0
        )
        assert score == 0.0

    def test_zero_zscore(self):
        """z=0 (perfectly typical) → score = 0."""
        score = score_conceptual(
            activity_a=1.0, activity_b=1.0,
            co_occurrence=0.0, z_score=0.0
        )
        assert score == 0.0

    def test_zscore_capped(self):
        """Z-scores beyond ±10 are capped at 1.0 atypicality."""
        s1 = score_conceptual(1.0, 1.0, 0.0, z_score=-10.0)
        s2 = score_conceptual(1.0, 1.0, 0.0, z_score=-100.0)
        assert s1 == s2  # both capped


# ─── score_perceptual (Type C) ─────────────────────────────────────────

class TestScorePerceptual:
    """Type C — High fitness, disruptive, but ignored (low citations)."""

    def test_karikó_pattern(self):
        """High fitness, disruptive, very few citations → high score."""
        score = score_perceptual(
            fitness=0.9, d_index=0.8,
            citations=10, expected_citations=1000
        )
        assert score > 0.5

    def test_well_cited(self):
        """Citations match expected → score ≈ 0 (not ignored)."""
        score = score_perceptual(
            fitness=0.9, d_index=0.8,
            citations=1000, expected_citations=1000
        )
        assert score == pytest.approx(0.0)

    def test_overcited(self):
        """More citations than expected → score 0 (definitely not ignored)."""
        score = score_perceptual(
            fitness=0.9, d_index=0.8,
            citations=2000, expected_citations=1000
        )
        assert score == 0.0

    def test_zero_expected(self):
        """Zero expected citations → score 0 (defensive)."""
        score = score_perceptual(fitness=0.9, d_index=0.8, citations=5, expected_citations=0)
        assert score == 0.0

    def test_low_fitness(self):
        """Low fitness → low score even if ignored."""
        score = score_perceptual(
            fitness=0.1, d_index=0.8,
            citations=10, expected_citations=1000
        )
        assert score < 0.1


# ─── DomainPair ────────────────────────────────────────────────────────

class TestDomainPair:
    def test_creation(self):
        pair = DomainPair("ML", "Biology")
        assert pair.domain_a == "ML"
        assert pair.domain_b == "Biology"
        assert pair.co_occurrence == 0.0

    def test_is_cold_default(self):
        """New pair with zero co-occurrence but zero activity → not cold."""
        pair = DomainPair("ML", "Biology")
        assert not pair.is_cold  # activity is 0

    def test_is_cold_active(self):
        """Active domains with low co-occurrence → cold."""
        pair = DomainPair("ML", "Biology")
        pair.activity_a = 0.8
        pair.activity_b = 0.7
        pair.co_occurrence = 0.05
        assert pair.is_cold

    def test_not_cold_high_cooc(self):
        """High co-occurrence → not cold."""
        pair = DomainPair("ML", "Biology")
        pair.activity_a = 0.8
        pair.activity_b = 0.7
        pair.co_occurrence = 0.5
        assert not pair.is_cold

    def test_score_b_computed(self):
        """Conceptual score computed from attributes."""
        pair = DomainPair("ML", "Biology")
        pair.activity_a = 0.9
        pair.activity_b = 0.8
        pair.co_occurrence = 0.0
        pair.z_score = -5.0
        assert pair.score_b > 0

    def test_set_technical_score(self):
        pair = DomainPair("ML", "Biology")
        pair.set_technical_score(0.8, 0.1, 0.2)
        assert pair.score_a > 0

    def test_to_dict(self):
        pair = DomainPair("ML", "Biology")
        d = pair.to_dict()
        assert d["pair"] == "ML × Biology"
        assert "co_occurrence" in d
        assert "is_cold" in d

    def test_repr(self):
        pair = DomainPair("ML", "Biology")
        r = repr(pair)
        assert "ML" in r and "Biology" in r


# ─── HoleDetector ──────────────────────────────────────────────────────

class TestHoleDetector:
    def test_pair_count(self):
        """N domains → N*(N-1)/2 pairs."""
        detector = HoleDetector(["A", "B", "C", "D"])
        assert len(detector.pairs) == 6  # 4*3/2

    def test_get_pair(self):
        detector = HoleDetector(["ML", "Biology", "Chemistry"])
        pair = detector.get_pair("Biology", "ML")  # reversed order
        assert pair is not None
        assert {pair.domain_a, pair.domain_b} == {"ML", "Biology"}

    def test_get_pair_nonexistent(self):
        detector = HoleDetector(["ML", "Biology"])
        assert detector.get_pair("ML", "Physics") is None

    def test_cold_pairs(self):
        detector = HoleDetector(["A", "B", "C"])
        # All pairs start with co_occurrence=0, but also activity=0
        cold = detector.cold_pairs(threshold=0.1)
        assert len(cold) == 3  # all are cold (co_occurrence < 0.1)

    def test_hot_pairs(self):
        detector = HoleDetector(["A", "B"])
        pair = detector.get_pair("A", "B")
        pair.co_occurrence = 0.8
        hot = detector.hot_pairs(threshold=0.5)
        assert len(hot) == 1

    def test_summary(self):
        detector = HoleDetector(["A", "B", "C"])
        s = detector.summary()
        assert s["total_pairs"] == 3
        assert "cold_pairs" in s
        assert "top_conceptual_holes" in s


# ─── map_symbol_to_continents ──────────────────────────────────────────

class TestContinentMapping:
    def test_known_domain(self):
        """'algèbre' belongs to Mathématiques Pures."""
        continents = map_symbol_to_continents("algèbre")
        assert "Mathématiques Pures" in continents

    def test_ml_domain(self):
        """'ML' belongs to Informatique & IA."""
        continents = map_symbol_to_continents("ML")
        assert "Informatique & IA" in continents

    def test_unknown_domain(self):
        """Unknown domain → ['Non classé']."""
        continents = map_symbol_to_continents("underwater_basket_weaving")
        assert continents == ["Non classé"]

    def test_finance_domain(self):
        continents = map_symbol_to_continents("finance")
        assert "Finance & Économie" in continents

    def test_continents_dict_not_empty(self):
        """The CONTINENTS dict has 7 entries."""
        assert len(CONTINENTS) == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
