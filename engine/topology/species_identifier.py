"""
YGGDRASIL ENGINE — Species Identifier v1
Mesure les 5 curseurs de Lehmann 2019 sur un graphe de co-occurrence,
puis identifie le profil mycélien le plus proche.

Source: Lehmann, Zheng, Soutschek, Roy, Yurkov & Rillig (2019)
"Tradeoffs in hyphal traits determine mycelium architecture in saprobic fungi"
Scientific Reports, 9:14152. DOI: 10.1038/s41598-019-50565-7

Les 5 curseurs:
  BA  = Branching Angle (°)        — angle entre arêtes aux bifurcations
  IL  = Internodal Length           — distance entre bifurcations (hops)
  D   = Hyphal Diameter             — poids moyen des arêtes
  Db  = Box Counting Dimension      — complexité fractale
  L   = Lacunarity                  — hétérogénéité spatiale

Usage:
    python engine/topology/species_identifier.py
"""
import json
import math
import numpy as np
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent

# ============================================================
# DONNÉES DE RÉFÉRENCE — Lehmann et al. 2019 (31 espèces)
# Moyennes par phylum extraites du paper (texte + figures)
# ============================================================

LEHMANN_PHYLA = {
    "Mucoromycota": {
        "n_species": 7,
        "BA":  {"mean": 73.0, "range": (60, 86)},   # grands angles
        "IL":  {"mean": 70.0, "range": (40, 100)},   # courts internodes
        "D":   {"mean": 4.0,  "range": (2.7, 5.5)},  # variable
        "Db":  {"mean": 1.55, "range": (1.5, 1.6)},  # haute complexité
        "L":   {"mean": 0.55, "range": (0.45, 0.65)}, # moyen
        "strategy": "Dense, exploratoire",
    },
    "Basidiomycota": {
        "n_species": 4,
        "BA":  {"mean": 33.0, "range": (26, 40)},    # petits angles
        "IL":  {"mean": 326.0, "range": (200, 453)},  # longs internodes
        "D":   {"mean": 5.75, "range": (5.0, 6.5)},   # gros diamètre
        "Db":  {"mean": 1.25, "range": (1.2, 1.3)},   # faible complexité
        "L":   {"mean": 0.42, "range": (0.4, 0.45)},  # faible lacunarité
        "strategy": "Longue portée, corridors",
    },
    "Ascomycota": {
        "n_species": 20,
        "BA":  {"mean": 56.0, "range": (35, 75)},    # moyen
        "IL":  {"mean": 170.0, "range": (80, 300)},   # moyen
        "D":   {"mean": 4.0,  "range": (2.7, 5.5)},   # moyen
        "Db":  {"mean": 1.40, "range": (1.25, 1.55)}, # moyen
        "L":   {"mean": 0.65, "range": (0.55, 0.70)}, # haute lacunarité
        "strategy": "Polyvalent, hétérogène",
    },
}

# Bornes globales (min-max sur les 31 espèces) pour normalisation
TRAIT_BOUNDS = {
    "BA":  (26.0, 86.0),     # degrés (universel)
    "IL":  (40.0, 453.0),    # µm Lehmann
    "D":   (2.7, 6.5),       # µm Lehmann — notre log10(co-occ) tombe dans ce range
    "Db":  (1.2, 1.6),       # sans unité
    "L":   (0.4, 0.7),       # sans unité (σ²/μ² sans +1)
}


def sparsify(adjacency, percentile=90):
    """
    Seuillage: garder les arêtes au-dessus du percentile de poids.
    Crée une topologie significative à partir d'un graphe quasi-complet.
    """
    weights = adjacency[adjacency > 0]
    if len(weights) == 0:
        return adjacency.copy()
    threshold = np.percentile(weights, percentile)
    sparse = adjacency.copy()
    sparse[sparse < threshold] = 0
    return sparse


