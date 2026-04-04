"""
CARMACK MOVES — Validation dans WT3
Cherche les papiers réels pour les 19 formules du scanner Muninn.
+ Détecte les trous structurels (co-occurrences faibles entre domaines)
"""
import sqlite3
import json
import sys
import os

PYTHON = r"C:\Users\ludov\AppData\Local\Programs\Python\Python313\python.exe"
DB = "d:/ygg/yggdrasil-engine/data/wt3.db"
CONCEPTS_FILE = "d:/ygg/yggdrasil-engine/data/scan/concepts_65k.json"
OUT = "d:/ygg/yggdrasil-engine/data/results/scan_carmack_security.json"

# ── STEP 1: Chercher les concepts OpenAlex pertinents ──
print("=" * 70)
print("CARMACK SECURITY SCAN — Validation WT3")
print("=" * 70)

# Charger les concepts
print("\n[1/4] Chargement concepts_65k.json...")
with open(CONCEPTS_FILE, "r", encoding="utf-8") as f:
    cdata = json.load(f)

concepts = cdata.get("concepts", {})
print(f"  → {len(concepts)} concepts chargés")

# Mots-clés à chercher dans les noms de concepts
CONCEPT_SEARCHES = {
    # AXE 1 - Épidémiologie
    "epidemi": "AXE1",
    "epidemic": "AXE1",
    "SIR model": "AXE1",
    "SIS model": "AXE1",
    "contagion": "AXE1",
    "percolation": "AXE1",
    "spreading": "AXE1",

    # AXE 2 - Finance
    "systemic risk": "AXE2",
    "financial network": "AXE2",
    "financial contagion": "AXE2",
    "credit risk": "AXE2",
    "default": "AXE2",
    "interbank": "AXE2",
    "value at risk": "AXE2",

    # AXE 3 - Physique
    "heat equation": "AXE3",
    "diffusion": "AXE3",
    "ising": "AXE3",
    "phase transition": "AXE3",
    "reaction-diffusion": "AXE3",
    "percolation threshold": "AXE3",
    "laplacian": "AXE3",
    "spectral": "AXE3",

    # AXE 4 - Neurosciences
    "predictive coding": "AXE4",
    "free energy": "AXE4",
    "attention": "AXE4",
    "anomaly detect": "AXE4",
    "mismatch": "AXE4",
    "surprise": "AXE4",

    # AXE 5 - Écologie
    "metapopulation": "AXE5",
    "island biogeography": "AXE5",
    "invasion": "AXE5",
    "lotka-volterra": "AXE5",
    "population dynamics": "AXE5",
    "ecological network": "AXE5",
    "species-area": "AXE5",

    # AXE 6 - Théorie des jeux
    "game theory": "AXE6",
    "stackelberg": "AXE6",
    "multi-armed bandit": "AXE6",
    "influence maximization": "AXE6",
    "optimal stopping": "AXE6",
    "set cover": "AXE6",
    "nash equilibrium": "AXE6",
    "mechanism design": "AXE6",

    # AXE 7 - Biologie cellulaire
    "signal transduction": "AXE7",
    "mapk": "AXE7",
    "phosphorylation": "AXE7",
    "apoptosis": "AXE7",
    "cytokine": "AXE7",
    "receptor": "AXE7",
    "ultrasensitiv": "AXE7",
    "cell signaling": "AXE7",
    "cascade": "AXE7",

    # SECURITY (pour les trous structurels)
    "vulnerability": "SEC",
    "software security": "SEC",
    "static analysis": "SEC",
    "malware": "SEC",
    "intrusion detect": "SEC",
    "fault local": "SEC",
    "software defect": "SEC",
    "code analysis": "SEC",
    "software testing": "SEC",
}

# Chercher dans les concepts
concept_matches = {}
for cid, info in concepts.items():
    cname = info.get("name", "").lower()
    for keyword, axe in CONCEPT_SEARCHES.items():
        if keyword.lower() in cname:
            idx = info.get("idx", -1)
            wc = info.get("works_count", 0)
            if axe not in concept_matches:
                concept_matches[axe] = []
            concept_matches[axe].append({
                "id": cid,
                "idx": idx,
                "name": info.get("name", ""),
                "level": info.get("level", -1),
                "works_count": wc,
                "matched_keyword": keyword,
            })

