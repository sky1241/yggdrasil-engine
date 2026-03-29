#!/usr/bin/env python3
"""
Impact Scanner — Échelle d'impact par paper/auteur sur la topologie spectrale.

Lit WT3 chunk par chunk (papers table), croise avec les positions spectrales
(spectral_births.json), et construit une table d'impact:
  - Pour chaque paper: quels concepts il connecte, poids topologique
  - Pour chaque auteur: impact cumulé (somme des papers)
  - Pour chaque année: delta topologique (nouveaux concepts, nouvelles arêtes)

CRASH-SAFE: SQLite WAL + commit par batch.
RESUMABLE: table progress, skip ce qui est fait.

Output: data/impact.db

Tables:
    paper_impact   — paper_id, year, domain, n_concepts, n_glyphs,
                     centroid_x/y/z, spread, weight_sum, author_names (JSON)
    author_impact  — author_name, n_papers, total_weight, avg_spread,
                     centroid_x/y/z, first_year, last_year, domains (JSON)
    year_impact    — year, n_papers, n_new_concepts, n_authors,
                     total_weight, centroid_x/y/z
    progress       — batch_id, done_at

Usage:
    python engine/topology/impact_scanner.py              # Full build
    python engine/topology/impact_scanner.py --status     # Show progress
    python engine/topology/impact_scanner.py --batch-size 5000
"""
import argparse
import json
import math
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WT3_PATH = ROOT / "data" / "wt3.db"
SPECTRAL_PATH = ROOT / "data" / "scan" / "spectral_births.json"
OUTPUT_PATH = ROOT / "data" / "impact.db"
LOG_PATH = ROOT / "data" / "impact_log.txt"

BATCH_SIZE = 5000  # papers per batch


def log(msg: str):
    """Print + append to log file."""
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_spectral_positions() -> dict:
    """Load spectral_births.json → {concept_name: {x,y,z,degree,birth_year}, ...}
    Also index by concept id for WT3 lookup (concepts stored as indices).
    """
    log(f"Loading spectral positions from {SPECTRAL_PATH.name}...")
    with open(SPECTRAL_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build index by id (WT3 stores concept indices)
    by_id = {}
    # Build index by name for author lookups
    by_name = {}
    for node in data["nodes"]:
        entry = {
            "x": node["x"],
            "y": node["y"],
            "z": node["z"],
            "degree": node.get("degree", 0),
            "type": node["type"],
            "name": node.get("name", ""),
            "birth_year": node.get("birth_year"),
        }
        by_id[node["id"]] = entry
        if node.get("name"):
            by_name[node["name"]] = entry

    log(f"  Loaded {len(by_id):,} nodes ({data['meta']['n_concepts']:,} concepts, {data['meta']['n_glyphs']:,} glyphs)")
    return by_id, by_name, data["meta"]


def init_output_db(db_path: Path) -> sqlite3.Connection:
    """Create output database with schema."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS paper_impact (
            paper_id    TEXT PRIMARY KEY,
            year        INTEGER,
            domain      TEXT,
            n_concepts  INTEGER,
            n_glyphs    INTEGER,
            centroid_x  REAL,
            centroid_y  REAL,
            centroid_z  REAL,
            spread      REAL,
            weight_pop  REAL,
            weight_rare REAL,
            spread_rare REAL,
            author_names TEXT
        );

        CREATE TABLE IF NOT EXISTS year_impact (
            year        INTEGER PRIMARY KEY,
            n_papers    INTEGER,
            n_concepts_seen INTEGER,
            n_authors   INTEGER,
            total_weight_pop  REAL,
            total_weight_rare REAL,
            avg_spread_rare   REAL,
            centroid_x  REAL,
            centroid_y  REAL,
            centroid_z  REAL
        );

        CREATE TABLE IF NOT EXISTS author_impact (
            author_name TEXT PRIMARY KEY,
            n_papers    INTEGER,
            total_weight_pop  REAL,
            total_weight_rare REAL,
            avg_spread_rare   REAL,
            centroid_x  REAL,
            centroid_y  REAL,
            centroid_z  REAL,
            first_year  INTEGER,
            last_year   INTEGER,
            domains     TEXT
        );

        CREATE TABLE IF NOT EXISTS progress (
            batch_id    INTEGER PRIMARY KEY,
            n_papers    INTEGER,
            done_at     TEXT
        );
    """)
    conn.commit()
    return conn


