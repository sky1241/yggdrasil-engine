"""
YGGDRASIL ENGINE — Gödel Hold-Out Test
========================================
Train Sedov-Taylor sur 12 météorites, prédire Gödel seul.

Le VRAI hold-out: Gödel est EXCLU du fit.
On compare R(t) prédit vs R(t) observé.

Auteur: Sky × Claude (Opus 4.6) — Session 33, 2 avril 2026
"""
import json
import sys
import os
import numpy as np
from pathlib import Path
from scipy.optimize import curve_fit
from collections import defaultdict

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.analysis.meteorites import (
    Frame, measure_all, build_catalog, MeteoriteRegistry,
    impact_energy, measure_impact, classify_candle,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
FRAMES_PATH = DATA_DIR / "scan" / "frames.json"
OUTPUT_PATH = DATA_DIR / "results" / "godel_holdout.json"

GODEL_NAME = "Gödel 1931"


def meshedness_bebber(n_concepts, n_edges):
    """Bebber 2007: alpha = (e - n + 1) / (2n - 5)."""
    n, e = n_concepts, n_edges
    denom = 2 * n - 5
    if denom <= 0 or n < 3:
        return 0.0
    return (e - n + 1) / denom


def build_frames() -> dict[str, Frame]:
    """Build Frame objects from frames.json."""
    print("  Loading frames.json...")
    with open(FRAMES_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    raw_frames = raw["frames"]

    def period_sort_key(fr):
        p = fr["period"]
        if p.startswith("-"):
            return (int(p), 6)
        parts = p.split("-")
        yr = int(parts[0])
        mo = int(parts[1]) if len(parts) > 1 else 6
        return (yr, mo)

    raw_frames_sorted = sorted(raw_frames, key=period_sort_key)
    frames_dict = {}

    for fr in raw_frames_sorted:
        period = fr["period"]
        nc = fr.get("concepts_active", 0)
        ne = fr.get("edges_cumulative", 0)
        mesh = meshedness_bebber(nc, ne)

        frame = Frame(
            period=period,
            n_concepts=nc,
            n_edges=ne,
            meshedness=mesh,
            concept_ids=set(range(nc)),
        )
        frames_dict[period] = frame

    print(f"  Built {len(frames_dict)} Frame objects")
    return frames_dict


def fit_on_boxes(boxes, label=""):
    """
    Fit Sedov-Taylor on a list of MeteoriteBox.
    Returns (fit_result_dict, beta, alpha) or None on failure.
    """
    fit_points = []
    for box in boxes:
        E = box.candle.E
        rho0 = box.candle.rho0
        if E <= 0 or rho0 <= 0:
            continue
        for t, R_obs in box.measured_radii:
            if t > 0 and R_obs > 0:
                fit_points.append((E, rho0, t, R_obs, box.candle.name))

    if len(fit_points) < 3:
        print(f"  {label}: only {len(fit_points)} points — skip")
        return None

    E_arr = np.array([p[0] for p in fit_points])
    rho_arr = np.array([p[1] for p in fit_points])
    t_arr = np.array([p[2] for p in fit_points])
    R_obs_arr = np.array([p[3] for p in fit_points])

    # Fit 1: Classic R(t) = beta * (E*t^2/rho0)^alpha
    x = E_arr * t_arr**2 / rho_arr

    def sedov_model(x, beta, alpha):
        return beta * np.power(x, alpha)

    try:
        popt, pcov = curve_fit(
            sedov_model, x, R_obs_arr,
            p0=[100.0, 0.3],
            bounds=([0.001, 0.01], [100000.0, 2.0]),
            maxfev=10000,
        )
        beta_fit, alpha_fit = popt
        R_pred = sedov_model(x, *popt)
        ss_res = np.sum((R_obs_arr - R_pred)**2)
        ss_tot = np.sum((R_obs_arr - np.mean(R_obs_arr))**2)
        r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        perr = np.sqrt(np.diag(pcov))
    except Exception as e:
        print(f"  {label} Fit 1 FAILED: {e}")
        return None

    # Fit 2: Separated R = beta * E^a * t^b * rho0^(-c)
    def sedov_sep(X, beta, a, b, c):
        E, t, rho = X
        return beta * np.power(E, a) * np.power(t, b) * np.power(rho, -c)

    fit2 = None
    try:
        X_data = (E_arr, t_arr, rho_arr)
        popt2, pcov2 = curve_fit(
            sedov_sep, X_data, R_obs_arr,
            p0=[100.0, 0.2, 0.4, 0.2],
            bounds=([0.001, 0.01, 0.01, 0.01], [100000.0, 2.0, 3.0, 2.0]),
            maxfev=10000,
        )
        b2, a2, bb2, c2 = popt2
        R_pred2 = sedov_sep(X_data, *popt2)
        ss_res2 = np.sum((R_obs_arr - R_pred2)**2)
        r_sq2 = 1.0 - ss_res2 / ss_tot if ss_tot > 0 else 0.0
        fit2 = {
            "beta": round(float(b2), 4),
            "a_energy": round(float(a2), 4),
            "b_time": round(float(bb2), 4),
            "c_density": round(float(c2), 4),
            "r_squared": round(float(r_sq2), 4),
        }
    except Exception as e:
        print(f"  {label} Fit 2 FAILED: {e}")

    result = {
        "beta": round(float(beta_fit), 4),
        "beta_err": round(float(perr[0]), 4),
        "alpha": round(float(alpha_fit), 4),
        "alpha_err": round(float(perr[1]), 4),
        "r_squared": round(float(r_sq), 4),
        "n_points": len(fit_points),
        "n_meteorites": len(boxes),
        "fit_separated": fit2,
    }

    print(f"  {label}:")
    print(f"    Fit 1: beta={beta_fit:.2f}, alpha={alpha_fit:.4f}, R²={r_sq:.4f}  ({len(fit_points)} pts, {len(boxes)} meteorites)")
    if fit2:
        print(f"    Fit 2: a(E)={fit2['a_energy']:.4f}, b(t)={fit2['b_time']:.4f}, c(rho)={fit2['c_density']:.4f}, R2={fit2['r_squared']:.4f}")

    return result, beta_fit, alpha_fit, (fit2 or {})


def predict_godel_from_fit(godel_box, beta, alpha, fit2):
    """
    Predict Gödel's R(t) using the trained parameters.
    Compare with observed R(t).
    """
    E = godel_box.candle.E
    rho0 = godel_box.candle.rho0

    observed = godel_box.measured_radii  # [(t, R_obs), ...]
    if not observed:
        return {"error": "no observed data for Gödel"}

    # Predict with Fit 1: R = beta * (E*t^2/rho0)^alpha
    predictions_f1 = []
    for t, R_obs in observed:
        if t > 0:
            x = E * t**2 / rho0
            R_pred = beta * x ** alpha
            predictions_f1.append({
                "t_months": t,
                "R_observed": R_obs,
                "R_predicted": round(R_pred, 2),
                "error": round(R_obs - R_pred, 2),
                "ratio": round(R_obs / R_pred, 4) if R_pred > 0 else None,
            })

    # Predict with Fit 2 if available
    predictions_f2 = []
    if fit2 and all(k in fit2 for k in ("beta", "a_energy", "b_time", "c_density")):
        for t, R_obs in observed:
            if t > 0:
                R_pred = fit2["beta"] * E**fit2["a_energy"] * t**fit2["b_time"] * rho0**(-fit2["c_density"])
                predictions_f2.append({
                    "t_months": t,
                    "R_observed": R_obs,
                    "R_predicted": round(R_pred, 2),
                    "error": round(R_obs - R_pred, 2),
                    "ratio": round(R_obs / R_pred, 4) if R_pred > 0 else None,
                })

    # Summary stats
    def summary_stats(preds):
        if not preds:
            return {}
        ratios = [p["ratio"] for p in preds if p["ratio"] is not None]
        errors = [p["error"] for p in preds]
        R_obs_arr = np.array([p["R_observed"] for p in preds])
        R_pred_arr = np.array([p["R_predicted"] for p in preds])
        ss_res = np.sum((R_obs_arr - R_pred_arr)**2)
        ss_tot = np.sum((R_obs_arr - np.mean(R_obs_arr))**2)
        r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return {
            "mean_ratio": round(float(np.mean(ratios)), 4) if ratios else None,
            "median_ratio": round(float(np.median(ratios)), 4) if ratios else None,
            "std_ratio": round(float(np.std(ratios)), 4) if ratios else None,
            "rmse": round(float(np.sqrt(np.mean(np.array(errors)**2))), 2),
            "mae": round(float(np.mean(np.abs(errors))), 2),
            "r_squared_holdout": round(float(r_sq), 4),
            "n_points": len(preds),
        }

    stats_f1 = summary_stats(predictions_f1)
    stats_f2 = summary_stats(predictions_f2)

    return {
        "name": GODEL_NAME,
        "E": E,
        "rho0": rho0,
        "n_observed_points": len(observed),
        "R_max_observed": max(R for _, R in observed) if observed else 0,
        "fit1_classic": {
            "stats": stats_f1,
            "sample_points": predictions_f1[:12] + predictions_f1[-3:] if len(predictions_f1) > 15 else predictions_f1,
        },
        "fit2_separated": {
            "stats": stats_f2,
            "sample_points": predictions_f2[:12] + predictions_f2[-3:] if len(predictions_f2) > 15 else predictions_f2,
        },
    }


def run():
    print("=" * 60)
    print("  GÖDEL HOLD-OUT TEST")
    print("  Train: 12 météorites  |  Test: Gödel 1931")
    print("=" * 60)

    # 1. Build frames
    frames = build_frames()

    # 2. Measure ALL 13
    print("\n  Measuring all 13 meteorites...")
    registry = measure_all(frames, window_months=120)

    # 3. Split: Gödel out
    godel_box = None
    train_boxes = []
    for box in registry.boxes:
        if box.candle.name == GODEL_NAME:
            godel_box = box
        else:
            train_boxes.append(box)

    if godel_box is None:
        print("  ERROR: Gödel not found in registry (no measured data?)")
        return
    if not godel_box.measured_radii:
        print("  ERROR: Gödel has 0 measured points")
        return

    print(f"\n  Gödel found: E={godel_box.candle.E}, rho0={godel_box.candle.rho0:.6f}, "
          f"{len(godel_box.measured_radii)} observed points, "
          f"R_max={max(R for _, R in godel_box.measured_radii)}")
    print(f"  Train set: {len(train_boxes)} meteorites")

    # 4. Fit on 12 (SANS Gödel)
    print(f"\n{'='*60}")
    print(f"  FIT TRAIN (12 météorites, Gödel EXCLU)")
    print(f"{'='*60}")
    train_result = fit_on_boxes(train_boxes, label="TRAIN (12)")

    if train_result is None:
        print("  FATAL: fit failed on 12 meteorites")
        return

    train_fit, beta_train, alpha_train, fit2_train = train_result

    # 5. Fit on 13 (avec Gödel, pour comparaison)
    print(f"\n{'='*60}")
    print(f"  FIT ALL (13 météorites, référence)")
    print(f"{'='*60}")
    all_result = fit_on_boxes(registry.boxes, label="ALL (13)")
    if all_result:
        all_fit, beta_all, alpha_all, fit2_all = all_result
    else:
        all_fit = None

    # 6. Predict Gödel
    print(f"\n{'='*60}")
    print(f"  PRÉDICTION GÖDEL (hold-out)")
    print(f"{'='*60}")
    godel_pred = predict_godel_from_fit(godel_box, beta_train, alpha_train, fit2_train)

    s1 = godel_pred["fit1_classic"]["stats"]
    s2 = godel_pred["fit2_separated"]["stats"]

    print(f"  Fit 1 (classic):")
    print(f"    R² hold-out = {s1.get('r_squared_holdout', '?')}")
    print(f"    Mean ratio obs/pred = {s1.get('mean_ratio', '?')}")
    print(f"    RMSE = {s1.get('rmse', '?')}")
    if s2:
        print(f"  Fit 2 (separated):")
        print(f"    R² hold-out = {s2.get('r_squared_holdout', '?')}")
        print(f"    Mean ratio obs/pred = {s2.get('mean_ratio', '?')}")
        print(f"    RMSE = {s2.get('rmse', '?')}")

    # 7. Verdict
    print(f"\n{'='*60}")
    print(f"  VERDICT")
    print(f"{'='*60}")
    ratio = s2.get("mean_ratio") if s2 else s1.get("mean_ratio")
    r2_ho = s2.get("r_squared_holdout") if s2 else s1.get("r_squared_holdout")

    if ratio is not None and r2_ho is not None:
        if 0.5 <= ratio <= 2.0 and r2_ho > 0.5:
            verdict = "PASS — Gödel prédit correctement (ratio et R² acceptables)"
        elif 0.3 <= ratio <= 3.0 and r2_ho > 0.0:
            verdict = "PARTIAL — Gödel dans le bon ordre de grandeur mais fit imparfait"
        else:
            verdict = "FAIL — Gödel hors prédiction"
        print(f"  Ratio obs/pred = {ratio}")
        print(f"  R² hold-out = {r2_ho}")
        print(f"  → {verdict}")
    else:
        verdict = "INCONCLUSIVE — pas assez de données"
        print(f"  → {verdict}")

    # 8. Save
    output = {
        "test": "godel_holdout",
        "date": "2026-04-02",
        "method": "Train Sedov on 12 meteorites, predict Gödel blind",
        "train": train_fit,
        "all_13_reference": all_fit if all_fit else None,
        "godel": {
            "E": godel_box.candle.E,
            "rho0": godel_box.candle.rho0,
            "strate": godel_box.candle.strate,
            "continents": godel_box.candle.continents_touched,
            "n_observed": len(godel_box.measured_radii),
            "R_max_observed": max(R for _, R in godel_box.measured_radii),
            "classification": classify_candle(godel_box.candle),
        },
        "prediction": godel_pred,
        "verdict": verdict,
    }

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Saved → {OUTPUT_PATH}")


if __name__ == "__main__":
    run()
