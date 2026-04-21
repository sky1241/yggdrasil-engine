#!/usr/bin/env python3
"""
YGGDRASIL — Session 38: Heat Kernel sur S0 Laplacien
======================================================
Le Carmack move original (session 33): f(t) = exp(-t*L) * f(0)

Approche:
  1. Charger le graphe cooc_global (69M arêtes, 65K noeuds)
  2. Construire le Laplacien normalisé sparse
  3. Calculer les k plus petites eigenvalues/vectors (LOBPCG)
  4. Pour chaque météorite: f(0) = Dirac sur seeds
     f(t) = Σ_k exp(-t*λ_k) * <v_k, f(0)> * v_k
  5. Mesurer reach, spread, concentration à t=8 (durée de vie)
  6. Corréler avec K et r

ZÉRO PARAMÈTRE À FITTER — tout est dans la structure du graphe.

Sky × Claude (Opus 4.6) — Session 38, 21 avril 2026
"""
import json, sys, os, time
import numpy as np
import sqlite3
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import lobpcg
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')
def P(*args, **kw): print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")
K_EIGEN = 50  # number of smallest eigenvalues to compute

# ═══════════════════════════════════════════════════════
# LOAD 36 METEORITES
# ═══════════════════════════════════════════════════════

CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), encoding='utf-8'))
EXPAND = json.load(open(os.path.join(REPO, "data/results/wave_expand_checkpoint.json"), encoding='utf-8'))

all_mets = []
orig_bfs = CHECK['phase_1']
orig_log = CHECK['phase_3e']['fits']
for m in orig_bfs:
    year = int(m.split()[-1])
    all_mets.append({
        'name': m, 'year': year,
        'seeds': orig_bfs[m]['seeds'],
        'K': orig_log[m]['K'], 'r': orig_log[m]['r_growth'],
    })
for name, d in EXPAND.items():
    if d['phase_3']['K'] <= 100:
        continue
    all_mets.append({
        'name': name, 'year': d['phase_1']['open_year'],
        'seeds': d['phase_1']['seeds'],
        'K': d['phase_3']['K'], 'r': d['phase_3']['r_growth'],
    })

all_mets.sort(key=lambda x: x['year'])
N_METS = len(all_mets)
train_idx = [i for i, m in enumerate(all_mets) if m['year'] <= 1960]
test_idx  = [i for i, m in enumerate(all_mets) if m['year'] >= 1973]

P("=" * 80)
P(f"HEAT KERNEL — {N_METS} météorites ({len(train_idx)} train, {len(test_idx)} test)")
P(f"k={K_EIGEN} smallest eigenvalues, zéro paramètre")
P("=" * 80)

# ═══════════════════════════════════════════════════════
# PHASE 1: Build S0 Laplacian from cooc_global
# ═══════════════════════════════════════════════════════

P(f"\nPhase 1: Construction du Laplacien S0 depuis cooc_global...")
t0 = time.time()

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

# Get all concept IDs and build index
cur.execute("SELECT DISTINCT concept_a FROM cooc_global UNION SELECT DISTINCT concept_b FROM cooc_global")
all_concepts = sorted(set(r[0] for r in cur.fetchall()))
N = len(all_concepts)
concept_to_idx = {c: i for i, c in enumerate(all_concepts)}
idx_to_concept = {i: c for c, i in concept_to_idx.items()}

P(f"  {N} concepts, building sparse adjacency...")

# Stream edges
rows, cols, data = [], [], []
batch_size = 1000000
offset = 0

cur.execute("SELECT COUNT(*) FROM cooc_global")
total_edges = cur.fetchone()[0]
P(f"  {total_edges:,} edges to load...")

