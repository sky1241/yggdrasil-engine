#!/usr/bin/env python3
"""
YGGDRASIL — CARMACK MOVE: ETAS × Knowledge Graph
===================================================
Appliquer le modèle ETAS (Epidemic-Type Aftershock Sequence) de la
sismologie aux ondes de propagation dans le graphe de connaissances.

ETAS dit: après un séisme principal, le taux de répliques suit:
  lambda(t) = mu + K * sum_i (t - t_i + c)^(-p)

En simplifié (1 événement principal, pas de cascades):
  R(t) = K / (t + c)^p          [Omori-Utsu law]
  mu(t) = A / (t + c)^p         [branching ratio decay]

Le branching ratio n = K * integral(g(t)) = K * c^(1-p) / (p-1)
  Si n < 1: sous-critique (onde meurt)
  Si n > 1: supercritique (onde explose)
  Si n ≈ 1: critique (SOC)

Sources:
  Ogata 1988, JASA — ETAS model original
  Omori 1894 — loi de décroissance des répliques
  Utsu 1961 — modification de la loi d'Omori
  Saichev & Sornette 2005, Phys. Rev. E 71, 016608

Carmack move: seismology × epidemic = cooc 0, score 321.6
Ce modèle n'a JAMAIS été appliqué aux graphes de connaissances.

Sky × Claude (Opus 4.6) — Session 35, 7 avril 2026
"""
import json, sys, os, math, time
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

REPO = "D:/ygg/yggdrasil-engine"
CHECK_PATH = os.path.join(REPO, "data", "results", "_wave_checkpoint.json")
OUTPUT = os.path.join(REPO, "data", "results", "wave_etas_carmack.json")

print("=" * 80)
print("CARMACK MOVE: ETAS × KNOWLEDGE GRAPH")
print("seismology × epidemic = cooc 0, score 321.6")
print("=" * 80)

# Load data
ck = json.load(open(CHECK_PATH, 'r', encoding='utf-8'))
bfs = ck['phase_1']
mare = ck['phase_2']
logistic = ck['phase_3e']['fits']
METS = list(bfs.keys())


# ══════════════════════════════════════════════════════
# ETAS MODELS
# ══════════════════════════════════════════════════════

def omori_utsu(t, K, c, p):
    """Omori-Utsu law: rate of aftershocks.
    R(t) = K / (t + c)^p
    Source: Utsu 1961, modified Omori 1894.
    """
    return K / np.power(t + c, p)


def etas_cumulative(t, K, c, p):
    """Cumulative ETAS: total aftershocks up to time t.
    N(t) = K * c^(1-p) / (p-1) * [1 - (1 + t/c)^(1-p)]  for p > 1
    N(t) = K * ln(1 + t/c)                                 for p = 1
    Source: Ogata 1988.
    """
    if abs(p - 1.0) < 0.01:
        return K * np.log(1 + t / c)
    return K * (c ** (1 - p)) / (p - 1) * (1 - np.power(1 + t / c, 1 - p))


def etas_branching(t, A, c, p, mu_bg):
    """Branching ratio (mu) as ETAS decay.
    mu(t) = A / (t + c)^p + mu_bg
    Source: adapted from Omori-Utsu for branching process.
    """
    return A / np.power(t + c, p) + mu_bg


# ══════════════════════════════════════════════════════
# PART 1: Fit Omori-Utsu on new_concepts per year (aftershock rate)
# ══════════════════════════════════════════════════════

print(f"\n[1] FIT OMORI-UTSU SUR new_concepts/year")
print("=" * 80)

