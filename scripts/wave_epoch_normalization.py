#!/usr/bin/env python3
"""
YGGDRASIL — V3 Epoch Normalization
====================================
L'onde va plus vite en 2020 qu'en 1931 parce qu'il y a plus de science.
On normalise r et t₀ par le volume de papers à l'époque de l'impact.

Hypothèse: r_normalized = r / f(papers_per_year)
Si r_normalized est STABLE → le mécanisme est le même, c'est juste la mare qui grossit.

Sky × Claude (Opus 4.6) — Session 35, 6 avril 2026
"""
import json, sys, os, math, time, sqlite3
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

REPO = "D:/ygg/yggdrasil-engine"
DB = os.path.join(REPO, "data", "wt3.db")
CHECK_PATH = os.path.join(REPO, "data", "results", "_wave_checkpoint.json")
OUTPUT = os.path.join(REPO, "data", "results", "wave_epoch_normalization.json")

print("=" * 80)
print("V3 EPOCH NORMALIZATION — r et t₀ vs volume de science")
print("=" * 80)

# Load data
ck = json.load(open(CHECK_PATH, 'r', encoding='utf-8'))
bfs = ck['phase_1']
mare = ck['phase_2']
logistic = ck['phase_3e']['fits']
METS = list(bfs.keys())

# ══════════════════════════════════════════════════════
# PART 1: Mesurer le volume de science par époque
# ══════════════════════════════════════════════════════

print("\n[1] VOLUME DE SCIENCE PAR ÉPOQUE (papers/an dans WT3)")
print("=" * 80)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Count papers per year
c.execute("SELECT year, COUNT(*) FROM papers WHERE year IS NOT NULL GROUP BY year ORDER BY year")
papers_per_year = dict(c.fetchall())

# Skip cooc count (885M rows, too slow). Use papers count only.
edges_per_year = {}

conn.close()

# For each meteorite: volume at impact year
epoch_data = {}
for m in METS:
    yr = bfs[m]['open_year']
    # Papers in impact year
    ppy = papers_per_year.get(yr, 0)
    # Papers in 5-year window around impact
    ppy_5 = sum(papers_per_year.get(y, 0) for y in range(yr-2, yr+3))
    # Cooc edges in impact year
    epy = edges_per_year.get(str(yr), 0)
    # Cumulative papers up to impact year
    cum_papers = sum(v for y, v in papers_per_year.items() if y <= yr)

    epoch_data[m] = {
        'year': yr,
        'papers_year': ppy,
        'papers_5yr': ppy_5,
        'edges_year': epy,
        'cumulative_papers': cum_papers,
        'log_papers_year': math.log1p(ppy),
        'log_cumulative': math.log1p(cum_papers),
    }

    K = logistic[m].get('K', bfs[m]['r_max'])
    r = logistic[m].get('r_growth', 1)
    t0 = logistic[m].get('t0', 1)
    print(f"  {m:25s} yr={yr} ppy={ppy:>6,} cum={cum_papers:>8,} "
          f"K={K:>8,} r={r:.2f} t0={t0:.2f}")


# ══════════════════════════════════════════════════════
# PART 2: Normaliser r et t₀
# ══════════════════════════════════════════════════════

print(f"\n[2] NORMALISATION")
print("=" * 80)

r_vals = np.array([logistic[m].get('r_growth', 1) for m in METS])
t0_vals = np.array([logistic[m].get('t0', 1) for m in METS])
K_vals = np.array([logistic[m].get('K', bfs[m]['r_max']) for m in METS])

ppy = np.array([epoch_data[m]['papers_year'] for m in METS], dtype=float)
ppy5 = np.array([epoch_data[m]['papers_5yr'] for m in METS], dtype=float)
cum = np.array([epoch_data[m]['cumulative_papers'] for m in METS], dtype=float)
log_ppy = np.log1p(ppy)
log_cum = np.log1p(cum)
years = np.array([epoch_data[m]['year'] for m in METS], dtype=float)

# Normalized versions
r_over_logppy = r_vals / (log_ppy + 1)
r_over_sqrtppy = r_vals / (np.sqrt(ppy) + 1)
t0_times_logppy = t0_vals * (log_ppy + 1)
t0_times_sqrtppy = t0_vals * (np.sqrt(ppy) + 1)

# Check correlations: does normalization REDUCE variance?
print(f"\n  Variance comparison:")
print(f"    r brut:            CV = {np.std(r_vals)/np.mean(r_vals):.4f}")
print(f"    r / log(ppy):      CV = {np.std(r_over_logppy)/np.mean(r_over_logppy):.4f}")
print(f"    r / sqrt(ppy):     CV = {np.std(r_over_sqrtppy)/np.mean(r_over_sqrtppy):.4f}")
print(f"    t0 brut:           CV = {np.std(t0_vals)/np.mean(t0_vals):.4f}")
print(f"    t0 × log(ppy):    CV = {np.std(t0_times_logppy)/np.mean(t0_times_logppy):.4f}")
print(f"    t0 × sqrt(ppy):   CV = {np.std(t0_times_sqrtppy)/np.mean(t0_times_sqrtppy):.4f}")

