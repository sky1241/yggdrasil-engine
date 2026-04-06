#!/usr/bin/env python3
"""
YGGDRASIL — V3 Boosted Predictive Model
=========================================
Utilise WT4 positions spectrales (66K noeuds) + toutes les features.
Puis test temporel honnête: train pré-1960, predict post-1974.

Sky × Claude (Opus 4.6) — Session 34, 6 avril 2026
"""
import json, sys, os, math, time
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

REPO = "D:/ygg/yggdrasil-engine"
CHECK_PATH = os.path.join(REPO, "data", "results", "_wave_checkpoint.json")
SPECTRAL_PATH = os.path.join(REPO, "data", "scan", "spectral_births.json")
OUTPUT = os.path.join(REPO, "data", "results", "wave_boosted_model.json")

N = 65026

print("=" * 80)
print("V3 BOOSTED PREDICTIVE MODEL")
print("WT4 positions spectrales + test temporel honnête")
print("=" * 80)

# Load data
ck = json.load(open(CHECK_PATH, 'r', encoding='utf-8'))
bfs = ck['phase_1']
mare = ck['phase_2']
logistic = ck['phase_3e']['fits']

# Load spectral positions
print("Loading spectral_births.json (66K positions)...", flush=True)
t0 = time.time()
sb = json.load(open(SPECTRAL_PATH, 'r', encoding='utf-8'))
node_by_id = {n['id']: n for n in sb['nodes']}
print(f"  {len(node_by_id)} nodes loaded in {time.time()-t0:.1f}s")

# Compute graph center (mean of all concept positions)
concepts_only = [n for n in sb['nodes'] if n.get('type') == 'concept']
if not concepts_only:
    concepts_only = [n for n in sb['nodes'] if n['id'] >= 0]  # all nodes
cx = np.mean([n['x'] for n in concepts_only])
cy = np.mean([n['y'] for n in concepts_only])
cz = np.mean([n['z'] for n in concepts_only])
print(f"  Graph center: ({cx:.4f}, {cy:.4f}, {cz:.4f})")

METS = list(bfs.keys())

# ══════════════════════════════════════════════════════
# NEW FEATURES from WT4
# ══════════════════════════════════════════════════════

print(f"\n[1] FEATURES WT4 SPECTRALES")
print("=" * 80)

wt4_features = {}
for m_name in METS:
    seeds = bfs[m_name]['seeds']

    # Seed spectral positions
    seed_positions = []
    for s in seeds:
        if s in node_by_id:
            n = node_by_id[s]
            seed_positions.append((n['x'], n['y'], n['z']))

    if not seed_positions:
        wt4_features[m_name] = {
            'seed_spectral_dist': 0, 'seed_spectral_spread': 0,
            'seed_x_mean': 0, 'seed_y_mean': 0, 'seed_z_mean': 0,
        }
        continue

    sx = np.mean([p[0] for p in seed_positions])
    sy = np.mean([p[1] for p in seed_positions])
    sz = np.mean([p[2] for p in seed_positions])

    # Distance from graph center (periphery vs core)
    dist_center = math.sqrt((sx - cx)**2 + (sy - cy)**2 + (sz - cz)**2)

    # Spread of seeds (how far apart are the seeds)
    if len(seed_positions) > 1:
        dists = []
        for i in range(len(seed_positions)):
            for j in range(i+1, len(seed_positions)):
                d = math.sqrt(sum((a-b)**2 for a, b in zip(seed_positions[i], seed_positions[j])))
                dists.append(d)
        spread = np.mean(dists)
    else:
        spread = 0

    # Spectral degree (from spectral_births)
    seed_degrees = [node_by_id[s].get('degree', 0) for s in seeds if s in node_by_id]
    mean_spectral_deg = np.mean(seed_degrees) if seed_degrees else 0

    wt4_features[m_name] = {
        'seed_spectral_dist': round(dist_center, 4),
        'seed_spectral_spread': round(spread, 4),
        'seed_x_mean': round(sx, 4),
        'seed_y_mean': round(sy, 4),
        'seed_z_mean': round(sz, 4),
        'mean_spectral_degree': round(mean_spectral_deg, 1),
    }

    K = logistic[m_name].get('K', bfs[m_name]['r_max'])
    r = logistic[m_name].get('r_growth', 1)
    print(f"  {m_name:25s} dist={dist_center:.3f} spread={spread:.3f} "
          f"spec_deg={mean_spectral_deg:>8.0f} K={K:>8,} r={r:.2f}")


