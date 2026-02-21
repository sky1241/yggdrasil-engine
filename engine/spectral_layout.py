"""
YGGDRASIL ENGINE — Spectral Layout v3
TF-IDF + KNN + Laplacien sparse

Construit un graphe KNN par TF-IDF cosine, puis calcule
les positions spectrales via le Laplacien du graphe.

Usage:
    python engine/spectral_layout.py
"""
import json
import time
import numpy as np
from pathlib import Path
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import kneighbors_graph
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import eigsh, lobpcg
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).parent.parent

# ============================================================
# CONFIG
# ============================================================
K_NEIGHBORS = 20
SCALE = 1.5
CLIP_PERCENTILE = 99

print("=" * 60)
print("YGGDRASIL -- SPECTRAL LAYOUT v3 -- sparse Laplacien")
print("=" * 60)
t0 = time.time()

# ============================================================
# STEP 1: Load data
# ============================================================
print("\n[1/6] Loading data...")
with open(ROOT / "data" / "strates_export_v2.json", encoding="utf-8") as f:
    strates = json.load(f)

s0 = strates["strates"][0]["symbols"]
originals = [(i, s) for i, s in enumerate(s0) if not s.get("mined")]
mined = [(i, s) for i, s in enumerate(s0) if s.get("mined")]
N_ORIG = len(originals)
N_MINED = len(mined)
print(f"  S0: {len(s0)} total, {N_ORIG} originaux, {N_MINED} mines")

with open(ROOT / "data" / "mined_concepts.json", encoding="utf-8") as f:
    concept_lookup = {c["concept_id"]: c for c in json.load(f)["concepts"]}

# ============================================================
# STEP 2: Build corpus
# ============================================================
print("\n[2/6] Building corpus...")
corpus = []
for idx, sym in mined:
    cid = sym.get("concept_id", "")
    concept = concept_lookup.get(cid, {})
    name = concept.get("name", sym.get("from", sym["s"]))
    desc = concept.get("description", "")
    domain = sym.get("domain", "")
    text = f"{name} {name} {name} {desc} {domain} {domain} {domain}"
    corpus.append(text)

N = len(corpus)
print(f"  {N} documents")

# ============================================================
# STEP 3: TF-IDF
# ============================================================
print("\n[3/6] TF-IDF...")
t1 = time.time()
vectorizer = TfidfVectorizer(
    max_features=15000, stop_words="english",
    min_df=2, max_df=0.7, ngram_range=(1, 2), sublinear_tf=True,
)
tfidf = vectorizer.fit_transform(corpus)
print(f"  {tfidf.shape}, nnz={tfidf.nnz}, {tfidf.nnz/N:.1f} feat/doc, {time.time()-t1:.1f}s")

# ============================================================
# STEP 4: KNN graph (sparse)
# ============================================================
print(f"\n[4/6] KNN graph K={K_NEIGHBORS}...")
t2 = time.time()

# Get KNN distances
knn = kneighbors_graph(tfidf, n_neighbors=K_NEIGHBORS, metric="cosine",
                       mode="distance", include_self=False, n_jobs=-1)

# Convert distance -> similarity
knn.data = np.maximum(1.0 - knn.data, 0)

# Symmetrize
A = knn.maximum(knn.T).tocsr()
n_edges = A.nnz // 2
print(f"  {n_edges} edges, avg_deg={A.nnz/N:.1f}, {time.time()-t2:.1f}s")

# Connectivity
n_comp, labels = connected_components(A, directed=False)
print(f"  {n_comp} composante(s)")
if n_comp > 1:
    sizes = np.bincount(labels)
    largest_id = np.argmax(sizes)
    print(f"  Largest: {sizes.max()} ({sizes.max()/N*100:.1f}%), isolated: {(sizes==1).sum()}")
    for c in range(n_comp):
        if c != largest_id:
            ns = np.where(labels == c)[0][0]
            nl = np.where(labels == largest_id)[0][0]
            A[ns, nl] = 0.001
            A[nl, ns] = 0.001
    A = A.tocsr()

# ============================================================
# STEP 5: Laplacien + eigsh (SPARSE, pas de toarray!)
# ============================================================
print(f"\n[5/6] Laplacien sparse + eigsh...")
t3 = time.time()

