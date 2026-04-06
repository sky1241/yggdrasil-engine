#!/usr/bin/env python3
"""
YGGDRASIL ENGINE — V3 Predictive Wave Model
=============================================
Relier les paramètres logistiques (K, r, t₀) aux propriétés de la mare.
Objectif: un papier sort → on prédit l'onde AVANT qu'elle se produise.

4 étapes:
  1. Régression K,r,t₀ = f(mare_properties) — Ridge, LOO 13-fold
  2. P4 (trous structurels) autour des seeds — la mare vide aspire l'onde ?
  3. Carmack moves — déserts dans le graphe
  4. Test prédictif Gödel hold-out

Sources:
  Verhulst 1838 (logistic), Chung 1997 (spectral), Newman 2002 (percolation)
  Uzzi et al 2013 (z-score atypicality)

Sky × Claude (Opus 4.6) — Session 34, 6 avril 2026
"""
import json, sys, os, math, time, sqlite3
import numpy as np
from scipy.stats import spearmanr, pearsonr
from sklearn.linear_model import Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data", "wt3.db")
COMP_PATH = os.path.join(REPO, "data", "results", "wave_comprehensive_test.json")
CHECK_PATH = os.path.join(REPO, "data", "results", "_wave_checkpoint.json")
CONCEPTS_PATH = os.path.join(REPO, "data", "scan", "concepts_65k.json")
OUTPUT = os.path.join(REPO, "data", "results", "wave_predictive_model.json")

N_CONCEPTS = 65026

def load_json(p):
    with open(p, 'r', encoding='utf-8') as f: return json.load(f)

def save_json(d, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False, default=str)

print("=" * 80)
print("V3 PREDICTIVE WAVE MODEL")
print("Relier K, r, t₀ aux propriétés de la mare")
print("=" * 80)

# ══════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════

comp = load_json(COMP_PATH)
ck = load_json(CHECK_PATH)

# Logistic params
logistic_fits = ck['phase_3e']['fits']
mare_props = ck['phase_2']
bfs_data = ck['phase_1']

METS = list(bfs_data.keys())

# Build data matrix
data = {}
for m in METS:
    lf = logistic_fits[m]
    mp = mare_props[m]
    bf = bfs_data[m]
    data[m] = {
        # Targets (logistic params)
        'K': lf.get('K', bf['r_max']),
        'r_growth': lf.get('r_growth', 1.0),
        't0': lf.get('t0', 2.0),
        'r_max': bf['r_max'],
        'pct': bf['pct'],
        'death_t': bf.get('death_t', 10),
        'mu_peak': bf.get('mu_peak', 0),
        # Features (mare)
        'local_density': mp['local_density'],
        'avg_internal_weight': mp['avg_internal_weight'],
        'median_neighbor_works': mp['median_neighbor_works'],
        'n_neighbors': mp['n_neighbors'],
        'hub_fraction': mp['hub_fraction'],
        'avg_edge_weight': mp['avg_edge_weight'],
        'seed_degree': mp['seed_degree'],
        'seed_works': mp['seed_works'],
        'seed_weight': mp['seed_weight'],
        'pre_edges': mp['pre_edges'],
        'pre_weight': mp['pre_weight'],
        'avg_level': mp['avg_level'],
        'n_seeds': mp['n_seeds'],
    }

print(f"Loaded {len(data)} meteorites")
for m in sorted(data.keys(), key=lambda x: -data[x]['K']):
    d = data[m]
    print(f"  {m:25s} K={d['K']:>8,} r={d['r_growth']:.2f} t0={d['t0']:.2f} "
          f"dens={d['local_density']:.3f} aiw={d['avg_internal_weight']:.0f}")

# ══════════════════════════════════════════════════════
# ÉTAPE 1 — RÉGRESSION K = f(mare)
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("ÉTAPE 1 — RÉGRESSION K, r, t₀ = f(mare)")
print(f"{'='*80}")

feature_names = ['local_density', 'avg_internal_weight', 'median_neighbor_works',
                 'n_neighbors', 'hub_fraction', 'avg_edge_weight',
                 'seed_degree', 'seed_works', 'seed_weight',
                 'pre_edges', 'pre_weight', 'avg_level', 'n_seeds']

