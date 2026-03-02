#!/usr/bin/env python3
"""
Brique 4 — arXiv Glyph Scanner
Stream arXiv .tar files, extract LaTeX formulas, build glyph co-occurrence chunks.

Usage:
    python engine/glyphs/arxiv_scanner.py --init        # Plan chunks from E:/arxiv/src/
    python engine/glyphs/arxiv_scanner.py               # Scan next chunk
    python engine/glyphs/arxiv_scanner.py --chunks 5    # Scan 5 chunks
    python engine/glyphs/arxiv_scanner.py --status      # Show progress
"""
import gzip
import io
import json
import os
import re
import sys
import time
import signal
import tarfile
import argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent

# ── CONFIG ──────────────────────────────────────────────────────────
ARXIV_DIR = Path(os.environ.get("YGG_ARXIV_DIR", "E:/arxiv/src"))
SCAN_DIR = ROOT / "data" / "scan"
TREE_PATH = SCAN_DIR / "glyph_tree.json"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
CHUNKS_DIR = SCAN_DIR / "glyph_chunks"

CHUNK_TARGET_BYTES = 1 * 1024 * 1024 * 1024   # ~1 GB per chunk
MONTH_FROM_YEAR = 1980
CUTOFF_YYMM = 1512   # December 2015 — max YYMM to include

# ── CTRL+C ──────────────────────────────────────────────────────────
_interrupted = False

def _on_sigint(sig, frame):
    global _interrupted
    print("\n  [Ctrl+C] Finishing current file then saving...")
    _interrupted = True

signal.signal(signal.SIGINT, _on_sigint)


# ── HELPERS ─────────────────────────────────────────────────────────

def yymm_to_period(yymm: str) -> tuple[int, str]:
    """
    Convert YYMM string to (year, time_key).
    '1501' → (2015, '2015-01'), '9501' → (1995, '1995-01'), '0001' → (2000, '2000-01')
    """
    yy = int(yymm[:2])
    mm = int(yymm[2:])
    if yy >= 91:
        year = 1900 + yy
    else:
        year = 2000 + yy

    if year >= MONTH_FROM_YEAR:
        return year, f"{year}-{mm:02d}"
    else:
        return year, str(year)


def yymm_from_tarname(name: str) -> str | None:
    """Extract YYMM from 'arXiv_src_YYMM_NNN.tar'."""
    m = re.match(r"arXiv_src_(\d{4})_\d+\.tar$", name)
    return m.group(1) if m else None


def extract_tex_from_gz(gz_bytes: bytes) -> str | None:
    """
    Extract .tex content from a .gz entry inside an arXiv tar.
    Handles two formats:
    - Sub-tar: .gz decompresses to a tar containing .tex files
    - Direct: .gz decompresses to a .tex file directly
    """
    try:
        decompressed = gzip.decompress(gz_bytes)
    except (gzip.BadGzipFile, OSError):
        return None

    # Try sub-tar first
    try:
        with tarfile.open(fileobj=io.BytesIO(decompressed)) as inner:
            # Find the main .tex file (prefer largest .tex)
            tex_members = [m for m in inner.getmembers()
                          if m.name.endswith(".tex") and m.isfile() and m.size > 100]
            if not tex_members:
                return None
            # Take the largest .tex (usually the main paper)
            tex_members.sort(key=lambda m: m.size, reverse=True)
            f = inner.extractfile(tex_members[0])
            if f:
                raw = f.read()
                try:
                    return raw.decode("utf-8")
                except UnicodeDecodeError:
                    return raw.decode("latin-1", errors="replace")
    except (tarfile.TarError, EOFError):
        pass

    # Fallback: direct .tex
    try:
        return decompressed.decode("utf-8")
    except UnicodeDecodeError:
        return decompressed.decode("latin-1", errors="replace")


# ── INIT ────────────────────────────────────────────────────────────

def discover_tar_files() -> list[tuple[str, int]]:
    """Find all valid .tar files in ARXIV_DIR, filtered by cutoff."""
    tars = []
    for f in sorted(ARXIV_DIR.glob("arXiv_src_*.tar")):
        yymm = yymm_from_tarname(f.name)
        if yymm is None:
            continue
        yymm_int = int(yymm)
        # Apply cutoff: skip tars after December 2015
        # YYMM encoding: 91-99 = 1991-1999, 00-90 = 2000-2090
        year, _ = yymm_to_period(yymm)
        if year > 2015:
            continue
        if year == 2015 and int(yymm[2:]) > 12:
            continue
        tars.append((f.name, f.stat().st_size))
    return tars


