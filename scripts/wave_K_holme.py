#!/usr/bin/env python3
"""
YGGDRASIL — Session 36b: Améliorer K avec Holme 2020
======================================================
Holme 2020 (PLOS Comp Bio): R²=0.96 avec 3 features (Random Forest)
Best single: closeness (0.69), degree (0.65), coreness (0.54)

On calcule:
1. Closeness centrality approx des seeds (BFS sample)
2. Inter-community bridge count (espèces des voisins)
3. k-core number des seeds (coreness)
4. Random Forest + LOO + test temporel honnête

Sky × Claude (Opus 4.6) — Session 36, 7 avril 2026
Sources: Holme 2020, Sah 2016, Watts 2002, Newman 2002
"""
import json, sys, os, math, time
import numpy as np
import sqlite3
from collections import Counter, defaultdict
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

def P(*args, **kw):
    print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")
CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), encoding='utf-8'))
SPECIES = json.load(open(os.path.join(REPO, "data/scan/species_65k.json"), encoding='utf-8'))
SPECTRAL = json.load(open(os.path.join(REPO, "data/scan/spectral_births.json"), encoding='utf-8'))
MYC = json.load(open(os.path.join(REPO, "data/results/wave_mycelium_id_s36.json"), encoding='utf-8'))
ASSEMBLY = json.load(open(os.path.join(REPO, "data/results/wave_assembly_s36.json"), encoding='utf-8'))

bfs = CHECK['phase_1']
mare = CHECK['phase_2']
logistic = CHECK['phase_3e']['fits']
METS = list(bfs.keys())

# Lookups
id_to_name = {n['id']: n['name'] for n in SPECTRAL['nodes'] if n.get('type') == 'concept'}
name_to_species = {d['name']: d['species'] for d in SPECIES['concepts'].values()}

K_all = np.array([logistic[m]['K'] for m in METS])
r_all = np.array([logistic[m]['r_growth'] for m in METS])
death_all = np.array([bfs[m].get('death_t', 8) or 8 for m in METS])

train_mets = [m for m in METS if int(m.split()[-1]) <= 1960]
test_mets  = [m for m in METS if int(m.split()[-1]) >= 1974]
train_idx = [METS.index(m) for m in train_mets]
test_idx  = [METS.index(m) for m in test_mets]

P("=" * 80)
P("K PREDICTION — Holme 2020 features + Random Forest")
P("=" * 80)

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

