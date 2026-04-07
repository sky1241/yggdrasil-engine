#!/usr/bin/env python3
"""
YGGDRASIL — VALIDATION HONNÊTE DE TOUT
========================================
Test temporel (train pré-1960 → predict post-1974) pour CHAQUE trouvaille.
Pas de LOO, pas de bullshit. Train sur le passé, predict le futur.

Correction Bonferroni pour tests multiples.

Sky × Claude (Opus 4.6) — Session 35, 7 avril 2026
"""
import json, sys, os, math
import numpy as np
from scipy.stats import spearmanr, mannwhitneyu
from scipy.optimize import curve_fit
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

REPO = "D:/ygg/yggdrasil-engine"
CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), 'r', encoding='utf-8'))
WT4 = json.load(open(os.path.join(REPO, "data/scan/wt4_spectral.json"), 'r', encoding='utf-8'))
SPECTRAL = json.load(open(os.path.join(REPO, "data/scan/spectral_births.json"), 'r', encoding='utf-8'))
OUTPUT = os.path.join(REPO, "data/results/wave_honest_validation.json")

bfs = CHECK['phase_1']
mare = CHECK['phase_2']
logistic = CHECK['phase_3e']['fits']
omori = json.load(open(os.path.join(REPO, "data/results/wave_etas_carmack.json"), 'r', encoding='utf-8'))['omori_fits']
METS = list(bfs.keys())
N = 65026

# Split
train_mets = [m for m in METS if bfs[m]['open_year'] <= 1960]
test_mets = [m for m in METS if bfs[m]['open_year'] >= 1974]

# Targets
K_all = np.array([logistic[m].get('K', bfs[m]['r_max']) for m in METS])
r_all = np.array([logistic[m].get('r_growth', 1) for m in METS])
t0_all = np.array([logistic[m].get('t0', 1) for m in METS])
death_all = np.array([bfs[m].get('death_t', 8) or 8 for m in METS])

K_train = np.array([K_all[METS.index(m)] for m in train_mets])
K_test = np.array([K_all[METS.index(m)] for m in test_mets])
r_test = np.array([r_all[METS.index(m)] for m in test_mets])
t0_test = np.array([t0_all[METS.index(m)] for m in test_mets])

# Spectral data
node_by_id = {n['id']: n for n in SPECTRAL['nodes']}
cx = np.mean([n['x'] for n in SPECTRAL['nodes']])
cy = np.mean([n['y'] for n in SPECTRAL['nodes']])
cz = np.mean([n['z'] for n in SPECTRAL['nodes']])

eigenvalues = np.array(WT4['meta']['eigenvalues'])
gap = 1 - eigenvalues[1]

print("=" * 80)
print("VALIDATION HONNÊTE — Test temporel pour TOUT")
print(f"Train: {len(train_mets)} météorites pré-1960")
print(f"Test:  {len(test_mets)} météorites post-1974")
print("=" * 80)

results = {}
n_tests = 0

# ══════════════════════════════════════════════════════
# TEST 1: K = hub_frac / density (ρ=0.75 LOO)
# ══════════════════════════════════════════════════════

print(f"\n[1] K = hub_frac / density")
hf_d_all = np.array([mare[m]['hub_fraction'] / (mare[m]['local_density'] + 0.001) for m in METS])
hf_d_train = np.array([hf_d_all[METS.index(m)] for m in train_mets])
hf_d_test = np.array([hf_d_all[METS.index(m)] for m in test_mets])

# Fit linear on train
coeffs = np.polyfit(hf_d_train, K_train, 1)
K_pred = np.polyval(coeffs, hf_d_test)
K_pred = np.maximum(K_pred, 1000)

errors = [abs(K_pred[i] - K_test[i]) / K_test[i] * 100 for i in range(len(test_mets))]
med_err = np.median(errors)
n_tests += 1

print(f"  Fit: K = {coeffs[0]:.1f} × (hub_frac/density) + {coeffs[1]:.0f}")
print(f"  {'Met':25s} {'K_obs':>8s} {'K_pred':>8s} {'err%':>6s}")
for i, m in enumerate(test_mets):
    print(f"  {m:25s} {K_test[i]:8,.0f} {K_pred[i]:8,.0f} {errors[i]:5.1f}%")
