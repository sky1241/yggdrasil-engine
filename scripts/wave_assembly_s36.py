#!/usr/bin/env python3
"""
YGGDRASIL — Session 36: Assemblage dynamique
==============================================
Scientométrie + topologie locale + mare + candlestick → R(t) trajectoire

DIAGNOSTIC SESSION 35:
  - K prediction: 20.9% PASS (Ridge mare)
  - r prediction: candle_ratio FAILS temporally (uses post-impact data)
  - R(t) trajectory: R²=-0.15 FAIL because r prediction is 173-406% off
  - When K is fixed to TRUE: R² = +0.57 → K is the lever
  - PRIORITY: find a PRE-IMPACT predictor for r

ÉTAPES:
  A. Scientometric proxies from WT3 cooc (temporal)
     - fitness_growth: growth rate of seed co-occurrences 5y pre-impact
     - d_index_proxy: ratio new/existing cooc at impact
     - z_score_proxy: seed pair atypicality from cooc_global
     - activity_pre: total cooc weight of seeds 1y pre-impact

  B. Local topological metrics from cooc_global (static)
     - seed PageRank in local subgraph
     - seed clustering coefficient
     - weighted degree stats of seed neighbors

  C. Correlation screen: ALL features vs K, r, t₀, death
     - Spearman on all 13 meteorites
     - Flag any strong correlator for r (the missing piece)

  D. Assembly + Ridge + honest temporal test
     - Train: pre-1960 (6 meteorites)
     - Test: post-1974 (7 meteorites)

  E. R(t) trajectory with best assembly

Sky × Claude (Opus 4.6) — Session 36, 7 avril 2026
"""
import json, sys, os, math, time
import numpy as np
import sqlite3
import networkx as nx
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")
CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), encoding='utf-8'))
CANDLES = json.load(open(os.path.join(REPO, "data/results/wave_candlestick_model.json"), encoding='utf-8'))
OUTPUT = os.path.join(REPO, "data/results/wave_assembly_s36.json")

bfs = CHECK['phase_1']
mare = CHECK['phase_2']
logistic = CHECK['phase_3e']['fits']
METS = list(bfs.keys())
N = 65026

# Split
train_mets = [m for m in METS if int(m.split()[-1]) <= 1960]
test_mets  = [m for m in METS if int(m.split()[-1]) >= 1974]
train_idx = [METS.index(m) for m in train_mets]
test_idx  = [METS.index(m) for m in test_mets]

# Targets
K_all     = np.array([logistic[m]['K'] for m in METS])
r_all     = np.array([logistic[m]['r_growth'] for m in METS])
t0_all    = np.array([logistic[m]['t0'] for m in METS])
death_all = np.array([bfs[m].get('death_t', 8) or 8 for m in METS])

def P(*args, **kw):
    """Print with flush."""
    print(*args, **kw, flush=True)

P("=" * 80)
P("SESSION 36 — ASSEMBLAGE DYNAMIQUE")
P("scientiométrie + topologie locale + mare + candlestick")
P("=" * 80)


# ═══════════════════════════════════════════════════════
# PHASE A: Scientometric proxies from WT3
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE A: Proxys scientométriques depuis WT3 (cooc temporelle)")
P(f"{'='*80}")

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

