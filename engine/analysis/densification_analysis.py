"""
YGGDRASIL — Analyse de densification & saturation scientifique
================================================================
833K papers, 2000-2012, 155 mois de données propres.
Sedov-Taylor + Arbesman + autocatalyse.
"""
import json, math
import numpy as np
from scipy.optimize import curve_fit

def main():
    with open("data/results/monthly_frames.json") as f:
        results = json.load(f)

    months = np.array(range(len(results)), dtype=float)
    concepts = np.array([r["cum_concepts"] for r in results], dtype=float)
    new_concepts = np.array([r["new_concepts"] for r in results], dtype=float)
    monthly_papers = np.array([r["papers"] for r in results], dtype=float)
    rho_g = np.array([r["rho_g"] for r in results], dtype=float)
    efficiency = new_concepts / monthly_papers * 1000

    output = {}

    print("=" * 70)
    print("  ANALYSE COMPLETE - DENSIFICATION & SATURATION")
    print("  833K papers, 2000-2012, 155 mois")
    print("=" * 70)

    # === 1. RENDEMENT ===
    print("\n--- 1. RENDEMENT: nouveaux concepts / 1000 papers ---")
    for i, r in enumerate(results):
        if r["period"].endswith("-06"):
            yr = r["period"][:4]
            window = efficiency[max(0, i - 3):i + 3]
            avg_eff = np.mean(window)
            bar = "#" * int(avg_eff)
            print(f"  {yr}: {avg_eff:>6.1f} concepts/1K papers  {bar}")

    e_start = np.mean(efficiency[:6])
    e_end = np.mean(efficiency[-6:])
    drop = (1 - e_end / e_start) * 100
    print(f"  Chute: {e_end/e_start:.2f}x ({drop:.0f}% de perte)")
    output["efficiency_drop_pct"] = round(drop, 1)

    # === 2. SEDOV FIT ===
    print("\n--- 2. SEDOV-TAYLOR FIT ---")
    mask = months > 12

    def power_decay(t, A, alpha):
        return A * np.power(t, -alpha)

    popt, _ = curve_fit(power_decay, months[mask], new_concepts[mask],
                        p0=[5000, 0.6], bounds=([100, 0.1], [100000, 2.0]))
    A_fit, alpha_fit = popt
    pred = power_decay(months[mask], *popt)
    ss_res = np.sum((new_concepts[mask] - pred) ** 2)
    ss_tot = np.sum((new_concepts[mask] - np.mean(new_concepts[mask])) ** 2)
    r2 = 1 - ss_res / ss_tot
    print(f"  dx/dt = {A_fit:.0f} * t^(-{alpha_fit:.3f})")
    print(f"  R2 = {r2:.4f}")
    print(f"  Sedov theorique: alpha = 0.600")
    print(f"  Mesure:           alpha = {alpha_fit:.3f}")
    output["sedov_alpha"] = round(alpha_fit, 3)
    output["sedov_r2"] = round(r2, 4)

    # === 3. RHO LOGISTIC ===
    print("\n--- 3. DENSIFICATION rho(t) ---")

    def logistic(t, L, k, t0):
        return L / (1 + np.exp(-k * (t - t0)))

    popt_rho, _ = curve_fit(logistic, months, rho_g, p0=[1.0, 0.1, 30], maxfev=10000)
    L, k, t0 = popt_rho
    r2_rho = 1 - np.sum((rho_g - logistic(months, *popt_rho)) ** 2) / np.sum((rho_g - np.mean(rho_g)) ** 2)
    inflection_year = 2000 + t0 / 12
    sat_year = 2000 + (t0 + 4.6 / k) / 12
    print(f"  rho(t) = {L:.4f} / (1 + exp(-{k:.4f}*(t-{t0:.1f})))")
    print(f"  R2 = {r2_rho:.4f}")
    print(f"  Plafond: {L:.4f}")
    print(f"  Inflexion: {inflection_year:.1f}")
    print(f"  Saturation 99%: {sat_year:.1f}")
    output["rho_plafond"] = round(L, 4)
    output["rho_inflection_year"] = round(inflection_year, 1)
    output["rho_saturation_year"] = round(sat_year, 1)

    # === 4. TABLEAU ANNUEL ===
    print("\n--- 4. TABLEAU COMPLET ---")
    header = f"  {'An':>4} | {'Papers':>7} | {'CumCon':>7} | {'Nvx':>5} | {'Eff':>5} | {'rho':>5} | Verdict"
    print(header)
    print("  " + "-" * 60)

    yearly = {}
    for r in results:
        yr = r["period"][:4]
        if yr not in yearly:
            yearly[yr] = {"papers": 0, "new": 0}
        yearly[yr]["papers"] += r["papers"]
        yearly[yr]["new"] += r["new_concepts"]
        yearly[yr]["cum"] = r["cum_concepts"]
        yearly[yr]["rho"] = r["rho_g"]

    for yr in sorted(yearly.keys()):
        d = yearly[yr]
        eff = d["new"] / d["papers"] * 1000
        if eff > 40:
            v = "FERTILE"
        elif eff > 10:
            v = "normal"
        elif eff > 3:
            v = "sterile"
        else:
            v = "MORT"
        print(f"  {yr:>4} | {d['papers']:>7,} | {d['cum']:>7,} | {d['new']:>5,} | {eff:>5.1f} | {d['rho']:>5.3f} | {v}")

    # === 5. PARADOXE ===
    print("\n--- 5. LE PARADOXE ---")
    p_grow = np.mean(monthly_papers[-12:]) / np.mean(monthly_papers[:12])
    c_grow = np.mean(new_concepts[-12:]) / np.mean(new_concepts[:12])
    print(f"  Papers/mois 2000: {np.mean(monthly_papers[:12]):.0f} -> 2012: {np.mean(monthly_papers[-12:]):.0f} (x{p_grow:.2f})")
    print(f"  Concepts/mois 2000: {np.mean(new_concepts[:12]):.0f} -> 2012: {np.mean(new_concepts[-12:]):.0f} (x{c_grow:.2f})")
    print(f"  Ratio: {p_grow/c_grow:.1f}x plus de papers pour meme innovation")
    paper_per_concept_2000 = 1000 / np.mean(efficiency[:12])
    paper_per_concept_2012 = 1000 / np.mean(efficiency[-12:])
    print(f"  2000: 1 concept nouveau tous les {paper_per_concept_2000:.0f} papers")
    print(f"  2012: 1 concept nouveau tous les {paper_per_concept_2012:.0f} papers")
    output["papers_per_concept_2000"] = round(paper_per_concept_2000)
    output["papers_per_concept_2012"] = round(paper_per_concept_2012)
    output["paper_growth"] = round(p_grow, 2)
    output["concept_growth"] = round(c_grow, 2)

    # === 6. METEORITES ===
    print("\n--- 6. METEORITES DETECTEES (exces > 2 sigma) ---")
    trend = power_decay(months[months > 6], A_fit, alpha_fit)
    actual = new_concepts[months > 6]
    residuals = actual - trend
    std_r = np.std(residuals)
    meteorites = []
    for i in range(len(residuals)):
        if residuals[i] > 2 * std_r:
            idx = i + 7
            r = results[idx]
            sig = residuals[i] / std_r
            meteorites.append({"period": r["period"], "new": r["new_concepts"],
                               "excess": round(residuals[i]), "sigma": round(sig, 1)})
            print(f"    {r['period']}: {r['new_concepts']} concepts (+{residuals[i]:.0f}, {sig:.1f}sigma)")
    output["meteorites"] = meteorites

    # === 7. POINT NEGATIF ===
    print("\n--- 7. POINT NEGATIF THEORIQUE ---")

    # Arbesman decay: facts have half-life ~8 years
    arbesman_h = 8 * 12  # months
    decay_rate = concepts[-1] * (1 - 2 ** (-1 / arbesman_h))
    current_birth = np.mean(new_concepts[-12:])
    net = current_birth - decay_rate
    print(f"  Arbesman decay (h=8 ans): {decay_rate:.0f} concepts obsoletes/mois")
    print(f"  Naissance actuelle: {current_birth:.0f} concepts/mois")
    print(f"  Balance nette: {net:+.0f} concepts/mois")
    output["arbesman_decay_per_month"] = round(decay_rate)
    output["birth_rate_per_month"] = round(current_birth)
    output["net_balance"] = round(net)

    if net < 0:
        print(f"  >>> DEJA EN NEGATIF")
    else:
        # Project forward
        for t_proj in range(len(results), 2400):
            birth = A_fit * max(t_proj, 1) ** (-alpha_fit)
            cum = concepts[-1] + birth * (t_proj - len(results))
            decay = cum * (1 - 2 ** (-1 / arbesman_h))
            if birth < decay:
                year_cross = 2000 + t_proj / 12
                print(f"  Croisement au mois {t_proj} = annee {year_cross:.1f}")
                print(f"  Concepts: ~{cum:.0f}, naissent {birth:.0f}/mois, meurent {decay:.0f}/mois")
                print(f"  >>> POINT NEGATIF: la science DECROIT en net")
                output["negative_point_year"] = round(year_cross, 1)
                break
        else:
            print(f"  Pas de croisement dans les 200 prochaines annees")
            output["negative_point_year"] = "never"

    # === 8. SYNTHESE ===
    print("\n" + "=" * 70)
    print("  SYNTHESE FINALE")
    print("=" * 70)
    print(f"  Sedov alpha = {alpha_fit:.3f} (theo 0.600) -> R2={r2:.4f}")
    print(f"  rho sature a {L:.3f} depuis ~{inflection_year:.0f}")
    print(f"  Efficacite: -{drop:.0f}% en 12 ans")
    print(f"  Papers x{p_grow:.1f}, Concepts x{c_grow:.1f}")
    print(f"  Sedov partition: ~28% cinetique (decouverte), ~72% thermique (renforcement)")
    print(f"  = 72% du travail scientifique sert a CONFIRMER ce qu on sait deja")

    # Save
    with open("data/results/densification_analysis.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved to data/results/densification_analysis.json")


if __name__ == "__main__":
    main()
