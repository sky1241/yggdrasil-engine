#!/usr/bin/env python3
"""
YGGDRASIL — Test des paires-miroirs (le test qui tranche)
═══════════════════════════════════════════════════════════
QUESTION: Le signal vient-il du Laplacien qui détecte des vrais ponts,
          ou juste du fait que les percées impliquent des gros concepts ?

MÉTHODE: Pour chaque percée (i,j), trouver des paires-miroirs (r1,r2) avec:
  1. Même décile de degré (déjà fait dans validation_honest.py)
  2. Même distance spectrale ||U[i]-U[j]|| ≈ ||U[r1]-U[r2]||  (NOUVEAU)
  3. Zéro co-occurrence (comme les prédictions)
  4. Inter-espèces (comme les prédictions)

Si les percées scorent ENCORE plus haut que les miroirs → signal réel.
Si elles scorent pareil → artefact de centralité. Moteur trouve du vide, pas du signal.

USAGE:
  cd yggdrasil-engine
  python engine/analysis/mirror_pairs_test.py

Prérequis: avoir déjà lancé glyph_laplacian.py (qui génère les eigenvectors).

Sky × Claude — 2 Mars 2026, Versoix
"""

import gc
import json
import os
import sys
import time
import zipfile
import ast
import struct

import numpy as np
from scipy.stats import mannwhitneyu, percentileofscore

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
if REPO not in sys.path:
    sys.path.insert(0, REPO)
BT_DIR = os.path.join(REPO, "experiments", "blind_test_v2")
N = 65026
K = 64

# ── Chargement des données ─────────────────────────────────


def load_eigenvectors():
    """Charge la matrice U (N×K) des eigenvectors depuis glyph_laplacian output."""
    # Chercher dans plusieurs emplacements possibles
    candidates = [
        os.path.join(REPO, "data", "scan", "spectral_embeddings.npy"),  # glyph_laplacian.py output
        os.path.join(REPO, "data", "scan", "spectral_U.npy"),
        os.path.join(BT_DIR, "spectral_U.npy"),
    ]

    for path in candidates:
        if os.path.exists(path):
            print(f"  Loading U from {path}")
            if path.endswith('.npz'):
                data = np.load(path)
                return data['U'] if 'U' in data else data[list(data.keys())[0]]
            return np.load(path)

    # Essayer de recalculer depuis les données du blind test
    snapshot_zip = os.path.join(BT_DIR, "snapshot_2015_65k.npz")
    if os.path.exists(snapshot_zip):
        print("  U matrix not found, recomputing from snapshot...")
        return _compute_U_from_snapshot(snapshot_zip)

    raise FileNotFoundError(
        "Cannot find spectral_U.npy. Run glyph_laplacian.py first, "
        "or save U with: np.save('data/scan/spectral_U.npy', U)"
    )


def _compute_U_from_snapshot(snapshot_zip):
    """Recalcule U depuis le snapshot (si pas sauvegardé)."""
    from scipy.sparse import csr_matrix, csc_matrix
    from scipy.sparse.linalg import eigsh, LinearOperator

    print("  Loading snapshot (CSR format)...")
    with np.load(snapshot_zip) as npz:
        data_arr = npz['data'].astype(np.float32)
        indices = npz['indices'].astype(np.int32)
        indptr = npz['indptr']

    A = csr_matrix((data_arr, indices, indptr), shape=(N, N), dtype=np.float32)
    del data_arr, indices, indptr
    gc.collect()

    # Degré
    degrees = np.array(A.sum(axis=1)).ravel() + np.array(A.T.sum(axis=1)).ravel()
    degrees = np.maximum(degrees, 1e-10)
    d_inv_sqrt = 1.0 / np.sqrt(degrees)

    # LinearOperator pour D^{-1/2}(A+A^T)D^{-1/2}
    def matvec(x):
        x_scaled = d_inv_sqrt * x
        y = A.dot(x_scaled) + A.T.dot(x_scaled)
        return d_inv_sqrt * y

    op = LinearOperator((N, N), matvec=matvec, dtype=np.float32)

    print(f"  Computing {K} eigenvectors...")
    eigenvalues, eigenvectors = eigsh(op, k=K, which='LM')

    # U = eigenvectors pondérés par sqrt(|lambda|)
    weights = np.sqrt(np.abs(eigenvalues))
    U = eigenvectors * weights[np.newaxis, :]

    # Sauvegarder pour la prochaine fois
    out_path = os.path.join(REPO, "data", "scan", "spectral_embeddings.npy")
    np.save(out_path, U.astype(np.float32))
    print(f"  Saved U to {out_path}")

    return U


