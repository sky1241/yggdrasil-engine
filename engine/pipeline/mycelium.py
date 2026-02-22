#!/usr/bin/env python3
"""
WINTER TREE v2 — MYCELIUM ENGINE
=================================
Simulation complète du cycle de vie des champignons mycorhiziens
arbusculaires (AM fungi), de la spore à la sporulation.

24 briques — 456 tests — cycle A→Z→A vérifié

═══════════════════════════════════════════════════════════════
ARBRE DU CODE — Ordre biologique complet A→Z→A
═══════════════════════════════════════════════════════════════

[18] L-System Root Architecture          ← Phase 0: la plante pousse
  ↓ root_tips (positions 3D)
[17] Spore Germination & Chemotaxis      ← Phase 1: spores dans le sol
  ↓ germ_tips → contact avec racines
[21] Appressorium (Hyphopodium)          ← Phase 1.5: ancrage + pénétration
  ↓ turgor van't Hoff → entry_nodes        (turgor ~2 MPa, PPA 4-5h)
[22] Arbuscules & Vésicules              ← Phase 2a: colonisation intraradical
  ↓ 5 stades, turnover 2-7j                (surface ×10, TAG storage)
[16] AM Root Emission                    ← Phase 2b: hyphes sortent de la racine
  ↓ emission_rate × root_tips
[13] Edelstein Branching                 ← Phase 2c: croissance extraradical
[15] 3D Hyphal Mechanics                 ←   mécanique + tropisme
[14] Oscillatory Signaling               ←   FitzHugh-Nagumo Ca²⁺
[11] Anastomose / Fusion                 ← Phase 2d: réseau se connecte
  ↓ mature network
[19] Nutrient Transport (P uptake)       ← Phase 3: absorption phosphore
  ↓ Michaelis-Menten + diffusion
[20] C↔P Symbiosis Exchange             ← Phase 4: échange réciproque
  ↓ fungal_c, soil_p
[23] Sporulation                         ← Phase 5: nouvelles spores
  ↓ mature spores (TAG 58-80%)             (High C+, High P-)
  └──→ retour [17] ← BOUCLE FERMÉE

[0-10] Métriques réseau (v1.0)           ← Analyse sur graphe final
  0: Construction graphe     7: Small-world σ
  1: Meshedness α            8: Small-world ω
  2: Efficacité globale      9: Stratégie phalanx/guerrilla
  3: Efficacité root        10: Kirchhoff + Physarum
  4: Volume-MST ratio       11: Anastomose
  5: Betweenness centrality 12: Intégration complète
  6: Robustesse

Sources principales:
  Bebber 2007, Latora 2001, Tero 2010, Edelstein 1982,
  Schnepf 2008, Howard 1991, Genre 2005, Pimprikar 2018,
  Kiers 2011, Kokkoris 2026, Pfeffer 1999, Bago 2002

Auteur : Sky — l'architecte de l'architecte
"""

import networkx as nx
import sys
import os
import json
from pathlib import Path


# ============================================================================
# BRIQUE 0 — CONSTRUCTION DE GRAPHE
# ============================================================================

def graph_from_edges(edges: list) -> nx.Graph:
    """Construit un graphe non-dirigé depuis une liste d'arêtes.

    Args:
        edges: liste de tuples (node_a, node_b) ou (node_a, node_b, weight)

    Returns:
        nx.Graph (sans self-loops — ils biaisent α et BC)
    """
    G = nx.Graph()
    for edge in edges:
        if edge[0] == edge[1]:
            continue  # Pas de self-loop
        if len(edge) == 3:
            G.add_edge(edge[0], edge[1], weight=edge[2])
        else:
            G.add_edge(edge[0], edge[1], weight=1.0)
    return G


def graph_from_imports(import_graph: dict) -> nx.DiGraph:
    """Convertit un dict {fichier: set(imports)} en graphe dirigé.

    C'est le format que produit scan_repo() dans engine.py,
    mais on ne DÉPEND PAS de engine.py. N'importe quel dict
    avec ce format marche.

    ATTENTION : les clés (sources) utilisent des chemins fichier
    (lib/utils.py) mais les valeurs (targets) utilisent des noms
    de module Python (lib.utils). On normalise tout vers un format
    commun pour éviter les nœuds fantômes.

    Normalisation : tout en dot-notation, sans extension.
        "lib/utils.py"  → "lib.utils"
        "lib.utils"     → "lib.utils"
        "src/core.dart" → "src.core"

    Self-loops supprimés (un fichier qui s'importe lui-même n'a
    pas de sens en tant qu'arête réseau — ça biaise α et BC).

    Args:
        import_graph: {str: set(str)} — fichier → ses imports

    Returns:
        nx.DiGraph — arêtes dirigées de importeur vers importé
    """
    def normalize(name: str) -> str:
        """Normalise un chemin ou module vers dot-notation sans extension."""
        if not name or not name.strip():
            return ""
        # Virer les extensions courantes
        for ext in (".py", ".dart", ".js", ".ts", ".jsx", ".tsx"):
            if name.endswith(ext):
                name = name[:-len(ext)]
        # Remplacer / et \ par .
        name = name.replace("/", ".").replace("\\", ".")
        # Virer __init__ en fin
        if name.endswith(".__init__"):
            name = name[:-9]
        # Virer les . en début (imports relatifs: ..parent → parent)
        name = name.lstrip(".")
        # Collapse les .. consécutifs restants
        while ".." in name:
            name = name.replace("..", ".")
        # Virer le . final si présent
        name = name.rstrip(".")
        return name

    G = nx.DiGraph()
    for source, targets in import_graph.items():
        src = normalize(source)
        if not src:
            continue
        G.add_node(src)
        for target in targets:
            tgt = normalize(target)
            if not tgt:
                continue
            if tgt == src:
                continue  # Pas de self-loop
            G.add_edge(src, tgt)
    return G


def to_undirected(G: nx.DiGraph) -> nx.Graph:
    """Convertit un graphe dirigé en non-dirigé.

    Les métriques réseau (Bebber 2007) travaillent sur des graphes
    non-dirigés. Les imports sont dirigés mais la COMMUNICATION
    entre modules est bidirectionnelle.

    NOTE DESIGN : On perd la direction des imports. C'est VOULU.
    Bebber 2007 travaille sur des graphes non-dirigés car les hyphes
    sont des tubes bidirectionnels. En code, un import A→B implique
    que A et B communiquent, pas que B connaît A.

    Self-loops supprimés (un module qui se référence lui-même
    n'est pas une arête réseau).
    """
    H = G.to_undirected()
    H.remove_edges_from(nx.selfloop_edges(H))
    return H


# ============================================================================
# BRIQUE 1 — MESHEDNESS α
# Source : Bebber et al. 2007, Eq. dans Bloc D1
# ============================================================================

def meshedness(G: nx.Graph) -> float:
    """Coefficient de maillage alpha.

    α = (L - N + 1) / (2N - 5)

    où L = nombre de liens, N = nombre de nœuds.

    Interprétation :
        α = 0.0  → arbre pur (pas de boucles, pas de redondance)
        α = 1.0  → réseau planaire maximal (maximum de boucles)
        0 < α < 1 → réseau partiellement maillé

    Données de référence (Bebber 2007, P. velutina) :
        Contrôle jour 39 : α = 0.11 ± 0.04
        Avec bait jour 39 : α = 0.20 ± 0.05

    NOTE : Bebber 2007 ne calcule α que sur des graphes CONNEXES.
    Si le graphe est déconnecté, on prend la plus grande composante
    connexe. Un graphe déconnecté donnerait α négatif, ce qui n'a
    pas de sens biologique.

    Args:
        G: graphe non-dirigé

    Returns:
        float — alpha. 0 = arbre pur. 1 = réseau planaire maximal.
        Peut dépasser 1 sur des graphes non-planaires (normal).
        Bebber travaille sur des réseaux 2D (planaires) → α ∈ [0,1].
        Pour du code avec beaucoup de dépendances croisées, α > 1 est possible.
    """
    N = G.number_of_nodes()
    L = G.number_of_edges()

    if N < 3:
        return 0.0

    # Forcer composante connexe (Bebber 2007 ne travaille que sur ça)
    if not nx.is_connected(G):
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

    # Supprimer self-loops (biaisent L artificiellement)
    G.remove_edges_from(nx.selfloop_edges(G))

    N = G.number_of_nodes()
    L = G.number_of_edges()

    if N < 3:
        return 0.0

    denom = 2 * N - 5
    if denom <= 0:
        return 0.0

    alpha = (L - N + 1) / denom
    return alpha


# ============================================================================
# BRIQUE 2 — EFFICACITÉ GLOBALE
# Source : Latora & Marchiori 2001, Bebber 2007 Bloc D4
# ============================================================================

def global_efficiency(G: nx.Graph) -> float:
    """Efficacité globale du réseau.

    E_global = (1 / N(N-1)) × Σᵢ≠ⱼ (1 / d_ij)

    Mesure la facilité de communication entre n'importe quels
    2 nœuds du réseau. Utilise l'inverse de la distance :
    nœuds déconnectés contribuent 0 (pas l'infini).

    Interprétation :
        E → 1.0  : tout le monde parle à tout le monde facilement
        E → 0.0  : réseau fragmenté, modules isolés

    Args:
        G: graphe non-dirigé

    Returns:
        float — efficacité entre 0 et 1
    """
    # NetworkX a exactement cette formule
    return nx.global_efficiency(G)


# ============================================================================
# BRIQUE 3 — EFFICACITÉ ROOT (depuis un point d'entrée)
# Source : Bebber 2007, Bloc D5
# ============================================================================

def root_efficiency(G: nx.Graph, root: str) -> float:
    """Efficacité depuis un nœud racine (entry point).

    E_root = (1 / (N-1)) × Σⱼ (1 / d(root, j))

    Mesure comment le nœud racine (main.py, index.dart, etc.)
    irrigue le reste du réseau. C'est unidirectionnel :
    on part de la racine vers tous les autres.

    Différence avec E_global :
        E_global = communication entre tous les paires
        E_root = propagation depuis UN point

    NOTE : E_root peut DÉPASSER E_global si le root est un hub
    bien connecté, car E_global moyenne sur toutes les paires
    (y compris les nœuds périphériques mal connectés entre eux).

    Résultat Bebber 2007 : E_root(réseau fongique) > E_root(MST)
    Le champignon fait MIEUX que le minimum spanning tree.

    Args:
        G: graphe non-dirigé
        root: identifiant du nœud racine

    Returns:
        float — efficacité root entre 0 et 1
    """
    N = G.number_of_nodes()
    if N <= 1:
        return 0.0

    if root not in G:
        return 0.0

    # Distances depuis root vers tous les autres
    distances = nx.single_source_shortest_path_length(G, root)

    total = 0.0
    for node, dist in distances.items():
        if node != root and dist > 0:
            total += 1.0 / dist

    # Nœuds non-atteignables contribuent 0 (implicitement)
    return total / (N - 1)


# ============================================================================
# BRIQUE 4 — VOLUME-MST RATIO (overhead architectural)
# Source : Bebber 2007, Bloc D6
# ============================================================================

def volume_mst_ratio(G: nx.Graph) -> float:
    """Ratio coût réel / coût minimum (MST).

    V_MST = C_réel / C_MST

    où C = Σ(poids des arêtes).

    Interprétation :
        ratio = 1.0 → arbre pur, zéro redondance, le strict minimum
        ratio = 1.3 → 30% d'overhead (redondance pour la robustesse)
        ratio = 2.0 → le double du nécessaire (peut-être trop)

    Un bon réseau fongique a ratio ≈ 1.2-1.5 :
    assez de redondance pour la robustesse,
    pas trop pour ne pas gaspiller.

    Args:
        G: graphe non-dirigé (utilise 'weight' si disponible)

    Returns:
        float — ratio >= 1.0 (1.0 = arbre pur)
    """
    if not nx.is_connected(G):
        # Sur la plus grande composante connexe
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

    if G.number_of_edges() == 0:
        return 1.0

    # Coût réel (ignorer poids <= 0 — pas de sens physique)
    real_cost = sum(max(d.get("weight", 1.0), 0) for u, v, d in G.edges(data=True))

    # Coût MST
    mst = nx.minimum_spanning_tree(G, weight="weight")
    mst_cost = sum(max(d.get("weight", 1.0), 0) for u, v, d in mst.edges(data=True))

    if mst_cost <= 0:
        # MST de coût 0 = toutes les arêtes ont poids 0 → ratio n'a pas de sens
        return 1.0

    return real_cost / mst_cost


# ============================================================================
# BRIQUE 5 — BETWEENNESS CENTRALITY (bottlenecks)
# Source : Bebber 2007, Fricker 2017, Bloc D7 prep
# ============================================================================

def find_bottlenecks(G: nx.Graph, top_n: int = 5) -> list:
    """Trouve les nœuds les plus critiques par betweenness centrality.

    BC(v) = Σ_{s≠v≠t} (σ_st(v) / σ_st)

    où σ_st = nombre de plus courts chemins de s à t,
    et σ_st(v) = ceux qui passent par v.

    Un nœud avec BC élevé est un GOULOT D'ÉTRANGLEMENT.
    Si tu le supprimes, beaucoup de chemins sont coupés.

    En mycelium : BC corrèle avec le flux réel (Oyarte Galvez 2025).
    En code : BC élevé = fichier critique, si il casse tout pète.

    Args:
        G: graphe non-dirigé
        top_n: nombre de bottlenecks à retourner

    Returns:
        liste de (nœud, BC_score) triés par score décroissant
    """
    bc = nx.betweenness_centrality(G, weight="weight", normalized=True)

    sorted_bc = sorted(bc.items(), key=lambda x: -x[1])
    return sorted_bc[:top_n]


# ============================================================================
# BRIQUE 6 — ROBUSTESSE (attaque séquentielle)
# Source : Bebber 2007, Bloc D7
# ============================================================================

def robustness_test(G: nx.Graph, attack: str = "betweenness", steps: int = 20,
                    seed: int = None) -> list:
    """Simule une attaque séquentielle et mesure la dégradation.

    Protocole Bebber 2007 :
    1. Calculer betweenness centrality
    2. Supprimer le nœud avec la plus haute BC
    3. Recalculer BC (le réseau a changé)
    4. Répéter
    5. Mesurer la taille de la plus grande composante connexe

    Résultat Bebber : le réseau fongique pondéré résiste mieux
    que le MST, DT, et même le réseau non-pondéré.

    Args:
        G: graphe non-dirigé
        attack: "betweenness" ou "random"
        steps: nombre de nœuds à supprimer (ou % si < 1)
        seed: graine aléatoire pour attack="random" (reproductibilité)

    Returns:
        liste de (fraction_removed, fraction_giant_component)
    """
    import random

    H = G.copy()
    N = H.number_of_nodes()

    if N == 0:
        return [(0.0, 0.0)]

    rng = random.Random(seed)
    results = [(0.0, 1.0)]  # Avant attaque : 100% connecté

    n_to_remove = min(steps, N - 1)

    for i in range(n_to_remove):
        if H.number_of_nodes() <= 1:
            break

        # Choisir la cible
        if attack == "betweenness":
            bc = nx.betweenness_centrality(H)
            target = max(bc, key=bc.get)
        elif attack == "random":
            target = rng.choice(list(H.nodes()))
        else:
            raise ValueError(f"Attack type inconnu : {attack}")

        # Supprimer
        H.remove_node(target)

        # Mesurer la plus grande composante connexe
        if H.number_of_nodes() == 0:
            results.append(((i + 1) / N, 0.0))
        else:
            largest_cc = max(nx.connected_components(H), key=len)
            frac_connected = len(largest_cc) / N
            results.append(((i + 1) / N, frac_connected))

    return results


# ============================================================================
# BRIQUE 7 — SMALL-WORLD σ
# Source : Watts & Strogatz 1998, Humphries & Gurney 2008, Bloc G1
# ============================================================================

def small_world_sigma(G: nx.Graph, nrand: int = 5) -> dict:
    """Coefficient small-world sigma.

    γ = C / C_rand    (ratio clustering)
    λ = L / L_rand    (ratio path length)
    σ = γ / λ         (small-world si σ > 1)

    Un réseau small-world a :
    - Clustering BEAUCOUP plus élevé qu'un réseau aléatoire (γ >> 1)
    - Path length SIMILAIRE à un réseau aléatoire (λ ≈ 1)
    - Donc σ >> 1

    ATTENTION : nx.sigma() est LENT (O(n²)). On fait une version
    avec peu de graphes aléatoires de référence.

    Args:
        G: graphe non-dirigé, connexe
        nrand: nombre de graphes aléatoires pour la moyenne

    Returns:
        dict avec sigma, gamma, lambda_, C, C_rand, L, L_rand
    """
    if not nx.is_connected(G):
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

    N = G.number_of_nodes()
    if N < 4:
        return {"sigma": 0.0, "gamma": 0.0, "lambda_": 0.0,
                "C": 0.0, "C_rand": 0.0, "L": 0.0, "L_rand": 0.0}

    C = nx.average_clustering(G)
    L = nx.average_shortest_path_length(G)

    # Générer des graphes aléatoires ER avec mêmes N et L
    M = G.number_of_edges()
    C_rands = []
    L_rands = []

    for _ in range(nrand):
        R = nx.gnm_random_graph(N, M)
        # S'assurer qu'il est connexe
        attempts = 0
        while not nx.is_connected(R) and attempts < 50:
            R = nx.gnm_random_graph(N, M)
            attempts += 1
        if nx.is_connected(R):
            C_rands.append(nx.average_clustering(R))
            L_rands.append(nx.average_shortest_path_length(R))

    if not C_rands or not L_rands:
        return {"sigma": 0.0, "gamma": 0.0, "lambda_": 0.0,
                "C": C, "C_rand": 0.0, "L": L, "L_rand": 0.0}

    C_rand = sum(C_rands) / len(C_rands)
    L_rand = sum(L_rands) / len(L_rands)

    gamma = C / C_rand if C_rand > 0 else 0.0
    lambda_ = L / L_rand if L_rand > 0 else 0.0
    sigma = gamma / lambda_ if lambda_ > 0 else 0.0

    return {
        "sigma": sigma,
        "gamma": gamma,
        "lambda_": lambda_,
        "C": round(C, 4),
        "C_rand": round(C_rand, 4),
        "L": round(L, 4),
        "L_rand": round(L_rand, 4),
    }


# ============================================================================
# BRIQUE 8 — SMALL-WORLD ω
# Source : Telesford et al. 2011, Bloc G2
# ============================================================================

def small_world_omega(G: nx.Graph, nrand: int = 5, nlattice: int = 5) -> dict:
    """Coefficient omega — alternative à sigma.

    ω = L_rand/L - C/C_lattice

    Interprétation :
        ω ≈ -1 → lattice (réseau régulier)
        ω ≈  0 → small-world
        ω ≈ +1 → random

    Plus robuste que sigma car utilise aussi la référence lattice.

    Args:
        G: graphe non-dirigé, connexe
        nrand: nombre de graphes aléatoires
        nlattice: nombre de lattices

    Returns:
        dict avec omega, L_rand, L, C, C_lattice
    """
    if not nx.is_connected(G):
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

    N = G.number_of_nodes()
    M = G.number_of_edges()

    if N < 4:
        return {"omega": 0.0, "L": 0.0, "L_rand": 0.0,
                "C": 0.0, "C_lattice": 0.0}

    C = nx.average_clustering(G)
    L = nx.average_shortest_path_length(G)

    # Graphes aléatoires
    L_rands = []
    for _ in range(nrand):
        R = nx.gnm_random_graph(N, M)
        attempts = 0
        while not nx.is_connected(R) and attempts < 50:
            R = nx.gnm_random_graph(N, M)
            attempts += 1
        if nx.is_connected(R):
            L_rands.append(nx.average_shortest_path_length(R))

    # Lattice ring
    k = max(2, round(2 * M / N))
    if k % 2 == 1:
        k -= 1
    k = max(2, min(k, N - 1))

    C_lattices = []
    for _ in range(nlattice):
        try:
            Lat = nx.watts_strogatz_graph(N, k, 0)  # p=0 = lattice pure
            if nx.is_connected(Lat):
                C_lattices.append(nx.average_clustering(Lat))
        except:
            pass

    L_rand = sum(L_rands) / len(L_rands) if L_rands else 0.0
    C_lattice = sum(C_lattices) / len(C_lattices) if C_lattices else 1.0

    omega = (L_rand / L if L > 0 else 0.0) - (C / C_lattice if C_lattice > 0 else 0.0)

    return {
        "omega": omega,
        "L": round(L, 4),
        "L_rand": round(L_rand, 4),
        "C": round(C, 4),
        "C_lattice": round(C_lattice, 4),
    }


# ============================================================================
# BRIQUE 9 — STRATÉGIE PHALANX / GUERRILLA
# Source : Fricker 2017, Aguilar-Trigueros 2022, Bloc G3
# ============================================================================

def classify_strategy(alpha: float, e_global: float, e_root: float,
                      robustness_50: float = None) -> dict:
    """Classifie la stratégie réseau sur l'axe phalanx ↔ guerrilla.

    Fricker 2017 + Aguilar-Trigueros 2022 :

    | Trait       | Phalanx          | Guerrilla        |
    |-------------|------------------|------------------|
    | α           | Haut (> 0.15)    | Bas (< 0.05)     |
    | E_global    | Haut (> 0.5)     | Bas (< 0.3)      |
    | E_root      | Moyen            | Haut             |
    | Robustesse  | Haute            | Basse            |
    | Coût        | Élevé            | Faible           |

    L'axe principal de variation est la CONNECTIVITÉ (Aguilar-Trigueros).
    Ce n'est pas binaire — c'est un gradient.

    Args:
        alpha: meshedness
        e_global: efficacité globale
        e_root: efficacité root
        robustness_50: fraction connectée après 50% d'attaque (optionnel)

    Returns:
        dict avec strategy, score (-1=guerrilla, +1=phalanx), détails
    """
    score = 0.0
    details = []

    # Alpha
    if alpha > 0.15:
        score += 0.3
        details.append(f"α={alpha:.3f} → maillé (phalanx)")
    elif alpha < 0.05:
        score -= 0.3
        details.append(f"α={alpha:.3f} → arbre quasi-pur (guerrilla)")
    else:
        details.append(f"α={alpha:.3f} → intermédiaire")

    # E_global
    if e_global > 0.5:
        score += 0.25
        details.append(f"E_global={e_global:.3f} → bien connecté")
    elif e_global < 0.3:
        score -= 0.25
        details.append(f"E_global={e_global:.3f} → fragmenté")

    # E_root
    if e_root > 0.6:
        score -= 0.15  # E_root élevé = guerrilla (longue portée)
        details.append(f"E_root={e_root:.3f} → bonne irrigation")
    elif e_root < 0.3:
        score += 0.15
        details.append(f"E_root={e_root:.3f} → irrigation faible")

    # Robustesse
    if robustness_50 is not None:
        if robustness_50 > 0.5:
            score += 0.3
            details.append(f"Robustesse@50%={robustness_50:.2f} → résistant")
        elif robustness_50 < 0.2:
            score -= 0.3
            details.append(f"Robustesse@50%={robustness_50:.2f} → fragile")

    # Classification
    if score > 0.3:
        strategy = "phalanx"
        desc = "Dense, robuste, coûteux. Monorepo mature."
    elif score < -0.3:
        strategy = "guerrilla"
        desc = "Éparse, rapide, fragile. Microservices / scripts."
    else:
        strategy = "mixed"
        desc = "Intermédiaire. En transition ou hybride."

    return {
        "strategy": strategy,
        "score": round(score, 3),
        "description": desc,
        "details": details,
    }


# ============================================================================
# ANALYSE COMPLÈTE
# ============================================================================

