#!/usr/bin/env python3
"""
YGGDRASIL ENGINE — GLYPH LAPLACIAN
════════════════════════════════════════════════════════════
Spectral link prediction: find missing formulas from eigenvector decomposition.

Memory-efficient: zipfile+mmap load (float32), zero-copy CSC transpose,
LinearOperator (no symmetrization needed → saves ~1 GB).

Method:
  1. Load co-occurrence matrix (cutoff 2015) as float32 via mmap
  2. Normalized adjacency via LinearOperator: D^{-1/2} (A+A^T) D^{-1/2}
  3. Extract K=64 largest eigenvectors ("glyphs")
  4. Score(i,j) = Σ_k λ_k × v_k(i) × v_k(j)
  5. High score + zero observed = PREDICTION

Sky × Claude — 2 Mars 2026, Versoix
"""

import gc
import json
import os
import sys
import time
import zipfile
import heapq

# CRITICAL: import numpy FIRST and pre-load data BEFORE importing scipy.
# scipy + sklearn imports consume ~200-300 MB. If we import them first,
# we can't allocate the 316 MB data array. Loading data first works.
import numpy as np
# scipy imports are DEFERRED to after data loading (see main())

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
BT_DIR = os.path.join(REPO, "blind_test_v2")
N = 65026


def _json_default(obj):
    """Handle numpy types for JSON serialization."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Not JSON serializable: {type(obj)}")
K = 64  # number of glyphs (eigenvectors)
TOP_ACTIVE = 5000
N_NEIGHBORS = 100
TOP_K = 10000


def _read_npy_from_zip(zf, member, target_dtype=None):
    """Read a .npy array from inside a zip, optionally converting dtype.

    Streams in chunks → peak memory = only the output array.
    """
    import struct as _struct
    with zf.open(member) as f:
        # Parse npy header
        magic = f.read(6)
        ver = _struct.unpack('<BB', f.read(2))
        if ver[0] == 1:
            hdr_len = _struct.unpack('<H', f.read(2))[0]
        else:
            hdr_len = _struct.unpack('<I', f.read(4))[0]
        hdr = f.read(hdr_len).decode('latin1')

        # Parse dtype and shape from header string
        # Format: "{'descr': '<f8', 'fortran_order': False, 'shape': (82700789,), }"
        import ast
        d = ast.literal_eval(hdr.strip())
        src_dtype = np.dtype(d['descr'])
        shape = d['shape']
        n = 1
        for s in shape:
            n *= s

        out_dtype = target_dtype if target_dtype else src_dtype
        out = np.empty(n, dtype=out_dtype)

        if src_dtype == out_dtype:
            # Direct read
            raw = f.read(n * src_dtype.itemsize)
            out[:] = np.frombuffer(raw, dtype=src_dtype)
        else:
            # Streaming conversion (e.g., float64 → float32)
            CHUNK = 500_000
            pos = 0
            while pos < n:
                count = min(CHUNK, n - pos)
                raw = f.read(count * src_dtype.itemsize)
                if not raw:
                    break
                chunk = np.frombuffer(raw, dtype=src_dtype)
                out[pos:pos + len(chunk)] = chunk
                pos += len(chunk)

    return out.reshape(shape) if len(shape) > 1 else out


def _load_raw_arrays(npz_path):
    """Load raw arrays from .npz, converting data to float32.

    Called BEFORE scipy imports to ensure memory is available.
    Returns: (data_f32, indices_i32, indptr)
    """
    with zipfile.ZipFile(npz_path) as zf:
        print("    Loading indptr...")
        indptr = _read_npy_from_zip(zf, 'indptr.npy')

        print("    Streaming data float64→float32 (316 MB)...")
        data_f32 = _read_npy_from_zip(zf, 'data.npy', target_dtype=np.float32)

        print("    Loading indices int32 (316 MB)...")
        indices = _read_npy_from_zip(zf, 'indices.npy', target_dtype=np.int32)

    return data_f32, indices, indptr


def main():
    t0 = time.time()
    print("=" * 80)
    print("GLYPH LAPLACIAN — Spectral Link Prediction")
    print(f"K = {K} glyphs | Cutoff 2015 | 65,026 concepts")
    print("=" * 80)

    # ══════════════════════════════════════════════
    # [1/7] LOAD
    # ══════════════════════════════════════════════
    print("\n[1/7] Loading data...")

    npz_path = os.path.join(BT_DIR, "snapshot_2015_65k.npz")

    # PHASE A: Load raw arrays BEFORE importing scipy (saves ~300 MB headroom)
    data_f32, indices_i32, indptr = _load_raw_arrays(npz_path)
    print(f"  Raw arrays: data={data_f32.nbytes/1e6:.0f} MB, "
          f"indices={indices_i32.nbytes/1e6:.0f} MB")

    # Log-transform data in-place
    np.log1p(data_f32, out=data_f32)
    print(f"  Log-transformed in-place")

    # PHASE B: Now import scipy (large arrays already allocated)
    print("  Importing scipy...")
    from scipy.sparse import csr_matrix, csc_matrix
    from scipy.sparse.linalg import eigsh, LinearOperator
    from scipy.stats import mannwhitneyu

    mat = csr_matrix((data_f32, indices_i32, indptr), shape=(N, N))
    del data_f32, indices_i32, indptr  # CSR owns the arrays now
    gc.collect()
    print(f"  CSR matrix: {mat.shape}, nnz={mat.nnz:,}")

    # Load metadata sequentially (free each before loading next)
    print("  Loading activity...")
    with open(os.path.join(BT_DIR, "activity_2015.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)
    del act_data; gc.collect()

    print("  Loading concepts...")
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        c65 = json.load(f)
    idx_to_name = {}
    idx_to_level = {}
    url_to_idx = {}
    for url, info in c65["concepts"].items():
        idx_to_name[info["idx"]] = info["name"]
        idx_to_level[info["idx"]] = info.get("level", -1)
        url_to_idx[url] = info["idx"]
    del c65; gc.collect()

    print("  Loading species...")
    with open(os.path.join(BT_DIR, "species_2015.json"), 'r', encoding='utf-8') as f:
        sp_data = json.load(f)
    species_map = np.full(N, -1, dtype=np.int32)
    for url, info in sp_data["concepts"].items():
        if url in url_to_idx:
            species_map[url_to_idx[url]] = info["species"]
    del sp_data, url_to_idx; gc.collect()

    print("  Loading ground truth...")
    with open(os.path.join(BT_DIR, "ground_truth_v2.json"), 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    breakthroughs = [b for b in gt_data["breakthroughs"] if b.get("matched")]
    del gt_data
    print(f"  {len(breakthroughs)} breakthroughs, {int(np.sum(activity > 0)):,} active concepts")
    print(f"  Loaded in {time.time()-t0:.1f}s")

    # ══════════════════════════════════════════════
    # [2/7] NORMALIZED ADJACENCY (LinearOperator, no symmetrize)
    # ══════════════════════════════════════════════
    print("\n[2/7] Building normalized adjacency LinearOperator...")
    t1 = time.time()

    # Compute degrees of symmetric matrix A + A^T
    # degree[i] = row_sum(A)[i] + col_sum(A)[i]  (A is upper-triangular)
    row_sums = np.array(mat.sum(axis=1), dtype=np.float64).flatten()
    col_sums = np.array(mat.sum(axis=0), dtype=np.float64).flatten()
    degrees = row_sums + col_sums
    del row_sums, col_sums

    d_inv_sqrt = np.zeros(N, dtype=np.float64)
    mask = degrees > 0
    d_inv_sqrt[mask] = 1.0 / np.sqrt(degrees[mask])
    connected = int(np.sum(mask))
    print(f"  Connected: {connected:,} / {N:,}")

    # Zero-copy CSC transpose view:
    # Reinterpret CSR arrays (indptr, indices, data) as CSC → gives A^T
    # CSR row j → CSC column j, CSR col indices → CSC row indices
    mat_T = csc_matrix((mat.data, mat.indices, mat.indptr), shape=(N, N))
    print(f"  Zero-copy CSC transpose created (0 extra MB)")

    # LinearOperator: computes D^{-1/2} (A + A^T) D^{-1/2} x
    n_matvec = [0]

    def matvec(x):
        n_matvec[0] += 1
        # Scale by D^{-1/2}
        scaled = (x * d_inv_sqrt).astype(np.float32)
        # A × scaled (CSR, upper-tri)
        z = mat.dot(scaled).astype(np.float64)
        # A^T × scaled (CSC = zero-copy transpose)
        z += mat_T.dot(scaled).astype(np.float64)
        # Scale by D^{-1/2}
        return z * d_inv_sqrt

    op = LinearOperator((N, N), matvec=matvec, dtype=np.float64)
    print(f"  LinearOperator ready ({time.time()-t1:.1f}s)")

    # ══════════════════════════════════════════════
    # [3/7] EIGSH K=64
    # ══════════════════════════════════════════════
    print(f"\n[3/7] eigsh(op, k={K}, which='LM', maxiter=5000)...")
    t2 = time.time()

    eigenvalues, eigenvectors = eigsh(op, k=K, which='LM', maxiter=5000)
    dt = time.time() - t2
    print(f"  {n_matvec[0]} matvec calls in {dt:.1f}s ({dt/60:.1f} min)")

    # Sort by descending eigenvalue
    order = np.argsort(-eigenvalues)
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    print(f"  Eigenvalues top 5: {np.round(eigenvalues[:5], 4)}")
    print(f"  Eigenvalues bot 5: {np.round(eigenvalues[-5:], 4)}")

    # ══════════════════════════════════════════════
    # [4/7] BUILD EMBEDDING
    # ══════════════════════════════════════════════
    print(f"\n[4/7] Building spectral embedding U (65K × {K})...")

    # U[i] = eigenvectors[i] * sqrt(|eigenvalues|)
    # Then Score(i,j) = U[i] @ U[j] = Σ_k λ_k × v_k(i) × v_k(j)
    sqrt_lambda = np.sqrt(np.abs(eigenvalues))
    U = eigenvectors * sqrt_lambda[np.newaxis, :]  # (N, K)
    print(f"  Embedding: {U.shape}, {U.nbytes / 1e6:.1f} MB")

    embed_path = os.path.join(REPO, "data", "scan", "spectral_embeddings.npy")
    np.save(embed_path, U)
    print(f"  Saved: {embed_path}")

    # ══════════════════════════════════════════════
    # [5/7] SCORE + RANK
    # ══════════════════════════════════════════════
    print(f"\n[5/7] Scoring predictions...")
    t3 = time.time()

    # A) Score ground truth pairs
    print("  A) Ground truth scores:")
    gt_scores = []
    for bt in breakthroughs:
        i, j = bt["concept_a_idx"], bt["concept_b_idx"]
        score = float(U[i] @ U[j])
        gt_scores.append(score)
        print(f"    {bt['name']:30s} score={score:.6f}")
    gt_scores = np.array(gt_scores)

    # B) Find top predictions (zero-cooc, inter-species, level >= 2)
    print(f"\n  B) Searching top predictions...")

    # Select top concepts by degree
    active_idxs = np.where(degrees > 0)[0]
    top_active = active_idxs[np.argsort(-degrees[active_idxs])[:TOP_ACTIVE]]
    print(f"  Top {TOP_ACTIVE} concepts by degree")

    # Precompute normalized U for cosine similarity
    U_norms = np.linalg.norm(U, axis=1, keepdims=True)
    U_norms[U_norms == 0] = 1
    U_normed = U / U_norms

    # Min-heap for top predictions
    heap = []
    heap_min = -np.inf
    n_candidates = 0

    print(f"  Scanning {TOP_ACTIVE} concepts × {N_NEIGHBORS} neighbors...")
    t_scan = time.time()

    for ci, idx_a in enumerate(top_active):
        if (ci + 1) % 500 == 0:
            dt_scan = time.time() - t_scan
            print(f"    {ci+1}/{TOP_ACTIVE} ({dt_scan:.0f}s, heap={len(heap)})...")

        sp_a = species_map[idx_a]
        if sp_a < 0:
            continue
        lvl_a = idx_to_level.get(int(idx_a), -1)
        if lvl_a < 2:
            continue

        # Compute spectral scores to all concepts
        raw_scores = U[idx_a] @ U.T  # (N,)

        # Find top N_NEIGHBORS by cosine similarity
        sims = U_normed[idx_a] @ U_normed.T  # (N,)
        top_idxs = np.argpartition(-sims, N_NEIGHBORS)[:N_NEIGHBORS]

        # Get existing neighbors of idx_a from upper-tri CSR
        lo_a, hi_a = int(mat.indptr[idx_a]), int(mat.indptr[idx_a + 1])
        row_neighbors = set(mat.indices[lo_a:hi_a].tolist())

        for idx_b in top_idxs:
            idx_b = int(idx_b)
            if idx_b == idx_a:
                continue

            # Inter-species filter
            sp_b = species_map[idx_b]
            if sp_b < 0 or sp_a == sp_b:
                continue

            # Level filter
            lvl_b = idx_to_level.get(idx_b, -1)
            if lvl_b < 2:
                continue

            # Zero-cooc filter (check both directions of upper-tri)
            lo, hi = min(idx_a, idx_b), max(idx_a, idx_b)
            if lo == idx_a:
                # idx_a is the smaller index → check if hi is in row neighbors
                if hi in row_neighbors:
                    continue
            else:
                # idx_b is the smaller index → check mat[idx_b, idx_a]
                lo_b, hi_b = int(mat.indptr[idx_b]), int(mat.indptr[idx_b + 1])
                if hi_b > lo_b:
                    cols_b = mat.indices[lo_b:hi_b]
                    if np.searchsorted(cols_b, idx_a) < len(cols_b) and \
                       cols_b[min(np.searchsorted(cols_b, idx_a), len(cols_b)-1)] == idx_a:
                        continue

            score = float(raw_scores[idx_b])
            n_candidates += 1

            if len(heap) < TOP_K:
                heapq.heappush(heap, (score, idx_a, idx_b))
                if len(heap) == TOP_K:
                    heap_min = heap[0][0]
            elif score > heap_min:
                heapq.heapreplace(heap, (score, idx_a, idx_b))
                heap_min = heap[0][0]

    dt_scan = time.time() - t_scan
    print(f"  Scanned in {dt_scan:.1f}s, candidates: {n_candidates:,}")

    # Free the sparse matrix now
    del mat, mat_T; gc.collect()

    # Sort and deduplicate
    predictions = sorted(heap, key=lambda x: -x[0])
    seen = set()
    unique_preds = []
    for score, i, j in predictions:
        pair = (min(i, j), max(i, j))
        if pair not in seen:
            seen.add(pair)
            unique_preds.append((score, i, j))
    predictions = unique_preds[:TOP_K]
    print(f"  Unique predictions: {len(predictions):,}")
    if predictions:
        print(f"  Score range: [{predictions[-1][0]:.6f}, {predictions[0][0]:.6f}]")

    # ══════════════════════════════════════════════
    # [6/7] NAME GLYPHS + DECOMPOSE
    # ══════════════════════════════════════════════
    print(f"\n[6/7] Naming {K} glyphs + decomposing top 100...")

    glyphs = []
    for k in range(K):
        vec = eigenvectors[:, k]
        top_pos_idxs = np.argsort(-vec)[:10]
        top_neg_idxs = np.argsort(vec)[:10]

        pos_names = [idx_to_name.get(int(i), f"?{i}") for i in top_pos_idxs]
        neg_names = [idx_to_name.get(int(i), f"?{i}") for i in top_neg_idxs]

        name_pos = pos_names[0].split()[0] if pos_names else "?"
        name_neg = neg_names[0].split()[0] if neg_names else "?"
        auto_name = f"{name_pos}↔{name_neg}"

        glyphs.append({
            "id": k,
            "eigenvalue": float(eigenvalues[k]),
            "name": auto_name,
            "top_positive": [
                {"idx": int(top_pos_idxs[i]), "name": pos_names[i],
                 "loading": float(vec[top_pos_idxs[i]])}
                for i in range(10)
            ],
            "top_negative": [
                {"idx": int(top_neg_idxs[i]), "name": neg_names[i],
                 "loading": float(vec[top_neg_idxs[i]])}
                for i in range(10)
            ],
        })

    # Display top 20 glyphs
    print(f"\n  {'Glyph':>8s}  {'λ':>8s}  {'Name':25s}  Top+ / Top-")
    print(f"  {'─'*8}  {'─'*8}  {'─'*25}  {'─'*50}")
    for g in glyphs[:20]:
        pos = g["top_positive"][0]["name"][:20] if g["top_positive"] else "?"
        neg = g["top_negative"][0]["name"][:20] if g["top_negative"] else "?"
        print(f"  G{g['id']:>6d}  {g['eigenvalue']:8.4f}  {g['name']:25s}  {pos} / {neg}")
    if K > 20:
        print(f"  ... ({K - 20} more)")

    # Save glyphs
    glyphs_path = os.path.join(REPO, "data", "scan", "glyphs.json")
    with open(glyphs_path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "k": K,
                "method": "eigsh_normalized_adjacency_log1p_linearop",
                "cutoff": 2015,
                "eigenvalues": [float(e) for e in eigenvalues],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "glyphs": glyphs,
        }, f, indent=2, ensure_ascii=False, default=_json_default)
    print(f"  Saved: {glyphs_path}")

    # Decompose top 100 predictions
    print(f"\n  Top 30 predictions with glyph decomposition:")
    top_predictions = []
    for rank, (score, i, j) in enumerate(predictions[:100]):
        contributions = eigenvalues * eigenvectors[i] * eigenvectors[j]
        top_glyph_idxs = np.argsort(-np.abs(contributions))[:5]

        formula = [
            {"glyph_id": int(gk), "glyph_name": glyphs[int(gk)]["name"],
             "contribution": float(contributions[gk])}
            for gk in top_glyph_idxs
        ]

        name_a = idx_to_name.get(i, f"?{i}")
        name_b = idx_to_name.get(j, f"?{j}")

        top_predictions.append({
            "rank": rank + 1, "score": score,
            "concept_a": {"idx": i, "name": name_a, "species": int(species_map[i]),
                          "level": idx_to_level.get(i, -1)},
            "concept_b": {"idx": j, "name": name_b, "species": int(species_map[j]),
                          "level": idx_to_level.get(j, -1)},
            "formula": formula,
        })

        if rank < 30:
            glyph_str = " + ".join(
                f"{f['glyph_name']}({f['contribution']:+.4f})" for f in formula[:3])
            print(f"    {rank+1:3d}. [{score:.4f}] {name_a[:25]:25s} × {name_b[:25]:25s}"
                  f"  via {glyph_str}")

    # Save all predictions
    all_predictions = []
    for rank, (score, i, j) in enumerate(predictions):
        entry = {
            "rank": rank + 1, "score": score,
            "concept_a_idx": i, "concept_a_name": idx_to_name.get(i, f"?{i}"),
            "concept_b_idx": j, "concept_b_name": idx_to_name.get(j, f"?{j}"),
            "species_a": int(species_map[i]), "species_b": int(species_map[j]),
        }
        if rank < 100:
            contributions = eigenvalues * eigenvectors[i] * eigenvectors[j]
            top_glyph_idxs = np.argsort(-np.abs(contributions))[:5]
            entry["formula"] = [
                {"glyph_id": int(gk), "glyph_name": glyphs[int(gk)]["name"],
                 "contribution": float(contributions[gk])}
                for gk in top_glyph_idxs
            ]
        all_predictions.append(entry)

    pred_path = os.path.join(REPO, "data", "scan", "spectral_predictions.json")
    with open(pred_path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "method": "glyph_laplacian_spectral",
                "k": K, "cutoff": 2015,
                "n_predictions": len(all_predictions),
                "top_active": TOP_ACTIVE,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "predictions": all_predictions,
        }, f, indent=2, ensure_ascii=False, default=_json_default)
    print(f"\n  Saved: {pred_path}")

    # ══════════════════════════════════════════════
    # [7/7] BLIND TEST COMPARISON
    # ══════════════════════════════════════════════
    print(f"\n[7/7] Blind test: spectral vs P4...")

    pred_scores = np.array([p[0] for p in predictions])  # sorted descending

    bt_results = []
    for bt in breakthroughs:
        i, j = bt["concept_a_idx"], bt["concept_b_idx"]
        score = float(U[i] @ U[j])

        rank = int(np.searchsorted(-pred_scores, -score)) + 1
        if rank > len(predictions):
            rank = len(predictions) + 1

        bt_results.append({
            "name": bt["name"], "year": bt["year"],
            "concept_a": bt["concept_a_name"], "concept_b": bt["concept_b_name"],
            "spectral_score": score, "rank": rank,
            "in_top_100": rank <= 100, "in_top_1000": rank <= 1000,
            "in_top_10000": rank <= 10000,
        })

    n_gt = len(bt_results)
    recall_100 = sum(1 for r in bt_results if r["in_top_100"]) / n_gt
    recall_1000 = sum(1 for r in bt_results if r["in_top_1000"]) / n_gt
    recall_10000 = sum(1 for r in bt_results if r["in_top_10000"]) / n_gt
    median_rank = float(np.median([r["rank"] for r in bt_results]))

    # Mann-Whitney U: GT scores vs random pairs
    rng = np.random.RandomState(42)
    random_scores = []
    for _ in range(2000):
        ri, rj = rng.randint(0, N), rng.randint(0, N)
        while ri == rj:
            rj = rng.randint(0, N)
        random_scores.append(float(U[ri] @ U[rj]))
    random_scores = np.array(random_scores)

    U_stat, p_value = mannwhitneyu(gt_scores, random_scores, alternative='greater')
    n1, n2 = len(gt_scores), len(random_scores)
    effect_r = 1 - 2 * U_stat / (n1 * n2)
    pooled_std = np.sqrt(
        (np.var(gt_scores) * (n1 - 1) + np.var(random_scores) * (n2 - 1))
        / (n1 + n2 - 2)
    ) if (n1 + n2 > 2) else 1
    cohens_d = (np.mean(gt_scores) - np.mean(random_scores)) / pooled_std \
        if pooled_std > 0 else 0

    # Display
    print(f"\n{'='*80}")
    print("GLYPH LAPLACIAN — BLIND TEST RESULTS")
    print(f"{'='*80}")
    print(f"\n  SPECTRAL (K={K} glyphs)")
    print(f"  {'─'*50}")
    print(f"  Recall@100:    {recall_100:.2%} ({int(recall_100 * n_gt)}/{n_gt})")
    print(f"  Recall@1,000:  {recall_1000:.2%} ({int(recall_1000 * n_gt)}/{n_gt})")
    print(f"  Recall@10,000: {recall_10000:.2%} ({int(recall_10000 * n_gt)}/{n_gt})")
    print(f"  Median rank:   {median_rank:,.0f}")
    print(f"  Mann-Whitney p = {p_value:.2e}")
    print(f"  Effect size r  = {effect_r:.4f}")
    print(f"  Cohen's d      = {cohens_d:.4f}")

    print(f"\n  P4 BASELINE (blind_test_v2)")
    print(f"  {'─'*50}")
    print(f"  Mann-Whitney p = 3.4e-12")
    print(f"  Cohen's d      = 0.44")

    print(f"\n  {'Breakthrough':<30s} {'Score':>10s} {'Rank':>8s} {'Top10K':>7s}")
    print(f"  {'─'*30} {'─'*10} {'─'*8} {'─'*7}")
    for r in sorted(bt_results, key=lambda x: x["rank"]):
        rank_str = f"{r['rank']:,}" if r['rank'] <= TOP_K else f">{TOP_K//1000}K"
        top_str = "YES" if r["in_top_10000"] else "no"
        print(f"  {r['name']:<30s} {r['spectral_score']:10.6f} {rank_str:>8s} {top_str:>7s}")

    # Save
    bt_path = os.path.join(REPO, "data", "scan", "spectral_blind_test.json")
    with open(bt_path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {"method": "glyph_laplacian", "k": K, "cutoff": 2015,
                     "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
            "spectral": {
                "recall_100": round(recall_100, 4),
                "recall_1000": round(recall_1000, 4),
                "recall_10000": round(recall_10000, 4),
                "median_rank": median_rank,
                "mann_whitney_U": float(U_stat),
                "p_value": float(p_value),
                "effect_size_r": round(float(effect_r), 4),
                "cohens_d": round(float(cohens_d), 4),
                "gt_score_mean": round(float(np.mean(gt_scores)), 8),
                "random_score_mean": round(float(np.mean(random_scores)), 8),
            },
            "p4_baseline": {"p_value": 3.4e-12, "cohens_d": 0.44},
            "per_breakthrough": bt_results,
        }, f, indent=2, ensure_ascii=False, default=_json_default)
    print(f"\n  Saved: {bt_path}")

    # SUMMARY
    total_time = time.time() - t0
    print(f"\n{'='*80}")
    print(f"GLYPH LAPLACIAN COMPLETE — {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"{'='*80}")
    print(f"  {K} glyphs extracted")
    print(f"  {len(predictions):,} spectral predictions")
    print(f"  Blind test: recall@100={recall_100:.0%}, "
          f"recall@1K={recall_1000:.0%}, recall@10K={recall_10000:.0%}")
    print(f"  p-value: {p_value:.2e} (P4: 3.4e-12)")


if __name__ == "__main__":
    main()
