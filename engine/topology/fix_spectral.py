#!/usr/bin/env python3
"""
Fix spectral positions: normalized Laplacian + outlier handling.
Uses saved co-occurrence matrix (no re-scan needed).
"""
import json, random, time
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def robust_norm(arr, clip_pct=98, scale=1.0):
    arr = arr - np.median(arr)
    lo = np.percentile(arr, 100 - clip_pct)
    hi = np.percentile(arr, clip_pct)
    arr = np.clip(arr, lo, hi)
    mx = max(abs(arr.min()), abs(arr.max()))
    if mx > 0:
        arr = arr / mx * scale
    return arr


def main():
    random.seed(42)

    print("=" * 60)
    print("FIX SPECTRAL POSITIONS -- Laplacien normalise")
    print("=" * 60)

    # Load saved matrix
    with open(ROOT / 'data' / 'topology' / 'domain_cooccurrence_matrix.json', encoding='utf-8') as f:
        saved = json.load(f)

    domains = saved['domains']
    matrix = np.array(saved['matrix'], dtype=np.float64)
    dpc = np.array(saved['domain_paper_count'], dtype=np.float64)
    N = len(domains)
    dom_idx = {d: i for i, d in enumerate(domains)}

    print(f"Domaines: {N}")
    print(f"Papers total: {saved['papers_total']:,}")
    print(f"Papers matches: {saved['papers_matched']:,}")

    # ── Log transform ──
    W = np.log1p(matrix)

    # ── Normalized Laplacian: L_norm = D^{-1/2} L D^{-1/2} ──
    # This prevents high-degree nodes from dominating eigenvectors
    degree = W.sum(axis=1)
    print(f"\nDegree range: {degree.min():.2f} - {degree.max():.2f}")
    print(f"Low-degree domains:")
    for i in np.argsort(degree)[:5]:
        print(f"  {domains[i]:25s} degree={degree[i]:.2f}  papers={dpc[i]:,.0f}")

    # D^{-1/2}
    d_inv_sqrt = np.zeros(N)
    for i in range(N):
        if degree[i] > 0:
            d_inv_sqrt[i] = 1.0 / np.sqrt(degree[i])

    D_inv_sqrt = np.diag(d_inv_sqrt)

    # L_norm = I - D^{-1/2} W D^{-1/2}
    L_norm = np.eye(N) - D_inv_sqrt @ W @ D_inv_sqrt

    eigenvalues, eigenvectors = np.linalg.eigh(L_norm)

    print(f"\nEigenvalues (10 premieres):")
    for i in range(min(10, N)):
        gap = eigenvalues[i+1] - eigenvalues[i] if i < N-1 else 0
        print(f"  L{i:2d} = {eigenvalues[i]:.6f}  gap={gap:.6f}")

    # Use eigenvectors 1 and 2 (skip 0 which is constant)
    px = eigenvectors[:, 1].copy()
    pz = eigenvectors[:, 2].copy()

    print(f"\nRaw px: [{px.min():.4f}, {px.max():.4f}] std={px.std():.4f}")
    print(f"Raw pz: [{pz.min():.4f}, {pz.max():.4f}] std={pz.std():.4f}")

    # ── Robust normalization: clip outliers at P2/P98, then scale to [-1, 1] ──
    px = robust_norm(px, clip_pct=98, scale=1.0)
    pz = robust_norm(pz, clip_pct=98, scale=1.0)

    print(f"\nNormalized px: [{px.min():.4f}, {px.max():.4f}] std={px.std():.4f}")
    print(f"Normalized pz: [{pz.min():.4f}, {pz.max():.4f}] std={pz.std():.4f}")

    # ── Show positions ──
    print(f"\nPOSITIONS SPECTRALES (Laplacien normalise):")
    for i, d in enumerate(domains):
        print(f"  {d:25s} ({px[i]:+.4f}, {pz[i]:+.4f})  papers={dpc[i]:,.0f}")

    # ── Save domain positions ──
    dom_positions = {}
    for i, d in enumerate(domains):
        dom_positions[d] = {
            'px': round(float(px[i]), 4),
            'pz': round(float(pz[i]), 4),
            'papers': int(dpc[i])
        }

    with open(ROOT / 'data' / 'topology' / 'domain_spectral_positions.json', 'w', encoding='utf-8') as f:
        json.dump(dom_positions, f, ensure_ascii=False, indent=2)
    print(f"\n-> domain_spectral_positions.json")

    # ── Update strates_export_v2.json ──
    print(f"\nMise a jour strates_export_v2.json...")
    with open(ROOT / 'data' / 'core' / 'strates_export_v2.json', encoding='utf-8') as f:
        data = json.load(f)

    s0 = data['strates'][0]['symbols']
    updated = 0
    not_found = 0

    for sym in s0:
        domain = sym.get('domain', 'mathematique')
        if domain in dom_idx:
            idx = dom_idx[domain]
            noise_scale = 0.08
            sym['px'] = round(float(px[idx]) + random.gauss(0, noise_scale), 4)
            sym['pz'] = round(float(pz[idx]) + random.gauss(0, noise_scale), 4)
            sym['spectral'] = 'cooc'
            updated += 1
        else:
            not_found += 1

    with open(ROOT / 'data' / 'core' / 'strates_export_v2.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"  Updated: {updated}, not found: {not_found}")
    print(f"\nDONE")


if __name__ == '__main__':
    main()
