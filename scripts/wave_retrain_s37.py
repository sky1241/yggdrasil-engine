#!/usr/bin/env python3
"""
YGGDRASIL — Session 37: Retrain sur 36 météorites
====================================================
Merge 13 originales + 23 nouvelles.
Mesurer curseurs mycéliens pour les 23 nouvelles.
Retrain K (Ridge) + r (mycelium) sur 17 train → predict 19 test.
R(t) trajectoire.

Sky × Claude (Opus 4.6) — Session 37, 8 avril 2026
"""
import json, sys, os, math, time
import numpy as np
import sqlite3
from collections import defaultdict
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor

sys.stdout.reconfigure(encoding='utf-8')

def P(*args, **kw):
    print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")

# Load original 13
CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), encoding='utf-8'))
MYC_ORIG = json.load(open(os.path.join(REPO, "data/results/wave_mycelium_id_s36.json"), encoding='utf-8'))
SPECTRAL = json.load(open(os.path.join(REPO, "data/scan/spectral_births.json"), encoding='utf-8'))

# Load 25 new (23 OK)
EXPAND = json.load(open(os.path.join(REPO, "data/results/wave_expand_checkpoint.json"), encoding='utf-8'))

node_by_id = {n['id']: n for n in SPECTRAL['nodes']}
N_CONCEPTS = 65026

# ═══════════════════════════════════════════════════════
# BUILD UNIFIED DATASET
# ═══════════════════════════════════════════════════════

P("=" * 80)
P("RETRAIN SUR 36 METEORITES")
P("=" * 80)

# Merge all meteorites into one structure
all_mets = []  # list of (name, year, seeds, K, r, t0, death, mare, wave_data)

# Original 13
orig_bfs = CHECK['phase_1']
orig_mare = CHECK['phase_2']
orig_log = CHECK['phase_3e']['fits']
for m in orig_bfs:
    year = int(m.split()[-1])
    all_mets.append({
        'name': m,
        'year': year,
        'seeds': orig_bfs[m]['seeds'],
        'K': orig_log[m]['K'],
        'r': orig_log[m]['r_growth'],
        't0': orig_log[m]['t0'],
        'death': orig_bfs[m].get('death_t', 8) or 8,
        'mare': orig_mare[m],
        'wave_data': orig_bfs[m]['wave_data'],
        'source': 'original',
    })

# New 23 (skip DEAD)
for name, d in EXPAND.items():
    if d['phase_3']['K'] <= 100:
        continue
    year = d['phase_1']['open_year']
    all_mets.append({
        'name': name,
        'year': year,
        'seeds': d['phase_1']['seeds'],
        'K': d['phase_3']['K'],
        'r': d['phase_3']['r_growth'],
        't0': d['phase_3']['t0'],
        'death': d['phase_1']['death_t'],
        'mare': d['phase_2'],
        'wave_data': d['phase_1']['wave_data'],
        'source': 'expand',
    })

# Sort by year
all_mets.sort(key=lambda x: x['year'])
NAMES = [m['name'] for m in all_mets]
N_METS = len(all_mets)

# Split: train <= 1960, test >= 1973
train_idx = [i for i, m in enumerate(all_mets) if m['year'] <= 1960]
test_idx  = [i for i, m in enumerate(all_mets) if m['year'] >= 1973]

P(f"\n  Total: {N_METS} meteorites ({len(train_idx)} train, {len(test_idx)} test)")
P(f"  Train: {[all_mets[i]['name'] for i in train_idx]}")
P(f"  Test:  {[all_mets[i]['name'] for i in test_idx]}")

K_all = np.array([m['K'] for m in all_mets])
r_all = np.array([m['r'] for m in all_mets])
death_all = np.array([m['death'] for m in all_mets])


# ═══════════════════════════════════════════════════════
# MEASURE MYCELIUM CURSORS FOR NEW METEORITES
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CURSEURS MYCELIENS — mesure pour les nouvelles meteorites")
P(f"{'='*80}")

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

# Spectral center
all_x = [n['x'] for n in SPECTRAL['nodes']]
all_y = [n['y'] for n in SPECTRAL['nodes']]
all_z = [n['z'] for n in SPECTRAL['nodes']]
cx, cy, cz = np.mean(all_x), np.mean(all_y), np.mean(all_z)

myc_all = {}