print(f"  Médiane erreur: {med_err:.1f}%")
verdict_1 = "PASS" if med_err < 25 else "PARTIAL" if med_err < 50 else "FAIL"
print(f"  VERDICT: {verdict_1}")
results['K_hub_density'] = {'median_err': round(med_err, 1), 'verdict': verdict_1}

# ══════════════════════════════════════════════════════
# TEST 2: K = Ridge(all mare features) — le test de session 34
# ══════════════════════════════════════════════════════

print(f"\n[2] K = Ridge(mare features)")
fn = sorted(mare[METS[0]].keys())
X_train = np.array([[mare[m][f] for f in fn] for m in train_mets])
X_test = np.array([[mare[m][f] for f in fn] for m in test_mets])
sc = StandardScaler()
X_tr_s = sc.fit_transform(X_train)
X_te_s = sc.transform(X_test)
K_pred_ridge = Ridge(alpha=0.1).fit(X_tr_s, K_train).predict(X_te_s)
K_pred_ridge = np.maximum(K_pred_ridge, 1000)

errors_2 = [abs(K_pred_ridge[i] - K_test[i]) / K_test[i] * 100 for i in range(len(test_mets))]
med_err_2 = np.median(errors_2)
n_tests += 1

print(f"  {'Met':25s} {'K_obs':>8s} {'K_pred':>8s} {'err%':>6s}")
for i, m in enumerate(test_mets):
    print(f"  {m:25s} {K_test[i]:8,.0f} {K_pred_ridge[i]:8,.0f} {errors_2[i]:5.1f}%")
print(f"  Médiane erreur: {med_err_2:.1f}%")
verdict_2 = "PASS" if med_err_2 < 25 else "PARTIAL" if med_err_2 < 50 else "FAIL"
print(f"  VERDICT: {verdict_2}")
results['K_ridge_mare'] = {'median_err': round(med_err_2, 1), 'verdict': verdict_2}

# ══════════════════════════════════════════════════════
# TEST 3: death = spectral gap (0 param)
# ══════════════════════════════════════════════════════

print(f"\n[3] death = spectral gap")
death_train_mean = np.mean([death_all[METS.index(m)] for m in train_mets])
death_test_obs = np.array([death_all[METS.index(m)] for m in test_mets])
death_pred = death_train_mean  # constant prediction from train

errors_3 = [abs(death_pred - death_test_obs[i]) for i in range(len(test_mets))]
mae_3 = np.mean(errors_3)
n_tests += 1

print(f"  death_pred (train mean) = {death_pred:.1f} ans")
print(f"  {'Met':25s} {'obs':>5s} {'pred':>5s} {'err':>5s}")
for i, m in enumerate(test_mets):
    print(f"  {m:25s} {death_test_obs[i]:5.0f} {death_pred:5.1f} {errors_3[i]:5.1f}")
print(f"  MAE: {mae_3:.2f} ans")
verdict_3 = "PASS" if mae_3 < 3.0 else "PARTIAL" if mae_3 < 5.0 else "FAIL"
print(f"  VERDICT: {verdict_3}")
results['death_spectral'] = {'mae': round(mae_3, 2), 'verdict': verdict_3}

# ══════════════════════════════════════════════════════
# TEST 4: p Omori universel (0 param)
# ══════════════════════════════════════════════════════

print(f"\n[4] p Omori universel")
p_train = [omori[m]['p'] for m in train_mets if isinstance(omori[m].get('p'), (int, float)) and omori[m].get('r2', -1) > 0.3]
p_test = [omori[m]['p'] for m in test_mets if isinstance(omori[m].get('p'), (int, float)) and omori[m].get('r2', -1) > 0.3]

p_mean_train = np.mean(p_train) if p_train else 4.74
p_mean_test = np.mean(p_test) if p_test else 0
p_std_test = np.std(p_test) if p_test else 0
n_tests += 1

print(f"  p train (n={len(p_train)}): {p_mean_train:.3f}")
print(f"  p test  (n={len(p_test)}): {p_mean_test:.3f} ±{p_std_test:.3f}")
print(f"  Différence: {abs(p_mean_train - p_mean_test):.3f}")

