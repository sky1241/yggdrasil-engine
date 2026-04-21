#!/usr/bin/env python3
"""
YGGDRASIL — Session 38: K-shell decomposition test
====================================================
Calcule le k-shell index (coreness) de chaque seed sur cooc_global.
Corrèle avec K et r. Test temporel honnête.

Ref: Kitsak et al. (2010) Nature Physics 6, 888-893.
     Liu et al. (2015) Sci. Rep. 5, 13172.

Sky × Claude (Opus 4.6) — Session 38, 21 avril 2026
"""
import json, sys, os, time
import numpy as np
import sqlite3
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
P(f"K-SHELL DECOMPOSITION — {N_METS} météorites ({len(train_idx)} train, {len(test_idx)} test)")
P("=" * 80)

# ═══════════════════════════════════════════════════════
# BUILD LOCAL SUBGRAPH AND COMPUTE K-SHELL
# ═══════════════════════════════════════════════════════

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

def build_local_graph(seeds, cur, top_n=300):
    """
    Build local subgraph: seeds + top_n neighbors per seed.
    Also add cross-connections among those neighbors (2-hop closure).
    Returns adjacency dict: node -> set of neighbors.
    """
    all_nodes = set(seeds)
    adj = {}

    # 1-hop from seeds
    for seed in seeds:
        cur.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a = ? ORDER BY weight DESC LIMIT ?", (seed, top_n))
        neighbors_a = [(b, w) for b, w in cur.fetchall()]
        cur.execute("SELECT concept_a, weight FROM cooc_global WHERE concept_b = ? ORDER BY weight DESC LIMIT ?", (seed, top_n))
        neighbors_b = [(a, w) for a, w in cur.fetchall()]

        for n, w in neighbors_a + neighbors_b:
            all_nodes.add(n)
            adj.setdefault(seed, set()).add(n)
            adj.setdefault(n, set()).add(seed)

    # Cross-connections within the neighborhood (makes k-shell more meaningful)
    node_list = sorted(all_nodes)
    for node in node_list:
        if node in seeds:
            continue
        cur.execute("""
            SELECT concept_b FROM cooc_global
            WHERE concept_a = ? AND concept_b IN ({})
            """.format(','.join(str(n) for n in node_list)),
            (node,))
        for (b,) in cur.fetchall():
            adj.setdefault(node, set()).add(b)
            adj.setdefault(b, set()).add(node)

    return adj, node_list


def kshell_decomposition(adj):
    """
    Standard k-shell decomposition.
    Returns dict: node -> k-shell index (coreness).
    """
    # Copy degree
    degree = {n: len(adj.get(n, set())) for n in adj}
    remaining = set(adj.keys())
    shell = {}
    k = 1

    while remaining:
        # Find all nodes with degree <= k
        changed = True
        while changed:
            changed = False
            to_remove = set()
            for n in remaining:
                if degree[n] <= k:
                    to_remove.add(n)
            if to_remove:
                changed = True
                for n in to_remove:
                    shell[n] = k
                    remaining.remove(n)
                    # Reduce degree of neighbors
                    for nb in adj.get(n, set()):
                        if nb in remaining:
                            degree[nb] -= 1
        k += 1

    return shell


P("\nCalcul k-shell pour chaque météorite...")