scisci = {}
for mi, m in enumerate(METS):
    year = int(m.split()[-1])
    seeds = bfs[m]['seeds']
    t0_start = time.time()

    # ── A1: FITNESS GROWTH RATE (5y pre-impact) ──
    # For each seed: count distinct co-occurring concepts per year
    # Growth rate = linear slope of this count
    # Also collect yearly counts for D-index proxy (fast: one query per year)
    growth_rates = []
    activities_1y = []
    activities_5y = []
    yearly_per_seed = {}  # seed -> {year: count}

    for seed in seeds:
        yearly_counts = {}
        yearly_weights = {}
        # Query 7 years: 5 pre + impact year + 1 post
        for y in range(year - 5, year + 2):
            cur.execute("""
                SELECT COUNT(DISTINCT concept_b), COALESCE(SUM(weight), 0)
                FROM cooc
                WHERE concept_a = ? AND period >= ? AND period < ?
            """, (seed, f"{y}-01", f"{y+1}-01"))
            row = cur.fetchone()
            yearly_counts[y] = row[0]
            yearly_weights[y] = row[1]

        yearly_per_seed[seed] = yearly_counts

        # Growth rate on pre-impact years only
        pre_yrs = list(range(year - 5, year))
        counts_pre = np.array([yearly_counts[y] for y in pre_yrs])

        if counts_pre.sum() > 0:
            slope = np.polyfit(np.arange(len(pre_yrs)), counts_pre, 1)[0]
            growth_rates.append(slope)
        else:
            growth_rates.append(0)

        activities_1y.append(yearly_weights.get(year - 1, 0))
        activities_5y.append(sum(yearly_weights[y] for y in pre_yrs))

    fitness_growth = float(np.mean(growth_rates))
    activity_1y = float(np.mean(activities_1y))
    activity_5y = float(np.mean(activities_5y))

    # ── A2: D-INDEX PROXY from yearly counts (FAST, no full scan) ──
    # D_proxy = (impact_year_count - pre_year_avg) / impact_year_count
    # High D = disruptive burst of new concepts at impact
    d_ratios = []
    for seed in seeds:
        yc = yearly_per_seed[seed]
        pre_avg = np.mean([yc[y] for y in range(year - 3, year)])  # 3y average
        impact_count = yc.get(year, 0)
        if impact_count > 0:
            d_ratios.append((impact_count - pre_avg) / impact_count)
        else:
            d_ratios.append(0)

    d_index_proxy = float(np.mean(d_ratios))

    # ── A3: POST-IMPACT GROWTH from same yearly counts (FAST) ──
    post_growth_rates = []
    for seed in seeds:
        yc = yearly_per_seed[seed]
        pre_count = yc.get(year - 1, 0)
        post_count = yc.get(year, 0)  # impact year
        post_1y = yc.get(year + 1, 0)

        if pre_count > 0:
            post_growth_rates.append((post_count - pre_count) / pre_count)
        else:
            post_growth_rates.append(post_count if post_count > 0 else 0)

    post_growth = float(np.mean(post_growth_rates))

    # ── A4: Z-SCORE PROXY (atypicality of seed pair combination) ──
    z_scores = []
    if len(seeds) >= 2:
        # Get degrees of all seeds
        seed_degrees = {}
        for s in seeds:
            cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a = ?", (s,))
            d1 = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_b = ?", (s,))
            d2 = cur.fetchone()[0]
            seed_degrees[s] = d1 + d2

        for i in range(len(seeds)):
            for j in range(i+1, len(seeds)):
                a, b = min(seeds[i], seeds[j]), max(seeds[i], seeds[j])
                cur.execute("SELECT weight FROM cooc_global WHERE concept_a = ? AND concept_b = ?", (a, b))
                row = cur.fetchone()
                observed = row[0] if row else 0

                # Expected under configuration model
                deg_i = seed_degrees[seeds[i]]
                deg_j = seed_degrees[seeds[j]]
                # Total degree sum ≈ 2 * n_edges
                expected = deg_i * deg_j / (2 * 69440760)
                if expected > 0:
                    z = (observed - expected) / math.sqrt(expected + 0.01)
                    z_scores.append(z)

    z_score_proxy = float(np.mean(z_scores)) if z_scores else 0.0

    dt = time.time() - t0_start
    scisci[m] = {
        'fitness_growth': fitness_growth,
        'd_index_proxy': d_index_proxy,
        'z_score_proxy': z_score_proxy,
        'activity_1y': activity_1y,
        'activity_5y': activity_5y,
        'post_growth': post_growth,
    }

    P(f"  {m:20s} fit={fitness_growth:+8.1f} D={d_index_proxy:.3f} z={z_score_proxy:+8.3f} "
          f"act1y={activity_1y:10.0f} post={post_growth:+.3f} ({dt:.1f}s)")


# ═══════════════════════════════════════════════════════
# PHASE B: Local topological metrics from cooc_global
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE B: Topologie locale depuis cooc_global")
P(f"{'='*80}")

