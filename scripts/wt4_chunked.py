"""WT4 chunked rebuild: load COO chunks from disk, build sparse, eigsh, save spectral_births."""
import gc
import json
import math
import os
import time
from collections import defaultdict

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

CHUNKDIR = "d:/ygg/yggdrasil-engine/data/scan/_wt4_chunks"
ROOT = "d:/ygg/yggdrasil-engine"

t0 = time.time()

# ── Step 1: Load concept IDs ──
print("Loading concept IDs...", flush=True)
with open(f"{ROOT}/data/scan/concepts_65k.json", encoding="utf-8") as f:
    cdata = json.load(f)
all_concept_ids = sorted(
    info["idx"] for info in cdata["concepts"].values()
    if isinstance(info, dict) and "idx" in info
)
concept_names = {}
for url, info in cdata["concepts"].items():
    if isinstance(info, dict) and "idx" in info:
        concept_names[info["idx"]] = info.get("name", f"C{info['idx']}")
del cdata
gc.collect()

# Load bipartite chunk for glyph IDs
bip = np.load(f"{CHUNKDIR}/bip.npz")
glyph_ids = sorted(set(bip["r"].tolist()))
N_g = len(glyph_ids)
N_c = len(all_concept_ids)
N = N_g + N_c
print(f"  {N_g} glyphs + {N_c} concepts = {N} nodes", flush=True)

g2idx = {g: i for i, g in enumerate(glyph_ids)}
c2idx = {c: i + N_g for i, c in enumerate(all_concept_ids)}

# ── Step 2: Build bipartite sparse ──
print("Building bipartite sparse...", flush=True)
gi = np.array([g2idx[int(g)] for g in bip["r"]], dtype=np.int32)
ci = np.array([c2idx.get(int(c), -1) for c in bip["c"]], dtype=np.int32)
valid = ci >= 0
gi_v = gi[valid]
ci_v = ci[valid]
bw = np.log1p(bip["w"][valid].astype(np.float64))
bip_max = bw.max()
bw_norm = (bw / bip_max).astype(np.float32) if bip_max > 0 else bw.astype(np.float32)
del bip, gi, ci, valid, bw

rows_b = np.concatenate([gi_v, ci_v])
cols_b = np.concatenate([ci_v, gi_v])
vals_b = np.concatenate([bw_norm, bw_norm])
A = sparse.coo_matrix((vals_b, (rows_b, cols_b)), shape=(N, N)).tocsr()
del rows_b, cols_b, vals_b, gi_v, ci_v, bw_norm
gc.collect()
print(f"  Bipartite: nnz={A.nnz:,} ({time.time()-t0:.0f}s)", flush=True)

# ── Step 3: Get cooc max ──
cooc_max = 0
for fname in sorted(os.listdir(CHUNKDIR)):
    if not fname.startswith("cooc_"):
        continue
    chunk = np.load(f"{CHUNKDIR}/{fname}")
    cm = float(chunk["w"].max())
    if cm > cooc_max:
        cooc_max = cm
    del chunk
cooc_log_max = math.log1p(cooc_max)
print(f"  Cooc max: {cooc_max:.2f}, log1p: {cooc_log_max:.4f}", flush=True)

# ── Step 4: Add cooc chunks one by one ──
print("Adding cooc chunks...", flush=True)
concept_cooc_degree = defaultdict(float)
total_cooc = 0

for fname in sorted(os.listdir(CHUNKDIR)):
    if not fname.startswith("cooc_"):
        continue
    chunk = np.load(f"{CHUNKDIR}/{fname}")
    ca = chunk["r"]
    cb = chunk["c"]
    cw = chunk["w"]

    ci_a = np.array([c2idx.get(int(x), -1) for x in ca], dtype=np.int32)
    ci_b = np.array([c2idx.get(int(x), -1) for x in cb], dtype=np.int32)
    valid = (ci_a >= 0) & (ci_b >= 0)
    ci_a_v = ci_a[valid]
    ci_b_v = ci_b[valid]
    w_raw = cw[valid]

    # Track degrees (vectorized sum per concept)
    ca_valid = ca[valid]
    cb_valid = cb[valid]
    for i in range(len(w_raw)):
        concept_cooc_degree[int(ca_valid[i])] += float(w_raw[i])
        concept_cooc_degree[int(cb_valid[i])] += float(w_raw[i])

    w_norm = (np.log1p(w_raw.astype(np.float64)) / cooc_log_max).astype(np.float32)

    rows_c = np.concatenate([ci_a_v, ci_b_v])
    cols_c = np.concatenate([ci_b_v, ci_a_v])
    vals_c = np.concatenate([w_norm, w_norm])

    batch = sparse.coo_matrix((vals_c, (rows_c, cols_c)), shape=(N, N)).tocsr()
    A = A + batch

    total_cooc += int(valid.sum())
    del chunk, ca, cb, cw, ci_a, ci_b, valid, ci_a_v, ci_b_v
    del w_raw, w_norm, rows_c, cols_c, vals_c, batch, ca_valid, cb_valid
    gc.collect()
    print(f"  {fname}: total={total_cooc:,}, nnz={A.nnz:,} ({time.time()-t0:.0f}s)", flush=True)

