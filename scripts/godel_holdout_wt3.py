"""
YGGDRASIL ENGINE — Godel Hold-Out Test v2 (WT3 local blast)
=============================================================
Mesure le VRAI R(t) local: nouvelles aretes co-occurrence
autour des concepts-graines de chaque meteorite dans WT3.

Train: 12 meteorites, Test: Godel 1931.

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
from engine.analysis.meteorites import impact_energy, classify_candle, Candle

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
WT3_PATH = DATA_DIR / "wt3.db"
OUTPUT_PATH = DATA_DIR / "results" / "godel_holdout_wt3.json"

GODEL_NAME = "Godel 1931"

# =====================================================================
# SEED CONCEPTS — concepts-graines par meteorite (idx dans concepts_65k)
# Curated from OpenAlex concept search
# =====================================================================

METEORITE_SEEDS = {
    "Shannon 1948": {
        "open": "1948", "strate": "S1", "continents": 7,
        "seeds": [57221, 1033],  # Information theory, Entropy
    },
    "ADN Watson-Crick 1953": {
        "open": "1953", "strate": "S0", "continents": 5,
        "seeds": [58019, 8408],  # DNA, Molecular biology
    },
    "Transistor 1947": {
        "open": "1947", "strate": "S0", "continents": 6,
        "seeds": [11323, 1331],  # Transistor, Semiconductor
    },
    "Laser 1960": {
        "open": "1960", "strate": "S0", "continents": 5,
        "seeds": [57047, 53232],  # Laser, Stimulated emission
    },
    "Godel 1931": {
        "open": "1931", "strate": "S6", "continents": 9,
        "seeds": [12665, 8122, 1806],  # Incompleteness theorems, Computability, Computability theory
    },
    "Turing 1936": {
        "open": "1936", "strate": "S6", "continents": 4,
        "seeds": [8122, 5866, 1806],  # Computability, Halting problem, Computability theory
    },
    "CRISPR 2012": {
        "open": "2012", "strate": "S0", "continents": 4,
        "seeds": [64738, 5064],  # CRISPR, Cas9
    },
    "AlphaFold 2020": {
        "open": "2020", "strate": "S0", "continents": 3,
        "seeds": [12593, 16301],  # Protein structure prediction, Protein folding
    },
    "Gravitational waves 2016": {
        "open": "2016", "strate": "S1", "continents": 2,
        "seeds": [14090],  # Gravitational wave
    },
    "Higgs boson 2012": {
        "open": "2012", "strate": "S1", "continents": 2,
        "seeds": [9062],  # Higgs boson
    },
    "mRNA vaccines 2020": {
        "open": "1990", "strate": "S0", "continents": 4,
        "seeds": [380, 39251],  # Precursor mRNA, Vaccine efficacy
    },
    "Internet TCP/IP 1974": {
        "open": "1974", "strate": "S0", "continents": 7,
        "seeds": [1758, 53391, 2196],  # The Internet, Computer network, Packet switching
    },
    "Poincare-Perelman 2003": {
        "open": "2003", "strate": "S3", "continents": 1,
        "seeds": [63206, 41700],  # Poincare conjecture, Conjecture
    },
}


def measure_local_blast(db, seeds, open_year, window_years=10):
    """
    Measure local blast: count cumulative new cooc edges around seed concepts
    after the impact year, per year.

    Uses concept_a index only (fast, ~0s per query).
    Returns [(year_offset, cumulative_new_edges, cumulative_weight), ...]
    """
    # Step 1: count edges BEFORE impact (baseline)
    baseline_edges = set()
    baseline_weight = 0.0

    for seed in seeds:
        rows = db.execute(
            "SELECT concept_b, weight FROM cooc WHERE concept_a = ? AND period < ?",
            (seed, str(open_year))
        ).fetchall()
        for b, w in rows:
            baseline_edges.add((seed, b))
            baseline_weight += w

    # Step 2: track new edges per year after impact
    yearly_new = {}
    seen_edges = set(baseline_edges)

    for yr in range(open_year, open_year + window_years + 1):
        yr_str = str(yr)
        new_this_year = 0
        weight_this_year = 0.0

        for seed in seeds:
            # Exact year match (pre-1980 = yearly periods)
            rows = db.execute(
                "SELECT concept_b, weight FROM cooc WHERE concept_a = ? AND period = ?",
                (seed, yr_str)
            ).fetchall()

            # Also check monthly periods (post-1980)
            rows_monthly = db.execute(
                "SELECT concept_b, weight FROM cooc WHERE concept_a = ? AND period >= ? AND period < ?",
                (seed, f"{yr}-01", f"{yr+1}-01")
            ).fetchall()

            for b, w in rows + rows_monthly:
                edge = (seed, b)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    new_this_year += 1
                    weight_this_year += w

        yearly_new[yr] = (new_this_year, weight_this_year)

    # Build cumulative series
    result = []
    cum_edges = 0
    cum_weight = 0.0
    for yr in range(open_year, open_year + window_years + 1):
        offset = yr - open_year
        ne, nw = yearly_new.get(yr, (0, 0.0))
        cum_edges += ne
        cum_weight += nw
        result.append({
            "year_offset": offset,
            "year": yr,
            "new_edges": ne,
            "cum_edges": cum_edges,
            "cum_weight": round(cum_weight, 4),
        })

    return result, len(baseline_edges), baseline_weight


def run():
    print("=" * 60)
    print("  GODEL HOLD-OUT v2 — LOCAL BLAST (WT3)")
    print("  Train: 12 meteorites  |  Test: Godel 1931")
    print("=" * 60)

    db = sqlite3.connect(str(WT3_PATH))
    print(f"  Connected to WT3: {WT3_PATH}")

    # 1. Measure local blast for all 13 meteorites
    measurements = {}
    for name, info in METEORITE_SEEDS.items():
        t0 = time.time()
        open_yr = int(info["open"][:4])
        blast, base_n, base_w = measure_local_blast(
            db, info["seeds"], open_yr, window_years=10
        )
        dt = time.time() - t0
        E = impact_energy(info["strate"], info["continents"])

        # R(t) = cumulative new edges at each year offset
        r_series = [(p["year_offset"], p["cum_edges"]) for p in blast if p["year_offset"] > 0]
        r_max = max(ce for _, ce in r_series) if r_series else 0

        measurements[name] = {
            "E": E,
            "seeds": info["seeds"],
            "open_year": open_yr,
            "baseline_edges": base_n,
            "baseline_weight": round(base_w, 2),
            "blast": blast,
            "r_series": r_series,
            "r_max": r_max,
        }

        print(f"  {name:35s} E={E:5.0f}  base={base_n:5d} edges  "
              f"R_max={r_max:5d}  ({dt:.1f}s)")

    # 2. Split train / holdout
    godel = measurements.pop(GODEL_NAME)
    train = measurements

    print(f"\n  Godel: {len(godel['r_series'])} points, R_max={godel['r_max']}")
    print(f"  Train: {len(train)} meteorites")

    # 3. Fit Sedov on train (12)
    # For rho0, use baseline_edges as density proxy (more edges = denser soil)
    print(f"\n{'='*60}")
    print(f"  FIT TRAIN — 12 meteorites (Godel EXCLU)")
    print(f"{'='*60}")

    fit_points = []
    for name, m in train.items():
        E = m["E"]
        rho0 = max(m["baseline_edges"], 1)  # density = pre-existing edges
        for t, R in m["r_series"]:
            if t > 0 and R > 0:
                fit_points.append((E, float(rho0), float(t), float(R), name))

    E_arr = np.array([p[0] for p in fit_points])
    rho_arr = np.array([p[1] for p in fit_points])
    t_arr = np.array([p[2] for p in fit_points])
    R_arr = np.array([p[3] for p in fit_points])

    print(f"  {len(fit_points)} fit points from {len(train)} meteorites")

    # Fit 1: Classic R = beta * (E*t^2/rho0)^alpha
    x = E_arr * t_arr**2 / rho_arr
    def sedov_classic(x, beta, alpha):
        return beta * np.power(x, alpha)

    try:
        popt1, pcov1 = curve_fit(
            sedov_classic, x, R_arr,
            p0=[10.0, 0.3],
            bounds=([0.001, 0.01], [100000.0, 2.0]),
            maxfev=10000,
        )
        beta1, alpha1 = popt1
        R_pred1 = sedov_classic(x, *popt1)
        ss_res = np.sum((R_arr - R_pred1)**2)
        ss_tot = np.sum((R_arr - np.mean(R_arr))**2)
        r2_1 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        perr1 = np.sqrt(np.diag(pcov1))
        print(f"  Fit 1: beta={beta1:.4f}, alpha={alpha1:.4f}, R2={r2_1:.4f}")
    except Exception as e:
        print(f"  Fit 1 FAILED: {e}")
        beta1, alpha1, r2_1 = 1.0, 0.2, 0.0

    # Fit 2: Separated R = beta * E^a * t^b * rho0^(-c)
    def sedov_sep(X, beta, a, b, c):
        E, t, rho = X
        return beta * np.power(E, a) * np.power(t, b) * np.power(rho, -c)

    fit2 = {}
    try:
        X_data = (E_arr, t_arr, rho_arr)
        popt2, pcov2 = curve_fit(
            sedov_sep, X_data, R_arr,
            p0=[10.0, 0.2, 0.4, 0.2],
            bounds=([0.001, 0.01, 0.01, 0.01], [100000.0, 2.0, 3.0, 2.0]),
            maxfev=10000,
        )
        b2, a2, bb2, c2 = popt2
        R_pred2 = sedov_sep(X_data, *popt2)
        ss_res2 = np.sum((R_arr - R_pred2)**2)
        r2_2 = 1.0 - ss_res2 / ss_tot if ss_tot > 0 else 0.0
        fit2 = {"beta": b2, "a_energy": a2, "b_time": bb2, "c_density": c2, "r2": r2_2}
        print(f"  Fit 2: a(E)={a2:.4f}, b(t)={bb2:.4f}, c(rho)={c2:.4f}, R2={r2_2:.4f}")
    except Exception as e:
        print(f"  Fit 2 FAILED: {e}")

    # Per-meteorite residuals
    print(f"\n  Per-meteorite residuals (Fit 1):")
    resid_by = defaultdict(list)
    for E, rho, t, R, name in fit_points:
        Rp = beta1 * (E * t**2 / rho) ** alpha1
        resid_by[name].append(R - Rp)
    for name, resids in resid_by.items():
        rmse = np.sqrt(np.mean(np.array(resids)**2))
        print(f"    {name:35s} n={len(resids):3d}  RMSE={rmse:8.1f}")

    # 4. Predict Godel
    print(f"\n{'='*60}")
    print(f"  PREDICTION GODEL (hold-out)")
    print(f"{'='*60}")

    E_g = godel["E"]
    rho_g = max(godel["baseline_edges"], 1)
    print(f"  E={E_g}, rho0={rho_g} (baseline edges), seeds={godel['seeds']}")

    predictions = []
    for t, R_obs in godel["r_series"]:
        if t > 0:
            x_g = E_g * t**2 / rho_g
            R_pred_f1 = beta1 * x_g ** alpha1

            R_pred_f2 = None
            if fit2:
                R_pred_f2 = fit2["beta"] * E_g**fit2["a_energy"] * t**fit2["b_time"] * rho_g**(-fit2["c_density"])

            predictions.append({
                "t_years": t,
                "R_observed": R_obs,
                "R_pred_f1": round(R_pred_f1, 2),
                "ratio_f1": round(R_obs / R_pred_f1, 4) if R_pred_f1 > 0 else None,
                "R_pred_f2": round(R_pred_f2, 2) if R_pred_f2 is not None else None,
                "ratio_f2": round(R_obs / R_pred_f2, 4) if R_pred_f2 and R_pred_f2 > 0 else None,
            })

    print(f"\n  {'t':>3s}  {'R_obs':>7s}  {'R_f1':>7s}  {'ratio1':>7s}  {'R_f2':>7s}  {'ratio2':>7s}")
    print(f"  {'-'*45}")
    for p in predictions:
        f2_str = f"{p['R_pred_f2']:7.1f}" if p['R_pred_f2'] else "     -"
        r2_str = f"{p['ratio_f2']:7.4f}" if p['ratio_f2'] else "     -"
        print(f"  {p['t_years']:3d}  {p['R_observed']:7d}  {p['R_pred_f1']:7.1f}  "
              f"{p['ratio_f1'] or 0:7.4f}  {f2_str}  {r2_str}")

    # Summary stats
    def calc_stats(key_pred, key_ratio):
        obs = np.array([p["R_observed"] for p in predictions if p[key_pred] is not None])
        pred = np.array([p[key_pred] for p in predictions if p[key_pred] is not None])
        ratios = np.array([p[key_ratio] for p in predictions if p[key_ratio] is not None])
        if len(obs) == 0:
            return {}
        ss_res = np.sum((obs - pred)**2)
        ss_tot = np.sum((obs - np.mean(obs))**2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return {
            "r2_holdout": round(float(r2), 4),
            "mean_ratio": round(float(np.mean(ratios)), 4),
            "median_ratio": round(float(np.median(ratios)), 4),
            "std_ratio": round(float(np.std(ratios)), 4),
            "rmse": round(float(np.sqrt(np.mean((obs - pred)**2))), 2),
            "n_points": len(obs),
        }

    stats1 = calc_stats("R_pred_f1", "ratio_f1")
    stats2 = calc_stats("R_pred_f2", "ratio_f2")

    print(f"\n  Fit 1 stats: R2={stats1.get('r2_holdout','?')}, "
          f"mean_ratio={stats1.get('mean_ratio','?')}, RMSE={stats1.get('rmse','?')}")
    if stats2:
        print(f"  Fit 2 stats: R2={stats2.get('r2_holdout','?')}, "
              f"mean_ratio={stats2.get('mean_ratio','?')}, RMSE={stats2.get('rmse','?')}")

    # 5. Verdict
    print(f"\n{'='*60}")
    print(f"  VERDICT")
    print(f"{'='*60}")

    best = stats2 if stats2 else stats1
    ratio = best.get("mean_ratio")
    r2_ho = best.get("r2_holdout")

    if ratio is not None and r2_ho is not None:
        if 0.5 <= ratio <= 2.0 and r2_ho > 0.5:
            verdict = "PASS — Godel predit correctement"
        elif 0.3 <= ratio <= 3.0 and r2_ho > 0.0:
            verdict = "PARTIAL — bon ordre de grandeur, fit imparfait"
        elif 0.3 <= ratio <= 3.0:
            verdict = "WEAK — ratio OK mais R2 negatif (forme de courbe incorrecte)"
        else:
            verdict = "FAIL — Godel hors prediction"
        print(f"  Best fit ratio = {ratio}")
        print(f"  Best fit R2 holdout = {r2_ho}")
        print(f"  -> {verdict}")
    else:
        verdict = "INCONCLUSIVE"
        print(f"  -> {verdict}")

    # 6. Save
    output = {
        "test": "godel_holdout_wt3",
        "date": "2026-04-02",
        "version": "v2_local_blast",
        "method": "Local blast radius from WT3 cooc table. R(t) = cumulative new edges around seed concepts after impact.",
        "rho0_def": "baseline_edges = number of cooc edges around seeds BEFORE impact year",
        "train_fit1": {
            "beta": round(float(beta1), 4),
            "alpha": round(float(alpha1), 4),
            "r2": round(float(r2_1), 4),
            "n_points": len(fit_points),
        },
        "train_fit2": {k: round(float(v), 4) if isinstance(v, float) else v for k, v in fit2.items()} if fit2 else None,
        "godel": {
            "E": E_g,
            "rho0_baseline_edges": rho_g,
            "seeds": godel["seeds"],
            "r_max_observed": godel["r_max"],
            "blast_detail": godel["blast"],
        },
        "prediction": predictions,
        "stats_fit1": stats1,
        "stats_fit2": stats2,
        "verdict": verdict,
        "all_meteorites": {
            name: {
                "E": m["E"],
                "rho0": m["baseline_edges"],
                "seeds": m["seeds"],
                "r_max": m["r_max"],
                "r_series": m["r_series"],
            }
            for name, m in train.items()
        },
    }

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Saved -> {OUTPUT_PATH}")

    db.close()


if __name__ == "__main__":
    run()
