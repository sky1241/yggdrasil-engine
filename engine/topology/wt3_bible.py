#!/usr/bin/env python3
"""
WT3 — La Bible: unified join of WT1 (concept×concept) + WT2 (paper×glyph×concept)

Streams all chunks into a single SQLite database, one chunk at a time
to stay under ~100 MB RAM on a 16 GB machine.

Output: data/bible/wt3.db

Tables:
    papers       — paper_id, domain, glyphs (JSON), concepts (JSON)
    bipartite    — glyph_id, concept_id, weight (aggregated across all chunks)
    cooc         — concept_a, concept_b, period, weight (aggregated across all chunks)
    cooc_global  — concept_a, concept_b, weight (sum across all periods)

Indexes:
    papers: paper_id, domain
    bipartite: glyph_id, concept_id
    cooc: concept_a, concept_b, period
    cooc_global: concept_a, concept_b

RULE: S-2 and S0 Laplacians stay SEPARATE. The bipartite table is a bridge, NOT a fusion.

Usage:
    python engine/topology/wt3_bible.py              # Full build
    python engine/topology/wt3_bible.py --status      # Show progress
    python engine/topology/wt3_bible.py --verify      # Verify integrity
"""
import argparse
import gzip
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCAN_DIR = ROOT / "data" / "scan"
BIBLE_DIR = ROOT / "data" / "bible"
DB_PATH = BIBLE_DIR / "wt3.db"

WT1_CHUNKS = SCAN_DIR / "chunks"
WT2_CHUNKS = SCAN_DIR / "wt2_chunks"


