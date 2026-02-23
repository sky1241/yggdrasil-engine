#!/usr/bin/env python3
"""
YGGDRASIL Phase 4 — PLUIE LOCALE
Matrice de co-occurrence concepts depuis OpenAlex snapshot complet.

Stream ~400 GB de .gz, extrait les paires de concepts, construit matrice sparse.
Windows 11, D:/openalex/data/works/

Usage:
    python build_cooccurrence.py                    # run complet
    python build_cooccurrence.py --test 5           # test sur 5 fichiers
    python build_cooccurrence.py --resume            # reprend depuis checkpoint
"""

import gzip
import json
import os
import sys
import time
import glob
import zlib
import argparse
import signal
from pathlib import Path
from collections import defaultdict
from itertools import combinations

import numpy as np
from scipy import sparse

# ─── CONFIG ──────────────────────────────────────────────────────────────────
WORKS_DIR = os.environ.get("YGG_WORKS_DIR", os.path.join("D:", os.sep, "openalex", "data", "works"))
STRATES_PATH = os.environ.get("YGG_STRATES", os.path.join("data", "core", "strates_export_v2.json"))
OPENALEX_MAP_PATH = os.environ.get("YGG_OA_MAP", os.path.join("data", "core", "openalex_map.json"))
OUTPUT_DIR = os.environ.get("YGG_OUTPUT", os.path.join("data", "pluie"))
CHECKPOINT_PATH = os.path.join(OUTPUT_DIR, "_checkpoint.json")

# Seuil minimum de score concept OpenAlex pour inclusion
MIN_CONCEPT_SCORE = 0.3

# ─── SIGNAL HANDLER (Ctrl+C sauvegarde checkpoint) ──────────────────────────
_interrupted = False

def _signal_handler(sig, frame):
    global _interrupted
    print("\n⚡ Interruption détectée — sauvegarde checkpoint en cours...")
    _interrupted = True

signal.signal(signal.SIGINT, _signal_handler)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def load_yggdrasil_concepts(strates_path, openalex_map_path):
    """
    Charge les concepts Yggdrasil et leur mapping OpenAlex.
    Retourne:
        concept_to_idx: dict {openalex_concept_id: matrix_index}
        idx_to_concept: dict {matrix_index: openalex_concept_id}
        idx_to_symbol: dict {matrix_index: symbol_name}
        n_concepts: int
    """
    with open(strates_path, "r", encoding="utf-8") as f:
        strates = json.load(f)
    
    with open(openalex_map_path, "r", encoding="utf-8") as f:
        oa_map = json.load(f)
    
    # Extraire tous les symboles uniques depuis strates
    # strates_export_v2.json: liste de {from, to, strate, ...} ou structure similaire
    symbols = set()
    if isinstance(strates, list):
        for entry in strates:
            if isinstance(entry, dict):
                if "from" in entry:
                    symbols.add(entry["from"])
                if "to" in entry:
                    symbols.add(entry["to"])
            elif isinstance(entry, str):
                symbols.add(entry)
    elif isinstance(strates, dict):
        # Peut être {symbol: {...}, ...} ou {strate: [symbols]}
        for key, val in strates.items():
            if isinstance(val, list):
                symbols.update(val)
            else:
                symbols.add(key)
    
    print(f"📊 {len(symbols)} symboles Yggdrasil chargés")
    
    # Mapper vers OpenAlex IDs
    concept_to_idx = {}
    idx_to_concept = {}
    idx_to_symbol = {}
    idx = 0
    
    unmapped = []
    for symbol in sorted(symbols):
        if symbol in oa_map:
            oa_id = oa_map[symbol]
            # Normaliser: OpenAlex utilise des URLs comme IDs
            # ex: "https://openalex.org/C41008148" ou juste "C41008148"
            if isinstance(oa_id, dict):
                oa_id = oa_id.get("id", oa_id.get("concept_id", ""))
            oa_id = str(oa_id).strip()
            
            if oa_id and oa_id not in concept_to_idx:
                concept_to_idx[oa_id] = idx
                idx_to_concept[idx] = oa_id
                idx_to_symbol[idx] = symbol
                idx += 1
        else:
            unmapped.append(symbol)
    
    n_concepts = len(concept_to_idx)
    print(f"🎯 {n_concepts} concepts mappés vers OpenAlex ({len(unmapped)} non-mappés)")
    if unmapped and len(unmapped) <= 20:
        print(f"   Non-mappés: {unmapped}")
    elif unmapped:
        print(f"   Premiers non-mappés: {unmapped[:10]}...")
    
    return concept_to_idx, idx_to_concept, idx_to_symbol, n_concepts


