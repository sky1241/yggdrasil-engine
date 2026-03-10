#!/usr/bin/env python3
"""
AUDIT PHILIPPE V2 — 8 failles testées
═══════════════════════════════════════
Sky × Claude — 2 Mars 2026
"""

import json, os, sys, time, gc, random
from collections import Counter
import numpy as np
from scipy.stats import mannwhitneyu

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")
PRED_DIR = os.path.join(REPO, "experiments", "predictions_2025")

PHILIPPE_CORE = {
    "H-infinity methods in control theory": 59994,
    "Robust control": 53433,
    "Convex optimization": 9037,
    "Frequency response": 62860,
    "Linear matrix inequality": 15898,
    "System identification": 3068,
    "PID controller": 55897,
    "Transfer function": 62157,
    "Optimal control": 63699,
    "Lyapunov function": 58937,
    "Lyapunov stability": 22574,
    "Adaptive control": 1209,
    "Feedback control": 51931,
}
PHILIPPE_IDXS = set(PHILIPPE_CORE.values())
ALL_KNOWN = PHILIPPE_IDXS | {
    47589, 17140, 15773, 17705, 270, 54454, 9153, 14478,
    57584, 60254, 14780, 59068, 55136, 62539, 61920, 62098,
    60888, 15524, 60028, 59882, 27649, 58410, 63277, 64133,
    64602, 64849,
}

PLASMA_KW = {"plasma", "divertor", "tokamak", "helical", "cyclotron", "mhd",
             "magnetohydro", "rogowski", "bolometer", "electron dens", "electron temp",
             "magnetic", "ion beam", "electromagnet", "flux", "reflectometry",
             "interferometer", "diafiltration", "amplifier", "stellarator"}


def extract_positions(concept_idxs, indptr, all_indices):
    """Row + column scan → flat positions + meta."""
    idxs = sorted(concept_idxs)
    positions, meta = [], []

    for pi in idxs:
        start, end = int(indptr[pi]), int(indptr[pi + 1])
        if end <= start:
            continue
        cols = all_indices[start:end]
        for j, c in enumerate(cols):
            c = int(c)
            if c != pi:
                positions.append(start + j)
                meta.append((pi, c))

    # Column scan in 10M chunks to avoid 103 MB mask allocation
    CHUNK = 10_000_000
    n_total = len(all_indices)
    for cs in range(0, n_total, CHUNK):
        ce = min(cs + CHUNK, n_total)
        chunk = all_indices[cs:ce]
        m = np.zeros(len(chunk), dtype=np.bool_)
        for pi in idxs:
            m |= (chunk == pi)
        hits = np.where(m)[0]
        if len(hits):
            flat_hits = hits + cs
            col_vals = chunk[hits]
            row_vals = np.searchsorted(indptr, flat_hits, side='right') - 1
            for k in range(len(hits)):
                r, c = int(row_vals[k]), int(col_vals[k])
                if r != c:
                    positions.append(int(flat_hits[k]))
                    meta.append((r, c))
        del m, chunk; gc.collect()
    return positions, meta


def build_pairs(meta, values):
    pairs = {}
    for i, (r, c) in enumerate(meta):
        pair = (min(r, c), max(r, c))
        if pair not in pairs:
            pairs[pair] = float(values[i])
    return pairs