def _load_csr_matrix():
    """Charge la matrice CSR depuis le snapshot (format: data/indices/indptr)."""
    from scipy.sparse import csr_matrix
    snapshot_zip = os.path.join(BT_DIR, "snapshot_2015_65k.npz")
    if not os.path.exists(snapshot_zip):
        raise FileNotFoundError(f"Missing {snapshot_zip}")

    with np.load(snapshot_zip) as npz:
        data = npz['data'].astype(np.float32)
        indices = npz['indices'].astype(np.int32)
        indptr = npz['indptr']

    mat = csr_matrix((data, indices, indptr), shape=(N, N))
    return mat


def load_degrees_and_matrix():
    """Charge les degrés ET retourne la matrice CSR (un seul chargement)."""
    mat = _load_csr_matrix()
    # Degré = nombre de voisins non-zero (row + col car matrice triangulaire sup)
    row_deg = np.diff(mat.indptr)  # nnz per row
    col_deg = np.zeros(N, dtype=np.int32)
    np.add.at(col_deg, mat.indices, 1)
    degrees = row_deg.astype(np.int32) + col_deg
    return degrees, mat


def has_cooc(mat, i, j):
    """Check if pair (i,j) has co-occurrence > 0 in CSR matrix. O(log n) per check."""
    # Check both directions (matrix may be upper-triangular)
    start_i, end_i = mat.indptr[i], mat.indptr[i + 1]
    if end_i > start_i:
        cols_i = mat.indices[start_i:end_i]
        if np.searchsorted(cols_i, j) < len(cols_i) and cols_i[np.searchsorted(cols_i, j)] == j:
            return True
    start_j, end_j = mat.indptr[j], mat.indptr[j + 1]
    if end_j > start_j:
        cols_j = mat.indices[start_j:end_j]
        if np.searchsorted(cols_j, i) < len(cols_j) and cols_j[np.searchsorted(cols_j, i)] == i:
            return True
    return False


def load_species():
    """Charge le mapping concept → espèce (format: concepts_65k + species_2015)."""
    # D'abord charger url → idx depuis concepts_65k.json
    concepts_path = os.path.join(REPO, "data", "scan", "concepts_65k.json")
    with open(concepts_path, encoding='utf-8') as f:
        c65 = json.load(f)
    url_to_idx = {}
    for url, info in c65["concepts"].items():
        url_to_idx[url] = info["idx"]
    del c65

    # Ensuite charger species depuis species_2015.json (blind_test_v2)
    sp_path = os.path.join(BT_DIR, "species_2015.json")
    if not os.path.exists(sp_path):
        sp_path = os.path.join(REPO, "data", "scan", "species_65k.json")

    with open(sp_path, encoding='utf-8') as f:
        sp_data = json.load(f)

    species_map = np.full(N, -1, dtype=np.int8)
    for url, info in sp_data["concepts"].items():
        if url in url_to_idx:
            species_map[url_to_idx[url]] = int(info["species"])
    del sp_data, url_to_idx
    gc.collect()

    return species_map


