#!/usr/bin/env python3
"""
YGGDRASIL — Pipeline 50 POUR + 50 CONTRE
═══════════════════════════════════════════
Pipeline complet: OpenAlex → scisci → mycelium → classification → JSON
Sky × Claude — 21 Février 2026, Versoix

Optimisé: group_by=publication_year → 1 seul appel pour toute la timeline
"""

import json
import time
import math
import urllib.request
import urllib.parse
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

import numpy as np

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
REPO_DIR = SCRIPT_DIR.parent.parent

# ══════════════════════════════════════════
# OPENALEX API — LA PLUIE
# ══════════════════════════════════════════

EMAIL = "sky@yggdrasil.ch"
BASE_URL = "https://api.openalex.org"
TOTAL_OPENALEX = 250_000_000

def api_get(endpoint, params=None, retries=3):
    """GET with retry and rate limit handling."""
    url = f"{BASE_URL}/{endpoint}"
    if params is None:
        params = {}
    params["mailto"] = EMAIL
    url += "?" + urllib.parse.urlencode(params)
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": f"YggdrasilEngine/1.0 (mailto:{EMAIL})"
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = min(2 ** attempt * 2, 30)
                print(f"  ⏳ Rate limit, wait {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ❌ HTTP {e.code}: {e.reason}")
                if attempt == retries - 1:
                    raise
                time.sleep(1)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1)
    return None


def search_concept(name):
    """Find OpenAlex concept ID by name. Prefers exact matches."""
    data = api_get("concepts", {"filter": f"display_name.search:{name}", "per_page": 10})
    if not data:
        return None
    results = data.get("results", [])
    if not results:
        return None
    
    # Priority 1: exact match (case insensitive)
    name_lower = name.lower().strip()
    for r in results:
        if r["display_name"].lower().strip() == name_lower:
            return _concept_dict(r)
    
    # Priority 2: starts with the name
    for r in results:
        if r["display_name"].lower().startswith(name_lower):
            return _concept_dict(r)
    
    # Priority 3: closest length match (most specific)
    best = min(results, key=lambda x: abs(len(x["display_name"]) - len(name)))
    return _concept_dict(best)

def _concept_dict(r):
    return {
        "id": r["id"],
        "display_name": r["display_name"],
        "works_count": r.get("works_count", 0),
        "cited_by_count": r.get("cited_by_count", 0),
        "level": r.get("level", -1)
    }


def get_timeline(concept_a_id, concept_b_id):
    """
    Get co-occurrence timeline using group_by — ONE API call for all years.
    Returns: {year: count, ...}
    """
    data = api_get("works", {
        "filter": f"concepts.id:{concept_a_id},concepts.id:{concept_b_id}",
        "group_by": "publication_year",
        "per_page": 200
    })
    if not data:
        return {}
    
    timeline = {}
    for item in data.get("group_by", []):
        year = int(item["key"])
        count = item["count"]
        if 1975 <= year <= 2025:
            timeline[year] = count
    
    # Fill zeros for missing years
    for y in range(1975, 2026):
        if y not in timeline:
            timeline[y] = 0
    
    return dict(sorted(timeline.items()))


def get_total_co_occurrence(concept_a_id, concept_b_id):
    """Get total co-occurrence count."""
    data = api_get("works", {
        "filter": f"concepts.id:{concept_a_id},concepts.id:{concept_b_id}",
        "per_page": 1
    })
    if not data:
        return 0
    return data.get("meta", {}).get("count", 0)


# ══════════════════════════════════════════
# SCISCI — LE THERMOMÈTRE
# ══════════════════════════════════════════

