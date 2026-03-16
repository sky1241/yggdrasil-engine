#!/usr/bin/env python3
"""
WT3 Enrichissement — Ajouter title, authors, year aux papers existantes.

Scanne le dump OpenAlex works (E:/openalex/data/works/) fichier par fichier.
Pour chaque work ayant un arXiv ID présent dans WT3, extrait:
    title, authors (JSON list), year

CRASH-SAFE: commit SQLite après chaque fichier .gz.
RESUMABLE: tracke chaque fichier dans la table progress (phase='enrich').
PETIT: un fichier .gz à la fois, jamais plus de quelques MB en RAM.

Usage:
    python engine/topology/wt3_enrich.py              # Lance/reprend
    python engine/topology/wt3_enrich.py --status      # Progression
    python engine/topology/wt3_enrich.py --test        # Test sur 5 fichiers
"""
import argparse
import gzip
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "wt3.db"
WORKS_DIR = Path(os.environ.get("YGG_WORKS_DIR", "E:/openalex/data/works"))
LOG_PATH = ROOT / "data" / "wt3_enrich_log.txt"


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line.encode("ascii", errors="replace").decode(), flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── arXiv ID extraction (copié du mapper) ────────────────────────────────────

def extract_arxiv_id(paper):
    ids = paper.get("ids", {})
    if "arxiv" in ids:
        return _clean_arxiv_id(ids["arxiv"])
    for loc in (paper.get("locations") or []):
        landing = loc.get("landing_page_url") or ""
        if "arxiv.org/abs/" in landing:
            return _clean_arxiv_id(landing)
        pdf = loc.get("pdf_url") or ""
        if "arxiv.org/pdf/" in pdf:
            return _clean_arxiv_id(pdf)
    doi = (ids.get("doi") or "")
    if "arxiv" in doi.lower():
        return _clean_arxiv_id(doi)
    return None


def _clean_arxiv_id(raw):
    m = re.search(r'(?:abs|pdf)/(.+?)(?:v\d+)?$', raw)
    if m:
        return m.group(1).strip()
    m = re.search(r'arxiv\.(\d{4}\.\d+)', raw, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'([a-z-]+/\d{7})', raw)
    if m:
        return m.group(1)
    return raw.strip()


# ── Schema migration ─────────────────────────────────────────────────────────

def ensure_columns(conn):
    """Ajoute les colonnes title, authors, year si elles n'existent pas."""
    cur = conn.execute("PRAGMA table_info(papers)")
    existing = {row[1] for row in cur.fetchall()}
    for col, typ in [("title", "TEXT"), ("authors", "TEXT"), ("year", "INTEGER")]:
        if col not in existing:
            conn.execute(f"ALTER TABLE papers ADD COLUMN {col} {typ}")
            log(f"  ALTER TABLE papers ADD {col} {typ}")
    conn.commit()


# ── Discover files ────────────────────────────────────────────────────────────

def discover_gz_files():
    """Liste tous les .gz dans works/, triés."""
    result = []
    for dirpath, _, filenames in os.walk(WORKS_DIR):
        for fn in filenames:
            if fn.endswith(".gz"):
                result.append(os.path.join(dirpath, fn))
    result.sort()
    return result


def get_done_files(conn):
    """Fichiers déjà traités (phase='enrich')."""
    cur = conn.execute(
        "SELECT chunk_id FROM progress WHERE phase='enrich'"
    )
    return {row[0] for row in cur.fetchall()}


# ── Process one file ──────────────────────────────────────────────────────────

def process_one_file(conn, gz_path, paper_ids):
    """
    Lit un .gz, cherche les arXiv papers, UPDATE dans WT3.
    Retourne (matched, total_in_file).
    """
    matched = 0
    total = 0
    batch = []

    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        for line in f:
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            arxiv_id = extract_arxiv_id(rec)
            if arxiv_id is None or arxiv_id not in paper_ids:
                continue

            # Extraire metadata
            title = rec.get("title") or rec.get("display_name") or ""
            year = rec.get("publication_year")
            auths = rec.get("authorships") or []
            author_list = []
            for a in auths:
                author = a.get("author", {}) or {}
                name = a.get("raw_author_name") or author.get("display_name") or ""
                insts = []
                for inst in (a.get("institutions") or []):
                    iname = inst.get("display_name")
                    if iname:
                        insts.append(iname)
                if name:
                    entry = {"name": name}
                    if insts:
                        entry["institutions"] = insts
                    author_list.append(entry)

            authors_json = json.dumps(author_list, ensure_ascii=False)
            batch.append((title, authors_json, year, arxiv_id))
            matched += 1

    # Batch UPDATE
    if batch:
        conn.executemany(
            "UPDATE papers SET title=?, authors=?, year=? WHERE paper_id=?",
            batch
        )

    return matched, total


