#!/usr/bin/env python3
"""
YGGDRASIL — Session 36: Modèle dynamique "famille du champignon"
=================================================================
Au lieu de prédire r (impossible pré-impact), on prédit la FORME R(t)/K.

3 approches:
1. Ridge par timestep: prédire R(t)/K à chaque t depuis les features mare
2. Template matching: trouver la météorite train la plus similaire
3. Type-based: classifier en exploseur/rampeur et utiliser la courbe type

Sky × Claude (Opus 4.6) — Session 36, 7 avril 2026
"""
import json, sys, os
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

def P(*args, **kw):
    print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), encoding='utf-8'))
ASSEMBLY = json.load(open(os.path.join(REPO, "data/results/wave_assembly_s36.json"), encoding='utf-8'))
bfs = CHECK['phase_1']
mare = CHECK['phase_2']
logistic = CHECK['phase_3e']['fits']
METS = list(bfs.keys())

train_mets = [m for m in METS if int(m.split()[-1]) <= 1960]
test_mets  = [m for m in METS if int(m.split()[-1]) >= 1974]
train_idx = [METS.index(m) for m in train_mets]
test_idx  = [METS.index(m) for m in test_mets]

P("=" * 80)
P("MODELE DYNAMIQUE — famille du champignon")
P("Prédire la FORME R(t)/K au lieu de r")
P("=" * 80)

# Extract normalized curves for all meteorites, padded to 12 timesteps
max_t = 12
curves = {}
for m in METS:
    wd = bfs[m]['wave_data']
    K = logistic[m]['K']
    curve = np.zeros(max_t)
    for w in wd:
        t = w['t']
        if t < max_t:
            curve[t] = w['total_touched'] / K
    # Pad with last value
    last_val = curve[0]
    for t in range(max_t):
        if curve[t] > 0:
            last_val = curve[t]
        elif t > 0:
            curve[t] = last_val
    curves[m] = curve

# Features matrix (pre-impact only)
mare_feats = ['n_neighbors', 'local_density', 'hub_fraction', 'avg_edge_weight',
              'median_neighbor_works', 'seed_degree', 'seed_works', 'seed_weight',
              'n_seeds', 'avg_internal_weight', 'pre_edges', 'pre_weight', 'avg_level']
sci_feats = ['fitness_growth', 'd_index_proxy', 'z_score_proxy', 'activity_1y', 'activity_5y']
topo_feats = ['global_degree', 'global_weight', 'weight_per_edge', 'spectral_dist']

X = []
for m in METS:
    row = [mare[m][f] for f in mare_feats]
    row += [ASSEMBLY['phase_A_scientometrics'][m][f] for f in sci_feats]
    row += [ASSEMBLY['phase_B_topology'][m][f] for f in topo_feats]
    X.append(row)
X = np.array(X)
feat_names = [f"mare_{f}" for f in mare_feats] + [f"sci_{f}" for f in sci_feats] + [f"topo_{f}" for f in topo_feats]

# K prediction (best from phase D)
K_all = np.array([logistic[m]['K'] for m in METS])
sc_K = StandardScaler()
X_tr_K = sc_K.fit_transform(X[train_idx])
X_te_K = sc_K.transform(X[test_idx])
model_K = Ridge(alpha=1.0)
model_K.fit(X_tr_K, K_all[train_idx])
K_pred = model_K.predict(X_te_K)


# ═══════════════════════════════════════════════════════
# APPROACH 1: Ridge par timestep
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("APPROCHE 1: Ridge par timestep — prédire R(t)/K à chaque t")
P(f"{'='*80}")

P(f"\n  {'t':>3s}  {'train_R2':>8s}  {'test_MAE':>8s}")
R_pred_ridge = {m: np.zeros(max_t) for m in test_mets}
for t in range(1, 9):
    y = np.array([curves[m][t] for m in METS])
    sc = StandardScaler()
    X_tr = sc.fit_transform(X[train_idx])
    X_te = sc.transform(X[test_idx])
    model = Ridge(alpha=1.0)
    model.fit(X_tr, y[train_idx])
    y_pred = np.clip(model.predict(X_te), 0, 1.1)
    mae = np.mean(np.abs(y_pred - y[test_idx]))
    r2_tr = model.score(X_tr, y[train_idx])
    for i, m in enumerate(test_mets):
        R_pred_ridge[m][t] = y_pred[i]
    P(f"  t={t:2d}  R2_tr={r2_tr:+.4f}  MAE={mae:.4f}")

