#!/usr/bin/env python3
"""
YGGDRASIL — CARMACK MOVES HUNTER
═════════════════════════════════
Trouve les "Carmack moves" : algorithmes/techniques d'autres domaines
que personne n'a pensé à appliquer aux problèmes ouverts.

John Carmack → fast inverse sqrt (Newton-Raphson × gamedev)
Nous → [???] × God's Number / P vs NP / Ramsey

Sources:
1. Type C cross-axes du cannon scan (ponts ignorés = Karikó)
2. Déserts absolus les plus surprenants (vides = terrain vierge)
3. WT2 papers qui touchent les ponts (preuve que ça existe)

Sky × Claude — 21 Mars 2026
"""

import json
import gzip
import os
import sys
import io
import time
import sqlite3
from collections import defaultdict, Counter

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")

# ══════════════════════════════════════════════
# CARMACK MOVE CANDIDATES
# Format: (technique_name, technique_idx, target_domain, target_idxs, tier, rationale)
# ══════════════════════════════════════════════

# Target concepts for each problem
GN_TARGETS = {
    "Cayley graph": 3217, "Wreath product": 64319, "Permutation group": 63903,
    "Symmetric group": 4492, "Spectral gap": 28454, "Expander graph": 8508,
    "Mixing time": 64555,
}

PNP_TARGETS = {
    "P versus NP": 13541, "Comp. complexity": 12499, "Boolean satisfiability": 60347,
    "NP-complete": 3609, "PSPACE": 15276, "Circuit complexity": 63572,
    "Proof complexity": 933, "Decidability": 8312,
}

RAMSEY_TARGETS = {
    "Ramsey theory": 1997, "Ramsey's theorem": 55433,
}

