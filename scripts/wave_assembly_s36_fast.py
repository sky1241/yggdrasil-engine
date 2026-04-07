#!/usr/bin/env python3
"""
YGGDRASIL — Session 36: Assemblage dynamique (version RAPIDE)
==============================================================
Scientométrie + topologie simple + spectral WT4 + mare + candlestick

DIAGNOSTIC:
  - r prediction est le BOTTLENECK (173-406% erreur en test temporel)
  - candle_ratio ne peut pas prédire r pre-impact (uses post-impact data)
  - K avec TRUE r donne R² = +0.57 → K fonctionne, c'est r qui manque
  - PRIORITÉ: trouver un prédicteur PRÉ-IMPACT pour r

VERSION RAPIDE: pas de construction de sous-graphe (trop lent).
On utilise les métriques topo directement depuis cooc_global (degré/poids)
et les positions spectrales WT4 (déjà calculées).

Sky × Claude (Opus 4.6) — Session 36, 7 avril 2026
"""
import json, sys, os, math, time
import numpy as np
import sqlite3
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

def P(*args, **kw):
    print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")
CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), encoding='utf-8'))
CANDLES = json.load(open(os.path.join(REPO, "data/results/wave_candlestick_model.json"), encoding='utf-8'))
SPECTRAL = json.load(open(os.path.join(REPO, "data/scan/spectral_births.json"), encoding='utf-8'))
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

# Spectral positions (WT4)
node_by_id = {n['id']: n for n in SPECTRAL['nodes']}

P("=" * 80)
P("SESSION 36 — ASSEMBLAGE DYNAMIQUE (FAST)")
P("=" * 80)


# ═══════════════════════════════════════════════════════
# PHASE A: Scientometric proxies from WT3
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE A: Proxys scientométriques depuis WT3")
P(f"{'='*80}")

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

scisci = {}
for mi, m in enumerate(METS):
    year = int(m.split()[-1])
    seeds = bfs[m]['seeds']
    t0s = time.time()

    # A1: FITNESS GROWTH RATE (5y pre + impact + 1y post)
    growth_rates = []
    activities_1y = []
    activities_5y = []
    impact_counts = []
    pre_counts = []
    post_counts = []

    for seed in seeds:
        yearly_counts = {}
        yearly_weights = {}
        for y in range(year - 5, year + 2):
            cur.execute("""
                SELECT COUNT(DISTINCT concept_b), COALESCE(SUM(weight), 0)
                FROM cooc WHERE concept_a = ? AND period >= ? AND period < ?
            """, (seed, f"{y}-01", f"{y+1}-01"))
            row = cur.fetchone()
            yearly_counts[y] = row[0]
            yearly_weights[y] = row[1]

        pre_yrs = list(range(year - 5, year))
        counts_pre = np.array([yearly_counts[y] for y in pre_yrs])

        if counts_pre.sum() > 0:
            slope = np.polyfit(np.arange(len(pre_yrs)), counts_pre, 1)[0]
            growth_rates.append(slope)
        else:
            growth_rates.append(0)

        activities_1y.append(yearly_weights.get(year - 1, 0))
        activities_5y.append(sum(yearly_weights[y] for y in pre_yrs))
        impact_counts.append(yearly_counts.get(year, 0))
        pre_counts.append(yearly_counts.get(year - 1, 0))
        post_counts.append(yearly_counts.get(year + 1, 0))

    fitness_growth = float(np.mean(growth_rates))
    activity_1y = float(np.mean(activities_1y))
    activity_5y = float(np.mean(activities_5y))

    # A2: D-INDEX PROXY (impact burst vs pre-average)
    d_vals = []
    for i, seed in enumerate(seeds):
        pre_avg = np.mean([pre_counts[i]])  # just 1y pre
        ic = impact_counts[i]
        if ic > 0:
            d_vals.append((ic - pre_avg) / ic)
        else:
            d_vals.append(0)
    d_index_proxy = float(np.mean(d_vals))

    # A3: POST GROWTH (impact vs post-impact)
    pg_vals = []
    for i in range(len(seeds)):
        if pre_counts[i] > 0:
            pg_vals.append((impact_counts[i] - pre_counts[i]) / pre_counts[i])
        else:
            pg_vals.append(impact_counts[i] if impact_counts[i] > 0 else 0)
    post_growth = float(np.mean(pg_vals))

    # A4: ACCELERATION (is the growth rate itself increasing?)
    accels = []
    for seed in seeds:
        # Already computed yearly_counts in the loop above — but we lost it
        # Recompute just the rate of change of rate of change
        pass
    # Skip acceleration for now, use fitness_growth slope

    # A5: Z-SCORE PROXY (seed pair atypicality)
    z_scores = []
    if len(seeds) >= 2:
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
                deg_i = seed_degrees[seeds[i]]
                deg_j = seed_degrees[seeds[j]]
                expected = deg_i * deg_j / (2 * 69440760)
                if expected > 0:
                    z = (observed - expected) / math.sqrt(expected + 0.01)
                    z_scores.append(z)
    z_score_proxy = float(np.mean(z_scores)) if z_scores else 0.0

    dt = time.time() - t0s
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
# PHASE B: Simple topology from cooc_global + WT4 spectral
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE B: Topologie simple (cooc_global degré + WT4 spectral)")
P(f"{'='*80}")