# R(t) with ridge fractions
P(f"\n  R(t) = fraction_Ridge(t) x K_pred")
P(f"  {'Met':25s} {'K_obs':>8s} {'K_pred':>8s} {'R2_fracxKtrue':>13s} {'R2_fracxKpred':>13s}")
r2_ridge_true = []
r2_ridge_pred = []
for i, m in enumerate(test_mets):
    wd = bfs[m]['wave_data']
    K_true = K_all[test_idx[i]]
    t_arr = np.array([w['t'] for w in wd], dtype=float)
    R_obs = np.array([w['total_touched'] for w in wd], dtype=float)
    ss_tot = np.sum((R_obs - R_obs.mean())**2)

    # frac x K_true
    R_p1 = np.array([R_pred_ridge[m][min(int(t), max_t-1)] * K_true for t in t_arr])
    r2_1 = 1 - np.sum((R_obs - R_p1)**2) / ss_tot if ss_tot > 0 else 0
    r2_ridge_true.append(r2_1)

    # frac x K_pred
    R_p2 = np.array([R_pred_ridge[m][min(int(t), max_t-1)] * K_pred[i] for t in t_arr])
    r2_2 = 1 - np.sum((R_obs - R_p2)**2) / ss_tot if ss_tot > 0 else 0
    r2_ridge_pred.append(r2_2)

    P(f"  {m:25s} {K_true:8,.0f} {K_pred[i]:8,.0f} {r2_1:+13.4f} {r2_2:+13.4f}")

P(f"\n  Med R2 (frac x K_true): {np.median(r2_ridge_true):.4f}")
P(f"  Med R2 (frac x K_pred): {np.median(r2_ridge_pred):.4f}")


# ═══════════════════════════════════════════════════════
# APPROACH 2: Template matching (nearest neighbor in feature space)
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("APPROCHE 2: Template matching — plus proche voisin dans features")
P(f"{'='*80}")

sc_tmpl = StandardScaler()
X_tr_tmpl = sc_tmpl.fit_transform(X[train_idx])
X_te_tmpl = sc_tmpl.transform(X[test_idx])

r2_template = []
P(f"\n  {'Met':25s} {'template':>20s} {'R2':>8s}")
for i, m in enumerate(test_mets):
    wd = bfs[m]['wave_data']
    t_arr = np.array([w['t'] for w in wd], dtype=float)
    R_obs = np.array([w['total_touched'] for w in wd], dtype=float)
    ss_tot = np.sum((R_obs - R_obs.mean())**2)

    dists = np.linalg.norm(X_tr_tmpl - X_te_tmpl[i], axis=1)
    nearest_local = np.argmin(dists)
    nearest_global = train_idx[nearest_local]
    nearest_name = METS[nearest_global]

    template = curves[nearest_name]
    R_pred = np.array([template[min(int(t), max_t-1)] * K_pred[i] for t in t_arr])
    r2 = 1 - np.sum((R_obs - R_pred)**2) / ss_tot if ss_tot > 0 else 0
    r2_template.append(r2)
    P(f"  {m:25s} {nearest_name:>20s} {r2:+8.4f}")

P(f"\n  Med R2 template: {np.median(r2_template):.4f}")


# ═══════════════════════════════════════════════════════
# APPROACH 3: Type-based (exploseur/rampeur from n_seeds)
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("APPROCHE 3: Type-based — famille du champignon")
P(f"{'='*80}")

# Build type curves from train set
# Type 1: n_seeds <= 2 (most meteorites)
# Type 2: n_seeds >= 3 (Gödel, Turing)
# Also: avg_edge_weight > 5 = "thick pond" (Laser, ADN, Internet)

# Let's try multiple type systems
type_systems = {}

# System A: n_seeds
def classify_nseed(m):
    return "few" if mare[m]['n_seeds'] <= 2 else "many"
type_systems['n_seeds'] = classify_nseed

# System B: avg_edge_weight
def classify_aew(m):
    return "thin" if mare[m]['avg_edge_weight'] < 2 else "thick"
type_systems['aew'] = classify_aew

# System C: hub_fraction
def classify_hf(m):
    return "high_hub" if mare[m]['hub_fraction'] > 0.22 else "low_hub"
type_systems['hub_frac'] = classify_hf

# System D: combined (2x2)
def classify_combo(m):
    thick = mare[m]['avg_edge_weight'] >= 2
    many = mare[m]['n_seeds'] >= 3
    if thick:
        return "thick"
    elif many:
        return "many_seeds"
    else:
        return "standard"
type_systems['combo'] = classify_combo

