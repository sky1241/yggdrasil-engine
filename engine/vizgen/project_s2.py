#!/usr/bin/env python3
"""
YGGDRASIL — S-2 PROJECTION ENGINE
===================================
Projette les glyphes S-2 depuis les positions S0.
Principe: S0 est "parfait" → on projette vers le bas.
- Direct match: le glyphe est dans S0 → position right below
- Usage match: mot-clé dans le usage → 70% vers centroide
- Default: au centroide du continent avec dispersion

Sky × Claude — 22 Février 2026
"""

import json
import math
import random
from pathlib import Path
from collections import Counter

random.seed(42)
ROOT = Path(__file__).parent.parent.parent
DATA = ROOT / "data"

def load_data():
    with open(DATA / "math_symbols_unique.json", encoding="utf-8") as f:
        glyphs = json.load(f)
    with open(ROOT / "viz" / "data.json", encoding="utf-8") as f:
        viz = json.load(f)
    return glyphs, viz

# Usage keywords → continent index
USAGE_TO_CONT = {
    # Math Pures (0)
    "algebra": 0, "lie": 0, "group": 0, "ring": 0, "ideal": 0,
    "topology": 0, "manifold": 0, "homology": 0, "homotopy": 0,
    "analysis": 0, "integral": 0, "derivative": 0, "limit": 0, "series": 0,
    "set": 0, "function": 0, "relation": 0, "proof": 0, "theorem": 0,
    "number": 0, "prime": 0, "combinatorics": 0, "permutation": 0,
    "geometry": 0, "angle": 0, "triangle": 0, "perpendicular": 0,
    "category": 0, "functor": 0, "morphism": 0,
    "matrix": 0, "vector": 0, "tensor": 0, "determinant": 0,
    "complex": 0, "rational": 0, "integer": 0, "natural": 0,
    "infinity": 0, "cardinal": 0, "ordinal": 0,
    "logic": 0, "negation": 0, "conjunction": 0, "disjunction": 0,
    "quantifier": 0, "predicate": 0, "turnstile": 0,
    "summation": 0, "product": 0, "union": 0, "intersection": 0,
    "element": 0, "subset": 0, "superset": 0, "empty": 0,
    "operator": 0, "binary": 0, "ordering": 0, "equivalence": 0,
    "norm": 0, "factorial": 0,
    "fraktur": 0, "blackboard": 0, "script": 0, "calligraphic": 0,
    "greek": 0,
    # Physique (1)
    "quantum": 1, "hamiltonian": 1, "lagrangian": 1, "wave": 1,
    "force": 1, "energy": 1, "momentum": 1, "spin": 1,
    "planck": 1, "dirac": 1, "nabla": 1, "gradient": 1,
    "electromagnetic": 1, "magnetic": 1, "electric": 1,
    "thermodynamic": 1, "entropy": 1, "temperature": 1,
    "particle": 1, "photon": 1,
    # Ingénierie (2)
    "circuit": 2, "signal": 2, "frequency": 2, "voltage": 2,
    "resistance": 2, "current": 2, "impedance": 2,
    "control": 2, "feedback": 2, "transfer": 2,
    "measure": 2, "unit": 2, "dimension": 2,
    # Informatique (3)
    "algorithm": 3, "computation": 3, "complexity": 3,
    "boolean": 3, "bit": 3, "programming": 3, "turing": 3,
    # Finance (4)
    "probability": 4, "random": 4, "stochastic": 4,
    "expectation": 4, "variance": 4, "distribution": 4,
    "percentage": 4, "rate": 4,
    # Bio (5)
    "biological": 5, "genetic": 5, "molecular": 5,
    # Chimie (6)
    "chemical": 6, "reaction": 6, "equilibrium": 6, "bond": 6,
}


