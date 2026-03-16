#!/usr/bin/env python3
"""
WT4 — Forme 3D unifiée (S-2 × S-1 × S0).

Graphe COMPLET unifié:
  - 1,316 glyphes (S-2)
  - ~65K concepts (S0)
  - 6.2M arêtes bipartite glyph↔concept (pont S-2↔S0)
  - 69.4M arêtes concept↔concept (cooc_global = LE MYCÉLIUM)
  - Total: ~66K nœuds, ~75M arêtes

Laplacien normalisé sur le graphe entier → eigenvectors 1,2,3 = x,y,z.
Glyphes ET concepts positionnés ENSEMBLE dans le même espace 3D.

RÈGLE: Laplaciens S-2 et S0 restent SÉPARÉS en stockage.
       WT4 = calcul DÉRIVÉ, pas une fusion de tables.

Usage:
    python engine/topology/wt4_spectral.py              # Full compute
    python engine/topology/wt4_spectral.py --verify      # Check output
    python engine/topology/wt4_spectral.py --status      # Show progress
"""
import argparse
import json
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "wt3.db"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
CONCEPTS_PATH = ROOT / "data" / "scan" / "concepts_65k.json"
OUTPUT_PATH = ROOT / "data" / "scan" / "wt4_spectral.json"
VIZ_GLYPH_PATH = ROOT / "viz" / "data" / "wt4_spectral.json"
VIZ_FULL_PATH = ROOT / "viz" / "data" / "wt4_full.json"
LOG_PATH = ROOT / "data" / "wt4_log.txt"

K_EIGENVECTORS = 20
CLIP_PERCENTILE = 98
SCALE = 1.5


