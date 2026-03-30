"""
YGGDRASIL ENGINE — V3b Species: 5 Lehmann cursors per species (9 measurements)
================================================================================
Measures BA, IL, D, Db, L on each of the 9 spectral species.

Pipeline:
1. Load species assignments (species_65k.json) + concept index (concepts_65k.json)
2. Stream cooc_global (69.4M rows) ONCE -> dispatch edges per species
3. For each species: spectral embedding (2D), sparsify, measure 5 cursors
4. Identify each species against Lehmann 2019 references

Author: Sky x Claude (Opus 4.6) — Session 32, 30 mars 2026
"""
import json
import sys
import math
import sqlite3
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.topology.species_identifier import (
    LEHMANN_PHYLA, TRAIT_BOUNDS, normalize_trait,
    measure_branching_angles, measure_hyphal_diameter,
    measure_box_counting_dimension, measure_lacunarity,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
WT3_PATH = DATA_DIR / "wt3.db"
SPECIES_PATH = DATA_DIR / "scan" / "species_65k.json"
CONCEPTS_PATH = DATA_DIR / "scan" / "concepts_65k.json"
OUTPUT_PATH = DATA_DIR / "results" / "species_per_cluster.json"

SPECIES_NAMES = {
    0: "MatSci/Chem",
    1: "Geo/Earth",
    2: "Medicine",
    3: "Psych/Biz",
    4: "CS/Math",
    5: "Biology",
    6: "Humanities",
    7: "CellBio/Mol",
    8: "Physics",
}


def load_species_map():
    """Load concept index -> species mapping."""
    print("  Loading concepts_65k.json...")
    with open(CONCEPTS_PATH, "r", encoding="utf-8") as f:
        c65k = json.load(f)
    urls = list(c65k["concepts"].keys())
    concept_names = {i: c65k["concepts"][url]["name"] for i, url in enumerate(urls)}

    print("  Loading species_65k.json...")
    with open(SPECIES_PATH, "r", encoding="utf-8") as f:
        sp = json.load(f)

    # Map integer concept_id -> species
    species_map = {}
    for i, url in enumerate(urls):
        if url in sp["concepts"]:
            species_map[i] = sp["concepts"][url]["species"]

    print(f"  {len(species_map)} concepts mapped to species")
    return species_map, concept_names


def stream_edges_per_species(species_map):
    """Stream cooc_global once, dispatch edges to per-species lists."""
    print("  Streaming cooc_global from WT3...")
    db = sqlite3.connect(str(WT3_PATH))

    # Per-species edge lists: {species: [(local_a, local_b, weight), ...]}
    edges_per_sp = defaultdict(list)
    # Global -> local ID mapping per species
    global_to_local = {}  # {species: {global_id: local_id}}
    for sp in range(9):
        global_to_local[sp] = {}

    cursor = db.execute("SELECT concept_a, concept_b, weight FROM cooc_global")
    total = 0
    intra = 0
    batch_size = 500000

    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        for a, b, w in rows:
            total += 1
            sp_a = species_map.get(a)
            sp_b = species_map.get(b)
            if sp_a is not None and sp_b is not None and sp_a == sp_b:
                sp = sp_a
                # Map to local IDs
                g2l = global_to_local[sp]
                if a not in g2l:
                    g2l[a] = len(g2l)
                if b not in g2l:
                    g2l[b] = len(g2l)
                edges_per_sp[sp].append((g2l[a], g2l[b], w))
                intra += 1

        if total % 5000000 == 0:
            print(f"    {total:,} rows | {intra:,} intra-species edges", flush=True)

    db.close()
    print(f"  Done: {total:,} total, {intra:,} intra-species ({100*intra/total:.1f}%)")

    # Build local -> global name mapping
    local_to_global = {}
    for sp in range(9):
        local_to_global[sp] = {v: k for k, v in global_to_local[sp].items()}

    return edges_per_sp, global_to_local, local_to_global


def build_sparse_matrix(edges, n_nodes):
    """Build symmetric sparse adjacency matrix from edge list."""
    mat = lil_matrix((n_nodes, n_nodes))
    for a, b, w in edges:
        mat[a, b] = w
        mat[b, a] = w
    return csr_matrix(mat)


def spectral_positions_2d(adj_sparse, n_nodes):
    """Compute 2D spectral embedding from sparse adjacency matrix."""
    if n_nodes < 5:
        return {i: (0.0, 0.0) for i in range(n_nodes)}

    # Degree matrix
    degrees = np.array(adj_sparse.sum(axis=1)).flatten()
    degrees[degrees == 0] = 1.0

    # Normalized Laplacian: L = I - D^(-1/2) A D^(-1/2)
    d_inv_sqrt = 1.0 / np.sqrt(degrees)
    # Scale adjacency
    D_inv_sqrt = csr_matrix((d_inv_sqrt, (range(n_nodes), range(n_nodes))),
                            shape=(n_nodes, n_nodes))
    L_norm = csr_matrix(np.eye(n_nodes)) - D_inv_sqrt @ adj_sparse @ D_inv_sqrt

    try:
        # Smallest eigenvalues (skip 0)
        k = min(3, n_nodes - 1)
        eigenvalues, eigenvectors = eigsh(L_norm, k=k, which="SM", maxiter=5000)
        # Use eigenvectors 1 and 2 as x, z positions
        pos = {}
        for i in range(n_nodes):
            x = float(eigenvectors[i, 1]) if k > 1 else 0.0
            z = float(eigenvectors[i, 2]) if k > 2 else 0.0
            pos[i] = (x, z)
        return pos
    except Exception as e:
        print(f"    Spectral embedding failed: {e}")
        # Fallback: random positions
        rng = np.random.RandomState(42)
        return {i: (float(rng.randn()), float(rng.randn())) for i in range(n_nodes)}


def sparsify_sparse(adj_sparse, percentile=90):
    """Sparsify a CSR matrix by keeping edges above percentile threshold."""
    data = adj_sparse.data
    if len(data) == 0:
        return adj_sparse
    threshold = np.percentile(data[data > 0], percentile)
    mask = adj_sparse >= threshold
    return adj_sparse.multiply(mask)


def sparsify_max_k_sparse(adj_sparse, max_k=3):
    """
    Each node keeps its top-K strongest neighbors. Symmetrized.
    max_k=3 = dichotomous branching (Murray's Law).
    """
    n = adj_sparse.shape[0]
    result = lil_matrix((n, n))
    adj_csr = adj_sparse.tocsr()

    for i in range(n):
        row_start = adj_csr.indptr[i]
        row_end = adj_csr.indptr[i + 1]
        indices = adj_csr.indices[row_start:row_end]
        data = adj_csr.data[row_start:row_end]

        if len(indices) <= max_k:
            for j, w in zip(indices, data):
                result[i, j] = w
        else:
            # Keep top-K
            top_k = np.argsort(data)[-max_k:]
            for idx in top_k:
                result[i, indices[idx]] = data[idx]

    # Symmetrize
    result_csr = csr_matrix(result)
    sym = result_csr.maximum(result_csr.T)
    return sym


def measure_il_sparse(adj_sparse, n_nodes, max_bfs_pairs=500):
    """
    Internodal length on sparse matrix using BFS.
    Limits to max_bfs_pairs bifurcation pairs for speed.
    """
    # Find bifurcations (degree >= 3)
    degrees = np.array((adj_sparse > 0).sum(axis=1)).flatten()
    bifurcations = np.where(degrees >= 3)[0]

    if len(bifurcations) < 2:
        return 0.0, 0.0

    # Sample if too many
    if len(bifurcations) > 100:
        rng = np.random.RandomState(42)
        bifurcations = rng.choice(bifurcations, 100, replace=False)

    distances = []
    bif_set = set(bifurcations)
    adj_csr = adj_sparse.tocsr()

    for src in bifurcations:
        # BFS from src
        visited = {src: 0}
        queue = [src]
        head = 0
        while head < len(queue):
            node = queue[head]
            head += 1
            # Get neighbors from sparse matrix
            row_start = adj_csr.indptr[node]
            row_end = adj_csr.indptr[node + 1]
            for idx in range(row_start, row_end):
                nbr = adj_csr.indices[idx]
                if nbr not in visited:
                    visited[nbr] = visited[node] + 1
                    queue.append(nbr)

        for dst in bifurcations:
            if dst > src and dst in visited:
                distances.append(visited[dst])

        if len(distances) >= max_bfs_pairs:
            break

    if not distances:
        return 0.0, 0.0

    mean_d = np.mean(distances)
    cv = np.std(distances) / mean_d if mean_d > 0 else 0.0
    return float(mean_d), float(cv)


def measure_ba_sparse(positions, adj_sparse, n_nodes):
    """Branching angles on sparse matrix."""
    degrees = np.array((adj_sparse > 0).sum(axis=1)).flatten()
    adj_csr = adj_sparse.tocsr()
    angles = []

    for i in range(n_nodes):
        if degrees[i] < 3:
            continue
        if i not in positions:
            continue

        # Get neighbors
        row_start = adj_csr.indptr[i]
        row_end = adj_csr.indptr[i + 1]
        neighbors = adj_csr.indices[row_start:row_end]

        xi, zi = positions[i]

        for ai in range(len(neighbors)):
            for bi in range(ai + 1, len(neighbors)):
                ja, jb = neighbors[ai], neighbors[bi]
                if ja not in positions or jb not in positions:
                    continue
                xa, za = positions[ja]
                xb, zb = positions[jb]

                va = (xa - xi, za - zi)
                vb = (xb - xi, zb - zi)

                dot = va[0] * vb[0] + va[1] * vb[1]
                mag_a = math.sqrt(va[0]**2 + va[1]**2)
                mag_b = math.sqrt(vb[0]**2 + vb[1]**2)

                if mag_a > 0 and mag_b > 0:
                    cos_angle = max(-1.0, min(1.0, dot / (mag_a * mag_b)))
                    angle = math.degrees(math.acos(cos_angle))
                    angles.append(angle)

            # Limit angle computations for large nodes
            if len(angles) > 50000:
                break
        if len(angles) > 50000:
            break

    if not angles:
        return 0.0, 0.0

    mean_a = np.mean(angles)
    cv = np.std(angles) / mean_a if mean_a > 0 else 0.0
    return float(mean_a), float(cv)


def measure_d_sparse(adj_sparse):
    """
    Hyphal diameter (log10 of edge weights) on sparse matrix.
    cooc_global weights are 1/C(n,2) weighted, typically << 1.
    We scale by 1e6 to bring into Lehmann range (2.7-6.5).
    """
    data = adj_sparse.data
    positive = data[data > 0]
    if len(positive) == 0:
        return 0.0, 0.0
    # Scale weights to bring log10 into Lehmann range
    # Typical weight: 0.001-100 -> scaled: 1000-1e8 -> log10: 3-8
    scaled = positive * 1e6
    log_w = np.log10(scaled)
    mean_log = np.mean(log_w)
    cv = np.std(log_w) / abs(mean_log) if mean_log != 0 else 0.0
    return float(mean_log), float(cv)


def measure_species(sp_id, edges, local_to_global, concept_names):
    """Measure 5 Lehmann cursors for one species."""
    n_nodes = max(max(a, b) for a, b, _ in edges) + 1 if edges else 0
    if n_nodes < 10:
        return None

    name = SPECIES_NAMES.get(sp_id, f"Species_{sp_id}")
    print(f"\n  --- Species {sp_id}: {name} ({n_nodes} nodes, {len(edges)} edges) ---")

    # Build sparse adjacency
    adj = build_sparse_matrix(edges, n_nodes)
    density = len(edges) / (n_nodes * (n_nodes - 1) / 2) * 100
    print(f"    Density: {density:.2f}%")

    # Spectral positions (2D embedding)
    print(f"    Computing spectral positions...", flush=True)
    positions = spectral_positions_2d(adj, n_nodes)

    # Sparsify for BA and IL — max-K=3 (dichotomous branching, Murray's Law)
    print(f"    Sparsifying (max-K=3)...", flush=True)
    adj_sparse = sparsify_max_k_sparse(adj, max_k=3)
    n_edges_sparse = adj_sparse.nnz // 2

    degrees_sparse = np.array((adj_sparse > 0).sum(axis=1)).flatten()
    n_bifurc = int((degrees_sparse >= 3).sum())
    print(f"    Sparse edges: {n_edges_sparse}, bifurcations: {n_bifurc}")

    # 5 cursors
    print(f"    Measuring BA...", flush=True)
    ba_mean, ba_cv = measure_ba_sparse(positions, adj_sparse, n_nodes)

    print(f"    Measuring IL...", flush=True)
    il_mean, il_cv = measure_il_sparse(adj_sparse, n_nodes)

    print(f"    Measuring D...", flush=True)
    d_mean, d_cv = measure_d_sparse(adj)  # full graph

    print(f"    Measuring Db...", flush=True)
    # Convert positions to domain-keyed dict for existing functions
    domain_names = [str(i) for i in range(n_nodes)]
    pos_dict = {str(i): positions.get(i, (0.0, 0.0)) for i in range(n_nodes)}
    db_val, db_r2 = measure_box_counting_dimension(pos_dict, domain_names)

    print(f"    Measuring L...", flush=True)
    l_val, l_cv = measure_lacunarity(pos_dict, domain_names)

    result = {
        "species_id": sp_id,
        "name": name,
        "n_nodes": n_nodes,
        "n_edges": len(edges),
        "n_edges_sparse": n_edges_sparse,
        "n_bifurcations": n_bifurc,
        "density_pct": round(density, 2),
        "BA": {"value": round(ba_mean, 2), "cv": round(ba_cv, 3)},
        "IL": {"value": round(il_mean, 2), "cv": round(il_cv, 3)},
        "D":  {"value": round(d_mean, 2), "cv": round(d_cv, 3)},
        "Db": {"value": round(db_val, 3), "r2": round(db_r2, 3)},
        "L":  {"value": round(l_val, 3), "cv": round(l_cv, 3)},
    }

    print(f"    BA={ba_mean:.1f}  IL={il_mean:.1f}  D={d_mean:.2f}  "
          f"Db={db_val:.3f}  L={l_val:.3f}")

    # Identify against Lehmann
    traits = ["BA", "IL", "D", "Db", "L"]
    measured_norm = {t: normalize_trait(result[t]["value"], t) for t in traits}

    best_phylum = None
    best_dist = float("inf")
    phylum_distances = {}

    for phylum, data in LEHMANN_PHYLA.items():
        dist_sq = 0.0
        for t in traits:
            ref_norm = normalize_trait(data[t]["mean"], t)
            dist_sq += (measured_norm[t] - ref_norm) ** 2
        dist = math.sqrt(dist_sq)
        phylum_distances[phylum] = round(dist, 4)
        if dist < best_dist:
            best_dist = dist
            best_phylum = phylum

    result["identification"] = {
        "best_match": best_phylum,
        "distance": round(best_dist, 4),
        "distances": phylum_distances,
        "strategy": LEHMANN_PHYLA[best_phylum]["strategy"],
    }
    print(f"    -> {best_phylum} (dist={best_dist:.3f}): "
          f"{LEHMANN_PHYLA[best_phylum]['strategy']}")

    return result


def main():
    print("=" * 60)
    print("  V3b SPECIES — 5 Lehmann cursors x 9 species")
    print("=" * 60)

    species_map, concept_names = load_species_map()
    edges_per_sp, g2l, l2g = stream_edges_per_species(species_map)

    results = []
    for sp_id in range(9):
        edges = edges_per_sp.get(sp_id, [])
        if not edges:
            print(f"\n  Species {sp_id}: NO EDGES")
            continue

        r = measure_species(sp_id, edges, l2g.get(sp_id, {}), concept_names)
        if r:
            results.append(r)

    # Summary table
    print(f"\n{'='*60}")
    print(f"  SUMMARY TABLE")
    print(f"{'='*60}")
    print(f"  {'Species':>15s}  {'BA':>6s}  {'IL':>6s}  {'D':>5s}  {'Db':>5s}  "
          f"{'L':>5s}  {'Match':>15s}")
    print(f"  {'-'*15}  {'-'*6}  {'-'*6}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*15}")

    for r in results:
        print(f"  {r['name']:>15s}  {r['BA']['value']:6.1f}  {r['IL']['value']:6.1f}  "
              f"{r['D']['value']:5.2f}  {r['Db']['value']:5.3f}  {r['L']['value']:5.3f}  "
              f"{r['identification']['best_match']:>15s}")

    print(f"\n  Lehmann references:")
    for phylum, data in LEHMANN_PHYLA.items():
        print(f"  {phylum:>15s}  {data['BA']['mean']:6.1f}  {data['IL']['mean']:6.1f}  "
              f"{data['D']['mean']:5.2f}  {data['Db']['mean']:5.3f}  {data['L']['mean']:5.3f}  "
              f"({data['strategy']})")

    # Save
    import os
    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    output = {
        "date": "2026-03-30",
        "method": "Stream cooc_global -> per-species subgraph -> 5 Lehmann cursors",
        "n_species": len(results),
        "species": results,
        "lehmann_reference": {
            name: {t: data[t]["mean"] for t in ["BA", "IL", "D", "Db", "L"]}
            for name, data in LEHMANN_PHYLA.items()
        },
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