def compute_centroids(viz):
    """Compute centroid of each continent from S0 symbols."""
    continents = viz["continents"]
    centroids = {}
    for ci in range(-1, len(continents)):
        syms = [s for s in viz["symbols"] if s["strate"] == 0 and s["continent"] == ci]
        if syms:
            centroids[ci] = (
                sum(s["px"] for s in syms) / len(syms),
                sum(s["pz"] for s in syms) / len(syms),
            )
    return centroids


def project_s2():
    """Project all glyphs to S-2 positions based on S0."""
    glyphs, viz = load_data()
    continents = viz["continents"]
    centroids = compute_centroids(viz)

    # S0 lookup
    s0_map = {}
    for s in viz["symbols"]:
        if s["strate"] == 0:
            s0_map[s["s"]] = s

    results = []
    for g in glyphs:
        sym = g["symbol"]
        usage = g.get("usage", "").lower()

        # 1. Direct S0 match
        if sym in s0_map:
            s0 = s0_map[sym]
            results.append({
                "symbol": sym,
                "continent": s0["continent"],
                "parent_px": s0["px"],
                "parent_pz": s0["pz"],
                "match": "direct",
                "domain": s0.get("domain", "?"),
            })
            continue

        # 2. Usage keyword match
        matched_cont = None
        matched_kw = None
        for keyword, ci in USAGE_TO_CONT.items():
            if keyword in usage:
                matched_cont = ci
                matched_kw = keyword
                break

        if matched_cont is not None:
            cx, cz = centroids.get(matched_cont, (0, 0))
            results.append({
                "symbol": sym,
                "continent": matched_cont,
                "parent_px": cx,
                "parent_pz": cz,
                "match": "usage",
                "domain": matched_kw,
            })
            continue

        # 3. Default: Math Pures centroid
        default_ci = 0
        cx, cz = centroids.get(default_ci, (0, 0))
        results.append({
            "symbol": sym,
            "continent": default_ci,
            "parent_px": cx,
            "parent_pz": cz,
            "match": "default",
            "domain": g["category"],
        })

    # Compute S-2 positions
    s2_symbols = []
    for r in results:
        ci = r["continent"]
        cx, cz = centroids.get(ci, (0, 0))
        ppx, ppz = r["parent_px"], r["parent_pz"]

        if r["match"] == "direct":
            # Right below parent, tiny jitter
            px = ppx + random.uniform(-0.02, 0.02)
            pz = ppz + random.uniform(-0.02, 0.02)
        elif r["match"] == "usage":
            # Interpolate 70% toward centroid
            t = 0.7
            px = ppx * (1 - t) + cx * t + random.uniform(-0.05, 0.05)
            pz = ppz * (1 - t) + cz * t + random.uniform(-0.05, 0.05)
        else:
            # At centroid with dispersion
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0.02, 0.25)
            px = cx + radius * math.cos(angle)
            pz = cz + radius * math.sin(angle)

        is_centre = 1 if r["match"] == "direct" else 0
        s2_symbols.append([r["symbol"], round(px, 4), round(pz, 4), is_centre, r["domain"], 2, 0])

    # Stats
    match_types = Counter(r["match"] for r in results)
    cont_counts = Counter(r["continent"] for r in results)
    print(f"S-2 PROJECTION: {len(s2_symbols)} glyphs")
    print(f"  Direct (below parent): {match_types['direct']}")
    print(f"  Usage (toward centroid): {match_types['usage']}")
    print(f"  Default (at centroid): {match_types['default']}")
    print(f"By continent:")
    for ci, n in sorted(cont_counts.items()):
        name = continents[ci]["name"] if 0 <= ci < len(continents) else "Orphelins"
        print(f"  {ci} ({name}): {n}")

    # Save
    output = {
        "strate": -2,
        "name": "GLYPHES",
        "method": "s0_projection",
        "total": len(s2_symbols),
        "match_stats": dict(match_types),
        "symbols": s2_symbols,
    }
    outpath = DATA / "core" / "s2_projected.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)
    print(f"\nSaved: {outpath}")

    return output


if __name__ == "__main__":
    project_s2()
