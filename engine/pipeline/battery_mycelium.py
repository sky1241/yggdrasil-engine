#!/usr/bin/env python3
"""
BATTERIE MYCELIUM — 50 POUR × 50 CONTRE
═════════════════════════════════════════
Question: Le mycelium peut-il PRÉDIRE le pattern juste
à partir de la topologie du graphe?

50 POUR = tests orientés (on connaît le pattern → P1/P3/P4/P5)
50 CONTRE = tests aveugles (on sait que c'est P2 dense → bruit de fond)

On entraîne PAS de modèle. On définit des SEUILS empiriques
basés sur les signatures trouvées par bridge_mycelium.py:
  P1 PONT:  BC < 0.01, zeros > 0, ratio > 10
  P2 DENSE: BC > 0.01, zeros = 0, ratio < 5
  P4 TROU:  BC < 0.005, zeros > 0, ratio > 50
  P5 MORT:  slope < 0

Puis on teste: combien le mycelium classe correctement?

Sky × Claude — 21 Février 2026, Versoix (minuit)
"""

import json
import sys
import os
import importlib.util
from pathlib import Path
from collections import defaultdict
from copy import deepcopy

import networkx as nx
import numpy as np

# ════════════════════════════════════════════════════════════
# IMPORT MYCELIUM
# ════════════════════════════════════════════════════════════
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"

myc_path = SCRIPT_DIR / "mycelium_full.py"
if not myc_path.exists():
    myc_path = SCRIPT_DIR / "mycelium_full.py"
if not myc_path.exists():
    for p in [SCRIPT_DIR, SCRIPT_DIR.parent]:
        candidate = p / "mycelium_full.py"
        if candidate.exists():
            myc_path = candidate
            break

spec = importlib.util.spec_from_file_location("mycelium", str(myc_path))
myc = importlib.util.module_from_spec(spec)
old_argv = sys.argv
sys.argv = ["battery.py"]
spec.loader.exec_module(myc)
sys.argv = old_argv


# ════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES
# ════════════════════════════════════════════════════════════

CATALOG = {
    "fermat":       {"file": "fermat_data.json",       "a": "Elliptic Curves",     "b": "Modular Forms",      "pattern": "P1", "test": 1},
    "groups":       {"file": "groups_data.json",       "a": "Group Theory",        "b": "Algebra",            "pattern": "P2", "test": 2},
    "higgs":        {"file": "higgs_data.json",        "a": "Higgs Theory",        "b": "Particle Physics",   "pattern": "P3", "test": 3},
    "crispr":       {"file": "crispr_data.json",       "a": "CRISPR",              "b": "Gene Editing",       "pattern": "P1", "test": 4},
    "darkmatter":   {"file": "darkmatter_data.json",   "a": "Dark Matter",         "b": "Quantum Gravity",    "pattern": "P4", "test": 5},
    "deeplearning": {"file": "deeplearning_data.json", "a": "Deep Learning",       "b": "Computer Vision",    "pattern": "P1", "test": 6},
    "graphene":     {"file": "graphene_data.json",     "a": "Graphene",            "b": "Semiconductors",     "pattern": "P5", "test": 7},
    "poincare":     {"file": "poincare_data.json",     "a": "Ricci Flow",          "b": "Riemannian",         "pattern": "P1", "test": 8},
    "immunotherapy":{"file": "immunotherapy_data.json", "a": "Immunology",          "b": "Oncology",           "pattern": "P1", "test": 9},
    "gravitational":{"file": "gravitational_data.json","a": "Gravitational Waves", "b": "Binary Merger",      "pattern": "P3", "test": 10},
    "superconductor":{"file":"superconductor_data.json","a":"HTS",                 "b": "Cuprate",            "pattern": "P1", "test": 11},
    "quantum_crypto":{"file":"quantum_crypto_data.json","a":"Quantum Computing",   "b": "Cryptography",       "pattern": "P4", "test": 12},
    "microbiome":   {"file": "microbiome_data.json",   "a": "Microbiome",          "b": "Psychiatry",         "pattern": "P1", "test": 13},
    "stringtheory": {"file": "stringtheory_data.json", "a": "String Theory",       "b": "LHC Experiments",    "pattern": "P5", "test": 14},
    "alphafold":    {"file": "alphafold_data.json",    "a": "Protein Folding",     "b": "Deep Learning",      "pattern": "P1", "test": 15},
    "blockchain":   {"file": "blockchain_data.json",   "a": "Blockchain",          "b": "Cryptography",       "pattern": "P1", "test": 16},
    "topological":  {"file": "topological_data.json",  "a": "Topological Insulators","b":"Condensed Matter",  "pattern": "P1", "test": 17},
    "exoplanet":    {"file": "exoplanet_data.json",    "a": "Exoplanets",          "b": "Astrobiology",       "pattern": "P2", "test": 18},
    "fusion":       {"file": "fusion_data.json",       "a": "Tokamak",             "b": "HTS Magnets",        "pattern": "P4", "test": 19},
    "behavioral":   {"file": "behavioral_econ_data.json","a":"Behavioral Econ",    "b": "Cognitive Bias",     "pattern": "P1", "test": 20},
}


