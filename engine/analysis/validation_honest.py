#!/usr/bin/env python3
"""
YGGDRASIL — Validation honnête
================================
Corrige 3 biais dans les métriques de validation du Glyph Laplacian:

  Biais 1: Cohen's d gonflé par concepts morts (degré=0, score=0)
  Biais 2: Percées vs prédictions = pommes vs oranges (cooc partielle vs zero-cooc)
  Biais 3: Recall pré-filtré (top 5000 × inter-espèces × level≥2 × zero-cooc)

Module réutilisable: fonctions pures, pas de side-effects.
"""

import numpy as np
from scipy.stats import mannwhitneyu, percentileofscore


def degree_matched_random(U, degrees, breakthroughs, n_per_bt=100, seed=42):
    """
    Biais 1 fix: tire des paires random appariées par décile de degré.

    Au lieu de random sur 65K concepts (incluant degré=0),
    on tire dans le même bin de degré que chaque breakthrough.

    Returns: (matched_scores, naive_scores)
    """
    rng = np.random.RandomState(seed)
    N = U.shape[0]

    # Déciles de degré (sur concepts actifs seulement)
    active_mask = degrees > 0
    active_idxs = np.where(active_mask)[0]

    if len(active_idxs) == 0:
        return np.array([]), np.array([])

    # 10 bins de degré basés sur les percentiles des concepts actifs
    active_degrees = degrees[active_idxs]
    percentiles = np.percentile(active_degrees, np.arange(10, 100, 10))
    # Bin chaque concept actif
    bins = np.digitize(active_degrees, percentiles)  # 0-9
    # Mapping idx -> bin
    idx_to_bin = {}
    bin_to_idxs = {b: [] for b in range(10)}
    for i, idx in enumerate(active_idxs):
        b = int(bins[i])
        idx_to_bin[int(idx)] = b
        bin_to_idxs[b].append(int(idx))

    # Convertir en arrays pour np.choice
    for b in bin_to_idxs:
        bin_to_idxs[b] = np.array(bin_to_idxs[b])

    # Tirer des paires appariées par degré
    matched_scores = []
    for bt in breakthroughs:
        idx_a = bt["concept_a_idx"]
        idx_b = bt["concept_b_idx"]
        bin_a = idx_to_bin.get(idx_a, 5)  # fallback milieu
        bin_b = idx_to_bin.get(idx_b, 5)

        cands_a = bin_to_idxs.get(bin_a, active_idxs)
        cands_b = bin_to_idxs.get(bin_b, active_idxs)

        if len(cands_a) == 0 or len(cands_b) == 0:
            continue

        for _ in range(n_per_bt):
            ri = rng.choice(cands_a)
            rj = rng.choice(cands_b)
            attempts = 0
            while ri == rj and attempts < 10:
                rj = rng.choice(cands_b)
                attempts += 1
            if ri != rj:
                matched_scores.append(float(U[ri] @ U[rj]))

    # Aussi tirer des naive (comme avant, pour comparaison)
    naive_scores = []
    for _ in range(2000):
        ri = rng.randint(0, N)
        rj = rng.randint(0, N)
        while ri == rj:
            rj = rng.randint(0, N)
        naive_scores.append(float(U[ri] @ U[rj]))

    return np.array(matched_scores), np.array(naive_scores)


def rank_in_fullspace(U, breakthroughs, species_map, n_sample=200000, seed=42):
    """
    Biais 2+3 fix: estime le rang de chaque breakthrough dans l'espace complet.

    Track A: parmi TOUTES les paires inter-espèces (avec ou sans cooc)
    Track B: n'est PAS recalculé ici (c'est le rank existant dans les zero-cooc)

    On échantillonne n_sample paires random inter-espèces et on calcule
    le percentile de chaque breakthrough dans cette distribution.

    Returns: dict par breakthrough avec {percentile, estimated_rank, n_better}
    """
    rng = np.random.RandomState(seed)
    N = U.shape[0]

    # Concepts avec espèce valide
    valid = np.where(species_map >= 0)[0]
    if len(valid) == 0:
        return {}

    # Échantillonner des paires inter-espèces
    sample_scores = []
    attempts = 0
    max_attempts = n_sample * 5

    while len(sample_scores) < n_sample and attempts < max_attempts:
        batch = min(n_sample * 2, max_attempts - attempts)
        ri = rng.choice(valid, size=batch)
        rj = rng.choice(valid, size=batch)

        # Filtrer: inter-espèces + i != j
        mask = (ri != rj) & (species_map[ri] != species_map[rj])
        ri_good = ri[mask]
        rj_good = rj[mask]

        # Calculer scores par batch (évite boucle Python)
        for k in range(len(ri_good)):
            if len(sample_scores) >= n_sample:
                break
            sample_scores.append(float(U[ri_good[k]] @ U[rj_good[k]]))

        attempts += batch

    sample_scores = np.array(sample_scores)
    print(f"    Sampled {len(sample_scores):,} inter-species pairs for fullspace ranking")

    # Pour chaque breakthrough, calculer le percentile
    results = []
    for bt in breakthroughs:
        i, j = bt["concept_a_idx"], bt["concept_b_idx"]
        score = float(U[i] @ U[j])

        # Percentile: fraction des paires random avec score >= bt_score
        pctl = percentileofscore(sample_scores, score, kind='weak')
        n_better = int(np.sum(sample_scores >= score))

        results.append({
            "name": bt["name"],
            "score": score,
            "percentile": round(pctl, 4),
            "top_fraction": round(1 - pctl / 100, 6),
            "n_better_in_sample": n_better,
            "n_sample": len(sample_scores),
        })

    return results


