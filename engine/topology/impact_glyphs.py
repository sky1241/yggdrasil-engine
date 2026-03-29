#!/usr/bin/env python3
"""
Impact Glyphs — Per-glyph (S-2 symbol) impact aggregation.

For each of the ~1,316 glyphs, compute:
  - How many papers touch it, and their aggregate impact scores
  - Temporal evolution: impact curve per glyph over decades/years
  - Which authors contributed most impact to this glyph
  - Cross-domain reach: how many different domains touch this glyph
  - Tier breakdown: extinction/asteroide/meteorite/rocher/pierre/caillou

Then for the top 500 glyphs, compute pairwise co-appearance impact
using the papers table (which glyphs co-appear in the same papers).

Input: data/impact_scale.db + data/wt3.db (papers table)
       data/scan/spectral_births.json (glyph names)
Output: data/impact_glyphs.db + data/impact_glyphs.json

Usage:
    python engine/topology/impact_glyphs.py
    python engine/topology/impact_glyphs.py --top 30
    python engine/topology/impact_glyphs.py --skip-pairs
    python engine/topology/impact_glyphs.py --pairs-only
"""
import argparse
import json
import math
import os
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
WT3_DB = ROOT / "data" / "wt3.db"
SCALE_DB = ROOT / "data" / "impact_scale.db"
SPECTRAL_JSON = ROOT / "data" / "scan" / "spectral_births.json"
OUTPUT_DB = ROOT / "data" / "impact_glyphs.db"
OUTPUT_JSON = ROOT / "data" / "impact_glyphs.json"


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_glyph_names():
    """Load glyph id→name mapping from spectral_births.json."""
    if not SPECTRAL_JSON.exists():
        log(f"  WARNING: {SPECTRAL_JSON} not found, glyph names unavailable")
        return {}
    with open(SPECTRAL_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    names = {}
    for node in data.get("nodes", []):
        if node.get("type") == "glyph":
            names[node["id"]] = node.get("name", f"glyph_{node['id']}")
    log(f"  Loaded {len(names):,} glyph names from spectral_births.json")
    return names


def build_glyph_scores(wt3_conn, scale_conn, out_conn, glyph_names):
    """
    Stream papers from WT3, parse glyphs JSON field, join with paper_scale
    to compute per-glyph impact stats.

    This processes ~833K papers.
    """
    log("Phase 1: Loading paper scores into memory...")

    # Load all paper scores into dict (833K entries, ~100MB RAM)
    paper_scores = {}
    rows = scale_conn.execute(
        "SELECT paper_id, score, tier, year, domain, n_concepts, z_spread "
        "FROM paper_scale"
    ).fetchall()
    for r in rows:
        paper_scores[r[0]] = {
            "score": r[1], "tier": r[2], "year": r[3],
            "domain": r[4], "n_concepts": r[5], "z_spread": r[6]
        }
    log(f"  Loaded {len(paper_scores):,} paper scores")

    # Load author info per paper
    log("Phase 2: Loading paper authors...")
    paper_authors = {}
    last_rowid = 0
    batch = 50000
    while True:
        arows = scale_conn.execute(
            "SELECT paper_id, author_names FROM paper_scale "
            "WHERE rowid > ? ORDER BY rowid LIMIT ?",
            (last_rowid, batch)
        ).fetchall()
        if not arows:
            break
        for pid, auth_json in arows:
            if auth_json:
                try:
                    paper_authors[pid] = json.loads(auth_json)
                except (json.JSONDecodeError, TypeError):
                    pass
        last_rowid += len(arows)
    log(f"  Loaded authors for {len(paper_authors):,} papers")

    # Phase 3: Stream papers from WT3 and aggregate per glyph
    log("Phase 3: Streaming papers from WT3, parsing glyphs...")

    # glyph_id -> stats accumulator
    glyphs = {}

    def year_to_window(y):
        if y is None:
            return None
        if y < 1950:
            return f"{(y // 50) * 50}s"
        if y < 1990:
            return f"{(y // 10) * 10}s"
        return str(y)

    # Skip COUNT(*) on 78GB — use known total from WT3 meta
    total_papers = 833030
    log(f"  Expected papers: ~{total_papers:,} (streaming from WT3)")

    last_rowid = 0
    batch_size = 10000
    done = 0
    total_edges = 0
    t0 = time.time()

    while True:
        rows = wt3_conn.execute(
            "SELECT rowid, paper_id, glyphs FROM papers "
            "WHERE rowid > ? AND glyphs IS NOT NULL ORDER BY rowid LIMIT ?",
            (last_rowid, batch_size)
        ).fetchall()

        if not rows:
            break

        for rowid, paper_id, glyphs_json in rows:
            ps = paper_scores.get(paper_id)
            if ps is None:
                continue

            try:
                glyph_ids = json.loads(glyphs_json)
            except (json.JSONDecodeError, TypeError):
                continue

            if not glyph_ids:
                continue

            score = ps["score"]
            tier = ps["tier"]
            dom = ps["domain"]
            year = ps["year"]
            z_sp = ps["z_spread"]
            w = year_to_window(year)
            authors = paper_authors.get(paper_id, [])

            for glyph_id in glyph_ids:
                gid = str(glyph_id)  # normalize to string
                total_edges += 1

                if gid not in glyphs:
                    glyphs[gid] = {
                        "total_score": 0.0,
                        "max_score": 0.0,
                        "n_papers": 0,
                        "scores": [],
                        "tiers": {"extinction": 0, "asteroide": 0, "meteorite": 0,
                                  "rocher": 0, "pierre": 0, "caillou": 0},
                        "domains": {},
                        "windows": {},
                        "top_authors": {},
                        "z_spreads": [],
                    }

                g = glyphs[gid]
                g["total_score"] += score
                g["max_score"] = max(g["max_score"], score)
                g["n_papers"] += 1
                g["tiers"][tier] = g["tiers"].get(tier, 0) + 1

                if len(g["scores"]) < 10000:
                    g["scores"].append(score)

                g["z_spreads"].append(z_sp)

                if dom:
                    g["domains"][dom] = g["domains"].get(dom, 0) + 1

                if w:
                    if w not in g["windows"]:
                        g["windows"][w] = {"n": 0, "total": 0.0, "max": 0.0}
                    gw = g["windows"][w]
                    gw["n"] += 1
                    gw["total"] += score
                    gw["max"] = max(gw["max"], score)

                for author in authors[:10]:
                    if not author or len(author) < 2:
                        continue
                    if author not in g["top_authors"]:
                        g["top_authors"][author] = {"n": 0, "total": 0.0, "max": 0.0}
                    ga = g["top_authors"][author]
                    ga["n"] += 1
                    ga["total"] += score
                    ga["max"] = max(ga["max"], score)

        last_rowid = rows[-1][0]
        done += len(rows)

        if done % 50000 == 0:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            log(f"  {done:,}/{total_papers:,} ({100*done/total_papers:.0f}%) "
                f"| {rate:,.0f} papers/s | {total_edges:,} edges | {len(glyphs):,} glyphs")

    elapsed = time.time() - t0
    log(f"  Processed {done:,} papers, {total_edges:,} edges in {elapsed:.1f}s")
    log(f"  {len(glyphs):,} glyphs with impact data")

    # Phase 4: Write to SQLite
    log("Phase 4: Writing glyph_impact table...")

    out_conn.execute("DROP TABLE IF EXISTS glyph_impact")
    out_conn.execute("""
        CREATE TABLE glyph_impact (
            glyph_id        TEXT PRIMARY KEY,
            glyph_name      TEXT,
            n_papers        INTEGER,
            total_score     REAL,
            avg_score       REAL,
            max_score       REAL,
            p90_score       REAL,
            n_domains       INTEGER,
            n_extinctions   INTEGER,
            n_asteroides    INTEGER,
            n_meteorites    INTEGER,
            avg_z_spread    REAL,
            domain_diversity REAL,
            top_domain      TEXT,
            top_authors     TEXT,
            temporal_curve  TEXT,
            tier_breakdown  TEXT
        )
    """)

    inserts = []
    for gid, g in glyphs.items():
        n = g["n_papers"]
        avg = g["total_score"] / n if n else 0

        # P90
        scores_sorted = sorted(g["scores"])
        p90_idx = int(len(scores_sorted) * 0.9)
        p90 = scores_sorted[p90_idx] if scores_sorted else 0

        # Domain diversity (Shannon entropy normalized)
        dom_total = sum(g["domains"].values())
        n_doms = len(g["domains"])
        if n_doms > 1 and dom_total > 0:
            entropy = -sum(
                (cnt / dom_total) * math.log(cnt / dom_total)
                for cnt in g["domains"].values()
            )
            max_entropy = math.log(n_doms)
            diversity = entropy / max_entropy if max_entropy > 0 else 0
        else:
            diversity = 0

        top_dom = max(g["domains"].items(), key=lambda x: x[1])[0] if g["domains"] else ""

        # Glyph name from spectral_births
        glyph_name = glyph_names.get(int(gid), f"glyph_{gid}") if gid.isdigit() else gid

        # Top 5 authors by total impact on this glyph
        top_auth = sorted(g["top_authors"].items(),
                          key=lambda x: x[1]["total"], reverse=True)[:5]
        top_auth_list = [{"name": a, "n": s["n"], "total": round(s["total"], 1),
                          "max": round(s["max"], 2)} for a, s in top_auth]

        # Temporal curve (sorted by window)
        curve = sorted(g["windows"].items())
        curve_list = [{"window": w, "n": s["n"],
                       "avg": round(s["total"] / s["n"], 2) if s["n"] else 0,
                       "max": round(s["max"], 2)} for w, s in curve]

        avg_z = sum(g["z_spreads"]) / len(g["z_spreads"]) if g["z_spreads"] else 0

        inserts.append((
            gid, glyph_name, n, round(g["total_score"], 2), round(avg, 3),
            round(g["max_score"], 2), round(p90, 2),
            n_doms,
            g["tiers"].get("extinction", 0),
            g["tiers"].get("asteroide", 0),
            g["tiers"].get("meteorite", 0),
            round(avg_z, 3),
            round(diversity, 4),
            top_dom,
            json.dumps(top_auth_list, ensure_ascii=False),
            json.dumps(curve_list, ensure_ascii=False),
            json.dumps(g["tiers"], ensure_ascii=False),
        ))

    log(f"  Inserting {len(inserts):,} glyphs...")
    out_conn.executemany(
        "INSERT OR IGNORE INTO glyph_impact VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        inserts
    )

    out_conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_gi_total ON glyph_impact(total_score DESC);
        CREATE INDEX IF NOT EXISTS idx_gi_avg ON glyph_impact(avg_score DESC);
        CREATE INDEX IF NOT EXISTS idx_gi_max ON glyph_impact(max_score DESC);
        CREATE INDEX IF NOT EXISTS idx_gi_papers ON glyph_impact(n_papers DESC);
        CREATE INDEX IF NOT EXISTS idx_gi_ext ON glyph_impact(n_extinctions DESC);
        CREATE INDEX IF NOT EXISTS idx_gi_diversity ON glyph_impact(domain_diversity DESC);
    """)
    out_conn.commit()
    log(f"  glyph_impact: {len(inserts):,} rows, 6 indexes")


def build_glyph_pairs(wt3_conn, scale_conn, out_conn):
    """
    For the top 500 glyphs by total_score, compute pairwise co-appearance impact:
    which glyphs co-appear in the same papers, weighted by paper impact score.

    Approach: stream papers again, for each paper with 2+ glyphs in top set,
    emit all (glyph_a, glyph_b) pairs with the paper's score.
    """
    log("Phase 5: Building glyph pair impact overlap...")

    # Get top 500 glyphs
    top_glyphs = out_conn.execute(
        "SELECT glyph_id, total_score, n_papers FROM glyph_impact "
        "ORDER BY total_score DESC LIMIT 500"
    ).fetchall()
    top_set = set()
    for r in top_glyphs:
        top_set.add(str(r[0]))
    log(f"  Top {len(top_set):,} glyphs selected")

    # Load glyph total_scores for lookup
    glyph_scores = {}
    for r in out_conn.execute("SELECT glyph_id, total_score FROM glyph_impact").fetchall():
        glyph_scores[r[0]] = r[1]

    # Load paper scores
    log("  Loading paper scores for pair weighting...")
    paper_scores = {}
    rows = scale_conn.execute(
        "SELECT paper_id, score FROM paper_scale"
    ).fetchall()
    for r in rows:
        paper_scores[r[0]] = r[1]
    log(f"  {len(paper_scores):,} paper scores loaded")

    # Accumulate pair stats: (a, b) -> {cooc_count, total_score, max_score}
    pair_stats = defaultdict(lambda: {"cooc": 0, "total": 0.0, "max": 0.0})

    # Stream papers from WT3
    log("  Streaming papers for glyph co-appearance...")
    total_papers = 833030
    last_rowid = 0
    batch_size = 10000
    done = 0
    t0 = time.time()

    while True:
        rows = wt3_conn.execute(
            "SELECT rowid, paper_id, glyphs FROM papers "
            "WHERE rowid > ? AND glyphs IS NOT NULL ORDER BY rowid LIMIT ?",
            (last_rowid, batch_size)
        ).fetchall()

        if not rows:
            break

        for rowid, paper_id, glyphs_json in rows:
            score = paper_scores.get(paper_id)
            if score is None:
                continue

            try:
                glyph_ids = json.loads(glyphs_json)
            except (json.JSONDecodeError, TypeError):
                continue

            if not glyph_ids or len(glyph_ids) < 2:
                continue

            # Filter to top set only
            top_in_paper = sorted(set(str(g) for g in glyph_ids if str(g) in top_set))

            if len(top_in_paper) < 2:
                continue

            # Emit all pairs (sorted to ensure a < b)
            for i in range(len(top_in_paper)):
                for j in range(i + 1, len(top_in_paper)):
                    key = (top_in_paper[i], top_in_paper[j])
                    ps = pair_stats[key]
                    ps["cooc"] += 1
                    ps["total"] += score
                    ps["max"] = max(ps["max"], score)

        last_rowid = rows[-1][0]
        done += len(rows)

        if done % 100000 == 0:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            log(f"  {done:,}/{total_papers:,} ({100*done/total_papers:.0f}%) "
                f"| {rate:,.0f} papers/s | {len(pair_stats):,} pairs")

    elapsed = time.time() - t0
    log(f"  Scanned {done:,} papers in {elapsed:.1f}s, found {len(pair_stats):,} glyph pairs")

    # Write pair table
    out_conn.execute("DROP TABLE IF EXISTS glyph_pair_impact")
    out_conn.execute("""
        CREATE TABLE glyph_pair_impact (
            glyph_a     TEXT,
            glyph_b     TEXT,
            cooc_count  INTEGER,
            cooc_score  REAL,
            max_score   REAL,
            impact_a    REAL,
            impact_b    REAL,
            combined    REAL,
            PRIMARY KEY (glyph_a, glyph_b)
        )
    """)

    inserts = []
    for (a, b), ps in pair_stats.items():
        sa = glyph_scores.get(a, 0)
        sb = glyph_scores.get(b, 0)
        # Combined impact: geometric mean of glyph impacts × log(cooc_count + 1) × avg pair score
        avg_pair_score = ps["total"] / ps["cooc"] if ps["cooc"] else 0
        combined = math.sqrt(sa * sb) * math.log(ps["cooc"] + 1) * (1 + avg_pair_score / 100)
        inserts.append((
            a, b, ps["cooc"], round(ps["total"], 2), round(ps["max"], 2),
            round(sa, 2), round(sb, 2), round(combined, 2)
        ))

    log(f"  Inserting {len(inserts):,} glyph pairs...")
    out_conn.executemany(
        "INSERT OR IGNORE INTO glyph_pair_impact VALUES (?,?,?,?,?,?,?,?)",
        inserts
    )

    out_conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_gpi_combined ON glyph_pair_impact(combined DESC);
        CREATE INDEX IF NOT EXISTS idx_gpi_cooc ON glyph_pair_impact(cooc_count DESC);
        CREATE INDEX IF NOT EXISTS idx_gpi_a ON glyph_pair_impact(glyph_a);
        CREATE INDEX IF NOT EXISTS idx_gpi_b ON glyph_pair_impact(glyph_b);
    """)
    out_conn.commit()
    log(f"  glyph_pair_impact: {len(inserts):,} rows, 4 indexes")


