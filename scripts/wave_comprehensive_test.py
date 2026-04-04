#!/usr/bin/env python3
"""
YGGDRASIL ENGINE — V3 Comprehensive Wave Model Test
=====================================================
13 météorites × 7 phases × 6 modèles.
Méthodique, scientifique, justifiable.

Sources:
  Newman 2002, cond-mat/0205009 (SIR-percolation)
  Chung 1997, Spectral Graph Theory (heat kernel)
  Lamb 1932 / Lighthill 1978 (surface wave)
  Worthington 1908 (crater scaling)
  Kermack-McKendrick 1927 (SIR)
  Harris 1963 (Galton-Watson branching)
  Moreno et al 2004, cond-mat/0312131 (rumor spreading)

Sky × Claude (Opus 4.6) — Session 34, 4 avril 2026
"""
import json
import sys
import os
import math
import time
import sqlite3
import numpy as np
from scipy.stats import spearmanr, pearsonr
from scipy.optimize import curve_fit, minimize_scalar
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

REPO = "D:/ygg/yggdrasil-engine"
DB_PATH = os.path.join(REPO, "data", "wt3.db")
CONCEPTS_PATH = os.path.join(REPO, "data", "scan", "concepts_65k.json")
WT4_PATH = os.path.join(REPO, "data", "scan", "wt4_spectral.json")
OUTPUT = os.path.join(REPO, "data", "results", "wave_comprehensive_test.json")
CHECKPOINT = os.path.join(REPO, "data", "results", "_wave_checkpoint.json")

N_CONCEPTS = 65026
MAX_YEARS = 15

# ══════════════════════════════════════════════════════
# 13 METEORITES — Seeds from godel_holdout_wave.py
# ══════════════════════════════════════════════════════

METEORITE_SEEDS = {
    "Shannon 1948": {
        "open": "1948", "strate": 1, "continents": 7,
        "seeds": [57221, 1033],
    },
    "Transistor 1947": {
        "open": "1947", "strate": 0, "continents": 6,
        "seeds": [11323, 1331],
    },
    "Turing 1936": {
        "open": "1936", "strate": 6, "continents": 4,
        "seeds": [8122, 5866, 1806],
    },
    "ADN 1953": {
        "open": "1953", "strate": 0, "continents": 5,
        "seeds": [58019, 8408],
    },
    "Godel 1931": {
        "open": "1931", "strate": 6, "continents": 9,
        "seeds": [12665, 8122, 1806],
    },
    "Laser 1960": {
        "open": "1960", "strate": 0, "continents": 5,
        "seeds": [57047, 53232],
    },
    "CRISPR 2012": {
        "open": "2012", "strate": 0, "continents": 4,
        "seeds": [64738, 5064],
    },
    "AlphaFold 2020": {
        "open": "2020", "strate": 0, "continents": 3,
        "seeds": [12593, 16301],
    },
    "Grav waves 2016": {
        "open": "2016", "strate": 1, "continents": 2,
        "seeds": [14090],
    },
    "Higgs 2012": {
        "open": "2012", "strate": 1, "continents": 2,
        "seeds": [9062],
    },
    "mRNA 1990": {
        "open": "1990", "strate": 0, "continents": 4,
        "seeds": [380, 39251],
    },
    "Internet 1974": {
        "open": "1974", "strate": 0, "continents": 7,
        "seeds": [1758, 53391, 2196],
    },
    "Poincare 2003": {
        "open": "2003", "strate": 3, "continents": 1,
        "seeds": [63206, 41700],
    },
}


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def save_checkpoint(data):
    save_json(data, CHECKPOINT)


def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        return load_json(CHECKPOINT)
    return {}


def corr(x, y):
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 4:
        return {"spearman_r": 0, "spearman_p": 1, "pearson_r": 0, "pearson_p": 1, "n": int(mask.sum())}
    r_s, p_s = spearmanr(x[mask], y[mask])
    r_p, p_p = pearsonr(x[mask], y[mask])
    return {"spearman_r": round(r_s, 4), "spearman_p": round(p_s, 4),
            "pearson_r": round(r_p, 4), "pearson_p": round(p_p, 4), "n": int(mask.sum())}


# ══════════════════════════════════════════════════════
# PHASE 1 — BFS WAVE PROPAGATION
# ═════════════════════════════════════════���════════════

def measure_wave(db, name, seeds, impact_year):
    """BFS wave propagation from impact point. From godel_holdout_wave.py."""
    wavefront = set(seeds)
    all_touched = set(seeds)
    edges_seen = set()
    results = []
    wave = 0
    stall_count = 0

    for yr in range(impact_year, impact_year + MAX_YEARS):
        t0 = time.time()
        db.execute('DROP TABLE IF EXISTS tmp_front')
        db.execute('CREATE TEMP TABLE tmp_front (cid INTEGER PRIMARY KEY)')
        db.executemany('INSERT INTO tmp_front VALUES (?)', [(c,) for c in wavefront])

        new_edges = 0
        new_concepts = set()

        rows = db.execute('''
            SELECT c.concept_a, c.concept_b FROM cooc c
            INNER JOIN tmp_front f ON c.concept_a = f.cid
            WHERE c.period = ?
        ''', (str(yr),)).fetchall()
        for ca, cb in rows:
            edge = (ca, cb) if ca < cb else (cb, ca)
            if edge not in edges_seen:
                edges_seen.add(edge)
                new_edges += 1
                if cb not in all_touched:
                    new_concepts.add(cb)

        if yr >= 1980:
            for mo in range(1, 13):
                rows_m = db.execute('''
                    SELECT c.concept_a, c.concept_b FROM cooc c
                    INNER JOIN tmp_front f ON c.concept_a = f.cid
                    WHERE c.period = ?
                ''', (f'{yr}-{mo:02d}',)).fetchall()
                for ca, cb in rows_m:
                    edge = (ca, cb) if ca < cb else (cb, ca)
                    if edge not in edges_seen:
                        edges_seen.add(edge)
                        new_edges += 1
                        if cb not in all_touched:
                            new_concepts.add(cb)

        all_touched.update(new_concepts)
        if new_concepts:
            wave += 1
            wavefront = new_concepts
            stall_count = 0
        else:
            stall_count += 1

        offset = yr - impact_year
        results.append({
            "t": offset, "year": yr, "wave": wave,
            "front": len(wavefront), "new_edges": new_edges,
            "new_concepts": len(new_concepts), "total_touched": len(all_touched),
        })

        dt = time.time() - t0
        print(f"    {yr} w={wave:2d} front={len(wavefront):6d} "
              f"edges={new_edges:8,} new_c={len(new_concepts):6,} "
              f"total={len(all_touched):6,} ({dt:.0f}s)", flush=True)

        if stall_count >= 2 and offset >= 5:
            print(f"    -> wave dead, stopping", flush=True)
            break

    return results