targets = ['K', 'r_growth', 't0']

X = np.array([[data[m][f] for f in feature_names] for m in METS])
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

regression_results = {}

for target in targets:
    y = np.array([data[m][target] for m in METS])

    print(f"\n  --- {target} ---")

    # Spearman correlations
    print(f"  {'Feature':30s} {'rho':>8s} {'p':>8s}")
    corrs = {}
    for i, fn in enumerate(feature_names):
        r_s, p_s = spearmanr(X[:, i], y)
        corrs[fn] = {'rho': round(r_s, 4), 'p': round(p_s, 4)}
        flag = " ***" if abs(r_s) > 0.6 else " *" if abs(r_s) > 0.4 else ""
        print(f"  {fn:30s} {r_s:+8.4f} {p_s:8.4f}{flag}")

    # Ridge regression LOO
    alphas = [0.01, 0.1, 1.0, 10.0, 100.0]
    best_alpha, best_mae = 1.0, float('inf')

    for alpha in alphas:
        loo_errors = []
        for i in range(len(METS)):
            mask = np.ones(len(METS), dtype=bool)
            mask[i] = False
            model = Ridge(alpha=alpha)
            model.fit(X_scaled[mask], y[mask])
            pred = model.predict(X_scaled[i:i+1])[0]
            loo_errors.append(abs(pred - y[i]))
        mae = np.mean(loo_errors)
        if mae < best_mae:
            best_mae = mae
            best_alpha = alpha

    # Final LOO with best alpha
    loo_preds = []
    for i in range(len(METS)):
        mask = np.ones(len(METS), dtype=bool)
        mask[i] = False
        model = Ridge(alpha=best_alpha)
        model.fit(X_scaled[mask], y[mask])
        pred = model.predict(X_scaled[i:i+1])[0]
        loo_preds.append({
            'met': METS[i], 'obs': round(float(y[i]), 2),
            'pred': round(float(pred), 2),
            'error': round(abs(float(pred) - float(y[i])), 2),
            'pct_error': round(abs(float(pred) - float(y[i])) / max(abs(float(y[i])), 1) * 100, 1),
        })

    mae = np.mean([p['error'] for p in loo_preds])
    median_pct = np.median([p['pct_error'] for p in loo_preds])
    y_mean = np.mean(y)

    # Fit final model for feature importance
    final_model = Ridge(alpha=best_alpha)
    final_model.fit(X_scaled, y)
    importances = dict(zip(feature_names, [round(float(c), 4) for c in final_model.coef_]))
    top_features = sorted(importances.items(), key=lambda x: -abs(x[1]))[:5]

    print(f"\n  Ridge LOO (alpha={best_alpha}):")
    print(f"  {'Met':25s} {'Obs':>10s} {'Pred':>10s} {'Err':>10s} {'%Err':>6s}")
    for p in sorted(loo_preds, key=lambda x: -x['obs']):
        print(f"  {p['met']:25s} {p['obs']:10,.1f} {p['pred']:10,.1f} {p['error']:10,.1f} {p['pct_error']:5.1f}%")
    print(f"  MAE = {mae:,.1f} (médiane %err = {median_pct:.1f}%)")
    print(f"  Top features: {', '.join(f'{n}({v:+.1f})' for n,v in top_features)}")

    verdict = "PASS" if median_pct < 20 else "PARTIAL" if median_pct < 40 else "FAIL"
    print(f"  VERDICT: {verdict}")

    regression_results[target] = {
        'verdict': verdict,
        'best_alpha': best_alpha,
        'mae': round(mae, 2),
        'median_pct_error': round(median_pct, 1),
        'correlations': corrs,
        'top_features': dict(top_features),
        'loo_predictions': loo_preds,
    }


# ══════════════════════════════════════════════════════
# ÉTAPE 2 — P4 AUTOUR DES SEEDS
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("ÉTAPE 2 — P4 (TROUS STRUCTURELS) AUTOUR DES SEEDS")
print(f"{'='*80}")