cur.execute("SELECT concept_a, concept_b, weight FROM cooc_global")
count = 0
while True:
    batch = cur.fetchmany(batch_size)
    if not batch:
        break
    for a, b, w in batch:
        if a in concept_to_idx and b in concept_to_idx:
            i, j = concept_to_idx[a], concept_to_idx[b]
            rows.append(i)
            cols.append(j)
            data.append(float(w))
            rows.append(j)
            cols.append(i)
            data.append(float(w))
    count += len(batch)
    if count % 5000000 == 0:
        P(f"    {count:,}/{total_edges:,} edges loaded...")

db.close()

P(f"  Building sparse matrix ({N}×{N}, {len(rows):,} entries)...")
A = csr_matrix((data, (rows, cols)), shape=(N, N))
del rows, cols, data

# Normalized Laplacian: L = I - D^{-1/2} A D^{-1/2}
P(f"  Computing normalized Laplacian...")
degree = np.array(A.sum(axis=1)).flatten()
# Avoid division by zero
degree_safe = np.maximum(degree, 1e-10)
d_inv_sqrt = 1.0 / np.sqrt(degree_safe)
D_inv_sqrt = diags(d_inv_sqrt)
L_norm = diags(np.ones(N)) - D_inv_sqrt @ A @ D_inv_sqrt

P(f"  Laplacian: {L_norm.shape}, nnz={L_norm.nnz:,}")
P(f"  Phase 1 done in {time.time()-t0:.1f}s")

# ═══════════════════════════════════════════════════════
# PHASE 2: Compute k smallest eigenvalues/vectors
# ═══════════════════════════════════════════════════════

P(f"\nPhase 2: LOBPCG for {K_EIGEN} smallest eigenvalues...")
t1 = time.time()

rng = np.random.RandomState(42)
X0 = rng.randn(N, K_EIGEN).astype(np.float64)

eigenvalues, eigenvectors = lobpcg(L_norm.astype(np.float64), X0, largest=False,
                                    maxiter=500, tol=1e-6, verbosityLevel=0)

# Sort by eigenvalue
order = np.argsort(eigenvalues)
eigenvalues = eigenvalues[order]
eigenvectors = eigenvectors[:, order]

P(f"  Eigenvalues[0:10]: {np.round(eigenvalues[:10], 6)}")
P(f"  Eigenvalues[40:50]: {np.round(eigenvalues[40:50], 6)}")
P(f"  Gap spectral (λ1): {eigenvalues[1]:.6f}")
P(f"  Phase 2 done in {time.time()-t1:.1f}s")

# Save eigenvalues for reference
np.save(os.path.join(REPO, "data/scan/s0_hk_eigenvalues.npy"), eigenvalues)
P(f"  Saved eigenvalues to data/scan/s0_hk_eigenvalues.npy")

# ═══════════════════════════════════════════════════════
# PHASE 3: Heat kernel for each meteorite
# ═══════════════════════════════════════════════════════

P(f"\nPhase 3: Heat kernel f(t) = exp(-t*L) * f(0) pour chaque météorite...")

T_VALUES = [1, 2, 4, 8, 12]  # time steps to evaluate

