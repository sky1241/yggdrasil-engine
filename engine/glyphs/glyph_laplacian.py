#!/usr/bin/env python3
"""
Brique 6 — Glyph Spectral Laplacian
Aggregate glyph chunks → sparse matrix → normalized Laplacian → spectral positions.

Usage:
    python engine/glyphs/glyph_laplacian.py              # Run full pipeline
    python engine/glyphs/glyph_laplacian.py --status     # Show chunk status
"""
import gzip
import json
import sys
import argparse
import numpy as np
from pathlib import Path
from scipy import sparse
from scipy.sparse.linalg import eigsh

ROOT = Path(__file__).resolve().parent.parent.parent

SCAN_DIR = ROOT / "data" / "scan"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
OUTPUT_PATH = SCAN_DIR / "glyph_positions.json"

ARXIV_CHUNKS_DIR = SCAN_DIR / "glyph_chunks"
PMC_CHUNKS_DIR = SCAN_DIR / "pmc_glyph_chunks"

K_EIGENVECTORS = 9   # same as species classifier


def load_chunks(chunks_dir: Path) -> list[Path]:
    """Find all complete chunk directories."""
    if not chunks_dir.exists():
        return []
    chunks = []
    for d in sorted(chunks_dir.iterdir()):
        if d.is_dir() and (d / "cooc.json.gz").exists():
            meta_path = d / "meta.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                if meta.get("status") == "complete":
                    chunks.append(d)
    return chunks


def aggregate_chunks(chunk_dirs: list[Path], N: int) -> sparse.csr_matrix:
    """
    Aggregate all cooc.json.gz from chunks into a single N×N sparse matrix.
    Sums all period weights (we don't need temporal resolution here).
    """
    print(f"  Aggregating {len(chunk_dirs)} chunks into {N}×{N} matrix...")

    rows, cols, vals = [], [], []
    total_pairs = 0

    for i, cdir in enumerate(chunk_dirs):
        with gzip.open(cdir / "cooc.json.gz", "rt", encoding="utf-8") as f:
            cooc = json.load(f)

        for period, pairs in cooc.items():
            for pair_key, weight in pairs.items():
                parts = pair_key.split("|")
                if len(parts) != 2:
                    continue
                a, b = int(parts[0]), int(parts[1])
                if a >= N or b >= N:
                    continue
                rows.append(a)
                cols.append(b)
                vals.append(weight)
                total_pairs += 1

        if (i + 1) % 50 == 0 or i == len(chunk_dirs) - 1:
            print(f"    {i+1}/{len(chunk_dirs)} chunks, {total_pairs:,} pairs")

    # Build sparse COO → CSR
    W = sparse.coo_matrix((vals, (rows, cols)), shape=(N, N)).tocsr()

    # Symmetrize: W = W + W.T
    W = W + W.T

    print(f"  Matrix: {W.nnz:,} nonzeros, "
          f"density={100*W.nnz/(N*N):.1f}%")

    return W


def compute_laplacian(W: sparse.csr_matrix, k: int = K_EIGENVECTORS):
    """
    Compute normalized Laplacian L_sym = D^{-1/2} W D^{-1/2}
    and return top-k eigenvectors.
    """
    N = W.shape[0]
    print(f"  Computing normalized Laplacian ({N}×{N}, k={k})...")

    # Degree vector
    d = np.array(W.sum(axis=1)).flatten()

    # D^{-1/2}, handle zero degrees
    d_inv_sqrt = np.zeros(N)
    mask = d > 0
    d_inv_sqrt[mask] = 1.0 / np.sqrt(d[mask])
    D_inv_sqrt = sparse.diags(d_inv_sqrt)

    # L_sym = D^{-1/2} W D^{-1/2}
    L_sym = D_inv_sqrt @ W @ D_inv_sqrt

    # Top-k eigenvalues/vectors (largest magnitude for L_sym)
    eigenvalues, eigenvectors = eigsh(L_sym, k=k, which="LM")

    # Sort by eigenvalue descending
    idx = np.argsort(-eigenvalues)
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    print(f"  Eigenvalues: {eigenvalues}")
    print(f"  Active nodes (degree>0): {mask.sum()}/{N}")

    return eigenvalues, eigenvectors, d