# Load concept info
cdata = load_json(CONCEPTS_PATH)
idx2info = {v['idx']: v for k, v in cdata['concepts'].items()}

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Total works for z-score
total_works = sum(v.get('works_count', 0) for v in idx2info.values())

p4_results = {}
for m_name in METS:
    seeds = bfs_data[m_name]['seeds']
    t0_time = time.time()

    # Get 1-hop neighbors of seeds
    neighbors = set()
    for s in seeds:
        c.execute("SELECT concept_b FROM cooc_global WHERE concept_a=?", (s,))
        neighbors.update(r[0] for r in c.fetchall())
        c.execute("SELECT concept_a FROM cooc_global WHERE concept_b=?", (s,))
        neighbors.update(r[0] for r in c.fetchall())
    neighbors -= set(seeds)

    # Sample neighbors for P4 computation
    sample = list(neighbors)[:200]

    # Compute P4 for seed × sample pairs
    p4_scores = []
    n_deserts = 0
    z_scores = []

    for s in seeds:
        wa = idx2info.get(s, {}).get('works_count', 0)
        for nb in sample:
            wb = idx2info.get(nb, {}).get('works_count', 0)
            if wa == 0 or wb == 0:
                continue

            lo, hi = min(s, nb), max(s, nb)
            c.execute("SELECT weight FROM cooc_global WHERE concept_a=? AND concept_b=?", (lo, hi))
            row = c.fetchone()
            observed = row[0] if row else 0

            expected = wa * wb / total_works
            std = max(math.sqrt(max(expected * (1 - wa/total_works) * (1 - wb/total_works), 0)), 1.0)
            z = (observed - expected) / std

            cooc_norm = observed / max(expected, 1e-10)
            gap = max(0, 1 - cooc_norm)
            activity = math.log1p(wa) * math.log1p(wb)
            p4 = activity * gap * abs(z)

            p4_scores.append(p4)
            z_scores.append(z)
            if observed == 0:
                n_deserts += 1

    n_pairs = len(p4_scores)
    avg_p4 = np.mean(p4_scores) if p4_scores else 0
    desert_ratio = n_deserts / n_pairs if n_pairs > 0 else 0
    avg_z = np.mean(z_scores) if z_scores else 0
    median_p4 = np.median(p4_scores) if p4_scores else 0

    p4_results[m_name] = {
        'avg_p4': round(avg_p4, 4),
        'median_p4': round(median_p4, 4),
        'desert_ratio': round(desert_ratio, 4),
        'avg_z': round(avg_z, 4),
        'n_pairs': n_pairs,
        'n_deserts': n_deserts,
    }

    dt = time.time() - t0_time
    print(f"  {m_name:25s} avg_P4={avg_p4:8.2f} desert={desert_ratio:.2f} "
          f"z={avg_z:+.2f} K={data[m_name]['K']:>8,} ({dt:.0f}s)")

# Correlations P4 metrics vs K
print(f"\n  Corrélations P4 vs K:")
K_vals = np.array([data[m]['K'] for m in METS])
for metric in ['avg_p4', 'median_p4', 'desert_ratio', 'avg_z']:
    vals = np.array([p4_results[m][metric] for m in METS])
    r_s, p_s = spearmanr(vals, K_vals)
    flag = " ***" if abs(r_s) > 0.6 else " *" if abs(r_s) > 0.4 else ""
    print(f"    {metric:20s} rho={r_s:+.4f} p={p_s:.4f}{flag}")


# ══════════════════════════════════════════════════════
# ÉTAPE 3 — CARMACK MOVES
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("ÉTAPE 3 — CARMACK MOVES (déserts dans le graphe)")
print(f"{'='*80}")