results = {}
for mi, met in enumerate(all_mets):
    name = met['name']
    seeds = met['seeds']
    t0_met = time.time()

    # f(0) = Dirac on seeds (normalized)
    f0 = np.zeros(N)
    n_valid_seeds = 0
    for seed in seeds:
        if seed in concept_to_idx:
            f0[concept_to_idx[seed]] = 1.0
            n_valid_seeds += 1

    if n_valid_seeds == 0:
        results[name] = {f: 0 for f in ['hk_reach_t8', 'hk_entropy_t8', 'hk_spread_t8',
                                          'hk_peak_t8', 'hk_reach_t1', 'hk_speed',
                                          'hk_concentration', 'hk_total_energy']}
        P(f"  [{mi+1:2d}/{N_METS}] {name:25s}  NO VALID SEEDS — skip")
        continue

    f0 /= n_valid_seeds  # normalize

    # Project f(0) onto eigenvectors: c_k = <v_k, f(0)>
    coeffs = eigenvectors.T @ f0  # (K_EIGEN,)

    # Compute f(t) for each t
    features = {}
    for t in T_VALUES:
        # f(t) = Σ_k exp(-t*λ_k) * c_k * v_k
        weights = np.exp(-t * eigenvalues) * coeffs  # (K_EIGEN,)
        f_t = eigenvectors @ weights  # (N,)

        # Normalize to probability distribution
        f_t_abs = np.abs(f_t)
        total = f_t_abs.sum()
        if total > 0:
            f_t_prob = f_t_abs / total
        else:
            f_t_prob = np.zeros(N)

        # Features at this time
        threshold = 1e-6  # minimum probability to count as "reached"
        reached = np.sum(f_t_prob > threshold)

        # Entropy (measure of spread)
        nonzero = f_t_prob[f_t_prob > 0]
        entropy = -np.sum(nonzero * np.log(nonzero)) if len(nonzero) > 0 else 0

        # Peak value (concentration)
        peak = float(np.max(f_t_prob))

        # Effective spread (number of nodes with >1% of max)
        spread = np.sum(f_t_prob > peak * 0.01) if peak > 0 else 0

        features[f'hk_reach_t{t}'] = int(reached)
        features[f'hk_entropy_t{t}'] = float(entropy)
        features[f'hk_spread_t{t}'] = int(spread)
        features[f'hk_peak_t{t}'] = float(peak)

    # Derived features
    features['hk_speed'] = features['hk_reach_t2'] / max(features['hk_reach_t8'], 1)
    features['hk_concentration'] = features['hk_peak_t8'] * N  # how concentrated at t=8
    features['hk_total_energy'] = float(np.sum(np.exp(-8 * eigenvalues) * coeffs**2))
    features['n_valid_seeds'] = n_valid_seeds

    results[name] = features
    dt = time.time() - t0_met

    P(f"  [{mi+1:2d}/{N_METS}] {name:25s}  reach@8={features['hk_reach_t8']:>6d}  "
      f"entropy@8={features['hk_entropy_t8']:.2f}  spread@8={features['hk_spread_t8']:>6d}  "
      f"speed={features['hk_speed']:.3f}  ({dt:.2f}s)")

# ═══════════════════════════════════════════════════════
# CORRELATIONS
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CORRELATIONS SPEARMAN (n=36)")
P(f"{'='*80}\n")

K_all = np.array([m['K'] for m in all_mets])
r_all = np.array([m['r'] for m in all_mets])

feature_names = [
    'hk_reach_t1', 'hk_reach_t2', 'hk_reach_t4', 'hk_reach_t8', 'hk_reach_t12',
    'hk_entropy_t1', 'hk_entropy_t2', 'hk_entropy_t4', 'hk_entropy_t8', 'hk_entropy_t12',
    'hk_spread_t1', 'hk_spread_t2', 'hk_spread_t4', 'hk_spread_t8', 'hk_spread_t12',
    'hk_peak_t1', 'hk_peak_t2', 'hk_peak_t4', 'hk_peak_t8', 'hk_peak_t12',
    'hk_speed', 'hk_concentration', 'hk_total_energy',
]

P(f"  {'Feature':25s} {'ρ(K)':>8s} {'p(K)':>10s} {'ρ(r)':>8s} {'p(r)':>10s}")
P(f"  {'-'*25} {'-'*8} {'-'*10} {'-'*8} {'-'*10}")

best_k_feat, best_k_rho = None, 0
best_r_feat, best_r_rho = None, 0

for feat in feature_names:
    vals = np.array([results[m['name']].get(feat, 0) for m in all_mets])
    if np.std(vals) == 0:
        continue
    rho_k, p_k = spearmanr(vals, K_all)
    rho_r, p_r = spearmanr(vals, r_all)
    P(f"  {feat:25s} {rho_k:+.4f}   {p_k:.2e}   {rho_r:+.4f}   {p_r:.2e}")
    if abs(rho_k) > abs(best_k_rho):
        best_k_rho, best_k_feat = rho_k, feat
    if abs(rho_r) > abs(best_r_rho):
        best_r_rho, best_r_feat = rho_r, feat