def honest_metrics(gt_scores, matched_random, naive_random):
    """
    Calcule les métriques honnêtes vs naïves côte à côte.

    Returns: dict avec d_naive, d_matched, p_naive, p_matched, etc.
    """
    results = {}

    for label, random_scores in [("naive", naive_random), ("matched", matched_random)]:
        if len(random_scores) == 0:
            continue

        gt = np.array(gt_scores)
        rand = np.array(random_scores)

        # Mann-Whitney
        U_stat, p_value = mannwhitneyu(gt, rand, alternative='greater')
        n1, n2 = len(gt), len(rand)
        effect_r = 1 - 2 * U_stat / (n1 * n2)

        # Cohen's d
        pooled_std = np.sqrt(
            (np.var(gt) * (n1 - 1) + np.var(rand) * (n2 - 1))
            / (n1 + n2 - 2)
        ) if (n1 + n2 > 2) else 1
        cohens_d = (np.mean(gt) - np.mean(rand)) / pooled_std if pooled_std > 0 else 0

        results[label] = {
            "cohens_d": round(float(cohens_d), 4),
            "mann_whitney_U": float(U_stat),
            "p_value": float(p_value),
            "effect_size_r": round(float(effect_r), 4),
            "gt_mean": round(float(np.mean(gt)), 8),
            "random_mean": round(float(np.mean(rand)), 8),
            "random_std": round(float(np.std(rand)), 8),
            "n_gt": n1,
            "n_random": n2,
        }

    return results


def recall_fullspace(breakthroughs, fullspace_results, thresholds_pct=(0.01, 0.1, 1.0)):
    """
    Biais 3 fix: recall dans l'espace complet.

    Au lieu de recall@100 dans les 10K prédictions filtrées,
    calcule: "fraction des breakthroughs dans le top X% de toutes les paires".

    thresholds_pct: pourcentages du top à considérer (0.01% = top 8200 sur 82M)

    Returns: dict {threshold_pct: recall}
    """
    results = {}

    for pct in thresholds_pct:
        # Une breakthrough est dans le top X% si son percentile >= (100 - X)
        threshold_pctl = 100 - pct
        n_in = sum(1 for r in fullspace_results if r["percentile"] >= threshold_pctl)
        n_total = len(fullspace_results)
        recall = n_in / n_total if n_total > 0 else 0

        results[f"top_{pct}%"] = {
            "recall": round(recall, 4),
            "n_in": n_in,
            "n_total": n_total,
            "equivalent_pairs": f"top {pct}% of ~82M pairs = ~{int(82_000_000 * pct / 100):,}",
        }

    return results


def print_honest_report(metrics, fullspace_recall, fullspace_results, bt_zero_cooc_results):
    """Affiche un rapport lisible comparant métriques naïves et honnêtes."""

    print(f"\n{'='*80}")
    print("VALIDATION HONNÊTE — Spectral Blind Test")
    print(f"{'='*80}")

    # Biais 1: Cohen's d
    print(f"\n  BIAIS 1: Cohen's d (degré-apparié vs naïf)")
    print(f"  {'─'*55}")
    if "naive" in metrics:
        m = metrics["naive"]
        print(f"  d naïf     = {m['cohens_d']:8.4f}  (random uniforme, inclut degré=0)")
        print(f"    p = {m['p_value']:.2e}, r = {m['effect_size_r']:.4f}")
        print(f"    GT mean = {m['gt_mean']:.8f}, random mean = {m['random_mean']:.8f}")
    if "matched" in metrics:
        m = metrics["matched"]
        print(f"  d apparié  = {m['cohens_d']:8.4f}  (random apparié par décile de degré)")
        print(f"    p = {m['p_value']:.2e}, r = {m['effect_size_r']:.4f}")
        print(f"    GT mean = {m['gt_mean']:.8f}, random mean = {m['random_mean']:.8f}")

    if "naive" in metrics and "matched" in metrics:
        d_n = metrics["naive"]["cohens_d"]
        d_m = metrics["matched"]["cohens_d"]
        if d_m > 0 and d_n > 0:
            print(f"\n  → Inflation: d naïf est {d_n/d_m:.1f}× le d honnête")
        elif d_n > 0:
            print(f"\n  → d honnête ≤ 0 : le signal disparaît avec contrôle apparié")
        else:
            print(f"\n  → d naïf ≤ 0 : pas de signal même sans appariement")

    # Biais 2: Track A vs Track B
    print(f"\n  BIAIS 2: Rang des percées (espace complet vs zero-cooc)")
    print(f"  {'─'*55}")
    print(f"  {'Breakthrough':<30s} {'Percentile':>10s} {'Top%':>8s} {'Rank (0-cooc)':>14s}")
    print(f"  {'─'*30} {'─'*10} {'─'*8} {'─'*14}")
    for fs, zc in zip(fullspace_results, bt_zero_cooc_results):
        name = fs["name"][:30]
        pctl = fs["percentile"]
        top_frac = f"{fs['top_fraction']*100:.3f}%"
        zc_rank = f"#{zc['rank']:,}" if zc["rank"] <= 10000 else ">10K"
        print(f"  {name:<30s} {pctl:>9.2f}% {top_frac:>8s} {zc_rank:>14s}")

    # Biais 3: Recall plein espace
    print(f"\n  BIAIS 3: Recall (filtré vs espace complet)")
    print(f"  {'─'*55}")
    for key, val in fullspace_recall.items():
        print(f"  Recall {key:>8s} = {val['recall']:.2%} "
              f"({val['n_in']}/{val['n_total']})")
        print(f"    → {val['equivalent_pairs']}")

    print(f"\n{'='*80}")