for mi, met in enumerate(all_mets):
    name = met['name']

    # Use cached if original
    if met['source'] == 'original' and name in MYC_ORIG['per_meteorite']:
        myc_all[name] = MYC_ORIG['per_meteorite'][name]
        continue

    seeds = met['seeds']
    t0s = time.time()

    # Build local subgraph: seeds + top 150 neighbors
    edges = {}
    for seed in seeds:
        cur.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a = ? ORDER BY weight DESC LIMIT 150", (seed,))
        for row in cur.fetchall():
            a, b = min(seed, row[0]), max(seed, row[0])
            edges[(a, b)] = max(edges.get((a, b), 0), row[1])

    all_nodes = set()
    for (a, b) in edges:
        all_nodes.add(a)
        all_nodes.add(b)
    node_list = sorted(all_nodes)
    node_idx = {n: i for i, n in enumerate(node_list)}
    N = len(node_list)

    if N < 5:
        myc_all[name] = {'BA': 0, 'IL': 0, 'D': 0, 'Db': 1, 'L': 0, 'alpha': 0, 'E_global': 0}
        P(f"  {name:25s} SKIP (N={N})")
        continue

    # Adjacency
    adj = np.zeros((N, N))
    for (a, b), w in edges.items():
        if a in node_idx and b in node_idx:
            adj[node_idx[a], node_idx[b]] = w
            adj[node_idx[b], node_idx[a]] = w

    # D = log10 edge weights
    weights = adj[adj > 0].flatten()
    D_val = float(np.mean(np.log10(weights))) if len(weights) > 0 else 0

    # Sparsify P90
    if len(weights) > 0:
        threshold = np.percentile(weights, 90)
        sparse = np.where(adj >= threshold, adj, 0)
    else:
        sparse = adj.copy()

    # BA = branching angle (3D spectral positions)
    angles = []
    for i in range(N):
        nid = node_list[i]
        if nid not in node_by_id:
            continue
        ni = node_by_id[nid]
        xi, yi, zi = ni['x'], ni['y'], ni['z']
        neighbors = [j for j in range(N) if j != i and sparse[i, j] > 0]
        if len(neighbors) < 2:
            continue
        for a_i in range(min(len(neighbors), 10)):
            for b_i in range(a_i + 1, min(len(neighbors), 10)):
                ja, jb = neighbors[a_i], neighbors[b_i]
                if node_list[ja] not in node_by_id or node_list[jb] not in node_by_id:
                    continue
                na, nb = node_by_id[node_list[ja]], node_by_id[node_list[jb]]
                va = (na['x']-xi, na['y']-yi, na['z']-zi)
                vb = (nb['x']-xi, nb['y']-yi, nb['z']-zi)
                dot = va[0]*vb[0]+va[1]*vb[1]+va[2]*vb[2]
                ma = math.sqrt(sum(v**2 for v in va))
                mb = math.sqrt(sum(v**2 for v in vb))
                if ma > 0 and mb > 0:
                    cos_a = max(-1, min(1, dot/(ma*mb)))
                    angles.append(math.degrees(math.acos(cos_a)))
    BA_val = float(np.mean(angles)) if angles else 0

    # IL = internodal length
    degrees_s = [(sparse[i] > 0).sum() for i in range(N)]
    bifurc = [i for i in range(N) if degrees_s[i] >= 3]
    binary = (sparse > 0).astype(int)
    il_dists = []
    for src in bifurc[:15]:
        visited = {src: 0}
        queue = [src]
        while queue:
            node = queue.pop(0)
            for nbr in range(N):
                if binary[node, nbr] > 0 and nbr not in visited:
                    visited[nbr] = visited[node] + 1
                    queue.append(nbr)
        for dst in bifurc:
            if dst > src and dst in visited:
                il_dists.append(visited[dst])
    IL_val = float(np.mean(il_dists)) if il_dists else 0

    # Db = box counting 3D
    coords = np.array([(node_by_id[n]['x'], node_by_id[n]['y'], node_by_id[n]['z'])
                        for n in node_list if n in node_by_id])
    if len(coords) >= 3:
        extent = max(coords.max(axis=0) - coords.min(axis=0))
        if extent > 0:
            log_inv, log_n = [], []
            for k in range(1, 8):
                eps = extent / (2**k)
                if eps <= 0: continue
                boxes = set()
                for c in coords:
                    boxes.add(tuple(int((c[d] - coords[:,d].min())/eps) for d in range(3)))
                if boxes:
                    log_inv.append(math.log(1/eps))
                    log_n.append(math.log(len(boxes)))
            Db_val = float(np.polyfit(log_inv, log_n, 1)[0]) if len(log_inv) >= 3 else 1.0
        else:
            Db_val = 1.0
    else:
        Db_val = 1.0

    # L = lacunarity 3D
    lacs = []
    if len(coords) >= 3 and extent > 0:
        for n_div in [3, 5, 7]:
            eps = extent / n_div
            if eps <= 0: continue
            boxes = defaultdict(int)
            for c in coords:
                bx = tuple(int((c[d] - coords[:,d].min())/eps) for d in range(3))
                boxes[bx] += 1
            masses = list(boxes.values()) + [0] * (n_div**3 - len(boxes))
            masses = np.array(masses, dtype=float)
            mu = masses.mean()
            if mu > 0:
                lacs.append(float(masses.var() / (mu**2)))
    L_val = float(np.mean(lacs)) if lacs else 0

    # Meshedness
    n_edges_s = int((sparse > 0).sum()) // 2
    alpha = (n_edges_s - N + 1) / max(2*N - 5, 1)

    # Global efficiency (sample)
    sample = list(range(min(N, 50)))
    eff_sum, eff_count = 0, 0
    for src in sample:
        visited = {src: 0}
        queue = [src]
        while queue:
            node = queue.pop(0)
            for nbr in range(N):
                if binary[node, nbr] > 0 and nbr not in visited:
                    visited[nbr] = visited[node] + 1
                    queue.append(nbr)
        for dst in sample:
            if dst != src and dst in visited and visited[dst] > 0:
                eff_sum += 1.0 / visited[dst]
                eff_count += 1
    E_global = eff_sum / max(eff_count, 1)

    dt = time.time() - t0s
    myc_all[name] = {
        'BA': round(BA_val, 2), 'IL': round(IL_val, 2), 'D': round(D_val, 2),
        'Db': round(Db_val, 3), 'L': round(L_val, 3),
        'alpha': round(alpha, 4), 'E_global': round(E_global, 4),
    }
    P(f"  {name:25s} BA={BA_val:5.1f} Db={Db_val:.3f} alpha={alpha:.4f} Eglob={E_global:.4f} ({dt:.1f}s)")

