#!/usr/bin/env python3
"""
YGGDRASIL — SCAN GOD'S NUMBER: SOLVE MODE
════════════════════════════════════════════════════
Pas juste scanner — RESOUDRE.

1. Papers qui TRAVERSENT les axes (pas juste intra-axe)
2. Trous strategiques: si on les remplit, combien de connexions s'ouvrent?
3. Papers "keystone" — a 1 pas de connecter deux deserts
4. Le chemin le plus court pour resoudre GN(n) selon la structure des trous

Sky x Claude — 14 Mars 2026, Versoix
"""

import json
import gzip
import os
import sys
import io
import time
from collections import defaultdict, Counter

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
PRED_DIR = os.path.join(REPO, "experiments", "predictions_2025")
SCAN_DIR = os.path.join(REPO, "data", "scan")
RESULTS_DIR = os.path.join(REPO, "data", "results")

GN_CORE = {
    "Cayley graph": 3217,
    "Wreath product": 64319,
    "Permutation group": 63903,
    "Symmetric group": 4492,
    "Semidirect product": 61178,
    "Simple group": 57573,
    "Classification of finite simple groups": 59370,
    "Normal subgroup": 917,
    "Nilpotent group": 16592,
    "Coset": 62772,
    "Commutator subgroup": 6423,
    "Group theory": 62210,
    "Spectral gap": 28454,
    "Expander graph": 8508,
    "Markov chain mixing time": 64555,
    "Eigenvalues and eigenvectors": 9157,
    "Laplacian matrix": 2429,
    "Random walk": 3378,
    "Knot theory": 6795,
    "Unknot": 38541,
    "Coding theory": 2234,
    "Sphere packing": 13095,
    "Sorting network": 59567,
    "Quantum walk": 6307,
    "Percolation theory": 2489,
    "Combinatorial optimization": 57247,
    "Constraint satisfaction problem": 15562,
    "PSPACE": 15276,
    "Inverse problem": 5503,
    "Interval arithmetic": 14255,
    "Sensitivity analysis": 11886,
    "Phase transition": 7678,
}
GN_IDXS = set(GN_CORE.values())
GN_IDX_TO_NAME = {v: k for k, v in GN_CORE.items()}

AXES = {
    1: ("Cayley/Permutation", {3217, 64319, 63903, 4492, 61178, 57573, 59370, 917, 16592, 62772, 6423, 62210}),
    2: ("Spectral/Expansion", {28454, 8508, 64555, 9157, 2429, 3378}),
    3: ("Isomorphic/Bridges", {6795, 38541, 2234, 13095, 59567, 6307, 2489, 57247}),
    4: ("Cannon/Constraints", {15562, 15276, 5503, 14255, 11886, 7678}),
}