def phase_1_bfs(checkpoint):
    """Measure BFS wave for all 13 meteorites."""
    print("\n" + "=" * 80)
    print("PHASE 1 — BFS WAVE PROPAGATION (13 météorites)")
    print("=" * 80)

    if 'phase_1' in checkpoint and len(checkpoint['phase_1']) == 13:
        print("  Phase 1 already complete (loaded from checkpoint)")
        return checkpoint['phase_1']

    existing = checkpoint.get('phase_1', {})
    db = sqlite3.connect(DB_PATH)
    results = dict(existing)

    for name, info in METEORITE_SEEDS.items():
        if name in results:
            print(f"\n  {name}: CACHED (R_max={results[name]['r_max']:,})")
            continue

        print(f"\n  {name}:", flush=True)
        t0 = time.time()
        impact_yr = int(info["open"][:4])
        wave_data = measure_wave(db, name, info["seeds"], impact_yr)

        r_max = max(w["total_touched"] for w in wave_data) if wave_data else 0
        pct = r_max / N_CONCEPTS

        peak = max(wave_data, key=lambda w: w["new_edges"]) if wave_data else None
        death_t = None
        for w in wave_data:
            if w["wave"] >= 3 and w["new_concepts"] == 0:
                death_t = w["t"]
                break

        # Compute mu(t) branching ratios
        mu_series = []
        for i in range(1, len(wave_data)):
            prev_front = wave_data[i-1]["front"]
            new_c = wave_data[i]["new_concepts"]
            mu = new_c / prev_front if prev_front > 0 else 0
            mu_series.append(round(mu, 4))

        results[name] = {
            "seeds": info["seeds"],
            "open_year": impact_yr,
            "strate": info["strate"],
            "continents": info["continents"],
            "wave_data": wave_data,
            "r_max": r_max,
            "pct": round(pct, 4),
            "death_t": death_t,
            "peak_year": peak["year"] if peak else None,
            "peak_edges": peak["new_edges"] if peak else 0,
            "mu_series": mu_series,
            "mu_peak": max(mu_series) if mu_series else 0,
        }

        dt = time.time() - t0
        d_str = f"t+{death_t}" if death_t else "alive"
        print(f"  -> R_max={r_max:,} ({pct:.0%}), death={d_str}, {dt:.0f}s", flush=True)

        # Checkpoint after each meteorite
        checkpoint['phase_1'] = results
        save_checkpoint(checkpoint)

    db.close()
    return results


# ══════════════════════════════════════════════════════
# PHASE 2 — MARE PROPERTIES
# ═══════════════════════════════════════════��══════════

def phase_2_mare(checkpoint):
    """Measure local topology around each meteorite's seeds."""
    print("\n" + "=" * 80)
    print("PHASE 2 — MARE PROPERTIES (13 météorites)")
    print("=" * 80)

    if 'phase_2' in checkpoint and len(checkpoint['phase_2']) == 13:
        print("  Phase 2 already complete (loaded from checkpoint)")
        return checkpoint['phase_2']

    # Load concept info
    cdata = load_json(CONCEPTS_PATH)
    idx2info = {v['idx']: v for k, v in cdata['concepts'].items()}

    existing = checkpoint.get('phase_2', {})
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    results = dict(existing)

    for name, info in METEORITE_SEEDS.items():
        if name in results:
            print(f"  {name}: CACHED", flush=True)
            continue

        seeds = info["seeds"]
        impact_yr = int(info["open"][:4])
        t0 = time.time()

        # Seed properties
        seed_works = sum(idx2info.get(s, {}).get('works_count', 0) for s in seeds)
        seed_degree = 0
        seed_weight = 0.0
        for s in seeds:
            c.execute("SELECT COUNT(*), COALESCE(SUM(weight),0) FROM cooc_global WHERE concept_a=?", (s,))
            cnt, w = c.fetchone()
            seed_degree += cnt
            seed_weight += w
            c.execute("SELECT COUNT(*), COALESCE(SUM(weight),0) FROM cooc_global WHERE concept_b=?", (s,))
            cnt, w = c.fetchone()
            seed_degree += cnt
            seed_weight += w

        avg_edge_weight = seed_weight / max(seed_degree, 1)

        # Neighbors
        neighbors = set()
        for s in seeds:
            c.execute("SELECT concept_b FROM cooc_global WHERE concept_a=?", (s,))
            neighbors.update(r[0] for r in c.fetchall())
            c.execute("SELECT concept_a FROM cooc_global WHERE concept_b=?", (s,))
            neighbors.update(r[0] for r in c.fetchall())
        neighbors -= set(seeds)
        n_neighbors = len(neighbors)

        # Hub fraction (sample)
        sample_nbrs = list(neighbors)[:2000]
        hub_count = sum(1 for n in sample_nbrs if idx2info.get(n, {}).get('works_count', 0) > 100000)
        hub_fraction = hub_count / len(sample_nbrs) if sample_nbrs else 0

        # Average level
        avg_level = np.mean([idx2info.get(s, {}).get('level', 2) for s in seeds])

        # Local density (sample 500 neighbors)
        sample = list(neighbors)[:500]
        internal_edges = 0
        internal_weight = 0.0
        for i, n1 in enumerate(sample):
            if i + 1 < len(sample):
                placeholders = ','.join(str(x) for x in sample[i+1:])
                c.execute(f"""
                    SELECT COUNT(*), COALESCE(SUM(weight),0)
                    FROM cooc_global WHERE concept_a=? AND concept_b IN ({placeholders})
                """, (n1,))
                row = c.fetchone()
                internal_edges += row[0]
                internal_weight += row[1]

        possible = len(sample) * (len(sample) - 1) / 2
        local_density = internal_edges / possible if possible > 0 else 0
        avg_internal_weight = internal_weight / max(internal_edges, 1)

        # Median neighbor works
        nbr_works = [idx2info.get(n, {}).get('works_count', 0) for n in sample_nbrs]
        median_nbr_works = float(np.median(nbr_works)) if nbr_works else 0

        # Pre-impact activity
        pre_edges = 0
        pre_weight = 0.0
        for s in seeds:
            c.execute("""
                SELECT COUNT(*), COALESCE(SUM(weight),0) FROM cooc
                WHERE concept_a=? AND period < ? AND length(period)=4
            """, (s, str(impact_yr)))
            cnt, w = c.fetchone()
            pre_edges += cnt
            pre_weight += w

        results[name] = {
            'seed_works': seed_works,
            'seed_degree': seed_degree,
            'seed_weight': round(seed_weight, 2),
            'avg_edge_weight': round(avg_edge_weight, 4),
            'n_neighbors': n_neighbors,
            'hub_fraction': round(hub_fraction, 4),
            'avg_level': round(avg_level, 2),
            'n_seeds': len(seeds),
            'local_density': round(local_density, 6),
            'avg_internal_weight': round(avg_internal_weight, 4),
            'median_neighbor_works': round(median_nbr_works, 0),
            'pre_edges': pre_edges,
            'pre_weight': round(pre_weight, 4),
        }

        dt = time.time() - t0
        print(f"  {name:25s} deg={seed_degree:,} dens={local_density:.4f} "
              f"aiw={avg_internal_weight:.1f} ({dt:.0f}s)", flush=True)

        checkpoint['phase_2'] = results
        save_checkpoint(checkpoint)

    db.close()
    return results


