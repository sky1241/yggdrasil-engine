#!/usr/bin/env python3
"""
WT4 — Forme 3D unifiée: Laplacien spectral sur bipartite projeté.

Charge la matrice bipartite glyph×concept depuis WT3, projette dans
l'espace glyph-glyph (A = B @ B^T), calcule le Laplacien normalisé,
extrait les eigenvectors 1-2-3 comme coordonnées x,y,z.

La projection A[i,j] = Σ_k B[i,k]*B[j,k] pondère l'adjacence entre
glyphes par leur usage partagé de concepts S0 = "masses S0".

RÈGLE: Laplaciens S-2 et S0 restent SÉPARÉS en stockage.
       WT4 = calcul DÉRIVÉ, pas une fusion de tables.

Usage:
    python engine/topology/wt4_spectral.py          # Full compute
    python engine/topology/wt4_spectral.py --verify  # Check output
"""
import argparse
import json
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "wt3.db"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
OUTPUT_PATH = ROOT / "data" / "scan" / "wt4_spectral.json"
VIZ_OUTPUT_PATH = ROOT / "viz" / "data" / "wt4_spectral.json"

K_EIGENVECTORS = 10  # extract 10, use 1-2-3 for x,y,z (skip 0=constant)
CLIP_PERCENTILE = 98  # robust normalization
SCALE = 1.5


def log(msg: str):
    print(msg.encode("ascii", errors="replace").decode(), flush=True)


# ─── Phase 1: Load bipartite from WT3 ─────────────────────────────

def load_bipartite(db_path: Path):
    """Load bipartite table into sparse COO matrix.
    Returns: B (sparse CSR), glyph_ids (sorted), concept_ids (sorted)
    """
    log("[WT4] Phase 1: Loading bipartite from WT3...")
    t0 = time.time()

    conn = sqlite3.connect(str(db_path), timeout=10)

    # Get all edges
    rows = conn.execute(
        "SELECT glyph_id, concept_id, weight FROM bipartite"
    ).fetchall()
    conn.close()

    log(f"  {len(rows):,} edges loaded in {time.time()-t0:.1f}s")

    # Build index mappings (contiguous IDs for sparse matrix)
    glyph_set = sorted(set(r[0] for r in rows))
    concept_set = sorted(set(r[1] for r in rows))

    g2idx = {g: i for i, g in enumerate(glyph_set)}
    c2idx = {c: i for i, c in enumerate(concept_set)}

    n_glyphs = len(glyph_set)
    n_concepts = len(concept_set)
    log(f"  {n_glyphs} glyphs x {n_concepts} concepts")

    # Build sparse matrix
    row_idx = [g2idx[r[0]] for r in rows]
    col_idx = [c2idx[r[1]] for r in rows]
    weights = [r[2] for r in rows]

    B = sparse.coo_matrix(
        (weights, (row_idx, col_idx)),
        shape=(n_glyphs, n_concepts),
        dtype=np.float64,
    ).tocsr()

    density = B.nnz / (n_glyphs * n_concepts) * 100
    log(f"  B: {B.shape}, nnz={B.nnz:,}, density={density:.2f}%")

    return B, glyph_set, concept_set


# ─── Phase 2: Compute nd (domains per glyph) ──────────────────────

def compute_nd(db_path: Path, glyph_ids: list[int]):
    """Count distinct domains per glyph from WT3 papers table.
    Uses batch processing to avoid loading all 833K papers at once.
    """
    log("[WT4] Phase 2: Computing nd (domains per glyph)...")
    t0 = time.time()

    conn = sqlite3.connect(str(db_path), timeout=30)

    # Process in batches of 50K papers
    glyph_domains = defaultdict(set)
    offset = 0
    batch_size = 50000
    total_papers = 0

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
                glyph_list = json.loads(glyphs_json)
            except (json.JSONDecodeError, TypeError):
                continue
            for gid in glyph_list:
                glyph_domains[gid].add(domain)

        total_papers += len(rows)
        offset += batch_size
        if total_papers % 200000 == 0:
            log(f"  {total_papers:,} papers processed...")

    conn.close()

    # Build nd dict
    nd = {}
    domains_per_glyph = {}
    for gid in glyph_ids:
        doms = glyph_domains.get(gid, set())
        nd[gid] = len(doms)
        domains_per_glyph[gid] = sorted(doms)

    nd_vals = [nd[g] for g in glyph_ids]
    log(f"  {total_papers:,} papers, nd range: {min(nd_vals)}-{max(nd_vals)}, "
        f"mean={np.mean(nd_vals):.1f}, median={np.median(nd_vals):.0f}")
    log(f"  Time: {time.time()-t0:.1f}s")

    return nd, domains_per_glyph


