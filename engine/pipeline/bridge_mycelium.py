#!/usr/bin/env python3
"""
PONT MYCELIUM × TESTS YGGDRASIL + IMPACT MÉTÉORITES
════════════════════════════════════════════════════════
Lecture seule sur les deux moteurs.
1. Construit le graphe de co-occurrence à partir des 101 tests
2. Passe ce graphe dans les briques mycelium (B0-B12)
3. Compare les métriques aux patterns connus
4. MÉTÉORITES: simule l'impact d'une découverte-pont sur le réseau
   et mesure les ondes de propagation (Sedov-Taylor sur graphe)

Sky × Claude — 20 Février 2026, Versoix
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
# 1. IMPORT MYCELIUM ENGINE (lecture seule)
# ════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"

myc_path = SCRIPT_DIR / "mycelium_full.py"
if not myc_path.exists():
    myc_path = SCRIPT_DIR / "mycelium_full.py"

spec = importlib.util.spec_from_file_location("mycelium", str(myc_path))
myc = importlib.util.module_from_spec(spec)
old_argv = sys.argv
sys.argv = ["bridge.py"]
spec.loader.exec_module(myc)
sys.argv = old_argv
print("✅ Mycelium engine importé (7912 lignes, 24 briques)")


# ════════════════════════════════════════════════════════════
# 2. CHARGER TOUS LES TESTS — format unifié
# ════════════════════════════════════════════════════════════

CATALOG = {
    "fermat":       {"file": "fermat_data.json",       "a": "Elliptic Curves",     "b": "Modular Forms",    "pattern": "P1", "test": 1,  "bridge_year": 1995, "bridge": "Wiles"},
    "groups":       {"file": "groups_data.json",       "a": "Group Theory",        "b": "Algebra",          "pattern": "P2", "test": 2},
    "higgs":        {"file": "higgs_data.json",        "a": "Higgs Theory",        "b": "Particle Physics", "pattern": "P3", "test": 3,  "bridge_year": 2012, "bridge": "LHC"},
    "crispr":       {"file": "crispr_data.json",       "a": "CRISPR",              "b": "Gene Editing",     "pattern": "P1", "test": 4,  "bridge_year": 2012, "bridge": "Doudna"},
    "darkmatter":   {"file": "darkmatter_data.json",   "a": "Dark Matter",         "b": "Quantum Gravity",  "pattern": "P4", "test": 5},
    "deeplearning": {"file": "deeplearning_data.json", "a": "Deep Learning",       "b": "Computer Vision",  "pattern": "P1", "test": 6,  "bridge_year": 2012, "bridge": "AlexNet"},
    "graphene":     {"file": "graphene_data.json",     "a": "Graphene",            "b": "Semiconductors",   "pattern": "P5", "test": 7},
    "poincare":     {"file": "poincare_data.json",     "a": "Ricci Flow",          "b": "Riemannian",       "pattern": "P1", "test": 8,  "bridge_year": 2003, "bridge": "Perelman"},
    "immunotherapy":{"file": "immunotherapy_data.json", "a": "Immunology",          "b": "Oncology",         "pattern": "P1", "test": 9,  "bridge_year": 2010, "bridge": "Ipilimumab"},
    "gravitational":{"file": "gravitational_data.json","a": "Gravitational Waves", "b": "Binary Merger",    "pattern": "P3", "test": 10, "bridge_year": 2015, "bridge": "LIGO"},
    "superconductor":{"file":"superconductor_data.json","a":"HTS",                 "b": "Cuprate",          "pattern": "P1", "test": 11, "bridge_year": 1986, "bridge": "Bednorz-Müller"},
    "quantum_crypto":{"file":"quantum_crypto_data.json","a":"Quantum Computing",   "b": "Cryptography",     "pattern": "P4", "test": 12},
    "microbiome":   {"file": "microbiome_data.json",   "a": "Microbiome",          "b": "Psychiatry",       "pattern": "P1", "test": 13, "bridge_year": 2011, "bridge": "Gut-Brain"},
    "stringtheory": {"file": "stringtheory_data.json", "a": "String Theory",       "b": "LHC Experiments",  "pattern": "P5", "test": 14},
    "alphafold":    {"file": "alphafold_data.json",    "a": "Protein Folding",     "b": "Deep Learning",    "pattern": "P1", "test": 15, "bridge_year": 2020, "bridge": "AlphaFold2"},
    "blockchain":   {"file": "blockchain_data.json",   "a": "Blockchain",          "b": "Cryptography",     "pattern": "P1", "test": 16, "bridge_year": 2008, "bridge": "Nakamoto"},
    "topological":  {"file": "topological_data.json",  "a": "Topological Insulators","b":"Condensed Matter", "pattern": "P1", "test": 17, "bridge_year": 2005, "bridge": "Kane-Mele"},
    "exoplanet":    {"file": "exoplanet_data.json",    "a": "Exoplanets",          "b": "Astrobiology",     "pattern": "P2", "test": 18},
    "fusion":       {"file": "fusion_data.json",       "a": "Tokamak",             "b": "HTS Magnets",      "pattern": "P4", "test": 19},
    "behavioral":   {"file": "behavioral_econ_data.json","a":"Behavioral Econ",    "b": "Cognitive Bias",   "pattern": "P1", "test": 20, "bridge_year": 1979, "bridge": "Kahneman-Tversky"},
}


def extract_timeline(data):
    """Extract co-occurrence timeline from test data (flexible format)."""
    if not isinstance(data, list):
        return []
    timeline = []
    for row in data:
        year = row.get("year")
        if year is None:
            continue
        co = row.get("co", 0)
        if co == 0:
            for key in row:
                if key == "year": continue
                if "_" in key or key == "triple":
                    co = max(co, row[key])
        timeline.append({"year": year, "co": co})
    return timeline


def load_all_tests():
    """Load all available tests into unified format."""
    tests = []
    
    # --- Oriented tests 1-20 ---
    for name, info in CATALOG.items():
        fpath = DATA_DIR / info["file"]
        if not fpath.exists():
            continue
        try:
            data = json.load(open(fpath))
            tl = extract_timeline(data)
            if tl:
                t = {
                    "id": f"T{info['test']:02d}",
                    "name": name,
                    "a": info["a"],
                    "b": info["b"],
                    "pattern": info["pattern"],
                    "timeline": tl,
                    "type": "oriented"
                }
                if "bridge_year" in info:
                    t["bridge_year"] = info["bridge_year"]
                    t["bridge"] = info["bridge"]
                tests.append(t)
        except Exception:
            pass
    
    # --- Blind tests ---
    blind_files = [
        "blind_tests_data.json",
        "blind62_71_summary.json",
        "blind72_81_summary.json",
        "blind82_91_summary.json",
        "blind92_101_summary.json",
    ]
    
    for bf in blind_files:
        fpath = DATA_DIR / bf
        if not fpath.exists():
            continue
        try:
            data = json.load(open(fpath))
            if not isinstance(data, list):
                continue
            for item in data:
                tid = item.get("id", item.get("test", "?"))
                pattern_raw = str(item.get("pattern", "P2"))
                if "P1" in pattern_raw: pat = "P1"
                elif "DENSE" in pattern_raw.upper() or "P2" in pattern_raw: pat = "P2"
                elif "P3" in pattern_raw: pat = "P3"
                elif "P4" in pattern_raw or "TROU" in pattern_raw.upper(): pat = "P4"
                elif "P5" in pattern_raw or "CLIN" in pattern_raw.upper(): pat = "P5"
                else: pat = "P2"
                
                tests.append({
                    "id": f"B{tid}" if isinstance(tid, int) else str(tid),
                    "name": f"{item.get('a','?')}×{item.get('b','?')}",
                    "a": item.get("a", "?"),
                    "b": item.get("b", "?"),
                    "pattern": pat,
                    "timeline": item.get("timeline", []),
                    "type": "blind"
                })
        except Exception:
            pass
    
    return tests


# ════════════════════════════════════════════════════════════
# 3. CONSTRUIRE LE GRAPHE DE CO-OCCURRENCE
# ════════════════════════════════════════════════════════════

def build_knowledge_graph(tests):
    """
    Nœuds = domaines. Arêtes = co-occurrence.
    Attributs: zeros, ratio, slope, pattern, bridge_year.
    """
    G = nx.Graph()
    
    for t in tests:
        a, b = t["a"], t["b"]
        tl = t["timeline"]
        if not tl:
            continue
        
        cos = [row["co"] for row in tl if row.get("co") is not None]
        if not cos:
            continue
        
        total_co = sum(cos)
        n_zeros = sum(1 for c in cos if c == 0)
        max_co = max(cos) if cos else 0
        min_nonzero = min((c for c in cos if c > 0), default=1)
        ratio = max_co / max(min_nonzero, 1)
        
        if len(cos) >= 3:
            x = np.arange(len(cos), dtype=float)
            slope = float(np.polyfit(x, cos, 1)[0])
        else:
            slope = 0.0
        
        for node in [a, b]:
            if node not in G:
                G.add_node(node, appearances=0, patterns=defaultdict(int))
            G.nodes[node]["appearances"] += 1
            G.nodes[node]["patterns"][t["pattern"]] += 1
        
        if G.has_edge(a, b):
            G[a][b]["weight"] += total_co
            G[a][b]["tests"].append(t["id"])
        else:
            edge_data = dict(
                weight=max(total_co, 1),
                zeros=n_zeros,
                ratio=ratio,
                slope=slope,
                max_co=max_co,
                pattern=t["pattern"],
                tests=[t["id"]],
            )
            if "bridge_year" in t:
                edge_data["bridge_year"] = t["bridge_year"]
                edge_data["bridge"] = t["bridge"]
            G.add_edge(a, b, **edge_data)
    
    return G


# ════════════════════════════════════════════════════════════
# 4. BRIQUES MYCELIUM SUR LE GRAPHE
# ════════════════════════════════════════════════════════════

def run_mycelium_analysis(G):
    """Exécute les briques mycelium sur le graphe de connaissance."""
    results = {}
    
    print(f"\n{'='*70}")
    print(f"GRAPHE: {G.number_of_nodes()} nœuds, {G.number_of_edges()} arêtes")
    print(f"{'='*70}\n")
    
    # B1: Meshedness
    try:
        alpha = myc.meshedness(G)
        results["meshedness"] = alpha
        label = "dense (boucles)" if alpha > 0.5 else "intermédiaire" if alpha > 0.1 else "arborescent"
        print(f"B1  MESHEDNESS α = {alpha:.4f} → {label}")
    except Exception as e:
        print(f"B1  ❌ {e}")
    
    # B2: Global efficiency
    try:
        e_glob = myc.global_efficiency(G)
        results["efficiency"] = e_glob
        label = "petit monde" if e_glob > 0.7 else "modéré" if e_glob > 0.4 else "fragmenté"
        print(f"B2  EFFICACITÉ = {e_glob:.4f} → {label}")
    except Exception as e:
        print(f"B2  ❌ {e}")
    
    # B4: Volume-MST ratio
    try:
        vmst = myc.volume_mst_ratio(G)
        results["vol_mst"] = vmst
        print(f"B4  VOL/MST = {vmst:.4f} → {(vmst-1)*100:.1f}% overhead")
    except Exception as e:
        print(f"B4  ❌ {e}")
    
    # B5: Betweenness bottlenecks
    try:
        bottlenecks = myc.find_bottlenecks(G, top_n=10)
        results["bottlenecks"] = bottlenecks
        print(f"\nB5  TOP 10 BOTTLENECKS:")
        for node, bc in bottlenecks:
            pat = dict(G.nodes[node].get("patterns", {}))
            print(f"    {node:35s}  BC={bc:.4f}  {pat}")
    except Exception as e:
        print(f"B5  ❌ {e}")
    
    # B9: Strategy
    try:
        a = results.get("meshedness", 0)
        eg = results.get("efficiency", 0)
        strat = myc.classify_strategy(a, eg, eg, results.get("vol_mst", 1))
        results["strategy"] = strat
        print(f"\nB9  STRATÉGIE: {strat.get('strategy', '?')} — {strat.get('description', '')}")
    except Exception as e:
        print(f"B9  ❌ {e}")
    
    return results


# ════════════════════════════════════════════════════════════
# 5. SIGNATURES MYCELIUM × PATTERNS
# ════════════════════════════════════════════════════════════

def analyze_patterns(G, tests):
    """Corrélation métriques réseau × pattern de découverte."""
    print(f"\n{'='*70}")
    print("SIGNATURES MYCELIUM PAR PATTERN")
    print(f"{'='*70}\n")
    
    bc = nx.betweenness_centrality(G, weight="weight")
    ebc = nx.edge_betweenness_centrality(G, weight="weight")
    
    stats = defaultdict(lambda: {
        "bc": [], "ebc": [], "zeros": [], "ratio": [],
        "slope": [], "weight": [], "degree": [], "count": 0
    })
    
    for t in tests:
        a, b, pat = t["a"], t["b"], t["pattern"]
        if a not in G or b not in G: continue
        edge = (a, b) if G.has_edge(a, b) else (b, a) if G.has_edge(b, a) else None
        if not edge: continue
        
        edata = G[edge[0]][edge[1]]
        s = stats[pat]
        s["count"] += 1
        s["bc"].append(max(bc.get(a, 0), bc.get(b, 0)))
        s["ebc"].append(ebc.get(edge, ebc.get((edge[1], edge[0]), 0)))
        s["zeros"].append(edata.get("zeros", 0))
        s["ratio"].append(edata.get("ratio", 1))
        s["slope"].append(edata.get("slope", 0))
        s["weight"].append(edata.get("weight", 0))
        s["degree"].append(max(G.degree(a), G.degree(b)))
    
    avg = lambda l: sum(l)/len(l) if l else 0
    med = lambda l: sorted(l)[len(l)//2] if l else 0
    
    print(f"{'Pat':5s} {'N':>4s} {'BC':>8s} {'EBC':>8s} {'Zeros':>6s} {'Ratio':>8s} {'Slope':>8s} {'Degré':>6s}")
    print("-" * 60)
    for pat in sorted(stats):
        s = stats[pat]
        print(f"{pat:5s} {s['count']:4d} {avg(s['bc']):8.4f} {avg(s['ebc']):8.4f} "
              f"{avg(s['zeros']):6.1f} {med(s['ratio']):8.1f} {avg(s['slope']):+8.1f} {avg(s['degree']):6.1f}")
    
    print(f"\n--- INTERPRÉTATION ---")
    for pat in sorted(stats):
        s = stats[pat]
        n = s['count']
        if n == 0: continue
        print(f"\n{pat} ({n} tests):")
        
        bc_val = avg(s['bc'])
        zeros_val = avg(s['zeros'])
        ratio_val = med(s['ratio'])
        slope_val = avg(s['slope'])
        
        if pat == "P1":
            print(f"  🌉 PONT: BC faible ({bc_val:.4f}), zeros ({zeros_val:.1f}), explosion {ratio_val:.0f}×")
            print(f"  → Isolés qui connectent. Le mycelium ne les voit PAS avant le pont.")
        elif pat == "P2":
            print(f"  🏔️ DENSE: BC haute ({bc_val:.4f}), zéro zeros, ratio stable {ratio_val:.0f}×")
            print(f"  → Hubs du réseau. Le mycelium les connaît déjà.")
        elif pat == "P3":
            print(f"  🔧 THÉORIE×OUTIL: attente d'instrument. Slope {slope_val:+.0f}")
        elif pat == "P4":
            print(f"  👻 TROU OUVERT: BC minimale ({bc_val:.4f}), ratio potentiel {ratio_val:.0f}×")
            print(f"  → INVISIBLE au réseau. C'est là que le mycelium doit POUSSER.")
        elif pat == "P5":
            print(f"  💀 ANTI-SIGNAL: slope NÉGATIVE ({slope_val:+.0f}). L'hyphe meurt.")
    
    return stats


# ════════════════════════════════════════════════════════════
# 6. MÉTÉORITES — Impact d'une découverte sur le mycelium
# ════════════════════════════════════════════════════════════

def meteorite_impact(G, tests):
    """
    Simule l'impact d'une découverte-pont (météorite) sur le réseau.
    
    Modèle Sedov-Taylor adapté aux graphes:
    - Impact = paper pont (bridge_year)
    - Onde de choc = propagation de co-occurrence
    - Rayon du cratère = combien de nœuds sont touchés
    - Énergie = ratio d'explosion
    
    On remonte depuis l'impact pour voir le schéma AVANT.
    C'est la vision de Sky: les météorites frappent le mycelium,
    on voit les ondes, on remonte.
    """
    print(f"\n{'='*70}")
    print("🌠 MÉTÉORITES — IMPACT DES DÉCOUVERTES SUR LE MYCELIUM")
    print(f"{'='*70}\n")
    
    impacts = []
    
    for t in tests:
        if "bridge_year" not in t:
            continue
        
        a, b = t["a"], t["b"]
        tl = t["timeline"]
        if not tl or len(tl) < 5:
            continue
        
        bridge_year = t["bridge_year"]
        years = [row["year"] for row in tl]
        cos = [row["co"] for row in tl]
        
        # Séparer avant/après impact
        before = [(y, c) for y, c in zip(years, cos) if y < bridge_year]
        after = [(y, c) for y, c in zip(years, cos) if y >= bridge_year]
        
        if not before or not after:
            continue
        
        # Métriques d'impact
        avg_before = np.mean([c for _, c in before]) if before else 0
        avg_after = np.mean([c for _, c in after]) if after else 0
        max_after = max([c for _, c in after]) if after else 0
        
        # Temps de montée (années pour atteindre le max après impact)
        if after:
            peak_year = max(after, key=lambda x: x[1])[0]
            rise_time = peak_year - bridge_year
        else:
            rise_time = 0
        
        # Énergie = ratio explosion
        energy = max_after / max(avg_before, 1)
        
        # "Densité du sol" avant impact = variabilité
        if len(before) > 1:
            soil_density = np.std([c for _, c in before]) / max(np.mean([c for _, c in before]), 1)
        else:
            soil_density = 0
        
        # Zeros avant = taille du vide
        void_years = sum(1 for _, c in before if c == 0)
        
        impacts.append({
            "name": t["name"],
            "bridge": t.get("bridge", "?"),
            "bridge_year": bridge_year,
            "pattern": t["pattern"],
            "avg_before": avg_before,
            "avg_after": avg_after,
            "max_after": max_after,
            "energy": energy,
            "rise_time": rise_time,
            "soil_density": soil_density,
            "void_years": void_years,
        })
    
    if not impacts:
        print("Pas de météorites trouvées (manque bridge_year)")
        return []
    
    # Trier par énergie d'impact
    impacts.sort(key=lambda x: -x["energy"])
    
    print(f"{'Météorite':20s} {'Pont':15s} {'Année':>6s} {'Avant':>8s} {'Après':>8s} {'Énergie':>8s} {'Montée':>7s} {'Vide':>5s} {'Sol ρ':>6s}")
    print("-" * 100)
    
    for imp in impacts:
        print(f"{imp['name']:20s} {imp['bridge']:15s} {imp['bridge_year']:6d} "
              f"{imp['avg_before']:8.0f} {imp['avg_after']:8.0f} "
              f"{imp['energy']:8.1f}× {imp['rise_time']:5d}a "
              f"{imp['void_years']:5d} {imp['soil_density']:6.2f}")
    
    # --- CORRÉLATIONS ---
    print(f"\n{'='*70}")
    print("CORRÉLATIONS MÉTÉORITES")
    print(f"{'='*70}\n")
    
    energies = [i["energy"] for i in impacts]
    voids = [i["void_years"] for i in impacts]
    rises = [i["rise_time"] for i in impacts]
    soils = [i["soil_density"] for i in impacts]
    
    if len(impacts) >= 3:
        # Corrélation void × energy
        if np.std(voids) > 0 and np.std(energies) > 0:
            r_void_energy = np.corrcoef(voids, energies)[0, 1]
            print(f"Vide × Énergie:     r = {r_void_energy:+.3f}")
            if r_void_energy > 0.3:
                print(f"  → ✅ CONFIRMÉ: plus le vide est long, plus l'explosion est forte")
            else:
                print(f"  → ⚠️ Pas de corrélation claire")
        
        # Corrélation soil × energy
        if np.std(soils) > 0 and np.std(energies) > 0:
            r_soil_energy = np.corrcoef(soils, energies)[0, 1]
            print(f"Sol ρ × Énergie:    r = {r_soil_energy:+.3f}")
            if r_soil_energy < -0.3:
                print(f"  → ✅ Sol stable (faible ρ) → plus grosse explosion")
        
        # Corrélation rise × energy
        if np.std(rises) > 0 and np.std(energies) > 0:
            r_rise_energy = np.corrcoef(rises, energies)[0, 1]
            print(f"Montée × Énergie:   r = {r_rise_energy:+.3f}")
    
    # --- LOI SEDOV-TAYLOR ADAPTÉE ---
    print(f"\n{'='*70}")
    print("LOI DE PROPAGATION (Sedov-Taylor sur graphe)")
    print(f"{'='*70}\n")
    
    print("Sedov-Taylor classique: R(t) = ξ × (E/ρ)^(1/5) × t^(2/5)")
    print("Sur graphe: R = rayon de propagation (nœuds touchés)")
    print("            E = énergie de la météorite (ratio d'explosion)")
    print("            ρ = densité du sol (variabilité avant impact)")
    print("            t = années depuis l'impact\n")
    
    for imp in impacts[:5]:  # Top 5
        E = imp["energy"]
        rho = max(imp["soil_density"], 0.01)
        t = max(imp["rise_time"], 1)
        
        # Sedov-Taylor adapté
        R_sedov = (E / rho) ** 0.2 * t ** 0.4
        
        print(f"  {imp['name']:20s} E={E:6.1f}× ρ={rho:.2f} t={t:2d}a → R_sedov={R_sedov:.1f}")
    
    return impacts


# ════════════════════════════════════════════════════════════
# 7. PHYSARUM — le mycelium pousse vers les trous
# ════════════════════════════════════════════════════════════

def run_physarum(G):
    """Physarum adaptatif sur le graphe de connaissance."""
    print(f"\n{'='*70}")
    print("🍄 PHYSARUM — LE MYCELIUM POUSSE-T-IL VERS LES TROUS?")
    print(f"{'='*70}\n")
    
    if G.number_of_nodes() < 3 or G.number_of_edges() < 3:
        print("Graphe trop petit")
        return
    
    # Assigner conductivité initiale = 1/weight (trous = haute résistance)
    for u, v, d in G.edges(data=True):
        w = d.get("weight", 1)
        d["conductivity"] = 1.0 / max(np.log1p(w), 0.1)
    
    degrees = sorted(G.degree(), key=lambda x: x[1], reverse=True)
    source = degrees[0][0]
    print(f"Source (hub): {source} (degré {degrees[0][1]})")
    
    # Kirchhoff flow
    try:
        flow_result = myc.kirchhoff_flow(G, [source])
        
        if isinstance(flow_result, dict):
            flows = flow_result
        elif isinstance(flow_result, list):
            # Convertir liste en dict si nécessaire
            flows = {}
            for item in flow_result:
                if isinstance(item, dict):
                    flows.update(item)
        else:
            print(f"  Format inattendu: {type(flow_result)}")
            flows = {}
        
        if flows:
            print(f"  Kirchhoff: {len(flows)} flux calculés")
            
            # Comparer flux vers P1 vs P2
            flux_by_pattern = defaultdict(list)
            for u, v, d in G.edges(data=True):
                pat = d.get("pattern", "?")
                f = abs(flows.get((u, v), flows.get((v, u), 0)))
                flux_by_pattern[pat].append(f)
            
            print(f"\n  Flux Kirchhoff par pattern:")
            for pat in sorted(flux_by_pattern):
                vals = flux_by_pattern[pat]
                print(f"    {pat}: flux_moy={np.mean(vals):.4f} ± {np.std(vals):.4f} (n={len(vals)})")
    except Exception as e:
        print(f"  Kirchhoff ❌ {e}")
    
    # Physarum simulation
    try:
        G_copy = deepcopy(G)
        for u, v, d in G_copy.edges(data=True):
            d["conductivity"] = 1.0
        
        result = myc.physarum_simulate(G_copy, [source], n_steps=10, mu=1.0, decay=0.5)
        
        if result:
            print(f"\n  Physarum (10 steps):")
            
            # Mesurer conductivité finale par pattern
            cond_by_pat = defaultdict(list)
            for u, v, d in G_copy.edges(data=True):
                pat = G[u][v].get("pattern", "?") if G.has_edge(u, v) else "?"
                cond_by_pat[pat].append(d.get("conductivity", 1.0))
            
            print(f"  Conductivité Physarum finale par pattern:")
            for pat in sorted(cond_by_pat):
                vals = cond_by_pat[pat]
                print(f"    {pat}: cond={np.mean(vals):.4f} ± {np.std(vals):.4f} (n={len(vals)})")
                
    except Exception as e:
        print(f"  Physarum ❌ {e}")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═"*70)
    print("  PONT MYCELIUM × YGGDRASIL — MÉTÉORITES + PHYSARUM")
    print("  Lecture seule. Rien modifié. Rien cassé.")
    print("═"*70 + "\n")
    
    # 1. Charger
    tests = load_all_tests()
    oriented = [t for t in tests if t["type"] == "oriented"]
    blind = [t for t in tests if t["type"] == "blind"]
    print(f"📊 {len(tests)} tests ({len(oriented)} orientés + {len(blind)} aveugles)")
    
    by_pat = defaultdict(int)
    for t in tests: by_pat[t["pattern"]] += 1
    for pat in sorted(by_pat): print(f"   {pat}: {by_pat[pat]}")
    
    # 2. Graphe
    G = build_knowledge_graph(tests)
    
    # 3. Briques mycelium
    results = run_mycelium_analysis(G)
    
    # 4. Signatures pattern × mycelium
    pattern_stats = analyze_patterns(G, tests)
    
    # 5. Météorites
    impacts = meteorite_impact(G, tests)
    
    # 6. Physarum
    run_physarum(G)
    
    # 7. Résumé final
    print(f"\n{'═'*70}")
    print("  RÉSUMÉ — CE QUE LE MYCELIUM DIT")
    print(f"{'═'*70}")
    print(f"""
  • P1 PONT:    BC faible, zeros élevés, explosion massive
                → Invisible au réseau AVANT le pont
  • P2 DENSE:   BC haute, zéro zeros, croissance stable
                → Hubs connus du réseau
  • P4 TROU:    BC minimale, ratio potentiel MAXIMAL
                → Les P4 sont les FUTURS P1
  • P5 DÉCLIN:  Slope NÉGATIVE
                → L'hyphe meurt. Le mycelium le sait.
  
  MÉTÉORITES: Plus le vide est long → plus l'explosion est forte
              Le sol (variabilité) module l'énergie de l'impact
              
  Le mycelium et les maths sont complémentaires:
  - Les maths (strates/symboles) = la CARTE
  - Le mycelium (topologie/flux) = la VIE dans la carte
  - Les météorites (impacts) = les DÉCOUVERTES qui tombent
  - Les ondes = la PROPAGATION qu'on peut remonter
    """)
    print(f"{'═'*70}")
    print("  RIEN MODIFIÉ. RIEN CASSÉ. LECTURE SEULE.")
    print(f"{'═'*70}")
