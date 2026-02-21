#!/usr/bin/env python3
"""
CROSS-ANALYSIS: Physarum Flux × Works Count
============================================
Objectif: Identifier les contradictions entre importance structurelle
(flux Physarum / betweenness) et activité scientifique (works_count).

Stratégie:
  1. Graphe domaine (85 nœuds) → Physarum + BC complet
  2. Graphe concept k-NN (21K nœuds) → degree + clustering local
  3. Croisement: flux structurel vs works_count → contradictions

Output:
  - Concepts isolés (haut wc, faible flux)
  - Ponts cachés (faible wc, fort flux)
  - Vides fertiles P4 (zones inter-domaines sous-explorées)
  - JSON export pour viz

Sky — 21 février 2026
"""

import json
import sys
import os
import numpy as np
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import networkx as nx

try:
    from mycelium_full import graph_from_edges, kirchhoff_flow, physarum_simulate
    HAS_MYCELIUM = True
except ImportError:
    HAS_MYCELIUM = False
    print("⚠️  mycelium_full.py non trouvé, fallback networkx pur")

DATA_DIR = Path(__file__).parent.parent / "data"


def load_data():
    print("═" * 60)
    print("  CHARGEMENT DES DONNÉES")
    print("═" * 60)

    with open(DATA_DIR / "strates_export_v2.json") as f:
        strates = json.load(f)
    s0 = strates["strates"][0]["symbols"]
    print(f"  S0: {len(s0)} symboles")

    with open(DATA_DIR / "domain_cooccurrence_matrix.json") as f:
        cooc = json.load(f)
    domains = cooc["domains"]
    matrix = np.array(cooc["matrix"], dtype=float)
    print(f"  Co-occurrence: {len(domains)}×{len(domains)} domaines")

    with open(DATA_DIR / "escaliers_unified.json") as f:
        esc = json.load(f)
    print(f"  Escaliers: {len(esc['geo'])} geo + {len(esc['key'])} key")

    return s0, domains, matrix, esc


def build_domain_graph(domains, matrix):
    print("\n" + "═" * 60)
    print("  PHASE 1: GRAPHE DOMAINE (85 nœuds)")
    print("═" * 60)

    diag = np.diag(matrix).copy()
    diag[diag == 0] = 1
    norm = np.sqrt(np.outer(diag, diag))
    sim = matrix / norm
    np.fill_diagonal(sim, 0)

    flat = sim[np.triu_indices_from(sim, k=1)]
    threshold = np.percentile(flat[flat > 0], 70)

    edges = []
    for i in range(len(domains)):
        for j in range(i + 1, len(domains)):
            if sim[i][j] > threshold:
                edges.append((domains[i], domains[j], float(sim[i][j])))

    if HAS_MYCELIUM:
        G = graph_from_edges(edges)
    else:
        G = nx.Graph()
        for u, v, w in edges:
            G.add_edge(u, v, weight=w)

    print(f"  Seuil similarité: {threshold:.4f}")
    print(f"  Arêtes: {G.number_of_edges()} (sur {len(domains)} domaines)")
    print(f"  Composantes: {nx.number_connected_components(G)}")

    return G, sim


def run_physarum_domain(G, domains):
    print("\n  → Betweenness Centrality...")
    bc = nx.betweenness_centrality(G, weight="weight")

    print("  → Physarum simulation...")
    all_nodes = list(G.nodes())

    if HAS_MYCELIUM and len(all_nodes) > 2:
        # Sources need to be dict {node: flow}
        src_names = []
        for s in ["algèbre", "biologie", "quantique", "informatique", "chimie"]:
            if s in G.nodes():
                src_names.append(s)
        if not src_names:
            src_names = all_nodes[:3]

        # Build balanced source/sink dict: sources inject, sinks absorb
        n_src = len(src_names)
        # All other nodes are sinks
        sink_names = [n for n in all_nodes if n not in src_names]
        sources_dict = {}
        for s in src_names:
            sources_dict[s] = 1.0 / n_src
        for s in sink_names:
            sources_dict[s] = -1.0 / len(sink_names)

        try:
            result = physarum_simulate(
                G, sources=sources_dict, n_steps=30, mu=1.0, decay=0.5, h=0.2
            )
            flows = result["final_flows"]
            node_flux = defaultdict(float)
            for (u, v), f in flows.items():
                node_flux[u] += abs(f)
                node_flux[v] += abs(f)
            print(f"  → Physarum: {len(flows)} arêtes avec flux, "
                  f"converged={result['converged']}, steps={result['steps']}")
            print(f"     thick={len(result['thick_edges'])}, dead={len(result['dead_edges'])}")
        except Exception as e:
            print(f"  ⚠️  Physarum failed: {e}, fallback degree centrality")
            node_flux = dict(nx.degree_centrality(G))
    else:
        node_flux = dict(nx.degree_centrality(G))

    bc_max = max(bc.values()) if bc else 1
    flux_max = max(node_flux.values()) if node_flux else 1

    domain_metrics = {}
    for d in G.nodes():
        domain_metrics[d] = {
            "bc": bc.get(d, 0) / bc_max if bc_max > 0 else 0,
            "flux": node_flux.get(d, 0) / flux_max if flux_max > 0 else 0,
            "structural_score": (
                0.5 * (bc.get(d, 0) / bc_max if bc_max > 0 else 0)
                + 0.5 * (node_flux.get(d, 0) / flux_max if flux_max > 0 else 0)
            ),
        }

    sorted_domains = sorted(
        domain_metrics.items(), key=lambda x: x[1]["structural_score"], reverse=True
    )
    print("\n  Top 10 domaines structurellement importants:")
    for d, m in sorted_domains[:10]:
        print(f"    {d:25s}  BC={m['bc']:.3f}  Flux={m['flux']:.3f}  Score={m['structural_score']:.3f}")

    return domain_metrics


