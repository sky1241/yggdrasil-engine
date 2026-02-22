#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCAN P4 CROSS-PROJETS
=====================
Applique la logique Yggdrasil (détection de trous structurels)
aux PROPRES PROJETS de Sky.

Chaque projet = un continent.
Chaque technique utilisée = un outil S0.
Connexion manquante = P4 (trou structurel = opportunité).

Usage:
    python engine/cross_projects.py
"""
import json
import os
from datetime import datetime
from itertools import combinations

# ── Définition des projets et leurs outils ────────────────────────

PROJECTS = {
    "Yggdrasil": {
        "desc": "Détection trous structurels dans la science",
        "tools": [
            "spectral_layout", "laplacien", "co_occurrence",
            "betweenness_centrality", "physarum", "fitness_wang",
            "disruption_index", "uzzi_zscore", "fiedler_vector",
            "meshedness", "graph_theory", "pattern_classification",
            "openalex_api", "strate_hierarchy",
        ],
        "domains": ["graph_theory", "scientometrics", "biology", "topology"],
    },
    "Ichimoku": {
        "desc": "Trading crypto adaptatif par régime de marché",
        "tools": [
            "welch_psd", "fft", "hmm_regime", "lightgbm",
            "walk_forward", "monte_carlo", "ichimoku",
            "atr", "kelly_criterion", "optuna",
            "halving_indexer", "position_sizing",
            "checkpoint_recovery", "volatility_targeting",
        ],
        "domains": ["signal_processing", "machine_learning", "finance", "statistics"],
    },
    "Automates": {
        "desc": "Générateur d'automates mécaniques 3D",
        "tools": [
            "constraint_engine", "cam_mechanics", "grashof_condition",
            "geneva_mechanism", "worm_gear", "torque_calc",
            "shaft_deflection", "trimesh_3d", "stl_export",
            "figurine_builder", "text_to_config_nlp",
            "material_science", "print_orientation",
        ],
        "domains": ["mechanical_engineering", "3d_printing", "nlp", "physics"],
    },
    "Shazam_Piano": {
        "desc": "Pipeline audio → partition → vidéo pédagogique",
        "tools": [
            "pyin_pitch", "krumhansl_key", "demucs_separation",
            "midi_quantization", "arranger_4levels",
            "nsdf_autocorrelation", "mpm_algorithm",
            "ffmpeg_pipeline", "flutter_riverpod",
        ],
        "domains": ["signal_processing", "music_theory", "mobile_dev", "pedagogy"],
    },
    "Infernal_Wheel": {
        "desc": "Tracking addiction + santé personnelle",
        "tools": [
            "powershell_http", "mutex_io", "infernal_day_4am",
            "addiction_tracking", "health_integration",
            "ux_framework_5200lines", "flutter_hive",
            "trilateration_ml", "cnn_lstm", "dbscan",
        ],
        "domains": ["health_science", "mobile_dev", "machine_learning", "ux_design"],
    },
    "Winter_Tree": {
        "desc": "Framework de classification + orchestration AI",
        "tools": [
            "bio_classification", "repo_scanner", "github_scanner",
            "tree_hierarchy_10levels", "family_detection",
            "handoff_protocol", "master_prompt",
            "mycelium_engine", "l_system", "physarum",
            "sporulation", "nutrient_transport",
        ],
        "domains": ["biology", "software_architecture", "ai_orchestration", "mycology"],
    },
    "P_eq_NP": {
        "desc": "Mapping par accumulation de la complexité",
        "tools": [
            "strate_hierarchy", "mycelium_mapping",
            "periodic_table_complexity", "bounded_strata",
        ],
        "domains": ["complexity_theory", "mathematics", "topology"],
    },
}

# ── Outils partagés entre domaines (lianes potentielles) ──────────

CROSS_DOMAIN_TOOLS = {
    # Outils qui EXISTENT dans un projet mais DEVRAIENT être dans un autre
    "welch_psd": {
        "exists_in": ["Ichimoku"],
        "should_be_in": ["Infernal_Wheel", "Shazam_Piano"],
        "why": "Détection de cycles cachés dans tout signal temporel",
    },
    "hmm_regime": {
        "exists_in": ["Ichimoku"],
        "should_be_in": ["Infernal_Wheel", "Yggdrasil"],
        "why": "Détection de régimes dans addiction (sober/moderate/heavy) et dans l'évolution scientifique",
    },
    "physarum": {
        "exists_in": ["Yggdrasil", "Winter_Tree"],
        "should_be_in": ["Ichimoku"],
        "why": "Optimisation de flux = allocation de capital. Physarum trouve les chemins optimaux.",
    },
    "constraint_engine": {
        "exists_in": ["Automates"],
        "should_be_in": ["Yggdrasil"],
        "why": "Les TROU checks sont identiques aux trous structurels — même pattern de détection",
    },
    "pattern_classification": {
        "exists_in": ["Yggdrasil"],
        "should_be_in": ["Ichimoku", "Infernal_Wheel"],
        "why": "P1-P5 patterns applicables aux régimes de marché et aux patterns d'addiction",
    },
    "disruption_index": {
        "exists_in": ["Yggdrasil"],
        "should_be_in": ["Ichimoku"],
        "why": "D-index mesure si un paper est disruptif. Appliqué au trading: une bougie est-elle disruptive?",
    },
    "persistent_homology": {
        "exists_in": [],
        "should_be_in": ["Yggdrasil", "Ichimoku"],
        "why": "Topologie persistante détecte les structures qui survivent à différentes échelles — P4 pur",
    },
    "shannon_entropy": {
        "exists_in": [],
        "should_be_in": ["Ichimoku", "Infernal_Wheel", "Yggdrasil"],
        "why": "Entropie du signal = mesure du désordre. Applicable partout.",
    },
    "combined_labels": {
        "exists_in": ["Ichimoku"],
        "should_be_in": ["Infernal_Wheel"],
        "why": "IF regime==bear FORCE CASH → IF regime==depression FORCE REST. Même logique.",
    },
    "krumhansl_key": {
        "exists_in": ["Shazam_Piano"],
        "should_be_in": [],
        "why": "Détection de tonalité par corrélation de profil — applicable à tout signal périodique?",
    },
    "repo_scanner": {
        "exists_in": ["Winter_Tree"],
        "should_be_in": ["Yggdrasil"],
        "why": "Scanner un repo ET son domaine scientifique simultanément",
    },
}


# ── Détection P4 ──────────────────────────────────────────────────

def detect_p4_holes():
    """Trouve les connexions manquantes entre projets (P4 = trou structurel)."""
    holes = []

    for tool_name, tool_info in CROSS_DOMAIN_TOOLS.items():
        for target in tool_info["should_be_in"]:
            if target not in tool_info["exists_in"]:
                # C'est un P4 — l'outil existe quelque part mais pas ici
                source = tool_info["exists_in"][0] if tool_info["exists_in"] else "NOUVEAU"

                # Calculer le score d'impact
                # Plus l'outil est partagé (liane), plus l'impact est haut
                n_exists = len(tool_info["exists_in"])
                n_should = len(tool_info["should_be_in"])

                if n_exists == 0:
                    # Outil qui n'existe nulle part — innovation pure
                    impact = 10
                    hole_type = "B"  # Conceptuel — personne n'y a pensé
                else:
                    # Outil qui existe mais pas branché — pont manquant
                    impact = 5 + n_should
                    hole_type = "B" if n_exists == 0 else "C"  # Perceptuel — existe mais pas vu

                holes.append({
                    "tool": tool_name,
                    "from": source,
                    "to": target,
                    "type": hole_type,
                    "impact": impact,
                    "why": tool_info["why"],
                    "status": "P4_OPEN",
                })

    # Trier par impact
    holes.sort(key=lambda x: -x["impact"])
    return holes


# ── Matrice de co-occurrence entre projets ────────────────────────

def compute_project_matrix():
    """Matrice de connexion entre projets via outils partagés."""
    project_names = list(PROJECTS.keys())
    n = len(project_names)
    matrix = [[0] * n for _ in range(n)]

    # Compter les outils partagés
    for i, p1 in enumerate(project_names):
        tools1 = set(PROJECTS[p1]["tools"])
        for j, p2 in enumerate(project_names):
            if i >= j:
                continue
            tools2 = set(PROJECTS[p2]["tools"])
            shared = tools1 & tools2
            matrix[i][j] = len(shared)
            matrix[j][i] = len(shared)

    # Compter les domaines partagés
    domain_matrix = [[0] * n for _ in range(n)]
    for i, p1 in enumerate(project_names):
        domains1 = set(PROJECTS[p1]["domains"])
        for j, p2 in enumerate(project_names):
            if i >= j:
                continue
            domains2 = set(PROJECTS[p2]["domains"])
            shared = domains1 & domains2
            domain_matrix[i][j] = len(shared)
            domain_matrix[j][i] = len(shared)

    return project_names, matrix, domain_matrix


# ── Main ──────────────────────────────────────────────────────────

def main():
    print("=== SCAN P4 CROSS-PROJETS ===")
    print("Méthode: Yggdrasil appliqué à lui-même")
    print(f"Projets: {len(PROJECTS)}")
    print()

    # Matrice
    names, tool_matrix, domain_matrix = compute_project_matrix()

    print("--- MATRICE OUTILS PARTAGES ---")
    header = "              " + "  ".join(f"{n[:6]:>6}" for n in names)
    print(header)
    for i, name in enumerate(names):
        row = f"{name[:12]:>12}  " + "  ".join(f"{tool_matrix[i][j]:>6}" for j in range(len(names)))
        print(row)
    print()

    print("--- MATRICE DOMAINES PARTAGES ---")
    print(header)
    for i, name in enumerate(names):
        row = f"{name[:12]:>12}  " + "  ".join(f"{domain_matrix[i][j]:>6}" for j in range(len(names)))
        print(row)
    print()

    # Paires les plus isolées (P4 candidats)
    print("--- PAIRES LES PLUS ISOLEES (0 outils communs) ---")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if tool_matrix[i][j] == 0:
                print(f"  {names[i]} <-> {names[j]}: 0 outils, {domain_matrix[i][j]} domaines")
    print()

    # Trous P4
    holes = detect_p4_holes()
    print(f"--- TROUS P4 DETECTES: {len(holes)} ---")
    print()
    for h in holes:
        print(f"  [{h['type']}] {h['tool']}")
        print(f"      {h['from']} --> {h['to']}  (impact: {h['impact']})")
        print(f"      {h['why']}")
        print()

    # Top 5 actions prioritaires
    print("--- TOP 5 ACTIONS PRIORITAIRES ---")
    for i, h in enumerate(holes[:5]):
        print(f"  {i+1}. Brancher {h['tool']} de {h['from']} dans {h['to']}")
        print(f"     Pourquoi: {h['why']}")
        print()

    # Export
    output = {
        "source": "CROSS_PROJECTS_P4_SCAN",
        "generated": datetime.now().isoformat(),
        "projects": {k: v for k, v in PROJECTS.items()},
        "holes": holes,
        "tool_matrix": {
            "names": names,
            "values": tool_matrix,
        },
        "domain_matrix": {
            "names": names,
            "values": domain_matrix,
        },
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cross", "cross_projects_p4.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Export: {out_path}")


if __name__ == "__main__":
    main()
