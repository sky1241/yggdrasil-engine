#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCAN RACINES CROSS-PROJETS
===========================
Pas les outils (arbres). Les RACINES (fondations mathématiques).

Chaque projet utilise les mêmes principes fondamentaux sans le savoir.
Ce script mappe les racines profondes, pas le code visible.

Usage:
    python engine/cross_roots.py
"""
import json
import os
from datetime import datetime

# ── Les RACINES (pas les outils) ──────────────────────────────────

ROOTS = {
    "R1_transform_domain": {
        "name": "Transformation de domaine (temps → fréquence)",
        "math": "Fourier, Laplace, ondelettes — voir un signal autrement",
        "manifests_as": {
            "Ichimoku":     "Welch PSD: prix BTC → spectre → cycle dominant",
            "Shazam":       "PYIN: son piano → fréquence → note MIDI",
            "Yggdrasil":    "Laplacien spectral: graphe co-occurrence → positions 2D",
            "Infernal":     "⚠ ABSENT — drinks.csv est un signal temporel non transformé",
            "Automates":    "⚠ ABSENT — les cames SONT des transformations (rotation→translation) mais pas formalisé",
            "Winter_Tree":  "⚠ ABSENT — la classification est un graphe, transformable en spectre",
        },
        "root_principle": "Tout signal complexe est une somme de signaux simples. Changer de domaine révèle ce qui est caché.",
    },

    "R2_flow_optimization": {
        "name": "Optimisation de flux sur graphe",
        "math": "Kirchhoff, Physarum, Ford-Fulkerson — trouver le chemin optimal",
        "manifests_as": {
            "Yggdrasil":    "Physarum: flux mycélien entre domaines scientifiques",
            "Winter_Tree":  "Nutrient transport: flux de nutriments dans le réseau mycorhizien",
            "Ichimoku":     "⚠ ABSENT — le capital EST un flux. Allocation = optimisation de flux.",
            "Automates":    "⚠ ABSENT — les forces dans les mécanismes SONT des flux (couple → mouvement)",
            "Shazam":       "⚠ ABSENT — le son est un flux d'énergie acoustique",
            "Infernal":     "⚠ ABSENT — l'addiction est un flux (craving → consommation → relief → craving)",
        },
        "root_principle": "Tout réseau a des flux. Les flux cherchent le chemin de moindre résistance. Physarum le trouve.",
    },

    "R3_hidden_state": {
        "name": "Inférence d'états cachés",
        "math": "Bayes, HMM, Kalman — le visible est généré par l'invisible",
        "manifests_as": {
            "Ichimoku":     "HMM 3/5/8 états: les prix VISIBLES sont générés par des régimes CACHÉS",
            "Yggdrasil":    "P1-P5 classification: les co-occurrences VISIBLES révèlent des patterns CACHÉS",
            "Infernal":     "⚠ PARTIEL — tracking VISIBLE mais pas d'inférence de l'état CACHÉ (dépression, stress, ennui)",
            "Shazam":       "⚠ PARTIEL — détection de tonalité = inférer la clé CACHÉE à partir des notes VISIBLES",
            "Automates":    "⚠ ABSENT — les contraintes physiques sont les états cachés du mécanisme",
            "Winter_Tree":  "Family detection: la FORME visible révèle la FAMILLE cachée",
        },
        "root_principle": "Ce qu'on observe est un symptôme. La cause est un état caché. HMM infère la cause.",
    },

    "R4_constraint_satisfaction": {
        "name": "Satisfaction de contraintes / détection de trous",
        "math": "CSP, SAT, programmation par contraintes — qu'est-ce qui manque ?",
        "manifests_as": {
            "Automates":    "90 TROU checks: espace des mécanismes → contraintes → ce qui viole = trou",
            "Yggdrasil":    "Trous A/B/C: espace scientifique → co-occurrence → ce qui manque = trou",
            "Ichimoku":     "⚠ IMPLICITE — risk management = contrainte (MDD < 15%, Sharpe > 0.5)",
            "Infernal":     "⚠ IMPLICITE — seuils d'alerte = contraintes (> 10 drinks = alerte)",
            "Shazam":       "⚠ ABSENT — range MIDI, tempo, key = contraintes sur la musique",
            "Winter_Tree":  "⚠ ABSENT — depends = contraintes d'ordre (build order)",
        },
        "root_principle": "Tout espace a des contraintes. Violer une contrainte = un trou. Trouver les trous = trouver les opportunités.",
    },

    "R5_hierarchical_stratification": {
        "name": "Stratification hiérarchique",
        "math": "Post, Turing, Chomsky — tout se stratifie en niveaux de complexité",
        "manifests_as": {
            "Yggdrasil":    "7 strates S0→S6: hiérarchie arithmétique de Post",
            "Winter_Tree":  "10 niveaux -5→+5: mycorhizes → cime",
            "Shazam":       "4 niveaux L1→L4: difficulté pédagogique",
            "Ichimoku":     "⚠ IMPLICITE — 3/5/8 régimes SONT une stratification du marché",
            "Automates":    "⚠ IMPLICITE — tiers budget/medium/premium = stratification",
            "Infernal":     "⚠ ABSENT — l'addiction a des stades (expérimentation → usage → abus → dépendance)",
        },
        "root_principle": "Tout système se stratifie. Les couches basses fondent les couches hautes. L'ordre de construction compte.",
    },

    "R6_signal_vs_noise": {
        "name": "Séparation signal / bruit",
        "math": "Shannon, Wiener, SVD — extraire le sens du chaos",
        "manifests_as": {
            "Shazam":       "Demucs/HPSS: séparer mélodie du bruit/percussion",
            "Ichimoku":     "Walk-forward + 30 seeds: séparer alpha du surfit",
            "Yggdrasil":    "C1 vs C2: séparer le prouvé du conjecturé",
            "Infernal":     "⚠ PARTIEL — tracking = signal, mais pas de filtre anti-bruit",
            "Automates":    "⚠ ABSENT — quels checks sont du vrai signal vs du bruit de précision?",
            "Winter_Tree":  "⚠ ABSENT — quelle partie du scan repo est signal vs artefact?",
        },
        "root_principle": "Tout signal contient du bruit. Séparer les deux est la première étape de toute analyse.",
    },

    "R7_accumulation_not_force": {
        "name": "Mapping par accumulation (pas par force brute)",
        "math": "Statistique bayésienne — accumuler les preuves jusqu'à la certitude",
        "manifests_as": {
            "Yggdrasil":    "Accumuler les co-occurrences → le pattern émerge seul",
            "Ichimoku":     "Walk-forward accumule les folds → la stratégie émerge",
            "P_eq_NP":      "Mapper par accumulation → le trou dans la carte montre P=NP",
            "Winter_Tree":  "Scanner → scanner → la famille émerge",
            "Automates":    "90 checks accumulés → le mécanisme valide émerge",
            "Shazam":       "Notes accumulées → la tonalité émerge (Krumhansl-Schmuckler)",
            "Infernal":     "Données accumulées → le pattern d'addiction émerge",
        },
        "root_principle": "Ne pas forcer. Accumuler. Le signal émerge du volume. C'est la méthode Sky.",
    },
}


# ── Analyse ───────────────────────────────────────────────────────

def analyse_roots():
    """Analyse quelles racines sont présentes/absentes par projet."""
    projects = set()
    for root in ROOTS.values():
        for p in root["manifests_as"]:
            projects.add(p)

    projects = sorted(projects)

    # Matrice racines × projets
    matrix = {}
    for p in projects:
        matrix[p] = {"present": [], "partial": [], "absent": []}

    for root_id, root in ROOTS.items():
        for project, status in root["manifests_as"].items():
            if status.startswith("⚠ ABSENT"):
                matrix[project]["absent"].append(root_id)
            elif status.startswith("⚠ PARTIEL") or status.startswith("⚠ IMPLICITE"):
                matrix[project]["partial"].append(root_id)
            else:
                matrix[project]["present"].append(root_id)

    return projects, matrix


def find_root_lianes():
    """Trouve les lianes entre racines — les connexions profondes."""
    lianes = []

    for root_id, root in ROOTS.items():
        present_in = []
        absent_in = []
        partial_in = []

        for project, status in root["manifests_as"].items():
            if status.startswith("⚠ ABSENT"):
                absent_in.append(project)
            elif status.startswith("⚠ PARTIEL") or status.startswith("⚠ IMPLICITE"):
                partial_in.append(project)
            else:
                present_in.append(project)

        # Chaque absent = une liane potentielle
        for target in absent_in + partial_in:
            if present_in:
                source = present_in[0]
                is_partial = target in partial_in
                lianes.append({
                    "root": root_id,
                    "root_name": root["name"],
                    "principle": root["root_principle"],
                    "source": source,
                    "source_impl": root["manifests_as"][source],
                    "target": target,
                    "target_status": root["manifests_as"][target],
                    "depth": "partial" if is_partial else "absent",
                    "priority": 1 if is_partial else 2,  # partiel = plus facile à compléter
                })

    lianes.sort(key=lambda x: (x["priority"], x["root"]))
    return lianes


# ── Main ──────────────────────────────────────────────────────────

def main():
    print("=== SCAN RACINES CROSS-PROJETS ===")
    print("Niveau: RACINES (pas outils)")
    print("Méthode: mapper les fondations mathématiques partagées")
    print()

    projects, matrix = analyse_roots()

    # Afficher matrice
    print("--- MATRICE RACINES × PROJETS ---")
    print(f"{'':>15}", end="")
    for root_id in ROOTS:
        print(f"  {root_id[3:9]:>6}", end="")
    print()

    for p in projects:
        print(f"{p:>15}", end="")
        for root_id in ROOTS:
            if root_id in matrix[p]["present"]:
                print(f"  {'██':>6}", end="")
            elif root_id in matrix[p]["partial"]:
                print(f"  {'▒▒':>6}", end="")
            else:
                print(f"  {'··':>6}", end="")
        print()

    print()
    print("██ = présent   ▒▒ = partiel/implicite   ·· = absent")
    print()

    # Score par projet
    print("--- SCORE ENRACINEMENT PAR PROJET ---")
    for p in projects:
        n_present = len(matrix[p]["present"])
        n_partial = len(matrix[p]["partial"])
        n_absent = len(matrix[p]["absent"])
        score = n_present * 2 + n_partial * 1
        total = len(ROOTS) * 2
        pct = 100 * score / total
        bar = "█" * n_present + "▒" * n_partial + "·" * n_absent
        print(f"  {p:>15}: {bar}  {score}/{total} ({pct:.0f}%)")
    print()

    # La racine la plus universelle
    print("--- RACINE LA PLUS UNIVERSELLE ---")
    for root_id, root in ROOTS.items():
        present = sum(1 for s in root["manifests_as"].values() if not s.startswith("⚠"))
        total = len(root["manifests_as"])
        print(f"  {root['name'][:50]:>52}: {present}/{total} projets")
    print()

    # Lianes de racines
    lianes = find_root_lianes()
    print(f"--- LIANES DE RACINES: {len(lianes)} connexions manquantes ---")
    print()

    current_root = None
    for l in lianes:
        if l["root"] != current_root:
            current_root = l["root"]
            print(f"  [{ROOTS[l['root']]['name']}]")
            print(f"  Principe: {l['principle']}")

        depth_marker = "▒" if l["depth"] == "partial" else "·"
        print(f"    {depth_marker} {l['source']:>15} --({l['root'][3:]})--> {l['target']}")
        print(f"      Déjà: {l['source_impl'][:70]}")
        print(f"      Manque: {l['target_status'][:70]}")
        print()

    # Export
    output = {
        "source": "CROSS_ROOTS_SCAN",
        "generated": datetime.now().isoformat(),
        "roots": {k: {
            "name": v["name"],
            "math": v["math"],
            "principle": v["root_principle"],
            "manifests": v["manifests_as"],
        } for k, v in ROOTS.items()},
        "matrix": matrix,
        "lianes": lianes,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "cross_roots.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Export: {out_path}")


if __name__ == "__main__":
    main()
