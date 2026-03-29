#!/usr/bin/env python3
"""
Impact Scale — Échelle probabiliste d'impact normalisée par domaine.

Prend impact.db (brut) et produit une échelle calibrée:
1. Flag collabs (>50 auteurs) séparément
2. Normalise le spread par domaine (z-score intra-domaine)
3. Combine rarity + spread normalisé → score d'impact final
4. Calcule le delta temporel (concept births par fenêtre)
5. Classe chaque paper/auteur sur une échelle de 0 à 10

Échelle:
  0-1: Caillou (paper ordinaire dans son domaine)
  2-3: Pierre (au-dessus de la moyenne, touche des concepts rares)
  4-5: Rocher (top 10% du domaine, pont inter-domaines)
  6-7: Météorite (top 1%, crée de nouvelles connexions)
  8-9: Astéroïde (top 0.1%, reconfigure la topologie locale)
  10:  Extinction (top 0.01%, change tout — Gödel, Shannon, Turing)

Output: data/impact_scale.db + data/impact_scale.json

Usage:
    python engine/topology/impact_scale.py
    python engine/topology/impact_scale.py --top 30
"""
import argparse
import json
import math
import os
import sqlite3
import sys
import time
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
IMPACT_DB = ROOT / "data" / "impact.db"
BIRTHS_PATH = ROOT / "data" / "scan" / "concept_births.json"
OUTPUT_DB = ROOT / "data" / "impact_scale.db"
OUTPUT_JSON = ROOT / "data" / "impact_scale.json"


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def load_domain_stats(conn: sqlite3.Connection) -> dict:
    """Compute per-domain mean/std of spread_rare for z-score normalization."""
    rows = conn.execute("""
        SELECT domain,
               COUNT(*) as n,
               AVG(spread_rare) as mean_spread,
               AVG(spread_rare * spread_rare) as mean_sq
        FROM paper_impact
        WHERE domain IS NOT NULL AND spread_rare > 0
        GROUP BY domain
        HAVING COUNT(*) >= 10
    """).fetchall()

    stats = {}
    for domain, n, mean, mean_sq in rows:
        variance = mean_sq - mean * mean
        std = math.sqrt(max(variance, 0))
        stats[domain] = {"n": n, "mean": mean, "std": max(std, 0.001)}

    # Global fallback for rare domains
    global_row = conn.execute("""
        SELECT AVG(spread_rare), AVG(spread_rare * spread_rare)
        FROM paper_impact WHERE spread_rare > 0
    """).fetchone()
    g_mean, g_mean_sq = global_row
    g_std = math.sqrt(max(g_mean_sq - g_mean * g_mean, 0))
    stats["_global"] = {"n": 0, "mean": g_mean, "std": max(g_std, 0.001)}

    return stats


def compute_impact_score(spread_rare: float, weight_rare: float,
                         n_concepts: int, domain: str,
                         domain_stats: dict, is_collab: bool) -> dict:
    """Compute calibrated impact score (0-10 scale).

    Components:
    - z_spread: how unusual is this paper's spread for its domain (z-score)
    - rarity_density: weight_rare / n_concepts = avg rarity per concept
    - combo: weighted combination → mapped to 0-10 scale

    Collabs get a 0.7x penalty (volume ≠ impact).
    """
    if not spread_rare or not weight_rare or not n_concepts:
        return {"score": 0.0, "z_spread": 0.0, "rarity_density": 0.0, "tier": "caillou"}

    # Z-score of spread_rare within domain
    # spread_rare already incorporates rarity weighting — no double layer needed
    ds = domain_stats.get(domain, domain_stats["_global"])
    z_spread = (spread_rare - ds["mean"]) / ds["std"]

    # Rarity density (for reporting only, not used in score)
    rarity_density = weight_rare / n_concepts

    # Bonus for touching many concepts (log scale, mild)
    breadth_bonus = math.log(max(n_concepts, 1)) / math.log(50)  # 1→0, 50→1
    breadth_bonus = min(max(breadth_bonus, 0), 1.0)

    # raw = z_spread + mild breadth bonus
    raw = z_spread + 0.3 * breadth_bonus

    # Collab penalty
    if is_collab:
        raw *= 0.7

    # Map z-score to 0-10 scale (piecewise linear)
    # z ~ N(0,1): -2→0, -1→2, 0→3.5, 1→5, 2→6.5, 3→8, 4→9, 5→9.5, 6+→10
    if raw <= -2:
        score = 0.0
    elif raw <= 0:
        score = (raw + 2) * 1.75  # -2→0, 0→3.5
    elif raw <= 2:
        score = 3.5 + raw * 1.5  # 0→3.5, 2→6.5
    elif raw <= 4:
        score = 6.5 + (raw - 2) * 1.25  # 2→6.5, 4→9
    else:
        score = 9.0 + min((raw - 4) * 0.5, 1.0)  # 4→9, 6+→10
    score = round(min(max(score, 0), 10), 2)

    # Tier
    if score >= 9:
        tier = "extinction"
    elif score >= 7.5:
        tier = "asteroide"
    elif score >= 6:
        tier = "meteorite"
    elif score >= 4:
        tier = "rocher"
    elif score >= 2:
        tier = "pierre"
    else:
        tier = "caillou"

    return {
        "score": score,
        "z_spread": round(z_spread, 3),
        "rarity_density": round(rarity_density, 4),
        "tier": tier,
    }