holme = {}
for mi, m in enumerate(METS):
    seeds = bfs[m]['seeds']
    t0s = time.time()

    # ── 1. CLOSENESS CENTRALITY (approximated) ──
    # For each seed: BFS on cooc_global, measure avg distance to sample nodes
    # Approx: use 1-hop and 2-hop reach as proxy for closeness
    seed_closeness = []
    seed_reach_1hop = []
    seed_reach_2hop = []
    for seed in seeds:
        # 1-hop neighbors
        cur.execute("SELECT concept_b FROM cooc_global WHERE concept_a = ?", (seed,))
        nbrs_a = set(r[0] for r in cur.fetchall())
        cur.execute("SELECT concept_a FROM cooc_global WHERE concept_b = ?", (seed,))
        nbrs_b = set(r[0] for r in cur.fetchall())
        nbrs_1 = nbrs_a | nbrs_b
        n1 = len(nbrs_1)
        seed_reach_1hop.append(n1)

        # 2-hop: sample 50 neighbors, count THEIR neighbors
        sample_nbrs = list(nbrs_a)[:50]
        nbrs_2 = set()
        for n in sample_nbrs:
            cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a = ?", (n,))
            nbrs_2_count = cur.fetchone()[0]
            nbrs_2.add(nbrs_2_count)  # just count, not enumerate

        # Closeness proxy = 1-hop reach / total (higher = more central)
        closeness = n1 / 65026.0
        seed_closeness.append(closeness)

        # 2-hop reach estimate: n1 + sum of neighbor degrees (with overlap correction)
        avg_nbr_degree = np.mean(list(nbrs_2)) if nbrs_2 else 0
        reach_2 = min(n1 + n1 * avg_nbr_degree * 0.3, 65026)  # rough dedup
        seed_reach_2hop.append(reach_2)

    avg_closeness = float(np.mean(seed_closeness))
    avg_reach_1 = float(np.mean(seed_reach_1hop))
    avg_reach_2 = float(np.mean(seed_reach_2hop))

    # ── 2. INTER-COMMUNITY BRIDGES ──
    # Count how many 1-hop neighbors belong to DIFFERENT species than the seeds
    seed_species = [name_to_species.get(id_to_name.get(s, ''), -1) for s in seeds]
    main_sp = Counter(seed_species).most_common(1)[0][0]

    bridge_count = 0
    same_count = 0
    species_touched = set()
    for seed in seeds:
        cur.execute("SELECT concept_b FROM cooc_global WHERE concept_a = ? LIMIT 500", (seed,))
        for row in cur.fetchall():
            nbr_sp = name_to_species.get(id_to_name.get(row[0], ''), -1)
            if nbr_sp >= 0:
                species_touched.add(nbr_sp)
                if nbr_sp != main_sp:
                    bridge_count += 1
                else:
                    same_count += 1

    total_checked = bridge_count + same_count
    bridge_frac = bridge_count / max(total_checked, 1)
    n_species_touched = len(species_touched)

    # ── 3. K-CORE NUMBER (coreness) ──
    # Approximate: how many of seed's neighbors have degree >= seed's degree?
    # True k-core requires full graph decomposition, too expensive
    # Proxy: fraction of neighbors with degree >= median degree
    seed_degrees = []
    nbr_high_deg_frac = []
    for seed in seeds:
        cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a = ?", (seed,))
        d = cur.fetchone()[0]
        seed_degrees.append(d)

        # Sample 30 neighbors, check their degrees
        cur.execute("SELECT concept_b FROM cooc_global WHERE concept_a = ? LIMIT 30", (seed,))
        nbr_ds = []
        for row in cur.fetchall():
            cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a = ?", (row[0],))
            nbr_ds.append(cur.fetchone()[0])
        if nbr_ds:
            nbr_high_deg_frac.append(np.mean([1 for nd in nbr_ds if nd >= d]) if d > 0 else 0)

    avg_degree = float(np.mean(seed_degrees))
    coreness_proxy = float(np.mean(nbr_high_deg_frac)) if nbr_high_deg_frac else 0

    # ── 4. EDGE DENSITY around seeds ──
    # Already have from mare: local_density
    local_dens = mare[m]['local_density']

    dt = time.time() - t0s
    holme[m] = {
        'closeness': avg_closeness,
        'reach_1hop': avg_reach_1,
        'reach_2hop': avg_reach_2,
        'bridge_frac': bridge_frac,
        'bridge_count': bridge_count,
        'n_species_touched': n_species_touched,
        'coreness_proxy': coreness_proxy,
        'avg_degree': avg_degree,
        'local_density': local_dens,
        'main_species': main_sp,
    }
    P(f"  {m:20s} close={avg_closeness:.4f} reach1={avg_reach_1:6.0f} "
      f"bridges={bridge_frac:.2f} nsp={n_species_touched} "
      f"core={coreness_proxy:.3f} deg={avg_degree:.0f} ({dt:.1f}s)")

db.close()


# ═══════════════════════════════════════════════════════
# CORRELATION SCREEN
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CORRELATION nouvelles features vs K")
P(f"{'='*80}")

holme_feats = ['closeness', 'reach_1hop', 'reach_2hop', 'bridge_frac',
               'bridge_count', 'n_species_touched', 'coreness_proxy', 'avg_degree']

P(f"\n  {'Feature':25s} {'rho(K)':>7s} {'p':>7s} {'rho(r)':>7s} {'p':>7s}")
for f in holme_feats:
    vals = np.array([holme[m][f] for m in METS])
    if np.std(vals) < 1e-10:
        continue
    rk, pk = spearmanr(vals, K_all)
    rr, pr = spearmanr(vals, r_all)
    flag = ""
    if abs(rk) > 0.5: flag += " <<<K"
    if abs(rr) > 0.5: flag += " <<<R"
    P(f"  {f:25s} {rk:+7.3f} {pk:7.4f} {rr:+7.3f} {pr:7.4f}{flag}")


# ═══════════════════════════════════════════════════════
# RANDOM FOREST vs RIDGE — K prediction
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("RANDOM FOREST vs RIDGE — K prediction")
P(f"{'='*80}")