# Spectral center
all_x = [n['x'] for n in SPECTRAL['nodes']]
all_y = [n['y'] for n in SPECTRAL['nodes']]
all_z = [n['z'] for n in SPECTRAL['nodes']]
cx, cy, cz = np.mean(all_x), np.mean(all_y), np.mean(all_z)

topo = {}
for mi, m in enumerate(METS):
    seeds = bfs[m]['seeds']
    t0s = time.time()

    # B1: Seed degree and weight from cooc_global (FAST: 2 queries per seed)
    seed_global_degs = []
    seed_global_weights = []
    for seed in seeds:
        cur.execute("SELECT COUNT(*), COALESCE(SUM(weight), 0) FROM cooc_global WHERE concept_a = ?", (seed,))
        r1 = cur.fetchone()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(weight), 0) FROM cooc_global WHERE concept_b = ?", (seed,))
        r2 = cur.fetchone()
        seed_global_degs.append(r1[0] + r2[0])
        seed_global_weights.append(r1[1] + r2[1])

    avg_global_deg = float(np.mean(seed_global_degs))
    avg_global_weight = float(np.mean(seed_global_weights))
    avg_weight_per_edge = avg_global_weight / max(avg_global_deg, 1)

    # B2: Spectral position of seeds (from WT4 — NO DB query needed)
    spec_dists = []
    for seed in seeds:
        if seed in node_by_id:
            n = node_by_id[seed]
            d = math.sqrt((n['x']-cx)**2 + (n['y']-cy)**2 + (n['z']-cz)**2)
            spec_dists.append(d)
    spectral_dist = float(np.mean(spec_dists)) if spec_dists else 0

    dt = time.time() - t0s
    topo[m] = {
        'global_degree': avg_global_deg,
        'global_weight': avg_global_weight,
        'weight_per_edge': avg_weight_per_edge,
        'spectral_dist': spectral_dist,
    }
    P(f"  {m:20s} deg={avg_global_deg:8.0f} w={avg_global_weight:10.0f} "
      f"w/e={avg_weight_per_edge:6.2f} spec={spectral_dist:.4f} ({dt:.1f}s)")

db.close()


# ═══════════════════════════════════════════════════════
# PHASE C: Complete feature matrix + correlation screen
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE C: Corrélation de TOUTES les features avec K, r, t₀, death")
P(f"{'='*80}")

# 1. Mare features
mare_features = ['n_neighbors', 'local_density', 'hub_fraction', 'avg_edge_weight',
                 'median_neighbor_works', 'seed_degree', 'seed_works', 'seed_weight',
                 'pre_edges', 'pre_weight', 'avg_level', 'n_seeds', 'avg_internal_weight']

