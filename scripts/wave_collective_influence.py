#!/usr/bin/env python3
"""
YGGDRASIL — Session 38: Collective Influence (CI) test
=======================================================
Calcule CI_L sur le sous-graphe local (top-N voisins) de chaque seed.
Corrèle avec K et r. Test temporel honnête.

IMPORTANT: le graphe complet a ⟨k⟩=2136 — BFS depth 3 = explosion combinatoire.
On travaille sur le sous-graphe local (top 300 neighbors), comme wave_retrain_s37.py.
CI_1 et CI_2 calculés sur ce sous-graphe.

Ref: Morone & Makse (2015) Nature 524, 65-68.
     CI_L(i) = (k_i - 1) * Σ_{j∈∂Ball(i,L)} (k_j - 1)

Sky × Claude (Opus 4.6) — Session 38, 21 avril 2026
"""
import json, sys, os, time
import numpy as np
import sqlite3
from collections import deque
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')
def P(*args, **kw): print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")
TOP_N = 300  # neighbors per seed (same as wave_retrain_s37.py)

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
P(f"COLLECTIVE INFLUENCE — {N_METS} météorites ({len(train_idx)} train, {len(test_idx)} test)")
P(f"Sous-graphe local: top {TOP_N} neighbors par seed")
P("=" * 80)

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

# ═══════════════════════════════════════════════════════
# BUILD LOCAL SUBGRAPH + COMPUTE CI
# ═══════════════════════════════════════════════════════

def build_local_subgraph(seeds, cur, top_n):
    """Build local subgraph: seeds + top_n neighbors per seed.
    Also fetch cross-connections within neighborhood."""
    edges = {}
    all_nodes = set(seeds)

    # 1-hop from seeds (top N by weight)
    for seed in seeds:
        cur.execute(
            "SELECT concept_b, weight FROM cooc_global WHERE concept_a = ? ORDER BY weight DESC LIMIT ?",
            (seed, top_n))
        for b, w in cur.fetchall():
            key = (min(seed, b), max(seed, b))
            edges[key] = max(edges.get(key, 0), w)
            all_nodes.add(b)

        cur.execute(
            "SELECT concept_a, weight FROM cooc_global WHERE concept_b = ? ORDER BY weight DESC LIMIT ?",
            (seed, top_n))
        for a, w in cur.fetchall():
            key = (min(a, seed), max(a, seed))
            edges[key] = max(edges.get(key, 0), w)
            all_nodes.add(a)

    # Cross-connections within neighborhood (makes CI more meaningful)
    node_list = sorted(all_nodes)
    node_set_str = ','.join(str(n) for n in node_list)
    for node in node_list:
        cur.execute(f"""
            SELECT concept_b, weight FROM cooc_global
            WHERE concept_a = ? AND concept_b IN ({node_set_str})
        """, (node,))
        for b, w in cur.fetchall():
            key = (min(node, b), max(node, b))
            edges[key] = max(edges.get(key, 0), w)

    # Build adjacency dict
    adj = {}
    for (a, b), w in edges.items():
        adj.setdefault(a, {})[b] = w
        adj.setdefault(b, {})[a] = w

    return adj, node_list


def compute_ci_local(seed, adj, L):
    """
    CI_L on local subgraph.
    CI_L(i) = (k_i - 1) * Σ_{j∈∂Ball(i,L)} (k_j - 1)
    """
    # BFS on local adj
    visited = {seed: 0}
    queue = deque([seed])
    boundary = []

    while queue:
        node = queue.popleft()
        dist = visited[node]
        if dist >= L:
            continue
        for nb in adj.get(node, {}):
            if nb not in visited:
                visited[nb] = dist + 1
                if dist + 1 == L:
                    boundary.append(nb)
                elif dist + 1 < L:
                    queue.append(nb)

    k_seed = len(adj.get(seed, {}))
    ci_sum = sum(max(0, len(adj.get(j, {})) - 1) for j in boundary)
    return max(0, k_seed - 1) * ci_sum, k_seed, len(boundary)


P("\nCalcul CI pour chaque météorite...\n")