def build_concept_knn(s0, k=8):
    print("\n" + "═" * 60)
    print("  PHASE 2: GRAPHE CONCEPT k-NN (S0)")
    print("═" * 60)

    concepts = [c for c in s0 if c.get("px") is not None and c.get("pz") is not None]
    print(f"  Concepts avec positions: {len(concepts)}")

    positions = np.array([[c["px"], c["pz"]] for c in concepts])

    from scipy.spatial import cKDTree
    tree = cKDTree(positions)
    print(f"  Building k={k} nearest neighbors...")

    distances, indices = tree.query(positions, k=k + 1)

    G = nx.Graph()
    for i in range(len(concepts)):
        node_id = i
        G.add_node(node_id)
        for j_idx in range(1, k + 1):
            j = int(indices[i][j_idx])
            dist = float(distances[i][j_idx])
            if dist > 0:
                G.add_edge(node_id, j, weight=1.0 / (dist + 1e-6))

    print(f"  Nœuds: {G.number_of_nodes()}, Arêtes: {G.number_of_edges()}")

    print("  → Degree centrality...")
    degree = nx.degree_centrality(G)

    print("  → Clustering coefficient...")
    clustering = nx.clustering(G, weight="weight")

    concept_metrics = {}
    for i, c in enumerate(concepts):
        concept_metrics[i] = {
            "s": c["s"],
            "from": c.get("from", ""),
            "domain": c.get("domain", ""),
            "works_count": c.get("works_count", 0),
            "cube": c.get("cube", ""),
            "px": c["px"],
            "pz": c["pz"],
            "degree": degree.get(i, 0),
            "clustering": clustering.get(i, 0),
        }

    return concept_metrics, concepts


