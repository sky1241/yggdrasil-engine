#!/usr/bin/env python3
"""
Predictions 2025 — Step 1: Full Scan (NO cutoff)
=================================================
Scans all 581 chunks, ALL periods, builds:
  - Sparse co-occurrence matrix (65K x 65K, upper triangular)
  - Activity vector (papers per concept)
  - Total works count

NO cutoff. We take EVERYTHING.

Memory strategy: save intermediate checkpoint .npz files every 100 chunks,
then merge at the end. Avoids OOM from holding ~100M nnz CSR + batch in RAM.

Output:
  predictions_2025/snapshot_full.npz     (scipy sparse CSR)
  predictions_2025/activity_full.json    (activity + total_works)
  predictions_2025/meta_full.json        (scan metadata)
"""
import gzip
import json
import os
import sys
import time
import gc
import numpy as np
from scipy.sparse import coo_matrix, load_npz, save_npz

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
CHUNKS_DIR = os.path.join(REPO, "data", "scan", "chunks")
N_CONCEPTS = 65026
BATCH_SIZE = 5
CHECKPOINT_EVERY = 80  # save to disk every N chunks (keeps CSR < 600 MB)


def flush_batch_to_csr(batch_arrays):
    """Convert batch arrays to CSR matrix."""
    if not batch_arrays:
        return None

    all_r = np.concatenate([a[0] for a in batch_arrays])
    all_c = np.concatenate([a[1] for a in batch_arrays])
    all_v = np.concatenate([a[2] for a in batch_arrays])
    batch_arrays.clear()
    gc.collect()

    result = coo_matrix(
        (all_v, (all_r, all_c)),
        shape=(N_CONCEPTS, N_CONCEPTS)
    ).tocsr()
    del all_r, all_c, all_v
    gc.collect()
    return result


