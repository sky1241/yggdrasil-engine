#!/usr/bin/env python3
"""
Build arXiv_ID → domain lookup from mapper chunks.

For each paper:
  1. Find OpenAlex level-0 concept with highest score
  2. Fallback: use arXiv category from ID prefix (pre-2007 papers)

Output: data/scan/arxiv_domain_lookup.json.gz
  { "astro-ph/0401001": "Physics", "0910.0001": "Computer science", ... }

Usage:
    python engine/professions/build_domain_lookup.py
"""
import gzip
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MAPPER_DIR = ROOT / "data" / "scan" / "arxiv_map_chunks"
OUTPUT_PATH = ROOT / "data" / "scan" / "arxiv_domain_lookup.json.gz"

# OpenAlex level-0 concept IDs → display names
LEVEL0_CONCEPTS = {
    "https://openalex.org/C142362112": "Art",
    "https://openalex.org/C86803240": "Biology",
    "https://openalex.org/C144133560": "Business",
    "https://openalex.org/C185592680": "Chemistry",
    "https://openalex.org/C41008148": "Computer science",
    "https://openalex.org/C162324750": "Economics",
    "https://openalex.org/C127413603": "Engineering",
    "https://openalex.org/C39432304": "Environmental science",
    "https://openalex.org/C205649164": "Geography",
    "https://openalex.org/C127313418": "Geology",
    "https://openalex.org/C95457728": "History",
    "https://openalex.org/C192562407": "Materials science",
    "https://openalex.org/C33923547": "Mathematics",
    "https://openalex.org/C71924100": "Medicine",
    "https://openalex.org/C138885662": "Philosophy",
    "https://openalex.org/C121332964": "Physics",
    "https://openalex.org/C17744445": "Political science",
    "https://openalex.org/C15744967": "Psychology",
    "https://openalex.org/C144024400": "Sociology",
}

# arXiv category → OpenAlex level-0 mapping
ARXIV_CAT_TO_DOMAIN = {
    "astro-ph": "Physics",
    "cond-mat": "Physics",
    "gr-qc": "Physics",
    "hep-ex": "Physics",
    "hep-lat": "Physics",
    "hep-ph": "Physics",
    "hep-th": "Physics",
    "nucl-ex": "Physics",
    "nucl-th": "Physics",
    "physics": "Physics",
    "quant-ph": "Physics",
    "math-ph": "Physics",  # mathematical physics → Physics
    "math": "Mathematics",
    "cs": "Computer science",
    "nlin": "Mathematics",  # nonlinear → Math
    "q-bio": "Biology",
    "q-fin": "Economics",
    "stat": "Mathematics",  # statistics → Math
    "eess": "Engineering",  # electrical engineering
    "econ": "Economics",
}


def domain_from_concepts(concepts: list[dict]) -> str | None:
    """Find level-0 concept with highest score."""
    best_score = -1
    best_domain = None
    for c in concepts:
        cid = c.get("id", "")
        if cid in LEVEL0_CONCEPTS:
            score = c.get("score", 0)
            if score > best_score:
                best_score = score
                best_domain = LEVEL0_CONCEPTS[cid]
    return best_domain


def domain_from_arxiv_id(arxiv_id: str) -> str | None:
    """Extract domain from arXiv ID prefix (pre-2007 papers)."""
    if "/" in arxiv_id:
        cat = arxiv_id.split("/")[0]
        return ARXIV_CAT_TO_DOMAIN.get(cat)
    return None


def build():
    """Merge all mapper chunks into a compact domain lookup."""
    print("=== Build arXiv → Domain Lookup ===")

    chunks = sorted([
        d for d in MAPPER_DIR.iterdir()
        if d.is_dir() and (d / "map.json.gz").exists()
    ])
    print(f"  Mapper chunks: {len(chunks)}")

    lookup = {}
    stats = {"from_concept": 0, "from_arxiv_cat": 0, "no_domain": 0}
    t0 = time.time()

    for i, chunk_dir in enumerate(chunks):
        with gzip.open(chunk_dir / "map.json.gz", "rt", encoding="utf-8") as f:
            data = json.load(f)

        for arxiv_id, info in data.items():
            # Clean arXiv ID (remove .pdf suffix if present)
            clean_id = arxiv_id.replace(".pdf", "")

            # Strategy 1: level-0 concept from OpenAlex
            domain = domain_from_concepts(info.get("concepts", []))
            if domain:
                stats["from_concept"] += 1
            else:
                # Strategy 2: arXiv category prefix
                domain = domain_from_arxiv_id(clean_id)
                if domain:
                    stats["from_arxiv_cat"] += 1
                else:
                    stats["no_domain"] += 1
                    continue

            lookup[clean_id] = domain

        if (i + 1) % 50 == 0 or i == len(chunks) - 1:
            elapsed = time.time() - t0
            print(f"    {i+1}/{len(chunks)} chunks, {len(lookup):,} entries, {elapsed:.0f}s")

    # Save
    with gzip.open(OUTPUT_PATH, "wt", encoding="utf-8") as f:
        json.dump(lookup, f, ensure_ascii=False)

    elapsed = time.time() - t0
    print(f"\n  Output: {OUTPUT_PATH}")
    print(f"  Total entries: {len(lookup):,}")
    print(f"  From concept: {stats['from_concept']:,}")
    print(f"  From arXiv cat: {stats['from_arxiv_cat']:,}")
    print(f"  No domain: {stats['no_domain']:,}")
    print(f"  Time: {elapsed:.0f}s")

    # Domain distribution
    from collections import Counter
    dist = Counter(lookup.values())
    print(f"\n  Domain distribution:")
    for domain, count in dist.most_common():
        pct = 100 * count / len(lookup)
        print(f"    {domain:25s} {count:>8,} ({pct:5.1f}%)")


if __name__ == "__main__":
    build()
