"""Tests for Yggdrasil Engine"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.symbols import SymbolDatabase, load
from engine.holes import score_technical, score_conceptual, score_perceptual, HoleDetector
from engine.scisci import disruption_index, uzzi_zscore, fitness_wang_barabasi


def test_load_symbols():
    db = load()
    assert len(db.symbols) == 794, f"Expected 794, got {len(db.symbols)}"
    assert len(db.sol) == 549, f"Expected 549 S0, got {len(db.sol)}"
    assert len(db.strate(6)) == 20, f"Expected 20 S6, got {len(db.strate(6))}"
    print("✓ test_load_symbols")


def test_domains():
    db = load()
    domains = db.domains
    assert len(domains) > 40, f"Expected 40+ domains, got {len(domains)}"
    assert "quantique" in domains
    assert "finance" in domains
    print(f"✓ test_domains ({len(domains)} domaines)")


def test_score_technical():
    """Poincaré pattern: high production, stagnant fitness, low D-index."""
    score = score_technical(production=0.8, delta_fitness=0.05, d_index=0.1)
    assert score > 0.5, f"Expected > 0.5, got {score}"
    
    # Non-stagnant should score lower
    score2 = score_technical(production=0.8, delta_fitness=0.9, d_index=0.1)
    assert score2 < score, f"Non-stagnant should score lower"
    print(f"✓ test_score_technical (A={score:.3f})")


def test_score_conceptual():
    """GAN pattern: active domains, zero co-occurrence."""
    score = score_conceptual(activity_a=0.8, activity_b=0.7, co_occurrence=0.0, z_score=-5.0)
    assert score > 0.2, f"Expected > 0.2, got {score}"
    
    # With co-occurrence should score lower
    score2 = score_conceptual(activity_a=0.8, activity_b=0.7, co_occurrence=0.8, z_score=-5.0)
    assert score2 < score, f"With co-occurrence should score lower"
    print(f"✓ test_score_conceptual (B={score:.3f})")


def test_score_perceptual():
    """mRNA pattern: high fitness, high D-index, low citations."""
    score = score_perceptual(fitness=0.9, d_index=0.8, citations=5, expected_citations=500)
    assert score > 0.5, f"Expected > 0.5, got {score}"
    
    # Well-cited should score lower
    score2 = score_perceptual(fitness=0.9, d_index=0.8, citations=500, expected_citations=500)
    assert score2 < score, f"Well-cited should score lower"
    print(f"✓ test_score_perceptual (C={score:.3f})")


def test_disruption_index():
    """D-index: disruptive vs developmental."""
    d_disruptive = disruption_index(n_i=100, n_j=5, n_k=10)
    d_developmental = disruption_index(n_i=5, n_j=100, n_k=10)
    
    assert d_disruptive > 0, f"Should be disruptive (>0), got {d_disruptive}"
    assert d_developmental < 0, f"Should be developmental (<0), got {d_developmental}"
    print(f"✓ test_disruption_index (D+={d_disruptive:.3f}, D-={d_developmental:.3f})")


def test_uzzi_zscore():
    """Z-score: atypical vs conventional."""
    z_atypical = uzzi_zscore(observed=2, mean_random=50, std_random=10)
    z_conventional = uzzi_zscore(observed=80, mean_random=50, std_random=10)
    
    assert z_atypical < -2, f"Should be atypical (<<0), got {z_atypical}"
    assert z_conventional > 2, f"Should be conventional (>>0), got {z_conventional}"
    print(f"✓ test_uzzi_zscore (z_atyp={z_atypical:.1f}, z_conv={z_conventional:.1f})")


def test_export_viz():
    db = load()
    viz = db.export_viz_json()
    assert "strates" in viz
    assert "symbols" in viz
    assert len(viz["symbols"]) == 794
    assert len(viz["strates"]) == 7
    print(f"✓ test_export_viz ({len(viz['symbols'])} symbols)")


def test_hole_detector():
    db = load()
    detector = HoleDetector(db.domains[:10])  # First 10 domains
    assert len(detector.pairs) > 0
    print(f"✓ test_hole_detector ({len(detector.pairs)} pairs)")


if __name__ == "__main__":
    print("\n=== YGGDRASIL ENGINE TESTS ===\n")
    test_load_symbols()
    test_domains()
    test_score_technical()
    test_score_conceptual()
    test_score_perceptual()
    test_disruption_index()
    test_uzzi_zscore()
    test_export_viz()
    test_hole_detector()
    print("\n✅ ALL TESTS PASSED\n")