def get_last_batch(out_conn: sqlite3.Connection) -> int:
    """Get last completed batch ID for resume."""
    row = out_conn.execute("SELECT MAX(batch_id) FROM progress").fetchone()
    return row[0] if row[0] is not None else -1


def compute_paper_impact(concepts_idx: list, glyphs_list: list,
                         positions: dict) -> dict:
    """Compute impact metrics for a single paper.

    Two metrics:
    - weight_pop = sum(degree) — popularity proxy (how famous are the concepts)
    - weight_rare = sum(1/log(degree+1)) — rarity signal (rare concepts amplified)
    - spread = unweighted RMS from centroid
    - spread_rare = rarity-weighted RMS from centroid (the real impact metric)

    A paper that touches rare, spectrally distant concepts = high spread_rare = big meteorite.
    A paper that touches the same 5 popular concepts everyone uses = low spread_rare = pebble.
    """
    pts = []
    weight_pop = 0.0
    weight_rare = 0.0

    for cidx in concepts_idx:
        if cidx in positions:
            p = positions[cidx]
            deg = max(p["degree"], 1)
            rarity = 1.0 / math.log(deg + 1)
            pts.append((p["x"], p["y"], p["z"], deg, rarity))
            weight_pop += deg
            weight_rare += rarity

    if not pts:
        return {
            "centroid_x": 0, "centroid_y": 0, "centroid_z": 0,
            "spread": 0, "weight_pop": 0, "weight_rare": 0, "spread_rare": 0,
        }

    n = len(pts)

    # Rarity-weighted centroid (rare concepts pull harder)
    cx = sum(p[0] * p[4] for p in pts) / weight_rare
    cy = sum(p[1] * p[4] for p in pts) / weight_rare
    cz = sum(p[2] * p[4] for p in pts) / weight_rare

    # Unweighted spread
    if n > 1:
        spread = math.sqrt(
            sum((p[0]-cx)**2 + (p[1]-cy)**2 + (p[2]-cz)**2 for p in pts) / n
        )
    else:
        spread = 0.0

    # Rarity-weighted spread (the real metric)
    if n > 1:
        spread_rare = math.sqrt(
            sum(p[4] * ((p[0]-cx)**2 + (p[1]-cy)**2 + (p[2]-cz)**2)
                for p in pts) / weight_rare
        )
    else:
        spread_rare = 0.0

    return {
        "centroid_x": round(cx, 5),
        "centroid_y": round(cy, 5),
        "centroid_z": round(cz, 5),
        "spread": round(spread, 5),
        "weight_pop": round(weight_pop, 2),
        "weight_rare": round(weight_rare, 5),
        "spread_rare": round(spread_rare, 5),
    }


