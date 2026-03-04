#!/usr/bin/env python3
"""
S-1 Scanner — Build domain × glyph profiles from arXiv LaTeX.

For each paper: extract arXiv_ID → lookup domain → parse glyphs → accumulate.
Uses the same tar scanning as arxiv_scanner.py but enriches with domain info.

Output per chunk: data/scan/s1_chunks/chunk_NNN/
  - domain_profile.json.gz  { domain: { glyph_id: count } }
  - domain_cooc.json.gz     { domain: { "gid_a|gid_b": weight } }
  - meta.json

Usage:
    python engine/professions/domain_glyph_scanner.py --init
    python engine/professions/domain_glyph_scanner.py --chunks 9999
    python engine/professions/domain_glyph_scanner.py --status
"""
import argparse
import gzip
import json
import re
import signal
import sys
import tarfile
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

SCAN_DIR = ROOT / "data" / "scan"
TREE_PATH = SCAN_DIR / "s1_tree.json"
CHUNKS_DIR = SCAN_DIR / "s1_chunks"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
LOOKUP_PATH = SCAN_DIR / "arxiv_domain_lookup.json.gz"
ARXIV_DIR = Path("E:/arxiv/src")

CUTOFF_YYMM = 1512  # December 2015

_interrupted = False


def _sigint_handler(sig, frame):
    global _interrupted
    _interrupted = True
    print("\n  [Ctrl+C] Finishing current chunk...")


signal.signal(signal.SIGINT, _sigint_handler)


# ── ARXIV ID EXTRACTION ───────────────────────────────────────────

def extract_arxiv_id(member_name: str) -> str | None:
    """Extract arXiv ID from tar member name.
    Old format: '0401/astro-ph0401001.gz' → 'astro-ph/0401001'
    New format: '0910/0910.0001.gz' → '0910.0001'
    """
    basename = member_name.split("/")[-1].replace(".gz", "")
    # New format: YYMM.NNNNN
    if re.match(r"^\d{4}\.\d+$", basename):
        return basename
    # Old format: category + YYMMNNNNN
    m = re.match(r"^([a-zA-Z-]+)(\d{7,})$", basename)
    if m:
        cat = m.group(1)
        num = m.group(2)
        yymm = num[:4]
        seq = num[4:]
        return f"{cat}/{yymm}{seq}"
    return None


# arXiv category → domain fallback (when not in mapper)
ARXIV_CAT_TO_DOMAIN = {
    "astro-ph": "Physics", "cond-mat": "Physics", "gr-qc": "Physics",
    "hep-ex": "Physics", "hep-lat": "Physics", "hep-ph": "Physics",
    "hep-th": "Physics", "nucl-ex": "Physics", "nucl-th": "Physics",
    "physics": "Physics", "quant-ph": "Physics", "math-ph": "Physics",
    "math": "Mathematics", "cs": "Computer science",
    "nlin": "Mathematics", "q-bio": "Biology", "q-fin": "Economics",
    "stat": "Mathematics", "eess": "Engineering", "econ": "Economics",
}


def domain_from_category(arxiv_id: str) -> str | None:
    """Fallback: extract domain from arXiv ID category prefix."""
    if "/" in arxiv_id:
        cat = arxiv_id.split("/")[0]
        return ARXIV_CAT_TO_DOMAIN.get(cat)
    return None


# ── TAR HELPERS ────────────────────────────────────────────────────

def yymm_from_tarname(tarname: str) -> int | None:
    """Extract YYMM from 'arXiv_src_YYMM_NNN.tar'."""
    m = re.search(r"arXiv_src_(\d{4})_", tarname)
    return int(m.group(1)) if m else None


