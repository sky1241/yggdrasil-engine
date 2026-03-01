#!/usr/bin/env python3
"""
Predictions 2025 — Step 1b: Merge Checkpoints
==============================================
Merges 8 checkpoint .npz files using pairwise merge (divide & conquer).
Also re-scans activity/meta from all 581 chunks (fast, ~2 min).

Peak memory: ~2 GB (loading 2 checkpoints at a time).
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


def merge_two(path_a, path_b, out_path):
    """Merge two sparse .npz files into one, summing duplicates."""
    print(f"  Merging {os.path.basename(path_a)} + {os.path.basename(path_b)}...")
    sys.stdout.flush()

    mat_a = load_npz(path_a).tocoo()
    r_a, c_a, d_a = mat_a.row.copy(), mat_a.col.copy(), mat_a.data.copy()
    nnz_a = mat_a.nnz
    del mat_a
    gc.collect()

    mat_b = load_npz(path_b).tocoo()
    r_b, c_b, d_b = mat_b.row.copy(), mat_b.col.copy(), mat_b.data.copy()
    nnz_b = mat_b.nnz
    del mat_b
    gc.collect()

    combined_r = np.concatenate([r_a, r_b])
    del r_a, r_b; gc.collect()
    combined_c = np.concatenate([c_a, c_b])
    del c_a, c_b; gc.collect()
    combined_d = np.concatenate([d_a, d_b])
    del d_a, d_b; gc.collect()

    merged = coo_matrix(
        (combined_d, (combined_r, combined_c)),
        shape=(N_CONCEPTS, N_CONCEPTS)
    ).tocsr()
    del combined_r, combined_c, combined_d
    gc.collect()

    save_npz(out_path, merged)
    print(f"    {nnz_a:,} + {nnz_b:,} → {merged.nnz:,} nnz")
    sys.stdout.flush()
    del merged
    gc.collect()
    return out_path


def main():
    t0 = time.time()
    checkpoint_dir = os.path.join(BASE, "_checkpoints")

    # === 1. Re-scan activity/meta (fast) ===
    print("=== Re-scanning activity/meta from all chunks ===")
    sys.stdout.flush()

    activity = np.zeros(N_CONCEPTS, dtype=np.float64)
    total_works = 0
    periods_total = 0

    chunk_dirs = sorted([
        d for d in os.listdir(CHUNKS_DIR)
        if os.path.isdir(os.path.join(CHUNKS_DIR, d)) and d.startswith("chunk_")
    ])
    n_chunks = len(chunk_dirs)

    for ci, chunk_name in enumerate(chunk_dirs):
        chunk_dir = os.path.join(CHUNKS_DIR, chunk_name)

        meta_path = os.path.join(chunk_dir, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            for period, count in meta.get("period_papers", {}).items():
                total_works += count

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

        if (ci + 1) % 100 == 0 or ci + 1 == n_chunks:
            print(f"  [{ci+1}/{n_chunks}] activity scanned")
            sys.stdout.flush()

    act_time = time.time() - t0
    n_active = int(np.sum(activity > 0))
    print(f"  Activity scan: {act_time:.0f}s")
    print(f"  Active concepts: {n_active:,} | Total works: {total_works:,}")
    print(f"  Periods: {periods_total:,}")
    sys.stdout.flush()

    # === 2. Pairwise merge of checkpoints ===
    print(f"\n=== Merging checkpoints (pairwise) ===")
    sys.stdout.flush()

    current_files = sorted([
        os.path.join(checkpoint_dir, f)
        for f in os.listdir(checkpoint_dir)
        if f.startswith("ckpt_") and f.endswith(".npz")
    ])
    print(f"  Found {len(current_files)} checkpoints")

    round_num = 0
    while len(current_files) > 1:
        round_num += 1
        print(f"\n  Round {round_num}: {len(current_files)} files → {(len(current_files)+1)//2}")
        sys.stdout.flush()

        next_files = []
        for i in range(0, len(current_files), 2):
            if i + 1 < len(current_files):
                out_name = f"merged_r{round_num}_{i//2:03d}.npz"
                out_path = os.path.join(checkpoint_dir, out_name)
                merge_two(current_files[i], current_files[i+1], out_path)
                next_files.append(out_path)
            else:
                # Odd one out, carry forward
                next_files.append(current_files[i])
                print(f"  Carrying forward: {os.path.basename(current_files[i])}")

        current_files = next_files

    # === 3. Load final merged matrix ===
    print(f"\n=== Loading final matrix ===")
    sys.stdout.flush()

    final_mat = load_npz(current_files[0])
    nnz = final_mat.nnz
    mem_mb = (final_mat.data.nbytes +
              final_mat.indices.nbytes +
              final_mat.indptr.nbytes) / 1e6
    print(f"  Final matrix: {nnz:,} nnz, {mem_mb:.0f} MB")

    # === 4. Save outputs ===
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

    act_out = {
        "activity": activity.tolist(),
        "total_works": total_works,
        "n_active": n_active,
        "cutoff_year": "NONE (full scan)"
    }
    act_path_out = os.path.join(BASE, "activity_full.json")
    with open(act_path_out, 'w', encoding='utf-8') as f:
        json.dump(act_out, f)
    print(f"  Activity: {act_path_out}")
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
        "periods_total": periods_total,
        "total_time_sec": round(total_time, 1),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    meta_path_out = os.path.join(BASE, "meta_full.json")
    with open(meta_path_out, 'w', encoding='utf-8') as f:
        json.dump(meta_out, f, indent=2)

    # Cleanup ALL checkpoint and merged files
    for f in os.listdir(checkpoint_dir):
        os.remove(os.path.join(checkpoint_dir, f))
    os.rmdir(checkpoint_dir)
    print(f"  Checkpoints cleaned up")

    print(f"\n{'=' * 60}")
    print(f"STEP 1 MERGE DONE — {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"  Periods: {periods_total:,}")
    print(f"  Total works: {total_works:,}")
    print(f"  Active concepts: {n_active:,}")
    print(f"  Non-zero pairs: {nnz:,}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