omori_fits = {}
for m in METS:
    wd = bfs[m]['wave_data']
    # new_concepts per year (= aftershock rate)
    t_arr = np.array([w['t'] for w in wd if w['t'] > 0 and w['new_concepts'] > 0], dtype=float)
    nc_arr = np.array([w['new_concepts'] for w in wd if w['t'] > 0 and w['new_concepts'] > 0], dtype=float)

    if len(t_arr) < 3:
        omori_fits[m] = {'r2': -1, 'note': 'too few points'}
        print(f"  {m:25s} SKIP (< 3 points)")
        continue

    try:
        popt, _ = curve_fit(omori_utsu, t_arr, nc_arr,
                            p0=[nc_arr.max() * 2, 0.5, 1.5],
                            bounds=([1, 0.001, 0.1], [1e8, 10, 5]),
                            maxfev=10000)
        K, c, p = popt
        pred = omori_utsu(t_arr, *popt)
        ss_res = np.sum((nc_arr - pred) ** 2)
        ss_tot = np.sum((nc_arr - nc_arr.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # Branching ratio: n = K * c^(1-p) / (p-1) for p > 1
        if p > 1:
            n_branch = K * c ** (1 - p) / (p - 1)
        else:
            n_branch = float('inf')

        omori_fits[m] = {
            'r2': round(r2, 4), 'K': round(K, 2), 'c': round(c, 4), 'p': round(p, 4),
            'n_branch': round(n_branch, 2) if n_branch < 1e6 else 'inf',
            'n_points': len(t_arr),
        }
        print(f"  {m:25s} R²={r2:+.4f} K={K:>12,.1f} c={c:.3f} p={p:.3f} n={n_branch:>10,.1f}")

    except Exception as e:
        omori_fits[m] = {'r2': -1, 'note': str(e)}
        print(f"  {m:25s} FAILED: {e}")

r2s = [f['r2'] for f in omori_fits.values() if f['r2'] > -1]
med_r2 = np.median(r2s) if r2s else -1
print(f"\n  Médiane R² = {med_r2:.4f} (n={len(r2s)})")


# ══════════════════════════════════════════════════════
# PART 2: Fit ETAS cumulative on R(t)
# ══════════════════════════════════════════════════════

print(f"\n[2] FIT ETAS CUMULATIF SUR R(t)")
print("=" * 80)

etas_fits = {}
for m in METS:
    wd = bfs[m]['wave_data']
    t_arr = np.array([w['t'] for w in wd if w['t'] > 0], dtype=float)
    r_arr = np.array([w['total_touched'] for w in wd if w['t'] > 0], dtype=float)

    if len(t_arr) < 3:
        etas_fits[m] = {'r2': -1}
        continue

    try:
        popt, _ = curve_fit(etas_cumulative, t_arr, r_arr,
                            p0=[r_arr.max(), 0.5, 0.5],
                            bounds=([100, 0.001, 0.01], [1e8, 20, 3]),
                            maxfev=10000)
        K, c, p = popt
        pred = etas_cumulative(t_arr, *popt)
        ss_res = np.sum((r_arr - pred) ** 2)
        ss_tot = np.sum((r_arr - r_arr.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        etas_fits[m] = {
            'r2': round(r2, 4), 'K': round(K, 1), 'c': round(c, 4), 'p': round(p, 4),
        }
        print(f"  {m:25s} R²={r2:+.4f} K={K:>12,.1f} c={c:.3f} p={p:.3f}")

    except Exception as e:
        etas_fits[m] = {'r2': -1, 'note': str(e)}
        print(f"  {m:25s} FAILED: {e}")

r2s_etas = [f['r2'] for f in etas_fits.values() if f['r2'] > -1]
med_r2_etas = np.median(r2s_etas) if r2s_etas else -1
print(f"\n  Médiane R² = {med_r2_etas:.4f} (n={len(r2s_etas)})")


# ══════════════════════════════════════════════════════
# PART 3: Fit ETAS branching on mu(t)
# ══════════════════════════════════════════════════════

print(f"\n[3] FIT ETAS BRANCHING SUR mu(t)")
print("=" * 80)

mu_fits = {}
for m in METS:
    mu = bfs[m]['mu_series']
    if len(mu) < 3:
        mu_fits[m] = {'r2': -1}
        continue

    t_arr = np.arange(1, len(mu) + 1, dtype=float)
    mu_arr = np.array(mu)

    try:
        popt, _ = curve_fit(etas_branching, t_arr, mu_arr,
                            p0=[mu_arr.max() * 2, 0.1, 1.5, 0.5],
                            bounds=([0.1, 0.001, 0.1, 0], [1e6, 10, 5, 100]),
                            maxfev=10000)
        A, c, p, mu_bg = popt
        pred = etas_branching(t_arr, *popt)
        ss_res = np.sum((mu_arr - pred) ** 2)
        ss_tot = np.sum((mu_arr - mu_arr.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        mu_fits[m] = {
            'r2': round(r2, 4), 'A': round(A, 2), 'c': round(c, 4),
            'p': round(p, 4), 'mu_bg': round(mu_bg, 4),
        }
        print(f"  {m:25s} R²={r2:+.4f} A={A:>10,.1f} c={c:.3f} p={p:.3f} mu_bg={mu_bg:.2f}")

    except Exception as e:
        mu_fits[m] = {'r2': -1, 'note': str(e)}
        print(f"  {m:25s} FAILED: {e}")

r2s_mu = [f['r2'] for f in mu_fits.values() if f['r2'] > -1]
med_r2_mu = np.median(r2s_mu) if r2s_mu else -1
print(f"\n  Médiane R² = {med_r2_mu:.4f} (n={len(r2s_mu)})")


# ══════════════════════════════════════════════════════
# PART 4: Universalité des paramètres ETAS
# ══════════════════════════════════════════════════════

print(f"\n[4] UNIVERSALITÉ DES PARAMÈTRES ETAS")
print("=" * 80)

# Check if p (Omori exponent) is stable across meteorites
p_omori = [f['p'] for f in omori_fits.values() if f.get('r2', -1) > 0.3]
p_etas = [f['p'] for f in etas_fits.values() if f.get('r2', -1) > 0.3]
p_mu = [f['p'] for f in mu_fits.values() if f.get('r2', -1) > 0.3]

for name, vals in [('Omori p', p_omori), ('ETAS cumul p', p_etas), ('Branching p', p_mu)]:
    if vals:
        arr = np.array(vals)
        cv = np.std(arr) / np.mean(arr) if np.mean(arr) > 0 else 999
        print(f"  {name:20s}: mean={np.mean(arr):.3f} ±{np.std(arr):.3f} CV={cv:.3f} (n={len(vals)})")
        if cv < 0.3:
            print(f"    → UNIVERSEL (CV < 0.3)")
        elif cv < 0.5:
            print(f"    → QUASI-UNIVERSEL (CV < 0.5)")
        else:
            print(f"    → PAS UNIVERSEL (CV > 0.5)")


# ══════════════════════════════════════════════════════
# PART 5: Corrélation paramètres ETAS vs mare
# ══════════════════════════════════════════════════════

print(f"\n[5] PARAMÈTRES ETAS vs PROPRIÉTÉS MARE")
print("=" * 80)

K_vals = np.array([logistic[m].get('K', bfs[m]['r_max']) for m in METS])

# Omori K vs mare
valid_mets = [m for m in METS if omori_fits[m].get('r2', -1) > 0]
if len(valid_mets) >= 6:
    omori_K = np.array([omori_fits[m]['K'] for m in valid_mets])
    omori_p = np.array([omori_fits[m]['p'] for m in valid_mets])
    omori_c = np.array([omori_fits[m]['c'] for m in valid_mets])
    rmax = np.array([bfs[m]['r_max'] for m in valid_mets])

    print(f"\n  Corrélations Omori params vs R_max (n={len(valid_mets)}):")
    for name, vals in [('Omori_K', omori_K), ('Omori_p', omori_p), ('Omori_c', omori_c)]:
        r, p = spearmanr(vals, rmax)
        flag = " ***" if abs(r) > 0.6 else ""
        print(f"    {name:15s} rho={r:+.4f} p={p:.4f}{flag}")

    # Also vs mare features
    print(f"\n  Corrélations Omori_K vs mare:")
    for fn in ['local_density', 'avg_internal_weight', 'median_neighbor_works', 'hub_fraction', 'n_seeds']:
        vals = np.array([mare[m].get(fn, 0) for m in valid_mets])
        r, p = spearmanr(vals, omori_K)
        flag = " ***" if abs(r) > 0.6 else ""
        print(f"    {fn:30s} rho={r:+.4f} p={p:.4f}{flag}")


# ══════════════════════════════════════════════════════
# PART 6: Comparaison ETAS vs logistique vs Omori
# ══════════════════════════════════════════════════════

print(f"\n[6] COMPARAISON: ETAS vs LOGISTIQUE vs OMORI")
print("=" * 80)

log_r2 = [logistic[m].get('r2', -1) if isinstance(logistic[m], dict) else -1 for m in METS]

print(f"\n  {'Météorite':25s} {'Logistic':>9s} {'ETAS_cum':>9s} {'Omori':>9s} {'Mu_ETAS':>9s} {'Best':>10s}")
comparison = {}
for i, m in enumerate(METS):
    lr = log_r2[i] if log_r2[i] > -1 else logistic[m].get('r2', -1)
    er = etas_fits[m].get('r2', -1)
    omr = omori_fits[m].get('r2', -1)
    mur = mu_fits[m].get('r2', -1)

    scores = {'logistic': lr, 'etas_cumul': er, 'omori': omr, 'mu_etas': mur}
    best = max(scores, key=lambda k: scores[k])

    comparison[m] = scores
    print(f"  {m:25s} {lr:+9.4f} {er:+9.4f} {omr:+9.4f} {mur:+9.4f} {best:>10s}")


# ══════════════════════════════════════════════════════
# VERDICT
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("VERDICT — CARMACK MOVE ETAS × KNOWLEDGE GRAPH")
print(f"{'='*80}")

print(f"""
  Omori-Utsu sur new_concepts/year:
    Médiane R² = {med_r2:.4f}
    {'PASS' if med_r2 > 0.7 else 'PARTIAL' if med_r2 > 0.4 else 'FAIL'}

  ETAS cumulatif sur R(t):
    Médiane R² = {med_r2_etas:.4f}
    {'PASS' if med_r2_etas > 0.9 else 'PARTIAL' if med_r2_etas > 0.7 else 'FAIL'}

  ETAS branching sur mu(t):
    Médiane R² = {med_r2_mu:.4f}
    {'PASS' if med_r2_mu > 0.7 else 'PARTIAL' if med_r2_mu > 0.4 else 'FAIL'}

  La loi d'Omori (décroissance en 1/(t+c)^p) s'applique-t-elle
  aux percées scientifiques comme aux répliques sismiques ?
""")

# Save
output = {
    "test": "etas_carmack_move_v1",
    "date": "2026-04-07",
    "carmack_desert": {"pair": "seismology × epidemic", "cooc": 0, "score": 321.6},
    "omori_fits": omori_fits,
    "etas_cumulative_fits": etas_fits,
    "mu_etas_fits": mu_fits,
    "median_r2": {"omori": round(med_r2, 4), "etas_cumul": round(med_r2_etas, 4), "mu_etas": round(med_r2_mu, 4)},
    "comparison": comparison,
    "sources": {
        "ogata": "Ogata, Y. (1988). Statistical models for earthquake occurrences. JASA, 83, 9-27",
        "omori": "Omori, F. (1894). On the aftershocks of earthquakes. J. College of Science, 7, 111-200",
        "utsu": "Utsu, T. (1961). A statistical study on the occurrence of aftershocks. Geophys. Mag., 30, 521-605",
        "saichev_sornette": "Saichev, A. & Sornette, D. (2005). Phys. Rev. E 71, 016608",
    },
}
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"Saved: {OUTPUT}")
print("DONE.")