print(f"\n  Concepts trouvés par axe:")
for axe in sorted(concept_matches.keys()):
    matches = concept_matches[axe]
    print(f"    {axe}: {len(matches)} concepts")
    # Top 5 par works_count
    top = sorted(matches, key=lambda x: -x["works_count"])[:5]
    for m in top:
        print(f"      [{m['idx']:>5}] {m['name']:40s} ({m['works_count']:>10,} works)  ← {m['matched_keyword']}")

# ── STEP 2: Chercher les papiers dans WT3 ──
print(f"\n[2/4] Connexion WT3 ({DB})...")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Vérifier quelles colonnes existent
cur.execute("PRAGMA table_info(papers)")
cols = [r['name'] for r in cur.fetchall()]
print(f"  → colonnes papers: {cols}")
has_title = "title" in cols

# Requêtes titre pour les 19 formules
TITLE_QUERIES = {
    # AXE 1 - Épidémiologie sur graphes
    "F01: SIR scale-free": "title LIKE '%epidemic%' AND (title LIKE '%scale-free%' OR title LIKE '%scale free%')",
    "F01: Pastor-Satorras": "title LIKE '%Pastor-Satorras%' OR title LIKE '%epidemic%scale%free%network%'",
    "F02: percolation+network": "title LIKE '%percolation%' AND title LIKE '%network%'",
    "F02: Molloy-Reed": "title LIKE '%Molloy%Reed%' OR (title LIKE '%degree sequence%' AND title LIKE '%random graph%')",
    "F03: competing virus": "title LIKE '%competing%' AND (title LIKE '%virus%' OR title LIKE '%epidemic%')",
    "F03: multi-strain": "title LIKE '%multi%strain%' OR title LIKE '%two%virus%' OR title LIKE '%competing%spread%'",

    # AXE 2 - Finance
    "F04: DebtRank": "title LIKE '%DebtRank%' OR title LIKE '%debt rank%'",
    "F04: systemic risk+network": "title LIKE '%systemic risk%' AND title LIKE '%network%'",
    "F05: Eisenberg-Noe": "title LIKE '%Eisenberg%' AND title LIKE '%Noe%'",
    "F05: clearing+payment+network": "title LIKE '%clearing%' AND title LIKE '%payment%'",
    "F05: financial contagion": "title LIKE '%financial contagion%'",

    # AXE 3 - Physique
    "F06: heat kernel+graph": "title LIKE '%heat kernel%' AND title LIKE '%graph%'",
    "F06: diffusion+graph+spectral": "title LIKE '%diffusion%' AND title LIKE '%graph%' AND title LIKE '%spectral%'",
    "F07: Ising+network": "title LIKE '%Ising%' AND title LIKE '%network%'",
    "F07: Ising+scale-free": "title LIKE '%Ising%' AND (title LIKE '%scale-free%' OR title LIKE '%scale free%')",
    "F08: Fisher-KPP": "title LIKE '%Fisher-KPP%' OR title LIKE '%Fisher KPP%'",
    "F08: reaction-diffusion+network": "title LIKE '%reaction%diffusion%' AND title LIKE '%network%'",

    # AXE 4 - Neurosciences
    "F09: free energy+brain": "title LIKE '%free energy%' AND (title LIKE '%brain%' OR title LIKE '%neural%' OR title LIKE '%cortex%')",
    "F09: predictive coding": "title LIKE '%predictive coding%'",
    "F10: biased competition": "title LIKE '%biased competition%'",
    "F10: selective attention+model": "title LIKE '%selective attention%' AND title LIKE '%model%'",

    # AXE 5 - Écologie
    "F11: metapopulation": "title LIKE '%metapopulation%'",
    "F11: metapopulation+network": "title LIKE '%metapopulation%' AND title LIKE '%network%'",
    "F12: island biogeography": "title LIKE '%island biogeography%' OR title LIKE '%island%biogeograph%'",

    # AXE 6 - Théorie des jeux
    "F13: influence maximization": "title LIKE '%influence maximization%' OR title LIKE '%influence minimization%'",
    "F13: network immunization": "title LIKE '%network immunization%' OR (title LIKE '%immuniz%' AND title LIKE '%network%')",
    "F14: multi-armed bandit": "title LIKE '%multi%armed bandit%' OR title LIKE '%bandit%UCB%'",
    "F15: secretary problem": "title LIKE '%secretary problem%' OR title LIKE '%optimal stopping%'",

    # AXE 7 - Biologie cellulaire
    "F16: ultrasensitivity": "title LIKE '%ultrasensitiv%'",
    "F16: Goldbeter-Koshland": "title LIKE '%Goldbeter%' OR title LIKE '%Koshland%'",
    "F17: MAPK cascade": "title LIKE '%MAPK%' AND title LIKE '%cascade%'",
    "F17: signal amplification+cascade": "title LIKE '%signal%' AND title LIKE '%amplification%' AND title LIKE '%cascade%'",
    "F18: cytokine storm": "title LIKE '%cytokine storm%'",
    "F19: receptor clustering": "title LIKE '%receptor clustering%' OR title LIKE '%receptor%cluster%'",
    "F19: vulnerability chaining": "title LIKE '%vulnerability chain%' OR (title LIKE '%vulnerabilit%' AND title LIKE '%combin%')",

    # TROUS STRUCTURELS — Les ponts qui n'existent pas (ou presque)
    "HOLE: epidemic+software": "title LIKE '%epidemic%' AND (title LIKE '%software%' OR title LIKE '%code%')",
    "HOLE: DebtRank+software": "title LIKE '%DebtRank%' AND title LIKE '%software%'",
    "HOLE: percolation+software": "title LIKE '%percolation%' AND title LIKE '%software%'",
    "HOLE: Ising+software": "title LIKE '%Ising%' AND title LIKE '%software%'",
    "HOLE: metapopulation+software": "title LIKE '%metapopulation%' AND title LIKE '%software%'",
    "HOLE: bandit+security": "title LIKE '%bandit%' AND title LIKE '%security%'",
    "HOLE: ultrasensitivity+software": "title LIKE '%ultrasensitiv%' AND title LIKE '%software%'",
    "HOLE: cascade+vulnerability": "title LIKE '%cascade%' AND title LIKE '%vulnerability%'",
    "HOLE: contagion+software": "(title LIKE '%contagion%' OR title LIKE '%epidemic%') AND title LIKE '%vulnerability%'",
    "HOLE: heat kernel+security": "title LIKE '%heat kernel%' AND title LIKE '%security%'",
    "HOLE: game theory+vulnerability": "title LIKE '%game theor%' AND title LIKE '%vulnerability%'",
    "HOLE: influence+patch": "title LIKE '%influence maxim%' AND (title LIKE '%patch%' OR title LIKE '%immuniz%')",
}

