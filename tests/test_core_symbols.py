"""Tests for engine.core.symbols — Symbol database.

Tests Symbol class, SymbolDatabase (with mock data), strate mappings.
Uses in-memory data — no real data files needed.
"""
import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.core.symbols import (
    Symbol,
    SymbolDatabase,
    STRATE_COLORS,
    STRATE_NAMES,
    STRATE_CENTERS,
)


# ─── Symbol class ──────────────────────────────────────────────────────

class TestSymbol:
    def test_basic_creation(self):
        sym = Symbol("∫", "Leibniz", "analyse", 0, px=0.3, pz=-0.1)
        assert sym.s == "∫"
        assert sym.from_name == "Leibniz"
        assert sym.domain == "analyse"
        assert sym.strate == 0

    def test_color_by_strate(self):
        """Each strate has a unique color."""
        for strate_id in range(7):
            sym = Symbol("x", "test", "test", strate_id)
            assert sym.color == STRATE_COLORS[strate_id]

    def test_is_center_true(self):
        """Center symbol of strate 0 is '='."""
        sym = Symbol("=", "Descartes", "logique", 0)
        assert sym.is_center is True

    def test_is_center_false(self):
        sym = Symbol("∫", "Leibniz", "analyse", 0)
        assert sym.is_center is False

    def test_center_all_strates(self):
        """Each strate has a center symbol."""
        for strate_id, center_sym in STRATE_CENTERS.items():
            sym = Symbol(center_sym, "test", "test", strate_id)
            assert sym.is_center is True

    def test_to_dict(self):
        sym = Symbol("α", "Euler", "analyse", 1, px=0.5, pz=0.3)
        d = sym.to_dict()
        assert d["s"] == "α"
        assert d["from"] == "Euler"
        assert d["domain"] == "analyse"
        assert d["strate"] == 1
        assert d["color"] == list(STRATE_COLORS[1])
        assert d["is_center"] is False

    def test_repr(self):
        sym = Symbol("∇", "Hamilton", "analyse", 2)
        r = repr(sym)
        assert "∇" in r
        assert "S2" in r


# ─── STRATE constants ─────────────────────────────────────────────────

class TestStrateConstants:
    def test_seven_strates(self):
        assert len(STRATE_COLORS) == 7
        assert len(STRATE_NAMES) == 7
        assert len(STRATE_CENTERS) == 7

    def test_strate_ids(self):
        for i in range(7):
            assert i in STRATE_COLORS
            assert i in STRATE_NAMES
            assert i in STRATE_CENTERS

    def test_colors_are_rgb(self):
        for color in STRATE_COLORS.values():
            assert len(color) == 3
            assert all(0 <= c <= 255 for c in color)

    def test_sol_center(self):
        assert STRATE_CENTERS[0] == "="

    def test_plafond_center(self):
        assert STRATE_CENTERS[6] == "BB(n)"


# ─── SymbolDatabase with mock data ─────────────────────────────────────

@pytest.fixture
def mock_symbols_file(tmp_path):
    """Create a temporary symbols JSON file for testing."""
    data = {
        "strates": [
            {
                "id": 0,
                "symbols": [
                    {"s": "=", "from": "Descartes", "domain": "logique", "px": 0, "pz": 0},
                    {"s": "+", "from": "Widmann", "domain": "arithmétique", "px": 0.1, "pz": 0.2},
                    {"s": "∫", "from": "Leibniz", "domain": "analyse", "px": -0.3, "pz": 0.1},
                ]
            },
            {
                "id": 1,
                "symbols": [
                    {"s": "K", "from": "Kleene", "domain": "calculabilité", "px": 0, "pz": 0},
                ]
            },
            {"id": 2, "symbols": []},
            {"id": 3, "symbols": []},
            {"id": 4, "symbols": []},
            {"id": 5, "symbols": []},
            {
                "id": 6,
                "symbols": [
                    {"s": "BB(n)", "from": "Rado", "domain": "calculabilité", "px": 0, "pz": 0},
                ]
            },
        ]
    }
    filepath = tmp_path / "test_symbols.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return filepath


class TestSymbolDatabase:
    def test_load(self, mock_symbols_file):
        db = SymbolDatabase(filepath=mock_symbols_file)
        assert len(db.symbols) == 5

    def test_strate_lookup(self, mock_symbols_file):
        db = SymbolDatabase(filepath=mock_symbols_file)
        sol = db.strate(0)
        assert len(sol) == 3

    def test_strate_empty(self, mock_symbols_file):
        db = SymbolDatabase(filepath=mock_symbols_file)
        assert len(db.strate(2)) == 0

    def test_domain_lookup(self, mock_symbols_file):
        db = SymbolDatabase(filepath=mock_symbols_file)
        calc = db.domain("calculabilité")
        assert len(calc) == 2  # K and BB(n)

    def test_domain_nonexistent(self, mock_symbols_file):
        db = SymbolDatabase(filepath=mock_symbols_file)
        assert db.domain("underwater_basket_weaving") == []

    def test_domains_list(self, mock_symbols_file):
        db = SymbolDatabase(filepath=mock_symbols_file)
        domains = db.domains
        assert "logique" in domains
        assert "analyse" in domains
        assert "calculabilité" in domains

    def test_sol_property(self, mock_symbols_file):
        db = SymbolDatabase(filepath=mock_symbols_file)
        assert len(db.sol) == 3

    def test_stats(self, mock_symbols_file):
        db = SymbolDatabase(filepath=mock_symbols_file)
        s = db.stats()
        assert s["total"] == 5
        assert s["by_strate"]["S0"] == 3
        assert s["by_strate"]["S1"] == 1
        assert s["by_strate"]["S6"] == 1
        assert s["domains_count"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
