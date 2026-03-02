#!/usr/bin/env python3
"""
YGGDRASIL — arXiv ↔ OpenAlex Mapper
=====================================
Scanne le snapshot OpenAlex (~692 GB, 1981 fichiers) pour extraire tous les
papers ayant un lien arXiv. Crée un mapping compact:

    arXiv ID → {openalex_id, concepts[], topics[], year, type}

Ce mapping permet de lier les glyphes LaTeX (S-2) extraits des tars arXiv
aux concepts OpenAlex (S0+) pour construire le pont inter-strates.

Structure créée:
    data/scan/
    ├── arxiv_openalex_map.json.gz   Mapping complet (~3M entries)
    └── arxiv_mapper_state.json      État du scan (pour resume)

Usage:
    python arxiv_openalex_mapper.py --init      # Planifie les chunks
    python arxiv_openalex_mapper.py             # Scanne le prochain chunk
    python arxiv_openalex_mapper.py --chunks 50 # Scanne 50 chunks
    python arxiv_openalex_mapper.py --all       # Scanne tout d'un coup
    python arxiv_openalex_mapper.py --status    # Affiche la progression
    python arxiv_openalex_mapper.py --merge     # Fusionne les résultats partiels
"""

import gzip
import json
import os
import re
import sys
import time
import signal
import argparse
from pathlib import Path
from collections import defaultdict

# --- CONFIG -------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent    # yggdrasil-engine/
WORKS_DIR = Path(os.environ.get("YGG_WORKS_DIR", "D:/openalex/data/works"))

SCAN_DIR = ROOT / "data" / "scan"
STATE_PATH = SCAN_DIR / "arxiv_mapper_state.json"
MAP_DIR = SCAN_DIR / "arxiv_map_chunks"
FINAL_MAP_PATH = SCAN_DIR / "arxiv_openalex_map.json.gz"

CHUNK_TARGET_BYTES = 2 * 1024 * 1024 * 1024   # ~2 GB par chunk (plus gros = moins de chunks)

# --- CTRL+C -------------------------------------------------------------------

_interrupted = False

def _on_sigint(sig, frame):
    global _interrupted
    print("\n  [Ctrl+C] On finit le fichier en cours puis on sauvegarde...")
    _interrupted = True

signal.signal(signal.SIGINT, _on_sigint)


# ==============================================================================
#  UTILS
# ==============================================================================

def extract_arxiv_id(paper):
    """Extrait l'arXiv ID d'un paper OpenAlex. Retourne None si pas arXiv."""
    # Méthode 1: ids.arxiv (rare mais direct)
    ids = paper.get("ids", {})
    if "arxiv" in ids:
        return _clean_arxiv_id(ids["arxiv"])

    # Méthode 2: locations[].landing_page_url contient arxiv.org
    for loc in (paper.get("locations") or []):
        landing = loc.get("landing_page_url") or ""
        if "arxiv.org/abs/" in landing:
            return _clean_arxiv_id(landing)
        pdf = loc.get("pdf_url") or ""
        if "arxiv.org/pdf/" in pdf:
            return _clean_arxiv_id(pdf)

    # Méthode 3: DOI contient arxiv
    doi = (ids.get("doi") or "")
    if "arxiv" in doi.lower():
        return _clean_arxiv_id(doi)

    return None


def _clean_arxiv_id(raw):
    """Nettoie un ID arXiv: 'http://arxiv.org/abs/2301.12345v2' → '2301.12345'"""
    # Extraire la partie après /abs/ ou /pdf/
    m = re.search(r'(?:abs|pdf)/(.+?)(?:v\d+)?$', raw)
    if m:
        return m.group(1).strip()
    # DOI style: 10.48550/arxiv.2301.12345
    m = re.search(r'arxiv\.(\d{4}\.\d+)', raw, re.IGNORECASE)
    if m:
        return m.group(1)
    # Old-style: hep-th/9901001
    m = re.search(r'([a-z-]+/\d{7})', raw)
    if m:
        return m.group(1)
    return raw.strip()


