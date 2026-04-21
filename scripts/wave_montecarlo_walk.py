#!/usr/bin/env python3
"""
YGGDRASIL — Session 38: Monte Carlo Random Walk test (v2 — fast)
=================================================================
Pre-load voisins en mémoire, puis random walks sans SQL.
500 walks × 8 steps par seed sur cooc_global.

Strategy: pour chaque météorite, pre-load le "neighborhood cloud" —
tous les noeuds atteignables en 2-3 hops depuis les seeds (top N par poids).
Walks restent dans ce cloud (si un walker sort, il s'arrête).

Ref: Kempe, Kleinberg & Tardos (2003) KDD, 137-146.

Sky × Claude (Opus 4.6) — Session 38, 21 avril 2026
"""
import json, sys, os, time, random
import numpy as np
import sqlite3
from collections import Counter
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')
def P(*args, **kw): print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")
SPECTRAL = json.load(open(os.path.join(REPO, "data/scan/spectral_births.json"), encoding='utf-8'))

node_species = {}
for n in SPECTRAL['nodes']:
    node_species[n['id']] = n.get('cluster', -1)

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
P(f"MONTE CARLO RANDOM WALK v2 — {N_METS} météorites ({len(train_idx)} train, {len(test_idx)} test)")
P("=" * 80)

# ═══════════════════════════════════════════════════════
# PARAMS
# ═══════════════════════════════════════════════════════

N_WALKS = 500
T_STEPS = 8
TOP_NEIGHBORS = 500  # per node in the cloud
random.seed(42)
np.random.seed(42)

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

def load_neighborhood_cloud(seeds, cur, top_n=500):
    """
    Pre-load a neighborhood cloud in memory.
    Step 1: Load top_n neighbors of each seed.
    Step 2: Load top_n neighbors of THOSE neighbors (2-hop cloud).
    Returns: dict node -> [(neighbor, weight), ...] with cumulative weights for fast sampling.
    """
    cloud = {}  # node -> [(neighbor, cum_weight), ...]
    all_nodes = set(seeds)

    # Step 1: seeds -> 1-hop
    hop1_nodes = set()
    for seed in seeds:
        cur.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a = ? ORDER BY weight DESC LIMIT ?", (seed, top_n))
        nb_a = cur.fetchall()
        cur.execute("SELECT concept_a, weight FROM cooc_global WHERE concept_b = ? ORDER BY weight DESC LIMIT ?", (seed, top_n))
        nb_b = cur.fetchall()

        # Merge
        merged = {}
        for n, w in nb_a + nb_b:
            merged[n] = max(merged.get(n, 0), w)

        neighbors = sorted(merged.items(), key=lambda x: -x[1])[:top_n]
        # Build cumulative weights for fast sampling
        cum = []
        total = 0
        for n, w in neighbors:
            total += w
            cum.append((n, total))
            hop1_nodes.add(n)

        cloud[seed] = (cum, total)
        all_nodes.update(n for n, _ in neighbors)

    # Step 2: 1-hop nodes -> 2-hop (only for nodes in hop1)
    for node in hop1_nodes:
        if node in cloud:
            continue
        cur.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a = ? ORDER BY weight DESC LIMIT ?", (node, top_n))
        nb_a = cur.fetchall()
        cur.execute("SELECT concept_a, weight FROM cooc_global WHERE concept_b = ? ORDER BY weight DESC LIMIT ?", (node, top_n))
        nb_b = cur.fetchall()

        merged = {}
        for n, w in nb_a + nb_b:
            merged[n] = max(merged.get(n, 0), w)

        neighbors = sorted(merged.items(), key=lambda x: -x[1])[:top_n]
        cum = []
        total = 0
        for n, w in neighbors:
            total += w
            cum.append((n, total))

        cloud[node] = (cum, total)
        all_nodes.update(n for n, _ in neighbors)

    return cloud, all_nodes


def weighted_random_choice(cum_weights, total):
    """Fast weighted random choice using cumulative weights."""
    r = random.random() * total
    # Binary search
    lo, hi = 0, len(cum_weights) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if cum_weights[mid][1] < r:
            lo = mid + 1
        else:
            hi = mid
    return cum_weights[lo][0]


def run_walks(seeds, cloud, n_walks, t_steps):
    """Run random walks in memory (no SQL)."""
    all_visited = set()
    visited_per_step = [set() for _ in range(t_steps + 1)]
    species_counter = Counter()
    stopped_early = 0
    total_walks = 0

    for seed in seeds:
        for _ in range(n_walks):
            total_walks += 1
            current = seed
            visited_per_step[0].add(current)
            all_visited.add(current)

            for step in range(1, t_steps + 1):
                if current not in cloud:
                    stopped_early += 1
                    break

                cum, total = cloud[current]
                if not cum or total <= 0:
                    stopped_early += 1
                    break

                current = weighted_random_choice(cum, total)
                visited_per_step[step].add(current)
                all_visited.add(current)

                sp = node_species.get(current, -1)
                if sp >= 0:
                    species_counter[sp] += 1

    return all_visited, visited_per_step, species_counter, stopped_early, total_walks


P(f"\nSimulation: {N_WALKS} walks × {T_STEPS} steps par seed")
P(f"Cloud: top {TOP_NEIGHBORS} neighbors, 2-hop\n")