def extract_timeline(data):
    if not isinstance(data, list): return []
    timeline = []
    for row in data:
        year = row.get("year")
        if year is None: continue
        co = row.get("co", 0)
        if co == 0:
            for key in row:
                if key == "year": continue
                if "_" in key or key == "triple":
                    co = max(co, row[key])
        timeline.append({"year": year, "co": co})
    return timeline


def load_tests():
    tests = []
    
    for name, info in CATALOG.items():
        fpath = DATA_DIR / info["file"]
        if not fpath.exists(): continue
        try:
            data = json.load(open(fpath))
            tl = extract_timeline(data)
            if tl:
                tests.append({
                    "id": f"T{info['test']:02d}", "name": name,
                    "a": info["a"], "b": info["b"],
                    "pattern": info["pattern"], "timeline": tl, "type": "oriented"
                })
        except: pass
    
    for bf in ["blind_tests_data.json", "blind62_71_summary.json",
               "blind72_81_summary.json", "blind82_91_summary.json",
               "blind92_101_summary.json"]:
        fpath = DATA_DIR / bf
        if not fpath.exists(): continue
        try:
            data = json.load(open(fpath))
            if not isinstance(data, list): continue
            for item in data:
                tid = item.get("id", item.get("test", "?"))
                pr = str(item.get("pattern", "P2"))
                if "P1" in pr: pat = "P1"
                elif "P4" in pr or "TROU" in pr.upper(): pat = "P4"
                elif "P5" in pr or "CLIN" in pr.upper(): pat = "P5"
                elif "P3" in pr: pat = "P3"
                else: pat = "P2"
                tests.append({
                    "id": f"B{tid}" if isinstance(tid, int) else str(tid),
                    "name": f"{item.get('a','?')}×{item.get('b','?')}",
                    "a": item.get("a", "?"), "b": item.get("b", "?"),
                    "pattern": pat, "timeline": item.get("timeline", []),
                    "type": "blind"
                })
        except: pass
    
    return tests


# ════════════════════════════════════════════════════════════
# CONSTRUIRE GRAPHE
# ════════════════════════════════════════════════════════════

def build_graph(tests):
    G = nx.Graph()
    for t in tests:
        a, b = t["a"], t["b"]
        tl = t["timeline"]
        if not tl: continue
        cos = [row["co"] for row in tl if row.get("co") is not None]
        if not cos: continue
        
        total = sum(cos)
        n_zeros = sum(1 for c in cos if c == 0)
        max_co = max(cos)
        min_nz = min((c for c in cos if c > 0), default=1)
        ratio = max_co / max(min_nz, 1)
        
        slope = 0.0
        if len(cos) >= 3:
            x = np.arange(len(cos), dtype=float)
            slope = float(np.polyfit(x, cos, 1)[0])
        
        for node in [a, b]:
            if node not in G:
                G.add_node(node, appearances=0, patterns=defaultdict(int))
            G.nodes[node]["appearances"] += 1
            G.nodes[node]["patterns"][t["pattern"]] += 1
        
        if not G.has_edge(a, b):
            G.add_edge(a, b, weight=max(total, 1), zeros=n_zeros,
                       ratio=ratio, slope=slope, max_co=max_co,
                       pattern=t["pattern"], tests=[t["id"]])
        else:
            G[a][b]["weight"] += total
            G[a][b]["tests"].append(t["id"])
    return G