def extract_concepts(paper):
    """Extrait les concept IDs avec score >= 0.3."""
    concepts = []
    for c in (paper.get("concepts") or []):
        score = c.get("score", 0)
        if score is None or score < 0.3:
            continue
        cid = c.get("id", "")
        name = c.get("display_name", "")
        if cid:
            concepts.append({"id": cid, "name": name, "score": round(score, 3)})
    return concepts


def extract_topics(paper):
    """Extrait les topics (primary topic + subfield + field + domain)."""
    topics = []
    for t in (paper.get("topics") or []):
        tid = t.get("id", "")
        name = t.get("display_name", "")
        if tid:
            topics.append({"id": tid, "name": name})
    return topics


# ==============================================================================
#  INIT — planifier les chunks
# ==============================================================================

def discover_gz_files():
    """Trouve tous les .gz dans works/."""
    all_gz = sorted(WORKS_DIR.rglob("*.gz"))
    valid = [f for f in all_gz if f.name.endswith(".gz")]
    return valid


def init_mapper():
    """Point d'entrée --init: planifie les chunks."""
    print("=" * 60)
    print("  INIT: arXiv ↔ OpenAlex Mapper")
    print("=" * 60)

    gz_files = discover_gz_files()
    total_bytes = sum(f.stat().st_size for f in gz_files)
    print(f"  {len(gz_files):,} fichiers, {total_bytes / 1024**3:.1f} GB")

    rel_paths = [str(f.relative_to(WORKS_DIR)) for f in gz_files]
    file_sizes = {str(f.relative_to(WORKS_DIR)): f.stat().st_size for f in gz_files}

    # Planifier les chunks
    chunks = []
    chunk_files = []
    chunk_bytes = 0
    chunk_id = 1

    for rp in rel_paths:
        fsize = file_sizes[rp]
        chunk_files.append(rp)
        chunk_bytes += fsize

        if chunk_bytes >= CHUNK_TARGET_BYTES:
            chunks.append({
                "id": chunk_id,
                "files": list(chunk_files),
                "bytes": chunk_bytes,
                "status": "pending",
            })
            chunk_id += 1
            chunk_files = []
            chunk_bytes = 0

    if chunk_files:
        chunks.append({
            "id": chunk_id,
            "files": list(chunk_files),
            "bytes": chunk_bytes,
            "status": "pending",
        })

    os.makedirs(MAP_DIR, exist_ok=True)

    state = {
        "version": 1,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "chunk_target_bytes": CHUNK_TARGET_BYTES,
            "works_dir": str(WORKS_DIR),
        },
        "files": {
            "total": len(gz_files),
            "total_bytes": total_bytes,
        },
        "progress": {
            "chunks_total": len(chunks),
            "chunks_completed": 0,
            "papers_scanned": 0,
            "arxiv_found": 0,
        },
        "chunks": chunks,
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"  MAPPER PRÊT")
    print(f"  {len(gz_files):,} fichiers -> {len(chunks)} chunks x ~2 GB")
    print(f"  État: {STATE_PATH}")
    print(f"\n  Prochain: python {Path(__file__).name} --chunks 1")
    print(f"{'=' * 60}")


# ==============================================================================
#  SCAN — lire un chunk, extraire les papers arXiv
# ==============================================================================

