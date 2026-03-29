"""Concept birth x impact correlation analysis.

For each concept with both a birth year and a temporal impact curve,
compare the average impact in the first window after birth vs later windows.
"""
import sys, json, sqlite3, statistics, os
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

BASE = "d:/ygg/yggdrasil-engine"

# Load births
with open(f"{BASE}/data/scan/concept_births.json", encoding="utf-8") as f:
    births = json.load(f)
print(f"Births loaded: {len(births)} concepts")

# Load temporal curves
conn = sqlite3.connect(f"{BASE}/data/impact_concepts.db")
cur = conn.cursor()
cur.execute("SELECT concept_id, temporal_curve, avg_score, n_papers FROM concept_impact")
rows = cur.fetchall()
conn.close()
print(f"Impact rows: {len(rows)}")


def window_to_year(w):
    """Parse window string to representative year."""
    if w.endswith("s") and len(w) == 5:  # '1960s' etc
        return int(w[:4])
    try:
        return int(w)
    except Exception:
        return None


results = []
skipped_no_curve = 0
skipped_no_birth_window = 0

for concept_id, tc_json, avg_score, n_papers in rows:
    cid = str(concept_id)
    if cid not in births:
        continue
    if not tc_json:
        skipped_no_curve += 1
        continue

    birth_year = births[cid]
    curve = json.loads(tc_json)

    # Sort windows by year
    windows = []
    for w in curve:
        y = window_to_year(w["window"])
        if y is not None:
            windows.append((y, w))
    windows.sort(key=lambda x: x[0])

    if not windows:
        skipped_no_curve += 1
        continue

    # Find the birth window: first window at or near birth year
    birth_windows = []
    later_windows = []
    found_birth = False
    for y, w in windows:
        if not found_birth:
            if y >= birth_year - 10:
                birth_windows.append(w)
                found_birth = True
        else:
            later_windows.append(w)

    if not birth_windows or not later_windows:
        skipped_no_birth_window += 1
        continue

    birth_avg = birth_windows[0]["avg"]
    birth_n = birth_windows[0]["n"]

    later_total_n = sum(w["n"] for w in later_windows)
    later_avg = sum(w["avg"] * w["n"] for w in later_windows) / max(1, later_total_n)

    # Trend: first half vs second half of later windows
    if len(later_windows) >= 4:
        mid = len(later_windows) // 2
        first_half = later_windows[:mid]
        second_half = later_windows[mid:]
        fh_avg = sum(w["avg"] * w["n"] for w in first_half) / max(1, sum(w["n"] for w in first_half))
        sh_avg = sum(w["avg"] * w["n"] for w in second_half) / max(1, sum(w["n"] for w in second_half))
        if sh_avg > fh_avg * 1.05:
            trend = "growing"
        elif sh_avg < fh_avg * 0.95:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "too_few_windows"

    ratio = birth_avg / later_avg if later_avg > 0 else None

    results.append({
        "concept_id": cid,
        "birth_year": birth_year,
        "birth_avg_impact": round(birth_avg, 3),
        "birth_n_papers": birth_n,
        "later_avg_impact": round(later_avg, 3),
        "later_n_papers": later_total_n,
        "birth_vs_later_ratio": round(ratio, 3) if ratio else None,
        "trend": trend,
        "overall_avg": avg_score,
        "total_papers": n_papers,
    })

print(f"Matched: {len(results)}")
print(f"Skipped no curve: {skipped_no_curve}")
print(f"Skipped no birth window match: {skipped_no_birth_window}")

# --- Aggregate stats ---
birth_higher = sum(1 for r in results if r["birth_vs_later_ratio"] and r["birth_vs_later_ratio"] > 1.0)
birth_lower = sum(1 for r in results if r["birth_vs_later_ratio"] and r["birth_vs_later_ratio"] < 1.0)
birth_equal = sum(1 for r in results if r["birth_vs_later_ratio"] and abs(r["birth_vs_later_ratio"] - 1.0) < 0.01)

trends = Counter(r["trend"] for r in results)
ratios = [r["birth_vs_later_ratio"] for r in results if r["birth_vs_later_ratio"]]
median_ratio = statistics.median(ratios)
mean_ratio = statistics.mean(ratios)