# ── Main ──────────────────────────────────────────────────────────────────────

def run(test_mode=False):
    log("=" * 60)
    log("  WT3 ENRICH — ajout title/authors/year")
    log("=" * 60)

    if not DB_PATH.exists():
        log(f"ERREUR: {DB_PATH} introuvable")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")

    # 1) Migration schema
    ensure_columns(conn)

    # 2) Charger tous les paper_ids en mémoire
    log("  Chargement des paper_ids depuis WT3...")
    cur = conn.execute("SELECT paper_id FROM papers")
    paper_ids = {row[0] for row in cur}
    log(f"  {len(paper_ids):,} paper_ids chargés")

    # 3) Lister les fichiers
    gz_files = discover_gz_files()
    done_files = get_done_files(conn)
    todo = [f for f in gz_files if f not in done_files]
    log(f"  {len(gz_files):,} fichiers total, {len(done_files):,} déjà faits, {len(todo):,} restants")

    if test_mode:
        todo = todo[:5]
        log(f"  MODE TEST: {len(todo)} fichiers seulement")

    if not todo:
        log("  Rien à faire!")
        show_status(conn)
        conn.close()
        return

    # 4) Scanner fichier par fichier
    t0 = time.time()
    total_matched = 0
    total_papers = 0

    for i, gz_path in enumerate(todo):
        t1 = time.time()
        matched, n_papers = process_one_file(conn, gz_path, paper_ids)
        total_matched += matched
        total_papers += n_papers

        # Marquer comme fait
        conn.execute(
            "INSERT OR IGNORE INTO progress (phase, chunk_id, done_at) VALUES (?, ?, datetime('now'))",
            ("enrich", gz_path)
        )
        conn.commit()

        # Checkpoint WAL périodique
        if (i + 1) % 50 == 0:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        dt = time.time() - t1
        elapsed = time.time() - t0
        pct = (i + 1) / len(todo) * 100
        # Nom court du fichier
        short = gz_path.split("works/")[-1] if "works/" in gz_path else gz_path[-40:]
        log(f"  [{i+1}/{len(todo)}] {pct:.0f}% | {short} | {matched} matchés / {n_papers} papers | {dt:.1f}s | total matchés: {total_matched:,}")

    # 5) Final
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    elapsed = time.time() - t0
    log(f"\n  TERMINÉ en {elapsed:.0f}s ({elapsed/60:.1f} min)")
    log(f"  {total_matched:,} papers enrichis sur {total_papers:,} scannés")

    # Update meta
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('enrich_date', datetime('now'))"
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('enrich_matched', ?)",
        (str(total_matched),)
    )
    conn.commit()

    show_status(conn)
    conn.close()


def show_status(conn=None):
    close = False
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), timeout=10)
        close = True

    # Combien enrichis?
    cur = conn.execute("SELECT COUNT(*) FROM papers WHERE title IS NOT NULL")
    enriched = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM papers")
    total = cur.fetchone()[0]
    done_files = len(get_done_files(conn))
    gz_total = len(discover_gz_files())

    log(f"\n  STATUS:")
    log(f"    Papers enrichis: {enriched:,} / {total:,} ({enriched/total*100:.1f}%)")
    log(f"    Fichiers scannés: {done_files:,} / {gz_total:,}")

    if close:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WT3 Enrich — title/authors/year")
    parser.add_argument("--status", action="store_true", help="Afficher la progression")
    parser.add_argument("--test", action="store_true", help="Test sur 5 fichiers")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        run(test_mode=args.test)