results = {}
for mi, met in enumerate(all_mets):
    name = met['name']
    seeds = met['seeds']
    t0 = time.time()

    adj, node_list = build_local_graph(seeds, cur, top_n=300)
    shell = kshell_decomposition(adj)

    # Extract features for seeds
    seed_shells = [shell.get(s, 0) for s in seeds]
    all_shells = list(shell.values())

    # Also compute: where does the seed sit relative to the network?
    max_shell = max(all_shells) if all_shells else 1
    seed_degree = [len(adj.get(s, set())) for s in seeds]

    res = {
        'kshell_mean': float(np.mean(seed_shells)),
        'kshell_max': float(np.max(seed_shells)),
        'kshell_min': float(np.min(seed_shells)),
        'kshell_relative': float(np.mean(seed_shells)) / max_shell if max_shell > 0 else 0,
        'max_shell_network': float(max_shell),
        'degree_mean': float(np.mean(seed_degree)),
        'degree_max': float(np.max(seed_degree)),
        'N_subgraph': len(node_list),
        'n_seeds': len(seeds),
        # How many shells exist?
        'n_distinct_shells': len(set(all_shells)),
        # Fraction of nodes in the innermost shell
        'core_fraction': sum(1 for v in all_shells if v == max_shell) / len(all_shells) if all_shells else 0,
    }

    results[name] = res
    dt = time.time() - t0
    P(f"  [{mi+1:2d}/{N_METS}] {name:25s}  kshell={res['kshell_mean']:.1f}/{max_shell:.0f}  "
      f"relative={res['kshell_relative']:.3f}  degree={res['degree_mean']:.0f}  "
      f"N={res['N_subgraph']}  ({dt:.1f}s)")

db.close()

# ═══════════════════════════════════════════════════════
# CORRELATIONS
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CORRELATIONS SPEARMAN (n=36)")
P(f"{'='*80}\n")

K_all = np.array([m['K'] for m in all_mets])
r_all = np.array([m['r'] for m in all_mets])

features = ['kshell_mean', 'kshell_max', 'kshell_min', 'kshell_relative',
            'max_shell_network', 'degree_mean', 'degree_max',
            'n_distinct_shells', 'core_fraction']

P(f"  {'Feature':25s} {'ρ(K)':>8s} {'p(K)':>10s} {'ρ(r)':>8s} {'p(r)':>10s}")
P(f"  {'-'*25} {'-'*8} {'-'*10} {'-'*8} {'-'*10}")

best_k_feat, best_k_rho = None, 0
best_r_feat, best_r_rho = None, 0

for feat in features:
    vals = np.array([results[m['name']][feat] for m in all_mets])
    if np.std(vals) == 0:
        P(f"  {feat:25s}  CONSTANT — skip")
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

ridge_k = Ridge(alpha=1.0)
ridge_k.fit(X_train_s, K_train)
K_pred = ridge_k.predict(X_test_s)
K_errors = np.abs(K_pred - K_test) / K_test * 100
K_med_err = float(np.median(K_errors))

P(f"  K prediction (Ridge, k-shell features):")
P(f"    Median error: {K_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={K_test[idx]:>8,.0f}  pred={K_pred[idx]:>8,.0f}  err={K_errors[idx]:.0f}%")

ridge_r = Ridge(alpha=1.0)
ridge_r.fit(X_train_s, r_train)
r_pred = ridge_r.predict(X_test_s)
r_errors = np.abs(r_pred - r_test) / r_test * 100
r_med_err = float(np.median(r_errors))

P(f"\n  r prediction (Ridge, k-shell features):")
P(f"    Median error: {r_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={r_test[idx]:>6.3f}  pred={r_pred[idx]:>6.3f}  err={r_errors[idx]:.0f}%")

# ═══════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("VERDICT K-SHELL")
P(f"{'='*80}")
k_verdict = "PASS" if K_med_err < 54 else "FAIL"
r_verdict = "PASS" if r_med_err < 41 else "FAIL"
P(f"  Best correlation K: {best_k_feat} ρ={best_k_rho:+.3f}")
P(f"  Best correlation r: {best_r_feat} ρ={best_r_rho:+.3f}")
P(f"  Test temporel K: {K_med_err:.1f}% (baseline: 54%)")
P(f"  Test temporel r: {r_med_err:.1f}% (baseline: 41%)")
P(f"  K: {k_verdict}")
P(f"  r: {r_verdict}")

output = {
    'method': 'kshell_decomposition',
    'date': '2026-04-21',
    'session': 38,
    'n_meteorites': N_METS,
    'references': [
        'Kitsak et al. (2010) Nature Physics 6, 888-893',
        'Liu et al. (2015) Sci. Rep. 5, 13172',
    ],
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

out_path = os.path.join(REPO, "data/results/wave_kshell.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
P(f"\n  Saved: {out_path}")
P("DONE.")