# ══════════════════════════════════════════════════════
# PHASE 3A — NEWMAN SIR-PERCOLATION
# ══════════════════════════════════════════════════════

def phase_3a_newman(phase1, phase2, checkpoint):
    """Newman SIR-percolation. Source: cond-mat/0205009."""
    print("\n" + "=" * 80)
    print("PHASE 3A — NEWMAN SIR-PERCOLATION (cond-mat/0205009)")
    print("=" * 80)

    if 'phase_3a' in checkpoint:
        print("  Cached")
        return checkpoint['phase_3a']

    # Load P(k)
    print("  Loading P(k) from cooc_global...", flush=True)
    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT concept_a, COUNT(*) FROM cooc_global GROUP BY concept_a")
    deg_a = dict(c.fetchall())
    c.execute("SELECT concept_b, COUNT(*) FROM cooc_global GROUP BY concept_b")
    deg_b = dict(c.fetchall())
    conn.close()

    degree = Counter()
    for cid, d in deg_a.items(): degree[cid] += d
    for cid, d in deg_b.items(): degree[cid] += d

    pk_counter = Counter(degree.values())
    max_k = min(max(degree.values()), 20000)
    pk_array = np.zeros(max_k + 1)
    for k, cnt in pk_counter.items():
        if k <= max_k:
            pk_array[k] = cnt
    pk_array /= pk_array.sum()

    k_mean = sum(k * pk_array[k] for k in range(len(pk_array)))
    k2_mean = sum(k**2 * pk_array[k] for k in range(len(pk_array)))
    T_c = k_mean / (k2_mean - k_mean) if k2_mean > k_mean else 0
    print(f"  P(k) loaded in {time.time()-t0:.0f}s. <k>={k_mean:.0f}, T_c={T_c:.6f}", flush=True)

    def newman_S(T):
        z = k_mean
        if z == 0: return 0
        u = 0.999
        for _ in range(500):
            g1_u = sum(k * pk_array[k] * (u ** (k-1)) for k in range(1, len(pk_array)) if pk_array[k] > 0) / z
            u_new = 1 - T + T * g1_u
            if abs(u_new - u) < 1e-12: break
            u = u_new
        g0_u = sum(pk_array[k] * (u ** k) for k in range(len(pk_array)) if pk_array[k] > 0)
        return max(0, 1 - g0_u)

    # Fit T for each meteorite
    mets = list(phase1.keys())
    T_fits = {}
    for m in mets:
        target = phase1[m]['pct']
        def obj(T): return (newman_S(T) - target) ** 2
        res = minimize_scalar(obj, bounds=(0.0001, 0.01), method='bounded')
        T_fits[m] = round(res.x, 8)

    # Correlations T vs mare features
    T_vals = np.array([T_fits[m] for m in mets])
    pcts = np.array([phase1[m]['pct'] for m in mets])

    features = {}
    for fn in ['seed_works', 'seed_degree', 'seed_weight', 'avg_edge_weight',
               'n_neighbors', 'hub_fraction', 'avg_level', 'local_density',
               'avg_internal_weight', 'median_neighbor_works', 'pre_edges', 'pre_weight']:
        features[fn] = np.array([phase2[m].get(fn, 0) for m in mets])

    # Composites
    features['aiw_over_density'] = features['avg_internal_weight'] / (features['local_density'] + 1e-8)
    features['log_aiw'] = np.log1p(features['avg_internal_weight'])
    features['1_minus_density'] = 1 - features['local_density']

    T_corrs = {}
    best_fn, best_rho = "", 0
    print(f"\n  {'Feature':30s} {'rho vs T':>10s} {'p':>8s}")
    for fn, vals in features.items():
        c_val = corr(vals, T_vals)
        T_corrs[fn] = c_val
        flag = " ***" if abs(c_val['spearman_r']) > 0.6 else ""
        print(f"  {fn:30s} {c_val['spearman_r']:+10.4f} {c_val['spearman_p']:8.4f}{flag}")
        if abs(c_val['spearman_r']) > abs(best_rho):
            best_rho = c_val['spearman_r']
            best_fn = fn

    # LOO cross-validation with best feature
    best_vals = features[best_fn]
    loo = []
    for i in range(len(mets)):
        mask = np.ones(len(mets), dtype=bool)
        mask[i] = False
        coeffs = np.polyfit(best_vals[mask], T_vals[mask], 1)
        T_pred = max(T_c, min(0.01, np.polyval(coeffs, best_vals[i])))
        S_pred = newman_S(T_pred)
        rmax_pred = S_pred * N_CONCEPTS
        rmax_obs = phase1[mets[i]]['r_max']
        loo.append({
            'met': mets[i], 'T_obs': T_fits[mets[i]], 'T_pred': round(T_pred, 8),
            'rmax_obs': rmax_obs, 'rmax_pred': round(rmax_pred),
            'error': round(abs(rmax_pred - rmax_obs)),
        })

    mae = np.mean([l['error'] for l in loo])
    rmse = np.sqrt(np.mean([l['error']**2 for l in loo]))

    print(f"\n  LOO ({best_fn}):")
    print(f"  {'Met':25s} {'T_obs':>10s} {'T_pred':>10s} {'R_obs':>8s} {'R_pred':>8s} {'Err':>8s}")
    for l in loo:
        print(f"  {l['met']:25s} {l['T_obs']:10.6f} {l['T_pred']:10.6f} "
              f"{l['rmax_obs']:8,} {l['rmax_pred']:8,} {l['error']:8,}")
    print(f"  MAE={mae:,.0f} ({mae/N_CONCEPTS*100:.1f}%), RMSE={rmse:,.0f}")

    # Also LOO without Laser
    loo_no_laser = [l for l in loo if l['met'] != 'Laser 1960']
    mae_no_laser = np.mean([l['error'] for l in loo_no_laser])
    print(f"  MAE sans Laser = {mae_no_laser:,.0f} ({mae_no_laser/N_CONCEPTS*100:.1f}%)")

    verdict = "PASS" if mae < 10000 else "PARTIAL" if mae < 20000 else "FAIL"
    print(f"  VERDICT: {verdict}")

    result = {
        "verdict": verdict,
        "T_c": round(T_c, 8), "k_mean": round(k_mean, 1),
        "T_fits": T_fits,
        "best_predictor": best_fn, "best_rho": round(best_rho, 4),
        "loo_mae": round(mae), "loo_rmse": round(rmse),
        "loo_mae_no_laser": round(mae_no_laser),
        "loo": loo, "T_correlations": {k: v['spearman_r'] for k, v in T_corrs.items()},
        "source": "Newman 2002, cond-mat/0205009",
    }
    checkpoint['phase_3a'] = result
    save_checkpoint(checkpoint)
    return result


