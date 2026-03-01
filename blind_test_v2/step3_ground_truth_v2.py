#!/usr/bin/env python3
"""
Blind Test V2 — Step 3: Ground Truth (extended)
================================================
Maps 12 V1 breakthroughs + 8 new ones to concept pairs
using concepts_65k.json.

For V1 breakthroughs: exact concept_id match.
For new breakthroughs: fuzzy name match in concepts_65k.json.

Input:
  data/scan/concepts_65k.json

Output:
  blind_test_v2/ground_truth_v2.json
"""
import json
import os
import sys
import re

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)

# === V1 BREAKTHROUGHS (exact concept IDs from prompt) ===
V1_BREAKTHROUGHS = [
    {
        "name": "AlphaFold",
        "year": "2018-2020",
        "concept_a_id": "C154945302",  # Artificial intelligence
        "concept_b_id": "C55493867",   # Biochemistry
    },
    {
        "name": "mRNA vaccines",
        "year": "2020",
        "concept_a_id": "C171250308",  # Nanotechnology
        "concept_b_id": "C203014093",  # Immunology
    },
    {
        "name": "CRISPR base editing",
        "year": "2016-2017",
        "concept_a_id": "C178790620",  # Organic chemistry
        "concept_b_id": "C54355233",   # Genetics
    },
    {
        "name": "Gravitational waves",
        "year": "2015-2016",
        "concept_a_id": "C120665830",  # Optics
        "concept_b_id": "C62520636",   # Quantum mechanics
    },
    {
        "name": "AlphaGo",
        "year": "2016-2017",
        "concept_a_id": "C11413529",   # Algorithm
        "concept_b_id": "C154945302",  # Artificial intelligence
    },
    {
        "name": "Transformers/GPT",
        "year": "2017-2020",
        "concept_a_id": "C154945302",  # Artificial intelligence
        "concept_b_id": "C41895202",   # Linguistics
    },
    {
        "name": "CAR-T therapy",
        "year": "2017",
        "concept_a_id": "C203014093",  # Immunology
        "concept_b_id": "C95444343",   # Cell biology
    },
    {
        "name": "Cryo-EM",
        "year": "2016+",
        "concept_a_id": "C184779094",  # Atomic physics
        "concept_b_id": "C55493867",   # Biochemistry
    },
    {
        "name": "Topological insulators",
        "year": "2016+",
        "concept_a_id": "C159985019",  # Composite material
        "concept_b_id": "C62520636",   # Quantum mechanics
    },
    {
        "name": "Microbiome therapeutics",
        "year": "2018+",
        "concept_a_id": "C126322002",  # Internal medicine
        "concept_b_id": "C18903297",   # Ecology
    },
    {
        "name": "Quantum supremacy",
        "year": "2019",
        "concept_a_id": "C11413529",   # Algorithm
        "concept_b_id": "C62520636",   # Quantum mechanics
    },
    {
        "name": "GAN explosion",
        "year": "2016+",
        "concept_a_id": "C105795698",  # Statistics
        "concept_b_id": "C154945302",  # Artificial intelligence
    },
]

# === V2 NEW BREAKTHROUGHS (need fuzzy match) ===
V2_NEW_BREAKTHROUGHS = [
    {
        "name": "Perovskite solar cells",
        "year": "2016+",
        "search_a": "Perovskite",
        "search_b": "Photovoltaic",
    },
    {
        "name": "Organoids",
        "year": "2017+",
        "search_a": "Stem cell",
        "search_b": "Tissue engineering",
    },
    {
        "name": "Single-cell RNA-seq",
        "year": "2016+",
        "search_a": "RNA",
        "search_b": "Single cell",
    },
    {
        "name": "Neuromorphic computing",
        "year": "2018+",
        "search_a": "Neuroscience",
        "search_b": "Semiconductor",
    },
    {
        "name": "Federated learning",
        "year": "2019+",
        "search_a": "Privacy",
        "search_b": "Machine learning",
    },
    {
        "name": "Graph neural networks",
        "year": "2018+",
        "search_a": "Graph theory",
        "search_b": "Deep learning",
    },
    {
        "name": "Optogenetics maturation",
        "year": "2016+",
        "search_a": "Optics",
        "search_b": "Neuroscience",
    },
    {
        "name": "Liquid biopsy",
        "year": "2016+",
        "search_a": "Biopsy",
        "search_b": "Cancer",
    },
]


def fuzzy_match(search_term, concepts_by_name):
    """Find best matching concept for a search term."""
    term_lower = search_term.lower().strip()

    # 1. Exact match (case-insensitive)
    for name, info_list in concepts_by_name.items():
        if name.lower() == term_lower:
            # Return highest-level (most general) match
            best = max(info_list, key=lambda x: (-x["level"], x["works_count"]))
            return best

    # 2. Starts-with match
    matches = []
    for name, info_list in concepts_by_name.items():
        if name.lower().startswith(term_lower):
            for info in info_list:
                matches.append(info)
    if matches:
        best = max(matches, key=lambda x: x["works_count"])
        return best

    # 3. Contains match
    matches = []
    for name, info_list in concepts_by_name.items():
        if term_lower in name.lower():
            for info in info_list:
                matches.append(info)
    if matches:
        # Prefer shorter names (more specific match) with high works_count
        best = max(matches, key=lambda x: x["works_count"])
        return best

    return None