# ══════════════════════════════════════════════════════
# COMBINED FEATURE MATRIX (old + new)
# ══════════════════════════════════════════════════════

print(f"\n[2] CORRÉLATIONS COMPLÈTES (anciennes + nouvelles features)")
print("=" * 80)

all_features = {}
for m in METS:
    f = {}
    # Old mare features
    for k, v in mare[m].items():
        f[k] = v
    # New WT4 features
    for k, v in wt4_features[m].items():
        f[k] = v
    # Derived
    f['1_over_n_seeds'] = 1.0 / mare[m]['n_seeds']
    f['dist_x_spread'] = wt4_features[m]['seed_spectral_dist'] * wt4_features[m].get('seed_spectral_spread', 0)
    f['dist_over_n_seeds'] = wt4_features[m]['seed_spectral_dist'] / mare[m]['n_seeds']
    all_features[m] = f

# Targets
K_vals = np.array([logistic[m].get('K', bfs[m]['r_max']) for m in METS])
r_vals = np.array([logistic[m].get('r_growth', 1) for m in METS])
t0_vals = np.array([logistic[m].get('t0', 1) for m in METS])

feature_names = sorted(all_features[METS[0]].keys())
X = np.array([[all_features[m][f] for f in feature_names] for m in METS])

print(f"  {len(feature_names)} features × {len(METS)} météorites")

# Correlations
print(f"\n  {'Feature':35s} {'vs K':>8s} {'p':>7s} {'vs r':>8s} {'p':>7s} {'vs t0':>8s} {'p':>7s}")
corr_results = {}
for i, fn in enumerate(feature_names):
    vals = X[:, i]
    if np.std(vals) == 0:
        continue
    rk, pk = spearmanr(vals, K_vals)
    rr, pr = spearmanr(vals, r_vals)
    rt, pt = spearmanr(vals, t0_vals)
    corr_results[fn] = {
        'K': (round(rk, 4), round(pk, 4)),
        'r': (round(rr, 4), round(pr, 4)),
        't0': (round(rt, 4), round(pt, 4)),
    }
    flag = ""
    if abs(rr) > 0.6 or abs(rt) > 0.6:
        flag = " <<<"
    print(f"  {fn:35s} {rk:+8.4f} {pk:7.4f} {rr:+8.4f} {pr:7.4f} {rt:+8.4f} {pt:7.4f}{flag}")


# ══════════════════════════════════════════════════════
# RIDGE REGRESSION — Boosted
# ══════════════════════════════════════════════════════

print(f"\n[3] RIDGE REGRESSION BOOSTÉE (LOO 13-fold)")
print("=" * 80)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