results = {}
if has_title:
    print(f"\n[3/4] Recherche titres dans {len(TITLE_QUERIES)} requêtes...")
    for label, where in TITLE_QUERIES.items():
        try:
            cur.execute(f"SELECT COUNT(*) as cnt FROM papers WHERE {where}")
            cnt = cur.fetchone()['cnt']
            results[label] = {"count": cnt}
            marker = ""
            if label.startswith("HOLE:") and cnt == 0:
                marker = " ← JACKPOT (trou structurel confirmé)"
            elif label.startswith("HOLE:") and cnt < 5:
                marker = f" ← QUASI-JACKPOT ({cnt} papiers seulement)"
            elif label.startswith("HOLE:") and cnt > 20:
                marker = f" ← PONT EXISTANT (pas un vrai trou)"
            print(f"  {label:50s} → {cnt:>5} papers{marker}")

            # Si peu de résultats, afficher les titres
            if 0 < cnt <= 10:
                cur.execute(f"SELECT paper_id, title, year FROM papers WHERE {where} ORDER BY year DESC LIMIT 5")
                for row in cur.fetchall():
                    results[label].setdefault("papers", []).append({
                        "id": row['paper_id'], "title": row['title'], "year": row['year']
                    })
                    print(f"    → [{row['year']}] {row['paper_id']}: {row['title'][:80]}")
        except Exception as e:
            print(f"  {label:50s} → ERREUR: {e}")
            results[label] = {"error": str(e)}