db.close()


# ═══════════════════════════════════════════════════════
# BUILD FEATURE MATRIX
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("FEATURE MATRIX — mare + mycelium")
P(f"{'='*80}")

mare_feats = ['n_neighbors', 'local_density', 'hub_fraction', 'avg_edge_weight',
              'median_neighbor_works', 'seed_degree', 'seed_works', 'seed_weight',
              'n_seeds', 'avg_internal_weight', 'pre_edges', 'pre_weight', 'avg_level']
myc_feats = ['BA', 'IL', 'D', 'Db', 'L', 'alpha', 'E_global']

X_mare = np.array([[all_mets[i]['mare'].get(f, 0) for f in mare_feats] for i in range(N_METS)])
X_myc = np.array([[myc_all[NAMES[i]].get(f, 0) for f in myc_feats] for i in range(N_METS)])
X_mare = np.nan_to_num(X_mare, nan=0.0)
X_myc = np.nan_to_num(X_myc, nan=0.0)

# Derived
hf = X_mare[:, mare_feats.index('hub_fraction')]
dens = X_mare[:, mare_feats.index('local_density')]
X_derived = (hf / (dens + 0.01)).reshape(-1, 1)

X_K = np.column_stack([X_mare, X_derived])  # K features: mare + hub/dens
X_r = X_myc  # r features: mycelium only


# ═══════════════════════════════════════════════════════
# CORRELATIONS ON 36 METEORITES
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CORRELATIONS SUR 36 METEORITES")
P(f"{'='*80}")

P(f"\n  {'Feature':30s} {'rho(K)':>7s} {'p':>7s} {'rho(r)':>7s} {'p':>7s}")
for i, f in enumerate(mare_feats):
    vals = X_mare[:, i]
    if np.std(vals) < 1e-10: continue
    rk, pk = spearmanr(vals, K_all)
    rr, pr = spearmanr(vals, r_all)
    flag = ""
    if abs(rk) > 0.4: flag += " K"
    if abs(rr) > 0.4: flag += " R"
    if flag:
        P(f"  mare_{f:25s} {rk:+7.3f} {pk:7.4f} {rr:+7.3f} {pr:7.4f}{flag}")

for i, f in enumerate(myc_feats):
    vals = X_myc[:, i]
    if np.std(vals) < 1e-10: continue
    rk, pk = spearmanr(vals, K_all)
    rr, pr = spearmanr(vals, r_all)
    flag = ""
    if abs(rk) > 0.4: flag += " K"
    if abs(rr) > 0.4: flag += " R"
    if flag:
        P(f"  myc_{f:26s} {rk:+7.3f} {pk:7.4f} {rr:+7.3f} {pr:7.4f}{flag}")


# ═══════════════════════════════════════════════════════
# K PREDICTION — Ridge + RF on 17 train → 19 test
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P(f"K PREDICTION — {len(train_idx)} train -> {len(test_idx)} test")
P(f"{'='*80}")