for sys_name, classifier in type_systems.items():
    P(f"\n  Type system: {sys_name}")

    # Build average curves per type from train
    type_curves = {}
    type_counts = {}
    for m in train_mets:
        tp = classifier(m)
        if tp not in type_curves:
            type_curves[tp] = []
        type_curves[tp].append(curves[m])

    for tp in type_curves:
        type_curves[tp] = np.mean(type_curves[tp], axis=0)
        P(f"    {tp:15s}: {' '.join([f'{v:.2f}' for v in type_curves[tp][:8]])}")

    r2_type = []
    for i, m in enumerate(test_mets):
        wd = bfs[m]['wave_data']
        t_arr = np.array([w['t'] for w in wd], dtype=float)
        R_obs = np.array([w['total_touched'] for w in wd], dtype=float)
        ss_tot = np.sum((R_obs - R_obs.mean())**2)

        tp = classifier(m)
        if tp in type_curves:
            tc = type_curves[tp]
        else:
            # Fallback: use average of all train curves
            tc = np.mean([curves[m2] for m2 in train_mets], axis=0)

        R_pred = np.array([tc[min(int(t), max_t-1)] * K_pred[i] for t in t_arr])
        r2 = 1 - np.sum((R_obs - R_pred)**2) / ss_tot if ss_tot > 0 else 0
        r2_type.append(r2)
        P(f"    {m:25s} type={tp:12s} R2={r2:+.4f}")

    P(f"    Med R2: {np.median(r2_type):.4f}")


# ═══════════════════════════════════════════════════════
# APPROACH 4: Weighted template (distance-weighted average of ALL train curves)
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("APPROCHE 4: Weighted template — moyenne pondérée de toutes les courbes train")
P(f"{'='*80}")

r2_weighted = []
P(f"\n  {'Met':25s} {'weights (S/T/Tu/A/G/L)':>30s} {'R2':>8s}")
for i, m in enumerate(test_mets):
    wd = bfs[m]['wave_data']
    t_arr = np.array([w['t'] for w in wd], dtype=float)
    R_obs = np.array([w['total_touched'] for w in wd], dtype=float)
    ss_tot = np.sum((R_obs - R_obs.mean())**2)

    # Distance-weighted average of train curves
    dists = np.linalg.norm(X_tr_tmpl - X_te_tmpl[i], axis=1)
    weights = 1 / (dists + 0.01)
    weights /= weights.sum()

    weighted_curve = np.zeros(max_t)
    for j, m2 in enumerate(train_mets):
        weighted_curve += weights[j] * curves[m2]

    R_pred = np.array([weighted_curve[min(int(t), max_t-1)] * K_pred[i] for t in t_arr])
    r2 = 1 - np.sum((R_obs - R_pred)**2) / ss_tot if ss_tot > 0 else 0
    r2_weighted.append(r2)

    w_str = ' '.join([f"{w:.2f}" for w in weights])
    P(f"  {m:25s} [{w_str}] {r2:+8.4f}")

P(f"\n  Med R2 weighted: {np.median(r2_weighted):.4f}")


# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("RÉSUMÉ — quel modèle dynamique gagne?")
P(f"{'='*80}")

P(f"\n  Session 35 (logistic K+r+t0):     R2 = -0.15 FAIL")
P(f"  Session 36 (Ridge K + topo r):    R2 = +0.44 PARTIAL")
P(f"  Ridge par timestep (frac x Kpred): R2 = {np.median(r2_ridge_pred):.4f}")
P(f"  Template matching:                 R2 = {np.median(r2_template):.4f}")
P(f"  Weighted template:                 R2 = {np.median(r2_weighted):.4f}")
P(f"  Plafond (K pred + r true):         R2 = 0.67")

# Save results
output = {
    "test": "dynamic_model_s36",
    "date": "2026-04-07",
    "approach_1_ridge_timestep": {
        "r2_frac_Ktrue": round(float(np.median(r2_ridge_true)), 4),
        "r2_frac_Kpred": round(float(np.median(r2_ridge_pred)), 4),
        "per_met": {m: round(float(r2_ridge_pred[i]), 4) for i, m in enumerate(test_mets)},
    },
    "approach_2_template": {
        "r2": round(float(np.median(r2_template)), 4),
        "per_met": {m: round(float(r2_template[i]), 4) for i, m in enumerate(test_mets)},
    },
    "approach_4_weighted": {
        "r2": round(float(np.median(r2_weighted)), 4),
        "per_met": {m: round(float(r2_weighted[i]), 4) for i, m in enumerate(test_mets)},
    },
}

OUT = os.path.join(REPO, "data/results/wave_dynamic_model_s36.json")
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

P(f"\nSaved: {OUT}")
P("DONE.")