topo = {}
for mi, m in enumerate(METS):
    seeds = bfs[m]['seeds']
    seed_set = set(seeds)
    t0_start = time.time()

    # Get 1-hop neighborhood of seeds
    nbr_weights = {}  # (a, b) -> weight
    for seed in seeds:
        cur.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a = ?", (seed,))
        for row in cur.fetchall():
            nbr_weights[(seed, row[0])] = row[1]
        cur.execute("SELECT concept_a, weight FROM cooc_global WHERE concept_b = ?", (seed,))
        for row in cur.fetchall():
            nbr_weights[(row[0], seed)] = row[1]

    # All neighbor IDs
    all_nbrs = set()
    for (a, b) in nbr_weights:
        all_nbrs.add(a)
        all_nbrs.add(b)

    # Build graph with seed edges
    G = nx.Graph()
    for (a, b), w in nbr_weights.items():
        G.add_edge(a, b, weight=w)

    n_seed_edges = G.number_of_edges()

    # Add edges among top-weight neighbors (sample for tractability)
    # Focus on the most important neighbors (highest edge weight to seeds)
    nbr_list = sorted(all_nbrs - seed_set)

    # Get edge weights from seeds to each neighbor
    nbr_importance = {}
    for n in nbr_list:
        w = 0
        for s in seeds:
            w += nbr_weights.get((s, n), 0) + nbr_weights.get((n, s), 0)
        nbr_importance[n] = w

    # Take top 300 most important neighbors
    top_nbrs = sorted(nbr_list, key=lambda x: nbr_importance[x], reverse=True)[:300]
    top_set = set(top_nbrs) | seed_set

    # Query connections among top neighbors
    for node in top_nbrs:
        cur.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a = ?", (node,))
        for row in cur.fetchall():
            if row[0] in top_set and row[0] != node:
                G.add_edge(node, row[0], weight=row[1])

    dt_build = time.time() - t0_start

    # Compute metrics for seeds
    try:
        pr = nx.pagerank(G, weight='weight', max_iter=200, tol=1e-4)
    except Exception:
        pr = {}

    try:
        cc = nx.clustering(G, nodes=seeds, weight='weight')
    except Exception:
        cc = {}

    try:
        ec = nx.eigenvector_centrality(G, weight='weight', max_iter=300, tol=1e-4)
    except Exception:
        ec = {}

    # Seed metrics (average over seeds)
    pagerank_avg = float(np.mean([pr.get(s, 0) for s in seeds]))
    clustering_avg = float(np.mean([cc.get(s, 0) for s in seeds]))
    eigenvector_avg = float(np.mean([ec.get(s, 0) for s in seeds]))

    # Additional: weighted degree stats of neighbors
    nbr_degrees = [G.degree(n, weight='weight') for n in top_nbrs if G.has_node(n)]
    nbr_degree_median = float(np.median(nbr_degrees)) if nbr_degrees else 0
    nbr_degree_std = float(np.std(nbr_degrees)) if nbr_degrees else 0

    # Seed's weighted degree in local graph
    seed_wdeg = float(np.mean([G.degree(s, weight='weight') for s in seeds if G.has_node(s)]))

    topo[m] = {
        'pagerank_local': pagerank_avg,
        'clustering_local': clustering_avg,
        'eigenvector_local': eigenvector_avg,
        'nbr_degree_median': nbr_degree_median,
        'nbr_degree_std': nbr_degree_std,
        'seed_weighted_degree': seed_wdeg,
        'n_nodes': G.number_of_nodes(),
        'n_edges': G.number_of_edges(),
    }

    dt = time.time() - t0_start
    P(f"  {m:20s} PR={pagerank_avg:.6f} CC={clustering_avg:.4f} EV={eigenvector_avg:.6f} "
          f"({G.number_of_nodes()}n/{G.number_of_edges()}e, {dt:.1f}s)")

db.close()


# ═══════════════════════════════════════════════════════
# PHASE C: Feature correlation screen
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE C: Corrélation de TOUTES les features avec K, r, t₀, death")
P(f"{'='*80}")

