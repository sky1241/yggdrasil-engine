#!/usr/bin/env python3
"""
YGGDRASIL — SCAN MUNINN GLYPHS (Mission #2)
════════════════════════════════════════════════════
Scan WT2 par COMBINAISONS de glyphes pour trouver F5/F8/F9
— les 3 formules Muninn invisibles au scan Uzzi.

F5 = EMA: alpha * x + (1-alpha) * S  → {alpha, cdot, +}
F8 = Decay+seuil: w * 2^(-1/tau), |Z|>=3 → {tau, geq, cdot}
F9 = Novelty: sum(1{...}) - sum(1{...}) → {sum, in, |, indicator}

Sky × Claude — 10 Mars 2026, Versoix
"""

import json
import gzip
import os
import sys
import time
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
WT2_DIR = os.path.join(REPO, "data", "scan", "wt2_chunks")
RESULTS_DIR = os.path.join(REPO, "data", "results")

# ══════════════════════════════════════════════════
# GLYPH SIGNATURES for F5, F8, F9
# ══════════════════════════════════════════════════
# Each formula has REQUIRED glyphs (must all be present) and BONUS glyphs

FORMULAS = {
    "F5_ema": {
        "desc": "Exponential Moving Average: S_t = α·x_t + (1-α)·S_{t-1}",
        "required": {90, 631},       # alpha + cdot (multiplication with alpha = EMA signature)
        "bonus": {4, 451},            # + and sum (weighted accumulation)
        "min_required": 2,
    },
    "F8_decay_threshold": {
        "desc": "Co-occurrence decay: w·2^(-1/τ), threshold |Z|≥3",
        "required": {109, 631},       # tau + cdot (tau-based decay)
        "bonus": {535, 16},            # geq + pipe (threshold condition)
        "min_required": 2,
    },
    "F9_novelty": {
        "desc": "Novelty scoring: Σ𝟙{...} - Σ𝟙{...} with indicator",
        "required": {451, 442},        # sum + in (summation with membership test)
        "bonus": {16, 249, 273},       # pipe, 𝕀, 𝟙 (indicator function symbols)
        "min_required": 2,
    },
}

# Domains to EXCLUDE (expected/boring for Muninn)
EXCLUDE_DOMAINS = {
    "Computer science", "Mathematics", "Pure mathematics",
    "Combinatorics", "Discrete mathematics", "Theoretical computer science",
}

# Muninn's own concept indices (from scan_muninn.py) — skip these
MUNINN_KNOWN = {
    12550, 54681, 57221, 61733, 34208, 5237, 11819, 2429, 9157, 934,
    62789, 8467, 40678, 28203, 32258, 60649, 8014, 54757, 63207, 3378,
    64837, 332, 16972, 2484, 3162, 1389, 449, 715, 9389, 2752,
}


def scan_chunks():
    """Scan all 416 WT2 chunks for glyph combinations."""
    t0 = time.time()
    chunk_dirs = sorted([
        d for d in os.listdir(WT2_DIR)
        if d.startswith("chunk_") and os.path.isdir(os.path.join(WT2_DIR, d))
    ])
    print(f"Scanning {len(chunk_dirs)} WT2 chunks...")

    # Results per formula
    results = {f: {
        "matches": [],           # (paper_id, domain, concepts, glyphs_found, bonus_count)
        "domain_counts": Counter(),
        "concept_counts": Counter(),
        "pioneer_papers": [],    # papers in unexpected domains
    } for f in FORMULAS}

    total_papers = 0
    papers_with_glyphs = 0

    for ci, chunk_name in enumerate(chunk_dirs):
        papers_path = os.path.join(WT2_DIR, chunk_name, "papers.json.gz")
        if not os.path.exists(papers_path):
            continue

        try:
            with gzip.open(papers_path, 'rt', encoding='utf-8') as f:
                papers = json.load(f)
        except Exception as e:
            print(f"  SKIP {chunk_name}: {e}")
            continue

        chunk_papers = 0
        for paper_id, pdata in papers.items():
            total_papers += 1
            chunk_papers += 1

            glyphs = set(pdata.get("g", []))
            concepts = pdata.get("c", [])
            domain = pdata.get("d", "")

            if not glyphs:
                continue
            papers_with_glyphs += 1

            for fname, fdef in FORMULAS.items():
                req = fdef["required"]
                bonus = fdef["bonus"]

                # Check required glyphs
                matched_req = req & glyphs
                if len(matched_req) < fdef["min_required"]:
                    continue

                # Count bonus matches
                matched_bonus = bonus & glyphs
                bonus_count = len(matched_bonus)
                total_match = len(matched_req) + bonus_count

                # Store match
                results[fname]["matches"].append({
                    "paper_id": paper_id,
                    "domain": domain,
                    "concepts": concepts,
                    "glyphs_matched": sorted(matched_req | matched_bonus),
                    "n_required": len(matched_req),
                    "n_bonus": bonus_count,
                    "total_match": total_match,
                })

                # Count domain (skip CS/Math)
                if domain and domain not in EXCLUDE_DOMAINS:
                    results[fname]["domain_counts"][domain] += 1

                    # Count concepts in unexpected domains
                    for cidx in concepts:
                        if cidx not in MUNINN_KNOWN:
                            results[fname]["concept_counts"][cidx] += 1

        if (ci + 1) % 50 == 0:
            elapsed = time.time() - t0
            print(f"  {ci+1}/{len(chunk_dirs)} chunks, {total_papers:,} papers, {elapsed:.0f}s")

    print(f"\nDone: {total_papers:,} papers, {papers_with_glyphs:,} with glyphs, {time.time()-t0:.0f}s")
    return results, total_papers, papers_with_glyphs


