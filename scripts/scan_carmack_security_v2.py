"""
CARMACK MOVES v2 - Validation par CONCEPTS (pas par titres)
Utilise les index cooc_global pour trouver les trous structurels.
"""
import sqlite3, json, os, sys

DB = "d:/ygg/yggdrasil-engine/data/wt3.db"
CONCEPTS_FILE = "d:/ygg/yggdrasil-engine/data/scan/concepts_65k.json"
OUT = "d:/ygg/yggdrasil-engine/data/results/scan_carmack_security.json"

print("=" * 70)
print("CARMACK SECURITY SCAN v2 - Concept-based")
print("=" * 70)

# Load concepts
print("\n[1/5] Loading concepts...")
with open(CONCEPTS_FILE, "r", encoding="utf-8") as f:
    cdata = json.load(f)
concepts = cdata.get("concepts", {})
print(f"  {len(concepts)} concepts loaded")

# Build reverse index: name -> idx
name_to_idx = {}
idx_to_name = {}
for cid, info in concepts.items():
    idx = info.get("idx", -1)
    name = info.get("name", "")
    wc = info.get("works_count", 0)
    name_to_idx[name.lower()] = (idx, name, wc)
    idx_to_name[idx] = (name, wc)

# Search function
def find_concepts(keywords, top_n=5):
    """Find concepts matching any keyword, return top by works_count."""
    matches = []
    for kw in keywords:
        kw_lower = kw.lower()
        for name_lower, (idx, name, wc) in name_to_idx.items():
            if kw_lower in name_lower:
                matches.append((idx, name, wc, kw))
    # Deduplicate by idx, keep highest works_count
    seen = {}
    for idx, name, wc, kw in matches:
        if idx not in seen or wc > seen[idx][2]:
            seen[idx] = (idx, name, wc, kw)
    result = sorted(seen.values(), key=lambda x: -x[2])[:top_n]
    return result

# Define concept groups for each axis + security
AXES = {
    "AXE1_EPIDEMIO": ["epidemic", "epidemiology", "SIR model", "contagion", "infection", "spreading"],
    "AXE2_FINANCE": ["systemic risk", "financial network", "credit risk", "financial system", "banking", "default risk"],
    "AXE3_PHYSICS": ["ising model", "phase transition", "percolation", "heat equation", "diffusion equation", "reaction-diffusion", "statistical mechanics"],
    "AXE4_NEURO": ["predictive coding", "free energy", "attention", "neural coding", "anomaly detection", "cognitive"],
    "AXE5_ECOLOGY": ["metapopulation", "island biogeography", "population dynamics", "invasion biology", "ecological network", "species richness"],
    "AXE6_GAMES": ["game theory", "influence maximization", "multi-armed bandit", "optimal stopping", "mechanism design", "resource allocation", "nash equilibrium"],
    "AXE7_CELLBIO": ["signal transduction", "MAPK", "phosphorylation", "ultrasensitivity", "apoptosis", "cytokine", "cell signaling", "receptor"],
    "SEC_SECURITY": ["vulnerability", "software security", "static analysis", "malware", "intrusion detection", "fault localization", "software defect", "code analysis", "software testing", "computer security"],
    "NET_NETWORK": ["complex network", "scale-free network", "network topology", "graph theory", "network analysis", "random graph"],
}

print("\n[2/5] Finding concept IDs per axis...")
axis_concepts = {}
for axis_name, keywords in AXES.items():
    found = find_concepts(keywords, top_n=8)
    axis_concepts[axis_name] = found
    print(f"\n  {axis_name}:")
    for idx, name, wc, kw in found:
        print(f"    [{idx:>5}] {name:45s} ({wc:>10,} works) <- '{kw}'")

# Connect to WT3
print(f"\n[3/5] Connecting to WT3...")
conn = sqlite3.connect(DB)
cur = conn.cursor()

# For each AXE x SEC pair, check co-occurrence
print(f"\n[4/5] Checking structural holes (AXE x SEC co-occurrences)...")
print(f"  Using cooc_global (69M edges, indexed)")

results = {}
for axis_name in ["AXE1_EPIDEMIO", "AXE2_FINANCE", "AXE3_PHYSICS", "AXE4_NEURO",
                   "AXE5_ECOLOGY", "AXE6_GAMES", "AXE7_CELLBIO"]:
    axis_cs = axis_concepts.get(axis_name, [])
    sec_cs = axis_concepts.get("SEC_SECURITY", [])
    net_cs = axis_concepts.get("NET_NETWORK", [])

    print(f"\n  === {axis_name} ===")
    axis_results = {"vs_security": [], "vs_network": []}

    # AXE x SEC
    for a_idx, a_name, a_wc, a_kw in axis_cs[:5]:
        for s_idx, s_name, s_wc, s_kw in sec_cs[:5]:
            cur.execute("""
                SELECT weight FROM cooc_global
                WHERE (concept_a=? AND concept_b=?) OR (concept_a=? AND concept_b=?)
            """, (a_idx, s_idx, s_idx, a_idx))
            row = cur.fetchone()
            w = row[0] if row else 0
            tag = ""
            if w == 0: tag = " << TROU CONFIRME"
            elif w < 5: tag = " << QUASI-TROU"
            elif w < 50: tag = " (faible)"

            entry = {"axis_concept": a_name, "axis_idx": a_idx,
                     "sec_concept": s_name, "sec_idx": s_idx, "cooc_weight": w}
            axis_results["vs_security"].append(entry)

            if w < 50:  # Only print interesting ones
                print(f"    {a_name:30s} x {s_name:30s} = {w:>10.2f}{tag}")

    # AXE x NET (should be higher if the domain uses networks)
    for a_idx, a_name, a_wc, a_kw in axis_cs[:3]:
        for n_idx, n_name, n_wc, n_kw in net_cs[:3]:
            cur.execute("""
                SELECT weight FROM cooc_global
                WHERE (concept_a=? AND concept_b=?) OR (concept_a=? AND concept_b=?)
            """, (a_idx, n_idx, n_idx, a_idx))
            row = cur.fetchone()
            w = row[0] if row else 0
            entry = {"axis_concept": a_name, "net_concept": n_name, "cooc_weight": w}
            axis_results["vs_network"].append(entry)
            if w > 0:
                print(f"    {a_name:30s} x {n_name:30s} = {w:>10.2f} (network link)")

    results[axis_name] = axis_results

