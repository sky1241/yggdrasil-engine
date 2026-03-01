#!/usr/bin/env python3
"""
Predictions 2025 — Step 2: Spectral Clustering (FULL data)
==========================================================
K=9 species on the full co-occurrence matrix.

Input:
  predictions_2025/snapshot_full.npz
  predictions_2025/activity_full.json
  data/scan/concepts_65k.json

Output:
  predictions_2025/species_full.json
"""
import json
import os
import time
import gc
import numpy as np
from scipy.sparse import load_npz
from scipy.sparse.linalg import eigsh, LinearOperator
from sklearn.cluster import KMeans

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
K = 9
N_CONCEPTS = 65026


def main():
    t0 = time.time()
    print("Predictions 2025 — Step 2: Species Clustering (FULL data)")
    print("=" * 60)

    # Load matrix
    print("\n[1/5] Loading snapshot_full.npz...")
    mat = load_npz(os.path.join(BASE, "snapshot_full.npz"))
    print(f"  Shape: {mat.shape}, nnz: {mat.nnz:,}")

    # Compute degrees from original (upper triangular) matrix
    # W_sym = mat + mat.T, degree = row_sum(mat) + col_sum(mat)
    print("\n[2/5] Computing degrees (no full symmetrize)...")
    mat_t = mat.T.tocsr()
    degrees = np.array(mat.sum(axis=1)).flatten() + np.array(mat_t.sum(axis=1)).flatten()
    connected = int(np.sum(degrees > 0))
    print(f"  Connected: {connected:,} | Isolated: {N_CONCEPTS - connected:,}")

    # Activity
    print("\n[3/5] Loading activity...")
    with open(os.path.join(BASE, "activity_full.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)
    n_active = int(np.sum(activity > 0))
    print(f"  Active concepts: {n_active:,}")

    # Spectral clustering using LinearOperator (no full symmetric matrix in RAM)
    print(f"\n[4/5] Normalized adjacency via LinearOperator + eigsh (k={K})...")
    t1 = time.time()

    d_inv_sqrt = np.zeros(N_CONCEPTS, dtype=np.float64)
    deg_mask = degrees > 0
    d_inv_sqrt[deg_mask] = 1.0 / np.sqrt(degrees[deg_mask])

    # D^{-1/2} (mat + mat^T) D^{-1/2} @ x  =  D^{-1/2} mat (D^{-1/2} x) + D^{-1/2} mat^T (D^{-1/2} x)
    def matvec(x):
        scaled = d_inv_sqrt * x
        y = mat.dot(scaled) + mat_t.dot(scaled)
        return d_inv_sqrt * y

    A = LinearOperator((N_CONCEPTS, N_CONCEPTS), matvec=matvec, dtype=np.float64)
    print(f"  LinearOperator ready (mat: {mat.nnz:,} nnz)")

    eigenvalues, eigenvectors = eigsh(A, k=K, which='LM')
    dt = time.time() - t1
    print(f"  Eigenvalues: {np.round(eigenvalues, 4)}")
    print(f"  Computed in {dt:.1f}s")

    del mat, mat_t
    gc.collect()

    # KMeans
    print(f"\n[5/5] KMeans K={K}...")
    norms = np.linalg.norm(eigenvectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    eigvec_normed = eigenvectors / norms

    kmeans = KMeans(n_clusters=K, n_init=20, random_state=42)
    labels = kmeans.fit_predict(eigvec_normed)

    # Load concept names
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        c65 = json.load(f)

    idx_to_info = {}
    for cid, info in c65["concepts"].items():
        idx_to_info[info["idx"]] = {"id": cid, "name": info["name"], "level": info["level"]}

    # Report
    print()
    print("=" * 70)
    print(f"SPECIES FULL (K={K}, {n_active:,} active concepts)")
    print("=" * 70)

    species_counts = {}
    for k in range(K):
        mask_k = labels == k
        active_in_k = int(np.sum(mask_k & (activity > 0)))
        total_in_k = int(np.sum(mask_k))
        species_counts[k] = active_in_k

        indices = np.where(mask_k & (activity > 0))[0]
        degs = [(idx, degrees[idx]) for idx in indices]
        degs.sort(key=lambda x: -x[1])
        top_names = [idx_to_info[d[0]]["name"] for d in degs[:8] if d[0] in idx_to_info]
        top_str = ", ".join(top_names)
        print(f"  Species {k}: {active_in_k:>6,} active ({total_in_k:>6,} total) | Top: {top_str}")

    # Save
    result = {}
    for idx in range(N_CONCEPTS):
        if idx in idx_to_info:
            info = idx_to_info[idx]
            result[info["id"]] = {
                "name": info["name"],
                "level": info["level"],
                "species": int(labels[idx]),
                "degree": float(degrees[idx]),
                "active": bool(activity[idx] > 0)
            }

    output_path = os.path.join(BASE, "species_full.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "meta": {
                "total": len(result),
                "n_active": n_active,
                "k": K,
                "method": "spectral_clustering_full_data",
                "eigenvalues": eigenvalues.tolist(),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "species_counts": species_counts,
            "concepts": result
        }, f, ensure_ascii=False)

    total_time = time.time() - t0
    print(f"\nSaved: {output_path}")
    print(f"Step 2 DONE — {total_time:.0f}s ({total_time/60:.1f} min)")


if __name__ == "__main__":
    main()