def cross_reference(results):
    """Check against first scan results."""
    scan_path = os.path.join(RESULTS_DIR, "scan_muninn.json")
    with open(scan_path, 'r', encoding='utf-8') as f:
        first_scan = json.load(f)

    # Build set of (mun_idx, other_idx) from first scan
    known_pairs = set()
    known_concepts = set()
    for r in first_scan.get("all_cross_unknown", []):
        known_pairs.add((r["mun_idx"], r["other_idx"]))
        known_concepts.add(r["other_idx"])
    for r in first_scan.get("top_100_holes", []):
        known_pairs.add((r["mun_idx"], r["other_idx"]))
        known_concepts.add(r["other_idx"])

    return known_concepts


def load_concept_names():
    """Load concept index → name mapping."""
    path = os.path.join(REPO, "data", "scan", "concepts_65k.json")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    idx_to_name = {}
    for url, info in data["concepts"].items():
        idx_to_name[info["idx"]] = info["name"]
    return idx_to_name


def load_species():
    """Load concept → species mapping."""
    import numpy as np
    pred_dir = os.path.join(REPO, "experiments", "predictions_2025")
    with open(os.path.join(pred_dir, "species_full.json"), 'r', encoding='utf-8') as f:
        sdata = json.load(f)
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"), 'r', encoding='utf-8') as f:
        cdata = json.load(f)
    with open(os.path.join(pred_dir, "collision_matrix_full.json"), 'r', encoding='utf-8') as f:
        collision = json.load(f)
    species_names = collision["meta"]["species_names"]

    url_to_idx = {url: info["idx"] for url, info in cdata["concepts"].items()}
    idx_to_species = {}
    for url, info in sdata["concepts"].items():
        if url in url_to_idx:
            idx_to_species[url_to_idx[url]] = info["species"]

    return idx_to_species, species_names


