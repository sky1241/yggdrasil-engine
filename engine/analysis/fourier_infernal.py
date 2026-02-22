#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIANE #1 — Fourier × Infernal Wheel
====================================
Applique l'analyse spectrale d'Ichimoku (Welch PSD) sur les données
d'addiction de drinks.csv pour trouver les cycles cachés.

Même algo que HSBC-algo-genetic/src/spectral/fourier_features.py
Domaine différent: BTC → alcool.

Usage:
    python engine/fourier_infernal.py
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np

# ── Welch PSD (copié d'Ichimoku, adapté) ──────────────────────────

def compute_welch_psd(data, fs=1.0, nperseg=None):
    """Welch PSD — même code que fourier_features.py d'Ichimoku."""
    try:
        from scipy.signal import welch
        n = len(data)
        if nperseg is None:
            nperseg = min(1024, max(8, n // 4))
        freqs, psd = welch(data, fs=fs, nperseg=nperseg)
        return freqs, psd
    except ImportError:
        n = len(data)
        if n <= 1:
            return np.array([0.0]), np.array([0.0])
        window = np.hanning(n)
        data_centered = data - np.nanmean(data)
        fft = np.fft.rfft(window * data_centered)
        psd = (np.abs(fft) ** 2) / (np.sum(window ** 2) * fs)
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)
        return freqs, psd


# ── Chargement données ────────────────────────────────────────────

def load_drinks(path):
    """Charge drinks.csv → série temporelle journalière."""
    daily = defaultdict(int)
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            day = row["InfernalDay"]
            total = int(row.get("Wine", 0)) + int(row.get("Beer", 0)) + int(row.get("Strong", 0))
            daily[day] += total

    if not daily:
        return [], []

    # Remplir les trous (jours sans données = 0 drinks)
    days_sorted = sorted(daily.keys())
    start = datetime.strptime(days_sorted[0], "%Y-%m-%d")
    end = datetime.strptime(days_sorted[-1], "%Y-%m-%d")

    dates = []
    values = []
    d = start
    while d <= end:
        key = d.strftime("%Y-%m-%d")
        dates.append(key)
        values.append(daily.get(key, 0))
        d += timedelta(days=1)

    return dates, values


# ── Analyse spectrale ─────────────────────────────────────────────

def analyse_cycles(values, fs=1.0):
    """Trouve les cycles dominants dans le signal."""
    data = np.array(values, dtype=float)
    if len(data) < 8:
        return {"error": "Pas assez de données (min 8 jours)"}

    # Centrer le signal
    data_centered = data - np.mean(data)

    # Welch PSD
    freqs, psd = compute_welch_psd(data_centered, fs=fs)

    # Ignorer DC (index 0)
    if len(freqs) <= 1:
        return {"error": "Signal trop court pour FFT"}

    freqs_no_dc = freqs[1:]
    psd_no_dc = psd[1:]

    # Top 5 pics
    n_peaks = min(5, len(psd_no_dc))
    top_idx = np.argsort(psd_no_dc)[::-1][:n_peaks]

    peaks = []
    for idx in top_idx:
        freq = freqs_no_dc[idx]
        period = 1.0 / freq if freq > 0 else float("inf")
        power = psd_no_dc[idx]
        total_power = np.sum(psd_no_dc)
        pct = 100.0 * power / total_power if total_power > 0 else 0

        label = ""
        if 6.5 <= period <= 7.5:
            label = "CYCLE HEBDOMADAIRE"
        elif 13.5 <= period <= 14.5:
            label = "CYCLE BI-HEBDO"
        elif 3.0 <= period <= 4.0:
            label = "CYCLE ~3-4 JOURS"
        elif 27 <= period <= 31:
            label = "CYCLE MENSUEL"
        elif 2.0 <= period <= 2.5:
            label = "CYCLE ~2 JOURS"

        peaks.append({
            "rank": len(peaks) + 1,
            "period_days": round(period, 2),
            "frequency": round(freq, 4),
            "power_pct": round(pct, 1),
            "label": label,
        })

    # Spectral flatness (0=peaky=cyclique, 1=flat=bruit blanc)
    positives = psd_no_dc[psd_no_dc > 0]
    if len(positives) > 0:
        gmean = float(np.exp(np.mean(np.log(positives))))
        amean = float(np.mean(positives))
        flatness = gmean / amean if amean > 0 else 0
    else:
        flatness = 0

    # LFP — ratio basses fréquences (cycles > 5 jours)
    f0 = 1.0 / 5.0  # 0.2 cycles/jour
    mask_low = freqs_no_dc < f0
    total_power = float(np.sum(psd_no_dc))
    lfp = float(np.sum(psd_no_dc[mask_low])) / total_power if total_power > 0 else 0

    # Régime (même seuils qu'Ichimoku)
    if lfp >= 0.6:
        regime = "TREND"  # cycles longs dominent → pattern stable
    elif lfp <= 0.3 or flatness >= 0.7:
        regime = "NOISE"  # pas de pattern clair → bruit
    else:
        regime = "MIXED"  # entre les deux

    return {
        "n_days": len(values),
        "mean_drinks_per_day": round(np.mean(data), 1),
        "std_drinks_per_day": round(np.std(data), 1),
        "max_day": int(np.max(data)),
        "min_day": int(np.min(data)),
        "dry_days": int(np.sum(data == 0)),
        "peaks": peaks,
        "spectral_flatness": round(flatness, 3),
        "lfp_ratio": round(lfp, 3),
        "regime": regime,
    }


# ── Prédiction jours à risque ─────────────────────────────────────

def predict_risk_days(dates, values, top_period, n_future=7):
    """Si un cycle dominant existe, prédit les prochains jours à risque."""
    if top_period is None or top_period < 2:
        return []

    data = np.array(values, dtype=float)
    n = len(data)
    period = int(round(top_period))

    # Moyenne par phase du cycle
    phase_avg = np.zeros(period)
    phase_count = np.zeros(period)
    for i in range(n):
        phase = i % period
        phase_avg[phase] += data[i]
        phase_count[phase] += 1
    phase_avg = np.where(phase_count > 0, phase_avg / phase_count, 0)

    # Trouver la phase la plus dangereuse
    peak_phase = int(np.argmax(phase_avg))

    # Prédire les prochains jours
    last_date = datetime.strptime(dates[-1], "%Y-%m-%d")
    predictions = []
    for day_offset in range(1, n_future + 1):
        future_date = last_date + timedelta(days=day_offset)
        future_phase = (n + day_offset) % period
        risk = phase_avg[future_phase] / max(phase_avg) if max(phase_avg) > 0 else 0
        predictions.append({
            "date": future_date.strftime("%Y-%m-%d"),
            "phase": future_phase,
            "risk_score": round(risk, 2),
            "predicted_drinks": round(phase_avg[future_phase], 1),
            "warning": bool(risk > 0.8),
        })

    return predictions


# ── Main ──────────────────────────────────────────────────────────

def main():
    # Chercher drinks.csv
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", ".infernal_wheel", "drinks.csv"),
        os.path.expanduser("~/.infernal_wheel/drinks.csv"),
        r"c:\Users\ludov\.infernal_wheel\drinks.csv",
    ]

    drinks_path = None
    for p in paths:
        if os.path.exists(p):
            drinks_path = p
            break

    if not drinks_path:
        print("ERREUR: drinks.csv introuvable")
        sys.exit(1)

    print(f"=== LIANE #1: FOURIER x INFERNAL WHEEL ===")
    print(f"Source: {drinks_path}")
    print(f"Algo: Welch PSD (identique à Ichimoku BTC)")
    print(f"Domaine: addiction (pas crypto)")
    print()

    # Charger
    dates, values = load_drinks(drinks_path)
    print(f"Période: {dates[0]} → {dates[-1]} ({len(dates)} jours)")
    print()

    # Analyser
    result = analyse_cycles(values, fs=1.0)  # 1 sample/jour

    if "error" in result:
        print(f"ERREUR: {result['error']}")
        sys.exit(1)

    # Afficher stats
    print(f"--- STATS ---")
    print(f"Moyenne:        {result['mean_drinks_per_day']} drinks/jour")
    print(f"Ecart-type:     {result['std_drinks_per_day']}")
    print(f"Max:            {result['max_day']} drinks (en 1 jour)")
    print(f"Min:            {result['min_day']} drinks")
    print(f"Jours sobres:   {result['dry_days']} / {result['n_days']} ({100*result['dry_days']//result['n_days']}%)")
    print()

    # Régime spectral
    print(f"--- REGIME SPECTRAL ---")
    print(f"Flatness:       {result['spectral_flatness']} (0=cyclique, 1=bruit)")
    print(f"LFP ratio:      {result['lfp_ratio']} (>0.6=trend, <0.3=bruit)")
    print(f"Regime:         {result['regime']}")
    print()

    # Cycles détectés
    print(f"--- CYCLES DETECTES (top 5) ---")
    for peak in result["peaks"]:
        label = f"  *** {peak['label']} ***" if peak["label"] else ""
        print(f"  #{peak['rank']}: période = {peak['period_days']} jours "
              f"({peak['power_pct']}% du signal){label}")
    print()

    # Prédictions
    top_period = result["peaks"][0]["period_days"] if result["peaks"] else None
    predictions = predict_risk_days(dates, values, top_period, n_future=7)

    if predictions:
        print(f"--- PREDICTION 7 PROCHAINS JOURS ---")
        print(f"(basé sur cycle dominant de {top_period} jours)")
        for pred in predictions:
            warning = " ⚠ JOUR A RISQUE" if pred["warning"] else ""
            print(f"  {pred['date']}: risque={pred['risk_score']} "
                  f"(~{pred['predicted_drinks']} drinks){warning}")
        print()

    # Export JSON
    output = {
        "source": "LIANE_FOURIER_x_INFERNAL",
        "algo": "Welch PSD (from Ichimoku spectral engine)",
        "generated": datetime.now().isoformat(),
        "stats": {k: v for k, v in result.items() if k != "peaks"},
        "cycles": result["peaks"],
        "predictions": predictions,
        "daily_series": {d: v for d, v in zip(dates, values)},
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lianes", "liane_fourier_infernal.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Export: {out_path}")


if __name__ == "__main__":
    main()
