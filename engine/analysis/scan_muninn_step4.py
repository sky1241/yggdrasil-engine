#!/usr/bin/env python3
"""
YGGDRASIL — SCAN MUNINN STEP 4-5
════════════════════════════════════════════════════
Applique holes.py scoring (Type A/B/C) + classification P1-P5
aux résultats de scan_muninn.json.

Mappe chaque match vers les formules Muninn F1-F10.

Sky × Claude — 10 Mars 2026, Versoix
"""

import json
import os
import sys
import time
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
PRED_DIR = os.path.join(REPO, "experiments", "predictions_2025")

# ══════════════════════════════════════════════════
# FORMULA FAMILIES — mun_idx → formula tag
# ══════════════════════════════════════════════════
FORMULA_MAP = {
    12550: "F1_ebbinghaus",   # Exponential decay
    54681: "F1_ebbinghaus",   # Half-life
    60649: "F1_ebbinghaus",   # Forgetting
    8014:  "F1_ebbinghaus",   # Exponential function (2^x)
    57221: "F2_ncd",          # Information theory
    61733: "F2_ncd",          # Data compression
    34208: "F2_ncd",          # Kolmogorov complexity
    40678: "F3_tfidf",        # Cosine similarity
    54757: "F3_tfidf",        # Logarithm (IDF)
    62789: "F4_spreading",    # Semantic network
    3378:  "F4_spreading",    # Random walk
    63207: "F4_spreading",    # Graph theory
    5237:  "F5_ema",          # Exponential smoothing
    11819: "F5_ema",          # Moving average
    28203: "F9_novelty",      # Predictive coding
    32258: "F9_novelty",      # Novelty detection
    934:   "F6_spectral",     # Spectral clustering
    2429:  "F6_spectral",     # Laplacian matrix
    9157:  "F6_spectral",     # Eigenvalues
    64837: "F6_spectral",     # Markov chain
    8467:  "F8_cooc",         # Co-occurrence
}


def classify_pattern(r, cooc_max):
    """P1-P5 Pattern classification."""
    z = r["z"]
    cooc = r["cooc"]
    cross = r["cross"]
    cooc_norm = cooc / cooc_max if cooc_max > 0 else 0

    if z < -10 and cooc_norm < 0.001:
        return "P5"  # Anti-signal: virtually no co-occurrence
    if z < -5 and cross:
        return "P4"  # Open hole: significant cross-species gap
    if z < 0 and cross:
        return "P4"  # Mild open hole
    if cooc_norm > 0.1:
        return "P2"  # Dense: well-connected
    if z > 0 and cross:
        return "P1"  # Bridge: existing cross-species link
    return "P3"      # Theory×Tool


def classify_type(r, cooc_max, activity, act_max):
    """
    Type A/B/C classification using holes.py formulas.

    Type B (Conceptual) = primary — we have all the data for this.
    Score_B = Activity(A) × Activity(B) × (1 - CoOcc_norm) × |z_score|/10

    Type A (Technical) = flagged when both domains are highly productive but stuck.
    Type C (Perceptual) = flagged when cooc ≈ 0 despite both being massive fields.
    """
    mun_idx = r["mun_idx"]
    other_idx = r["other_idx"]

    wa = float(activity[mun_idx]) if mun_idx < len(activity) else 0
    wb = float(activity[other_idx]) if other_idx < len(activity) else 0

    # Normalize
    an = wa / act_max if act_max > 0 else 0
    bn = wb / act_max if act_max > 0 else 0
    cooc_norm = min(r["cooc"] / cooc_max, 1.0) if cooc_max > 0 else 0

    # Type B — Conceptual hole (holes.py formula)
    void_size = 1.0 - cooc_norm
    atypicality = min(abs(r["z"]), 10.0) / 10.0
    score_b = an * bn * void_size * atypicality

    # Type C — Perceptual (blind spot): cooc nearly 0 but BOTH are big fields
    # This means the connection COULD exist but nobody sees it
    if cooc_norm < 0.001 and an > 0.001 and bn > 0.001:
        score_c = an * bn * (1.0 - cooc_norm)
    else:
        score_c = 0.0

    # Type A — Technical (stuck): high z magnitude + high production
    # Proxy: if z < -15, the gap is KNOWN but unfilled (technical barrier)
    if r["z"] < -15 and bn > 0.001:
        score_a = bn * min(abs(r["z"]) / 30.0, 1.0) * 0.5
    else:
        score_a = 0.0

    # Determine dominant type
    scores = {"A": score_a, "B": score_b, "C": score_c}
    dominant = max(scores, key=scores.get)

    return scores, dominant


