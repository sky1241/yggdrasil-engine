#!/usr/bin/env python3
"""
YGGDRASIL — SCAN PHILIPPE SCHUCHERT
════════════════════════════════════════════════
Premier test réel: trouver les P4 cachés autour
du domaine data-driven robust control.

Pas "robotics × ML" (évident).
On cherche les portes qu'il voit PAS depuis l'intérieur.

Sky × Claude — 21 Février 2026, Versoix
"""

import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / "pipeline"))

from pipeline_100 import (
    search_concept, get_timeline, get_total_co_occurrence,
    compute_scisci, compute_mycelium, classify_pattern
)
import json
import time
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# ══════════════════════════════════════════════
# PHILIPPE'S S0 TOOLS (son quartier)
# ══════════════════════════════════════════════
PHILIPPE_TOOLS = [
    "H-infinity control",
    "robust control",
    "convex optimization",
    "frequency response",
    "linear matrix inequality",
    "system identification",
]

# ══════════════════════════════════════════════
# DOMAINES INATTENDUS — LES CÂBLES PAR AILLEURS
# ══════════════════════════════════════════════
UNEXPECTED_DOMAINS = [
    # CONTOURNEMENT NP-HARD
    "tropical geometry",
    "quantum computing",
    "satisfiability",
    "sum-of-squares",
    "random matrix",
    # STABILITÉ AUTREMENT
    "contraction mapping",
    "dissipativity",
    "Hamiltonian mechanics",       # port-Hamiltonian → parent concept
    # CERTIFICATION/VÉRIFICATION
    "formal verification",
    "reachability",                # reachability analysis
    "interval arithmetic",
    # WILD CARDS
    "information geometry",
    "transportation theory",       # optimal transport
    "persistent homology",
    "kernel methods",
    "symbolic regression",
    "causal inference",
    "tensor decomposition",        # remplacement GNN
    "reproducing kernel Hilbert space",  # remplacement Koopman
    "spectral graph theory",       # remplacement conformal prediction
]

def build_pairs():
    pairs = []
    for tool in PHILIPPE_TOOLS:
        for domain in UNEXPECTED_DOMAINS:
            pairs.append((tool, domain))
    return pairs

def run_scan(pair_index_start=0, pair_index_end=None):
    pairs = build_pairs()
    if pair_index_end is None:
        pair_index_end = len(pairs)
    
    pairs_to_scan = pairs[pair_index_start:pair_index_end]
    print(f"\n{'='*70}")
    print(f"SCAN PHILIPPE — {len(pairs_to_scan)} paires")
    print(f"({pair_index_start} -> {pair_index_end} sur {len(pairs)} total)")
    print(f"{'='*70}\n")
    
    results = []
    errors = 0
    
    for i, (tool, domain) in enumerate(pairs_to_scan):
        idx = pair_index_start + i
        print(f"\n[{idx+1:03d}] {tool} x {domain}")
        
        try:
            concept_a = search_concept(tool)
            time.sleep(0.15)
            concept_b = search_concept(domain)
            time.sleep(0.15)
            
            if not concept_a:
                print(f"  X Not found: {tool}")
                results.append({"pair": [tool, domain], "error": f"Not found: {tool}"})
                errors += 1
                continue
            if not concept_b:
                print(f"  X Not found: {domain}")
                results.append({"pair": [tool, domain], "error": f"Not found: {domain}"})
                errors += 1
                continue
            
            print(f"  A: {concept_a['display_name']} ({concept_a['works_count']:,} works, L{concept_a['level']})")
            print(f"  B: {concept_b['display_name']} ({concept_b['works_count']:,} works, L{concept_b['level']})")
            
            timeline = get_timeline(concept_a["id"], concept_b["id"])
            time.sleep(0.15)
            co_total = sum(timeline.values())
            active_years = len([v for v in timeline.values() if v > 0])
            print(f"  Timeline: {active_years}/{len(timeline)} years, {co_total} papers")
            
            scisci_m = compute_scisci(timeline, concept_a["works_count"], concept_b["works_count"], co_total)
            mycelium_m = compute_mycelium(timeline)
            classif = classify_pattern(scisci_m, mycelium_m, timeline)
            
            result = {
                "pair": [tool, domain],
                "openalex_a": concept_a["display_name"],
                "openalex_b": concept_b["display_name"],
                "ids": [concept_a["id"], concept_b["id"]],
                "co_total": co_total,
                "active_years": active_years,
                "classification": classif["classification"],
                "confidence": classif["confidence"],
                "pattern_scores": classif["scores"],
                "scisci": scisci_m,
                "mycelium": mycelium_m,
                "timeline": timeline,
            }
            results.append(result)
            
            icon = {"P1": "PONT", "P2": "DENSE", "P3": "EXPLO", "P4": "TROU", "P5": "MORT"}.get(classif["classification"], "?")
            print(f"  -> {classif['classification']} ({icon}) conf={classif['confidence']:.0f}% | co={scisci_m['co_strength']:.2f} z={scisci_m['z_score']:.1f}")
            
            if classif["classification"] == "P4":
                print(f"  *** P4 TROU DETECTE: {tool} x {domain} ***")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"pair": [tool, domain], "error": str(e)})
            errors += 1
        
        time.sleep(0.2)
    
    # SUMMARY
    print(f"\n\n{'='*70}")
    print(f"RESULTATS SCAN PHILIPPE")
    print(f"{'='*70}")
    
    by_pattern = {"P1": [], "P2": [], "P3": [], "P4": [], "P5": [], "error": []}
    for r in results:
        if "error" in r:
            by_pattern["error"].append(r)
        else:
            by_pattern[r["classification"]].append(r)
    
    for p in ["P4", "P1", "P3", "P2", "P5"]:
        items = by_pattern[p]
        if items:
            print(f"\n{p} — {len(items)} paires:")
            for r in sorted(items, key=lambda x: x["co_total"]):
                print(f"  {r['pair'][0]:30s} x {r['pair'][1]:25s} | {r['co_total']:6d} papers | co={r['scisci']['co_strength']:.2f}")
    
    if by_pattern["error"]:
        print(f"\nERRORS: {len(by_pattern['error'])}")
        for r in by_pattern["error"]:
            print(f"  {r['pair'][0]} x {r['pair'][1]}: {r.get('error', '?')}")
    
    total_ok = len(results) - errors
    print(f"\nTOTAL: {total_ok}/{len(results)} reussis, {errors} erreurs")
    print(f"P4 trouves: {len(by_pattern['P4'])}")
    
    summary = {
        "scan": "philippe_schuchert",
        "date": datetime.utcnow().isoformat() + "Z",
        "n_pairs": len(results),
        "n_errors": errors,
        "by_pattern": {p: len(v) for p, v in by_pattern.items()},
        "results": results
    }
    
    outfile = DATA_DIR / "scan_philippe.json"
    DATA_DIR.mkdir(exist_ok=True)
    with open(outfile, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved: {outfile}")
    
    return summary

if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_scan(start, end)
