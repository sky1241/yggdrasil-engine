#!/usr/bin/env python3
"""
Brique 7 — Glyph Frame Builder
Build cumulative timeline of glyph emergence from chunks.

Usage:
    python engine/glyphs/glyph_frame_builder.py
"""
import gzip
import json
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent

SCAN_DIR = ROOT / "data" / "scan"
SEEDS_PATH = ROOT / "data" / "core" / "seeds_s2.json"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
OUTPUT_PATH = SCAN_DIR / "glyph_frames.json"

ARXIV_CHUNKS_DIR = SCAN_DIR / "glyph_chunks"
PMC_CHUNKS_DIR = SCAN_DIR / "pmc_glyph_chunks"


def load_complete_chunks(chunks_dir: Path) -> list[Path]:
    """Find all complete chunk directories."""
    if not chunks_dir.exists():
        return []
    result = []
    for d in sorted(chunks_dir.iterdir()):
        if d.is_dir() and (d / "activity.json.gz").exists():
            meta_path = d / "meta.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    m = json.load(f)
                if m.get("status") == "complete":
                    result.append(d)
    return result


def build_phase1() -> list[dict]:
    """Phase 1: Historical S-2 seeds from seeds_s2.json."""
    if not SEEDS_PATH.exists():
        print("  WARNING: seeds_s2.json not found, skipping Phase 1")
        return []

    with open(SEEDS_PATH, encoding="utf-8") as f:
        seeds_data = json.load(f)

    # Group seeds by t0_year
    by_year = defaultdict(list)
    for seed in seeds_data["seeds"]:
        by_year[seed["t0_year"]].append(seed)

    frames = []
    all_glyphs = set()

    for year in sorted(by_year.keys()):
        new_glyphs = [s["glyph"] for s in by_year[year]]
        new_names = [s["name"] for s in by_year[year]]
        all_glyphs.update(new_glyphs)

        frames.append({
            "period": str(year),
            "year": year,
            "phase": "historical",
            "new_glyphs": new_glyphs,
            "new_names": new_names,
            "total_glyphs": len(all_glyphs),
            "glyphs_active": 0,  # no data yet
            "edges_cumulative": 0,
        })

    print(f"  Phase 1: {len(frames)} historical frames, {len(all_glyphs)} seed glyphs")
    return frames


def build_phase2() -> list[dict]:
    """Phase 2: Scan chunks for glyph activity by period."""
    arxiv_chunks = load_complete_chunks(ARXIV_CHUNKS_DIR)
    pmc_chunks = load_complete_chunks(PMC_CHUNKS_DIR)
    all_chunks = arxiv_chunks + pmc_chunks

    if not all_chunks:
        print("  WARNING: No complete chunks found for Phase 2")
        return []

    print(f"  Phase 2: reading {len(all_chunks)} chunks "
          f"({len(arxiv_chunks)} arXiv + {len(pmc_chunks)} PMC)")

    # Aggregate activity and edge counts per period
    period_glyphs = defaultdict(set)     # period → set of glyph_ids
    period_edges = defaultdict(int)       # period → number of pairs

    for i, cdir in enumerate(all_chunks):
        # Activity
        with gzip.open(cdir / "activity.json.gz", "rt", encoding="utf-8") as f:
            activity = json.load(f)
        for period, glyphs in activity.items():
            for gid_str in glyphs:
                period_glyphs[period].add(int(gid_str))

        # Edge count from cooc
        with gzip.open(cdir / "cooc.json.gz", "rt", encoding="utf-8") as f:
            cooc = json.load(f)
        for period, pairs in cooc.items():
            period_edges[period] += len(pairs)

        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(all_chunks)} chunks")

    # Sort periods and build cumulative frames
    periods = sorted(period_glyphs.keys())
    print(f"  {len(periods)} periods from {periods[0]} to {periods[-1]}")

    frames = []
    cumulative_glyphs = set()
    cumulative_edges = 0

    for period in periods:
        new_glyphs = period_glyphs[period] - cumulative_glyphs
        cumulative_glyphs.update(period_glyphs[period])
        cumulative_edges += period_edges.get(period, 0)

        # Parse year from period
        try:
            year = int(period.split("-")[0])
        except ValueError:
            year = 0

        frames.append({
            "period": period,
            "year": year,
            "phase": "data",
            "glyphs_active": len(cumulative_glyphs),
            "glyphs_new": len(new_glyphs),
            "glyphs_period": len(period_glyphs[period]),
            "edges_cumulative": cumulative_edges,
            "edges_period": period_edges.get(period, 0),
        })

    return frames


def build():
    """Build complete glyph timeline."""
    print("=== Glyph Frame Builder ===")

    frames_p1 = build_phase1()
    frames_p2 = build_phase2()

    all_frames = frames_p1 + frames_p2

    output = {
        "meta": {
            "total_frames": len(all_frames),
            "historical_frames": len(frames_p1),
            "data_frames": len(frames_p2),
            "method": "glyph_frame_builder_v1",
        },
        "frames": all_frames,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)

    print(f"\n  Output: {OUTPUT_PATH}")
    print(f"  Total frames: {len(all_frames)}")
    if frames_p2:
        last = frames_p2[-1]
        print(f"  Final state: {last['glyphs_active']} glyphs, "
              f"{last['edges_cumulative']:,} edges")


if __name__ == "__main__":
    build()