regression = {}
for target_name, y in [('K', K_vals), ('r', r_vals), ('t0', t0_vals)]:
    # Find best alpha
    best_alpha, best_mae = 1.0, float('inf')
    for alpha in [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]:
        errors = []
        for i in range(len(METS)):
            mask = np.ones(len(METS), dtype=bool)
            mask[i] = False
            model = Ridge(alpha=alpha)
            model.fit(X_scaled[mask], y[mask])
            pred = model.predict(X_scaled[i:i+1])[0]
            errors.append(abs(pred - y[i]))
        mae = np.mean(errors)
        if mae < best_mae:
            best_mae = mae
            best_alpha = alpha

    # LOO with best alpha
    loo = []
    for i in range(len(METS)):
        mask = np.ones(len(METS), dtype=bool)
        mask[i] = False
        model = Ridge(alpha=best_alpha)
        model.fit(X_scaled[mask], y[mask])
        pred = float(model.predict(X_scaled[i:i+1])[0])
        obs = float(y[i])
        pct_err = abs(pred - obs) / max(abs(obs), 0.01) * 100
        loo.append({'met': METS[i], 'obs': round(obs, 2), 'pred': round(pred, 2),
                    'error': round(abs(pred-obs), 2), 'pct_error': round(pct_err, 1)})

    mae = np.mean([l['error'] for l in loo])
    med_pct = np.median([l['pct_error'] for l in loo])

    # Feature importance
    final_model = Ridge(alpha=best_alpha)
    final_model.fit(X_scaled, y)
    importances = sorted(zip(feature_names, final_model.coef_), key=lambda x: -abs(x[1]))[:5]

    verdict = "PASS" if med_pct < 20 else "PARTIAL" if med_pct < 40 else "FAIL"

    print(f"\n  --- {target_name} (alpha={best_alpha}) ---")
    print(f"  {'Met':25s} {'Obs':>10s} {'Pred':>10s} {'Err%':>6s}")
    for l in sorted(loo, key=lambda x: -x['obs']):
        print(f"  {l['met']:25s} {l['obs']:10,.1f} {l['pred']:10,.1f} {l['pct_error']:5.1f}%")
    print(f"  MAE={mae:,.1f} med%err={med_pct:.1f}% VERDICT={verdict}")
    print(f"  Top features: {', '.join(f'{n}({v:+.0f})' for n,v in importances)}")

    regression[target_name] = {
        'verdict': verdict, 'best_alpha': best_alpha,
        'mae': round(mae, 2), 'median_pct_error': round(med_pct, 1),
        'loo': loo, 'top_features': dict(importances[:5]),
    }


# ══════════════════════════════════════════════════════
# TEST TEMPOREL HONNÊTE — Train pré-1960, predict post-1974
# ══════════════════════════════════════════════════════

print(f"\n[4] TEST TEMPOREL HONNÊTE")
print("=" * 80)

train_mets = [m for m in METS if bfs[m]['open_year'] <= 1960]
test_mets = [m for m in METS if bfs[m]['open_year'] >= 1974]

print(f"  Train ({len(train_mets)}): {', '.join(train_mets)}")
print(f"  Test  ({len(test_mets)}): {', '.join(test_mets)}")

X_train = np.array([[all_features[m][f] for f in feature_names] for m in train_mets])
X_test = np.array([[all_features[m][f] for f in feature_names] for m in test_mets])

scaler_temp = StandardScaler()
X_train_s = scaler_temp.fit_transform(X_train)
X_test_s = scaler_temp.transform(X_test)

temporal_results = {}
for target_name, y_all in [('K', K_vals), ('r', r_vals), ('t0', t0_vals)]:
    y_train = np.array([y_all[METS.index(m)] for m in train_mets])
    y_test = np.array([y_all[METS.index(m)] for m in test_mets])

    # Use best alpha from LOO
    alpha = regression[target_name]['best_alpha']
    model = Ridge(alpha=alpha)
    model.fit(X_train_s, y_train)
    preds = model.predict(X_test_s)

    print(f"\n  --- {target_name} ---")
    print(f"  {'Met':25s} {'Obs':>10s} {'Pred':>10s} {'Err%':>6s}")
    errors = []
    for i, m in enumerate(test_mets):
        obs = float(y_test[i])
        pred = float(preds[i])
        pct = abs(pred - obs) / max(abs(obs), 0.01) * 100
        errors.append(pct)
        print(f"  {m:25s} {obs:10,.1f} {pred:10,.1f} {pct:5.1f}%")

    mae = np.mean([abs(float(preds[i]) - float(y_test[i])) for i in range(len(test_mets))])
    med_pct = np.median(errors)
    verdict = "PASS" if med_pct < 25 else "PARTIAL" if med_pct < 50 else "FAIL"
    print(f"  MAE={mae:,.1f} med%err={med_pct:.1f}% VERDICT={verdict}")

    temporal_results[target_name] = {
        'verdict': verdict, 'mae': round(mae, 2), 'median_pct_error': round(med_pct, 1),
        'n_train': len(train_mets), 'n_test': len(test_mets),
    }


# ══════════════════════════════════════════════════════
# RECONSTRUCT R(t) for test meteorites
# ══════════════════════════════════════════════════════