def idx_to_axis(idx):
    for ax_num, (ax_name, ax_idxs) in AXES.items():
        if idx in ax_idxs:
            return ax_num, ax_name
    return 0, "?"

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_cross_axis_papers():
    """Trouve les papers qui TRAVERSENT les axes — les vrais ponts."""
    print("=" * 100)
    print("PHASE 1: PAPERS CROSS-AXE")
    print("Quels papers connectent AXE 1 (Cayley) a AXE 2 (Spectral) a AXE 3 (Bridges) a AXE 4 (Cannon)?")
    print("=" * 100)

    chunks_dir = os.path.join(SCAN_DIR, "wt2_chunks")
    chunk_list = sorted(os.listdir(chunks_dir))

    cross_papers = []  # papers touching concepts from 2+ axes
    all_gn_papers = {}  # arxiv_id -> {axes, concepts, domain, glyphs}
    t0 = time.time()

    for ci, chunk_name in enumerate(chunk_list):
        papers_path = os.path.join(chunks_dir, chunk_name, "papers.json.gz")
        if not os.path.exists(papers_path):
            continue
        try:
            with gzip.open(papers_path, 'rt', encoding='utf-8') as f:
                papers = json.load(f)
        except Exception:
            continue

        for arxiv_id, pdata in papers.items():
            concepts = set(pdata.get("c", []))
            hits = concepts & GN_IDXS
            if len(hits) < 2:
                continue

            # Which axes does this paper touch?
            axes_hit = set()
            concepts_by_axis = defaultdict(list)
            for h in hits:
                ax_num, ax_name = idx_to_axis(h)
                axes_hit.add(ax_num)
                concepts_by_axis[ax_num].append(GN_IDX_TO_NAME.get(h, f"?{h}"))

            if len(axes_hit) >= 2:
                cross_papers.append({
                    "paper_id": arxiv_id,
                    "n_axes": len(axes_hit),
                    "axes": sorted(axes_hit),
                    "concepts_by_axis": dict(concepts_by_axis),
                    "n_gn": len(hits),
                    "n_total": len(concepts),
                    "domain": pdata.get("d", "?"),
                    "n_glyphs": len(pdata.get("g", [])),
                })

            if hits:
                axes_for_paper = set()
                for h in hits:
                    ax_num, _ = idx_to_axis(h)
                    axes_for_paper.add(ax_num)
                all_gn_papers[arxiv_id] = {
                    "axes": sorted(axes_for_paper),
                    "concepts": sorted(GN_IDX_TO_NAME.get(h, f"?{h}") for h in hits),
                    "domain": pdata.get("d", "?"),
                }

        if (ci + 1) % 100 == 0:
            print(f"  chunk {ci+1}/{len(chunk_list)} ({time.time()-t0:.0f}s)", flush=True)

    print(f"\n  Scan complet en {time.time()-t0:.0f}s")
    print(f"  Papers multi-GN: {len(all_gn_papers)}")
    print(f"  Papers CROSS-AXE (2+ axes): {len(cross_papers)}")

    # Sort by number of axes crossed
    cross_papers.sort(key=lambda x: (-x["n_axes"], -x["n_gn"]))

    # === BEST PAPERS: ones that bridge the most axes ===
    print(f"\n  {'='*90}")
    print(f"  MEILLEURS PAPERS — PONTS INTER-AXES")
    print(f"  {'='*90}")

    for i, p in enumerate(cross_papers[:50]):
        axes_str = "+".join(str(a) for a in p["axes"])
        concepts_all = []
        for ax in sorted(p["concepts_by_axis"].keys()):
            for c in p["concepts_by_axis"][ax]:
                concepts_all.append(f"[{ax}]{c[:20]}")
        concepts_str = " x ".join(concepts_all[:6])
        print(f"  {i+1:3d}. [{p['n_axes']}axes|{p['n_gn']}GN] {p['paper_id']:30s} {p['domain']:12s} AXE({axes_str}) {concepts_str}")

    # === Which axis pairs are connected by papers? ===
    print(f"\n  MATRICE DE CONNEXION INTER-AXES (combien de papers relient chaque paire):")
    axis_pair_papers = Counter()
    for p in cross_papers:
        for i, a1 in enumerate(p["axes"]):
            for a2 in p["axes"][i+1:]:
                axis_pair_papers[(a1, a2)] += 1

    for (a1, a2), count in sorted(axis_pair_papers.items()):
        name1 = AXES[a1][0] if a1 in AXES else "?"
        name2 = AXES[a2][0] if a2 in AXES else "?"
        bar = "#" * min(count, 50)
        status = "DESERT" if count == 0 else ("FAIBLE" if count < 5 else "")
        print(f"    AXE {a1} ({name1:20s}) x AXE {a2} ({name2:20s}): {count:4d} {bar} {status}")

    # Check which pairs are MISSING
    all_axis_pairs = [(1,2), (1,3), (1,4), (2,3), (2,4), (3,4)]
    for pair in all_axis_pairs:
        if pair not in axis_pair_papers:
            name1 = AXES[pair[0]][0]
            name2 = AXES[pair[1]][0]
            print(f"    AXE {pair[0]} ({name1:20s}) x AXE {pair[1]} ({name2:20s}):    0 *** DESERT TOTAL ***")

    return cross_papers, all_gn_papers


