#!/usr/bin/env python3
"""
Impact Concepts — Per-concept impact aggregation.

For each of the 65,026 concepts, compute:
  - How many papers touch it, and their aggregate impact scores
  - Temporal evolution: impact curve per concept over decades/years
  - Which authors contributed most impact to this concept
  - Cross-domain reach: how many different domains touch this concept
  - Rarity-weighted impact: rare concepts that attract high-impact papers = structural bridges

This is the BIG calculation: 6.2M bipartite edges × 833K paper scores.

Input: data/impact.db + data/impact_scale.db + data/wt3.db (bipartite table)
Output: data/impact_concepts.db + data/impact_concepts.json

Usage:
    python engine/topology/impact_concepts.py
    python engine/topology/impact_concepts.py --top 30
"""
import argparse
import json
import math
import os
import sqlite3
import sys
import time
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
WT3_DB = ROOT / "data" / "wt3.db"
IMPACT_DB = ROOT / "data" / "impact.db"
SCALE_DB = ROOT / "data" / "impact_scale.db"
OUTPUT_DB = ROOT / "data" / "impact_concepts.db"
OUTPUT_JSON = ROOT / "data" / "impact_concepts.json"


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def build_concept_scores(wt3_conn, scale_conn, out_conn):
    """
    Join bipartite (paper_id, concept_id) with paper_scale (paper_id → score)
    to compute per-concept impact stats.

    This processes ~6.2M bipartite edges.
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

    # Also load author info per paper from impact.db
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

    # Phase 3: Stream bipartite edges from WT3 and aggregate per concept
    log("Phase 3: Streaming bipartite edges from WT3...")

    # concept_id -> stats accumulator
    concepts = {}

    # Time windows for temporal curve
    def year_to_window(y):
        if y is None:
            return None
        if y < 1950:
            return f"{(y // 50) * 50}s"
        if y < 1990:
            return f"{(y // 10) * 10}s"
        return str(y)

    # The paper→concept link is in papers.concepts (JSON list of concept indices)
    # Stream papers from WT3 and parse each one's concepts
    # Skip COUNT(*) on 78GB — use known total from WT3 build (833K papers)
    total_papers = 833030  # known from WT3 meta
    log(f"  Expected papers: ~{total_papers:,} (streaming from WT3)")

    last_rowid = 0
    batch_size = 10000
    done = 0
    total_edges = 0
    t0 = time.time()

    while True:
        rows = wt3_conn.execute(
            "SELECT rowid, paper_id, concepts FROM papers "
            "WHERE rowid > ? AND concepts IS NOT NULL ORDER BY rowid LIMIT ?",
            (last_rowid, batch_size)
        ).fetchall()

        if not rows:
            break

        for rowid, paper_id, concepts_json in rows:
            ps = paper_scores.get(paper_id)
            if ps is None:
                continue

            try:
                concept_ids = json.loads(concepts_json)
            except (json.JSONDecodeError, TypeError):
                continue

            score = ps["score"]
            tier = ps["tier"]
            dom = ps["domain"]
            year = ps["year"]
            z_sp = ps["z_spread"]
            w = year_to_window(year)
            authors = paper_authors.get(paper_id, [])

            for concept_id in concept_ids:
                cid = str(concept_id)  # normalize to string
                total_edges += 1

                if cid not in concepts:
                    concepts[cid] = {
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

                c = concepts[cid]
                c["total_score"] += score
                c["max_score"] = max(c["max_score"], score)
                c["n_papers"] += 1
                c["tiers"][tier] = c["tiers"].get(tier, 0) + 1

                if len(c["scores"]) < 10000:
                    c["scores"].append(score)

                c["z_spreads"].append(z_sp)

                if dom:
                    c["domains"][dom] = c["domains"].get(dom, 0) + 1

                if w:
                    if w not in c["windows"]:
                        c["windows"][w] = {"n": 0, "total": 0.0, "max": 0.0}
                    cw = c["windows"][w]
                    cw["n"] += 1
                    cw["total"] += score
                    cw["max"] = max(cw["max"], score)

                for author in authors[:10]:
                    if not author or len(author) < 2:
                        continue
                    if author not in c["top_authors"]:
                        c["top_authors"][author] = {"n": 0, "total": 0.0, "max": 0.0}
                    ca = c["top_authors"][author]
                    ca["n"] += 1
                    ca["total"] += score
                    ca["max"] = max(ca["max"], score)

        last_rowid = rows[-1][0]
        done += len(rows)

        if done % 50000 == 0:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            log(f"  {done:,}/{total_papers:,} ({100*done/total_papers:.0f}%) "
                f"| {rate:,.0f} papers/s | {total_edges:,} edges | {len(concepts):,} concepts")

    elapsed = time.time() - t0
    log(f"  Processed {done:,} papers, {total_edges:,} edges in {elapsed:.1f}s")
    log(f"  {len(concepts):,} concepts with impact data")

    # Phase 4: Write to SQLite
    log("Phase 4: Writing concept_impact table...")

    out_conn.execute("DROP TABLE IF EXISTS concept_impact")
    out_conn.execute("""
        CREATE TABLE concept_impact (
            concept_id      TEXT PRIMARY KEY,
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
    for cid, c in concepts.items():
        n = c["n_papers"]
        avg = c["total_score"] / n if n else 0

        # P90
        scores_sorted = sorted(c["scores"])
        p90_idx = int(len(scores_sorted) * 0.9)
        p90 = scores_sorted[p90_idx] if scores_sorted else 0

        # Domain diversity (Shannon entropy normalized)
        dom_total = sum(c["domains"].values())
        n_doms = len(c["domains"])
        if n_doms > 1 and dom_total > 0:
            entropy = -sum(
                (cnt / dom_total) * math.log(cnt / dom_total)
                for cnt in c["domains"].values()
            )
            max_entropy = math.log(n_doms)
            diversity = entropy / max_entropy if max_entropy > 0 else 0
        else:
            diversity = 0

        top_dom = max(c["domains"].items(), key=lambda x: x[1])[0] if c["domains"] else ""

        # Top 5 authors by total impact on this concept
        top_auth = sorted(c["top_authors"].items(),
                          key=lambda x: x[1]["total"], reverse=True)[:5]
        top_auth_list = [{"name": a, "n": s["n"], "total": round(s["total"], 1),
                          "max": round(s["max"], 2)} for a, s in top_auth]

        # Temporal curve (sorted by window)
        curve = sorted(c["windows"].items())
        curve_list = [{"window": w, "n": s["n"],
                       "avg": round(s["total"] / s["n"], 2) if s["n"] else 0,
                       "max": round(s["max"], 2)} for w, s in curve]

        avg_z = sum(c["z_spreads"]) / len(c["z_spreads"]) if c["z_spreads"] else 0

        inserts.append((
            cid, n, round(c["total_score"], 2), round(avg, 3),
            round(c["max_score"], 2), round(p90, 2),
            n_doms,
            c["tiers"].get("extinction", 0),
            c["tiers"].get("asteroide", 0),
            c["tiers"].get("meteorite", 0),
            round(avg_z, 3),
            round(diversity, 4),
            top_dom,
            json.dumps(top_auth_list, ensure_ascii=False),
            json.dumps(curve_list, ensure_ascii=False),
            json.dumps(c["tiers"], ensure_ascii=False),
        ))

    log(f"  Inserting {len(inserts):,} concepts...")
    out_conn.executemany(
        "INSERT OR IGNORE INTO concept_impact VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        inserts
    )

    out_conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_ci_total ON concept_impact(total_score DESC);
        CREATE INDEX IF NOT EXISTS idx_ci_avg ON concept_impact(avg_score DESC);
        CREATE INDEX IF NOT EXISTS idx_ci_max ON concept_impact(max_score DESC);
        CREATE INDEX IF NOT EXISTS idx_ci_papers ON concept_impact(n_papers DESC);
        CREATE INDEX IF NOT EXISTS idx_ci_ext ON concept_impact(n_extinctions DESC);
        CREATE INDEX IF NOT EXISTS idx_ci_diversity ON concept_impact(domain_diversity DESC);
    """)
    out_conn.commit()
    log(f"  concept_impact: {len(inserts):,} rows, 6 indexes")


def build_concept_pairs(wt3_conn, out_conn):
    """
    For the top ~5000 concepts by total_score, compute pairwise impact overlap:
    how many high-impact papers do two concepts share?

    This is the heavy calculation: 5000² / 2 = 12.5M pairs to check.
    Uses cooc_global from WT3 for the edge weights.
    """
    log("Phase 5: Building concept pair impact overlap...")

    # Get top concepts — concept_ids in concept_impact may be strings,
    # but cooc_global uses integers. Build both lookup sets.
    top_concepts = out_conn.execute(
        "SELECT concept_id, total_score, n_papers FROM concept_impact "
        "ORDER BY total_score DESC LIMIT 5000"
    ).fetchall()
    top_set = set()
    for r in top_concepts:
        top_set.add(str(r[0]))  # string version for matching
    log(f"  Top {len(top_set):,} concepts selected")

    # Get cooc_global weights for these pairs from WT3
    out_conn.execute("DROP TABLE IF EXISTS concept_pair_impact")
    out_conn.execute("""
        CREATE TABLE concept_pair_impact (
            concept_a   TEXT,
            concept_b   TEXT,
            cooc_weight REAL,
            impact_a    REAL,
            impact_b    REAL,
            combined    REAL,
            PRIMARY KEY (concept_a, concept_b)
        )
    """)

    # Load concept total_scores for lookup
    concept_scores = {}
    for r in out_conn.execute("SELECT concept_id, total_score FROM concept_impact").fetchall():
        concept_scores[r[0]] = r[1]

    # Stream cooc_global from WT3 — only pairs where BOTH concepts are in top set
    log("  Streaming cooc_global pairs...")
    last_rowid = 0
    batch_size = 200000
    found = 0
    total_cooc = 69440760  # known from WT3 meta
    done = 0
    t0 = time.time()

    while True:
        rows = wt3_conn.execute(
            "SELECT rowid, concept_a, concept_b, weight FROM cooc_global "
            "WHERE rowid > ? ORDER BY rowid LIMIT ?",
            (last_rowid, batch_size)
        ).fetchall()

        if not rows:
            break

        inserts = []
        for rowid, ca, cb, weight in rows:
            ca_s = str(ca)
            cb_s = str(cb)
            if ca_s in top_set and cb_s in top_set:
                sa = concept_scores.get(ca_s, 0)
                sb = concept_scores.get(cb_s, 0)
                # Combined impact: geometric mean of impacts × cooc weight
                combined = math.sqrt(sa * sb) * math.log(weight + 1)
                inserts.append((ca_s, cb_s, weight, round(sa, 2), round(sb, 2), round(combined, 2)))

        if inserts:
            out_conn.executemany(
                "INSERT OR IGNORE INTO concept_pair_impact VALUES (?,?,?,?,?,?)",
                inserts
            )
            found += len(inserts)

        last_rowid = rows[-1][0]
        done += len(rows)

        if done % 2000000 == 0:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            log(f"  {done:,}/{total_cooc:,} ({100*done/total_cooc:.0f}%) "
                f"| {rate:,.0f}/s | {found:,} pairs found")

    out_conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_cpi_combined ON concept_pair_impact(combined DESC);
        CREATE INDEX IF NOT EXISTS idx_cpi_a ON concept_pair_impact(concept_a);
        CREATE INDEX IF NOT EXISTS idx_cpi_b ON concept_pair_impact(concept_b);
    """)
    out_conn.commit()

    elapsed = time.time() - t0
    log(f"  Scanned {done:,} cooc_global rows in {elapsed:.1f}s")
    log(f"  {found:,} high-impact concept pairs stored")


