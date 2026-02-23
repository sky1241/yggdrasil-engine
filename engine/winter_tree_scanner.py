#!/usr/bin/env python3
"""
YGGDRASIL — Winter Tree Scanner
================================
Scanne le snapshot OpenAlex (~467 GB, 1492 fichiers) par chunks de ~1 GB.
Indexe les co-occurrences des 65,026 concepts par annee/mois dans un winter-tree.

Structure creee:
    data/scan/
    +-- winter_tree.json          Index principal (annees, chunks, stats)
    +-- concepts_65k.json         Lookup concept_id -> {idx, name, level}
    +-- chunks/
        +-- chunk_001/
        |   +-- meta.json         Stats du chunk
        |   +-- cooc.json.gz      Co-occurrences {annee: {paire: count}}
        |   +-- activity.json.gz  Activite {annee: {concept: count}}
        +-- chunk_002/
        +-- ...

Usage:
    python winter_tree_scanner.py --init           # Construit lookup + planifie chunks
    python winter_tree_scanner.py                  # Scanne le prochain chunk
    python winter_tree_scanner.py --chunks 5       # Scanne 5 chunks
    python winter_tree_scanner.py --status         # Affiche la progression
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

ROOT = Path(__file__).resolve().parent.parent          # yggdrasil-engine/
WORKS_DIR = Path(os.environ.get("YGG_WORKS_DIR", "D:/openalex/data/works"))
CONCEPTS_DIR = Path(os.environ.get("YGG_CONCEPTS_DIR", "D:/openalex/data/concepts"))

SCAN_DIR = ROOT / "data" / "scan"
TREE_PATH = SCAN_DIR / "winter_tree.json"
CONCEPTS_PATH = SCAN_DIR / "concepts_65k.json"
CHUNKS_DIR = SCAN_DIR / "chunks"

CHUNK_TARGET_BYTES = 1 * 1024 * 1024 * 1024   # ~1 GB par chunk
MIN_CONCEPT_SCORE = 0.3
MONTH_FROM_YEAR = 1980                          # mois par mois a partir de 1980

# --- CTRL+C -------------------------------------------------------------------

_interrupted = False

def _on_sigint(sig, frame):
    global _interrupted
    print("\n  [Ctrl+C] On finit le fichier en cours puis on sauvegarde...")
    _interrupted = True

signal.signal(signal.SIGINT, _on_sigint)


# ==============================================================================
#  INIT — construire le lookup 65K + planifier les chunks
# ==============================================================================

def build_concept_lookup():
    """Lit les 65K concepts du snapshot OpenAlex -> concepts_65k.json"""
    print("=" * 60)
    print("  INIT: chargement des 65K concepts OpenAlex")
    print("=" * 60)

    concept_files = sorted(CONCEPTS_DIR.rglob("*.gz"))
    if not concept_files:
        print(f"  PAS DE FICHIERS dans {CONCEPTS_DIR}")
        sys.exit(1)
    print(f"  {len(concept_files)} fichiers concepts trouves")

    concepts = {}
    idx = 0
    by_level = defaultdict(int)

    for cf in concept_files:
        with gzip.open(cf, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                cid = d.get("id", "")
                name = d.get("display_name", "")
                level = d.get("level", -1)
                wc = d.get("works_count", 0)
                if cid and name:
                    concepts[cid] = {
                        "idx": idx,
                        "name": name,
                        "level": level,
                        "works_count": wc,
                    }
                    by_level[level] += 1
                    idx += 1

    os.makedirs(SCAN_DIR, exist_ok=True)

    payload = {
        "meta": {
            "total": len(concepts),
            "by_level": dict(sorted(by_level.items())),
            "source": str(CONCEPTS_DIR),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "concepts": concepts,
    }
    with open(CONCEPTS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    sz = os.path.getsize(CONCEPTS_PATH) / 1024 / 1024
    print(f"  {len(concepts):,} concepts -> {CONCEPTS_PATH.name} ({sz:.1f} MB)")
    print(f"  Par level: {dict(sorted(by_level.items()))}")
    return concepts


def discover_gz_files():
    """Trouve tous les .gz complets dans works/ (exclut les downloads partiels)."""
    all_gz = sorted(WORKS_DIR.rglob("*.gz"))
    valid = [f for f in all_gz if re.match(r"^part_\d+\.gz$", f.name)]
    return valid


def init_tree():
    """Point d'entree --init: lookup concepts + plan des chunks."""
    concepts = build_concept_lookup()

    print(f"\n  Scan de {WORKS_DIR}...")
    gz_files = discover_gz_files()
    total_bytes = sum(f.stat().st_size for f in gz_files)
    print(f"  {len(gz_files):,} fichiers, {total_bytes / 1024**3:.1f} GB")

    # Chemins relatifs depuis WORKS_DIR pour portabilite
    rel_paths = [str(f.relative_to(WORKS_DIR)) for f in gz_files]
    file_sizes = {str(f.relative_to(WORKS_DIR)): f.stat().st_size for f in gz_files}

    # Planifier les chunks (~1 GB chacun)
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

    os.makedirs(CHUNKS_DIR, exist_ok=True)

    tree = {
        "version": 1,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "concept_count": len(concepts),
            "chunk_target_bytes": CHUNK_TARGET_BYTES,
            "min_concept_score": MIN_CONCEPT_SCORE,
            "month_from_year": MONTH_FROM_YEAR,
            "works_dir": str(WORKS_DIR),
        },
        "files": {
            "total": len(gz_files),
            "total_bytes": total_bytes,
            "dirs": len(set(str(f.parent) for f in gz_files)),
        },
        "progress": {
            "chunks_total": len(chunks),
            "chunks_completed": 0,
            "papers_scanned": 0,
            "papers_with_concepts": 0,
            "pairs_counted": 0,
        },
        "years": {},
        "chunks": chunks,
    }

    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"  WINTER TREE PRET")
    print(f"  {len(concepts):,} concepts")
    print(f"  {len(gz_files):,} fichiers -> {len(chunks)} chunks x ~1 GB")
    print(f"  Arbre: {TREE_PATH}")
    print(f"\n  Prochain: python {Path(__file__).name} --chunks 1")
    print(f"{'=' * 60}")