# Correlations: epoch features vs r, t₀, K
print(f"\n  Corrélations époque vs paramètres:")
print(f"  {'Feature':25s} {'vs r':>8s} {'p':>7s} {'vs t0':>8s} {'p':>7s} {'vs K':>8s} {'p':>7s}")
epoch_features = {
    'year': years,
    'papers_year': ppy,
    'log_papers_year': log_ppy,
    'cumulative_papers': cum,
    'log_cumulative': log_cum,
    'sqrt_papers_year': np.sqrt(ppy),
}
epoch_corrs = {}
for fn, vals in epoch_features.items():
    rr, pr = spearmanr(vals, r_vals)
    rt, pt = spearmanr(vals, t0_vals)
    rk, pk = spearmanr(vals, K_vals)
    epoch_corrs[fn] = {'r': (round(rr,4), round(pr,4)), 't0': (round(rt,4), round(pt,4)), 'K': (round(rk,4), round(pk,4))}
    flag = " <<<" if abs(rr) > 0.5 or abs(rt) > 0.5 else ""
    print(f"  {fn:25s} {rr:+8.4f} {pr:7.4f} {rt:+8.4f} {pt:7.4f} {rk:+8.4f} {pk:7.4f}{flag}")


# ══════════════════════════════════════════════════════
# PART 3: Modèle avec features époque
# ══════════════════════════════════════════════════════

print(f"\n[3] RIDGE AVEC FEATURES ÉPOQUE")
print("=" * 80)

# Add epoch features to mare features
all_features = {}
for m in METS:
    f = dict(mare[m])
    f['log_papers_year'] = epoch_data[m]['log_papers_year']
    f['log_cumulative'] = epoch_data[m]['log_cumulative']
    f['1_over_n_seeds'] = 1.0 / mare[m]['n_seeds']
    all_features[m] = f

feature_names = sorted(all_features[METS[0]].keys())
X = np.array([[all_features[m][fn] for fn in feature_names] for m in METS])

# LOO for each target
scaler = StandardScaler()
X_s = scaler.fit_transform(X)

loo_results = {}
for target_name, y in [('K', K_vals), ('r', r_vals), ('t0', t0_vals)]:
    best_alpha, best_mae = 1.0, float('inf')
    for alpha in [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]:
        errs = []
        for i in range(len(METS)):
            mask = np.ones(len(METS), dtype=bool); mask[i] = False
            pred = Ridge(alpha=alpha).fit(X_s[mask], y[mask]).predict(X_s[i:i+1])[0]
            errs.append(abs(pred - y[i]) / max(abs(y[i]), 0.01) * 100)
        if np.median(errs) < best_mae:
            best_mae = np.median(errs)
            best_alpha = alpha

    loo = []
    for i in range(len(METS)):
        mask = np.ones(len(METS), dtype=bool); mask[i] = False
        pred = float(Ridge(alpha=best_alpha).fit(X_s[mask], y[mask]).predict(X_s[i:i+1])[0])
        pct = abs(pred - float(y[i])) / max(abs(float(y[i])), 0.01) * 100
        loo.append({'met': METS[i], 'obs': round(float(y[i]),2), 'pred': round(pred,2), 'pct': round(pct,1)})

    med_pct = np.median([l['pct'] for l in loo])
    verdict = "PASS" if med_pct < 20 else "PARTIAL" if med_pct < 40 else "FAIL"

    # Feature importance
    model = Ridge(alpha=best_alpha).fit(X_s, y)
    top = sorted(zip(feature_names, model.coef_), key=lambda x: -abs(x[1]))[:5]

    print(f"\n  --- {target_name} (alpha={best_alpha}) med%err={med_pct:.1f}% {verdict} ---")
    for l in sorted(loo, key=lambda x: -x['obs']):
        print(f"    {l['met']:25s} obs={l['obs']:>10,.1f} pred={l['pred']:>10,.1f} {l['pct']:5.1f}%")
    print(f"    Top: {', '.join(f'{n}' for n,_ in top[:3])}")

    loo_results[target_name] = {'verdict': verdict, 'median_pct': round(med_pct,1), 'alpha': best_alpha, 'loo': loo}


# ══════════════════════════════════════════════════════
# PART 4: Test temporel avec features époque
# ══════════════════════════════════════════════════════

print(f"\n[4] TEST TEMPOREL AVEC FEATURES ÉPOQUE")
print("=" * 80)

train_mets = [m for m in METS if bfs[m]['open_year'] <= 1960]
test_mets = [m for m in METS if bfs[m]['open_year'] >= 1974]

X_train = np.array([[all_features[m][fn] for fn in feature_names] for m in train_mets])
X_test = np.array([[all_features[m][fn] for fn in feature_names] for m in test_mets])
sc = StandardScaler()
X_train_s = sc.fit_transform(X_train)
X_test_s = sc.transform(X_test)

