#!/usr/bin/env python3
"""
Brique 5 — PMC Glyph Scanner
Stream PMC .tar.gz files, extract MathML formulas, build glyph co-occurrence chunks.

Usage:
    python engine/glyphs/pmc_scanner.py --init        # Plan chunks from E:/pmc/
    python engine/glyphs/pmc_scanner.py               # Scan next chunk
    python engine/glyphs/pmc_scanner.py --chunks 5    # Scan 5 chunks
    python engine/glyphs/pmc_scanner.py --status      # Show progress
"""
import gzip
import json
import os
import sys
import time
import signal
import tarfile
import argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent

# ── CONFIG ──────────────────────────────────────────────────────────
PMC_DIR = Path(os.environ.get("YGG_PMC_DIR", "E:/pmc"))
SCAN_DIR = ROOT / "data" / "scan"
TREE_PATH = SCAN_DIR / "pmc_glyph_tree.json"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
CHUNKS_DIR = SCAN_DIR / "pmc_glyph_chunks"

CUTOFF_YEAR = 2015

# ── CTRL+C ──────────────────────────────────────────────────────────
_interrupted = False

def _on_sigint(sig, frame):
    global _interrupted
    print("\n  [Ctrl+C] Finishing current file then saving...")
    _interrupted = True

signal.signal(signal.SIGINT, _on_sigint)


# ── INIT ────────────────────────────────────────────────────────────

def discover_pmc_tars() -> list[tuple[str, int]]:
    """Find all baseline .tar.gz files in E:/pmc/oa_*/ directories."""
    tars = []
    for subset in ["oa_comm", "oa_noncomm", "oa_other"]:
        subset_dir = PMC_DIR / subset
        if not subset_dir.exists():
            continue
        for f in sorted(subset_dir.glob("*.tar.gz")):
            if "baseline" in f.name:
                tars.append((str(f.relative_to(PMC_DIR)), f.stat().st_size))
    return tars