def temporal_test(name, X, target, use_rf=False, alpha=1.0):
    X_tr, X_te = X[train_idx], X[test_idx]
    y_tr, y_te = target[train_idx], target[test_idx]
    if use_rf:
        m = RandomForestRegressor(n_estimators=200, max_depth=4, random_state=42)
        m.fit(X_tr, y_tr)
    else:
        sc = StandardScaler()
        X_tr = sc.fit_transform(X_tr)
        X_te = sc.transform(X_te)
        m = Ridge(alpha=alpha)
        m.fit(X_tr, y_tr)
    pred = m.predict(X_te)
    errs = np.abs(pred - y_te) / np.abs(y_te) * 100
    return float(np.median(errs)), pred

P(f"\n  {'Model':35s} {'K_err':>7s} {'r_err':>7s}")

# K models
for name, X in [("Ridge(mare)", X_K), ("Ridge(mare+myc)", np.column_stack([X_K, X_myc])),
                ("RF(mare)", X_K), ("RF(mare+myc)", np.column_stack([X_K, X_myc]))]:
    rf = name.startswith("RF")
    ke, kp = temporal_test(name, X, K_all, use_rf=rf)
    P(f"  {name:35s} {ke:6.1f}%")

# r models
for name, X in [("Ridge(mycelium)", X_r), ("RF(mycelium)", X_r)]:
    rf = name.startswith("RF")
    re, rp = temporal_test(name, X, r_all, use_rf=rf)
    P(f"  {name:35s}         {re:6.1f}%")

# Best K and r
K_err_ridge, K_pred_ridge = temporal_test("best_K", X_K, K_all)
K_err_rf, K_pred_rf = temporal_test("best_K_rf", X_K, K_all, use_rf=True)
r_err, r_pred = temporal_test("best_r", X_r, r_all)

best_K_err = min(K_err_ridge, K_err_rf)
K_pred = K_pred_ridge if K_err_ridge <= K_err_rf else K_pred_rf
K_method = "Ridge" if K_err_ridge <= K_err_rf else "RF"

P(f"\n  Best K: {K_method} ({best_K_err:.1f}%)")
P(f"  Best r: Ridge mycelium ({r_err:.1f}%)")


# ═══════════════════════════════════════════════════════
# R(t) TRAJECTORY
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("R(t) TRAJECTORY — K(mare) + r(mycelium) + t0(death)")
P(f"{'='*80}")

t0_pred = 0.208 * death_all[test_idx]

P(f"\n  {'Met':25s} {'K_obs':>8s} {'K_pred':>8s} {'r_obs':>6s} {'r_pred':>6s} {'R2':>7s}")
r2s = []
for ii, i in enumerate(test_idx):
    m = all_mets[i]
    wd = m['wave_data']
    t_arr = np.array([w['t'] for w in wd], dtype=float)
    R_obs = np.array([w['total_touched'] for w in wd], dtype=float)
    R_pred_t = K_pred[ii] / (1 + np.exp(-np.clip(r_pred[ii] * (t_arr - t0_pred[ii]), -500, 500)))
    ss_res = np.sum((R_obs - R_pred_t)**2)
    ss_tot = np.sum((R_obs - R_obs.mean())**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    r2s.append(r2)
    P(f"  {m['name']:25s} {m['K']:8,.0f} {K_pred[ii]:8,.0f} {m['r']:6.2f} {r_pred[ii]:6.2f} {r2:+7.4f}")

med_r2 = float(np.median(r2s))
v = "PASS" if med_r2 > 0.5 else "PARTIAL" if med_r2 > 0 else "FAIL"
P(f"\n  Median R2 = {med_r2:.4f} -> {v}")
P(f"\n  EVOLUTION:")
P(f"  S35 (6 train, 7 test):   R2 = -0.15 FAIL")
P(f"  S36 (6 train, 7 test):   R2 = +0.41 PARTIAL")
P(f"  S37 ({len(train_idx)} train, {len(test_idx)} test): R2 = {med_r2:.4f} {v}")


# ═══════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════

output = {
    "test": "retrain_s37",
    "date": "2026-04-08",
    "n_meteorites": N_METS,
    "n_train": len(train_idx),
    "n_test": len(test_idx),
    "K_model": K_method,
    "K_error": round(best_K_err, 1),
    "r_error": round(r_err, 1),
    "R_t_median_r2": round(med_r2, 4),
    "R_t_verdict": v,
    "per_meteorite": {
        all_mets[test_idx[ii]]['name']: {
            'K_obs': float(K_all[test_idx[ii]]),
            'K_pred': float(K_pred[ii]),
            'r_obs': float(r_all[test_idx[ii]]),
            'r_pred': float(r_pred[ii]),
            'r2': round(r2s[ii], 4),
        } for ii in range(len(test_idx))
    },
    "mycelium_cursors": myc_all,
}

OUT = os.path.join(REPO, "data/results/wave_retrain_s37.json")
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

P(f"\nSaved: {OUT}")
P("DONE.")