def create_db(db_path: Path) -> sqlite3.Connection:
    """Create the SQLite database with all tables."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64 MB cache
    conn.execute("PRAGMA temp_store=MEMORY")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            paper_id   TEXT PRIMARY KEY,
            domain     TEXT,
            glyphs     TEXT,    -- JSON array of glyph IDs
            concepts   TEXT     -- JSON array of concept IDs
        );

        CREATE TABLE IF NOT EXISTS bipartite (
            glyph_id   INTEGER,
            concept_id INTEGER,
            weight     REAL,
            PRIMARY KEY (glyph_id, concept_id)
        );

        CREATE TABLE IF NOT EXISTS cooc (
            concept_a  INTEGER,
            concept_b  INTEGER,
            period     TEXT,
            weight     REAL,
            PRIMARY KEY (concept_a, concept_b, period)
        );

        CREATE TABLE IF NOT EXISTS cooc_global (
            concept_a  INTEGER,
            concept_b  INTEGER,
            weight     REAL,
            PRIMARY KEY (concept_a, concept_b)
        );

        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    return conn


def ingest_wt2_papers(conn: sqlite3.Connection):
    """Stream WT2 papers.json.gz chunks into the papers table."""
    chunks = sorted([d for d in WT2_CHUNKS.iterdir() if d.is_dir()])
    total = len(chunks)
    total_papers = 0
    t0 = time.time()

    print(f"[WT3] Ingesting WT2 papers: {total} chunks")

    for i, chunk_dir in enumerate(chunks, 1):
        papers_path = chunk_dir / "papers.json.gz"
        if not papers_path.exists():
            continue

        with gzip.open(papers_path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        rows = []
        for paper_id, info in data.items():
            glyphs = json.dumps(info.get("g", []))
            concepts = json.dumps(info.get("c", []))
            domain = info.get("d", "")
            rows.append((paper_id, domain, glyphs, concepts))

        conn.executemany(
            "INSERT OR IGNORE INTO papers (paper_id, domain, glyphs, concepts) VALUES (?, ?, ?, ?)",
            rows,
        )
        total_papers += len(rows)

        if i % 50 == 0 or i == total:
            conn.commit()
            elapsed = time.time() - t0
            rate = total_papers / elapsed if elapsed > 0 else 0
            print(f"  [{i}/{total}] {total_papers:,} papers ({rate:,.0f}/s)")

    conn.commit()
    print(f"[WT3] Papers done: {total_papers:,} in {time.time()-t0:.1f}s")
    return total_papers


def ingest_wt2_bipartite(conn: sqlite3.Connection):
    """Stream WT2 bipartite.json.gz chunks, aggregating weights."""
    chunks = sorted([d for d in WT2_CHUNKS.iterdir() if d.is_dir()])
    total = len(chunks)
    total_pairs = 0
    t0 = time.time()

    print(f"[WT3] Ingesting WT2 bipartite: {total} chunks")

    for i, chunk_dir in enumerate(chunks, 1):
        bip_path = chunk_dir / "bipartite.json.gz"
        if not bip_path.exists():
            continue

        with gzip.open(bip_path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        rows = []
        for pair_key, weight in data.items():
            parts = pair_key.split("|")
            if len(parts) != 2:
                continue
            glyph_id = int(parts[0])
            concept_id = int(parts[1])
            rows.append((glyph_id, concept_id, weight, weight))

        conn.executemany(
            """INSERT INTO bipartite (glyph_id, concept_id, weight)
               VALUES (?, ?, ?)
               ON CONFLICT(glyph_id, concept_id)
               DO UPDATE SET weight = weight + ?""",
            rows,
        )
        total_pairs += len(rows)

        if i % 50 == 0 or i == total:
            conn.commit()
            elapsed = time.time() - t0
            rate = total_pairs / elapsed if elapsed > 0 else 0
            print(f"  [{i}/{total}] {total_pairs:,} pairs ({rate:,.0f}/s)")

    conn.commit()
    print(f"[WT3] Bipartite done: {total_pairs:,} in {time.time()-t0:.1f}s")
    return total_pairs


def ingest_wt1_cooc(conn: sqlite3.Connection):
    """Stream WT1 cooc.json.gz chunks, aggregating by period and globally."""
    chunks = sorted([d for d in WT1_CHUNKS.iterdir() if d.is_dir()])
    total = len(chunks)
    total_pairs = 0
    t0 = time.time()

    print(f"[WT3] Ingesting WT1 cooccurrences: {total} chunks")

    for i, chunk_dir in enumerate(chunks, 1):
        cooc_path = chunk_dir / "cooc.json.gz"
        if not cooc_path.exists():
            continue

        with gzip.open(cooc_path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        cooc_rows = []
        global_rows = []

        for period, pairs in data.items():
            for pair_key, weight in pairs.items():
                parts = pair_key.split("|")
                if len(parts) != 2:
                    continue
                a = int(parts[0])
                b = int(parts[1])
                cooc_rows.append((a, b, period, weight, weight))
                global_rows.append((a, b, weight, weight))

        conn.executemany(
            """INSERT INTO cooc (concept_a, concept_b, period, weight)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(concept_a, concept_b, period)
               DO UPDATE SET weight = weight + ?""",
            cooc_rows,
        )
        conn.executemany(
            """INSERT INTO cooc_global (concept_a, concept_b, weight)
               VALUES (?, ?, ?)
               ON CONFLICT(concept_a, concept_b)
               DO UPDATE SET weight = weight + ?""",
            global_rows,
        )
        total_pairs += len(cooc_rows)

        if i % 50 == 0 or i == total:
            conn.commit()
            elapsed = time.time() - t0
            rate = total_pairs / elapsed if elapsed > 0 else 0
            print(f"  [{i}/{total}] {total_pairs:,} pairs ({rate:,.0f}/s)")

    conn.commit()
    print(f"[WT3] Cooccurrences done: {total_pairs:,} in {time.time()-t0:.1f}s")
    return total_pairs


def create_indexes(conn: sqlite3.Connection):
    """Create indexes after bulk insert for performance."""
    print("[WT3] Creating indexes...")
    t0 = time.time()
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_papers_domain ON papers(domain);
        CREATE INDEX IF NOT EXISTS idx_bipartite_glyph ON bipartite(glyph_id);
        CREATE INDEX IF NOT EXISTS idx_bipartite_concept ON bipartite(concept_id);
        CREATE INDEX IF NOT EXISTS idx_cooc_period ON cooc(period);
        CREATE INDEX IF NOT EXISTS idx_cooc_a ON cooc(concept_a);
        CREATE INDEX IF NOT EXISTS idx_cooc_b ON cooc(concept_b);
        CREATE INDEX IF NOT EXISTS idx_cooc_global_a ON cooc_global(concept_a);
        CREATE INDEX IF NOT EXISTS idx_cooc_global_b ON cooc_global(concept_b);
    """)
    conn.commit()
    print(f"[WT3] Indexes created in {time.time()-t0:.1f}s")