def cross_analysis(concept_metrics, domain_metrics, escaliers):
    print("\n" + "═" * 60)
    print("  PHASE 3: CROISEMENT FLUX × WORKS_COUNT")
    print("═" * 60)

    for idx, cm in concept_metrics.items():
        d = cm["domain"]
        dm = domain_metrics.get(d, {"structural_score": 0, "bc": 0, "flux": 0})
        cm["domain_structural"] = dm["structural_score"]
        cm["domain_bc"] = dm["bc"]
        cm["domain_flux"] = dm["flux"]
        cm["structural_importance"] = (
            0.6 * dm["structural_score"] + 0.3 * cm["degree"] + 0.1 * cm["clustering"]
        )

    active = [cm for cm in concept_metrics.values() if cm["works_count"] > 0]
    print(f"  Concepts actifs (wc > 0): {len(active)}")

    if not active:
        print("  ⚠️  Aucun concept actif!")
        return [], [], [], {}

    # Normalize wc per domain
    domain_wc = defaultdict(list)
    for cm in active:
        domain_wc[cm["domain"]].append(cm["works_count"])

    domain_q1, domain_q3 = {}, {}
    for d, wcs in domain_wc.items():
        if wcs:
            domain_q1[d] = np.percentile(wcs, 25)
            domain_q3[d] = np.percentile(wcs, 75)

    for cm in active:
        d = cm["domain"]
        q1 = domain_q1.get(d, 1)
        q3 = domain_q3.get(d, max(q1, 1))
        if q3 > q1 > 0:
            cm["wc_normalized"] = (cm["works_count"] - q1) / (q3 - q1)
        elif q1 > 0:
            cm["wc_normalized"] = cm["works_count"] / q1
        else:
            cm["wc_normalized"] = 0

    # ═══════════ CONTRADICTIONS ═══════════

    wc_vals = [c["wc_normalized"] for c in active]
    struct_vals = [c["structural_importance"] for c in active]

    wc_p80 = np.percentile(wc_vals, 80)
    struct_p20 = np.percentile(struct_vals, 20)
    wc_p30 = np.percentile(wc_vals, 30)
    struct_p80 = np.percentile(struct_vals, 80)

    # 1. ISOLATED HUBS
    isolated_hubs = sorted(
        [c for c in active if c["wc_normalized"] > wc_p80 and c["structural_importance"] < struct_p20],
        key=lambda x: x["wc_normalized"], reverse=True
    )

    # 2. HIDDEN BRIDGES
    hidden_bridges = sorted(
        [c for c in active if c["wc_normalized"] < wc_p30 and c["structural_importance"] > struct_p80],
        key=lambda x: x["structural_importance"], reverse=True
    )

    # 3. FERTILE VOIDS (P4): Musée concepts with low connectivity
    escalier_symbols = set()
    for e in escaliers.get("geo", []):
        escalier_symbols.add(e["s"])
    for e in escaliers.get("key", []):
        escalier_symbols.add(e["s"])

    musee_all = [c for c in concept_metrics.values()
                 if c["cube"] == "musee" and c["works_count"] > 0]
    if musee_all:
        musee_deg_med = np.median([c["degree"] for c in musee_all])
        fertile_voids = sorted(
            [c for c in musee_all
             if c["degree"] < musee_deg_med
             and c["s"] not in escalier_symbols],
            key=lambda x: x["degree"]
        )
    else:
        fertile_voids = []

    # 4. DOMAIN CONTRADICTIONS (rank-based to avoid scale issues)
    domain_contradiction = {}
    # Compute per-domain averages
    domain_stats = {}
    for d in set(c["domain"] for c in active):
        d_concepts = [c for c in active if c["domain"] == d]
        if len(d_concepts) < 5:
            continue
        avg_wc = np.mean([c["works_count"] for c in d_concepts])
        avg_struct = np.mean([c["structural_importance"] for c in d_concepts])
        domain_stats[d] = {"n": len(d_concepts), "avg_wc": avg_wc, "avg_struct": avg_struct}

    # Rank both metrics across domains
    if domain_stats:
        all_wc = [v["avg_wc"] for v in domain_stats.values()]
        all_struct = [v["avg_struct"] for v in domain_stats.values()]
        wc_sorted = sorted(all_wc)
        struct_sorted = sorted(all_struct)

        for d, v in domain_stats.items():
            wc_rank = wc_sorted.index(v["avg_wc"]) / max(len(wc_sorted) - 1, 1)
            struct_rank = struct_sorted.index(v["avg_struct"]) / max(len(struct_sorted) - 1, 1)
            gap = wc_rank - struct_rank  # positive = more cited than connected

            domain_contradiction[d] = {
                "n_concepts": v["n"],
                "avg_wc": round(float(v["avg_wc"]), 0),
                "avg_structural": round(float(v["avg_struct"]), 4),
                "wc_rank": round(float(wc_rank), 3),
                "struct_rank": round(float(struct_rank), 3),
                "gap": round(float(gap), 3),
                "interpretation": (
                    "OVER-CITED" if gap > 0.3
                    else "UNDER-CITED" if gap < -0.3
                    else "ÉQUILIBRÉ"
                ),
            }

    return isolated_hubs, hidden_bridges, fertile_voids, domain_contradiction