def score_pairs(pairs, activity, total_works_sum, concept_idxs,
                idx_to_level, species_map, min_level=3, use_log=False):
    """Compute z + P4 → stats dict."""
    active = activity > 0
    if use_log:
        la = np.log1p(activity)
        a_max, a_min = float(la[active].max()), float(la[active].min())
    else:
        a_max, a_min = float(activity[active].max()), float(activity[active].min())

    cooc_max = max(pairs.values()) if pairs else 1.0
    cset = set(concept_idxs)
    z_cross, p4_cross, z_all = [], [], []
    results = []
    n_cross, n_holes = 0, 0

    for (ia, ib), obs in pairs.items():
        wa, wb = float(activity[ia]), float(activity[ib])
        if wa == 0 or wb == 0:
            continue
        E = wa * wb / total_works_sum
        pa, pb = wa / total_works_sum, wb / total_works_sum
        std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
        z = (obs - E) / std

        if use_log:
            an = max(min((np.log1p(wa) - a_min) / (a_max - a_min), 1.0), 0.0)
            bn = max(min((np.log1p(wb) - a_min) / (a_max - a_min), 1.0), 0.0)
        else:
            an = max(min((wa - a_min) / (a_max - a_min), 1.0), 0.0)
            bn = max(min((wb - a_min) / (a_max - a_min), 1.0), 0.0)

        gap = 1.0 - obs / cooc_max
        p4 = an * bn * gap * abs(z)

        core_idx = ia if ia in cset else ib
        other_idx = ib if ia in cset else ia
        olvl = idx_to_level.get(other_idx, -1)
        if olvl < min_level:
            continue

        csp = species_map.get(core_idx, -1)
        osp = species_map.get(other_idx, -1)
        cross = csp != osp and csp >= 0 and osp >= 0

        z_all.append(z)
        if cross:
            z_cross.append(z)
            p4_cross.append(p4)
            n_cross += 1
            if z < 0:
                n_holes += 1

        results.append({"other_idx": other_idx, "other_level": olvl,
                        "z": z, "p4": p4, "cross": cross,
                        "core_sp": csp, "other_sp": osp,
                        "wa": wa, "wb": wb, "cooc": obs})

    return {"n_pairs": len(results), "n_cross": n_cross, "n_holes": n_holes,
            "z_cross": np.array(z_cross), "p4_cross": np.array(p4_cross),
            "z_all": np.array(z_all), "results": results}


