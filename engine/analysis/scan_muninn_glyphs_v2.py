#!/usr/bin/env python3
"""
YGGDRASIL — SCAN MUNINN GLYPHS V2
════════════════════════════════════════════════════
Resserré: signatures PLUS STRICTES + focus domaines rares.
V1 était trop large (alpha+cdot = 277K papers de physique).

F5 = EMA: alpha + cdot + sum (convex combination signature)
F8 = Decay+seuil: tau + geq (decay WITH threshold = specific)
F9 = Novelty: sum + indicator (𝟙 or 𝕀 = very rare symbol)

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
# TIGHT GLYPH SIGNATURES
# ══════════════════════════════════════════════════
FORMULAS = {
    "F5_ema": {
        "desc": "EMA: α·x + (1-α)·S — convex combination",
        "required": {90, 631, 451},  # alpha + cdot + sum (ALL three)
        "bonus": {4},                 # +
        "min_required": 3,
    },
    "F5_ema_loose": {
        "desc": "EMA loose: α + Σ (weighted average pattern)",
        "required": {90, 451},        # alpha + sum
        "bonus": {631, 4},            # cdot, +
        "min_required": 2,
    },
    "F8_decay_threshold": {
        "desc": "Decay+threshold: τ + ≥ (decay constant with inequality)",
        "required": {109, 535},       # tau + geq
        "bonus": {631, 16},           # cdot, pipe
        "min_required": 2,
    },
    "F8_decay_pipe": {
        "desc": "Decay+absolute: τ + | (decay with norm/absolute value)",
        "required": {109, 16},        # tau + pipe
        "bonus": {535, 631},          # geq, cdot
        "min_required": 2,
    },
    "F9_indicator": {
        "desc": "Indicator: Σ + 𝟙 (summation with indicator function)",
        "required": {451, 273},       # sum + double-struck 1 (indicator)
        "bonus": {442, 16},           # in, pipe
        "min_required": 2,
    },
    "F9_indicator_alt": {
        "desc": "Indicator alt: Σ + 𝕀 (summation with identity/indicator)",
        "required": {451, 249},       # sum + double-struck I
        "bonus": {442, 16},           # in, pipe
        "min_required": 2,
    },
    "F9_membership": {
        "desc": "Membership scoring: Σ + ∈ + | (sum with membership + norm)",
        "required": {451, 442, 16},   # sum + in + pipe (ALL three)
        "bonus": {273, 249},          # indicators
        "min_required": 3,
    },
}

# Domains to EXCLUDE
EXCLUDE_DOMAINS = {
    "Computer science", "Mathematics", "Pure mathematics",
    "Combinatorics", "Discrete mathematics", "Theoretical computer science",
}

# Even MORE exclusion for "expected" matches
BORING_DOMAINS = EXCLUDE_DOMAINS | {"Physics"}

# Muninn known concepts
MUNINN_KNOWN = {
    12550, 54681, 57221, 61733, 34208, 5237, 11819, 2429, 9157, 934,
    62789, 8467, 40678, 28203, 32258, 60649, 8014, 54757, 63207, 3378,
    64837, 332, 16972, 2484, 3162, 1389, 449, 715, 9389, 2752,
}


def scan_chunks():
    t0 = time.time()
    chunk_dirs = sorted([
        d for d in os.listdir(WT2_DIR)
        if d.startswith("chunk_") and os.path.isdir(os.path.join(WT2_DIR, d))
    ])
    print(f"Scanning {len(chunk_dirs)} WT2 chunks...")

    results = {f: {
        "matches": [],
        "domain_counts": Counter(),
        "domain_counts_no_physics": Counter(),
        "concept_counts": Counter(),
        "concept_counts_no_physics": Counter(),
    } for f in FORMULAS}

    total_papers = 0

    for ci, chunk_name in enumerate(chunk_dirs):
        papers_path = os.path.join(WT2_DIR, chunk_name, "papers.json.gz")
        if not os.path.exists(papers_path):
            continue

        try:
            with gzip.open(papers_path, 'rt', encoding='utf-8') as f:
                papers = json.load(f)
        except Exception:
            continue

        for paper_id, pdata in papers.items():
            total_papers += 1
            glyphs = set(pdata.get("g", []))
            concepts = pdata.get("c", [])
            domain = pdata.get("d", "")

            if not glyphs:
                continue

            for fname, fdef in FORMULAS.items():
                req = fdef["required"]
                bonus = fdef["bonus"]

                matched_req = req & glyphs
                if len(matched_req) < fdef["min_required"]:
                    continue

                matched_bonus = bonus & glyphs
                total_match = len(matched_req) + len(matched_bonus)

                if domain and domain not in EXCLUDE_DOMAINS:
                    results[fname]["domain_counts"][domain] += 1

                    if domain not in BORING_DOMAINS:
                        results[fname]["domain_counts_no_physics"][domain] += 1

                        # Store paper info for non-physics domains
                        results[fname]["matches"].append({
                            "paper_id": paper_id,
                            "domain": domain,
                            "concepts": concepts,
                            "glyphs_matched": sorted(matched_req | matched_bonus),
                            "total_match": total_match,
                        })

                        for cidx in concepts:
                            if cidx not in MUNINN_KNOWN:
                                results[fname]["concept_counts_no_physics"][cidx] += 1

                    for cidx in concepts:
                        if cidx not in MUNINN_KNOWN:
                            results[fname]["concept_counts"][cidx] += 1

        if (ci + 1) % 100 == 0:
            print(f"  {ci+1}/{len(chunk_dirs)} chunks, {total_papers:,} papers, {time.time()-t0:.0f}s")

    print(f"\nDone: {total_papers:,} papers, {time.time()-t0:.0f}s")
    return results, total_papers


def main():
    t0 = time.time()
    print("=" * 100)
    print("SCAN MUNINN GLYPHS V2 — Signatures resserrées, focus domaines rares")
    print("=" * 100)

    results, total_papers = scan_chunks()

    # Load metadata
    print("\nLoading concept names + species...")
    concepts_path = os.path.join(REPO, "data", "scan", "concepts_65k.json")
    with open(concepts_path, 'r', encoding='utf-8') as f:
        cdata = json.load(f)
    idx_to_name = {}
    for url, info in cdata["concepts"].items():
        idx_to_name[info["idx"]] = info["name"]

    pred_dir = os.path.join(REPO, "experiments", "predictions_2025")
    with open(os.path.join(pred_dir, "species_full.json"), 'r', encoding='utf-8') as f:
        sdata = json.load(f)
    with open(os.path.join(pred_dir, "collision_matrix_full.json"), 'r', encoding='utf-8') as f:
        collision = json.load(f)
    species_names = collision["meta"]["species_names"]

    url_to_idx = {url: info["idx"] for url, info in cdata["concepts"].items()}
    idx_to_species = {}
    for url, info in sdata["concepts"].items():
        if url in url_to_idx:
            idx_to_species[url_to_idx[url]] = info["species"]

    MUNINN_SPECIES = 4

    # Load first scan known concepts
    scan_path = os.path.join(RESULTS_DIR, "scan_muninn.json")
    with open(scan_path, 'r', encoding='utf-8') as f:
        first_scan = json.load(f)
    first_scan_concepts = set()
    for r in first_scan.get("all_cross_unknown", []):
        first_scan_concepts.add(r["other_idx"])

    # ══════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════
    # Group by formula family (merge tight/loose variants)
    families = {
        "F5_EMA": ["F5_ema", "F5_ema_loose"],
        "F8_DECAY": ["F8_decay_threshold", "F8_decay_pipe"],
        "F9_NOVELTY": ["F9_indicator", "F9_indicator_alt", "F9_membership"],
    }

    for family_name, variant_names in families.items():
        print(f"\n{'='*100}")
        print(f"  {family_name}")
        print(f"{'='*100}")

        for fname in variant_names:
            fdef = FORMULAS[fname]
            fres = results[fname]
            matches = fres["matches"]

            all_domain_count = sum(fres["domain_counts"].values())
            no_phys_count = sum(fres["domain_counts_no_physics"].values())

            print(f"\n  --- {fname}: {fdef['desc']} ---")
            print(f"  Required: {sorted(fdef['required'])}, min={fdef['min_required']}")
            print(f"  All hors CS/Math: {all_domain_count:,} | Hors Physics aussi: {no_phys_count:,}")

            if not fres["domain_counts"]:
                print("  (no matches)")
                continue

            # All domains including physics
            print(f"\n  Domains (all hors CS/Math):")
            for d, c in fres["domain_counts"].most_common(20):
                marker = " <<<" if d not in BORING_DOMAINS else ""
                print(f"    {d:40s} | {c:6,} papers{marker}")

            # Focus: non-physics domains
            if no_phys_count > 0:
                print(f"\n  FOCUS — Domaines rares (hors Physics + CS/Math): {no_phys_count:,} papers")
                for d, c in fres["domain_counts_no_physics"].most_common(20):
                    print(f"    {d:40s} | {c:6,} papers")

                # Top concepts in rare domains
                print(f"\n  Top concepts in rare domains:")
                shown = 0
                for cidx, count in fres["concept_counts_no_physics"].most_common(100):
                    sp = idx_to_species.get(cidx, -1)
                    if sp == MUNINN_SPECIES or sp < 0:
                        continue
                    name = idx_to_name.get(cidx, f"?{cidx}")
                    sp_name = species_names.get(str(sp), "?")
                    new = "NEW" if cidx not in first_scan_concepts else "known"
                    print(f"    {name:40s} | sp={sp_name[:20]:20s} | {count:4d} papers [{new}]")
                    shown += 1
                    if shown >= 20:
                        break

                # Pioneer papers
                # Group matches by domain, show papers from rarest domains
                domain_papers = defaultdict(list)
                for m in matches:
                    domain_papers[m["domain"]].append(m)

                print(f"\n  Pioneer papers (rarest domains):")
                rare_sorted = sorted(domain_papers.items(), key=lambda x: len(x[1]))
                shown_total = 0
                for domain, dpapers in rare_sorted:
                    if shown_total >= 40:
                        break
                    # Sort by total_match descending
                    dpapers.sort(key=lambda x: x["total_match"], reverse=True)
                    for m in dpapers[:3]:  # max 3 per domain
                        concepts_str = ", ".join(
                            idx_to_name.get(c, f"?{c}")[:25] for c in m["concepts"][:4]
                        )
                        print(f"    [{m['domain'][:20]:20s}] {m['paper_id'][:22]:22s} "
                              f"| glyphs={m['glyphs_matched']} "
                              f"| {concepts_str}")
                        shown_total += 1

    # ══════════════════════════════════════════════════
    # CROSS-REFERENCE: New trous invisibles au premier scan
    # ══════════════════════════════════════════════════
    print(f"\n{'='*100}")
    print("NOUVEAUX TROUS — Concepts cross-species absents du premier scan Uzzi")
    print(f"{'='*100}")

    for family_name, variant_names in families.items():
        # Merge all concepts from all variants
        all_concepts = Counter()
        for fname in variant_names:
            all_concepts.update(results[fname]["concept_counts_no_physics"])

        new_cross = []
        for cidx, count in all_concepts.most_common(200):
            sp = idx_to_species.get(cidx, -1)
            if sp == MUNINN_SPECIES or sp < 0:
                continue
            if cidx in first_scan_concepts:
                continue
            name = idx_to_name.get(cidx, f"?{cidx}")
            sp_name = species_names.get(str(sp), "?")
            new_cross.append((cidx, name, sp_name, count))

        print(f"\n  {family_name}: {len(new_cross)} nouveaux concepts cross-species")
        for cidx, name, sp_name, count in new_cross[:15]:
            print(f"    {name:40s} | {sp_name:25s} | {count:4d} papers | idx={cidx}")

    # ══════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════
    print(f"\n{'='*100}")
    print("RÉSUMÉ")
    print(f"{'='*100}")
    print(f"  Papers scannés: {total_papers:,}")

    for fname in sorted(FORMULAS.keys()):
        fres = results[fname]
        all_count = sum(fres["domain_counts"].values())
        rare_count = sum(fres["domain_counts_no_physics"].values())
        n_domains = len(fres["domain_counts_no_physics"])
        print(f"  {fname:25s} | hors CS/Math: {all_count:6,} | hors Phys aussi: {rare_count:5,} | {n_domains} domaines rares")

    # ══════════════════════════════════════════════════
    # SAVE
    # ══════════════════════════════════════════════════
    outfile = os.path.join(RESULTS_DIR, "scan_muninn_glyphs_v2.json")
    output = {
        "scan": "muninn_glyphs_v2_tight",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_papers": total_papers,
    }
    for fname in sorted(FORMULAS.keys()):
        fdef = FORMULAS[fname]
        fres = results[fname]

        # New cross-species concepts
        new_cross = []
        for cidx, count in fres["concept_counts_no_physics"].most_common(50):
            sp = idx_to_species.get(cidx, -1)
            if sp == MUNINN_SPECIES or sp < 0:
                continue
            if cidx in first_scan_concepts:
                continue
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
            "total_hors_cs_math": sum(fres["domain_counts"].values()),
            "total_hors_physics": sum(fres["domain_counts_no_physics"].values()),
            "domain_distribution": dict(fres["domain_counts_no_physics"].most_common(30)),
            "new_cross_species": new_cross[:30],
            "pioneer_papers": [
                {"paper_id": m["paper_id"], "domain": m["domain"],
                 "glyphs": m["glyphs_matched"], "concepts": m["concepts"][:8]}
                for m in sorted(fres["matches"], key=lambda x: x["total_match"], reverse=True)[:30]
            ],
        }

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")
    print(f"Total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