def resolve_breakthroughs():
    """Charge les percées depuis ground_truth_v2.json (même source que glyph_laplacian.py)."""
    gt_path = os.path.join(BT_DIR, "ground_truth_v2.json")
    if not os.path.exists(gt_path):
        raise FileNotFoundError(
            f"Missing {gt_path}. Run blind_test_v2 first."
        )

    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)

    breakthroughs = [b for b in gt_data["breakthroughs"] if b.get("matched")]
    print(f"  Loaded {len(breakthroughs)} matched breakthroughs from ground_truth_v2.json")
    return breakthroughs


def spectral_score(U, i, j):
    """Score spectral d'une paire = U[i] · U[j]."""
    return float(U[i] @ U[j])


def spectral_distance(U, i, j):
    """Distance spectrale entre deux concepts = ||U[i] - U[j]||."""
    return float(np.linalg.norm(U[i] - U[j]))


def find_mirror_pairs(U, degrees, species_map, cooc_mat, breakthroughs,
                      n_mirrors=200, tolerance=0.15, seed=42):
    """
    LE TEST QUI TRANCHE.

    Pour chaque percée (i,j), trouve n_mirrors paires (r1,r2) telles que:
      1. degree_decile(r1) == degree_decile(i)
      2. degree_decile(r2) == degree_decile(j)
      3. |spectral_dist(r1,r2) - spectral_dist(i,j)| < tolerance × spectral_dist(i,j)
      4. cooc(r1,r2) == 0  (zero co-occurrence)
      5. species(r1) != species(r2)  (inter-espèces)

    Returns: dict avec scores des percées et scores des miroirs.
    """
    rng = np.random.RandomState(seed)

    # ── Préparer les déciles de degré ──
    active_mask = degrees > 0
    active_idxs = np.where(active_mask)[0]
    active_degrees = degrees[active_idxs]
    percentiles = np.percentile(active_degrees, np.arange(10, 100, 10))

    # Bin chaque concept actif
    all_bins = np.digitize(degrees[active_idxs], percentiles)
    idx_to_bin = {}
    bin_to_idxs = {b: [] for b in range(10)}
    for i, idx in enumerate(active_idxs):
        b = int(all_bins[i])
        idx_to_bin[int(idx)] = b
        bin_to_idxs[b].append(int(idx))

    for b in bin_to_idxs:
        bin_to_idxs[b] = np.array(bin_to_idxs[b])

    # ── Pour chaque percée, trouver des miroirs ──
    results = []

    for bt in breakthroughs:
        idx_a = bt["concept_a_idx"]
        idx_b = bt["concept_b_idx"]

        bt_score = spectral_score(U, idx_a, idx_b)
        bt_dist = spectral_distance(U, idx_a, idx_b)

        bin_a = idx_to_bin.get(idx_a, 5)
        bin_b = idx_to_bin.get(idx_b, 5)

        cands_a = bin_to_idxs.get(bin_a, active_idxs)
        cands_b = bin_to_idxs.get(bin_b, active_idxs)

        if len(cands_a) == 0 or len(cands_b) == 0:
            print(f"  ⚠ No candidates for {bt['name']}")
            continue

        mirror_scores = []
        attempts = 0
        max_attempts = n_mirrors * 500  # Beaucoup de tentatives car filtrage strict

        while len(mirror_scores) < n_mirrors and attempts < max_attempts:
            # Tirer une paire dans les mêmes bins de degré
            r1 = int(rng.choice(cands_a))
            r2 = int(rng.choice(cands_b))
            attempts += 1

            # Filtre: pas le même concept
            if r1 == r2:
                continue

            # Filtre: inter-espèces
            if species_map[r1] == species_map[r2]:
                continue

            # Filtre: zéro co-occurrence
            if has_cooc(cooc_mat, r1, r2):
                continue

            # Filtre: même distance spectrale (±tolerance)
            mirror_dist = spectral_distance(U, r1, r2)
            if bt_dist > 0:
                relative_diff = abs(mirror_dist - bt_dist) / bt_dist
                if relative_diff > tolerance:
                    continue

            # ✅ C'est un miroir valide
            mirror_scores.append(spectral_score(U, r1, r2))

        if len(mirror_scores) < 10:
            print(f"  ⚠ {bt['name']}: only {len(mirror_scores)} mirrors found "
                  f"(needed {n_mirrors}). Relaxing tolerance...")
            # Retry avec tolérance plus large
            attempts2 = 0
            while len(mirror_scores) < n_mirrors and attempts2 < max_attempts:
                r1 = int(rng.choice(cands_a))
                r2 = int(rng.choice(cands_b))
                attempts2 += 1
                if r1 == r2:
                    continue
                if species_map[r1] == species_map[r2]:
                    continue
                pair_key = (min(r1, r2), max(r1, r2))
                if pair_key in cooc_set:
                    continue
                mirror_dist = spectral_distance(U, r1, r2)
                if bt_dist > 0:
                    relative_diff = abs(mirror_dist - bt_dist) / bt_dist
                    if relative_diff > 0.30:  # Tolérance 30%
                        continue
                mirror_scores.append(spectral_score(U, r1, r2))

        n_found = len(mirror_scores)
        mirror_scores = np.array(mirror_scores) if mirror_scores else np.array([0.0])

        # Le verdict: la percée bat-elle ses miroirs ?
        bt_beats = float(np.mean(bt_score > mirror_scores)) * 100

        results.append({
            "name": bt["name"],
            "bt_score": bt_score,
            "bt_dist": bt_dist,
            "mirror_mean": float(np.mean(mirror_scores)),
            "mirror_std": float(np.std(mirror_scores)),
            "mirror_max": float(np.max(mirror_scores)),
            "n_mirrors": n_found,
            "bt_beats_pct": bt_beats,
            "bt_percentile": float(percentileofscore(mirror_scores, bt_score, kind='weak')),
        })

        status = "✅" if bt_beats > 50 else "❌"
        print(f"  {status} {bt['name']:30s} | score={bt_score:.6f} | "
              f"mirror_mean={float(np.mean(mirror_scores)):.6f} | "
              f"beats={bt_beats:.0f}% | n={n_found}")

    return results