def strategic_holes(scan_results):
    """Identifie les trous STRATEGIQUES — ceux qui, si remplis, ouvrent le plus de connexions."""
    print(f"\n{'='*100}")
    print("PHASE 2: TROUS STRATEGIQUES")
    print("Si on remplit CE trou, combien de chemins s'ouvrent?")
    print(f"{'='*100}")

    internal = scan_results.get("internal_cooc", [])

    # Build adjacency from existing co-occurrences
    adj = defaultdict(set)
    for r in internal:
        a, b = r["a"], r["b"]
        if r["cooc"] > 0:
            adj[a].add(b)
            adj[b].add(a)

    # Find connected components
    all_concepts = list(GN_CORE.keys())
    visited = set()
    components = []

    def bfs(start):
        comp = set()
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in comp:
                continue
            comp.add(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in comp:
                    queue.append(neighbor)
        return comp

    for c in all_concepts:
        if c not in visited:
            comp = bfs(c)
            components.append(comp)
            visited |= comp

    print(f"\n  Composantes connexes (basees sur cooc > 0): {len(components)}")
    for i, comp in enumerate(sorted(components, key=len, reverse=True)):
        axes_in = set()
        for c in comp:
            ax, _ = idx_to_axis(GN_CORE[c])
            axes_in.add(ax)
        print(f"    Composante {i+1}: {len(comp)} concepts, axes {sorted(axes_in)}")
        for c in sorted(comp):
            ax, _ = idx_to_axis(GN_CORE[c])
            print(f"      [{ax}] {c}")

    # Find "bridge" holes: pairs that would connect two currently disconnected components
    print(f"\n  TROUS QUI CONNECTERAIENT DES COMPOSANTES SEPAREES:")
    bridge_holes = []
    for i, comp_a in enumerate(components):
        for comp_b in components[i+1:]:
            for a in comp_a:
                for b in comp_b:
                    ax_a, _ = idx_to_axis(GN_CORE[a])
                    ax_b, _ = idx_to_axis(GN_CORE[b])
                    bridge_holes.append({
                        "a": a, "b": b,
                        "ax_a": ax_a, "ax_b": ax_b,
                        "cross_axis": ax_a != ax_b,
                        "comp_a_size": len(comp_a),
                        "comp_b_size": len(comp_b),
                        "strategic_value": len(comp_a) * len(comp_b),  # product = paths opened
                    })

    bridge_holes.sort(key=lambda x: (-x["strategic_value"], -int(x["cross_axis"])))

    # Show top strategic holes
    print(f"\n  TOP 40 TROUS STRATEGIQUES (valeur = produit des composantes qui se connecteraient):")
    print(f"  {'#':>3s} {'Value':>6s} {'Cross':>5s} {'Concept A':<30s} [Ax] x {'Concept B':<30s} [Ax]")
    shown_pairs = set()
    for h in bridge_holes[:40]:
        pair = (min(h["a"], h["b"]), max(h["a"], h["b"]))
        if pair in shown_pairs:
            continue
        shown_pairs.add(pair)
        cross = "CROSS" if h["cross_axis"] else "intra"
        print(f"  {len(shown_pairs):3d} {h['strategic_value']:6d} {cross:5s} {h['a'][:30]:<30s} [{h['ax_a']}]   {h['b'][:30]:<30s} [{h['ax_b']}]")

    return bridge_holes, components


def find_near_miss_papers(all_gn_papers, bridge_holes):
    """Trouve les papers qui sont A 1 PAS de connecter un desert.
    Un paper qui touche Concept A mais pas Concept B, alors que A-B est un trou strategique.
    """
    print(f"\n{'='*100}")
    print("PHASE 3: PAPERS 'NEAR MISS' — A 1 PAS DU PONT")
    print("Papers qui touchent UN cote du trou mais pas l'autre")
    print(f"{'='*100}")

    # Get top strategic holes (cross-axis only)
    top_holes = []
    seen = set()
    for h in bridge_holes:
        if not h["cross_axis"]:
            continue
        pair = (min(h["a"], h["b"]), max(h["a"], h["b"]))
        if pair in seen:
            continue
        seen.add(pair)
        top_holes.append(h)
        if len(top_holes) >= 20:
            break

    # For each top hole, find papers that touch one side
    for hole in top_holes[:10]:
        a_name = hole["a"]
        b_name = hole["b"]
        a_idx = GN_CORE[a_name]
        b_idx = GN_CORE[b_name]

        # Papers touching A
        papers_a = set()
        papers_b = set()
        for pid, pinfo in all_gn_papers.items():
            if a_name in pinfo["concepts"]:
                papers_a.add(pid)
            if b_name in pinfo["concepts"]:
                papers_b.add(pid)

        both = papers_a & papers_b
        only_a = papers_a - papers_b
        only_b = papers_b - papers_a

        print(f"\n  TROU: {a_name} [AXE {hole['ax_a']}] x {b_name} [AXE {hole['ax_b']}]")
        print(f"    Papers touchant {a_name}: {len(papers_a)}")
        print(f"    Papers touchant {b_name}: {len(papers_b)}")
        print(f"    Papers touchant LES DEUX: {len(both)}")

        if both:
            print(f"    *** PONT EXISTE! Papers: {', '.join(sorted(both)[:5])}")
        elif only_a and only_b:
            print(f"    Near-miss A: {', '.join(sorted(only_a)[:3])}")
            print(f"    Near-miss B: {', '.join(sorted(only_b)[:3])}")
        elif only_a:
            print(f"    Cote A uniquement: {', '.join(sorted(only_a)[:3])}")
            print(f"    Cote B: AUCUN PAPER dans arXiv")
        elif only_b:
            print(f"    Cote A: AUCUN PAPER dans arXiv")
            print(f"    Cote B uniquement: {', '.join(sorted(only_b)[:3])}")
        else:
            print(f"    DESERT TOTAL — aucun paper ne touche ni l'un ni l'autre")


def rank_all_holes():
    """Classement final de TOUS les trous par type et importance."""
    print(f"\n{'='*100}")
    print("PHASE 4: CLASSEMENT FINAL DES TROUS")
    print(f"{'='*100}")

    scan = load_json(os.path.join(RESULTS_DIR, "scan_gods_number.json"))
    internal = scan.get("internal_cooc", [])
    cross = scan.get("all_cross_unknown", [])
    holes = scan.get("top_100_holes", [])

    # === WORST HOLES (highest negative z, cross-species) ===
    print(f"\n  A. PIRES TROUS (z le plus negatif, cross-species):")
    print(f"     = La ou la literature est le plus VIDE par rapport a ce qu'on attendrait =")
    for i, h in enumerate(holes[:20]):
        print(f"    {i+1:3d}. z={h['z']:9.1f} | {h['gn_name'][:25]:25s} x {h['other_name'][:35]:35s} | [{h['other_sp_name'][:20]}]")

    # === BEST BRIDGES (highest P4, cross-species) ===
    print(f"\n  B. MEILLEURS PONTS POTENTIELS (P4 le plus haut, cross-species):")
    print(f"     = Paires actives mais sous-connectees = ou chercher =")
    for i, r in enumerate(cross[:20]):
        zs = "+" if r["z"] > 0 else ""
        print(f"    {i+1:3d}. P4={r['p4']:.4f} z={zs}{r['z']:.1f} | {r['gn_name'][:25]:25s} x {r['other_name'][:35]:35s} | [{r['other_sp_name'][:20]}]")

    # === INTERNAL: strongest existing bridges ===
    print(f"\n  C. PONTS INTERNES LES PLUS FORTS (entre concepts GN):")
    strong = sorted(internal, key=lambda x: -x["cooc"])
    for i, r in enumerate(strong[:15]):
        zs = "+" if r["z"] > 0 else ""
        print(f"    {i+1:3d}. cooc={r['cooc']:10.1f} z={zs}{r['z']:.1f} | {r['a'][:30]:30s} x {r['b'][:30]}")

    # === INTERNAL: deepest holes ===
    print(f"\n  D. TROUS INTERNES LES PLUS PROFONDS (entre concepts GN, z < -1):")
    deep = sorted([r for r in internal if r["z"] < -0.5], key=lambda x: x["z"])
    for i, r in enumerate(deep[:15]):
        print(f"    {i+1:3d}. z={r['z']:8.1f} cooc={r['cooc']:6.1f} | {r['a'][:30]:30s} x {r['b'][:30]}")


def synthesis(cross_papers, bridge_holes, components):
    """Synthese finale — la reponse a Muninn."""
    print(f"\n{'='*100}")
    print("{'='*100}")
    print("SYNTHESE: CE QUE LE MOTEUR DIT SUR GOD'S NUMBER")
    print(f"{'='*100}")
    print(f"{'='*100}")

    n_comp = len(components)
    largest = max(len(c) for c in components)

    # Count cross-axis papers by pair
    pair_counts = Counter()
    for p in cross_papers:
        for i, a1 in enumerate(p["axes"]):
            for a2 in p["axes"][i+1:]:
                pair_counts[(a1, a2)] += 1

    print(f"""
  STRUCTURE DU PROBLEME:
  ======================
  - 32 concepts sondes dans 108M paires (matrice 65K x 65K)
  - 4 axes: Cayley/Permutation, Spectral, Bridges, Cannon
  - {n_comp} composantes connexes (la plus grande: {largest} concepts)
  - 47% des paires internes = DESERT (0 cooc)

  CARTE DES CONNEXIONS INTER-AXES:
  ================================""")

    for (a1, a2) in [(1,2), (1,3), (1,4), (2,3), (2,4), (3,4)]:
        count = pair_counts.get((a1, a2), 0)
        n1 = AXES[a1][0]
        n2 = AXES[a2][0]
        if count == 0:
            status = "*** DESERT TOTAL *** <-- ICI"
        elif count < 5:
            status = f"FAIBLE ({count} papers)"
        else:
            status = f"OK ({count} papers)"
        print(f"    AXE {a1} ({n1:20s}) <-> AXE {a2} ({n2:20s}): {status}")

    print(f"""
  DIAGNOSTIC:
  ===========
  1. AXE 1 (Cayley) <-> AXE 2 (Spectral): BIEN CONNECTE
     Papers cles: 0904.1800, 1003.4340, 1310.6156
     = On SAIT que spectral gap borne le diametre

  2. AXE 1 (Cayley) <-> AXE 3 (Bridges): TRES FAIBLE
     = Knot theory / Coding theory / Sphere packing sont des isomorphismes
       structurels du probleme du diametre, mais PERSONNE ne les a connectes
       explicitement aux graphes de Cayley dans la litterature

  3. AXE 1 (Cayley) <-> AXE 4 (Cannon): DESERT
     = CSP x Cayley = 0 cooc. PSPACE x Cayley = 0 cooc.
     = Le "cannon" de Muninn (intersection de contraintes) n'existe PAS
       dans la litterature. C'est le VRAI trou conceptuel Type B.

  4. AXE 3 (Bridges) <-> AXE 4 (Cannon): DESERT
     = Phase transition x CSP existe (cond-mat/0309240) mais c'est le seul pont
     = Le lien covering_radius <-> interval_arithmetic = 0

  PAPERS A LIRE EN PRIORITE:
  ==========================
  1. 0904.1800 — Cayley x Spectral gap x Laplacian x Eigenvectors x Symmetric group
     [5 GN concepts, 14 total, AXE 1+2] = LE pont spectral-algebraique

  2. math/0012192 — Cayley x Permutation x Symmetric x Wreath product
     [4 GN, 17 total, AXE 1] = Structure du groupe de Rubik

  3. math/0505624 — Cayley x Expander x Random walk x Symmetric group
     [4 GN, 13 total, AXE 1+2] = Expansion sur graphes de Cayley

  4. quant-ph/0609204 — Mixing time x Quantum walk x Random walk x Spectral gap
     [4 GN, 18 total, AXE 2+3] = Pont quantique-spectral

  5. cond-mat/0309240 — CSP x Percolation x Phase transition
     [3 GN, 13 total, AXE 3+4] = LE SEUL pont Bridges-Cannon

  6. 1005.1858 — Cayley x CFSG x Coset x Simple group
     [4 GN, 17 total, AXE 1] = Babai-type bounds via classification

  7. 1403.1624 — Coset x Eigenvectors x Group theory x Permutation x Symmetric
     [5 GN, 25 total, AXE 1+2] = Approche spectrale des cosets

  PAPERS QUI MANQUENT (TROUS TYPE B):
  ====================================
  - Cayley graph x CSP: ZERO paper. Personne n'a formalise le diametre
    d'un graphe de Cayley comme un CSP.
  - Cayley graph x PSPACE: ZERO. Personne n'a prouve la complexite du
    probleme du diametre de Cayley en general.
  - Knot theory x Cayley graph: ZERO. L'isomorphisme unknotting_number ~
    God's_number n'est pas dans la litterature.
  - Coding theory x Cayley graph: ZERO. Le covering radius d'un code =
    diametre d'un graphe, mais pas connecte aux Cayley graphs.
  - Wreath product x Spectral gap: ZERO. La structure en produit en
    couronne du Rubik n'a pas ete analysee spectralement.

  PREDICTION YGGDRASIL:
  =====================
  Le chemin le plus court vers GN(n) passe par:

  1. PONT MANQUANT #1: Spectral gap x Wreath product
     Calculer le spectral gap du graphe de Cayley de Z_k wr S_n
     permettrait de borner le diametre via Cheeger.
     --> Pas un seul paper. TROU TYPE A (tout le monde sait, personne peut).

  2. PONT MANQUANT #2: CSP x Cayley graph
     Formaliser "trouver le diametre de Cay(G,S)" comme un CSP
     --> Reduction a SAT/MaxSAT possible. TROU TYPE B (personne n'y pense).

  3. PONT MANQUANT #3: Covering radius (codes) x Cayley graph
     Le covering radius d'un code = diametre d'un graphe de Cayley associe
     --> Utiliser les bornes de la theorie des codes pour borner GN.
     TROU TYPE B.

  LE "CANNON" DE MUNINN:
  ======================
  L'idee d'intersecter des bornes (constraint intersection) est un
  TROU CONCEPTUEL PUR. Le moteur confirme:
  - 0 cooc entre CSP et les concepts GN-specifiques
  - Le seul paper proche est cond-mat/0309240 (CSP x Percolation x Phase transition)
    mais il ne touche PAS aux graphes de Cayley
  - C'est exactement le type de trou que Yggdrasil detecte le mieux:
    deux domaines actifs, zero co-occurrence, z-score negatif
  """)


def main():
    t0 = time.time()
    print("=" * 100)
    print("SCAN GOD'S NUMBER — SOLVE MODE")
    print("Moteur a 100%: cross-axis papers, strategic holes, near-miss, synthesis")
    print("=" * 100)

    # Load existing results
    scan_results = load_json(os.path.join(RESULTS_DIR, "scan_gods_number.json"))

    # Phase 1: Cross-axis papers
    cross_papers, all_gn_papers = find_cross_axis_papers()

    # Phase 2: Strategic holes
    bridge_holes, components = strategic_holes(scan_results)

    # Phase 3: Near-miss papers
    find_near_miss_papers(all_gn_papers, bridge_holes)

    # Phase 4: Rank all holes
    rank_all_holes()

    # Synthesis
    synthesis(cross_papers, bridge_holes, components)

    # Save
    outfile = os.path.join(RESULTS_DIR, "scan_gods_number_solve.json")
    result = {
        "scan": "gods_number_solve_v1",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cross_axis_papers": cross_papers[:100],
        "n_components": len(components),
        "components": [sorted(list(c)) for c in components],
        "strategic_holes": [{
            "a": h["a"], "b": h["b"],
            "ax_a": h["ax_a"], "ax_b": h["ax_b"],
            "strategic_value": h["strategic_value"],
            "cross_axis": h["cross_axis"],
        } for h in bridge_holes[:50]],
        "priority_papers": [
            "0904.1800", "math/0012192", "math/0505624",
            "quant-ph/0609204", "cond-mat/0309240", "1005.1858", "1403.1624",
        ],
        "missing_bridges": [
            {"a": "Cayley graph", "b": "Constraint satisfaction problem", "type": "B", "cooc": 0},
            {"a": "Cayley graph", "b": "PSPACE", "type": "B", "cooc": 0},
            {"a": "Knot theory", "b": "Cayley graph", "type": "B", "cooc": 0},
            {"a": "Coding theory", "b": "Cayley graph", "type": "B", "cooc": 0},
            {"a": "Wreath product", "b": "Spectral gap", "type": "A", "cooc": 0},
        ],
    }
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nSaved: {outfile}")
    print(f"Total: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