else:
    print("\n  ⚠ Pas de colonne 'title' — recherche par concepts uniquement")

# ── STEP 3: Vérifier les co-occurrences entre axes (trous structurels) ──
print(f"\n[4/4] Vérification co-occurrences inter-axes...")

# Prendre les top concepts par axe
axe_top_concepts = {}
for axe, matches in concept_matches.items():
    # Top 3 concepts par works_count
    top = sorted(matches, key=lambda x: -x["works_count"])[:3]
    axe_top_concepts[axe] = [(m["idx"], m["name"]) for m in top]

# Vérifier co-occurrences entre AXE1-7 et SEC
cooc_results = {}
for src_axe in ["AXE1", "AXE2", "AXE3", "AXE4", "AXE5", "AXE6", "AXE7"]:
    if src_axe not in axe_top_concepts or "SEC" not in axe_top_concepts:
        continue
    for src_idx, src_name in axe_top_concepts[src_axe]:
        for sec_idx, sec_name in axe_top_concepts["SEC"]:
            try:
                # Chercher dans cooc_global
                cur.execute("""
                    SELECT weight FROM cooc_global
                    WHERE (concept_a = ? AND concept_b = ?)
                       OR (concept_a = ? AND concept_b = ?)
                """, (src_idx, sec_idx, sec_idx, src_idx))
                row = cur.fetchone()
                w = row['weight'] if row else 0
                key = f"{src_axe}:{src_name} × SEC:{sec_name}"
                cooc_results[key] = w
                if w == 0:
                    print(f"  {key:70s} → cooc=0 ← TROU CONFIRMÉ")
                elif w < 10:
                    print(f"  {key:70s} → cooc={w} ← QUASI-TROU")
                else:
                    print(f"  {key:70s} → cooc={w}")
            except Exception as e:
                print(f"  ERREUR {src_axe}×SEC: {e}")

conn.close()

# ── SAVE ──
output = {
    "meta": {
        "type": "carmack_security_scan",
        "formulas": 19,
        "axes": 7,
        "db": DB,
    },
    "concept_matches_by_axe": {
        axe: len(matches) for axe, matches in concept_matches.items()
    },
    "concept_top_by_axe": {
        axe: [{"idx": m["idx"], "name": m["name"], "works_count": m["works_count"]}
              for m in sorted(matches, key=lambda x: -x["works_count"])[:5]]
        for axe, matches in concept_matches.items()
    },
    "title_search_results": results,
    "cooc_structural_holes": cooc_results,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n✓ Résultats sauvés → {OUT}")
print(f"  {len(results)} requêtes titre")
print(f"  {len(cooc_results)} paires co-occurrence")

# Résumé des jackpots
holes = [k for k, v in results.items() if k.startswith("HOLE:") and isinstance(v, dict) and v.get("count", 999) == 0]
quasi = [k for k, v in results.items() if k.startswith("HOLE:") and isinstance(v, dict) and 0 < v.get("count", 999) < 5]
existing = [k for k, v in results.items() if k.startswith("HOLE:") and isinstance(v, dict) and v.get("count", 999) >= 20]

print(f"\n{'='*70}")
print(f"RÉSUMÉ TROUS STRUCTURELS")
print(f"{'='*70}")
print(f"  JACKPOTS (0 papiers):        {len(holes)}")
for h in holes:
    print(f"    ✓ {h}")
print(f"  QUASI-JACKPOTS (<5 papiers): {len(quasi)}")
for q in quasi:
    print(f"    ~ {q}: {results[q]['count']} papiers")
print(f"  PONTS EXISTANTS (≥20):       {len(existing)}")
for e in existing:
    print(f"    ✗ {e}: {results[e]['count']} papiers")