results = {}
for mi, met in enumerate(all_mets):
    name = met['name']
    seeds = met['seeds']
    t0 = time.time()

    adj, node_list = build_local_subgraph(seeds, cur, TOP_N)
    N_local = len(node_list)
    E_local = sum(1 for n in adj for _ in adj[n]) // 2

    ci_1_vals, ci_2_vals = [], []
    degrees = []
    # Also: global degree from cooc_global (full graph)
    global_degrees = []

    for seed in seeds:
        ci1, k1, nb1 = compute_ci_local(seed, adj, L=1)
        ci2, k2, nb2 = compute_ci_local(seed, adj, L=2)
        ci_1_vals.append(ci1)
        ci_2_vals.append(ci2)
        degrees.append(k1)

        # Global degree (count from DB)
        cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a = ?", (seed,))
        gd = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_b = ?", (seed,))
        gd += cur.fetchone()[0]
        global_degrees.append(gd)

    # Also: total weight from seeds (strength)
    seed_strengths = []
    for seed in seeds:
        cur.execute("SELECT SUM(weight) FROM cooc_global WHERE concept_a = ?", (seed,))
        s = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(weight) FROM cooc_global WHERE concept_b = ?", (seed,))
        s += cur.fetchone()[0] or 0
        seed_strengths.append(s)

    res = {
        'N_local': N_local,
        'E_local': E_local,
        'local_degree_mean': float(np.mean(degrees)),
        'local_degree_max': float(np.max(degrees)),
        'global_degree_mean': float(np.mean(global_degrees)),
        'global_degree_max': float(np.max(global_degrees)),
        'strength_mean': float(np.mean(seed_strengths)),
        'strength_max': float(np.max(seed_strengths)),
        'CI_1_mean': float(np.mean(ci_1_vals)),
        'CI_1_max': float(np.max(ci_1_vals)),
        'CI_1_sum': float(np.sum(ci_1_vals)),
        'CI_2_mean': float(np.mean(ci_2_vals)),
        'CI_2_max': float(np.max(ci_2_vals)),
        'CI_2_sum': float(np.sum(ci_2_vals)),
        # CI normalized by local graph size
        'CI_1_norm': float(np.mean(ci_1_vals)) / (N_local * E_local) if E_local > 0 else 0,
        'CI_2_norm': float(np.mean(ci_2_vals)) / (N_local * E_local) if E_local > 0 else 0,
        'n_seeds': len(seeds),
    }
    results[name] = res

    dt = time.time() - t0
    P(f"  [{mi+1:2d}/{N_METS}] {name:25s}  N={N_local:>5d}  CI_1={res['CI_1_mean']:>10,.0f}  "
      f"CI_2={res['CI_2_mean']:>12,.0f}  gdeg={res['global_degree_mean']:>6,.0f}  ({dt:.1f}s)")

db.close()

# ═══════════════════════════════════════════════════════
# CORRELATIONS
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CORRELATIONS SPEARMAN (n=36)")
P(f"{'='*80}\n")

K_all = np.array([m['K'] for m in all_mets])
r_all = np.array([m['r'] for m in all_mets])

features = [
    'local_degree_mean', 'local_degree_max',
    'global_degree_mean', 'global_degree_max',
    'strength_mean', 'strength_max',
    'CI_1_mean', 'CI_1_max', 'CI_1_sum',
    'CI_2_mean', 'CI_2_max', 'CI_2_sum',
    'CI_1_norm', 'CI_2_norm',
    'N_local', 'E_local',
]

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
        X[i, j] = results[met['name']][feat]

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

P(f"  K prediction (Ridge, CI features):")
P(f"    Median error: {K_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={K_test[idx]:>8,.0f}  pred={K_pred[idx]:>8,.0f}  err={K_errors[idx]:.0f}%")

ridge_r = Ridge(alpha=1.0)
ridge_r.fit(X_train_s, r_train)
r_pred = ridge_r.predict(X_test_s)
r_errors = np.abs(r_pred - r_test) / r_test * 100
r_med_err = float(np.median(r_errors))

P(f"\n  r prediction (Ridge, CI features):")
P(f"    Median error: {r_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={r_test[idx]:>6.3f}  pred={r_pred[idx]:>6.3f}  err={r_errors[idx]:.0f}%")

# ═══════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("VERDICT CI")
P(f"{'='*80}")
P(f"  Best correlation K: {best_k_feat} ρ={best_k_rho:+.3f}")
P(f"  Best correlation r: {best_r_feat} ρ={best_r_rho:+.3f}")
P(f"  Test temporel K: {K_med_err:.1f}% (baseline session 37: 54%)")
P(f"  Test temporel r: {r_med_err:.1f}% (baseline session 37: 41%)")

k_verdict = "PASS" if K_med_err < 54 else "FAIL"
r_verdict = "PASS" if r_med_err < 41 else "FAIL"
P(f"  K: {k_verdict}")
P(f"  r: {r_verdict}")

# Save
output = {
    'method': 'collective_influence',
    'date': '2026-04-21',
    'session': 38,
    'n_meteorites': N_METS,
    'n_train': len(train_idx),
    'n_test': len(test_idx),
    'params': {'TOP_N': TOP_N, 'L_values': [1, 2]},
    'correlations': {},
    'test_temporel': {
        'K_median_error': K_med_err,
        'r_median_error': r_med_err,
        'K_verdict': k_verdict,
        'r_verdict': r_verdict,
    },
    'per_meteorite': results,
    'references': [
        'Morone & Makse (2015) Nature 524, 65-68',
        'Teng, Pei & Makse (2017) Sci. Rep. 7, 45240',
    ],
}
for feat in features:
    vals = [results[m['name']][feat] for m in all_mets]
    if np.std(vals) > 0:
        rho_k, p_k = spearmanr(vals, K_all)
        rho_r, p_r = spearmanr(vals, r_all)
        output['correlations'][feat] = {
            'rho_K': float(rho_k), 'p_K': float(p_k),
            'rho_r': float(rho_r), 'p_r': float(p_r),
        }

out_path = os.path.join(REPO, "data/results/wave_collective_influence.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
P(f"\n  Saved: {out_path}")
P("DONE.")
