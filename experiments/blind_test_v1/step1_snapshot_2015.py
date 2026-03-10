"""
ÉTAPE 1 — Snapshot 2015 gelé via API OpenAlex
==============================================
1. Récupère les top 100 concepts level 1-2 (par works_count global)
2. Pour chacun : works_count filtré à publication_year ≤ 2015
3. Pour chaque paire : co-occurrence (works taggués avec les 2) filtré ≤ 2015
4. Sauvegarde → blind_test/data_2015_frozen.json

ZÉRO données post-2015.
Rate limit : max 5 req/s (polite 200ms sleep)
"""

import json
import time
import os
import sys
import itertools
import requests

# ══════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(OUT_DIR, "data_2015_frozen.json")
CACHE_FILE = os.path.join(OUT_DIR, "_api_cache.json")

API = "https://api.openalex.org"
MAILTO = "sky@yggdrasil-engine.dev"  # polite pool
HEADERS = {"User-Agent": f"YggdrasilEngine/1.0 (mailto:{MAILTO})"}
SLEEP = 0.22  # ~4.5 req/s, under the 5/s limit

# ══════════════════════════════════════════════════════════
# API helpers
# ══════════════════════════════════════════════════════════
_cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        _cache = json.load(f)
    print(f"[cache] Loaded {len(_cache)} cached responses")

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(_cache, f)

def api_get(url, params=None):
    """GET with cache + rate limit + retry."""
    key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    if key in _cache:
        return _cache[key]

    for attempt in range(3):
        try:
            time.sleep(SLEEP)
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 5))
                print(f"  [429] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            _cache[key] = data
            return data
        except Exception as e:
            print(f"  [ERR] Attempt {attempt+1}/3: {e}")
            time.sleep(2 ** attempt)

    print(f"  [FAIL] {url}")
    return None

# ══════════════════════════════════════════════════════════
# STEP 1a: Get top 100 concepts level 1-2 by works_count
# ══════════════════════════════════════════════════════════
print("=" * 60)
print("ÉTAPE 1a — Top 100 concepts level 1-2")
print("=" * 60)

concepts = []
for page in range(1, 5):  # 4 pages × 25 = 100
    print(f"  Fetching concepts page {page}...")
    data = api_get(f"{API}/concepts", {
        "filter": "level:1|2",
        "sort": "works_count:desc",
        "per_page": "25",
        "page": str(page),
        "mailto": MAILTO,
    })
    if not data or "results" not in data:
        print(f"  [FAIL] Page {page}")
        break
    for c in data["results"]:
        concepts.append({
            "id": c["id"].replace("https://openalex.org/", ""),
            "display_name": c["display_name"],
            "level": c["level"],
            "works_count_global": c["works_count"],
        })

print(f"  → {len(concepts)} concepts récupérés")
save_cache()

# Show first 10
for i, c in enumerate(concepts[:10]):
    print(f"  {i+1:3d}. {c['display_name']:<40s} L{c['level']} | {c['works_count_global']:>12,} works")

# ══════════════════════════════════════════════════════════
# STEP 1b: works_count per concept filtered to ≤2015
# ══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ÉTAPE 1b — works_count par concept (≤2015 UNIQUEMENT)")
print("=" * 60)

for i, c in enumerate(concepts):
    cid = c["id"]
    # Use group_by to get count of works with this concept published ≤2015
    data = api_get(f"{API}/works", {
        "filter": f"concepts.id:{cid},publication_year:<2016",
        "per_page": "1",
        "mailto": MAILTO,
    })
    if data and "meta" in data:
        c["works_count_2015"] = data["meta"]["count"]
    else:
        c["works_count_2015"] = 0

    if (i + 1) % 10 == 0 or i == 0:
        print(f"  [{i+1:3d}/100] {c['display_name']:<35s} → {c['works_count_2015']:>10,} works ≤2015")

save_cache()
print(f"  → Done. Sample: {concepts[0]['display_name']} = {concepts[0]['works_count_2015']:,}")

# ══════════════════════════════════════════════════════════
# STEP 1c: Co-occurrence matrix (pairwise, ≤2015)
# ══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ÉTAPE 1c — Matrice de co-occurrence (paires, ≤2015)")
print("=" * 60)

n = len(concepts)
n_pairs = n * (n - 1) // 2
print(f"  {n} concepts → {n_pairs} paires à requêter")
print(f"  Temps estimé : ~{n_pairs * SLEEP / 60:.0f} min")

cooccurrence = {}  # "C123|C456" → count
done = 0
t0 = time.time()

for i in range(n):
    for j in range(i + 1, n):
        cid_a = concepts[i]["id"]
        cid_b = concepts[j]["id"]
        pair_key = f"{cid_a}|{cid_b}"

        data = api_get(f"{API}/works", {
            "filter": f"concepts.id:{cid_a},concepts.id:{cid_b},publication_year:<2016",
            "per_page": "1",
            "mailto": MAILTO,
        })

        if data and "meta" in data:
            cooccurrence[pair_key] = data["meta"]["count"]
        else:
            cooccurrence[pair_key] = 0

        done += 1
        if done % 100 == 0 or done == 1:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta = (n_pairs - done) / rate / 60 if rate > 0 else 0
            print(f"  [{done:5d}/{n_pairs}] {rate:.1f} req/s | ETA {eta:.0f}min | last: {concepts[i]['display_name'][:20]} × {concepts[j]['display_name'][:20]} = {cooccurrence[pair_key]:,}")

        # Save cache every 500 pairs
        if done % 500 == 0:
            save_cache()

save_cache()
elapsed_total = time.time() - t0
print(f"  → Done. {done} paires en {elapsed_total/60:.1f} min")

# ══════════════════════════════════════════════════════════
# STEP 1d: Save frozen data
# ══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ÉTAPE 1d — Sauvegarde")
print("=" * 60)

# Count non-zero co-occurrences
nonzero = sum(1 for v in cooccurrence.values() if v > 0)

result = {
    "meta": {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": "OpenAlex API, filter=publication_year:<2016",
        "n_concepts": len(concepts),
        "n_pairs": len(cooccurrence),
        "n_nonzero_cooc": nonzero,
        "cutoff_year": 2015,
        "warning": "ZERO post-2015 data in this file"
    },
    "concepts": concepts,
    "cooccurrence": cooccurrence,
}

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

sz = os.path.getsize(OUT_FILE)
print(f"  → {OUT_FILE}")
print(f"  → {sz:,} bytes ({sz/1024:.0f} KB)")
print(f"  → {len(concepts)} concepts, {len(cooccurrence)} paires, {nonzero} non-zero")
print()
print("ÉTAPE 1 TERMINÉE. Zéro donnée post-2015.")