def print_report(isolated, bridges, voids, domain_map, domain_metrics):
    print("\n" + "█" * 60)
    print("█" + " " * 58 + "█")
    print("█   RAPPORT: PHYSARUM × WORKS_COUNT — CONTRADICTIONS    █")
    print("█" + " " * 58 + "█")
    print("█" * 60)

    print(f"\n{'─' * 60}")
    print(f"  🏝️  CONCEPTS ISOLÉS (haut wc, faible flux): {len(isolated)}")
    print(f"{'─' * 60}")
    print(f"  = Populaires mais déconnectés du réseau")
    for c in isolated[:20]:
        print(f"  {c['s']:20s} | wc={c['works_count']:>8,} | struct={c['structural_importance']:.3f} | {c['domain']}")

    print(f"\n{'─' * 60}")
    print(f"  🌉  PONTS CACHÉS (faible wc, fort flux): {len(bridges)}")
    print(f"{'─' * 60}")
    print(f"  = Structurellement critiques mais sous-cités")
    for c in bridges[:20]:
        print(f"  {c['s']:20s} | wc={c['works_count']:>8,} | struct={c['structural_importance']:.3f} | {c['domain']}")

    print(f"\n{'─' * 60}")
    print(f"  🕳️  VIDES FERTILES P4 (musée, isolés, inter-domaines): {len(voids)}")
    print(f"{'─' * 60}")
    print(f"  = Zones à explorer — futurs ponts potentiels")
    for c in voids[:20]:
        print(f"  {c['s']:20s} | wc={c['works_count']:>8,} | deg={c['degree']:.4f} | {c['domain']}")

    print(f"\n{'─' * 60}")
    print(f"  🔥  CONTRADICTIONS PAR DOMAINE")
    print(f"{'─' * 60}")
    over = {k: v for k, v in domain_map.items() if "OVER" in v["interpretation"]}
    under = {k: v for k, v in domain_map.items() if "UNDER" in v["interpretation"]}

    if over:
        print(f"\n  OVER-CITED (beaucoup de papers, peu de structure):")
        for d, v in sorted(over.items(), key=lambda x: x[1]["gap"], reverse=True):
            print(f"    {d:25s} gap={v['gap']:+.3f}  wc_rank={v['wc_rank']:.2f}  struct_rank={v['struct_rank']:.2f}  (n={v['n_concepts']})")

    if under:
        print(f"\n  UNDER-CITED (forte structure, peu de papers):")
        for d, v in sorted(under.items(), key=lambda x: x[1]["gap"]):
            print(f"    {d:25s} gap={v['gap']:+.3f}  wc_rank={v['wc_rank']:.2f}  struct_rank={v['struct_rank']:.2f}  (n={v['n_concepts']})")

    equil = {k: v for k, v in domain_map.items() if "ÉQUILIBRÉ" in v["interpretation"]}
    print(f"\n  ÉQUILIBRÉS: {len(equil)} domaines")


def export_results(isolated, bridges, voids, domain_map, domain_metrics, concept_metrics):
    out = {
        "meta": {
            "date": "2026-02-21",
            "n_isolated": len(isolated),
            "n_bridges": len(bridges),
            "n_voids": len(voids),
            "n_domains_over": sum(1 for v in domain_map.values() if "OVER" in v["interpretation"]),
            "n_domains_under": sum(1 for v in domain_map.values() if "UNDER" in v["interpretation"]),
        },
        "isolated_hubs": [
            {"s": c["s"], "from": c["from"], "domain": c["domain"],
             "wc": c["works_count"], "struct": round(c["structural_importance"], 4),
             "px": c["px"], "pz": c["pz"]}
            for c in isolated[:50]
        ],
        "hidden_bridges": [
            {"s": c["s"], "from": c["from"], "domain": c["domain"],
             "wc": c["works_count"], "struct": round(c["structural_importance"], 4),
             "px": c["px"], "pz": c["pz"]}
            for c in bridges[:50]
        ],
        "fertile_voids": [
            {"s": c["s"], "from": c["from"], "domain": c["domain"],
             "wc": c["works_count"], "degree": round(c["degree"], 4),
             "px": c["px"], "pz": c["pz"]}
            for c in voids[:100]
        ],
        "domain_contradictions": domain_map,
        "domain_structural": {
            d: round(m["structural_score"], 4) for d, m in domain_metrics.items()
        },
    }

    outpath = DATA_DIR / "cross_physarum_wc.json"
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n  💾 Export: {outpath}")
    print(f"     {os.path.getsize(outpath):,} bytes")
    return out


if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  YGGDRASIL — CROSS PHYSARUM × WORKS_COUNT")
    print("  Contradictions • Ponts cachés • Vides fertiles")
    print("═" * 60 + "\n")

    s0, domains, matrix, escaliers = load_data()
    G_domain, sim_matrix = build_domain_graph(domains, matrix)
    domain_metrics = run_physarum_domain(G_domain, domains)
    concept_metrics, concepts = build_concept_knn(s0, k=8)
    isolated, bridges, voids, domain_map = cross_analysis(
        concept_metrics, domain_metrics, escaliers
    )
    print_report(isolated, bridges, voids, domain_map, domain_metrics)
    results = export_results(isolated, bridges, voids, domain_map, domain_metrics, concept_metrics)

    print("\n" + "═" * 60)
    print("  ✅ ANALYSE TERMINÉE")
    print("═" * 60)