# ════════════════════════════════════════════════════════════
# CLASSIFICATEUR MYCELIUM (seuils empiriques)
# ════════════════════════════════════════════════════════════

def mycelium_classify(bc_a, bc_b, ebc, zeros, ratio, slope, degree_a, degree_b):
    """
    Classifie un pattern à partir des métriques mycelium.
    Basé sur les signatures empiriques de bridge_mycelium.py:
    
    P1: BC faible, zeros > 0, ratio élevé → pont explosif
    P2: BC haute, zeros = 0, ratio faible → hub dense
    P3: Un côté BC haute, l'autre faible → théorie attend outil
    P4: BC minimale des deux côtés, ratio très élevé → trou fantôme
    P5: slope négative → signal mourant
    """
    bc_max = max(bc_a, bc_b)
    bc_min = min(bc_a, bc_b)
    bc_diff = bc_max - bc_min
    deg_max = max(degree_a, degree_b)
    
    # Score pour chaque pattern
    scores = {}
    
    # P5: ANTI-SIGNAL — slope négative est le signal le plus fort
    s5 = 0
    if slope < -5: s5 += 40
    if slope < -10: s5 += 30
    if zeros == 0: s5 += 10  # pas de trou, juste déclin
    if ratio < 20: s5 += 10
    scores["P5"] = s5
    
    # P4: TROU OUVERT — invisible au réseau, potentiel maximal
    s4 = 0
    if bc_max < 0.005: s4 += 25
    if bc_max < 0.001: s4 += 20
    if zeros > 0: s4 += 20
    if ratio > 50: s4 += 20
    if deg_max <= 1.5: s4 += 15
    scores["P4"] = s4
    
    # P1: PONT — isolé mais explosion
    s1 = 0
    if bc_max < 0.015: s1 += 20
    if zeros > 0: s1 += 15
    if ratio > 10: s1 += 20
    if ratio > 50: s1 += 15
    if slope > 0: s1 += 10
    if deg_max < 2.5: s1 += 10
    scores["P1"] = s1
    
    # P3: THÉORIE×OUTIL — asymétrie BC (un côté connecté, l'autre non)
    s3 = 0
    if bc_diff > 0.01: s3 += 30
    if zeros > 0 and zeros <= 5: s3 += 20
    if ratio < 10: s3 += 15
    if slope > 0: s3 += 10
    scores["P3"] = s3
    
    # P2: DENSE — le hub par défaut
    s2 = 0
    if bc_max > 0.01: s2 += 25
    if zeros == 0: s2 += 30
    if ratio < 5: s2 += 20
    if slope > 50: s2 += 10
    if deg_max >= 2: s2 += 15
    scores["P2"] = s2
    
    # Le gagnant
    best = max(scores, key=scores.get)
    confidence = scores[best] / max(sum(scores.values()), 1) * 100
    
    return best, confidence, scores


# ════════════════════════════════════════════════════════════
# BATTERIE DE TESTS
# ════════════════════════════════════════════════════════════

