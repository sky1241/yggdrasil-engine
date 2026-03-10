#!/usr/bin/env python3
"""
Blind Test V2 — Step 1b: Spectral Clustering on 2015 matrix
============================================================
Re-runs spectral clustering K=9 on the co-occurrence matrix <= 2015
to avoid look-ahead contamination from species_65k.json (which used
all periods including post-2015).

Input:
  blind_test_v2/snapshot_2015_65k.npz   (from step 1)
  blind_test_v2/activity_2015.json      (from step 1)
  data/scan/concepts_65k.json           (for concept names)

Output:
  blind_test_v2/species_2015.json       (species labels from 2015 data ONLY)

Method: identical to engine/topology/species_classifier.py
  - Normalized adjacency: D^{-1/2} W D^{-1/2}
  - eigsh k=9 largest eigenvalues
  - KMeans K=9 on normalized eigenvectors
"""
import json
import os
import time
import numpy as np
from scipy import sparse
from scipy.sparse import load_npz
from scipy.sparse.linalg import eigsh
from sklearn.cluster import KMeans

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
K = 9
N_CONCEPTS = 65026


def main():
    t0 = time.time()
    print("Blind Test V2 — Step 1b: Species Clustering (2015 data only)")
    print("=" * 60)
    print(f"K = {K} species | NO post-2015 data")
    print("=" * 60)

    # 1. Load matrix
    print("\n[1/5] Loading snapshot_2015_65k.npz...")
    mat = load_npz(os.path.join(BASE, "snapshot_2015_65k.npz"))
    print(f"  Shape: {mat.shape}, nnz: {mat.nnz:,}")

    # 2. Symmetrize (matrix is upper-triangular from step 1)
    print("\n[2/5] Symmetrizing...")
    W = mat + mat.T
    W = W.tocsr()
    del mat
    print(f"  Symmetric: {W.nnz:,} non-zeros")

    degrees = np.array(W.sum(axis=1)).flatten()
    connected = int(np.sum(degrees > 0))
    isolated = N_CONCEPTS - connected
    print(f"  Connected: {connected:,} | Isolated: {isolated:,}")

    # 3. Load activity to identify concepts active <= 2015
    print("\n[3/5] Loading activity...")
    with open(os.path.join(BASE, "activity_2015.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)
    n_active = int(np.sum(activity > 0))
    print(f"  Active concepts (activity > 0): {n_active:,} / {N_CONCEPTS:,}")

    # 4. Spectral clustering
    print(f"\n[4/5] Normalized adjacency (in-place scaling) + eigsh (k={K})...")
    t1 = time.time()
    import gc

    d_inv_sqrt = np.zeros(N_CONCEPTS, dtype=np.float64)
    mask = degrees > 0
    d_inv_sqrt[mask] = 1.0 / np.sqrt(degrees[mask])

    # In-place D^{-1/2} W D^{-1/2} to avoid 3x memory peak
    # Ensure float64
    W = W.astype(np.float64)
    # Row scaling: W[i,:] *= d_inv_sqrt[i]
    for i in range(N_CONCEPTS):
        lo, hi = W.indptr[i], W.indptr[i + 1]
        if lo < hi:
            W.data[lo:hi] *= d_inv_sqrt[i]
    # Column scaling: W[:,j] *= d_inv_sqrt[j]
    W.data *= d_inv_sqrt[W.indices]
    print(f"  In-place scaling done")

    eigenvalues, eigenvectors = eigsh(W, k=K, which='LM')
    dt = time.time() - t1
    print(f"  Eigenvalues: {np.round(eigenvalues, 4)}")
    print(f"  Computed in {dt:.1f}s")

    del W
    gc.collect()

    # 5. KMeans
    print(f"\n[5/5] KMeans K={K}...")
    norms = np.linalg.norm(eigenvectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    eigvec_normed = eigenvectors / norms

    kmeans = KMeans(n_clusters=K, n_init=20, random_state=42)
    labels = kmeans.fit_predict(eigvec_normed)

    # Load concept names for reporting
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        c65 = json.load(f)

    idx_to_info = {}
    for cid, info in c65["concepts"].items():
        idx_to_info[info["idx"]] = {
            "id": cid, "name": info["name"], "level": info["level"]
        }

    # Report
    print()
    print("=" * 70)
    print(f"SPECIES 2015 (K={K}, {n_active:,} active concepts)")
    print("=" * 70)

    species_counts = {}
    for k in range(K):
        mask_k = labels == k
        # Count only ACTIVE concepts in this species
        active_in_k = int(np.sum(mask_k & (activity > 0)))
        total_in_k = int(np.sum(mask_k))
        species_counts[k] = active_in_k

        indices = np.where(mask_k & (activity > 0))[0]
        degs = [(idx, degrees[idx]) for idx in indices]
        degs.sort(key=lambda x: -x[1])
        top_names = []
        for d in degs[:8]:
            if d[0] in idx_to_info:
                top_names.append(idx_to_info[d[0]]["name"])
        top_str = ", ".join(top_names)
        print(f"  Species {k}: {active_in_k:>6,} active ({total_in_k:>6,} total) "
              f"| Top: {top_str}")

    # Save
    result = {}
    for idx in range(N_CONCEPTS):
        if idx in idx_to_info:
            info = idx_to_info[idx]
            result[info["id"]] = {
                "name": info["name"],
                "level": info["level"],
                "species": int(labels[idx]),
                "degree_2015": float(degrees[idx]),
                "active_2015": bool(activity[idx] > 0)
            }

    output_path = os.path.join(BASE, "species_2015.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "meta": {
                "total": len(result),
                "n_active": n_active,
                "k": K,
                "method": "spectral_clustering_2015_only",
                "eigenvalues": eigenvalues.tolist(),
                "cutoff_year": 2015,
                "warning": "ZERO post-2015 data — species labels safe for blind test",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "species_counts": species_counts,
            "concepts": result
        }, f, ensure_ascii=False)

    total_time = time.time() - t0
    print(f"\nSaved: {output_path}")
    print(f"Step 1b DONE — {total_time:.0f}s ({total_time/60:.1f} min)")


if __name__ == "__main__":
    main()