def save_meta(conn: sqlite3.Connection, stats: dict):
    """Save build metadata."""
    for k, v in stats.items():
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (k, json.dumps(v) if not isinstance(v, str) else v),
        )
    conn.commit()


def verify(db_path: Path):
    """Verify database integrity and print stats."""
    conn = sqlite3.connect(str(db_path))
    print(f"\n[WT3] Verifying {db_path}")
    print(f"  File size: {db_path.stat().st_size / 1024**2:.0f} MB")

    for table in ["papers", "bipartite", "cooc", "cooc_global"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count:,} rows")

    # Sample queries
    domains = conn.execute(
        "SELECT domain, COUNT(*) as c FROM papers GROUP BY domain ORDER BY c DESC LIMIT 5"
    ).fetchall()
    print(f"\n  Top domains:")
    for d, c in domains:
        print(f"    {d}: {c:,}")

    top_glyphs = conn.execute(
        "SELECT glyph_id, SUM(weight) as w FROM bipartite GROUP BY glyph_id ORDER BY w DESC LIMIT 5"
    ).fetchall()
    print(f"\n  Top glyphs (by total weight):")
    for g, w in top_glyphs:
        print(f"    glyph {g}: {w:,.2f}")

    top_cooc = conn.execute(
        "SELECT concept_a, concept_b, weight FROM cooc_global ORDER BY weight DESC LIMIT 5"
    ).fetchall()
    print(f"\n  Top concept pairs (global):")
    for a, b, w in top_cooc:
        print(f"    {a}|{b}: {w:,.2f}")

    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"\n  Integrity: {integrity}")
    conn.close()


def status(db_path: Path):
    """Show build status."""
    if not db_path.exists():
        print("[WT3] No database found. Run without --status to build.")
        return

    conn = sqlite3.connect(str(db_path))
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    print(f"[WT3] Status:")
    for k, v in meta.items():
        print(f"  {k}: {v}")
    conn.close()


def build():
    """Full build: ingest WT1 + WT2 into SQLite."""
    BIBLE_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / 1024**2
        print(f"[WT3] WARNING: {DB_PATH} already exists ({size_mb:.0f} MB)")
        print("  Delete it manually to rebuild, or use --verify to check it.")
        return

    print(f"[WT3] Building La Bible: {DB_PATH}")
    print(f"  WT1 source: {WT1_CHUNKS}")
    print(f"  WT2 source: {WT2_CHUNKS}")
    t0 = time.time()

    conn = create_db(DB_PATH)

    # Phase 1: WT2 papers
    n_papers = ingest_wt2_papers(conn)

    # Phase 2: WT2 bipartite
    n_bipartite = ingest_wt2_bipartite(conn)

    # Phase 3: WT1 cooccurrences
    n_cooc = ingest_wt1_cooc(conn)

    # Phase 4: Indexes
    create_indexes(conn)

    # Phase 5: Meta
    total_time = time.time() - t0
    stats = {
        "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_papers": n_papers,
        "total_bipartite_pairs": n_bipartite,
        "total_cooc_pairs": n_cooc,
        "build_time_sec": round(total_time, 1),
        "wt1_chunks": len(list(WT1_CHUNKS.iterdir())),
        "wt2_chunks": len(list(WT2_CHUNKS.iterdir())),
    }
    save_meta(conn, stats)

    # Phase 6: VACUUM to compact
    print("[WT3] Compacting database...")
    conn.execute("VACUUM")
    conn.close()

    final_size = DB_PATH.stat().st_size / 1024**2
    print(f"\n[WT3] === LA BIBLE EST ÉCRITE ===")
    print(f"  Papers:     {n_papers:,}")
    print(f"  Bipartite:  {n_bipartite:,} glyph×concept pairs")
    print(f"  Cooc:       {n_cooc:,} concept×concept×period pairs")
    print(f"  Size:       {final_size:.0f} MB")
    print(f"  Time:       {total_time:.0f}s")


def main():
    parser = argparse.ArgumentParser(description="WT3 — La Bible builder")
    parser.add_argument("--status", action="store_true", help="Show build status")
    parser.add_argument("--verify", action="store_true", help="Verify integrity")
    args = parser.parse_args()

    if args.status:
        status(DB_PATH)
    elif args.verify:
        verify(DB_PATH)
    else:
        build()


if __name__ == "__main__":
    main()
