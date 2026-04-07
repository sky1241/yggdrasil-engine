#!/usr/bin/env python3
"""
YGGDRASIL — Session 36: Identification mycélienne LOCALE de chaque mare
========================================================================
Pour chaque météorite: mesurer les curseurs Lehmann + traits réseau
sur le sous-graphe LOCAL (seeds + 1-hop neighbors).

Curseurs Lehmann (5):
  BA  = branching angle (via positions spectrales WT4)
  IL  = internodal length (BFS sur sous-graphe sparse)
  D   = hyphal diameter (log10 des poids cooc_global)
  Db  = box counting dimension (positions spectrales)
  L   = lacunarity (gliding box)

Traits réseau supplémentaires (Aguilar-Trigueros 2022):
  alpha = meshedness = (E - N + 1) / (2N - 5)
  E_global = global efficiency = mean(1/d_ij) pour i!=j

Archétypes attendus:
  Low-connectivity (arbre) → propagation lente (RAMPEUR)
  High-connectivity dense → propagation moyenne
  High-connectivity efficient → propagation rapide (EXPLOSEUR)

Sky × Claude (Opus 4.6) — Session 36, 7 avril 2026

Sources:
  - Lehmann et al. 2019, Sci Rep 9:14152
  - Aguilar-Trigueros et al. 2022, ISME Comms 2:2
  - Camenzind et al. 2024, Nat Comms
  - Galvez & Vignolini 2025, Nature 639:172-180
"""
import json, sys, os, math, time
import numpy as np
import sqlite3
from collections import defaultdict
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding='utf-8')

def P(*args, **kw):
    print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")
CHECK = json.load(open(os.path.join(REPO, "data/results/_wave_checkpoint.json"), encoding='utf-8'))
SPECTRAL = json.load(open(os.path.join(REPO, "data/scan/spectral_births.json"), encoding='utf-8'))
SPECIES = json.load(open(os.path.join(REPO, "data/scan/species_65k.json"), encoding='utf-8'))

bfs = CHECK['phase_1']
mare = CHECK['phase_2']
logistic = CHECK['phase_3e']['fits']
METS = list(bfs.keys())

# Build lookups
node_by_id = {n['id']: n for n in SPECTRAL['nodes']}
id_to_name = {n['id']: n['name'] for n in SPECTRAL['nodes'] if n.get('type') == 'concept'}
name_to_species = {d['name']: d['species'] for d in SPECIES['concepts'].values()}

# Targets
K_all = np.array([logistic[m]['K'] for m in METS])
r_all = np.array([logistic[m]['r_growth'] for m in METS])
t0_all = np.array([logistic[m]['t0'] for m in METS])
death_all = np.array([bfs[m].get('death_t', 8) or 8 for m in METS])

# Split
train_mets = [m for m in METS if int(m.split()[-1]) <= 1960]
test_mets  = [m for m in METS if int(m.split()[-1]) >= 1974]
train_idx = [METS.index(m) for m in train_mets]
test_idx  = [METS.index(m) for m in test_mets]

P("=" * 80)
P("IDENTIFICATION MYCELIENNE LOCALE — chaque mare a sa famille de champignon")
P("Lehmann 2019 + Aguilar-Trigueros 2022")
P("=" * 80)

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

