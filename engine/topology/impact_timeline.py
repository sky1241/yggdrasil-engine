#!/usr/bin/env python3
"""
Impact Timeline — Chronological impact analysis with variable time windows.

Windows:
  - Before 1900: every 100 years
  - 1900-1930: every 10 years
  - After 1930: every year

For each window: aggregate papers, compute weighted impact (spread, centroid shift,
top authors, top papers), normalize by window size for comparison.

Input: data/impact.db (from impact_scanner.py)
Output: data/impact_timeline.json + data/impact_timeline.db

Usage:
    python engine/topology/impact_timeline.py
    python engine/topology/impact_timeline.py --top 10    # show top N per window
"""
import argparse
import json
import math
import os
import sqlite3
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
# Force UTF-8 stdout on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
IMPACT_DB = ROOT / "data" / "impact.db"
OUTPUT_JSON = ROOT / "data" / "impact_timeline.json"
OUTPUT_DB = ROOT / "data" / "impact_timeline.db"


def build_windows():
    """Build time windows as Sky specified:
    - Before 1900: 100-year bins
    - 1900-1930: 10-year bins
    - 1930+: yearly
    """
    windows = []

    # Before 1900: centuries
    for start in range(1800, 1900, 100):
        windows.append((start, start + 99, f"{start}s"))

    # 1900-1929: decades
    for start in range(1900, 1930, 10):
        windows.append((start, start + 9, f"{start}-{start+9}"))

    # 1930+: yearly
    for year in range(1930, 2026):
        windows.append((year, year, str(year)))

    return windows