def normalize_positions(eigenvectors: np.ndarray, scale: float = 1.5,
                       clip_pct: float = 99.0):
    """
    Extract 2D positions from eigenvectors[:,1] and [:,2].
    Normalize robustly with percentile clipping.
    """
    # Skip eigvec[:,0] (constant Fiedler), use 1 and 2
    px_raw = eigenvectors[:, 1]
    pz_raw = eigenvectors[:, 2]

    # Robust normalization
    for arr in [px_raw, pz_raw]:
        p_lo = np.percentile(arr[arr != 0], 100 - clip_pct) if np.any(arr != 0) else -1
        p_hi = np.percentile(arr[arr != 0], clip_pct) if np.any(arr != 0) else 1
        span = max(abs(p_lo), abs(p_hi))
        if span > 0:
            arr[:] = np.clip(arr / span, -1, 1) * scale

    return px_raw, pz_raw


def normalize_all_positions(eigenvectors: np.ndarray, scale: float = 1.5,
                            clip_pct: float = 99.0):
    """
    Extract ALL eigenvector coordinates (skip [0] = constant).
    Returns array of shape (N, K-1).
    """
    K = eigenvectors.shape[1]
    coords = eigenvectors[:, 1:].copy()  # skip eigvec 0

    for col in range(coords.shape[1]):
        arr = coords[:, col]
        nonzero = arr[arr != 0]
        if len(nonzero) == 0:
            continue
        p_lo = np.percentile(nonzero, 100 - clip_pct)
        p_hi = np.percentile(nonzero, clip_pct)
        span = max(abs(p_lo), abs(p_hi))
        if span > 0:
            coords[:, col] = np.clip(arr / span, -1, 1) * scale

    return coords


def run(k: int = K_EIGENVECTORS):
    """Full pipeline: aggregate → Laplacian → positions → save."""
    print("=== Glyph Spectral Laplacian ===")

    # Load registry
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    N = reg["meta"]["total"]
    print(f"Registry: {N} glyphs")

    # Find chunks
    arxiv_chunks = load_chunks(ARXIV_CHUNKS_DIR)
    pmc_chunks = load_chunks(PMC_CHUNKS_DIR)
    all_chunks = arxiv_chunks + pmc_chunks
    print(f"Chunks: {len(arxiv_chunks)} arXiv + {len(pmc_chunks)} PMC = {len(all_chunks)} total")

    if not all_chunks:
        print("  ERROR: No complete chunks found. Run scanners first.")
        sys.exit(1)

    # Aggregate
    W = aggregate_chunks(all_chunks, N)

    # Laplacian
    eigenvalues, eigenvectors, degrees = compute_laplacian(W, k=k)

    # Positions (2D legacy + all K-1 coords)
    px, pz = normalize_positions(eigenvectors)
    all_coords = normalize_all_positions(eigenvectors)

    # Save
    glyphs_out = {}
    for gid_str, g in reg["glyphs"].items():
        idx = g["glyph_id"]
        glyphs_out[gid_str] = {
            "symbol": g["symbol"],
            "name": g["name"],
            "px": round(float(px[idx]), 6),
            "pz": round(float(pz[idx]), 6),
            "coords": [round(float(c), 6) for c in all_coords[idx]],
            "degree": round(float(degrees[idx]), 4),
            "semantic_group": g["semantic_group"],
            "category": g["category"],
        }

    output = {
        "meta": {
            "total": N,
            "k": k,
            "method": "glyph_laplacian_v2",
            "chunks_arxiv": len(arxiv_chunks),
            "chunks_pmc": len(pmc_chunks),
            "matrix_nnz": int(W.nnz),
            "matrix_density_pct": round(100 * W.nnz / (N * N), 2),
            "eigenvalues": [round(float(v), 6) for v in eigenvalues],
            "active_glyphs": int(np.sum(degrees > 0)),
        },
        "glyphs": glyphs_out,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)

    active = np.sum(degrees > 0)
    print(f"\n  Output: {OUTPUT_PATH}")
    print(f"  Active glyphs: {active}/{N}")
    print(f"  Coords: {all_coords.shape[1]} dimensions (eigenvectors 1-{k-1})")
    print(f"  Position range: px=[{px.min():.3f}, {px.max():.3f}], "
          f"pz=[{pz.min():.3f}, {pz.max():.3f}]")


def show_status():
    arxiv = load_chunks(ARXIV_CHUNKS_DIR)
    pmc = load_chunks(PMC_CHUNKS_DIR)
    print(f"=== Glyph Laplacian Status ===")
    print(f"  arXiv chunks complete: {len(arxiv)}")
    print(f"  PMC chunks complete: {len(pmc)}")
    print(f"  Total: {len(arxiv) + len(pmc)}")
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            out = json.load(f)
        print(f"  Positions: {out['meta']['active_glyphs']}/{out['meta']['total']} active")
    else:
        print(f"  Positions: not computed yet")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Glyph Spectral Laplacian")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        run()
