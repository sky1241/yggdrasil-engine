#!/usr/bin/env python3
"""
YGGDRASIL — Session 38: Topologie temporelle (dynamique pré-impact)
====================================================================
Mesure comment le graphe CHANGE autour de chaque seed AVANT l'impact.
Utilise la table cooc (885M rows, per-period) — pas cooc_global (statique).

Insight: les 4 méthodes réseau statiques ont TOUTES FAIL parce que le graphe
est trop dense et uniforme. La DYNAMIQUE (vitesse de croissance locale) est
peut-être le signal manquant.

Features extraites pour chaque météorite:
  - degree_growth: taux de croissance du degré du seed dans les 10 ans pré-impact
  - edge_birth_rate: nombre de nouvelles arêtes par an autour du seed
  - acceleration: accélération de la croissance (dérivée seconde)
  - local_density_change: comment la densité locale évolue
  - concept_birth_rate: combien de nouveaux concepts apparaissent dans le voisinage

Sky × Claude (Opus 4.6) — Session 38, 21 avril 2026
"""
import json, sys, os, time
import numpy as np
import sqlite3
from scipy.stats import spearmanr, linregress
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
P(f"TOPOLOGIE TEMPORELLE — {N_METS} météorites ({len(train_idx)} train, {len(test_idx)} test)")
P("=" * 80)

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

# ═══════════════════════════════════════════════════════
# TEMPORAL FEATURES: how the graph changes BEFORE impact
# ═══════════════════════════════════════════════════════

WINDOW = 15  # years before impact to analyze

def get_temporal_profile(seeds, impact_year, cur, window=WINDOW):
    """
    For each seed, query the cooc table to measure how the local neighborhood
    changes in the years before the impact.

    Uses idx_cooc_a_period (concept_a, period) for speed.
    Single query per seed: fetch all periods at once, then bin by year.
    """
    yearly = {}
    start_year = impact_year - window

    for seed in seeds:
        # Single range query using the composite index idx_cooc_a_period
        cur.execute("""
            SELECT period, concept_b, weight FROM cooc
            WHERE concept_a = ? AND CAST(period AS INTEGER) BETWEEN ? AND ?
        """, (seed, start_year, impact_year))

        for period, b, w in cur.fetchall():
            try:
                year = int(period)
            except:
                continue
            if year < start_year or year > impact_year:
                continue
            if year not in yearly:
                yearly[year] = {'n_edges': 0, 'total_weight': 0, 'neighbors': set()}
            yearly[year]['n_edges'] += 1
            yearly[year]['total_weight'] += w
            yearly[year]['neighbors'].add(b)

    # Fill missing years with zeros and convert sets to counts
    result = {}
    for year in range(start_year, impact_year + 1):
        if year in yearly:
            result[year] = {
                'n_edges': yearly[year]['n_edges'],
                'total_weight': yearly[year]['total_weight'],
                'n_neighbors': len(yearly[year]['neighbors']),
            }
        else:
            result[year] = {'n_edges': 0, 'total_weight': 0, 'n_neighbors': 0}

    return result