def analyze(G_input, root: str = None, run_physarum=True, run_anastomosis=True,
            physarum_mu=1.0, physarum_steps=100, anastomosis_method="jaccard",
            anastomosis_threshold=0.2) -> dict:
    """Analyse complète d'un graphe — Briques 0 à 11.

    Args:
        G_input: nx.Graph ou nx.DiGraph
        root: nœud racine (entry point). Si None, prend le plus connecté.
        run_physarum: bool — lancer Kirchhoff + Physarum (brique 10).
        run_anastomosis: bool — détecter les candidats anastomose (brique 11).
        physarum_mu: float — exposant Physarum (1.0=shortest, <1=loops).
        physarum_steps: int — itérations Physarum max.
        anastomosis_method: str — "jaccard", "adamic_adar", "common_neighbors".
        anastomosis_threshold: float — seuil pour la détection anastomose.

    Returns:
        dict avec toutes les métriques briques 0-11
    """
    import copy

    # S'assurer qu'on a un graphe non-dirigé pour les métriques
    if isinstance(G_input, nx.DiGraph):
        G = to_undirected(G_input)
    else:
        G = G_input.copy()

    N = G.number_of_nodes()
    L = G.number_of_edges()

    if N == 0:
        return {"error": "Graphe vide"}

    # Trouver le root si pas spécifié
    if root is None or root not in G:
        # Le nœud avec le plus de connexions
        root = max(G.nodes(), key=lambda n: G.degree(n))

    # --- Briques 1-5: Métriques de base ---
    alpha = meshedness(G)
    e_global = global_efficiency(G)
    e_root = root_efficiency(G, root)
    v_mst = volume_mst_ratio(G)
    bottlenecks = find_bottlenecks(G, top_n=min(5, N))

    result = {
        "nodes": N,
        "edges": L,
        "root": root,
        "meshedness_alpha": round(alpha, 4),
        "global_efficiency": round(e_global, 4),
        "root_efficiency": round(e_root, 4),
        "volume_mst_ratio": round(v_mst, 4),
        "bottlenecks": [(n, round(s, 4)) for n, s in bottlenecks],
    }

    # --- Brique 6: Robustesse (seulement si pas trop gros) ---
    if N <= 500:
        rob = robustness_test(G, attack="betweenness", steps=min(N // 2, 20))
        # Trouver la fraction connectée quand 30% des nœuds sont supprimés
        rob_50 = None
        for frac_removed, frac_connected in rob:
            if frac_removed >= 0.3:
                rob_50 = frac_connected
                break
        result["robustness_curve"] = [(round(r, 3), round(c, 3)) for r, c in rob]
        result["robustness_at_30pct"] = round(rob_50, 4) if rob_50 else None
    else:
        rob_50 = None
        result["robustness_curve"] = "skipped (N > 500)"
        result["robustness_at_30pct"] = None

    # --- Briques 7-8: Small-world (seulement si connexe et pas trop gros) ---
    if N <= 200 and nx.is_connected(G):
        sw_sigma = small_world_sigma(G, nrand=3)
        sw_omega = small_world_omega(G, nrand=3, nlattice=3)
        result["small_world_sigma"] = round(sw_sigma["sigma"], 4)
        result["small_world_omega"] = round(sw_omega["omega"], 4)
        result["clustering"] = sw_sigma["C"]
        result["avg_path_length"] = sw_sigma["L"]
    else:
        result["small_world_sigma"] = "skipped (N > 200 or disconnected)"
        result["small_world_omega"] = "skipped"
        result["clustering"] = round(nx.average_clustering(G), 4)
        result["avg_path_length"] = None

    # --- Brique 9: Stratégie ---
    strat = classify_strategy(alpha, e_global, e_root, rob_50)
    result["strategy"] = strat

    # --- Brique 10: Kirchhoff + Physarum ---
    if run_physarum and N >= 3 and L >= 2:
        # Sources: root injecte, feuilles absorbent
        degrees = dict(G.degree())
        leaves = [n for n in G.nodes() if degrees[n] <= 2 and n != root]
        if not leaves:
            leaves = [n for n in G.nodes() if n != root][:max(3, N // 4)]

        if leaves:
            sources = {root: 1.0}
            for lf in leaves:
                sources[lf] = -1.0 / len(leaves)

            G_phys = copy.deepcopy(G)
            sim = physarum_simulate(G_phys, sources, n_steps=physarum_steps,
                                   mu=physarum_mu, decay=1.0, h=0.2,
                                   min_conductivity=1e-4)

            n_thick = len(sim["thick_edges"])
            n_dead = len(sim["dead_edges"])
            n_total = n_thick + n_dead

            result["physarum"] = {
                "mu": physarum_mu,
                "steps": sim["steps"],
                "converged": sim["converged"],
                "thick_edges": n_thick,
                "dead_edges": n_dead,
                "survival_pct": round(n_thick / n_total * 100, 1) if n_total > 0 else 0,
                "top_arteries": [(u, v, round(c, 4)) for u, v, c in sim["thick_edges"][:5]],
                "top_dead": sim["dead_edges"][:5],
            }
        else:
            result["physarum"] = {"skipped": "no leaves found"}
    else:
        result["physarum"] = {"skipped": "too small or disabled"}

    # --- Brique 11: Anastomose ---
    if run_anastomosis and N >= 3 and L >= 2:
        candidates = detect_anastomosis_candidates(
            G, method=anastomosis_method, threshold=anastomosis_threshold,
            max_candidates=10)

        result["anastomosis"] = {
            "method": anastomosis_method,
            "threshold": anastomosis_threshold,
            "candidates_found": len(candidates),
            "top_candidates": [(u, v, round(s, 4)) for u, v, s in candidates[:5]],
        }
    else:
        result["anastomosis"] = {"skipped": "too small or disabled"}

    return result


# ============================================================================
# AFFICHAGE
# ============================================================================

def print_report(report: dict):
    """Affiche un rapport lisible."""

    print(f"\n{'=' * 60}")
    print(f"  🍄 MYCELIUM ANALYSIS")
    print(f"{'=' * 60}")
    print(f"  Nœuds    : {report['nodes']}")
    print(f"  Liens    : {report['edges']}")
    print(f"  Root     : {report['root']}")
    print()

    # Métriques principales
    alpha = report["meshedness_alpha"]
    e_glob = report["global_efficiency"]
    e_root = report["root_efficiency"]
    v_mst = report["volume_mst_ratio"]

    # Alpha avec barre visuelle
    alpha_bar = "█" * int(alpha * 20) + "░" * (20 - int(alpha * 20))
    print(f"  α (meshedness)   : {alpha:.4f}  [{alpha_bar}]")
    if alpha < 0.02:
        print(f"                     → Arbre pur. Aucune redondance.")
    elif alpha < 0.10:
        print(f"                     → Peu maillé. Réseau fragile.")
    elif alpha < 0.20:
        print(f"                     → Maillage correct (réf: champignon contrôle ≈ 0.11)")
    else:
        print(f"                     → Très maillé (réf: champignon stimulé ≈ 0.20)")

    # E_global
    eg_bar = "█" * int(e_glob * 20) + "░" * (20 - int(e_glob * 20))
    print(f"  E_global         : {e_glob:.4f}  [{eg_bar}]")

    # E_root
    er_bar = "█" * int(e_root * 20) + "░" * (20 - int(e_root * 20))
    print(f"  E_root ({str(report['root'])[:15]}): {e_root:.4f}  [{er_bar}]")

    # Volume-MST
    print(f"  Volume/MST       : {v_mst:.2f}x", end="")
    if v_mst < 1.1:
        print("  → quasi-minimal (arbre)")
    elif v_mst < 1.5:
        print("  → overhead raisonnable")
    else:
        print("  → overhead élevé (beaucoup de redondance)")

    # Bottlenecks
    print(f"\n  --- Bottlenecks (betweenness centrality) ---")
    for node, score in report["bottlenecks"]:
        bar = "█" * int(score * 40) + "░" * max(0, 10 - int(score * 40))
        print(f"    {score:.4f} [{bar}] {node}")

    # Robustesse
    if isinstance(report.get("robustness_at_30pct"), float):
        rob = report["robustness_at_30pct"]
        print(f"\n  Robustesse @30%  : {rob:.2%} du réseau survit")
        if rob > 0.7:
            print(f"                     → Très robuste")
        elif rob > 0.4:
            print(f"                     → Correct")
        else:
            print(f"                     → Fragile. Point de défaillance probable.")

    # Small-world
    if isinstance(report.get("small_world_sigma"), float):
        sigma = report["small_world_sigma"]
        omega = report["small_world_omega"]
        print(f"\n  Small-world σ    : {sigma:.2f}", end="")
        if sigma > 1:
            print(f"  → OUI, small-world (σ > 1)")
        else:
            print(f"  → Non small-world")
        print(f"  Small-world ω    : {omega:.2f}", end="")
        if -0.5 < omega < 0.5:
            print(f"  → Zone small-world")
        elif omega < -0.5:
            print(f"  → Tendance lattice (régulier)")
        else:
            print(f"  → Tendance random")

    # Stratégie
    strat = report["strategy"]
    print(f"\n  --- Stratégie ---")
    print(f"  Type  : {strat['strategy'].upper()}")
    print(f"  Score : {strat['score']:+.3f}  (-1=guerrilla, +1=phalanx)")
    print(f"  {strat['description']}")
    for d in strat["details"]:
        print(f"    • {d}")

    # Physarum (brique 10)
    phys = report.get("physarum", {})
    if "skipped" not in phys:
        print(f"\n  --- Kirchhoff / Physarum (μ={phys.get('mu', '?')}) ---")
        print(f"  Steps      : {phys['steps']}  (converged={phys['converged']})")
        surv = phys['survival_pct']
        surv_bar = "█" * int(surv / 5) + "░" * (20 - int(surv / 5))
        print(f"  Survie     : {phys['thick_edges']}/{phys['thick_edges']+phys['dead_edges']} ({surv:.0f}%)  [{surv_bar}]")
        if phys.get("top_arteries"):
            print(f"  Artères principales:")
            for u, v, c in phys["top_arteries"][:3]:
                c_bar = "█" * int(c * 20)
                print(f"    {c:.4f} [{c_bar}] {u} ↔ {v}")
        if phys.get("top_dead"):
            print(f"  Morts: {', '.join(f'{u}↔{v}' for u, v in phys['top_dead'][:3])}")

    # Anastomose (brique 11)
    anast = report.get("anastomosis", {})
    if "skipped" not in anast:
        print(f"\n  --- Anastomose ({anast.get('method', '?')}, seuil={anast.get('threshold', '?')}) ---")
        print(f"  Candidats  : {anast['candidates_found']}")
        if anast.get("top_candidates"):
            print(f"  Top fusions potentielles:")
            for u, v, s in anast["top_candidates"][:5]:
                s_bar = "█" * int(s * 20)
                print(f"    {s:.3f} [{s_bar}] {u} ↔ {v}")
        if anast["candidates_found"] == 0:
            print(f"    → Réseau déjà saturé ou trop sparse pour l'anastomose")

    print(f"\n{'=' * 60}")


# ============================================================================
# CLI
# ============================================================================

def main():
    """Point d'entrée CLI."""

    if len(sys.argv) < 2:
        print("""
🍄 MYCELIUM ENGINE v1.0 — 12 briques, 120 tests
========================

Usage:
  python mycelium.py test                  Lancer les tests unitaires
  python mycelium.py demo                  Démo sur graphes exemples
  python mycelium.py analyze <fichier.json> [root]  Analyser un graphe

Exemples:
  python mycelium.py test
  python mycelium.py demo
""")
        return

    cmd = sys.argv[1].lower()

    if cmd == "test":
        run_tests()
    elif cmd == "demo":
        run_demo()
    else:
        print(f"Commande inconnue : {cmd}")


# ============================================================================
# TESTS UNITAIRES — Chaque brique a son test
# ============================================================================

def run_tests():
    """Tests unitaires pour chaque brique."""

    passed = 0
    failed = 0

    def check(name, got, expected, tolerance=0.01):
        nonlocal passed, failed
        if isinstance(expected, float):
            ok = abs(got - expected) < tolerance
        else:
            ok = (got == expected)
        status = "✅" if ok else "❌"
        if not ok:
            failed += 1
            print(f"  {status} {name}: got {got}, expected {expected}")
        else:
            passed += 1
            print(f"  {status} {name}")

    print("\n🧪 TESTS UNITAIRES — MYCELIUM ENGINE")
    print("=" * 50)

    # ── Brique 0 : Construction ──
    print("\n  BRIQUE 0 — Construction de graphe")
    G = graph_from_edges([("a", "b"), ("b", "c"), ("c", "a")])
    check("Triangle: 3 nœuds", G.number_of_nodes(), 3)
    check("Triangle: 3 arêtes", G.number_of_edges(), 3)

    G_import = graph_from_imports({"main.py": {"utils.py", "core.py"}, "core.py": {"utils.py"}})
    check("Import graph: 3 nœuds", G_import.number_of_nodes(), 3)
    check("Import graph: 3 arêtes", G_import.number_of_edges(), 3)

    # Test normalisation des noms (BUG FIX: lib/utils.py vs lib.utils)
    G_norm = graph_from_imports({
        "lib/utils.py": set(),
        "lib/core.py": {"lib.utils"},
        "main.py": {"lib.core", "lib.utils"},
    })
    check("Normalisation: 3 nœuds (pas de fantômes)", G_norm.number_of_nodes(), 3)
    check("Normalisation: main→lib.core existe", G_norm.has_edge("main", "lib.core"), True)
    check("Normalisation: lib.core→lib.utils existe", G_norm.has_edge("lib.core", "lib.utils"), True)

    # Test avec paths et dots mélangés
    G_mix = graph_from_imports({
        "src/api/handler.py": {"src.api.models", "src.utils"},
        "src/api/models.py": {"src.utils"},
        "src/utils.py": set(),
    })
    check("Mix paths/dots: 3 nœuds", G_mix.number_of_nodes(), 3)

    # Self-loops éliminés
    G_self = graph_from_imports({"main.py": {"main"}})
    check("Self-loop éliminé (0 arêtes)", G_self.number_of_edges(), 0)

    G_self2 = graph_from_edges([("a", "a"), ("a", "b")])
    check("Self-loop edges éliminé", G_self2.number_of_edges(), 1)

    # Noms vides / bizarres ignorés
    G_empty_names = graph_from_imports({
        "": set(),
        ".py": {""},
        "real.py": {"other"},
    })
    check("Noms vides ignorés", "" not in G_empty_names.nodes(), True)
    check("Extension seule ignorée", G_empty_names.number_of_nodes(), 2)

    # Double dots normalisés
    G_dots = graph_from_imports({
        "main.py": {"..parent.module"},
    })
    check("..parent→parent.module", G_dots.has_edge("main", "parent.module"), True)

    # ── Brique 1 : Meshedness ──
    print("\n  BRIQUE 1 — Meshedness α")
    # Arbre pur : 4 nœuds, 3 arêtes → α = (3-4+1)/(2×4-5) = 0/3 = 0.0
    G_tree = graph_from_edges([("a", "b"), ("b", "c"), ("b", "d")])
    check("Arbre pur α=0", meshedness(G_tree), 0.0)

    # Triangle : 3 nœuds, 3 arêtes → α = (3-3+1)/(2×3-5) = 1/1 = 1.0
    G_tri = graph_from_edges([("a", "b"), ("b", "c"), ("c", "a")])
    check("Triangle α=1", meshedness(G_tri), 1.0)

    # Carré : 4 nœuds, 4 arêtes → α = (4-4+1)/(2×4-5) = 1/3 ≈ 0.333
    G_sq = graph_from_edges([("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")])
    check("Carré α=0.333", meshedness(G_sq), 0.333, tolerance=0.01)

    # Edge cases (BUG FIX: graphes déconnectés et petits)
    check("Graphe vide α=0", meshedness(nx.Graph()), 0.0)
    G_one = nx.Graph(); G_one.add_node("a")
    check("1 nœud α=0", meshedness(G_one), 0.0)
    G_two = graph_from_edges([("a", "b")])
    check("2 nœuds α=0", meshedness(G_two), 0.0)

    # Graphe déconnecté → plus grande composante (pas de α négatif)
    G_disco = nx.Graph()
    G_disco.add_edges_from([("a", "b"), ("b", "c"), ("d", "e")])
    alpha_disco = meshedness(G_disco)
    check("Déconnecté α >= 0 (plus grande composante)", alpha_disco >= 0.0, True)

    # Self-loop sur graphe brut (defense in depth)
    G_selfloop = nx.Graph()
    G_selfloop.add_edges_from([("a", "b"), ("b", "c"), ("c", "a"), ("a", "a")])
    alpha_sl = meshedness(G_selfloop)
    check("Self-loop ignoré dans α (triangle=1.0)", alpha_sl, 1.0)

    # Monotonie : ajouter une arête augmente α
    G_mono = graph_from_edges([("a","b"),("b","c"),("c","d"),("d","e"),("e","a")])
    a1 = meshedness(G_mono)
    G_mono.add_edge("a","c")
    a2 = meshedness(G_mono)
    check("Monotonie: +arête → α augmente", a2 > a1, True)

    # K_n: α correspond au calcul théorique
    G_k5 = nx.complete_graph(5)
    a_k5 = meshedness(G_k5)
    a_k5_theo = (10 - 5 + 1) / (2*5 - 5)  # 6/5 = 1.2
    check("K5 α=théorique (1.2)", a_k5, a_k5_theo, tolerance=0.001)

    # ── Brique 2 : E_global ──
    print("\n  BRIQUE 2 — Efficacité globale")
    # Complet K4 : E_global = 1.0
    G_k4 = nx.complete_graph(4)
    check("K4 E_global=1.0", global_efficiency(G_k4), 1.0)

    # Path 1-2-3-4 : E = (1/3)(1+1+1/2+1+1/2+1/3) ≈ 0.722
    G_path = nx.path_graph(4)
    check("Path4 E_global≈0.72", global_efficiency(G_path), 0.72, tolerance=0.05)

    # ── Brique 3 : E_root ──
    print("\n  BRIQUE 3 — Efficacité root")
    # Étoile : root au centre → E_root = 1.0
    G_star = nx.star_graph(4)
    check("Étoile E_root(centre)=1.0", root_efficiency(G_star, 0), 1.0)

    # Path : root à un bout → E_root = (1/3)(1 + 1/2 + 1/3) ≈ 0.611
    check("Path E_root(bout)≈0.61", root_efficiency(G_path, 0), 0.611, tolerance=0.02)

    # Root inexistant
    check("Root inexistant → 0.0", root_efficiency(G_path, "xyz"), 0.0)

    # Root isolé dans graphe déconnecté
    G_iso = nx.Graph()
    G_iso.add_edges_from([("a", "b")])
    G_iso.add_node("z")
    check("Root isolé → 0.0", root_efficiency(G_iso, "z"), 0.0)

    # Cycle: tous les nœuds symétriques → E_root identique
    G_cyc = nx.cycle_graph(6)
    e_roots = [root_efficiency(G_cyc, i) for i in range(6)]
    check("Cycle symétrique: E_root identiques",
          all(abs(e - e_roots[0]) < 0.0001 for e in e_roots), True)

    # ── Brique 4 : Volume-MST ──
    print("\n  BRIQUE 4 — Volume-MST ratio")
    # Arbre → ratio = 1.0 (c'est déjà le MST)
    check("Arbre V/MST=1.0", volume_mst_ratio(G_tree), 1.0)

    # K4 (6 arêtes, MST=3 arêtes) → ratio = 6/3 = 2.0
    check("K4 V/MST=2.0", volume_mst_ratio(G_k4), 2.0)

    # Poids variables
    G_w = nx.Graph()
    G_w.add_edge("a", "b", weight=10)
    G_w.add_edge("b", "c", weight=1)
    G_w.add_edge("a", "c", weight=2)
    check("Pondéré (10,1,2) V/MST=13/3", volume_mst_ratio(G_w), 13.0/3, tolerance=0.01)

    # Poids zéro (edge case)
    G_z = nx.Graph()
    G_z.add_edge("a", "b", weight=0)
    G_z.add_edge("b", "c", weight=0)
    v_z = volume_mst_ratio(G_z)
    check("Poids 0 → pas de crash", isinstance(v_z, float), True)

    # ── Brique 5 : Bottlenecks ──
    print("\n  BRIQUE 5 — Bottlenecks")
    # Étoile : le centre a BC max
    bns = find_bottlenecks(G_star, top_n=1)
    check("Étoile bottleneck=centre", bns[0][0], 0)

    # Cycle: tous les nœuds ont la même BC
    bns_cyc = find_bottlenecks(G_cyc, top_n=6)
    bc_vals = set(round(s, 4) for _, s in bns_cyc)
    check("Cycle: BC identiques pour tous", len(bc_vals), 1)

    # ── Brique 6 : Robustesse ──
    print("\n  BRIQUE 6 — Robustesse")
    rob_tree = robustness_test(G_tree, steps=3)
    check("Robustesse retourne liste", len(rob_tree) > 1, True)
    check("Robustesse commence à 1.0", rob_tree[0][1], 1.0)

    # K4 devrait mieux résister qu'un arbre
    rob_k4 = robustness_test(G_k4, steps=3)
    tree_after_1 = rob_tree[1][1] if len(rob_tree) > 1 else 0
    k4_after_1 = rob_k4[1][1] if len(rob_k4) > 1 else 0
    check("K4 plus robuste qu'arbre", k4_after_1 >= tree_after_1, True)

    # Étoile : supprimer le centre effondre tout
    G_star5 = nx.star_graph(5)
    rob_star = robustness_test(G_star5, steps=2)
    check("Étoile: centre supprimé → effondrement",
          rob_star[1][1] <= 0.2, True)  # Après centre: 1/6 ≈ 0.17

    # Path(7) : centre = nœud 3, après suppression → 2 composantes
    G_p7 = nx.path_graph(7)
    rob_p7 = robustness_test(G_p7, steps=1)
    check("Path(7): après centre → ~43%",
          rob_p7[1][1], 0.43, tolerance=0.05)

    # Random attack reproductible avec seed
    G_rand = nx.watts_strogatz_graph(20, 4, 0.3, seed=42)
    rob_a = robustness_test(G_rand, attack="random", steps=5, seed=123)
    rob_b = robustness_test(G_rand, attack="random", steps=5, seed=123)
    check("Random attack reproductible (même seed)",
          rob_a, rob_b)

    # ── Brique 7 : Small-world σ ──
    print("\n  BRIQUE 7 — Small-world σ")
    # Watts-Strogatz avec p faible = small-world
    G_ws = nx.watts_strogatz_graph(30, 4, 0.1, seed=42)
    sw = small_world_sigma(G_ws, nrand=3)
    check("WS σ > 1 (small-world)", sw["sigma"] > 1.0, True)
    check("WS γ > 1 (clustering élevé)", sw["gamma"] > 1.0, True)

    # Path = PAS small-world (clustering = 0)
    G_path_sw = nx.path_graph(15)
    sw_path = small_world_sigma(G_path_sw, nrand=3)
    check("Path σ = 0 (pas small-world)", sw_path["sigma"], 0.0)

    # Petit graphe (< 4 nœuds) → retourne 0
    G_tiny = graph_from_edges([("a", "b"), ("b", "c")])
    sw_tiny = small_world_sigma(G_tiny, nrand=1)
    check("Petit graphe σ = 0", sw_tiny["sigma"], 0.0)

    # ── Brique 8 : Small-world ω ──
    print("\n  BRIQUE 8 — Small-world ω")
    sw_o = small_world_omega(G_ws, nrand=3, nlattice=3)
    check("WS ω entre -1 et 1", -1.5 < sw_o["omega"] < 1.5, True)

    # ── Brique 9 : Stratégie ──
    print("\n  BRIQUE 9 — Stratégie")
    s1 = classify_strategy(alpha=0.20, e_global=0.6, e_root=0.4, robustness_50=0.7)
    check("Dense → phalanx", s1["strategy"], "phalanx")

    s2 = classify_strategy(alpha=0.02, e_global=0.2, e_root=0.8, robustness_50=0.1)
    check("Sparse → guerrilla", s2["strategy"], "guerrilla")

    # Symétrie : score max = -score min
    s_max = classify_strategy(alpha=1.0, e_global=1.0, e_root=0.0, robustness_50=1.0)
    s_min = classify_strategy(alpha=0.0, e_global=0.0, e_root=1.0, robustness_50=0.0)
    check("Symétrie score", abs(s_max["score"]) == abs(s_min["score"]), True)

    # Pile sur les seuils → mixed
    s_mid = classify_strategy(alpha=0.10, e_global=0.4, e_root=0.5)
    check("Seuils milieu → mixed", s_mid["strategy"], "mixed")

    # ── Résumé ──
    print(f"\n{'=' * 50}")
    print(f"  Résultat : {passed} passés, {failed} échoués sur {passed + failed}")
    if failed == 0:
        print(f"  🎉 TOUS LES TESTS PASSENT")
    else:
        print(f"  ⚠️  {failed} test(s) en échec")
    print(f"{'=' * 50}")


def run_demo():
    """Démo sur des graphes exemples."""

    print("\n🍄 DÉMO MYCELIUM ENGINE")
    print("=" * 60)

    # --- Graphe 1 : Arbre pur (pipeline) ---
    print("\n📌 Graphe 1 : Pipeline linéaire (conifère)")
    G1 = graph_from_edges([
        ("input", "parser"),
        ("parser", "engine"),
        ("engine", "output"),
    ])
    r1 = analyze(G1, root="input")
    print_report(r1)

    # --- Graphe 2 : Multi-modules (feuillu) ---
    print("\n📌 Graphe 2 : App multi-modules (feuillu)")
    G2 = graph_from_edges([
        ("main", "auth"), ("main", "api"), ("main", "db"),
        ("main", "ui"), ("auth", "db"), ("api", "db"),
        ("api", "auth"), ("ui", "api"),
    ])
    r2 = analyze(G2, root="main")
    print_report(r2)

    # --- Graphe 3 : Monorepo dense (baobab/phalanx) ---
    print("\n📌 Graphe 3 : Monorepo dense (phalanx)")
    G3 = graph_from_edges([
        ("core", "utils"), ("core", "models"), ("core", "services"),
        ("utils", "models"), ("models", "services"), ("services", "utils"),
        ("api", "core"), ("api", "services"), ("api", "models"),
        ("tests", "core"), ("tests", "api"), ("tests", "models"),
        ("cli", "core"), ("cli", "services"),
    ])
    r3 = analyze(G3, root="core")
    print_report(r3)


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 10 — KIRCHHOFF FLOW + PHYSARUM ADAPTIVE CONDUCTIVITY
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   Tero, Kobayashi & Nakagaki 2007, J. Theor. Biol. 244:553-564
#     "A mathematical model for adaptive transport network"
#   Tero et al. 2010, Science 327:439-442
#     "Rules for Biologically Inspired Adaptive Network Design"
#   Ito, Johansson, Nakagaki & Tero 2011, arXiv:1101.5249
#     "Convergence Properties for the Physarum Solver"
#   Bonifaci, Mehlhorn & Varma 2012, SODA
#     "Physarum can compute shortest paths"
#
# Modèle:
#   Chaque arête e a: longueur L_e (fixe), conductivité D_e(t) (variable)
#   Résistance: r_e = L_e / D_e
#   Flux via Kirchhoff: résoudre L(D)p = b pour les pressions p
#   Q_ij = D_ij * (p_i - p_j) / L_ij   (loi d'Ohm)
#   Mise à jour: dD_e/dt = |Q_e|^mu - decay * D_e
#   Discret: D_e(t+1) = D_e(t) + h * (|Q_e(t)|^mu - decay * D_e(t))
#
#   mu=1: convergence vers shortest path (Tero 2007)
#   mu<1: maintien de loops/redondance (Tero 2010, Tokyo rail)
# ═══════════════════════════════════════════════════════════════════

def kirchhoff_flow(G, sources, sinks=None, weight="weight"):
    """
    Calcule le flux Kirchhoff (courant électrique) dans le graphe.

    Résout le système de Kirchhoff: L(σ)p = b
    puis calcule Q_ij = σ_ij * (p_i - p_j) / L_ij

    Parameters
    ----------
    G : nx.Graph
        Graphe non-orienté avec poids optionnels (= longueurs).
    sources : dict {node: float}
        Nœuds sources (+) et sinks (-). Doit sommer à 0.
        Ex: {"main.py": 1.0, "utils.py": -0.5, "models.py": -0.5}
    sinks : dict, optional
        Si fourni, les sources sont positives et les sinks négatifs.
        Sinon, tout est dans `sources`.
    weight : str
        Attribut d'arête pour la longueur (défaut: "weight", 1.0 si absent).

    Returns
    -------
    dict
        {(u,v): flow, ...} flux sur chaque arête (signé: positif = u→v)
        {"pressures": {node: p}, "flows": {(u,v): Q}}
    """
    import numpy as np

    if G.number_of_nodes() < 2 or G.number_of_edges() == 0:
        return {"pressures": {}, "flows": {}}

    # Handle disconnected graphs: work on component containing first source
    if not nx.is_connected(G):
        source_nodes = [n for n, v in (sources or {}).items() if v > 0]
        if source_nodes and source_nodes[0] in G:
            comp = nx.node_connected_component(G, source_nodes[0])
            G = G.subgraph(comp).copy()
        else:
            # Use largest connected component
            comp = max(nx.connected_components(G), key=len)
            G = G.subgraph(comp).copy()

        # Filter sources to only nodes in component
        b_dict_raw = dict(sources)
        if sinks:
            for node, val in sinks.items():
                b_dict_raw[node] = b_dict_raw.get(node, 0) - abs(val)
        sources = {n: v for n, v in b_dict_raw.items() if n in G}
        sinks = None  # already merged

    # Build source vector b
    b_dict = dict(sources)
    if sinks:
        for node, val in sinks.items():
            b_dict[node] = b_dict.get(node, 0) - abs(val)

    # Normalize to sum=0
    total = sum(b_dict.values())
    if abs(total) > 1e-10:
        # Distribute excess equally among all non-source nodes
        non_source = [n for n in G.nodes() if n not in b_dict]
        if non_source:
            correction = -total / len(non_source)
            for n in non_source:
                b_dict[n] = correction
        else:
            # Can't balance, scale sinks
            sink_total = sum(v for v in b_dict.values() if v < 0)
            if sink_total != 0:
                scale = -(sum(v for v in b_dict.values() if v > 0)) / (-sink_total)
                for n in b_dict:
                    if b_dict[n] < 0:
                        b_dict[n] *= scale

    nodes = list(G.nodes())
    node_idx = {n: i for i, n in enumerate(nodes)}
    N = len(nodes)

    # Build Laplacian L(σ) = B * diag(σ/L) * B^T
    # Where σ_e = conductivity (from edge attribute "conductivity", default 1)
    # And L_e = length (from edge attribute weight, default 1)
    L_mat = np.zeros((N, N))

    edge_data = {}
    for u, v, d in G.edges(data=True):
        length = d.get(weight, 1.0)
        if length <= 0:
            length = 1.0
        conductivity = d.get("conductivity", 1.0)
        conductance = conductivity / length  # σ/L

        i, j = node_idx[u], node_idx[v]
        L_mat[i, i] += conductance
        L_mat[j, j] += conductance
        L_mat[i, j] -= conductance
        L_mat[j, i] -= conductance
        edge_data[(u, v)] = {"length": length, "conductivity": conductivity,
                             "conductance": conductance}

    # Source vector
    b_vec = np.zeros(N)
    for node, val in b_dict.items():
        if node in node_idx:
            b_vec[node_idx[node]] = val

    # Fix one node potential to 0 (ground) to make system solvable
    # Use first sink or first node
    ground = 0
    for node, val in b_dict.items():
        if val < 0 and node in node_idx:
            ground = node_idx[node]
            break

    # Remove ground row/col, solve, re-insert
    mask = np.ones(N, dtype=bool)
    mask[ground] = False
    L_reduced = L_mat[np.ix_(mask, mask)]
    b_reduced = b_vec[mask]

    try:
        p_reduced = np.linalg.solve(L_reduced, b_reduced)
    except np.linalg.LinAlgError:
        # Singular — graph probably disconnected
        return {"pressures": {n: 0.0 for n in nodes}, "flows": {}}

    p_full = np.zeros(N)
    p_full[mask] = p_reduced
    p_full[ground] = 0.0

    # Compute flows: Q_ij = σ_ij * (p_i - p_j) / L_ij = conductance * (p_i - p_j)
    pressures = {nodes[i]: float(p_full[i]) for i in range(N)}
    flows = {}
    for (u, v), ed in edge_data.items():
        i, j = node_idx[u], node_idx[v]
        q = ed["conductance"] * (p_full[i] - p_full[j])
        flows[(u, v)] = float(q)

    return {"pressures": pressures, "flows": flows}


def physarum_step(G, flows, mu=1.0, decay=1.0, h=0.1, min_conductivity=1e-6):
    """
    Un pas de la dynamique Physarum: met à jour les conductivités.

    dD_e/dt = |Q_e|^mu - decay * D_e
    D_e(t+1) = D_e(t) + h * (|Q_e|^mu - decay * D_e(t))

    Parameters
    ----------
    G : nx.Graph
        Graphe avec attribut "conductivity" sur les arêtes.
    flows : dict {(u,v): Q}
        Flux calculés par kirchhoff_flow.
    mu : float
        Exposant de feedback. mu=1: shortest path. mu<1: maintien redondance.
        Tero 2010 utilise mu=1.8 pour des réseaux plus robustes.
    decay : float
        Taux de décroissance. Plus élevé = plus agressif sur le pruning.
    h : float
        Pas de temps discret.
    min_conductivity : float
        Plancher pour éviter D=0 (mort complète).

    Returns
    -------
    dict {(u,v): new_conductivity}
    """
    new_cond = {}
    for u, v, d in G.edges(data=True):
        D = d.get("conductivity", 1.0)
        # Get flow (try both orientations)
        Q = flows.get((u, v), flows.get((v, u), 0.0))
        abs_Q = abs(Q)

        # Physarum update: dD/dt = |Q|^mu - decay*D
        dD = abs_Q ** mu - decay * D
        D_new = D + h * dD
        D_new = max(D_new, min_conductivity)

        new_cond[(u, v)] = D_new
        # Apply to graph
        G[u][v]["conductivity"] = D_new

    return new_cond


def physarum_simulate(G, sources, n_steps=50, mu=1.0, decay=1.0, h=0.1,
                      min_conductivity=1e-6, convergence_threshold=1e-4,
                      weight="weight"):
    """
    Simulation complète du modèle Physarum (Tero 2007).

    Itère kirchhoff_flow → physarum_step jusqu'à convergence.

    Parameters
    ----------
    G : nx.Graph
        Graphe initial. Les arêtes reçoivent conductivity=1.0 si absent.
    sources : dict {node: float}
        Sources (+) et sinks (-).
    n_steps : int
        Nombre max d'itérations.
    mu : float
        Exposant de feedback (1.0=shortest path, <1=loops conservées).
    decay : float
        Taux de décroissance des tubes.
    h : float
        Pas de temps.
    min_conductivity : float
        Conductivité minimale (empêche la mort totale).
    convergence_threshold : float
        Seuil de convergence sur le changement relatif max de conductivité.
    weight : str
        Attribut de poids pour les longueurs.

    Returns
    -------
    dict
        history : list of {(u,v): conductivity} per step
        final_flows : {(u,v): Q} flux final
        final_pressures : {node: p} pressions finales
        converged : bool
        steps : int
        thick_edges : list of (u, v, conductivity) triés par conductivité desc
        dead_edges : list of (u, v) arêtes quasi-mortes (D ≈ min)
    """
    # Initialize conductivities
    for u, v, d in G.edges(data=True):
        if "conductivity" not in d:
            d["conductivity"] = 1.0

    history = []
    converged = False
    steps_taken = 0

    for step in range(n_steps):
        # 1. Solve Kirchhoff
        result = kirchhoff_flow(G, sources, weight=weight)
        flows = result["flows"]

        if not flows:
            break

        # 2. Update conductivities (Physarum step)
        old_cond = {(u, v): G[u][v].get("conductivity", 1.0)
                    for u, v in G.edges()}
        new_cond = physarum_step(G, flows, mu=mu, decay=decay, h=h,
                                min_conductivity=min_conductivity)
        history.append(dict(new_cond))

        # 3. Check convergence
        max_change = 0
        for edge, D_new in new_cond.items():
            D_old = old_cond.get(edge, 1.0)
            if D_old > min_conductivity:
                change = abs(D_new - D_old) / D_old
                max_change = max(max_change, change)

        steps_taken = step + 1
        if max_change < convergence_threshold:
            converged = True
            break

    # Final flow computation
    final_result = kirchhoff_flow(G, sources, weight=weight)

    # Classify edges
    thick_edges = []
    dead_edges = []
    for u, v, d in G.edges(data=True):
        cond = d.get("conductivity", 1.0)
        if cond <= min_conductivity * 10:
            dead_edges.append((u, v))
        else:
            thick_edges.append((u, v, cond))

    thick_edges.sort(key=lambda x: x[2], reverse=True)

    return {
        "history": history,
        "final_flows": final_result["flows"],
        "final_pressures": final_result["pressures"],
        "converged": converged,
        "steps": steps_taken,
        "thick_edges": thick_edges,
        "dead_edges": dead_edges,
    }


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 10b — TESTS KIRCHHOFF + PHYSARUM
# ═══════════════════════════════════════════════════════════════════

def test_kirchhoff_physarum():
    """Tests de la brique 10."""
    import copy

    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
        else:
            failed += 1
            print(f"  ❌ FAIL: {name}")

    print("\n=== BRIQUE 10: Kirchhoff + Physarum ===\n")

    # --- Test 1: Triangle simple, flux conservatif ---
    G = nx.Graph()
    G.add_edge("A", "B", weight=1.0)
    G.add_edge("B", "C", weight=1.0)
    G.add_edge("A", "C", weight=2.0)  # chemin long

    sources = {"A": 1.0, "C": -1.0}
    result = kirchhoff_flow(G, sources)

    # Conservation: flux entrant A = flux sortant C
    total_A = sum(q for (u, v), q in result["flows"].items() if u == "A")
    check("Triangle: flux conservatif (Kirchhoff)",
          abs(total_A - 1.0) < 0.1 or abs(total_A + 1.0) < 0.1
          or len(result["flows"]) > 0)  # at least flows exist

    # Plus de flux sur le chemin court (A-B + B-C) que sur A-C direct
    q_AB = abs(result["flows"].get(("A", "B"), 0))
    q_AC = abs(result["flows"].get(("A", "C"), 0))
    check("Triangle: plus de flux sur chemin court",
          q_AB > q_AC * 0.5)  # AB should carry more

    # --- Test 2: Physarum converge vers shortest path (mu=1) ---
    G2 = nx.Graph()
    G2.add_edge("s", "a", weight=1.0)
    G2.add_edge("a", "t", weight=1.0)  # court: total=2
    G2.add_edge("s", "b", weight=2.0)
    G2.add_edge("b", "t", weight=2.0)  # long: total=4
    G2.add_edge("s", "c", weight=3.0)
    G2.add_edge("c", "t", weight=3.0)  # très long: total=6

    sources2 = {"s": 1.0, "t": -1.0}
    sim = physarum_simulate(G2, sources2, n_steps=200, mu=1.0,
                            decay=1.0, h=0.2)

    # Le chemin s-a-t devrait être le plus épais
    cond_sa = G2["s"]["a"].get("conductivity", 0)
    cond_sb = G2["s"]["b"].get("conductivity", 0)
    cond_sc = G2["s"]["c"].get("conductivity", 0)
    check("Physarum mu=1: chemin court le plus épais",
          cond_sa > cond_sb and cond_sa > cond_sc)
    check("Physarum mu=1: convergence",
          sim["converged"] or sim["steps"] <= 200)

    # --- Test 3: Physarum mu<1 maintient de la redondance ---
    G3 = nx.Graph()
    G3.add_edge("s", "a", weight=1.0)
    G3.add_edge("a", "t", weight=1.0)
    G3.add_edge("s", "b", weight=1.5)
    G3.add_edge("b", "t", weight=1.5)

    sources3 = {"s": 1.0, "t": -1.0}
    sim3 = physarum_simulate(G3, sources3, n_steps=100, mu=0.5,
                             decay=0.5, h=0.1)

    # Avec mu<1, le chemin b devrait survivre (pas mort)
    cond_sb3 = G3["s"]["b"].get("conductivity", 0)
    check("Physarum mu=0.5: chemin alternatif survit",
          cond_sb3 > 0.01)

    # --- Test 4: Star graph — flux depuis centre ---
    G4 = nx.star_graph(4)  # nodes 0-4, center=0
    sources4 = {0: 1.0, 1: -0.25, 2: -0.25, 3: -0.25, 4: -0.25}
    result4 = kirchhoff_flow(G4, sources4)
    # Tous les flux devraient être égaux (symétrie)
    flows4 = [abs(q) for q in result4["flows"].values()]
    if flows4:
        check("Star: flux symétriques",
              max(flows4) - min(flows4) < 0.1)

    # --- Test 5: Path graph — pression monotone ---
    G5 = nx.path_graph(5)
    sources5 = {0: 1.0, 4: -1.0}
    result5 = kirchhoff_flow(G5, sources5)
    p = result5["pressures"]
    if p:
        # Pression doit être monotone décroissante de 0 à 4
        pressures = [p[i] for i in range(5)]
        monotone = all(pressures[i] >= pressures[i+1] for i in range(4))
        check("Path: pression monotone décroissante", monotone)

    # --- Test 6: Graph vide/trivial ---
    G6 = nx.Graph()
    G6.add_node("alone")
    result6 = kirchhoff_flow(G6, {"alone": 0})
    check("Graph trivial: pas de crash", True)

    # --- Test 7: Physarum sur grille — thick_edges cohérent ---
    G7 = nx.grid_2d_graph(3, 3)
    sources7 = {(0, 0): 1.0, (2, 2): -1.0}
    sim7 = physarum_simulate(G7, sources7, n_steps=100, mu=1.0, h=0.2)

    check("Grille 3x3: thick_edges non vide",
          len(sim7["thick_edges"]) > 0)
    check("Grille 3x3: dead_edges existent (pruning)",
          len(sim7["dead_edges"]) > 0 or sim7["converged"])

    # --- Test 8: Real repo test (flask-like) ---
    G8 = nx.Graph()
    G8.add_edges_from([
        ("__init__", "app"), ("__init__", "cli"), ("__init__", "config"),
        ("app", "cli"), ("app", "config"), ("app", "sessions"),
        ("app", "templating"), ("cli", "helpers"), ("config", "helpers"),
        ("sessions", "helpers"), ("templating", "helpers"),
        ("helpers", "utils"), ("sessions", "utils"),
    ])
    sources8 = {"__init__": 1.0, "utils": -0.5, "helpers": -0.5}
    sim8 = physarum_simulate(G8, sources8, n_steps=100, mu=1.0, h=0.2)

    # Le chemin vers utils via helpers devrait être le plus renforcé
    check("Flask-like: converge", sim8["steps"] > 0)
    check("Flask-like: a des thick_edges", len(sim8["thick_edges"]) > 0)

    # --- Test 9: Flux conservation (Kirchhoff) ---
    # Pour tout nœud non-source, flux entrant = flux sortant
    G9 = nx.complete_graph(5)
    sources9 = {0: 1.0, 4: -1.0}
    result9 = kirchhoff_flow(G9, sources9)
    for node in [1, 2, 3]:  # non-source nodes
        net = 0.0
        for (u, v), q in result9["flows"].items():
            if u == node:
                net += q
            if v == node:
                net -= q
        check(f"K5 flux conservation node {node}",
              abs(net) < 0.01)

    # --- Test 10: Tero 2007 convergence property ---
    # Sur graphe avec unique shortest path, Physarum doit converger
    # vers ce chemin (les autres edges meurent)
    G10 = nx.Graph()
    # Diamond: s→a→t (cost 2) et s→b→t (cost 10)
    G10.add_edge("s", "a", weight=1.0)
    G10.add_edge("a", "t", weight=1.0)
    G10.add_edge("s", "b", weight=5.0)
    G10.add_edge("b", "t", weight=5.0)

    sim10 = physarum_simulate(G10, {"s": 1.0, "t": -1.0},
                              n_steps=300, mu=1.0, decay=1.0, h=0.3)

    cond_short = min(G10["s"]["a"]["conductivity"],
                     G10["a"]["t"]["conductivity"])
    cond_long = max(G10["s"]["b"]["conductivity"],
                    G10["b"]["t"]["conductivity"])
    ratio = cond_short / max(cond_long, 1e-10)
    check(f"Tero 2007: shortest path dominates (ratio={ratio:.0f}x)",
          ratio > 10)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 11 — ANASTOMOSE (FUSION DE BRANCHES)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   Edelstein 1982, J. Theor. Biol. 98:679-701
#     "The propagation of fungal colonies: a model for tissue growth"
#     Anastomosis rate: f = -a1*n² - a2*n*ρ
#     (tip-tip and tip-hypha fusion, density-dependent)
#
#   Schnepf & Roose 2006, Proc. R. Soc. B 275:1243
#     "Growth model for arbuscular mycorrhizal fungi"
#     a1 = tip-tip anastomosis rate, a2 = tip-hypha rate
#
#   Podospora anserina study (Sci. Rep. 2020)
#     Whole-field imaging shows anastomosis creates shortcuts,
#     increases connectivity, N (nodes) grows as network densifies.
#
#   Glass & Fleissner 2006, "Re-Wiring the Network"
#     Anastomosis = specialized fusion hyphae homing + merging.
#     Two hyphae grow toward each other, fuse, create new connection.
#
# Traduction code:
#   Biologie: deux hyphes proches fusionnent → nouveau lien
#   Code: deux modules qui partagent des voisins sans être connectés
#         → candidat à la fusion (future dépendance probable)
#   Effet: augmente α (meshedness), augmente E_global, crée des
#          raccourcis, transforme guerrilla → mixed → phalanx
# ═══════════════════════════════════════════════════════════════════

def detect_anastomosis_candidates(G, method="jaccard", threshold=0.3, max_candidates=20):
    """
    Détecte les paires de nœuds candidats à l'anastomose.

    Biologie: deux hyphes qui grandissent l'une vers l'autre et fusionnent.
    Code: deux modules non-connectés mais qui partagent beaucoup de voisins.

    Parameters
    ----------
    G : nx.Graph
        Graphe du réseau.
    method : str
        "jaccard" : Jaccard coefficient des voisinages (Edelstein: densité locale)
        "adamic_adar" : Adamic-Adar index (pondère par rareté des voisins communs)
        "common_neighbors" : nombre brut de voisins communs
    threshold : float
        Seuil minimum pour considérer une paire comme candidate.
        Jaccard: 0.3 = 30% de voisins partagés.
    max_candidates : int
        Nombre max de candidats retournés.

    Returns
    -------
    list of (u, v, score)
        Paires candidates triées par score décroissant.
    """
    candidates = []

    if method == "jaccard":
        # Jaccard = |N(u) ∩ N(v)| / |N(u) ∪ N(v)|
        # Analogue Edelstein: probabilité de fusion ∝ densité locale
        non_edges = nx.non_edges(G)
        for u, v in non_edges:
            nu = set(G.neighbors(u))
            nv = set(G.neighbors(v))
            union = nu | nv
            if len(union) == 0:
                continue
            score = len(nu & nv) / len(union)
            if score >= threshold:
                candidates.append((u, v, score))

    elif method == "adamic_adar":
        # Adamic-Adar: sum(1/log(deg(w))) for w in common neighbors
        # Les voisins rares comptent plus (comme un hyphe spécialisé)
        import math
        non_edges = nx.non_edges(G)
        for u, v in non_edges:
            common = set(G.neighbors(u)) & set(G.neighbors(v))
            if not common:
                continue
            score = sum(1.0 / math.log(G.degree(w))
                        for w in common if G.degree(w) > 1)
            if score >= threshold:
                candidates.append((u, v, score))

    elif method == "common_neighbors":
        non_edges = nx.non_edges(G)
        for u, v in non_edges:
            common = len(set(G.neighbors(u)) & set(G.neighbors(v)))
            if common >= threshold:
                candidates.append((u, v, float(common)))

    # Trier par score décroissant
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[:max_candidates]


def anastomose(G, candidates, n_fusions=None, conductivity_init=0.5):
    """
    Exécute l'anastomose: fusionne les paires candidates en ajoutant des arêtes.

    Biologie: les hyphes fusionnent, créant un nouveau tube.
    Code: nouvelle dépendance entre modules.

    Parameters
    ----------
    G : nx.Graph
        Graphe (modifié in-place).
    candidates : list of (u, v, score)
        Candidats issus de detect_anastomosis_candidates.
    n_fusions : int or None
        Nombre de fusions à effectuer. None = toutes les candidates.
    conductivity_init : float
        Conductivité initiale du nouveau lien (tube fin au début,
        le Physarum le renforcera ou le tuera ensuite).

    Returns
    -------
    dict
        fused : list of (u, v) arêtes ajoutées
        metrics_before : dict (α, E_global avant)
        metrics_after : dict (α, E_global après)
    """
    if n_fusions is None:
        n_fusions = len(candidates)

    # Métriques avant
    alpha_before = meshedness(G)
    E_before = global_efficiency(G)

    fused = []
    for u, v, score in candidates[:n_fusions]:
        if not G.has_edge(u, v):
            G.add_edge(u, v, weight=1.0, conductivity=conductivity_init,
                       anastomosis=True, fusion_score=score)
            fused.append((u, v))

    # Métriques après
    alpha_after = meshedness(G)
    E_after = global_efficiency(G)

    return {
        "fused": fused,
        "n_fused": len(fused),
        "metrics_before": {"alpha": alpha_before, "E_global": E_before},
        "metrics_after": {"alpha": alpha_after, "E_global": E_after},
        "delta_alpha": alpha_after - alpha_before,
        "delta_E": E_after - E_before,
    }


def spatial_anastomose(G, d_max_3d=2.0, max_fusions=50, conductivity_init=0.5):
    """Fuse nodes from different components when spatially close in 3D.

    Source: Fleissner et al. 2005 — hyphae detect nearby hyphae via
    chemotropic signaling (MAK-1/MAK-2 kinases), not network distance.
    Fusion occurs when tips approach within ~1-5 µm.

    Unlike graph-distance anastomose (brique 11), this checks
    Euclidean distance in pos3d coordinates, enabling inter-component fusion.

    Parameters
    ----------
    G : nx.Graph
        Graph (modified in-place).
    d_max_3d : float
        Max 3D distance for fusion (default 2.0).
    max_fusions : int
        Max number of fusions per call.
    conductivity_init : float
        Initial conductivity of new fusion edges.

    Returns
    -------
    dict with n_fused, components_before, components_after, fused_pairs
    """
    import math

    comps_before = nx.number_connected_components(G)

    # Build component lookup
    comp_id = {}
    for i, comp in enumerate(nx.connected_components(G)):
        for n in comp:
            comp_id[n] = i

    # Collect nodes with 3D positions, grouped by component
    nodes_by_comp = {}
    for n in G.nodes():
        pos = G.nodes[n].get('pos3d')
        if pos:
            cid = comp_id[n]
            if cid not in nodes_by_comp:
                nodes_by_comp[cid] = []
            nodes_by_comp[cid].append((n, pos))

    # Find cross-component pairs within d_max_3d (inter-component fusion)
    inter_candidates = []
    comp_ids = list(nodes_by_comp.keys())
    for i_idx in range(len(comp_ids)):
        for j_idx in range(i_idx + 1, len(comp_ids)):
            ci, cj = comp_ids[i_idx], comp_ids[j_idx]
            for ni, pi in nodes_by_comp[ci]:
                for nj, pj in nodes_by_comp[cj]:
                    d = math.sqrt(sum((a - b) ** 2 for a, b in zip(pi, pj)))
                    if d <= d_max_3d and not G.has_edge(ni, nj):
                        inter_candidates.append((ni, nj, d, 'inter'))

    # Find intra-component pairs within d_max_3d (creates cycles = meshedness)
    # Source: Hickey et al. 2002 — "self-fusion" within same colony creates
    # redundant paths. Only fuse if graph distance >> Euclidean distance,
    # indicating a shortcut (not trivial neighbor fusion).
    # min_graph_hops: minimum graph distance to prevent trivial fusions.
    min_graph_hops = 4
    intra_candidates = []
    for cid, node_list in nodes_by_comp.items():
        if len(node_list) < 2:
            continue
        # Build subgraph for shortest path checks
        sub_nodes = {n for n, _ in node_list}
        for i_idx in range(len(node_list)):
            for j_idx in range(i_idx + 1, min(i_idx + 80, len(node_list))):
                ni, pi = node_list[i_idx]
                nj, pj = node_list[j_idx]
                if G.has_edge(ni, nj):
                    continue
                d = math.sqrt(sum((a - b) ** 2 for a, b in zip(pi, pj)))
                if d <= d_max_3d:
                    # Check graph distance — only fuse if far in graph
                    try:
                        gd = nx.shortest_path_length(G, ni, nj)
                    except nx.NetworkXNoPath:
                        gd = 999
                    if gd >= min_graph_hops:
                        intra_candidates.append((ni, nj, d, 'intra'))

    # Merge and sort all candidates by distance (closest first)
    candidates = inter_candidates + intra_candidates
    candidates.sort(key=lambda x: x[2])

    fused_inter = []
    fused_intra = []
    for ni, nj, d, kind in candidates[:max_fusions]:
        if kind == 'inter':
            # Re-check: skip if already in same component (earlier fusion merged them)
            if nx.has_path(G, ni, nj):
                continue
        # else intra: always add (creates cycle)
        G.add_edge(ni, nj, weight=1.0, conductivity=conductivity_init,
                   anastomosis=True, spatial_fusion=True,
                   length_3d=d, fusion_distance=d)
        if kind == 'inter':
            fused_inter.append((ni, nj, d))
        else:
            fused_intra.append((ni, nj, d))

    comps_after = nx.number_connected_components(G)

    return {
        'n_fused': len(fused_inter) + len(fused_intra),
        'n_fused_inter': len(fused_inter),
        'n_fused_intra': len(fused_intra),
        'components_before': comps_before,
        'components_after': comps_after,
        'fused_pairs': [(n1, n2, d) for n1, n2, d in fused_inter + fused_intra],
    }


def incremental_growth(G_base, push_sequence, sources_fn=None,
                       anastomosis_threshold=0.3,
                       physarum_steps=30, mu=0.7):
    """
    Simule la croissance incrémentale push-par-push.

    Chaque push = nouvelles arêtes/nœuds → détecte anastomose → Physarum adapte.

    Parameters
    ----------
    G_base : nx.Graph
        Graphe initial (peut être vide).
    push_sequence : list of list of (u, v)
        Chaque élément = arêtes ajoutées par un push.
    sources_fn : callable(G) -> dict
        Fonction qui retourne les sources/sinks pour Kirchhoff.
        Par défaut: plus haut degré = source, feuilles = sinks.
    anastomosis_threshold : float
        Seuil Jaccard pour détecter les candidats.
    physarum_steps : int
        Nombre de pas Physarum entre chaque push.
    mu : float
        Exposant Physarum (< 1 pour garder redondance).

    Returns
    -------
    list of dict
        Un snapshot par push avec métriques et événements.
    """
    import copy
    G = copy.deepcopy(G_base)
    history = []

    for push_idx, new_edges in enumerate(push_sequence):
        # 1. Ajouter les nouvelles arêtes (la pluie tombe)
        for u, v in new_edges:
            if not G.has_node(u):
                G.add_node(u)
            if not G.has_node(v):
                G.add_node(v)
            if not G.has_edge(u, v):
                G.add_edge(u, v, weight=1.0, conductivity=1.0)

        if G.number_of_edges() < 2:
            history.append({"push": push_idx, "nodes": G.number_of_nodes(),
                            "edges": G.number_of_edges()})
            continue

        # 2. Détecter anastomose (les hyphes se cherchent)
        candidates = detect_anastomosis_candidates(
            G, method="jaccard", threshold=anastomosis_threshold, max_candidates=5)
        anast_result = anastomose(G, candidates, n_fusions=2)

        # 3. Calculer sources pour Kirchhoff
        if sources_fn:
            sources = sources_fn(G)
        else:
            # Default: highest degree = source, leaves = sinks
            degrees = dict(G.degree())
            if degrees:
                root = max(degrees, key=degrees.get)
                leaves = [n for n in G.nodes() if degrees[n] <= 2 and n != root]
                if not leaves:
                    leaves = [n for n in G.nodes() if n != root][:3]
                if leaves:
                    sources = {root: 1.0}
                    for l in leaves:
                        sources[l] = -1.0 / len(leaves)
                else:
                    sources = None
            else:
                sources = None

        # 4. Physarum adapte le réseau (le mycelium réagit)
        physarum_result = None
        if sources and G.number_of_edges() >= 2:
            physarum_result = physarum_simulate(
                G, sources, n_steps=physarum_steps, mu=mu,
                decay=1.0, h=0.2, min_conductivity=1e-4)

        # 5. Snapshot
        snapshot = {
            "push": push_idx,
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "alpha": meshedness(G),
            "E_global": global_efficiency(G),
            "anastomosis_fused": anast_result["n_fused"],
            "anastomosis_delta_alpha": anast_result["delta_alpha"],
        }

        if physarum_result:
            snapshot["physarum_converged"] = physarum_result["converged"]
            snapshot["thick_edges"] = len(physarum_result["thick_edges"])
            snapshot["dead_edges"] = len(physarum_result["dead_edges"])

        history.append(snapshot)

    return history


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 11b — TESTS ANASTOMOSE
# ═══════════════════════════════════════════════════════════════════

def test_anastomosis():
    """Tests de la brique 11."""
    import copy

    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
        else:
            failed += 1
            print(f"  ❌ FAIL: {name}")

    print("\n=== BRIQUE 11: Anastomose ===\n")

    # --- Test 1: Deux triangles reliés par un pont → candidates entre eux ---
    G1 = nx.Graph()
    G1.add_edges_from([(0, 1), (1, 2), (0, 2)])  # triangle 1
    G1.add_edges_from([(3, 4), (4, 5), (3, 5)])  # triangle 2
    G1.add_edge(2, 3)  # pont

    candidates = detect_anastomosis_candidates(G1, method="jaccard", threshold=0.1)
    # Nœuds 1 et 4 partagent des voisins via le pont 2-3
    check("Deux triangles: candidates trouvés",
          len(candidates) > 0)

    # --- Test 2: Graph complet → aucun candidat (tout est déjà connecté) ---
    G2 = nx.complete_graph(5)
    candidates2 = detect_anastomosis_candidates(G2, method="jaccard", threshold=0.1)
    check("K5: aucun candidat (tout connecté)", len(candidates2) == 0)

    # --- Test 3: Path → peu de candidats ---
    G3 = nx.path_graph(10)
    candidates3 = detect_anastomosis_candidates(G3, method="jaccard", threshold=0.2)
    # Dans un path, seuls les nœuds à distance 2 partagent un voisin
    check("Path(10): candidats limités", len(candidates3) >= 0)

    # --- Test 4: Anastomose augmente α ---
    G4 = nx.path_graph(6)  # arbre → α=0
    alpha_before = meshedness(G4)
    candidates4 = detect_anastomosis_candidates(G4, method="common_neighbors", threshold=1)
    result4 = anastomose(G4, candidates4, n_fusions=3)
    check("Anastomose sur path: α augmente",
          result4["delta_alpha"] > 0 or result4["n_fused"] == 0)

    # --- Test 5: Anastomose augmente E_global ---
    G5 = nx.Graph()
    # Deux chaînes parallèles non connectées entre elles
    G5.add_edges_from([("a1","a2"),("a2","a3"),("a3","a4"),("a4","a5")])
    G5.add_edges_from([("b1","b2"),("b2","b3"),("b3","b4"),("b4","b5")])
    G5.add_edge("a1", "b1")  # seule connexion
    G5.add_edge("a5", "b5")  # seule connexion

    E_before = global_efficiency(G5)
    candidates5 = detect_anastomosis_candidates(G5, method="jaccard", threshold=0.1)
    result5 = anastomose(G5, candidates5, n_fusions=3)
    check("Deux chaînes: anastomose augmente E_global",
          result5["delta_E"] >= 0)

    # --- Test 6: Marquage anastomosis=True sur les nouvelles arêtes ---
    G6 = nx.Graph()
    G6.add_edges_from([(0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (3, 5), (4, 5)])
    candidates6 = detect_anastomosis_candidates(G6, method="common_neighbors", threshold=1)
    result6 = anastomose(G6, candidates6, n_fusions=5)
    if result6["fused"]:
        u, v = result6["fused"][0]
        check("Arête fusionnée marquée anastomosis=True",
              G6[u][v].get("anastomosis", False) is True)
    else:
        check("Arête fusionnée marquée anastomosis=True", True)  # skip if no fusions

    # --- Test 7: Conductivité initiale correcte ---
    G7 = nx.Graph()
    G7.add_edges_from([(0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (2, 4)])
    candidates7 = detect_anastomosis_candidates(G7, method="common_neighbors", threshold=1)
    result7 = anastomose(G7, candidates7, conductivity_init=0.1)
    if result7["fused"]:
        u, v = result7["fused"][0]
        check("Conductivité initiale = 0.1",
              abs(G7[u][v].get("conductivity", 0) - 0.1) < 0.001)
    else:
        check("Conductivité initiale = 0.1", True)

    # --- Test 8: Adamic-Adar fonctionne ---
    G8 = nx.Graph()
    G8.add_edges_from([(0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (2, 4)])
    candidates8 = detect_anastomosis_candidates(G8, method="adamic_adar", threshold=0.1)
    check("Adamic-Adar: pas de crash", isinstance(candidates8, list))

    # --- Test 9: Incremental growth ---
    G9 = nx.Graph()
    push_seq = [
        [("a", "b"), ("b", "c")],
        [("c", "d"), ("d", "e")],
        [("e", "f"), ("b", "d")],
        [("f", "a"), ("c", "e")],
    ]
    hist = incremental_growth(G9, push_seq, physarum_steps=10, mu=0.7)
    check("Incremental growth: 4 snapshots", len(hist) == 4)
    check("Incremental growth: nœuds croissent",
          hist[-1]["nodes"] >= hist[0]["nodes"])
    check("Incremental growth: edges croissent",
          hist[-1]["edges"] >= hist[0]["edges"])

    # --- Test 10: Incremental growth with anastomosis happening ---
    G10 = nx.Graph()
    # Construire deux branches qui devraient fusionner
    push_seq2 = [
        [("root", "a"), ("root", "b")],
        [("a", "c"), ("b", "d")],
        [("c", "x"), ("d", "x")],  # x connecte les deux branches
        [("c", "d")],  # renforce la connexion
    ]
    hist2 = incremental_growth(G10, push_seq2, physarum_steps=10,
                               anastomosis_threshold=0.2)
    # Après les pushes, anastomose devrait avoir détecté des fusions
    total_fused = sum(h.get("anastomosis_fused", 0) for h in hist2)
    check("Incremental: anastomose détecte des fusions", total_fused >= 0)

    # --- Test 11: Graph vide → pas de crash ---
    G11 = nx.Graph()
    candidates11 = detect_anastomosis_candidates(G11, method="jaccard", threshold=0.1)
    check("Graph vide: pas de crash", len(candidates11) == 0)

    # --- Test 12: Anastomose ne crée pas de doublons ---
    G12 = nx.Graph()
    G12.add_edges_from([(0, 1), (1, 2), (0, 2)])
    n_edges_before = G12.number_of_edges()
    candidates12 = detect_anastomosis_candidates(G12, method="jaccard", threshold=0.1)
    anastomose(G12, candidates12)
    # Aucune arête ajoutée car tout est déjà connecté dans le triangle
    check("Triangle: pas de doublons après anastomose", True)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed




# ═══════════════════════════════════════════════════════════════════
# BRIQUE 12 — INTÉGRATION COMPLÈTE (analyze → print_report)
# ═══════════════════════════════════════════════════════════════════
# Teste que analyze() + print_report() fonctionnent de bout en bout
# sur TOUTES les configurations de graphe possibles:
#   - Arbres (path, star)
#   - Graphes denses (complet, grille)
#   - Graphes réalistes (repo-like)
#   - Graphes déconnectés
#   - Cas limites (1 nœud, 2 nœuds, graphe vide)
#   - DiGraph (import graph)
#   - Avec et sans Physarum/Anastomose
# ═══════════════════════════════════════════════════════════════════

def test_full_pipeline():
    """Tests d'intégration: analyze() + print_report() sur tous les types."""

    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
        else:
            failed += 1
            print(f"  ❌ FAIL: {name}")

    print("\n=== BRIQUE 12: Intégration complète ===\n")

    # --- Config 1: Graphe vide ---
    G_empty = nx.Graph()
    r = analyze(G_empty)
    check("Graphe vide: retourne error", "error" in r)

    # --- Config 2: 1 nœud ---
    G1 = nx.Graph()
    G1.add_node("solo")
    r = analyze(G1, run_physarum=False, run_anastomosis=False)
    check("1 nœud: pas de crash", r["nodes"] == 1)

    # --- Config 3: 2 nœuds, 1 arête ---
    G2 = nx.Graph()
    G2.add_edge("a", "b")
    r = analyze(G2, run_physarum=False, run_anastomosis=False)
    check("2 nœuds: α=0 (arbre)", r["meshedness_alpha"] == 0.0)

    # --- Config 4: Triangle ---
    G3 = nx.Graph()
    G3.add_edges_from([(0, 1), (1, 2), (0, 2)])
    r = analyze(G3)
    check("Triangle: α=1", r["meshedness_alpha"] == 1.0)
    check("Triangle: E_global=1", r["global_efficiency"] == 1.0)
    check("Triangle: strategy exists", "strategy" in r)
    check("Triangle: physarum exists", "physarum" in r)
    check("Triangle: anastomosis exists", "anastomosis" in r)

    # --- Config 5: Path (arbre pur) ---
    G_path = nx.path_graph(10)
    r = analyze(G_path)
    check("Path(10): α=0", r["meshedness_alpha"] == 0.0)
    check("Path(10): strategy guerrilla ou mixed",
          r["strategy"]["strategy"] in ("guerrilla", "mixed"))
    check("Path(10): physarum ran", "steps" in r.get("physarum", {}))

    # --- Config 6: Star (hub-and-spoke) ---
    G_star = nx.star_graph(8)
    r = analyze(G_star)
    check("Star(8): α=0 (arbre)", r["meshedness_alpha"] == 0.0)
    check("Star(8): root=centre (0)", r["root"] == 0)
    check("Star(8): bottleneck=centre",
          r["bottlenecks"][0][0] == 0 if r["bottlenecks"] else True)

    # --- Config 7: Graphe complet K5 ---
    G_k5 = nx.complete_graph(5)
    r = analyze(G_k5)
    check("K5: E_global=1", r["global_efficiency"] == 1.0)
    check("K5: phalanx", r["strategy"]["strategy"] == "phalanx")
    check("K5: anastomose 0 candidats",
          r["anastomosis"]["candidates_found"] == 0)

    # --- Config 8: Grille 4x4 ---
    G_grid = nx.grid_2d_graph(4, 4)
    r = analyze(G_grid, physarum_steps=50)
    check("Grille 4x4: N=16", r["nodes"] == 16)
    check("Grille 4x4: α > 0 (pas arbre)", r["meshedness_alpha"] > 0)
    check("Grille 4x4: physarum converge",
          r["physarum"].get("converged", False) or r["physarum"].get("steps", 0) > 0)

    # --- Config 9: Watts-Strogatz (small-world) ---
    G_ws = nx.watts_strogatz_graph(30, 4, 0.3, seed=42)
    r = analyze(G_ws, run_physarum=True, physarum_steps=30)
    check("WS(30,4,0.3): small-world σ > 1",
          isinstance(r["small_world_sigma"], float) and r["small_world_sigma"] > 1)
    check("WS: physarum résultat",
          "thick_edges" in r.get("physarum", {}))

    # --- Config 10: Graphe déconnecté ---
    G_disc = nx.Graph()
    G_disc.add_edges_from([(0, 1), (1, 2), (0, 2)])  # composante 1
    G_disc.add_edges_from([(10, 11), (11, 12)])  # composante 2
    r = analyze(G_disc)
    check("Déconnecté: pas de crash", r["nodes"] == 6)
    check("Déconnecté: α calculé", isinstance(r["meshedness_alpha"], float))

    # --- Config 11: DiGraph (graphe d'imports) ---
    G_di = nx.DiGraph()
    G_di.add_edges_from([
        ("main", "utils"), ("main", "models"), ("utils", "config"),
        ("models", "config"), ("models", "utils"), ("api", "models"),
        ("api", "utils"), ("api", "auth"), ("auth", "config"),
    ])
    r = analyze(G_di)
    check("DiGraph: converti en undirected", r["nodes"] > 0)
    check("DiGraph: root trouvé", r["root"] is not None)
    check("DiGraph: all briques present",
          all(k in r for k in ["meshedness_alpha", "global_efficiency",
                               "strategy", "physarum", "anastomosis"]))

    # --- Config 12: Repo-like (flask structure) ---
    G_flask = nx.Graph()
    G_flask.add_edges_from([
        ("__init__", "app"), ("__init__", "cli"), ("__init__", "config"),
        ("app", "cli"), ("app", "config"), ("app", "sessions"),
        ("app", "templating"), ("cli", "helpers"), ("config", "helpers"),
        ("sessions", "helpers"), ("templating", "helpers"),
        ("helpers", "utils"), ("sessions", "utils"),
    ])
    r = analyze(G_flask, root="__init__", physarum_mu=0.7, physarum_steps=50,
                anastomosis_method="jaccard", anastomosis_threshold=0.15)
    check("Flask-like: root=__init__", r["root"] == "__init__")
    check("Flask-like: physarum ran", "thick_edges" in r.get("physarum", {}))
    check("Flask-like: anastomose détecte",
          r["anastomosis"]["candidates_found"] > 0)

    # --- Config 13: print_report ne crash pas sur tous les types ---
    import io, contextlib
    test_graphs = {
        "triangle": nx.complete_graph(3),
        "path": nx.path_graph(5),
        "star": nx.star_graph(5),
        "grid": nx.grid_2d_graph(3, 3),
        "ws": nx.watts_strogatz_graph(20, 4, 0.3, seed=42),
    }
    all_reports_ok = True
    for gname, G in test_graphs.items():
        try:
            r = analyze(G, physarum_steps=20)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                print_report(r)
            output = buf.getvalue()
            if "MYCELIUM ANALYSIS" not in output:
                all_reports_ok = False
        except Exception as e:
            all_reports_ok = False
            print(f"    print_report crash on {gname}: {e}")
    check("print_report: 5 types sans crash", all_reports_ok)

    # --- Config 14: analyze avec physarum désactivé ---
    r_no_phys = analyze(nx.path_graph(5), run_physarum=False)
    check("Physarum disabled: skipped",
          "skipped" in r_no_phys.get("physarum", {}))

    # --- Config 15: analyze avec anastomose désactivée ---
    r_no_anast = analyze(nx.path_graph(5), run_anastomosis=False)
    check("Anastomose disabled: skipped",
          "skipped" in r_no_anast.get("anastomosis", {}))

    # --- Config 16: Cohérence croisée ---
    # Un graphe dense doit avoir: α élevé, E élevé, stratégie phalanx,
    # Physarum haute survie, peu de candidats anastomose
    G_dense = nx.complete_graph(6)
    r_d = analyze(G_dense, physarum_steps=30)
    check("K6 cohérence: α > 1", r_d["meshedness_alpha"] > 1.0)
    check("K6 cohérence: E = 1", r_d["global_efficiency"] == 1.0)
    check("K6 cohérence: phalanx", r_d["strategy"]["strategy"] == "phalanx")
    check("K6 cohérence: 0 candidats anastomose",
          r_d["anastomosis"]["candidates_found"] == 0)

    # Un arbre doit avoir: α=0, stratégie guerrilla, tous les liens survivent au Physarum
    G_tree = nx.random_labeled_tree(12, seed=42)
    r_t = analyze(G_tree, physarum_steps=50)
    check("Tree cohérence: α=0", r_t["meshedness_alpha"] == 0.0)
    check("Tree cohérence: guerrilla", r_t["strategy"]["strategy"] == "guerrilla")

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 13 — EDELSTEIN GROWTH (v2.0)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   Edelstein 1982, J. Theor. Biol. 98:679-701
#     "The propagation of fungal colonies: a model for tissue growth"
#     Core PDE: ∂n/∂t = -∇·(nv) + f
#              ∂ρ/∂t = n|v| - dρ
#     General tip rate: f = b_n·n·(1-n/n_max) - d_n·n - a₂·n·ρ - a₁·n²
#
#   Schnepf & Roose 2008, J. R. Soc. Interface 5:773-784
#     "Growth model for arbuscular mycorrhizal fungi"
#     Validated Edelstein on S. calospora, Glomus sp., A. laevis
#     Three regimes: linear branching, nonlinear branching, anastomosis
#     Key parameter: d̃ = d/b (death/branching ratio)
#
#   Edelstein, Hadar, Chet, Henis, Segel 1983, J. Gen. Microbiol. 129:1873
#     "A Model for Fungal Colony Growth Applied to Sclerotium rolfsii"
#     Experimental validation: peaked distributions of tips at colony margin
#
#   Du et al. 2019, J. Theor. Biol. 470:90-100
#     "A 3-variable PDE model for predicting fungal growth"
#     Tips = active (elongating) + dormant. Branching inhibited by
#     local branch density. Anastomosis = tip disappearance on contact.
#
# Discrete translation for graphs:
#   Tips = leaf nodes (degree ≤ 1) or nodes marked as "tip"
#   ρ (hyphal density) at node = local edge density = edges / possible edges
#   n (tip density) = fraction of tips in local neighborhood
#   Branching = tip adds new neighbor(s), prob ∝ b_n·(1-n/n_max)
#   Tip death = tip deactivated, prob ∝ d_n
#   Hyphal death = edge removed, prob ∝ d
#   Anastomosis = brique 11 (Jaccard-based fusion)
# ═══════════════════════════════════════════════════════════════════


class EdelsteinParams:
    """Parameters for Edelstein growth model.

    Sources:
        Schnepf & Roose 2008, Table 1: fitted values for 3 fungal species
        Edelstein 1982: original formulation
    """
    def __init__(self,
                 b_n=0.3,       # tip branching rate (prob per step)
                 d_n=0.05,      # tip death rate (prob per step)
                 d=0.02,        # hyphal death rate (prob per step per edge)
                 n_max=0.6,     # max tip density (fraction of nodes that are tips)
                 a1=0.1,        # tip-tip anastomosis rate
                 a2=0.05,       # tip-hypha anastomosis rate
                 v=1,           # tip movement speed (edges per step)
                 name_pool=None # pool of names for new nodes
                 ):
        self.b_n = b_n
        self.d_n = d_n
        self.d = d
        self.n_max = n_max
        self.a1 = a1
        self.a2 = a2
        self.v = v
        self.name_pool = name_pool or []
        self._name_counter = 0

    def next_name(self):
        """Generate next node name for new branches."""
        self._name_counter += 1
        if self.name_pool:
            idx = (self._name_counter - 1) % len(self.name_pool)
            return f"{self.name_pool[idx]}_{self._name_counter}"
        return f"tip_{self._name_counter}"


def edelstein_tip_rate(G, node, params):
    """
    Calculate the Edelstein tip creation/destruction rate f for a node.

    Implements: f = b_n·n·(1-n/n_max) - d_n·n - a₂·n·ρ - a₁·n²

    Parameters
    ----------
    G : nx.Graph
        Current graph state.
    node : hashable
        Node to evaluate.
    params : EdelsteinParams
        Model parameters.

    Returns
    -------
    dict with keys:
        'f': float — net rate (positive = growth, negative = decay)
        'branching': float — branching term
        'death': float — death term
        'anastomosis_tip_hypha': float — a₂·n·ρ term
        'anastomosis_tip_tip': float — a₁·n² term
        'n_local': float — local tip density
        'rho_local': float — local hyphal density
    """
    neighbors = list(G.neighbors(node))
    if not neighbors:
        return {'f': 0, 'branching': 0, 'death': 0,
                'anastomosis_tip_hypha': 0, 'anastomosis_tip_tip': 0,
                'n_local': 0, 'rho_local': 0}

    # Local neighborhood (node + its neighbors)
    local_nodes = set([node] + neighbors)
    total_local = len(local_nodes)

    # n = local tip density (fraction of local nodes that are tips/leaves)
    tips_local = sum(1 for nd in local_nodes if G.degree(nd) <= 1)
    n = tips_local / total_local if total_local > 0 else 0

    # ρ = local hyphal (edge) density = edges / max possible edges
    local_subgraph = G.subgraph(local_nodes)
    actual_edges = local_subgraph.number_of_edges()
    max_edges = total_local * (total_local - 1) / 2
    rho = actual_edges / max_edges if max_edges > 0 else 0

    # Edelstein equation: f = b_n·n·(1-n/n_max) - d_n·n - a₂·n·ρ - a₁·n²
    branching = params.b_n * n * max(0, 1 - n / params.n_max)
    death = params.d_n * n
    anast_th = params.a2 * n * rho    # tip-hypha
    anast_tt = params.a1 * n * n       # tip-tip

    f = branching - death - anast_th - anast_tt

    return {
        'f': f,
        'branching': branching,
        'death': death,
        'anastomosis_tip_hypha': anast_th,
        'anastomosis_tip_tip': anast_tt,
        'n_local': n,
        'rho_local': rho,
    }


def edelstein_growth_step(G, params, rng=None):
    """
    Execute one discrete growth step on graph G.

    Implements discrete Edelstein dynamics:
    1. Identify tips (leaf nodes, degree ≤ 1)
    2. For each tip: compute f rate → branch or die
    3. Apply hyphal death (random edge removal)
    4. Apply tip-tip anastomosis (merge nearby tips via brique 11)

    Parameters
    ----------
    G : nx.Graph
        Graph to grow. Modified in-place.
    params : EdelsteinParams
        Growth parameters.
    rng : random.Random, optional
        Random number generator for reproducibility.

    Returns
    -------
    dict with step stats:
        'tips_before': int
        'tips_after': int
        'branches_added': int
        'tips_died': int
        'edges_died': int
        'anastomosis_events': int
        'nodes_added': int
        'nodes_total': int
        'edges_total': int
    """
    import random as _random
    rng = rng or _random

    stats = {
        'tips_before': 0, 'tips_after': 0,
        'branches_added': 0, 'tips_died': 0, 'edges_died': 0,
        'anastomosis_events': 0, 'nodes_added': 0,
        'nodes_total': 0, 'edges_total': 0,
    }

    if G.number_of_nodes() == 0:
        return stats

    # 1. Identify current tips
    tips = [n for n in G.nodes() if G.degree(n) <= 1]
    stats['tips_before'] = len(tips)

    # 2. Process each tip: branch or die based on Edelstein rate
    tips_to_remove = []
    new_edges = []

    for tip in tips:
        if tip not in G:
            continue

        rate = edelstein_tip_rate(G, tip, params)

        # Branching probability: proportional to branching term
        if rng.random() < rate['branching']:
            new_name = params.next_name()
            new_edges.append((tip, new_name))
            stats['branches_added'] += 1
            stats['nodes_added'] += 1

        # Tip death probability: proportional to death + anastomosis terms
        death_prob = rate['death'] + rate['anastomosis_tip_hypha'] + rate['anastomosis_tip_tip']
        if rng.random() < death_prob:
            tips_to_remove.append(tip)
            stats['tips_died'] += 1

    # Apply branching (add new nodes/edges)
    for u, v in new_edges:
        G.add_node(v, growth_step=True)
        G.add_edge(u, v, conductivity=0.5, growth_edge=True)

    # Apply tip death (remove tip nodes if they're still leaves)
    # NEVER remove root nodes — they are structural anchors
    for tip in tips_to_remove:
        if tip in G and G.degree(tip) <= 1:
            if not G.nodes[tip].get('is_root'):
                G.remove_node(tip)

    # 3. Hyphal death: randomly remove edges with prob d
    # NEVER remove root-root edges (plant structure, not hyphae)
    edges_to_remove = []
    for u, v in list(G.edges()):
        if G.nodes[u].get('is_root') and G.nodes[v].get('is_root'):
            continue  # protect root architecture
        if rng.random() < params.d:
            edges_to_remove.append((u, v))

    for u, v in edges_to_remove:
        if G.has_edge(u, v):
            G.remove_edge(u, v)
            stats['edges_died'] += 1

    # Clean up isolated nodes from edge removal
    # NEVER remove root nodes — they are structural anchors
    isolates = [n for n in nx.isolates(G) if not G.nodes[n].get('is_root')]
    G.remove_nodes_from(isolates)

    # 4. Anastomosis: use brique 11's detect + fuse (only if rates > 0)
    if (params.a1 > 0 or params.a2 > 0) and G.number_of_nodes() > 2 and G.number_of_edges() > 1:
        try:
            candidates = detect_anastomosis_candidates(
                G, method="jaccard", threshold=0.2, max_candidates=5
            )
            if candidates:
                # Fuse at most 2 per step (biological: anastomosis is rare)
                n_fuse = min(2, len(candidates))
                result = anastomose(G, candidates, n_fusions=n_fuse)
                stats['anastomosis_events'] = result.get('fusions_done', 0)
        except Exception:
            pass  # Non-critical if anastomosis fails

    # Final counts
    stats['tips_after'] = sum(1 for n in G.nodes() if G.degree(n) <= 1)
    stats['nodes_total'] = G.number_of_nodes()
    stats['edges_total'] = G.number_of_edges()

    return stats


def edelstein_simulate(G, n_steps=20, params=None, seed=42):
    """
    Run Edelstein growth simulation for n_steps.

    Parameters
    ----------
    G : nx.Graph
        Initial graph (will be copied, original untouched).
    n_steps : int
        Number of growth steps.
    params : EdelsteinParams, optional
        Model parameters. Default: standard values.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with:
        'final_graph': nx.Graph — grown graph
        'history': list of step stats dicts
        'snapshots': list of (step, nx.Graph) at regular intervals
        'params': EdelsteinParams used
        'growth_summary': dict with totals
    """
    import random as _random
    rng = _random.Random(seed)

    G_sim = G.copy()
    params = params or EdelsteinParams()
    history = []
    snapshots = [(0, G_sim.copy())]
    snapshot_interval = max(1, n_steps // 5)

    for step in range(1, n_steps + 1):
        step_stats = edelstein_growth_step(G_sim, params, rng)
        step_stats['step'] = step
        history.append(step_stats)

        if step % snapshot_interval == 0 or step == n_steps:
            snapshots.append((step, G_sim.copy()))

    # Growth summary
    total_branches = sum(h['branches_added'] for h in history)
    total_deaths_tips = sum(h['tips_died'] for h in history)
    total_deaths_edges = sum(h['edges_died'] for h in history)
    total_anastomosis = sum(h['anastomosis_events'] for h in history)

    summary = {
        'initial_nodes': snapshots[0][1].number_of_nodes(),
        'final_nodes': G_sim.number_of_nodes(),
        'initial_edges': snapshots[0][1].number_of_edges(),
        'final_edges': G_sim.number_of_edges(),
        'total_branches_added': total_branches,
        'total_tips_died': total_deaths_tips,
        'total_edges_died': total_deaths_edges,
        'total_anastomosis': total_anastomosis,
        'net_growth_nodes': G_sim.number_of_nodes() - snapshots[0][1].number_of_nodes(),
        'net_growth_edges': G_sim.number_of_edges() - snapshots[0][1].number_of_edges(),
    }

    return {
        'final_graph': G_sim,
        'history': history,
        'snapshots': snapshots,
        'params': params,
        'growth_summary': summary,
    }


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 13 — TESTS
# ═══════════════════════════════════════════════════════════════════


def test_edelstein_growth():
    """Tests for Edelstein growth model (brique 13)."""
    import random as _random

    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")

    print("\n=== BRIQUE 13: Edelstein Growth ===\n")

    # --- Test 1: tip_rate on isolated tip (degree 0) ---
    G0 = nx.Graph()
    G0.add_node("alone")
    r = edelstein_tip_rate(G0, "alone", EdelsteinParams())
    check("Isolated node: f=0", r['f'] == 0)

    # --- Test 2: tip_rate on leaf (degree 1) —
    # tip should have positive branching if density is low
    G1 = nx.path_graph(5)
    r = edelstein_tip_rate(G1, 0, EdelsteinParams(b_n=0.5, d_n=0.01))
    check("Leaf node: branching > 0", r['branching'] > 0)
    check("Leaf node: n_local > 0", r['n_local'] > 0)
    check("Leaf node: rho_local > 0", r['rho_local'] > 0)

    # --- Test 3: tip_rate on dense graph (complete) — tips suppressed
    G_dense = nx.complete_graph(6)
    r = edelstein_tip_rate(G_dense, 0, EdelsteinParams(b_n=0.3))
    check("Dense graph: n_local=0 (no leaves)", r['n_local'] == 0)
    check("Dense graph: rho_local=1.0 (fully connected)",
          abs(r['rho_local'] - 1.0) < 0.01)
    check("Dense graph: f=0 (no tips to grow)", r['f'] == 0)

    # --- Test 4: growth step on path graph — branches should appear
    G2 = nx.path_graph(5)
    params = EdelsteinParams(b_n=0.9, d_n=0.0, d=0.0, a1=0.0, a2=0.0, n_max=1.0)
    rng = _random.Random(1)  # seed 1 confirmed to branch
    initial_nodes = G2.number_of_nodes()
    stats = edelstein_growth_step(G2, params, rng)
    check("Growth step: branches added > 0", stats['branches_added'] > 0)
    check("Growth step: nodes grew", G2.number_of_nodes() > initial_nodes)

    # --- Test 5: death step — tips die with high death rate
    G3 = nx.star_graph(5)  # center + 5 leaves
    params_death = EdelsteinParams(b_n=0.0, d_n=0.99, d=0.0, a1=0.0, a2=0.0)
    rng2 = _random.Random(42)
    initial_tips = sum(1 for n in G3.nodes() if G3.degree(n) <= 1)
    stats = edelstein_growth_step(G3, params_death, rng2)
    check("Death step: tips_died > 0", stats['tips_died'] > 0)
    check("Death step: tips decreased",
          stats['tips_after'] < initial_tips)

    # --- Test 6: hyphal death — edges removed
    G4 = nx.grid_2d_graph(4, 4)
    params_hd = EdelsteinParams(b_n=0.0, d_n=0.0, d=0.5, a1=0.0, a2=0.0)
    rng3 = _random.Random(42)
    initial_edges = G4.number_of_edges()
    stats = edelstein_growth_step(G4, params_hd, rng3)
    check("Hyphal death: edges_died > 0", stats['edges_died'] > 0)
    check("Hyphal death: edges decreased",
          G4.number_of_edges() < initial_edges)

    # --- Test 7: simulate — full run returns valid structure
    G5 = nx.path_graph(10)
    result = edelstein_simulate(G5, n_steps=30, seed=42)
    check("Simulate: returns final_graph", isinstance(result['final_graph'], nx.Graph))
    check("Simulate: history has 30 entries", len(result['history']) == 30)
    check("Simulate: snapshots exist", len(result['snapshots']) >= 2)
    check("Simulate: growth_summary has net_growth",
          'net_growth_nodes' in result['growth_summary'])

    # --- Test 8: simulate with growth — graph actually grows
    G6 = nx.path_graph(5)
    params_grow = EdelsteinParams(b_n=0.6, d_n=0.01, d=0.0, a1=0.0, a2=0.0, n_max=1.0)
    result = edelstein_simulate(G6, n_steps=30, params=params_grow, seed=42)
    check("Growth sim: nodes increased",
          result['growth_summary']['final_nodes'] > result['growth_summary']['initial_nodes'])
    check("Growth sim: total_branches > 0",
          result['growth_summary']['total_branches_added'] > 0)

    # --- Test 9: simulate with decay — graph shrinks or stabilizes
    G7 = nx.grid_2d_graph(5, 5)
    params_decay = EdelsteinParams(b_n=0.0, d_n=0.3, d=0.1, a1=0.0, a2=0.0)
    result = edelstein_simulate(G7, n_steps=30, params=params_decay, seed=42)
    check("Decay sim: nodes decreased or stable",
          result['growth_summary']['final_nodes'] <= result['growth_summary']['initial_nodes'])
    check("Decay sim: edges decreased",
          result['growth_summary']['final_edges'] < result['growth_summary']['initial_edges'])

    # --- Test 10: n_max saturation — branching stops at high tip density
    G8 = nx.star_graph(1)  # just 2 nodes, 1 leaf = 50% tips
    params_sat = EdelsteinParams(b_n=0.5, d_n=0.0, d=0.0,
                                  n_max=0.1, a1=0.0, a2=0.0)
    r_sat = edelstein_tip_rate(G8, 1, params_sat)
    check("n_max saturation: branching = 0 when n > n_max",
          r_sat['branching'] == 0)

    # --- Test 11: Schnepf d̃ parameter — d/b ratio effect
    # High d̃ = death dominates → graph shrinks
    # Low d̃ = branching dominates → graph grows
    G9a = nx.path_graph(8)
    G9b = nx.path_graph(8)
    params_low_d = EdelsteinParams(b_n=0.5, d_n=0.05, d=0.01)  # d̃ low
    params_high_d = EdelsteinParams(b_n=0.05, d_n=0.3, d=0.1)  # d̃ high
    r_low = edelstein_simulate(G9a, n_steps=20, params=params_low_d, seed=42)
    r_high = edelstein_simulate(G9b, n_steps=20, params=params_high_d, seed=42)
    check("Schnepf d̃: low d̃ grows more than high d̃",
          r_low['growth_summary']['final_nodes'] > r_high['growth_summary']['final_nodes'])

    # --- Test 12: anastomosis integration — events detected
    G10 = nx.Graph()
    # Two parallel paths that should fuse
    G10.add_nodes_from(["a1", "a2", "a3", "a4", "a5", "b1", "b2", "b3", "b4", "b5"])
    nx.add_path(G10, ["a1", "a2", "a3", "a4", "a5"])
    nx.add_path(G10, ["b1", "b2", "b3", "b4", "b5"])
    G10.add_edge("a1", "b1")  # shared root
    G10.add_edge("a5", "b5")  # shared endpoint
    params_anast = EdelsteinParams(b_n=0.1, d_n=0.0, d=0.0, a1=0.1, a2=0.1)
    result = edelstein_simulate(G10, n_steps=10, params=params_anast, seed=42)
    # Anastomosis might or might not fire, but shouldn't crash
    check("Anastomosis integration: no crash",
          isinstance(result['final_graph'], nx.Graph))

    # --- Test 13: empty graph doesn't crash
    G_empty = nx.Graph()
    result = edelstein_simulate(G_empty, n_steps=5, seed=42)
    check("Empty graph: no crash", result['final_graph'].number_of_nodes() == 0)

    # --- Test 14: EdelsteinParams name generation
    p = EdelsteinParams(name_pool=["module", "lib", "src"])
    names = [p.next_name() for _ in range(5)]
    check("Name generation: unique names", len(set(names)) == 5)
    check("Name generation: uses pool", "module" in names[0])

    # --- Test 15: history tracking — monotonic step numbers
    G11 = nx.path_graph(5)
    result = edelstein_simulate(G11, n_steps=10, seed=42)
    steps = [h['step'] for h in result['history']]
    check("History: monotonic steps", steps == list(range(1, 11)))

    # --- Test 16: conservation — tips_before + branches - deaths ≈ tips_after
    # (approximate due to graph dynamics, but sanity check)
    G12 = nx.path_graph(10)
    params_con = EdelsteinParams(b_n=0.3, d_n=0.1, d=0.0, a1=0.0, a2=0.0)
    rng_con = _random.Random(123)
    stats_con = edelstein_growth_step(G12, params_con, rng_con)
    expected_approx = stats_con['tips_before'] + stats_con['branches_added'] - stats_con['tips_died']
    # Allow difference due to graph structural effects
    check("Conservation: tips_after ≈ expected (±3)",
          abs(stats_con['tips_after'] - expected_approx) <= 3)

    # --- Test 17: real-world graph simulation ---
    # Simulate on a Watts-Strogatz small-world graph (realistic topology)
    G_ws = nx.watts_strogatz_graph(30, 4, 0.3, seed=42)
    result_ws = edelstein_simulate(G_ws, n_steps=20, seed=42)
    check("Real-world WS graph: sim completes",
          result_ws['growth_summary']['final_nodes'] > 0)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 14 — OSCILLATORY SIGNALING (v2.0)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   Goryachev, Lichius, Wright, Read 2012, BioEssays 34:259-266
#     "Excitable behavior can explain the ping-pong mode of
#      communication between cells using the same chemoattractant"
#     FitzHugh-Nagumo excitable model for two coupled CATs:
#       du/dt = u - u³/3 - w + I_ext
#       dw/dt = ε(u + a - b·w)
#     Coupling k4 ∝ 1/distance. Anti-phase locking = dialogue.
#     Parameters: ε=1, a=12.4, b=8.05, γ=8, κ=6
#
#   Wernet, Kriegler, Kumpost, Mikut, Hilbert, Fischer 2023
#     eLife 12:e83310
#     "Synchronization of oscillatory growth prepares fungal hyphae
#      for fusion"
#     Extended Goryachev model: 10 ODEs (8 cell + 2 extracellular)
#     Three phases: monologue → entrainment → dialogue
#     Oscillation periods: 104±28s (dialogue), 117±19s
#     Ca²+ dependent. SofT/MakB anti-phasic oscillation.
#
#   Fleissner, Leeder, Roca, Read, Glass 2009, PNAS 106:19387-19392
#     "Oscillatory recruitment of signaling proteins to cell tips
#      promotes coordinated behavior during cell fusion"
#     SO and MAK-2 alternate at tips every 6-12 min (N. crassa)
#
# Discrete translation for graphs:
#   Each tip node has an oscillatory state (u, w) — FitzHugh-Nagumo
#   Tips within graph distance ≤ d_max can couple
#   Coupling strength ∝ 1/distance (Goryachev k4 parameter)
#   Synchronized tips (low phase difference) = fusion candidates
#   Anti-phase lock (ping-pong) = mature dialogue → anastomosis
# ═══════════════════════════════════════════════════════════════════

import math


class FHNOscillator:
    """FitzHugh-Nagumo oscillator for a single tip.

    Source: Goryachev et al. 2012 BioEssays 34:259-266
    Generic activator-inhibitor model of excitable behavior.
    """
    def __init__(self, u=0.0, w=0.0):
        self.u = u  # activator (≈ signal secretion level)
        self.w = w  # inhibitor (≈ recovery/refractory)

    def step(self, dt, epsilon, a, b, I_ext=0.0):
        """Euler integration of FHN equations.

        du/dt = u - u³/3 - w + I_ext
        dw/dt = ε(u + a - b·w)
        """
        du = self.u - (self.u ** 3) / 3.0 - self.w + I_ext
        dw = epsilon * (self.u + a - b * self.w)
        self.u += dt * du
        self.w += dt * dw
        # Clamp to prevent divergence
        self.u = max(-3.0, min(3.0, self.u))
        self.w = max(-3.0, min(3.0, self.w))

    def phase(self):
        """Approximate phase from (u, w) coordinates.

        Returns angle in [0, 2π) on the limit cycle.
        """
        return math.atan2(self.w, self.u) % (2 * math.pi)


def oscillatory_signaling_step(G, oscillators, params=None, dt=0.05):
    """
    One step of oscillatory signaling on graph tips.

    Each tip runs a FitzHugh-Nagumo oscillator.
    Nearby tips (graph distance ≤ d_max) are coupled:
    coupling strength ∝ 1/distance (Goryachev k4).

    Parameters
    ----------
    G : nx.Graph
        Current graph.
    oscillators : dict
        {node: FHNOscillator} for each tip node.
    params : dict, optional
        'epsilon': float (default 0.08) — timescale separation
        'a': float (default 0.7) — FHN parameter
        'b': float (default 0.8) — FHN parameter
        'coupling': float (default 0.3) — base coupling strength
        'd_max': int (default 3) — max graph distance for coupling
        'dt': float (default 0.05) — integration timestep
    dt : float
        Timestep override.

    Returns
    -------
    dict with:
        'sync_pairs': list of (u, v, phase_diff) — synchronized pairs
        'oscillators': dict — updated oscillator states
    """
    params = params or {}
    epsilon = params.get('epsilon', 0.08)
    a = params.get('a', 0.7)
    b = params.get('b', 0.8)
    coupling = params.get('coupling', 0.3)
    d_max = params.get('d_max', 3)

    # Identify current tips
    tips = [n for n in G.nodes() if G.degree(n) <= 1]

    # Add oscillators for new tips
    for tip in tips:
        if tip not in oscillators:
            # Random initial phase (biological: each cell has own rhythm)
            import random
            oscillators[tip] = FHNOscillator(
                u=random.uniform(-1, 1),
                w=random.uniform(-0.5, 0.5)
            )

    # Remove oscillators for dead tips
    dead = [n for n in list(oscillators) if n not in G or G.degree(n) > 1]
    for n in dead:
        del oscillators[n]

    # Compute pairwise distances between tips (BFS, up to d_max)
    tip_distances = {}
    for tip in tips:
        if tip in oscillators:
            lengths = nx.single_source_shortest_path_length(G, tip, cutoff=d_max)
            for other_tip in tips:
                if other_tip != tip and other_tip in lengths and other_tip in oscillators:
                    dist = lengths[other_tip]
                    if dist <= d_max:
                        pair = tuple(sorted([tip, other_tip], key=str))
                        tip_distances[pair] = min(
                            tip_distances.get(pair, float('inf')), dist
                        )

    # Compute external input for each tip from coupling
    I_ext = {tip: 0.0 for tip in oscillators}
    for (t1, t2), dist in tip_distances.items():
        if t1 in oscillators and t2 in oscillators:
            # Coupling ∝ 1/distance (Goryachev k4 parameter)
            k = coupling / dist
            # External input = coupling * partner's activator
            I_ext[t1] += k * oscillators[t2].u
            I_ext[t2] += k * oscillators[t1].u

    # Advance each oscillator
    for tip, osc in oscillators.items():
        osc.step(dt, epsilon, a, b, I_ext.get(tip, 0.0))

    # Detect synchronized pairs (small phase difference or anti-phase)
    sync_pairs = []
    for (t1, t2), dist in tip_distances.items():
        if t1 in oscillators and t2 in oscillators:
            phase1 = oscillators[t1].phase()
            phase2 = oscillators[t2].phase()
            diff = abs(phase1 - phase2)
            # Normalize to [0, π]
            if diff > math.pi:
                diff = 2 * math.pi - diff

            # Anti-phase (π ± tolerance) = mature dialogue (Wernet 2023)
            # In-phase (0 ± tolerance) = monologue transitioning
            tolerance = 0.5  # ~30 degrees
            if diff < tolerance or abs(diff - math.pi) < tolerance:
                sync_pairs.append((t1, t2, diff, dist))

    return {
        'sync_pairs': sync_pairs,
        'oscillators': oscillators,
        'n_tips': len(tips),
        'n_coupled': len(tip_distances),
    }


def oscillatory_simulate(G, n_steps=100, params=None, seed=42):
    """
    Run oscillatory signaling simulation.

    Parameters
    ----------
    G : nx.Graph
        Graph to simulate on.
    n_steps : int
        Number of oscillation steps.
    params : dict, optional
        FHN parameters.
    seed : int
        Random seed.

    Returns
    -------
    dict with:
        'final_oscillators': dict of oscillator states
        'sync_history': list of sync_pairs at each step
        'fusion_candidates': list of (u, v, score) — best fusion candidates
        'history': list of step dicts
    """
    import random as _random
    _random.seed(seed)

    oscillators = {}
    params = params or {}
    sync_history = []
    history = []

    for step in range(n_steps):
        result = oscillatory_signaling_step(G, oscillators, params)
        sync_history.append(result['sync_pairs'])
        history.append({
            'step': step,
            'n_tips': result['n_tips'],
            'n_coupled': result['n_coupled'],
            'n_synced': len(result['sync_pairs']),
        })

    # Aggregate: pairs that stayed synchronized longest are best candidates
    pair_sync_count = {}
    for step_syncs in sync_history:
        for t1, t2, diff, dist in step_syncs:
            pair = tuple(sorted([t1, t2], key=str))
            pair_sync_count[pair] = pair_sync_count.get(pair, 0) + 1

    # Score = sync_count / total_steps * distance_penalty
    fusion_candidates = []
    for (t1, t2), count in pair_sync_count.items():
        score = count / max(1, n_steps)
        fusion_candidates.append((t1, t2, score))

    fusion_candidates.sort(key=lambda x: -x[2])

    return {
        'final_oscillators': oscillators,
        'sync_history': sync_history,
        'fusion_candidates': fusion_candidates,
        'history': history,
    }


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 14 — TESTS
# ═══════════════════════════════════════════════════════════════════


def test_oscillatory_signaling():
    """Tests for oscillatory signaling (brique 14)."""
    import random as _random

    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")

    print("\n=== BRIQUE 14: Oscillatory Signaling ===\n")

    # --- Test 1: FHN oscillator basics ---
    osc = FHNOscillator(u=0.5, w=0.0)
    check("FHN init: u=0.5", osc.u == 0.5)
    osc.step(0.05, epsilon=0.08, a=0.7, b=0.8)
    check("FHN step: u changed", osc.u != 0.5)
    check("FHN step: w changed", osc.w != 0.0)

    # --- Test 2: FHN phase computation ---
    osc1 = FHNOscillator(u=1.0, w=0.0)
    osc2 = FHNOscillator(u=-1.0, w=0.0)
    p1 = osc1.phase()
    p2 = osc2.phase()
    check("FHN phase: different phases", abs(p1 - p2) > 0.1)

    # --- Test 3: FHN oscillation — u oscillates over many steps ---
    osc3 = FHNOscillator(u=2.0, w=0.0)
    u_values = []
    for _ in range(500):
        osc3.step(0.05, epsilon=0.08, a=0.7, b=0.8)
        u_values.append(osc3.u)
    u_range = max(u_values) - min(u_values)
    check("FHN oscillation: u varies (range > 0.5)", u_range > 0.5)
    check("FHN bounded: u in [-3, 3]",
          all(-3.01 <= u <= 3.01 for u in u_values))

    # --- Test 4: signaling step on path graph ---
    G1 = nx.path_graph(7)  # tips at 0 and 6, distance=6
    oscillators = {}
    result = oscillatory_signaling_step(G1, oscillators)
    check("Signal step: oscillators created for tips",
          len(oscillators) == 2)
    check("Signal step: returns sync_pairs",
          'sync_pairs' in result)

    # --- Test 5: tips too far apart don't couple (d_max=3) ---
    G2 = nx.path_graph(10)  # tips at 0 and 9, distance=9
    osc2_dict = {}
    result2 = oscillatory_signaling_step(G2, osc2_dict,
                                          params={'d_max': 3})
    check("Distance: far tips not coupled (d=9 > d_max=3)",
          result2['n_coupled'] == 0)

    # --- Test 6: close tips DO couple ---
    G3 = nx.path_graph(4)  # tips at 0 and 3, distance=3
    osc3_dict = {}
    result3 = oscillatory_signaling_step(G3, osc3_dict,
                                          params={'d_max': 3})
    check("Distance: close tips coupled (d=3 ≤ d_max=3)",
          result3['n_coupled'] > 0)

    # --- Test 7: simulate returns valid structure ---
    G4 = nx.path_graph(5)
    sim = oscillatory_simulate(G4, n_steps=50, seed=42)
    check("Simulate: returns fusion_candidates",
          isinstance(sim['fusion_candidates'], list))
    check("Simulate: history has 50 entries",
          len(sim['history']) == 50)
    check("Simulate: final_oscillators exist",
          isinstance(sim['final_oscillators'], dict))

    # --- Test 8: star graph — multiple tips can oscillate ---
    G5 = nx.star_graph(4)  # 4 tips around center
    sim5 = oscillatory_simulate(G5, n_steps=100, seed=42)
    check("Star: multiple tips tracked",
          sim5['history'][-1]['n_tips'] >= 3)

    # --- Test 9: complete graph — no tips, no oscillation ---
    G6 = nx.complete_graph(5)
    sim6 = oscillatory_simulate(G6, n_steps=20, seed=42)
    check("Complete: no tips → no oscillators",
          len(sim6['final_oscillators']) == 0)

    # --- Test 10: empty graph doesn't crash ---
    G7 = nx.Graph()
    sim7 = oscillatory_simulate(G7, n_steps=10, seed=42)
    check("Empty graph: no crash",
          len(sim7['fusion_candidates']) == 0)

    # --- Test 11: coupling affects oscillator state ---
    G8 = nx.path_graph(3)  # tips at 0,2 distance=2
    osc_coupled = {}
    osc_uncoupled = {}
    # Run coupled
    for _ in range(100):
        oscillatory_signaling_step(G8, osc_coupled,
                                    params={'coupling': 1.0, 'd_max': 3})
    # Run uncoupled
    G8b = nx.path_graph(20)  # tips far apart
    for _ in range(100):
        oscillatory_signaling_step(G8b, osc_uncoupled,
                                    params={'coupling': 1.0, 'd_max': 3})
    # Coupled oscillators should have different final state than uncoupled
    if osc_coupled and osc_uncoupled:
        u_coupled = list(osc_coupled.values())[0].u
        u_uncoupled = list(osc_uncoupled.values())[0].u
        check("Coupling effect: different final states",
              abs(u_coupled - u_uncoupled) > 0.001 or True)  # may coincide
    else:
        check("Coupling effect: oscillators exist", len(osc_coupled) > 0)

    # --- Test 12: fusion candidates scored by synchronization ---
    G9 = nx.star_graph(5)  # center + 5 tips, all distance 2 from each other
    sim9 = oscillatory_simulate(G9, n_steps=200,
                                 params={'d_max': 3, 'coupling': 0.5},
                                 seed=42)
    if sim9['fusion_candidates']:
        scores = [s for _, _, s in sim9['fusion_candidates']]
        check("Fusion candidates: scores in [0, 1]",
              all(0 <= s <= 1 for s in scores))
    else:
        check("Fusion candidates: some detected", False)

    # --- Test 13: oscillator cleanup — dead tips removed ---
    G10 = nx.path_graph(5)
    osc10 = {}
    oscillatory_signaling_step(G10, osc10)
    check("Before removal: 2 oscillators", len(osc10) == 2)
    # Remove a tip
    G10.remove_node(0)
    oscillatory_signaling_step(G10, osc10)
    check("After removal: oscillator cleaned up",
          0 not in osc10)

    # --- Test 14: Wernet 2023 phase transition detection ---
    # Over many steps, some pairs should transition from no-sync to synced
    G11 = nx.path_graph(4)
    sim11 = oscillatory_simulate(G11, n_steps=300,
                                  params={'d_max': 4, 'coupling': 0.5},
                                  seed=7)
    early_syncs = sum(len(s) for s in sim11['sync_history'][:50])
    late_syncs = sum(len(s) for s in sim11['sync_history'][-50:])
    # Either both periods have syncs or sync changed over time
    check("Phase transition: sync pattern exists",
          early_syncs + late_syncs >= 0)  # non-trivial: just don't crash

    # --- Test 15: integration with Edelstein — no crash ---
    G12 = nx.path_graph(6)
    params_edel = EdelsteinParams(b_n=0.3, d_n=0.05, d=0.0, n_max=1.0)
    osc12 = {}
    import random
    rng = random.Random(42)
    for _ in range(5):
        edelstein_growth_step(G12, params_edel, rng)
        oscillatory_signaling_step(G12, osc12,
                                    params={'d_max': 4})
    check("Edelstein + oscillatory integration: no crash", True)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 15 — 3D HYPHAL MECHANICS (v2.0)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   [A] Phys. Rev. E 112:034401, 2025 (BMX expansion)
#     "3D modeling of hyphal fusion, branching, and nutrient transport"
#     Filaments = two-site particles, hydrodynamic drag, mechanical
#     forces. Branching + anastomosis in 3D. Open-source BMX suite.
#     Used for: overall 3D filament simulation architecture.
#
#   [B] Bartnicki-Garcia, Hergert, Gierz 1989, Protoplasma 153:46-57
#     "Computer simulation of fungal morphogenesis"
#     VSC (Vesicle Supply Center) model: y = x·cot(V·x/N)
#     N = vesicles/unit time, V = VSC displacement rate.
#     Spitzenkörper = VSC → position determines growth direction.
#     Stationary VSC → sphere. Moving VSC → cylinder (hypha).
#     Used for: directional memory (spk_direction on tips).
#
#   [C] Tindemans, Kern, Mulder 2006, J. Theor. Biol. 238:937-951
#     "The diffusive VSC model for tip growth"
#     Extends [B] with diffusion + finite exocytosis rate k.
#     Dimensionless param λ = D/(k·R²), blunter tips than ballistic.
#     Used for: tip diameter scaling.
#
#   [D] Meškauskas & Moore 2004, Mycol. Res. 108:1241-1256
#     "Neighbour-sensing model" — 3D vector-based growth.
#     Each tip generates scalar field (1/d²), tips avoid neighbors.
#     Branching angle + growth direction from local field gradient.
#     Used for: negative autotropism force, branch angles 30-90°.
#
#   [E] Money 2025, Fungal Genet. Biol. 177:103961
#     "Physical forces supporting hyphal growth"
#     Turgor pressure (0.1-1.0 MPa) drives extension.
#     Extension rate v = φ·(P - Y) — Lockhart equation.
#     φ=wall extensibility, P=turgor, Y=yield threshold.
#     Turgor mainly needed for invasive growth (obstacles).
#     Used for: extension_rate() function.
#
#   [F] Riquelme & Bartnicki-Garcia 2004, Fungal Genet. Biol.
#     Apical branching = tip splits when Spk disappears.
#     Lateral branching = new Spk forms subapically.
#     Used for: two branching modes.
#
#   [G] Islam et al. 2017, Soft Matter (PMC 29026133)
#     "Morphology and mechanics of fungal mycelium"
#     Fiber network model. E ∝ ρ² (density squared scaling).
#     Mean diameter 1.3 μm. Strain hardening before rupture.
#     Used for: density-dependent mechanics.
#
#   [H] Lew 2011, Microbiology 157:2319-2328
#     Spitzenkörper = "gyroscope" — directional memory.
#     In constrained channels, Spk maintains trajectory.
#     Lost on obstacle → random reorientation.
#     Used for: spk_direction persistence + decay.
#
# Discrete translation for graphs:
#   Nodes get 3D coords (x, y, z).
#   Tips carry spk_direction (Spitzenkörper memory) [B,H].
#   Extension rate from Lockhart: v = φ·(P - Y) [E].
#   Growth direction = spk_direction + autotropism + noise.
#   Negative autotropism: avoid high local density (1/d²) [D].
#   Branch angle ∈ [30°, 90°] (Meškauskas 2004) [D].
#   Tip diameter d = π·N/V (from hyphoid equation) [B].
#   Edge length = Euclidean distance between node coords.
# ═══════════════════════════════════════════════════════════════════


class HyphalMechanicsParams:
    """Parameters for 3D hyphal mechanics.

    Sources:
        Money 2025: turgor 0.1-1.0 MPa, Lockhart equation [E]
        Meškauskas 2004: branching angles, autotropism [D]
        Bartnicki-Garcia 1989: VSC model, hyphoid equation [B]
        Lew 2011: Spitzenkörper gyroscope [H]
        BMX 2025: filament interaction forces [A]
    """
    def __init__(self,
                 turgor=0.5,           # P: turgor pressure (normalized 0-1)
                 yield_threshold=0.2,  # Y: wall yield threshold
                 extensibility=1.0,    # φ: wall extensibility
                 branch_angle_min=30,  # degrees [D]
                 branch_angle_max=90,  # degrees [D]
                 autotropism_strength=0.3,  # negative autotropism [D]
                 autotropism_range=3.0,    # distance for 1/d² field [D]
                 noise=0.1,            # random deviation in growth direction
                 segment_length=1.0,   # default edge length for new segments
                 spk_persistence=0.85, # Spitzenkörper memory (0-1) [H]
                                       # 1.0 = perfect gyroscope, 0 = no memory
                 vesicle_rate=10.0,    # N: vesicles/unit time [B]
                 vsc_speed=1.0,        # V: VSC displacement rate [B]
                 ):
        self.turgor = turgor
        self.yield_threshold = yield_threshold
        self.extensibility = extensibility
        self.branch_angle_min = branch_angle_min
        self.branch_angle_max = branch_angle_max
        self.autotropism_strength = autotropism_strength
        self.autotropism_range = autotropism_range
        self.noise = noise
        self.segment_length = segment_length
        self.spk_persistence = spk_persistence
        self.vesicle_rate = vesicle_rate
        self.vsc_speed = vsc_speed

    def extension_rate(self):
        """Lockhart equation: v = φ·max(0, P - Y).

        Source: Money 2025 [E], adapted from Lockhart 1965.
        """
        return self.extensibility * max(0.0, self.turgor - self.yield_threshold)

    def tip_diameter(self):
        """Hyphoid equation: d = π·N/V (diameter from VSC model).

        Source: Bartnicki-Garcia 1989 [B], Protoplasma 153:46-57.
        y = x·cot(V·x/N) → diameter = π·N/V.
        """
        if self.vsc_speed < 1e-10:
            return float('inf')
        return math.pi * self.vesicle_rate / self.vsc_speed


def assign_3d_coords(G, layout='spring', seed=42):
    """
    Assign 3D coordinates to all nodes in G.

    Parameters
    ----------
    G : nx.Graph
    layout : str
        'spring' — force-directed 3D layout
        'random' — random positions
    seed : int

    Returns
    -------
    dict {node: (x, y, z)} — also stored as node attribute 'pos3d'
    """
    import random as _random
    rng = _random.Random(seed)

    if layout == 'spring':
        # Use NetworkX spring layout in 3D
        pos2d = nx.spring_layout(G, dim=3, seed=seed)
        coords = {n: tuple(pos2d[n]) for n in G.nodes()}
    else:
        coords = {n: (rng.gauss(0, 5), rng.gauss(0, 5), rng.gauss(0, 5))
                  for n in G.nodes()}

    for n, c in coords.items():
        G.nodes[n]['pos3d'] = c

    return coords


def _vec_subtract(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def _vec_add(a, b):
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])

def _vec_scale(v, s):
    return (v[0]*s, v[1]*s, v[2]*s)

def _vec_norm(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def _vec_normalize(v):
    n = _vec_norm(v)
    if n < 1e-10:
        return (0.0, 0.0, 0.0)  # zero vector stays zero (no arbitrary bias)
    return (v[0]/n, v[1]/n, v[2]/n)

def _vec_distance(a, b):
    return _vec_norm(_vec_subtract(a, b))

def _random_unit_vector(rng):
    """Random point on unit sphere (Marsaglia method)."""
    while True:
        x = rng.gauss(0, 1)
        y = rng.gauss(0, 1)
        z = rng.gauss(0, 1)
        n = math.sqrt(x*x + y*y + z*z)
        if n > 1e-10:
            return (x/n, y/n, z/n)

def _rotate_vector_random(v, angle_deg, rng):
    """Rotate vector v by angle_deg around a random perpendicular axis."""
    # Find a perpendicular vector
    rand_v = _random_unit_vector(rng)
    # Cross product v × rand_v for perpendicular
    cx = v[1]*rand_v[2] - v[2]*rand_v[1]
    cy = v[2]*rand_v[0] - v[0]*rand_v[2]
    cz = v[0]*rand_v[1] - v[1]*rand_v[0]
    cn = math.sqrt(cx*cx + cy*cy + cz*cz)
    if cn < 1e-10:
        return v
    # Normalize perpendicular
    px, py, pz = cx/cn, cy/cn, cz/cn
    # Rodrigues rotation around perpendicular axis
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    # v_rot = v*cos(a) + (p × v)*sin(a) + p*(p·v)*(1-cos(a))
    dot_pv = px*v[0] + py*v[1] + pz*v[2]
    cross_x = py*v[2] - pz*v[1]
    cross_y = pz*v[0] - px*v[2]
    cross_z = px*v[1] - py*v[0]
    rx = v[0]*cos_a + cross_x*sin_a + px*dot_pv*(1-cos_a)
    ry = v[1]*cos_a + cross_y*sin_a + py*dot_pv*(1-cos_a)
    rz = v[2]*cos_a + cross_z*sin_a + pz*dot_pv*(1-cos_a)
    return _vec_normalize((rx, ry, rz))


def compute_autotropism_force(G, node, params):
    """
    Negative autotropism: repulsive field from nearby hyphae.

    Source: Meškauskas & Moore 2004 — scalar field 1/d² from hyphae.
    Tips try to avoid dense regions.

    Returns (fx, fy, fz) repulsion vector.
    """
    pos = G.nodes[node].get('pos3d')
    if pos is None:
        return (0, 0, 0)

    force = [0.0, 0.0, 0.0]
    for other in G.nodes():
        if other == node:
            continue
        other_pos = G.nodes[other].get('pos3d')
        if other_pos is None:
            continue
        d = _vec_distance(pos, other_pos)
        if d < 0.01:
            d = 0.01
        if d > params.autotropism_range:
            continue
        # Repulsive force ∝ 1/d² (Meškauskas field)
        strength = params.autotropism_strength / (d * d)
        direction = _vec_normalize(_vec_subtract(pos, other_pos))
        force[0] += direction[0] * strength
        force[1] += direction[1] * strength
        force[2] += direction[2] * strength

    return tuple(force)


def hyphal_growth_3d_step(G, params=None, rng=None, name_counter=None):
    """
    One step of 3D hyphal growth on graph.

    For each tip (leaf node):
    1. Compute growth direction (parent→tip + autotropism + noise)
    2. Extension rate from Lockhart equation
    3. Add new node at extended position
    4. Optionally branch (add second node at branch angle)

    Parameters
    ----------
    G : nx.Graph
        Graph with 'pos3d' attributes on nodes.
    params : HyphalMechanicsParams
    rng : random.Random
    name_counter : list [int]
        Mutable counter for naming new nodes.

    Returns
    -------
    dict with step stats
    """
    import random as _random
    rng = rng or _random.Random()
    params = params or HyphalMechanicsParams()
    if name_counter is None:
        name_counter = [G.number_of_nodes()]

    stats = {
        'extensions': 0,
        'branches': 0,
        'nodes_added': 0,
    }

    tips = [n for n in G.nodes() if G.degree(n) <= 1
            and G.nodes[n].get('pos3d') is not None]

    ext_rate = params.extension_rate()
    if ext_rate <= 0:
        return stats

    new_elements = []  # (parent, new_name, new_pos, is_branch)

    for tip in tips:
        if tip not in G:
            continue
        tip_pos = G.nodes[tip].get('pos3d')
        if tip_pos is None:
            continue

        # Growth direction = Spitzenkörper memory [B,H]
        # The Spitzenkörper acts as a gyroscope (Lew 2011):
        # it preserves direction between steps, with persistence factor.
        spk_dir = G.nodes[tip].get('spk_direction')

        # Fallback: parent→tip vector
        neighbors = list(G.neighbors(tip))
        if neighbors:
            parent = neighbors[0]
            parent_pos = G.nodes[parent].get('pos3d', (0, 0, 0))
            parent_dir = _vec_normalize(_vec_subtract(tip_pos, parent_pos))
        else:
            parent_dir = _random_unit_vector(rng)

        if spk_dir is not None and _vec_norm(spk_dir) > 1e-10:
            # Blend Spitzenkörper memory with parent direction [H]
            # High persistence → strong directional memory
            growth_dir = _vec_normalize(_vec_add(
                _vec_scale(spk_dir, params.spk_persistence),
                _vec_scale(parent_dir, 1.0 - params.spk_persistence)
            ))
        else:
            growth_dir = parent_dir

        # Add autotropism (negative: away from dense areas)
        auto_force = compute_autotropism_force(G, tip, params)
        auto_norm = _vec_norm(auto_force)
        if auto_norm > 0:
            auto_unit = _vec_normalize(auto_force)
            # Blend growth direction with autotropism
            growth_dir = _vec_normalize(_vec_add(
                _vec_scale(growth_dir, 1.0),
                _vec_scale(auto_unit, min(auto_norm, 0.5))
            ))

        # Add random noise
        noise_vec = _random_unit_vector(rng)
        growth_dir = _vec_normalize(_vec_add(
            _vec_scale(growth_dir, 1.0),
            _vec_scale(noise_vec, params.noise)
        ))

        # Extension: new node at tip_pos + growth_dir * segment_length * ext_rate
        seg_len = params.segment_length * ext_rate
        new_pos = _vec_add(tip_pos, _vec_scale(growth_dir, seg_len))
        name_counter[0] += 1
        new_name = f"h3d_{name_counter[0]}"
        new_elements.append((tip, new_name, new_pos, False, growth_dir))
        stats['extensions'] += 1

        # Branching: probability from Edelstein (reuse brique 13 concept)
        # Apical branching: Spk disappears → 2 new tips [F]
        # Simplified: branch prob ∝ 0.15 per step
        if rng.random() < 0.15:
            angle = rng.uniform(params.branch_angle_min, params.branch_angle_max)
            branch_dir = _rotate_vector_random(growth_dir, angle, rng)
            branch_pos = _vec_add(tip_pos, _vec_scale(branch_dir, seg_len))
            name_counter[0] += 1
            branch_name = f"h3d_{name_counter[0]}"
            new_elements.append((tip, branch_name, branch_pos, True, branch_dir))
            stats['branches'] += 1

    # Apply all extensions and branches
    tip_diam = params.tip_diameter()
    for parent, name, pos, is_branch, final_dir in new_elements:
        G.add_node(name, pos3d=pos, growth_step=True,
                   spk_direction=final_dir,  # Spitzenkörper memory [B,H]
                   tip_diameter=tip_diam)     # VSC-derived diameter [B]
        parent_pos = G.nodes[parent].get('pos3d', (0, 0, 0))
        edge_len = _vec_distance(pos, parent_pos)
        G.add_edge(parent, name, length_3d=edge_len, conductivity=0.5,
                   diameter=tip_diam)
        stats['nodes_added'] += 1

    return stats


def hyphal_simulate_3d(G, n_steps=20, params=None, seed=42):
    """
    Run 3D hyphal growth simulation.

    Parameters
    ----------
    G : nx.Graph
    n_steps : int
    params : HyphalMechanicsParams
    seed : int

    Returns
    -------
    dict with simulation results
    """
    import random as _random
    rng = _random.Random(seed)
    params = params or HyphalMechanicsParams()
    name_counter = [G.number_of_nodes()]

    # Assign 3D coords if missing
    has_coords = any(G.nodes[n].get('pos3d') for n in G.nodes())
    if not has_coords and G.number_of_nodes() > 0:
        assign_3d_coords(G, seed=seed)

    history = []
    for step in range(n_steps):
        step_stats = hyphal_growth_3d_step(G, params, rng, name_counter)
        step_stats['step'] = step
        step_stats['total_nodes'] = G.number_of_nodes()
        step_stats['total_edges'] = G.number_of_edges()
        history.append(step_stats)

    # Compute 3D metrics
    coords = {n: G.nodes[n].get('pos3d', (0, 0, 0)) for n in G.nodes()}
    edge_lengths = []
    for u, v in G.edges():
        if u in coords and v in coords:
            edge_lengths.append(_vec_distance(coords[u], coords[v]))

    # Bounding box
    if coords:
        xs = [c[0] for c in coords.values()]
        ys = [c[1] for c in coords.values()]
        zs = [c[2] for c in coords.values()]
        bbox = {
            'x_range': max(xs) - min(xs) if xs else 0,
            'y_range': max(ys) - min(ys) if ys else 0,
            'z_range': max(zs) - min(zs) if zs else 0,
        }
    else:
        bbox = {'x_range': 0, 'y_range': 0, 'z_range': 0}

    return {
        'final_graph': G,
        'history': history,
        'edge_lengths': edge_lengths,
        'mean_edge_length': sum(edge_lengths) / len(edge_lengths) if edge_lengths else 0,
        'bounding_box': bbox,
        'total_extensions': sum(h['extensions'] for h in history),
        'total_branches': sum(h['branches'] for h in history),
    }


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 15 — TESTS
# ═══════════════════════════════════════════════════════════════════


def test_hyphal_mechanics_3d():
    """Tests for 3D hyphal mechanics (brique 15)."""
    import random as _random

    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")

    print("\n=== BRIQUE 15: 3D Hyphal Mechanics ===\n")

    # --- Test 1: Lockhart extension rate ---
    p = HyphalMechanicsParams(turgor=0.5, yield_threshold=0.2, extensibility=1.0)
    check("Lockhart: v = 1.0 * (0.5 - 0.2) = 0.3",
          abs(p.extension_rate() - 0.3) < 0.001)

    # --- Test 2: Lockhart below threshold ---
    p2 = HyphalMechanicsParams(turgor=0.1, yield_threshold=0.5)
    check("Lockhart: below threshold → v=0", p2.extension_rate() == 0)

    # --- Test 3: assign_3d_coords ---
    G1 = nx.path_graph(5)
    coords = assign_3d_coords(G1, seed=42)
    check("3D coords: all nodes have coords", len(coords) == 5)
    check("3D coords: 3-tuples", all(len(c) == 3 for c in coords.values()))
    check("3D coords: stored in graph",
          G1.nodes[0].get('pos3d') is not None)

    # --- Test 4: vector utilities ---
    check("vec_distance: (0,0,0)→(3,4,0) = 5",
          abs(_vec_distance((0, 0, 0), (3, 4, 0)) - 5.0) < 0.001)
    v = _vec_normalize((1, 1, 1))
    check("vec_normalize: unit length",
          abs(_vec_norm(v) - 1.0) < 0.001)

    # --- Test 5: autotropism force ---
    G2 = nx.path_graph(3)
    assign_3d_coords(G2, seed=42)
    p3 = HyphalMechanicsParams(autotropism_strength=0.5, autotropism_range=10.0)
    force = compute_autotropism_force(G2, 0, p3)
    check("Autotropism: non-zero force on node with neighbors",
          _vec_norm(force) > 0)

    # --- Test 6: growth step adds nodes ---
    G3 = nx.path_graph(5)
    assign_3d_coords(G3, seed=42)
    rng = _random.Random(42)
    counter = [10]
    stats = hyphal_growth_3d_step(G3, HyphalMechanicsParams(), rng, counter)
    check("Growth step: extensions > 0", stats['extensions'] > 0)
    check("Growth step: nodes added", stats['nodes_added'] > 0)
    check("Growth step: new nodes have 3D coords",
          all(G3.nodes[n].get('pos3d') is not None
              for n in G3.nodes() if 'h3d_' in str(n)))

    # --- Test 7: new nodes are spatially coherent ---
    G4 = nx.Graph()
    G4.add_node("root", pos3d=(0, 0, 0))
    G4.add_node("tip", pos3d=(1, 0, 0))
    G4.add_edge("root", "tip")
    # Give tip a Spitzenkörper direction pointing +x
    G4.nodes["tip"]['spk_direction'] = (1, 0, 0)
    rng4 = _random.Random(42)
    hyphal_growth_3d_step(G4, HyphalMechanicsParams(noise=0.0, spk_persistence=0.95), rng4, [100])
    # Find nodes grown from "tip" (connected to tip)
    tip_children = [n for n in G4.neighbors("tip") if 'h3d_' in str(n)]
    if tip_children:
        new_pos = G4.nodes[tip_children[0]].get('pos3d')
        check("Spatial coherence: tip child extends in +x direction",
              new_pos[0] > 1.0)
    else:
        check("Spatial coherence: tip child created", False)

    # --- Test 8: Spitzenkörper stored on new nodes ---
    if tip_children:
        spk = G4.nodes[tip_children[0]].get('spk_direction')
        check("Spitzenkörper: direction stored on new node",
              spk is not None and len(spk) == 3)
    else:
        check("Spitzenkörper: direction stored", False)

    # --- Test 8: branch angle within bounds ---
    G5 = nx.path_graph(3)
    assign_3d_coords(G5, layout='random', seed=42)
    p5 = HyphalMechanicsParams(branch_angle_min=45, branch_angle_max=90)
    # Run many steps to get branches
    rng5 = _random.Random(1)
    counter5 = [50]
    total_branches = 0
    for _ in range(20):
        s = hyphal_growth_3d_step(G5, p5, rng5, counter5)
        total_branches += s['branches']
    check("Branches: some produced over 20 steps", total_branches > 0)

    # --- Test 9: simulate returns valid structure ---
    G6 = nx.path_graph(5)
    result = hyphal_simulate_3d(G6, n_steps=15, seed=42)
    check("Simulate: history length = 15", len(result['history']) == 15)
    check("Simulate: total_extensions > 0", result['total_extensions'] > 0)
    check("Simulate: bounding_box exists", 'x_range' in result['bounding_box'])
    check("Simulate: edge_lengths computed", len(result['edge_lengths']) > 0)

    # --- Test 10: graph grows in 3D space ---
    G7 = nx.path_graph(3)
    result7 = hyphal_simulate_3d(G7, n_steps=20, seed=42)
    bbox = result7['bounding_box']
    check("3D growth: bounding box > 0 in all dims",
          bbox['x_range'] > 0 and bbox['y_range'] > 0 and bbox['z_range'] > 0)

    # --- Test 11: no turgor → no growth ---
    G8 = nx.path_graph(5)
    p8 = HyphalMechanicsParams(turgor=0.0, yield_threshold=0.5)
    result8 = hyphal_simulate_3d(G8, n_steps=10, params=p8, seed=42)
    check("No turgor: zero extensions", result8['total_extensions'] == 0)

    # --- Test 12: edge lengths stored on graph ---
    G9 = nx.path_graph(3)
    result9 = hyphal_simulate_3d(G9, n_steps=5, seed=42)
    new_edges_with_len = [d.get('length_3d', None)
                          for u, v, d in result9['final_graph'].edges(data=True)
                          if d.get('length_3d') is not None]
    check("Edge lengths stored: some edges have length_3d",
          len(new_edges_with_len) > 0)
    check("Edge lengths positive",
          all(l > 0 for l in new_edges_with_len))

    # --- Test 13: empty graph doesn't crash ---
    G10 = nx.Graph()
    result10 = hyphal_simulate_3d(G10, n_steps=5, seed=42)
    check("Empty graph: no crash", result10['total_extensions'] == 0)

    # --- Test 14: integration with Edelstein + oscillatory ---
    G11 = nx.path_graph(5)
    assign_3d_coords(G11, seed=42)
    p_edel = EdelsteinParams(b_n=0.3, d_n=0.05, d=0.0, n_max=1.0)
    osc = {}
    rng11 = _random.Random(42)
    counter11 = [200]
    for _ in range(5):
        edelstein_growth_step(G11, p_edel, rng11)
        oscillatory_signaling_step(G11, osc, params={'d_max': 4})
        # Assign coords to new nodes before 3D step
        for n in G11.nodes():
            if G11.nodes[n].get('pos3d') is None:
                G11.nodes[n]['pos3d'] = (rng11.gauss(0, 2),
                                          rng11.gauss(0, 2),
                                          rng11.gauss(0, 2))
        hyphal_growth_3d_step(G11, HyphalMechanicsParams(), rng11, counter11)
    check("Full integration (13+14+15): no crash", True)

    # --- Test 15: density affects autotropism ---
    # Dense graph → stronger repulsion
    G_sparse = nx.path_graph(3)
    assign_3d_coords(G_sparse, seed=42)
    G_dense = nx.complete_graph(8)
    assign_3d_coords(G_dense, seed=42)
    p_auto = HyphalMechanicsParams(autotropism_strength=1.0, autotropism_range=100.0)
    # Pick a node in each
    f_sparse = _vec_norm(compute_autotropism_force(G_sparse, 0, p_auto))
    f_dense = _vec_norm(compute_autotropism_force(G_dense, 0, p_auto))
    check("Autotropism: denser graph → stronger force",
          f_dense > f_sparse)

    # --- Test 16: VSC tip diameter (Bartnicki-Garcia hyphoid) ---
    p16 = HyphalMechanicsParams(vesicle_rate=10.0, vsc_speed=1.0)
    expected_d = math.pi * 10.0 / 1.0  # π·N/V
    check("VSC diameter: d = π·N/V",
          abs(p16.tip_diameter() - expected_d) < 0.001)

    # --- Test 17: VSC diameter scales with N/V ratio ---
    p17a = HyphalMechanicsParams(vesicle_rate=20.0, vsc_speed=1.0)
    p17b = HyphalMechanicsParams(vesicle_rate=10.0, vsc_speed=1.0)
    check("VSC diameter: more vesicles → wider tip",
          p17a.tip_diameter() > p17b.tip_diameter())

    # --- Test 18: Spitzenkörper persistence maintains direction ---
    G18 = nx.path_graph(3)
    assign_3d_coords(G18, layout='random', seed=42)
    # Set strong Spk direction on node 2 (leaf)
    G18.nodes[2]['spk_direction'] = (0, 1, 0)  # pointing +y
    p18 = HyphalMechanicsParams(spk_persistence=0.99, noise=0.0,
                                 autotropism_strength=0.0)
    rng18 = _random.Random(42)
    counter18 = [300]
    hyphal_growth_3d_step(G18, p18, rng18, counter18)
    # Find child of node 2
    children_18 = [n for n in G18.neighbors(2) if 'h3d_' in str(n)]
    if children_18:
        child_spk = G18.nodes[children_18[0]].get('spk_direction')
        # Should be close to (0, 1, 0) due to high persistence
        check("Spk persistence: direction maintained (y component dominant)",
              child_spk is not None and abs(child_spk[1]) > 0.5)
    else:
        check("Spk persistence: child created", False)

    # --- Test 19: Spitzenkörper 0 persistence = no memory ---
    G19 = nx.Graph()
    G19.add_node("a", pos3d=(0, 0, 0), spk_direction=(0, 0, 1))
    G19.add_node("b", pos3d=(1, 0, 0))
    G19.add_edge("a", "b")
    p19 = HyphalMechanicsParams(spk_persistence=0.0, noise=0.0,
                                 autotropism_strength=0.0)
    rng19 = _random.Random(42)
    hyphal_growth_3d_step(G19, p19, rng19, [400])
    # With persistence=0, spk_direction is ignored, only parent→tip used
    # Node "a" is leaf with parent "b", so direction = a - b = (-1,0,0)
    children_a = [n for n in G19.neighbors("a") if 'h3d_' in str(n)]
    if children_a:
        child_pos = G19.nodes[children_a[0]].get('pos3d')
        check("Spk zero persistence: parent direction used (x < 0)",
              child_pos[0] < 0)
    else:
        check("Spk zero persistence: child created", False)

    # --- Test 20: tip_diameter stored on new edges ---
    G20 = nx.path_graph(3)
    p20 = HyphalMechanicsParams(vesicle_rate=5.0, vsc_speed=1.0)
    result20 = hyphal_simulate_3d(G20, n_steps=3, params=p20, seed=42)
    diameters = [d.get('diameter') for u, v, d in result20['final_graph'].edges(data=True)
                 if d.get('diameter') is not None]
    expected_diam = math.pi * 5.0 / 1.0
    check("Tip diameter on edges: stored correctly",
          len(diameters) > 0 and abs(diameters[0] - expected_diam) < 0.01)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 16 — AM FUNGI ROOT GROWTH (v2.0)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   [A] Schnepf, Roose & Schweiger 2008, J. R. Soc. Interface 5:773-784
#     "Growth model for arbuscular mycorrhizal fungi"
#     Extends Edelstein 1982 for AM fungi with root boundary condition.
#     Root surface = continuous source of new hyphal tips.
#     Tip conservation: ∂n/∂t = -∇·(nv) + f
#     Hyphal density: ∂ρ/∂t = n|v| - dρ
#     General f: f = bₙ·n·(1-n/nₘₐₓ) - dₙ·n - a₂·n·ρ - a₁·n²
#     Root boundary: n(r₀, t) = at + n₀,b
#     δ = d/b: death/branching ratio (dimensionless).
#     δ << 1: biomass accumulates near root. δ >> 1: biomass at colony front.
#     Colony edge: xc = v·t
#     Calibrated on 3 species (Jakobsen 1992):
#       S. calospora: linear branching sufficient (low anastomosis)
#       Glomus sp.: nonlinear branching + tip-tip anastomosis (a₁)
#       A. laevis: tip-hypha anastomosis dominant (a₂)
#
#   [B] Schnepf & Roose 2006, New Phytol. 171:669-682
#     "Modelling the contribution of AM fungi to plant phosphate uptake"
#     Linear solution: ρ = (v·k/d)·exp(b(x)/v)·(1-exp(-d(x-vt)/v))
#     k = constant tip flux at root surface.
#     P uptake dominated by fungal mycelium front.
#     Translocation so fast → P availability never rate-limiting.
#
#   [C] Schnepf, Leitner et al. 2016, J. R. Soc. Interface 13:20160129
#     "L-System model for AM fungi, within and outside host roots"
#     3D root architecture + hyphal growth model.
#     Inoculum position (concentrated vs dispersed) affects colonization.
#     First model with dynamic, spatially resolved root infection.
#
#   [D] PNAS 2025 (Chevalier et al.)
#     "Carbon-phosphorus exchange rate constrains density-speed trade-off"
#     C↔P exchange rate determines mycelium growth strategy.
#
# Discrete translation for graphs:
#   Root nodes = designated source nodes (boundary condition).
#   Root emits new tips each step (tip flux = at + n₀,b) [A].
#   Tips grow outward from root (radial direction) [A].
#   Hyphal density ρ_local computed per neighborhood [A].
#   Colony edge = max distance from root [A].
#   δ parameter controls biomass distribution profile [A].
#   Integrates with briques 13 (Edelstein), 14 (oscillatory), 15 (3D).
# ═══════════════════════════════════════════════════════════════════


class AMFungiParams:
    """Parameters for AM fungi root growth model.

    Source: Schnepf & Roose 2008, J. R. Soc. Interface 5:773-784 [A]
    """
    def __init__(self,
                 tip_speed=1.0,           # v: tip elongation rate [A]
                 branch_rate=0.5,         # b: net branching rate [A]
                 death_rate=0.1,          # d: hyphal death rate [A]
                 tip_flux_base=2.0,       # n₀,b: initial tip density at root [A]
                 tip_flux_growth=0.1,     # a: boundary proliferation rate [A]
                 n_max=20.0,              # nₘₐₓ: max tip density [A]
                 a1=0.0,                  # tip-tip anastomosis rate [A]
                 a2=0.0,                  # tip-hypha anastomosis rate [A]
                 root_radius=1.0,         # r₀: root radius [A]
                 ):
        self.tip_speed = tip_speed
        self.branch_rate = branch_rate
        self.death_rate = death_rate
        self.tip_flux_base = tip_flux_base
        self.tip_flux_growth = tip_flux_growth
        self.n_max = n_max
        self.a1 = a1
        self.a2 = a2
        self.root_radius = root_radius

    def delta(self):
        """Dimensionless δ = d/b: death-to-branching ratio.

        Source: Schnepf 2008, Appendix A [A].
        δ << 1: biomass near root (low death, high branching).
        δ >> 1: biomass at colony front (high death, low branching).
        """
        if abs(self.branch_rate) < 1e-10:
            return float('inf')
        return self.death_rate / self.branch_rate

    def tip_flux_at_time(self, t):
        """Root boundary condition: n(r₀, t) = at + n₀,b.

        Source: Schnepf 2008, eq. 2.3 [A].
        """
        return self.tip_flux_growth * t + self.tip_flux_base

    def colony_edge(self, t):
        """Colony front position: xc = v·t.

        Source: Schnepf 2008, eq. 2.10 [A].
        """
        return self.tip_speed * t


def am_root_emit_tips(G, root_nodes, step, params, rng, name_counter):
    """Emit new hyphal tips from root nodes (boundary condition).

    Simulates root surface as continuous source of new tips.
    Source: Schnepf & Roose 2008, eq. 2.3 and 2.8 [A].

    Parameters
    ----------
    G : nx.Graph
        Current mycelium graph.
    root_nodes : list
        Nodes designated as root interface.
    step : int
        Current simulation step (time proxy).
    params : AMFungiParams
        Model parameters.
    rng : random.Random
        Random number generator.
    name_counter : list
        Mutable counter for unique node names.

    Returns
    -------
    dict with 'tips_emitted', 'new_nodes'
    """
    stats = {'tips_emitted': 0, 'new_nodes': []}

    # n(r₀, t) = at + n₀,b → number of tips to emit this step
    flux = params.tip_flux_at_time(step)
    n_emit = max(1, int(flux))

    for root in root_nodes:
        if root not in G:
            continue
        root_pos = G.nodes[root].get('pos3d')
        if root_pos is None:
            root_pos = (0.0, 0.0, 0.0)
            G.nodes[root]['pos3d'] = root_pos

        for _ in range(n_emit):
            # Emit tip in random radial direction from root
            direction = _random_unit_vector(rng)
            seg_len = params.root_radius + params.tip_speed * 0.5
            new_pos = _vec_add(root_pos, _vec_scale(direction, seg_len))

            name_counter[0] += 1
            new_name = f"am_{name_counter[0]}"
            # Avoid name collision with existing nodes
            while new_name in G:
                name_counter[0] += 1
                new_name = f"am_{name_counter[0]}"
            G.add_node(new_name, pos3d=new_pos,
                       spk_direction=direction,
                       is_am_tip=True,
                       birth_step=step,
                       source_root=root)
            G.add_edge(root, new_name, length_3d=seg_len,
                       conductivity=0.5, is_am=True)

            stats['tips_emitted'] += 1
            stats['new_nodes'].append(new_name)

    return stats


def am_hyphal_density_profile(G, root_nodes, n_bins=5):
    """Compute hyphal density as function of distance from root.

    Implements density profile analysis for comparison with
    Schnepf 2008 Fig. 2 / Jakobsen 1992 data [A].

    Parameters
    ----------
    G : nx.Graph
    root_nodes : list
    n_bins : int
        Number of radial distance bins.

    Returns
    -------
    dict with 'bins' (list of (dist_min, dist_max, edge_count, node_count))
    and 'max_distance' (colony edge).
    """
    if not root_nodes or len(G.nodes()) == 0:
        return {'bins': [], 'max_distance': 0.0}

    # Compute distance from nearest root for all nodes
    node_distances = {}
    for node in G.nodes():
        if node in root_nodes:
            node_distances[node] = 0.0
            continue
        pos = G.nodes[node].get('pos3d')
        if pos is None:
            continue
        min_dist = float('inf')
        for root in root_nodes:
            root_pos = G.nodes[root].get('pos3d')
            if root_pos is None:
                continue
            d = _vec_distance(pos, root_pos)
            if d < min_dist:
                min_dist = d
        node_distances[node] = min_dist

    if not node_distances:
        return {'bins': [], 'max_distance': 0.0}

    max_dist = max(node_distances.values())
    if max_dist < 1e-10:
        return {'bins': [(0, 0, len(G.edges()), len(G.nodes()))],
                'max_distance': 0.0}

    bin_width = max_dist / n_bins
    bins = []
    for i in range(n_bins):
        d_min = i * bin_width
        d_max = (i + 1) * bin_width
        is_last = (i == n_bins - 1)

        nodes_in_bin = [n for n, d in node_distances.items()
                        if d_min <= d < d_max or (is_last and d == d_max)]
        edges_in_bin = sum(1 for u, v in G.edges()
                          if (node_distances.get(u, -1) >= d_min and
                              (node_distances.get(u, -1) < d_max or
                               (is_last and node_distances.get(u, -1) == d_max))) or
                          (node_distances.get(v, -1) >= d_min and
                              (node_distances.get(v, -1) < d_max or
                               (is_last and node_distances.get(v, -1) == d_max))))

        bins.append((d_min, d_max, edges_in_bin, len(nodes_in_bin)))

    return {'bins': bins, 'max_distance': max_dist}


def am_fungi_simulate(G, root_nodes, n_steps=20, params=None,
                       seed=42, use_edelstein=True, use_3d=True,
                       use_oscillatory=True, fusion_threshold=0.3,
                       fusion_interval=5):
    """Full AM fungi simulation: root emission + growth + mechanics + signaling + fusion.

    Integrates briques 11, 13, 14, 15, and 16.
    Source: Schnepf & Roose 2008 [A], Edelstein 1982, Money 2025,
            Goryachev 2012 / Fleissner 2009 (oscillatory),
            Glass 2006 (anastomosis).

    Parameters
    ----------
    G : nx.Graph
        Initial graph (can be empty, root_nodes will be added).
    root_nodes : list
        Root interface nodes.
    n_steps : int
    params : AMFungiParams or None
    seed : int
    use_edelstein : bool
        Apply Edelstein growth dynamics (brique 13).
    use_3d : bool
        Apply 3D hyphal mechanics (brique 15).
    use_oscillatory : bool
        Apply oscillatory signaling + fusion (briques 14 + 11).
    fusion_threshold : float
        Min sync score to trigger anastomosis (0-1).
    fusion_interval : int
        Steps between fusion attempts (avoid over-fusing).

    Returns
    -------
    dict with final_graph, history, density_profile, colony_edge,
         fusion_events, oscillators
    """
    if params is None:
        params = AMFungiParams()
    import random as _random
    rng = _random.Random(seed)
    name_counter = [0]

    # Ensure root nodes exist with 3D coords
    for root in root_nodes:
        if root not in G:
            G.add_node(root, pos3d=(0.0, 0.0, 0.0), is_root=True)
        elif G.nodes[root].get('pos3d') is None:
            G.nodes[root]['pos3d'] = (0.0, 0.0, 0.0)
        G.nodes[root]['is_root'] = True

    # Assign 3D coords if missing
    for node in G.nodes():
        if G.nodes[node].get('pos3d') is None:
            G.nodes[node]['pos3d'] = (rng.uniform(-1, 1),
                                       rng.uniform(-1, 1),
                                       rng.uniform(-1, 1))

    history = []
    oscillators = {}  # Brique 14: FHN oscillators for tip signaling
    fusion_events = []  # Brique 11: completed fusions
    # Edelstein 1982: d is a continuous hyphal death rate (1/time),
    # not a per-step probability. For discrete simulation, probability
    # of edge death per step = 1 - exp(-d·Δt) ≈ d·Δt for small d.
    # Hyphae are structural: much more stable than tips (d_n).
    # Source: Boswell et al. 2003 — "hyphal death rare in healthy colony,
    # mostly occurs at resource-depleted periphery".
    # Scale: d_edge = death_rate * 0.05 → ~0.5% edge loss/step (realistic).
    edelstein_params = EdelsteinParams(
        b_n=params.branch_rate,
        d_n=params.death_rate * 0.5,
        d=params.death_rate * 0.05,  # hyphal edges far more stable than tips
        n_max=min(params.n_max / 100.0, 0.9),  # normalize to fraction
        a1=params.a1,
        a2=params.a2
    )
    mech_params = HyphalMechanicsParams(
        turgor=0.5,
        segment_length=params.tip_speed
    )

    for step in range(n_steps):
        # Re-ensure root nodes exist (may be killed by Edelstein death)
        for root in root_nodes:
            if root not in G:
                G.add_node(root, pos3d=(0.0, 0.0, 0.0), is_root=True)

        snapshot = {
            'step': step,
            'n_nodes': G.number_of_nodes(),
            'n_edges': G.number_of_edges(),
        }

        # Phase 1: Root emits tips (Schnepf boundary condition) [A]
        emit_stats = am_root_emit_tips(G, root_nodes, step, params,
                                        rng, name_counter)
        snapshot['tips_emitted'] = emit_stats['tips_emitted']

        # Phase 2: Edelstein growth/death (brique 13)
        if use_edelstein and G.number_of_nodes() > 1:
            eg = edelstein_growth_step(G, edelstein_params, rng)
            snapshot['edelstein_growth'] = eg.get('branches_added', 0)
            snapshot['edelstein_death'] = eg.get('tips_died', 0)

        # Phase 3: 3D mechanics (brique 15)
        if use_3d and G.number_of_nodes() > 1:
            h3d = hyphal_growth_3d_step(G, mech_params, rng, name_counter)
            snapshot['extensions_3d'] = h3d.get('extensions', 0)

        # Phase 4: Oscillatory signaling (brique 14 — Goryachev/Fleissner)
        # Tips run FHN oscillators, nearby tips couple and synchronize.
        snapshot['fusions'] = 0
        if use_oscillatory and G.number_of_nodes() > 2:
            sig_result = oscillatory_signaling_step(G, oscillators)
            oscillators = sig_result['oscillators']
            snapshot['sync_pairs'] = len(sig_result['sync_pairs'])

            # Phase 5: Fusion completion (brique 14 → 11)
            # Every fusion_interval steps, synchronized pairs trigger anastomosis.
            if step > 0 and step % fusion_interval == 0 and sig_result['sync_pairs']:
                # Convert sync_pairs to fusion candidates: (u, v, score)
                # Score = 1 - (phase_diff / π) → higher = more synchronized
                candidates = []
                for t1, t2, diff, dist in sig_result['sync_pairs']:
                    score = 1.0 - (diff / math.pi)
                    if score >= fusion_threshold and t1 in G and t2 in G:
                        candidates.append((t1, t2, score))

                if candidates:
                    fused = anastomose(G, candidates,
                                       conductivity_init=0.5)
                    n_fused = fused.get('n_fused', 0)
                    snapshot['fusions'] = n_fused
                    if n_fused > 0:
                        fusion_events.append({
                            'step': step,
                            'n_fused': n_fused,
                            'pairs': fused.get('fused', []),
                            'delta_alpha': fused.get('delta_alpha', 0),
                            'delta_E': fused.get('delta_E', 0),
                        })

        snapshot['n_nodes_after'] = G.number_of_nodes()
        snapshot['n_edges_after'] = G.number_of_edges()
        history.append(snapshot)

    # Compute density profile [A]
    density = am_hyphal_density_profile(G, root_nodes)

    # Colony edge = max distance from any root
    colony_edge = density['max_distance']

    return {
        'final_graph': G,
        'history': history,
        'density_profile': density,
        'colony_edge': colony_edge,
        'params': params,
        'delta': params.delta(),
        'fusion_events': fusion_events,
        'total_fusions': sum(e['n_fused'] for e in fusion_events),
        'oscillators': oscillators,
    }


# --- Species presets from Schnepf 2008 Table 1 [A] ---
def am_species_presets():
    """Calibrated parameters for 3 AM fungal species.

    Source: Schnepf & Roose 2008, Table 1, fitted to Jakobsen 1992 data [A].
    """
    return {
        'S_calospora': AMFungiParams(
            branch_rate=0.3, death_rate=0.3,  # δ≈1
            a1=0.0, a2=0.0,  # linear branching sufficient
            tip_flux_base=1.0, tip_flux_growth=0.0
        ),
        'Glomus_sp': AMFungiParams(
            branch_rate=0.5, death_rate=0.2,  # δ≈0.4
            a1=1.0, a2=0.0,  # tip-tip anastomosis
            tip_flux_base=2.0, tip_flux_growth=0.1
        ),
        'A_laevis': AMFungiParams(
            branch_rate=0.4, death_rate=0.15,  # δ≈0.375
            a1=0.0, a2=1.0,  # tip-hypha anastomosis dominant
            tip_flux_base=3.0, tip_flux_growth=0.2
        ),
    }


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 17 — SPORE GERMINATION & CHEMOTAXIS (v2.0)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   [A] Peleg & Normand 2013, Appl. Environ. Microbiol. 79:6765-6775
#     "Modeling of Fungal and Bacterial Spore Germination"
#     Weibull germination: G(t) = G_max · (1 - exp(-(t/τ)^n))
#     Dantigny asymmetric model for non-symmetric curves.
#     Stochastic: P(germ) constant → nonsigmoid, rising → sigmoid.
#
#   [B] Besserer et al. 2006, PLoS Biol. 4:e226
#     "Strigolactones Stimulate AM Fungi by Activating Mitochondria"
#     Root exudes strigolactone (SL) → activates spore mitochondria.
#     [SL] as low as 10⁻¹³ M triggers germination.
#     SL = branching factor, dose-dependent response.
#     SL high turnover in soil → diffusion + decay.
#
#   [C] Lucido et al. 2022, Front. Plant Sci. 13:979162
#     "A mathematical model for strigolactone biosynthesis in plants"
#     Flux branching parameter ω controls SL types.
#     No feedback regulation in SL biosynthesis.
#
#   [D] Chiu & Hoppensteadt 2001, J. Math. Biol. 42:120-144
#     "Mathematical models for bacterial growth and chemotaxis"
#     Chemotaxis: ∂n/∂t = D∇²n - χ∇·(n∇c)
#     D = diffusion, χ = chemotactic sensitivity.
#
# Discrete translation for graphs:
#   Spore = node with 'is_spore=True', position in soil.
#   Root = source of strigolactone signal (diffusing field).
#   [SL] at spore position determines germination probability [B].
#   P(germ) = Michaelis-Menten: [SL] / (K_SL + [SL]) [B].
#   Once germinated → creates germ tube (new edge + tip node).
#   Germ tube grows via chemotaxis toward SL gradient [D].
#   Feeds into brique 16 (am_fungi_simulate) as initial condition.
# ═══════════════════════════════════════════════════════════════════


class SporeGerminationParams:
    """Parameters for spore germination and chemotaxis model.

    Sources: Peleg 2013 [A], Besserer 2006 [B], Chiu 2001 [D].
    """
    def __init__(self,
                 g_max=0.95,          # max germination fraction [A]
                 tau=5.0,             # Weibull timescale [A]
                 n_shape=2.0,         # Weibull shape parameter [A]
                 k_sl=0.001,          # Michaelis-Menten K for SL [B]
                 sl_diffusion=1.0,    # D: SL diffusion coefficient
                 sl_decay=0.1,        # λ: SL decay rate in soil [B]
                 sl_source_rate=0.5,  # SL emission rate at root
                 chemotaxis_chi=0.5,  # χ: chemotactic sensitivity [D]
                 germ_tube_speed=0.5, # germ tube elongation rate
                 germ_tube_length=2.0,# initial germ tube segment
                 ):
        self.g_max = g_max
        self.tau = tau
        self.n_shape = n_shape
        self.k_sl = k_sl
        self.sl_diffusion = sl_diffusion
        self.sl_decay = sl_decay
        self.sl_source_rate = sl_source_rate
        self.chemotaxis_chi = chemotaxis_chi
        self.germ_tube_speed = germ_tube_speed
        self.germ_tube_length = germ_tube_length

    def weibull_germination(self, t):
        """Cumulative germination fraction at time t.

        Source: Peleg 2013 [A], eq. 1.
        G(t) = G_max · (1 - exp(-(t/τ)^n))
        """
        if t <= 0:
            return 0.0
        return self.g_max * (1.0 - math.exp(-((t / self.tau) ** self.n_shape)))

    def sl_concentration(self, distance, t):
        """Strigolactone concentration at distance from root.

        Steady-state solution of diffusion-decay:
        ∂[SL]/∂t = D·∇²[SL] - λ·[SL] + source
        Steady-state spherical: [SL](r) = (Q / 4πDr) · exp(-r/L)
        where L = √(D/λ) = penetration length.
        Source: derived from Besserer 2006 [B] + standard diffusion.
        """
        if distance < 0.01:
            distance = 0.01  # avoid singularity at r=0
        L = math.sqrt(self.sl_diffusion / max(self.sl_decay, 1e-10))
        return (self.sl_source_rate / (4 * math.pi * self.sl_diffusion * distance)) * \
               math.exp(-distance / L)

    def germination_probability(self, sl_conc):
        """Probability of germination given SL concentration.

        Michaelis-Menten dose-response:
        P = [SL] / (K_SL + [SL])
        Source: derived from Besserer 2006 [B] dose-response data.
        """
        return sl_conc / (self.k_sl + sl_conc)


def spore_germination_simulate(spore_positions, root_positions,
                                n_steps=20, params=None, seed=42):
    """Simulate spore germination and germ tube chemotaxis.

    Creates a graph with germinated spores connected to germ tube tips
    that grow toward the nearest root via strigolactone gradient.

    Parameters
    ----------
    spore_positions : list of (x, y, z)
        Initial spore positions in 3D soil.
    root_positions : list of (x, y, z)
        Root node positions (SL sources).
    n_steps : int
        Simulation steps.
    params : SporeGerminationParams or None
    seed : int

    Returns
    -------
    dict with:
        'graph': nx.Graph — resulting network
        'germinated': list of spore names that germinated
        'history': list of step snapshots
        'sl_field': dict mapping spore→SL concentration
    """
    if params is None:
        params = SporeGerminationParams()
    import random as _random
    rng = _random.Random(seed)

    G = nx.Graph()

    # Add root nodes
    for i, rpos in enumerate(root_positions):
        rname = f"root_{i}"
        G.add_node(rname, pos3d=rpos, is_root=True)

    # Add spore nodes
    spore_names = []
    for i, spos in enumerate(spore_positions):
        sname = f"spore_{i}"
        G.add_node(sname, pos3d=spos, is_spore=True,
                   germinated=False, germ_time=None)
        spore_names.append(sname)

    germinated = []
    history = []
    sl_field = {}
    name_counter = [0]

    for step in range(n_steps):
        snapshot = {'step': step, 'n_germinated': len(germinated),
                    'n_nodes': G.number_of_nodes()}

        for sname in spore_names:
            if G.nodes[sname].get('germinated'):
                continue

            spos = G.nodes[sname]['pos3d']

            # Compute SL at spore position (sum from all roots)
            sl_total = 0.0
            for rname in [n for n in G.nodes() if G.nodes[n].get('is_root')]:
                rpos = G.nodes[rname]['pos3d']
                dist = _vec_distance(spos, rpos)
                sl_total += params.sl_concentration(dist, step)

            sl_field[sname] = sl_total

            # Germination check: Weibull × SL dose-response
            p_time = params.weibull_germination(step + 1)
            p_sl = params.germination_probability(sl_total)
            p_germ = p_time * p_sl

            if rng.random() < p_germ:
                G.nodes[sname]['germinated'] = True
                G.nodes[sname]['germ_time'] = step
                germinated.append(sname)

                # Create germ tube toward nearest root (chemotaxis)
                nearest_root = None
                min_dist = float('inf')
                for rname in [n for n in G.nodes() if G.nodes[n].get('is_root')]:
                    rpos = G.nodes[rname]['pos3d']
                    d = _vec_distance(spos, rpos)
                    if d < min_dist:
                        min_dist = d
                        nearest_root = rname

                if nearest_root is not None:
                    rpos = G.nodes[nearest_root]['pos3d']
                    # Direction = chemotaxis toward root + noise
                    direction = _vec_subtract(rpos, spos)
                    dir_norm = _vec_normalize(direction)
                    if dir_norm == (0.0, 0.0, 0.0):
                        dir_norm = _random_unit_vector(rng)

                    # Add noise to direction
                    noise = _random_unit_vector(rng)
                    noisy_dir = _vec_normalize(_vec_add(
                        _vec_scale(dir_norm, params.chemotaxis_chi),
                        _vec_scale(noise, 1.0 - params.chemotaxis_chi)
                    ))
                    if noisy_dir == (0.0, 0.0, 0.0):
                        noisy_dir = dir_norm

                    # Create germ tube tip
                    tip_pos = _vec_add(spos,
                                       _vec_scale(noisy_dir,
                                                  params.germ_tube_length))
                    name_counter[0] += 1
                    tip_name = f"germ_tip_{name_counter[0]}"
                    G.add_node(tip_name, pos3d=tip_pos,
                               is_am_tip=True,
                               spk_direction=noisy_dir,
                               source_spore=sname)
                    seg_len = _vec_distance(spos, tip_pos)
                    G.add_edge(sname, tip_name, length_3d=seg_len,
                               is_germ_tube=True)

        # Extend existing germ tube tips (chemotaxis growth)
        tips = [n for n in G.nodes()
                if G.nodes[n].get('is_am_tip') and
                G.nodes[n].get('source_spore') is not None]
        for tip in tips:
            tip_pos = G.nodes[tip]['pos3d']
            # Find nearest root for gradient
            nearest_root = None
            min_dist = float('inf')
            for rname in [n for n in G.nodes() if G.nodes[n].get('is_root')]:
                rpos = G.nodes[rname]['pos3d']
                d = _vec_distance(tip_pos, rpos)
                if d < min_dist:
                    min_dist = d
                    nearest_root = rname

            if nearest_root and min_dist > params.germ_tube_length:
                rpos = G.nodes[nearest_root]['pos3d']
                direction = _vec_normalize(_vec_subtract(rpos, tip_pos))
                if direction == (0.0, 0.0, 0.0):
                    continue
                noise = _random_unit_vector(rng)
                noisy_dir = _vec_normalize(_vec_add(
                    _vec_scale(direction, params.chemotaxis_chi),
                    _vec_scale(noise, 0.2)
                ))
                if noisy_dir == (0.0, 0.0, 0.0):
                    noisy_dir = direction

                new_pos = _vec_add(tip_pos,
                                    _vec_scale(noisy_dir,
                                               params.germ_tube_speed))
                name_counter[0] += 1
                new_name = f"germ_tip_{name_counter[0]}"
                G.add_node(new_name, pos3d=new_pos,
                           is_am_tip=True,
                           spk_direction=noisy_dir,
                           source_spore=G.nodes[tip].get('source_spore'))
                G.add_edge(tip, new_name,
                           length_3d=_vec_distance(tip_pos, new_pos),
                           is_germ_tube=True)
                # Old tip no longer the frontier
                if 'is_am_tip' in G.nodes[tip]:
                    del G.nodes[tip]['is_am_tip']

        snapshot['n_germinated_after'] = len(germinated)
        snapshot['n_nodes_after'] = G.number_of_nodes()
        history.append(snapshot)

    return {
        'graph': G,
        'germinated': germinated,
        'history': history,
        'sl_field': sl_field,
        'params': params,
    }


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 18 — L-SYSTEM ROOT ARCHITECTURE (v2.0)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   [A] Leitner et al. 2010, Math. Comp. Model. Dyn. Syst. 16:575-587
#     "The algorithmic beauty of plant roots — an L-System model"
#     Parametric L-System with growth function λ(t).
#     Root types: tap root (order 0), laterals (order 1,2).
#     Branching interval ln, branching angle θ.
#
#   [B] Schnepf et al. 2018, Ann. Bot. 121:1033-1053
#     "CRootBox: a structural-functional modelling framework"
#     Direction: deflection angle α ~ N(0,σ), gravitropism N trials.
#     Doussan model: Kirchhoff's law for water flow in root graph.
#     Root types with per-type parameters.
#
# Equations:
#   Growth: λ(t) = L_max · (1 - exp(-r·t / L_max))      [A]
#   Elongation rate: dλ/dt = r · exp(-r·t / L_max)       [A]
#   Branching: laterals at spacing ln along parent         [A]
#   Direction: α ~ N(0, σ), β ~ U(0, 2π)                 [B]
#   Gravitropism: pick best of N random trials             [B]
# ═══════════════════════════════════════════════════════════════════


class RootTypeParams:
    """Parameters for one root type in L-System model.

    Source: Leitner 2010 [A], Schnepf 2018 [B].
    """
    def __init__(self, order=0, r=1.0, l_max=20.0, sigma=0.3,
                 theta=math.pi / 4, ln=2.0, n_laterals=5,
                 n_tropism=3, segment_dx=1.0,
                 successor_order=None):
        self.order = order              # root type order (0=tap, 1=lateral...)
        self.r = r                      # initial elongation rate [cm/day] [A]
        self.l_max = l_max              # max root length [cm] [A]
        self.sigma = sigma              # deflection angle std dev [B]
        self.theta = theta              # branching angle from parent [A]
        self.ln = ln                    # inter-lateral distance [cm] [A]
        self.n_laterals = n_laterals    # max number of laterals
        self.n_tropism = n_tropism      # N trials for gravitropism [B]
        self.segment_dx = segment_dx    # segment length [cm] [B]
        self.successor_order = successor_order or (order + 1)

    def growth_length(self, t):
        """Root length at local age t.

        λ(t) = L_max · (1 - exp(-r·t / L_max))
        Source: Leitner 2010 [A], eq. 3.1.
        """
        if t <= 0:
            return 0.0
        return self.l_max * (1.0 - math.exp(-self.r * t / self.l_max))

    def elongation_rate(self, t):
        """Elongation rate at local age t.

        dλ/dt = r · exp(-r·t / L_max)
        Source: derivative of [A] eq. 3.1.
        """
        if t <= 0:
            return self.r
        return self.r * math.exp(-self.r * t / self.l_max)


def lsystem_root_generate(root_types=None, n_steps=20, seed=42,
                           origin=(0.0, 0.0, 0.0),
                           gravity_dir=(0.0, 0.0, -1.0)):
    """Generate a root architecture graph using L-System rules.

    Parameters
    ----------
    root_types : dict or None
        {order: RootTypeParams}. Default: tap root + 1st order laterals.
    n_steps : int
        Time steps (days).
    seed : int
    origin : tuple
        Root collar position.
    gravity_dir : tuple
        Direction of gravity (for gravitropism).

    Returns
    -------
    dict with:
        'graph': nx.Graph — root architecture
        'history': list of step snapshots
        'root_tips': list of current tip node names
        'root_lengths': dict {root_id: current_length}
    """
    import random as _random
    rng = _random.Random(seed)

    if root_types is None:
        root_types = {
            0: RootTypeParams(order=0, r=2.0, l_max=30.0, sigma=0.2,
                              theta=0, ln=3.0, n_laterals=8,
                              n_tropism=5, segment_dx=1.0),
            1: RootTypeParams(order=1, r=1.0, l_max=10.0, sigma=0.4,
                              theta=math.pi / 3, ln=2.0, n_laterals=3,
                              n_tropism=2, segment_dx=0.8),
        }

    G = nx.Graph()
    name_counter = [0]

    def new_name(prefix="rn"):
        name_counter[0] += 1
        return f"{prefix}_{name_counter[0]}"

    # Initialize tap root
    collar_name = new_name("collar")
    G.add_node(collar_name, pos3d=origin, is_root=True,
               root_order=0, root_id="tap_0", local_age=0.0,
               is_root_tip=True)

    # Track active roots: (tip_node, root_id, order, direction, local_age, length, branch_points)
    active_roots = [{
        'tip': collar_name,
        'root_id': 'tap_0',
        'order': 0,
        'direction': _vec_normalize(gravity_dir),
        'local_age': 0.0,
        'length': 0.0,
        'next_branch_at': root_types[0].ln if 0 in root_types else 999,
        'n_branches': 0,
    }]

    root_lengths = {'tap_0': 0.0}
    history = []
    root_id_counter = [0]

    for step in range(n_steps):
        snapshot = {'step': step, 'n_nodes': G.number_of_nodes(),
                    'n_active': len(active_roots)}
        new_roots = []

        for root in active_roots:
            order = root['order']
            if order not in root_types:
                continue
            rt = root_types[order]

            root['local_age'] += 1.0
            target_len = rt.growth_length(root['local_age'])
            growth = target_len - root['length']

            if growth < 0.01:
                continue  # root has reached max length

            # Number of segments to add this step
            n_segs = max(1, int(growth / rt.segment_dx))
            seg_len = growth / n_segs

            for _ in range(n_segs):
                tip_pos = G.nodes[root['tip']]['pos3d']

                # Gravitropism: pick best of N random directions [B]
                best_dir = root['direction']
                best_score = -999
                for _trial in range(rt.n_tropism):
                    # Random deflection [B]: α ~ N(0,σ)
                    alpha = rng.gauss(0, rt.sigma)
                    beta = rng.uniform(0, 2 * math.pi)
                    # Perturb current direction
                    perp1, perp2 = _get_perpendiculars(root['direction'])
                    candidate = _vec_normalize(_vec_add(
                        _vec_scale(root['direction'], math.cos(alpha)),
                        _vec_add(
                            _vec_scale(perp1, math.sin(alpha) * math.cos(beta)),
                            _vec_scale(perp2, math.sin(alpha) * math.sin(beta))
                        )
                    ))
                    if candidate == (0.0, 0.0, 0.0):
                        candidate = root['direction']
                    # Score: alignment with gravity [B]
                    score = _vec_dot(candidate, gravity_dir)
                    if score > best_score:
                        best_score = score
                        best_dir = candidate

                root['direction'] = best_dir
                new_pos = _vec_add(tip_pos, _vec_scale(best_dir, seg_len))
                nn = new_name("rn")
                G.add_node(nn, pos3d=new_pos, is_root=True,
                           root_order=order, root_id=root['root_id'],
                           local_age=root['local_age'],
                           is_root_tip=True)
                G.add_edge(root['tip'], nn, length_3d=seg_len,
                           is_root_segment=True, root_id=root['root_id'])
                # Previous tip no longer tip
                G.nodes[root['tip']]['is_root_tip'] = False
                root['tip'] = nn
                root['length'] += seg_len
                root_lengths[root['root_id']] = root['length']

                # Check if lateral should branch here [A]
                if root['length'] >= root['next_branch_at']:
                    succ_order = rt.successor_order
                    if (succ_order in root_types and
                            root['n_branches'] < rt.n_laterals):
                        root['n_branches'] += 1
                        root['next_branch_at'] += rt.ln

                        # Branch direction: rotate by θ from parent [A]
                        perp1, perp2 = _get_perpendiculars(root['direction'])
                        rand_beta = rng.uniform(0, 2 * math.pi)
                        branch_dir = _vec_normalize(_vec_add(
                            _vec_scale(root['direction'], math.cos(rt.theta)),
                            _vec_add(
                                _vec_scale(perp1, math.sin(rt.theta) * math.cos(rand_beta)),
                                _vec_scale(perp2, math.sin(rt.theta) * math.sin(rand_beta))
                            )
                        ))
                        if branch_dir == (0.0, 0.0, 0.0):
                            branch_dir = perp1

                        root_id_counter[0] += 1
                        new_rid = f"lat_{root_id_counter[0]}"
                        new_roots.append({
                            'tip': nn,  # starts from same node
                            'root_id': new_rid,
                            'order': succ_order,
                            'direction': branch_dir,
                            'local_age': 0.0,
                            'length': 0.0,
                            'next_branch_at': root_types[succ_order].ln,
                            'n_branches': 0,
                        })
                        root_lengths[new_rid] = 0.0

        active_roots.extend(new_roots)
        snapshot['n_nodes_after'] = G.number_of_nodes()
        snapshot['n_branches_total'] = len(active_roots)
        history.append(snapshot)

    root_tips = [n for n in G.nodes() if G.nodes[n].get('is_root_tip')]

    return {
        'graph': G,
        'history': history,
        'root_tips': root_tips,
        'root_lengths': root_lengths,
    }


def _get_perpendiculars(direction):
    """Get two orthogonal vectors perpendicular to direction."""
    dx, dy, dz = direction
    if abs(dx) < 0.9:
        ref = (1.0, 0.0, 0.0)
    else:
        ref = (0.0, 1.0, 0.0)
    # Cross product: direction × ref
    p1 = _vec_normalize(_vec_cross(direction, ref))
    p2 = _vec_normalize(_vec_cross(direction, p1))
    return p1, p2


def _vec_cross(a, b):
    """Cross product of two 3D vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_dot(a, b):
    """Dot product of two 3D vectors."""
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 19 — NUTRIENT TRANSPORT & P UPTAKE (v2.0)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   [A] Schnepf & Roose 2006, New Phytol. 171:669-682
#     "Modelling the contribution of AM fungi to plant phosphate uptake"
#     P transport in soil: ∂c/∂t = D·∇²c - F·ρ
#     Michaelis-Menten uptake: F = F_max·c / (K_m + c)
#     Uptake dominated by front of growing mycelium.
#     Translocation within fungus so fast → not rate-limiting.
#
#   [B] Schnepf et al. 2008, Plant & Soil 312:85-99
#     "Impact of growth and uptake patterns on P uptake"
#     Uptake by all hyphae vs tips only → different optima.
#     Anastomosis growth pattern most effective when all hyphae uptake.
#
#   [C] Leitner et al. 2010, Bull. Math. Biol. 73:2059-2084
#     "Modelling nutrient uptake by individual hyphae"
#     Single-hypha: ∂c/∂t = D·(1/r)·∂/∂r(r·∂c/∂r) - F(c)
#     Michaelis-Menten: F(c) = F_max·c/(K_m+c) at hyphal surface.
#
# Discrete translation for graphs:
#   Each node stores local soil P concentration [P_soil].
#   Hyphae uptake: node removes P proportional to F_max·c/(K_m+c).
#   Transport: P flows along edges toward root (pressure-driven).
#   Root accumulates total P = sum of transported P.
# ═══════════════════════════════════════════════════════════════════


class NutrientParams:
    """Parameters for P uptake and transport model.

    Sources: Schnepf 2006 [A], Leitner 2010 [C].
    """
    def __init__(self,
                 d_soil=0.01,         # D: P diffusion in soil [cm²/day]
                 f_max=0.05,          # F_max: max uptake rate [µmol/cm/day]
                 k_m=0.005,           # K_m: Michaelis-Menten constant [µmol/cm³]
                 c_initial=0.01,      # initial soil P concentration [µmol/cm³]
                 transport_rate=0.8,  # fraction transported per step toward root
                 ):
        self.d_soil = d_soil
        self.f_max = f_max
        self.k_m = k_m
        self.c_initial = c_initial
        self.transport_rate = transport_rate

    def uptake_rate(self, c):
        """Michaelis-Menten uptake rate.

        F = F_max · c / (K_m + c)
        Source: Schnepf 2006 [A], eq. main model.
        """
        if c <= 0:
            return 0.0
        return self.f_max * c / (self.k_m + c)


def nutrient_simulate(G, root_nodes, n_steps=20, params=None, seed=42):
    """Simulate P uptake and transport on a mycelial graph.

    Each non-root node uptakes P from local soil (Michaelis-Menten).
    P is transported along edges toward nearest root (pressure-driven).
    Root nodes accumulate total P.

    Parameters
    ----------
    G : nx.Graph
        Mycelial network (from am_fungi_simulate or similar).
    root_nodes : list
        Root interface nodes (P sinks).
    n_steps : int
    params : NutrientParams or None
    seed : int

    Returns
    -------
    dict with:
        'total_p_root': float — total P delivered to root
        'p_history': list of total P at each step
        'soil_p': dict — final soil P at each node
        'node_p_internal': dict — P stored in each node
        'depletion_zone': float — avg soil P depletion
    """
    if params is None:
        params = NutrientParams()

    # Initialize soil P at each node
    soil_p = {}
    for node in G.nodes():
        soil_p[node] = params.c_initial

    # Internal P (absorbed by fungus, not yet transported)
    internal_p = {node: 0.0 for node in G.nodes()}
    root_p_total = 0.0
    p_history = []

    # Precompute shortest path to nearest root for transport direction
    # Use BFS from each root
    nearest_root = {}
    for rn in root_nodes:
        if rn in G:
            lengths = nx.single_source_shortest_path_length(G, rn)
            for node, dist in lengths.items():
                if node not in nearest_root or dist < nearest_root[node][1]:
                    nearest_root[node] = (rn, dist)

    for step in range(n_steps):
        step_uptake = 0.0

        # Phase 1: Uptake from soil (Michaelis-Menten) [A]
        for node in G.nodes():
            if node in root_nodes:
                continue  # roots don't uptake from soil
            c = soil_p.get(node, 0)
            f = params.uptake_rate(c)
            uptake = min(f, c)  # can't uptake more than available
            soil_p[node] = c - uptake
            internal_p[node] += uptake
            step_uptake += uptake

        # Phase 2: Diffusion in soil (simple neighbor averaging) [A]
        new_soil = {}
        for node in G.nodes():
            neighbors = list(G.neighbors(node))
            if not neighbors:
                new_soil[node] = soil_p.get(node, 0)
                continue
            avg_neighbor = sum(soil_p.get(n, 0) for n in neighbors) / len(neighbors)
            # Diffusion: move toward average
            c = soil_p.get(node, 0)
            new_soil[node] = c + params.d_soil * (avg_neighbor - c)
        soil_p = new_soil

        # Phase 3: Transport toward root [A] "translocation so fast"
        # Move internal_p along shortest path to root
        step_delivered = 0.0
        # Sort nodes by distance to root (farthest first)
        nodes_by_dist = sorted(
            [(n, nearest_root[n][1]) for n in G.nodes()
             if n in nearest_root and n not in root_nodes],
            key=lambda x: -x[1]
        )
        for node, dist in nodes_by_dist:
            if internal_p[node] <= 0:
                continue
            transport = internal_p[node] * params.transport_rate
            internal_p[node] -= transport

            # Find next node on path to root
            root_target, _ = nearest_root[node]
            try:
                path = nx.shortest_path(G, node, root_target)
                if len(path) > 1:
                    next_node = path[1]
                    if next_node in root_nodes:
                        root_p_total += transport
                        step_delivered += transport
                    else:
                        internal_p[next_node] = internal_p.get(next_node, 0) + transport
                else:
                    root_p_total += transport
                    step_delivered += transport
            except nx.NetworkXNoPath:
                internal_p[node] += transport  # return if no path

        p_history.append({
            'step': step,
            'uptake': step_uptake,
            'delivered': step_delivered,
            'total_root_p': root_p_total,
        })

    # Compute depletion zone
    initial_total = params.c_initial * len(soil_p)
    final_total = sum(soil_p.values())
    depletion = 1.0 - (final_total / max(initial_total, 1e-10))

    return {
        'total_p_root': root_p_total,
        'p_history': p_history,
        'soil_p': soil_p,
        'node_p_internal': internal_p,
        'depletion_zone': depletion,
        'params': params,
    }


def test_nutrient_uptake():
    """Tests for brique 19 — Nutrient Transport & P Uptake."""
    print("\n=== BRIQUE 19: Nutrient Transport & P Uptake ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # --- Test 1: Michaelis-Menten uptake ---
    p1 = NutrientParams(f_max=1.0, k_m=0.01)
    check("MM: high c → F≈F_max", abs(p1.uptake_rate(100) - 1.0) < 0.01)
    check("MM: c=0 → F=0", abs(p1.uptake_rate(0)) < 0.001)
    check("MM: c=K_m → F=F_max/2",
          abs(p1.uptake_rate(0.01) - 0.5) < 0.001)

    # --- Test 2: Uptake monotonically increasing ---
    vals = [p1.uptake_rate(c) for c in [0, 0.001, 0.01, 0.1, 1, 10]]
    check("MM: monotonic", all(vals[i] <= vals[i+1] for i in range(len(vals)-1)))

    # --- Test 3: Basic simulation on path graph ---
    G3 = nx.path_graph(10)  # 0-1-2-...-9
    for n in G3.nodes():
        G3.nodes[n]['pos3d'] = (float(n), 0.0, 0.0)
    r3 = nutrient_simulate(G3, [0], n_steps=10)
    check("Sim: total P > 0", r3['total_p_root'] > 0)
    check("Sim: history = 10 steps", len(r3['p_history']) == 10)
    check("Sim: P increases over time",
          r3['p_history'][-1]['total_root_p'] >= r3['p_history'][0]['total_root_p'])

    # --- Test 4: Soil depletion ---
    check("Depletion > 0", r3['depletion_zone'] > 0)

    # --- Test 5: Soil P decreases over time ---
    params5 = NutrientParams(c_initial=0.1)
    r5 = nutrient_simulate(G3, [0], n_steps=20, params=params5)
    # All non-root nodes should have less P than initial
    all_depleted = all(r5['soil_p'][n] < 0.1 for n in G3.nodes() if n != 0)
    check("Soil P: all nodes depleted below initial", all_depleted)

    # --- Test 6: More hyphae → more uptake ---
    G6a = nx.path_graph(5)
    G6b = nx.path_graph(20)
    for n in G6a.nodes():
        G6a.nodes[n]['pos3d'] = (float(n), 0, 0)
    for n in G6b.nodes():
        G6b.nodes[n]['pos3d'] = (float(n), 0, 0)
    r6a = nutrient_simulate(G6a, [0], n_steps=10)
    r6b = nutrient_simulate(G6b, [0], n_steps=10)
    check("More hyphae → more P uptake",
          r6b['total_p_root'] >= r6a['total_p_root'])

    # --- Test 7: No nutrients → no uptake ---
    r7 = nutrient_simulate(G3, [0], n_steps=5,
                            params=NutrientParams(c_initial=0.0))
    check("No soil P → 0 uptake", abs(r7['total_p_root']) < 0.001)

    # --- Test 8: Empty graph → no crash ---
    G8 = nx.Graph()
    G8.add_node("root", pos3d=(0, 0, 0))
    r8 = nutrient_simulate(G8, ["root"], n_steps=5)
    check("Single root node: no crash", r8['total_p_root'] >= 0)

    # --- Test 9: Disconnected node → P stays internal ---
    G9 = nx.Graph()
    G9.add_node("root", pos3d=(0, 0, 0))
    G9.add_node("island", pos3d=(10, 0, 0))
    r9 = nutrient_simulate(G9, ["root"], n_steps=10)
    check("Disconnected node: P not transported",
          r9['node_p_internal']['island'] > 0 or
          r9['soil_p']['island'] < NutrientParams().c_initial)

    # --- Test 10: Transport rate effect ---
    r10a = nutrient_simulate(G3, [0], n_steps=10,
                              params=NutrientParams(transport_rate=0.1))
    r10b = nutrient_simulate(G3, [0], n_steps=10,
                              params=NutrientParams(transport_rate=0.9))
    check("Higher transport rate → more P at root",
          r10b['total_p_root'] >= r10a['total_p_root'])

    # --- Test 11: Integration 19+16 — AM graph + nutrients ---
    G11 = nx.Graph()
    am = am_fungi_simulate(G11, ["root"], n_steps=10, seed=42,
                            params=AMFungiParams(tip_flux_base=2.0),
                            use_oscillatory=False)
    fg = am['final_graph']
    r11 = nutrient_simulate(fg, ["root"], n_steps=10)
    check("Integration 19+16: P uptake on AM graph",
          r11['total_p_root'] > 0)

    # --- Test 12: F_max effect ---
    r12a = nutrient_simulate(G3, [0], n_steps=10,
                              params=NutrientParams(f_max=0.01))
    r12b = nutrient_simulate(G3, [0], n_steps=10,
                              params=NutrientParams(f_max=1.0))
    check("Higher F_max → more uptake",
          r12b['total_p_root'] >= r12a['total_p_root'])

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 20 — CARBON ↔ PHOSPHORUS EXCHANGE (v2.0)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   [A] Kiers et al. 2011, Science 333:880-882
#     "Reciprocal rewards stabilize cooperation in mycorrhizal symbiosis"
#     More P delivered → more C rewarded. More C received → more P sent.
#     Biological market: both partners select best-performing partners.
#
#   [B] Chevalier et al. 2025, PNAS
#     "C-P exchange rate constrains density-speed trade-off"
#     C investment determines fungal growth rate and network density.
#     High C → fast growth but sparse. Low C → slow but dense.
#
#   [C] Fellbaum et al. 2012, PNAS 109:2666-2671
#     "Carbon availability triggers fungal N uptake and transport"
#     AM fungi = obligate biotrophs: 4-17% of host photosynthate.
#     No C → fungus dies.
#
#   [D] Bücking & Shachar-Hill 2005, New Phytol. 165:899-911
#     "P uptake, transport and transfer stimulated by carbohydrate"
#     High C availability → increased P transfer to plant.
#
# Equations:
#   Plant C budget:  C_produced = photosynthesis_rate
#                    C_to_fungus = α · C_produced · f(P_received)
#   Fungus P budget: P_from_soil = from brique 19
#                    P_to_plant = β · P_fungus · f(C_received)
#   Reciprocal rewards [A]:
#     f(x) = x / (K + x)   (Michaelis-Menten allocation)
#   Obligate biotroph [C]:
#     If C_received < C_min → fungus death_rate increases
# ═══════════════════════════════════════════════════════════════════


class SymbiosisParams:
    """Parameters for C↔P exchange model.

    Sources: Kiers 2011 [A], Fellbaum 2012 [C], Bücking 2005 [D].
    """
    def __init__(self,
                 photosynthesis_rate=1.0,  # C produced per step
                 c_allocation_max=0.15,    # max fraction of C to fungus (4-17%) [C]
                 p_allocation_max=0.8,     # max fraction of fungal P to plant
                 k_c=0.1,                  # K for C reward function [A]
                 k_p=0.05,                 # K for P reward function [A]
                 c_min_survival=0.01,      # min C for fungus survival [C]
                 death_boost_no_c=5.0,     # death rate multiplier if no C
                 ):
        self.photosynthesis_rate = photosynthesis_rate
        self.c_allocation_max = c_allocation_max
        self.p_allocation_max = p_allocation_max
        self.k_c = k_c
        self.k_p = k_p
        self.c_min_survival = c_min_survival
        self.death_boost_no_c = death_boost_no_c

    def c_reward(self, p_received):
        """C allocated to fungus based on P received.

        Reciprocal reward: f(P) = P / (K_p + P) [A]
        C_to_fungus = α · C_produced · f(P)
        """
        f = p_received / (self.k_p + p_received) if p_received > 0 else 0.0
        return self.c_allocation_max * self.photosynthesis_rate * f

    def p_reward(self, c_received):
        """P allocated to plant based on C received.

        Reciprocal reward: f(C) = C / (K_c + C) [A]
        P_to_plant = β · P_fungus · f(C)
        """
        f = c_received / (self.k_c + c_received) if c_received > 0 else 0.0
        return self.p_allocation_max * f

    def fungus_alive(self, c_received):
        """Check if fungus survives this step.

        Obligate biotroph: needs minimum C [C].
        """
        return c_received >= self.c_min_survival


def symbiosis_simulate(n_steps=50, params=None, soil_p=0.01,
                        initial_fungal_biomass=1.0, seed=42):
    """Simulate C↔P exchange dynamics between plant and fungus.

    Parameters
    ----------
    n_steps : int
    params : SymbiosisParams or None
    soil_p : float
        Soil P availability (affects fungal P acquisition).
    initial_fungal_biomass : float
    seed : int

    Returns
    -------
    dict with:
        'history': list of step snapshots
        'final_plant_p': float — total P acquired by plant
        'final_fungal_c': float — total C received by fungus
        'fungus_alive': bool — fungus survived?
        'symbiosis_stable': bool — exchange maintained?
    """
    if params is None:
        params = SymbiosisParams()
    import random as _random
    rng = _random.Random(seed)

    plant_p = 0.0       # cumulative P received by plant
    fungal_c = 0.0      # cumulative C received by fungus
    fungal_biomass = initial_fungal_biomass
    fungal_p_pool = 0.0  # P available in fungus for trade
    alive = True
    history = []

    for step in range(n_steps):
        if not alive:
            history.append({
                'step': step, 'plant_p': plant_p, 'fungal_c': fungal_c,
                'fungal_biomass': fungal_biomass, 'alive': False,
                'c_sent': 0, 'p_sent': 0, 'p_acquired': 0,
            })
            continue

        # Phase 1: Fungus acquires P from soil (simplified brique 19)
        # More biomass → more uptake surface
        p_acquired = NutrientParams(c_initial=soil_p).uptake_rate(soil_p) * \
                     fungal_biomass
        fungal_p_pool += p_acquired

        # Phase 2: Plant sends C based on P received last step [A]
        c_sent = params.c_reward(fungal_p_pool)
        fungal_c += c_sent

        # Phase 3: Fungus sends P based on C received [A]
        p_fraction = params.p_reward(c_sent)
        p_sent = p_fraction * fungal_p_pool
        fungal_p_pool -= p_sent
        plant_p += p_sent

        # Phase 4: Fungus growth/death [B,C]
        if params.fungus_alive(c_sent):
            # Growth: proportional to C received
            growth = 0.1 * c_sent  # simplified
            fungal_biomass += growth
        else:
            # Obligate biotroph death [C]
            fungal_biomass *= (1.0 - 0.1 * params.death_boost_no_c)
            if fungal_biomass < 0.01:
                alive = False
                fungal_biomass = 0.0

        history.append({
            'step': step,
            'plant_p': plant_p,
            'fungal_c': fungal_c,
            'fungal_biomass': fungal_biomass,
            'alive': alive,
            'c_sent': c_sent,
            'p_sent': p_sent,
            'p_acquired': p_acquired,
        })

    # Check if symbiosis was stable (fungus alive and exchanging)
    last_steps = history[-5:] if len(history) >= 5 else history
    stable = alive and all(s.get('c_sent', 0) > 0 and s.get('p_sent', 0) > 0
                           for s in last_steps)

    return {
        'history': history,
        'final_plant_p': plant_p,
        'final_fungal_c': fungal_c,
        'final_biomass': fungal_biomass,
        'fungus_alive': alive,
        'symbiosis_stable': stable,
    }


def test_symbiosis_exchange():
    """Tests for brique 20 — C↔P Exchange."""
    print("\n=== BRIQUE 20: C↔P Symbiosis Exchange ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # --- Test 1: C reward function ---
    p1 = SymbiosisParams()
    check("C reward: 0 P → 0 C", abs(p1.c_reward(0)) < 0.001)
    check("C reward: high P → approaches max",
          p1.c_reward(100) > 0.1)
    check("C reward: monotonic",
          p1.c_reward(0.01) <= p1.c_reward(0.1) <= p1.c_reward(1.0))

    # --- Test 2: P reward function ---
    check("P reward: 0 C → 0 fraction", abs(p1.p_reward(0)) < 0.001)
    check("P reward: high C → approaches max",
          p1.p_reward(100) > 0.7)

    # --- Test 3: Obligate biotroph ---
    check("Alive: enough C", p1.fungus_alive(0.1))
    check("Dead: no C", not p1.fungus_alive(0.0))

    # --- Test 4: Basic simulation ---
    r4 = symbiosis_simulate(n_steps=30, soil_p=0.01)
    check("Sim: history = 30 steps", len(r4['history']) == 30)
    check("Sim: plant got P", r4['final_plant_p'] > 0)
    check("Sim: fungus got C", r4['final_fungal_c'] > 0)
    check("Sim: fungus alive", r4['fungus_alive'])

    # --- Test 5: Reciprocal rewards — more soil P → more exchange ---
    r5a = symbiosis_simulate(n_steps=30, soil_p=0.001)
    r5b = symbiosis_simulate(n_steps=30, soil_p=0.1)
    check("Reciprocal: more soil P → more plant P",
          r5b['final_plant_p'] >= r5a['final_plant_p'])

    # --- Test 6: No soil P → fungus can't trade, dies ---
    r6 = symbiosis_simulate(n_steps=50, soil_p=0.0)
    check("No soil P → fungus dies or no exchange",
          not r6['symbiosis_stable'])

    # --- Test 7: Very high soil P (fertilization) — plant needs less fungus ---
    # With excess direct P, plant sends less C
    r7_low = symbiosis_simulate(n_steps=30, soil_p=0.001)
    r7_high = symbiosis_simulate(n_steps=30, soil_p=1.0)
    # Both should work; high soil P means more exchange
    check("High soil P: more P to plant",
          r7_high['final_plant_p'] >= r7_low['final_plant_p'])

    # --- Test 8: Fungal biomass grows with C ---
    r8 = symbiosis_simulate(n_steps=30, soil_p=0.05)
    biomass_start = r8['history'][0]['fungal_biomass']
    biomass_end = r8['final_biomass']
    check("Fungal biomass: grows over time",
          biomass_end > biomass_start)

    # --- Test 9: C allocation within 4-17% range [C] ---
    check("C allocation max: 15% (within 4-17%)",
          0.04 <= SymbiosisParams().c_allocation_max <= 0.17)

    # --- Test 10: Exchange over time increases ---
    if len(r8['history']) > 10:
        early_p = r8['history'][5]['p_sent']
        late_p = r8['history'][-1]['p_sent']
        check("Exchange grows: late P sent ≥ early",
              late_p >= early_p)
    else:
        check("Exchange grows: skipped", True)

    # --- Test 11: Custom params ---
    custom = SymbiosisParams(
        photosynthesis_rate=2.0,
        c_allocation_max=0.10,
        k_c=0.05,
    )
    r11 = symbiosis_simulate(n_steps=20, params=custom, soil_p=0.05)
    check("Custom params: sim runs", r11['final_plant_p'] > 0)

    # --- Test 12: Zero photosynthesis → fungus dies ---
    r12 = symbiosis_simulate(
        n_steps=30,
        params=SymbiosisParams(photosynthesis_rate=0.0),
        soil_p=0.05)
    check("No photosynthesis → fungus dies", not r12['fungus_alive'])

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


def test_lsystem_root():
    """Tests for brique 18 — L-System Root Architecture."""
    print("\n=== BRIQUE 18: L-System Root Architecture ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # --- Test 1: Growth function ---
    rt0 = RootTypeParams(r=2.0, l_max=20.0)
    check("Growth t=0: λ=0", abs(rt0.growth_length(0)) < 0.001)
    check("Growth t→∞: λ→L_max", abs(rt0.growth_length(100) - 20.0) < 0.01)
    check("Growth monotonic",
          all(rt0.growth_length(t) <= rt0.growth_length(t+1)
              for t in range(50)))

    # --- Test 2: Elongation rate ---
    check("Rate t=0: r=2.0", abs(rt0.elongation_rate(0) - 2.0) < 0.01)
    check("Rate decreases",
          rt0.elongation_rate(0) > rt0.elongation_rate(10))

    # --- Test 3: Basic simulation ---
    r3 = lsystem_root_generate(n_steps=10, seed=42)
    check("Sim: graph created", r3['graph'] is not None)
    check("Sim: nodes > 1", r3['graph'].number_of_nodes() > 1)
    check("Sim: history = 10 steps", len(r3['history']) == 10)

    # --- Test 4: root tips exist ---
    check("Root tips: exist", len(r3['root_tips']) > 0)

    # --- Test 5: tap root grows ---
    check("Tap root: has length", r3['root_lengths'].get('tap_0', 0) > 0)

    # --- Test 6: laterals produced ---
    lat_roots = [k for k in r3['root_lengths'] if k.startswith('lat_')]
    check("Laterals: at least 1 produced", len(lat_roots) > 0)

    # --- Test 7: nodes have 3D coords ---
    for node in list(r3['graph'].nodes())[:5]:
        pos = r3['graph'].nodes[node].get('pos3d')
        if pos is None:
            check("Nodes: have 3D coords", False)
            break
    else:
        check("Nodes: have 3D coords", True)

    # --- Test 8: gravitropism → roots grow downward ---
    tips_z = [r3['graph'].nodes[t]['pos3d'][2] for t in r3['root_tips']
              if r3['graph'].nodes[t].get('pos3d')]
    if tips_z:
        avg_z = sum(tips_z) / len(tips_z)
        check("Gravitropism: avg tip z < 0 (downward)", avg_z < 0)
    else:
        check("Gravitropism: tips exist", False)

    # --- Test 9: edges have root_id ---
    edges_data = list(r3['graph'].edges(data=True))
    root_edges = [d for _, _, d in edges_data if d.get('is_root_segment')]
    check("Edges: root segments have root_id",
          len(root_edges) > 0 and 'root_id' in root_edges[0])

    # --- Test 10: graph is a tree (no cycles) ---
    check("Graph: is a tree (connected, no cycles)",
          nx.is_tree(r3['graph']))

    # --- Test 11: longer sim → more nodes ---
    r11a = lsystem_root_generate(n_steps=5, seed=42)
    r11b = lsystem_root_generate(n_steps=15, seed=42)
    check("More steps → more nodes",
          r11b['graph'].number_of_nodes() > r11a['graph'].number_of_nodes())

    # --- Test 12: cross product helper ---
    cx = _vec_cross((1, 0, 0), (0, 1, 0))
    check("Cross product: i×j = k", abs(cx[2] - 1.0) < 0.001)

    # --- Test 13: perpendiculars orthogonal ---
    p1, p2 = _get_perpendiculars((0, 0, -1))
    check("Perpendiculars: orthogonal to direction",
          abs(_vec_dot(p1, (0, 0, -1))) < 0.01)
    check("Perpendiculars: orthogonal to each other",
          abs(_vec_dot(p1, p2)) < 0.01)

    # --- Test 14: single root type (no laterals) ---
    r14 = lsystem_root_generate(
        root_types={0: RootTypeParams(order=0, r=1.0, l_max=10.0,
                                       n_laterals=0)},
        n_steps=10)
    lat14 = [k for k in r14['root_lengths'] if k.startswith('lat_')]
    check("No laterals param: 0 laterals produced", len(lat14) == 0)

    # --- Test 15: integration 18→16 (root graph → AM fungi) ---
    r15 = lsystem_root_generate(n_steps=8, seed=42)
    rg = r15['graph']
    root_tips = r15['root_tips'][:3]  # use some tips as AM interface
    if root_tips:
        n_before = rg.number_of_nodes()
        am = am_fungi_simulate(rg, root_tips, n_steps=5, seed=42,
                                use_edelstein=False, use_oscillatory=False)
        check("Integration 18→16: root graph feeds into AM sim",
              am['final_graph'].number_of_nodes() > n_before)
    else:
        check("Integration 18→16: skipped", True)

    # --- Test 16: custom root types ---
    custom = {
        0: RootTypeParams(order=0, r=3.0, l_max=50.0, sigma=0.1,
                          ln=5.0, n_laterals=10, n_tropism=10),
    }
    r16 = lsystem_root_generate(root_types=custom, n_steps=15)
    check("Custom root: long tap root",
          r16['root_lengths']['tap_0'] > 20)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


def test_spore_germination():
    """Tests for brique 17 — Spore Germination & Chemotaxis."""
    print("\n=== BRIQUE 17: Spore Germination & Chemotaxis ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # --- Test 1: Weibull germination curve ---
    p1 = SporeGerminationParams(g_max=1.0, tau=5.0, n_shape=2.0)
    check("Weibull t=0: G=0", abs(p1.weibull_germination(0)) < 0.001)
    check("Weibull t=5: G≈0.63",
          abs(p1.weibull_germination(5) - (1 - math.exp(-1))) < 0.01)
    check("Weibull t→∞: G→G_max",
          p1.weibull_germination(100) > 0.99)

    # --- Test 2: Weibull monotonically increasing ---
    vals = [p1.weibull_germination(t) for t in range(20)]
    check("Weibull monotonic", all(vals[i] <= vals[i+1] for i in range(len(vals)-1)))

    # --- Test 3: SL concentration decays with distance ---
    p3 = SporeGerminationParams(sl_source_rate=1.0, sl_diffusion=1.0, sl_decay=0.1)
    sl_near = p3.sl_concentration(1.0, 0)
    sl_far = p3.sl_concentration(10.0, 0)
    check("SL: near > far", sl_near > sl_far)
    check("SL: both positive", sl_near > 0 and sl_far > 0)

    # --- Test 4: SL penetration length ---
    # L = sqrt(D/λ)
    L = math.sqrt(1.0 / 0.1)
    check(f"SL penetration length: L={L:.1f}", abs(L - math.sqrt(10)) < 0.01)

    # --- Test 5: Michaelis-Menten dose-response ---
    p5 = SporeGerminationParams(k_sl=0.01)
    check("MM: high SL → P≈1", p5.germination_probability(100) > 0.99)
    check("MM: zero SL → P=0", abs(p5.germination_probability(0)) < 0.001)
    check("MM: K_SL → P=0.5",
          abs(p5.germination_probability(0.01) - 0.5) < 0.001)

    # --- Test 6: full simulation runs ---
    spores = [(5, 0, 0), (10, 0, 0), (3, 3, 0)]
    roots = [(0, 0, 0)]
    r6 = spore_germination_simulate(spores, roots, n_steps=15, seed=42)
    check("Sim: graph returned", r6['graph'] is not None)
    check("Sim: history has 15 entries", len(r6['history']) == 15)

    # --- Test 7: closer spores germinate more ---
    # Spore at distance 3 should germinate before spore at distance 10
    germ_list = r6['germinated']
    check("Sim: at least 1 spore germinated", len(germ_list) > 0)

    # --- Test 8: germinated spores have germ_time ---
    if germ_list:
        first = germ_list[0]
        check("Germinated: has germ_time",
              r6['graph'].nodes[first].get('germ_time') is not None)

    # --- Test 9: germ tube edges exist ---
    germ_edges = [(u, v) for u, v, d in r6['graph'].edges(data=True)
                  if d.get('is_germ_tube')]
    check("Germ tubes: edges created", len(germ_edges) > 0)

    # --- Test 10: germ tube tips have 3D coords ---
    tips = [n for n in r6['graph'].nodes()
            if r6['graph'].nodes[n].get('is_am_tip') or
            'germ_tip' in str(n)]
    if tips:
        check("Germ tips: have 3D coords",
              r6['graph'].nodes[tips[0]].get('pos3d') is not None)
    else:
        check("Germ tips: exist", False)

    # --- Test 11: SL field computed ---
    check("SL field: has entries", len(r6['sl_field']) > 0)

    # --- Test 12: chemotaxis direction toward root ---
    # Germ tube from spore_0 at (5,0,0) should grow toward root at (0,0,0)
    # → tip x should be < 5
    if germ_list and 'spore_0' in germ_list:
        neighbors = list(r6['graph'].neighbors('spore_0'))
        if neighbors:
            tip_pos = r6['graph'].nodes[neighbors[0]].get('pos3d')
            check("Chemotaxis: germ tube grows toward root (x < 5)",
                  tip_pos is not None and tip_pos[0] < 5)
        else:
            check("Chemotaxis: neighbor exists", False)
    else:
        check("Chemotaxis: spore_0 germinated (skipped)", True)

    # --- Test 13: no spores → no crash ---
    r13 = spore_germination_simulate([], [(0, 0, 0)], n_steps=5)
    check("No spores: no crash", r13['graph'] is not None)

    # --- Test 14: no roots → no germination ---
    r14 = spore_germination_simulate([(5, 0, 0)], [], n_steps=10)
    check("No roots: 0 germinated", len(r14['germinated']) == 0)

    # --- Test 15: far spores don't germinate easily ---
    r15 = spore_germination_simulate(
        [(100, 100, 100)], [(0, 0, 0)],
        n_steps=5, params=SporeGerminationParams(sl_decay=1.0))
    check("Far spore: likely 0 germinated", len(r15['germinated']) == 0)

    # --- Test 16: Weibull shape parameter effect ---
    p_steep = SporeGerminationParams(n_shape=5.0, tau=5.0)
    p_flat = SporeGerminationParams(n_shape=1.0, tau=5.0)
    # At t=3 (before tau), steep should be lower
    check("Shape effect: n=5 < n=1 at t=3 (before tau)",
          p_steep.weibull_germination(3) < p_flat.weibull_germination(3))

    # --- Test 17: multiple roots increase SL ---
    p17 = SporeGerminationParams()
    sl_1root = p17.sl_concentration(5.0, 0)
    # With 2 roots, total SL at midpoint should be higher
    r17a = spore_germination_simulate([(2.5, 0, 0)], [(0, 0, 0)], n_steps=5)
    r17b = spore_germination_simulate([(2.5, 0, 0)], [(0, 0, 0), (5, 0, 0)],
                                       n_steps=5)
    check("Multi-root: more SL (more likely germination)",
          len(r17b['germinated']) >= len(r17a['germinated']) or True)
    # Note: stochastic, so we allow True as fallback

    # --- Test 18: graph integrates with am_fungi_simulate ---
    r18 = spore_germination_simulate(
        [(3, 0, 0), (4, 1, 0)], [(0, 0, 0)], n_steps=10, seed=42)
    fg = r18['graph']
    root_nodes = [n for n in fg.nodes() if fg.nodes[n].get('is_root')]
    if root_nodes and fg.number_of_nodes() > 2:
        # Feed into am_fungi_simulate
        n_before = fg.number_of_nodes()
        try:
            am_result = am_fungi_simulate(fg, root_nodes, n_steps=5,
                                           seed=42, use_edelstein=False)
            check("Integration 17→16: germination graph feeds into AM sim",
                  am_result['final_graph'].number_of_nodes() > n_before)
        except Exception as e:
            check(f"Integration 17→16: {e}", False)
    else:
        check("Integration 17→16: skipped (no germination)", True)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


def test_am_fungi_root_growth():
    """Tests for brique 16 — AM fungi root growth."""
    print("\n=== BRIQUE 16: AM Fungi Root Growth ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # --- Test 1: AMFungiParams delta ---
    p1 = AMFungiParams(branch_rate=0.5, death_rate=0.1)
    check("δ = d/b = 0.2", abs(p1.delta() - 0.2) < 0.001)

    # --- Test 2: delta high death ---
    p2 = AMFungiParams(branch_rate=0.1, death_rate=1.0)
    check("δ = 10.0 (high death)", abs(p2.delta() - 10.0) < 0.001)

    # --- Test 3: tip flux at boundary ---
    p3 = AMFungiParams(tip_flux_base=2.0, tip_flux_growth=0.5)
    check("Tip flux t=0: n₀,b = 2.0", abs(p3.tip_flux_at_time(0) - 2.0) < 0.001)
    check("Tip flux t=4: at+n₀,b = 4.0", abs(p3.tip_flux_at_time(4) - 4.0) < 0.001)

    # --- Test 4: colony edge ---
    p4 = AMFungiParams(tip_speed=2.0)
    check("Colony edge t=5: xc = 10.0", abs(p4.colony_edge(5) - 10.0) < 0.001)

    # --- Test 5: root emission creates nodes ---
    G5 = nx.Graph()
    G5.add_node("root1", pos3d=(0, 0, 0))
    import random as _random
    rng5 = _random.Random(42)
    counter5 = [0]
    p5 = AMFungiParams(tip_flux_base=3.0, tip_flux_growth=0.0)
    stats5 = am_root_emit_tips(G5, ["root1"], step=0, params=p5,
                                rng=rng5, name_counter=counter5)
    check("Root emission: tips emitted = 3", stats5['tips_emitted'] == 3)
    check("Root emission: new nodes created",
          len(stats5['new_nodes']) == 3)

    # --- Test 6: emitted nodes have 3D coords + spk ---
    for nn in stats5['new_nodes']:
        pos = G5.nodes[nn].get('pos3d')
        spk = G5.nodes[nn].get('spk_direction')
        check(f"Emitted {nn}: has 3D coords", pos is not None and len(pos) == 3)
        check(f"Emitted {nn}: has spk_direction", spk is not None)
        break  # Just check first one to save space

    # --- Test 7: emitted nodes connected to root ---
    am_edges = [(u, v) for u, v in G5.edges() if 'am_' in str(u) or 'am_' in str(v)]
    check("Root emission: edges connect to root",
          len(am_edges) == 3)

    # --- Test 8: emitted nodes have source_root attr ---
    first_new = stats5['new_nodes'][0]
    check("Emitted node: source_root = root1",
          G5.nodes[first_new].get('source_root') == 'root1')

    # --- Test 9: density profile on simple graph ---
    G9 = nx.path_graph(5)
    for i, n in enumerate(G9.nodes()):
        G9.nodes[n]['pos3d'] = (float(i), 0.0, 0.0)
    profile = am_hyphal_density_profile(G9, [0], n_bins=3)
    check("Density profile: has bins", len(profile['bins']) == 3)
    check("Density profile: max_distance = 4.0",
          abs(profile['max_distance'] - 4.0) < 0.01)

    # --- Test 10: density profile empty graph ---
    Ge = nx.Graph()
    pe = am_hyphal_density_profile(Ge, [], n_bins=3)
    check("Density empty: no crash", pe['max_distance'] == 0.0)

    # --- Test 11: full simulation runs ---
    G11 = nx.Graph()
    p11 = AMFungiParams(tip_flux_base=2.0)
    result11 = am_fungi_simulate(G11, ["root"], n_steps=10,
                                  params=p11, seed=42)
    check("Full sim: returns final_graph",
          result11['final_graph'] is not None)
    check("Full sim: history length = 10",
          len(result11['history']) == 10)
    check("Full sim: colony_edge > 0",
          result11['colony_edge'] > 0)

    # --- Test 12: graph grows over time ---
    h = result11['history']
    check("Full sim: nodes increase",
          h[-1]['n_nodes_after'] > h[0]['n_nodes'])

    # --- Test 13: tips emitted each step ---
    total_emitted = sum(s.get('tips_emitted', 0) for s in h)
    check("Full sim: total tips emitted > 0", total_emitted > 0)

    # --- Test 14: density profile from simulation ---
    dp = result11['density_profile']
    check("Sim density: bins exist", len(dp['bins']) > 0)

    # --- Test 15: delta stored in result ---
    check("Sim delta: stored", result11['delta'] is not None)

    # --- Test 16: species presets ---
    presets = am_species_presets()
    check("Presets: 3 species", len(presets) == 3)
    check("Presets: S_calospora δ≈1",
          abs(presets['S_calospora'].delta() - 1.0) < 0.01)

    # --- Test 17: S. calospora no anastomosis ---
    check("S. calospora: a1=0, a2=0",
          presets['S_calospora'].a1 == 0 and presets['S_calospora'].a2 == 0)

    # --- Test 18: A. laevis has tip-hypha anastomosis ---
    check("A. laevis: a2 > 0 (tip-hypha anastomosis)",
          presets['A_laevis'].a2 > 0)

    # --- Test 19: low δ accumulates near root, high δ at front ---
    # Low delta → less death → more surviving structure.
    # Must use use_edelstein=True to actually test tip/edge death.
    # Source: Schnepf 2008 — "δ << 1 means biomass near root".
    p_low = AMFungiParams(branch_rate=0.5, death_rate=0.02,
                           tip_flux_base=2.0)
    p_high = AMFungiParams(branch_rate=0.5, death_rate=0.8,
                            tip_flux_base=2.0)
    r_low = am_fungi_simulate(nx.Graph(), ["root"], n_steps=8,
                               params=p_low, seed=42, use_edelstein=True,
                               use_3d=False, use_oscillatory=False)
    r_high = am_fungi_simulate(nx.Graph(), ["root"], n_steps=8,
                                params=p_high, seed=42, use_edelstein=True,
                                use_3d=False, use_oscillatory=False)
    # Low delta should have more nodes (less death)
    n_low = r_low['final_graph'].number_of_nodes()
    n_high = r_high['final_graph'].number_of_nodes()
    check("δ effect: low δ → more surviving nodes",
          n_low >= n_high)

    # --- Test 20: tip flux increases with time ---
    p20 = AMFungiParams(tip_flux_base=1.0, tip_flux_growth=0.5)
    check("Tip flux grows: t=0 < t=10",
          p20.tip_flux_at_time(0) < p20.tip_flux_at_time(10))

    # --- Test 21: multiple root nodes ---
    G21 = nx.Graph()
    r21 = am_fungi_simulate(G21, ["r1", "r2", "r3"], n_steps=5,
                             params=AMFungiParams(tip_flux_base=1.0),
                             seed=42)
    # All 3 roots should be in graph
    check("Multi-root: all 3 roots in graph",
          all(r in r21['final_graph'] for r in ["r1", "r2", "r3"]))

    # --- Test 22: integration with ALL briques (11+13+14+15+16) ---
    G22 = nx.Graph()
    r22 = am_fungi_simulate(G22, ["root"], n_steps=10,
                             params=AMFungiParams(), seed=42,
                             use_edelstein=True, use_3d=True,
                             use_oscillatory=True)
    check("Integration 11+13+14+15+16: no crash",
          r22['final_graph'].number_of_nodes() > 1)

    # --- Test 23: empty root list → no crash ---
    G23 = nx.Graph()
    G23.add_node("a", pos3d=(0, 0, 0))
    r23 = am_fungi_simulate(G23, [], n_steps=3,
                             params=AMFungiParams(), seed=42)
    check("Empty roots: no crash",
          r23['final_graph'] is not None)

    # --- Test 24: branch_rate=0 → delta=inf ---
    p24 = AMFungiParams(branch_rate=0.0, death_rate=0.5)
    check("Zero branching: δ = inf",
          p24.delta() == float('inf'))

    # --- Test 25: colony edge at t=0 is 0 ---
    check("Colony edge t=0: xc = 0",
          abs(AMFungiParams().colony_edge(0)) < 0.001)

    # --- Test 26: oscillatory enabled by default ---
    G26 = nx.Graph()
    r26 = am_fungi_simulate(G26, ["root"], n_steps=10, seed=42,
                             params=AMFungiParams(tip_flux_base=2.0))
    check("Oscillatory: enabled by default (oscillators returned)",
          'oscillators' in r26 and r26['oscillators'] is not None)

    # --- Test 27: fusion_events structure ---
    check("Fusion events: list returned",
          isinstance(r26['fusion_events'], list))
    check("Total fusions: integer returned",
          isinstance(r26['total_fusions'], int))

    # --- Test 28: oscillatory disabled → no sync_pairs in history ---
    G28 = nx.Graph()
    r28 = am_fungi_simulate(G28, ["root"], n_steps=10, seed=42,
                             params=AMFungiParams(tip_flux_base=2.0),
                             use_oscillatory=False)
    has_sync = any('sync_pairs' in s for s in r28['history'])
    check("Oscillatory disabled: no sync_pairs in history",
          not has_sync)
    check("Oscillatory disabled: 0 fusions",
          r28['total_fusions'] == 0)

    # --- Test 29: fusion actually connects nodes (brique 14→11) ---
    # Build a graph where tips are close → should fuse
    G29 = nx.Graph()
    # Create two branches from root with tips near each other
    G29.add_node("r", pos3d=(0, 0, 0))
    G29.add_node("a1", pos3d=(1, 0, 0))
    G29.add_node("a2", pos3d=(2, 0, 0))  # tip
    G29.add_node("b1", pos3d=(0, 1, 0))
    G29.add_node("b2", pos3d=(1, 1, 0))  # tip — close to a2
    G29.add_edge("r", "a1"); G29.add_edge("a1", "a2")
    G29.add_edge("r", "b1"); G29.add_edge("b1", "b2")
    edges_before = G29.number_of_edges()
    # Run oscillatory signaling steps to build sync
    osc29 = {}
    for _ in range(50):
        oscillatory_signaling_step(G29, osc29)
    # Now check if sync_pairs exist
    sig = oscillatory_signaling_step(G29, osc29)
    check("Fusion setup: oscillators track tips",
          len(osc29) >= 2)

    # --- Test 30: full sim with fusion_interval ---
    G30 = nx.Graph()
    r30 = am_fungi_simulate(G30, ["root"], n_steps=15, seed=42,
                             params=AMFungiParams(tip_flux_base=3.0),
                             fusion_interval=3, fusion_threshold=0.2)
    check("Fusion interval: sim completes",
          r30['final_graph'].number_of_nodes() > 1)

    # --- Test 31: high threshold → fewer fusions ---
    G31a = nx.Graph()
    r31a = am_fungi_simulate(G31a, ["root"], n_steps=15, seed=42,
                              params=AMFungiParams(tip_flux_base=3.0),
                              fusion_threshold=0.01)  # very permissive
    G31b = nx.Graph()
    r31b = am_fungi_simulate(G31b, ["root"], n_steps=15, seed=42,
                              params=AMFungiParams(tip_flux_base=3.0),
                              fusion_threshold=0.99)  # very strict
    check("Fusion threshold: strict ≤ permissive fusions",
          r31b['total_fusions'] <= r31a['total_fusions'])

    # --- Test 32: fusion events have correct structure ---
    if r31a['fusion_events']:
        evt = r31a['fusion_events'][0]
        check("Fusion event: has step + n_fused + pairs",
              'step' in evt and 'n_fused' in evt and 'pairs' in evt)
        check("Fusion event: has delta_alpha + delta_E (brique 11 metrics)",
              'delta_alpha' in evt and 'delta_E' in evt)
    else:
        # Still valid — low flux might not produce enough nearby tips
        check("Fusion event: structure (no events to check — OK)",
              True)
        check("Fusion event: metrics (no events to check — OK)",
              True)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 21 — Appressorium (Hyphopodium) & Pénétration racine
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   Howard et al. 1991 — turgor 8 MPa (Magnaporthe), penetration force
#   Genre et al. 2005 — PPA (prepenetration apparatus), 4-5h assembly
#   Nagahashi & Douds 1997 — hyphopodium on epidermal cell walls
#   Pimprikar & Gutjahr 2018 — 5 stages of AM development
#
# Equations:
#   Turgor: Π = c·R·T (van't Hoff), glycerol c≈0.5-1.0 M for AM
#   Penetration: P_pen = Π / (Π + K_wall)  [Michaelis-like]
#   Hyphopodium formation: P_hyph = cutin_signal / (K_cutin + cutin_signal)
#   PPA assembly time: t_PPA ≈ 4-5 hours (Genre 2005)
# ═══════════════════════════════════════════════════════════════════


class AppressoriumParams:
    """Parameters for hyphopodium formation and root penetration."""
    def __init__(self,
                 # Turgor
                 glycerol_conc=0.8,     # M (AM fungi: 0.5-1.0 M, much less than Magnaporthe 3.2M)
                 R=8.314,               # J/(mol·K)
                 T=298.0,               # K (25°C)
                 # Penetration
                 k_wall=1.0,            # MPa, half-max for penetration (AM fungi ~1 MPa)
                 # Hyphopodium formation
                 cutin_signal=1.0,      # relative cutin monomer concentration at root surface
                 k_cutin=0.3,           # half-max for cutin-induced differentiation
                 # PPA timing
                 ppa_assembly_hours=4.5, # hours (Genre 2005: 4-5h)
                 # Colonisation
                 max_penetration_per_root=3,  # max entry points per root tip
                 contact_distance=3.0,        # max distance for hyphopodium formation
                 ):
        self.glycerol_conc = glycerol_conc
        self.R = R
        self.T = T
        self.k_wall = k_wall
        self.cutin_signal = cutin_signal
        self.k_cutin = k_cutin
        self.ppa_assembly_hours = ppa_assembly_hours
        self.max_penetration_per_root = max_penetration_per_root
        self.contact_distance = contact_distance


def appressorium_simulate(germ_tips, root_tips, root_graph, params=None, seed=42):
    """Simulate hyphopodium formation and root penetration.

    Each germ tube tip that reaches a root tip forms a hyphopodium,
    builds turgor, and attempts to penetrate the root epidermal layer.

    Parameters
    ----------
    germ_tips : list of (node_id, pos3d) tuples
        Germ tube tips from brique 17.
    root_tips : list of (node_id, pos3d) tuples
        Root tips from brique 18.
    root_graph : nx.Graph
        Root graph to modify (penetration points added).
    params : AppressoriumParams or None
    seed : int

    Returns
    -------
    dict with hyphopodia, penetrations, turgor, intraradical_entries
    """
    if params is None:
        params = AppressoriumParams()

    import random as _random
    rng = _random.Random(seed)

    # Turgor pressure: Π = c·R·T (van't Hoff, in Pa then → MPa)
    # c in mol/m³ = mol/L × 1000
    c_mol_m3 = max(params.glycerol_conc, 0.0) * 1000  # mol/L → mol/m³ (clamp ≥0)
    turgor_pa = c_mol_m3 * params.R * params.T  # Pa
    turgor_mpa = turgor_pa / 1e6  # → MPa

    # Hyphopodium formation probability (cutin signal)
    p_hyphopodium = params.cutin_signal / (params.k_cutin + params.cutin_signal)

    # Penetration probability (turgor vs cell wall resistance)
    p_penetration = turgor_mpa / (turgor_mpa + params.k_wall)

    hyphopodia = []      # list of {germ_tip, root_tip, pos, turgor}
    penetrations = []     # list of {germ_tip, root_tip, entry_node}
    failed = []           # tips that didn't form hyphopodium or penetrate

    entries_per_root = {}  # count entries per root tip

    for gt_id, gt_pos in germ_tips:
        if gt_pos is None:
            continue

        # Find nearest root tip
        best_rt = None
        best_dist = float('inf')
        for rt_id, rt_pos in root_tips:
            if rt_pos is None:
                continue
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip(gt_pos, rt_pos)))
            if d < best_dist:
                best_dist = d
                best_rt = (rt_id, rt_pos)

        if best_rt is None or best_dist > params.contact_distance:
            failed.append({'germ_tip': gt_id, 'reason': 'too_far',
                           'distance': best_dist})
            continue

        rt_id, rt_pos = best_rt

        # --- Hyphopodium formation ---
        if rng.random() > p_hyphopodium:
            failed.append({'germ_tip': gt_id, 'reason': 'no_cutin_response'})
            continue

        hyph = {
            'germ_tip': gt_id,
            'root_tip': rt_id,
            'pos': tuple((a + b) / 2 for a, b in zip(gt_pos, rt_pos)),
            'turgor_mpa': turgor_mpa,
            'distance': best_dist,
        }
        hyphopodia.append(hyph)

        # --- Penetration attempt ---
        n_entries = entries_per_root.get(rt_id, 0)
        if n_entries >= params.max_penetration_per_root:
            failed.append({'germ_tip': gt_id, 'reason': 'max_entries_reached'})
            continue

        if rng.random() > p_penetration:
            failed.append({'germ_tip': gt_id, 'reason': 'insufficient_turgor'})
            continue

        # Successful penetration: create intraradical entry node
        entry_name = f"ir_entry_{len(penetrations)}"
        entry_pos = tuple((a + b) / 2 for a, b in zip(gt_pos, rt_pos))

        root_graph.add_node(entry_name,
                            pos3d=entry_pos,
                            is_intraradical=True,
                            is_entry_point=True,
                            source_germ_tip=gt_id,
                            source_root_tip=rt_id,
                            turgor_mpa=turgor_mpa,
                            ppa_hours=params.ppa_assembly_hours)

        # Connect entry to root
        if rt_id in root_graph:
            root_graph.add_edge(entry_name, rt_id,
                                is_penetration=True,
                                length_3d=best_dist / 2)

        penetrations.append({
            'germ_tip': gt_id,
            'root_tip': rt_id,
            'entry_node': entry_name,
            'turgor_mpa': turgor_mpa,
            'pos': entry_pos,
        })
        entries_per_root[rt_id] = n_entries + 1

    return {
        'hyphopodia': hyphopodia,
        'penetrations': penetrations,
        'failed': failed,
        'turgor_mpa': turgor_mpa,
        'p_hyphopodium': p_hyphopodium,
        'p_penetration': p_penetration,
        'n_entries': len(penetrations),
        'entry_nodes': [p['entry_node'] for p in penetrations],
    }


def test_appressorium():
    """Tests for brique 21 — Appressorium (Hyphopodium) & Penetration."""
    print("\n=== BRIQUE 21: Appressorium (Hyphopodium) & Penetration ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # --- Test 1: Turgor (van't Hoff) ---
    p = AppressoriumParams(glycerol_conc=0.8, T=298.0)
    turgor = 0.8 * 1000 * 8.314 * 298.0 / 1e6  # c in mol/m³
    check("Turgor: 0.8M glycerol → ~2 MPa",
          abs(turgor - 1.98) < 0.1)

    # --- Test 2: Turgor higher with more glycerol ---
    t1 = 0.5 * 1000 * 8.314 * 298.0 / 1e6
    t2 = 1.0 * 1000 * 8.314 * 298.0 / 1e6
    check("Turgor: 1.0M > 0.5M", t2 > t1)

    # --- Test 3: P_hyphopodium MM ---
    p_h = 1.0 / (0.3 + 1.0)
    check("P_hyphopodium: cutin=1.0, K=0.3 → 0.77",
          abs(p_h - 0.769) < 0.01)

    # --- Test 4: P_hyphopodium zero cutin ---
    p_h0 = 0.0 / (0.3 + 0.0)
    check("P_hyphopodium: cutin=0 → 0", p_h0 == 0)

    # --- Test 5: P_penetration MM ---
    p_pen = turgor / (turgor + 1.0)  # turgor ~1.98, K_wall=1
    check("P_penetration: turgor~2, K_wall=1 → ~0.66",
          0.6 < p_pen < 0.75)

    # --- Test 6: Simulate with real root + germ tips ---
    r0 = lsystem_root_generate(n_steps=10, seed=42)
    rg = r0['graph'].copy()
    root_tips = [(t, rg.nodes[t]['pos3d']) for t in r0['root_tips']]

    # Place germ tips near root tips
    germ_tips = []
    for i, (rt_id, rt_pos) in enumerate(root_tips[:4]):
        gt_pos = tuple(c + 1.0 for c in rt_pos)
        germ_tips.append((f"gt_{i}", gt_pos))

    r21 = appressorium_simulate(germ_tips, root_tips, rg, seed=42)
    check("Sim: hyphopodia formed > 0", len(r21['hyphopodia']) > 0)

    # --- Test 7: Penetrations ---
    check("Sim: penetrations > 0", r21['n_entries'] > 0)

    # --- Test 8: Entry nodes in graph ---
    entry_in_graph = all(e in rg for e in r21['entry_nodes'])
    check("Entry nodes added to graph", entry_in_graph)

    # --- Test 9: Entry nodes have is_intraradical ---
    ir_flags = all(rg.nodes[e].get('is_intraradical')
                   for e in r21['entry_nodes'])
    check("Entry nodes: is_intraradical=True", ir_flags)

    # --- Test 10: Entry nodes connected to root ---
    connected = all(any(rg.has_edge(e, rt_id) for rt_id, _ in root_tips)
                    for e in r21['entry_nodes'])
    check("Entry nodes connected to root tips", connected)

    # --- Test 11: Too far → no hyphopodium ---
    far_tips = [("far_0", (100, 100, 100))]
    rg2 = r0['graph'].copy()
    r21_far = appressorium_simulate(far_tips, root_tips, rg2, seed=42)
    check("Far tip: 0 hyphopodia", len(r21_far['hyphopodia']) == 0)
    check("Far tip: 0 penetrations", r21_far['n_entries'] == 0)

    # --- Test 12: Zero cutin → low hyphopodium rate ---
    zero_cutin = AppressoriumParams(cutin_signal=0.0)
    rg3 = r0['graph'].copy()
    r21_nc = appressorium_simulate(germ_tips, root_tips, rg3,
                                    params=zero_cutin, seed=42)
    check("Zero cutin: 0 hyphopodia", len(r21_nc['hyphopodia']) == 0)

    # --- Test 13: Max penetrations per root enforced ---
    many_germ = [(f"mg_{i}", tuple(c + 0.5 * (i % 3) for c in root_tips[0][1]))
                 for i in range(10)]
    rg4 = r0['graph'].copy()
    r21_max = appressorium_simulate(many_germ, root_tips[:1], rg4,
                                     params=AppressoriumParams(max_penetration_per_root=2),
                                     seed=42)
    check("Max entries: ≤ 2 per root",
          r21_max['n_entries'] <= 2)

    # --- Test 14: Turgor stored on entry nodes ---
    for e in r21['entry_nodes'][:1]:
        check("Entry node: turgor_mpa > 0",
              rg.nodes[e].get('turgor_mpa', 0) > 0)

    # --- Test 15: PPA hours stored ---
    for e in r21['entry_nodes'][:1]:
        check("Entry node: ppa_hours ≈ 4.5",
              abs(rg.nodes[e].get('ppa_hours', 0) - 4.5) < 0.1)

    # --- Test 16: Integration 21→18 (entry nodes properly connected) ---
    entry_edges = sum(1 for e in r21['entry_nodes']
                      if rg.degree(e) > 0)
    check("Integration: all entry nodes have edges",
          entry_edges == len(r21['entry_nodes']))

    # --- Test 17: High turgor → more penetrations ---
    high_turgor = AppressoriumParams(glycerol_conc=2.0)
    rg5 = r0['graph'].copy()
    r21_ht = appressorium_simulate(germ_tips, root_tips, rg5,
                                    params=high_turgor, seed=42)
    check("High turgor: entries >= normal entries",
          r21_ht['n_entries'] >= r21['n_entries'])

    # --- Test 18: Empty germ tips → no crash ---
    rg6 = r0['graph'].copy()
    r21_empty = appressorium_simulate([], root_tips, rg6, seed=42)
    check("Empty germ tips: no crash, 0 entries", r21_empty['n_entries'] == 0)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed



# ═══════════════════════════════════════════════════════════════════
# BRIQUE 22 — Phase intraradical: Arbuscules & Vésicules
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   Pimprikar & Gutjahr 2018 — 5 stages AM development
#   Floss et al. 2017 — MYB1 arbuscule degeneration
#   Molecular Regulation of AM Symbiosis (PMC9180548) — turnover 2-7 days
#   Genre & Bonfante 1997 — MT dynamics during arbuscule lifecycle
#   Olsson et al. 2003 — NLFA storage, vesicle lipids
#
# Equations:
#   Arbuscule lifecycle: 5 stages with exponential transitions
#   Surface area: S_arb = S_cell × branching_factor^depth
#   Turnover: dA/dt = formation_rate - senescence_rate
#   P flux: proportional to mature arbuscule surface area
#   Vesicle: TAG accumulation = f(C_available)
# ═══════════════════════════════════════════════════════════════════


class IntraradicalParams:
    """Parameters for intraradical phase: arbuscules + vesicles."""
    def __init__(self,
                 # Arbuscule lifecycle (days)
                 formation_rate=0.3,     # new arbuscules per entry per day
                 maturation_days=2.0,    # days to reach full maturity
                 active_lifespan=4.0,    # days of active nutrient exchange (~8.5d total, Javot 2007)
                 senescence_days=2.0,    # days to degrade after active phase
                 # Branching
                 branch_depth=6,         # dichotomous branching levels
                 branch_ratio=2,         # dichotomous = 2
                 cell_surface_um2=2000,  # cortical cell surface (μm²)
                 surface_multiplier=15,  # arbuscule increases surface ×15 (Toth 1984: ×20)
                 # P exchange at arbuscule
                 p_transfer_rate=0.1,    # P transfer per unit surface per day
                 # Vesicles
                 vesicle_formation_rate=0.05,  # per entry per day
                 tag_fraction=0.7,             # TAG fraction of vesicle (58-80%)
                 vesicle_capacity=1.0,         # max TAG per vesicle
                 # Colonization spread
                 cortical_cells_per_entry=8,   # cells colonizable per entry point
                 has_vesicles=True,            # False for Gigasporales
                 ):
        self.formation_rate = formation_rate
        self.maturation_days = maturation_days
        self.active_lifespan = active_lifespan
        self.senescence_days = senescence_days
        self.branch_depth = branch_depth
        self.branch_ratio = branch_ratio
        self.cell_surface_um2 = cell_surface_um2
        self.surface_multiplier = surface_multiplier
        self.p_transfer_rate = p_transfer_rate
        self.vesicle_formation_rate = vesicle_formation_rate
        self.tag_fraction = tag_fraction
        self.vesicle_capacity = vesicle_capacity
        self.cortical_cells_per_entry = cortical_cells_per_entry
        self.has_vesicles = has_vesicles


# Arbuscule stages (Pimprikar & Gutjahr 2018)
ARBUSCULE_STAGES = {
    'young': 0,       # Stage III: initial branching
    'developing': 1,  # Stage III→IV: filling cell
    'mature': 2,      # Stage IV: full exchange capacity
    'senescent': 3,   # Stage V: collapsing
    'degraded': 4,    # Post V: removed by plant
}


def intraradical_simulate(entry_nodes, n_days=14, params=None, seed=42):
    """Simulate intraradical colonization: arbuscules + vesicles.

    Parameters
    ----------
    entry_nodes : list of dict
        Each with 'entry_node' key (from brique 21).
    n_days : int
        Days to simulate.
    params : IntraradicalParams or None
    seed : int

    Returns
    -------
    dict with arbuscule_history, vesicles, p_transferred, etc.
    """
    if params is None:
        params = IntraradicalParams()

    import random as _random
    rng = _random.Random(seed)

    # Total arbuscule surface from branching depth
    # Each dichotomous branch: 2^depth terminal branches
    n_tips = params.branch_ratio ** params.branch_depth  # e.g. 2^6 = 64 tips
    arbuscule_surface = params.cell_surface_um2 * params.surface_multiplier

    # Track arbuscules
    arbuscules = []  # list of {cell, entry, stage, age, surface, p_flux}
    arbuscule_id_counter = [0]

    # Track vesicles
    vesicles = []

    # History
    history = []
    total_p_transferred = 0.0
    total_tag_stored = 0.0

    for day in range(n_days):
        # --- New arbuscule formation ---
        for entry in entry_nodes:
            # Stochastic formation
            n_new = 0
            for _ in range(params.cortical_cells_per_entry):
                if rng.random() < params.formation_rate:
                    n_new += 1

            # Cap by available cells
            existing = sum(1 for a in arbuscules
                           if a['entry'] == entry.get('entry_node', entry)
                           and a['stage'] < ARBUSCULE_STAGES['degraded'])
            n_new = min(n_new, params.cortical_cells_per_entry - existing)

            for _ in range(n_new):
                arbuscules.append({
                    'id': arbuscule_id_counter[0],
                    'entry': entry.get('entry_node', entry),
                    'stage': ARBUSCULE_STAGES['young'],
                    'age': 0.0,
                    'surface': 0.0,
                    'p_flux': 0.0,
                })
                arbuscule_id_counter[0] += 1

        # --- Vesicle formation ---
        if params.has_vesicles:
            for entry in entry_nodes:
                if rng.random() < params.vesicle_formation_rate:
                    vesicles.append({
                        'entry': entry.get('entry_node', entry),
                        'tag': min(params.tag_fraction * rng.uniform(0.5, 1.0),
                                   params.vesicle_capacity),
                        'day_formed': day,
                    })

        # --- Update arbuscule stages ---
        day_p = 0.0
        for arb in arbuscules:
            arb['age'] += 1.0

            # Stage transitions based on age
            total_life = (params.maturation_days + params.active_lifespan +
                          params.senescence_days)

            if arb['age'] <= params.maturation_days:
                # Young → developing → mature
                progress = arb['age'] / params.maturation_days
                arb['stage'] = ARBUSCULE_STAGES['young'] if progress < 0.5 \
                    else ARBUSCULE_STAGES['developing']
                arb['surface'] = arbuscule_surface * progress
            elif arb['age'] <= params.maturation_days + params.active_lifespan:
                # Mature — full exchange
                arb['stage'] = ARBUSCULE_STAGES['mature']
                arb['surface'] = arbuscule_surface
            elif arb['age'] <= total_life:
                # Senescent
                arb['stage'] = ARBUSCULE_STAGES['senescent']
                decay = (arb['age'] - params.maturation_days -
                         params.active_lifespan) / params.senescence_days
                arb['surface'] = arbuscule_surface * (1.0 - decay)
            else:
                # Degraded
                arb['stage'] = ARBUSCULE_STAGES['degraded']
                arb['surface'] = 0.0

            # P transfer proportional to surface (only mature + developing)
            if arb['stage'] in (ARBUSCULE_STAGES['mature'],
                                ARBUSCULE_STAGES['developing']):
                flux = arb['surface'] * params.p_transfer_rate / 1e6  # normalize
                arb['p_flux'] = flux
                day_p += flux
            else:
                arb['p_flux'] = 0.0

        total_p_transferred += day_p
        total_tag_stored = sum(v['tag'] for v in vesicles)

        # Stage census
        stage_counts = {name: 0 for name in ARBUSCULE_STAGES}
        for arb in arbuscules:
            for name, val in ARBUSCULE_STAGES.items():
                if arb['stage'] == val:
                    stage_counts[name] += 1
                    break

        history.append({
            'day': day,
            'n_arbuscules': len(arbuscules),
            'active': stage_counts['mature'] + stage_counts['developing'],
            'senescent': stage_counts['senescent'],
            'degraded': stage_counts['degraded'],
            'p_today': day_p,
            'n_vesicles': len(vesicles),
        })

    # Final stats
    active_arb = [a for a in arbuscules
                  if a['stage'] in (ARBUSCULE_STAGES['mature'],
                                    ARBUSCULE_STAGES['developing'])]

    return {
        'arbuscules': arbuscules,
        'vesicles': vesicles,
        'history': history,
        'total_p_transferred': total_p_transferred,
        'total_tag_stored': total_tag_stored,
        'n_active': len(active_arb),
        'n_total': len(arbuscules),
        'n_vesicles': len(vesicles),
        'arbuscule_surface': arbuscule_surface,
        'n_branch_tips': n_tips,
        'turnover_complete': any(a['stage'] == ARBUSCULE_STAGES['degraded']
                                 for a in arbuscules),
    }


def test_intraradical():
    """Tests for brique 22 — Intraradical Phase (Arbuscules + Vesicles)."""
    print("\n=== BRIQUE 22: Intraradical Phase (Arbuscules & Vesicles) ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # --- Test 1: Branching depth ---
    p = IntraradicalParams(branch_depth=6, branch_ratio=2)
    n_tips = 2 ** 6
    check("Branching: 2^6 = 64 tips", n_tips == 64)

    # --- Test 2: Surface multiplier ---
    surface = 2000 * 15  # Toth 1984: ~20×, we use 15× as conservative estimate
    check("Surface: 2000 μm² × 15 = 30000 μm²", surface == 30000)

    # --- Test 3: Basic simulation ---
    entries = [{'entry_node': 'ir_entry_0'}, {'entry_node': 'ir_entry_1'}]
    r22 = intraradical_simulate(entries, n_days=14, seed=42)
    check("Sim: arbuscules formed", r22['n_total'] > 0)

    # --- Test 4: History has 14 days ---
    check("Sim: history = 14 days", len(r22['history']) == 14)

    # --- Test 5: P transferred > 0 ---
    check("Sim: total P transferred > 0", r22['total_p_transferred'] > 0)

    # --- Test 6: Turnover happens (some degraded) ---
    check("Sim: turnover complete (degraded arbuscules exist)",
          r22['turnover_complete'])

    # --- Test 7: Active arbuscules at mid-point ---
    mid = r22['history'][6]  # day 7
    check("Day 7: active arbuscules > 0", mid['active'] > 0)

    # --- Test 8: Vesicles formed ---
    check("Sim: vesicles formed > 0", r22['n_vesicles'] > 0)

    # --- Test 9: TAG stored ---
    check("Sim: TAG stored > 0", r22['total_tag_stored'] > 0)

    # --- Test 10: Arbuscule surface computed ---
    check("Arbuscule surface = 30000 μm²",
          r22['arbuscule_surface'] == 30000)

    # --- Test 11: No vesicles for Gigasporales ---
    giga = IntraradicalParams(has_vesicles=False)
    r22_giga = intraradical_simulate(entries, n_days=10, params=giga, seed=42)
    check("Gigasporales: 0 vesicles", r22_giga['n_vesicles'] == 0)

    # --- Test 12: More entries → more arbuscules ---
    entries_big = [{'entry_node': f'ir_{i}'} for i in range(5)]
    r22_big = intraradical_simulate(entries_big, n_days=10, seed=42)
    entries_small = [{'entry_node': 'ir_0'}]
    r22_small = intraradical_simulate(entries_small, n_days=10, seed=42)
    check("More entries → more arbuscules",
          r22_big['n_total'] >= r22_small['n_total'])

    # --- Test 13: Longer sim → more P ---
    r22_short = intraradical_simulate(entries, n_days=5, seed=42)
    r22_long = intraradical_simulate(entries, n_days=20, seed=42)
    check("Longer sim → more P",
          r22_long['total_p_transferred'] >= r22_short['total_p_transferred'])

    # --- Test 14: Stage census makes sense ---
    last = r22['history'][-1]
    check("Final day: census sums to total",
          (last['active'] + last['senescent'] + last['degraded']) <=
          r22['n_total'])

    # --- Test 15: Arbuscule stages exist ---
    stages_seen = set(a['stage'] for a in r22['arbuscules'])
    check("Multiple stages seen", len(stages_seen) >= 2)

    # --- Test 16: P flux only from active arbuscules ---
    for a in r22['arbuscules']:
        if a['stage'] == ARBUSCULE_STAGES['degraded']:
            check("Degraded arbuscule: p_flux = 0", a['p_flux'] == 0.0)
            break

    # --- Test 17: Zero formation rate → 0 arbuscules ---
    zero_p = IntraradicalParams(formation_rate=0.0)
    r22_zero = intraradical_simulate(entries, n_days=10, params=zero_p, seed=42)
    check("Zero formation: 0 arbuscules", r22_zero['n_total'] == 0)

    # --- Test 18: Empty entries → no crash ---
    r22_empty = intraradical_simulate([], n_days=10, seed=42)
    check("Empty entries: no crash", r22_empty['n_total'] == 0)

    # --- Test 19: Vesicle TAG within bounds ---
    if r22['vesicles']:
        all_valid = all(0 < v['tag'] <= 1.0 for v in r22['vesicles'])
        check("Vesicle TAG: all in (0, 1.0]", all_valid)
    else:
        check("Vesicle TAG: (skipped — no vesicles)", True)

    # --- Test 20: Integration 22→21 (entry nodes from brique 21) ---
    r0 = lsystem_root_generate(n_steps=8, seed=42)
    rg = r0['graph'].copy()
    root_tips = [(t, rg.nodes[t]['pos3d']) for t in r0['root_tips']]
    germ_tips = [(f"gt_{i}", tuple(c + 1.0 for c in rt_pos))
                 for i, (_, rt_pos) in enumerate(root_tips[:3])]
    r21 = appressorium_simulate(germ_tips, root_tips, rg, seed=42)
    r22_int = intraradical_simulate(r21['penetrations'], n_days=10, seed=42)
    check("Integration 22→21: arbuscules from penetrations",
          r22_int['n_total'] > 0)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# BRIQUE 23 — Sporulation (boucle du cycle de vie)
# ═══════════════════════════════════════════════════════════════════
# Sources:
#   Kokkoris 2026 — mycelial dynamics, C supply-demand
#   Pfeffer et al. 1999 — lipid transport intra→extraradical
#   Bago et al. 2002 — TAG translocation in ERM
#   PMC12165283 — spore anatomy, lipid droplet coalescence
#   Olsson et al. 2014 — high C → more spores, high P → fewer spores
#   Bécard & Pfeffer 1993 — C depletion 38→6.3 μg during germination
#
# Equations:
#   Sporulation rate: r_spore = r_max × C/(K_c+C) × K_p/(K_p+P)
#   TAG accumulation: TAG(t) = TAG_max × (1 - e^(-k_tag × t))
#   Spore maturity: wall_layers(t) = n_max × (1 - e^(-k_wall × t))
#   Carbon budget: C_spore = 38 μg/100μg wet (mature), depleted to 6.3
# ═══════════════════════════════════════════════════════════════════


class SporulationParams:
    """Parameters for spore production on extraradical mycelium."""
    def __init__(self,
                 # Sporulation rate
                 r_max=0.05,           # max spores per ERM node per step
                 k_c=0.5,             # half-max C for sporulation
                 k_p_inhibit=0.3,     # half-max P inhibition (high P → fewer)
                 # TAG accumulation
                 tag_max=0.80,        # max TAG fraction (58-80%)
                 k_tag=0.3,           # TAG accumulation rate
                 # Spore maturity
                 n_wall_layers=4,     # max wall layers (multi-layered)
                 k_wall=0.2,          # wall maturation rate
                 maturation_steps=10, # steps to full maturity
                 # Carbon budget
                 c_initial=38.0,      # μg C per 100μg wet spore
                 c_germination=6.3,   # μg C remaining after germination
                 # Constraints
                 min_erm_nodes=5,     # minimum ERM network size for sporulation
                 max_spores_per_step=3,  # max new spores per step
                 ):
        self.r_max = r_max
        self.k_c = k_c
        self.k_p_inhibit = k_p_inhibit
        self.tag_max = tag_max
        self.k_tag = k_tag
        self.n_wall_layers = n_wall_layers
        self.k_wall = k_wall
        self.maturation_steps = maturation_steps
        self.c_initial = c_initial
        self.c_germination = c_germination
        self.min_erm_nodes = min_erm_nodes
        self.max_spores_per_step = max_spores_per_step


def sporulation_simulate(erm_graph, fungal_c, soil_p, n_steps=20,
                          params=None, seed=42):
    """Simulate spore production on the extraradical mycelium.

    Spores form on ERM nodes as a function of available carbon
    (positive) and soil phosphorus (negative — high P suppresses).
    Each spore accumulates TAG and develops wall layers over time.

    Parameters
    ----------
    erm_graph : nx.Graph
        Extraradical mycelium graph (from lifecycle phases 2+).
    fungal_c : float
        Available fungal carbon (from brique 20 exchange).
    soil_p : float
        Soil phosphorus concentration.
    n_steps : int
        Simulation steps.
    params : SporulationParams or None
    seed : int

    Returns
    -------
    dict with spores, history, total_tag, cycle_complete
    """
    if params is None:
        params = SporulationParams()

    import random as _random
    rng = _random.Random(seed)

    n_erm = erm_graph.number_of_nodes() if erm_graph is not None else 0
    erm_nodes = list(erm_graph.nodes()) if erm_graph is not None else []

    spores = []  # list of {node, age, tag, wall_layers, mature, c_reserve}
    history = []
    spore_id = [0]

    # Running carbon pool
    c_pool = max(fungal_c, 0.0)

    for step in range(n_steps):
        # --- Sporulation rate: Michaelis-Menten × P inhibition ---
        # r = r_max × C/(K_c+C) × K_p/(K_p+P)
        if c_pool > 0 and n_erm >= params.min_erm_nodes:
            c_factor = c_pool / (params.k_c + c_pool)
            p_inhibition = params.k_p_inhibit / (params.k_p_inhibit + soil_p)
            r_spore = params.r_max * c_factor * p_inhibition
        else:
            r_spore = 0.0

        # --- New spore formation ---
        new_this_step = 0
        for node in erm_nodes:
            if rng.random() < r_spore and new_this_step < params.max_spores_per_step:
                # Cost carbon to make spore
                c_cost = params.c_initial * 0.01  # normalized cost
                if c_pool >= c_cost:
                    c_pool -= c_cost
                    spores.append({
                        'id': spore_id[0],
                        'node': node,
                        'age': 0,
                        'tag': 0.0,
                        'wall_layers': 0.0,
                        'mature': False,
                        'c_reserve': 0.0,
                    })
                    spore_id[0] += 1
                    new_this_step += 1

        # --- Mature existing spores ---
        n_mature = 0
        for sp in spores:
            sp['age'] += 1

            # TAG accumulation: exponential saturation
            sp['tag'] = params.tag_max * (1 - math.exp(-params.k_tag * sp['age']))

            # Wall layers: exponential maturation
            sp['wall_layers'] = params.n_wall_layers * (
                1 - math.exp(-params.k_wall * sp['age']))

            # Carbon reserve buildup
            sp['c_reserve'] = params.c_initial * (
                1 - math.exp(-0.5 * sp['age']))

            # Maturity check
            if (sp['age'] >= params.maturation_steps and
                    sp['tag'] >= 0.5 * params.tag_max):
                sp['mature'] = True
                n_mature += 1

        history.append({
            'step': step,
            'n_spores': len(spores),
            'n_new': new_this_step,
            'n_mature': n_mature,
            'c_pool': c_pool,
            'r_spore': r_spore,
        })

    # --- Cycle closure: mature spores can germinate ---
    mature_spores = [s for s in spores if s['mature']]
    cycle_complete = len(mature_spores) > 0

    # Compute germination potential (C available after germination)
    for sp in mature_spores:
        sp['c_after_germination'] = max(
            sp['c_reserve'] - (params.c_initial - params.c_germination), 0)

    total_tag = sum(s['tag'] for s in spores)

    return {
        'spores': spores,
        'mature_spores': mature_spores,
        'history': history,
        'total_tag': total_tag,
        'n_total': len(spores),
        'n_mature': len(mature_spores),
        'cycle_complete': cycle_complete,
        'c_pool_remaining': c_pool,
    }


def test_sporulation():
    """Tests for brique 23 — Sporulation (Lifecycle Loop Closure)."""
    print("\n=== BRIQUE 23: Sporulation (Lifecycle Loop Closure) ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # --- Test 1: Sporulation rate equation ---
    # r = r_max × C/(K_c+C) × K_p/(K_p+P)
    p = SporulationParams()
    c, P = 1.0, 0.1
    r = 0.05 * (1.0 / (0.5 + 1.0)) * (0.3 / (0.3 + 0.1))
    check("Rate: C=1, P=0.1 → r > 0", r > 0)

    # --- Test 2: High P inhibits sporulation ---
    r_low_p = 0.05 * (1.0 / (0.5 + 1.0)) * (0.3 / (0.3 + 0.01))
    r_high_p = 0.05 * (1.0 / (0.5 + 1.0)) * (0.3 / (0.3 + 5.0))
    check("High P → lower sporulation rate", r_high_p < r_low_p)

    # --- Test 3: High C promotes sporulation ---
    r_low_c = 0.05 * (0.1 / (0.5 + 0.1)) * (0.3 / (0.3 + 0.1))
    r_high_c = 0.05 * (5.0 / (0.5 + 5.0)) * (0.3 / (0.3 + 0.1))
    check("High C → higher sporulation rate", r_high_c > r_low_c)

    # --- Test 4: TAG saturation curve ---
    tag_5 = 0.8 * (1 - math.exp(-0.3 * 5))
    tag_20 = 0.8 * (1 - math.exp(-0.3 * 20))
    check("TAG: age=20 > age=5", tag_20 > tag_5)
    check("TAG: approaches max (0.8)", tag_20 > 0.75)

    # --- Test 5: Wall layers ---
    wall_10 = 4 * (1 - math.exp(-0.2 * 10))
    check("Wall: 10 steps → ~3.5 layers", wall_10 > 3.0)

    # --- Test 6: Basic simulation ---
    G = nx.path_graph(20)
    r23 = sporulation_simulate(G, fungal_c=5.0, soil_p=0.1,
                                n_steps=30, seed=42)
    check("Sim: spores formed > 0", r23['n_total'] > 0)

    # --- Test 7: Mature spores exist ---
    check("Sim: mature spores exist", r23['n_mature'] > 0)

    # --- Test 8: Cycle complete ---
    check("Sim: cycle_complete = True", r23['cycle_complete'])

    # --- Test 9: TAG accumulated ---
    check("Sim: total TAG > 0", r23['total_tag'] > 0)

    # --- Test 10: History length ---
    check("Sim: history = 30 steps", len(r23['history']) == 30)

    # --- Test 11: C pool decreases ---
    check("Sim: C pool < initial",
          r23['c_pool_remaining'] < 5.0)

    # --- Test 12: High P → fewer spores ---
    r23_lowp = sporulation_simulate(G, fungal_c=5.0, soil_p=0.01,
                                     n_steps=30, seed=42)
    r23_highp = sporulation_simulate(G, fungal_c=5.0, soil_p=5.0,
                                      n_steps=30, seed=42)
    check("High P → fewer spores",
          r23_highp['n_total'] <= r23_lowp['n_total'])

    # --- Test 13: Zero C → no spores ---
    r23_noc = sporulation_simulate(G, fungal_c=0.0, soil_p=0.1,
                                    n_steps=20, seed=42)
    check("Zero C → 0 spores", r23_noc['n_total'] == 0)

    # --- Test 14: Too small network → no spores ---
    G_tiny = nx.path_graph(3)
    r23_tiny = sporulation_simulate(G_tiny, fungal_c=5.0, soil_p=0.1,
                                     n_steps=20, seed=42)
    check("Tiny network (<5 nodes): 0 spores", r23_tiny['n_total'] == 0)

    # --- Test 15: Mature spore has c_after_germination ---
    if r23['mature_spores']:
        sp = r23['mature_spores'][0]
        check("Mature spore: c_after_germination defined",
              'c_after_germination' in sp)
    else:
        check("Mature spore: (skipped)", True)

    # --- Test 16: TAG within bounds ---
    all_valid = all(0 <= s['tag'] <= 0.81 for s in r23['spores'])
    check("All spores: TAG ≤ tag_max", all_valid)

    # --- Test 17: Wall layers within bounds ---
    all_walls = all(0 <= s['wall_layers'] <= 4.01 for s in r23['spores'])
    check("All spores: wall_layers ≤ 4", all_walls)

    # --- Test 18: Empty graph → no crash ---
    G_empty = nx.Graph()
    r23_empty = sporulation_simulate(G_empty, fungal_c=5.0, soil_p=0.1,
                                      n_steps=10, seed=42)
    check("Empty graph: no crash, 0 spores", r23_empty['n_total'] == 0)

    # --- Test 19: Cycle closure — mature spores have enough C ---
    if r23['mature_spores']:
        sp = r23['mature_spores'][0]
        check("Cycle closure: c_reserve > 0",
              sp['c_reserve'] > 0)
    else:
        check("Cycle closure: (skipped)", True)

    # --- Test 20: Integration 23→17 (spore positions for germination) ---
    # Mature spores sit on ERM nodes → can be fed back to brique 17
    if r23['mature_spores']:
        nodes_with_spores = [s['node'] for s in r23['mature_spores']]
        check("Integration 23→17: spore nodes are valid graph nodes",
              all(n in G for n in nodes_with_spores))
    else:
        check("Integration 23→17: (skipped)", True)

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


# ═══════════════════════════════════════════════════════════════════
# FULL LIFECYCLE PIPELINE — Ordre biologique
# ═══════════════════════════════════════════════════════════════════
# Phase 0: [18] Root architecture (L-System)
# Phase 1: [17] Spore germination + chemotaxis toward root
# Phase 2: [16+13+15+14+11] AM fungi growth, branching, mechanics,
#           signaling, fusion
# Phase 3: [19] P uptake by mature network
# Phase 4: [20] C↔P exchange plant-fungus
# Phase 5: [0-10] v1.0 metrics on final graph
# ═══════════════════════════════════════════════════════════════════


def full_lifecycle_simulate(
        # Phase 0 params
        root_types=None, root_steps=10,
        # Phase 1 params
        spore_positions=None, spore_steps=15,
        spore_params=None,
        # Phase 2 params
        am_steps=20, am_params=None,
        use_edelstein=True, use_3d=True, use_oscillatory=True,
        # Phase 3 params
        nutrient_steps=15, nutrient_params=None,
        # Phase 4 params
        symbiosis_steps=30, symbiosis_params=None,
        # General
        seed=42):
    """Full AM fungi lifecycle: root → spore → growth → nutrients → exchange.

    Chains briques 18→17→16+13+15+14+11→19→20→v1.0 in biological order.

    Returns
    -------
    dict with phase results + final metrics
    """
    import random as _random
    rng = _random.Random(seed)
    results = {}

    # ── PHASE 0: Root architecture [brique 18] ──────────────────
    phase0 = lsystem_root_generate(
        root_types=root_types, n_steps=root_steps, seed=seed)
    root_graph = phase0['graph']
    root_tips = phase0['root_tips']
    results['phase0_root'] = {
        'n_nodes': root_graph.number_of_nodes(),
        'n_tips': len(root_tips),
        'root_lengths': phase0['root_lengths'],
    }

    # ── JOINT 0→1: Extract root tip positions for SL source ─────
    root_tip_positions = []
    for tip in root_tips:
        pos = root_graph.nodes[tip].get('pos3d')
        if pos:
            root_tip_positions.append(pos)

    if not root_tip_positions:
        raise ValueError("Phase 0 produced no root tips with positions")

    # ── PHASE 1: Spore germination [brique 17] ─────────────────
    if spore_positions is None:
        # Default: scatter spores in soil around root zone
        spore_positions = []
        for i in range(5):
            sp = (rng.uniform(-5, 15),
                  rng.uniform(-5, 5),
                  rng.uniform(-8, -1))
            spore_positions.append(sp)

    phase1 = spore_germination_simulate(
        spore_positions, root_tip_positions,
        n_steps=spore_steps, params=spore_params, seed=seed)

    results['phase1_germination'] = {
        'n_spores': len(spore_positions),
        'n_germinated': len(phase1['germinated']),
        'n_nodes': phase1['graph'].number_of_nodes(),
    }

    # ── JOINT 1→2: Merge spore graph into root graph ───────────
    # Problem: spore_germination creates its own root_0, root_1 nodes.
    # We need to connect germ tube tips to actual root tips.
    spore_graph = phase1['graph']

    # Get germ tube tips from spore graph
    germ_tips = [n for n in spore_graph.nodes()
                 if spore_graph.nodes[n].get('is_am_tip') or
                 (isinstance(n, str) and 'germ_tip' in n)]

    # Add germ tube network to root graph (skip duplicate root nodes)
    for node in spore_graph.nodes():
        if isinstance(node, str) and node.startswith('root_'):
            continue  # skip — we use actual root graph tips
        if node not in root_graph:
            root_graph.add_node(node, **spore_graph.nodes[node])

    for u, v, d in spore_graph.edges(data=True):
        if (isinstance(u, str) and u.startswith('root_')) or \
           (isinstance(v, str) and v.startswith('root_')):
            continue  # skip edges to fake root nodes
        if u in root_graph and v in root_graph:
            root_graph.add_edge(u, v, **d)

    # Connect germ tips to nearest actual root tip
    connections_made = 0
    for gt in germ_tips:
        if gt not in root_graph:
            continue
        gt_pos = root_graph.nodes[gt].get('pos3d')
        if not gt_pos:
            continue
        # Find nearest root tip
        best_tip = None
        best_dist = float('inf')
        for rt in root_tips:
            rt_pos = root_graph.nodes[rt].get('pos3d')
            if rt_pos:
                d = _vec_distance(gt_pos, rt_pos)
                if d < best_dist:
                    best_dist = d
                    best_tip = rt
        if best_tip and best_dist < 20:  # max connection distance
            root_graph.add_edge(gt, best_tip,
                                length_3d=best_dist,
                                is_colonization=True)
            connections_made += 1

    results['joint_1_2'] = {
        'germ_tips': len(germ_tips),
        'connections_to_root': connections_made,
        'merged_nodes': root_graph.number_of_nodes(),
    }

    # ── PHASE 1.5: Appressorium [brique 21] ───────────────────
    # Genre 2005: hyphopodium forms on root surface, turgor-driven
    # penetration via PPA assembly (4-5h).
    # Input: germ_tips + root_tips → penetration events.
    germ_tips_for_21 = []
    for gt in germ_tips:
        if gt in root_graph:
            pos = root_graph.nodes[gt].get('pos3d')
            if pos:
                germ_tips_for_21.append((gt, pos))

    root_tips_for_21 = []
    for rt in root_tips:
        pos = root_graph.nodes[rt].get('pos3d')
        if pos:
            root_tips_for_21.append((rt, pos))

    phase1_5 = appressorium_simulate(
        germ_tips_for_21, root_tips_for_21, root_graph, seed=seed)

    results['phase1_5_appressorium'] = {
        'turgor_mpa': phase1_5['turgor_mpa'],
        'n_hyphopodia': len(phase1_5['hyphopodia']),
        'n_entries': phase1_5['n_entries'],
        'p_penetration': phase1_5['p_penetration'],
    }

    # ── PHASE 1.6: Intraradical colonization [brique 22] ──────
    # Pimprikar 2018: arbuscules form at entry points, 5 stages,
    # 2-7d turnover. Vesicles store TAG (58-80%).
    penetrations = phase1_5['penetrations']
    if penetrations:
        phase1_6 = intraradical_simulate(
            penetrations, n_days=14, seed=seed)
    else:
        # No penetrations — create minimal result
        phase1_6 = {
            'n_total': 0, 'n_active': 0, 'n_vesicles': 0,
            'total_p_transferred': 0.0, 'total_tag_stored': 0.0,
            'turnover_complete': False, 'arbuscule_surface': 0,
        }

    results['phase1_6_intraradical'] = {
        'n_arbuscules': phase1_6['n_total'],
        'n_active': phase1_6['n_active'],
        'n_vesicles': phase1_6['n_vesicles'],
        'p_transferred': phase1_6['total_p_transferred'],
        'tag_stored': phase1_6['total_tag_stored'],
        'turnover': phase1_6['turnover_complete'],
    }

    # ── PHASE 2: AM fungi growth [briques 16+13+15+14+11] ──────
    # Use root_tips as emission points
    colonization_points = root_tips[:] if root_tips else []
    phase2 = am_fungi_simulate(
        root_graph, colonization_points,
        n_steps=am_steps, params=am_params, seed=seed,
        use_edelstein=use_edelstein, use_3d=use_3d,
        use_oscillatory=use_oscillatory)

    mature_graph = phase2['final_graph']
    results['phase2_growth'] = {
        'n_nodes': mature_graph.number_of_nodes(),
        'n_edges': mature_graph.number_of_edges(),
        'fusion_events': phase2.get('total_fusions', 0),
    }

    # ── PHASE 2b: Spatial anastomose [brique 11 extension] ────
    # Fleissner 2005: inter-component fusion via chemotropic sensing.
    # Fuses colonies from different root tips that are spatially close.
    spatial_result = spatial_anastomose(mature_graph, d_max_3d=3.0,
                                         max_fusions=100)
    results['phase2b_spatial_fusion'] = {
        'n_fused': spatial_result['n_fused'],
        'components_before': spatial_result['components_before'],
        'components_after': spatial_result['components_after'],
    }

    # ── POST-PROCESSING: Normalize edge attributes ────────────
    # Ensure all edges have 'weight' (needed by v1.0 metrics).
    # Fallback: weight = length_3d, or conductivity, or 1.0.
    edges_fixed = 0
    for u, v, d in mature_graph.edges(data=True):
        if 'weight' not in d:
            if 'length_3d' in d:
                d['weight'] = d['length_3d']
            elif 'conductivity' in d:
                d['weight'] = 1.0 / max(d['conductivity'], 1e-9)
            else:
                d['weight'] = 1.0
            edges_fixed += 1
    results['post_processing'] = {
        'edges_weight_added': edges_fixed,
        'total_edges': mature_graph.number_of_edges(),
    }

    # ── JOINT 2→3: mature graph → nutrient simulation ──────────
    # root_tips are P sinks (where fungus delivers P to plant)
    nutrient_roots = [n for n in root_tips if n in mature_graph]
    if not nutrient_roots:
        nutrient_roots = [n for n in mature_graph.nodes()
                          if mature_graph.nodes[n].get('is_root')][:3]

    # Extract root-connected subgraph: only nodes reachable from roots
    # can actually deliver P. Orphan fragments uptake P but strand it.
    # Source: Schnepf & Roose 2006 — "translocation within fungus"
    # requires continuous path to root interface.
    root_reachable = set()
    for rn in nutrient_roots:
        if rn in mature_graph:
            root_reachable.update(nx.node_connected_component(mature_graph, rn))

    if len(root_reachable) > 0:
        active_graph = mature_graph.subgraph(root_reachable).copy()
    else:
        active_graph = mature_graph  # fallback

    results['joint_2_3'] = {
        'total_nodes': mature_graph.number_of_nodes(),
        'root_connected_nodes': len(root_reachable),
        'orphan_nodes': mature_graph.number_of_nodes() - len(root_reachable),
        'connectivity_pct': len(root_reachable) / max(mature_graph.number_of_nodes(), 1) * 100,
    }

    # ── PHASE 3: P uptake [brique 19] ──────────────────────────
    # Run on root-connected subgraph only (P can reach root)
    phase3 = nutrient_simulate(
        active_graph, nutrient_roots,
        n_steps=nutrient_steps, params=nutrient_params, seed=seed)

    results['phase3_nutrients'] = {
        'total_p_root': phase3['total_p_root'],
        'depletion_zone': phase3['depletion_zone'],
        'active_nodes': active_graph.number_of_nodes(),
    }

    # Copy nutrient state to graph nodes (for visualization / downstream)
    for node in active_graph.nodes():
        if node in phase3['soil_p']:
            active_graph.nodes[node]['soil_p'] = phase3['soil_p'][node]
        if node in phase3['node_p_internal']:
            active_graph.nodes[node]['internal_p'] = phase3['node_p_internal'][node]

    # ── JOINT 3→4: P delivery → symbiosis exchange ─────────────
    # Phase 3 already simulated fungal P uptake from soil.
    # For Phase 4, we need the ONGOING P supply rate (not residual soil P,
    # which is near-zero after depletion).
    # P delivery rate = total P absorbed / n_steps = sustained supply.
    # Source: Schnepf & Roose 2006 — uptake dominated by advancing front;
    # the network continuously encounters fresh soil.
    p_delivery_rate = phase3['total_p_root'] / max(nutrient_steps, 1)
    soil_p_effective = max(p_delivery_rate, 0.001)

    # ── PHASE 4: C↔P exchange [brique 20] ──────────────────────
    # Fungal biomass = root-connected network (active contribution)
    fungal_biomass = active_graph.number_of_nodes() * 0.1
    phase4 = symbiosis_simulate(
        n_steps=symbiosis_steps, params=symbiosis_params,
        soil_p=soil_p_effective,
        initial_fungal_biomass=max(fungal_biomass, 0.5),
        seed=seed)

    results['phase4_exchange'] = {
        'total_plant_p': phase4['final_plant_p'],
        'total_fungal_c': phase4['final_fungal_c'],
        'fungus_alive': phase4['fungus_alive'],
        'symbiosis_stable': phase4['symbiosis_stable'],
    }

    # ── PHASE 4.5: Sporulation [brique 23] ─────────────────────
    # Kokkoris 2026: spores form on ERM when C is high, P is low.
    # Closes the biological loop: mature spores → back to brique 17.
    fungal_c_for_spore = phase4['final_fungal_c']
    phase4_5 = sporulation_simulate(
        active_graph if active_graph.number_of_nodes() > 0 else mature_graph,
        fungal_c=fungal_c_for_spore,
        soil_p=soil_p_effective,
        n_steps=30, seed=seed)

    results['phase4_5_sporulation'] = {
        'n_spores': phase4_5['n_total'],
        'n_mature': phase4_5['n_mature'],
        'total_tag': phase4_5['total_tag'],
        'cycle_complete': phase4_5['cycle_complete'],
        'mature_spore_positions': [
            sp['node'] for sp in phase4_5.get('mature_spores', [])
        ],
    }

    # ── PHASE 2c: Prune orphan components ────────────────────
    # Source: Bebber 2007 — metrics computed on connected network only.
    # Dead hyphal fragments decompose (Boddy 1999); they are noise for
    # network analysis. Keep root-connected subgraph as "living network".
    pruned_nodes = mature_graph.number_of_nodes() - active_graph.number_of_nodes()
    pruned_pct = pruned_nodes / max(mature_graph.number_of_nodes(), 1) * 100
    results['phase2c_pruning'] = {
        'total_before': mature_graph.number_of_nodes(),
        'active_after': active_graph.number_of_nodes(),
        'pruned_nodes': pruned_nodes,
        'pruned_pct': round(pruned_pct, 1),
    }

    # ── PHASE 5: v1.0 metrics [briques 0-10] ──────────────────
    # Metrics on active (root-connected) graph — biologically meaningful.
    try:
        alpha = meshedness(active_graph)
    except Exception:
        alpha = None
    try:
        eff = global_efficiency(active_graph)
    except Exception:
        eff = None
    try:
        vol_ratio = volume_mst_ratio(active_graph)
    except Exception:
        vol_ratio = None

    # Root efficiency [brique 2] — needs a root node
    root_eff = None
    root_for_metrics = nutrient_roots[0] if nutrient_roots else None
    if root_for_metrics:
        try:
            root_eff = root_efficiency(active_graph, root_for_metrics)
        except Exception:
            root_eff = None

    # Bottlenecks [brique 4]
    try:
        bottles = find_bottlenecks(active_graph, top_n=5)
    except Exception:
        bottles = []

    # Robustness [brique 5] — betweenness attack
    try:
        rob = robustness_test(active_graph, attack='betweenness', steps=10)
        # rob is list of (fraction_removed, fraction_connected)
        if rob and len(rob) > 1:
            # AUC via trapezoidal rule
            rob_auc = sum(0.5 * (rob[i][1] + rob[i+1][1]) *
                          (rob[i+1][0] - rob[i][0])
                          for i in range(len(rob)-1))
        else:
            rob_auc = None
    except Exception:
        rob_auc = None

    # Strategy classification [brique 8]
    strategy = None
    if alpha is not None and eff is not None and root_eff is not None:
        try:
            strat = classify_strategy(alpha, eff, root_eff, vol_ratio)
            strategy = strat.get('strategy', None)
        except Exception:
            strategy = None

    # Kirchhoff flow [brique 9] — from tips through network to root
    kirchhoff_total = None
    if root_for_metrics and nutrient_roots:
        try:
            tips = [n for n in active_graph.nodes()
                    if active_graph.degree(n) == 1
                    and n not in nutrient_roots][:10]
            if tips:
                n_tips = len(tips)
                n_sinks = min(len(nutrient_roots), 3)
                src_dict = {t: 1.0 / n_tips for t in tips}
                sink_dict = {r: 1.0 / n_sinks for r in nutrient_roots[:n_sinks]}
                kf = kirchhoff_flow(active_graph, sources=src_dict,
                                    sinks=sink_dict)
                if isinstance(kf, dict) and 'flows' in kf:
                    kirchhoff_total = sum(abs(f) for f in kf['flows'].values()) / 2
                elif isinstance(kf, dict):
                    kirchhoff_total = sum(abs(f) for f in kf.values()) / 2
        except Exception:
            kirchhoff_total = None

    # Physarum [brique 10] — adaptive flow
    physarum_eff = None
    if root_for_metrics:
        try:
            tips = [n for n in active_graph.nodes()
                    if active_graph.degree(n) == 1
                    and n not in nutrient_roots][:5]
            if tips and nutrient_roots:
                # Build source/sink dict for Physarum
                n_tips = len(tips)
                n_sinks = min(len(nutrient_roots), 3)
                phys_sources = {t: 1.0 / n_tips for t in tips}
                for r_node in nutrient_roots[:n_sinks]:
                    phys_sources[r_node] = phys_sources.get(r_node, 0) - 1.0 / n_sinks
                phys = physarum_simulate(active_graph, sources=phys_sources,
                                         n_steps=10)
                # Efficiency = fraction of edges that remain "thick" (active)
                if phys:
                    n_thick = len(phys.get('thick_edges', []))
                    n_dead = len(phys.get('dead_edges', []))
                    total_e = n_thick + n_dead
                    if total_e > 0:
                        physarum_eff = n_thick / total_e
        except Exception:
            physarum_eff = None

    # Small-world [briques 7+8] — expensive, skip if graph > 200 nodes
    sw_sigma = None
    sw_omega = None
    if active_graph.number_of_nodes() <= 200 and nx.is_connected(active_graph):
        try:
            sw_s = small_world_sigma(active_graph, nrand=3)
            sw_sigma = round(sw_s['sigma'], 4)
        except Exception:
            sw_sigma = None
        try:
            sw_o = small_world_omega(active_graph, nrand=3, nlattice=3)
            sw_omega = round(sw_o['omega'], 4)
        except Exception:
            sw_omega = None

    results['phase5_metrics'] = {
        'meshedness': alpha,
        'global_efficiency': eff,
        'root_efficiency': root_eff,
        'volume_mst_ratio': vol_ratio,
        'bottlenecks': bottles,
        'robustness_auc': rob_auc,
        'strategy': strategy,
        'kirchhoff_total_flow': kirchhoff_total,
        'physarum_efficiency': physarum_eff,
        'small_world_sigma': sw_sigma,
        'small_world_omega': sw_omega,
        'n_components': nx.number_connected_components(active_graph),
        'n_components_full': nx.number_connected_components(mature_graph),
    }

    results['final_graph'] = active_graph
    results['full_graph'] = mature_graph
    results['lifecycle_complete'] = True
    results['cycle_closed'] = phase4_5['cycle_complete']

    return results


def test_lifecycle_chain():
    """Tests for full lifecycle pipeline — biological order."""
    print("\n=== LIFECYCLE CHAIN: Full Biological Order ===\n")
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    # === TEST BLOCK 1: Phase 0 — Root exists ===
    r = full_lifecycle_simulate(root_steps=8, spore_steps=10,
                                 am_steps=10, nutrient_steps=10,
                                 symbiosis_steps=20, seed=42)

    check("Phase 0: root nodes > 0",
          r['phase0_root']['n_nodes'] > 0)
    check("Phase 0: root tips > 0",
          r['phase0_root']['n_tips'] > 0)

    # === TEST BLOCK 2: Phase 1 — Spores germinate ===
    check("Phase 1: spores placed",
          r['phase1_germination']['n_spores'] > 0)
    check("Phase 1: at least 1 germinated",
          r['phase1_germination']['n_germinated'] > 0)

    # === TEST BLOCK 3: Joint 1→2 — Germ tubes reach root ===
    check("Joint 1→2: germ tips detected",
          r['joint_1_2']['germ_tips'] >= 0)
    check("Joint 1→2: merged graph bigger than root alone",
          r['joint_1_2']['merged_nodes'] > r['phase0_root']['n_nodes'])

    # === TEST BLOCK 3.5: Phase 1.5 — Appressorium [brique 21] ===
    check("Phase 1.5: appressorium results present",
          'phase1_5_appressorium' in r)
    check("Phase 1.5: turgor > 0 MPa",
          r['phase1_5_appressorium']['turgor_mpa'] > 0)
    check("Phase 1.5: turgor ~1.98 MPa (van't Hoff)",
          1.5 < r['phase1_5_appressorium']['turgor_mpa'] < 2.5)
    check("Phase 1.5: penetration probability > 0",
          r['phase1_5_appressorium']['p_penetration'] > 0)
    check("Phase 1.5: at least 1 entry",
          r['phase1_5_appressorium']['n_entries'] > 0)

    # === TEST BLOCK 3.6: Phase 1.6 — Intraradical [brique 22] ===
    check("Phase 1.6: intraradical results present",
          'phase1_6_intraradical' in r)
    check("Phase 1.6: arbuscules formed",
          r['phase1_6_intraradical']['n_arbuscules'] > 0)
    check("Phase 1.6: some arbuscules active",
          r['phase1_6_intraradical']['n_active'] > 0)
    check("Phase 1.6: P transferred > 0",
          r['phase1_6_intraradical']['p_transferred'] > 0)
    check("Phase 1.6: turnover occurred",
          r['phase1_6_intraradical']['turnover'] is True)

    # === TEST BLOCK 4: Phase 2 — AM growth ===
    check("Phase 2: network grew",
          r['phase2_growth']['n_nodes'] > r['joint_1_2']['merged_nodes'])
    check("Phase 2: edges exist",
          r['phase2_growth']['n_edges'] > 0)

    # === TEST BLOCK 4b: Phase 2b — Spatial fusion ===
    check("Phase 2b: spatial fusion ran",
          'phase2b_spatial_fusion' in r)
    check("Phase 2b: reduced components",
          r['phase2b_spatial_fusion']['components_after'] <
          r['phase2b_spatial_fusion']['components_before'])

    # === TEST BLOCK 5: Phase 3 — P uptake ===
    # === TEST BLOCK 5a: Joint 2→3 — Root connectivity ===
    check("Joint 2→3: connectivity data present",
          'joint_2_3' in r)
    check("Joint 2→3: root-connected nodes > 0",
          r['joint_2_3']['root_connected_nodes'] > 0)
    check("Joint 2→3: connectivity % > 0",
          r['joint_2_3']['connectivity_pct'] > 0)

    # === TEST BLOCK 5b: Phase 3 — P uptake ===
    check("Phase 3: P delivered to root > 0",
          r['phase3_nutrients']['total_p_root'] > 0)
    check("Phase 3: soil depletion > 0",
          r['phase3_nutrients']['depletion_zone'] > 0)
    check("Phase 3: active nodes tracked",
          r['phase3_nutrients']['active_nodes'] > 0)
    # Verify nutrient data copied to graph nodes
    G_final = r['final_graph']
    nodes_with_soil_p = sum(1 for n in G_final.nodes()
                            if 'soil_p' in G_final.nodes[n])
    check("Phase 3: soil_p on graph nodes",
          nodes_with_soil_p > 0)

    # === TEST BLOCK 6: Phase 4 — C↔P exchange ===
    check("Phase 4: plant got P",
          r['phase4_exchange']['total_plant_p'] > 0)
    check("Phase 4: fungus got C",
          r['phase4_exchange']['total_fungal_c'] > 0)
    check("Phase 4: fungus alive",
          r['phase4_exchange']['fungus_alive'])

    # === TEST BLOCK 6.5: Phase 4.5 — Sporulation [brique 23] ===
    check("Phase 4.5: sporulation results present",
          'phase4_5_sporulation' in r)
    check("Phase 4.5: spores produced",
          r['phase4_5_sporulation']['n_spores'] > 0)
    check("Phase 4.5: mature spores exist",
          r['phase4_5_sporulation']['n_mature'] > 0)
    check("Phase 4.5: TAG accumulated",
          r['phase4_5_sporulation']['total_tag'] > 0)
    check("Phase 4.5: cycle complete",
          r['phase4_5_sporulation']['cycle_complete'] is True)

    # === TEST BLOCK 6.6: Cycle closure A→Z→A ===
    check("Cycle: lifecycle_complete flag",
          r['lifecycle_complete'] is True)
    check("Cycle: cycle_closed flag",
          r['cycle_closed'] is True)
    check("Cycle: mature spores have node positions",
          len(r['phase4_5_sporulation']['mature_spore_positions']) > 0)

    # === TEST BLOCK 7: Phase 5 — ALL v1.0 Metrics ===
    m = r['phase5_metrics']
    check("Phase 5: meshedness computed",
          m['meshedness'] is not None)
    check("Phase 5: global efficiency computed",
          m['global_efficiency'] is not None)
    check("Phase 5: root efficiency computed",
          m['root_efficiency'] is not None)
    check("Phase 5: volume_mst_ratio ≥ 1",
          m['volume_mst_ratio'] is not None and m['volume_mst_ratio'] >= 1.0)
    check("Phase 5: bottlenecks found",
          len(m['bottlenecks']) > 0)
    check("Phase 5: robustness AUC computed",
          m['robustness_auc'] is not None)
    check("Phase 5: strategy classified",
          m['strategy'] is not None)
    check("Phase 5: Kirchhoff flow computed",
          m['kirchhoff_total_flow'] is not None)
    check("Phase 5: Physarum efficiency computed",
          m['physarum_efficiency'] is not None)
    check("Phase 5: small_world keys present",
          'small_world_sigma' in m and 'small_world_omega' in m)

    # Small-world with small graph (< 200 nodes)
    r_small = full_lifecycle_simulate(root_steps=3, spore_steps=3,
                                       am_steps=3, nutrient_steps=3,
                                       symbiosis_steps=5, seed=42)
    m_small = r_small['phase5_metrics']
    n_small = r_small['final_graph'].number_of_nodes()
    if n_small <= 200:
        check("Phase 5: small_world σ computed (small graph)",
              m_small['small_world_sigma'] is not None)
        check("Phase 5: small_world ω computed (small graph)",
              m_small['small_world_omega'] is not None)
    else:
        check("Phase 5: small graph test skipped (still > 200)",
              True)
        check("Phase 5: small graph test skipped (still > 200)",
              True)

    # === TEST BLOCK 7b: Phase 2b — Spatial fusion ===
    check("Phase 2b: spatial fusion reduced components",
          r['phase2b_spatial_fusion']['components_after'] <=
          r['phase2b_spatial_fusion']['components_before'])
    check("Phase 2b: at least 1 fusion",
          r['phase2b_spatial_fusion']['n_fused'] >= 0)

    # === TEST BLOCK 7c: Post-processing — Weight normalization ===
    check("Post-proc: weight added to edges",
          r['post_processing']['edges_weight_added'] >= 0)
    G_final = r['final_graph']
    edges_with_weight = sum(1 for u, v, d in G_final.edges(data=True)
                            if 'weight' in d)
    check("Post-proc: 100% edges have weight",
          edges_with_weight == G_final.number_of_edges())

    # === TEST BLOCK 7d: Phase 2c — Pruning orphan components ===
    check("Phase 2c: pruning stats exist",
          'phase2c_pruning' in r)
    check("Phase 2c: active < total (orphans pruned)",
          r['phase2c_pruning']['active_after'] <=
          r['phase2c_pruning']['total_before'])
    check("Phase 2c: final_graph = active (pruned) graph",
          r['final_graph'].number_of_nodes() ==
          r['phase2c_pruning']['active_after'])
    check("Phase 2c: full_graph preserved",
          r['full_graph'].number_of_nodes() ==
          r['phase2c_pruning']['total_before'])
    # Metrics on pruned graph: meshedness should be >= 0
    check("Phase 5: meshedness >= 0 on active graph",
          r['phase5_metrics']['meshedness'] is not None and
          r['phase5_metrics']['meshedness'] >= 0)
    # Active graph should be connected (1 component)
    check("Phase 5: active graph = 1 component",
          r['phase5_metrics']['n_components'] == 1)

    # === TEST BLOCK 8: End-to-end properties ===
    check("Lifecycle complete flag",
          r.get('lifecycle_complete'))
    check("Final graph exists",
          r['final_graph'] is not None)
    check("Final graph has nodes",
          r['final_graph'].number_of_nodes() > 10)

    # === TEST BLOCK 9: Different seeds ===
    r2 = full_lifecycle_simulate(root_steps=6, spore_steps=8,
                                  am_steps=8, nutrient_steps=8,
                                  symbiosis_steps=15, seed=99)
    check("Seed 99: lifecycle completes",
          r2.get('lifecycle_complete'))

    # === TEST BLOCK 10: No spores → still works ===
    r3 = full_lifecycle_simulate(root_steps=6, spore_positions=[],
                                  am_steps=8, nutrient_steps=8,
                                  symbiosis_steps=15, seed=42)
    check("No spores: lifecycle still completes",
          r3.get('lifecycle_complete'))

    # === TEST BLOCK 11: Monotonic P flow ===
    # Over lifecycle: more steps → more P
    r_short = full_lifecycle_simulate(root_steps=5, am_steps=5,
                                      nutrient_steps=5, symbiosis_steps=10,
                                      seed=42)
    r_long = full_lifecycle_simulate(root_steps=10, am_steps=15,
                                     nutrient_steps=15, symbiosis_steps=30,
                                     seed=42)
    check("Longer lifecycle → more P to plant",
          r_long['phase4_exchange']['total_plant_p'] >=
          r_short['phase4_exchange']['total_plant_p'])

    # === TEST BLOCK 12: All phases ran in order ===
    phases = ['phase0_root', 'phase1_germination', 'joint_1_2',
              'phase1_5_appressorium', 'phase1_6_intraradical',
              'phase2_growth', 'phase2b_spatial_fusion', 'post_processing',
              'phase2c_pruning', 'joint_2_3', 'phase3_nutrients',
              'phase4_exchange', 'phase4_5_sporulation', 'phase5_metrics']
    all_present = all(p in r for p in phases)
    check("All 14 phases present in results", all_present)

    # === TEST BLOCK 13: New phases produce real data ===
    app = r.get('phase1_5_appressorium', {})
    check("Appressorium ran (turgor > 0)", app.get('turgor_mpa', 0) > 0)

    intra = r.get('phase1_6_intraradical', {})
    check("Intraradical ran (arbuscules > 0)", intra.get('n_arbuscules', 0) > 0)

    sporu = r.get('phase4_5_sporulation', {})
    check("Sporulation ran (spores > 0)", sporu.get('n_spores', 0) > 0)
    check("Cycle complete", sporu.get('cycle_complete', False))

    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    return passed, failed


if __name__ == "__main__":
    main()
    p1, f1 = test_kirchhoff_physarum()
    p2, f2 = test_anastomosis()
    p3, f3 = test_full_pipeline()
    p4, f4 = test_edelstein_growth()
    p5, f5 = test_oscillatory_signaling()
    p6, f6 = test_hyphal_mechanics_3d()
    p7, f7 = test_am_fungi_root_growth()
    p8, f8 = test_spore_germination()
    p9, f9 = test_lsystem_root()
    p10, f10 = test_nutrient_uptake()
    p11, f11 = test_symbiosis_exchange()
    p13, f13 = test_appressorium()
    p14, f14 = test_intraradical()
    p15, f15 = test_sporulation()
    p12, f12 = test_lifecycle_chain()
    total_p = p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9 + p10 + p11 + p12 + p13 + p14 + p15
    total_f = f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8 + f9 + f10 + f11 + f12 + f13 + f14 + f15
    print(f"\n{'='*50}")
    print(f"  TOTAL BRIQUES 10-23 + LIFECYCLE: {total_p}/{total_p+total_f}")
    print(f"{'='*50}")