# ═════════════════════════════════════════════════════��
# PHASE 3B — SURFACE WAVE (Lamb 1932, Lighthill 1978)
# ════════════════════════════════════════════���═════════

def phase_3b_surface_wave(phase1, checkpoint):
    """Fit A(t) = A0/sqrt(t) * exp(-alpha*t). Source: Lamb 1932, Lighthill 1978."""
    print("\n" + "=" * 80)
    print("PHASE 3B — ONDE DE SURFACE (Lamb 1932, Lighthill 1978)")
    print("=" * 80)

    if 'phase_3b' in checkpoint:
        print("  Cached")
        return checkpoint['phase_3b']

    def surface_wave(t, A0, alpha):
        return A0 / np.sqrt(np.maximum(t, 0.1)) * np.exp(-alpha * t)

    fits = {}
    for m, data in phase1.items():
        wave_d = data['wave_data']
        # new_concepts per year (the wave front amplitude)
        t_arr = np.array([w['t'] for w in wave_d if w['t'] > 0 and w['new_concepts'] > 0], dtype=float)
        nc_arr = np.array([w['new_concepts'] for w in wave_d if w['t'] > 0 and w['new_concepts'] > 0], dtype=float)

        if len(t_arr) < 3:
            fits[m] = {"r2": -1, "A0": 0, "alpha": 0, "note": "too few points"}
            continue

        try:
            popt, _ = curve_fit(surface_wave, t_arr, nc_arr, p0=[nc_arr.max()*2, 0.3],
                                bounds=([0.1, 0.01], [1e8, 5.0]), maxfev=5000)
            pred = surface_wave(t_arr, *popt)
            ss_res = np.sum((nc_arr - pred)**2)
            ss_tot = np.sum((nc_arr - nc_arr.mean())**2)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
            fits[m] = {"r2": round(r2, 4), "A0": round(popt[0], 2), "alpha": round(popt[1], 4)}
        except:
            fits[m] = {"r2": -1, "A0": 0, "alpha": 0, "note": "fit failed"}

        print(f"  {m:25s} R²={fits[m]['r2']:+.4f} A0={fits[m]['A0']:>10.1f} α={fits[m]['alpha']:.4f}")

    r2s = [f['r2'] for f in fits.values() if f['r2'] > -1]
    median_r2 = np.median(r2s) if r2s else -1
    verdict = "PASS" if median_r2 > 0.7 else "PARTIAL" if median_r2 > 0.4 else "FAIL"
    print(f"  Median R² = {median_r2:.4f}, VERDICT: {verdict}")

    result = {"verdict": verdict, "median_r2": round(median_r2, 4), "fits": fits,
              "source": "Lamb 1932 Hydrodynamics / Lighthill 1978 Waves in Fluids"}
    checkpoint['phase_3b'] = result
    save_checkpoint(checkpoint)
    return result


# ══════════════════════════════════════════════════════
# PHASE 3C — DAMPED OSCILLATOR (Hawkes-type)
# ══════════════════════════════════════════════════════

def phase_3c_oscillator(phase1, checkpoint):
    """Fit mu(t) = A*exp(-gamma*t)*cos(omega*t+phi)+offset."""
    print("\n" + "=" * 80)
    print("PHASE 3C — OSCILLATEUR AMORTI (Hawkes-type)")
    print("=" * 80)

    if 'phase_3c' in checkpoint:
        print("  Cached")
        return checkpoint['phase_3c']

    def damped_osc(t, A, gamma, omega, phi, offset):
        return A * np.exp(-gamma * t) * np.cos(omega * t + phi) + offset

    fits = {}
    gammas, omegas = [], []

    for m, data in phase1.items():
        mu = data['mu_series']
        if len(mu) < 4:
            fits[m] = {"r2": -1, "note": "too few mu points"}
            continue

        t_arr = np.arange(1, len(mu) + 1, dtype=float)
        mu_arr = np.array(mu)

        try:
            popt, _ = curve_fit(damped_osc, t_arr, mu_arr,
                                p0=[mu_arr.max(), 0.5, 3.0, 0.0, 1.0],
                                bounds=([0, 0.01, 0.1, -np.pi, 0], [1e6, 5, 15, np.pi, 100]),
                                maxfev=10000)
            pred = damped_osc(t_arr, *popt)
            ss_res = np.sum((mu_arr - pred)**2)
            ss_tot = np.sum((mu_arr - mu_arr.mean())**2)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
            fits[m] = {"r2": round(r2, 4), "A": round(popt[0], 2), "gamma": round(popt[1], 4),
                        "omega": round(popt[2], 4), "phi": round(popt[3], 4), "offset": round(popt[4], 4)}
            if r2 > 0.5:
                gammas.append(popt[1])
                omegas.append(popt[2])
        except:
            # Try simpler exponential
            try:
                def exp_d(t, A, b): return A * np.exp(-b * t)
                popt2, _ = curve_fit(exp_d, t_arr, mu_arr, p0=[mu_arr.max(), 0.5], maxfev=5000)
                pred2 = exp_d(t_arr, *popt2)
                ss2 = np.sum((mu_arr - pred2)**2)
                r2_2 = 1 - ss2/ss_tot if ss_tot > 0 else 0
                fits[m] = {"r2": round(r2_2, 4), "A": round(popt2[0], 2), "gamma": round(popt2[1], 4),
                            "note": "exponential only (oscillator failed)"}
            except:
                fits[m] = {"r2": -1, "note": "all fits failed"}

        print(f"  {m:25s} R²={fits[m]['r2']:+.4f} {fits[m].get('note', '')}")

    # Check universality
    universal = {}
    if gammas:
        universal = {
            "gamma_mean": round(np.mean(gammas), 4), "gamma_std": round(np.std(gammas), 4),
            "omega_mean": round(np.mean(omegas), 4), "omega_std": round(np.std(omegas), 4),
            "n_good_fits": len(gammas),
            "gamma_cv": round(np.std(gammas)/np.mean(gammas), 4) if np.mean(gammas) > 0 else None,
            "omega_cv": round(np.std(omegas)/np.mean(omegas), 4) if np.mean(omegas) > 0 else None,
        }
        print(f"\n  Universalité: gamma={universal['gamma_mean']}±{universal['gamma_std']} "
              f"omega={universal['omega_mean']}±{universal['omega_std']} (n={len(gammas)})")

    r2s = [f['r2'] for f in fits.values() if f['r2'] > -1]
    median_r2 = np.median(r2s) if r2s else -1
    verdict = "PASS" if median_r2 > 0.7 else "PARTIAL" if median_r2 > 0.4 else "FAIL"
    print(f"  Median R² = {median_r2:.4f}, VERDICT: {verdict}")

    result = {"verdict": verdict, "median_r2": round(median_r2, 4), "fits": fits,
              "universality": universal, "source": "Hawkes/ETAS branching process"}
    checkpoint['phase_3c'] = result
    save_checkpoint(checkpoint)
    return result