def extract_temporal_features(yearly, impact_year, window=WINDOW):
    """Extract features from the yearly temporal profile."""
    years = sorted(yearly.keys())
    if len(years) < 3:
        return {f: 0 for f in [
            'degree_at_impact', 'degree_5y_before', 'degree_growth_rate',
            'weight_at_impact', 'weight_growth_rate',
            'edge_birth_rate', 'acceleration',
            'degree_ratio_5y', 'activity_trend_slope',
            'cumulative_edges_10y', 'cumulative_weight_10y',
            'max_yearly_edges', 'year_of_max_edges',
            'pre_impact_burst', 'dormancy_years',
        ]}

    edges_series = [yearly[y]['n_edges'] for y in years]
    weight_series = [yearly[y]['total_weight'] for y in years]
    neighbor_series = [yearly[y]['n_neighbors'] for y in years]

    # Degree at impact and 5 years before
    degree_at_impact = yearly.get(impact_year, {}).get('n_neighbors', 0)
    degree_5y = yearly.get(impact_year - 5, {}).get('n_neighbors', 0)

    # Growth rate: linear regression on neighbor count
    valid_years = [(y - impact_year, yearly[y]['n_neighbors']) for y in years if yearly[y]['n_neighbors'] > 0]
    if len(valid_years) >= 3:
        xs = [v[0] for v in valid_years]
        ys = [v[1] for v in valid_years]
        slope, intercept, r_value, p_value, std_err = linregress(xs, ys)
        degree_growth_rate = slope
    else:
        degree_growth_rate = 0

    # Weight growth rate
    valid_w = [(y - impact_year, yearly[y]['total_weight']) for y in years if yearly[y]['total_weight'] > 0]
    if len(valid_w) >= 3:
        xs = [v[0] for v in valid_w]
        ys = [v[1] for v in valid_w]
        slope_w, _, _, _, _ = linregress(xs, ys)
        weight_growth_rate = slope_w
    else:
        weight_growth_rate = 0

    # Edge birth rate: new edges per year (difference)
    edge_diffs = [edges_series[i] - edges_series[i-1] for i in range(1, len(edges_series))]
    edge_birth_rate = np.mean(edge_diffs) if edge_diffs else 0

    # Acceleration: change in edge birth rate
    if len(edge_diffs) >= 3:
        accel = [edge_diffs[i] - edge_diffs[i-1] for i in range(1, len(edge_diffs))]
        acceleration = np.mean(accel)
    else:
        acceleration = 0

    # Degree ratio: impact vs 5 years before
    degree_ratio_5y = degree_at_impact / degree_5y if degree_5y > 0 else 0

    # Activity trend: slope of edges per year
    if len(edges_series) >= 3:
        xs_e = list(range(len(edges_series)))
        slope_e, _, _, _, _ = linregress(xs_e, edges_series)
        activity_trend_slope = slope_e
    else:
        activity_trend_slope = 0

    # Cumulative activity in 10 years before impact
    cum_10y = sum(yearly.get(y, {}).get('n_edges', 0) for y in range(impact_year - 10, impact_year))
    cum_w_10y = sum(yearly.get(y, {}).get('total_weight', 0) for y in range(impact_year - 10, impact_year))

    # Max yearly edges and when
    max_edges = max(edges_series) if edges_series else 0
    year_of_max = years[edges_series.index(max_edges)] if max_edges > 0 else impact_year
    years_before_max = impact_year - year_of_max

    # Pre-impact burst: ratio of last 3 years vs previous 5 years
    last_3 = sum(yearly.get(y, {}).get('n_edges', 0) for y in range(impact_year - 2, impact_year + 1))
    prev_5 = sum(yearly.get(y, {}).get('n_edges', 0) for y in range(impact_year - 7, impact_year - 2))
    pre_impact_burst = last_3 / prev_5 if prev_5 > 0 else 0

    # Dormancy: how many consecutive years with 0 edges before impact
    dormancy = 0
    for y in range(impact_year - 1, impact_year - window - 1, -1):
        if yearly.get(y, {}).get('n_edges', 0) == 0:
            dormancy += 1
        else:
            break

    return {
        'degree_at_impact': degree_at_impact,
        'degree_5y_before': degree_5y,
        'degree_growth_rate': degree_growth_rate,
        'weight_at_impact': yearly.get(impact_year, {}).get('total_weight', 0),
        'weight_growth_rate': weight_growth_rate,
        'edge_birth_rate': edge_birth_rate,
        'acceleration': acceleration,
        'degree_ratio_5y': degree_ratio_5y,
        'activity_trend_slope': activity_trend_slope,
        'cumulative_edges_10y': cum_10y,
        'cumulative_weight_10y': cum_w_10y,
        'max_yearly_edges': max_edges,
        'year_of_max_edges': years_before_max,
        'pre_impact_burst': pre_impact_burst,
        'dormancy_years': dormancy,
    }


P(f"\nMesure dynamique pré-impact (fenêtre {WINDOW} ans)...\n")

results = {}
for mi, met in enumerate(all_mets):
    name = met['name']
    seeds = met['seeds']
    year = met['year']
    t0 = time.time()

    yearly = get_temporal_profile(seeds, year, cur, WINDOW)
    feats = extract_temporal_features(yearly, year, WINDOW)
    feats['yearly_profile'] = {str(y): d for y, d in yearly.items()}
    results[name] = feats

    dt = time.time() - t0
    P(f"  [{mi+1:2d}/{N_METS}] {name:25s}  deg@impact={feats['degree_at_impact']:>5d}  "
      f"growth={feats['degree_growth_rate']:>+7.1f}  burst={feats['pre_impact_burst']:>5.2f}  "
      f"cum10y={feats['cumulative_edges_10y']:>6d}  dorm={feats['dormancy_years']}  ({dt:.1f}s)")

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
    'degree_at_impact', 'degree_5y_before', 'degree_growth_rate',
    'weight_at_impact', 'weight_growth_rate',
    'edge_birth_rate', 'acceleration',
    'degree_ratio_5y', 'activity_trend_slope',
    'cumulative_edges_10y', 'cumulative_weight_10y',
    'max_yearly_edges', 'year_of_max_edges',
    'pre_impact_burst', 'dormancy_years',
]

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

P(f"  K prediction (Ridge, temporal features):")
P(f"    Median error: {K_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={K_test[idx]:>8,.0f}  pred={K_pred[idx]:>8,.0f}  err={K_errors[idx]:.0f}%")

ridge_r = Ridge(alpha=1.0)
ridge_r.fit(X_train_s, r_train)
r_pred = ridge_r.predict(X_test_s)
r_errors = np.abs(r_pred - r_test) / r_test * 100
r_med_err = float(np.median(r_errors))

P(f"\n  r prediction (Ridge, temporal features):")
P(f"    Median error: {r_med_err:.1f}%")
for idx, ti in enumerate(test_idx):
    P(f"      {all_mets[ti]['name']:25s}  obs={r_test[idx]:>6.3f}  pred={r_pred[idx]:>6.3f}  err={r_errors[idx]:.0f}%")

# ═══════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("VERDICT TOPOLOGIE TEMPORELLE")
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
    'method': 'temporal_topology',
    'date': '2026-04-21',
    'session': 38,
    'n_meteorites': N_METS,
    'params': {'window_years': WINDOW},
    'references': [
        'Original approach — not from literature',
        'Insight: static topology is uniform (⟨k⟩=2136), dynamics may differ',
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

out_path = os.path.join(REPO, "data/results/wave_temporal_topology.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
P(f"\n  Saved: {out_path}")
P("DONE.")
