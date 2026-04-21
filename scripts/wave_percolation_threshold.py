#!/usr/bin/env python3
"""
YGGDRASIL — Session 38: Percolation Threshold test
====================================================
3 estimateurs du seuil de percolation local autour de chaque seed.
Corrèle avec K et r. Test temporel honnête.

Ref: Radicchi (2015) Phys. Rev. E 91, 010801(R).
  p̃_c = ⟨k⟩ / (⟨k²⟩ - ⟨k⟩)     (moments)
  p̄_c = 1/λ_max(A)               (adjacency eigenvalue)
  p̂_c = 1/λ_max(M)               (non-backtracking matrix)

Sky × Claude (Opus 4.6) — Session 38, 21 avril 2026
"""
import json, sys, os, time
import numpy as np
import sqlite3
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')
def P(*args, **kw): print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")

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
P(f"PERCOLATION THRESHOLD — {N_METS} météorites ({len(train_idx)} train, {len(test_idx)} test)")
P("=" * 80)

# ═══════════════════════════════════════════════════════
# COMPUTE PERCOLATION FEATURES FOR EACH METEORITE
# ════════════════════════════════════════════════���══════

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

def build_local_subgraph(seeds, cur, top_n=200):
    """Build local subgraph: seeds + top_n neighbors per seed."""
    edges = {}
    all_nodes = set(seeds)
    for seed in seeds:
        cur.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a = ? ORDER BY weight DESC LIMIT ?", (seed, top_n))
        for b, w in cur.fetchall():
            a_min, b_max = min(seed, b), max(seed, b)
            edges[(a_min, b_max)] = max(edges.get((a_min, b_max), 0), w)
            all_nodes.add(b)
        cur.execute("SELECT concept_a, weight FROM cooc_global WHERE concept_b = ? ORDER BY weight DESC LIMIT ?", (seed, top_n))
        for a, w in cur.fetchall():
            a_min, b_max = min(a, seed), max(a, seed)
            edges[(a_min, b_max)] = max(edges.get((a_min, b_max), 0), w)
            all_nodes.add(a)
    return edges, sorted(all_nodes)


def compute_percolation_features(edges, node_list):
    """
    Compute 3 percolation threshold estimators on the local subgraph.
    Returns dict with: pc_moments, pc_adjacency, pc_nonbacktracking, plus local stats.
    """
    N = len(node_list)
    node_idx = {n: i for i, n in enumerate(node_list)}

    # Build adjacency matrix (unweighted for percolation)
    rows, cols = [], []
    for (a, b) in edges:
        if a in node_idx and b in node_idx:
            i, j = node_idx[a], node_idx[b]
            rows.extend([i, j])
            cols.extend([j, i])

    data = np.ones(len(rows))
    A = csr_matrix((data, (rows, cols)), shape=(N, N))

    # Degree sequence
    degrees = np.array(A.sum(axis=1)).flatten()
    k_mean = float(np.mean(degrees))
    k2_mean = float(np.mean(degrees**2))

    result = {
        'N': N,
        'E': len(edges),
        'k_mean': k_mean,
        'k2_mean': k2_mean,
    }

    # Method A: Moments
    denom = k2_mean - k_mean
    if denom > 0:
        result['pc_moments'] = k_mean / denom
    else:
        result['pc_moments'] = 1.0  # degenerate

    # Method B: Adjacency eigenvalue
    try:
        if N > 3:
            lambda_max = eigsh(A.astype(float), k=1, which='LM', return_eigenvectors=False)[0]
            result['pc_adjacency'] = 1.0 / lambda_max if lambda_max > 0 else 1.0
            result['lambda_max'] = float(lambda_max)
        else:
            result['pc_adjacency'] = 1.0
            result['lambda_max'] = 0.0
    except Exception as e:
        result['pc_adjacency'] = 1.0
        result['lambda_max'] = 0.0

    # Method C: Non-backtracking matrix (simplified)
    # The full 2|E|x2|E| matrix is too big. Use the Hashimoto matrix via
    # det(λ²I - λA + D - I) = 0, where the largest eigenvalue of M
    # equals largest root of this. For simplicity, use the approximation:
    # λ_NB ≈ sqrt(λ_max(A)² - k_mean + 1) when network is tree-like
    try:
        lm = result['lambda_max']
        if lm > 0 and lm**2 > k_mean - 1:
            lambda_nb = np.sqrt(lm**2 - k_mean + 1)
            result['pc_nonbacktracking'] = 1.0 / lambda_nb if lambda_nb > 0 else 1.0
        else:
            result['pc_nonbacktracking'] = result['pc_adjacency']
    except:
        result['pc_nonbacktracking'] = result['pc_adjacency']

    # Derived: heterogeneity index κ = ⟨k²⟩/⟨k⟩
    result['kappa'] = k2_mean / k_mean if k_mean > 0 else 0

    return result