def discover_gz_files(works_dir):
    """Trouve tous les .gz dans le répertoire works, triés."""
    pattern = os.path.join(works_dir, "**", "*.gz")
    files = sorted(glob.glob(pattern, recursive=True))
    if not files:
        # Essayer structure plate
        pattern = os.path.join(works_dir, "*.gz")
        files = sorted(glob.glob(pattern))
    return files


def stream_papers(gz_path):
    """
    Génère les papers d'un fichier .gz, une par une.
    Chaque ligne = 1 JSON paper.
    Gère les lignes malformées silencieusement.
    """
    try:
        with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue  # Skip malformed lines
    except (gzip.BadGzipFile, EOFError, OSError, zlib.error) as e:
        print(f"  ⚠️  Erreur fichier {os.path.basename(gz_path)}: {e}")


def extract_concept_indices(paper, concept_to_idx, min_score=MIN_CONCEPT_SCORE):
    """
    Extrait les indices de matrice pour les concepts d'un paper.
    Filtre par score minimum et par appartenance à Yggdrasil.
    """
    concepts = paper.get("concepts", [])
    if not concepts:
        return []
    
    indices = []
    for c in concepts:
        score = c.get("score", 0)
        if score < min_score:
            continue
        
        # Essayer plusieurs formats d'ID
        c_id = c.get("id", "")
        if not c_id:
            c_id = c.get("concept_id", "")
        c_id = str(c_id).strip()
        
        if c_id in concept_to_idx:
            indices.append(concept_to_idx[c_id])
    
    return indices


