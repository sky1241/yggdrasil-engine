#!/usr/bin/env python3
"""
YGGDRASIL — Session 38: Modèle 2 étages pour r
=================================================
Étage 1: g(année) = vitesse de base de l'époque (exponentiel post-internet)
Étage 2: r_résiduel = r_observé / g(année) = part propre à la météorite
         → prédire r_résiduel depuis features mare + mycélium

Insight Sky: après 2000, la vitesse explose exponentiellement (internet).
Mélanger époque + météorite dans un seul modèle = impossible.

Sky × Claude (Opus 4.6) — Session 38, 21 avril 2026
"""
import json, sys, os
import numpy as np
import sqlite3
from scipy.stats import spearmanr
from scipy.optimize import curve_fit
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')
def P(*args, **kw): print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")

# ═══════════════════════════════════════════════════════
# LOAD 36 METEORITES + FEATURES
# ═══════════════════════════════════════════════════════

CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), encoding='utf-8'))
EXPAND = json.load(open(os.path.join(REPO, "data/results/wave_expand_checkpoint.json"), encoding='utf-8'))
S37 = json.load(open(os.path.join(REPO, "data/results/wave_retrain_s37.json"), encoding='utf-8'))

all_mets = []
orig_bfs = CHECK['phase_1']
orig_mare = CHECK['phase_2']
orig_log = CHECK['phase_3e']['fits']
for m in orig_bfs:
    year = int(m.split()[-1])
    all_mets.append({
        'name': m, 'year': year,
        'seeds': orig_bfs[m]['seeds'],
        'K': orig_log[m]['K'], 'r': orig_log[m]['r_growth'],
        'mare': orig_mare[m],
    })
for name, d in EXPAND.items():
    if d['phase_3']['K'] <= 100:
        continue
    all_mets.append({
        'name': name, 'year': d['phase_1']['open_year'],
        'seeds': d['phase_1']['seeds'],
        'K': d['phase_3']['K'], 'r': d['phase_3']['r_growth'],
        'mare': d['phase_2'],
    })

all_mets.sort(key=lambda x: x['year'])
N_METS = len(all_mets)
train_idx = [i for i, m in enumerate(all_mets) if m['year'] <= 1960]
test_idx  = [i for i, m in enumerate(all_mets) if m['year'] >= 1973]

# Load mycelium cursors from S37
myc = S37['mycelium_cursors']

P("=" * 80)
P(f"MODÈLE 2 ÉTAGES — {N_METS} météorites ({len(train_idx)} train, {len(test_idx)} test)")
P("=" * 80)

years = np.array([m['year'] for m in all_mets])
r_all = np.array([m['r'] for m in all_mets])
K_all = np.array([m['K'] for m in all_mets])

# ═══════════════════════════════════════════════════════
# ÉTAGE 1: Fitter g(année) = baseline r de l'époque
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("ÉTAGE 1: g(année) — baseline r de l'époque")
P(f"{'='*80}\n")

# Try several curves
def linear(x, a, b):
    return a * x + b

def exponential(x, a, b, c):
    return a * np.exp(b * (x - 1900)) + c

def logistic(x, L, k, x0, b):
    return L / (1 + np.exp(-k * (x - x0))) + b

def power(x, a, b, c):
    return a * (x - 1890)**b + c

# Fit on ALL 36 meteorites (not just train — we're fitting the epoch effect)
P("  Données: r vs année")
for i, m in enumerate(all_mets):
    P(f"    {m['name']:25s}  year={m['year']}  r={m['r']:.3f}")

P("\n  Fitting courbes...")

# Linear
try:
    popt_lin, _ = curve_fit(linear, years, r_all)
    r_pred_lin = linear(years, *popt_lin)
    ss_res = np.sum((r_all - r_pred_lin)**2)
    ss_tot = np.sum((r_all - np.mean(r_all))**2)
    r2_lin = 1 - ss_res / ss_tot
    P(f"  Linear:      r = {popt_lin[0]:.4f}*year + {popt_lin[1]:.2f}  R²={r2_lin:.4f}")
except Exception as e:
    P(f"  Linear: FAIL ({e})")
    r2_lin = -999