myc = {}
for mi, m in enumerate(METS):
    seeds = bfs[m]['seeds']
    t0s = time.time()

    # Build local subgraph: seeds + top N neighbors by weight
    # Only use concept_a index (fast)
    edges = {}  # (a, b) -> weight
    for seed in seeds:
        cur.execute("""
            SELECT concept_b, weight FROM cooc_global
            WHERE concept_a = ? ORDER BY weight DESC LIMIT 150
        """, (seed,))
        for row in cur.fetchall():
            a, b = min(seed, row[0]), max(seed, row[0])
            edges[(a, b)] = max(edges.get((a, b), 0), row[1])

    # All nodes in subgraph
    all_nodes = set()
    for (a, b) in edges:
        all_nodes.add(a)
        all_nodes.add(b)
    node_list = sorted(all_nodes)
    node_idx = {n: i for i, n in enumerate(node_list)}
    N = len(node_list)

    if N < 5:
        myc[m] = {'error': 'too few nodes'}
        P(f"  {m:20s} SKIP (N={N})")
        continue

    # Build adjacency
    adj = np.zeros((N, N))
    for (a, b), w in edges.items():
        if a in node_idx and b in node_idx:
            adj[node_idx[a], node_idx[b]] = w
            adj[node_idx[b], node_idx[a]] = w

    # ── LEHMANN CURSORS ──

    # D = hyphal diameter (log10 edge weights)
    weights = adj[adj > 0].flatten()
    if len(weights) > 0:
        log_w = np.log10(weights)
        D_val = float(np.mean(log_w))
        D_cv = float(np.std(log_w) / abs(D_val)) if D_val != 0 else 0
    else:
        D_val, D_cv = 0, 0

    # Sparsify for BA and IL (keep top 10% edges by weight)
    if len(weights) > 0:
        threshold = np.percentile(weights, 90)
        sparse = np.where(adj >= threshold, adj, 0)
    else:
        sparse = adj.copy()

    # BA = branching angle (using spectral positions)
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
        for a_idx in range(len(neighbors)):
            for b_idx in range(a_idx + 1, len(neighbors)):
                ja, jb = neighbors[a_idx], neighbors[b_idx]
                na_id, nb_id = node_list[ja], node_list[jb]
                if na_id not in node_by_id or nb_id not in node_by_id:
                    continue
                na, nb = node_by_id[na_id], node_by_id[nb_id]
                va = (na['x'] - xi, na['y'] - yi, na['z'] - zi)
                vb = (nb['x'] - xi, nb['y'] - yi, nb['z'] - zi)
                dot = va[0]*vb[0] + va[1]*vb[1] + va[2]*vb[2]
                ma = math.sqrt(va[0]**2 + va[1]**2 + va[2]**2)
                mb = math.sqrt(vb[0]**2 + vb[1]**2 + vb[2]**2)
                if ma > 0 and mb > 0:
                    cos_a = max(-1.0, min(1.0, dot / (ma * mb)))
                    angles.append(math.degrees(math.acos(cos_a)))

    BA_val = float(np.mean(angles)) if angles else 0
    BA_cv = float(np.std(angles) / BA_val) if BA_val > 0 and angles else 0

    # IL = internodal length (BFS between bifurcations on sparse graph)
    degrees = [(sparse[i] > 0).sum() for i in range(N)]
    bifurcations = [i for i in range(N) if degrees[i] >= 3]
    il_dists = []
    binary = (sparse > 0).astype(int)
    for src in bifurcations[:20]:  # cap for speed
        visited = {src: 0}
        queue = [src]
        while queue:
            node = queue.pop(0)
            for nbr in range(N):
                if binary[node, nbr] > 0 and nbr not in visited:
                    visited[nbr] = visited[node] + 1
                    queue.append(nbr)
        for dst in bifurcations:
            if dst > src and dst in visited:
                il_dists.append(visited[dst])

    IL_val = float(np.mean(il_dists)) if il_dists else 0
    IL_cv = float(np.std(il_dists) / IL_val) if IL_val > 0 and il_dists else 0

    # Db = box counting dimension (spectral positions 3D)
    coords = []
    for nid in node_list:
        if nid in node_by_id:
            n = node_by_id[nid]
            coords.append((n['x'], n['y'], n['z']))
    coords = np.array(coords) if coords else np.zeros((1, 3))

    if len(coords) >= 3:
        extent = max(coords.max(axis=0) - coords.min(axis=0))
        if extent > 0:
            log_inv, log_n = [], []
            for k in range(1, 8):
                eps = extent / (2**k)
                if eps <= 0:
                    continue
                boxes = set()
                for c in coords:
                    boxes.add(tuple(int((c[d] - coords[:, d].min()) / eps) for d in range(3)))
                if len(boxes) > 0:
                    log_inv.append(math.log(1/eps))
                    log_n.append(math.log(len(boxes)))
            if len(log_inv) >= 3:
                Db_val = float(np.polyfit(log_inv, log_n, 1)[0])
            else:
                Db_val = 1.0
        else:
            Db_val = 1.0
    else:
        Db_val = 1.0

    # L = lacunarity (gliding box 3D)
    lacs = []
    if len(coords) >= 3 and extent > 0:
        for n_div in [3, 5, 7]:
            eps = extent / n_div
            if eps <= 0:
                continue
            boxes = defaultdict(int)
            for c in coords:
                bx = tuple(int((c[d] - coords[:, d].min()) / eps) for d in range(3))
                boxes[bx] += 1
            masses = list(boxes.values())
            # Include empty boxes
            total_boxes = n_div ** 3
            masses.extend([0] * (total_boxes - len(masses)))
            masses = np.array(masses, dtype=float)
            mu = masses.mean()
            if mu > 0:
                lacs.append(float(masses.var() / (mu**2)))
    L_val = float(np.mean(lacs)) if lacs else 0

    # ── NETWORK TRAITS (Aguilar-Trigueros 2022) ──

    # Meshedness alpha = (E - N + 1) / (2N - 5)
    n_edges_sparse = int((sparse > 0).sum()) // 2
    if N >= 3:
        alpha = (n_edges_sparse - N + 1) / max(2 * N - 5, 1)
    else:
        alpha = 0

    # Global efficiency = mean(1/d_ij) for all i!=j (on sparse graph)
    # BFS from each node (cap at 50 for speed)
    sample_nodes = list(range(min(N, 50)))
    eff_sum = 0
    eff_count = 0
    for src in sample_nodes:
        visited = {src: 0}
        queue = [src]
        while queue:
            node = queue.pop(0)
            for nbr in range(N):
                if binary[node, nbr] > 0 and nbr not in visited:
                    visited[nbr] = visited[node] + 1
                    queue.append(nbr)
        for dst in sample_nodes:
            if dst != src and dst in visited and visited[dst] > 0:
                eff_sum += 1.0 / visited[dst]
                eff_count += 1

    E_global = eff_sum / max(eff_count, 1)

    # Species of seeds
    seed_species = []
    for s in seeds:
        nm = id_to_name.get(s, '')
        seed_species.append(name_to_species.get(nm, -1))

    dt = time.time() - t0s
    myc[m] = {
        'BA': round(BA_val, 2), 'BA_cv': round(BA_cv, 3),
        'IL': round(IL_val, 2), 'IL_cv': round(IL_cv, 3),
        'D': round(D_val, 2), 'D_cv': round(D_cv, 3),
        'Db': round(Db_val, 3),
        'L': round(L_val, 3),
        'alpha': round(alpha, 4),
        'E_global': round(E_global, 4),
        'N': N, 'E_sparse': n_edges_sparse,
        'n_bifurcations': len(bifurcations),
        'species': seed_species,
    }
    P(f"  {m:20s} BA={BA_val:5.1f} IL={IL_val:4.1f} D={D_val:4.2f} Db={Db_val:.3f} "
      f"L={L_val:.3f} alpha={alpha:.4f} Eglob={E_global:.4f} "
      f"sp={seed_species} ({N}n/{n_edges_sparse}e, {dt:.1f}s)")