def save_checkpoint(checkpoint_path, processed_files, total_papers, total_pairs, elapsed):
    """Sauvegarde l'état de progression."""
    data = {
        "processed_files": processed_files,
        "total_papers": total_papers,
        "total_pairs": total_pairs,
        "elapsed_seconds": elapsed,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_checkpoint(checkpoint_path):
    """Charge le checkpoint si disponible."""
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ─── MAIN PIPELINE ───────────────────────────────────────────────────────────

def build_cooccurrence_matrix(args):
    """Pipeline principal."""
    
    print("=" * 70)
    print("🌧️  YGGDRASIL PHASE 4 — PLUIE LOCALE")
    print("    Matrice de co-occurrence depuis OpenAlex snapshot")
    print("=" * 70)
    print()
    
    # 1. Charger concepts Yggdrasil
    print("─── ÉTAPE 1: Chargement concepts Yggdrasil ───")
    concept_to_idx, idx_to_concept, idx_to_symbol, n_concepts = \
        load_yggdrasil_concepts(STRATES_PATH, OPENALEX_MAP_PATH)
    print()
    
    if n_concepts == 0:
        print("❌ Aucun concept mappé — vérifier les fichiers de mapping")
        sys.exit(1)
    
    # 2. Découvrir les fichiers .gz
    print("─── ÉTAPE 2: Découverte fichiers OpenAlex ───")
    gz_files = discover_gz_files(WORKS_DIR)
    total_files = len(gz_files)
    print(f"📁 {total_files} fichiers .gz trouvés dans {WORKS_DIR}")
    
    if total_files == 0:
        print("❌ Aucun fichier .gz trouvé")
        sys.exit(1)
    
    if args.test:
        gz_files = gz_files[:args.test]
        print(f"🧪 Mode test: {len(gz_files)} fichiers seulement")
    print()
    
    # 3. Préparer la matrice (COO pour construction, CSR pour stockage)
    print("─── ÉTAPE 3: Construction matrice co-occurrence ───")
    print(f"   Taille: {n_concepts} × {n_concepts}")
    print(f"   Score minimum concept: {MIN_CONCEPT_SCORE}")
    print()
    
    # Accumulateurs pour construction COO sparse
    # On accumule dans un dict pour éviter les doublons COO
    # Format: {(i, j): count}
    # Pour ~5000 concepts, worst case ~12.5M paires — dict tient en RAM
    cooccurrence = defaultdict(int)
    
    # Stats
    total_papers = 0
    papers_with_ygg_concepts = 0
    total_pairs_added = 0
    start_time = time.time()
    
    # Resume support
    skip_files = set()
    if args.resume:
        checkpoint = load_checkpoint(CHECKPOINT_PATH)
        if checkpoint:
            skip_files = set(checkpoint["processed_files"])
            total_papers = checkpoint["total_papers"]
            total_pairs_added = checkpoint["total_pairs"]
            print(f"📂 Reprise: {len(skip_files)} fichiers déjà traités")
            print(f"   Papers: {total_papers:,}, Paires: {total_pairs_added:,}")
            
            # Charger matrice partielle si elle existe
            partial_path = os.path.join(OUTPUT_DIR, "_partial_matrix.npz")
            if os.path.exists(partial_path):
                mat = sparse.load_npz(partial_path)
                # Reconvertir en dict
                cx = mat.tocoo()
                for i, j, v in zip(cx.row, cx.col, cx.data):
                    cooccurrence[(i, j)] = int(v)
                print(f"   Matrice partielle chargée: {len(cooccurrence):,} cellules non-nulles")
            print()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    processed_files = list(skip_files)
    
    # Checkpoint tous les N fichiers
    CHECKPOINT_EVERY = 50
    
    for file_idx, gz_path in enumerate(gz_files):
        if _interrupted:
            break
        
        if gz_path in skip_files:
            continue
        
        file_name = os.path.basename(gz_path)
        file_papers = 0
        file_pairs = 0
        file_start = time.time()
        
        for paper in stream_papers(gz_path):
            total_papers += 1
            file_papers += 1
            
            # Extraire indices concepts Yggdrasil
            indices = extract_concept_indices(paper, concept_to_idx, MIN_CONCEPT_SCORE)
            
            if len(indices) >= 2:
                papers_with_ygg_concepts += 1
                # Toutes les paires (non-ordonnées, symétrique)
                for i, j in combinations(sorted(indices), 2):
                    cooccurrence[(i, j)] += 1
                    cooccurrence[(j, i)] += 1  # Symétrique
                    file_pairs += 1
                    total_pairs_added += 1
                
                # Diagonale = nombre de papers par concept
                for i in indices:
                    cooccurrence[(i, i)] += 1
        
        processed_files.append(gz_path)
        file_elapsed = time.time() - file_start
        
        # Progress
        elapsed = time.time() - start_time
        pct = (file_idx + 1) / len(gz_files) * 100
        papers_per_sec = total_papers / max(elapsed, 1)
        
        # ETA
        if file_idx > 0:
            files_remaining = len(gz_files) - file_idx - 1
            avg_time_per_file = elapsed / (file_idx + 1 - len(skip_files))
            eta_seconds = files_remaining * avg_time_per_file
            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))
        else:
            eta_str = "calcul..."
        
        print(
            f"  [{file_idx+1:>5}/{len(gz_files)}] {pct:5.1f}% | "
            f"{file_name}: {file_papers:>8,} papers, {file_pairs:>6,} paires | "
            f"Total: {total_papers:>10,} papers | "
            f"{papers_per_sec:,.0f} p/s | "
            f"ETA: {eta_str} | "
            f"Cellules: {len(cooccurrence):,}"
        )
        
        # Checkpoint périodique
        if (file_idx + 1) % CHECKPOINT_EVERY == 0:
            print(f"  💾 Checkpoint... ", end="", flush=True)
            save_checkpoint(CHECKPOINT_PATH, processed_files, 
                          total_papers, total_pairs_added, elapsed)
            
            # Sauvegarder matrice partielle
            rows, cols, vals = [], [], []
            for (r, c), v in cooccurrence.items():
                rows.append(r)
                cols.append(c)
                vals.append(v)
            partial_mat = sparse.coo_matrix(
                (vals, (rows, cols)), shape=(n_concepts, n_concepts)
            ).tocsr()
            sparse.save_npz(os.path.join(OUTPUT_DIR, "_partial_matrix.npz"), partial_mat)
            print("OK")
    
    # ─── FINALISATION ────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    
    print()
    print("=" * 70)
    if _interrupted:
        print("⚡ INTERROMPU — checkpoint sauvegardé, reprendre avec --resume")
    else:
        print("✅ SCAN COMPLET")
    print("=" * 70)
    print()
    
    # Stats
    print("─── STATISTIQUES ───")
    print(f"  Papers scannés:          {total_papers:>15,}")
    print(f"  Papers avec ≥2 concepts: {papers_with_ygg_concepts:>15,}")
    print(f"  Paires comptées:         {total_pairs_added:>15,}")
    print(f"  Cellules non-nulles:     {len(cooccurrence):>15,}")
    density = len(cooccurrence) / (n_concepts * n_concepts) * 100
    print(f"  Densité matrice:         {density:>14.2f}%")
    print(f"  Temps total:             {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
    print(f"  Vitesse:                 {total_papers/max(elapsed,1):>12,.0f} papers/s")
    print()
    
    # 4. Construire matrice sparse finale
    print("─── ÉTAPE 4: Export matrice ───")
    rows, cols, vals = [], [], []
    for (r, c), v in cooccurrence.items():
        rows.append(r)
        cols.append(c)
        vals.append(v)
    
    matrix = sparse.coo_matrix(
        (vals, (rows, cols)), shape=(n_concepts, n_concepts)
    ).tocsr()
    
    # Sauvegarder
    matrix_path = os.path.join(OUTPUT_DIR, "cooccurrence_matrix.npz")
    sparse.save_npz(matrix_path, matrix)
    print(f"  💾 Matrice: {matrix_path}")
    print(f"     Shape: {matrix.shape}")
    print(f"     Non-zero: {matrix.nnz:,}")
    print(f"     Taille fichier: {os.path.getsize(matrix_path) / 1024 / 1024:.1f} MB")
    
    # Sauvegarder index mapping
    index_data = {
        "n_concepts": n_concepts,
        "idx_to_concept": {str(k): v for k, v in idx_to_concept.items()},
        "idx_to_symbol": {str(k): v for k, v in idx_to_symbol.items()},
        "concept_to_idx": concept_to_idx,
        "stats": {
            "total_papers": total_papers,
            "papers_with_concepts": papers_with_ygg_concepts,
            "total_pairs": total_pairs_added,
            "density_pct": density,
            "elapsed_seconds": elapsed,
            "min_concept_score": MIN_CONCEPT_SCORE,
            "date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    index_path = os.path.join(OUTPUT_DIR, "matrix_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    print(f"  💾 Index: {index_path}")
    
    # Top co-occurrences
    print()
    print("─── TOP 20 CO-OCCURRENCES ───")
    cx = matrix.tocoo()
    # Filtrer diagonale et doublons (garder i < j)
    mask = cx.row < cx.col
    top_indices = np.argsort(cx.data[mask])[-20:][::-1]
    rows_filtered = cx.row[mask][top_indices]
    cols_filtered = cx.col[mask][top_indices]
    vals_filtered = cx.data[mask][top_indices]
    
    for r, c, v in zip(rows_filtered, cols_filtered, vals_filtered):
        sym_r = idx_to_symbol.get(r, f"?{r}")
        sym_c = idx_to_symbol.get(c, f"?{c}")
        print(f"  {v:>10,} | {sym_r} ↔ {sym_c}")
    
    # Concepts les plus connectés (degré)
    print()
    print("─── TOP 20 CONCEPTS (degré) ───")
    degrees = np.array(matrix.sum(axis=1)).flatten()
    top_degree = np.argsort(degrees)[-20:][::-1]
    for idx in top_degree:
        sym = idx_to_symbol.get(idx, f"?{idx}")
        print(f"  {degrees[idx]:>12,.0f} | {sym}")
    
    # Cleanup checkpoint si terminé
    if not _interrupted:
        for f in [CHECKPOINT_PATH, os.path.join(OUTPUT_DIR, "_partial_matrix.npz")]:
            if os.path.exists(f):
                os.remove(f)
        print()
        print("🌧️  PLUIE TERMINÉE — matrice prête pour injection Yggdrasil")
    
    print()
    return matrix


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yggdrasil Phase 4 — Build co-occurrence matrix")
    parser.add_argument("--test", type=int, default=0, 
                        help="Mode test: ne traiter que N fichiers")
    parser.add_argument("--resume", action="store_true",
                        help="Reprendre depuis le dernier checkpoint")
    parser.add_argument("--min-score", type=float, default=MIN_CONCEPT_SCORE,
                        help=f"Score minimum concept OpenAlex (défaut: {MIN_CONCEPT_SCORE})")
    args = parser.parse_args()
    
    if args.min_score != MIN_CONCEPT_SCORE:
        MIN_CONCEPT_SCORE = args.min_score
    
    build_cooccurrence_matrix(args)