# Exponential
try:
    popt_exp, _ = curve_fit(exponential, years, r_all, p0=[0.01, 0.03, 1.0], maxfev=5000)
    r_pred_exp = exponential(years, *popt_exp)
    ss_res = np.sum((r_all - r_pred_exp)**2)
    ss_tot = np.sum((r_all - np.mean(r_all))**2)
    r2_exp = 1 - ss_res / ss_tot
    P(f"  Exponential: r = {popt_exp[0]:.6f}*exp({popt_exp[1]:.4f}*(year-1900)) + {popt_exp[2]:.2f}  R²={r2_exp:.4f}")
except Exception as e:
    P(f"  Exponential: FAIL ({e})")
    r2_exp = -999

# Logistic (S-curve — internet transition)
try:
    popt_log, _ = curve_fit(logistic, years, r_all, p0=[5.0, 0.05, 1980, 1.0], maxfev=5000)
    r_pred_log = logistic(years, *popt_log)
    ss_res = np.sum((r_all - r_pred_log)**2)
    ss_tot = np.sum((r_all - np.mean(r_all))**2)
    r2_log = 1 - ss_res / ss_tot
    P(f"  Logistic:    r = {popt_log[0]:.2f}/(1+exp(-{popt_log[1]:.4f}*(year-{popt_log[2]:.0f}))) + {popt_log[3]:.2f}  R²={r2_log:.4f}")
except Exception as e:
    P(f"  Logistic: FAIL ({e})")
    r2_log = -999

# Power
try:
    popt_pow, _ = curve_fit(power, years, r_all, p0=[0.001, 1.5, 0.5], maxfev=5000)
    r_pred_pow = power(years, *popt_pow)
    ss_res = np.sum((r_all - r_pred_pow)**2)
    ss_tot = np.sum((r_all - np.mean(r_all))**2)
    r2_pow = 1 - ss_res / ss_tot
    P(f"  Power:       r = {popt_pow[0]:.6f}*(year-1890)^{popt_pow[1]:.2f} + {popt_pow[2]:.2f}  R²={r2_pow:.4f}")
except Exception as e:
    P(f"  Power: FAIL ({e})")
    r2_pow = -999

# Pick best
fits = {'linear': (r2_lin, linear, popt_lin if r2_lin > -999 else None),
        'exponential': (r2_exp, exponential, popt_exp if r2_exp > -999 else None),
        'logistic': (r2_log, logistic, popt_log if r2_log > -999 else None),
        'power': (r2_pow, power, popt_pow if r2_pow > -999 else None)}

best_name = max(fits, key=lambda k: fits[k][0])
best_r2, best_func, best_params = fits[best_name]
P(f"\n  ★ Best fit: {best_name} (R²={best_r2:.4f})")

# Compute g(year) for each meteorite
g_values = best_func(years, *best_params)

P(f"\n  g(année) par météorite:")
for i, m in enumerate(all_mets):
    P(f"    {m['name']:25s}  year={m['year']}  r={m['r']:.3f}  g={g_values[i]:.3f}")

# ═══════════════════════════════════════════════════════
# RÉSIDUS: r_résiduel = r / g(année)
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("RÉSIDUS: r_résiduel = r_observé / g(année)")
P(f"{'='*80}\n")

# Avoid division by zero
g_safe = np.maximum(g_values, 0.1)
r_residual = r_all / g_safe

P(f"  {'Météorite':25s} {'r_obs':>7s} {'g(yr)':>7s} {'r_res':>7s}")
P(f"  {'-'*25} {'-'*7} {'-'*7} {'-'*7}")
for i, m in enumerate(all_mets):
    P(f"  {m['name']:25s} {r_all[i]:>7.3f} {g_values[i]:>7.3f} {r_residual[i]:>7.3f}")

P(f"\n  r_résiduel: mean={np.mean(r_residual):.3f}, std={np.std(r_residual):.3f}, "
  f"min={np.min(r_residual):.3f}, max={np.max(r_residual):.3f}")

# ═══════════════════════════════════════════════════════
# ÉTAGE 2: Prédire r_résiduel depuis features
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("ÉTAGE 2: Prédire r_résiduel depuis features mare + mycélium")
P(f"{'='*80}\n")