def run_battery(G, tests):
    """
    50 POUR (orientés) + 50 CONTRE (aveugles)
    Le mycelium classe → on compare au pattern réel
    """
    bc = nx.betweenness_centrality(G, weight="weight")
    ebc = nx.edge_betweenness_centrality(G, weight="weight")
    
    results = {"pour": [], "contre": []}
    
    # Séparer
    oriented = [t for t in tests if t["type"] == "oriented"]
    blind = [t for t in tests if t["type"] == "blind"]
    
    # Limiter à 50 chaque
    oriented = oriented[:50]
    blind = blind[:50]
    
    for group_name, group in [("pour", oriented), ("contre", blind)]:
        for t in group:
            a, b = t["a"], t["b"]
            if a not in G or b not in G: continue
            
            edge = (a, b) if G.has_edge(a, b) else (b, a) if G.has_edge(b, a) else None
            if not edge: continue
            
            edata = G[edge[0]][edge[1]]
            
            predicted, confidence, scores = mycelium_classify(
                bc_a=bc.get(a, 0),
                bc_b=bc.get(b, 0),
                ebc=ebc.get(edge, ebc.get((edge[1], edge[0]), 0)),
                zeros=edata.get("zeros", 0),
                ratio=edata.get("ratio", 1),
                slope=edata.get("slope", 0),
                degree_a=G.degree(a),
                degree_b=G.degree(b),
            )
            
            actual = t["pattern"]
            correct = predicted == actual
            
            results[group_name].append({
                "id": t["id"],
                "name": t["name"][:35],
                "actual": actual,
                "predicted": predicted,
                "correct": correct,
                "confidence": confidence,
                "scores": scores,
                "bc": max(bc.get(a, 0), bc.get(b, 0)),
                "zeros": edata.get("zeros", 0),
                "ratio": edata.get("ratio", 1),
                "slope": edata.get("slope", 0),
            })
    
    return results