def compute_window_stats(conn, year_start, year_end):
    """Compute impact stats for a time window."""

    # Papers in window — use weight_rare if available (v2), fallback to weight_pop
    # Check which columns exist
    cols = [r[1] for r in conn.execute("PRAGMA table_info(paper_impact)").fetchall()]
    has_v2 = "weight_rare" in cols and "spread_rare" in cols

    if has_v2:
        papers = conn.execute(
            "SELECT paper_id, year, domain, n_concepts, n_glyphs, "
            "centroid_x, centroid_y, centroid_z, spread_rare, weight_rare, author_names "
            "FROM paper_impact WHERE year >= ? AND year <= ? "
            "ORDER BY weight_rare DESC",
            (year_start, year_end)
        ).fetchall()
    else:
        papers = conn.execute(
            "SELECT paper_id, year, domain, n_concepts, n_glyphs, "
            "centroid_x, centroid_y, centroid_z, spread, weight_pop, author_names "
            "FROM paper_impact WHERE year >= ? AND year <= ? "
            "ORDER BY weight_pop DESC",
            (year_start, year_end)
        ).fetchall()

    if not papers:
        return None

    n = len(papers)
    window_years = year_end - year_start + 1

    # Column layout (both v1 and v2 queries return same shape):
    # 0=paper_id, 1=year, 2=domain, 3=n_concepts, 4=n_glyphs,
    # 5=centroid_x, 6=centroid_y, 7=centroid_z, 8=spread, 9=weight, 10=author_names
    total_weight = sum(p[9] or 0 for p in papers)
    total_concepts = sum(p[3] or 0 for p in papers)
    spreads = [p[8] for p in papers if p[8]]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0

    # Centroid of all papers in window
    cxs = [p[5] for p in papers if p[5] is not None]
    cys = [p[6] for p in papers if p[6] is not None]
    czs = [p[7] for p in papers if p[7] is not None]
    centroid_x = sum(cxs) / len(cxs) if cxs else 0
    centroid_y = sum(cys) / len(cys) if cys else 0
    centroid_z = sum(czs) / len(czs) if czs else 0

    # Spread of papers around window centroid (how dispersed is the research)
    if len(cxs) > 1:
        window_spread = math.sqrt(
            sum((x - centroid_x)**2 + (y - centroid_y)**2 + (z - centroid_z)**2
                for x, y, z in zip(cxs, cys, czs)) / len(cxs)
        )
    else:
        window_spread = 0

    # Normalized = per year (to compare 100-year windows with 1-year windows)
    weight_per_year = total_weight / window_years
    papers_per_year = n / window_years

    # Top papers (biggest weight = biggest splash)
    top_papers = []
    for p in papers[:10]:  # already sorted by weight_sum DESC
        authors = []
        if p[10]:
            try:
                authors = json.loads(p[10])
            except (json.JSONDecodeError, TypeError):
                pass
        top_papers.append({
            "paper_id": p[0],
            "year": p[1],
            "domain": p[2],
            "n_concepts": p[3],
            "spread": round(p[8], 4) if p[8] else 0,
            "weight": round(p[9], 0) if p[9] else 0,
            "authors": authors[:5],  # top 5 authors
        })

    # Top authors in this window
    author_counts = {}
    for p in papers:
        if p[10]:
            try:
                names = json.loads(p[10])
            except (json.JSONDecodeError, TypeError):
                continue
            for name in names:
                if not name or len(name) < 2:
                    continue
                if name not in author_counts:
                    author_counts[name] = {"n": 0, "weight": 0, "spreads": []}
                author_counts[name]["n"] += 1
                author_counts[name]["weight"] += p[9] or 0
                if p[8]:
                    author_counts[name]["spreads"].append(p[8])

    # Sort authors by weight
    top_authors = sorted(author_counts.items(), key=lambda x: x[1]["weight"], reverse=True)[:10]
    top_authors_list = []
    for name, stats in top_authors:
        avg_s = sum(stats["spreads"]) / len(stats["spreads"]) if stats["spreads"] else 0
        top_authors_list.append({
            "name": name,
            "n_papers": stats["n"],
            "weight": round(stats["weight"], 0),
            "avg_spread": round(avg_s, 4),
        })

    # Domains breakdown
    domain_counts = {}
    for p in papers:
        d = p[2] or "unknown"
        domain_counts[d] = domain_counts.get(d, 0) + 1
    top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "n_papers": n,
        "n_papers_per_year": round(papers_per_year, 1),
        "total_weight": round(total_weight, 0),
        "weight_per_year": round(weight_per_year, 0),
        "total_concepts_touched": total_concepts,
        "avg_spread": round(avg_spread, 5),
        "window_spread": round(window_spread, 5),
        "centroid": {
            "x": round(centroid_x, 5),
            "y": round(centroid_y, 5),
            "z": round(centroid_z, 5),
        },
        "top_papers": top_papers,
        "top_authors": top_authors_list,
        "top_domains": [{"domain": d, "count": c} for d, c in top_domains],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=5, help="Top N per window to display")
    args = parser.parse_args()

    if not IMPACT_DB.exists():
        print(f"ERROR: {IMPACT_DB} not found. Run impact_scanner.py first.")
        sys.exit(1)

    conn = sqlite3.connect(str(IMPACT_DB))
    windows = build_windows()

    print(f"Computing impact for {len(windows)} time windows...")
    t0 = time.time()

    timeline = []
    for i, (y_start, y_end, label) in enumerate(windows):
        stats = compute_window_stats(conn, y_start, y_end)
        if stats is None:
            continue

        entry = {
            "window": label,
            "year_start": y_start,
            "year_end": y_end,
            "window_years": y_end - y_start + 1,
            **stats,
        }
        timeline.append(entry)

        # Progress
        if stats["n_papers"] > 0:
            top_author = stats["top_authors"][0]["name"] if stats["top_authors"] else "?"
            print(f"  [{label:>9s}] {stats['n_papers']:>7,} papers | "
                  f"weight/yr {stats['weight_per_year']:>15,.0f} | "
                  f"spread {stats['avg_spread']:.3f} | "
                  f"top: {top_author[:30]}")

    conn.close()

    # Save JSON
    output = {
        "meta": {
            "description": "Impact timeline — variable windows (100yr/10yr/1yr)",
            "n_windows": len(timeline),
            "total_papers": sum(w["n_papers"] for w in timeline),
            "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "windows_spec": "before 1900: 100yr | 1900-1930: 10yr | 1930+: yearly",
        },
        "timeline": timeline,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone in {time.time()-t0:.1f}s")
    print(f"Output: {OUTPUT_JSON} ({OUTPUT_JSON.stat().st_size / 1e6:.1f} MB)")
    print(f"Windows with data: {len(timeline)}")

    # Also save to SQLite for fast queries
    out_conn = sqlite3.connect(str(OUTPUT_DB))
    out_conn.execute("DROP TABLE IF EXISTS timeline")
    out_conn.execute("""
        CREATE TABLE timeline (
            window      TEXT PRIMARY KEY,
            year_start  INTEGER,
            year_end    INTEGER,
            window_years INTEGER,
            n_papers    INTEGER,
            n_papers_per_year REAL,
            total_weight REAL,
            weight_per_year REAL,
            avg_spread  REAL,
            window_spread REAL,
            centroid_x  REAL,
            centroid_y  REAL,
            centroid_z  REAL,
            top_authors TEXT,
            top_papers  TEXT,
            top_domains TEXT
        )
    """)

    for w in timeline:
        out_conn.execute(
            "INSERT INTO timeline VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                w["window"], w["year_start"], w["year_end"], w["window_years"],
                w["n_papers"], w["n_papers_per_year"],
                w["total_weight"], w["weight_per_year"],
                w["avg_spread"], w["window_spread"],
                w["centroid"]["x"], w["centroid"]["y"], w["centroid"]["z"],
                json.dumps(w["top_authors"], ensure_ascii=False),
                json.dumps(w["top_papers"], ensure_ascii=False),
                json.dumps(w["top_domains"], ensure_ascii=False),
            )
        )

    out_conn.commit()
    out_conn.close()
    print(f"SQLite: {OUTPUT_DB} ({OUTPUT_DB.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
