#!/usr/bin/env python3
"""
YGGDRASIL ENGINE -- Co-occurrence Scan v4 (STREAMING + MULTIPROCESS)
Scanne 283M papers OpenAlex pour extraire les co-occurrences de domaines.

OPTIMIZATIONS:
  - Regex on raw bytes (no json.loads)
  - Streaming gzip (no bulk decompress = low memory)
  - Multiprocessing 2 workers (safe for 4.7 GB RAM)
  - ETA based on papers processed, not files
"""
import json, gzip, re, time, random, sys, os
import numpy as np
from pathlib import Path
from multiprocessing import Pool

ROOT = Path(__file__).parent.parent.parent
WORKS_DIR = Path("D:/openalex/data/works")
N_WORKERS = 2

# Regex at module level (available after fork/spawn)
CONCEPT_RE = re.compile(
    rb'"id"\s*:\s*"(https://openalex\.org/C\d+)"[^}]*?"score"\s*:\s*([\d.]+)'
)


def process_file(args):
    """Process a single .gz file with streaming gzip. Returns partial results."""
    gz_path, cid_to_domain, dom_idx, N = args

    matrix = np.zeros((N, N), dtype=np.int64)
    dpc = np.zeros(N, dtype=np.int64)
    papers_total = 0
    papers_matched = 0

    try:
        with gzip.open(gz_path, 'rb') as f:
            for line in f:
                if not line.strip():
                    continue
                papers_total += 1

                matches = CONCEPT_RE.findall(line)
                if not matches:
                    continue

                paper_domains = set()
                for cid_bytes, score_bytes in matches:
                    try:
                        score = float(score_bytes)
                    except ValueError:
                        continue
                    if score >= 0.3:
                        cid = cid_bytes.decode()
                        domain = cid_to_domain.get(cid)
                        if domain:
                            paper_domains.add(domain)

                if not paper_domains:
                    continue

                papers_matched += 1

                for d in paper_domains:
                    dpc[dom_idx[d]] += 1

                if len(paper_domains) >= 2:
                    pd_list = sorted(paper_domains)
                    for i, d1 in enumerate(pd_list):
                        for d2 in pd_list[i+1:]:
                            a, b = dom_idx[d1], dom_idx[d2]
                            matrix[a][b] += 1
                            matrix[b][a] += 1

    except Exception as e:
        return matrix, dpc, papers_total, papers_matched, 1, str(e)

    return matrix, dpc, papers_total, papers_matched, 0, ""