# Unnormalized Laplacian: L = D - A
degree = np.array(A.sum(axis=1)).flatten()
L = diags(degree) - A
L = L.tocsr()
print(f"  L: {L.shape}, nnz={L.nnz}")

# LOBPCG is faster than eigsh for finding smallest eigenvalues of large sparse
# Initialize with random vectors
rng = np.random.RandomState(42)
X0 = rng.randn(N, 4).astype(np.float64)

print(f"  LOBPCG for 4 smallest eigenvalues...")
eigenvalues, eigenvectors = lobpcg(L.astype(np.float64), X0, largest=False,
                                    maxiter=500, tol=1e-6, verbosityLevel=0)

# Sort by eigenvalue
order = np.argsort(eigenvalues)
eigenvalues = eigenvalues[order]
eigenvectors = eigenvectors[:, order]

print(f"  Eigenvalues: {eigenvalues}")
print(f"  Time: {time.time()-t3:.1f}s")

# Skip first eigenvector (constant, eigenvalue ~0)
# Use 2nd and 3rd as x,z coordinates
px_raw = eigenvectors[:, 1].copy()
pz_raw = eigenvectors[:, 2].copy()

print(f"  Raw px: min={px_raw.min():.6f} max={px_raw.max():.6f} std={px_raw.std():.6f}")
print(f"  Raw pz: min={pz_raw.min():.6f} max={pz_raw.max():.6f} std={pz_raw.std():.6f}")

# ============================================================
# Robust normalization
# ============================================================
def robust_normalize(arr, scale, clip_pct):
    arr = arr - np.median(arr)
    lo = np.percentile(arr, 100 - clip_pct)
    hi = np.percentile(arr, clip_pct)
    arr = np.clip(arr, lo, hi)
    mx = max(abs(arr.min()), abs(arr.max()))
    if mx > 0:
        arr = arr / mx * scale
    return arr

px = robust_normalize(px_raw, SCALE, CLIP_PERCENTILE)
pz = robust_normalize(pz_raw, SCALE, CLIP_PERCENTILE)

print(f"\n  Final px: [{px.min():.3f}, {px.max():.3f}] std={px.std():.3f}")
print(f"  Final pz: [{pz.min():.3f}, {pz.max():.3f}] std={pz.std():.3f}")
for name, arr in [("px", px), ("pz", pz)]:
    ps = [np.percentile(arr, p) for p in [5, 25, 50, 75, 95]]
    print(f"  {name}: P5={ps[0]:.3f} P25={ps[1]:.3f} P50={ps[2]:.3f} P75={ps[3]:.3f} P95={ps[4]:.3f}")

# ============================================================
# STEP 6: Save
# ============================================================
print(f"\n[6/6] Updating strates_export_v2.json...")

for local_i, (global_i, sym) in enumerate(mined):
    sym["px"] = round(float(px[local_i]), 4)
    sym["pz"] = round(float(pz[local_i]), 4)
    sym["spectral"] = True

output_path = ROOT / "data" / "strates_export_v2.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(strates, f, ensure_ascii=False, indent=1)

# Domain stats
print(f"\n  Positions par domaine (top 15):")
dp = defaultdict(lambda: {"px": [], "pz": []})
for li, (gi, sym) in enumerate(mined):
    d = sym.get("domain", "?")
    dp[d]["px"].append(px[li])
    dp[d]["pz"].append(pz[li])

for d, p in sorted(dp.items(), key=lambda x: -len(x[1]["px"]))[:15]:
    cx, cz = np.mean(p["px"]), np.mean(p["pz"])
    sx, sz = np.std(p["px"]), np.std(p["pz"])
    print(f"    {d:25s} n={len(p['px']):5d} center=({cx:+.3f},{cz:+.3f}) spread=({sx:.3f},{sz:.3f})")

tt = time.time() - t0
print(f"\n{'='*60}")
print(f"DONE in {tt:.0f}s ({tt/60:.1f} min)")
print(f"  {N_MINED} mines spectral, {N_ORIG} originaux inchanges")
print(f"  -> {output_path}")
print(f"{'='*60}")
