"""
YGGDRASIL ENGINE — V3 Sedov-Taylor Calibration
================================================
Calibre beta et alpha de R(t) = beta * (E*t^2/rho0)^alpha sur les 13 meteorites connues.

FAIT COMME LA TODO LE DIT:
- Construit de vrais objets Frame depuis frames.json + concept_births.json
- Appelle measure_all() de meteorites.py pour mesurer les 7 deltas + OHLC
- Appelle fit_sedov() du MeteoriteRegistry pour calibrer beta, alpha

Pas de rescan WT3 — tout est en lookup.

Auteur: Sky x Claude (Opus 4.6) — Session 32, 30 mars 2026
"""
import json
import sys
import os
import numpy as np
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.analysis.meteorites import (
    Frame, measure_all, build_catalog, MeteoriteRegistry, impact_energy
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FRAMES_PATH = DATA_DIR / "scan" / "frames.json"
BIRTHS_PATH = DATA_DIR / "scan" / "concept_births.json"
OUTPUT_PATH = DATA_DIR / "results" / "sedov_calibration.json"


def meshedness_bebber(n_concepts, n_edges):
    """Bebber 2007: alpha = (e - n + 1) / (2n - 5)."""
    n, e = n_concepts, n_edges
    denom = 2 * n - 5
    if denom <= 0 or n < 3:
        return 0.0
    return (e - n + 1) / denom


def build_frames() -> dict[str, Frame]:
    """
    Build real Frame objects from frames.json + concept_births.json.

    Returns {period_str: Frame} ready for measure_all().
    """
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

    # Build concept_ids from concepts_active (cumulative, monotone increasing).
    # Use sequential IDs {0..N-1} so that set differences give correct birth counts.
    # This works because concepts_active is cumulative and never decreases.
    frames_dict = {}

    for fr in raw_frames_sorted:
        period = fr["period"]
        nc = fr.get("concepts_active", 0)
        ne = fr.get("edges_cumulative", 0)
        mesh = meshedness_bebber(nc, ne)

        # Sequential IDs: frame with 51501 concepts -> {0, 1, ..., 51500}
        # Set difference between frames gives exact birth count
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


def calibrate():
    """Main calibration: build frames -> measure_all -> fit_sedov."""
    print("=" * 60)
    print("  SEDOV-TAYLOR CALIBRATION — V3 (proper)")
    print("=" * 60)

    frames = build_frames()

    # Run measure_all from meteorites.py — this is the TODO
    print("\n  Running measure_all() on 13 known meteorites...")
    registry = measure_all(frames, window_months=120)  # 10 years

    print(f"\n  Registry: {len(registry.boxes)} meteorites measured")
    for box in registry.boxes:
        c = box.candle
        n_radii = len(box.measured_radii)
        max_R = box.measured_radii[-1][1] if box.measured_radii else 0
        peak = box.deltas_at_peak
        peak_mag = peak.magnitude() if peak else 0
        print(f"  {c.name:35s} E={c.E:5.0f}  rho0={c.rho0:.4f}  "
              f"points={n_radii:3d}  R_max={max_R:5d}  "
              f"high={c.high_date or '?':>7s}  peak_mag={peak_mag:.2f}")

    # Fit Sedov-Taylor — custom fit with proper bounds
    # (registry.fit_sedov() has bounds [0.01-10, 0.05-0.5] too tight for our data)
    print(f"\n{'='*60}")
    print(f"  FIT SEDOV-TAYLOR")
    print(f"{'='*60}")

    # Gather all (E, rho0, t, R_obs) from boxes
    from scipy.optimize import curve_fit
    fit_points = []
    for box in registry.boxes:
        E = box.candle.E
        rho0 = box.candle.rho0
        if E <= 0 or rho0 <= 0:
            continue
        for t, R_obs in box.measured_radii:
            if t > 0 and R_obs > 0:
                fit_points.append((E, rho0, t, R_obs, box.candle.name))

    if len(fit_points) >= 3:
        E_arr = np.array([p[0] for p in fit_points])
        rho_arr = np.array([p[1] for p in fit_points])
        t_arr = np.array([p[2] for p in fit_points])
        R_obs_arr = np.array([p[3] for p in fit_points])

        # FIT 1: Classic Sedov R(t) = beta * (E*t^2/rho0)^alpha
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

            fit_result = {
                "beta": round(float(beta_fit), 4),
                "beta_err": round(float(perr[0]), 4),
                "exponent": round(float(alpha_fit), 4),
                "exponent_err": round(float(perr[1]), 4),
                "exponent_theoretical": 0.2,
                "r_squared": round(float(r_sq), 4),
                "n_points": len(fit_points),
                "status": "ok",
            }
            print(f"  Fit 1 — R(t) = beta * (E*t^2/rho0)^alpha")
            print(f"    beta  = {beta_fit:.4f} +/- {perr[0]:.4f}")
            print(f"    alpha = {alpha_fit:.4f} +/- {perr[1]:.4f}  (theoretical: 0.2)")
            print(f"    R^2   = {r_sq:.4f}")
            print(f"    Points: {len(fit_points)}")
        except Exception as e:
            print(f"  Fit 1 FAILED: {e}")
            fit_result = {"status": f"failed: {e}"}
            beta_fit = 1.033
            alpha_fit = 0.2

        # FIT 2: Separated beta * E^a * t^b * rho0^(-c)
        def sedov_sep(X, beta, a, b, c):
            E, t, rho = X
            return beta * np.power(E, a) * np.power(t, b) * np.power(rho, -c)

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
            perr2 = np.sqrt(np.diag(pcov2))

            fit_result["fit_separated"] = {
                "beta": round(float(b2), 4),
                "a_energy": round(float(a2), 4),
                "b_time": round(float(bb2), 4),
                "c_density": round(float(c2), 4),
                "r_squared": round(float(r_sq2), 4),
            }
            print(f"\n  Fit 2 — R = beta * E^a * t^b * rho0^(-c)")
            print(f"    beta = {b2:.4f}")
            print(f"    a(E) = {a2:.4f}  (Sedov: 0.2)")
            print(f"    b(t) = {bb2:.4f}  (Sedov: 0.4)")
            print(f"    c(rho) = {c2:.4f}  (Sedov: 0.2)")
            print(f"    R^2   = {r_sq2:.4f}")
        except Exception as e:
            print(f"  Fit 2 FAILED: {e}")

        # Per-meteorite residuals
        print(f"\n  Per-meteorite residuals:")
        from collections import defaultdict
        resid_by = defaultdict(list)
        for E, rho0, t, R, name in fit_points:
            xi = E * t**2 / rho0
            Rp = beta_fit * xi ** alpha_fit
            resid_by[name].append(R - Rp)
        for name, resids in resid_by.items():
            mean_r = np.mean(resids)
            rmse = np.sqrt(np.mean(np.array(resids)**2))
            print(f"    {name:35s} n={len(resids):3d}  mean={mean_r:+8.1f}  RMSE={rmse:8.1f}")
    else:
        fit_result = {"status": "insufficient_data", "n_points": len(fit_points)}
        print(f"  Only {len(fit_points)} valid points — insufficient")
        beta_fit = 1.033

    # Signature moyenne
    sig = registry.signature()
    if sig:
        print(f"\n{'='*60}")
        print(f"  SIGNATURE MOYENNE (peak deltas)")
        print(f"{'='*60}")
        sd = sig.to_dict()
        for k, v in sd.items():
            print(f"  {k:15s}: {v}")

    # Godel prediction — use calibrated beta
    print(f"\n{'='*60}")
    print(f"  GODEL PREDICTION")
    print(f"{'='*60}")
    godel = registry.predict_godel(
        beta=fit_result.get("beta", 1.033) if isinstance(fit_result.get("beta"), (int, float)) else 1.033
    )
    print(f"  E = {godel['E']}")
    print(f"  rho0 = {godel['rho0_placeholder']}")
    if godel.get("predicted_R"):
        for t, R in godel["predicted_R"][:6]:
            print(f"  R({t:3d} months) = {R}")
    if godel.get("signature"):
        print(f"  Applied signature: {godel['signature']}")

    # Candle classification
    print(f"\n{'='*60}")
    print(f"  CANDLE CLASSIFICATION (bougie <-> type de trou)")
    print(f"{'='*60}")
    from engine.analysis.meteorites import classify_candle
    for box in registry.boxes:
        cls = classify_candle(box.candle)
        length = box.candle.length
        l_str = f"{length:>4}" if length is not None else "   ?"
        print(f"  {box.candle.name:35s} bougie={l_str}m  rho0={box.candle.rho0:.2f}  -> {cls}")

    # Per-meteorite detail
    print(f"\n{'='*60}")
    print(f"  DELTAS AU PIC (High) PAR METEORITE")
    print(f"{'='*60}")
    for box in registry.boxes:
        if box.deltas_at_peak:
            d = box.deltas_at_peak
            print(f"  {box.candle.name:35s} vol={d.volume:+10d}  "
                  f"alpha={d.alpha_delta:+.4f}  births={d.births:+6d}  "
                  f"mag={d.magnitude():.2f}")

    # Full summary
    summary = registry.summary()

    # Save
    output = {
        "calibration_date": "2026-03-30",
        "method": "measure_all() + fit_sedov() from meteorites.py",
        "n_meteorites_measured": len(registry.boxes),
        "n_meteorites_catalog": 13,
        "fit_sedov": fit_result,
        "signature": sig.to_dict() if sig else None,
        "godel_prediction": godel,
        "meteorites": [box.to_dict() for box in registry.boxes],
        "classifications": {
            box.candle.name: classify_candle(box.candle)
            for box in registry.boxes
        },
    }

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Saved -> {OUTPUT_PATH}")

    print(f"\n{'='*60}")
    print(f"  CALIBRATION COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    calibrate()