def extract_tex_from_gz(gz_bytes: bytes) -> str | None:
    """Extract .tex content from gzipped data."""
    import io
    try:
        with gzip.open(io.BytesIO(gz_bytes), "rt",
                       encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        # Might be a tar-in-gz (multi-file submission)
        try:
            with gzip.open(io.BytesIO(gz_bytes), "rb") as f:
                raw = f.read()
            try:
                inner = tarfile.open(fileobj=io.BytesIO(raw))
                for member in inner.getmembers():
                    if member.name.endswith(".tex") and member.isfile():
                        ef = inner.extractfile(member)
                        if ef:
                            return ef.read().decode("utf-8", errors="replace")
            except Exception:
                pass
        except Exception:
            pass
    return None


# ── INIT ───────────────────────────────────────────────────────────

def init_tree():
    """Discover arXiv tars ≤ cutoff and plan chunks."""
    print("=" * 60)
    print("  INIT: S-1 Domain×Glyph Scanner")
    print("=" * 60)

    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    print(f"  Registry: {reg['meta']['total']} glyphs, "
          f"{len(reg['latex_to_id'])} LaTeX mappings")

    # Find tars
    tars = []
    total_bytes = 0
    for f in sorted(ARXIV_DIR.iterdir()):
        if not f.name.endswith(".tar"):
            continue
        yymm = yymm_from_tarname(f.name)
        if yymm is None or yymm > CUTOFF_YYMM:
            continue
        tars.append(f.name)
        total_bytes += f.stat().st_size

    print(f"\n  Scanning {ARXIV_DIR}...")
    print(f"  {len(tars)} tar files, {total_bytes / 1e9:.1f} GB "
          f"(cutoff ≤ 2015-12)")

    # Plan chunks (~1 GB each)
    CHUNK_TARGET = 1_073_741_824  # 1 GB
    chunks = []
    current = {"files": [], "bytes": 0}

    for tarname in tars:
        fsize = (ARXIV_DIR / tarname).stat().st_size
        current["files"].append(tarname)
        current["bytes"] += fsize

        if current["bytes"] >= CHUNK_TARGET:
            chunks.append(current)
            current = {"files": [], "bytes": 0}

    if current["files"]:
        chunks.append(current)

    # Build tree
    tree = {
        "version": 1,
        "type": "s1_domain_glyph",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "glyph_count": reg["meta"]["total"],
            "chunk_target_bytes": CHUNK_TARGET,
            "cutoff": "2015-12",
            "arxiv_dir": str(ARXIV_DIR),
        },
        "progress": {
            "chunks_total": len(chunks),
            "chunks_completed": 0,
            "papers_scanned": 0,
            "papers_with_domain": 0,
            "papers_with_glyphs": 0,
        },
        "chunks": [
            {
                "id": i + 1,
                "files": c["files"],
                "bytes": c["bytes"],
                "status": "pending",
            }
            for i, c in enumerate(chunks)
        ],
    }

    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)

    print(f"\n  Planned {len(chunks)} chunks")
    print(f"  Tree: {TREE_PATH}")


# ── SCAN ───────────────────────────────────────────────────────────

def scan_chunk(tree: dict, latex_to_id: dict, unicode_to_id: dict,
               domain_lookup: dict, domain_names: list) -> bool:
    """Scan next pending chunk. Returns True if more remain."""
    chunk = None
    for c in tree["chunks"]:
        if c["status"] == "pending":
            chunk = c
            break
    if chunk is None:
        return False

    cid = chunk["id"]
    total_chunks = tree["progress"]["chunks_total"]
    print(f"\n  === Chunk {cid}/{total_chunks} ===")
    chunk["status"] = "scanning"

    # Accumulators: domain → glyph_id → count
    domain_profile = defaultdict(lambda: defaultdict(int))
    # domain → "gid_a|gid_b" → weight
    domain_cooc = defaultdict(lambda: defaultdict(float))

    papers_total = 0
    papers_with_domain = 0
    papers_with_glyphs = 0
    t0 = time.time()

    for tarname in chunk["files"]:
        if _interrupted:
            break

        tarpath = ARXIV_DIR / tarname
        if not tarpath.exists():
            print(f"    SKIP (missing): {tarname}")
            continue

        yymm = yymm_from_tarname(tarname)
        if yymm is None:
            continue

        try:
            with tarfile.open(tarpath, "r:") as tar:
                while True:
                    if _interrupted:
                        break
                    try:
                        member = tar.next()
                    except Exception:
                        break
                    if member is None:
                        break
                    if not member.name.endswith(".gz") or not member.isfile():
                        continue

                    papers_total += 1

                    # Extract arXiv ID
                    arxiv_id = extract_arxiv_id(member.name)
                    if arxiv_id is None:
                        continue

                    # Look up domain (compact: int index → name)
                    domain_idx = domain_lookup.get(arxiv_id)
                    if domain_idx is not None:
                        domain = domain_names[domain_idx]
                    else:
                        # Fallback: category from ID
                        domain = domain_from_category(arxiv_id)
                    if domain is None:
                        continue

                    papers_with_domain += 1

                    # Extract tex (cap at 50 MB to avoid MemoryError)
                    try:
                        f = tar.extractfile(member)
                        if f is None:
                            continue
                        if member.size > 50_000_000:
                            continue
                        gz_bytes = f.read()
                    except (tarfile.TarError, IOError, MemoryError):
                        continue

                    try:
                        tex = extract_tex_from_gz(gz_bytes)
                    except MemoryError:
                        continue
                    if tex is None or len(tex) < 100:
                        continue

                    # Parse glyphs
                    try:
                        from engine.glyphs.latex_parser import parse_tex_glyphs
                        glyph_ids = parse_tex_glyphs(
                            tex, latex_to_id, unicode_to_id, min_envs=1
                        )
                    except MemoryError:
                        continue
                    if len(glyph_ids) < 2:
                        continue

                    papers_with_glyphs += 1

                    # Accumulate profile: domain → glyph counts
                    for gid in glyph_ids:
                        domain_profile[domain][gid] += 1

                    # Co-occurrence within domain (1/C(n,2) weighting)
                    n = len(glyph_ids)
                    n_pairs = n * (n - 1) // 2
                    if n_pairs == 0:
                        continue
                    weight = 1.0 / n_pairs
                    for i in range(n):
                        for j in range(i + 1, n):
                            pair_key = f"{glyph_ids[i]}|{glyph_ids[j]}"
                            domain_cooc[domain][pair_key] += weight

        except (tarfile.TarError, IOError) as e:
            print(f"    ERROR: {tarname}: {e}")
            continue

    elapsed = time.time() - t0

    # Save chunk output
    chunk_dir = CHUNKS_DIR / f"chunk_{cid:03d}"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    # domain_profile.json.gz
    profile_out = {d: dict(v) for d, v in domain_profile.items()}
    with gzip.open(chunk_dir / "domain_profile.json.gz", "wt",
                   encoding="utf-8") as f:
        json.dump(profile_out, f, ensure_ascii=False)

    # domain_cooc.json.gz
    cooc_out = {d: dict(v) for d, v in domain_cooc.items()}
    with gzip.open(chunk_dir / "domain_cooc.json.gz", "wt",
                   encoding="utf-8") as f:
        json.dump(cooc_out, f, ensure_ascii=False)

    # meta.json
    meta = {
        "id": cid,
        "files": chunk["files"],
        "status": "complete",
        "papers_total": papers_total,
        "papers_with_domain": papers_with_domain,
        "papers_with_glyphs": papers_with_glyphs,
        "domains_seen": len(domain_profile),
        "scan_time_sec": round(elapsed, 1),
        "papers_per_sec": round(papers_total / max(elapsed, 0.1), 1),
    }
    with open(chunk_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Update tree
    chunk["status"] = "complete"
    tree["progress"]["chunks_completed"] = sum(
        1 for c in tree["chunks"] if c["status"] == "complete"
    )
    tree["progress"]["papers_scanned"] += papers_total
    tree["progress"]["papers_with_domain"] += papers_with_domain
    tree["progress"]["papers_with_glyphs"] += papers_with_glyphs

    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)

    print(f"  Chunk {cid}: {papers_total:,} papers, "
          f"{papers_with_domain:,} with domain, "
          f"{papers_with_glyphs:,} with glyphs, "
          f"{len(domain_profile)} domains, {elapsed:.0f}s")

    return not _interrupted and any(
        c["status"] == "pending" for c in tree["chunks"]
    )