def scan_papers(wt3_conn: sqlite3.Connection, out_conn: sqlite3.Connection,
                positions: dict, batch_size: int):
    """Scan WT3 papers table batch by batch, compute impact, write to output.

    Uses cursor-based pagination (WHERE rowid > last_rowid) instead of OFFSET
    to avoid O(N²) slowdown on the 78GB database.
    """

    # Resume: find the last paper_id we processed
    last_paper = out_conn.execute(
        "SELECT paper_id FROM paper_impact ORDER BY rowid DESC LIMIT 1"
    ).fetchone()

    # Get the rowid of the last processed paper in WT3
    if last_paper:
        row = wt3_conn.execute(
            "SELECT rowid FROM papers WHERE paper_id = ?", (last_paper[0],)
        ).fetchone()
        last_rowid = row[0] if row else 0
    else:
        last_rowid = 0

    # Count total and remaining
    total = wt3_conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    done_count = out_conn.execute("SELECT COUNT(*) FROM paper_impact").fetchone()[0]
    remaining = total - done_count

    log(f"Total papers in WT3: {total:,} | Already done: {done_count:,} | "
        f"Remaining: {remaining:,} | Cursor at rowid {last_rowid}")

    if remaining <= 0:
        log("All papers already processed.")
        return

    batch_id = out_conn.execute("SELECT COALESCE(MAX(batch_id), -1) + 1 FROM progress").fetchone()[0]
    t0 = time.time()
    papers_this_run = 0

    while True:
        rows = wt3_conn.execute(
            "SELECT rowid, paper_id, domain, year, concepts, glyphs, authors "
            "FROM papers WHERE rowid > ? ORDER BY rowid LIMIT ?",
            (last_rowid, batch_size)
        ).fetchall()

        if not rows:
            break

        inserts = []
        for row in rows:
            rowid, paper_id, domain, year, concepts_json, glyphs_json, authors_json = row

            # Parse concepts
            try:
                concepts_idx = json.loads(concepts_json) if concepts_json else []
            except (json.JSONDecodeError, TypeError):
                concepts_idx = []

            # Parse glyphs
            try:
                glyphs_list = json.loads(glyphs_json) if glyphs_json else []
            except (json.JSONDecodeError, TypeError):
                glyphs_list = []

            # Parse authors
            try:
                authors = json.loads(authors_json) if authors_json else []
                author_names = [a.get("name", "") for a in authors if isinstance(a, dict)]
            except (json.JSONDecodeError, TypeError):
                author_names = []

            # Compute impact
            impact = compute_paper_impact(concepts_idx, glyphs_list, positions)

            inserts.append((
                paper_id, year, domain,
                len(concepts_idx), len(glyphs_list),
                impact["centroid_x"], impact["centroid_y"], impact["centroid_z"],
                impact["spread"], impact["weight_pop"], impact["weight_rare"],
                impact["spread_rare"],
                json.dumps(author_names, ensure_ascii=False) if author_names else None
            ))

        # Batch insert
        out_conn.executemany(
            "INSERT OR IGNORE INTO paper_impact "
            "(paper_id, year, domain, n_concepts, n_glyphs, "
            " centroid_x, centroid_y, centroid_z, spread, weight_pop, "
            " weight_rare, spread_rare, author_names) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            inserts
        )

        # Update cursor
        last_rowid = rows[-1][0]

        # Mark batch done
        out_conn.execute(
            "INSERT INTO progress (batch_id, n_papers, done_at) VALUES (?, ?, ?)",
            (batch_id, len(rows), time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        out_conn.commit()

        papers_this_run += len(rows)
        total_done = done_count + papers_this_run
        elapsed = time.time() - t0
        rate = papers_this_run / elapsed if elapsed > 0 else 0
        eta = (total - total_done) / rate if rate > 0 else 0
        log(f"  Batch {batch_id}: {total_done:,}/{total:,} ({100*total_done/total:.1f}%) "
            f"| {rate:.0f} papers/s | ETA {eta/60:.1f}min")

        batch_id += 1

    log(f"Paper scan DONE: {done_count + papers_this_run:,} papers "
        f"({papers_this_run:,} this run) in {time.time()-t0:.1f}s")


def build_year_impact(out_conn: sqlite3.Connection):
    """Aggregate paper_impact → year_impact."""
    log("Building year_impact...")
    out_conn.execute("DELETE FROM year_impact")
    out_conn.execute("""
        INSERT INTO year_impact (year, n_papers, n_concepts_seen, n_authors,
                                 total_weight_pop, total_weight_rare, avg_spread_rare,
                                 centroid_x, centroid_y, centroid_z)
        SELECT
            year,
            COUNT(*) as n_papers,
            SUM(n_concepts) as n_concepts_seen,
            0,
            SUM(weight_pop),
            SUM(weight_rare),
            AVG(spread_rare),
            AVG(centroid_x),
            AVG(centroid_y),
            AVG(centroid_z)
        FROM paper_impact
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY year
    """)
    n = out_conn.execute("SELECT COUNT(*) FROM year_impact").fetchone()[0]
    out_conn.commit()
    log(f"  {n} years indexed")


def build_author_impact(out_conn: sqlite3.Connection):
    """Aggregate paper_impact → author_impact (explode author_names JSON)."""
    log("Building author_impact...")
    out_conn.execute("DELETE FROM author_impact")

    # Read all papers with authors
    rows = out_conn.execute(
        "SELECT paper_id, year, domain, n_concepts, centroid_x, centroid_y, centroid_z, "
        "spread_rare, weight_pop, weight_rare, author_names FROM paper_impact "
        "WHERE author_names IS NOT NULL"
    ).fetchall()

    log(f"  Processing {len(rows):,} papers with author data...")

    # Accumulate per author
    authors = {}
    for row in rows:
        _, year, domain, n_concepts, cx, cy, cz, spread_r, w_pop, w_rare, names_json = row
        try:
            names = json.loads(names_json)
        except (json.JSONDecodeError, TypeError):
            continue

        for name in names:
            if not name or len(name) < 2:
                continue
            if name not in authors:
                authors[name] = {
                    "n_papers": 0, "w_pop": 0, "w_rare": 0,
                    "spreads_rare": [],
                    "cx": [], "cy": [], "cz": [],
                    "years": [], "domains": set()
                }
            a = authors[name]
            a["n_papers"] += 1
            a["w_pop"] += w_pop or 0
            a["w_rare"] += w_rare or 0
            a["spreads_rare"].append(spread_r or 0)
            a["cx"].append(cx or 0)
            a["cy"].append(cy or 0)
            a["cz"].append(cz or 0)
            if year:
                a["years"].append(year)
            if domain:
                a["domains"].add(domain)

    # Insert
    inserts = []
    for name, a in authors.items():
        n = a["n_papers"]
        inserts.append((
            name, n,
            round(a["w_pop"], 2),
            round(a["w_rare"], 5),
            round(sum(a["spreads_rare"]) / n, 5) if n else 0,
            round(sum(a["cx"]) / n, 5) if n else 0,
            round(sum(a["cy"]) / n, 5) if n else 0,
            round(sum(a["cz"]) / n, 5) if n else 0,
            min(a["years"]) if a["years"] else None,
            max(a["years"]) if a["years"] else None,
            json.dumps(sorted(a["domains"]), ensure_ascii=False)
        ))

    out_conn.executemany(
        "INSERT OR IGNORE INTO author_impact "
        "(author_name, n_papers, total_weight_pop, total_weight_rare, avg_spread_rare, "
        " centroid_x, centroid_y, centroid_z, first_year, last_year, domains) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        inserts
    )
    out_conn.commit()
    log(f"  {len(inserts):,} authors indexed")


def build_indexes(out_conn: sqlite3.Connection):
    """Create indexes for fast lookups."""
    log("Building indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_paper_year ON paper_impact(year)",
        "CREATE INDEX IF NOT EXISTS idx_paper_domain ON paper_impact(domain)",
        "CREATE INDEX IF NOT EXISTS idx_paper_wpop ON paper_impact(weight_pop DESC)",
        "CREATE INDEX IF NOT EXISTS idx_paper_wrare ON paper_impact(weight_rare DESC)",
        "CREATE INDEX IF NOT EXISTS idx_paper_spread ON paper_impact(spread_rare DESC)",
        "CREATE INDEX IF NOT EXISTS idx_author_wrare ON author_impact(total_weight_rare DESC)",
        "CREATE INDEX IF NOT EXISTS idx_author_spread ON author_impact(avg_spread_rare DESC)",
        "CREATE INDEX IF NOT EXISTS idx_author_papers ON author_impact(n_papers DESC)",
    ]
    for idx in indexes:
        out_conn.execute(idx)
    out_conn.commit()
    log("  Indexes done")


def show_status(out_conn: sqlite3.Connection):
    """Show current progress."""
    papers = out_conn.execute("SELECT COUNT(*) FROM paper_impact").fetchone()[0]
    authors = out_conn.execute("SELECT COUNT(*) FROM author_impact").fetchone()[0]
    years = out_conn.execute("SELECT COUNT(*) FROM year_impact").fetchone()[0]
    batches = out_conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
    last = out_conn.execute("SELECT done_at FROM progress ORDER BY batch_id DESC LIMIT 1").fetchone()

    print(f"=== Impact Scanner Status ===")
    print(f"Papers:  {papers:,}")
    print(f"Authors: {authors:,}")
    print(f"Years:   {years:,}")
    print(f"Batches: {batches:,}")
    if last:
        print(f"Last:    {last[0]}")


def show_top(out_conn: sqlite3.Connection, n: int = 20):
    """Show top authors by rarity-weighted impact."""
    print(f"\n=== Top {n} Authors by RARITY impact (rare concepts = high score) ===")
    rows = out_conn.execute(
        "SELECT author_name, n_papers, total_weight_rare, avg_spread_rare, "
        "first_year, last_year "
        "FROM author_impact WHERE n_papers >= 10 "
        "ORDER BY total_weight_rare DESC LIMIT ?", (n,)
    ).fetchall()
    for i, r in enumerate(rows, 1):
        print(f"  {i:2d}. {r[0][:40]:40s} | {r[1]:4d} papers | rare_w {r[2]:8.1f} "
              f"| spread {r[3]:.3f} | {r[4]}-{r[5]}")

    print(f"\n=== Top {n} Authors by SPREAD (widest spectral footprint, min 30 papers) ===")
    rows = out_conn.execute(
        "SELECT author_name, n_papers, total_weight_rare, avg_spread_rare, "
        "first_year, last_year "
        "FROM author_impact WHERE n_papers >= 30 "
        "ORDER BY avg_spread_rare DESC LIMIT ?", (n,)
    ).fetchall()
    for i, r in enumerate(rows, 1):
        print(f"  {i:2d}. {r[0][:40]:40s} | {r[1]:4d} papers | rare_w {r[2]:8.1f} "
              f"| spread {r[3]:.3f} | {r[4]}-{r[5]}")


def main():
    parser = argparse.ArgumentParser(description="Impact Scanner — build impact tables from WT3 + spectral positions")
    parser.add_argument("--status", action="store_true", help="Show progress")
    parser.add_argument("--top", type=int, default=0, help="Show top N authors")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help=f"Papers per batch (default {BATCH_SIZE})")
    args = parser.parse_args()

    if args.status or args.top:
        if not OUTPUT_PATH.exists():
            print("No impact.db found. Run without --status first.")
            return
        out_conn = sqlite3.connect(str(OUTPUT_PATH))
        if args.status:
            show_status(out_conn)
        if args.top:
            show_top(out_conn, args.top)
        out_conn.close()
        return

    # Full build
    log("=" * 60)
    log("IMPACT SCANNER — Building impact tables")
    log(f"  WT3:      {WT3_PATH} ({WT3_PATH.stat().st_size / 1e9:.1f} GB)")
    log(f"  Spectral: {SPECTRAL_PATH.name}")
    log(f"  Output:   {OUTPUT_PATH}")
    log("=" * 60)

    # Load positions
    positions, names, meta = load_spectral_positions()

    # Connect databases
    wt3_conn = sqlite3.connect(str(WT3_PATH))
    wt3_conn.execute("PRAGMA journal_mode=WAL")
    wt3_conn.execute("PRAGMA cache_size=-64000")

    out_conn = init_output_db(OUTPUT_PATH)

    # Phase 1: Scan papers
    scan_papers(wt3_conn, out_conn, positions, args.batch_size)

    # Phase 2: Aggregate by year
    build_year_impact(out_conn)

    # Phase 3: Aggregate by author
    build_author_impact(out_conn)

    # Phase 4: Indexes
    build_indexes(out_conn)

    # Final stats
    show_status(out_conn)

    wt3_conn.close()
    out_conn.close()

    log("DONE.")
    log(f"Output: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