# ─── Phase 3: Project to glyph-glyph space ────────────────────────

def project_bipartite(B):
    """Compute A = B @ B^T (glyph-glyph adjacency weighted by shared concepts)."""
    log("[WT4] Phase 3: Projecting bipartite → glyph-glyph...")
    t0 = time.time()

    A = B @ B.T  # (n_glyphs × n_glyphs)
    A = A.tocsr()

    # Zero diagonal (no self-loops for Laplacian)
    A.setdiag(0)
    A.eliminate_zeros()

    log(f"  A: {A.shape}, nnz={A.nnz:,}, density={A.nnz / A.shape[0]**2 * 100:.1f}%")
    log(f"  Weight range: {A.data.min():.4f} - {A.data.max():.2f}")
    log(f"  Time: {time.time()-t0:.1f}s")

    return A


# ─── Phase 4: Normalized Laplacian + eigenvectors ─────────────────

def compute_laplacian(A, k=K_EIGENVECTORS):
    """Normalized Laplacian L_sym = I - D^{-1/2} A D^{-1/2}, extract k smallest eigenvectors."""
    log(f"[WT4] Phase 4: Normalized Laplacian, k={k}...")
    t0 = time.time()

    N = A.shape[0]
    d = np.array(A.sum(axis=1)).flatten()

    # D^{-1/2}
    d_inv_sqrt = np.zeros(N)
    mask = d > 0
    d_inv_sqrt[mask] = 1.0 / np.sqrt(d[mask])
    D_inv_sqrt = sparse.diags(d_inv_sqrt)

    # Normalized adjacency: D^{-1/2} A D^{-1/2}
    A_norm = D_inv_sqrt @ A @ D_inv_sqrt

    # L_sym = I - A_norm (but eigsh on A_norm with which='LM' is more stable)
    log(f"  Computing eigsh (k={k}, which='LM' on normalized adjacency)...")
    eigenvalues, eigenvectors = eigsh(A_norm.tocsc(), k=k, which="LM")

    # Sort by eigenvalue descending (largest first = most structure)
    order = np.argsort(-eigenvalues)
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    log(f"  Eigenvalues: {np.round(eigenvalues, 4).tolist()}")
    log(f"  Gap: lambda_1={eigenvalues[0]:.4f}, lambda_2={eigenvalues[1]:.4f}, "
        f"gap={eigenvalues[0]-eigenvalues[1]:.4f}")
    log(f"  Time: {time.time()-t0:.1f}s")

    return eigenvalues, eigenvectors


# ─── Phase 5: Normalize + export ──────────────────────────────────

def robust_normalize(arr, scale=SCALE, clip_pct=CLIP_PERCENTILE):
    """Robust normalization with percentile clipping (from spectral_layout.py)."""
    arr = arr - np.median(arr)
    lo = np.percentile(arr, 100 - clip_pct)
    hi = np.percentile(arr, clip_pct)
    arr = np.clip(arr, lo, hi)
    mx = max(abs(arr.min()), abs(arr.max()))
    if mx > 0:
        arr = arr / mx * scale
    return arr