results = {}
for mi, met in enumerate(all_mets):
    name = met['name']
    seeds = met['seeds']
    t0 = time.time()

    # Pre-load cloud
    cloud, cloud_nodes = load_neighborhood_cloud(seeds, cur, TOP_NEIGHBORS)
    t_cloud = time.time() - t0

    # Run walks
    all_visited, vps, species_counter, stopped, total_walks = run_walks(seeds, cloud, N_WALKS, T_STEPS)
    t_walk = time.time() - t0 - t_cloud

    reach = len(all_visited)
    n_species = len(species_counter)
    stop_rate = stopped / total_walks if total_walks > 0 else 0

    reach_by_step = [len(vps[s]) for s in range(T_STEPS + 1)]
    early_reach = sum(reach_by_step[1:4])
    late_reach = sum(reach_by_step[4:])
    speed_ratio = early_reach / late_reach if late_reach > 0 else 1.0

    # Species Gini
    sp_counts = sorted(species_counter.values(), reverse=True)
    if len(sp_counts) > 1:
        n_sp = len(sp_counts)
        total_sp = sum(sp_counts)
        gini = sum((2*i - n_sp - 1) * sp_counts[i] for i in range(n_sp)) / (n_sp * total_sp) if total_sp > 0 else 0
    else:
        gini = 0

    # Seed reach variance
    seed_reaches = []
    for seed in seeds:
        sv = set()
        for _ in range(100):  # quick 100-walk per seed
            cur_node = seed
            for step in range(T_STEPS):
                if cur_node not in cloud:
                    break
                cum, total = cloud[cur_node]
                if not cum:
                    break
                cur_node = weighted_random_choice(cum, total)
                sv.add(cur_node)
        seed_reaches.append(len(sv))

    reach_cv = float(np.std(seed_reaches) / np.mean(seed_reaches)) if len(seed_reaches) > 1 and np.mean(seed_reaches) > 0 else 0

    res = {
        'reach': reach,
        'cloud_size': len(cloud_nodes),
        'reach_per_walk': reach / total_walks if total_walks > 0 else 0,
        'n_species_touched': n_species,
        'stop_rate': stop_rate,
        'speed_ratio': speed_ratio,
        'early_reach': early_reach,
        'late_reach': late_reach,
        'species_gini': gini,
        'reach_cv': reach_cv,
        'reach_by_step': reach_by_step,
        'mean_seed_reach': float(np.mean(seed_reaches)),
        'n_seeds': len(seeds),
    }
    results[name] = res

    dt = time.time() - t0
    P(f"  [{mi+1:2d}/{N_METS}] {name:25s}  reach={reach:>6d}  cloud={len(cloud_nodes):>6d}  "
      f"species={n_species}  speed={speed_ratio:.2f}  stop={stop_rate:.2f}  "
      f"(cloud {t_cloud:.1f}s + walk {t_walk:.1f}s)")

db.close()

# ═══════════════════════════════════════════════════════
# CORRELATIONS
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CORRELATIONS SPEARMAN (n=36)")
P(f"{'='*80}\n")

K_all = np.array([m['K'] for m in all_mets])
r_all = np.array([m['r'] for m in all_mets])

features = ['reach', 'cloud_size', 'reach_per_walk', 'n_species_touched', 'stop_rate',
            'speed_ratio', 'early_reach', 'late_reach', 'species_gini',
            'reach_cv', 'mean_seed_reach']

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

P(f"  K prediction (Ridge, MC walk features):")
P(f"    Median error: {K_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={K_test[idx]:>8,.0f}  pred={K_pred[idx]:>8,.0f}  err={K_errors[idx]:.0f}%")

ridge_r = Ridge(alpha=1.0)
ridge_r.fit(X_train_s, r_train)
r_pred = ridge_r.predict(X_test_s)
r_errors = np.abs(r_pred - r_test) / r_test * 100
r_med_err = float(np.median(r_errors))

P(f"\n  r prediction (Ridge, MC walk features):")
P(f"    Median error: {r_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={r_test[idx]:>6.3f}  pred={r_pred[idx]:>6.3f}  err={r_errors[idx]:.0f}%")

# ═══════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("VERDICT MONTE CARLO")
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
for name in results:
    results[name]['reach_by_step'] = results[name]['reach_by_step']

output = {
    'method': 'montecarlo_random_walk',
    'date': '2026-04-21',
    'session': 38,
    'n_meteorites': N_METS,
    'params': {'N_WALKS': N_WALKS, 'T_STEPS': T_STEPS, 'TOP_NEIGHBORS': TOP_NEIGHBORS, 'seed': 42},
    'references': [
        'Kempe, Kleinberg & Tardos (2003) KDD, 137-146',
        'Leskovec et al. (2007) ACM TOIT 7(1), 5',
    ],
    'test_temporel': {
        'K_median_error': K_med_err, 'r_median_error': r_med_err,
        'K_verdict': k_verdict, 'r_verdict': r_verdict,
    },
    'correlations': {},
    'per_meteorite': results,
}
for feat in features:
    vals = [results[m['name']][feat] for m in all_mets]
    if np.std(vals) > 0:
        rho_k, p_k = spearmanr(vals, K_all)
        rho_r, p_r = spearmanr(vals, r_all)
        output['correlations'][feat] = {'rho_K': float(rho_k), 'p_K': float(p_k), 'rho_r': float(rho_r), 'p_r': float(p_r)}

out_path = os.path.join(REPO, "data/results/wave_montecarlo_walk.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
P(f"\n  Saved: {out_path}")
P("DONE.")