# Cross-domain concept pairs that are deserts
carmack_pairs = [
    # Modèles d'onde × graph theory
    (60336, 61010, 'diffusion × spectral_graph_theory'),
    (55559, 2429, 'wave_propagation × laplacian_matrix'),
    (55559, 3378, 'wave_propagation × random_walk'),
    (60743, 2429, 'impulse_response × laplacian_matrix'),
    (60743, 61010, 'impulse_response × spectral_graph_theory'),
    # Épidémiologie × physique
    (9788, 12999, 'epidemic_model × heat_kernel'),
    (9788, 61732, 'epidemic_model × seismic_wave'),
    (9788, 32088, 'epidemic_model × financial_contagion'),
    # Percolation × signal
    (2489, 60743, 'percolation × impulse_response'),
    (2489, 32088, 'percolation × financial_contagion'),
    # Cratère × réseau
    (12452, 53869, 'impact_crater × cascade'),
    (12452, 17674, 'impact_crater × scale_free_network'),
    # Branching × spectral
    (12054, 61010, 'branching_process × spectral_graph_theory'),
    (12054, 2429, 'branching_process × laplacian_matrix'),
]

carmack_scores = []
print(f"\n  {'Paire':50s} {'cooc':>8s} {'E':>8s} {'z':>8s} {'desert':>7s}")
for a, b, label in carmack_pairs:
    lo, hi = min(a, b), max(a, b)
    c.execute("SELECT weight FROM cooc_global WHERE concept_a=? AND concept_b=?", (lo, hi))
    row = c.fetchone()
    obs = row[0] if row else 0

    wa = idx2info.get(a, {}).get('works_count', 0)
    wb = idx2info.get(b, {}).get('works_count', 0)
    exp = wa * wb / total_works if total_works > 0 else 0
    std = max(math.sqrt(max(exp * (1 - wa/total_works) * (1 - wb/total_works), 0)), 1.0)
    z = (obs - exp) / std

    desert = "DESERT" if obs == 0 else "linked"
    score = math.log1p(wa) * math.log1p(wb) * abs(z) if obs == 0 else 0

    carmack_scores.append({
        'pair': label, 'a': a, 'b': b,
        'cooc': round(obs, 4), 'expected': round(exp, 2),
        'z': round(z, 4), 'desert': obs == 0,
        'carmack_score': round(score, 2),
    })

    print(f"  {label:50s} {obs:8.2f} {exp:8.1f} {z:+8.2f} {desert:>7s}")

n_deserts = sum(1 for s in carmack_scores if s['desert'])
print(f"\n  Déserts: {n_deserts}/{len(carmack_scores)}")
top_carmack = sorted([s for s in carmack_scores if s['desert']], key=lambda x: -x['carmack_score'])[:5]
if top_carmack:
    print(f"  Top Carmack moves:")
    for s in top_carmack:
        print(f"    {s['pair']:50s} score={s['carmack_score']:8.1f} z={s['z']:+.2f}")

conn.close()


# ══════════════════════════════════════════════════════
# ÉTAPE 4 — TEST PRÉDICTIF GÖDEL HOLD-OUT
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("ÉTAPE 4 — TEST PRÉDICTIF GÖDEL HOLD-OUT")
print(f"{'='*80}")

holdout_name = "Godel 1931"
train_mets = [m for m in METS if m != holdout_name]

# Train Ridge on 12, predict Gödel
X_train = np.array([[data[m][f] for f in feature_names] for m in train_mets])
X_holdout = np.array([[data[holdout_name][f] for f in feature_names]])

scaler_ho = StandardScaler()
X_train_s = scaler_ho.fit_transform(X_train)
X_holdout_s = scaler_ho.transform(X_holdout)

print(f"\n  Train: {len(train_mets)} météorites, holdout: {holdout_name}")

holdout_preds = {}
for target in targets:
    y_train = np.array([data[m][target] for m in train_mets])
    y_obs = data[holdout_name][target]

    # Use best alpha from step 1
    alpha = regression_results[target]['best_alpha']
    model = Ridge(alpha=alpha)
    model.fit(X_train_s, y_train)
    pred = float(model.predict(X_holdout_s)[0])

    error = abs(pred - y_obs)
    pct_err = error / max(abs(y_obs), 1) * 100

    holdout_preds[target] = {
        'observed': round(y_obs, 2),
        'predicted': round(pred, 2),
        'error': round(error, 2),
        'pct_error': round(pct_err, 1),
    }
    print(f"  {target:12s} obs={y_obs:10,.2f} pred={pred:10,.2f} err={error:10,.2f} ({pct_err:.1f}%)")