# ── STATUS ─────────────────────────────────────────────────────────

def show_status():
    if not TREE_PATH.exists():
        print("  No s1_tree.json found. Run --init first.")
        return
    with open(TREE_PATH, encoding="utf-8") as f:
        tree = json.load(f)
    p = tree["progress"]
    print("=== S-1 Domain×Glyph Scanner Status ===")
    print(f"  Chunks: {p['chunks_completed']}/{p['chunks_total']}")
    print(f"  Papers scanned: {p['papers_scanned']:,}")
    print(f"  Papers with domain: {p['papers_with_domain']:,}")
    print(f"  Papers with glyphs: {p['papers_with_glyphs']:,}")


# ── MAIN ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="S-1 Domain×Glyph Scanner")
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

    # Load tree
    if not TREE_PATH.exists():
        print("  No s1_tree.json found. Run --init first.")
        sys.exit(1)
    with open(TREE_PATH, encoding="utf-8") as f:
        tree = json.load(f)

    # Load registry
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    latex_to_id = reg["latex_to_id"]
    unicode_to_id = reg["unicode_to_id"]

    # Load domain lookup — compact: store domain as int index
    print("  Loading domain lookup (compact)...")
    domain_names = []  # index → domain name
    domain_index = {}  # domain name → index
    domain_lookup = {}  # arxiv_id → domain_index (int, not string)
    with gzip.open(LOOKUP_PATH, "rt", encoding="utf-8") as f:
        raw = json.load(f)
    for arxiv_id, domain in raw.items():
        if domain not in domain_index:
            domain_index[domain] = len(domain_names)
            domain_names.append(domain)
        domain_lookup[arxiv_id] = domain_index[domain]
    del raw  # free the full-string dict
    print(f"  Domain lookup: {len(domain_lookup):,} entries, "
          f"{len(domain_names)} domains")

    print(f"  Registry: {reg['meta']['total']} glyphs")
    print(f"  Chunks: {tree['progress']['chunks_completed']}/"
          f"{tree['progress']['chunks_total']}")

    for i in range(args.chunks):
        if not scan_chunk(tree, latex_to_id, unicode_to_id, domain_lookup, domain_names):
            print("\n  All chunks complete!")
            break


if __name__ == "__main__":
    main()