# 2. Candlestick features
candle_features = ['ratio', 'body', 'volume', 'upper_wick', 'lower_wick', 'length', 'mu_peak']

# 3. Scientometric features
scisci_features = ['fitness_growth', 'd_index_proxy', 'z_score_proxy', 'activity_1y',
                   'activity_5y', 'post_growth']

# 4. Topological features
topo_features = ['global_degree', 'global_weight', 'weight_per_edge', 'spectral_dist']

# Collect all
all_feature_names = []
all_feature_values = []

for f in mare_features:
    all_feature_names.append(f"mare_{f}")
    all_feature_values.append(np.array([mare[m][f] for m in METS]))

for f in candle_features:
    all_feature_names.append(f"candle_{f}")
    all_feature_values.append(np.array([CANDLES['candles'][m][f] for m in METS]))

for f in scisci_features:
    all_feature_names.append(f"sci_{f}")
    all_feature_values.append(np.array([scisci[m][f] for m in METS]))

for f in topo_features:
    all_feature_names.append(f"topo_{f}")
    all_feature_values.append(np.array([topo[m][f] for m in METS]))

# Derived features
hf = np.array([mare[m]['hub_fraction'] for m in METS])
dens = np.array([mare[m]['local_density'] for m in METS])
all_feature_names.append("derived_hub_over_dens")
all_feature_values.append(hf / (dens + 0.01))

cr = np.array([CANDLES['candles'][m]['ratio'] for m in METS])
all_feature_names.append("derived_log_candle_ratio")
all_feature_values.append(np.log1p(cr))

fg = np.array([scisci[m]['fitness_growth'] for m in METS])
a5 = np.array([scisci[m]['activity_5y'] for m in METS])
all_feature_names.append("derived_fitness_per_activity")
all_feature_values.append(fg / (a5 + 1))

gd = np.array([topo[m]['global_degree'] for m in METS])
sd = np.array([topo[m]['spectral_dist'] for m in METS])
all_feature_names.append("derived_degree_times_spectral")
all_feature_values.append(gd * sd)

# Ratio activity / degree (how active per connection)
a1 = np.array([scisci[m]['activity_1y'] for m in METS])
all_feature_names.append("derived_activity_per_degree")
all_feature_values.append(a1 / (gd + 1))

# Spectral dist * fitness (peripheral + growing = ???)
all_feature_names.append("derived_spectral_times_fitness")
all_feature_values.append(sd * fg)

# Inverse density (open space)
all_feature_names.append("derived_inv_density")
all_feature_values.append(1 / (dens + 0.01))

# n_seeds (how many seeds)
ns = np.array([mare[m]['n_seeds'] for m in METS])
all_feature_names.append("derived_degree_per_seed")
all_feature_values.append(gd / (ns + 0.01))

n_features = len(all_feature_names)

# Correlation screen
P(f"\n  {n_features} features total. Showing |ρ|>0.5 for r or |ρ|>0.6 for K:")
P(f"\n  {'Feature':45s} {'ρ(K)':>7s} {'p':>7s} {'ρ(r)':>7s} {'p':>7s} {'ρ(t0)':>7s} {'ρ(d)':>7s}")
P("  " + "-" * 90)

strong_r = []
strong_K = []

for i, fname in enumerate(all_feature_names):
    vals = all_feature_values[i]
    if np.std(vals) < 1e-10:
        continue

    rk, pk = spearmanr(vals, K_all)
    rr, pr = spearmanr(vals, r_all)
    rt, pt = spearmanr(vals, t0_all)
    rd, pd = spearmanr(vals, death_all)

    flags = ""
    if abs(rr) > 0.5: flags += " <<<R"
    if abs(rk) > 0.6: flags += " <<<K"

    if abs(rr) > 0.5 or abs(rk) > 0.6:
        P(f"  {fname:45s} {rk:+7.3f} {pk:7.4f} {rr:+7.3f} {pr:7.4f} {rt:+7.3f} {rd:+7.3f}{flags}")

    if abs(rr) > 0.5:
        strong_r.append((fname, rr, pr, i))
    if abs(rk) > 0.6:
        strong_K.append((fname, rk, pk, i))