def init_tree():
    """--init: scan E:/arxiv/src/, plan chunks, create glyph_tree.json."""
    print("=" * 60)
    print("  INIT: Glyph Tree from arXiv LaTeX")
    print("=" * 60)

    # Load registry
    if not REGISTRY_PATH.exists():
        print(f"  ERROR: Registry not found at {REGISTRY_PATH}")
        print("  Run: python engine/glyphs/glyph_registry.py")
        sys.exit(1)

    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    n_glyphs = reg["meta"]["total"]
    print(f"  Registry: {n_glyphs} glyphs, {reg['meta']['latex_commands_mapped']} LaTeX mappings")

    # Discover tars
    print(f"\n  Scanning {ARXIV_DIR}...")
    tars = discover_tar_files()
    if not tars:
        print(f"  ERROR: No tar files found in {ARXIV_DIR}")
        sys.exit(1)

    total_bytes = sum(sz for _, sz in tars)
    print(f"  {len(tars)} tar files, {total_bytes / 1024**3:.1f} GB (cutoff ≤ 2015-12)")

    # Plan chunks
    chunks = []
    chunk_files = []
    chunk_bytes = 0
    chunk_id = 1

    for name, fsize in tars:
        chunk_files.append(name)
        chunk_bytes += fsize

        if chunk_bytes >= CHUNK_TARGET_BYTES:
            chunks.append({
                "id": chunk_id,
                "files": chunk_files,
                "bytes": chunk_bytes,
                "status": "pending",
            })
            chunk_files = []
            chunk_bytes = 0
            chunk_id += 1

    if chunk_files:
        chunks.append({
            "id": chunk_id,
            "files": chunk_files,
            "bytes": chunk_bytes,
            "status": "pending",
        })

    tree = {
        "version": 1,
        "type": "glyph_tree_arxiv",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "glyph_count": n_glyphs,
            "chunk_target_bytes": CHUNK_TARGET_BYTES,
            "month_from_year": MONTH_FROM_YEAR,
            "cutoff": "2015-12",
            "arxiv_dir": str(ARXIV_DIR),
        },
        "files": {
            "total": len(tars),
            "total_bytes": total_bytes,
        },
        "progress": {
            "chunks_total": len(chunks),
            "chunks_completed": 0,
            "papers_scanned": 0,
            "papers_with_glyphs": 0,
            "pairs_counted": 0,
        },
        "chunks": chunks,
    }

    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)

    print(f"\n  Planned {len(chunks)} chunks")
    print(f"  Tree: {TREE_PATH}")


# ── SCAN ────────────────────────────────────────────────────────────