def load_state():
    if not STATE_PATH.exists():
        print("  Pas de arxiv_mapper_state.json. Lancer --init d'abord.")
        sys.exit(1)
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def scan_chunk(state):
    """Scanne le prochain chunk pending. Retourne True s'il en reste."""

    chunk = None
    for c in state["chunks"]:
        if c["status"] == "pending":
            chunk = c
            break

    if chunk is None:
        print("  Tous les chunks sont déjà scannés!")
        return False

    cid = chunk["id"]
    n_total = state["progress"]["chunks_total"]
    works_dir = Path(state["config"]["works_dir"])

    print(f"\n{'=' * 60}")
    print(f"  CHUNK {cid}/{n_total}")
    print(f"  {len(chunk['files'])} fichiers, {chunk['bytes'] / 1024**3:.2f} GB")
    print(f"{'=' * 60}")

    chunk["status"] = "scanning"
    save_state(state)

    # Accumulateur pour ce chunk
    arxiv_papers = {}  # arxiv_id → {info}

    papers_total = 0
    arxiv_found = 0
    t_start = time.time()

    for fi, rel_path in enumerate(chunk["files"]):
        if _interrupted:
            break

        gz_path = works_dir / rel_path

        if not gz_path.exists():
            print(f"  !! {rel_path} introuvable, skip")
            continue

        fp = 0
        fa = 0
        t_file = time.time()

        try:
            with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        paper = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    papers_total += 1
                    fp += 1

                    # Skip erratum/retraction
                    ptype = paper.get("type", "")
                    if ptype in ("erratum", "retraction") or paper.get("is_retracted"):
                        continue

                    arxiv_id = extract_arxiv_id(paper)
                    if not arxiv_id:
                        continue

                    arxiv_found += 1
                    fa += 1

                    # Extraire les infos utiles
                    ids = paper.get("ids", {})
                    concepts = extract_concepts(paper)
                    topics = extract_topics(paper)
                    year = paper.get("publication_year")

                    arxiv_papers[arxiv_id] = {
                        "openalex": ids.get("openalex", ""),
                        "year": year,
                        "type": ptype,
                        "concepts": concepts,
                        "topics": topics,
                    }

        except (IOError, EOFError, OSError) as e:
            print(f"  !! Erreur {rel_path}: {e}")
            continue

        dt = time.time() - t_file
        rate = fp / dt if dt > 0 else 0
        print(f"  [{fi+1}/{len(chunk['files'])}] {rel_path}: "
              f"{fp:,} papers, {fa:,} arXiv ({rate:.0f} p/s)")

    # Sauvegarder le chunk
    elapsed = time.time() - t_start
    chunk_dir = MAP_DIR / f"chunk_{cid:03d}"
    os.makedirs(chunk_dir, exist_ok=True)

    # Sauvegarder le mapping partiel
    with gzip.open(chunk_dir / "map.json.gz", "wt", encoding="utf-8") as f:
        json.dump(arxiv_papers, f, ensure_ascii=False)

    # Meta
    meta = {
        "id": cid,
        "files": chunk["files"],
        "status": "complete",
        "papers_total": papers_total,
        "arxiv_found": arxiv_found,
        "scan_time_sec": round(elapsed, 1),
        "papers_per_sec": round(papers_total / elapsed, 1) if elapsed > 0 else 0,
    }
    with open(chunk_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Mettre à jour l'état
    chunk["status"] = "complete"
    state["progress"]["chunks_completed"] += 1
    state["progress"]["papers_scanned"] += papers_total
    state["progress"]["arxiv_found"] += arxiv_found
    save_state(state)

    rate = papers_total / elapsed if elapsed > 0 else 0
    print(f"\n  Chunk {cid} terminé: {papers_total:,} papers, "
          f"{arxiv_found:,} arXiv ({elapsed:.0f}s, {rate:.0f} p/s)")

    # Vérifier s'il reste des chunks
    remaining = sum(1 for c in state["chunks"] if c["status"] == "pending")
    if remaining > 0:
        pct = 100 * state["progress"]["chunks_completed"] / state["progress"]["chunks_total"]
        print(f"  Progression: {state['progress']['chunks_completed']}/{state['progress']['chunks_total']} ({pct:.0f}%)")
        print(f"  arXiv trouvés: {state['progress']['arxiv_found']:,}")
        return True
    else:
        print(f"\n  SCAN TERMINÉ!")
        print(f"  Total: {state['progress']['papers_scanned']:,} papers scannés")
        print(f"  arXiv: {state['progress']['arxiv_found']:,} papers trouvés")
        return False


# ==============================================================================
#  MERGE — fusionner les chunks en un seul mapping
# ==============================================================================

def merge_chunks():
    """Fusionne tous les chunks en un seul fichier compressé."""
    state = load_state()
    completed = [c for c in state["chunks"] if c["status"] == "complete"]
    print(f"  Fusion de {len(completed)} chunks...")

    merged = {}
    for chunk in completed:
        chunk_dir = MAP_DIR / f"chunk_{chunk['id']:03d}"
        map_path = chunk_dir / "map.json.gz"
        if map_path.exists():
            with gzip.open(map_path, "rt", encoding="utf-8") as f:
                partial = json.load(f)
            merged.update(partial)
            print(f"  chunk_{chunk['id']:03d}: {len(partial):,} entries")

    # Stats par année
    by_year = defaultdict(int)
    for aid, info in merged.items():
        y = info.get("year")
        if y:
            by_year[y] += 1

    # Sauvegarder
    print(f"\n  Écriture de {len(merged):,} entries -> {FINAL_MAP_PATH.name}")
    with gzip.open(FINAL_MAP_PATH, "wt", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "total": len(merged),
                "by_year": dict(sorted(by_year.items())),
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source": "OpenAlex snapshot",
            },
            "mapping": merged,
        }, f, ensure_ascii=False)

    sz = os.path.getsize(FINAL_MAP_PATH) / 1024 / 1024
    print(f"  Taille: {sz:.1f} MB")
    print(f"  Années: {min(by_year.keys())} → {max(by_year.keys())}")
    print(f"\n  Top 10 années:")
    for y, c in sorted(by_year.items(), key=lambda x: -x[1])[:10]:
        print(f"    {y}: {c:,}")