def init_tree():
    """--init: scan E:/pmc/, plan chunks (1 tar.gz = 1 chunk)."""
    print("=" * 60)
    print("  INIT: Glyph Tree from PMC MathML")
    print("=" * 60)

    # Load registry
    if not REGISTRY_PATH.exists():
        print(f"  ERROR: Registry not found at {REGISTRY_PATH}")
        sys.exit(1)

    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    n_glyphs = reg["meta"]["total"]
    print(f"  Registry: {n_glyphs} glyphs")

    # Discover tars
    print(f"\n  Scanning {PMC_DIR}...")
    tars = discover_pmc_tars()
    if not tars:
        print(f"  ERROR: No tar.gz files found in {PMC_DIR}")
        sys.exit(1)

    total_bytes = sum(sz for _, sz in tars)
    print(f"  {len(tars)} tar.gz files, {total_bytes / 1024**3:.1f} GB")

    # Each tar.gz is one chunk (they're already 1-10 GB each)
    chunks = []
    for i, (name, fsize) in enumerate(tars, 1):
        chunks.append({
            "id": i,
            "files": [name],
            "bytes": fsize,
            "status": "pending",
        })

    tree = {
        "version": 1,
        "type": "glyph_tree_pmc",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "glyph_count": n_glyphs,
            "cutoff_year": CUTOFF_YEAR,
            "pmc_dir": str(PMC_DIR),
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

    print(f"\n  Planned {len(chunks)} chunks (1 per tar.gz)")
    print(f"  Tree: {TREE_PATH}")


# ── SCAN ────────────────────────────────────────────────────────────

def scan_chunk(tree: dict, unicode_to_id: dict) -> bool:
    """Scan the next pending chunk."""
    from engine.glyphs.mathml_parser import parse_pmc_xml

    chunk = None
    for c in tree["chunks"]:
        if c["status"] == "pending":
            chunk = c
            break
    if chunk is None:
        return False

    cid = chunk["id"]
    print(f"\n  === PMC Chunk {cid}/{tree['progress']['chunks_total']} ===")
    print(f"  File: {chunk['files'][0]}")
    chunk["status"] = "scanning"

    # Accumulators
    cooc = defaultdict(lambda: defaultdict(float))
    activity = defaultdict(lambda: defaultdict(int))

    papers_total = 0
    papers_skipped = 0
    papers_matched = 0
    papers_cutoff = 0
    papers_nomath = 0
    pairs_counted = 0
    t0 = time.time()

    for tarname in chunk["files"]:
        if _interrupted:
            break

        tarpath = PMC_DIR / tarname
        if not tarpath.exists():
            print(f"    SKIP (missing): {tarname}")
            continue

        try:
            with tarfile.open(tarpath, "r:gz") as tar:
                for member in tar:
                    if _interrupted:
                        break
                    if not member.name.endswith(".xml") or not member.isfile():
                        continue
                    if member.size < 100:
                        continue

                    papers_total += 1

                    try:
                        f = tar.extractfile(member)
                        if f is None:
                            papers_skipped += 1
                            continue
                        xml_bytes = f.read()
                    except (tarfile.TarError, IOError):
                        papers_skipped += 1
                        continue

                    # Parse MathML
                    glyph_ids, time_key = parse_pmc_xml(
                        xml_bytes, unicode_to_id, cutoff_year=CUTOFF_YEAR)

                    if not glyph_ids:
                        if time_key is None:
                            papers_cutoff += 1
                        else:
                            papers_nomath += 1
                        continue

                    if len(glyph_ids) < 2:
                        papers_nomath += 1
                        continue

                    papers_matched += 1

                    # Activity
                    for gid in glyph_ids:
                        activity[time_key][gid] += 1

                    # Co-occurrence with 1/C(n,2) weighting
                    n = len(glyph_ids)
                    n_pairs = n * (n - 1) // 2
                    if n_pairs == 0:
                        continue
                    weight = 1.0 / n_pairs

                    for i in range(n):
                        for j in range(i + 1, n):
                            pair_key = f"{glyph_ids[i]}|{glyph_ids[j]}"
                            cooc[time_key][pair_key] += weight
                            pairs_counted += 1

                    if papers_total % 10000 == 0:
                        elapsed = time.time() - t0
                        rate = papers_total / elapsed if elapsed > 0 else 0
                        print(f"    {papers_total:,} papers, {papers_matched:,} matched, "
                              f"{papers_cutoff:,} cutoff, {rate:.0f}/s")

        except (tarfile.TarError, IOError) as e:
            print(f"    ERROR reading {tarname}: {e}")
            continue

    # Save
    elapsed = time.time() - t0
    chunk_dir = CHUNKS_DIR / f"chunk_{cid:03d}"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    cooc_ser = {p: dict(pairs) for p, pairs in cooc.items()}
    with gzip.open(chunk_dir / "cooc.json.gz", "wt", encoding="utf-8") as f:
        json.dump(cooc_ser, f)

    act_ser = {p: {str(k): v for k, v in concepts.items()}
               for p, concepts in activity.items()}
    with gzip.open(chunk_dir / "activity.json.gz", "wt", encoding="utf-8") as f:
        json.dump(act_ser, f)

    unique_pairs = sum(len(pairs) for pairs in cooc.values())

    meta = {
        "id": cid,
        "files": chunk["files"],
        "status": "interrupted" if _interrupted else "complete",
        "papers_total": papers_total,
        "papers_skipped": papers_skipped,
        "papers_matched": papers_matched,
        "papers_cutoff": papers_cutoff,
        "papers_nomath": papers_nomath,
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

    chunk["status"] = "interrupted" if _interrupted else "complete"
    tree["progress"]["chunks_completed"] = sum(
        1 for c in tree["chunks"] if c["status"] == "complete")
    tree["progress"]["papers_scanned"] += papers_total
    tree["progress"]["papers_with_glyphs"] += papers_matched
    tree["progress"]["pairs_counted"] += pairs_counted

    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)

    print(f"\n  PMC Chunk {cid}: {papers_total:,} papers, {papers_matched:,} matched, "
          f"{papers_cutoff:,} cutoff, {unique_pairs:,} unique pairs, {elapsed:.0f}s")

    return not _interrupted and any(c["status"] == "pending" for c in tree["chunks"])


def show_status():
    if not TREE_PATH.exists():
        print("  No pmc_glyph_tree.json found. Run --init first.")
        return
    with open(TREE_PATH, encoding="utf-8") as f:
        tree = json.load(f)
    p = tree["progress"]
    print(f"=== PMC Glyph Tree Status ===")
    print(f"  Chunks: {p['chunks_completed']}/{p['chunks_total']} complete")
    print(f"  Papers scanned: {p['papers_scanned']:,}")
    print(f"  Papers with glyphs: {p['papers_with_glyphs']:,}")
    print(f"  Pairs counted: {p['pairs_counted']:,}")
    print(f"  Cutoff: {tree['config']['cutoff_year']}")


def main():
    parser = argparse.ArgumentParser(description="PMC Glyph Scanner")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--chunks", type=int, default=1)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        show_status()
        return
    if args.init:
        init_tree()
        return

    if not TREE_PATH.exists():
        print("  No pmc_glyph_tree.json found. Run --init first.")
        sys.exit(1)
    with open(TREE_PATH, encoding="utf-8") as f:
        tree = json.load(f)

    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    unicode_to_id = reg["unicode_to_id"]

    print(f"Registry: {reg['meta']['total']} glyphs")
    print(f"Chunks: {tree['progress']['chunks_completed']}/{tree['progress']['chunks_total']}")

    for i in range(args.chunks):
        if not scan_chunk(tree, unicode_to_id):
            print("\n  All chunks complete!")
            break


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