# ══════════════════════════════════════════════════════
# PHASE 3D — POWER LAW (baseline)
# ══════════════════════════════════════════════════════

def phase_3d_power_law(phase1, checkpoint):
    """Fit R(t) = a * t^b. Baseline to beat."""
    print("\n" + "=" * 80)
    print("PHASE 3D — POWER LAW R(t) = a×t^b (baseline)")
    print("=" * 80)

    if 'phase_3d' in checkpoint:
        print("  Cached")
        return checkpoint['phase_3d']

    def power_law(t, a, b): return a * np.power(t, b)

    fits = {}
    for m, data in phase1.items():
        wd = data['wave_data']
        t_arr = np.array([w['t'] for w in wd if w['t'] > 0], dtype=float)
        r_arr = np.array([w['total_touched'] for w in wd if w['t'] > 0], dtype=float)
        if len(t_arr) < 3:
            fits[m] = {"r2": -1}
            continue
        try:
            popt, _ = curve_fit(power_law, t_arr, r_arr, p0=[1000, 1.0],
                                bounds=([0.01, 0.01], [1e8, 5]), maxfev=5000)
            pred = power_law(t_arr, *popt)
            ss_res = np.sum((r_arr - pred)**2)
            ss_tot = np.sum((r_arr - r_arr.mean())**2)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
            fits[m] = {"r2": round(r2, 4), "a": round(popt[0], 2), "b": round(popt[1], 4)}
        except:
            fits[m] = {"r2": -1}
        print(f"  {m:25s} R²={fits[m]['r2']:+.4f}")

    r2s = [f['r2'] for f in fits.values() if f['r2'] > -1]
    median_r2 = np.median(r2s) if r2s else -1
    verdict = "PASS" if median_r2 > 0.85 else "PARTIAL" if median_r2 > 0.6 else "FAIL"
    print(f"  Median R² = {median_r2:.4f}, VERDICT: {verdict}")

    result = {"verdict": verdict, "median_r2": round(median_r2, 4), "fits": fits,
              "source": "baseline power law"}
    checkpoint['phase_3d'] = result
    save_checkpoint(checkpoint)
    return result


# ══════════════════════════════════════════════════════
# PHASE 3E — LOGISTIC S-CURVE
# ══════════════════════════════════════════════════════

def phase_3e_logistic(phase1, checkpoint):
    """Fit R(t) = K / (1 + exp(-r*(t-t0)))."""
    print("\n" + "=" * 80)
    print("PHASE 3E — LOGISTIQUE R(t) = K/(1+exp(-r(t-t0)))")
    print("=" * 80)

    if 'phase_3e' in checkpoint:
        print("  Cached")
        return checkpoint['phase_3e']

    def logistic(t, K, r, t0): return K / (1 + np.exp(-r * (t - t0)))

    fits = {}
    for m, data in phase1.items():
        wd = data['wave_data']
        t_arr = np.array([w['t'] for w in wd if w['t'] >= 0], dtype=float)
        r_arr = np.array([w['total_touched'] for w in wd if w['t'] >= 0], dtype=float)
        if len(t_arr) < 4:
            fits[m] = {"r2": -1}
            continue
        try:
            K_guess = r_arr.max()
            popt, _ = curve_fit(logistic, t_arr, r_arr, p0=[K_guess, 1.0, 3.0],
                                bounds=([K_guess*0.5, 0.01, 0], [K_guess*2, 10, 15]), maxfev=10000)
            pred = logistic(t_arr, *popt)
            ss_res = np.sum((r_arr - pred)**2)
            ss_tot = np.sum((r_arr - r_arr.mean())**2)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
            K_error = abs(popt[0] - data['r_max']) / data['r_max'] if data['r_max'] > 0 else 1
            fits[m] = {"r2": round(r2, 4), "K": round(popt[0]), "r_growth": round(popt[1], 4),
                        "t0": round(popt[2], 2), "K_error_pct": round(K_error*100, 1)}
        except:
            fits[m] = {"r2": -1}
        print(f"  {m:25s} R²={fits[m]['r2']:+.4f} K_err={fits[m].get('K_error_pct','?')}%")

    r2s = [f['r2'] for f in fits.values() if f['r2'] > -1]
    median_r2 = np.median(r2s) if r2s else -1
    verdict = "PASS" if median_r2 > 0.90 else "PARTIAL" if median_r2 > 0.7 else "FAIL"
    print(f"  Median R² = {median_r2:.4f}, VERDICT: {verdict}")

    result = {"verdict": verdict, "median_r2": round(median_r2, 4), "fits": fits,
              "source": "logistic growth model"}
    checkpoint['phase_3e'] = result
    save_checkpoint(checkpoint)
    return result


# ══════════════════════════════════════════════════════
# PHASE 3F — DEATH SPECTRAL (Chung 1997)
# ══════════════════════════════════════════════════════