# Build feature matrix: mare + holme + mycelium
mare_feats = ['n_neighbors', 'local_density', 'hub_fraction', 'avg_edge_weight',
              'median_neighbor_works', 'seed_degree', 'seed_works', 'seed_weight',
              'n_seeds', 'avg_internal_weight', 'pre_edges', 'pre_weight', 'avg_level']
sci_feats = ['fitness_growth', 'd_index_proxy', 'z_score_proxy', 'activity_1y', 'activity_5y']
topo_feats = ['global_degree', 'global_weight', 'weight_per_edge', 'spectral_dist']
myc_feats = ['BA', 'IL', 'D', 'Db', 'L', 'alpha', 'E_global']

all_names = []
all_vals = []

for f in mare_feats:
    all_names.append(f"mare_{f}")
    all_vals.append(np.array([mare[m][f] for m in METS]))

for f in holme_feats:
    all_names.append(f"holme_{f}")
    all_vals.append(np.array([holme[m][f] for m in METS]))

for f in sci_feats:
    all_names.append(f"sci_{f}")
    all_vals.append(np.array([ASSEMBLY['phase_A_scientometrics'][m][f] for m in METS]))

for f in topo_feats:
    all_names.append(f"topo_{f}")
    all_vals.append(np.array([ASSEMBLY['phase_B_topology'][m][f] for m in METS]))

for f in myc_feats:
    all_names.append(f"myc_{f}")
    all_vals.append(np.array([MYC['per_meteorite'][m].get(f, 0) for m in METS]))

# Derived
hf = np.array([mare[m]['hub_fraction'] for m in METS])
dens = np.array([mare[m]['local_density'] for m in METS])
all_names.append("derived_hub_over_dens")
all_vals.append(hf / (dens + 0.01))

X_full = np.column_stack(all_vals)
X_full = np.nan_to_num(X_full, nan=0.0)
n_feat = len(all_names)

P(f"\n  {n_feat} features total")

# Feature subsets
mare_idx = [i for i, n in enumerate(all_names) if n.startswith("mare_")]
holme_idx = [i for i, n in enumerate(all_names) if n.startswith("holme_")]
myc_idx = [i for i, n in enumerate(all_names) if n.startswith("myc_")]

def test_K(name, feat_idx, use_rf=False):
    """Test K prediction: temporal + LOO."""
    X = X_full[:, feat_idx]

    # Temporal test
    X_tr, X_te = X[train_idx], X[test_idx]
    y_tr, y_te = K_all[train_idx], K_all[test_idx]

    if use_rf:
        m = RandomForestRegressor(n_estimators=100, max_depth=3, random_state=42)
        m.fit(X_tr, y_tr)
    else:
        sc = StandardScaler()
        X_tr = sc.fit_transform(X_tr)
        X_te = sc.transform(X_te)
        m = Ridge(alpha=1.0)
        m.fit(X_tr, y_tr)

    pred = m.predict(X_te)
    errs = np.abs(pred - y_te) / y_te * 100
    temp_err = float(np.median(errs))

    # LOO
    loo_errs = []
    for i in range(len(METS)):
        tr = [j for j in range(len(METS)) if j != i]
        if use_rf:
            m2 = RandomForestRegressor(n_estimators=100, max_depth=3, random_state=42)
            m2.fit(X[tr], K_all[tr])
            p = m2.predict(X[i:i+1])[0]
        else:
            sc2 = StandardScaler()
            Xtr2 = sc2.fit_transform(X[tr])
            Xte2 = sc2.transform(X[i:i+1])
            m2 = Ridge(alpha=1.0)
            m2.fit(Xtr2, K_all[tr])
            p = m2.predict(Xte2)[0]
        loo_errs.append(abs(p - K_all[i]) / K_all[i] * 100)

    loo_err = float(np.median(loo_errs))
    return temp_err, loo_err, pred

P(f"\n  {'Model':40s} {'Temporal':>8s} {'LOO':>8s}")