def export_results(
    eigenvalues, eigenvectors, glyph_ids, concept_ids,
    nd, domains_per_glyph, B,
):
    """Export 3D positions + metadata to JSON."""
    log("[WT4] Phase 5: Exporting results...")

    # Load glyph registry for metadata
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        registry = json.load(f)
    glyph_meta = registry.get("glyphs", {})

    # Eigenvectors 1,2,3 (skip 0=constant-ish) as x,y,z
    x_raw = eigenvectors[:, 1].copy()
    y_raw = eigenvectors[:, 2].copy()
    z_raw = eigenvectors[:, 3].copy()

    x = robust_normalize(x_raw)
    y = robust_normalize(y_raw)
    z = robust_normalize(z_raw)

    log(f"  x: [{x.min():.3f}, {x.max():.3f}], y: [{y.min():.3f}, {y.max():.3f}], "
        f"z: [{z.min():.3f}, {z.max():.3f}]")

    # Bipartite degree per glyph
    degrees = np.array(B.sum(axis=1)).flatten()

    # Build output
    glyphs_out = {}
    viz_out = []

    for i, gid in enumerate(glyph_ids):
        gid_str = str(gid)
        meta = glyph_meta.get(gid_str, {})

        entry = {
            "glyph_id": gid,
            "symbol": meta.get("symbol", "?"),
            "name": meta.get("name", ""),
            "semantic_group": meta.get("semantic_group", "other"),
            "category": meta.get("category", ""),
            "x": round(float(x[i]), 5),
            "y": round(float(y[i]), 5),
            "z": round(float(z[i]), 5),
            "nd": nd.get(gid, 0),
            "domains": domains_per_glyph.get(gid, []),
            "degree": round(float(degrees[i]), 2),
            "coords_raw": [round(float(eigenvectors[i, j]), 6) for j in range(min(6, eigenvectors.shape[1]))],
        }
        glyphs_out[gid_str] = entry

        # Viz format (flat array for Three.js)
        viz_out.append({
            "sym": meta.get("symbol", "?"),
            "name": meta.get("name", ""),
            "sg": meta.get("semantic_group", "other"),
            "cat": meta.get("category", ""),
            "x": entry["x"],
            "y": entry["y"],
            "z": entry["z"],
            "nd": entry["nd"],
            "deg": entry["degree"],
            "doms": domains_per_glyph.get(gid, []),
        })

    # Full output (data/scan/)
    output = {
        "meta": {
            "method": "wt4_bipartite_projected_laplacian",
            "n_glyphs": len(glyph_ids),
            "n_concepts": len(concept_ids),
            "k": K_EIGENVECTORS,
            "eigenvalues": [round(float(v), 6) for v in eigenvalues],
            "clip_percentile": CLIP_PERCENTILE,
            "scale": SCALE,
            "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "data/wt3.db bipartite table",
        },
        "glyphs": glyphs_out,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)
    log(f"  Full output: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.0f} KB)")

    # Viz output (viz/data/)
    VIZ_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VIZ_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(viz_out, f, ensure_ascii=False)
    log(f"  Viz output: {VIZ_OUTPUT_PATH} ({VIZ_OUTPUT_PATH.stat().st_size / 1024:.0f} KB)")

    return glyphs_out


# ─── Phase 6: Sanity checks ───────────────────────────────────────

def sanity_checks(glyphs_out, eigenvalues):
    """Verify mushroom shape, known pairs, domain separation."""
    log("[WT4] Phase 6: Sanity checks...")

    # 1. Eigenvalue gap
    gap = eigenvalues[0] - eigenvalues[1]
    log(f"  Eigenvalue gap: {gap:.4f} {'(good)' if gap > 0.01 else '(WEAK)'}")

    # 2. nd distribution vs position
    nds = [(g["nd"], g["x"], g["y"], g["z"]) for g in glyphs_out.values()]
    low_nd = [p for p in nds if p[0] <= 4]
    high_nd = [p for p in nds if p[0] >= 13]
    if low_nd and high_nd:
        low_r = np.mean([np.sqrt(x**2 + y**2 + z**2) for _, x, y, z in low_nd])
        high_r = np.mean([np.sqrt(x**2 + y**2 + z**2) for _, x, y, z in high_nd])
        log(f"  Mushroom check: nd<=4 mean_radius={low_r:.3f}, nd>=13 mean_radius={high_r:.3f}")
        if low_r > high_r:
            log(f"  -> Periphery (nd<=4) further out than core (nd>=13): CHAMPIGNON SHAPE OK")
        else:
            log(f"  -> Core further out than periphery: UNEXPECTED (but not necessarily wrong)")

    # 3. Known pairs proximity
    pairs_to_check = [
        ("8788", "8706", "integral/partial"),    # ∫ ↔ ∂
        ("8704", "8707", "forall/exists"),        # ∀ ↔ ∃
        ("40", "41", "parens"),                    # ( ↔ )
        ("8743", "8744", "and/or"),                # ∧ ↔ ∨
    ]
    for id_a, id_b, label in pairs_to_check:
        if id_a in glyphs_out and id_b in glyphs_out:
            ga, gb = glyphs_out[id_a], glyphs_out[id_b]
            dist = np.sqrt((ga["x"]-gb["x"])**2 + (ga["y"]-gb["y"])**2 + (ga["z"]-gb["z"])**2)
            log(f"  Pair {label} ({ga['symbol']}↔{gb['symbol']}): dist={dist:.4f}")

    # 4. Domain centroid spread
    domain_points = defaultdict(list)
    for g in glyphs_out.values():
        for d in g["domains"]:
            domain_points[d].append([g["x"], g["y"], g["z"]])

    log(f"  Domain centroids ({len(domain_points)} domains):")
    for dom in sorted(domain_points.keys()):
        pts = np.array(domain_points[dom])
        cx, cy, cz = pts.mean(axis=0)
        spread = pts.std()
        log(f"    {dom:25s} n={len(pts):4d} center=({cx:+.3f},{cy:+.3f},{cz:+.3f}) spread={spread:.3f}")