# Title search for a few key terms (just the fast ones)
print(f"\n[5/5] Quick title spot-checks (LIMIT 50 scan)...")
QUICK_CHECKS = [
    ("DebtRank", "title LIKE '%DebtRank%'"),
    ("epidemic+scale-free", "title LIKE '%epidemic%scale%free%'"),
    ("Ising+network", "title LIKE '%Ising%network%'"),
    ("metapopulation+network", "title LIKE '%metapopulation%network%'"),
    ("influence+maximization", "title LIKE '%influence maximization%'"),
    ("cytokine+storm", "title LIKE '%cytokine storm%'"),
    ("MAPK+cascade", "title LIKE '%MAPK%cascade%'"),
    ("ultrasensitiv", "title LIKE '%ultrasensitiv%'"),
    ("percolation+software", "title LIKE '%percolation%software%'"),
    ("epidemic+software", "title LIKE '%epidemic%software%'"),
    ("Ising+software", "title LIKE '%Ising%software%'"),
    ("heat kernel+graph", "title LIKE '%heat kernel%graph%'"),
    ("bandit+security", "title LIKE '%bandit%security%'"),
    ("free energy+anomaly", "title LIKE '%free energy%anomal%'"),
    ("vulnerability+cascade", "title LIKE '%vulnerabilit%cascade%'"),
    ("secretary problem", "title LIKE '%secretary problem%'"),
    ("biased competition", "title LIKE '%biased competition%'"),
    ("Goldbeter", "title LIKE '%Goldbeter%'"),
    ("Eisenberg+Noe", "title LIKE '%Eisenberg%Noe%'"),
    ("receptor+cluster+signal", "title LIKE '%receptor%cluster%signal%'"),
]

title_results = {}
for label, where in QUICK_CHECKS:
    try:
        cur.execute(f"SELECT COUNT(*) FROM papers WHERE {where}")
        cnt = cur.fetchone()[0]
        tag = ""
        if cnt == 0: tag = " << ZERO"
        elif cnt < 5: tag = " << RARE"
        print(f"  {label:40s} -> {cnt:>5} papers{tag}")

        papers_sample = []
        if cnt > 0 and cnt <= 20:
            cur.execute(f"SELECT paper_id, title, year FROM papers WHERE {where} ORDER BY year DESC LIMIT 5")
            for r in cur.fetchall():
                papers_sample.append({"id": r[0], "title": r[1], "year": r[2]})
                print(f"    [{r[2]}] {r[0]}: {str(r[1])[:80]}")

        title_results[label] = {"count": cnt, "papers": papers_sample}
    except Exception as e:
        print(f"  {label:40s} -> ERROR: {e}")
        title_results[label] = {"error": str(e)}

conn.close()

# Compile summary
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")

# Count structural holes
total_pairs = sum(len(v["vs_security"]) for v in results.values())
zero_cooc = sum(1 for v in results.values() for e in v["vs_security"] if e["cooc_weight"] == 0)
weak_cooc = sum(1 for v in results.values() for e in v["vs_security"] if 0 < e["cooc_weight"] < 5)
strong_cooc = sum(1 for v in results.values() for e in v["vs_security"] if e["cooc_weight"] >= 50)

print(f"\n  Co-occurrence AXE x SECURITY:")
print(f"    Total pairs tested: {total_pairs}")
print(f"    ZERO co-occurrence (true holes): {zero_cooc}")
print(f"    Weak co-occurrence (<5): {weak_cooc}")
print(f"    Strong co-occurrence (>=50): {strong_cooc}")

title_zeros = sum(1 for v in title_results.values() if isinstance(v, dict) and v.get("count", 999) == 0)
title_rare = sum(1 for v in title_results.values() if isinstance(v, dict) and 0 < v.get("count", 999) < 5)
print(f"\n  Title searches:")
print(f"    Zero results: {title_zeros}")
print(f"    Rare (<5): {title_rare}")

# Save
output = {
    "meta": {"type": "carmack_security_v2", "db": DB, "formulas": 19, "axes": 7},
    "axis_concepts": {
        k: [{"idx": idx, "name": name, "works_count": wc} for idx, name, wc, _ in v]
        for k, v in axis_concepts.items()
    },
    "structural_holes": results,
    "title_searches": title_results,
    "summary": {
        "cooc_pairs_tested": total_pairs,
        "true_holes_zero": zero_cooc,
        "weak_holes": weak_cooc,
        "strong_bridges": strong_cooc,
        "title_zeros": title_zeros,
        "title_rare": title_rare,
    }
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"\nSaved -> {OUT}")