# ==============================================================================
#  STATUS
# ==============================================================================

def show_status():
    state = load_state()
    p = state["progress"]
    total = p["chunks_total"]
    done = p["chunks_completed"]
    pct = 100 * done / total if total > 0 else 0

    print(f"  arXiv ↔ OpenAlex Mapper")
    print(f"  Chunks: {done}/{total} ({pct:.0f}%)")
    print(f"  Papers scannés: {p['papers_scanned']:,}")
    print(f"  arXiv trouvés: {p['arxiv_found']:,}")
    if p["papers_scanned"] > 0:
        rate = p["arxiv_found"] / p["papers_scanned"] * 100
        print(f"  Taux arXiv: {rate:.2f}%")
        est_total = int(478_000_000 * rate / 100)
        print(f"  Estimation finale: ~{est_total:,} papers arXiv")

    remaining = total - done
    if done > 0 and remaining > 0:
        # Estimer le temps restant
        chunks_meta = []
        for c in state["chunks"]:
            if c["status"] == "complete":
                chunk_dir = MAP_DIR / f"chunk_{c['id']:03d}"
                meta_path = chunk_dir / "meta.json"
                if meta_path.exists():
                    with open(meta_path, encoding="utf-8") as f:
                        m = json.load(f)
                    chunks_meta.append(m.get("scan_time_sec", 0))
        if chunks_meta:
            avg_time = sum(chunks_meta) / len(chunks_meta)
            eta_sec = avg_time * remaining
            eta_h = eta_sec / 3600
            print(f"  Temps moyen/chunk: {avg_time:.0f}s")
            print(f"  ETA: ~{eta_h:.1f}h")


# ==============================================================================
#  MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="arXiv ↔ OpenAlex Mapper")
    parser.add_argument("--init", action="store_true", help="Planifie les chunks")
    parser.add_argument("--chunks", type=int, default=1, help="Nombre de chunks à scanner")
    parser.add_argument("--all", action="store_true", help="Scanne tout")
    parser.add_argument("--status", action="store_true", help="Affiche la progression")
    parser.add_argument("--merge", action="store_true", help="Fusionne les résultats")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.init:
        init_mapper()
        return

    if args.merge:
        merge_chunks()
        return

    state = load_state()
    max_chunks = args.chunks if not args.all else 99999

    for i in range(max_chunks):
        if _interrupted:
            print("\n  Interrompu. Reprendre avec: python arxiv_openalex_mapper.py --chunks N")
            break
        if not scan_chunk(state):
            break

    # Auto-merge si tout est fini
    remaining = sum(1 for c in state["chunks"] if c["status"] == "pending")
    if remaining == 0:
        print("\n  Tous les chunks sont scannés. Fusion automatique...")
        merge_chunks()


if __name__ == "__main__":
    main()
