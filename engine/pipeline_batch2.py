#!/usr/bin/env python3
"""
YGGDRASIL — PIPELINE BATCH 2: Tests 51-100
═══════════════════════════════════════════
25 POUR (percées connues) + 25 CONTRE (bruit)
Sky × Claude — 21 Février 2026, Versoix

Réutilise le pipeline_100.py existant, ajoute 50 paires diversifiées.
"""

import json
import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Import everything from the existing pipeline
sys.path.insert(0, str(Path(__file__).parent))
from pipeline_100 import (
    run_test, DATA_DIR, REPO_DIR
)

# ══════════════════════════════════════════
# 25 NEW POUR — Percées connues (diversifiées)
# ══════════════════════════════════════════
PAIRS_POUR_B2 = [
    ("transformer", "natural language processing"),       # 51 GPT/BERT revolution
    ("lithium-ion battery", "electric vehicle"),          # 52
    ("gene therapy", "genetic disease"),                  # 53
    ("nanotechnology", "drug delivery"),                  # 54
    ("quantum dot", "display technology"),                # 55
    ("stem cell", "regenerative medicine"),               # 56
    ("machine learning", "drug discovery"),               # 57
    ("convolutional neural network", "medical imaging"),  # 58
    ("robotics", "surgery"),                              # 59
    ("synthetic biology", "biofuel"),                     # 60
    ("graphene", "water purification"),                   # 61
    ("wearable technology", "health monitoring"),         # 62 (wearable sensors)
    ("carbon nanotube", "transistor"),                    # 63
    ("photocatalysis", "hydrogen"),                       # 64
    ("liquid biopsy", "cancer"),                          # 65
    ("mass spectrometry", "proteomics"),                  # 66
    ("metal-organic framework", "gas storage"),           # 67
    ("genome sequencing", "personalized medicine"),       # 68
    ("exoplanet", "spectroscopy"),                        # 69
    ("CRISPR", "agriculture"),                            # 70 gene-edited crops
    ("federated learning", "privacy"),                    # 71
    ("neural network", "weather forecasting"),            # 72
    ("microfluidics", "diagnostics"),                     # 73
    ("gene drive", "malaria"),                            # 74
    ("organoid", "disease modeling"),                     # 75
]

# ══════════════════════════════════════════
# 25 NEW CONTRE — Bruit (domaines sans lien)
# ══════════════════════════════════════════
PAIRS_CONTRE_B2 = [
    ("petrology", "semiotics"),                          # 76
    ("thermodynamics", "papyrology"),                    # 77
    ("quantum field theory", "veterinary medicine"),     # 78
    ("tensor analysis", "jurisprudence"),                # 79
    ("spectroscopy", "theology"),                        # 80
    ("electromagnetism", "epigraphy"),                   # 81
    ("nuclear physics", "ethnomusicology"),              # 82
    ("solid-state physics", "lexicography"),             # 83
    ("aerodynamics", "numismatics"),                     # 84
    ("acoustics", "palynology"),                         # 85
    ("plasma physics", "demography"),                    # 86
    ("polymer science", "historiography"),               # 87
    ("analytical chemistry", "criminology"),             # 88
    ("geochemistry", "phenomenology"),                   # 89
    ("inorganic chemistry", "library science"),          # 90
    ("surface science", "comparative literature"),       # 91
    ("chemical engineering", "egyptology"),              # 92
    ("tribology", "folklore"),                           # 93
    ("rheology", "pedagogy"),                            # 94
    ("crystallography", "political science"),            # 95
    ("stochastic process", "classical archaeology"),     # 96
    ("biomechanics", "philately"),                       # 97
    ("photonics", "urban planning"),                     # 98
    ("cryogenics", "ethnography"),                       # 99
    ("corrosion", "cosmology"),                          # 100 (wait - corrosion × cosmology could be noise but cosmology already used)
]

# Fix: ensure #100 is truly noise
PAIRS_CONTRE_B2[-1] = ("corrosion", "medieval studies")  # 100


def git_push_safe(test_id, pair, pattern, validated):
    """Push results to git, filtering token."""
    status = "✅" if validated else "❌"
    msg = f"PIPELINE #{test_id:03d}: {pair[0]} × {pair[1]} — {pattern} {status}"
    
    try:
        os.chdir(REPO_DIR)
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        result_commit = subprocess.run(
            ["git", "commit", "-m", msg], capture_output=True, text=True
        )
        if result_commit.returncode != 0:
            print(f"  ⚠️ Nothing to commit")
            return False
        
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True
        )
        # Filter token
        stderr_clean = result.stderr
        for tok in ["ghp_", "x-access-token:"]:
            stderr_clean = stderr_clean.replace(tok, "***")
        
        if result.returncode == 0:
            print(f"  📤 Pushed: {msg}")
            return True
        else:
            print(f"  ⚠️ Push failed: {stderr_clean[:100]}")
            return False
    except Exception as e:
        print(f"  ⚠️ Git error: {e}")
        return False