# ─── Verify ───────────────────────────────────────────────────────

def verify():
    """Check output file integrity."""
    if not OUTPUT_PATH.exists():
        print(f"[WT4] No output found at {OUTPUT_PATH}. Run without --verify first.")
        return

    with open(OUTPUT_PATH, encoding="utf-8") as f:
        data = json.load(f)

    meta = data["meta"]
    glyphs = data["glyphs"]
    print(f"[WT4] Verify: {OUTPUT_PATH}")
    print(f"  Method: {meta['method']}")
    print(f"  Glyphs: {meta['n_glyphs']}, Concepts: {meta['n_concepts']}")
    print(f"  Eigenvalues: {meta['eigenvalues'][:5]}...")
    print(f"  Build date: {meta['build_date']}")

    xs = [g["x"] for g in glyphs.values()]
    ys = [g["y"] for g in glyphs.values()]
    zs = [g["z"] for g in glyphs.values()]
    nds = [g["nd"] for g in glyphs.values()]
    print(f"  x range: [{min(xs):.3f}, {max(xs):.3f}]")
    print(f"  y range: [{min(ys):.3f}, {max(ys):.3f}]")
    print(f"  z range: [{min(zs):.3f}, {max(zs):.3f}]")
    print(f"  nd range: [{min(nds)}, {max(nds)}], mean={np.mean(nds):.1f}")


# ─── Build ────────────────────────────────────────────────────────

def build():
    """Full WT4 computation."""
    log("[WT4] === FORME 3D SPECTRALE ===")
    t0 = time.time()

    # Phase 1: Load bipartite
    B, glyph_ids, concept_ids = load_bipartite(DB_PATH)

    # Phase 2: Compute nd
    nd, domains_per_glyph = compute_nd(DB_PATH, glyph_ids)

    # Phase 3: Project
    A = project_bipartite(B)

    # Phase 4: Laplacian + eigenvectors
    eigenvalues, eigenvectors = compute_laplacian(A)

    # Phase 5: Export
    glyphs_out = export_results(
        eigenvalues, eigenvectors, glyph_ids, concept_ids,
        nd, domains_per_glyph, B,
    )

    # Phase 6: Sanity checks
    sanity_checks(glyphs_out, eigenvalues)

    total = time.time() - t0
    log(f"\n[WT4] === DONE in {total:.1f}s ===")
    log(f"  {len(glyph_ids)} glyphs, {len(concept_ids)} concepts")
    log(f"  Output: {OUTPUT_PATH}")
    log(f"  Viz: {VIZ_OUTPUT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="WT4 — Forme 3D spectrale")
    parser.add_argument("--verify", action="store_true", help="Verify output")
    args = parser.parse_args()

    if args.verify:
        verify()
    else:
        build()


if __name__ == "__main__":
    main()