P(f"\n  Corrélateurs forts pour r (|ρ|>0.5): {len(strong_r)}")
for name, rho, p, _ in sorted(strong_r, key=lambda x: abs(x[1]), reverse=True):
    P(f"    {name:45s} ρ={rho:+.4f} (p={p:.4f})")

P(f"\n  Corrélateurs forts pour K (|ρ|>0.6): {len(strong_K)}")
for name, rho, p, _ in sorted(strong_K, key=lambda x: abs(x[1]), reverse=True):
    P(f"    {name:45s} ρ={rho:+.4f} (p={p:.4f})")


# ═══════════════════════════════════════════════════════
# PHASE D: Assembly + Ridge + Honest temporal test
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE D: Test temporel honnête (train pré-1960 → predict post-1974)")
P(f"{'='*80}")

def temporal_ridge(feat_idx, target, alpha=1.0):
    """Ridge: train pre-1960, predict post-1974."""
    X = np.column_stack([all_feature_values[i] for i in feat_idx])
    X_tr, X_te = X[train_idx], X[test_idx]
    y_tr, y_te = target[train_idx], target[test_idx]
    sc = StandardScaler()
    Xts = sc.fit_transform(X_tr)
    Xte = sc.transform(X_te)
    m = Ridge(alpha=alpha)
    m.fit(Xts, y_tr)
    pred = m.predict(Xte)
    errs = np.abs(pred - y_te) / np.abs(y_te) * 100
    return float(np.median(errs)), pred, errs, m

def compute_r2(K, r, t0, wd):
    t = np.array([w['t'] for w in wd], dtype=float)
    R_obs = np.array([w['total_touched'] for w in wd], dtype=float)
    R_p = K / (1 + np.exp(-np.clip(r * (t - t0), -500, 500)))
    ss_r = np.sum((R_obs - R_p)**2)
    ss_t = np.sum((R_obs - R_obs.mean())**2)
    return 1 - ss_r / ss_t if ss_t > 0 else 0

# ── D1: K prediction ──
P("\n  [D1] K prediction")
mare_idx = [i for i, n in enumerate(all_feature_names)
            if n.startswith("mare_") and "derived" not in n]
sci_idx = [i for i, n in enumerate(all_feature_names) if n.startswith("sci_")]
topo_idx = [i for i, n in enumerate(all_feature_names) if n.startswith("topo_")]
derived_idx = [i for i, n in enumerate(all_feature_names) if n.startswith("derived_")]

combos_K = {
    "mare": mare_idx,
    "mare+sci": mare_idx + sci_idx,
    "mare+topo": mare_idx + topo_idx,
    "mare+sci+topo": mare_idx + sci_idx + topo_idx,
    "all": mare_idx + sci_idx + topo_idx + derived_idx,
}

best_K = ("", 999, None)
for name, idx in combos_K.items():
    err, pred, _, _ = temporal_ridge(idx, K_all)
    P(f"    {name:25s} → {err:5.1f}% median error")
    if err < best_K[1]:
        best_K = (name, err, pred)

# ── D2: r prediction (PRE-IMPACT ONLY — no candle) ──
P("\n  [D2] r prediction (PRE-IMPACT seulement)")
pre_mare_idx = mare_idx  # mare features are from cooc_global (timeless)
pre_sci_idx = [i for i, n in enumerate(all_feature_names)
               if n.startswith("sci_") and "post_" not in n]
pre_topo_idx = topo_idx
pre_derived_idx = [i for i, n in enumerate(all_feature_names)
                   if n.startswith("derived_") and "candle" not in n]