print(f"\n[5] RECONSTRUCTION R(t) — Test météorites")
print("=" * 80)

trajectory_results = {}
for target_name in ['K', 'r', 't0']:
    y_train = np.array([K_vals[METS.index(m)] if target_name == 'K' else
                        r_vals[METS.index(m)] if target_name == 'r' else
                        t0_vals[METS.index(m)] for m in train_mets])

for m in test_mets:
    # Get predicted K, r, t0
    idx_all = METS.index(m)
    x_m = X_test_s[test_mets.index(m):test_mets.index(m)+1]

    K_pred = float(Ridge(alpha=regression['K']['best_alpha']).fit(
        X_train_s, np.array([K_vals[METS.index(t)] for t in train_mets])).predict(x_m)[0])
    r_pred = float(Ridge(alpha=regression['r']['best_alpha']).fit(
        X_train_s, np.array([r_vals[METS.index(t)] for t in train_mets])).predict(x_m)[0])
    t0_pred = float(Ridge(alpha=regression['t0']['best_alpha']).fit(
        X_train_s, np.array([t0_vals[METS.index(t)] for t in train_mets])).predict(x_m)[0])

    # Clamp
    K_pred = max(1000, K_pred)
    r_pred = max(0.1, r_pred)
    t0_pred = max(0.1, t0_pred)

    # Observed R(t)
    wave_data = bfs[m]['wave_data']
    t_obs = np.array([w['t'] for w in wave_data], dtype=float)
    r_obs = np.array([w['total_touched'] for w in wave_data], dtype=float)

    # Predicted R(t)
    r_pred_t = K_pred / (1 + np.exp(-r_pred * (t_obs - t0_pred)))
    r_pred_t = np.maximum(0, r_pred_t)

    # R²
    ss_res = np.sum((r_obs - r_pred_t)**2)
    ss_tot = np.sum((r_obs - r_obs.mean())**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    trajectory_results[m] = {
        'K_pred': round(K_pred), 'r_pred': round(r_pred, 3), 't0_pred': round(t0_pred, 3),
        'K_obs': bfs[m]['r_max'], 'r2_trajectory': round(r2, 4),
    }

    print(f"  {m:25s} K_obs={bfs[m]['r_max']:>8,} K_pred={K_pred:>8,.0f} "
          f"r_pred={r_pred:.2f} t0_pred={t0_pred:.2f} R²={r2:.4f}")


# ══════════════════════════════════════════════════════
# VERDICT FINAL
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("VERDICT FINAL — MODÈLE BOOSTÉ")
print(f"{'='*80}")

print(f"\n  LOO 13-fold (toutes données):")
for t in ['K', 'r', 't0']:
    r = regression[t]
    print(f"    {t:5s}: {r['verdict']:8s} med%err={r['median_pct_error']:.1f}%")

print(f"\n  Test temporel (train pré-1960 → predict post-1974):")
for t in ['K', 'r', 't0']:
    r = temporal_results[t]
    print(f"    {t:5s}: {r['verdict']:8s} med%err={r['median_pct_error']:.1f}% (n_train={r['n_train']}, n_test={r['n_test']})")

print(f"\n  Trajectoires R(t) reconstruites:")
r2s = [v['r2_trajectory'] for v in trajectory_results.values()]
print(f"    Médiane R² = {np.median(r2s):.4f}")
for m, v in sorted(trajectory_results.items(), key=lambda x: -x[1]['r2_trajectory']):
    print(f"    {m:25s} R²={v['r2_trajectory']:+.4f} K_obs={v['K_obs']:>8,} K_pred={v['K_pred']:>8,}")

# Save
output = {
    "test": "wave_boosted_model_v1",
    "date": "2026-04-06",
    "n_features": len(feature_names),
    "features": feature_names,
    "wt4_features": wt4_features,
    "correlations": corr_results,
    "regression_loo": regression,
    "temporal_test": temporal_results,
    "trajectory_reconstruction": trajectory_results,
    "graph_center": {"x": round(cx, 4), "y": round(cy, 4), "z": round(cz, 4)},
}
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\nSaved: {OUTPUT}")
print("DONE.")