def scan_chunk(tree: dict, latex_to_id: dict, unicode_to_id: dict) -> bool:
    """
    Scan the next pending chunk. Returns True if more chunks remain.
    """
    # Find next pending
    chunk = None
    for c in tree["chunks"]:
        if c["status"] == "pending":
            chunk = c
            break
    if chunk is None:
        return False

    cid = chunk["id"]
    print(f"\n  === Chunk {cid}/{tree['progress']['chunks_total']} ===")
    chunk["status"] = "scanning"

    # Accumulators
    cooc = defaultdict(lambda: defaultdict(float))   # {period: {pair: weight}}
    activity = defaultdict(lambda: defaultdict(int))  # {period: {glyph_id: count}}

    papers_total = 0
    papers_skipped = 0
    papers_matched = 0
    pairs_counted = 0
    t0 = time.time()

    for tarname in chunk["files"]:
        if _interrupted:
            break

        tarpath = ARXIV_DIR / tarname
        if not tarpath.exists():
            print(f"    SKIP (missing): {tarname}")
            continue

        # Extract YYMM from tarname
        yymm = yymm_from_tarname(tarname)
        if yymm is None:
            continue
        year, period = yymm_to_period(yymm)

        try:
            with tarfile.open(tarpath, "r:") as tar:
                for member in tar.getmembers():
                    if _interrupted:
                        break
                    # Only process .gz entries (paper sources)
                    if not member.name.endswith(".gz") or not member.isfile():
                        continue

                    papers_total += 1
                    try:
                        f = tar.extractfile(member)
                        if f is None:
                            papers_skipped += 1
                            continue
                        gz_bytes = f.read()
                    except (tarfile.TarError, IOError):
                        papers_skipped += 1
                        continue

                    # Extract tex content
                    tex = extract_tex_from_gz(gz_bytes)
                    if tex is None or len(tex) < 100:
                        papers_skipped += 1
                        continue

                    # Parse glyphs
                    from engine.glyphs.latex_parser import parse_tex_glyphs
                    glyph_ids = parse_tex_glyphs(tex, latex_to_id, unicode_to_id,
                                                  min_envs=1)
                    if len(glyph_ids) < 2:
                        papers_skipped += 1
                        continue

                    papers_matched += 1

                    # Activity
                    for gid in glyph_ids:
                        activity[period][gid] += 1

                    # Co-occurrence with 1/C(n,2) weighting
                    n = len(glyph_ids)
                    n_pairs = n * (n - 1) // 2
                    if n_pairs == 0:
                        continue
                    weight = 1.0 / n_pairs

                    for i in range(n):
                        for j in range(i + 1, n):
                            pair_key = f"{glyph_ids[i]}|{glyph_ids[j]}"
                            cooc[period][pair_key] += weight
                            pairs_counted += 1

        except (tarfile.TarError, IOError) as e:
            print(f"    ERROR reading {tarname}: {e}")
            continue

        # Progress every 10 tars
        if papers_total > 0 and papers_total % 5000 == 0:
            elapsed = time.time() - t0
            rate = papers_total / elapsed if elapsed > 0 else 0
            print(f"    {papers_total:,} papers, {papers_matched:,} matched, "
                  f"{rate:.0f}/s")

    # Save chunk output
    elapsed = time.time() - t0
    chunk_dir = CHUNKS_DIR / f"chunk_{cid:03d}"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    # cooc.json.gz
    cooc_serializable = {p: dict(pairs) for p, pairs in cooc.items()}
    with gzip.open(chunk_dir / "cooc.json.gz", "wt", encoding="utf-8") as f:
        json.dump(cooc_serializable, f)

    # activity.json.gz
    act_serializable = {p: {str(k): v for k, v in concepts.items()}
                        for p, concepts in activity.items()}
    with gzip.open(chunk_dir / "activity.json.gz", "wt", encoding="utf-8") as f:
        json.dump(act_serializable, f)

    # Unique pairs count
    unique_pairs = sum(len(pairs) for pairs in cooc.values())

    # meta.json
    meta = {
        "id": cid,
        "files": chunk["files"],
        "status": "interrupted" if _interrupted else "complete",
        "papers_total": papers_total,
        "papers_skipped": papers_skipped,
        "papers_matched": papers_matched,
        "pairs_counted": pairs_counted,
        "unique_pairs": unique_pairs,
        "weighting": "1/C(n,2)",
        "periods_seen": sorted(cooc.keys()),
        "active_glyphs": len({gid for p in activity.values() for gid in p}),
        "scan_time_sec": round(elapsed, 1),
        "papers_per_sec": round(papers_total / elapsed, 1) if elapsed > 0 else 0,
    }
    with open(chunk_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Update chunk status
    chunk["status"] = "interrupted" if _interrupted else "complete"

    # Update tree progress
    tree["progress"]["chunks_completed"] = sum(
        1 for c in tree["chunks"] if c["status"] == "complete")
    tree["progress"]["papers_scanned"] += papers_total
    tree["progress"]["papers_with_glyphs"] += papers_matched
    tree["progress"]["pairs_counted"] += pairs_counted

    # Save tree
    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)

    print(f"\n  Chunk {cid}: {papers_total:,} papers, {papers_matched:,} matched, "
          f"{unique_pairs:,} unique pairs, {elapsed:.0f}s")

    return not _interrupted and any(c["status"] == "pending" for c in tree["chunks"])


def show_status():
    """--status: show current progress."""
    if not TREE_PATH.exists():
        print("  No glyph_tree.json found. Run --init first.")
        return

    with open(TREE_PATH, encoding="utf-8") as f:
        tree = json.load(f)

    p = tree["progress"]
    n_chunks = p["chunks_total"]
    n_done = p["chunks_completed"]
    n_pending = sum(1 for c in tree["chunks"] if c["status"] == "pending")

    print(f"=== Glyph Tree Status ===")
    print(f"  Chunks: {n_done}/{n_chunks} complete, {n_pending} pending")
    print(f"  Papers scanned: {p['papers_scanned']:,}")
    print(f"  Papers with glyphs: {p['papers_with_glyphs']:,}")
    print(f"  Pairs counted: {p['pairs_counted']:,}")
    print(f"  Cutoff: {tree['config']['cutoff']}")
    print(f"  Source: {tree['config']['arxiv_dir']}")


# ── MAIN ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="arXiv Glyph Scanner")
    parser.add_argument("--init", action="store_true", help="Initialize glyph tree")
    parser.add_argument("--chunks", type=int, default=1, help="Number of chunks to scan")
    parser.add_argument("--status", action="store_true", help="Show progress")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.init:
        init_tree()
        return

    # Load tree
    if not TREE_PATH.exists():
        print("  No glyph_tree.json found. Run --init first.")
        sys.exit(1)
    with open(TREE_PATH, encoding="utf-8") as f:
        tree = json.load(f)

    # Load registry
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    latex_to_id = reg["latex_to_id"]
    unicode_to_id = reg["unicode_to_id"]

    print(f"Registry: {reg['meta']['total']} glyphs")
    print(f"Chunks: {tree['progress']['chunks_completed']}/{tree['progress']['chunks_total']}")

    for i in range(args.chunks):
        if not scan_chunk(tree, latex_to_id, unicode_to_id):
            print("\n  All chunks complete!")
            break


if __name__ == "__main__":
    # Ensure we can import from project root
    sys.path.insert(0, str(ROOT))
    main()