# Carmack move candidates — techniques from other domains
CARMACK_CANDIDATES = {
    # PHYSIQUE → MATH
    "Renormalization group": {
        "idx": 60204, "origin": "Physique (QFT)", "works": 61870,
        "move": "La renormalisation élimine les degrés de liberté à chaque échelle. "
                "Appliqué au cube : chaque 'layer' du 4×4 est une échelle. "
                "Renormaliser = réduire le 4×4 à un 3×3 effectif + correction.",
        "targets": ["GN", "PNP"],
    },
    "Ising model": {
        "idx": 56807, "origin": "Physique stat (48K papers)", "works": 48310,
        "move": "Ising = spins ±1 sur un réseau avec énergie d'interaction. "
                "Le cube EST un modèle d'Ising : chaque facette = spin, "
                "la configuration résolue = état fondamental, GN = temps de relaxation.",
        "targets": ["GN", "PNP"],
    },
    "Spin glass": {
        "idx": 7925, "origin": "Physique stat (20K papers)", "works": 20250,
        "move": "Le spin glass a un paysage d'énergie frustré avec des minima locaux. "
                "Le graphe de Cayley du cube a la MÊME structure. "
                "Les bornes sur le temps de relaxation des spin glasses → bornes sur GN.",
        "targets": ["GN"],
    },
    "Partition function (QFT)": {
        "idx": 29774, "origin": "Physique quantique (23K papers)", "works": 22648,
        "move": "Z = sum over all states. Pour le cube : Z = somme sur toutes les "
                "configurations, pondérée par e^(-beta * distance_au_résolu). "
                "Le free energy F = -kT ln Z donne une BORNE THERMODYNAMIQUE sur GN.",
        "targets": ["GN", "RAMSEY"],
    },
    "Resistance distance": {
        "idx": 59049, "origin": "Théorie des circuits (753 papers)", "works": 753,
        "move": "Resistance distance = distance effective dans un réseau électrique. "
                "Le graphe de Cayley vu comme un circuit : chaque arête = résistance 1Ω. "
                "La resistance distance effective donne une BORNE INFÉRIEURE sur le diamètre.",
        "targets": ["GN"],
    },
    "Electrical network": {
        "idx": 15129, "origin": "Électrotechnique (85K papers)", "works": 84657,
        "move": "Kirchhoff + Rayleigh monotonicity : couper des arêtes augmente la résistance. "
                "Sur le Cayley graph : enlever des moves augmente le diamètre. "
                "Borne par énergie de Thomson = optimisation variationnelle sur GN.",
        "targets": ["GN"],
    },
    "Cellular automaton": {
        "idx": 54073, "origin": "Systèmes complexes (22K papers)", "works": 21666,
        "move": "Rule 110 est Turing-complet. Le cube 4×4 est-il un automate cellulaire ? "
                "Si oui, les bornes de complexité des CA s'appliquent. "
                "Wolfram 2002 : certains CA ont des diamètres indécidables.",
        "targets": ["GN", "PNP"],
    },
    "Reversible computing": {
        "idx": 16053, "origin": "Informatique physique (1.5K papers)", "works": 1510,
        "move": "Chaque move du cube est RÉVERSIBLE (R → R'). "
                "Landauer 1961 : effacer 1 bit = kT ln 2 d'énergie. "
                "Mais les moves réversibles n'effacent PAS d'info. "
                "Borne de Bennett sur le nombre de moves réversibles nécessaires.",
        "targets": ["GN", "PNP"],
    },
    "Critical exponent": {
        "idx": 10021, "origin": "Physique stat (41K papers)", "works": 41301,
        "move": "Près d'une transition de phase, les observables suivent des lois de puissance "
                "avec des exposants UNIVERSELS. Si GN(n) ~ n^alpha, alpha est un exposant critique. "
                "La classe d'universalité du cube détermine alpha.",
        "targets": ["GN"],
    },
    "Percolation threshold": {
        "idx": 17933, "origin": "Physique stat (24K papers)", "works": 24489,
        "move": "Au seuil de percolation, un cluster géant apparaît. "
                "Sur le Cayley graph : à quel ratio de moves le graphe reste-t-il connexe ? "
                "Si on retire des moves aléatoirement, à quel seuil GN → ∞ ?",
        "targets": ["GN"],
    },
    "Potts model": {
        "idx": 64855, "origin": "Physique stat (6.5K papers)", "works": 6480,
        "move": "Potts = Ising généralisé à q états. Le cube n×n a q = |G| états. "
                "La function de partition du Potts sur le graphe de Cayley = "
                "le polynôme chromatique. Lien avec Ramsey via coloration.",
        "targets": ["GN", "RAMSEY"],
    },
    # INFORMATION → MATH
    "Kolmogorov complexity": {
        "idx": 34208, "origin": "Théorie de l'information (2K papers)", "works": 1974,
        "move": "K(x) = longueur du plus court programme qui produit x. "
                "Si K(position) ≈ log|G|, alors la position est 'incompressible' "
                "et nécessite ~GN moves. Borne par complexité de Kolmogorov.",
        "targets": ["GN", "PNP"],
    },
    "Data compression": {
        "idx": 61733, "origin": "Traitement signal (138K papers)", "works": 138084,
        "move": "Compresser = trouver les régularités. Si le groupe du cube est "
                "hautement structuré, la solution est compressible → GN est petit. "
                "Si incompressible → GN est grand. NCD (Normalized Compression Distance) "
                "entre position et résolu = approximation du nombre de moves.",
        "targets": ["GN"],
    },
    # ESPACE → MATH
    "Holographic principle": {
        "idx": 13175, "origin": "Physique théorique (6.4K papers)", "works": 6448,
        "move": "L'information d'un volume est bornée par sa SURFACE (pas son volume). "
                "Sur le Cayley graph : le nombre de positions à distance d du résolu "
                "croît comme la surface de la boule de rayon d. "
                "Borne holographique : GN ≥ log|G| / log(surface_growth_rate).",
        "targets": ["GN", "PNP"],
    },
    "Fractal dimension": {
        "idx": 17805, "origin": "Mathématiques (44K papers)", "works": 43622,
        "move": "Si la croissance de la boule dans le Cayley graph est fractale "
                "(pas polynomiale, pas exponentielle), la dimension fractale "
                "donne le taux de croissance exact → borne sur GN.",
        "targets": ["GN"],
    },
    "Penrose tiling": {
        "idx": 61412, "origin": "Mathématiques/Cristallographie (804 papers)", "works": 804,
        "move": "Quasi-cristaux = ordre sans périodicité. φ (golden ratio) est "
                "la constante structurelle des Penrose tilings. "
                "Si GN(n+1)/GN(n) → φ, le cube est un quasi-cristal combinatoire.",
        "targets": ["GN"],
    },
    # BIO → MATH
    "Fitness landscape": {
        "idx": 63747, "origin": "Biologie évolutive (11K papers)", "works": 11054,
        "move": "Le paysage de fitness = graphe où chaque nœud est un génotype "
                "et les arêtes sont des mutations. Le DIAMÈTRE du fitness landscape "
                "= le nombre minimum de mutations pour passer du pire au meilleur. "
                "C'est EXACTEMENT God's Number pour le cube = diamètre du Cayley graph.",
        "targets": ["GN"],
    },
    "Protein folding": {
        "idx": 16301, "origin": "Biochimie (136K papers)", "works": 136159,
        "move": "Le protein folding landscape a la MÊME structure que le cube : "
                "état natif = résolu, nombre de folding steps = GN. "
                "Levinthal's paradox (1969) : les protéines trouvent le fold en temps "
                "polynomial malgré un espace exponentiel. Même paradoxe pour le cube ?",
        "targets": ["GN", "PNP"],
    },
    "Ergodic theory": {
        "idx": 3508, "origin": "Mathématiques (24K papers)", "works": 23752,
        "move": "Un système ergodique visite tous les états en temps fini. "
                "Le graphe de Cayley est ergodique (chaque position est atteignable). "
                "Le temps de RETOUR ergodique → borne supérieure sur GN. "
                "Théorème de Birkhoff : la moyenne temporelle = moyenne spatiale.",
        "targets": ["GN"],
    },
    "Power law": {
        "idx": 63029, "origin": "Physique/Sociologie (61K papers)", "works": 60735,
        "move": "Si la distribution des distances dans le Cayley graph suit une loi "
                "de puissance P(d) ~ d^(-gamma), alors gamma détermine GN. "
                "Les réseaux scale-free ont des diamètres ~ log(log(N)). "
                "Le cube est-il scale-free ?",
        "targets": ["GN", "RAMSEY"],
    },
    "Simulated annealing": {
        "idx": 4263, "origin": "Optimisation (31K papers)", "works": 31025,
        "move": "SA explore un paysage d'énergie en acceptant des moves défavorables "
                "avec probabilité e^(-ΔE/T). Appliqué au cube : le 'recuit' simule "
                "le processus de résolution avec une température qui décroît. "
                "Le temps de convergence de SA → borne probabiliste sur GN.",
        "targets": ["GN"],
    },
    "Boltzmann entropy formula": {
        "idx": 53836, "origin": "Physique stat (6.5K papers)", "works": 6509,
        "move": "S = k ln W. Pour le cube : W = nombre de positions à distance d. "
                "L'entropie S(d) est maximale au milieu du graphe. "
                "dS/dd = 0 au 'point critique' → borne sur la distribution.",
        "targets": ["GN"],
    },
    # LOGIQUE → MATH
    "Godel incompleteness": {
        "idx": 12665, "origin": "Logique (1.8K papers)", "works": 1764,
        "move": "Certaines valeurs de Ramsey sont-elles indémontrables dans PA ? "
                "Paris-Harrington 1977 : OUI pour certains énoncés Ramsey-like. "
                "Si R(5,5) est indémontrable, le canon ne peut PAS converger. "
                "C'est une BORNE MÉTA sur la méthode elle-même.",
        "targets": ["RAMSEY", "PNP"],
    },
}