db.close()


# ═══════════════════════════════════════════════════════
# ARCHETYPE IDENTIFICATION
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("IDENTIFICATION DES ARCHETYPES")
P(f"{'='*80}")

# Aguilar-Trigueros 2022 archetypes:
# 1. Low-connectivity (tree-like): low alpha, high root efficiency
# 2. High-connectivity dense: high alpha, high robustness
# 3. High-connectivity efficient: medium alpha, high E_global

for m in METS:
    if 'error' in myc[m]:
        continue
    alpha = myc[m]['alpha']
    eg = myc[m]['E_global']
    r = logistic[m]['r_growth']

    if alpha < 0.05:
        archetype = "LOW-CONN (arbre)"
    elif eg > 0.4:
        archetype = "HI-CONN EFFICIENT"
    else:
        archetype = "HI-CONN DENSE"

    P(f"  {m:20s} alpha={alpha:.4f} Eglob={eg:.4f} r={r:.2f} → {archetype}")


# ═══════════════════════════════════════════════════════
# CORRELATION WITH WAVE PARAMETERS
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("CORRELATION curseurs myceliens vs K, r, t0, death")
P(f"{'='*80}")

features_myc = ['BA', 'IL', 'D', 'Db', 'L', 'alpha', 'E_global']
P(f"\n  {'Feature':20s} {'rho(K)':>7s} {'p':>7s} {'rho(r)':>7s} {'p':>7s} {'rho(death)':>10s}")