print(f"  Train ({len(train_mets)}): {', '.join(train_mets)}")
print(f"  Test  ({len(test_mets)}): {', '.join(test_mets)}")

temporal = {}
for target_name, y_all in [('K', K_vals), ('r', r_vals), ('t0', t0_vals)]:
    y_train = np.array([y_all[METS.index(m)] for m in train_mets])
    y_test = np.array([y_all[METS.index(m)] for m in test_mets])
    alpha = loo_results[target_name]['alpha']
    preds = Ridge(alpha=alpha).fit(X_train_s, y_train).predict(X_test_s)

    print(f"\n  --- {target_name} ---")
    errs = []
    for i, m in enumerate(test_mets):
        obs, pred = float(y_test[i]), float(preds[i])
        pct = abs(pred-obs)/max(abs(obs),0.01)*100
        errs.append(pct)
        print(f"    {m:25s} obs={obs:>10,.2f} pred={pred:>10,.2f} {pct:5.1f}%")

    med = np.median(errs)
    verdict = "PASS" if med < 25 else "PARTIAL" if med < 50 else "FAIL"
    print(f"    med%err={med:.1f}% {verdict}")
    temporal[target_name] = {'verdict': verdict, 'median_pct': round(med,1)}


# ══════════════════════════════════════════════════════
# PART 5: Trajectoire R(t) reconstruite
# ══════════════════════════════════════════════════════

print(f"\n[5] TRAJECTOIRES R(t) RECONSTRUITES")
print("=" * 80)

trajectories = {}
for m in test_mets:
    x_m = X_test_s[test_mets.index(m):test_mets.index(m)+1]
    K_p = max(1000, float(Ridge(alpha=loo_results['K']['alpha']).fit(
        X_train_s, np.array([K_vals[METS.index(t)] for t in train_mets])).predict(x_m)[0]))
    r_p = max(0.1, float(Ridge(alpha=loo_results['r']['alpha']).fit(
        X_train_s, np.array([r_vals[METS.index(t)] for t in train_mets])).predict(x_m)[0]))
    t0_p = max(0.1, float(Ridge(alpha=loo_results['t0']['alpha']).fit(
        X_train_s, np.array([t0_vals[METS.index(t)] for t in train_mets])).predict(x_m)[0]))

    wd = bfs[m]['wave_data']
    t_arr = np.array([w['t'] for w in wd], dtype=float)
    r_obs = np.array([w['total_touched'] for w in wd], dtype=float)
    r_pred = np.maximum(0, K_p / (1 + np.exp(-r_p * (t_arr - t0_p))))

    ss_res = np.sum((r_obs - r_pred)**2)
    ss_tot = np.sum((r_obs - r_obs.mean())**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0

    trajectories[m] = {'K': round(K_p), 'r': round(r_p,3), 't0': round(t0_p,3),
                        'K_obs': bfs[m]['r_max'], 'r2': round(r2,4)}
    print(f"  {m:25s} K={K_p:>8,.0f} r={r_p:.2f} t0={t0_p:.2f} R²={r2:+.4f} (K_obs={bfs[m]['r_max']:>8,})")

r2s = [v['r2'] for v in trajectories.values()]
print(f"\n  Médiane R² = {np.median(r2s):.4f}")


# ══════════════════════════════════════════════════════
# VERDICT
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("VERDICT — NORMALISATION ÉPOQUE")
print(f"{'='*80}")

print(f"\n  LOO 13-fold:")
for t in ['K', 'r', 't0']:
    print(f"    {t:5s}: {loo_results[t]['verdict']:8s} {loo_results[t]['median_pct']:.1f}%")

print(f"\n  Test temporel (pré-1960 → post-1974):")
for t in ['K', 'r', 't0']:
    print(f"    {t:5s}: {temporal[t]['verdict']:8s} {temporal[t]['median_pct']:.1f}%")

print(f"\n  Trajectoires: médiane R² = {np.median(r2s):.4f}")

# Compare with previous (no epoch)
print(f"\n  Comparaison AVANT/APRÈS normalisation époque:")
print(f"  {'':20s} {'AVANT':>10s} {'APRÈS':>10s} {'Amélioration':>15s}")
prev_temporal = {'K': 15.9, 'r': 77.0, 't0': 142.4}
for t in ['K', 'r', 't0']:
    before = prev_temporal[t]
    after = temporal[t]['median_pct']
    diff = before - after
    better = "OUI" if diff > 0 else "NON"
    print(f"  {t:20s} {before:10.1f}% {after:10.1f}% {diff:+10.1f}% ({better})")

# Save
output = {
    "test": "wave_epoch_normalization_v1",
    "date": "2026-04-06",
    "epoch_data": epoch_data,
    "epoch_correlations": epoch_corrs,
    "loo_results": loo_results,
    "temporal_results": temporal,
    "trajectories": trajectories,
    "comparison_before_after": {
        t: {"before": prev_temporal[t], "after": temporal[t]['median_pct']}
        for t in ['K', 'r', 't0']
    },
}
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\nSaved: {OUTPUT}")
print("DONE.")