def main():
    t0 = time.time()

    activity = np.zeros(N_CONCEPTS, dtype=np.float64)
    total_works = 0

    running_mat = None
    batch_arrays = []
    chunks_in_batch = 0
    chunks_since_checkpoint = 0
    total_pairs_global = 0
    periods_total = 0
    checkpoint_files = []
    checkpoint_dir = os.path.join(BASE, "_checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    # === RESUME: detect existing checkpoints ===
    existing_ckpts = sorted([
        f for f in os.listdir(checkpoint_dir)
        if f.startswith("ckpt_") and f.endswith(".npz")
    ]) if os.path.isdir(checkpoint_dir) else []

    resume_from_chunk = 0
    if existing_ckpts:
        for ckpt_name in existing_ckpts:
            ckpt_path = os.path.join(checkpoint_dir, ckpt_name)
            checkpoint_files.append(ckpt_path)
        resume_from_chunk = len(existing_ckpts) * CHECKPOINT_EVERY
        print(f"RESUME: Found {len(existing_ckpts)} checkpoints, "
              f"skipping cooc for chunks 0-{resume_from_chunk - 1}")
        sys.stdout.flush()

    chunk_dirs = sorted([
        d for d in os.listdir(CHUNKS_DIR)
        if os.path.isdir(os.path.join(CHUNKS_DIR, d)) and d.startswith("chunk_")
    ])
    n_chunks = len(chunk_dirs)
    print(f"Predictions 2025 — Step 1: Full Scan (NO cutoff)")
    print(f"{'=' * 60}")
    print(f"Chunks: {n_chunks} | Concepts: {N_CONCEPTS:,} | Batch: {BATCH_SIZE}")
    print(f"Checkpoint every: {CHECKPOINT_EVERY} chunks")
    if resume_from_chunk > 0:
        print(f"Resuming cooc scan from chunk {resume_from_chunk}")
    print(f"{'=' * 60}")
    sys.stdout.flush()

    for ci, chunk_name in enumerate(chunk_dirs):
        chunk_dir = os.path.join(CHUNKS_DIR, chunk_name)
        t_chunk = time.time()

        # meta.json — ALWAYS scan (fast)
        meta_path = os.path.join(chunk_dir, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            for period, count in meta.get("period_papers", {}).items():
                total_works += count

        # activity.json.gz — ALWAYS scan (fast)
        act_path = os.path.join(chunk_dir, "activity.json.gz")
        if os.path.exists(act_path):
            with gzip.open(act_path, 'rt', encoding='utf-8') as f:
                act_data = json.load(f)
            for period, concepts in act_data.items():
                periods_total += 1
                for idx_str, count in concepts.items():
                    idx = int(idx_str)
                    if 0 <= idx < N_CONCEPTS:
                        activity[idx] += count
            del act_data
            gc.collect()

        # Skip cooc for already-checkpointed chunks
        if ci < resume_from_chunk:
            if (ci + 1) % 50 == 0 or ci + 1 == resume_from_chunk:
                print(f"  [{ci+1:3d}/{n_chunks}] {chunk_name} | "
                      f"activity only (cooc in checkpoint)")
                sys.stdout.flush()
            continue

        # Flush batch BEFORE loading cooc to free memory
        batch_pairs_count = sum(a[0].shape[0] for a in batch_arrays)
        if batch_pairs_count > 10_000_000:
            batch_mat = flush_batch_to_csr(batch_arrays)
            if batch_mat is not None:
                if running_mat is None:
                    running_mat = batch_mat
                else:
                    running_mat = running_mat + batch_mat
                del batch_mat
            batch_arrays = []
            chunks_in_batch = 0
            gc.collect()

        # cooc.json.gz
        cooc_path = os.path.join(chunk_dir, "cooc.json.gz")
        chunk_pairs_count = 0
        if os.path.exists(cooc_path):
            with gzip.open(cooc_path, 'rt', encoding='utf-8') as f:
                cooc_data = json.load(f)

            chunk_agg = {}
            for period, pairs in cooc_data.items():
                for pair_str, weight in pairs.items():
                    chunk_agg[pair_str] = chunk_agg.get(pair_str, 0) + weight

            del cooc_data
            gc.collect()

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
        chunks_since_checkpoint += 1
        elapsed_chunk = time.time() - t_chunk
        elapsed_total = time.time() - t0

        rate = (ci + 1) / elapsed_total if elapsed_total > 0 else 1
        eta = (n_chunks - ci - 1) / rate

        batch_total = sum(a[0].shape[0] for a in batch_arrays)
        nnz_str = f"{running_mat.nnz:,}" if running_mat is not None else "0"
        print(f"  [{ci+1:3d}/{n_chunks}] {chunk_name} | "
              f"{elapsed_chunk:.1f}s | chunk_pairs: {chunk_pairs_count:,} | "
              f"batch: {batch_total:,} | nnz: {nnz_str} | "
              f"ETA: {eta/60:.0f}min")
        sys.stdout.flush()

        # Flush batch every BATCH_SIZE chunks
        if chunks_in_batch >= BATCH_SIZE:
            batch_mat = flush_batch_to_csr(batch_arrays)
            if batch_mat is not None:
                if running_mat is None:
                    running_mat = batch_mat
                else:
                    running_mat = running_mat + batch_mat
                del batch_mat
            batch_arrays = []
            chunks_in_batch = 0
            gc.collect()

            if running_mat is not None:
                mem_mb = (running_mat.data.nbytes +
                          running_mat.indices.nbytes +
                          running_mat.indptr.nbytes) / 1e6
                print(f"  >> FLUSH | nnz: {running_mat.nnz:,} | CSR: {mem_mb:.0f} MB")
                sys.stdout.flush()

        # === CHECKPOINT: save to disk and reset ===
        if chunks_since_checkpoint >= CHECKPOINT_EVERY and running_mat is not None:
            # Flush any remaining batch first
            if batch_arrays:
                batch_mat = flush_batch_to_csr(batch_arrays)
                if batch_mat is not None:
                    running_mat = running_mat + batch_mat
                    del batch_mat
                batch_arrays = []
                chunks_in_batch = 0
                gc.collect()

            ckpt_id = len(checkpoint_files)
            ckpt_path = os.path.join(checkpoint_dir, f"ckpt_{ckpt_id:03d}.npz")
            save_npz(ckpt_path, running_mat)
            ckpt_nnz = running_mat.nnz
            checkpoint_files.append(ckpt_path)

            del running_mat
            running_mat = None
            gc.collect()

            print(f"  >> CHECKPOINT {ckpt_id} saved: {ckpt_nnz:,} nnz → {ckpt_path}")
            sys.stdout.flush()
            chunks_since_checkpoint = 0

    # Final flush + checkpoint
    if batch_arrays:
        batch_mat = flush_batch_to_csr(batch_arrays)
        if batch_mat is not None:
            if running_mat is None:
                running_mat = batch_mat
            else:
                running_mat = running_mat + batch_mat
            del batch_mat
        del batch_arrays
        gc.collect()

    if running_mat is not None:
        ckpt_id = len(checkpoint_files)
        ckpt_path = os.path.join(checkpoint_dir, f"ckpt_{ckpt_id:03d}.npz")
        save_npz(ckpt_path, running_mat)
        checkpoint_files.append(ckpt_path)
        del running_mat
        gc.collect()
        print(f"  >> CHECKPOINT {ckpt_id} saved → {ckpt_path}")

    scan_time = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"SCAN COMPLETE — {scan_time:.0f}s ({scan_time/60:.1f} min)")
    print(f"Checkpoints: {len(checkpoint_files)}")
    print(f"{'=' * 60}")

    # === MERGE CHECKPOINTS ===
    print(f"\nMerging {len(checkpoint_files)} checkpoints...")

    if len(checkpoint_files) == 0:
        print("ERROR: No checkpoint files!")
        sys.exit(1)

    # Load all checkpoints as COO, concatenate, build final CSR
    # Memory-safe: load one at a time, append to lists, free each
    all_rows = []
    all_cols = []
    all_vals = []
    total_coo_entries = 0

    for ckpt_path in checkpoint_files:
        mat = load_npz(ckpt_path).tocoo()
        all_rows.append(mat.row)
        all_cols.append(mat.col)
        all_vals.append(mat.data)
        total_coo_entries += len(mat.data)
        print(f"  Loaded {ckpt_path}: {mat.nnz:,} nnz")
        del mat
        gc.collect()

    print(f"  Total COO entries before dedup: {total_coo_entries:,}")
    print(f"  Concatenating...")

    combined_r = np.concatenate(all_rows)
    del all_rows; gc.collect()
    combined_c = np.concatenate(all_cols)
    del all_cols; gc.collect()
    combined_v = np.concatenate(all_vals)
    del all_vals; gc.collect()

    print(f"  Building final CSR...")
    final_mat = coo_matrix(
        (combined_v, (combined_r, combined_c)),
        shape=(N_CONCEPTS, N_CONCEPTS)
    ).tocsr()
    del combined_r, combined_c, combined_v
    gc.collect()

    nnz = final_mat.nnz
    mem_mb = (final_mat.data.nbytes +
              final_mat.indices.nbytes +
              final_mat.indptr.nbytes) / 1e6
    print(f"  Final matrix: {nnz:,} nnz, {mem_mb:.0f} MB")

    # === SAVE ===
    print(f"\n{'=' * 60}")
    print(f"SAVING RESULTS")
    print(f"{'=' * 60}")

    npz_path = os.path.join(BASE, "snapshot_full.npz")
    save_npz(npz_path, final_mat)
    print(f"  Matrix: {npz_path}")
    print(f"    Non-zeros: {nnz:,}")
    print(f"    CSR memory: {mem_mb:.0f} MB")
    del final_mat
    gc.collect()

    n_active = int(np.sum(activity > 0))
    act_out = {
        "activity": activity.tolist(),
        "total_works": total_works,
        "n_active": n_active,
        "cutoff_year": "NONE (full scan)"
    }
    act_path = os.path.join(BASE, "activity_full.json")
    with open(act_path, 'w', encoding='utf-8') as f:
        json.dump(act_out, f)
    print(f"  Activity: {act_path}")
    print(f"    Active concepts: {n_active:,} / {N_CONCEPTS:,}")
    print(f"    Total works: {total_works:,}")

    total_time = time.time() - t0
    meta_out = {
        "cutoff_year": "NONE",
        "n_concepts": N_CONCEPTS,
        "n_chunks_scanned": n_chunks,
        "total_works": total_works,
        "n_active_concepts": n_active,
        "n_pairs_nonzero": nnz,
        "total_pairs_accumulated": total_pairs_global,
        "periods_total": periods_total,
        "batch_size": BATCH_SIZE,
        "checkpoint_every": CHECKPOINT_EVERY,
        "n_checkpoints": len(checkpoint_files),
        "scan_time_sec": round(scan_time, 1),
        "total_time_sec": round(total_time, 1),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    meta_path = os.path.join(BASE, "meta_full.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta_out, f, indent=2)

    # Cleanup checkpoints
    for ckpt_path in checkpoint_files:
        os.remove(ckpt_path)
    os.rmdir(checkpoint_dir)
    print(f"  Checkpoints cleaned up")

    print(f"\n{'=' * 60}")
    print(f"STEP 1 DONE — {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"  Periods: {periods_total:,}")
    print(f"  Total works: {total_works:,}")
    print(f"  Active concepts: {n_active:,}")
    print(f"  Non-zero pairs: {nnz:,}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
