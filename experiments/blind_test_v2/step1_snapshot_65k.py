#!/usr/bin/env python3
"""
Blind Test V2 — Step 1: Snapshot 2015 from 581 chunks
=====================================================
Scans all chunks, filters periods <= 2015, builds:
  - Sparse co-occurrence matrix (65K x 65K, upper triangular)
  - Activity vector (papers per concept)
  - Total works count

Output:
  blind_test_v2/snapshot_2015_65k.npz   (scipy sparse CSR)
  blind_test_v2/activity_2015.json      (activity + total_works)
  blind_test_v2/meta_2015.json          (scan metadata)

ZERO post-2015 data. Every period is checked.
"""
import gzip
import json
import os
import sys
import time
import gc
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix, save_npz

# === CONFIG ===
BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
CHUNKS_DIR = os.path.join(REPO, "data", "scan", "chunks")
N_CONCEPTS = 65026
CUTOFF_YEAR = 2015
BATCH_SIZE = 10  # flush every N chunks (safe for 16 GB RAM)


def period_year(s):
    """Extract year: '2007-06' -> 2007, '1500' -> 1500"""
    return int(s[:4])


def main():
    t0 = time.time()

    # --- Accumulators ---
    activity = np.zeros(N_CONCEPTS, dtype=np.float64)
    total_works = 0

    # Sparse matrix batching
    running_mat = None
    batch_arrays = []  # [(rows, cols, vals), ...]
    chunks_in_batch = 0
    total_pairs_global = 0
    periods_rejected = 0
    periods_accepted = 0

    # Find chunks
    chunk_dirs = sorted([
        d for d in os.listdir(CHUNKS_DIR)
        if os.path.isdir(os.path.join(CHUNKS_DIR, d)) and d.startswith("chunk_")
    ])
    n_chunks = len(chunk_dirs)
    print(f"Blind Test V2 — Step 1: Snapshot <={CUTOFF_YEAR}")
    print(f"{'=' * 60}")
    print(f"Chunks: {n_chunks} | Concepts: {N_CONCEPTS:,} | Batch: {BATCH_SIZE}")
    print(f"{'=' * 60}")
    sys.stdout.flush()

    for ci, chunk_name in enumerate(chunk_dirs):
        chunk_dir = os.path.join(CHUNKS_DIR, chunk_name)
        t_chunk = time.time()

        # --- meta.json: total_works ---
        meta_path = os.path.join(chunk_dir, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            for period, count in meta.get("period_papers", {}).items():
                if period_year(period) <= CUTOFF_YEAR:
                    total_works += count

        # --- activity.json.gz ---
        act_path = os.path.join(chunk_dir, "activity.json.gz")
        if os.path.exists(act_path):
            with gzip.open(act_path, 'rt', encoding='utf-8') as f:
                act_data = json.load(f)
            for period, concepts in act_data.items():
                if period_year(period) > CUTOFF_YEAR:
                    continue
                for idx_str, count in concepts.items():
                    idx = int(idx_str)
                    if 0 <= idx < N_CONCEPTS:
                        activity[idx] += count
            del act_data

        # --- cooc.json.gz ---
        cooc_path = os.path.join(chunk_dir, "cooc.json.gz")
        chunk_pairs_count = 0
        if os.path.exists(cooc_path):
            with gzip.open(cooc_path, 'rt', encoding='utf-8') as f:
                cooc_data = json.load(f)

            # Within-chunk aggregation across periods <= 2015
            chunk_agg = {}
            for period, pairs in cooc_data.items():
                yr = period_year(period)
                if yr > CUTOFF_YEAR:
                    periods_rejected += 1
                    continue
                periods_accepted += 1
                for pair_str, weight in pairs.items():
                    chunk_agg[pair_str] = chunk_agg.get(pair_str, 0) + weight

            del cooc_data
            gc.collect()

            # Convert to numpy
            n_pairs = len(chunk_agg)
            chunk_pairs_count = n_pairs
            if n_pairs > 0:
                rows = np.empty(n_pairs, dtype=np.int32)
                cols = np.empty(n_pairs, dtype=np.int32)
                vals = np.empty(n_pairs, dtype=np.float64)
                for i, (pair_str, w) in enumerate(chunk_agg.items()):
                    a, b = pair_str.split('|')
                    rows[i] = int(a)
                    cols[i] = int(b)
                    vals[i] = w
                batch_arrays.append((rows, cols, vals))
                total_pairs_global += n_pairs

            del chunk_agg
            gc.collect()

        chunks_in_batch += 1
        elapsed_chunk = time.time() - t_chunk
        elapsed_total = time.time() - t0

        # ETA
        rate = (ci + 1) / elapsed_total if elapsed_total > 0 else 1
        eta = (n_chunks - ci - 1) / rate

        batch_total = sum(a[0].shape[0] for a in batch_arrays)
        nnz_str = f"{running_mat.nnz:,}" if running_mat is not None else "0"
        print(f"  [{ci+1:3d}/{n_chunks}] {chunk_name} | "
              f"{elapsed_chunk:.1f}s | chunk_pairs: {chunk_pairs_count:,} | "
              f"batch: {batch_total:,} | nnz: {nnz_str} | "
              f"ETA: {eta/60:.0f}min")
        sys.stdout.flush()

        # --- Flush batch ---
        if chunks_in_batch >= BATCH_SIZE:
            if batch_arrays:
                all_r = np.concatenate([a[0] for a in batch_arrays])
                all_c = np.concatenate([a[1] for a in batch_arrays])
                all_v = np.concatenate([a[2] for a in batch_arrays])
                del batch_arrays
                batch_arrays = []

                batch_mat = coo_matrix(
                    (all_v, (all_r, all_c)),
                    shape=(N_CONCEPTS, N_CONCEPTS)
                ).tocsr()
                del all_r, all_c, all_v

                if running_mat is None:
                    running_mat = batch_mat
                else:
                    running_mat = running_mat + batch_mat
                del batch_mat
                gc.collect()

                mem_mb = (running_mat.data.nbytes +
                          running_mat.indices.nbytes +
                          running_mat.indptr.nbytes) / 1e6
                print(f"  >> FLUSH | nnz: {running_mat.nnz:,} | "
                      f"CSR: {mem_mb:.0f} MB")
                sys.stdout.flush()
            else:
                batch_arrays = []
            chunks_in_batch = 0

    # --- Final flush ---
    if batch_arrays:
        all_r = np.concatenate([a[0] for a in batch_arrays])
        all_c = np.concatenate([a[1] for a in batch_arrays])
        all_v = np.concatenate([a[2] for a in batch_arrays])
        del batch_arrays

        batch_mat = coo_matrix(
            (all_v, (all_r, all_c)),
            shape=(N_CONCEPTS, N_CONCEPTS)
        ).tocsr()
        del all_r, all_c, all_v

        if running_mat is None:
            running_mat = batch_mat
        else:
            running_mat = running_mat + batch_mat
        del batch_mat
        gc.collect()

    total_time = time.time() - t0

    # === SAVE ===
    print(f"\n{'=' * 60}")
    print(f"SAVING RESULTS")
    print(f"{'=' * 60}")

    # 1. Sparse matrix (upper triangular — pairs always have i < j from scanner)
    npz_path = os.path.join(BASE, "snapshot_2015_65k.npz")
    if running_mat is not None:
        save_npz(npz_path, running_mat)
        nnz = running_mat.nnz
        mem_mb = (running_mat.data.nbytes +
                  running_mat.indices.nbytes +
                  running_mat.indptr.nbytes) / 1e6
        print(f"  Matrix: {npz_path}")
        print(f"    Non-zeros: {nnz:,}")
        print(f"    CSR memory: {mem_mb:.0f} MB")
    else:
        nnz = 0
        print(f"  WARNING: No co-occurrence data found!")

    # 2. Activity vector + total_works
    n_active = int(np.sum(activity > 0))
    act_out = {
        "activity": activity.tolist(),
        "total_works": total_works,
        "n_active": n_active,
        "cutoff_year": CUTOFF_YEAR
    }
    act_path = os.path.join(BASE, "activity_2015.json")
    with open(act_path, 'w', encoding='utf-8') as f:
        json.dump(act_out, f)
    print(f"  Activity: {act_path}")
    print(f"    Active concepts: {n_active:,} / {N_CONCEPTS:,}")
    print(f"    Total works <={CUTOFF_YEAR}: {total_works:,}")

    # Top 10 most active
    top10_idx = np.argsort(-activity)[:10]
    print(f"    Top 10 activity:")
    for idx in top10_idx:
        print(f"      [{idx}] {activity[idx]:,.0f} papers")

    # 3. Meta
    meta_out = {
        "cutoff_year": CUTOFF_YEAR,
        "n_concepts": N_CONCEPTS,
        "n_chunks_scanned": n_chunks,
        "total_works_2015": total_works,
        "n_active_concepts": n_active,
        "n_pairs_nonzero": nnz,
        "total_pairs_accumulated": total_pairs_global,
        "periods_accepted": periods_accepted,
        "periods_rejected": periods_rejected,
        "batch_size": BATCH_SIZE,
        "scan_time_sec": round(total_time, 1),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    meta_path = os.path.join(BASE, "meta_2015.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta_out, f, indent=2)
    print(f"  Meta: {meta_path}")

    print(f"\n{'=' * 60}")
    print(f"STEP 1 DONE — {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"  Periods accepted: {periods_accepted:,} | rejected: {periods_rejected:,}")
    print(f"  Total works <={CUTOFF_YEAR}: {total_works:,}")
    print(f"  Active concepts: {n_active:,}")
    print(f"  Non-zero pairs: {nnz:,}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