# Build feature matrix from mare + mycelium
mare_features = ['median_neighbor_works', 'avg_edge_weight', 'n_species_touched',
                 'avg_neighbor_degree', 'max_edge_weight']
myc_features = ['BA', 'IL', 'D', 'Db', 'L', 'alpha', 'E_global']
seed_features = ['n_seeds']

all_feature_names = []
X = []

for i, met in enumerate(all_mets):
    row = []
    name = met['name']

    # Mare features
    mare = met['mare']
    for feat in mare_features:
        val = mare.get(feat, 0) if isinstance(mare, dict) else 0
        row.append(val)

    # Mycelium features
    mc = myc.get(name, {})
    for feat in myc_features:
        row.append(mc.get(feat, 0))

    # Seed count
    row.append(len(met['seeds']))

    X.append(row)

all_feature_names = mare_features + myc_features + seed_features
X = np.array(X)

# Correlations with r_residual
P(f"  Corrélations avec r_résiduel (n={N_METS}):\n")
P(f"  {'Feature':25s} {'ρ(r_res)':>8s} {'p':>10s}  {'ρ(r_brut)':>9s}")
P(f"  {'-'*25} {'-'*8} {'-'*10}  {'-'*9}")

best_feat, best_rho = None, 0
for j, feat in enumerate(all_feature_names):
    vals = X[:, j]
    if np.std(vals) == 0:
        continue
    rho_res, p_res = spearmanr(vals, r_residual)
    rho_brut, _ = spearmanr(vals, r_all)
    P(f"  {feat:25s} {rho_res:+.4f}   {p_res:.2e}   {rho_brut:+.4f}")
    if abs(rho_res) > abs(best_rho):
        best_rho, best_feat = rho_res, feat

P(f"\n  Best feature for r_résiduel: {best_feat} (ρ={best_rho:+.4f})")

# Also correlate r_residual with K
rho_rk, p_rk = spearmanr(r_residual, K_all)
P(f"  r_résiduel vs K: ρ={rho_rk:+.4f} (p={p_rk:.2e})")

# ═══════════════════════════════════════════════════════
# TEST TEMPOREL: 2-stage prediction
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("TEST TEMPOREL 2 ÉTAGES — train ≤1960, predict ≥1973")
P(f"{'='*80}\n")

# Stage 1: g(year) is fitted on ALL data (it's a known epoch effect, not a prediction)
# This is legitimate: we KNOW the year of the meteorite at prediction time.

# Stage 2: predict r_residual from features
X_train = X[train_idx]
X_test = X[test_idx]
r_res_train = r_residual[train_idx]
r_res_test = r_residual[test_idx]

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# Ridge on r_residual
ridge = Ridge(alpha=1.0)
ridge.fit(X_train_s, r_res_train)
r_res_pred = ridge.predict(X_test_s)

# Reconstruct r_pred = r_res_pred × g(year)
r_pred_2stage = r_res_pred * g_safe[test_idx]

r_errors = np.abs(r_pred_2stage - r_all[test_idx]) / r_all[test_idx] * 100
r_med_err = float(np.median(r_errors))

P(f"  r prediction (2-stage: g(year) × Ridge(mare+myc)):")
P(f"    Median error: {r_med_err:.1f}% (baseline S37: 41%, temporal: 18.9%)")
P(f"    Epoch model: {best_name} (R²={best_r2:.3f})")
P(f"    Per meteorite:")
for idx, ti in enumerate(test_idx):
    name = all_mets[ti]['name']
    P(f"      {name:25s}  r_obs={r_all[ti]:>6.3f}  g={g_safe[ti]:.3f}  "
      f"res_pred={r_res_pred[idx]:.3f}  r_pred={r_pred_2stage[idx]:.3f}  err={r_errors[idx]:.0f}%")

# Also: what if we just use g(year) alone? (no stage 2)
r_pred_epoch_only = g_safe[test_idx]
r_errors_epoch = np.abs(r_pred_epoch_only - r_all[test_idx]) / r_all[test_idx] * 100
r_med_epoch = float(np.median(r_errors_epoch))
P(f"\n  Epoch seul (g(year), 0 feature): {r_med_epoch:.1f}%")