P("\nCalcul des seuils de percolation locaux...")

results = {}
for mi, met in enumerate(all_mets):
    name = met['name']
    seeds = met['seeds']
    t0 = time.time()

    edges, node_list = build_local_subgraph(seeds, cur, top_n=200)
    res = compute_percolation_features(edges, node_list)
    results[name] = res

    dt = time.time() - t0
    P(f"  [{mi+1:2d}/{N_METS}] {name:25s}  N={res['N']:>5d}  pc_mom={res['pc_moments']:.4f}  "
      f"pc_adj={res['pc_adjacency']:.4f}  pc_nb={res['pc_nonbacktracking']:.4f}  "
      f"κ={res['kappa']:.1f}  ({dt:.1f}s)")

db.close()

# ═══════════════════════════════════════════════════════
# CORRELATIONS
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CORRELATIONS SPEARMAN (n=36)")
P(f"{'='*80}\n")

K_all = np.array([m['K'] for m in all_mets])
r_all = np.array([m['r'] for m in all_mets])

features = ['pc_moments', 'pc_adjacency', 'pc_nonbacktracking', 'kappa', 'k_mean', 'k2_mean', 'lambda_max']

P(f"  {'Feature':25s} {'ρ(K)':>8s} {'p(K)':>10s} {'ρ(r)':>8s} {'p(r)':>10s}")
P(f"  {'-'*25} {'-'*8} {'-'*10} {'-'*8} {'-'*10}")

best_k_feat, best_k_rho = None, 0
best_r_feat, best_r_rho = None, 0

for feat in features:
    vals = np.array([results[m['name']][feat] for m in all_mets])
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

X = np.zeros((N_METS, len(features)))
for i, met in enumerate(all_mets):
    for j, feat in enumerate(features):
        X[i, j] = results[met['name']].get(feat, 0)

X_train, X_test = X[train_idx], X[test_idx]
K_train, K_test = K_all[train_idx], K_all[test_idx]
r_train, r_test = r_all[train_idx], r_all[test_idx]

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# K
ridge_k = Ridge(alpha=1.0)
ridge_k.fit(X_train_s, K_train)
K_pred = ridge_k.predict(X_test_s)
K_errors = np.abs(K_pred - K_test) / K_test * 100
K_med_err = float(np.median(K_errors))

P(f"  K prediction (Ridge, percolation features):")
P(f"    Median error: {K_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={K_test[idx]:>8,.0f}  pred={K_pred[idx]:>8,.0f}  err={K_errors[idx]:.0f}%")

# r
ridge_r = Ridge(alpha=1.0)
ridge_r.fit(X_train_s, r_train)
r_pred = ridge_r.predict(X_test_s)
r_errors = np.abs(r_pred - r_test) / r_test * 100
r_med_err = float(np.median(r_errors))

P(f"\n  r prediction (Ridge, percolation features):")
P(f"    Median error: {r_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={r_test[idx]:>6.3f}  pred={r_pred[idx]:>6.3f}  err={r_errors[idx]:.0f}%")

# ═══════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("VERDICT PERCOLATION")
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
    'method': 'percolation_threshold',
    'date': '2026-04-21',
    'session': 38,
    'n_meteorites': N_METS,
    'references': ['Radicchi (2015) Phys. Rev. E 91, 010801(R)'],
    'test_temporel': {
        'K_median_error': K_med_err, 'r_median_error': r_med_err,
        'K_verdict': k_verdict, 'r_verdict': r_verdict,
    },
    'correlations': {},
    'per_meteorite': results,
}
for feat in features:
    vals = [results[m['name']].get(feat, 0) for m in all_mets]
    if np.std(vals) > 0:
        rho_k, p_k = spearmanr(vals, K_all)
        rho_r, p_r = spearmanr(vals, r_all)
        output['correlations'][feat] = {'rho_K': float(rho_k), 'p_K': float(p_k), 'rho_r': float(rho_r), 'p_r': float(p_r)}

out_path = os.path.join(REPO, "data/results/wave_percolation_threshold.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
P(f"\n  Saved: {out_path}")
P("DONE.")