def compute_verdict(results):
    """Le verdict final."""
    if not results:
        return {"verdict": "NO_DATA"}

    beats = [r["bt_beats_pct"] for r in results]
    mean_beats = np.mean(beats)
    n_wins = sum(1 for b in beats if b > 50)
    n_strong = sum(1 for b in beats if b > 75)
    n_total = len(beats)

    # Test statistique global: scores percées vs scores miroirs (pooled)
    bt_scores = np.array([r["bt_score"] for r in results])
    mirror_means = np.array([r["mirror_mean"] for r in results])

    # Paired test: chaque percée vs la moyenne de ses miroirs
    from scipy.stats import wilcoxon
    try:
        stat, p_paired = wilcoxon(bt_scores, mirror_means, alternative='greater')
    except Exception:
        p_paired = 1.0

    # Cohen's d apparié
    diffs = bt_scores - mirror_means
    if np.std(diffs) > 0:
        d_mirror = float(np.mean(diffs) / np.std(diffs))
    else:
        d_mirror = 0.0

    verdict = {
        "n_breakthroughs": n_total,
        "n_wins": n_wins,
        "n_strong_wins": n_strong,
        "mean_beats_pct": round(mean_beats, 1),
        "paired_wilcoxon_p": float(p_paired),
        "cohens_d_mirror": round(d_mirror, 3),
        "interpretation": "",
    }

    # ── Interprétation ──
    if d_mirror > 1.0 and p_paired < 0.001 and n_wins >= 15:
        verdict["interpretation"] = (
            "🟢 SIGNAL RÉEL. Les percées scorent significativement plus haut "
            "que des paires-miroirs de même degré ET même distance spectrale. "
            "Le Laplacien détecte autre chose que la centralité."
        )
    elif d_mirror > 0.5 and p_paired < 0.05 and n_wins >= 12:
        verdict["interpretation"] = (
            "🟡 SIGNAL PROBABLE. Les percées tendent à scorer plus haut que "
            "les miroirs, mais l'effet est modéré. Le moteur capte du signal "
            "au-delà de la centralité, mais pas de manière écrasante."
        )
    elif d_mirror > 0.2 and n_wins >= 10:
        verdict["interpretation"] = (
            "🟠 SIGNAL FAIBLE. Il reste un petit avantage des percées sur "
            "les miroirs. Probablement un mix de vrai signal et de bruit."
        )
    else:
        verdict["interpretation"] = (
            "🔴 PAS DE SIGNAL. Les percées ne battent pas leurs miroirs. "
            "Le moteur trouve du vide structuré mais pas du vide prédictif. "
            "Le d=5.76 était un artefact de centralité résiduel."
        )

    return verdict