def build_paper_scale(imp_conn: sqlite3.Connection, out_conn: sqlite3.Connection,
                      domain_stats: dict):
    """Score every paper and write to impact_scale.db."""
    log("Scoring papers...")

    out_conn.execute("DROP TABLE IF EXISTS paper_scale")
    out_conn.execute("""
        CREATE TABLE paper_scale (
            paper_id    TEXT PRIMARY KEY,
            year        INTEGER,
            domain      TEXT,
            score       REAL,
            tier        TEXT,
            z_spread    REAL,
            rarity_density REAL,
            spread_rare REAL,
            weight_rare REAL,
            n_concepts  INTEGER,
            is_collab   INTEGER,
            author_names TEXT
        )
    """)

    batch_size = 10000
    last_rowid = 0
    total = imp_conn.execute("SELECT COUNT(*) FROM paper_impact").fetchone()[0]
    done = 0
    t0 = time.time()

    tier_counts = {}

    while True:
        rows = imp_conn.execute(
            "SELECT rowid, paper_id, year, domain, n_concepts, "
            "spread_rare, weight_rare, author_names "
            "FROM paper_impact WHERE rowid > ? ORDER BY rowid LIMIT ?",
            (last_rowid, batch_size)
        ).fetchall()

        if not rows:
            break

        inserts = []
        for row in rows:
            rowid, paper_id, year, domain, n_concepts, spread_r, weight_r, auth_json = row

            # Detect collab
            is_collab = False
            if auth_json:
                try:
                    authors = json.loads(auth_json)
                    is_collab = len(authors) > 50
                except (json.JSONDecodeError, TypeError):
                    pass

            impact = compute_impact_score(
                spread_r, weight_r, n_concepts or 0,
                domain or "", domain_stats, is_collab
            )

            tier_counts[impact["tier"]] = tier_counts.get(impact["tier"], 0) + 1

            inserts.append((
                paper_id, year, domain,
                impact["score"], impact["tier"],
                impact["z_spread"], impact["rarity_density"],
                spread_r, weight_r, n_concepts,
                1 if is_collab else 0,
                auth_json
            ))

        out_conn.executemany(
            "INSERT OR IGNORE INTO paper_scale VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            inserts
        )
        out_conn.commit()

        last_rowid = rows[-1][0]
        done += len(rows)

        if done % 50000 == 0:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            log(f"  {done:,}/{total:,} ({100*done/total:.0f}%) | {rate:.0f}/s")

    out_conn.commit()
    log(f"  Papers scored: {done:,} in {time.time()-t0:.1f}s")
    log(f"  Distribution: {json.dumps(tier_counts, indent=2)}")

    # Indexes
    out_conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_ps_score ON paper_scale(score DESC);
        CREATE INDEX IF NOT EXISTS idx_ps_tier ON paper_scale(tier);
        CREATE INDEX IF NOT EXISTS idx_ps_year ON paper_scale(year);
        CREATE INDEX IF NOT EXISTS idx_ps_domain ON paper_scale(domain);
    """)


def build_author_scale(out_conn: sqlite3.Connection):
    """Aggregate paper_scale → author_scale."""
    log("Building author_scale...")

    out_conn.execute("DROP TABLE IF EXISTS author_scale")
    out_conn.execute("""
        CREATE TABLE author_scale (
            author_name   TEXT PRIMARY KEY,
            n_papers      INTEGER,
            avg_score     REAL,
            max_score     REAL,
            best_tier     TEXT,
            total_rarity  REAL,
            avg_z_spread  REAL,
            is_collab     INTEGER,
            first_year    INTEGER,
            last_year     INTEGER,
            domains       TEXT
        )
    """)

    # Read all scored papers with authors
    rows = out_conn.execute(
        "SELECT year, domain, score, tier, z_spread, rarity_density, "
        "weight_rare, is_collab, author_names "
        "FROM paper_scale WHERE author_names IS NOT NULL"
    ).fetchall()

    log(f"  Processing {len(rows):,} papers...")

    authors = {}
    for row in rows:
        year, domain, score, tier, z_sp, rarity_d, w_rare, is_col, auth_json = row
        try:
            names = json.loads(auth_json)
        except (json.JSONDecodeError, TypeError):
            continue

        for name in names:
            if not name or len(name) < 2:
                continue
            if name not in authors:
                authors[name] = {
                    "scores": [], "tiers": [], "z_spreads": [],
                    "w_rare_total": 0, "years": [], "domains": set(),
                    "is_collab": 0
                }
            a = authors[name]
            a["scores"].append(score or 0)
            a["tiers"].append(tier or "caillou")
            a["z_spreads"].append(z_sp or 0)
            a["w_rare_total"] += w_rare or 0
            if year:
                a["years"].append(year)
            if domain:
                a["domains"].add(domain)
            if is_col:
                a["is_collab"] = 1

    # Tier ranking for "best"
    tier_rank = {"extinction": 6, "asteroide": 5, "meteorite": 4,
                 "rocher": 3, "pierre": 2, "caillou": 1}

    inserts = []
    for name, a in authors.items():
        n = len(a["scores"])
        avg_score = sum(a["scores"]) / n
        max_score = max(a["scores"])
        best_tier = max(a["tiers"], key=lambda t: tier_rank.get(t, 0))
        avg_z = sum(a["z_spreads"]) / n

        inserts.append((
            name, n, round(avg_score, 2), round(max_score, 2),
            best_tier, round(a["w_rare_total"], 4), round(avg_z, 3),
            a["is_collab"],
            min(a["years"]) if a["years"] else None,
            max(a["years"]) if a["years"] else None,
            json.dumps(sorted(a["domains"]), ensure_ascii=False)
        ))

    out_conn.executemany(
        "INSERT OR IGNORE INTO author_scale VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        inserts
    )

    out_conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_as_avg ON author_scale(avg_score DESC);
        CREATE INDEX IF NOT EXISTS idx_as_max ON author_scale(max_score DESC);
        CREATE INDEX IF NOT EXISTS idx_as_tier ON author_scale(best_tier);
        CREATE INDEX IF NOT EXISTS idx_as_papers ON author_scale(n_papers DESC);
    """)
    out_conn.commit()
    log(f"  {len(inserts):,} authors scored")