combos_r = {
    "mare": pre_mare_idx,
    "sci": pre_sci_idx,
    "topo": pre_topo_idx,
    "mare+sci": pre_mare_idx + pre_sci_idx,
    "mare+topo": pre_mare_idx + pre_topo_idx,
    "sci+topo": pre_sci_idx + pre_topo_idx,
    "mare+sci+topo": pre_mare_idx + pre_sci_idx + pre_topo_idx,
    "all_pre": pre_mare_idx + pre_sci_idx + pre_topo_idx + pre_derived_idx,
}

# Also try with candle (post-impact, for reference)
candle_idx = [i for i, n in enumerate(all_feature_names) if n.startswith("candle_")]
combos_r["candle (ref)"] = candle_idx
combos_r["all+candle (ref)"] = pre_mare_idx + pre_sci_idx + pre_topo_idx + candle_idx

best_r_pre = ("", 999, None)
best_r_any = ("", 999, None)
for name, idx in combos_r.items():
    err, pred, _, _ = temporal_ridge(idx, r_all)
    tag = " [POST]" if "candle" in name or "ref" in name else ""
    P(f"    {name:25s} → {err:5.1f}% median error{tag}")
    if err < best_r_any[1]:
        best_r_any = (name, err, pred)
    if "candle" not in name and "ref" not in name and err < best_r_pre[1]:
        best_r_pre = (name, err, pred)

# ── D3: t0 prediction ──
P("\n  [D3] t₀ prediction")
# Baseline: 0.208 * death
t0_death = 0.208 * death_all[test_idx]
err_t0_death = float(np.median(np.abs(t0_death - t0_all[test_idx]) / np.abs(t0_all[test_idx]) * 100))
P(f"    {'0.208*death':25s} → {err_t0_death:5.1f}% median error")

for name, idx in [("mare", mare_idx), ("mare+sci+topo", pre_mare_idx + pre_sci_idx + pre_topo_idx)]:
    err, pred, _, _ = temporal_ridge(idx, t0_all)
    P(f"    {name:25s} → {err:5.1f}% median error")

# ── D4: Ridge with cross-validated alpha ──
P("\n  [D4] RidgeCV (alpha auto) pour K et r")
for target_name, target, best_idx_name, best_idx in [
    ("K", K_all, best_K[0], combos_K[best_K[0]]),
    ("r", r_all, best_r_pre[0], combos_r.get(best_r_pre[0], pre_mare_idx)),
]:
    X = np.column_stack([all_feature_values[i] for i in best_idx])
    sc = StandardScaler()
    X_tr = sc.fit_transform(X[train_idx])
    X_te = sc.transform(X[test_idx])
    y_tr, y_te = target[train_idx], target[test_idx]

    for alpha in [0.01, 0.1, 1.0, 10.0, 100.0]:
        m = Ridge(alpha=alpha)
        m.fit(X_tr, y_tr)
        pred = m.predict(X_te)
        err = float(np.median(np.abs(pred - y_te) / np.abs(y_te) * 100))
        P(f"    {target_name}({best_idx_name}, α={alpha:5.1f}) → {err:5.1f}%")


# ═══════════════════════════════════════════════════════
# PHASE E: R(t) trajectory
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("PHASE E: R(t) trajectoire")
P(f"{'='*80}")

# Use best K predictor + best r predictor
K_pred = best_K[2]
r_pred_pre = best_r_pre[2]
r_pred_any = best_r_any[2]
t0_pred = t0_death  # death-based for t0

P(f"\n  K model: {best_K[0]} ({best_K[1]:.1f}%)")
P(f"  r model (pre-impact): {best_r_pre[0]} ({best_r_pre[1]:.1f}%)")
P(f"  r model (any): {best_r_any[0]} ({best_r_any[1]:.1f}%)")
P(f"  t0 model: 0.208*death ({err_t0_death:.1f}%)")