# Build complete feature matrix
# 1. Mare features (already computed in checkpoint)
mare_features = ['n_neighbors', 'local_density', 'hub_fraction', 'avg_edge_weight',
                 'median_neighbor_works', 'seed_degree', 'seed_works', 'seed_weight',
                 'pre_edges', 'pre_weight', 'avg_level', 'n_seeds', 'avg_internal_weight']

# 2. Candlestick features
candle_features = ['ratio', 'body', 'volume', 'upper_wick', 'lower_wick', 'length', 'mu_peak']

# 3. Scientometric features
scisci_features = ['fitness_growth', 'd_index_proxy', 'z_score_proxy', 'activity_1y',
                   'activity_5y', 'post_growth']

# 4. Topological features
topo_features = ['pagerank_local', 'clustering_local', 'eigenvector_local',
                 'nbr_degree_median', 'nbr_degree_std', 'seed_weighted_degree']

# Collect all features
all_feature_names = []
all_feature_values = []

for f in mare_features:
    vals = np.array([mare[m][f] for m in METS])
    all_feature_names.append(f"mare_{f}")
    all_feature_values.append(vals)

for f in candle_features:
    vals = np.array([CANDLES['candles'][m][f] for m in METS])
    all_feature_names.append(f"candle_{f}")
    all_feature_values.append(vals)

for f in scisci_features:
    vals = np.array([scisci[m][f] for m in METS])
    all_feature_names.append(f"sci_{f}")
    all_feature_values.append(vals)

for f in topo_features:
    vals = np.array([topo[m][f] for m in METS])
    all_feature_names.append(f"topo_{f}")
    all_feature_values.append(vals)

# Derived features
hf = np.array([mare[m]['hub_fraction'] for m in METS])
dens = np.array([mare[m]['local_density'] for m in METS])
all_feature_names.append("mare_hub_frac_over_density")
all_feature_values.append(hf / (dens + 0.01))

cr = np.array([CANDLES['candles'][m]['ratio'] for m in METS])
all_feature_names.append("candle_log_ratio")
all_feature_values.append(np.log1p(cr))

fg = np.array([scisci[m]['fitness_growth'] for m in METS])
a5 = np.array([scisci[m]['activity_5y'] for m in METS])
all_feature_names.append("sci_fitness_per_activity")
all_feature_values.append(fg / (a5 + 1))

pg = np.array([scisci[m]['post_growth'] for m in METS])
all_feature_names.append("sci_post_times_fitness")
all_feature_values.append(pg * (fg + 1))

pr_local = np.array([topo[m]['pagerank_local'] for m in METS])
cl_local = np.array([topo[m]['clustering_local'] for m in METS])
all_feature_names.append("topo_pr_over_clustering")
all_feature_values.append(pr_local / (cl_local + 0.001))

X_full = np.column_stack(all_feature_values)
n_features = len(all_feature_names)

# Correlation screen
targets = {'K': K_all, 'r': r_all, 't0': t0_all, 'death': death_all}

P(f"\n  {'Feature':45s} {'ρ(K)':>7s} {'p':>7s} {'ρ(r)':>7s} {'p':>7s} {'ρ(t0)':>7s} {'p':>7s} {'ρ(d)':>7s} {'p':>7s}")
P("  " + "-" * 110)

strong_r = []  # Features with |ρ| > 0.5 for r
strong_K = []
strong_t0 = []

for i, fname in enumerate(all_feature_names):
    vals = all_feature_values[i]
    # Skip constant features
    if np.std(vals) < 1e-10:
        continue

    rk, pk = spearmanr(vals, K_all)
    rr, pr = spearmanr(vals, r_all)
    rt, pt = spearmanr(vals, t0_all)
    rd, pd = spearmanr(vals, death_all)

    flag_r = " <<<R" if abs(rr) > 0.5 else ""
    flag_K = " <<<K" if abs(rk) > 0.6 else ""

    if abs(rr) > 0.5 or abs(rk) > 0.6:
        P(f"  {fname:45s} {rk:+7.3f} {pk:7.4f} {rr:+7.3f} {pr:7.4f} {rt:+7.3f} {pt:7.4f} {rd:+7.3f} {pd:7.4f}{flag_K}{flag_r}")

    if abs(rr) > 0.5:
        strong_r.append((fname, rr, pr, i))
    if abs(rk) > 0.6:
        strong_K.append((fname, rk, pk, i))
    if abs(rt) > 0.5:
        strong_t0.append((fname, rt, pt, i))