ALL_TECHNIQUE_IDXS = {v["idx"] for v in CARMACK_CANDIDATES.values()}
ALL_TARGET_IDXS = set()
for d in [GN_TARGETS, PNP_TARGETS, RAMSEY_TARGETS]:
    ALL_TARGET_IDXS.update(d.values())


def search_wt2_papers(technique_idxs, target_idxs):
    """Search WT2 chunks for papers that bridge technique × target."""
    wt2_dir = os.path.join(REPO, "data", "pipeline", "wt2_chunks")
    if not os.path.isdir(wt2_dir):
        return []

    bridges = []
    chunk_files = sorted([f for f in os.listdir(wt2_dir) if f.startswith("papers") and f.endswith(".json.gz")])
    total = len(chunk_files)

    for ci, cf in enumerate(chunk_files):
        if ci % 50 == 0:
            print(f"    WT2 chunk {ci}/{total}...", end="\r")
        path = os.path.join(wt2_dir, cf)
        try:
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                papers = json.load(f)
        except Exception:
            continue

        for arxiv_id, pdata in papers.items():
            concepts = set(pdata.get("c", []))
            tech_hits = concepts & technique_idxs
            target_hits = concepts & target_idxs
            if tech_hits and target_hits:
                bridges.append({
                    "paper_id": arxiv_id,
                    "domain": pdata.get("d", "?"),
                    "tech_concepts": sorted(tech_hits),
                    "target_concepts": sorted(target_hits),
                    "n_total": len(concepts),
                })

    print(f"    WT2 done: {len(bridges)} bridge papers")
    return bridges


