#!/usr/bin/env python3
"""
WT2 Scanner — Per-paper index: glyphs × domain × concepts (bipartite bridge S-2↔S0)

For each arXiv paper: extract glyphs from LaTeX, lookup domain + OpenAlex concepts,
save per-paper data AND aggregate bipartite glyph×concept co-occurrences.

Input:
    - arXiv tars (E:/arxiv/src/)          → glyphs via latex_parser
    - arxiv_map_chunks/chunk_NNN/          → concepts per arXiv paper
    - arxiv_domain_lookup.json.gz          → domain per arXiv paper
    - glyph_registry.json                  → glyph dicts

Output per chunk: data/scan/wt2_chunks/chunk_NNN/
    - papers.json.gz       { arxiv_id: { glyphs: [...], domain: "...", concepts: [...] } }
    - bipartite.json.gz    { "glyph_id|concept_idx": weight }
    - meta.json

RULE: This is a BIPARTITE bridge. Never merge with S-2 or S0 Laplacians.

Usage:
    python engine/topology/wt2_scanner.py --init
    python engine/topology/wt2_scanner.py --chunks 9999
    python engine/topology/wt2_scanner.py --status
"""
import argparse
import gzip
import io
import json
import random
import re
import signal
import sys
import tarfile
import threading
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

SCAN_DIR = ROOT / "data" / "scan"
TREE_PATH = SCAN_DIR / "wt2_tree.json"
CHUNKS_DIR = SCAN_DIR / "wt2_chunks"
REGISTRY_PATH = ROOT / "data" / "core" / "glyph_registry.json"
LOOKUP_PATH = SCAN_DIR / "arxiv_domain_lookup.json.gz"
MAPPER_DIR = SCAN_DIR / "arxiv_map_chunks"
CONCEPTS_PATH = SCAN_DIR / "concepts_65k.json"
ARXIV_DIR = Path("E:/arxiv/src")

CUTOFF_YYMM = 1512  # December 2015

_interrupted = False

# Per-paper timeout (Windows-safe, no signal.alarm).
PAPER_TIMEOUT_SEC = 30


def _call_with_timeout(func, args, timeout=PAPER_TIMEOUT_SEC):
    """Run *func(*args)* in a daemon thread; return None on timeout."""
    result = [None]
    exc = [None]

    def target():
        try:
            result[0] = func(*args)
        except Exception as e:
            exc[0] = e

    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None          # timed out — caller will skip this paper
    if exc[0] is not None:
        raise exc[0]
    return result[0]


def _sigint_handler(sig, frame):
    global _interrupted
    _interrupted = True
    print("\n  [Ctrl+C] Finishing current chunk...")


signal.signal(signal.SIGINT, _sigint_handler)


# ── ARXIV ID EXTRACTION ───────────────────────────────────────────

def extract_arxiv_id(member_name: str) -> str | None:
    basename = member_name.split("/")[-1].replace(".gz", "")
    if re.match(r"^\d{4}\.\d+$", basename):
        return basename
    m = re.match(r"^([a-zA-Z-]+)(\d{7,})$", basename)
    if m:
        cat = m.group(1)
        num = m.group(2)
        return f"{cat}/{num[:4]}{num[4:]}"
    return None


def yymm_from_tarname(tarname: str) -> int | None:
    m = re.search(r"arXiv_src_(\d{4})_", tarname)
    return int(m.group(1)) if m else None


def extract_tex_from_gz(gz_bytes: bytes) -> str | None:
    try:
        with gzip.open(io.BytesIO(gz_bytes), "rb") as f:
            raw = f.read()
    except Exception:
        return None

    # Inner tarball? (multi-file submission)
    if raw[:4] in (b"\x1f\x8b", b"BZh9") or raw[:5] == b"ustar" or (len(raw) > 257 and raw[257:262] == b"ustar"):
        try:
            inner = tarfile.open(fileobj=io.BytesIO(raw))
            for member in inner.getmembers():
                if member.name.endswith(".tex") and member.isfile():
                    ef = inner.extractfile(member)
                    if ef:
                        return ef.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return None

    # Plain .tex (single file submission)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("latin-1")
        except Exception:
            return None


# ── LOAD CONCEPT INDEX ────────────────────────────────────────────

