#!/usr/bin/env python3
"""
WT3 — La Bible: unified join of WT1 (concept×concept) + WT2 (paper×glyph×concept)

Streams all chunks into a single SQLite database, one chunk at a time.
CRASH-SAFE: commits + WAL checkpoint after every single chunk.
RESUMABLE: tracks progress per phase+chunk, skips already-done work.

Output: E:/yggdrasil/wt3.db

Tables:
    papers       — paper_id, domain, glyphs (JSON), concepts (JSON)
    bipartite    — glyph_id, concept_id, weight (aggregated across all chunks)
    cooc         — concept_a, concept_b, period, weight (direct upsert, chunk by chunk)
    cooc_global  — concept_a, concept_b, weight (sum across all periods)
    progress     — phase, chunk_id, done_at (crash-resume tracking)

RULE: S-2 and S0 Laplacians stay SEPARATE. The bipartite table is a bridge, NOT a fusion.

Usage:
    python engine/topology/wt3_bible.py              # Full build (resumable)
    python engine/topology/wt3_bible.py --status      # Show progress
    python engine/topology/wt3_bible.py --verify      # Verify integrity
    python engine/topology/wt3_bible.py --reset       # Delete DB and start fresh
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
BIBLE_DIR = Path("E:/yggdrasil")
DB_PATH = BIBLE_DIR / "wt3.db"
LOG_PATH = ROOT / "data" / "bible" / "wt3_log.txt"

WT1_CHUNKS = SCAN_DIR / "chunks"
WT2_CHUNKS = SCAN_DIR / "wt2_chunks"


def log(msg: str):
    """Print and append to log file."""
    print(msg, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def checkpoint(conn: sqlite3.Connection):
    """Force WAL checkpoint to keep WAL file small."""
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def create_db(db_path: Path) -> sqlite3.Connection:
    """Create/open the SQLite database with all tables."""
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64 MB cache
    conn.execute("PRAGMA temp_store=FILE")  # disk temp for large GROUP BYs

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            paper_id   TEXT PRIMARY KEY,
            domain     TEXT,
            glyphs     TEXT,
            concepts   TEXT
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

        CREATE TABLE IF NOT EXISTS progress (
            phase    TEXT,
            chunk_id TEXT,
            done_at  TEXT,
            PRIMARY KEY (phase, chunk_id)
        );

        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    return conn


def is_done(conn: sqlite3.Connection, phase: str, chunk_id: str) -> bool:
    """Check if a phase+chunk was already completed."""
    row = conn.execute(
        "SELECT 1 FROM progress WHERE phase=? AND chunk_id=?",
        (phase, chunk_id),
    ).fetchone()
    return row is not None


def mark_done(conn: sqlite3.Connection, phase: str, chunk_id: str):
    """Mark a phase+chunk as completed, commit, and checkpoint WAL."""
    conn.execute(
        "INSERT OR IGNORE INTO progress (phase, chunk_id, done_at) VALUES (?, ?, ?)",
        (phase, chunk_id, time.strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    checkpoint(conn)


def count_done(conn: sqlite3.Connection, phase: str) -> int:
    """Count how many chunks are done for a phase."""
    return conn.execute(
        "SELECT COUNT(*) FROM progress WHERE phase=?", (phase,)
    ).fetchone()[0]


# ─── Phase 1: Papers ──────────────────────────────────────────────

def ingest_wt2_papers(conn: sqlite3.Connection):
    """Stream WT2 papers.json.gz chunks into the papers table."""
    chunks = sorted([d for d in WT2_CHUNKS.iterdir() if d.is_dir()])
    total = len(chunks)
    already = count_done(conn, "papers")
    if already >= total:
        n = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        log(f"[WT3] Phase 1 papers: already done ({n:,} papers, {already}/{total} chunks)")
        return n

    if already > 0:
        log(f"[WT3] Phase 1 papers: resuming from chunk {already+1}/{total}")

    total_papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    t0 = time.time()
    log(f"[WT3] Ingesting WT2 papers: {total} chunks ({already} already done)")

    for i, chunk_dir in enumerate(chunks, 1):
        chunk_id = chunk_dir.name
        if is_done(conn, "papers", chunk_id):
            continue

        papers_path = chunk_dir / "papers.json.gz"
        if not papers_path.exists():
            mark_done(conn, "papers", chunk_id)
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
        mark_done(conn, "papers", chunk_id)

        elapsed = time.time() - t0
        rate = total_papers / elapsed if elapsed > 0 else 0
        log(f"  [{i}/{total}] {total_papers:,} papers ({rate:,.0f}/s)")

    log(f"[WT3] Papers done: {total_papers:,} in {time.time()-t0:.1f}s")
    return total_papers


# ─── Phase 2: Bipartite ───────────────────────────────────────────

def ingest_wt2_bipartite(conn: sqlite3.Connection):
    """Stream WT2 bipartite.json.gz chunks, aggregating weights. Resumable."""
    chunks = sorted([d for d in WT2_CHUNKS.iterdir() if d.is_dir()])
    total = len(chunks)
    already = count_done(conn, "bipartite")
    if already >= total:
        n = conn.execute("SELECT COUNT(*) FROM bipartite").fetchone()[0]
        log(f"[WT3] Phase 2 bipartite: already done ({n:,} pairs, {already}/{total} chunks)")
        return n

    if already > 0:
        log(f"[WT3] Phase 2 bipartite: resuming from chunk {already+1}/{total}")

    total_pairs = 0
    t0 = time.time()
    log(f"[WT3] Ingesting WT2 bipartite: {total} chunks ({already} already done)")

    for i, chunk_dir in enumerate(chunks, 1):
        chunk_id = chunk_dir.name
        if is_done(conn, "bipartite", chunk_id):
            total_pairs += 1  # approximate, doesn't matter for display
            continue

        bip_path = chunk_dir / "bipartite.json.gz"
        if not bip_path.exists():
            mark_done(conn, "bipartite", chunk_id)
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
        mark_done(conn, "bipartite", chunk_id)

        elapsed = time.time() - t0
        rate = total_pairs / elapsed if elapsed > 0 else 0
        log(f"  [{i}/{total}] {total_pairs:,} pairs ({rate:,.0f}/s)")

    n = conn.execute("SELECT COUNT(*) FROM bipartite").fetchone()[0]
    log(f"[WT3] Bipartite done: {n:,} unique pairs in {time.time()-t0:.1f}s")
    return n


# ─── Phase 3: Cooccurrences — chunk by chunk ─────────────────────

def ingest_wt1_cooc(conn: sqlite3.Connection):
    """Stream WT1 cooc.json.gz chunks directly into cooc table.

    Like bipartite: read each chunk, aggregate in Python dict, upsert into cooc.
    No staging table needed. Chunk by chunk, crash-safe, resumable.
    """
    chunks = sorted([d for d in WT1_CHUNKS.iterdir() if d.is_dir()])
    total = len(chunks)
    already = count_done(conn, "cooc_direct")
    if already >= total:
        n = conn.execute("SELECT COUNT(*) FROM cooc").fetchone()[0]
        log(f"[WT3] Phase 3 cooc: already done ({n:,} pairs, {already}/{total} chunks)")
        return

    if already > 0:
        log(f"[WT3] Phase 3 cooc: resuming from chunk {already+1}/{total}")

    total_upserts = 0
    t0 = time.time()
    log(f"[WT3] Ingesting WT1 cooccurrences (direct): {total} chunks ({already} already done)")

    for i, chunk_dir in enumerate(chunks, 1):
        chunk_id = chunk_dir.name
        if is_done(conn, "cooc_direct", chunk_id):
            continue

        cooc_path = chunk_dir / "cooc.json.gz"
        if not cooc_path.exists():
            mark_done(conn, "cooc_direct", chunk_id)
            continue

        with gzip.open(cooc_path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        # Aggregate in Python dict first: (a, b, period) → sum(weight)
        agg = {}
        for period, pairs in data.items():
            for pair_key, weight in pairs.items():
                parts = pair_key.split("|")
                if len(parts) != 2:
                    continue
                a = int(parts[0])
                b = int(parts[1])
                key = (a, b, period)
                agg[key] = agg.get(key, 0.0) + weight
        del data

        # Upsert into cooc (ON CONFLICT add weight)
        rows = [(a, b, p, w, w) for (a, b, p), w in agg.items()]
        del agg
        conn.executemany(
            """INSERT INTO cooc (concept_a, concept_b, period, weight)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(concept_a, concept_b, period)
               DO UPDATE SET weight = weight + ?""",
            rows,
        )
        total_upserts += len(rows)
        del rows
        mark_done(conn, "cooc_direct", chunk_id)

        elapsed = time.time() - t0
        rate = total_upserts / elapsed if elapsed > 0 else 0
        if i % 10 == 0 or i == total or i <= 3:
            log(f"  [{i}/{total}] {total_upserts:,} upserts ({rate:,.0f}/s)")

    n = conn.execute("SELECT COUNT(*) FROM cooc").fetchone()[0]
    log(f"[WT3] Cooc done: {n:,} unique pairs×periods in {time.time()-t0:.1f}s")


# ─── Phase 4: cooc_global ─────────────────────────────────────────

def build_cooc_global(conn: sqlite3.Connection):
    """Build cooc_global by aggregating cooc across periods.

    This is a much smaller operation than the raw insert (cooc has ~108M unique
    pairs×periods, cooc_global collapses periods → fewer rows).
    Done in batches by concept_a ranges to stay crash-safe.
    """
    already = count_done(conn, "cooc_global")
    if already > 0:
        n = conn.execute("SELECT COUNT(*) FROM cooc_global").fetchone()[0]
        log(f"[WT3] Phase 4 cooc_global: already done ({n:,} pairs)")
        return n

    log("[WT3] Phase 4: Building cooc_global from cooc...")
    t0 = time.time()

    # Get range of concept_a values
    row = conn.execute("SELECT MIN(concept_a), MAX(concept_a) FROM cooc").fetchone()
    if row[0] is None:
        log("[WT3] cooc is empty, skipping cooc_global")
        mark_done(conn, "cooc_global", "all")
        return 0

    min_a, max_a = row
    batch_size = 1000  # process 1000 concept_a values at a time
    total_inserted = 0

    for start in range(min_a, max_a + 1, batch_size):
        end = start + batch_size
        conn.execute(
            """INSERT OR IGNORE INTO cooc_global (concept_a, concept_b, weight)
               SELECT concept_a, concept_b, SUM(weight)
               FROM cooc
               WHERE concept_a >= ? AND concept_a < ?
               GROUP BY concept_a, concept_b""",
            (start, end),
        )
        conn.commit()
        checkpoint(conn)
        batch_count = conn.execute(
            "SELECT changes()"
        ).fetchone()[0]
        total_inserted += batch_count

        if (start - min_a) % (batch_size * 50) == 0:
            elapsed = time.time() - t0
            log(f"  concept_a {start}-{end}: {total_inserted:,} total ({elapsed:.0f}s)")

    mark_done(conn, "cooc_global", "all")
    n = conn.execute("SELECT COUNT(*) FROM cooc_global").fetchone()[0]
    log(f"[WT3] cooc_global done: {n:,} pairs in {time.time()-t0:.1f}s")
    return n


# ─── Phase 5: Indexes ─────────────────────────────────────────────

def create_indexes(conn: sqlite3.Connection):
    """Create indexes after bulk insert for performance."""
    if is_done(conn, "indexes", "all"):
        log("[WT3] Phase 5 indexes: already done")
        return

    log("[WT3] Phase 5: Creating indexes...")
    t0 = time.time()
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_papers_domain ON papers(domain)",
        "CREATE INDEX IF NOT EXISTS idx_bipartite_glyph ON bipartite(glyph_id)",
        "CREATE INDEX IF NOT EXISTS idx_bipartite_concept ON bipartite(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_cooc_period ON cooc(period)",
        "CREATE INDEX IF NOT EXISTS idx_cooc_a ON cooc(concept_a)",
        "CREATE INDEX IF NOT EXISTS idx_cooc_b ON cooc(concept_b)",
        "CREATE INDEX IF NOT EXISTS idx_cooc_global_a ON cooc_global(concept_a)",
        "CREATE INDEX IF NOT EXISTS idx_cooc_global_b ON cooc_global(concept_b)",
    ]
    for idx_sql in indexes:
        idx_name = idx_sql.split("IF NOT EXISTS ")[1].split(" ON")[0]
        log(f"  Creating {idx_name}...")
        conn.execute(idx_sql)
        conn.commit()
        checkpoint(conn)

    mark_done(conn, "indexes", "all")
    log(f"[WT3] Indexes created in {time.time()-t0:.1f}s")


# ─── Phase 6: Meta + cleanup ──────────────────────────────────────

def save_meta(conn: sqlite3.Connection, stats: dict):
    """Save build metadata."""
    for k, v in stats.items():
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (k, json.dumps(v) if not isinstance(v, str) else v),
        )
    conn.commit()


# ─── Commands ──────────────────────────────────────────────────────

def verify(db_path: Path):
    """Verify database integrity and print stats."""
    conn = sqlite3.connect(str(db_path))
    print(f"\n[WT3] Verifying {db_path}")
    print(f"  File size: {db_path.stat().st_size / 1024**2:.0f} MB")

    for table in ["papers", "bipartite", "cooc", "cooc_global"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count:,} rows")

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
    """Show build status with progress details."""
    if not db_path.exists():
        print("[WT3] No database found. Run without --status to build.")
        return

    conn = sqlite3.connect(str(db_path))

    print(f"[WT3] Status: {db_path}")
    print(f"  File size: {db_path.stat().st_size / 1024**2:.0f} MB")

    for table in ["papers", "bipartite", "cooc", "cooc_global", "progress"]:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count:,} rows")
        except sqlite3.OperationalError:
            print(f"  {table}: (not created yet)")

    # Progress by phase
    try:
        phases = conn.execute(
            "SELECT phase, COUNT(*) FROM progress GROUP BY phase ORDER BY phase"
        ).fetchall()
        print(f"\n  Progress:")
        for phase, cnt in phases:
            print(f"    {phase}: {cnt} chunks done")
    except sqlite3.OperationalError:
        pass

    # Meta
    try:
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
        if meta:
            print(f"\n  Meta:")
            for k, v in meta.items():
                print(f"    {k}: {v}")
    except sqlite3.OperationalError:
        pass

    conn.close()


def build():
    """Full build: ingest WT1 + WT2 into SQLite. Fully resumable."""
    BIBLE_DIR.mkdir(parents=True, exist_ok=True)

    # Clear log for fresh run (but not for resume)
    existing_progress = 0
    if DB_PATH.exists():
        tmp = sqlite3.connect(str(DB_PATH))
        try:
            existing_progress = tmp.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
        except sqlite3.OperationalError:
            pass
        tmp.close()

    if existing_progress == 0:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("")

    log(f"[WT3] Building La Bible: {DB_PATH}")
    log(f"  WT1 source: {WT1_CHUNKS}")
    log(f"  WT2 source: {WT2_CHUNKS}")
    if existing_progress > 0:
        log(f"  Resuming: {existing_progress} chunks already done")
    t0 = time.time()

    conn = create_db(DB_PATH)

    # Drop legacy tables from old staging approach
    for old_table in ["cooc_raw", "cooc_staging"]:
        try:
            conn.execute(f"DROP TABLE IF EXISTS {old_table}")
            conn.commit()
        except Exception:
            pass

    # Drop failed index from previous attempt
    try:
        conn.execute("DROP INDEX IF EXISTS idx_staging_a")
        conn.commit()
    except Exception:
        pass

    # Phase 1: WT2 papers
    n_papers = ingest_wt2_papers(conn)

    # Phase 2: WT2 bipartite (resumable, no delete)
    n_bipartite = ingest_wt2_bipartite(conn)

    # Phase 3: WT1 cooccurrences (chunk by chunk, direct upsert, no staging)
    ingest_wt1_cooc(conn)
    n_cooc = conn.execute("SELECT COUNT(*) FROM cooc").fetchone()[0]

    # Phase 4: cooc_global (aggregate from cooc)
    n_global = build_cooc_global(conn)

    # Phase 5: Indexes
    create_indexes(conn)

    # Phase 6: Meta
    total_time = time.time() - t0
    stats = {
        "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_papers": n_papers,
        "total_bipartite_pairs": n_bipartite,
        "total_cooc_unique": conn.execute("SELECT COUNT(*) FROM cooc").fetchone()[0],
        "total_cooc_global": conn.execute("SELECT COUNT(*) FROM cooc_global").fetchone()[0],
        "build_time_sec": round(total_time, 1),
        "wt1_chunks": len(list(WT1_CHUNKS.iterdir())),
        "wt2_chunks": len(list(WT2_CHUNKS.iterdir())),
    }
    save_meta(conn, stats)

    # Done — no VACUUM needed (no staging table bloat)
    conn.close()

    final_size = DB_PATH.stat().st_size / 1024**2
    log(f"\n[WT3] === LA BIBLE EST ÉCRITE ===")
    log(f"  Papers:      {n_papers:,}")
    log(f"  Bipartite:   {n_bipartite:,} glyph×concept pairs")
    log(f"  Cooc:        {stats['total_cooc_unique']:,} unique concept×concept×period")
    log(f"  Cooc global: {n_global:,} unique concept×concept")
    log(f"  Size:        {final_size:.0f} MB")
    log(f"  Time:        {total_time:.0f}s")


def main():
    parser = argparse.ArgumentParser(description="WT3 — La Bible builder")
    parser.add_argument("--status", action="store_true", help="Show build status")
    parser.add_argument("--verify", action="store_true", help="Verify integrity")
    parser.add_argument("--reset", action="store_true", help="Delete DB and start fresh")
    args = parser.parse_args()

    if args.reset:
        for f in [DB_PATH, Path(str(DB_PATH) + "-wal"), Path(str(DB_PATH) + "-shm")]:
            if f.exists():
                f.unlink()
                print(f"  Deleted {f}")
        print("[WT3] Reset complete. Run again to rebuild.")
    elif args.status:
        status(DB_PATH)
    elif args.verify:
        verify(DB_PATH)
    else:
        build()


if __name__ == "__main__":
    main()