def main():
    t0 = time.time()
    print("=" * 120)
    print("CARMACK MOVES HUNTER")
    print(f"Fast inverse sqrt pour God's Number / P vs NP / Ramsey")
    print(f"{len(CARMACK_CANDIDATES)} techniques candidates × 3 cibles")
    print("=" * 120)

    # === 1. Load concept names ===
    print("\n[1] Loading concepts...")
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"), 'r', encoding='utf-8') as f:
        cdata = json.load(f)
    idx_to_name = {info["idx"]: info["name"] for info in cdata["concepts"].values()}

    # === 2. Load co-occurrences from WT3 ===
    print("[2] Loading co-occurrences from WT3...")
    db = sqlite3.connect(os.path.join(REPO, "data", "wt3.db"))
    cursor = db.cursor()

    # Only need tech × target pairs
    all_idxs = sorted(ALL_TECHNIQUE_IDXS | ALL_TARGET_IDXS)
    placeholders = ",".join(str(i) for i in all_idxs)
    cursor.execute(f"""
        SELECT concept_a, concept_b, weight
        FROM cooc_global
        WHERE concept_a IN ({placeholders}) AND concept_b IN ({placeholders})
    """)

    cooc = {}
    for a, b, w in cursor.fetchall():
        cooc[(min(a, b), max(a, b))] = float(w)
    db.close()
    print(f"  {len(cooc)} pairs loaded")

    # === 3. Load activity ===
    print("[3] Loading activity...")
    import numpy as np
    with open(os.path.join(REPO, "experiments", "predictions_2025", "activity_full.json"), 'r', encoding='utf-8') as f:
        activity = np.array(json.load(f)["activity"], dtype=np.float64)
    total_works = float(activity.sum())

    # === 4. Score each Carmack move ===
    print("\n[4] Scoring Carmack moves...")

    target_maps = {"GN": GN_TARGETS, "PNP": PNP_TARGETS, "RAMSEY": RAMSEY_TARGETS}

    moves = []
    for tech_name, tech_info in CARMACK_CANDIDATES.items():
        tech_idx = tech_info["idx"]
        wa = float(activity[tech_idx])

        for target_label in tech_info["targets"]:
            target_dict = target_maps[target_label]

            total_cooc = 0.0
            n_deserts = 0
            n_pairs = 0
            z_sum = 0.0
            pair_details = []

            for tgt_name, tgt_idx in target_dict.items():
                pair = (min(tech_idx, tgt_idx), max(tech_idx, tgt_idx))
                observed = cooc.get(pair, 0.0)
                wb = float(activity[tgt_idx])
                if wb == 0:
                    continue

                E = wa * wb / total_works
                pa, pb = wa / total_works, wb / total_works
                std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
                z = (observed - E) / std

                n_pairs += 1
                total_cooc += observed
                z_sum += z
                if observed == 0:
                    n_deserts += 1

                pair_details.append({
                    "target": tgt_name,
                    "cooc": observed,
                    "expected": E,
                    "z": z,
                })

            if n_pairs == 0:
                continue

            avg_z = z_sum / n_pairs
            desert_ratio = n_deserts / n_pairs

            # Carmack score = how UNKNOWN × how BIG the technique is
            # Higher = more surprising that nobody connected these
            carmack_score = desert_ratio * np.log1p(wa) * abs(avg_z)

            # Tier assignment
            if desert_ratio >= 0.8 and wa > 10000:
                tier = "S"
            elif desert_ratio >= 0.5 and wa > 5000:
                tier = "A"
            elif desert_ratio >= 0.3:
                tier = "B"
            else:
                tier = "C"

            moves.append({
                "technique": tech_name,
                "tech_idx": tech_idx,
                "origin": tech_info["origin"],
                "works": tech_info["works"],
                "target": target_label,
                "move": tech_info["move"],
                "carmack_score": carmack_score,
                "tier": tier,
                "avg_z": avg_z,
                "total_cooc": total_cooc,
                "n_deserts": n_deserts,
                "n_pairs": n_pairs,
                "desert_ratio": desert_ratio,
                "pairs": pair_details,
            })

    moves.sort(key=lambda x: -x["carmack_score"])

    # === 5. Search WT2 for bridge papers ===
    print("\n[5] Searching WT2 for bridge papers...")
    bridge_papers = search_wt2_papers(ALL_TECHNIQUE_IDXS, ALL_TARGET_IDXS)

    # Map papers to techniques
    paper_by_tech = defaultdict(list)
    for p in bridge_papers:
        for tidx in p["tech_concepts"]:
            for tname, tinfo in CARMACK_CANDIDATES.items():
                if tinfo["idx"] == tidx:
                    paper_by_tech[tname].append(p)

    # === 6. Display ===
    print(f"\n{'='*120}")
    print("CARMACK MOVES — CLASSEMENT PAR TIER")
    print(f"{'='*120}")

    for tier_label in ["S", "A", "B", "C"]:
        tier_moves = [m for m in moves if m["tier"] == tier_label]
        if not tier_moves:
            continue

        print(f"\n{'='*120}")
        print(f"TIER {tier_label} — {'ARME NUCLÉAIRE' if tier_label == 'S' else 'FORT' if tier_label == 'A' else 'MOYEN' if tier_label == 'B' else 'EXPÉRIMENTAL'}")
        print(f"{'='*120}")

        for m in tier_moves:
            papers = paper_by_tech.get(m["technique"], [])
            # Filter papers that also have target concepts
            target_idxs = set(target_maps[m["target"]].values())
            relevant_papers = [p for p in papers if set(p["target_concepts"]) & target_idxs]

            print(f"\n  {'─'*110}")
            print(f"  {m['technique']} × {m['target']} "
                  f"[score={m['carmack_score']:.2f}, tier={m['tier']}]")
            print(f"  Origine: {m['origin']} ({m['works']:,} papers)")
            print(f"  Déserts: {m['n_deserts']}/{m['n_pairs']} ({m['desert_ratio']:.0%})"
                  f" | z moyen: {m['avg_z']:.2f}"
                  f" | cooc total: {m['total_cooc']:.1f}")
            print(f"  Le move: {m['move']}")

            if relevant_papers:
                print(f"  Papers ({len(relevant_papers)}):")
                for p in relevant_papers[:5]:
                    tech_names = [idx_to_name.get(i, f"?{i}") for i in p["tech_concepts"]]
                    tgt_names = [idx_to_name.get(i, f"?{i}") for i in p["target_concepts"]]
                    print(f"    [{p['paper_id']}] {p['domain']}"
                          f" | tech: {', '.join(tech_names[:3])}"
                          f" | target: {', '.join(tgt_names[:3])}")
            else:
                print(f"  Papers: AUCUN — DÉSERT CONFIRMÉ")

            # Show pair details
            for pd in m["pairs"][:5]:
                status = "DESERT" if pd["cooc"] == 0 else f"cooc={pd['cooc']:.1f}"
                print(f"    × {pd['target']:30s} | {status:15s} | E={pd['expected']:.2f} | z={pd['z']:.2f}")

    # === 7. Summary by target ===
    print(f"\n{'='*120}")
    print("SYNTHÈSE PAR CIBLE")
    print(f"{'='*120}")

    for target_label in ["GN", "PNP", "RAMSEY"]:
        target_moves = [m for m in moves if m["target"] == target_label]
        target_moves.sort(key=lambda x: -x["carmack_score"])
        print(f"\n  --- {target_label} ---")
        for m in target_moves[:10]:
            papers = len(paper_by_tech.get(m["technique"], []))
            print(f"    [{m['tier']}] {m['technique']:30s} | score={m['carmack_score']:6.2f}"
                  f" | desert={m['desert_ratio']:.0%} | z={m['avg_z']:+.2f}"
                  f" | {papers} papers")

    # === 8. Bridge papers summary ===
    print(f"\n{'='*120}")
    print(f"BRIDGE PAPERS ({len(bridge_papers)} trouvés)")
    print(f"{'='*120}")

    # Count by domain
    domain_counts = Counter(p["domain"] for p in bridge_papers)
    print(f"  Par domaine:")
    for d, c in domain_counts.most_common(10):
        print(f"    {d:30s} | {c:4d} papers")

    # Most connected papers
    bridge_papers.sort(key=lambda x: len(x["tech_concepts"]) + len(x["target_concepts"]), reverse=True)
    print(f"\n  Top 20 papers les plus connectés:")
    for i, p in enumerate(bridge_papers[:20]):
        tech_names = [idx_to_name.get(i2, f"?{i2}") for i2 in p["tech_concepts"][:3]]
        tgt_names = [idx_to_name.get(i2, f"?{i2}") for i2 in p["target_concepts"][:3]]
        print(f"    {i+1:2d}. [{p['paper_id']}] {p['domain']:15s}"
              f" | tech: {', '.join(tech_names)}"
              f" | target: {', '.join(tgt_names)}")

    # === 9. Save ===
    print(f"\n  Temps: {time.time()-t0:.0f}s")
    os.makedirs(os.path.join(REPO, "data", "results"), exist_ok=True)
    outfile = os.path.join(REPO, "data", "results", "scan_carmack_moves.json")
    save = {
        "scan": "carmack_moves_v1",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_techniques": len(CARMACK_CANDIDATES),
        "n_moves": len(moves),
        "moves": moves,
        "bridge_papers": bridge_papers[:100],
        "bridge_paper_count": len(bridge_papers),
    }
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(save, f, indent=2, ensure_ascii=False, default=str)
    print(f"Saved: {outfile}")


if __name__ == "__main__":
    main()