def main():
    t0 = time.time()
    print("=" * 100)
    print("SCAN MUNINN — STEP 4-5: HOLES.PY SCORING + P1-P5 + FORMULA MAPPING")
    print("=" * 100)

    # Load scan results
    scan_path = os.path.join(REPO, "data", "results", "scan_muninn.json")
    with open(scan_path, 'r', encoding='utf-8') as f:
        scan = json.load(f)

    # Dedup: all_cross_unknown already contains holes as subset
    all_cross = scan.get("all_cross_unknown", scan.get("top_100_cross_unknown", []))
    intra = scan.get("top_50_intra", [])
    cooc_max = scan.get("cooc_max", max((r["cooc"] for r in all_cross), default=1.0))

    # Dedup by (mun_idx, other_idx)
    seen = set()
    deduped = []
    for r in all_cross + intra:
        key = (r["mun_idx"], r["other_idx"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    print(f"  Loaded {len(all_cross)} cross + {len(intra)} intra → {len(deduped)} unique after dedup")

    # Load activity
    with open(os.path.join(PRED_DIR, "activity_full.json"), 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    activity = np.array(act_data["activity"], dtype=np.float64)
    act_max = float(activity[activity > 0].max())
    del act_data

    # ══════════════════════════════════════════════════
    # STEP 4: Score + classify each match
    # ══════════════════════════════════════════════════
    print("\n[STEP 4] Applying holes.py scoring + P1-P5 classification...\n")

    enriched = []
    for r in deduped:
        formula = FORMULA_MAP.get(r["mun_idx"], "F?_unknown")
        pattern = classify_pattern(r, cooc_max)
        scores, dominant = classify_type(r, cooc_max, activity, act_max)

        enriched.append({
            **r,
            "formula": formula,
            "pattern": pattern,
            "score_A": round(scores["A"], 6),
            "score_B": round(scores["B"], 6),
            "score_C": round(scores["C"], 6),
            "dominant_type": dominant,
            "dominant_score": round(scores[dominant], 6),
        })

    # ══════════════════════════════════════════════════
    # Group by formula
    # ══════════════════════════════════════════════════
    formula_groups = {}
    for r in enriched:
        f = r["formula"]
        if f not in formula_groups:
            formula_groups[f] = []
        formula_groups[f].append(r)

    formula_descs = {
        "F1_ebbinghaus": "2^(-Δ/h) — Exponential decay, adaptive half-life",
        "F2_ncd": "NCD — Normalized Compression Distance",
        "F3_tfidf": "TF-IDF + Cosine similarity",
        "F4_spreading": "Spreading activation — Collins & Loftus 1975",
        "F5_ema": "Exponential Moving Average",
        "F6_spectral": "Normalized Laplacian + Spectral clustering",
        "F8_cooc": "Co-occurrence thresholds + fusion",
        "F9_novelty": "Novelty scoring — Predictive coding",
    }

    print(f"{'='*100}")
    print("RESULTS PAR FORMULE MUNINN — CROSS-SPECIES + HOLES.PY SCORING")
    print(f"{'='*100}")

    for formula in sorted(formula_groups.keys()):
        group = formula_groups[formula]
        cross = [r for r in group if r.get("cross", False)]
        desc = formula_descs.get(formula, "")

        if not cross:
            print(f"\n  {formula}: {desc} — 0 cross-species matches (intra only)")
            continue

        print(f"\n{'─'*100}")
        print(f"  {formula}: {desc}")
        print(f"  {len(cross)} cross-species matches | Types: "
              f"A={sum(1 for r in cross if r['dominant_type']=='A')}, "
              f"B={sum(1 for r in cross if r['dominant_type']=='B')}, "
              f"C={sum(1 for r in cross if r['dominant_type']=='C')}")
        print(f"{'─'*100}")

        cross_sorted = sorted(cross, key=lambda x: x["dominant_score"], reverse=True)
        for i, r in enumerate(cross_sorted[:15]):
            zs = "+" if r["z"] > 0 else ""
            print(f"  {i+1:3d}. [{r['pattern']}] Type {r['dominant_type']} "
                  f"Score={r['dominant_score']:.6f} "
                  f"(A={r['score_A']:.4f} B={r['score_B']:.4f} C={r['score_C']:.4f})"
                  f"\n       {r['mun_name'][:30]} × {r['other_name'][:35]}"
                  f" | z={zs}{r['z']:.1f} cooc={r['cooc']:.3f}"
                  f" | [{r['other_sp_name'][:20]}]")

    # ══════════════════════════════════════════════════
    # TOP 50 ABSOLUTE — the money shots
    # ══════════════════════════════════════════════════
    cross_all = sorted([r for r in enriched if r.get("cross", False)],
                       key=lambda x: x["dominant_score"], reverse=True)

    print(f"\n{'='*100}")
    print(f"TOP 50 ABSOLUTE — MEILLEURES PISTES MUNINN (cross-species, {len(cross_all)} total)")
    print(f"{'='*100}")

    for i, r in enumerate(cross_all[:50]):
        zs = "+" if r["z"] > 0 else ""
        # Connection description
        if r["pattern"] == "P5":
            tag = "ANTI-SIGNAL"
        elif r["pattern"] == "P4":
            tag = "TROU OUVERT"
        elif r["pattern"] == "P1":
            tag = "PONT"
        else:
            tag = r["pattern"]

        type_desc = {"A": "Technique", "B": "Conceptuel", "C": "Perceptuel"}

        print(f"\n  {i+1:2d}. {r['formula']:18s} | [{r['pattern']}] Type {r['dominant_type']} ({type_desc[r['dominant_type']]})")
        print(f"      {r['mun_name']} × {r['other_name']} (L{r['other_level']})")
        print(f"      Concept_ids: [{r['mun_idx']}, {r['other_idx']}]")
        print(f"      Espèces: {r['mun_sp_name']} × {r['other_sp_name']}")
        print(f"      z={zs}{r['z']:.2f} | cooc={r['cooc']:.6f} | P4={r['p4']:.6f}")
        print(f"      Scores: A={r['score_A']:.4f} B={r['score_B']:.4f} C={r['score_C']:.4f}")
        print(f"      → {tag}: Score dominant = {r['dominant_score']:.6f}")

    # ══════════════════════════════════════════════════
    # P5 ANTI-SIGNALS
    # ══════════════════════════════════════════════════
    p5 = [r for r in cross_all if r["pattern"] == "P5"]
    print(f"\n{'='*100}")
    print(f"P5 ANTI-SIGNALS — {len(p5)} TROUS PROFONDS (z << 0, cooc ≈ 0)")
    print(f"= Lianes secrètes de Muninn =")
    print(f"{'='*100}")
    for i, r in enumerate(p5[:25]):
        print(f"  {i+1:2d}. {r['formula']:18s} | {r['mun_name'][:22]:22s} × {r['other_name'][:30]:30s}"
              f" | z={r['z']:8.1f} | cooc={r['cooc']:.4f}"
              f" | Type {r['dominant_type']} B={r['score_B']:.4f}"
              f" | [{r['other_sp_name'][:20]}]")

    # ══════════════════════════════════════════════════
    # SPECIES HEATMAP
    # ══════════════════════════════════════════════════
    print(f"\n{'='*100}")
    print("RÉSUMÉ FINAL")
    print(f"{'='*100}")

    pattern_counts = {}
    type_counts = {}
    for r in cross_all:
        pattern_counts[r["pattern"]] = pattern_counts.get(r["pattern"], 0) + 1
        type_counts[r["dominant_type"]] = type_counts.get(r["dominant_type"], 0) + 1

    print(f"\n  Patterns:")
    for p in sorted(pattern_counts.keys()):
        labels = {"P1": "Bridge", "P2": "Dense", "P3": "Theory×Tool",
                  "P4": "Open Hole", "P5": "Anti-signal"}
        print(f"    {p} ({labels.get(p, '?'):15s}): {pattern_counts[p]:6,}")

    print(f"\n  Types:")
    for t in sorted(type_counts.keys()):
        labels = {"A": "Technique", "B": "Conceptuel", "C": "Perceptuel"}
        print(f"    Type {t} ({labels.get(t, '?'):12s}): {type_counts[t]:6,}")

    print(f"\n  Par espèce étrangère:")
    sp_stats = {}
    for r in cross_all:
        sp = r["other_sp_name"]
        if sp not in sp_stats:
            sp_stats[sp] = {"count": 0, "p5": 0, "top_score": 0, "formulas": set(),
                            "types": {"A": 0, "B": 0, "C": 0}}
        sp_stats[sp]["count"] += 1
        if r["pattern"] == "P5": sp_stats[sp]["p5"] += 1
        sp_stats[sp]["top_score"] = max(sp_stats[sp]["top_score"], r["dominant_score"])
        sp_stats[sp]["formulas"].add(r["formula"])
        sp_stats[sp]["types"][r["dominant_type"]] += 1

    for sp, v in sorted(sp_stats.items(), key=lambda x: -x[1]["count"]):
        formulas = ", ".join(sorted(v["formulas"]))
        print(f"    {sp:35s} | {v['count']:5,} matches ({v['p5']:3d} P5) "
              f"| A={v['types']['A']:3d} B={v['types']['B']:3d} C={v['types']['C']:3d}"
              f" | top={v['top_score']:.4f}"
              f"\n      Formules: {formulas}")

    print(f"\n  Par formule Muninn:")
    for formula in sorted(formula_groups.keys()):
        group = formula_groups[formula]
        cross = [r for r in group if r.get("cross", False)]
        p5s = [r for r in cross if r["pattern"] == "P5"]
        types_b = sum(1 for r in cross if r["dominant_type"] == "B")
        species = set(r["other_sp_name"] for r in cross)
        if cross:
            top = max(r["dominant_score"] for r in cross)
            print(f"    {formula:18s} | {len(cross):5,} cross ({len(p5s):3d} P5, {types_b:3d} B) "
                  f"| top={top:.4f} | espèces: {len(species)}")

    # ══════════════════════════════════════════════════
    # SAVE
    # ══════════════════════════════════════════════════
    outfile = os.path.join(REPO, "data", "results", "scan_muninn_enriched.json")
    output = {
        "scan": "muninn_step4_enriched_v2",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_cross_total": len(cross_all),
        "pattern_counts": pattern_counts,
        "type_counts": type_counts,
        "top_50_absolute": cross_all[:50],
        "p5_anti_signals": p5[:50],
        "by_formula": {
            formula: sorted(
                [r for r in formula_groups[formula] if r.get("cross", False)],
                key=lambda x: x["dominant_score"], reverse=True
            )[:25]
            for formula in sorted(formula_groups.keys())
        },
        "species_stats": {
            sp: {"count": v["count"], "p5": v["p5"],
                 "top_score": v["top_score"],
                 "types": v["types"],
                 "formulas": sorted(v["formulas"])}
            for sp, v in sp_stats.items()
        },
    }
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")
    print(f"Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