def build_year_scale(out_conn: sqlite3.Connection):
    """Aggregate paper_scale → year_scale with concept birth delta."""
    log("Building year_scale...")

    # Load concept births
    births_by_year = {}
    if BIRTHS_PATH.exists():
        with open(BIRTHS_PATH, "r", encoding="utf-8") as f:
            births = json.load(f)
        for cid, year in births.items():
            births_by_year[year] = births_by_year.get(year, 0) + 1

    out_conn.execute("DROP TABLE IF EXISTS year_scale")
    out_conn.execute("""
        CREATE TABLE year_scale (
            year          INTEGER PRIMARY KEY,
            n_papers      INTEGER,
            avg_score     REAL,
            max_score     REAL,
            n_meteorites  INTEGER,
            n_asteroides  INTEGER,
            n_extinctions INTEGER,
            concept_births INTEGER,
            cumulative_concepts INTEGER
        )
    """)

    rows = out_conn.execute("""
        SELECT year, COUNT(*), AVG(score), MAX(score),
               SUM(CASE WHEN tier = 'meteorite' THEN 1 ELSE 0 END),
               SUM(CASE WHEN tier = 'asteroide' THEN 1 ELSE 0 END),
               SUM(CASE WHEN tier = 'extinction' THEN 1 ELSE 0 END)
        FROM paper_scale
        WHERE year IS NOT NULL
        GROUP BY year ORDER BY year
    """).fetchall()

    cumulative = 0
    for r in rows:
        year = r[0]
        births = births_by_year.get(year, 0)
        cumulative += births
        out_conn.execute(
            "INSERT INTO year_scale VALUES (?,?,?,?,?,?,?,?,?)",
            (year, r[1], round(r[2], 3), round(r[3], 2),
             r[4], r[5], r[6], births, cumulative)
        )

    out_conn.commit()
    n = out_conn.execute("SELECT COUNT(*) FROM year_scale").fetchone()[0]
    log(f"  {n} years with concept births + tier counts")


