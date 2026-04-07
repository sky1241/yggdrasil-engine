#!/usr/bin/env python3
"""
YGGDRASIL — Session 37: BFS expansion — 25 nouvelles météorites
=================================================================
Mesure la propagation BFS temporelle + mare + logistic fit
pour chaque nouvelle percée scientifique.

Pipeline identique à wave_comprehensive_test.py phases 1-3.
Sauvegarde incrementale (checkpoint après chaque météorite).

Sky × Claude (Opus 4.6) — Session 36-37, 7 avril 2026
"""
import json, sys, os, time, math
import numpy as np
import sqlite3
from scipy.optimize import curve_fit
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

def P(*args, **kw):
    print(*args, **kw, flush=True)

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data/wt3.db")
OUTPUT = os.path.join(REPO, "data/results/wave_expand_checkpoint.json")
N_CONCEPTS = 65026

# All 25 new meteorites
NEW_METS = [
    # Pre-1960 (train)
    ("X-ray 1895",           1895, [34157]),
    ("Radioactivity 1896",   1896, [15754]),
    ("Electron 1897",        1897, [7363]),
    ("Relativity 1905",      1905, [17303, 7415]),
    ("Superconductivity 1911", 1911, [57657]),
    ("Insulin 1921",         1921, [34056]),
    ("QM 1925",              1925, [59231]),
    ("Penicillin 1928",      1928, [11674, 56429]),
    ("Neutron 1932",         1932, [8200]),
    ("Radar 1935",           1935, [58057]),
    ("Fission 1938",         1938, [54149]),
    ("Game theory 1944",     1944, [12038]),
    ("NMR 1946",             1946, [55739]),
    # Post-1973 (test)
    ("Recombinant DNA 1973", 1973, [54910]),
    ("Monoclonal Ab 1975",   1975, [57730]),
    ("GPS 1978",             1978, [58871]),
    ("STM 1981",             1981, [59677]),
    ("PCR 1983",             1983, [56237]),
    ("Fullerene 1985",       1985, [27009]),
    ("WWW 1991",             1991, [5775]),
    ("Stem cell 1998",       1998, [43967]),
    ("RNAi 2001",            2001, [10400]),
    ("Graphene 2004",        2004, [51183]),
    ("Blockchain 2008",      2008, [35787]),
    ("Deep learning 2012",   2012, [1389]),
]


def load_checkpoint():
    if os.path.exists(OUTPUT):
        return json.load(open(OUTPUT, encoding='utf-8'))
    return {}


def save_checkpoint(data):
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def bfs_wave(cur, seeds, impact_year, max_years=15):
    """
    BFS temporel: année par année, compter les nouveaux concepts touchés.
    Utilise l'index idx_cooc_a_period pour la vitesse.
    """
    touched = set(seeds)
    frontier = set(seeds)
    wave_data = [{'t': 0, 'new_concepts': len(seeds), 'total_touched': len(seeds),
                  'new_edges': 0, 'mu': 0}]

    for dt in range(1, max_years + 1):
        year = impact_year + dt
        new_concepts = set()
        new_edges = 0

        # Pre-1980: periods are years ("1948"). Post-1980: months ("2012-01")
        if year < 1980:
            periods = [str(year)]
        else:
            periods = [f"{year}-{mo:02d}" for mo in range(1, 13)]

        for period in periods:
            for concept in frontier:
                cur.execute("""
                    SELECT concept_b FROM cooc
                    WHERE concept_a = ? AND period = ?
                """, (concept, period))
                for row in cur.fetchall():
                    nb = row[0]
                    edge = (concept, nb) if concept < nb else (nb, concept)
                    new_edges += 1
                    if nb not in touched:
                        new_concepts.add(nb)

        touched.update(new_concepts)
        frontier = new_concepts if new_concepts else frontier  # keep frontier if no new

        nc = len(new_concepts)
        mu = new_edges / max(nc, 1) if nc > 0 else 0

        wave_data.append({
            't': dt,
            'new_concepts': nc,
            'total_touched': len(touched),
            'new_edges': new_edges,
            'mu': round(mu, 4),
        })

        P(f"      t={dt:2d} new={nc:6d} total={len(touched):6d} edges={new_edges:8d}")

        # Death detection: 2 consecutive years with < 0.1% new
        if dt >= 3:
            recent = [wave_data[dt-1]['new_concepts'], wave_data[dt]['new_concepts']]
            if all(r < N_CONCEPTS * 0.001 for r in recent):
                P(f"      DEATH at t={dt}")
                break

    return wave_data, len(touched)


