"""
YGGDRASIL ENGINE — Godel Hold-Out v3 (Wave Propagation)
========================================================
Le caillou dans la mare.

Pour chaque meteorite:
1. t=0: point d'impact (seed concepts)
2. Chaque annee: nouvelles aretes cooc qui touchent le front -> onde
3. R(t) = total concepts touches (l'onde qui s'elargit)

Train sur 12, predict Godel.

Auteur: Sky x Claude (Opus 4.6) — Session 33, 2 avril 2026
"""
import json
import sys
import os
import sqlite3
import numpy as np
from pathlib import Path
from scipy.optimize import curve_fit
from collections import defaultdict
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.analysis.meteorites import impact_energy

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
WT3_PATH = DATA_DIR / "wt3.db"
OUTPUT_PATH = DATA_DIR / "results" / "godel_holdout_wave.json"

GODEL_NAME = "Godel 1931"

METEORITE_SEEDS = {
    "Shannon 1948": {
        "open": "1948", "strate": "S1", "continents": 7,
        "seeds": [57221, 1033],
    },
    "ADN Watson-Crick 1953": {
        "open": "1953", "strate": "S0", "continents": 5,
        "seeds": [58019, 8408],
    },
    "Transistor 1947": {
        "open": "1947", "strate": "S0", "continents": 6,
        "seeds": [11323, 1331],
    },
    "Laser 1960": {
        "open": "1960", "strate": "S0", "continents": 5,
        "seeds": [57047, 53232],
    },
    "Godel 1931": {
        "open": "1931", "strate": "S6", "continents": 9,
        "seeds": [12665, 8122, 1806],
    },
    "Turing 1936": {
        "open": "1936", "strate": "S6", "continents": 4,
        "seeds": [8122, 5866, 1806],
    },
    "CRISPR 2012": {
        "open": "2012", "strate": "S0", "continents": 4,
        "seeds": [64738, 5064],
    },
    "AlphaFold 2020": {
        "open": "2020", "strate": "S0", "continents": 3,
        "seeds": [12593, 16301],
    },
    "Gravitational waves 2016": {
        "open": "2016", "strate": "S1", "continents": 2,
        "seeds": [14090],
    },
    "Higgs boson 2012": {
        "open": "2012", "strate": "S1", "continents": 2,
        "seeds": [9062],
    },
    "mRNA vaccines 2020": {
        "open": "1990", "strate": "S0", "continents": 4,
        "seeds": [380, 39251],
    },
    "Internet TCP/IP 1974": {
        "open": "1974", "strate": "S0", "continents": 7,
        "seeds": [1758, 53391, 2196],
    },
    "Poincare-Perelman 2003": {
        "open": "2003", "strate": "S3", "continents": 1,
        "seeds": [63206, 41700],
    },
}

MAX_YEARS = 15
STOP_THRESHOLD = 3  # stop if new_concepts < this for 2 years in a row