def main():
    t0 = time.time()
    print("=" * 80)
    print("AUDIT PHILIPPE V2 — 8 failles")
    print("=" * 80)

    # ═══ LOAD METADATA (one file at a time to minimize peak memory) ═══
    print("\n[0] Loading metadata...")

    # 1) concepts_65k.json → idx_name, idx_level, url_idx
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"), 'r', encoding='utf-8') as f:
        cdata = json.load(f)
    idx_name, idx_level, url_idx = {}, {}, {}
    for url, info in cdata["concepts"].items():
        idx_name[info["idx"]] = info["name"]
        idx_level[info["idx"]] = info.get("level", -1)
        url_idx[url] = info["idx"]
    del cdata; gc.collect()

    # 2) species_full.json → species_map
    with open(os.path.join(PRED_DIR, "species_full.json"), 'r', encoding='utf-8') as f:
        spdata = json.load(f)
    species_map = {}
    for url, info in spdata["concepts"].items():
        if url in url_idx:
            species_map[url_idx[url]] = info["species"]
    del spdata, url_idx; gc.collect()

    # 3) collision_matrix → species_names (tiny)
    with open(os.path.join(PRED_DIR, "collision_matrix_full.json"), 'r', encoding='utf-8') as f:
        species_names = json.load(f)["meta"]["species_names"]
    gc.collect()

    # 4) activity (tiny: 65K floats)
    with open(os.path.join(PRED_DIR, "activity_full.json"), 'r', encoding='utf-8') as f:
        activity = np.array(json.load(f)["activity"], dtype=np.float64)
    total_works = float(activity.sum())
    gc.collect()

    # ═══ PHILIPPE'S PROFILE ═══
    print("\n[0b] Philippe's concept profiles:")
    phil_acts = []
    for name, idx in sorted(PHILIPPE_CORE.items()):
        lvl = idx_level.get(idx, -1)
        sp = species_map.get(idx, -1)
        act = float(activity[idx])
        phil_acts.append(act)
        print(f"  {name:45s} | idx={idx:5d} | L{lvl} | sp={sp} | act={act:,.0f}")
    print(f"  Median activity: {np.median(phil_acts):,.0f}")
    print(f"  Range: [{min(phil_acts):,.0f}, {max(phil_acts):,.0f}]")

    # ═══ RANDOM BASELINES ═══
    print("\n[0c] Selecting 5 random baselines (same species, active, not Philippe)...")
    candidates = [(idx, idx_level.get(idx, -1), float(activity[idx]))
                   for idx in range(65026)
                   if species_map.get(idx, -1) == 4
                   and idx_level.get(idx, -1) >= 2
                   and activity[idx] > 0
                   and idx not in ALL_KNOWN]
    print(f"  Pool: {len(candidates)} concepts in species 4 (CS/Math)")

    N_BASE = 5
    baselines = []
    for seed in range(42, 42 + N_BASE):
        rng = random.Random(seed)
        chosen = rng.sample(candidates, 13)
        baselines.append({
            "seed": seed,
            "idxs": set(c[0] for c in chosen),
            "names": [idx_name.get(c[0], "?") for c in chosen],
        })
        print(f"  Seed {seed}: {[idx_name.get(c[0],'?')[:25] for c in chosen[:4]]}...")

    # ═══ PHASE 1: EXTRACT POSITIONS (indices ~413 MB) ═══
    print("\n[1] Loading indices...")
    npz_path = os.path.join(PRED_DIR, "snapshot_full.npz")
    npz = np.load(npz_path, allow_pickle=False)
    indptr = npz['indptr'].copy()
    all_indices = npz['indices']
    npz.close()

    print("  Extracting Philippe...")
    phil_pos, phil_meta = extract_positions(PHILIPPE_IDXS, indptr, all_indices)
    print(f"    {len(phil_pos):,} positions")

    # Accumulate all positions for single mmap pass
    all_pos = list(phil_pos)
    all_met = list(phil_meta)
    boundaries = [(0, len(phil_pos))]  # (start, end) for each concept set

    for bs in baselines:
        print(f"  Extracting baseline seed={bs['seed']}...")
        bstart = len(all_pos)
        bpos, bmeta = extract_positions(bs["idxs"], indptr, all_indices)
        all_pos.extend(bpos)
        all_met.extend(bmeta)
        boundaries.append((bstart, len(all_pos)))
        print(f"    {len(bpos):,} positions")
        del bpos, bmeta

    del all_indices; gc.collect()
    print(f"  Total: {len(all_pos):,} positions across {1+N_BASE} sets")

    # ═══ PHASE 2: EXTRACT VALUES (mmap) ═══
    print("\n[2] Extracting values via mmap...")
    import zipfile, tempfile, shutil
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(npz_path) as zf:
            zf.extract('data.npy', tmpdir)
        data = np.load(os.path.join(tmpdir, 'data.npy'), mmap_mode='r')
        arr = np.array(all_pos, dtype=np.int64)
        del all_pos; gc.collect()
        all_vals = data[arr].copy()
        del data, arr; gc.collect()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"  Got {len(all_vals):,} values")

    # Build pair dicts
    phil_start, phil_end = boundaries[0]
    phil_pairs = build_pairs(all_met[phil_start:phil_end], all_vals[phil_start:phil_end])

    base_pairs = []
    for i in range(N_BASE):
        bs, be = boundaries[i + 1]
        base_pairs.append(build_pairs(all_met[bs:be], all_vals[bs:be]))

    del all_vals, all_met, phil_pos, phil_meta; gc.collect()

    # ═══ PHASE 3: COMPUTE SCORES ═══
    print("\n[3] Computing P4 scores...")
    phil_lin = score_pairs(phil_pairs, activity, total_works, PHILIPPE_IDXS,
                           idx_level, species_map, min_level=3, use_log=False)
    phil_log = score_pairs(phil_pairs, activity, total_works, PHILIPPE_IDXS,
                           idx_level, species_map, min_level=3, use_log=True)
    print(f"  Philippe: {phil_lin['n_pairs']} pairs, {phil_lin['n_cross']} cross, "
          f"{phil_lin['n_holes']} holes")

    base_stats = []
    for i in range(N_BASE):
        bs = score_pairs(base_pairs[i], activity, total_works,
                         baselines[i]["idxs"], idx_level, species_map,
                         min_level=3, use_log=False)
        base_stats.append(bs)
        print(f"  Baseline {baselines[i]['seed']}: {bs['n_pairs']} pairs, "
              f"{bs['n_cross']} cross, {bs['n_holes']} holes")

    # ═══════════════════════════════════════════════════════════════
    # FAILLE 1 — MEGA-HUB BIAS (linear vs log)
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print("FAILLE 1 — MEGA-HUB BIAS (linear vs log normalization)")
    print(f"{'='*80}")

    cr_lin = sorted([r for r in phil_lin["results"] if r["cross"]],
                    key=lambda x: x["p4"], reverse=True)
    cr_log = sorted([r for r in phil_log["results"] if r["cross"]],
                    key=lambda x: x["p4"], reverse=True)

    top50_lin = set(r["other_idx"] for r in cr_lin[:50])
    top50_log = set(r["other_idx"] for r in cr_log[:50])
    overlap = top50_lin & top50_log

    print(f"  Top 50 overlap: {len(overlap)}/50 ({len(overlap)*2:.0f}%)")

    print(f"\n  Top 10 LINEAR:")
    for i, r in enumerate(cr_lin[:10]):
        print(f"    {i+1:2d}. P4={r['p4']:.6f} | z={r['z']:8.1f} | "
              f"L{r['other_level']} {idx_name.get(r['other_idx'],'?')[:40]}")
    print(f"\n  Top 10 LOG:")
    for i, r in enumerate(cr_log[:10]):
        print(f"    {i+1:2d}. P4={r['p4']:.6f} | z={r['z']:8.1f} | "
              f"L{r['other_level']} {idx_name.get(r['other_idx'],'?')[:40]}")

    # ═══════════════════════════════════════════════════════════════
    # FAILLE 4 — CLUSTER ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print("FAILLE 4 — CLUSTER ANALYSIS (top 50 holes)")
    print(f"{'='*80}")

    holes50 = sorted([r for r in cr_lin if r["z"] < 0], key=lambda x: x["z"])[:50]

    sp_dist = Counter(r["other_sp"] for r in holes50)
    print(f"  By species:")
    for sp, n in sp_dist.most_common():
        print(f"    {species_names.get(str(sp),'?'):40s} | {n:2d}/50")

    unique_other = set(r["other_idx"] for r in holes50)
    print(f"  Unique concepts: {len(unique_other)}")

    plasma_n, bio_n, sig_n, other_n = 0, 0, 0, 0
    bio_kw = {"gene", "cancer", "breast", "genome", "covid", "pandemic"}
    sig_kw = {"sampling", "signal", "interference", "spectrum"}
    for r in holes50:
        nm = idx_name.get(r["other_idx"], "").lower()
        if any(k in nm for k in PLASMA_KW):
            plasma_n += 1
        elif any(k in nm for k in bio_kw):
            bio_n += 1
        elif any(k in nm for k in sig_kw):
            sig_n += 1
        else:
            other_n += 1

    print(f"\n  Keyword clustering:")
    print(f"    Plasma/Fusion:  {plasma_n:2d}/50 ({plasma_n*2}%)")
    print(f"    Bio/Medicine:   {bio_n:2d}/50 ({bio_n*2}%)")
    print(f"    Signal:         {sig_n:2d}/50 ({sig_n*2}%)")
    print(f"    Other:          {other_n:2d}/50 ({other_n*2}%)")

    # ═══════════════════════════════════════════════════════════════
    # FAILLE 5 — ACTIVITY FILTER (min works > 5000)
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print("FAILLE 5 — ACTIVITY FILTER (min works thresholds)")
    print(f"{'='*80}")

    for thresh in [100, 500, 1000, 2000, 5000, 10000, 50000]:
        n = sum(1 for r in holes50 if min(r["wa"], r["wb"]) >= thresh)
        print(f"  min(works) >= {thresh:6,d}: {n:2d}/50 survive")

    print(f"\n  Survivors with min(works) >= 5000:")
    for r in holes50:
        mw = min(r["wa"], r["wb"])
        if mw >= 5000:
            print(f"    z={r['z']:8.1f} | min_w={mw:>10,.0f} | "
                  f"L{r['other_level']} {idx_name.get(r['other_idx'],'?')[:40]}")

    # ═══════════════════════════════════════════════════════════════
    # FAILLE 6 — BASELINE COMPARISON (CRITICAL)
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print("FAILLE 6 — BASELINE COMPARISON (13 random CS/Math × 5 seeds)")
    print(f"{'='*80}")

    header = (f"  {'Label':15s} | {'Pairs':>7s} | {'Cross':>6s} | {'Holes':>6s} | "
              f"{'z<-10':>5s} | {'z<-5':>5s} | {'med_z':>8s} | {'P4max':>10s}")
    print(header)
    print(f"  {'-'*15} | {'-'*7} | {'-'*6} | {'-'*6} | {'-'*5} | {'-'*5} | {'-'*8} | {'-'*10}")

    def row(label, st):
        zc = st["z_cross"]
        pc = st["p4_cross"]
        z10 = int(np.sum(zc < -10)) if len(zc) else 0
        z5 = int(np.sum(zc < -5)) if len(zc) else 0
        mz = float(np.median(zc)) if len(zc) else 0
        pm = float(pc.max()) if len(pc) else 0
        print(f"  {label:15s} | {st['n_pairs']:7,d} | {st['n_cross']:6,d} | "
              f"{st['n_holes']:6,d} | {z10:5d} | {z5:5d} | {mz:8.2f} | {pm:10.6f}")

    row("PHILIPPE", phil_lin)
    for i, bs in enumerate(base_stats):
        row(f"Baseline {baselines[i]['seed']}", bs)

    # Plasma in baselines
    print(f"\n  Plasma concepts in top 50 holes:")
    for i, bs in enumerate(base_stats):
        bh = sorted([r for r in bs["results"] if r["cross"] and r["z"] < 0],
                     key=lambda x: x["z"])[:50]
        bp = sum(1 for r in bh
                 if any(k in idx_name.get(r["other_idx"],"").lower() for k in PLASMA_KW))
        print(f"    Baseline {baselines[i]['seed']}: {bp}/50 plasma")

    # Philippe's plasma count for comparison
    phil_plasma = sum(1 for r in holes50
                      if any(k in idx_name.get(r["other_idx"],"").lower() for k in PLASMA_KW))
    print(f"    PHILIPPE:      {phil_plasma}/50 plasma")

    # ═══════════════════════════════════════════════════════════════
    # FAILLE 8 — MANN-WHITNEY
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print("FAILLE 8 — MANN-WHITNEY (Philippe vs baselines)")
    print(f"{'='*80}")

    for i, bs in enumerate(base_stats):
        if len(phil_lin["z_cross"]) and len(bs["z_cross"]):
            U, p = mannwhitneyu(phil_lin["z_cross"], bs["z_cross"],
                                alternative='two-sided')
            n1, n2 = len(phil_lin["z_cross"]), len(bs["z_cross"])
            Z = (U - n1*n2/2) / np.sqrt(n1*n2*(n1+n2+1)/12)
            r_eff = abs(Z) / np.sqrt(n1 + n2)
            print(f"  vs Baseline {baselines[i]['seed']}: U={U:>12,.0f} | "
                  f"p={p:.2e} | r={r_eff:.4f} | n=({n1:,d},{n2:,d})")

    # Pooled
    all_bz = np.concatenate([b["z_cross"] for b in base_stats if len(b["z_cross"])])
    if len(all_bz) and len(phil_lin["z_cross"]):
        U, p = mannwhitneyu(phil_lin["z_cross"], all_bz, alternative='two-sided')
        n1, n2 = len(phil_lin["z_cross"]), len(all_bz)
        Z = (U - n1*n2/2) / np.sqrt(n1*n2*(n1+n2+1)/12)
        r_eff = abs(Z) / np.sqrt(n1 + n2)
        print(f"\n  vs ALL pooled:   U={U:>12,.0f} | p={p:.2e} | r={r_eff:.4f} | "
              f"n=({n1:,d},{n2:,d})")

    # ═══════════════════════════════════════════════════════════════
    # FAILLE 2 — P4 DISTRIBUTION
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print("FAILLE 2 — P4 DISTRIBUTION (Philippe vs pooled baselines)")
    print(f"{'='*80}")

    all_bp4 = np.concatenate([b["p4_cross"] for b in base_stats if len(b["p4_cross"])])
    pc = phil_lin["p4_cross"]
    if len(pc) and len(all_bp4):
        print(f"  Philippe:  n={len(pc):>6,d} | mean={pc.mean():.6f} | "
              f"median={np.median(pc):.6f} | max={pc.max():.6f}")
        print(f"  Baselines: n={len(all_bp4):>6,d} | mean={all_bp4.mean():.6f} | "
              f"median={np.median(all_bp4):.6f} | max={all_bp4.max():.6f}")
        U, p = mannwhitneyu(pc, all_bp4, alternative='two-sided')
        print(f"  Mann-Whitney P4: U={U:,.0f}, p={p:.2e}")

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print(f"AUDIT COMPLETE — {time.time()-t0:.0f}s")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