print(f"\n=== AGGREGATE STATS ===")
print(f"Total analyzed: {len(results)}")
print(f"Birth impact HIGHER than later: {birth_higher} ({100*birth_higher/len(results):.1f}%)")
print(f"Birth impact LOWER than later:  {birth_lower} ({100*birth_lower/len(results):.1f}%)")
print(f"Birth impact ~EQUAL:            {birth_equal} ({100*birth_equal/len(results):.1f}%)")
print(f"Mean birth/later ratio: {mean_ratio:.3f}")
print(f"Median birth/later ratio: {median_ratio:.3f}")
print(f"Trends: {dict(trends)}")

# Top first-movers (min 3 papers at birth for significance)
sorted_by_ratio = sorted(
    [r for r in results if r["birth_vs_later_ratio"] and r["birth_n_papers"] >= 3],
    key=lambda x: x["birth_vs_later_ratio"], reverse=True
)

print(f"\n=== TOP 15 FIRST-MOVER ADVANTAGE (birth >> later) ===")
for r in sorted_by_ratio[:15]:
    print(f"  C{r['concept_id']}: birth={r['birth_avg_impact']:.2f} later={r['later_avg_impact']:.2f} "
          f"ratio={r['birth_vs_later_ratio']:.2f} (birth_n={r['birth_n_papers']}, year={r['birth_year']})")

print(f"\n=== TOP 15 SLOW GROWERS (birth << later) ===")
for r in sorted_by_ratio[-15:]:
    print(f"  C{r['concept_id']}: birth={r['birth_avg_impact']:.2f} later={r['later_avg_impact']:.2f} "
          f"ratio={r['birth_vs_later_ratio']:.2f} (birth_n={r['birth_n_papers']}, year={r['birth_year']})")

# Ratio distribution
buckets = {"<0.5": 0, "0.5-0.8": 0, "0.8-1.0": 0, "1.0-1.2": 0, "1.2-1.5": 0, "1.5-2.0": 0, ">2.0": 0}
for r in ratios:
    if r < 0.5:
        buckets["<0.5"] += 1
    elif r < 0.8:
        buckets["0.5-0.8"] += 1
    elif r < 1.0:
        buckets["0.8-1.0"] += 1
    elif r < 1.2:
        buckets["1.0-1.2"] += 1
    elif r < 1.5:
        buckets["1.2-1.5"] += 1
    elif r < 2.0:
        buckets["1.5-2.0"] += 1
    else:
        buckets[">2.0"] += 1

print(f"\nRatio distribution:")
for k, v in buckets.items():
    pct = 100 * v / len(ratios)
    bar = "#" * int(pct / 2)
    print(f"  {k:>8s}: {v:5d} ({pct:5.1f}%) {bar}")

# By birth decade
decade_stats = defaultdict(list)
for r in results:
    if r["birth_vs_later_ratio"]:
        decade = (r["birth_year"] // 10) * 10
        decade_stats[decade].append(r["birth_vs_later_ratio"])

print(f"\nMedian ratio by birth decade:")
for d in sorted(decade_stats.keys()):
    vals = decade_stats[d]
    print(f"  {d}s: median={statistics.median(vals):.3f}, mean={statistics.mean(vals):.3f}, n={len(vals)}")

# --- Save results ---
output = {
    "meta": {
        "description": "Concept birth x impact correlation analysis",
        "question": "Do first papers touching a concept have higher impact than later papers?",
        "date": "2026-03-29",
        "n_births_loaded": len(births),
        "n_impact_rows": len(rows),
        "n_matched": len(results),
    },
    "aggregate": {
        "birth_higher_pct": round(100 * birth_higher / len(results), 1),
        "birth_lower_pct": round(100 * birth_lower / len(results), 1),
        "birth_equal_pct": round(100 * birth_equal / len(results), 1),
        "mean_ratio": round(mean_ratio, 3),
        "median_ratio": round(median_ratio, 3),
        "trends": dict(trends),
        "ratio_distribution": buckets,
        "by_decade": {
            str(d): {
                "median": round(statistics.median(v), 3),
                "mean": round(statistics.mean(v), 3),
                "n": len(v),
            }
            for d, v in sorted(decade_stats.items())
        },
    },
    "top_first_movers": sorted_by_ratio[:50],
    "top_slow_growers": sorted_by_ratio[-50:],
    "all_concepts": results,
}

os.makedirs(f"{BASE}/data/results", exist_ok=True)
out_path = f"{BASE}/data/results/scan_concept_birth_impact.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=1)

fsize = os.path.getsize(out_path) / 1024 / 1024
print(f"\nSaved to data/results/scan_concept_birth_impact.json ({fsize:.1f} MB)")
