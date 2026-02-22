#!/usr/bin/env python3
"""
Génère des données mock OpenAlex + lance le pipeline en mode test.
Vérifie que tout fonctionne avant le run réel sur 400GB.
"""

import json
import gzip
import os
import random
import tempfile
import shutil

MOCK_DIR = os.path.join(tempfile.gettempdir(), "mock_openalex")
MOCK_WORKS = os.path.join(MOCK_DIR, "works")

# ─── 1. Générer strates_export_v2.json (mock 50 concepts, 4 strates) ─────

CONCEPTS = [
    # S0 - Fondations
    ("Machine learning", 0), ("Statistics", 0), ("Linear algebra", 0),
    ("Probability", 0), ("Optimization", 0), ("Calculus", 0),
    # S1 - Méthodes
    ("Neural network", 1), ("Deep learning", 1), ("Bayesian inference", 1),
    ("Reinforcement learning", 1), ("Computer vision", 1),
    ("Natural language processing", 1), ("Signal processing", 1),
    # S2 - Goulot
    ("Transfer learning", 2), ("Meta-learning", 2), ("Few-shot learning", 2),
    # S3 - Résonance (cross-domain)
    ("Drug discovery", 3), ("Climate modeling", 3), ("Genomics", 3),
    ("Quantum computing", 3), ("Robotics", 3), ("Materials science", 3),
    ("Neuroscience", 3), ("Economics", 3), ("Ecology", 3),
    # S4+
    ("Protein folding", 4), ("Autonomous vehicles", 4),
    ("Speech recognition", 4), ("Recommender system", 4),
    ("Graph neural network", 4), ("Generative model", 4),
]

# Fake OpenAlex concept IDs
OA_IDS = {name: f"https://openalex.org/C{10000+i}" for i, (name, _) in enumerate(CONCEPTS)}


def generate_mock_strates():
    """Génère strates_export_v2.json format [{from, to, strate}]."""
    entries = []
    for name, strate in CONCEPTS:
        # Créer quelques liens entre concepts adjacents
        entries.append({
            "from": name,
            "to": "",  
            "strate": strate
        })
    return entries


def generate_mock_openalex_map():
    """Génère openalex_map.json {symbol: openalex_id}."""
    return {name: OA_IDS[name] for name, _ in CONCEPTS}


def generate_mock_paper(concept_pool, n_concepts_range=(1, 8)):
    """Génère un paper mock avec des concepts aléatoires."""
    n = random.randint(*n_concepts_range)
    selected = random.sample(concept_pool, min(n, len(concept_pool)))
    
    concepts = []
    for name in selected:
        concepts.append({
            "id": OA_IDS[name],
            "display_name": name,
            "score": round(random.uniform(0.1, 1.0), 3)
        })
    
    return {
        "id": f"https://openalex.org/W{random.randint(1000000, 9999999)}",
        "title": f"Mock paper about {' and '.join(selected[:2])}",
        "publication_year": random.randint(2000, 2024),
        "concepts": concepts,
        "cited_by_count": random.randint(0, 500)
    }


def generate_mock_gz_files(n_files=5, papers_per_file=200):
    """Génère des fichiers .gz mock dans la structure OpenAlex."""
    os.makedirs(MOCK_WORKS, exist_ok=True)
    
    concept_names = [name for name, _ in CONCEPTS]
    
    # Biais: concepts de la même strate apparaissent plus souvent ensemble
    strate_groups = {}
    for name, strate in CONCEPTS:
        strate_groups.setdefault(strate, []).append(name)
    
    files_created = []
    for i in range(n_files):
        filename = f"updated_date=2024-01-{i+1:02d}/part_{i:03d}.gz"
        filepath = os.path.join(MOCK_WORKS, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with gzip.open(filepath, "wt", encoding="utf-8") as f:
            for _ in range(papers_per_file):
                # 70% du temps: concepts du même groupe (réaliste)
                if random.random() < 0.7:
                    strate = random.choice(list(strate_groups.keys()))
                    pool = strate_groups[strate]
                    # Ajouter quelques concepts d'autres strates
                    pool = pool + random.sample(concept_names, min(3, len(concept_names)))
                else:
                    pool = concept_names
                
                paper = generate_mock_paper(pool)
                f.write(json.dumps(paper) + "\n")
                
                # Ajouter quelques lignes vides et malformées (robustesse)
                if random.random() < 0.02:
                    f.write("\n")
                if random.random() < 0.01:
                    f.write("{malformed json\n")
        
        files_created.append(filepath)
    
    return files_created


def main():
    print("🧪 GÉNÉRATION DONNÉES MOCK")
    print("=" * 50)
    
    # Créer répertoire data/
    os.makedirs("data", exist_ok=True)
    
    # 1. Strates
    strates = generate_mock_strates()
    with open("data/strates_export_v2.json", "w", encoding="utf-8") as f:
        json.dump(strates, f, indent=2)
    print(f"✅ strates_export_v2.json: {len(strates)} entrées")
    
    # 2. OpenAlex map
    oa_map = generate_mock_openalex_map()
    with open("data/openalex_map.json", "w", encoding="utf-8") as f:
        json.dump(oa_map, f, indent=2)
    print(f"✅ openalex_map.json: {len(oa_map)} mappings")
    
    # 3. Fichiers .gz mock
    files = generate_mock_gz_files(n_files=5, papers_per_file=500)
    print(f"✅ {len(files)} fichiers .gz mock ({500*5:,} papers)")
    print(f"   Répertoire: {MOCK_WORKS}")
    
    # 4. Afficher structure
    print(f"\n📁 Structure mock:")
    for f in files:
        size = os.path.getsize(f)
        print(f"   {os.path.relpath(f, MOCK_DIR)}: {size/1024:.1f} KB")
    
    print(f"\n🎯 Pour tester le pipeline:")
    print(f"   python engine/build_cooccurrence.py --test 5")
    print(f"\n   (Modifier WORKS_DIR dans le script vers: {MOCK_WORKS})")
    
    return MOCK_WORKS


if __name__ == "__main__":
    main()