print(f"  Final: {total_cooc:,} cooc edges, nnz={A.nnz:,}", flush=True)

# ── Step 5: Eigsh ──
print(f"Eigsh on {N:,}x{N:,}...", flush=True)
d = np.array(A.sum(axis=1)).flatten()
d_inv_sqrt = np.zeros(N)
mask = d > 0
d_inv_sqrt[mask] = 1.0 / np.sqrt(d[mask])
D_inv_sqrt = sparse.diags(d_inv_sqrt)
A_norm = D_inv_sqrt @ A @ D_inv_sqrt
A_norm = A_norm.tocsc()
del A, D_inv_sqrt, d_inv_sqrt
gc.collect()
print(f"  A_norm ready, nnz={A_norm.nnz:,} ({time.time()-t0:.0f}s)", flush=True)

eigenvalues, eigenvectors = eigsh(A_norm, k=20, which="LM")
order = np.argsort(-eigenvalues)
eigenvalues = eigenvalues[order]
eigenvectors = eigenvectors[:, order]
print(f"  Eigenvalues top 5: {np.round(eigenvalues[:5], 4).tolist()}", flush=True)
print(f"  Spectral gap: {eigenvalues[0]-eigenvalues[1]:.6f}", flush=True)
del A_norm
gc.collect()

# ── Step 6: Save spectral_births.json ──
print("Saving spectral_births.json...", flush=True)


def robust_norm(arr, scale=1.5, pct=98):
    arr = arr - np.median(arr)
    lo, hi = np.percentile(arr, 100 - pct), np.percentile(arr, pct)
    arr = np.clip(arr, lo, hi)
    mx = max(abs(arr.min()), abs(arr.max()))
    return arr / mx * scale if mx > 0 else arr


all_x = robust_norm(eigenvectors[:, 1].copy())
all_y = robust_norm(eigenvectors[:, 2].copy())
all_z = robust_norm(eigenvectors[:, 3].copy())

with open(f"{ROOT}/data/scan/concept_births.json", encoding="utf-8") as f:
    births = {int(k): v for k, v in json.load(f).items()}

with open(f"{ROOT}/data/core/glyph_registry.json", encoding="utf-8") as f:
    glyph_meta = json.load(f).get("glyphs", {})

nodes = []
for gid in glyph_ids:
    i = g2idx[gid]
    meta = glyph_meta.get(str(gid), {})
    nodes.append({
        "id": gid, "type": "glyph",
        "name": meta.get("symbol", "?"),
        "x": round(float(all_x[i]), 5),
        "y": round(float(all_y[i]), 5),
        "z": round(float(all_z[i]), 5),
        "degree": round(float(d[i]), 2),
    })

n_with_birth = 0
for cid in all_concept_ids:
    idx = c2idx[cid]
    birth = births.get(cid)
    if birth is not None:
        n_with_birth += 1
    nodes.append({
        "id": cid, "type": "concept",
        "name": concept_names.get(cid, f"C{cid}"),
        "x": round(float(all_x[idx]), 5),
        "y": round(float(all_y[idx]), 5),
        "z": round(float(all_z[idx]), 5),
        "degree": round(float(concept_cooc_degree.get(cid, 0)), 1),
        "birth_year": birth,
    })

sb = {
    "meta": {
        "description": "FULL Laplacian spectral positions + birth years for ALL 66K nodes",
        "n_glyphs": N_g, "n_concepts": N_c, "n_total": len(nodes),
        "n_with_birth": n_with_birth,
        "eigenvalues_top5": [round(float(v), 6) for v in eigenvalues[:5]],
        "spectral_gap": round(float(eigenvalues[0] - eigenvalues[1]), 6),
        "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": "full_laplacian_chunked",
        "usage": "V3 meteorites + Film V5",
    },
    "nodes": nodes,
}

outpath = f"{ROOT}/data/scan/spectral_births.json"
with open(outpath, "w", encoding="utf-8") as f:
    json.dump(sb, f, ensure_ascii=False)

sz = os.path.getsize(outpath) / (1024 * 1024)
total_time = time.time() - t0
print(f"\n=== DONE in {total_time:.0f}s ({total_time/60:.1f} min) ===", flush=True)
print(f"  {len(nodes)} nodes, {n_with_birth} with birth", flush=True)
print(f"  File: {sz:.1f} MB", flush=True)