def log(msg: str):
    print(msg.encode("ascii", errors="replace").decode(), flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ─── Phase 1: Load ALL data from WT3 ─────────────────────────────

def load_all_data(db_path: Path):
    """Load bipartite + cooc_global + papers from WT3."""
    log("[WT4] Phase 1: Loading ALL data from WT3...")
    t0 = time.time()

    conn = sqlite3.connect(str(db_path), timeout=60)

    # 1a. Bipartite (glyph↔concept)
    log("  Loading bipartite...")
    bipartite = conn.execute(
        "SELECT glyph_id, concept_id, weight FROM bipartite"
    ).fetchall()
    glyph_ids = sorted(set(e[0] for e in bipartite))
    bip_concept_ids = set(e[1] for e in bipartite)
    log(f"  Bipartite: {len(bipartite):,} edges, "
        f"{len(glyph_ids)} glyphs, {len(bip_concept_ids):,} concepts")

    # 1b. cooc_global (concept↔concept = THE MYCELIUM)
    log("  Loading cooc_global (69.4M rows, may take a minute)...")
    t1 = time.time()
    cooc_concept_ids = set()
    cooc_edges = []
    batch_size = 5_000_000
    offset = 0
    total_cooc = 0

    while True:
        rows = conn.execute(
            "SELECT concept_a, concept_b, weight FROM cooc_global "
            "LIMIT ? OFFSET ?", (batch_size, offset)
        ).fetchall()
        if not rows:
            break
        cooc_edges.extend(rows)
        for ca, cb, _ in rows:
            cooc_concept_ids.add(ca)
            cooc_concept_ids.add(cb)
        total_cooc += len(rows)
        offset += batch_size
        log(f"    {total_cooc:,} cooc rows loaded...")

    log(f"  cooc_global: {len(cooc_edges):,} edges, "
        f"{len(cooc_concept_ids):,} unique concepts, {time.time()-t1:.1f}s")

    # 1c. All unique concept IDs (union of bipartite + cooc_global)
    all_concept_ids = sorted(bip_concept_ids | cooc_concept_ids)
    log(f"  Total unique concepts: {len(all_concept_ids):,} "
        f"(bipartite: {len(bip_concept_ids):,}, "
        f"cooc: {len(cooc_concept_ids):,})")

    conn.close()
    log(f"  Phase 1 total: {time.time()-t0:.1f}s")

    return bipartite, cooc_edges, glyph_ids, all_concept_ids


# ─── Phase 2: Compute nd (domains per glyph) ─────────────────────

def compute_nd(db_path: Path, glyph_ids: list[int]):
    """Count distinct domains per glyph from WT3 papers table."""
    log("[WT4] Phase 2: Computing nd (domains per glyph)...")
    t0 = time.time()

    conn = sqlite3.connect(str(db_path), timeout=60)
    glyph_domains = defaultdict(set)
    offset = 0
    batch_size = 50_000
    total = 0

    while True:
        rows = conn.execute(
            "SELECT domain, glyphs FROM papers LIMIT ? OFFSET ?",
            (batch_size, offset),
        ).fetchall()
        if not rows:
            break
        for domain, glyphs_json in rows:
            if not domain or not glyphs_json:
                continue
            try:
                for gid in json.loads(glyphs_json):
                    glyph_domains[gid].add(domain)
            except (json.JSONDecodeError, TypeError):
                continue
        total += len(rows)
        offset += batch_size
        if total % 200_000 == 0:
            log(f"  {total:,} papers...")

    conn.close()

    nd = {gid: len(glyph_domains.get(gid, set())) for gid in glyph_ids}
    domains_per_glyph = {gid: sorted(glyph_domains.get(gid, set()))
                         for gid in glyph_ids}

    nd_vals = list(nd.values())
    log(f"  {total:,} papers, nd range: {min(nd_vals)}-{max(nd_vals)}, "
        f"mean={np.mean(nd_vals):.1f}, median={np.median(nd_vals):.0f}")
    log(f"  Time: {time.time()-t0:.1f}s")

    return nd, domains_per_glyph


# ─── Phase 3: Build unified adjacency matrix ─────────────────────

def build_unified_graph(bipartite, cooc_edges, glyph_ids, concept_ids):
    """Build the FULL unified graph: glyphs + concepts + mycelium.

    Node numbering: [0..N_g-1] = glyphs, [N_g..N_g+N_c-1] = concepts.

    Edges:
      - bipartite (glyph↔concept): 6.2M, log-transformed
      - cooc_global (concept↔concept): 69.4M, log-transformed
      - Weights normalized to same scale

    Returns: A (sparse CSR), g2idx, c2idx, N_g, N_c
    """
    N_g = len(glyph_ids)
    N_c = len(concept_ids)
    N = N_g + N_c

    log(f"[WT4] Phase 3: Building unified graph ({N_g} glyphs + {N_c:,} concepts = {N:,} nodes)...")
    t0 = time.time()

    g2idx = {g: i for i, g in enumerate(glyph_ids)}
    c2idx = {c: i + N_g for i, c in enumerate(concept_ids)}

    # ── Step 1: Log-transform weights ──
    bip_weights = np.array([w for _, _, w in bipartite])
    cooc_weights = np.array([w for _, _, w in cooc_edges])

    log(f"  Bipartite weights: min={bip_weights.min():.6f}, "
        f"max={bip_weights.max():.2f}, median={np.median(bip_weights):.6f}")
    log(f"  Cooc weights: min={cooc_weights.min():.6f}, "
        f"max={cooc_weights.max():.2f}, median={np.median(cooc_weights):.4f}")

    # Log-transform both: w → log(1 + w)
    bip_log = np.log1p(bip_weights)
    cooc_log = np.log1p(cooc_weights)

    # Normalize both to [0, 1] range so they're comparable
    bip_max = bip_log.max()
    cooc_max = cooc_log.max()
    if bip_max > 0:
        bip_norm = bip_log / bip_max
    else:
        bip_norm = bip_log
    if cooc_max > 0:
        cooc_norm = cooc_log / cooc_max
    else:
        cooc_norm = cooc_log

    log(f"  After log+norm: bipartite [{bip_norm.min():.4f}, {bip_norm.max():.4f}], "
        f"cooc [{cooc_norm.min():.4f}, {cooc_norm.max():.4f}]")

    # ── Step 2: Pre-allocate numpy arrays (avoid Python list memory bloat) ──
    n_bip = len(bipartite)
    n_cooc = len(cooc_edges)
    total_sym = 2 * (n_bip + n_cooc)  # symmetric → 2x
    log(f"  Allocating {total_sym:,} entries ({total_sym * 8 / 1e9:.2f} GB per array)...")

    row_idx = np.empty(total_sym, dtype=np.int32)
    col_idx = np.empty(total_sym, dtype=np.int32)
    w_arr = np.empty(total_sym, dtype=np.float32)  # float32 saves RAM

    # Bipartite edges (glyph↔concept)
    log(f"  Adding {n_bip:,} bipartite edges...")
    pos = 0
    for k in range(n_bip):
        gid, cid, _ = bipartite[k]
        gi = g2idx[gid]
        ci = c2idx.get(cid, -1)
        if ci < 0:
            continue
        w = bip_norm[k]
        row_idx[pos] = gi;  col_idx[pos] = ci;  w_arr[pos] = w;  pos += 1
        row_idx[pos] = ci;  col_idx[pos] = gi;  w_arr[pos] = w;  pos += 1

    n_bip_added = (pos) // 2
    log(f"  Added {n_bip_added:,} bipartite edges")

    # Cooc edges (concept↔concept = MYCELIUM)
    log(f"  Adding {n_cooc:,} mycelium edges...")
    n_cooc_added = 0
    for k in range(n_cooc):
        ca, cb, _ = cooc_edges[k]
        ci_a = c2idx.get(ca, -1)
        ci_b = c2idx.get(cb, -1)
        if ci_a < 0 or ci_b < 0:
            continue
        w = cooc_norm[k]
        row_idx[pos] = ci_a;  col_idx[pos] = ci_b;  w_arr[pos] = w;  pos += 1
        row_idx[pos] = ci_b;  col_idx[pos] = ci_a;  w_arr[pos] = w;  pos += 1
        n_cooc_added += 1
        if n_cooc_added % 20_000_000 == 0:
            log(f"    {n_cooc_added:,} cooc edges added...")

    log(f"  Added {n_cooc_added:,} mycelium edges")

    # Trim to actual size
    row_idx = row_idx[:pos]
    col_idx = col_idx[:pos]
    w_arr = w_arr[:pos]

    # ── Step 3: Build sparse matrix ──
    log(f"  Building sparse matrix ({N:,} x {N:,}, {pos:,} entries)...")
    A = sparse.coo_matrix(
        (w_arr, (row_idx, col_idx)),
        shape=(N, N),
    ).tocsr()

    # Free COO arrays
    del row_idx, col_idx, w_arr

    density = A.nnz / (N * N) * 100
    log(f"  A: {N:,} x {N:,}, nnz={A.nnz:,}, density={density:.4f}%")
    log(f"  Bipartite edges: {n_bip_added:,}, Mycelium edges: {n_cooc_added:,}")
    log(f"  Time: {time.time()-t0:.1f}s")

    return A, g2idx, c2idx, N_g, N_c


# ─── Phase 4: Normalized Laplacian + eigenvectors ─────────────────

def compute_spectral(A, k=K_EIGENVECTORS):
    """Normalized Laplacian eigenvectors on the full unified graph.

    L_sym = I - D^{-1/2} A D^{-1/2}
    Compute largest eigenvalues of normalized adjacency (= smallest of L_sym).
    """
    N = A.shape[0]
    log(f"[WT4] Phase 4: Spectral decomposition ({N:,} nodes, k={k})...")
    t0 = time.time()

    # Degree vector
    d = np.array(A.sum(axis=1)).flatten()
    n_isolated = np.sum(d == 0)
    if n_isolated > 0:
        log(f"  WARNING: {n_isolated} isolated nodes (degree=0)")

    # D^{-1/2}
    d_inv_sqrt = np.zeros(N)
    mask = d > 0
    d_inv_sqrt[mask] = 1.0 / np.sqrt(d[mask])
    D_inv_sqrt = sparse.diags(d_inv_sqrt)

    # Normalized adjacency: D^{-1/2} A D^{-1/2}
    log(f"  Computing D^{{-1/2}} A D^{{-1/2}}...")
    A_norm = D_inv_sqrt @ A @ D_inv_sqrt
    A_norm = A_norm.tocsc()

    log(f"  A_norm: nnz={A_norm.nnz:,}")
    log(f"  Running eigsh(k={k}, which='LM')... (this may take several minutes)")

    eigenvalues, eigenvectors = eigsh(A_norm, k=k, which="LM")

    # Sort descending
    order = np.argsort(-eigenvalues)
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    log(f"  Eigenvalues (top 10): {np.round(eigenvalues[:10], 4).tolist()}")
    log(f"  lambda_1={eigenvalues[0]:.6f}, lambda_2={eigenvalues[1]:.6f}")
    log(f"  Spectral gap (1->2): {eigenvalues[0]-eigenvalues[1]:.6f}")
    log(f"  Spectral gap (2->3): {eigenvalues[1]-eigenvalues[2]:.6f}")
    log(f"  Spectral gap (3->4): {eigenvalues[2]-eigenvalues[3]:.6f}")
    log(f"  Time: {time.time()-t0:.1f}s")

    return eigenvalues, eigenvectors


# ─── Phase 5: Export ──────────────────────────────────────────────

def robust_normalize(arr, scale=SCALE, clip_pct=CLIP_PERCENTILE):
    """Robust normalization with percentile clipping."""
    arr = arr - np.median(arr)
    lo = np.percentile(arr, 100 - clip_pct)
    hi = np.percentile(arr, clip_pct)
    arr = np.clip(arr, lo, hi)
    mx = max(abs(arr.min()), abs(arr.max()))
    if mx > 0:
        arr = arr / mx * scale
    return arr


def export_results(
    eigenvalues, eigenvectors,
    glyph_ids, all_concept_ids,
    g2idx, c2idx, N_g, N_c,
    nd, domains_per_glyph,
    bipartite, cooc_edges,
):
    """Export glyph + concept positions to JSON."""
    log("[WT4] Phase 5: Exporting results...")
    t0 = time.time()

    # Load glyph registry
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        registry = json.load(f)
    glyph_meta = registry.get("glyphs", {})

    # Load concept names
    concept_names = {}
    if CONCEPTS_PATH.exists():
        with open(CONCEPTS_PATH, encoding="utf-8") as f:
            concepts_data = json.load(f)
        if isinstance(concepts_data, dict):
            for cid_str, info in concepts_data.items():
                if not cid_str.isdigit():
                    continue
                if isinstance(info, dict):
                    concept_names[int(cid_str)] = info.get(
                        "display_name", info.get("name", ""))
                elif isinstance(info, str):
                    concept_names[int(cid_str)] = info

    # Normalize ALL positions together (glyphs + concepts in same space)
    all_x = robust_normalize(eigenvectors[:, 1].copy())
    all_y = robust_normalize(eigenvectors[:, 2].copy())
    all_z = robust_normalize(eigenvectors[:, 3].copy())

    # Glyph stats
    glyph_x = all_x[:N_g]
    glyph_y = all_y[:N_g]
    glyph_z = all_z[:N_g]
    log(f"  Glyph coords: x=[{glyph_x.min():.3f},{glyph_x.max():.3f}], "
        f"y=[{glyph_y.min():.3f},{glyph_y.max():.3f}], "
        f"z=[{glyph_z.min():.3f},{glyph_z.max():.3f}]")

    # Bipartite degree per glyph
    glyph_degree = defaultdict(float)
    glyph_concept_count = defaultdict(int)
    for gid, cid, w in bipartite:
        glyph_degree[gid] += w
        glyph_concept_count[gid] += 1

    # Build glyph output
    glyphs_out = {}
    viz_glyphs = []

    for gid in glyph_ids:
        i = g2idx[gid]
        gid_str = str(gid)
        meta = glyph_meta.get(gid_str, {})
        entry = {
            "glyph_id": gid,
            "symbol": meta.get("symbol", "?"),
            "name": meta.get("name", ""),
            "semantic_group": meta.get("semantic_group", "other"),
            "category": meta.get("category", ""),
            "x": round(float(all_x[i]), 5),
            "y": round(float(all_y[i]), 5),
            "z": round(float(all_z[i]), 5),
            "nd": nd.get(gid, 0),
            "domains": domains_per_glyph.get(gid, []),
            "degree": round(float(glyph_degree[gid]), 2),
            "n_concepts": glyph_concept_count[gid],
            "coords_raw": [round(float(eigenvectors[i, j]), 6)
                          for j in range(min(10, eigenvectors.shape[1]))],
        }
        glyphs_out[gid_str] = entry
        viz_glyphs.append({
            "sym": entry["symbol"], "name": entry["name"],
            "sg": entry["semantic_group"], "cat": entry["category"],
            "x": entry["x"], "y": entry["y"], "z": entry["z"],
            "nd": entry["nd"], "deg": entry["degree"],
            "nc": entry["n_concepts"], "doms": entry["domains"],
        })

    # Build concept positions for full viz (top 5K by mycelium degree)
    concept_cooc_degree = defaultdict(float)
    for ca, cb, w in cooc_edges:
        concept_cooc_degree[ca] += w
        concept_cooc_degree[cb] += w

    top_concepts = sorted(
        concept_cooc_degree.keys(),
        key=lambda c: -concept_cooc_degree[c]
    )[:5000]

    viz_full = {"glyphs": [], "concepts": []}
    for gid in glyph_ids:
        i = g2idx[gid]
        meta = glyph_meta.get(str(gid), {})
        viz_full["glyphs"].append({
            "id": gid, "sym": meta.get("symbol", "?"),
            "name": meta.get("name", ""),
            "x": round(float(all_x[i]), 5),
            "y": round(float(all_y[i]), 5),
            "z": round(float(all_z[i]), 5),
            "nd": nd.get(gid, 0), "type": "glyph",
        })

    for cid in top_concepts:
        idx = c2idx.get(cid)
        if idx is None:
            continue
        viz_full["concepts"].append({
            "id": cid,
            "name": concept_names.get(cid, f"C{cid}"),
            "x": round(float(all_x[idx]), 5),
            "y": round(float(all_y[idx]), 5),
            "z": round(float(all_z[idx]), 5),
            "deg": round(float(concept_cooc_degree[cid]), 1),
            "type": "concept",
        })

    log(f"  Concept positions: {len(viz_full['concepts'])} top concepts")

    # Full output
    output = {
        "meta": {
            "method": "wt4_unified_laplacian",
            "description": "Full unified graph: glyphs + concepts + mycelium",
            "n_glyphs": N_g,
            "n_concepts": N_c,
            "n_total_nodes": N_g + N_c,
            "n_bipartite_edges": len(bipartite),
            "n_mycelium_edges": len(cooc_edges),
            "n_total_edges": len(bipartite) + len(cooc_edges),
            "k": K_EIGENVECTORS,
            "eigenvalues": [round(float(v), 6) for v in eigenvalues],
            "clip_percentile": CLIP_PERCENTILE,
            "scale": SCALE,
            "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "data/wt3.db (bipartite + cooc_global + papers)",
        },
        "glyphs": glyphs_out,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)
    log(f"  Full output: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.0f} KB)")

    VIZ_GLYPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VIZ_GLYPH_PATH, "w", encoding="utf-8") as f:
        json.dump(viz_glyphs, f, ensure_ascii=False)
    log(f"  Viz glyphs: {VIZ_GLYPH_PATH} ({VIZ_GLYPH_PATH.stat().st_size / 1024:.0f} KB)")

    with open(VIZ_FULL_PATH, "w", encoding="utf-8") as f:
        json.dump(viz_full, f, ensure_ascii=False)
    log(f"  Viz full: {VIZ_FULL_PATH} ({VIZ_FULL_PATH.stat().st_size / 1024:.0f} KB)")

    log(f"  Export time: {time.time()-t0:.1f}s")
    return glyphs_out