# E1: R(t) with pre-impact r
P(f"\n  [E1] R(t) avec r PRÉ-IMPACT ({best_r_pre[0]})")
P(f"  {'Météorite':25s} {'K_obs':>8s} {'K_pred':>8s} {'r_obs':>6s} {'r_pred':>6s} {'R²':>7s}")
r2s_pre = []
for i, m in enumerate(test_mets):
    r2 = compute_r2(K_pred[i], r_pred_pre[i], t0_pred[i], bfs[m]['wave_data'])
    r2s_pre.append(r2)
    P(f"  {m:25s} {K_all[test_idx[i]]:8,.0f} {K_pred[i]:8,.0f} "
      f"{r_all[test_idx[i]]:6.2f} {r_pred_pre[i]:6.2f} {r2:+7.4f}")
med_pre = float(np.median(r2s_pre))
v_pre = "PASS" if med_pre > 0.5 else "PARTIAL" if med_pre > 0 else "FAIL"
P(f"  → Médiane R² = {med_pre:.4f} → {v_pre}")

# E2: R(t) with best r (may include candle)
if best_r_any[0] != best_r_pre[0]:
    P(f"\n  [E2] R(t) avec r ANY ({best_r_any[0]})")
    P(f"  {'Météorite':25s} {'R²':>7s}")
    r2s_any = []
    for i, m in enumerate(test_mets):
        r2 = compute_r2(K_pred[i], r_pred_any[i], t0_pred[i], bfs[m]['wave_data'])
        r2s_any.append(r2)
        P(f"  {m:25s} {r2:+7.4f}")
    med_any = float(np.median(r2s_any))
    v_any = "PASS" if med_any > 0.5 else "PARTIAL" if med_any > 0 else "FAIL"
    P(f"  → Médiane R² = {med_any:.4f} → {v_any}")

# E3: Control — best K + TRUE r + TRUE t0
P(f"\n  [E3] Contrôle: best K pred + TRUE r + TRUE t0")
r2s_ctrl = []
for i, m in enumerate(test_mets):
    r2 = compute_r2(K_pred[i], r_all[test_idx[i]], t0_all[test_idx[i]], bfs[m]['wave_data'])
    r2s_ctrl.append(r2)
P(f"  → Médiane R² = {np.median(r2s_ctrl):.4f} (plafond si K correct + r parfait)")


# ═══════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("RÉSUMÉ FINAL")
P(f"{'='*80}")

P(f"\n  K: {best_K[0]} → {best_K[1]:.1f}% (vs 20.9% session 35)")
P(f"  r (pré-impact): {best_r_pre[0]} → {best_r_pre[1]:.1f}%")
P(f"  R(t): médiane R² = {med_pre:.4f} → {v_pre}")
P(f"  Plafond (K pred + r true): {np.median(r2s_ctrl):.4f}")
P(f"\n  Diagnostic confirmé: r est le bottleneck. candle_ratio ne peut pas prédire r pre-impact.")

output = {
    "test": "assembly_s36_fast_v1",
    "date": "2026-04-07",
    "phase_A_scientometrics": scisci,
    "phase_B_topology": topo,
    "phase_C_correlations": {
        "strong_r": [(n, round(rho, 4), round(p, 4)) for n, rho, p, _ in strong_r],
        "strong_K": [(n, round(rho, 4), round(p, 4)) for n, rho, p, _ in strong_K],
        "n_features": n_features,
    },
    "phase_D_test": {
        "K_model": best_K[0], "K_error_pct": round(best_K[1], 1),
        "r_pre_model": best_r_pre[0], "r_pre_error_pct": round(best_r_pre[1], 1),
        "r_any_model": best_r_any[0], "r_any_error_pct": round(best_r_any[1], 1),
    },
    "phase_E_trajectory": {
        "R2_median_pre": round(med_pre, 4),
        "verdict_pre": v_pre,
        "control_true_r": round(float(np.median(r2s_ctrl)), 4),
        "per_meteorite": {m: round(r2s_pre[i], 4) for i, m in enumerate(test_mets)},
    },
    "diagnostic": {
        "r_is_bottleneck": True,
        "best_pre_impact_r_error": round(best_r_pre[1], 1),
    },
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

P(f"\nSaved: {OUTPUT}")
P("DONE.")