def print_results(results):
    """Affiche les résultats de la batterie."""
    
    for group_name, label in [("pour", "50 POUR (orientés)"), ("contre", "50 CONTRE (aveugles)")]:
        group = results[group_name]
        if not group: continue
        
        correct = sum(1 for r in group if r["correct"])
        total = len(group)
        pct = correct / total * 100 if total > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"  {label} — SCORE: {correct}/{total} ({pct:.0f}%)")
        print(f"{'='*80}\n")
        
        print(f"{'ID':8s} {'Nom':37s} {'Réel':5s} {'Prédit':6s} {'OK?':4s} {'Conf':5s} {'BC':>7s} {'Zeros':>5s} {'Ratio':>7s} {'Slope':>7s}")
        print("-" * 100)
        
        for r in group:
            mark = "✅" if r["correct"] else "❌"
            print(f"{r['id']:8s} {r['name']:37s} {r['actual']:5s} {r['predicted']:6s} {mark:4s} "
                  f"{r['confidence']:4.0f}% {r['bc']:7.4f} {r['zeros']:5.0f} {r['ratio']:7.1f} {r['slope']:+7.1f}")
        
        # Matrice de confusion
        print(f"\n  MATRICE DE CONFUSION:")
        patterns = sorted(set(r["actual"] for r in group) | set(r["predicted"] for r in group))
        
        # Header
        print(f"  {'':8s}", end="")
        for p in patterns:
            print(f" →{p:5s}", end="")
        print(f"  {'Total':>6s}")
        print(f"  {'-'*8}", end="")
        for _ in patterns:
            print(f" {'-'*6}", end="")
        print(f"  {'-'*6}")
        
        for actual in patterns:
            row = [r for r in group if r["actual"] == actual]
            if not row: continue
            print(f"  {actual:8s}", end="")
            for predicted in patterns:
                count = sum(1 for r in row if r["predicted"] == predicted)
                if count > 0:
                    print(f" {count:5d} ", end="")
                else:
                    print(f"     . ", end="")
            print(f"  {len(row):5d}")
        
        # Par pattern: precision et recall
        print(f"\n  PAR PATTERN:")
        for pat in patterns:
            tp = sum(1 for r in group if r["actual"] == pat and r["predicted"] == pat)
            fp = sum(1 for r in group if r["actual"] != pat and r["predicted"] == pat)
            fn = sum(1 for r in group if r["actual"] == pat and r["predicted"] != pat)
            total_actual = sum(1 for r in group if r["actual"] == pat)
            
            precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            print(f"    {pat}: precision={precision:5.1f}%  recall={recall:5.1f}%  F1={f1:5.1f}%  (n={total_actual})")
        
        # Erreurs détaillées
        errors = [r for r in group if not r["correct"]]
        if errors:
            print(f"\n  ERREURS DÉTAILLÉES ({len(errors)}):")
            for r in errors:
                print(f"    {r['id']} {r['name']}: {r['actual']}→{r['predicted']} "
                      f"(scores: {', '.join(f'{k}={v}' for k,v in sorted(r['scores'].items(), key=lambda x:-x[1]))})")
    
    # SCORE GLOBAL
    all_results = results["pour"] + results["contre"]
    total_correct = sum(1 for r in all_results if r["correct"])
    total = len(all_results)
    pct = total_correct / total * 100 if total > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"  SCORE GLOBAL: {total_correct}/{total} ({pct:.1f}%)")
    print(f"{'='*80}")
    
    # Le test crucial: est-ce que le mycelium distingue P1/P4 de P2?
    p1p4 = [r for r in all_results if r["actual"] in ("P1", "P4")]
    p2 = [r for r in all_results if r["actual"] == "P2"]
    
    p1p4_correct = sum(1 for r in p1p4 if r["predicted"] in ("P1", "P4"))
    p2_correct = sum(1 for r in p2 if r["predicted"] == "P2")
    
    print(f"\n  TEST CRUCIAL — Le mycelium distingue-t-il TROUS de DENSE?")
    print(f"    P1+P4 classés comme trou: {p1p4_correct}/{len(p1p4)} ({p1p4_correct/max(len(p1p4),1)*100:.0f}%)")
    print(f"    P2 classés comme dense:   {p2_correct}/{len(p2)} ({p2_correct/max(len(p2),1)*100:.0f}%)")
    
    if p1p4_correct/max(len(p1p4),1) > 0.7 and p2_correct/max(len(p2),1) > 0.7:
        print(f"\n    🍄 LE MYCELIUM DISTINGUE LES TROUS DU BRUIT.")
        print(f"    Le médecin lit le thermomètre correctement.")
    elif p1p4_correct/max(len(p1p4),1) > 0.5 or p2_correct/max(len(p2),1) > 0.7:
        print(f"\n    🔶 Signal partiel. Le mycelium voit quelque chose mais pas tout.")
    else:
        print(f"\n    ⚠️ Pas de signal clair. Besoin de plus de données ou meilleurs seuils.")
    
    return all_results


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═"*80)
    print("  🍄 BATTERIE MYCELIUM — 50 POUR × 50 CONTRE")
    print("  Le mycelium peut-il prédire les patterns?")
    print("═"*80 + "\n")
    
    # Charger
    tests = load_tests()
    oriented = [t for t in tests if t["type"] == "oriented"]
    blind = [t for t in tests if t["type"] == "blind"]
    print(f"📊 {len(tests)} tests chargés ({len(oriented)} orientés + {len(blind)} aveugles)")
    
    # Graphe
    G = build_graph(tests)
    print(f"📈 Graphe: {G.number_of_nodes()} nœuds, {G.number_of_edges()} arêtes")
    
    # Batterie
    results = run_battery(G, tests)
    
    # Résultats
    all_results = print_results(results)
    
    # Export JSON
    export = {
        "date": "2026-02-21",
        "n_tests": len(all_results),
        "n_pour": len(results["pour"]),
        "n_contre": len(results["contre"]),
        "score_pour": sum(1 for r in results["pour"] if r["correct"]),
        "score_contre": sum(1 for r in results["contre"] if r["correct"]),
        "score_total": sum(1 for r in all_results if r["correct"]),
        "pct_total": sum(1 for r in all_results if r["correct"]) / max(len(all_results), 1) * 100,
        "results": [{k: v for k, v in r.items() if k != "scores"} for r in all_results]
    }
    
    out_path = DATA_DIR / "battery_mycelium_results.json"
    json.dump(export, open(out_path, "w"), indent=2, default=str)
    print(f"\n💾 Résultats exportés: {out_path}")
    
    print(f"\n{'═'*80}")
    print(f"  FIN BATTERIE — Sky × Claude — Versoix, minuit")
    print(f"{'═'*80}")