def main():
    t0 = time.time()
    print("=" * 70)
    print("YGGDRASIL — TEST DES PAIRES-MIROIRS")
    print("Le test qui tranche: signal réel ou artefact de centralité ?")
    print("=" * 70)

    # ── 1. Charger les données ──
    print("\n[1/5] Chargement des eigenvectors...")
    U = load_eigenvectors()
    print(f"  U shape: {U.shape}")

    print("\n[2/5] Chargement des degrés + matrice co-occurrence...")
    degrees, cooc_mat = load_degrees_and_matrix()
    print(f"  Active concepts: {np.sum(degrees > 0):,}")
    print(f"  Co-occurrence matrix: {cooc_mat.nnz:,} non-zero entries")

    print("\n[3/5] Chargement des espèces...")
    species_map = load_species()
    print(f"  Concepts avec espèce: {np.sum(species_map >= 0):,}")

    print("\n[4/4] Chargement des percées...")
    breakthroughs = resolve_breakthroughs()
    print(f"  Resolved: {len(breakthroughs)}/20")

    # ── 2. Trouver les paires-miroirs ──
    print("\n" + "=" * 70)
    print("TEST: degré + distance spectrale + zero-cooc + inter-espèces")
    print("Tolérance distance spectrale: ±15%")
    print("=" * 70)

    results = find_mirror_pairs(
        U, degrees, species_map, cooc_mat, breakthroughs,
        n_mirrors=200, tolerance=0.15, seed=42
    )

    # ── 3. Verdict ──
    verdict = compute_verdict(results)

    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    print(f"  Percées testées:    {verdict['n_breakthroughs']}")
    print(f"  Victoires (>50%):   {verdict['n_wins']}/{verdict['n_breakthroughs']}")
    print(f"  Victoires fortes:   {verdict['n_strong_wins']}/{verdict['n_breakthroughs']}")
    print(f"  Mean beats:         {verdict['mean_beats_pct']}%")
    print(f"  Wilcoxon p:         {verdict['paired_wilcoxon_p']:.2e}")
    print(f"  Cohen's d (miroir): {verdict['cohens_d_mirror']}")
    print(f"\n  {verdict['interpretation']}")

    # ── 4. Sauvegarder ──
    output = {
        "meta": {
            "test": "mirror_pairs",
            "method": "degree_decile + spectral_distance_15pct + zero_cooc + inter_species",
            "n_mirrors_per_bt": 200,
            "tolerance": 0.15,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "verdict": verdict,
        "details": results,
    }

    out_path = os.path.join(REPO, "data", "scan", "mirror_pairs_test.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else str(o))

    print(f"\n  Saved to {out_path}")
    print(f"  Total time: {time.time() - t0:.0f}s")

    # ── Note pour Sky ──
    print("\n" + "-" * 70)
    print("NOTE: Si le script ne trouve pas spectral_embeddings.npy,")
    print("relance d'abord glyph_laplacian.py (il sauvegarde automatiquement).")
    print("-" * 70)


if __name__ == "__main__":
    main()