# Reconstruct R(t) for Gödel
K_pred = holdout_preds['K']['predicted']
r_pred = holdout_preds['r_growth']['predicted']
t0_pred = holdout_preds['t0']['predicted']

print(f"\n  Logistic prédite: R(t) = {K_pred:,.0f} / (1 + exp(-{r_pred:.2f}×(t-{t0_pred:.2f})))")

# Compare with observed R(t)
godel_wave = bfs_data[holdout_name]['wave_data']
print(f"\n  {'t':>3s} {'R_obs':>8s} {'R_pred':>8s} {'Err':>8s}")
for w in godel_wave:
    t = w['t']
    r_obs = w['total_touched']
    r_pred_t = K_pred / (1 + np.exp(-r_pred * (t - t0_pred))) if K_pred > 0 else 0
    r_pred_t = max(0, r_pred_t)
    err = abs(r_pred_t - r_obs)
    print(f"  {t:3d} {r_obs:8,} {r_pred_t:8,.0f} {err:8,.0f}")

# Overall R² on Gödel trajectory
r_obs_arr = np.array([w['total_touched'] for w in godel_wave])
t_arr = np.array([w['t'] for w in godel_wave], dtype=float)
r_pred_arr = K_pred / (1 + np.exp(-r_pred * (t_arr - t0_pred)))
r_pred_arr = np.maximum(0, r_pred_arr)

ss_res = np.sum((r_obs_arr - r_pred_arr)**2)
ss_tot = np.sum((r_obs_arr - r_obs_arr.mean())**2)
r2_holdout = 1 - ss_res / ss_tot if ss_tot > 0 else 0

print(f"\n  R² sur trajectoire Gödel = {r2_holdout:.4f}")

verdict_ho = "PASS" if r2_holdout > 0.8 else "PARTIAL" if r2_holdout > 0.5 else "FAIL"
print(f"  VERDICT: {verdict_ho}")


# ══════════════════════════════════════════════════════
# GRAND RÉSUMÉ
# ══════════════════════════════════════════════════════

print(f"\n{'='*80}")
print("GRAND RÉSUMÉ — MODÈLE PRÉDICTIF")
print(f"{'='*80}")

print(f"""
  ÉTAPE 1 — Régression K = f(mare):
    K:       {regression_results['K']['verdict']:8s} (médiane err = {regression_results['K']['median_pct_error']}%)
    r:       {regression_results['r_growth']['verdict']:8s} (médiane err = {regression_results['r_growth']['median_pct_error']}%)
    t₀:      {regression_results['t0']['verdict']:8s} (médiane err = {regression_results['t0']['median_pct_error']}%)

  ÉTAPE 2 — P4 autour des seeds:
    La densité de trous prédit-elle K ? (voir corrélations ci-dessus)

  ÉTAPE 3 — Carmack moves:
    {n_deserts} déserts trouvés sur {len(carmack_scores)} paires

  ÉTAPE 4 — Gödel hold-out:
    K obs={holdout_preds['K']['observed']:,.0f} pred={holdout_preds['K']['predicted']:,.0f} ({holdout_preds['K']['pct_error']}%)
    R² trajectoire = {r2_holdout:.4f}
    VERDICT: {verdict_ho}
""")

# Save
output = {
    "test": "wave_predictive_model_v1",
    "date": "2026-04-06",
    "n_meteorites": 13,
    "step_1_regression": regression_results,
    "step_2_p4": p4_results,
    "step_3_carmack": carmack_scores,
    "step_4_holdout": {
        "holdout": holdout_name,
        "predictions": holdout_preds,
        "r2_trajectory": round(r2_holdout, 4),
        "verdict": verdict_ho,
    },
    "sources": {
        "logistic": "Verhulst 1838",
        "ridge": "Hoerl & Kennard 1970",
        "p4": "Uzzi et al 2013 (z-score atypicality)",
        "newman": "Newman 2002, cond-mat/0205009",
        "spectral": "Chung 1997, Spectral Graph Theory",
    },
}
save_json(output, OUTPUT)
print(f"Saved: {OUTPUT}")
print("DONE.")