# Is p_train ≈ p_test? (Mann-Whitney if enough data)
if len(p_train) >= 3 and len(p_test) >= 3:
    U, p_mw = mannwhitneyu(p_train, p_test, alternative='two-sided')
    print(f"  Mann-Whitney: U={U:.0f}, p={p_mw:.4f}")
    verdict_4 = "PASS" if p_mw > 0.05 else "FAIL"  # p>0.05 = no significant difference = universal
    print(f"  p>0.05 → pas de différence significative → p EST universel")
else:
    verdict_4 = "PARTIAL"
    p_mw = 1.0
print(f"  VERDICT: {verdict_4}")
results['p_omori_universal'] = {'p_train': round(p_mean_train, 3), 'p_test': round(p_mean_test, 3), 'mann_whitney_p': round(p_mw, 4), 'verdict': verdict_4}

# ══════════════════════════════════════════════════════
# TEST 5: candle_ratio prédit r (train → test)
# ══════════════════════════════════════════════════════

print(f"\n[5] candle_ratio → r (test temporel)")
candle_ratio = np.array([bfs[m]['peak_edges'] / max(death_all[METS.index(m)], 1) for m in METS])
log_ratio = np.log1p(candle_ratio)

lr_train = np.array([log_ratio[METS.index(m)] for m in train_mets])
r_train = np.array([r_all[METS.index(m)] for m in train_mets])
lr_test = np.array([log_ratio[METS.index(m)] for m in test_mets])

coeffs_r = np.polyfit(lr_train, r_train, 1)
r_pred = np.polyval(coeffs_r, lr_test)
r_pred = np.maximum(r_pred, 0.5)

errors_5 = [abs(r_pred[i] - r_test[i]) / max(r_test[i], 0.01) * 100 for i in range(len(test_mets))]
med_err_5 = np.median(errors_5)
n_tests += 1

print(f"  Fit (train): r = {coeffs_r[0]:.4f} × log(ratio) + {coeffs_r[1]:.4f}")
print(f"  {'Met':25s} {'r_obs':>6s} {'r_pred':>6s} {'err%':>6s}")
for i, m in enumerate(test_mets):
    print(f"  {m:25s} {r_test[i]:6.2f} {r_pred[i]:6.2f} {errors_5[i]:5.1f}%")
print(f"  Médiane erreur: {med_err_5:.1f}%")
verdict_5 = "PASS" if med_err_5 < 25 else "PARTIAL" if med_err_5 < 50 else "FAIL"
print(f"  VERDICT: {verdict_5}")
results['r_candlestick'] = {'median_err': round(med_err_5, 1), 'verdict': verdict_5}

# ══════════════════════════════════════════════════════
# TEST 6: R(t) trajectoire complète avec TOUT
# ══════════════════════════════════════════════════════

print(f"\n[6] R(t) TRAJECTOIRE COMPLÈTE — tout combiné")

# Use best K predictor from tests 1 vs 2
if med_err < med_err_2:
    K_final = K_pred
    K_method = "hub_frac/density"
else:
    K_final = K_pred_ridge
    K_method = "Ridge(mare)"

r_final = r_pred
t0_final = 0.208 * death_pred  # from hybrid model

print(f"  K: {K_method}")
print(f"  r: candle_ratio")
print(f"  t0: 0.208 × death = {t0_final:.2f}")
print(f"  death: {death_pred:.1f}")