def measure_mare(cur, seeds):
    """Measure pond properties around seeds (same as wave_comprehensive_test phase 2)."""
    # Collect 1-hop neighbors and their properties
    neighbors = set()
    edge_weights = []
    internal_weights = []

    for seed in seeds:
        cur.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a = ?", (seed,))
        for row in cur.fetchall():
            neighbors.add(row[0])
            edge_weights.append(row[1])
        cur.execute("SELECT concept_a, weight FROM cooc_global WHERE concept_b = ?", (seed,))
        for row in cur.fetchall():
            neighbors.add(row[0])
            edge_weights.append(row[1])

    neighbors -= set(seeds)
    n_nbr = len(neighbors)

    # Seed properties
    seed_degrees = []
    seed_works = []
    for s in seeds:
        cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a = ?", (s,))
        d1 = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_b = ?", (s,))
        d2 = cur.fetchone()[0]
        seed_degrees.append(d1 + d2)
        seed_works.append(d1)  # proxy

    # Hub fraction: neighbors with degree > median
    sample_nbrs = list(neighbors)[:200]
    nbr_degrees = []
    nbr_works = []
    for n in sample_nbrs:
        cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a = ?", (n,))
        d = cur.fetchone()[0]
        nbr_degrees.append(d)
        nbr_works.append(d)  # proxy

    if nbr_degrees:
        med_deg = np.median(nbr_degrees)
        hub_frac = sum(1 for d in nbr_degrees if d > med_deg * 2) / len(nbr_degrees)
        med_works = float(np.median(nbr_works))
    else:
        hub_frac = 0
        med_works = 0

    # Local density: fraction of possible edges that exist among neighbors
    # Approximate: sample 50 neighbors, count edges among them
    sample_50 = list(neighbors)[:50]
    if len(sample_50) >= 2:
        existing_edges = 0
        possible_edges = len(sample_50) * (len(sample_50) - 1) / 2
        for i, a in enumerate(sample_50):
            cur.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a = ? AND concept_b IN ({})".format(
                ','.join(str(b) for b in sample_50[i+1:])), (a,))
            existing_edges += cur.fetchone()[0]
        local_density = existing_edges / max(possible_edges, 1)
    else:
        local_density = 0

    avg_ew = float(np.mean(edge_weights)) if edge_weights else 0
    avg_iw = float(np.mean(internal_weights)) if internal_weights else 0

    return {
        'seed_works': float(np.mean(seed_works)),
        'seed_degree': float(np.mean(seed_degrees)),
        'seed_weight': sum(edge_weights[:len(seeds)]) if edge_weights else 0,
        'avg_edge_weight': avg_ew,
        'n_neighbors': n_nbr,
        'hub_fraction': hub_frac,
        'avg_level': 2.0,  # placeholder
        'n_seeds': len(seeds),
        'local_density': local_density,
        'avg_internal_weight': avg_iw,
        'median_neighbor_works': med_works,
        'pre_edges': len(edge_weights),
        'pre_weight': sum(edge_weights),
    }