def main():
    print("Blind Test V2 — Step 3: Ground Truth (extended)")
    print("=" * 60)

    # Load concepts
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        c65 = json.load(f)

    concepts = c65["concepts"]
    n_concepts = len(concepts)
    print(f"Loaded {n_concepts:,} concepts")

    # Build lookup by concept ID (without prefix)
    url_to_info = {}
    concepts_by_name = {}  # name -> [info, ...]
    for url, info in concepts.items():
        cid = url.replace("https://openalex.org/", "")
        full_info = {
            "url": url,
            "cid": cid,
            "idx": info["idx"],
            "name": info["name"],
            "level": info["level"],
            "works_count": info.get("works_count", 0),
        }
        url_to_info[cid] = full_info
        name = info["name"]
        if name not in concepts_by_name:
            concepts_by_name[name] = []
        concepts_by_name[name].append(full_info)

    # === Process V1 breakthroughs ===
    print(f"\n--- V1 Breakthroughs (12) ---")
    ground_truth = []

    for bt in V1_BREAKTHROUGHS:
        info_a = url_to_info.get(bt["concept_a_id"])
        info_b = url_to_info.get(bt["concept_b_id"])

        if info_a and info_b:
            # Pair key: sorted URLs
            urls = sorted([info_a["url"], info_b["url"]])
            pair_key = f"{urls[0]}|{urls[1]}"
            idx_pair = sorted([info_a["idx"], info_b["idx"]])
            idx_key = f"{idx_pair[0]}|{idx_pair[1]}"

            entry = {
                "name": bt["name"],
                "year": bt["year"],
                "source": "V1",
                "concept_a_name": info_a["name"],
                "concept_b_name": info_b["name"],
                "concept_a_url": info_a["url"],
                "concept_b_url": info_b["url"],
                "concept_a_idx": info_a["idx"],
                "concept_b_idx": info_b["idx"],
                "pair_key": pair_key,
                "idx_key": idx_key,
                "matched": True,
            }
            ground_truth.append(entry)
            print(f"  OK  {bt['name']:<30s} → "
                  f"{info_a['name'][:20]} × {info_b['name'][:20]}")
        else:
            missing = []
            if not info_a:
                missing.append(f"A={bt['concept_a_id']}")
            if not info_b:
                missing.append(f"B={bt['concept_b_id']}")
            ground_truth.append({
                "name": bt["name"],
                "year": bt["year"],
                "source": "V1",
                "matched": False,
                "missing": missing,
            })
            print(f"  MISS {bt['name']:<30s} — NOT MATCHED ({', '.join(missing)})")

    # === Process V2 new breakthroughs (fuzzy match) ===
    print(f"\n--- V2 New Breakthroughs (8) ---")

    for bt in V2_NEW_BREAKTHROUGHS:
        match_a = fuzzy_match(bt["search_a"], concepts_by_name)
        match_b = fuzzy_match(bt["search_b"], concepts_by_name)

        if match_a and match_b:
            # Make sure they're different concepts
            if match_a["idx"] == match_b["idx"]:
                print(f"  SKIP {bt['name']:<30s} — same concept for both!")
                ground_truth.append({
                    "name": bt["name"], "year": bt["year"],
                    "source": "V2", "matched": False,
                    "reason": "same concept matched for both terms",
                })
                continue

            urls = sorted([match_a["url"], match_b["url"]])
            pair_key = f"{urls[0]}|{urls[1]}"
            idx_pair = sorted([match_a["idx"], match_b["idx"]])
            idx_key = f"{idx_pair[0]}|{idx_pair[1]}"

            entry = {
                "name": bt["name"],
                "year": bt["year"],
                "source": "V2",
                "concept_a_name": match_a["name"],
                "concept_b_name": match_b["name"],
                "concept_a_url": match_a["url"],
                "concept_b_url": match_b["url"],
                "concept_a_idx": match_a["idx"],
                "concept_b_idx": match_b["idx"],
                "pair_key": pair_key,
                "idx_key": idx_key,
                "search_a": bt["search_a"],
                "search_b": bt["search_b"],
                "matched": True,
            }
            ground_truth.append(entry)
            print(f"  OK  {bt['name']:<30s} → "
                  f"{match_a['name'][:20]} (L{match_a['level']}) × "
                  f"{match_b['name'][:20]} (L{match_b['level']})")
        else:
            missing = []
            if not match_a:
                missing.append(f"A='{bt['search_a']}'")
            if not match_b:
                missing.append(f"B='{bt['search_b']}'")
            ground_truth.append({
                "name": bt["name"], "year": bt["year"],
                "source": "V2", "matched": False,
                "missing": missing,
            })
            print(f"  MISS {bt['name']:<30s} — NOT MATCHED ({', '.join(missing)})")

    # Summary
    matched = [g for g in ground_truth if g.get("matched")]
    unmatched = [g for g in ground_truth if not g.get("matched")]
    print(f"\n{'=' * 60}")
    print(f"Ground Truth: {len(matched)} matched, {len(unmatched)} unmatched")
    print(f"  V1: {sum(1 for g in matched if g['source']=='V1')}/12")
    print(f"  V2: {sum(1 for g in matched if g['source']=='V2')}/8")

    # Save
    output_path = os.path.join(BASE, "ground_truth_v2.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "meta": {
                "n_total": len(ground_truth),
                "n_matched": len(matched),
                "n_unmatched": len(unmatched),
                "timestamp": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            },
            "breakthroughs": ground_truth,
        }, f, indent=2, ensure_ascii=False)

    print(f"\nSaved: {output_path}")
    print("STEP 3 DONE")


if __name__ == "__main__":
    main()