def build_domain_scale(out_conn: sqlite3.Connection):
    """Per-domain summary with calibration data."""
    log("Building domain_scale...")

    out_conn.execute("DROP TABLE IF EXISTS domain_scale")
    out_conn.execute("""
        CREATE TABLE domain_scale (
            domain        TEXT PRIMARY KEY,
            n_papers      INTEGER,
            avg_score     REAL,
            avg_spread    REAL,
            std_spread    REAL,
            pct_meteorite REAL,
            pct_rocher    REAL
        )
    """)

    out_conn.execute("""
        INSERT INTO domain_scale
        SELECT domain, COUNT(*), AVG(score),
               AVG(spread_rare),
               0,
               100.0 * SUM(CASE WHEN tier IN ('meteorite','asteroide','extinction') THEN 1 ELSE 0 END) / COUNT(*),
               100.0 * SUM(CASE WHEN tier = 'rocher' THEN 1 ELSE 0 END) / COUNT(*)
        FROM paper_scale
        WHERE domain IS NOT NULL AND domain != ''
        GROUP BY domain
        HAVING COUNT(*) >= 10
    """)
    out_conn.commit()
    log("  Done")


def export_summary(out_conn: sqlite3.Connection):
    """Export top results to JSON."""
    log("Exporting summary JSON...")

    summary = {
        "meta": {
            "description": "Impact Scale — echelle probabiliste 0-10 normalisee par domaine",
            "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tiers": {
                "0-1": "caillou (paper ordinaire)",
                "2-3": "pierre (au-dessus de la moyenne)",
                "4-5": "rocher (top 10%, pont inter-domaines)",
                "6-7": "meteorite (top 1%, nouvelles connexions)",
                "8-9": "asteroide (top 0.1%, reconfigure la topologie)",
                "10": "extinction (top 0.01%, change tout)"
            }
        },
        "distribution": {},
        "top_papers": [],
        "top_authors_avg": [],
        "top_authors_max": [],
        "domain_calibration": [],
        "year_evolution": [],
    }

    # Distribution
    for tier in ["caillou", "pierre", "rocher", "meteorite", "asteroide", "extinction"]:
        n = out_conn.execute(
            "SELECT COUNT(*) FROM paper_scale WHERE tier = ?", (tier,)
        ).fetchone()[0]
        summary["distribution"][tier] = n

    # Top 50 papers
    rows = out_conn.execute("""
        SELECT paper_id, year, domain, score, tier, z_spread,
               rarity_density, spread_rare, n_concepts, is_collab, author_names
        FROM paper_scale ORDER BY score DESC LIMIT 50
    """).fetchall()
    for r in rows:
        authors = []
        if r[10]:
            try:
                authors = json.loads(r[10])[:5]
            except:
                pass
        summary["top_papers"].append({
            "paper_id": r[0], "year": r[1], "domain": r[2],
            "score": r[3], "tier": r[4], "z_spread": r[5],
            "rarity_density": r[6], "spread_rare": r[7],
            "n_concepts": r[8], "is_collab": bool(r[9]),
            "authors": authors,
        })

    # Top 30 authors by avg score (min 20 papers, no collabs)
    rows = out_conn.execute("""
        SELECT author_name, n_papers, avg_score, max_score, best_tier,
               avg_z_spread, first_year, last_year
        FROM author_scale
        WHERE n_papers >= 20 AND is_collab = 0
        ORDER BY avg_score DESC LIMIT 30
    """).fetchall()
    for r in rows:
        summary["top_authors_avg"].append({
            "name": r[0], "n_papers": r[1], "avg_score": r[2],
            "max_score": r[3], "best_tier": r[4],
            "avg_z_spread": r[5], "years": f"{r[6]}-{r[7]}",
        })

    # Top 30 by max score (single best paper)
    rows = out_conn.execute("""
        SELECT author_name, n_papers, avg_score, max_score, best_tier,
               avg_z_spread, first_year, last_year
        FROM author_scale
        WHERE n_papers >= 5 AND is_collab = 0
        ORDER BY max_score DESC LIMIT 30
    """).fetchall()
    for r in rows:
        summary["top_authors_max"].append({
            "name": r[0], "n_papers": r[1], "avg_score": r[2],
            "max_score": r[3], "best_tier": r[4],
            "years": f"{r[6]}-{r[7]}",
        })

    # Domain calibration
    rows = out_conn.execute(
        "SELECT * FROM domain_scale ORDER BY n_papers DESC"
    ).fetchall()
    for r in rows:
        summary["domain_calibration"].append({
            "domain": r[0], "n_papers": r[1], "avg_score": r[2],
            "avg_spread": r[3], "pct_meteorite": round(r[5], 2),
        })

    # Year evolution
    rows = out_conn.execute(
        "SELECT * FROM year_scale ORDER BY year"
    ).fetchall()
    for r in rows:
        summary["year_evolution"].append({
            "year": r[0], "n_papers": r[1], "avg_score": r[2],
            "max_score": r[3], "n_meteorites": r[4],
            "n_asteroides": r[5], "n_extinctions": r[6],
            "concept_births": r[7], "cumulative_concepts": r[8],
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log(f"  Exported to {OUTPUT_JSON} ({OUTPUT_JSON.stat().st_size / 1e3:.0f} KB)")


def show_top(out_conn: sqlite3.Connection, n: int):
    """Display top results."""
    print(f"\n{'='*80}")
    print(f"TOP {n} PAPERS BY IMPACT SCORE")
    print(f"{'='*80}")
    rows = out_conn.execute("""
        SELECT paper_id, year, domain, score, tier, z_spread, n_concepts, author_names
        FROM paper_scale ORDER BY score DESC LIMIT ?
    """, (n,)).fetchall()
    for i, r in enumerate(rows, 1):
        authors = ""
        if r[7]:
            try:
                a = json.loads(r[7])
                authors = a[0] if a else ""
            except:
                pass
        print(f"  {i:2d}. [{r[4]:10s}] {r[3]:5.2f} | {r[0]:30s} | {r[1]} {r[2]:15s} "
              f"| z={r[5]:+.2f} | {r[6]}c | {authors[:30]}")

    print(f"\n{'='*80}")
    print(f"TOP {n} AUTHORS BY AVG SCORE (min 20 papers, solo)")
    print(f"{'='*80}")
    rows = out_conn.execute("""
        SELECT author_name, n_papers, avg_score, max_score, best_tier,
               avg_z_spread, first_year, last_year
        FROM author_scale
        WHERE n_papers >= 20 AND is_collab = 0
        ORDER BY avg_score DESC LIMIT ?
    """, (n,)).fetchall()
    for i, r in enumerate(rows, 1):
        print(f"  {i:2d}. {r[0][:35]:35s} | {r[1]:3d} papers | avg {r[2]:.2f} "
              f"| max {r[3]:.2f} [{r[4]:10s}] | z={r[5]:+.2f} | {r[6]}-{r[7]}")

    print(f"\n{'='*80}")
    print(f"TIER DISTRIBUTION")
    print(f"{'='*80}")
    for tier in ["extinction", "asteroide", "meteorite", "rocher", "pierre", "caillou"]:
        n_t = out_conn.execute(
            "SELECT COUNT(*) FROM paper_scale WHERE tier = ?", (tier,)
        ).fetchone()[0]
        total = out_conn.execute("SELECT COUNT(*) FROM paper_scale").fetchone()[0]
        bar = "#" * int(50 * n_t / total) if total else ""
        print(f"  {tier:12s}: {n_t:>7,} ({100*n_t/total:5.1f}%) {bar}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=0)
    args = parser.parse_args()

    if args.top and OUTPUT_DB.exists():
        out_conn = sqlite3.connect(str(OUTPUT_DB))
        show_top(out_conn, args.top)
        out_conn.close()
        return

    if not IMPACT_DB.exists():
        print(f"ERROR: {IMPACT_DB} not found. Run impact_scanner.py first.")
        sys.exit(1)

    log("=" * 60)
    log("IMPACT SCALE — Building calibrated 0-10 scale")
    log("=" * 60)

    imp_conn = sqlite3.connect(str(IMPACT_DB))
    out_conn = sqlite3.connect(str(OUTPUT_DB))
    out_conn.execute("PRAGMA journal_mode=WAL")

    # Step 1: Domain calibration
    log("Step 1: Computing domain baselines...")
    domain_stats = load_domain_stats(imp_conn)
    for d in sorted(domain_stats.keys())[:10]:
        s = domain_stats[d]
        log(f"  {d:20s}: mean={s['mean']:.3f} std={s['std']:.3f} n={s['n']:,}")

    # Step 2: Score all papers
    build_paper_scale(imp_conn, out_conn, domain_stats)

    # Step 3: Author aggregation
    build_author_scale(out_conn)

    # Step 4: Year aggregation with concept births
    build_year_scale(out_conn)

    # Step 5: Domain summary
    build_domain_scale(out_conn)

    # Step 6: Export JSON summary
    export_summary(out_conn)

    imp_conn.close()
    out_conn.close()

    log("DONE.")
    log(f"Output: {OUTPUT_DB} ({OUTPUT_DB.stat().st_size / 1e6:.1f} MB)")

    # Show results
    out_conn = sqlite3.connect(str(OUTPUT_DB))
    show_top(out_conn, 20)
    out_conn.close()


if __name__ == "__main__":
    main()