def main():
    print("=" * 60)
    print(f"YGGDRASIL -- CO-OCCURRENCE SCAN v4 -- {N_WORKERS} WORKERS")
    print("=" * 60)
    t_global = time.time()

    # ================================================================
    # ETAPE 1
    # ================================================================
    print("\n[ETAPE 1] Preparer le lookup...")
    t0 = time.time()

    with open(ROOT / 'data' / 'core' / 'mined_concepts.json', encoding='utf-8') as f:
        mined = json.load(f)['concepts']

    cid_to_domain = {}
    for c in mined:
        cid_to_domain[c['concept_id']] = c['domain']

    domains = sorted(set(cid_to_domain.values()))
    dom_idx = {d: i for i, d in enumerate(domains)}
    N = len(domains)
    print(f"  Concepts: {len(cid_to_domain)}, Domaines: {N}")
    print(f"  Temps: {time.time()-t0:.1f}s")

    # ================================================================
    # ETAPE 2
    # ================================================================
    print(f"\n[ETAPE 2] Scanner les works ({N_WORKERS} workers, streaming)...")
    t1 = time.time()

    gz_files = sorted(WORKS_DIR.rglob("*.gz"))
    n_gz = len(gz_files)
    print(f"  Fichiers: {n_gz}")

    args_list = [(str(gz), cid_to_domain, dom_idx, N) for gz in gz_files]

    matrix = np.zeros((N, N), dtype=np.int64)
    domain_paper_count = np.zeros(N, dtype=np.int64)
    papers_total = 0
    papers_matched = 0
    errors = 0
    error_msgs = []
    files_done = 0

    with Pool(processes=N_WORKERS) as pool:
        for result in pool.imap_unordered(process_file, args_list, chunksize=2):
            m, dpc, pt, pm, err, msg = result
            matrix += m
            domain_paper_count += dpc
            papers_total += pt
            papers_matched += pm
            errors += err
            if msg:
                error_msgs.append(msg)
            files_done += 1

            if files_done % 20 == 0:
                pct = files_done / n_gz * 100
                elapsed = time.time() - t1
                rate = papers_total / elapsed if elapsed > 0 else 0
                # ETA based on papers rate and estimated total (283M)
                est_total = 283_000_000
                if papers_total > 0:
                    eta_papers = (est_total - papers_total) / rate if rate > 0 else 0
                else:
                    eta_papers = 0
                print(f"  [{pct:5.1f}%] {files_done}/{n_gz} | "
                      f"{papers_total:,} papers | {papers_matched:,} matches | "
                      f"{errors} err | {rate:,.0f} p/s | ETA ~{eta_papers/60:.0f}min",
                      flush=True)

    scan_time = time.time() - t1
    print(f"\n  {'='*60}")
    print(f"  SCAN TERMINE en {scan_time:.0f}s ({scan_time/60:.1f} min)")
    print(f"  Papers scannes:    {papers_total:,}")
    print(f"  Papers matches:    {papers_matched:,} ({papers_matched/max(1,papers_total)*100:.1f}%)")
    print(f"  Erreurs:           {errors}")
    if error_msgs:
        print(f"  Erreurs detail (first 5):")
        for msg in error_msgs[:5]:
            print(f"    {msg[:100]}")

    # ================================================================
    # ETAPE 3
    # ================================================================
    print(f"\n[ETAPE 3] Sauvegarder la matrice...")
    t2 = time.time()

    np.save(ROOT / 'data' / 'topology' / 'domain_cooccurrence_matrix.npy', matrix)
    np.save(ROOT / 'data' / 'topology' / 'domain_paper_counts.npy', domain_paper_count)

    with open(ROOT / 'data' / 'topology' / 'domain_cooccurrence_matrix.json', 'w', encoding='utf-8') as f:
        json.dump({
            'domains': domains,
            'matrix': matrix.tolist(),
            'domain_paper_count': domain_paper_count.tolist(),
            'papers_total': papers_total,
            'papers_matched': papers_matched,
        }, f, ensure_ascii=False)

    print(f"  Matrice sauvegardee. Temps: {time.time()-t2:.1f}s")

    # ================================================================
    # ETAPE 4
    # ================================================================
    print(f"\n[ETAPE 4] Resultats de la matrice...")

    print("\n  TOP 20 CONNEXIONS:")
    pairs = []
    for i in range(N):
        for j in range(i+1, N):
            pairs.append((domains[i], domains[j], int(matrix[i][j])))
    pairs.sort(key=lambda x: -x[2])
    for d1, d2, count in pairs[:20]:
        print(f"    {d1:25s} x {d2:25s} = {count:>12,}")

    print("\n  TROUS (0 connexion entre domaines actifs, seuil 100 papers):")
    active_threshold = 100
    hole_count = 0
    for d1, d2, count in sorted(pairs, key=lambda x: x[2]):
        if count > 0:
            break
        i1, i2 = dom_idx[d1], dom_idx[d2]
        if domain_paper_count[i1] >= active_threshold and domain_paper_count[i2] >= active_threshold:
            print(f"    {d1:25s} ({domain_paper_count[i1]:,}) x {d2:25s} ({domain_paper_count[i2]:,}) = 0")
            hole_count += 1
            if hole_count >= 20:
                print(f"    ... (limite 20)")
                break
    if hole_count == 0:
        print(f"    Aucun trou entre domaines actifs (>{active_threshold} papers)")

    total_pairs = N * (N-1) // 2
    nonzero = sum(1 for _, _, c in pairs if c > 0)
    print(f"\n  Densite: {nonzero}/{total_pairs} paires non-nulles ({nonzero/total_pairs*100:.1f}%)")

    print("\n  PAPERS PAR DOMAINE (top 15):")
    for i in np.argsort(-domain_paper_count)[:15]:
        print(f"    {domains[i]:25s} {domain_paper_count[i]:>12,} papers")

    # ================================================================
    # ETAPE 5
    # ================================================================
    print(f"\n[ETAPE 5] Laplacien spectral sur matrice {N}x{N}...")
    t3 = time.time()

    log_matrix = np.log1p(matrix).astype(np.float64)
    L_dom = np.diag(log_matrix.sum(axis=1)) - log_matrix
    eigenvalues, eigenvectors = np.linalg.eigh(L_dom)

    dom_px = eigenvectors[:, 1]
    dom_pz = eigenvectors[:, 2]
    dom_px = dom_px / np.abs(dom_px).max()
    dom_pz = dom_pz / np.abs(dom_pz).max()

    print(f"\n  POSITIONS SPECTRALES DES DOMAINES:")
    for i, d in enumerate(domains):
        print(f"    {d:25s} ({dom_px[i]:+.4f}, {dom_pz[i]:+.4f})  papers={domain_paper_count[i]:,}")

    print(f"\n  EIGENVALUES (20 premieres):")
    for i in range(min(20, len(eigenvalues))):
        gap = eigenvalues[i+1] - eigenvalues[i] if i < len(eigenvalues)-1 else 0
        marker = " <-- GAP" if gap > 0.5 else ""
        print(f"    L{i:2d} = {eigenvalues[i]:.6f}  (gap: {gap:.6f}){marker}")

    print(f"  Temps: {time.time()-t3:.1f}s")

    dom_positions = {}
    for i, d in enumerate(domains):
        dom_positions[d] = {
            'px': round(float(dom_px[i]), 4),
            'pz': round(float(dom_pz[i]), 4),
            'papers': int(domain_paper_count[i])
        }

    with open(ROOT / 'data' / 'topology' / 'domain_spectral_positions.json', 'w', encoding='utf-8') as f:
        json.dump(dom_positions, f, ensure_ascii=False, indent=2)
    print(f"  -> domain_spectral_positions.json")

    # ================================================================
    # ETAPE 6
    # ================================================================
    print(f"\n[ETAPE 6] Mise a jour des positions symboles S0...")
    t4 = time.time()
    random.seed(42)

    with open(ROOT / 'data' / 'core' / 'strates_export_v2.json', encoding='utf-8') as f:
        data = json.load(f)

    s0 = data['strates'][0]['symbols']
    updated = 0
    not_found = 0

    for sym in s0:
        domain = sym.get('domain', 'mathematique')
        if domain in dom_idx:
            idx = dom_idx[domain]
            noise_scale = 0.08
            sym['px'] = round(float(dom_px[idx]) + random.gauss(0, noise_scale), 4)
            sym['pz'] = round(float(dom_pz[idx]) + random.gauss(0, noise_scale), 4)
            sym['spectral'] = 'cooc'
            updated += 1
        else:
            not_found += 1

    with open(ROOT / 'data' / 'core' / 'strates_export_v2.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"  Symboles S0 mis a jour: {updated}")
    print(f"  Domaines non trouves: {not_found}")
    print(f"  Temps: {time.time()-t4:.1f}s")

    total_time = time.time() - t_global
    print(f"\n{'='*60}")
    print(f"TOUT TERMINE en {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