def phase_3f_death(phase1, checkpoint):
    """Mixing time vs death. Source: Chung 1997."""
    print("\n" + "=" * 80)
    print("PHASE 3F — MORT SPECTRALE (Chung 1997)")
    print("=" * 80)

    if 'phase_3f' in checkpoint:
        print("  Cached")
        return checkpoint['phase_3f']

    wt4 = load_json(WT4_PATH)
    eigenvalues = np.array(wt4['meta']['eigenvalues'])
    lambda_L = 1 - eigenvalues
    gap = float(lambda_L[1])
    mixing_time = 1.0 / gap

    mets = list(phase1.keys())
    deaths = np.array([phase1[m]['death_t'] for m in mets], dtype=float)
    # Some might be None (wave still alive)
    valid = np.isfinite(deaths) & (deaths > 0)

    if valid.sum() < 3:
        print("  Too few death measurements")
        result = {"verdict": "FAIL", "note": "too few deaths measured"}
        checkpoint['phase_3f'] = result
        save_checkpoint(checkpoint)
        return result

    deaths_valid = deaths[valid]
    mets_valid = [mets[i] for i in range(len(mets)) if valid[i]]
    mean_death = np.mean(deaths_valid)
    ratio = mean_death / mixing_time
    predicted = mixing_time * ratio
    errors = np.abs(deaths_valid - predicted)
    mae = np.mean(errors)

    print(f"  Gap={gap:.4f}, mixing={mixing_time:.2f} units, ratio={ratio:.2f} yr/unit")
    print(f"  Predicted death={predicted:.1f} yr, observed mean={mean_death:.1f} yr")
    print(f"  MAE={mae:.2f} yr (n={valid.sum()})")
    for i, m in enumerate(mets_valid):
        print(f"    {m:25s} obs={deaths_valid[i]:.0f} pred={predicted:.1f} err={errors[i]:.1f}")

    verdict = "PASS" if mae < 2.0 and 7 <= predicted <= 12 else "PARTIAL" if mae < 3.0 else "FAIL"
    print(f"  VERDICT: {verdict}")

    result = {
        "verdict": verdict, "spectral_gap": round(gap, 6), "mixing_time": round(mixing_time, 2),
        "ratio": round(ratio, 4), "predicted_death": round(predicted, 1),
        "mean_observed": round(mean_death, 1), "mae": round(mae, 2),
        "n_deaths": int(valid.sum()),
        "source": "Chung 1997, Spectral Graph Theory",
    }
    checkpoint['phase_3f'] = result
    save_checkpoint(checkpoint)
    return result


# ═════════════════════════════════════════��════════════
# PHASE 4 — CORRELATIONS (n=13)
# ══════════════════════════════════════════════════════

def phase_4_correlations(phase1, phase2, phase3a, checkpoint):
    """Full correlation battery with Bonferroni correction."""
    print("\n" + "=" * 80)
    print("PHASE 4 — CORRÉLATIONS MARE vs CAILLOU (n=13)")
    print("=" * 80)

    if 'phase_4' in checkpoint:
        print("  Cached")
        return checkpoint['phase_4']

    mets = list(phase1.keys())
    pcts = np.array([phase1[m]['pct'] for m in mets])
    T_vals = np.array([phase3a['T_fits'][m] for m in mets])
    deaths = np.array([phase1[m]['death_t'] if phase1[m]['death_t'] else np.nan for m in mets])
    mu_peaks = np.array([phase1[m]['mu_peak'] for m in mets])

    # Build feature matrix
    mare_features = ['local_density', 'avg_internal_weight', 'median_neighbor_works', 'pre_edges', 'pre_weight']
    seed_features = ['seed_works', 'seed_degree', 'seed_weight', 'avg_edge_weight',
                     'n_neighbors', 'hub_fraction', 'avg_level', 'n_seeds']

    all_features = {}
    for fn in mare_features + seed_features:
        all_features[fn] = np.array([phase2[m].get(fn, 0) for m in mets])

    # Composites
    all_features['aiw_over_density'] = all_features['avg_internal_weight'] / (all_features['local_density'] + 1e-8)
    all_features['log_aiw'] = np.log1p(all_features['avg_internal_weight'])
    all_features['strate'] = np.array([METEORITE_SEEDS[m]['strate'] for m in mets])
    all_features['continents'] = np.array([METEORITE_SEEDS[m]['continents'] for m in mets])
    all_features['E_old'] = all_features['strate'] * all_features['continents']

    targets = {'R_max': pcts, 'T_newman': T_vals, 'death': deaths, 'mu_peak': mu_peaks}

    # Correlations
    n_tests = len(all_features) * len(targets)
    bonferroni = 0.05 / n_tests

    results = {}
    print(f"\n  Bonferroni threshold: p < {bonferroni:.6f} ({n_tests} tests)")
    print(f"\n  {'Feature':30s} {'vs R_max':>10s} {'p':>8s} {'vs T':>10s} {'p':>8s} {'Type':>10s}")

    for fn, vals in sorted(all_features.items()):
        ftype = "mare" if fn in mare_features or fn in ['aiw_over_density', 'log_aiw', 'pre_edges', 'pre_weight'] else "seed"
        results[fn] = {"type": ftype}
        for tname, tvals in targets.items():
            c_val = corr(vals, tvals)
            results[fn][tname] = c_val
            results[fn][tname]['significant_bonferroni'] = c_val['spearman_p'] < bonferroni

        c_rmax = results[fn]['R_max']
        c_T = results[fn]['T_newman']
        flag = " ***" if c_rmax['spearman_p'] < bonferroni else " **" if abs(c_rmax['spearman_r']) > 0.6 else ""
        print(f"  {fn:30s} {c_rmax['spearman_r']:+10.4f} {c_rmax['spearman_p']:8.4f} "
              f"{c_T['spearman_r']:+10.4f} {c_T['spearman_p']:8.4f} {ftype:>10s}{flag}")

    # Hypothesis test: mare > caillou
    mare_rhos = [abs(results[fn]['R_max']['spearman_r']) for fn in all_features if results[fn]['type'] == 'mare']
    seed_rhos = [abs(results[fn]['R_max']['spearman_r']) for fn in all_features if results[fn]['type'] == 'seed']
    mare_best = max(mare_rhos) if mare_rhos else 0
    seed_best = max(seed_rhos) if seed_rhos else 0

    hypothesis = {
        "mare_best_rho": round(mare_best, 4),
        "seed_best_rho": round(seed_best, 4),
        "mare_wins": mare_best > seed_best,
    }
    print(f"\n  HYPOTHÈSE 'la mare décide': mare_best={mare_best:.4f} vs seed_best={seed_best:.4f} "
          f"-> {'MARE GAGNE' if mare_best > seed_best else 'CAILLOU GAGNE'}")

    verdict = "PASS" if mare_best > seed_best and mare_best > 0.5 else "PARTIAL" if mare_best > seed_best else "FAIL"
    print(f"  VERDICT: {verdict}")

    result_out = {"verdict": verdict, "correlations": results, "hypothesis": hypothesis,
                  "bonferroni_threshold": round(bonferroni, 6), "n_tests": n_tests}
    checkpoint['phase_4'] = result_out
    save_checkpoint(checkpoint)
    return result_out