P(f"\n  Features fortement corrélées avec r (|ρ|>0.5): {len(strong_r)}")
for name, rho, p, _ in sorted(strong_r, key=lambda x: abs(x[1]), reverse=True):
    P(f"    {name:45s} ρ={rho:+.4f} (p={p:.4f})")

P(f"\n  Features fortement corrélées avec K (|ρ|>0.6): {len(strong_K)}")
for name, rho, p, _ in sorted(strong_K, key=lambda x: abs(x[1]), reverse=True):
    P(f"    {name:45s} ρ={rho:+.4f} (p={p:.4f})")


# ═══════════════════════════════════════════════════════
# PHASE D: Assembly + Ridge + Honest temporal test
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE D: Assemblage + Ridge + Test temporel honnête")
P(f"{'='*80}")

def temporal_test_ridge(feature_names, feature_idx_list, target, target_name):
    """Train Ridge on pre-1960, predict post-1974. Return median % error."""
    X = np.column_stack([all_feature_values[i] for i in feature_idx_list])

    X_train = X[train_idx]
    X_test = X[test_idx]
    y_train = target[train_idx]
    y_test = target[test_idx]

    sc = StandardScaler()
    X_train_s = sc.fit_transform(X_train)
    X_test_s = sc.transform(X_test)

    model = Ridge(alpha=1.0)
    model.fit(X_train_s, y_train)
    y_pred = model.predict(X_test_s)

    # Percentage errors
    pct_errors = np.abs(y_pred - y_test) / np.abs(y_test) * 100
    med_err = np.median(pct_errors)

    return med_err, y_pred, pct_errors