def fit_logistic(wave_data):
    """Fit R(t) = K / (1 + exp(-r*(t-t0)))."""
    t = np.array([w['t'] for w in wave_data], dtype=float)
    R = np.array([w['total_touched'] for w in wave_data], dtype=float)

    if len(t) < 4 or R[-1] < 100:
        return {'K': R[-1], 'r_growth': 1.0, 't0': 1.0, 'r2': 0, 'K_error_pct': 0}

    def logistic(t, K, r, t0):
        return K / (1 + np.exp(-np.clip(r * (t - t0), -500, 500)))

    try:
        p0 = [R[-1] * 1.05, 2.0, 2.0]
        bounds = ([R[-1] * 0.5, 0.1, 0.01], [N_CONCEPTS * 1.1, 20, 10])
        popt, _ = curve_fit(logistic, t[1:], R[1:], p0=p0, bounds=bounds, maxfev=10000)
        K, r, t0 = popt

        R_pred = logistic(t[1:], K, r, t0)
        ss_res = np.sum((R[1:] - R_pred)**2)
        ss_tot = np.sum((R[1:] - R[1:].mean())**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            'K': round(float(K), 1),
            'r_growth': round(float(r), 4),
            't0': round(float(t0), 4),
            'r2': round(float(r2), 4),
            'K_error_pct': round(abs(K - R[-1]) / R[-1] * 100, 1),
        }
    except Exception as e:
        return {'K': float(R[-1]), 'r_growth': 1.0, 't0': 1.0, 'r2': 0, 'K_error_pct': 0,
                'error': str(e)}


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

P("=" * 80)
P(f"BFS EXPANSION — {len(NEW_METS)} nouvelles météorites")
P("=" * 80)

checkpoint = load_checkpoint()
db = sqlite3.connect(DB_PATH)
cur = db.cursor()

for name, year, seeds in NEW_METS:
    if name in checkpoint:
        P(f"\n  {name:25s} SKIP (already done)")
        continue

    P(f"\n  {'='*70}")
    P(f"  {name} — seeds={seeds}, impact={year}")
    P(f"  {'='*70}")

    t0 = time.time()

    # Phase 1: BFS wave
    P(f"    Phase 1: BFS temporel...")
    wave_data, r_max = bfs_wave(cur, seeds, year)
    death_t = len(wave_data) - 1
    for w in wave_data:
        if w['t'] >= 3 and w['new_concepts'] < N_CONCEPTS * 0.001:
            death_t = w['t']
            break

    peak_year = max(wave_data[1:], key=lambda w: w['new_edges'])['t'] if len(wave_data) > 1 else 1
    peak_edges = max(w['new_edges'] for w in wave_data[1:]) if len(wave_data) > 1 else 0
    mu_peak = max(w['mu'] for w in wave_data[1:]) if len(wave_data) > 1 else 0

    P(f"    r_max={r_max}, death_t={death_t}, peak_t={peak_year}")

    # Phase 2: Mare properties
    P(f"    Phase 2: Mare properties...")
    mare = measure_mare(cur, seeds)

    # Phase 3: Logistic fit
    P(f"    Phase 3: Logistic fit...")
    fit = fit_logistic(wave_data)

    dt = time.time() - t0

    checkpoint[name] = {
        'phase_1': {
            'seeds': seeds,
            'open_year': year,
            'wave_data': wave_data,
            'r_max': r_max,
            'pct': round(r_max / N_CONCEPTS * 100, 1),
            'death_t': death_t,
            'peak_year': peak_year,
            'peak_edges': peak_edges,
            'mu_peak': round(mu_peak, 4),
        },
        'phase_2': mare,
        'phase_3': fit,
        'time_sec': round(dt, 1),
    }

    save_checkpoint(checkpoint)

    P(f"    K={fit['K']:.0f} ({fit['K']/N_CONCEPTS*100:.1f}%) r={fit['r_growth']:.2f} "
      f"t0={fit['t0']:.2f} R2={fit['r2']:.4f} death={death_t} ({dt:.1f}s)")

db.close()

# Summary
P(f"\n{'='*80}")
P("RÉSUMÉ")
P(f"{'='*80}")
P(f"\n  {'Met':25s} {'K':>8s} {'%':>5s} {'r':>5s} {'t0':>5s} {'death':>5s} {'R2':>6s}")
for name, year, seeds in NEW_METS:
    if name in checkpoint:
        d = checkpoint[name]
        f = d['phase_3']
        p1 = d['phase_1']
        P(f"  {name:25s} {f['K']:8,.0f} {f['K']/N_CONCEPTS*100:4.1f}% {f['r_growth']:5.2f} "
          f"{f['t0']:5.2f} {p1['death_t']:5d} {f['r2']:6.4f}")

P(f"\nSaved: {OUTPUT}")
P("DONE.")
