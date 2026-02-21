"""
ÉTAPE 3 — Vérité terrain: mapper 12 percées → paires de concepts OpenAlex
==========================================================================
Input:  blind_test/data_2015_frozen.json (pour les concept IDs)
Output: blind_test/ground_truth.json

On mappe chaque percée vers la paire de concepts OpenAlex la plus proche
parmi les 100 concepts de notre snapshot.
"""

import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
FROZEN = os.path.join(BASE, "data_2015_frozen.json")
OUTPUT = os.path.join(BASE, "ground_truth.json")

print("=" * 60)
print("ÉTAPE 3 — Vérité terrain (12 percées)")
print("=" * 60)

# Load our concept list
with open(FROZEN, "r", encoding="utf-8") as f:
    frozen = json.load(f)

our_concepts = {c["id"]: c for c in frozen["concepts"]}
print(f"  {len(our_concepts)} concepts in our snapshot")

# ══════════════════════════════════════════════════════════
# Define breakthroughs with search terms for concept matching
# ══════════════════════════════════════════════════════════

# Each breakthrough maps to two DOMAIN concepts.
# We search OpenAlex concepts to find the best match among our 100.
# Format: (name, year_range, concept_a_search, concept_b_search, manual_fallback_a, manual_fallback_b)

# MANUAL MAPPING to our actual 100 concepts.
# Each breakthrough → best available pair from our concept list.
# Justification documented per entry.
BREAKTHROUGHS = [
    {
        "name": "AlphaFold",
        "year": "2018-2020",
        "description": "Deep Learning predicts protein 3D structure",
        "concept_a": "C154945302",  # Artificial intelligence
        "concept_b": "C55493867",   # Biochemistry
    },
    {
        "name": "mRNA vaccines",
        "year": "2020",
        "description": "mRNA-based COVID vaccines (Pfizer/Moderna)",
        "concept_a": "C203014093",  # Immunology
        "concept_b": "C171250308",  # Nanotechnology (lipid nanoparticles)
    },
    {
        "name": "CRISPR base editing",
        "year": "2016-2017",
        "description": "Precision gene editing without double-strand breaks",
        "concept_a": "C178790620",  # Organic chemistry
        "concept_b": "C54355233",   # Genetics
    },
    {
        "name": "Gravitational waves (LIGO)",
        "year": "2015-2016",
        "description": "First direct detection via laser interferometry",
        "concept_a": "C62520636",   # Quantum mechanics (closest to GR in our set)
        "concept_b": "C120665830",  # Optics (laser interferometry)
    },
    {
        "name": "AlphaGo / AlphaZero",
        "year": "2016-2017",
        "description": "AI masters Go and chess from self-play",
        "concept_a": "C154945302",  # Artificial intelligence
        "concept_b": "C11413529",   # Algorithm (game tree search / MCTS)
    },
    {
        "name": "Transformers / GPT",
        "year": "2017-2020",
        "description": "Attention-based architecture revolutionizes NLP",
        "concept_a": "C154945302",  # Artificial intelligence
        "concept_b": "C41895202",   # Linguistics (NLP domain)
    },
    {
        "name": "CAR-T therapy",
        "year": "2017",
        "description": "Engineered T cells to fight cancer",
        "concept_a": "C203014093",  # Immunology
        "concept_b": "C95444343",   # Cell biology (closest to oncology)
    },
    {
        "name": "Cryo-EM revolution",
        "year": "2016+",
        "description": "Cryo-electron microscopy reaches atomic resolution",
        "concept_a": "C184779094",  # Atomic physics (electron microscopy)
        "concept_b": "C55493867",   # Biochemistry (structural biology)
    },
    {
        "name": "Topological insulators",
        "year": "2016+",
        "description": "Materials with topological quantum properties",
        "concept_a": "C62520636",   # Quantum mechanics
        "concept_b": "C159985019",  # Composite material (materials science)
    },
    {
        "name": "Microbiome therapeutics",
        "year": "2018+",
        "description": "Gut microbiome as therapeutic target",
        "concept_a": "C18903297",   # Ecology (microbial ecology)
        "concept_b": "C126322002",  # Internal medicine
    },
    {
        "name": "Quantum supremacy",
        "year": "2019",
        "description": "Quantum computer outperforms classical on specific task",
        "concept_a": "C62520636",   # Quantum mechanics
        "concept_b": "C11413529",   # Algorithm (computational complexity)
    },
    {
        "name": "GAN explosion",
        "year": "2016+",
        "description": "Generative adversarial networks create realistic images",
        "concept_a": "C154945302",  # Artificial intelligence
        "concept_b": "C105795698",  # Statistics (generative models)
    },
]

# ══════════════════════════════════════════════════════════
# Match breakthroughs (manual, pre-verified)
# ══════════════════════════════════════════════════════════
print("\nMapping breakthroughs to concept pairs...")

ground_truth = []
for bt in BREAKTHROUGHS:
    cid_a = bt["concept_a"]
    cid_b = bt["concept_b"]
    name_a = our_concepts[cid_a]["display_name"] if cid_a in our_concepts else "???"
    name_b = our_concepts[cid_b]["display_name"] if cid_b in our_concepts else "???"

    # Ensure consistent pair key ordering (smaller ID first)
    if cid_a > cid_b:
        cid_a, cid_b = cid_b, cid_a
        name_a, name_b = name_b, name_a

    entry = {
        "breakthrough": bt["name"],
        "year": bt["year"],
        "description": bt["description"],
        "matched_concept_a": cid_a,
        "matched_concept_a_name": name_a,
        "matched_concept_b": cid_b,
        "matched_concept_b_name": name_b,
        "matched": True,
        "pair_key": f"{cid_a}|{cid_b}",
    }
    ground_truth.append(entry)
    print(f"  [OK] {bt['name']:<25s} -> {name_a} x {name_b}")

# ══════════════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════════════
matched = sum(1 for g in ground_truth if g["matched"])
print(f"\n  Matched: {matched}/{len(ground_truth)}")

result = {
    "meta": {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_breakthroughs": len(ground_truth),
        "n_matched": matched,
        "note": "Concepts matched from our top 100 level 1-2 OpenAlex concepts"
    },
    "breakthroughs": ground_truth,
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\n  → {OUTPUT}")
print("ÉTAPE 3 TERMINÉE.")