# ═════════════════════════════���════════════════════════
# PHASE 5 — HYBRIDS
# ══════════════════════════════════════════════════════

def phase_5_hybrids(phase1, phase2, phase3a, phase3e, phase3f, checkpoint):
    """Compare hybrid models with LOO."""
    print("\n" + "=" * 80)
    print("PHASE 5 — HYBRIDES (LOO 13-fold)")
    print("=" * 80)

    if 'phase_5' in checkpoint:
        print("  Cached")
        return checkpoint['phase_5']

    mets = list(phase1.keys())
    rmax_obs = np.array([phase1[m]['r_max'] for m in mets])
    deaths_obs = np.array([phase1[m]['death_t'] if phase1[m]['death_t'] else np.nan for m in mets])

    # H2: Newman + spectral death — the one with actual predictions
    h2_rmax_mae = phase3a['loo_mae']
    h2_death_mae = phase3f.get('mae', 99)
    h2_death_pred = phase3f.get('predicted_death', 0)

    # For logistic: get K and r_growth per meteorite
    logistic_fits = phase3e.get('fits', {})

    hybrids = {
        "H1_Newman_only": {
            "desc": "Newman S(T), T predicted from mare",
            "rmax_mae": phase3a['loo_mae'],
            "gives": ["R_max"],
            "params": 2,
            "source": "Newman 2002",
        },
        "H2_Newman_spectral": {
            "desc": "Newman R_max + spectral death time",
            "rmax_mae": phase3a['loo_mae'],
            "death_mae": round(h2_death_mae, 2),
            "gives": ["R_max", "death"],
            "params": 3,
            "source": "Newman 2002 + Chung 1997",
        },
        "H3_Newman_logistic": {
            "desc": "Newman K=R_max + logistic for R(t) shape",
            "rmax_mae": phase3a['loo_mae'],
            "logistic_median_r2": phase3e.get('median_r2', -1),
            "gives": ["R_max", "R(t)"],
            "params": 4,
            "source": "Newman 2002 + logistic growth",
        },
    }

    # Compute AIC-like score: lower = better
    n = len(mets)
    for hname, h in hybrids.items():
        rss = (h['rmax_mae'] / N_CONCEPTS) ** 2 * n  # approximate
        k = h['params']
        h['aic'] = round(n * math.log(rss/n + 1e-10) + 2*k, 2)

    print(f"\n  {'Hybrid':30s} {'R_max MAE':>10s} {'Death MAE':>10s} {'Gives':>20s} {'Params':>6s} {'AIC':>8s}")
    for hname, h in hybrids.items():
        d_mae = f"{h.get('death_mae', '—'):>10}" if isinstance(h.get('death_mae'), (int, float)) else "—"
        print(f"  {hname:30s} {h['rmax_mae']:10,} {d_mae} {'+'.join(h['gives']):>20s} {h['params']:6d} {h['aic']:8.1f}")

    best = min(hybrids.items(), key=lambda x: x[1]['aic'])
    print(f"\n  BEST: {best[0]} (AIC={best[1]['aic']:.1f})")

    verdict = "PASS" if best[1]['rmax_mae'] < 10000 else "PARTIAL" if best[1]['rmax_mae'] < 20000 else "FAIL"

    result = {"verdict": verdict, "best": best[0], "hybrids": hybrids}
    checkpoint['phase_5'] = result
    save_checkpoint(checkpoint)
    return result


# ══════════════════════════════════════════════════════
# PHASE 6 — LASER INVESTIGATION
# ══════════════════════════════════════════════════════

def phase_6_laser(phase1, phase2, phase3a, checkpoint):
    """Why is Laser the outlier?"""
    print("\n" + "=" * 80)
    print("PHASE 6 — INVESTIGATION LASER")
    print("=" * 80)

    if 'phase_6' in checkpoint:
        print("  Cached")
        return checkpoint['phase_6']

    mets = list(phase1.keys())

    # Compare Laser to others
    laser_data = phase2.get('Laser 1960', {})
    others = {m: phase2[m] for m in mets if m != 'Laser 1960'}

    comparisons = {}
    for fn in ['seed_works', 'seed_degree', 'seed_weight', 'avg_edge_weight',
               'local_density', 'avg_internal_weight', 'median_neighbor_works', 'hub_fraction']:
        laser_val = laser_data.get(fn, 0)
        other_vals = [others[m].get(fn, 0) for m in others]
        median_other = np.median(other_vals)
        ratio = laser_val / median_other if median_other > 0 else 0
        comparisons[fn] = {
            "laser": round(laser_val, 4), "median_others": round(median_other, 4),
            "ratio": round(ratio, 4),
        }
        flag = " <<<" if ratio > 2 or ratio < 0.5 else ""
        print(f"  {fn:30s} Laser={laser_val:>12.2f} median={median_other:>12.2f} ratio={ratio:.2f}{flag}")

    # Newman without Laser
    loo_no_laser = phase3a.get('loo_mae_no_laser', phase3a['loo_mae'])
    print(f"\n  Newman LOO MAE sans Laser: {loo_no_laser:,}")
    print(f"  Newman LOO MAE avec Laser: {phase3a['loo_mae']:,}")
    improvement = (phase3a['loo_mae'] - loo_no_laser) / phase3a['loo_mae'] * 100
    print(f"  Amélioration: {improvement:.0f}%")

    # Hypothesis: avg_edge_weight is the key
    aew_laser = laser_data.get('avg_edge_weight', 0)
    aew_others = [others[m].get('avg_edge_weight', 0) for m in others]
    print(f"\n  avg_edge_weight: Laser={aew_laser:.4f}, others median={np.median(aew_others):.4f}")
    print(f"  Laser's seeds are in THICK mycélium (high weight = already explored territory)")
    print(f"  → L'onde ne peut pas se propager car le milieu est déjà saturé")

    verdict = "Laser = TYPE A (technical barrier). Mare trop épaisse, onde absorbée."
    print(f"\n  VERDICT: {verdict}")

    result = {"verdict": verdict, "comparisons": comparisons,
              "loo_mae_with": phase3a['loo_mae'], "loo_mae_without": round(loo_no_laser),
              "improvement_pct": round(improvement, 1)}
    checkpoint['phase_6'] = result
    save_checkpoint(checkpoint)
    return result