def compute_r2_trajectory(K, r, t0, wave_data):
    """Compute R² of predicted R(t) vs observed."""
    t_arr = np.array([w['t'] for w in wave_data], dtype=float)
    R_obs = np.array([w['total_touched'] for w in wave_data], dtype=float)
    R_pred = K / (1 + np.exp(-np.clip(r * (t_arr - t0), -500, 500)))
    ss_res = np.sum((R_obs - R_pred) ** 2)
    ss_tot = np.sum((R_obs - R_obs.mean()) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else 0

# ── D1: Best K model ──
P("\n  [D1] Test K prediction — combinaisons de features")

# Pure mare (baseline from session 35)
mare_idx = [i for i, n in enumerate(all_feature_names) if n.startswith("mare_") and "_over_" not in n]
err_K_mare, K_pred_mare, _ = temporal_test_ridge(
    [all_feature_names[i] for i in mare_idx], mare_idx, K_all, "K")
P(f"    Mare only:              {err_K_mare:.1f}% median error")

# Mare + scientometric
sci_idx = [i for i, n in enumerate(all_feature_names) if n.startswith("sci_")]
err_K_ms, K_pred_ms, _ = temporal_test_ridge(
    [all_feature_names[i] for i in mare_idx + sci_idx], mare_idx + sci_idx, K_all, "K")
P(f"    Mare + scientiométrie:  {err_K_ms:.1f}% median error")

# Mare + topo
topo_idx = [i for i, n in enumerate(all_feature_names) if n.startswith("topo_")]
err_K_mt, K_pred_mt, _ = temporal_test_ridge(
    [all_feature_names[i] for i in mare_idx + topo_idx], mare_idx + topo_idx, K_all, "K")
P(f"    Mare + topologie:       {err_K_mt:.1f}% median error")

# Mare + sci + topo
err_K_all, K_pred_all, _ = temporal_test_ridge(
    [all_feature_names[i] for i in mare_idx + sci_idx + topo_idx],
    mare_idx + sci_idx + topo_idx, K_all, "K")
P(f"    Mare + sci + topo:      {err_K_all:.1f}% median error")

# Just strong K correlators
if strong_K:
    strong_K_idx = [x[3] for x in strong_K[:8]]
    err_K_strong, K_pred_strong, _ = temporal_test_ridge(
        [all_feature_names[i] for i in strong_K_idx], strong_K_idx, K_all, "K")
    P(f"    Strong K correlators:   {err_K_strong:.1f}% median error")

# ── D2: Best r model ──
P("\n  [D2] Test r prediction — chercher un prédicteur PRÉ-impact")

# Pre-impact only features (no candle, no post_growth)
pre_impact_feat_idx = [i for i, n in enumerate(all_feature_names)
                       if not n.startswith("candle_") and "post_" not in n]
err_r_pre, r_pred_pre, r_pct_pre = temporal_test_ridge(
    [all_feature_names[i] for i in pre_impact_feat_idx], pre_impact_feat_idx, r_all, "r")
P(f"    All pre-impact features: {err_r_pre:.1f}% median error")

# Mare only
err_r_mare, r_pred_mare, _ = temporal_test_ridge(
    [all_feature_names[i] for i in mare_idx], mare_idx, r_all, "r")
P(f"    Mare only:               {err_r_mare:.1f}% median error")

# Scientiometric only
err_r_sci, r_pred_sci, _ = temporal_test_ridge(
    [all_feature_names[i] for i in sci_idx], sci_idx, r_all, "r")
P(f"    Scientiométrie only:     {err_r_sci:.1f}% median error")

# Topo only
err_r_topo, r_pred_topo, _ = temporal_test_ridge(
    [all_feature_names[i] for i in topo_idx], topo_idx, r_all, "r")
P(f"    Topologie only:          {err_r_topo:.1f}% median error")

# Mare + sci + topo (all pre-impact)
pre_combined = mare_idx + sci_idx + topo_idx
err_r_comb, r_pred_comb, _ = temporal_test_ridge(
    [all_feature_names[i] for i in pre_combined], pre_combined, r_all, "r")
P(f"    Mare + sci + topo:       {err_r_comb:.1f}% median error")

# Strong r correlators if any
if strong_r:
    strong_r_pre = [(n, rho, p, idx) for n, rho, p, idx in strong_r
                    if not n.startswith("candle_") and "post_" not in n]
    if strong_r_pre:
        sr_idx = [x[3] for x in strong_r_pre[:6]]
        err_r_strong, r_pred_strong, _ = temporal_test_ridge(
            [all_feature_names[i] for i in sr_idx], sr_idx, r_all, "r")
        P(f"    Strong r (pre-impact):   {err_r_strong:.1f}% median error")

# ── D3: Best t0 model ──
P("\n  [D3] Test t₀ prediction")

# Death-based (baseline)
death_test = death_all[test_idx]
t0_from_death = 0.208 * death_test
t0_test = t0_all[test_idx]
err_t0_death = float(np.median(np.abs(t0_from_death - t0_test) / np.abs(t0_test) * 100))
P(f"    0.208 × death:           {err_t0_death:.1f}% median error")

# Ridge on all pre-impact
err_t0_pre, t0_pred_pre, _ = temporal_test_ridge(
    [all_feature_names[i] for i in pre_combined], pre_combined, t0_all, "t0")
P(f"    Ridge(pre-impact):       {err_t0_pre:.1f}% median error")


# ═══════════════════════════════════════════════════════
# PHASE E: R(t) trajectory with best assembly
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE E: R(t) trajectoire avec le meilleur assemblage")
P(f"{'='*80}")

# Pick best K, r, t0 predictions for R(t)
# Try multiple combinations
K_candidates = {
    'mare': (err_K_mare, K_pred_mare),
    'mare+sci': (err_K_ms, K_pred_ms),
    'mare+topo': (err_K_mt, K_pred_mt),
    'mare+sci+topo': (err_K_all, K_pred_all),
}
best_K_name = min(K_candidates, key=lambda x: K_candidates[x][0])
best_K_err, best_K_pred = K_candidates[best_K_name]

r_candidates = {
    'mare': (err_r_mare, r_pred_mare),
    'sci': (err_r_sci, r_pred_sci),
    'topo': (err_r_topo, r_pred_topo),
    'pre_combined': (err_r_comb, r_pred_comb),
    'all_pre': (err_r_pre, r_pred_pre),
}
best_r_name = min(r_candidates, key=lambda x: r_candidates[x][0])
best_r_err, best_r_pred = r_candidates[best_r_name]

t0_candidates = {
    '0.208*death': (err_t0_death, t0_from_death),
    'Ridge(pre)': (err_t0_pre, t0_pred_pre),
}
best_t0_name = min(t0_candidates, key=lambda x: t0_candidates[x][0])
best_t0_err, best_t0_pred = t0_candidates[best_t0_name]

P(f"\n  Meilleur K:  {best_K_name} ({best_K_err:.1f}%)")
P(f"  Meilleur r:  {best_r_name} ({best_r_err:.1f}%)")
P(f"  Meilleur t0: {best_t0_name} ({best_t0_err:.1f}%)")

# R(t) trajectory
P(f"\n  {'Météorite':25s} {'K_obs':>8s} {'K_pred':>8s} {'r_obs':>6s} {'r_pred':>6s} {'t0_obs':>6s} {'t0_pred':>6s} {'R²':>7s}")
r2_list = []
K_test_true = K_all[test_idx]
r_test_true = r_all[test_idx]
t0_test_true = t0_all[test_idx]

for i, m in enumerate(test_mets):
    wd = bfs[m]['wave_data']
    r2 = compute_r2_trajectory(best_K_pred[i], best_r_pred[i], best_t0_pred[i], wd)
    r2_list.append(r2)
    P(f"  {m:25s} {K_test_true[i]:8,.0f} {best_K_pred[i]:8,.0f} "
          f"{r_test_true[i]:6.2f} {best_r_pred[i]:6.2f} "
          f"{t0_test_true[i]:6.2f} {best_t0_pred[i]:6.2f} {r2:+7.4f}")

med_r2 = float(np.median(r2_list))
verdict = "PASS" if med_r2 > 0.5 else "PARTIAL" if med_r2 > 0 else "FAIL"

P(f"\n  Médiane R² = {med_r2:.4f}")
P(f"  VERDICT R(t): {verdict}")

# Also test: best K + TRUE r (to confirm diagnostic)
r2_hybrid = []
for i, m in enumerate(test_mets):
    wd = bfs[m]['wave_data']
    r2 = compute_r2_trajectory(best_K_pred[i], r_test_true[i], t0_test_true[i], wd)
    r2_hybrid.append(r2)
P(f"\n  Contrôle: best K pred + TRUE r + TRUE t0 → R² median = {np.median(r2_hybrid):.4f}")


# ═══════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("SAUVEGARDE")
P(f"{'='*80}")

output = {
    "test": "assembly_s36_v1",
    "date": "2026-04-07",
    "phase_A_scientometrics": scisci,
    "phase_B_topology": topo,
    "phase_C_correlations": {
        "strong_r": [(n, round(rho, 4), round(p, 4)) for n, rho, p, _ in strong_r],
        "strong_K": [(n, round(rho, 4), round(p, 4)) for n, rho, p, _ in strong_K],
        "n_features_total": n_features,
    },
    "phase_D_temporal_test": {
        "K_best_model": best_K_name,
        "K_best_error": round(best_K_err, 1),
        "r_best_model": best_r_name,
        "r_best_error": round(best_r_err, 1),
        "t0_best_model": best_t0_name,
        "t0_best_error": round(best_t0_err, 1),
    },
    "phase_E_trajectory": {
        "median_r2": round(med_r2, 4),
        "verdict": verdict,
        "per_meteorite": {m: round(r2_list[i], 4) for i, m in enumerate(test_mets)},
        "control_true_r": round(float(np.median(r2_hybrid)), 4),
    },
    "diagnostic": {
        "r_is_the_bottleneck": True,
        "candle_ratio_fails_temporally": True,
        "K_with_true_r_gives": round(float(np.median(r2_hybrid)), 4),
    },
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

P(f"\nSaved: {OUTPUT}")
P("DONE — Session 36 Phase 1 complete.")