class ConceptIndex:
    """SQLite-backed concept index. ~50MB RAM (page cache), 45K lookups/sec."""

    def __init__(self, db_path):
        import sqlite3
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=OFF")
        self.conn.execute("PRAGMA cache_size=-50000")  # 50MB page cache

    def get(self, arxiv_id, default=None):
        row = self.conn.execute(
            "SELECT idxs FROM concepts WHERE arxiv_id=?", (arxiv_id,)
        ).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def close(self):
        self.conn.close()


def load_concept_index():
    """Load arxiv_id → concept indices. SQLite-backed, zero RAM footprint.
    Builds DB once from mapper chunks, then reuses it."""
    DB_PATH = SCAN_DIR / "concept_index.db"

    # ── Check if DB exists and is fresh ──
    if DB_PATH.exists():
        db_mtime = DB_PATH.stat().st_mtime
        mapper_mtime = max(
            (d / "map.json.gz").stat().st_mtime
            for d in MAPPER_DIR.iterdir()
            if (d / "map.json.gz").exists()
        )
        if db_mtime > mapper_mtime:
            print("  Loading concept index (SQLite)...")
            idx = ConceptIndex(DB_PATH)
            count = idx.conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
            print(f"  Concept index: {count:,} papers (SQLite, zero-RAM)")
            return idx

    # ── Build SQLite DB from mapper chunks ──
    print("  Building concept index SQLite DB...")
    import gc, sqlite3

    with open(CONCEPTS_PATH, "r", encoding="utf-8") as f:
        cdata = json.load(f)
    cid_to_idx = {cid: info["idx"] for cid, info in cdata["concepts"].items()}
    del cdata
    gc.collect()

    # Remove stale DB
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("CREATE TABLE concepts (arxiv_id TEXT PRIMARY KEY, idxs TEXT)")

    t0 = time.time()
    n_chunks = 0
    n_papers = 0
    batch = []

    for chunk_dir in sorted(MAPPER_DIR.iterdir()):
        map_path = chunk_dir / "map.json.gz"
        if not map_path.exists():
            continue
        with gzip.open(map_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        for arxiv_id, info in data.items():
            concepts = info.get("concepts", [])
            idxs = []
            for c in concepts:
                cid = c.get("id", "")
                if cid in cid_to_idx:
                    idxs.append(cid_to_idx[cid])
            if idxs:
                batch.append((arxiv_id, json.dumps(idxs)))
                n_papers += 1
                if len(batch) >= 50000:
                    conn.executemany("INSERT OR REPLACE INTO concepts VALUES (?,?)", batch)
                    conn.commit()
                    batch.clear()
        del data
        gc.collect()
        n_chunks += 1
        if n_chunks % 50 == 0:
            print(f"    {n_chunks}/309 mapper chunks processed...")

    if batch:
        conn.executemany("INSERT OR REPLACE INTO concepts VALUES (?,?)", batch)
        conn.commit()
    conn.close()

    dt = time.time() - t0
    print(f"  SQLite DB built: {n_papers:,} papers from {n_chunks} chunks ({dt:.1f}s)")

    idx = ConceptIndex(DB_PATH)
    count = idx.conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    print(f"  Concept index: {count:,} papers (SQLite, zero-RAM)")
    return idx


# ── LOAD DOMAIN LOOKUP ────────────────────────────────────────────

def load_domain_lookup() -> tuple[dict, list]:
    """Stream-load arxiv_domain_lookup.json.gz → (domain_lookup, domain_names)."""
    print("  Loading domain lookup (streaming)...")
    domain_names = []
    domain_index = {}
    domain_lookup = {}
    pair_re = re.compile(r'"([^"]+)"\s*:\s*"([^"]+)"')
    remainder = ""
    with gzip.open(LOOKUP_PATH, "rt", encoding="utf-8") as f:
        while True:
            chunk = f.read(1_048_576)
            if not chunk:
                for m in pair_re.finditer(remainder):
                    aid, dom = m.group(1), m.group(2)
                    if dom not in domain_index:
                        domain_index[dom] = len(domain_names)
                        domain_names.append(dom)
                    domain_lookup[aid] = domain_index[dom]
                break
            text = remainder + chunk
            last_end = 0
            for m in pair_re.finditer(text):
                aid, dom = m.group(1), m.group(2)
                if dom not in domain_index:
                    domain_index[dom] = len(domain_names)
                    domain_names.append(dom)
                domain_lookup[aid] = domain_index[dom]
                last_end = m.end()
            remainder = text[last_end:]
    print(f"  Domain lookup: {len(domain_lookup):,} entries, "
          f"{len(domain_names)} domains")
    return domain_lookup, domain_names


# ── INIT ──────────────────────────────────────────────────────────

def init_tree():
    print("=" * 60)
    print("  INIT: WT2 Scanner — Per-paper bipartite bridge S-2↔S0")
    print("=" * 60)

    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    print(f"  Registry: {reg['meta']['total']} glyphs")

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

    print(f"  {len(tars)} tar files, {total_bytes / 1e9:.1f} GB (cutoff ≤ 2015-12)")

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

    tree = {
        "version": 1,
        "type": "wt2_bipartite_bridge",
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
            "papers_with_glyphs": 0,
            "papers_with_concepts": 0,
            "papers_full": 0,  # both glyphs AND concepts
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

    print(f"  Planned {len(chunks)} chunks")
    print(f"  Tree: {TREE_PATH}")


# ── SCAN ──────────────────────────────────────────────────────────

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
    if "/" in arxiv_id:
        cat = arxiv_id.split("/")[0]
        return ARXIV_CAT_TO_DOMAIN.get(cat)
    return None


def scan_chunk(tree: dict, latex_to_id: dict, unicode_to_id: dict,
               domain_lookup: dict, domain_names: list,
               arxiv_to_concepts: dict) -> bool:
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

    # Per-paper data
    papers_data = {}
    # Bipartite: "glyph_id|concept_idx" → weight
    bipartite = defaultdict(float)

    papers_total = 0
    papers_with_glyphs = 0
    papers_with_concepts = 0
    papers_full = 0
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

        tar_t0 = time.time()
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

                    arxiv_id = extract_arxiv_id(member.name)
                    if arxiv_id is None:
                        continue

                    # Lookup domain
                    domain_idx = domain_lookup.get(arxiv_id)
                    if domain_idx is not None:
                        domain = domain_names[domain_idx]
                    else:
                        domain = domain_from_category(arxiv_id)

                    # Lookup concepts
                    concept_idxs = arxiv_to_concepts.get(arxiv_id)
                    has_concepts = concept_idxs is not None and len(concept_idxs) > 0

                    # Extract tex (cap at 5 MB)
                    try:
                        f = tar.extractfile(member)
                        if f is None:
                            continue
                        if member.size > 5_000_000:
                            continue
                        gz_bytes = f.read()
                    except (tarfile.TarError, IOError, MemoryError):
                        continue

                    try:
                        tex = extract_tex_from_gz(gz_bytes)
                    except (MemoryError, Exception):
                        continue
                    if tex is None or len(tex) < 100:
                        continue
                    # Cap decompressed tex at 30 MB (safety only)
                    if len(tex) > 30_000_000:
                        continue

                    # Parse glyphs (with per-paper timeout)
                    try:
                        from engine.glyphs.latex_parser import parse_tex_glyphs
                        glyph_ids = _call_with_timeout(
                            parse_tex_glyphs,
                            (tex, latex_to_id, unicode_to_id, 1),
                        )
                        if glyph_ids is None:
                            # Timed out — skip this paper
                            print(f"    TIMEOUT ({PAPER_TIMEOUT_SEC}s): "
                                  f"{arxiv_id} ({len(tex)} chars)", flush=True)
                            continue
                    except (MemoryError, Exception):
                        continue

                    has_glyphs = len(glyph_ids) >= 2

                    if has_glyphs:
                        papers_with_glyphs += 1
                    if has_concepts:
                        papers_with_concepts += 1

                    if not has_glyphs:
                        continue

                    # Cap glyphs per paper
                    if len(glyph_ids) > 100:
                        rng = random.Random(arxiv_id)
                        glyph_ids = rng.sample(glyph_ids, 100)

                    # Build per-paper record
                    record = {"g": glyph_ids}
                    if domain is not None:
                        record["d"] = domain
                    if has_concepts:
                        record["c"] = concept_idxs
                        papers_full += 1

                    papers_data[arxiv_id] = record

                    # Bipartite glyph×concept co-occurrence
                    if has_concepts:
                        n_g = len(glyph_ids)
                        n_c = len(concept_idxs)
                        n_pairs = n_g * n_c
                        if n_pairs > 0:
                            weight = 1.0 / n_pairs
                            for gid in glyph_ids:
                                for cidx in concept_idxs:
                                    bipartite[f"{gid}|{cidx}"] += weight

        except (tarfile.TarError, IOError) as e:
            print(f"    ERROR: {tarname}: {e}")
            continue
        tar_dt = time.time() - tar_t0
        print(f"    {tarname}: {papers_total} papers, {tar_dt:.1f}s", flush=True)

    elapsed = time.time() - t0

    # Save chunk output
    chunk_dir = CHUNKS_DIR / f"chunk_{cid:03d}"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    # papers.json.gz — per-paper data
    with gzip.open(chunk_dir / "papers.json.gz", "wt", encoding="utf-8") as f:
        json.dump(papers_data, f, ensure_ascii=False)

    # bipartite.json.gz — glyph×concept co-occurrences
    bipartite_out = {k: round(v, 6) for k, v in bipartite.items()}
    with gzip.open(chunk_dir / "bipartite.json.gz", "wt", encoding="utf-8") as f:
        json.dump(bipartite_out, f, ensure_ascii=False)

    # meta.json
    meta = {
        "id": cid,
        "files": chunk["files"],
        "status": "complete",
        "papers_total": papers_total,
        "papers_with_glyphs": papers_with_glyphs,
        "papers_with_concepts": papers_with_concepts,
        "papers_full": papers_full,
        "unique_papers_saved": len(papers_data),
        "unique_bipartite_pairs": len(bipartite_out),
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
    tree["progress"]["papers_with_glyphs"] += papers_with_glyphs
    tree["progress"]["papers_with_concepts"] += papers_with_concepts
    tree["progress"]["papers_full"] += papers_full

    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)

    print(f"  Chunk {cid}: {papers_total:,} papers, "
          f"{papers_full:,} full (glyphs+concepts), "
          f"{len(bipartite_out):,} bipartite pairs, {elapsed:.0f}s")

    return not _interrupted and any(
        c["status"] == "pending" for c in tree["chunks"]
    )


# ── STATUS ────────────────────────────────────────────────────────

def show_status():
    if not TREE_PATH.exists():
        print("  No wt2_tree.json found. Run --init first.")
        return
    with open(TREE_PATH, encoding="utf-8") as f:
        tree = json.load(f)
    p = tree["progress"]
    print("=== WT2 Bipartite Bridge Scanner Status ===")
    print(f"  Chunks: {p['chunks_completed']}/{p['chunks_total']}")
    print(f"  Papers scanned: {p['papers_scanned']:,}")
    print(f"  Papers with glyphs: {p['papers_with_glyphs']:,}")
    print(f"  Papers with concepts: {p['papers_with_concepts']:,}")
    print(f"  Papers full (both): {p['papers_full']:,}")


# ── MAIN ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="WT2 Scanner — Bipartite bridge S-2↔S0")
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
        print("  No wt2_tree.json found. Run --init first.")
        sys.exit(1)
    with open(TREE_PATH, encoding="utf-8") as f:
        tree = json.load(f)

    # Load registry
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    latex_to_id = reg["latex_to_id"]
    unicode_to_id = reg["unicode_to_id"]

    # Load concept index (all 309 mapper chunks → compact dict)
    arxiv_to_concepts = load_concept_index()

    # Load domain lookup
    domain_lookup, domain_names = load_domain_lookup()

    print(f"  Registry: {reg['meta']['total']} glyphs")
    print(f"  Chunks: {tree['progress']['chunks_completed']}/"
          f"{tree['progress']['chunks_total']}")

    for i in range(args.chunks):
        if not scan_chunk(tree, latex_to_id, unicode_to_id,
                          domain_lookup, domain_names, arxiv_to_concepts):
            print("\n  All chunks complete!")
            break


if __name__ == "__main__":
    main()