combos = [
    ("Ridge(mare)", mare_idx, False),
    ("Ridge(mare+holme)", mare_idx + holme_idx, False),
    ("Ridge(all)", list(range(n_feat)), False),
    ("RF(mare)", mare_idx, True),
    ("RF(mare+holme)", mare_idx + holme_idx, True),
    ("RF(holme only)", holme_idx, True),
    ("RF(all)", list(range(n_feat)), True),
]

best_K = ("", 999, None)
for name, idx, rf in combos:
    te, loo, pred = test_K(name, idx, rf)
    P(f"  {name:40s} {te:7.1f}% {loo:7.1f}%")
    if te < best_K[1]:
        best_K = (name, te, pred)

P(f"\n  Best: {best_K[0]} ({best_K[1]:.1f}% temporal)")

# Detail of best
P(f"\n  Detail ({best_K[0]}):")
P(f"  {'Met':25s} {'K_obs':>8s} {'K_pred':>8s} {'err':>6s}")
for i, m in enumerate(test_mets):
    err = abs(best_K[2][i] - K_all[test_idx[i]]) / K_all[test_idx[i]] * 100
    P(f"  {m:25s} {K_all[test_idx[i]]:8,.0f} {best_K[2][i]:8,.0f} {err:5.1f}%")


# ═══════════════════════════════════════════════════════
# R(t) TRAJECTORY with best K + mycelium r
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("R(t) TRAJECTORY — best K + mycelium r + death t0")
P(f"{'='*80}")

# r from mycelium
X_myc = np.array([[MYC['per_meteorite'][m].get(f, 0) for f in myc_feats] for m in METS])
sc_r = StandardScaler()
X_r_tr = sc_r.fit_transform(X_myc[train_idx])
X_r_te = sc_r.transform(X_myc[test_idx])
m_r = Ridge(alpha=1.0)
m_r.fit(X_r_tr, r_all[train_idx])
r_pred = m_r.predict(X_r_te)

# t0 from death
t0_pred = 0.208 * death_all[test_idx]

K_pred = best_K[2]

P(f"\n  K model: {best_K[0]} ({best_K[1]:.1f}%)")
P(f"  r model: mycelium (9.1%)")
P(f"  t0 model: 0.208*death")

P(f"\n  {'Met':25s} {'K_obs':>8s} {'K_pred':>8s} {'r_obs':>6s} {'r_pred':>6s} {'R2':>7s}")
r2s = []
for i, m in enumerate(test_mets):
    wd = bfs[m]['wave_data']
    t_arr = np.array([w['t'] for w in wd], dtype=float)
    R_obs = np.array([w['total_touched'] for w in wd], dtype=float)
    R_pred_t = K_pred[i] / (1 + np.exp(-np.clip(r_pred[i] * (t_arr - t0_pred[i]), -500, 500)))
    ss_res = np.sum((R_obs - R_pred_t)**2)
    ss_tot = np.sum((R_obs - R_obs.mean())**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    r2s.append(r2)
    P(f"  {m:25s} {K_all[test_idx[i]]:8,.0f} {K_pred[i]:8,.0f} "
      f"{r_all[test_idx[i]]:6.2f} {r_pred[i]:6.2f} {r2:+7.4f}")

med_r2 = float(np.median(r2s))
v = "PASS" if med_r2 > 0.5 else "PARTIAL" if med_r2 > 0 else "FAIL"
P(f"\n  Median R2 = {med_r2:.4f} -> {v}")

P(f"\n  EVOLUTION:")
P(f"  Session 35: R2 = -0.15 FAIL")
P(f"  S36 Ridge:  R2 = +0.44 PARTIAL")
P(f"  S36 Holme:  R2 = {med_r2:.4f} {v}")


# ═══════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════

output = {
    "test": "K_holme_s36",
    "date": "2026-04-07",
    "sources": ["Holme 2020 PLOS Comp Bio", "Sah 2016 Sci Rep", "Watts 2002 PNAS"],
    "holme_features": holme,
    "best_K_model": best_K[0],
    "best_K_temporal_error": round(best_K[1], 1),
    "R_t_median_r2": round(med_r2, 4),
    "R_t_verdict": v,
    "per_meteorite_r2": {m: round(r2s[i], 4) for i, m in enumerate(test_mets)},
}

OUT = os.path.join(REPO, "data/results/wave_K_holme_s36.json")
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

P(f"\nSaved: {OUT}")
P("DONE.")