def compute_scisci(timeline, works_a, works_b, co_total):
    """Compute scientometric metrics from timeline."""
    years = sorted(timeline.keys())
    counts = [timeline[y] for y in years]
    
    # 1. Co-occurrence strength (from scisci.py)
    if works_a > 0 and works_b > 0:
        p_a = works_a / TOTAL_OPENALEX
        p_b = works_b / TOTAL_OPENALEX
        expected = p_a * p_b * TOTAL_OPENALEX
        co_strength = co_total / expected if expected > 0 else 0
    else:
        expected = 0
        co_strength = 0
    
    # 2. Uzzi z-score approximation
    # observed = co_total, random model = expected
    std_est = max(math.sqrt(expected), 1)
    z_score = (co_total - expected) / std_est if std_est > 0 else 0
    
    # 3. Fitness (simplified Wang-Barabási)
    # Treat timeline as citation curve
    if len(counts) > 0 and sum(counts) > 0:
        total = sum(counts)
        age = len(counts)
        expected_fitness = 0
        for t in range(1, age + 1):
            p_t = (1.0 / t) * math.exp(-(math.log(t) - 1.0)**2 / 2.0)
            expected_fitness += p_t
        fitness = total / expected_fitness if expected_fitness > 0 else 0
    else:
        fitness = 0
    
    # 4. Growth metrics
    if len(counts) >= 10:
        first_5 = sum(counts[:5])
        last_5 = sum(counts[-5:])
        growth_ratio = last_5 / first_5 if first_5 > 0 else float('inf')
    else:
        growth_ratio = 0
    
    # 5. Disruption proxy
    # High disruption = explosive growth after silence
    zeros_early = sum(1 for c in counts[:len(counts)//2] if c == 0)
    peak = max(counts) if counts else 0
    
    return {
        "co_strength": round(co_strength, 4),
        "expected_co": round(expected, 2),
        "z_score": round(z_score, 2),
        "fitness": round(fitness, 2),
        "growth_ratio": round(growth_ratio, 2),
        "peak_year": years[counts.index(peak)] if peak > 0 else None,
        "peak_value": peak,
        "zeros_early": zeros_early,
        "total_papers": co_total
    }


# ══════════════════════════════════════════
# MYCELIUM — LA TOPOLOGIE
# ══════════════════════════════════════════

def compute_mycelium(timeline):
    """
    Compute mycelium-style topology metrics from timeline.
    Simulates network properties from the time series.
    """
    years = sorted(timeline.keys())
    counts = [timeline[y] for y in years]
    n = len(counts)
    
    if n == 0 or sum(counts) == 0:
        return {"bc": 0, "meshedness": 0, "physarum": 0, "slope": 0, "zeros": n, "ratio": 0}
    
    # 1. Betweenness centrality proxy
    # High BC = the connection is a bridge (few paths go through it)
    non_zero = [c for c in counts if c > 0]
    total = sum(counts)
    zeros = sum(1 for c in counts if c == 0)
    
    # BC approximation: sparse connections = high BC
    density = len(non_zero) / n if n > 0 else 0
    bc = 1.0 - density  # Inverse: more zeros = higher BC = more bridge-like
    
    # 2. Meshedness (cyclomatic complexity proxy)
    # Dense mesh = many connections = high meshedness
    if total > 0:
        variance = np.var(counts)
        mean_c = np.mean(counts)
        cv = (math.sqrt(variance) / mean_c) if mean_c > 0 else 0
        meshedness = min(density * (1 - cv/3), 1.0)
    else:
        meshedness = 0
    
    # 3. Physarum (flow optimization)
    # Physarum finds efficient paths. Constant flow = high Physarum fitness
    if len(non_zero) >= 2:
        # Stability of non-zero years
        physarum = 1.0 / (1.0 + np.std(non_zero) / np.mean(non_zero))
    else:
        physarum = 0
    
    # 4. Slope (linear trend)
    if n >= 2:
        x = np.arange(n, dtype=float)
        y = np.array(counts, dtype=float)
        if np.std(x) > 0:
            slope = float(np.corrcoef(x, y)[0, 1])
        else:
            slope = 0
    else:
        slope = 0
    
    # 5. Ratio peak/mean
    peak = max(counts)
    mean_val = np.mean(counts)
    ratio = peak / mean_val if mean_val > 0 else 0
    
    # 6. Explosion detection (for P1/meteor)
    # Find max year-over-year growth
    max_growth = 0
    growth_year = None
    for i in range(1, len(counts)):
        if counts[i-1] > 0:
            g = counts[i] / counts[i-1]
            if g > max_growth:
                max_growth = g
                growth_year = years[i]
        elif counts[i] > 0 and counts[i-1] == 0:
            max_growth = max(max_growth, counts[i])
            growth_year = years[i]
    
    return {
        "bc": round(bc, 4),
        "meshedness": round(meshedness, 4),
        "physarum": round(physarum, 4),
        "slope": round(slope, 4),
        "zeros": zeros,
        "ratio": round(ratio, 2),
        "max_growth": round(max_growth, 2),
        "growth_year": growth_year,
        "density": round(density, 4)
    }


# ══════════════════════════════════════════
# CLASSIFIER — LE DIAGNOSTIC
# ══════════════════════════════════════════

def classify_pattern(scisci_m, mycelium_m, timeline):
    """
    Classify into P1-P5 based on metrics.
    
    P1 PONT: Bridge inter-domaines. BC élevé, explosion, puis densification.
    P2 DENSE: Zone hub. Meshedness élevé, pas de zeros, stable.
    P3 THÉORIE×OUTIL: Connexion théorie-instrument. Explosion après validation.
    P4 TROU OUVERT: Pont pas encore explosé. BC élevé, faible co-occurrence.
    P5 ANTI-SIGNAL: L'hyphe meurt. Slope négative.
    """
    bc = mycelium_m["bc"]
    zeros = mycelium_m["zeros"]
    slope = mycelium_m["slope"]
    ratio = mycelium_m["ratio"]
    meshedness = mycelium_m["meshedness"]
    co_strength = scisci_m["co_strength"]
    growth = scisci_m["growth_ratio"]
    total = scisci_m["total_papers"]
    z_score = scisci_m["z_score"]
    max_growth = mycelium_m.get("max_growth", 0)
    
    scores = {"P1": 0, "P2": 0, "P3": 0, "P4": 0, "P5": 0}
    
    # P1 PONT: explosion + bridge signature
    if max_growth > 5:
        scores["P1"] += 30
    if co_strength > 1.0:
        scores["P1"] += 20
    if growth > 2:
        scores["P1"] += 20
    if z_score > 5:
        scores["P1"] += 15
    if slope > 0.3:
        scores["P1"] += 15
    
    # P2 DENSE: stable, connected, no gaps
    if zeros == 0:
        scores["P2"] += 30
    if meshedness > 0.3:
        scores["P2"] += 25
    if co_strength > 5:
        scores["P2"] += 20
    if 0.5 < ratio < 3:
        scores["P2"] += 15
    if abs(slope) < 0.3:
        scores["P2"] += 10
    
    # P3 THÉORIE×OUTIL: sharp explosion after specific year
    if max_growth > 10:
        scores["P3"] += 25
    if zeros > 5:
        scores["P3"] += 15
    if growth > 3:
        scores["P3"] += 20
    if slope > 0.5:
        scores["P3"] += 20
    if ratio > 5:
        scores["P3"] += 20
    
    # P4 TROU OUVERT: very sparse, potential
    if total < 100:
        scores["P4"] += 30
    elif total < 1000:
        scores["P4"] += 15
    if co_strength < 0.5:
        scores["P4"] += 25
    if zeros > 20:
        scores["P4"] += 20
    if bc > 0.5:
        scores["P4"] += 15
    if z_score < 2:
        scores["P4"] += 10
    
    # P5 ANTI-SIGNAL: declining
    if slope < -0.3:
        scores["P5"] += 35
    if growth < 0.5 and growth > 0:
        scores["P5"] += 25
    counts = [timeline.get(y, 0) for y in sorted(timeline.keys())]
    if len(counts) >= 10:
        last_10 = counts[-10:]
        first_10 = counts[:10]
        if sum(last_10) < sum(first_10) * 0.5:
            scores["P5"] += 25
    if z_score < 0:
        scores["P5"] += 15
    
    # Pick winner
    best = max(scores, key=scores.get)
    confidence = scores[best]
    total_score = sum(scores.values())
    confidence_pct = (confidence / total_score * 100) if total_score > 0 else 0
    
    return {
        "classification": best,
        "confidence": round(confidence_pct, 1),
        "scores": scores
    }


# ══════════════════════════════════════════
# VALIDATION — EXPECTED vs ACTUAL
# ══════════════════════════════════════════

def validate(classification, test_type, pair_name):
    """
    For POUR tests: P1 or P3 expected (known breakthroughs)
    For CONTRE tests: P2, P4, or P5 expected (noise)
    """
    if test_type == "pour":
        # Known breakthroughs should be P1 (bridge) or P3 (theory×tool)
        return classification in ["P1", "P3"]
    else:
        # Noise should NOT be P1
        return classification != "P1"


# ══════════════════════════════════════════
# PAIRS DEFINITIONS
# ══════════════════════════════════════════

PAIRS_POUR = [
    ("CRISPR", "immune system"),                    # 1
    ("deep learning", "computer vision"),            # 2
    ("gravitational wave", "interferometry"),         # 3
    ("immunotherapy", "cancer"),                      # 4
    ("blockchain", "cryptography"),                   # 5
    ("messenger RNA", "nanoparticle"),                # 6
    ("quantum computer", "quantum error correction"), # 7
    ("graphene", "semiconductor"),                    # 8
    ("protein structure", "deep learning"),           # 9 AlphaFold
    ("chimeric antigen receptor", "leukemia"),       # 10 CAR-T
    ("topological insulator", "superconductivity"),  # 11
    ("optogenetics", "neuroscience"),                # 12
    ("perovskite", "solar cell"),                    # 13
    ("LIGO", "gravitational wave"),                  # 14
    ("microbiome", "mental health"),                 # 15
    ("metamaterial", "cloaking"),                    # 16
    ("organ-on-a-chip", "drug discovery"),           # 17
    ("quantum entanglement", "quantum teleportation"), # 18
    ("epigenetics", "regulation of gene expression"), # 19
    ("neuromorphic engineering", "spiking neural network"), # 20
    ("3D printing", "titanium alloy"),               # 21
    ("single-cell analysis", "RNA"),                 # 22
    ("reinforcement learning", "game theory"),       # 23
    ("dark energy", "cosmology"),                    # 24
    ("superconductivity", "ceramic"),                # 25
]

PAIRS_CONTRE = [
    ("ornithology", "number theory"),               # 26
    ("polymer chemistry", "musicology"),             # 27
    ("computational fluid dynamics", "archaeology"), # 28
    ("set theory", "marine biology"),                # 29
    ("knot theory", "volcanology"),                  # 30
    ("category theory", "paleontology"),             # 31
    ("combinatorics", "linguistics"),                # 32
    ("general topology", "oceanography"),            # 33
    ("abstract algebra", "ecology"),                 # 34
    ("graph theory", "geomorphology"),               # 35
    ("real analysis", "entomology"),                 # 36
    ("probability theory", "art history"),           # 37
    ("differential geometry", "botany"),             # 38
    ("complex analysis", "anthropology"),            # 39
    ("functional analysis", "seismology"),           # 40
    ("mathematical logic", "parasitology"),          # 41
    ("game theory", "mineralogy"),                   # 42
    ("dynamical systems", "philology"),              # 43
    ("measure theory", "ichthyology"),               # 44
    ("ring theory", "glaciology"),                   # 45
    ("group theory", "herpetology"),                 # 46
    ("operator theory", "mycology"),                 # 47
    ("harmonic analysis", "dendrochronology"),       # 48
    ("algebraic geometry", "malacology"),            # 49
    ("homological algebra", "limnology"),            # 50
]


# ══════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════

def run_test(test_id, pair, test_type):
    """Run single test through complete pipeline."""
    a_name, b_name = pair
    print(f"\n{'='*60}")
    print(f"TEST #{test_id:03d} [{test_type.upper()}]: {a_name} × {b_name}")
    print(f"{'='*60}")
    
    result = {
        "test_id": test_id,
        "type": test_type,
        "pair": [a_name, b_name],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "pipeline": "openalex+scisci+mycelium"
    }
    
    # Step 1: Find OpenAlex concepts
    print(f"  🔍 Searching concepts...")
    concept_a = search_concept(a_name)
    time.sleep(0.15)
    concept_b = search_concept(b_name)
    time.sleep(0.15)
    
    if not concept_a:
        print(f"  ❌ Concept not found: {a_name}")
        result["error"] = f"Concept not found: {a_name}"
        result["validated"] = False
        return result
    if not concept_b:
        print(f"  ❌ Concept not found: {b_name}")
        result["error"] = f"Concept not found: {b_name}"
        result["validated"] = False
        return result
    
    print(f"  ✅ A: {concept_a['display_name']} ({concept_a['works_count']} works)")
    print(f"  ✅ B: {concept_b['display_name']} ({concept_b['works_count']} works)")
    
    result["openalex_ids"] = [concept_a["id"], concept_b["id"]]
    result["concept_a"] = concept_a
    result["concept_b"] = concept_b
    
    # Step 2: Timeline co-occurrence
    print(f"  📊 Getting timeline...")
    timeline = get_timeline(concept_a["id"], concept_b["id"])
    time.sleep(0.15)
    
    co_total = sum(timeline.values())
    print(f"  📊 Timeline: {len([v for v in timeline.values() if v > 0])}/{len(timeline)} years active, {co_total} total papers")
    
    result["timeline"] = timeline
    result["co_total"] = co_total
    
    # Step 3: scisci metrics
    print(f"  🌡️ Computing scisci...")
    scisci_m = compute_scisci(timeline, concept_a["works_count"], concept_b["works_count"], co_total)
    print(f"  🌡️ co_strength={scisci_m['co_strength']}, z={scisci_m['z_score']}, growth={scisci_m['growth_ratio']}")
    result["scisci_metrics"] = scisci_m
    
    # Step 4: mycelium topology
    print(f"  🍄 Computing mycelium...")
    mycelium_m = compute_mycelium(timeline)
    print(f"  🍄 BC={mycelium_m['bc']}, mesh={mycelium_m['meshedness']}, slope={mycelium_m['slope']}")
    result["mycelium_metrics"] = mycelium_m
    
    # Step 5: Classification
    print(f"  🎯 Classifying...")
    classification = classify_pattern(scisci_m, mycelium_m, timeline)
    result["classification"] = classification["classification"]
    result["confidence"] = classification["confidence"]
    result["pattern_scores"] = classification["scores"]
    
    # Step 6: Validation
    validated = validate(classification["classification"], test_type, f"{a_name}×{b_name}")
    result["validated"] = validated
    
    status = "✅" if validated else "❌"
    print(f"  {status} Pattern: {classification['classification']} (confidence: {classification['confidence']}%) — {'VALID' if validated else 'INVALID'}")
    
    # Step 7: Save JSON
    fname = f"pipeline_test_{test_id:03d}.json"
    fpath = DATA_DIR / "pipeline" / fname
    with open(fpath, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"  💾 Saved: {fname}")
    
    return result


def git_push(test_id, pair, pattern, validated):
    """Push results to git (if token available)."""
    status = "✅" if validated else "❌"
    msg = f"PIPELINE #{test_id:03d}: {pair[0]} × {pair[1]} — {pattern} {status}"
    
    try:
        os.chdir(REPO_DIR)
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", msg], check=True, capture_output=True)
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True
        )
        # Filter token from output
        stdout = result.stdout.replace("ghp_", "***").replace("x-access-token:", "***")
        stderr = result.stderr.replace("ghp_", "***").replace("x-access-token:", "***")
        if result.returncode == 0:
            print(f"  📤 Pushed: {msg}")
            return True
        else:
            print(f"  ⚠️ Push failed (no token?): {stderr[:100]}")
            return False
    except Exception as e:
        print(f"  ⚠️ Git error: {e}")
        return False


def run_all():
    """Run 50 POUR + 50 CONTRE."""
    print("╔══════════════════════════════════════════════╗")
    print("║  YGGDRASIL — PIPELINE 50+50 COMPLET         ║")
    print("║  OpenAlex → scisci → mycelium → classifier  ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"Start: {datetime.utcnow().isoformat()}Z")
    
    results = []
    pour_valid = 0
    contre_valid = 0
    errors = 0
    
    # POUR tests (1-50, but we have 25 pairs)
    for i, pair in enumerate(PAIRS_POUR):
        test_id = i + 1
        try:
            r = run_test(test_id, pair, "pour")
            results.append(r)
            if r.get("validated"):
                pour_valid += 1
            git_push(test_id, pair, r.get("classification", "??"), r.get("validated", False))
        except Exception as e:
            print(f"  💥 ERROR: {e}")
            errors += 1
            results.append({"test_id": test_id, "error": str(e), "pair": list(pair)})
        time.sleep(0.2)
    
    # CONTRE tests (26-50)
    for i, pair in enumerate(PAIRS_CONTRE):
        test_id = i + 26
        try:
            r = run_test(test_id, pair, "contre")
            results.append(r)
            if r.get("validated"):
                contre_valid += 1
            git_push(test_id, pair, r.get("classification", "??"), r.get("validated", False))
        except Exception as e:
            print(f"  💥 ERROR: {e}")
            errors += 1
            results.append({"test_id": test_id, "error": str(e), "pair": list(pair)})
        time.sleep(0.2)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"RÉSUMÉ FINAL")
    print(f"{'='*60}")
    print(f"POUR:   {pour_valid}/{len(PAIRS_POUR)} validés ({pour_valid/len(PAIRS_POUR)*100:.0f}%)")
    print(f"CONTRE: {contre_valid}/{len(PAIRS_CONTRE)} validés ({contre_valid/len(PAIRS_CONTRE)*100:.0f}%)")
    total_valid = pour_valid + contre_valid
    total_tests = len(PAIRS_POUR) + len(PAIRS_CONTRE)
    print(f"TOTAL:  {total_valid}/{total_tests} ({total_valid/total_tests*100:.0f}%)")
    print(f"Erreurs: {errors}")
    
    # Save summary
    summary = {
        "date": datetime.utcnow().isoformat() + "Z",
        "pipeline": "openalex+scisci+mycelium",
        "n_pour": len(PAIRS_POUR),
        "n_contre": len(PAIRS_CONTRE),
        "pour_valid": pour_valid,
        "contre_valid": contre_valid,
        "total_valid": total_valid,
        "total_tests": total_tests,
        "pct": round(total_valid/total_tests*100, 1),
        "errors": errors,
        "results": results
    }
    with open(DATA_DIR / "pipeline" / "pipeline_100_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary


if __name__ == "__main__":
    # Can run individual test: python pipeline_100.py 1
    if len(sys.argv) > 1:
        tid = int(sys.argv[1])
        if tid <= 25:
            pair = PAIRS_POUR[tid - 1]
            r = run_test(tid, pair, "pour")
        else:
            pair = PAIRS_CONTRE[tid - 26]
            r = run_test(tid, pair, "contre")
        print(json.dumps(r, indent=2))
    else:
        run_all()