# ==============================================================================
#  SCAN — lire un chunk, indexer dans l'arbre
# ==============================================================================

def load_concepts():
    """Charge le lookup concept_id -> index entier."""
    if not CONCEPTS_PATH.exists():
        print("  Pas de concepts_65k.json. Lancer --init d'abord.")
        sys.exit(1)
    with open(CONCEPTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    cid_to_idx = {cid: info["idx"] for cid, info in data["concepts"].items()}
    print(f"  {len(cid_to_idx):,} concepts charges")
    return cid_to_idx


def load_tree():
    """Charge le winter tree."""
    if not TREE_PATH.exists():
        print("  Pas de winter_tree.json. Lancer --init d'abord.")
        sys.exit(1)
    with open(TREE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tree(tree):
    """Sauvegarde le winter tree."""
    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)


def time_key(paper):
    """Extrait la cle temporelle: 'YYYY-MM' si >= 1980, sinon 'YYYY'."""
    pub_year = paper.get("publication_year")
    if not pub_year:
        return None
    year = int(pub_year)
    if year >= MONTH_FROM_YEAR:
        pub_date = paper.get("publication_date", "")
        if pub_date and len(pub_date) >= 7:
            return pub_date[:7]   # "2019-03"
    return str(year)              # "1950"


def scan_chunk(tree, cid_to_idx):
    """Scanne le prochain chunk pending. Retourne True s'il en reste."""

    # Trouver le prochain chunk pending
    chunk = None
    for c in tree["chunks"]:
        if c["status"] == "pending":
            chunk = c
            break

    if chunk is None:
        print("  Tous les chunks sont deja scannes!")
        return False

    cid = chunk["id"]
    n_total = tree["progress"]["chunks_total"]
    works_dir = Path(tree["config"]["works_dir"])

    print(f"\n{'=' * 60}")
    print(f"  CHUNK {cid}/{n_total}")
    print(f"  {len(chunk['files'])} fichiers, {chunk['bytes'] / 1024**3:.2f} GB")
    print(f"  {chunk['files'][0]}  ->  {chunk['files'][-1]}")
    print(f"{'=' * 60}")

    chunk["status"] = "scanning"
    save_tree(tree)

    # -- Accumulateurs --
    # cooc[time_key][(a, b)] = count   (a < b toujours)
    cooc = defaultdict(lambda: defaultdict(int))
    # activity[time_key][concept_idx] = paper_count
    activity = defaultdict(lambda: defaultdict(int))
    # papers par periode
    period_papers = defaultdict(int)

    papers_total = 0
    papers_matched = 0
    pairs_total = 0
    t_start = time.time()

    for fi, rel_path in enumerate(chunk["files"]):
        if _interrupted:
            break

        gz_path = works_dir / rel_path

        if not gz_path.exists():
            print(f"  !! {rel_path} introuvable, skip")
            continue

        fp = 0   # file papers
        fm = 0   # file matched
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

                    tk = time_key(paper)
                    if not tk:
                        continue

                    concepts_raw = paper.get("concepts") or []
                    indices = []
                    for c in concepts_raw:
                        score = c.get("score", 0)
                        if score is None or score < MIN_CONCEPT_SCORE:
                            continue
                        c_id = c.get("id", "")
                        if c_id in cid_to_idx:
                            indices.append(cid_to_idx[c_id])

                    if not indices:
                        continue

                    papers_matched += 1
                    fm += 1
                    period_papers[tk] += 1

                    # Activite par concept
                    for idx in indices:
                        activity[tk][idx] += 1

                    # Co-occurrences (toutes les paires)
                    if len(indices) >= 2:
                        unique = sorted(set(indices))
                        for i in range(len(unique)):
                            for j in range(i + 1, len(unique)):
                                cooc[tk][(unique[i], unique[j])] += 1
                                pairs_total += 1

        except (gzip.BadGzipFile, EOFError, OSError, Exception) as e:
            print(f"  !! Erreur {rel_path}: {e}")

        dt = time.time() - t_file
        rate = fp / max(dt, 0.01)
        elapsed = time.time() - t_start
        print(f"  [{fi+1}/{len(chunk['files'])}] {Path(rel_path).name}: "
              f"{fp:,} papers ({fm:,} matched) "
              f"{rate:,.0f} p/s  [{elapsed:.0f}s total]")

    elapsed = time.time() - t_start

    # -- Sauvegarder les donnees du chunk --
    chunk_dir = CHUNKS_DIR / f"chunk_{cid:03d}"
    os.makedirs(chunk_dir, exist_ok=True)

    # Co-occurrences -> JSON gzippe
    cooc_out = {}
    for tk, pairs in cooc.items():
        cooc_out[tk] = {f"{a}|{b}": cnt for (a, b), cnt in pairs.items()}

    with gzip.open(chunk_dir / "cooc.json.gz", "wt", encoding="utf-8") as f:
        json.dump(cooc_out, f, ensure_ascii=False)

    # Activite -> JSON gzippe
    act_out = {}
    for tk, concepts in activity.items():
        act_out[tk] = {str(idx): cnt for idx, cnt in concepts.items()}

    with gzip.open(chunk_dir / "activity.json.gz", "wt", encoding="utf-8") as f:
        json.dump(act_out, f, ensure_ascii=False)

    # Meta du chunk
    periods_list = sorted(period_papers.keys())
    meta = {
        "id": cid,
        "files": chunk["files"],
        "status": "interrupted" if _interrupted else "complete",
        "papers_total": papers_total,
        "papers_matched": papers_matched,
        "pairs_counted": pairs_total,
        "unique_pairs": sum(len(p) for p in cooc.values()),
        "periods_seen": periods_list,
        "period_papers": dict(period_papers),
        "active_concepts": len(set(
            idx for tk in activity for idx in activity[tk]
        )),
        "scan_time_sec": round(elapsed, 1),
        "papers_per_sec": round(papers_total / max(elapsed, 1)),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(chunk_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # -- Mettre a jour le winter tree --
    chunk["status"] = "interrupted" if _interrupted else "complete"
    chunk["papers"] = papers_total
    chunk["matched"] = papers_matched
    chunk["pairs"] = pairs_total
    chunk["periods"] = len(periods_list)
    chunk["time_sec"] = round(elapsed, 1)
    chunk["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if periods_list:
        chunk["year_range"] = [periods_list[0], periods_list[-1]]

    if chunk["status"] == "complete":
        tree["progress"]["chunks_completed"] += 1
    tree["progress"]["papers_scanned"] += papers_total
    tree["progress"]["papers_with_concepts"] += papers_matched
    tree["progress"]["pairs_counted"] += pairs_total

    # Mise a jour des stats par annee dans l'arbre
    for tk, count in period_papers.items():
        if tk not in tree["years"]:
            tree["years"][tk] = {"papers": 0, "chunks": []}
        tree["years"][tk]["papers"] += count
        tree["years"][tk]["chunks"].append(cid)

    save_tree(tree)

    # -- Rapport --
    done = tree["progress"]["chunks_completed"]
    total_p = tree["progress"]["papers_scanned"]

    print(f"\n{'=' * 60}")
    tag = "OK" if chunk["status"] == "complete" else "INTERROMPU"
    print(f"  [{tag}] Chunk {cid}: {papers_total:,} papers, "
          f"{pairs_total:,} paires, {len(periods_list)} periodes")
    print(f"  Progression: {done}/{n_total} chunks, {total_p:,} papers total")
    print(f"  Temps: {elapsed:.0f}s ({papers_total / max(elapsed, 1):,.0f} p/s)")

    for fname in ["cooc.json.gz", "activity.json.gz", "meta.json"]:
        fpath = chunk_dir / fname
        if fpath.exists():
            sz = os.path.getsize(fpath)
            if sz > 1024 * 1024:
                print(f"  -> {fname}: {sz / 1024 / 1024:.1f} MB")
            else:
                print(f"  -> {fname}: {sz / 1024:.0f} KB")

    print(f"{'=' * 60}")
    return not _interrupted


# ==============================================================================
#  STATUS — afficher l'etat de l'arbre
# ==============================================================================

def show_status():
    """Affiche l'etat du winter tree."""
    tree = load_tree()
    p = tree["progress"]
    done = p["chunks_completed"]
    total = p["chunks_total"]
    pct = done / total * 100 if total else 0

    print(f"\n{'=' * 60}")
    print(f"  WINTER TREE")
    print(f"{'=' * 60}")
    print(f"  Concepts:  {tree['config']['concept_count']:,}")
    print(f"  Fichiers:  {tree['files']['total']:,} "
          f"({tree['files']['total_bytes'] / 1024**3:.1f} GB)")
    print(f"  Chunks:    {done}/{total} ({pct:.1f}%)")
    print(f"  Papers:    {p['papers_scanned']:,} "
          f"({p['papers_with_concepts']:,} avec concepts)")
    print(f"  Paires:    {p['pairs_counted']:,}")

    years = tree.get("years", {})
    if years:
        sorted_yrs = sorted(years.keys())
        print(f"  Periodes:  {len(years)} "
              f"({sorted_yrs[0]} -> {sorted_yrs[-1]})")

        # Top 10 par papers
        top = sorted(years.items(), key=lambda x: -x[1]["papers"])[:15]
        print(f"\n  Top 15 periodes:")
        for yk, stats in top:
            bar = "#" * min(40, stats["papers"] // max(1, top[0][1]["papers"] // 40))
            print(f"    {yk:>7}: {stats['papers']:>10,} papers  "
                  f"({len(stats['chunks'])} chunks)  {bar}")

    # Prochain chunk
    for c in tree["chunks"]:
        if c["status"] == "pending":
            print(f"\n  Prochain: chunk {c['id']} "
                  f"({len(c['files'])} fichiers, "
                  f"{c['bytes'] / 1024**3:.2f} GB)")
            break
    else:
        if done == total:
            print(f"\n  SCAN COMPLET!")

    print(f"{'=' * 60}")


# ==============================================================================
#  MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Yggdrasil Winter Tree Scanner - 65K concepts x annee/mois"
    )
    parser.add_argument("--init", action="store_true",
                        help="Construire le lookup concepts + planifier les chunks")
    parser.add_argument("--status", action="store_true",
                        help="Afficher la progression")
    parser.add_argument("--chunks", type=int, default=1,
                        help="Nombre de chunks a scanner (defaut: 1)")
    args = parser.parse_args()

    if args.init:
        init_tree()
        return

    if args.status:
        show_status()
        return

    # Mode scan
    tree = load_tree()
    cid_to_idx = load_concepts()

    for i in range(args.chunks):
        if _interrupted:
            break
        more = scan_chunk(tree, cid_to_idx)
        if not more:
            break

    show_status()


if __name__ == "__main__":
    main()