for fname in features_myc:
    vals = np.array([myc[m].get(fname, 0) for m in METS])
    if np.std(vals) < 1e-10:
        continue
    rk, pk = spearmanr(vals, K_all)
    rr, pr = spearmanr(vals, r_all)
    rd, pd = spearmanr(vals, death_all)
    flag = ""
    if abs(rr) > 0.5: flag += " <<<R"
    if abs(rk) > 0.5: flag += " <<<K"
    P(f"  {fname:20s} {rk:+7.3f} {pk:7.4f} {rr:+7.3f} {pr:7.4f} {rd:+10.3f}{flag}")

# Combined: alpha * E_global
vals_combo = np.array([myc[m].get('alpha', 0) * myc[m].get('E_global', 0) for m in METS])
rr, pr = spearmanr(vals_combo, r_all)
rk, pk = spearmanr(vals_combo, K_all)
P(f"  {'alpha*Eglob':20s} {rk:+7.3f} {pk:7.4f} {rr:+7.3f} {pr:7.4f}")


# ═══════════════════════════════════════════════════════
# TEST TEMPORAL HONNETE
# ═══════════════════════════════════════════════════════

P(f"\n{'='*80}")
P("TEST TEMPOREL: curseurs myceliens pour predire r et K")
P(f"{'='*80}")

X_myc = np.array([[myc[m].get(f, 0) for f in features_myc] for m in METS])

# Add mare features
mare_feats = ['n_neighbors', 'local_density', 'hub_fraction', 'avg_edge_weight',
              'median_neighbor_works', 'seed_degree', 'seed_works', 'seed_weight',
              'n_seeds', 'avg_internal_weight', 'pre_edges', 'pre_weight', 'avg_level']
X_mare = np.array([[mare[m][f] for f in mare_feats] for m in METS])

# Combined
X_combined = np.column_stack([X_mare, X_myc])

for name, X, target, tname in [
    ("mycelium only", X_myc, K_all, "K"),
    ("mare only", X_mare, K_all, "K"),
    ("mare + mycelium", X_combined, K_all, "K"),
    ("mycelium only", X_myc, r_all, "r"),
    ("mare only", X_mare, r_all, "r"),
    ("mare + mycelium", X_combined, r_all, "r"),
]:
    sc = StandardScaler()
    X_tr = sc.fit_transform(X[train_idx])
    X_te = sc.transform(X[test_idx])
    model = Ridge(alpha=1.0)
    model.fit(X_tr, target[train_idx])
    pred = model.predict(X_te)
    errs = np.abs(pred - target[test_idx]) / np.abs(target[test_idx]) * 100
    med_err = float(np.median(errs))
    P(f"  {tname} ~ {name:20s} → {med_err:5.1f}% median error")


# ═══════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════

output = {
    "test": "mycelium_id_s36",
    "date": "2026-04-07",
    "sources": [
        "Lehmann et al. 2019, Sci Rep 9:14152",
        "Aguilar-Trigueros et al. 2022, ISME Comms 2:2",
        "Camenzind et al. 2024, Nat Comms",
        "Galvez & Vignolini 2025, Nature 639:172-180",
    ],
    "per_meteorite": myc,
}

OUT = os.path.join(REPO, "data/results/wave_mycelium_id_s36.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

P(f"\nSaved: {OUT}")
P("DONE.")