def sparsify_max_degree(adjacency, max_k=3):
    """
    Chaque nœud garde ses top-K voisins les plus forts.
    Symétrisé: si A garde B, B garde A (comme un vrai mycélium
    où une connexion existe ou n'existe pas).

    max_k=3 → branchement dichotomique (nature)
    max_k=4 → avec anastomose
    """
    N = adjacency.shape[0]
    sparse = np.zeros_like(adjacency)
    for i in range(N):
        row = adjacency[i].copy()
        row[i] = 0
        nonzero = (row > 0).sum()
        if nonzero <= max_k:
            sparse[i] = row
        else:
            sorted_weights = np.sort(row[row > 0])
            threshold = sorted_weights[-max_k]
            sparse[i] = np.where(row >= threshold, row, 0)
    # Symétriser
    sparse = np.maximum(sparse, sparse.T)
    return sparse


# ============================================================
# MESURE DES 5 CURSEURS SUR UN GRAPHE
# ============================================================

def measure_branching_angles(positions, adjacency, domains):
    """
    Mesure l'angle de bifurcation moyen aux nœuds de degré >= 3.

    positions: dict domain -> (px, pz)
    adjacency: np.array NxN (matrice co-occurrence)
    domains: list of domain names

    Returns: (mean_angle_degrees, cv)
    """
    N = len(domains)
    angles = []

    for i in range(N):
        # Trouver les voisins (co-occurrence > 0)
        neighbors = [j for j in range(N) if j != i and adjacency[i, j] > 0]
        if len(neighbors) < 3:
            continue

        # Position du nœud central
        xi, zi = positions[domains[i]]

        # Calculer les angles entre toutes paires de voisins
        for a_idx in range(len(neighbors)):
            for b_idx in range(a_idx + 1, len(neighbors)):
                ja, jb = neighbors[a_idx], neighbors[b_idx]
                xa, za = positions[domains[ja]]
                xb, zb = positions[domains[jb]]

                # Vecteurs depuis le nœud central
                va = (xa - xi, za - zi)
                vb = (xb - xi, zb - zi)

                # Angle entre les deux vecteurs
                dot = va[0] * vb[0] + va[1] * vb[1]
                mag_a = math.sqrt(va[0]**2 + va[1]**2)
                mag_b = math.sqrt(vb[0]**2 + vb[1]**2)

                if mag_a > 0 and mag_b > 0:
                    cos_angle = max(-1.0, min(1.0, dot / (mag_a * mag_b)))
                    angle = math.degrees(math.acos(cos_angle))
                    angles.append(angle)

    if not angles:
        return 0.0, 0.0

    mean_a = np.mean(angles)
    cv = np.std(angles) / mean_a if mean_a > 0 else 0.0
    return float(mean_a), float(cv)


def measure_internodal_length(adjacency):
    """
    Mesure la distance moyenne (en hops) entre nœuds de degré >= 3.
    BFS entre toutes les paires de bifurcations.

    Returns: (mean_hops, cv)
    """
    N = adjacency.shape[0]
    degrees = np.array([(adjacency[i] > 0).sum() for i in range(N)])
    bifurcations = np.where(degrees >= 3)[0]

    if len(bifurcations) < 2:
        return 0.0, 0.0

    # BFS distances entre bifurcations
    distances = []
    binary = (adjacency > 0).astype(int)

    for src in bifurcations:
        # BFS
        visited = {src: 0}
        queue = [src]
        while queue:
            node = queue.pop(0)
            for nbr in range(N):
                if binary[node, nbr] > 0 and nbr not in visited:
                    visited[nbr] = visited[node] + 1
                    queue.append(nbr)

        for dst in bifurcations:
            if dst > src and dst in visited:
                distances.append(visited[dst])

    if not distances:
        return 0.0, 0.0

    mean_d = np.mean(distances)
    cv = np.std(distances) / mean_d if mean_d > 0 else 0.0
    return float(mean_d), float(cv)


def measure_hyphal_diameter(adjacency):
    """
    Mesure le poids moyen des arêtes en échelle log10 (analogue au diamètre hyphal).
    log10 compresse les co-occurrence counts vers un range comparable à Lehmann (2.7-6.5).

    Returns: (mean_log_weight, cv)
    """
    weights = adjacency[adjacency > 0].flatten()
    if len(weights) == 0:
        return 0.0, 0.0

    log_w = np.log10(weights)
    mean_log = np.mean(log_w)
    cv = np.std(log_w) / abs(mean_log) if mean_log != 0 else 0.0
    return float(mean_log), float(cv)