def run_batch2():
    """Run tests 51-100."""
    print("╔══════════════════════════════════════════════════╗")
    print("║  YGGDRASIL — BATCH 2: Tests 51-100              ║")
    print("║  25 POUR (percées) + 25 CONTRE (bruit)          ║")
    print("║  OpenAlex → scisci → mycelium → classifier      ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"Start: {datetime.utcnow().isoformat()}Z")
    
    results = []
    pour_valid = 0
    contre_valid = 0
    errors = 0
    
    # POUR tests (51-75)
    for i, pair in enumerate(PAIRS_POUR_B2):
        test_id = 51 + i
        try:
            r = run_test(test_id, pair, "pour")
            results.append(r)
            if r.get("validated"):
                pour_valid += 1
            git_push_safe(test_id, pair, r.get("classification", "??"), r.get("validated", False))
        except Exception as e:
            print(f"  💥 ERROR: {e}")
            errors += 1
            results.append({"test_id": test_id, "error": str(e), "pair": list(pair)})
        time.sleep(0.2)
    
    # CONTRE tests (76-100)
    for i, pair in enumerate(PAIRS_CONTRE_B2):
        test_id = 76 + i
        try:
            r = run_test(test_id, pair, "contre")
            results.append(r)
            if r.get("validated"):
                contre_valid += 1
            git_push_safe(test_id, pair, r.get("classification", "??"), r.get("validated", False))
        except Exception as e:
            print(f"  💥 ERROR: {e}")
            errors += 1
            results.append({"test_id": test_id, "error": str(e), "pair": list(pair)})
        time.sleep(0.2)
    
    # Summary batch 2
    total_valid = pour_valid + contre_valid
    total_tests = len(PAIRS_POUR_B2) + len(PAIRS_CONTRE_B2)
    
    print(f"\n{'='*60}")
    print(f"RÉSUMÉ BATCH 2 (Tests 51-100)")
    print(f"{'='*60}")
    print(f"POUR:   {pour_valid}/{len(PAIRS_POUR_B2)} validés ({pour_valid/len(PAIRS_POUR_B2)*100:.0f}%)")
    print(f"CONTRE: {contre_valid}/{len(PAIRS_CONTRE_B2)} validés ({contre_valid/len(PAIRS_CONTRE_B2)*100:.0f}%)")
    print(f"TOTAL:  {total_valid}/{total_tests} ({total_valid/total_tests*100:.0f}%)")
    print(f"Erreurs: {errors}")
    
    # Save batch 2 summary
    summary_b2 = {
        "date": datetime.utcnow().isoformat() + "Z",
        "pipeline": "openalex+scisci+mycelium",
        "batch": 2,
        "test_range": "51-100",
        "n_pour": len(PAIRS_POUR_B2),
        "n_contre": len(PAIRS_CONTRE_B2),
        "pour_valid": pour_valid,
        "contre_valid": contre_valid,
        "total_valid": total_valid,
        "total_tests": total_tests,
        "pct": round(total_valid/total_tests*100, 1),
        "errors": errors,
        "results": results
    }
    with open(DATA_DIR / "pipeline_batch2_summary.json", 'w') as f:
        json.dump(summary_b2, f, indent=2)
    print(f"\n💾 Saved: pipeline_batch2_summary.json")
    
    # Load batch 1 and merge for grand total
    try:
        with open(DATA_DIR / "pipeline_100_summary.json") as f:
            b1 = json.load(f)
        
        grand_total_valid = b1["total_valid"] + total_valid
        grand_total_tests = b1["total_tests"] + total_tests
        grand_pct = round(grand_total_valid/grand_total_tests*100, 1)
        
        grand_summary = {
            "date": datetime.utcnow().isoformat() + "Z",
            "pipeline": "openalex+scisci+mycelium",
            "batch1": {"tests": "1-50", "valid": b1["total_valid"], "total": b1["total_tests"], "pct": b1["pct"]},
            "batch2": {"tests": "51-100", "valid": total_valid, "total": total_tests, "pct": summary_b2["pct"]},
            "grand_total_valid": grand_total_valid,
            "grand_total_tests": grand_total_tests,
            "grand_pct": grand_pct,
            "all_results": b1["results"] + results
        }
        with open(DATA_DIR / "pipeline_grand_summary.json", 'w') as f:
            json.dump(grand_summary, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"GRAND TOTAL (100 TESTS)")
        print(f"{'='*60}")
        print(f"Batch 1: {b1['total_valid']}/{b1['total_tests']} ({b1['pct']}%)")
        print(f"Batch 2: {total_valid}/{total_tests} ({summary_b2['pct']}%)")
        print(f"TOTAL:   {grand_total_valid}/{grand_total_tests} ({grand_pct}%)")
        print(f"💾 Saved: pipeline_grand_summary.json")
    except Exception as e:
        print(f"⚠️ Could not merge with batch 1: {e}")
    
    return summary_b2


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run single test
        tid = int(sys.argv[1])
        if 51 <= tid <= 75:
            pair = PAIRS_POUR_B2[tid - 51]
            r = run_test(tid, pair, "pour")
        elif 76 <= tid <= 100:
            pair = PAIRS_CONTRE_B2[tid - 76]
            r = run_test(tid, pair, "contre")
        else:
            print(f"Test ID must be 51-100, got {tid}")
            sys.exit(1)
        print(json.dumps(r, indent=2))
    else:
        run_batch2()