# ─── Phase 6: Sanity checks ──────────────────────────────────────

def sanity_checks(glyphs_out, eigenvalues, eigenvectors, N_g, N_c):
    """Verify structure, known pairs, domain separation."""
    log("[WT4] Phase 6: Sanity checks...")

    # 1. Eigenvalue spectrum
    log(f"  Eigenvalue gap (1->2): {eigenvalues[0]-eigenvalues[1]:.6f}")
    log(f"  Eigenvalue gap (2->3): {eigenvalues[1]-eigenvalues[2]:.6f}")

    # 2. Glyph vs concept norms
    glyph_norms = np.linalg.norm(eigenvectors[:N_g, 1:4], axis=1)
    concept_norms = np.linalg.norm(eigenvectors[N_g:N_g+N_c, 1:4], axis=1)
    log(f"  Glyph norms (1-3): mean={glyph_norms.mean():.6f}, std={glyph_norms.std():.6f}")
    log(f"  Concept norms (1-3): mean={concept_norms.mean():.6f}, std={concept_norms.std():.6f}")

    # 3. nd vs radius (mushroom check)
    nds = [(g["nd"], g["x"], g["y"], g["z"]) for g in glyphs_out.values()]
    low_nd = [p for p in nds if p[0] <= 4]
    high_nd = [p for p in nds if p[0] >= 13]
    if low_nd and high_nd:
        low_r = np.mean([np.sqrt(x**2 + y**2 + z**2) for _, x, y, z in low_nd])
        high_r = np.mean([np.sqrt(x**2 + y**2 + z**2) for _, x, y, z in high_nd])
        log(f"  Mushroom: nd<=4 radius={low_r:.3f}, nd>=13 radius={high_r:.3f}")
        if low_r > high_r:
            log(f"  -> CHAMPIGNON OK (periphery further out)")
        else:
            log(f"  -> Core further out (inverse champignon)")

    # 4. Collapsed positions check
    positions = [(g["x"], g["y"], g["z"]) for g in glyphs_out.values()]
    pos_set = set((round(x, 4), round(y, 4), round(z, 4)) for x, y, z in positions)
    n_unique = len(pos_set)
    n_total = len(positions)
    if n_unique < n_total:
        log(f"  WARNING: {n_total - n_unique} collapsed glyphs "
            f"({n_unique}/{n_total} unique)")
    else:
        log(f"  All {n_total} glyph positions unique")

    # 5. Known pairs — glyph registry IDs (sequential, NOT Unicode codepoints)
    all_positions = [(g["x"], g["y"], g["z"]) for g in glyphs_out.values()]
    rng = np.random.default_rng(42)
    sample_dists = []
    for _ in range(10000):
        i, j = rng.choice(len(all_positions), size=2, replace=False)
        pi, pj = all_positions[i], all_positions[j]
        sample_dists.append(np.sqrt(
            (pi[0]-pj[0])**2 + (pi[1]-pj[1])**2 + (pi[2]-pj[2])**2))
    median_dist = np.median(sample_dists)
    log(f"  Random pair distances: median={median_dist:.4f}, mean={np.mean(sample_dists):.4f}")

    pairs = [
        ("477", "436", "integral/partial"),       # ∫ ↔ ∂
        ("434", "437", "forall/exists"),           # ∀ ↔ ∃
        ("2", "3", "parens"),                      # ( ↔ )
        ("473", "474", "and/or"),                  # ∧ ↔ ∨
        ("4", "452", "plus/minus"),                # + ↔ −
        ("442", "443", "element/not-element"),     # ∈ ↔ ∉
        ("76", "74", "Sigma/Pi"),                  # Σ ↔ Π
        ("76", "477", "Sigma/integral"),           # Σ ↔ ∫
        ("476", "475", "union/intersection"),      # ∪ ↔ ∩
        ("7", "530", "equals/not-equal"),          # = ↔ ≠
        ("6", "8", "less/greater"),                # < ↔ >
        ("10", "12", "brackets"),                  # [ ↔ ]
    ]
    n_closer = 0
    n_tested = 0
    for id_a, id_b, label in pairs:
        if id_a in glyphs_out and id_b in glyphs_out:
            ga, gb = glyphs_out[id_a], glyphs_out[id_b]
            dist = np.sqrt(
                (ga["x"]-gb["x"])**2 + (ga["y"]-gb["y"])**2 +
                (ga["z"]-gb["z"])**2)
            ratio = dist / median_dist if median_dist > 0 else 0
            closer = "CLOSER" if dist < median_dist else "FARTHER"
            log(f"  {label} ({ga['symbol']}<->{gb['symbol']}): "
                f"dist={dist:.4f}, {ratio:.2f}x median [{closer}]")
            n_tested += 1
            if dist < median_dist:
                n_closer += 1
    if n_tested > 0:
        log(f"  Pairs closer than median: {n_closer}/{n_tested} "
            f"({n_closer/n_tested*100:.0f}%)")

    # 6. Domain centroids
    domain_pts = defaultdict(list)
    for g in glyphs_out.values():
        for d in g["domains"]:
            domain_pts[d].append([g["x"], g["y"], g["z"]])

    log(f"  Domain centroids ({len(domain_pts)} domains):")
    for dom in sorted(domain_pts.keys()):
        pts = np.array(domain_pts[dom])
        cx, cy, cz = pts.mean(axis=0)
        spread = pts.std()
        log(f"    {dom:25s} n={len(pts):4d} "
            f"center=({cx:+.3f},{cy:+.3f},{cz:+.3f}) spread={spread:.3f}")

    # 7. Variance per eigenvector
    total_var = np.sum(eigenvalues**2)
    for i in range(min(6, len(eigenvalues))):
        pct = eigenvalues[i]**2 / total_var * 100
        log(f"  Eigenvector {i}: lambda={eigenvalues[i]:.4f}, "
            f"variance={pct:.1f}%")