def export_summary(out_conn, glyph_names):
    """Export top glyphs and pairs to JSON."""
    log("Phase 6: Exporting summary JSON...")

    summary = {
        "meta": {
            "description": "Per-glyph (S-2) impact aggregation — ~1.3K glyphs × 833K papers",
            "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "top_glyphs_by_total": [],
        "top_glyphs_by_avg": [],
        "top_glyphs_by_diversity": [],
        "top_extinction_magnets": [],
        "top_glyph_pairs": [],
    }

    # Top 50 by total score
    rows = out_conn.execute("""
        SELECT glyph_id, glyph_name, n_papers, total_score, avg_score, max_score,
               p90_score, n_domains, n_extinctions, n_asteroides,
               domain_diversity, top_domain
        FROM glyph_impact ORDER BY total_score DESC LIMIT 50
    """).fetchall()
    for r in rows:
        summary["top_glyphs_by_total"].append({
            "glyph_id": r[0], "name": r[1], "n_papers": r[2],
            "total": round(r[3], 1), "avg": r[4], "max": r[5], "p90": r[6],
            "n_domains": r[7], "extinctions": r[8], "asteroides": r[9],
            "diversity": r[10], "top_domain": r[11],
        })

    # Top 50 by avg score (min 20 papers — lower bar than concepts since fewer glyphs)
    rows = out_conn.execute("""
        SELECT glyph_id, glyph_name, n_papers, total_score, avg_score, max_score,
               n_domains, n_extinctions, domain_diversity, top_domain
        FROM glyph_impact WHERE n_papers >= 20
        ORDER BY avg_score DESC LIMIT 50
    """).fetchall()
    for r in rows:
        summary["top_glyphs_by_avg"].append({
            "glyph_id": r[0], "name": r[1], "n_papers": r[2],
            "total": round(r[3], 1), "avg": r[4], "max": r[5],
            "n_domains": r[6], "extinctions": r[7],
            "diversity": r[8], "top_domain": r[9],
        })

    # Top 30 by domain diversity (min 50 papers)
    rows = out_conn.execute("""
        SELECT glyph_id, glyph_name, n_papers, avg_score, n_domains,
               domain_diversity, top_domain
        FROM glyph_impact WHERE n_papers >= 50
        ORDER BY domain_diversity DESC LIMIT 30
    """).fetchall()
    for r in rows:
        summary["top_glyphs_by_diversity"].append({
            "glyph_id": r[0], "name": r[1], "n_papers": r[2], "avg": r[3],
            "n_domains": r[4], "diversity": r[5], "top_domain": r[6],
        })

    # Top 30 extinction magnets
    rows = out_conn.execute("""
        SELECT glyph_id, glyph_name, n_papers, n_extinctions, n_asteroides,
               n_meteorites, avg_score, max_score, top_domain
        FROM glyph_impact WHERE n_extinctions > 0
        ORDER BY n_extinctions DESC, n_asteroides DESC LIMIT 30
    """).fetchall()
    for r in rows:
        summary["top_extinction_magnets"].append({
            "glyph_id": r[0], "name": r[1], "n_papers": r[2],
            "extinctions": r[3], "asteroides": r[4], "meteorites": r[5],
            "avg": r[6], "max": r[7], "top_domain": r[8],
        })

    # Top 100 glyph pairs
    try:
        rows = out_conn.execute("""
            SELECT glyph_a, glyph_b, cooc_count, cooc_score, max_score,
                   impact_a, impact_b, combined
            FROM glyph_pair_impact ORDER BY combined DESC LIMIT 100
        """).fetchall()
        for r in rows:
            name_a = glyph_names.get(int(r[0]), r[0]) if r[0].isdigit() else r[0]
            name_b = glyph_names.get(int(r[1]), r[1]) if r[1].isdigit() else r[1]
            summary["top_glyph_pairs"].append({
                "a": r[0], "b": r[1], "name_a": name_a, "name_b": name_b,
                "cooc_count": r[2], "cooc_score": r[3], "max_score": r[4],
                "impact_a": r[5], "impact_b": r[6], "combined": r[7],
            })
    except sqlite3.OperationalError:
        pass  # table may not exist yet

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log(f"  Exported to {OUTPUT_JSON} ({OUTPUT_JSON.stat().st_size / 1e3:.0f} KB)")


def show_top(out_conn, n):
    """Display top results."""
    print(f"\n{'='*80}")
    print(f"TOP {n} GLYPHS BY TOTAL IMPACT")
    print(f"{'='*80}")
    rows = out_conn.execute("""
        SELECT glyph_id, glyph_name, n_papers, total_score, avg_score, max_score,
               n_domains, n_extinctions, n_asteroides, domain_diversity, top_domain
        FROM glyph_impact ORDER BY total_score DESC LIMIT ?
    """, (n,)).fetchall()
    for i, r in enumerate(rows, 1):
        ext_str = f"ext={r[7]}" if r[7] else ""
        ast_str = f"ast={r[8]}" if r[8] else ""
        flags = " ".join(filter(None, [ext_str, ast_str]))
        name = r[1] if r[1] else r[0]
        print(f"  {i:3d}. {name:20s} (id={r[0]:>5s}) | {r[2]:>6,}p | tot={r[3]:>10,.0f} "
              f"| avg={r[4]:.2f} | max={r[5]:.1f} | {r[6]}dom div={r[9]:.2f} "
              f"| {r[10]:15s} {flags}")

    print(f"\n{'='*80}")
    print(f"TOP {n} GLYPHS BY AVG IMPACT (min 20 papers)")
    print(f"{'='*80}")
    rows = out_conn.execute("""
        SELECT glyph_id, glyph_name, n_papers, avg_score, max_score, n_domains,
               n_extinctions, domain_diversity, top_domain
        FROM glyph_impact WHERE n_papers >= 20
        ORDER BY avg_score DESC LIMIT ?
    """, (n,)).fetchall()
    for i, r in enumerate(rows, 1):
        name = r[1] if r[1] else r[0]
        print(f"  {i:3d}. {name:20s} (id={r[0]:>5s}) | {r[2]:>6,}p | avg={r[3]:.2f} "
              f"| max={r[4]:.1f} | {r[5]}dom div={r[7]:.2f} | {r[8]:15s}")

    # Top glyph pairs
    try:
        print(f"\n{'='*80}")
        print(f"TOP {n} GLYPH PAIRS BY COMBINED IMPACT")
        print(f"{'='*80}")
        rows = out_conn.execute("""
            SELECT glyph_a, glyph_b, cooc_count, cooc_score, combined
            FROM glyph_pair_impact ORDER BY combined DESC LIMIT ?
        """, (n,)).fetchall()
        for i, r in enumerate(rows, 1):
            print(f"  {i:3d}. glyph {r[0]:>5s} x {r[1]:>5s} | cooc={r[2]:>6,} "
                  f"| score={r[3]:>10,.1f} | comb={r[4]:>12,.1f}")
    except sqlite3.OperationalError:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Per-glyph (S-2) impact aggregation"
    )
    parser.add_argument("--top", type=int, default=0,
                        help="Display top N results from existing DB")
    parser.add_argument("--skip-pairs", action="store_true",
                        help="Skip glyph pair calculation (faster)")
    parser.add_argument("--pairs-only", action="store_true",
                        help="Only run glyph pairs (skip phases 1-4)")
    args = parser.parse_args()

    if args.top and OUTPUT_DB.exists():
        out_conn = sqlite3.connect(str(OUTPUT_DB))
        show_top(out_conn, args.top)
        out_conn.close()
        return

    for db_path, name in [(WT3_DB, "wt3.db"), (SCALE_DB, "impact_scale.db")]:
        if not db_path.exists():
            print(f"ERROR: {db_path} not found.")
            sys.exit(1)

    log("=" * 60)
    log("IMPACT GLYPHS — Per-glyph (S-2) impact aggregation")
    log(f"  WT3: {WT3_DB} ({WT3_DB.stat().st_size / 1e9:.1f} GB)")
    log(f"  Scale: {SCALE_DB} ({SCALE_DB.stat().st_size / 1e6:.0f} MB)")
    log("=" * 60)

    t_start = time.time()

    # Load glyph names early
    glyph_names = load_glyph_names()

    wt3_conn = sqlite3.connect(f"file:{WT3_DB}?mode=ro", uri=True)
    scale_conn = sqlite3.connect(f"file:{SCALE_DB}?mode=ro", uri=True)
    out_conn = sqlite3.connect(str(OUTPUT_DB))
    out_conn.execute("PRAGMA journal_mode=WAL")

    # Phase 1-4: Glyph impact scores
    if not args.pairs_only:
        build_glyph_scores(wt3_conn, scale_conn, out_conn, glyph_names)

    # Phase 5: Glyph pair overlap (optional, heavy)
    if not args.skip_pairs:
        build_glyph_pairs(wt3_conn, scale_conn, out_conn)

    # Phase 6: Export JSON
    export_summary(out_conn, glyph_names)

    wt3_conn.close()
    scale_conn.close()
    out_conn.close()

    total_time = time.time() - t_start
    log(f"\nDONE in {total_time:.0f}s ({total_time/60:.1f} min)")
    log(f"Output: {OUTPUT_DB} ({OUTPUT_DB.stat().st_size / 1e6:.1f} MB)")

    # Show results
    out_conn = sqlite3.connect(str(OUTPUT_DB))
    show_top(out_conn, 20)
    out_conn.close()


if __name__ == "__main__":
    main()