def measure_box_counting_dimension(positions, domains, n_scales=10):
    """
    Box-counting dimension sur les positions spectrales 2D.

    Db = lim (log N(e) / log(1/e)) quand e -> 0

    Returns: (Db, r_squared)
    """
    coords = np.array([positions[d] for d in domains if d in positions])
    if len(coords) < 3:
        return 1.0, 0.0

    # Bornes
    x_min, z_min = coords.min(axis=0)
    x_max, z_max = coords.max(axis=0)
    extent = max(x_max - x_min, z_max - z_min)

    if extent <= 0:
        return 1.0, 0.0

    # Box counting à différentes échelles
    log_inv_eps = []
    log_n_boxes = []

    for k in range(1, n_scales + 1):
        n_div = 2 ** k
        eps = extent / n_div
        if eps <= 0:
            continue

        # Compter les boîtes occupées
        occupied = set()
        for x, z in coords:
            bx = int((x - x_min) / eps)
            bz = int((z - z_min) / eps)
            occupied.add((bx, bz))

        n_boxes = len(occupied)
        if n_boxes > 0:
            log_inv_eps.append(math.log(1.0 / eps))
            log_n_boxes.append(math.log(n_boxes))

    if len(log_inv_eps) < 3:
        return 1.0, 0.0

    # Régression linéaire: Db = pente
    x = np.array(log_inv_eps)
    y = np.array(log_n_boxes)
    n = len(x)

    sx = x.sum()
    sy = y.sum()
    sxx = (x * x).sum()
    sxy = (x * y).sum()

    denom = n * sxx - sx * sx
    if denom == 0:
        return 1.0, 0.0

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n

    # R²
    y_pred = slope * x + intercept
    ss_res = ((y - y_pred) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return float(slope), float(r_sq)


def measure_lacunarity(positions, domains, box_size=None):
    """
    Lacunarity (gliding box algorithm) sur les positions spectrales 2D.

    L = var(mass) / mean(mass)² pour une taille de boîte donnée.
    Plus L est élevé, plus la distribution est hétérogène.

    Returns: (L_mean, L_cv) — moyenne sur plusieurs tailles de boîte
    """
    coords = np.array([positions[d] for d in domains if d in positions])
    if len(coords) < 3:
        return 0.5, 0.0

    x_min, z_min = coords.min(axis=0)
    x_max, z_max = coords.max(axis=0)
    extent = max(x_max - x_min, z_max - z_min)

    if extent <= 0:
        return 0.5, 0.0

    lacunarities = []

    # Plusieurs tailles de boîte
    for n_div in [4, 6, 8, 10, 12]:
        eps = extent / n_div
        if eps <= 0:
            continue

        # Compter la masse (nombre de points) par boîte
        boxes = defaultdict(int)
        for x, z in coords:
            bx = int((x - x_min) / eps)
            bz = int((z - z_min) / eps)
            boxes[(bx, bz)] += 1

        # Inclure les boîtes vides dans le domaine
        masses = []
        for bx in range(n_div):
            for bz in range(n_div):
                masses.append(boxes.get((bx, bz), 0))

        masses = np.array(masses, dtype=float)
        mean_m = masses.mean()

        if mean_m > 0:
            lac = masses.var() / (mean_m ** 2)
            lacunarities.append(lac)

    if not lacunarities:
        return 0.5, 0.0

    mean_lac = np.mean(lacunarities)
    cv = np.std(lacunarities) / mean_lac if mean_lac > 0 else 0.0
    return float(mean_lac), float(cv)


# ============================================================
# MESURE COMPLÈTE
# ============================================================

def measure_all(adjacency, positions, domains, sparse_percentile=90):
    """
    Mesure les 5 curseurs sur un graphe.

    adjacency: np.array NxN
    positions: dict domain -> (px, pz)
    domains: list of domain names
    sparse_percentile: seuil pour sparsification (BA, IL)

    Returns: dict avec les 5 curseurs + CV + métadonnées
    """
    pos_tuples = {}
    for d in domains:
        if d in positions:
            p = positions[d]
            if isinstance(p, dict):
                pos_tuples[d] = (p["px"], p["pz"])
            else:
                pos_tuples[d] = tuple(p)

    # Sparsify pour les métriques topologiques (BA, IL)
    sparse = sparsify(adjacency, percentile=sparse_percentile)
    n_edges_full = int((adjacency > 0).sum()) // 2
    n_edges_sparse = int((sparse > 0).sum()) // 2

    ba_mean, ba_cv = measure_branching_angles(pos_tuples, sparse, domains)
    il_mean, il_cv = measure_internodal_length(sparse)
    d_mean, d_cv = measure_hyphal_diameter(adjacency)  # full graph, log10
    db_val, db_r2 = measure_box_counting_dimension(pos_tuples, domains)
    l_val, l_cv = measure_lacunarity(pos_tuples, domains)

    N = len(domains)
    degrees_sparse = np.array([(sparse[i] > 0).sum() for i in range(N)])
    n_bifurc = int((degrees_sparse >= 3).sum())

    return {
        "BA":  {"value": round(ba_mean, 2), "cv": round(ba_cv, 3)},
        "IL":  {"value": round(il_mean, 2), "cv": round(il_cv, 3)},
        "D":   {"value": round(d_mean, 2), "cv": round(d_cv, 3)},
        "Db":  {"value": round(db_val, 3), "r2": round(db_r2, 3)},
        "L":   {"value": round(l_val, 3), "cv": round(l_cv, 3)},
        "n_nodes": N,
        "n_edges_full": n_edges_full,
        "n_edges_sparse": n_edges_sparse,
        "n_bifurcations": n_bifurc,
        "sparse_percentile": sparse_percentile,
    }


# ============================================================
# IDENTIFICATION DE L'ESPÈCE
# ============================================================

def normalize_trait(value, trait_name, bounds=None):
    """Normalise une valeur de trait dans [0, 1] par rapport aux bornes Lehmann."""
    if bounds is None:
        bounds = TRAIT_BOUNDS.get(trait_name)
    if bounds is None:
        return 0.5
    lo, hi = bounds
    if hi == lo:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def identify_species(measurements, reference=None):
    """
    Compare les mesures du graphe aux profils Lehmann 2019.

    measurements: dict avec BA, IL, D, Db, L (output de measure_all)
    reference: dict phylum -> traits (default: LEHMANN_PHYLA)

    Returns: dict avec distances à chaque phylum + identification
    """
    if reference is None:
        reference = LEHMANN_PHYLA

    traits = ["BA", "IL", "D", "Db", "L"]

    # Valeurs mesurées normalisées
    measured = {}
    for t in traits:
        val = measurements[t]["value"]
        measured[t] = normalize_trait(val, t)

    # Distance à chaque phylum
    results = {}
    for phylum, data in reference.items():
        dist_sq = 0.0
        details = {}
        for t in traits:
            ref_norm = normalize_trait(data[t]["mean"], t)
            diff = measured[t] - ref_norm
            dist_sq += diff ** 2
            details[t] = {
                "measured_norm": round(measured[t], 3),
                "reference_norm": round(ref_norm, 3),
                "diff": round(diff, 3),
            }

        results[phylum] = {
            "distance": round(math.sqrt(dist_sq), 4),
            "strategy": data["strategy"],
            "n_species": data["n_species"],
            "details": details,
        }

    # Tri par distance
    ranked = sorted(results.items(), key=lambda x: x[1]["distance"])

    closest = ranked[0]
    second = ranked[1]

    # Seuil: si la distance au plus proche est > 1.0, c'est une nouvelle espèce
    is_new_species = closest[1]["distance"] > 1.0

    return {
        "identification": "NOUVELLE ESPECE" if is_new_species else closest[0],
        "confidence": round(1.0 - min(1.0, closest[1]["distance"]), 3),
        "margin": round(second[1]["distance"] - closest[1]["distance"], 4),
        "ranking": [
            {"phylum": name, **data}
            for name, data in ranked
        ],
        "is_new_species": is_new_species,
        "measured_raw": {t: measurements[t]["value"] for t in traits},
        "measured_normalized": measured,
    }


# ============================================================
# CHARGEMENT DONNÉES V1
# ============================================================

def load_v1_graph():
    """Charge la matrice V1 85×85 et les positions spectrales."""
    with open(ROOT / "data" / "topology" / "domain_cooccurrence_matrix.json",
              "r", encoding="utf-8") as f:
        cooc = json.load(f)

    domains = cooc["domains"]
    matrix = np.array(cooc["matrix"], dtype=float)

    with open(ROOT / "data" / "topology" / "domain_spectral_positions.json",
              "r", encoding="utf-8") as f:
        positions = json.load(f)

    return matrix, positions, domains


# ============================================================
# MAIN
# ============================================================

def run_single(matrix, positions, domains, sparse_method="percentile", sparse_param=90):
    """
    Lance mesure + identification pour une config de sparsification.

    sparse_method: "percentile" ou "max_degree"
    sparse_param: percentile (0-100) ou max_k (entier)
    """
    if sparse_method == "max_degree":
        sparse = sparsify_max_degree(matrix, max_k=sparse_param)
    else:
        sparse = sparsify(matrix, percentile=sparse_param)

    # Positions
    pos_tuples = {}
    for d in domains:
        if d in positions:
            p = positions[d]
            if isinstance(p, dict):
                pos_tuples[d] = (p["px"], p["pz"])
            else:
                pos_tuples[d] = tuple(p)

    N = len(domains)
    n_edges_full = int((matrix > 0).sum()) // 2
    n_edges_sparse = int((sparse > 0).sum()) // 2

    ba_mean, ba_cv = measure_branching_angles(pos_tuples, sparse, domains)
    il_mean, il_cv = measure_internodal_length(sparse)
    d_mean, d_cv = measure_hyphal_diameter(matrix)  # full graph, log10
    db_val, db_r2 = measure_box_counting_dimension(pos_tuples, domains)
    l_val, l_cv = measure_lacunarity(pos_tuples, domains)

    degrees = [(sparse[i] > 0).sum() for i in range(N)]
    mean_deg = np.mean(degrees)
    max_deg = max(degrees)
    n_bifurc = sum(1 for d in degrees if d >= 3)

    measurements = {
        "BA":  {"value": round(ba_mean, 2), "cv": round(ba_cv, 3)},
        "IL":  {"value": round(il_mean, 2), "cv": round(il_cv, 3)},
        "D":   {"value": round(d_mean, 2), "cv": round(d_cv, 3)},
        "Db":  {"value": round(db_val, 3), "r2": round(db_r2, 3)},
        "L":   {"value": round(l_val, 3), "cv": round(l_cv, 3)},
        "n_nodes": N,
        "n_edges_full": n_edges_full,
        "n_edges_sparse": n_edges_sparse,
        "n_bifurcations": n_bifurc,
        "mean_degree": round(mean_deg, 1),
        "max_degree": int(max_deg),
        "sparse_method": sparse_method,
        "sparse_param": sparse_param,
    }

    result = identify_species(measurements)
    return measurements, result


def run_compare(matrix, positions, domains):
    """
    Compare P90 vs max-degree K=3,4,5,6 sur les mêmes données.
    Sauvegarde species_comparison.json.
    """
    from datetime import datetime

    configs = [
        ("P90", "percentile", 90),
        ("K=3 (branchement)", "max_degree", 3),
        ("K=4 (+ anastomose)", "max_degree", 4),
        ("K=5", "max_degree", 5),
        ("K=6", "max_degree", 6),
    ]

    n_papers = 296_000_000  # V1
    n_edges_total = int((matrix > 0).sum()) // 2

    print("=" * 80)
    print("YGGDRASIL — SPECIES COMPARISON TEST")
    print(f"Données: V1 — {len(domains)} domaines, {n_edges_total} arêtes, {n_papers:,} papers")
    print(f"Lehmann et al. 2019 — 5 curseurs × 3 phylums × 31 espèces")
    print("=" * 80)

    header = f"{'Config':<22} {'Edges':>6} {'Deg':>5} {'Max':>4} {'Bif':>4}  {'BA':>6} {'IL':>5} {'D':>5} {'Db':>5} {'L':>5}  {'Espece':<15} {'Dist':>6} {'Conf':>5}"
    print(f"\n{header}")
    print("-" * len(header))

    results = []
    for name, method, param in configs:
        m, r = run_single(matrix, positions, domains, method, param)
        sp = r["identification"]
        dist = r["ranking"][0]["distance"]
        conf = r["confidence"] * 100

        print(f"{name:<22} {m['n_edges_sparse']:>6} {m['mean_degree']:>5} {m['max_degree']:>4} {m['n_bifurcations']:>4}  "
              f"{m['BA']['value']:>6} {m['IL']['value']:>5} {m['D']['value']:>5} {m['Db']['value']:>5} {m['L']['value']:>5}  "
              f"{sp:<15} {dist:>6.4f} {conf:>4.1f}%")

        results.append({
            "config": name,
            "method": method,
            "param": param,
            "measurements": m,
            "identification": r,
        })

    # Verdict
    species_set = set(r["identification"]["identification"] for r in results)
    stable = len(species_set) == 1

    print(f"\n{'=' * 80}")
    if stable:
        print(f"VERDICT: STABLE — toutes les configs donnent {species_set.pop()}")
    else:
        print(f"VERDICT: INSTABLE — espèces différentes: {species_set}")
    print(f"{'=' * 80}")

    # Sauvegarder
    comparison = {
        "date": datetime.now().isoformat(),
        "source": f"V1 ({len(domains)} domaines, {n_papers:,} papers)",
        "reference": "Lehmann et al. 2019, Sci Rep 9:14152",
        "question": "Est-ce que brider le degré max (nature: 3-4) change l'espèce ?",
        "stable": stable,
        "configs": results,
        "methodology": {
            "D_scale": "log10(co-occurrence counts)",
            "L_formula": "sigma^2 / mu^2 (sans +1)",
            "note": "max_degree symetrise: si A garde B, B garde A",
        },
    }

    out_path = ROOT / "data" / "topology" / "species_comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    print(f"\nSauvegardé: {out_path}")

    # Aussi sauvegarder le profil P90 comme résultat principal
    p90_result = results[0]
    profile = {
        "source": f"V1 ({len(domains)} domaines, {n_papers:,} papers)",
        "measurements": p90_result["measurements"],
        "identification": p90_result["identification"],
        "reference": "Lehmann et al. 2019, Sci Rep 9:14152",
        "methodology": {
            "sparsification": "P90",
            "D_scale": "log10(co-occurrence counts)",
            "L_formula": "sigma^2 / mu^2 (sans +1)",
        },
        "robustness": {
            "tested_configs": [r["config"] for r in results],
            "all_same_species": stable,
        },
    }

    profile_path = ROOT / "data" / "topology" / "species_profile.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"Sauvegardé: {profile_path}")

    return comparison


if __name__ == "__main__":
    import sys

    matrix, positions, domains = load_v1_graph()

    if "--compare" in sys.argv:
        run_compare(matrix, positions, domains)
    else:
        # Mode simple: P90 seul
        print("=" * 60)
        print("YGGDRASIL — SPECIES IDENTIFIER v1")
        print("Lehmann et al. 2019 — 5 curseurs mycéliens")
        print("=" * 60)

        print(f"\nChargement V1: {len(domains)} domaines, {int((matrix > 0).sum()) // 2} arêtes")

        measurements, result = run_single(matrix, positions, domains)

        print(f"\nSparsification: P90 -> {measurements['n_edges_sparse']}/{measurements['n_edges_full']} arêtes")
        print(f"\nCurseurs:")
        for t in ["BA", "IL", "D", "Db", "L"]:
            v = measurements[t]
            extra = f"cv={v['cv']}" if 'cv' in v else f"R²={v['r2']}"
            print(f"  {t:3s} = {v['value']} ({extra})")

        print(f"\nRésultat: {result['identification']} (confiance {result['confidence']*100:.1f}%)")
        for r in result["ranking"]:
            marker = " <<<" if r["phylum"] == result["identification"] else ""
            print(f"  {r['phylum']:20s} dist={r['distance']:.4f}{marker}")

        print("\nPour le test de robustesse: python species_identifier.py --compare")