# ─── Verify / Status ─────────────────────────────────────────────

def verify():
    if not OUTPUT_PATH.exists():
        print(f"[WT4] No output at {OUTPUT_PATH}")
        return
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    m = data["meta"]
    g = data["glyphs"]
    print(f"[WT4] {OUTPUT_PATH}")
    print(f"  Method: {m['method']}")
    print(f"  Nodes: {m['n_total_nodes']:,} "
          f"({m['n_glyphs']} glyphs + {m['n_concepts']:,} concepts)")
    print(f"  Bipartite edges: {m['n_bipartite_edges']:,}")
    print(f"  Mycelium edges: {m['n_mycelium_edges']:,}")
    print(f"  Eigenvalues (top 5): {m['eigenvalues'][:5]}")
    nds = [v["nd"] for v in g.values()]
    print(f"  nd: [{min(nds)}, {max(nds)}], mean={np.mean(nds):.1f}")


def status():
    if OUTPUT_PATH.exists():
        sz = OUTPUT_PATH.stat().st_size / 1024
        print(f"[WT4] Output exists: {OUTPUT_PATH} ({sz:.0f} KB)")
    else:
        print("[WT4] No output yet")
    if LOG_PATH.exists():
        with open(LOG_PATH, encoding="utf-8") as f:
            lines = f.readlines()
        print(f"[WT4] Log: {len(lines)} lines")
        for line in lines[-15:]:
            print(f"  {line.rstrip()}")


