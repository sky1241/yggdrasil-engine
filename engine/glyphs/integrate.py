#!/usr/bin/env python3
"""
Brique 8 — Integration
Create s2_spectral.json from glyph Laplacian positions.

Usage:
    python engine/glyphs/integrate.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

POSITIONS_PATH = ROOT / "data" / "scan" / "glyph_positions.json"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
S2_GLYPHES_PATH = ROOT / "data" / "core" / "s2_glyphes.json"
OUTPUT_PATH = ROOT / "data" / "core" / "s2_spectral.json"


def integrate():
    """Create s2_spectral.json with Laplacian positions."""
    print("=== Glyph Integration ===")

    # Load positions
    if not POSITIONS_PATH.exists():
        print(f"  ERROR: {POSITIONS_PATH} not found. Run glyph_laplacian.py first.")
        sys.exit(1)

    with open(POSITIONS_PATH, encoding="utf-8") as f:
        positions = json.load(f)

    # Load existing s2_glyphes.json for reference (domain info, seed status)
    if S2_GLYPHES_PATH.exists():
        with open(S2_GLYPHES_PATH, encoding="utf-8") as f:
            old_s2 = json.load(f)
        # Build lookup: symbol → [domain, is_seed]
        old_lookup = {}
        for entry in old_s2.get("symbols", []):
            # Format: [symbol, px, pz, is_seed, domain, ?, ?]
            if isinstance(entry, list) and len(entry) >= 5:
                old_lookup[entry[0]] = {
                    "domain": entry[4],
                    "is_seed": entry[3],
                }
    else:
        old_lookup = {}

    # Build new s2_spectral.json in same format as s2_glyphes.json
    symbols = []
    active = 0
    for gid_str, g in positions["glyphs"].items():
        sym = g["symbol"]
        px = g["px"]
        pz = g["pz"]
        degree = g["degree"]

        # Get domain from old data or use semantic group
        old = old_lookup.get(sym, {})
        domain = old.get("domain", g.get("semantic_group", "other"))
        is_seed = old.get("is_seed", 0)

        if degree > 0:
            active += 1

        # Same format: [symbol, px, pz, is_seed, domain, category_code, degree]
        symbols.append([sym, px, pz, is_seed, domain, 2, round(degree, 2)])

    output = {
        "strate": -2,
        "name": "GLYPHES",
        "method": "spectral_laplacian",
        "total": len(symbols),
        "active": active,
        "source": "arXiv LaTeX + PMC MathML co-occurrence",
        "eigenvalues": positions["meta"]["eigenvalues"],
        "chunks": {
            "arxiv": positions["meta"]["chunks_arxiv"],
            "pmc": positions["meta"]["chunks_pmc"],
        },
        "symbols": symbols,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Total: {len(symbols)} glyphs, {active} active (degree > 0)")
    print(f"  Method: spectral Laplacian from {positions['meta']['chunks_arxiv']} arXiv + "
          f"{positions['meta']['chunks_pmc']} PMC chunks")


if __name__ == "__main__":
    integrate()