P(f"\n  Best for K: {best_k_feat} (ρ={best_k_rho:+.4f})")
P(f"  Best for r: {best_r_feat} (ρ={best_r_rho:+.4f})")

# ═══════════════════════════════════════════════════════
# TEST TEMPOREL
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("TEST TEMPOREL — train ≤1960, predict ≥1973")
P(f"{'='*80}\n")

# Use all heat kernel features
use_features = [f for f in feature_names if np.std([results[m['name']].get(f, 0) for m in all_mets]) > 0]
X = np.zeros((N_METS, len(use_features)))
for i, met in enumerate(all_mets):
    for j, feat in enumerate(use_features):
        X[i, j] = results[met['name']].get(feat, 0)

X_train, X_test = X[train_idx], X[test_idx]
K_train, K_test = K_all[train_idx], K_all[test_idx]
r_train, r_test = r_all[train_idx], r_all[test_idx]

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

ridge_k = Ridge(alpha=1.0)
ridge_k.fit(X_train_s, K_train)
K_pred = ridge_k.predict(X_test_s)
K_errors = np.abs(K_pred - K_test) / K_test * 100
K_med_err = float(np.median(K_errors))

P(f"  K prediction (Ridge, heat kernel features):")
P(f"    Median error: {K_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={K_test[idx]:>8,.0f}  pred={K_pred[idx]:>8,.0f}  err={K_errors[idx]:.0f}%")

ridge_r = Ridge(alpha=1.0)
ridge_r.fit(X_train_s, r_train)
r_pred = ridge_r.predict(X_test_s)
r_errors = np.abs(r_pred - r_test) / r_test * 100
r_med_err = float(np.median(r_errors))

P(f"\n  r prediction (Ridge, heat kernel features):")
P(f"    Median error: {r_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={r_test[idx]:>6.3f}  pred={r_pred[idx]:>6.3f}  err={r_errors[idx]:.0f}%")

# ═══════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("VERDICT HEAT KERNEL")
P(f"{'='*80}")
k_verdict = "PASS" if K_med_err < 54 else "FAIL"
r_verdict = "PASS" if r_med_err < 41 else "FAIL"
P(f"  Best correlation K: {best_k_feat} ρ={best_k_rho:+.3f}")
P(f"  Best correlation r: {best_r_feat} ρ={best_r_rho:+.3f}")
P(f"  Test temporel K: {K_med_err:.1f}% (baseline: 54%)")
P(f"  Test temporel r: {r_med_err:.1f}% (baseline: 41%)")
P(f"  K: {k_verdict}")
P(f"  r: {r_verdict}")

# Save
output = {
    'method': 'heat_kernel_s0',
    'date': '2026-04-21',
    'session': 38,
    'n_meteorites': N_METS,
    'n_concepts': N,
    'k_eigen': K_EIGEN,
    'eigenvalues': eigenvalues.tolist(),
    'params': 'ZERO — pure graph structure',
    'references': [
        'Chung (1997) Spectral Graph Theory',
        'Session 33 Carmack move: f(t) = exp(-tL) × f(0)',
    ],
    'test_temporel': {
        'K_median_error': K_med_err, 'r_median_error': r_med_err,
        'K_verdict': k_verdict, 'r_verdict': r_verdict,
    },
    'correlations': {},
    'per_meteorite': results,
}
for feat in feature_names:
    vals = [results[m['name']].get(feat, 0) for m in all_mets]
    if np.std(vals) > 0:
        rho_k, p_k = spearmanr(vals, K_all)
        rho_r, p_r = spearmanr(vals, r_all)
        output['correlations'][feat] = {'rho_K': float(rho_k), 'p_K': float(p_k), 'rho_r': float(rho_r), 'p_r': float(p_r)}

out_path = os.path.join(REPO, "data/results/wave_heat_kernel.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
P(f"\n  Saved: {out_path}")
P("DONE.")