# ─── Build ────────────────────────────────────────────────────────

def build():
    """Full WT4 unified computation."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")

    log("[WT4] === FORME 3D UNIFIEE (S-2 x S-1 x S0) ===")
    log(f"  Source: {DB_PATH}")
    log(f"  Graphe: glyphes + concepts + mycelium (bipartite + cooc_global)")
    t0 = time.time()

    # Phase 1: Load ALL data
    bipartite, cooc_edges, glyph_ids, concept_ids = load_all_data(DB_PATH)

    # Phase 2: nd
    nd, domains_per_glyph = compute_nd(DB_PATH, glyph_ids)

    # Phase 3: Build unified graph
    A, g2idx, c2idx, N_g, N_c = build_unified_graph(
        bipartite, cooc_edges, glyph_ids, concept_ids)

    # Phase 4: Spectral decomposition
    eigenvalues, eigenvectors = compute_spectral(A, k=K_EIGENVECTORS)

    # Phase 5: Export
    glyphs_out = export_results(
        eigenvalues, eigenvectors,
        glyph_ids, concept_ids,
        g2idx, c2idx, N_g, N_c,
        nd, domains_per_glyph,
        bipartite, cooc_edges,
    )

    # Phase 6: Sanity
    sanity_checks(glyphs_out, eigenvalues, eigenvectors, N_g, N_c)

    total = time.time() - t0
    log(f"\n[WT4] === DONE in {total:.1f}s ({total/60:.1f} min) ===")
    log(f"  {N_g} glyphs + {N_c:,} concepts = {N_g+N_c:,} nodes")
    log(f"  {len(bipartite):,} bipartite + {len(cooc_edges):,} mycelium "
        f"= {len(bipartite)+len(cooc_edges):,} total edges")
    log(f"  Output: {OUTPUT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="WT4 - Forme 3D unifiee")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.verify:
        verify()
    else:
        build()


if __name__ == "__main__":
    main()
