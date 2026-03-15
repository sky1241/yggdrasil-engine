#!/usr/bin/env python3
"""
build_arxiv_tree.py — Build comprehensive arXiv inventory (arxiv_tree.json)

Scans E:/arxiv/src/ for .tar files, parses YYMM codes, groups by year-month,
cross-references with glyph scan chunks, identifies coverage gaps, and writes
a structured JSON inventory file.

Output: data/scan/arxiv_tree.json
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
ARXIV_SRC = Path("E:/arxiv/src")
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GLYPH_CHUNKS_DIR = REPO_ROOT / "data" / "scan" / "glyph_chunks"
GLYPH_TREE_PATH = REPO_ROOT / "data" / "scan" / "glyph_tree.json"
OUTPUT_PATH = REPO_ROOT / "data" / "scan" / "arxiv_tree.json"

# ── Regex for arXiv tar filenames ──────────────────────────────────────
# arXiv_src_YYMM_NNN.tar where YYMM = 2-digit year + 2-digit month, NNN = chunk
TAR_RE = re.compile(r'^arXiv_src_(\d{2})(\d{2})_(\d{2,3})\.tar$')

# ── YYMM → YYYY-MM conversion ─────────────────────────────────────────
def yymm_to_yyyy_mm(yy_str, mm_str):
    """Convert 2-digit year + 2-digit month to YYYY-MM string.
    arXiv started in 1991, so:
      91-99 → 1991-1999
      00-90 → 2000-2090
    """
    yy = int(yy_str)
    mm = int(mm_str)
    if yy >= 91:
        year = 1900 + yy
    else:
        year = 2000 + yy
    return f"{year:04d}-{mm:02d}"


def scan_tar_files():
    """Scan E:/arxiv/src/ for valid .tar files, return list of dicts."""
    tars = []
    min_size = 1 * 1024 * 1024  # 1 MB

    for fname in sorted(os.listdir(ARXIV_SRC)):
        if not fname.endswith('.tar'):
            continue
        m = TAR_RE.match(fname)
        if not m:
            print(f"  [SKIP] unrecognized filename: {fname}")
            continue

        fpath = ARXIV_SRC / fname
        size = os.path.getsize(fpath)

        if size < min_size:
            print(f"  [SKIP] too small ({size:,} bytes): {fname}")
            continue

        # Check first byte isn't '<' (HTML error page)
        with open(fpath, 'rb') as f:
            first_byte = f.read(1)
        if first_byte == b'<':
            print(f"  [SKIP] HTML error file: {fname}")
            continue

        yy, mm, chunk = m.group(1), m.group(2), m.group(3)
        period = yymm_to_yyyy_mm(yy, mm)

        tars.append({
            'filename': fname,
            'period': period,
            'yymm': yy + mm,
            'chunk': int(chunk),
            'size': size,
        })

    return tars


def load_glyph_scan_data():
    """Load glyph_tree.json and all chunk meta.json files."""
    glyph_tree = None
    if GLYPH_TREE_PATH.exists():
        with open(GLYPH_TREE_PATH, 'r', encoding='utf-8') as f:
            glyph_tree = json.load(f)

    chunk_metas = {}
    if GLYPH_CHUNKS_DIR.exists():
        for cdir in sorted(GLYPH_CHUNKS_DIR.iterdir()):
            meta_path = cdir / "meta.json"
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                chunk_metas[meta['id']] = meta

    return glyph_tree, chunk_metas


def build_expected_months(first_period, last_period):
    """Generate all YYYY-MM between first and last (inclusive)."""
    fy, fm = map(int, first_period.split('-'))
    ly, lm = map(int, last_period.split('-'))
    months = []
    y, m = fy, fm
    while (y, m) <= (ly, lm):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def main():
    print("=" * 70)
    print("  arXiv Inventory Builder — arxiv_tree.json")
    print("=" * 70)

    # ── 1. Scan tar files ──────────────────────────────────────────────
    print(f"\n[1/4] Scanning {ARXIV_SRC} ...")
    tars = scan_tar_files()
    print(f"  Found {len(tars)} valid .tar files")

    if not tars:
        print("ERROR: No valid tar files found!")
        sys.exit(1)

    total_size = sum(t['size'] for t in tars)
    print(f"  Total size: {total_size / (1024**3):.2f} GB")

    # ── 2. Group by month ──────────────────────────────────────────────
    print("\n[2/4] Grouping by year-month ...")
    months_data = defaultdict(lambda: {'tars': 0, 'size_bytes': 0, 'chunks': [], 'files': []})

    for t in tars:
        p = t['period']
        months_data[p]['tars'] += 1
        months_data[p]['size_bytes'] += t['size']
        months_data[p]['chunks'].append(t['chunk'])
        months_data[p]['files'].append(t['filename'])

    # Sort chunks within each month
    for p in months_data:
        months_data[p]['chunks'] = sorted(months_data[p]['chunks'])
        months_data[p]['files'] = sorted(months_data[p]['files'])

    periods_sorted = sorted(months_data.keys())
    first_period = periods_sorted[0]
    last_period = periods_sorted[-1]
    print(f"  Period range: {first_period} → {last_period}")
    print(f"  Months with data: {len(periods_sorted)}")

    # ── 3. Find gaps ──────────────────────────────────────────────────
    print("\n[3/4] Checking for coverage gaps ...")
    expected = build_expected_months(first_period, last_period)
    present = set(periods_sorted)
    gaps = [m for m in expected if m not in present]
    print(f"  Expected months: {len(expected)}")
    print(f"  Missing months:  {len(gaps)}")
    if gaps:
        for g in gaps:
            print(f"    GAP: {g}")

    # ── 4. Load glyph scan data ──────────────────────────────────────
    print("\n[4/4] Loading glyph scan data ...")
    glyph_tree, chunk_metas = load_glyph_scan_data()

    glyph_scan_info = {"status": "not_found", "chunks_done": 0, "total_chunks": 0}
    glyph_periods_covered = set()
    total_papers_scanned = 0
    total_papers_matched = 0
    total_pairs = 0
    total_unique_pairs = 0
    total_scan_time = 0.0

    if glyph_tree:
        gt_prog = glyph_tree.get('progress', {})
        glyph_scan_info = {
            "status": "complete" if gt_prog.get('chunks_completed', 0) == gt_prog.get('chunks_total', 0) else "in_progress",
            "chunks_done": gt_prog.get('chunks_completed', 0),
            "total_chunks": gt_prog.get('chunks_total', 0),
            "papers_scanned": gt_prog.get('papers_scanned', 0),
            "papers_with_glyphs": gt_prog.get('papers_with_glyphs', 0),
            "pairs_counted": gt_prog.get('pairs_counted', 0),
            "glyph_count": glyph_tree.get('config', {}).get('glyph_count', 0),
            "cutoff": glyph_tree.get('config', {}).get('cutoff', 'unknown'),
        }

    if chunk_metas:
        for cid, meta in chunk_metas.items():
            total_papers_scanned += meta.get('papers_total', 0)
            total_papers_matched += meta.get('papers_matched', 0)
            total_pairs += meta.get('pairs_counted', 0)
            total_unique_pairs += meta.get('unique_pairs', 0)
            total_scan_time += meta.get('scan_time_sec', 0)
            for p in meta.get('periods_seen', []):
                glyph_periods_covered.add(p)

        glyph_scan_info['from_chunk_metas'] = {
            'papers_total': total_papers_scanned,
            'papers_matched': total_papers_matched,
            'pairs_counted': total_pairs,
            'unique_pairs_sum': total_unique_pairs,
            'total_scan_time_sec': round(total_scan_time, 1),
            'total_scan_time_hours': round(total_scan_time / 3600, 2),
            'periods_covered': len(glyph_periods_covered),
            'avg_papers_per_sec': round(total_papers_scanned / total_scan_time, 1) if total_scan_time > 0 else 0,
        }

    print(f"  Glyph scan status: {glyph_scan_info['status']}")
    print(f"  Glyph chunks: {glyph_scan_info.get('chunks_done', 0)}/{glyph_scan_info.get('total_chunks', 0)}")
    if chunk_metas:
        print(f"  Papers scanned (from metas): {total_papers_scanned:,}")
        print(f"  Papers matched (from metas): {total_papers_matched:,}")
        print(f"  Periods covered by glyphs:   {len(glyph_periods_covered)}")

    # ── Cross-reference: which months have glyph coverage? ──────────
    for p in months_data:
        months_data[p]['glyph_scanned'] = p in glyph_periods_covered

    months_with_glyph = sum(1 for p in months_data if months_data[p]['glyph_scanned'])
    months_without_glyph = len(months_data) - months_with_glyph

    # ── Build yearly summary ──────────────────────────────────────────
    years_summary = defaultdict(lambda: {'months': 0, 'tars': 0, 'size_bytes': 0, 'glyph_scanned_months': 0})
    for p in periods_sorted:
        year = p[:4]
        years_summary[year]['months'] += 1
        years_summary[year]['tars'] += months_data[p]['tars']
        years_summary[year]['size_bytes'] += months_data[p]['size_bytes']
        if months_data[p]['glyph_scanned']:
            years_summary[year]['glyph_scanned_months'] += 1

    # Add size_gb for readability
    for y in years_summary:
        years_summary[y]['size_gb'] = round(years_summary[y]['size_bytes'] / (1024**3), 2)

    # ── Find largest/smallest months ──────────────────────────────────
    by_tars = sorted(months_data.items(), key=lambda x: x[1]['tars'], reverse=True)
    by_size = sorted(months_data.items(), key=lambda x: x[1]['size_bytes'], reverse=True)

    # ── Determine download status ─────────────────────────────────────
    # Check what range we have vs what we'd expect for a full arXiv dump
    # arXiv papers go from 1991 to present; the latest YYMM in our set tells us
    # where the download stopped
    download_info = {
        "source": "s3://arxiv/src/",
        "tool": "aria2c",
        "local_dir": str(ARXIV_SRC),
        "first_file": tars[0]['filename'],
        "last_file": tars[-1]['filename'],
        "period_range": f"{first_period} to {last_period}",
        "total_tars": len(tars),
        "total_size_gb": round(total_size / (1024**3), 2),
    }

    # Check if we're missing recent months (incomplete download)
    last_year = int(last_period[:4])
    last_month = int(last_period[5:7])
    today = date.today()
    if last_year < today.year or (last_year == today.year and last_month < today.month - 1):
        download_info['status'] = 'partial'
        download_info['note'] = f"Latest file is {last_period}, current date is {today.isoformat()}"
    else:
        download_info['status'] = 'complete'

    # ── Build output JSON ────────────────────────────────────────────
    # Convert months_data to regular dict with sorted keys
    months_out = {}
    for p in periods_sorted:
        md = months_data[p]
        months_out[p] = {
            'tars': md['tars'],
            'size_bytes': md['size_bytes'],
            'size_mb': round(md['size_bytes'] / (1024**2), 1),
            'chunks': md['chunks'],
            'glyph_scanned': md['glyph_scanned'],
        }

    output = {
        "version": 1,
        "type": "arxiv_tree",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": "Comprehensive arXiv source tar inventory with glyph scan cross-reference",
        "metadata": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_tars": len(tars),
            "total_size_bytes": total_size,
            "total_size_gb": round(total_size / (1024**3), 2),
            "period_range": f"{first_period} to {last_period}",
            "months_covered": len(periods_sorted),
            "months_expected": len(expected),
            "months_missing": len(gaps),
            "avg_tars_per_month": round(len(tars) / len(periods_sorted), 1),
            "avg_size_per_month_gb": round(total_size / len(periods_sorted) / (1024**3), 2),
        },
        "download": download_info,
        "glyph_scan": glyph_scan_info,
        "glyph_coverage": {
            "months_with_glyph_data": months_with_glyph,
            "months_without_glyph_data": months_without_glyph,
            "coverage_pct": round(100 * months_with_glyph / len(months_data), 1) if months_data else 0,
        },
        "years": dict(sorted(years_summary.items())),
        "months": months_out,
        "gaps": gaps,
        "top_months_by_tars": [
            {"period": p, "tars": d['tars'], "size_mb": round(d['size_bytes'] / (1024**2), 1)}
            for p, d in by_tars[:10]
        ],
        "top_months_by_size": [
            {"period": p, "tars": d['tars'], "size_mb": round(d['size_bytes'] / (1024**2), 1)}
            for p, d in by_size[:10]
        ],
    }

    # ── Write output ─────────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  Written: {OUTPUT_PATH}")
    print(f"  Size: {os.path.getsize(OUTPUT_PATH):,} bytes")

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Total .tar files:     {len(tars):,}")
    print(f"  Total size:           {total_size / (1024**3):.2f} GB")
    print(f"  Period range:         {first_period} → {last_period}")
    print(f"  Months covered:       {len(periods_sorted)} / {len(expected)} expected")
    print(f"  Coverage gaps:        {len(gaps)}")
    print(f"  Avg tars/month:       {len(tars) / len(periods_sorted):.1f}")
    print(f"  Download status:      {download_info['status']}")
    print()
    print(f"  Glyph scan status:    {glyph_scan_info['status']}")
    print(f"  Glyph chunks:         {glyph_scan_info.get('chunks_done', 0)}/{glyph_scan_info.get('total_chunks', 0)}")
    print(f"  Months with glyphs:   {months_with_glyph}/{len(months_data)}" +
          f" ({100*months_with_glyph/len(months_data):.0f}%)" if months_data else "")
    print()
    print("  Top 5 months by # of tars:")
    for p, d in by_tars[:5]:
        print(f"    {p}: {d['tars']:>3} tars, {d['size_bytes']/(1024**3):.2f} GB")
    print()
    print("  Yearly breakdown:")
    for y in sorted(years_summary.keys()):
        ys = years_summary[y]
        print(f"    {y}: {ys['months']:>2} months, {ys['tars']:>4} tars, "
              f"{ys['size_gb']:>7.2f} GB, "
              f"glyph: {ys['glyph_scanned_months']}/{ys['months']}")
    print("=" * 70)


if __name__ == '__main__':
    main()