def main():
    t0 = time.time()
    print("=" * 100)
    print("SCAN MUNINN GLYPHS — F5/F8/F9 via WT2 glyph combinations")
    print("= Les 3 formules invisibles au z-score Uzzi =")
    print("=" * 100)

    # Scan
    results, total_papers, papers_with_glyphs = scan_chunks()

    # Load metadata
    print("\nLoading concept names + species...")
    idx_to_name = load_concept_names()
    idx_to_species, species_names = load_species()
    known_concepts = cross_reference(results)

    # Muninn species = CS/Math = species 4
    MUNINN_SPECIES = 4

    # ══════════════════════════════════════════════════
    # RESULTS PER FORMULA
    # ══════════════════════════════════════════════════
    for fname in sorted(FORMULAS.keys()):
        fdef = FORMULAS[fname]
        fres = results[fname]
        matches = fres["matches"]

        print(f"\n{'='*100}")
        print(f"  {fname}: {fdef['desc']}")
        print(f"  Required glyphs: {sorted(fdef['required'])} + bonus: {sorted(fdef['bonus'])}")
        print(f"  Total matches: {len(matches):,}")
        print(f"{'='*100}")

        if not matches:
            print("  (no matches)")
            continue

        # Filter to unexpected domains only
        unexpected = [m for m in matches if m["domain"] not in EXCLUDE_DOMAINS and m["domain"]]
        print(f"  Matches hors CS/Math: {len(unexpected):,}")

        # Domain distribution (hors CS/Math)
        print(f"\n  Domain distribution (top 30, hors CS/Math):")
        for domain, count in fres["domain_counts"].most_common(30):
            print(f"    {domain:45s} | {count:5,} papers")

        # Strong matches (bonus glyphs too)
        strong = [m for m in unexpected if m["n_bonus"] >= 1]
        print(f"\n  Strong matches (required + ≥1 bonus): {len(strong):,}")

        # Concept frequency in unexpected domains
        print(f"\n  Top 30 concepts in unexpected domains:")
        for cidx, count in fres["concept_counts"].most_common(30):
            name = idx_to_name.get(cidx, f"?{cidx}")
            sp = idx_to_species.get(cidx, -1)
            sp_name = species_names.get(str(sp), "?")
            cross = "CROSS" if sp != MUNINN_SPECIES and sp >= 0 else ""
            new = "NEW" if cidx not in known_concepts else ""
            tag = f"{cross} {new}".strip()
            if tag:
                tag = f"[{tag}]"
            print(f"    {name:40s} (idx={cidx:5d}, sp={sp_name[:20]:20s}) "
                  f"| {count:4d} papers {tag}")

        # Pioneer papers: papers in the rarest domain×formula combos
        # Group by domain, find domains with ≤10 papers
        rare_domains = {d for d, c in fres["domain_counts"].items() if c <= 20}
        pioneers = [m for m in unexpected if m["domain"] in rare_domains]
        pioneers.sort(key=lambda x: x["total_match"], reverse=True)

        print(f"\n  Pioneer papers (rare domains, ≤20 papers):")
        seen_domains_papers = set()
        shown = 0
        for m in pioneers:
            key = (m["domain"], m["paper_id"])
            if key in seen_domains_papers:
                continue
            seen_domains_papers.add(key)
            concepts_str = ", ".join(
                idx_to_name.get(c, f"?{c}")[:30] for c in m["concepts"][:5]
            )
            print(f"    [{m['domain'][:25]:25s}] paper={m['paper_id'][:20]:20s} "
                  f"| glyphs={m['glyphs_matched']} | concepts: {concepts_str}")
            shown += 1
            if shown >= 30:
                break

        # Cross-species concepts NOT in first scan
        print(f"\n  NEW cross-species concepts (absent from first Uzzi scan):")
        new_cross = []
        for cidx, count in fres["concept_counts"].most_common(100):
            sp = idx_to_species.get(cidx, -1)
            if sp != MUNINN_SPECIES and sp >= 0 and cidx not in known_concepts:
                name = idx_to_name.get(cidx, f"?{cidx}")
                sp_name = species_names.get(str(sp), "?")
                new_cross.append((cidx, name, sp, sp_name, count))

        for cidx, name, sp, sp_name, count in new_cross[:25]:
            print(f"    {name:40s} | sp={sp_name[:20]:20s} | {count:4d} papers | idx={cidx}")

    # ══════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════
    print(f"\n{'='*100}")
    print("RÉSUMÉ")
    print(f"{'='*100}")
    print(f"  Papers scannés: {total_papers:,}")
    print(f"  Papers avec glyphes: {papers_with_glyphs:,}")

    for fname in sorted(FORMULAS.keys()):
        fres = results[fname]
        matches = fres["matches"]
        unexpected = [m for m in matches if m["domain"] not in EXCLUDE_DOMAINS and m["domain"]]
        n_domains = len(fres["domain_counts"])
        n_new = sum(1 for cidx in fres["concept_counts"]
                    if idx_to_species.get(cidx, -1) != MUNINN_SPECIES
                    and idx_to_species.get(cidx, -1) >= 0
                    and cidx not in known_concepts)
        print(f"\n  {fname}:")
        print(f"    Total matches: {len(matches):,}")
        print(f"    Hors CS/Math: {len(unexpected):,}")
        print(f"    Domaines uniques: {n_domains}")
        print(f"    Nouveaux concepts cross-species: {n_new}")

    # ══════════════════════════════════════════════════
    # SAVE
    # ══════════════════════════════════════════════════
    outfile = os.path.join(RESULTS_DIR, "scan_muninn_glyphs.json")
    output = {
        "scan": "muninn_glyphs_f5_f8_f9",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_papers": total_papers,
        "papers_with_glyphs": papers_with_glyphs,
    }
    for fname in sorted(FORMULAS.keys()):
        fres = results[fname]
        fdef = FORMULAS[fname]

        # Collect new cross-species concepts
        new_cross = []
        for cidx, count in fres["concept_counts"].most_common(50):
            sp = idx_to_species.get(cidx, -1)
            if sp != MUNINN_SPECIES and sp >= 0 and cidx not in known_concepts:
                new_cross.append({
                    "idx": cidx,
                    "name": idx_to_name.get(cidx, f"?{cidx}"),
                    "species": sp,
                    "species_name": species_names.get(str(sp), "?"),
                    "paper_count": count,
                })

        output[fname] = {
            "desc": fdef["desc"],
            "required_glyphs": sorted(fdef["required"]),
            "bonus_glyphs": sorted(fdef["bonus"]),
            "total_matches": len(fres["matches"]),
            "matches_outside_cs_math": len([m for m in fres["matches"]
                                            if m["domain"] not in EXCLUDE_DOMAINS and m["domain"]]),
            "domain_distribution": dict(fres["domain_counts"].most_common(50)),
            "new_cross_species_concepts": new_cross,
            "pioneer_papers": [
                {"paper_id": m["paper_id"], "domain": m["domain"],
                 "glyphs": m["glyphs_matched"],
                 "concepts": m["concepts"][:10]}
                for m in sorted(
                    [m for m in fres["matches"]
                     if m["domain"] not in EXCLUDE_DOMAINS and m["domain"]
                     and fres["domain_counts"].get(m["domain"], 0) <= 20],
                    key=lambda x: x["total_match"], reverse=True
                )[:50]
            ],
        }

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")
    print(f"Total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