def measure_wave(db, name, seeds, impact_year):
    """Measure wave propagation from impact point."""
    wavefront = set(seeds)
    all_touched = set(seeds)
    edges_seen = set()
    results = []
    wave = 0
    stall_count = 0

    for yr in range(impact_year, impact_year + MAX_YEARS):
        t0 = time.time()

        # Build temp table for front
        db.execute('DROP TABLE IF EXISTS tmp_front')
        db.execute('CREATE TEMP TABLE tmp_front (cid INTEGER PRIMARY KEY)')
        db.executemany('INSERT INTO tmp_front VALUES (?)', [(c,) for c in wavefront])

        new_edges = 0
        new_concepts = set()

        # Yearly period (pre-1980)
        yr_str = str(yr)
        rows = db.execute('''
            SELECT c.concept_a, c.concept_b
            FROM cooc c
            INNER JOIN tmp_front f ON c.concept_a = f.cid
            WHERE c.period = ?
        ''', (yr_str,)).fetchall()

        for ca, cb in rows:
            edge = (ca, cb) if ca < cb else (cb, ca)
            if edge not in edges_seen:
                edges_seen.add(edge)
                new_edges += 1
                if cb not in all_touched:
                    new_concepts.add(cb)

        # Monthly periods (post-1980)
        if yr >= 1980:
            for mo in range(1, 13):
                rows_m = db.execute('''
                    SELECT c.concept_a, c.concept_b
                    FROM cooc c
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
            "t": offset,
            "year": yr,
            "wave": wave,
            "front": len(wavefront),
            "new_edges": new_edges,
            "new_concepts": len(new_concepts),
            "total_touched": len(all_touched),
        })

        dt = time.time() - t0
        print(f"    {yr} w={wave:2d} front={len(wavefront):6d} "
              f"edges={new_edges:8,} new_c={len(new_concepts):6,} "
              f"total={len(all_touched):6,} ({dt:.0f}s)", flush=True)

        # Early stop
        if stall_count >= 2 and offset >= 5:
            print(f"    -> wave dead, stopping", flush=True)
            break

    return results


def run():
    print("=" * 60, flush=True)
    print("  GODEL HOLD-OUT v3 — WAVE PROPAGATION", flush=True)
    print("  Le caillou dans la mare", flush=True)
    print("=" * 60, flush=True)

    db = sqlite3.connect(str(WT3_PATH))

    # Measure all 13 meteorites
    all_waves = {}
    for name, info in METEORITE_SEEDS.items():
        print(f"\n  {name}:", flush=True)
        t0 = time.time()
        impact_yr = int(info["open"][:4])
        E = impact_energy(info["strate"], info["continents"])

        wave_data = measure_wave(db, name, info["seeds"], impact_yr)

        # R(t) series: (t_years, total_concepts_touched)
        r_series = [(w["t"], w["total_touched"]) for w in wave_data if w["t"] > 0]
        r_max = max(w["total_touched"] for w in wave_data) if wave_data else 0

        # Peak wave (year with max new_edges)
        peak = max(wave_data, key=lambda w: w["new_edges"]) if wave_data else None
        peak_year = peak["year"] if peak else None
        peak_edges = peak["new_edges"] if peak else 0

        # Wave death (first year with 0 new concepts after wave >= 3)
        death_t = None
        for w in wave_data:
            if w["wave"] >= 3 and w["new_concepts"] == 0:
                death_t = w["t"]
                break

        all_waves[name] = {
            "E": E,
            "seeds": info["seeds"],
            "open_year": impact_yr,
            "n_seeds": len(info["seeds"]),
            "wave_data": wave_data,
            "r_series": r_series,
            "r_max": r_max,
            "peak_year": peak_year,
            "peak_edges": peak_edges,
            "death_t": death_t,
        }

        total_time = time.time() - t0
        print(f"  -> R_max={r_max:,} concepts, peak={peak_year} ({peak_edges:,} edges), "
              f"death=t+{death_t}, total {total_time:.0f}s", flush=True)

    # Split train / holdout
    godel = all_waves.pop(GODEL_NAME)
    train = all_waves

    print(f"\n{'='*60}", flush=True)
    print(f"  SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"  {'Name':35s} {'E':>5s} {'R_max':>8s} {'Peak_yr':>8s} {'Death':>6s}", flush=True)
    for name, m in sorted(train.items(), key=lambda x: -x[1]["r_max"]):
        d = f"t+{m['death_t']}" if m['death_t'] else "alive"
        print(f"  {name:35s} {m['E']:5.0f} {m['r_max']:8,} {m['peak_year'] or '?':>8} {d:>6s}", flush=True)
    d = f"t+{godel['death_t']}" if godel['death_t'] else "alive"
    print(f"  {'>>> '+GODEL_NAME:35s} {godel['E']:5.0f} {godel['r_max']:8,} {godel['peak_year'] or '?':>8} {d:>6s}", flush=True)

    # Fit Sedov on train
    print(f"\n{'='*60}", flush=True)
    print(f"  FIT (12 meteorites, Godel exclu)", flush=True)
    print(f"{'='*60}", flush=True)

    fit_points = []
    for name, m in train.items():
        E = m["E"]
        n_seeds = m["n_seeds"]
        for t, R in m["r_series"]:
            if t > 0 and R > len(m["seeds"]):  # only after wave starts
                fit_points.append((E, float(n_seeds), float(t), float(R), name))

    E_arr = np.array([p[0] for p in fit_points])
    ns_arr = np.array([p[1] for p in fit_points])  # n_seeds as density proxy
    t_arr = np.array([p[2] for p in fit_points])
    R_arr = np.array([p[3] for p in fit_points])

    print(f"  {len(fit_points)} points from {len(train)} meteorites", flush=True)

    # Fit: R(t) = beta * E^a * t^b
    # Simple: no rho0, just energy and time
    def model_simple(X, beta, a, b):
        E, t = X
        return beta * np.power(E, a) * np.power(t, b)

    results = {}
    try:
        popt, pcov = curve_fit(
            model_simple, (E_arr, t_arr), R_arr,
            p0=[100.0, 0.5, 1.0],
            bounds=([0.001, 0.01, 0.01], [100000.0, 3.0, 5.0]),
            maxfev=10000,
        )
        beta, a, b = popt
        R_pred = model_simple((E_arr, t_arr), *popt)
        ss_res = np.sum((R_arr - R_pred)**2)
        ss_tot = np.sum((R_arr - np.mean(R_arr))**2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        print(f"  Fit: R = {beta:.2f} * E^{a:.4f} * t^{b:.4f}, R2={r2:.4f}", flush=True)
        results["fit_simple"] = {
            "beta": round(float(beta), 4),
            "a_energy": round(float(a), 4),
            "b_time": round(float(b), 4),
            "r2": round(float(r2), 4),
        }
    except Exception as e:
        print(f"  Fit FAILED: {e}", flush=True)
        beta, a, b, r2 = 1.0, 0.5, 1.0, 0.0

    # Fit Sedov classic: R = beta * (E*t^2)^alpha
    x_sedov = E_arr * t_arr**2
    def sedov_classic(x, beta, alpha):
        return beta * np.power(x, alpha)

    try:
        popt_s, pcov_s = curve_fit(
            sedov_classic, x_sedov, R_arr,
            p0=[100.0, 0.4],
            bounds=([0.001, 0.01], [100000.0, 2.0]),
            maxfev=10000,
        )
        beta_s, alpha_s = popt_s
        R_pred_s = sedov_classic(x_sedov, *popt_s)
        ss_res_s = np.sum((R_arr - R_pred_s)**2)
        r2_s = 1.0 - ss_res_s / ss_tot if ss_tot > 0 else 0.0
        print(f"  Sedov: R = {beta_s:.2f} * (E*t^2)^{alpha_s:.4f}, R2={r2_s:.4f}", flush=True)
        results["fit_sedov"] = {
            "beta": round(float(beta_s), 4),
            "alpha": round(float(alpha_s), 4),
            "r2": round(float(r2_s), 4),
        }
    except Exception as e:
        print(f"  Sedov fit FAILED: {e}", flush=True)
        beta_s, alpha_s, r2_s = 1.0, 0.4, 0.0

    # Predict Godel
    print(f"\n{'='*60}", flush=True)
    print(f"  PREDICTION GODEL", flush=True)
    print(f"{'='*60}", flush=True)

    E_g = godel["E"]
    predictions = []
    for t, R_obs in godel["r_series"]:
        if t > 0:
            R_simple = beta * E_g**a * t**b
            R_sedov = beta_s * (E_g * t**2)**alpha_s
            predictions.append({
                "t": t, "R_obs": R_obs,
                "R_simple": round(R_simple, 0),
                "R_sedov": round(R_sedov, 0),
                "ratio_simple": round(R_obs / R_simple, 4) if R_simple > 0 else None,
                "ratio_sedov": round(R_obs / R_sedov, 4) if R_sedov > 0 else None,
            })

    print(f"  {'t':>3s}  {'R_obs':>8s}  {'R_simple':>9s}  {'ratio_s':>8s}  {'R_sedov':>9s}  {'ratio_v':>8s}", flush=True)
    for p in predictions:
        print(f"  {p['t']:3d}  {p['R_obs']:8,}  {p['R_simple']:9,.0f}  "
              f"{p['ratio_simple'] or 0:8.4f}  {p['R_sedov']:9,.0f}  "
              f"{p['ratio_sedov'] or 0:8.4f}", flush=True)

    # Stats
    def calc_stats(preds, key_pred, key_ratio):
        obs = np.array([p["R_obs"] for p in preds if p[key_pred]])
        pred = np.array([p[key_pred] for p in preds if p[key_pred]])
        ratios = np.array([p[key_ratio] for p in preds if p[key_ratio]])
        if len(obs) == 0:
            return {}
        ss_res = np.sum((obs - pred)**2)
        ss_tot = np.sum((obs - np.mean(obs))**2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return {
            "r2_holdout": round(float(r2), 4),
            "mean_ratio": round(float(np.mean(ratios)), 4),
            "rmse": round(float(np.sqrt(np.mean((obs - pred)**2))), 0),
        }

    stats_simple = calc_stats(predictions, "R_simple", "ratio_simple")
    stats_sedov = calc_stats(predictions, "R_sedov", "ratio_sedov")

    print(f"\n  Simple: R2={stats_simple.get('r2_holdout','?')}, "
          f"ratio={stats_simple.get('mean_ratio','?')}, RMSE={stats_simple.get('rmse','?')}", flush=True)
    print(f"  Sedov:  R2={stats_sedov.get('r2_holdout','?')}, "
          f"ratio={stats_sedov.get('mean_ratio','?')}, RMSE={stats_sedov.get('rmse','?')}", flush=True)

    # Verdict
    best = stats_sedov if stats_sedov.get("r2_holdout", -999) > stats_simple.get("r2_holdout", -999) else stats_simple
    ratio = best.get("mean_ratio")
    r2_ho = best.get("r2_holdout")

    if ratio and r2_ho is not None:
        if 0.5 <= ratio <= 2.0 and r2_ho > 0.5:
            verdict = "PASS"
        elif 0.3 <= ratio <= 3.0 and r2_ho > 0.0:
            verdict = "PARTIAL"
        elif 0.3 <= ratio <= 3.0:
            verdict = "WEAK"
        else:
            verdict = "FAIL"
    else:
        verdict = "INCONCLUSIVE"

    print(f"\n  VERDICT: {verdict}", flush=True)

    # Save
    output = {
        "test": "godel_holdout_wave",
        "date": "2026-04-02",
        "version": "v3_wave_propagation",
        "method": "BFS wave from impact seeds through cooc edges per year. R(t) = total concepts touched.",
        "results": results,
        "stats_simple": stats_simple,
        "stats_sedov": stats_sedov,
        "verdict": verdict,
        "godel_prediction": predictions,
        "godel_wave": godel["wave_data"],
        "all_meteorites": {
            name: {
                "E": m["E"],
                "seeds": m["seeds"],
                "r_max": m["r_max"],
                "peak_year": m["peak_year"],
                "peak_edges": m["peak_edges"],
                "death_t": m["death_t"],
                "r_series": m["r_series"],
            }
            for name, m in train.items()
        },
    }

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Saved -> {OUTPUT_PATH}", flush=True)

    db.close()


if __name__ == "__main__":
    run()