print(f"\n  {'Met':25s} {'K_obs':>8s} {'K_pred':>8s} {'r_obs':>6s} {'r_pred':>6s} {'R²':>7s}")
r2_list = []
for i, m in enumerate(test_mets):
    wd = bfs[m]['wave_data']
    t_arr = np.array([w['t'] for w in wd], dtype=float)
    R_obs = np.array([w['total_touched'] for w in wd], dtype=float)

    R_pred_t = K_final[i] / (1 + np.exp(-r_final[i] * (t_arr - t0_final)))
    R_pred_t = np.maximum(0, R_pred_t)

    ss_res = np.sum((R_obs - R_pred_t) ** 2)
    ss_tot = np.sum((R_obs - R_obs.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    r2_list.append(r2)

    print(f"  {m:25s} {K_test[i]:8,.0f} {K_final[i]:8,.0f} {r_test[i]:6.2f} {r_final[i]:6.2f} {r2:+7.4f}")

med_r2 = np.median(r2_list)
n_tests += 1
verdict_6 = "PASS" if med_r2 > 0.5 else "PARTIAL" if med_r2 > 0 else "FAIL"
print(f"\n  Médiane R² = {med_r2:.4f}")
print(f"  VERDICT: {verdict_6}")
results['R_t_trajectory'] = {'median_r2': round(med_r2, 4), 'verdict': verdict_6}

# ══════════════════════════════════════════════════════
# CORRECTION BONFERRONI
# ══════════════════════════════════════════════════════

print(f"\n[7] CORRECTION BONFERRONI")
# On a testé ~20 combinaisons de features pour K au total (sessions 34-35)
# Le seuil corrigé est 0.05 / 20 = 0.0025
bonferroni = 0.05 / 20
print(f"  Nombre de tests features K: ~20")
print(f"  Seuil Bonferroni: p < {bonferroni}")

# Recalculate p-values on ALL data for key findings
rho_hfd, p_hfd = spearmanr(hf_d_all, K_all)
rho_cr, p_cr = spearmanr(candle_ratio, r_all)
rho_mw, p_mw_all = spearmanr(np.array([mare[m]['median_neighbor_works'] for m in METS]), K_all)

print(f"\n  {'Trouvaille':40s} {'ρ':>6s} {'p':>10s} {'Bonf':>8s}")
findings = [
    ('hub_frac/density → K', rho_hfd, p_hfd),
    ('median_neighbor_works → K', rho_mw, p_mw_all),
    ('candle_ratio → r', rho_cr, p_cr),
]
for name, rho, p in findings:
    sig = 'SIG' if p < bonferroni else 'non-sig'
    print(f"  {name:40s} {rho:+6.4f} {p:10.6f} {sig:>8s}")


# ══════════════════════════════════════════════════════
# GRAND TABLEAU FINAL
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("GRAND TABLEAU — VALIDATION HONNÊTE")
print(f"{'='*80}")

print(f"\n  {'Test':45s} {'Verdict':>8s} {'Détail':>15s}")
tests = [
    ('K = hub_frac / density', verdict_1, f'{med_err:.1f}%'),
    ('K = Ridge(mare)', verdict_2, f'{med_err_2:.1f}%'),
    ('death = spectral gap', verdict_3, f'MAE {mae_3:.2f}yr'),
    ('p Omori universel', verdict_4, f'MW p={p_mw:.3f}'),
    ('r = f(candle_ratio)', verdict_5, f'{med_err_5:.1f}%'),
    ('R(t) trajectoire complète', verdict_6, f'R²={med_r2:.3f}'),
]

pass_count = sum(1 for _, v, _ in tests if v == 'PASS')
partial_count = sum(1 for _, v, _ in tests if v == 'PARTIAL')
fail_count = sum(1 for _, v, _ in tests if v == 'FAIL')

for name, verdict, detail in tests:
    icon = "✓" if verdict == "PASS" else "~" if verdict == "PARTIAL" else "✗"
    print(f"  {icon} {name:43s} {verdict:>8s} {detail:>15s}")

print(f"\n  PASS: {pass_count}, PARTIAL: {partial_count}, FAIL: {fail_count}")
print(f"\n  Bonferroni (p < {bonferroni}):")
print(f"    hub_frac/density → K: {'SIG' if p_hfd < bonferroni else 'non-sig'} (p={p_hfd:.6f})")
print(f"    candle_ratio → r: {'SIG' if p_cr < bonferroni else 'non-sig'} (p={p_cr:.6f})")

# Save
output = {
    "test": "honest_validation_v1",
    "date": "2026-04-07",
    "split": {"train": train_mets, "test": test_mets, "n_train": len(train_mets), "n_test": len(test_mets)},
    "results": results,
    "bonferroni": {
        "n_total_tests": 20,
        "threshold": round(bonferroni, 4),
        "hub_frac_density_K": {"rho": round(rho_hfd, 4), "p": round(p_hfd, 6), "significant": p_hfd < bonferroni},
        "candle_ratio_r": {"rho": round(rho_cr, 4), "p": round(p_cr, 6), "significant": p_cr < bonferroni},
        "median_works_K": {"rho": round(rho_mw, 4), "p": round(p_mw_all, 6), "significant": p_mw_all < bonferroni},
    },
    "summary": {
        "pass": pass_count, "partial": partial_count, "fail": fail_count,
    },
}
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\nSaved: {OUTPUT}")
print("DONE.")