def export_summary(out_conn):
    """Export top concepts and pairs to JSON."""
    log("Phase 6: Exporting summary JSON...")

    summary = {
        "meta": {
            "description": "Per-concept impact aggregation — 65K concepts × 833K papers",
            "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "top_concepts_by_total": [],
        "top_concepts_by_avg": [],
        "top_concepts_by_diversity": [],
        "top_extinction_magnets": [],
        "top_concept_pairs": [],
    }

    # Top 50 by total score
    rows = out_conn.execute("""
        SELECT concept_id, n_papers, total_score, avg_score, max_score,
               p90_score, n_domains, n_extinctions, n_asteroides,
               domain_diversity, top_domain
        FROM concept_impact ORDER BY total_score DESC LIMIT 50
    """).fetchall()
    for r in rows:
        summary["top_concepts_by_total"].append({
            "concept": r[0], "n_papers": r[1], "total": round(r[2], 1),
            "avg": r[3], "max": r[4], "p90": r[5], "n_domains": r[6],
            "extinctions": r[7], "asteroides": r[8],
            "diversity": r[9], "top_domain": r[10],
        })

    # Top 50 by avg score (min 50 papers)
    rows = out_conn.execute("""
        SELECT concept_id, n_papers, total_score, avg_score, max_score,
               n_domains, n_extinctions, domain_diversity, top_domain
        FROM concept_impact WHERE n_papers >= 50
        ORDER BY avg_score DESC LIMIT 50
    """).fetchall()
    for r in rows:
        summary["top_concepts_by_avg"].append({
            "concept": r[0], "n_papers": r[1], "total": round(r[2], 1),
            "avg": r[3], "max": r[4], "n_domains": r[5],
            "extinctions": r[6], "diversity": r[7], "top_domain": r[8],
        })

    # Top 30 by domain diversity (min 100 papers)
    rows = out_conn.execute("""
        SELECT concept_id, n_papers, avg_score, n_domains, domain_diversity, top_domain
        FROM concept_impact WHERE n_papers >= 100
        ORDER BY domain_diversity DESC LIMIT 30
    """).fetchall()
    for r in rows:
        summary["top_concepts_by_diversity"].append({
            "concept": r[0], "n_papers": r[1], "avg": r[2],
            "n_domains": r[3], "diversity": r[4], "top_domain": r[5],
        })

    # Top 30 extinction magnets
    rows = out_conn.execute("""
        SELECT concept_id, n_papers, n_extinctions, n_asteroides, n_meteorites,
               avg_score, max_score, top_domain
        FROM concept_impact WHERE n_extinctions > 0
        ORDER BY n_extinctions DESC, n_asteroides DESC LIMIT 30
    """).fetchall()
    for r in rows:
        summary["top_extinction_magnets"].append({
            "concept": r[0], "n_papers": r[1],
            "extinctions": r[2], "asteroides": r[3], "meteorites": r[4],
            "avg": r[5], "max": r[6], "top_domain": r[7],
        })

    # Top 100 concept pairs
    try:
        rows = out_conn.execute("""
            SELECT concept_a, concept_b, cooc_weight, impact_a, impact_b, combined
            FROM concept_pair_impact ORDER BY combined DESC LIMIT 100
        """).fetchall()
        for r in rows:
            summary["top_concept_pairs"].append({
                "a": r[0], "b": r[1], "cooc": r[2],
                "impact_a": r[3], "impact_b": r[4], "combined": r[5],
            })
    except sqlite3.OperationalError:
        pass  # table may not exist yet

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log(f"  Exported to {OUTPUT_JSON} ({OUTPUT_JSON.stat().st_size / 1e3:.0f} KB)")


def show_top(out_conn, n):
    """Display top results."""
    print(f"\n{'='*80}")
    print(f"TOP {n} CONCEPTS BY TOTAL IMPACT")
    print(f"{'='*80}")
    rows = out_conn.execute("""
        SELECT concept_id, n_papers, total_score, avg_score, max_score,
               n_domains, n_extinctions, n_asteroides, domain_diversity, top_domain
        FROM concept_impact ORDER BY total_score DESC LIMIT ?
    """, (n,)).fetchall()
    for i, r in enumerate(rows, 1):
        ext_str = f"ext={r[6]}" if r[6] else ""
        ast_str = f"ast={r[7]}" if r[7] else ""
        flags = " ".join(filter(None, [ext_str, ast_str]))
        print(f"  {i:3d}. {r[0]:40s} | {r[1]:>6,}p | tot={r[2]:>8,.0f} "
              f"| avg={r[3]:.2f} | max={r[4]:.1f} | {r[5]}dom div={r[8]:.2f} "
              f"| {r[9]:15s} {flags}")

    print(f"\n{'='*80}")
    print(f"TOP {n} CONCEPTS BY AVG IMPACT (min 50 papers)")
    print(f"{'='*80}")
    rows = out_conn.execute("""
        SELECT concept_id, n_papers, avg_score, max_score, n_domains,
               n_extinctions, domain_diversity, top_domain
        FROM concept_impact WHERE n_papers >= 50
        ORDER BY avg_score DESC LIMIT ?
    """, (n,)).fetchall()
    for i, r in enumerate(rows, 1):
        print(f"  {i:3d}. {r[0]:40s} | {r[1]:>6,}p | avg={r[2]:.2f} | max={r[3]:.1f} "
              f"| {r[4]}dom div={r[6]:.2f} | {r[7]:15s}")

    # Top concept pairs
    try:
        print(f"\n{'='*80}")
        print(f"TOP {n} CONCEPT PAIRS BY COMBINED IMPACT")
        print(f"{'='*80}")
        rows = out_conn.execute("""
            SELECT concept_a, concept_b, cooc_weight, combined
            FROM concept_pair_impact ORDER BY combined DESC LIMIT ?
        """, (n,)).fetchall()
        for i, r in enumerate(rows, 1):
            print(f"  {i:3d}. {r[0]:30s} × {r[1]:30s} | cooc={r[2]:>8,.0f} | comb={r[3]:>10,.1f}")
    except sqlite3.OperationalError:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=0)
    parser.add_argument("--skip-pairs", action="store_true",
                        help="Skip concept pair calculation (faster)")
    parser.add_argument("--pairs-only", action="store_true",
                        help="Only run concept pairs (skip phases 1-4)")
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
    log("IMPACT CONCEPTS — Per-concept impact aggregation")
    log(f"  WT3: {WT3_DB} ({WT3_DB.stat().st_size / 1e9:.1f} GB)")
    log(f"  Scale: {SCALE_DB} ({SCALE_DB.stat().st_size / 1e6:.0f} MB)")
    log("=" * 60)

    t_start = time.time()

    wt3_conn = sqlite3.connect(f"file:{WT3_DB}?mode=ro", uri=True)
    scale_conn = sqlite3.connect(f"file:{SCALE_DB}?mode=ro", uri=True)
    out_conn = sqlite3.connect(str(OUTPUT_DB))
    out_conn.execute("PRAGMA journal_mode=WAL")

    # Phase 1-4: Concept impact scores
    if not args.pairs_only:
        build_concept_scores(wt3_conn, scale_conn, out_conn)

    # Phase 5: Concept pair overlap (optional, heavy)
    if not args.skip_pairs:
        build_concept_pairs(wt3_conn, out_conn)

    # Phase 6: Export JSON
    export_summary(out_conn)

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