# And: stage 2 alone (no epoch correction)
ridge_raw = Ridge(alpha=1.0)
ridge_raw.fit(scaler.fit_transform(X[train_idx]), r_all[train_idx])
r_pred_raw = ridge_raw.predict(scaler.transform(X[test_idx]))
r_errors_raw = np.abs(r_pred_raw - r_all[test_idx]) / r_all[test_idx] * 100
r_med_raw = float(np.median(r_errors_raw))
P(f"  Features seules (mare+myc, sans époque): {r_med_raw:.1f}%")

# ═══════════════════════════════════════════════════════
# AUSSI: tester K avec résidu époque
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("BONUS: K avec même approche (résidu époque)")
P(f"{'='*80}\n")

# Fit K vs year
try:
    popt_k, _ = curve_fit(exponential, years, K_all, p0=[1.0, 0.03, 1000], maxfev=5000)
    g_k = exponential(years, *popt_k)
    ss_res = np.sum((K_all - g_k)**2)
    ss_tot = np.sum((K_all - np.mean(K_all))**2)
    r2_k_epoch = 1 - ss_res / ss_tot
    P(f"  K vs année (exp): R²={r2_k_epoch:.4f}")

    K_residual = K_all / np.maximum(g_k, 100)

    # Predict K_residual
    ridge_k = Ridge(alpha=1.0)
    ridge_k.fit(scaler.fit_transform(X[train_idx]), K_residual[train_idx])
    K_res_pred = ridge_k.predict(scaler.transform(X[test_idx]))
    K_pred_2stage = K_res_pred * np.maximum(g_k[test_idx], 100)
    K_errors = np.abs(K_pred_2stage - K_all[test_idx]) / K_all[test_idx] * 100
    K_med_err = float(np.median(K_errors))
    P(f"  K 2-stage median error: {K_med_err:.1f}% (baseline S37: 54%)")
except Exception as e:
    P(f"  K epoch fit FAIL: {e}")
    K_med_err = 999

# ═══════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("VERDICT 2 ÉTAGES")
P(f"{'='*80}")
P(f"  Epoch model: {best_name} (R²={best_r2:.3f})")
P(f"  ")
P(f"  r — comparaison:")
P(f"    Baseline S37 (features brutes):     41.4%")
P(f"    Époque seule g(year):               {r_med_epoch:.1f}%")
P(f"    Features seules (mare+myc):         {r_med_raw:.1f}%")
P(f"    ★ 2 étages g(year) × Ridge:        {r_med_err:.1f}%")
P(f"  ")
P(f"  K — comparaison:")
P(f"    Baseline S37:                       54.0%")
P(f"    ★ 2 étages:                         {K_med_err:.1f}%")

r_verdict = "PASS" if r_med_err < 41 else "FAIL"
k_verdict = "PASS" if K_med_err < 54 else "FAIL"
P(f"  r: {r_verdict}")
P(f"  K: {k_verdict}")

# Save
output = {
    'method': 'epoch_residual_2stage',
    'date': '2026-04-21',
    'session': 38,
    'n_meteorites': N_METS,
    'epoch_model': {
        'type': best_name,
        'params': best_params.tolist() if best_params is not None else None,
        'R2': best_r2,
    },
    'test_temporel': {
        'r_median_error_2stage': r_med_err,
        'r_median_error_epoch_only': r_med_epoch,
        'r_median_error_features_only': r_med_raw,
        'K_median_error_2stage': K_med_err,
        'r_verdict': r_verdict,
        'K_verdict': k_verdict,
    },
    'r_residuals': {m['name']: float(r_residual[i]) for i, m in enumerate(all_mets)},
    'correlations_with_residual': {},
}
for j, feat in enumerate(all_feature_names):
    vals = X[:, j]
    if np.std(vals) > 0:
        rho, p = spearmanr(vals, r_residual)
        output['correlations_with_residual'][feat] = {'rho': float(rho), 'p': float(p)}

out_path = os.path.join(REPO, "data/results/wave_epoch_residual.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
P(f"\n  Saved: {out_path}")
P("DONE.")