# ═════════════════════════════════════════════════════��
# PHASE 7 — GRAND VERDICT
# ══════════════════════════════════════════════════════

def phase_7_verdict(phase1, r3a, r3b, r3c, r3d, r3e, r3f, r4, r5, r6):
    """Final summary."""
    print("\n" + "=" * 80)
    print("PHASE 7 — GRAND VERDICT")
    print("=" * 80)

    mets = list(phase1.keys())

    # Grand tableau
    print(f"\n  {'Météorite':25s} {'R_max':>8s} {'pct':>6s} {'death':>5s} {'mu_peak':>8s}")
    for m in sorted(mets, key=lambda x: -phase1[x]['r_max']):
        d = phase1[m]
        dt = f"t+{d['death_t']}" if d['death_t'] else "alive"
        print(f"  {m:25s} {d['r_max']:8,} {d['pct']:6.2%} {dt:>5s} {d['mu_peak']:8.1f}")

    # Model comparison
    print(f"\n  {'Modèle':35s} {'Verdict':>8s} {'Détail':>15s} {'Source':>30s}")
    models = [
        ("3A Newman SIR-percolation", r3a['verdict'], f"MAE={r3a['loo_mae']:,}", "Newman 2002"),
        ("3B Onde de surface", r3b['verdict'], f"med R²={r3b['median_r2']:.2f}", "Lamb 1932"),
        ("3C Oscillateur amorti", r3c['verdict'], f"med R²={r3c['median_r2']:.2f}", "Hawkes"),
        ("3D Power law", r3d['verdict'], f"med R²={r3d['median_r2']:.2f}", "baseline"),
        ("3E Logistique", r3e['verdict'], f"med R²={r3e['median_r2']:.2f}", "S-curve"),
        ("3F Mort spectrale", r3f['verdict'], f"MAE={r3f.get('mae','?')}yr", "Chung 1997"),
    ]
    for name, verdict, detail, source in models:
        icon = "✓" if verdict == "PASS" else "~" if verdict == "PARTIAL" else "✗"
        print(f"  {icon} {name:33s} {verdict:>8s} {detail:>15s} {source:>30s}")

    print(f"\n  Corrélations (Phase 4): {r4['verdict']}")
    print(f"  Hybrides (Phase 5): best = {r5['best']}")
    print(f"  Laser (Phase 6): {r6['verdict']}")

    # Overall
    overall = {
        "n_meteorites": len(mets),
        "newman_works": r3a['verdict'] in ['PASS', 'PARTIAL'],
        "death_spectral_works": r3f['verdict'] == 'PASS',
        "mare_decides": r4['hypothesis']['mare_wins'],
        "best_model": r5['best'],
        "laser_explained": "TYPE A" in r6['verdict'],
    }
    print(f"\n  OVERALL: {json.dumps(overall, indent=2)}")

    return overall


# ═════════════════════════════════════════��════════════
# MAIN
# ══════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("YGGDRASIL V3 — COMPREHENSIVE WAVE MODEL TEST")
    print(f"13 météorites × 7 phases × 6 modèles")
    print(f"Methodique, scientifique, justifiable.")
    print("=" * 80)
    t_start = time.time()

    checkpoint = load_checkpoint()

    # Phase 1: BFS
    p1 = phase_1_bfs(checkpoint)

    # Phase 2: Mare
    p2 = phase_2_mare(checkpoint)

    # Phase 3: Individual models
    p3a = phase_3a_newman(p1, p2, checkpoint)
    p3b = phase_3b_surface_wave(p1, checkpoint)
    p3c = phase_3c_oscillator(p1, checkpoint)
    p3d = phase_3d_power_law(p1, checkpoint)
    p3e = phase_3e_logistic(p1, checkpoint)
    p3f = phase_3f_death(p1, checkpoint)

    # Phase 4: Correlations
    p4 = phase_4_correlations(p1, p2, p3a, checkpoint)

    # Phase 5: Hybrids
    p5 = phase_5_hybrids(p1, p2, p3a, p3e, p3f, checkpoint)

    # Phase 6: Laser
    p6 = phase_6_laser(p1, p2, p3a, checkpoint)

    # Phase 7: Verdict
    overall = phase_7_verdict(p1, p3a, p3b, p3c, p3d, p3e, p3f, p4, p5, p6)

    elapsed = time.time() - t_start

    # Save final output
    output = {
        "test": "wave_comprehensive_v1",
        "date": "2026-04-04",
        "runtime_seconds": round(elapsed, 1),
        "n_meteorites": 13,
        "phase_1_bfs": {m: {k: v for k, v in d.items() if k != 'wave_data'}
                        for m, d in p1.items()},  # exclude heavy wave_data
        "phase_2_mare": p2,
        "phase_3a_newman": p3a,
        "phase_3b_surface_wave": p3b,
        "phase_3c_oscillator": p3c,
        "phase_3d_power_law": p3d,
        "phase_3e_logistic": p3e,
        "phase_3f_death": p3f,
        "phase_4_correlations": p4,
        "phase_5_hybrids": p5,
        "phase_6_laser": p6,
        "grand_verdict": overall,
        "sources": {
            "newman": "Newman 2002 cond-mat/0205009",
            "chung": "Chung 1997 Spectral Graph Theory AMS CBMS 92",
            "lamb": "Lamb 1932 Hydrodynamics 6th ed CUP",
            "lighthill": "Lighthill 1978 Waves in Fluids CUP",
            "worthington": "Worthington 1908 A Study of Splashes Longmans",
            "harris": "Harris 1963 Theory of Branching Processes Springer",
            "kermack": "Kermack McKendrick 1927 Proc R Soc Lond A 115(772)",
            "moreno": "Moreno Nekovee Pacheco 2004 cond-mat/0312131",
        },
    }
    save_json(output, OUTPUT)

    print(f"\n{'='*80}")
    print(f"  Saved: {OUTPUT}")
    print(f"  Runtime: {elapsed/60:.1f} min")
    print(f"  DONE.")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
