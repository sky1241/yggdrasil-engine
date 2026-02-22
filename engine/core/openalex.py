"""
YGGDRASIL ENGINE — OpenAlex API Module
Interface avec OpenAlex (250M+ papers académiques).

https://docs.openalex.org/
"""
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional

BASE_URL = "https://api.openalex.org"
CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"


def _get(endpoint: str, params: dict = None, email: str = None) -> dict:
    """GET request vers OpenAlex API."""
    url = f"{BASE_URL}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    headers = {"User-Agent": "YggdrasilEngine/1.0"}
    if email:
        headers["mailto"] = email
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def search_concept(name: str) -> Optional[dict]:
    """
    Recherche un concept OpenAlex par nom.
    
    Retourne: {id, display_name, works_count, cited_by_count, level}
    """
    data = _get("concepts", {"filter": f"display_name.search:{name}", "per_page": 5})
    results = data.get("results", [])
    return results[0] if results else None


def get_concept(concept_id: str) -> dict:
    """Récupère les détails d'un concept."""
    return _get(f"concepts/{concept_id}")


def get_co_occurrence(concept_a_id: str, concept_b_id: str) -> int:
    """
    Compte les papers qui contiennent les deux concepts.
    
    = La PLUIE dans Yggdrasil — les données brutes de co-occurrence.
    """
    data = _get("works", {
        "filter": f"concepts.id:{concept_a_id},concepts.id:{concept_b_id}",
        "per_page": 1,
    })
    return data.get("meta", {}).get("count", 0)


def get_concept_works_by_year(concept_id: str) -> dict[int, int]:
    """
    Nombre de papers par année pour un concept.
    
    Utile pour calculer l'activité et la fitness temporelle.
    """
    data = _get(f"concepts/{concept_id}")
    counts = data.get("counts_by_year", [])
    return {item["year"]: item["works_count"] for item in counts}


def get_domain_pair_timeline(concept_a_id: str, concept_b_id: str,
                              start_year: int = 2000) -> dict[int, int]:
    """
    Timeline de co-occurrence entre deux concepts par année.
    
    Utile pour détecter les trous qui se REMPLISSENT.
    """
    results = {}
    for year in range(start_year, 2025):
        data = _get("works", {
            "filter": f"concepts.id:{concept_a_id},concepts.id:{concept_b_id},publication_year:{year}",
            "per_page": 1,
        })
        count = data.get("meta", {}).get("count", 0)
        results[year] = count
        time.sleep(0.1)  # Rate limiting
    
    return results


def batch_co_occurrences(concept_ids: list[str], 
                          cache_file: Optional[str] = None) -> dict:
    """
    Calcule la matrice de co-occurrence entre tous les concepts.
    
    C'est LA PLUIE qui tombe sur Yggdrasil.
    Chaque goutte = un paper qui connecte deux concepts.
    
    Args:
        concept_ids: liste d'IDs OpenAlex
        cache_file: fichier de cache pour éviter de re-fetcher
    
    Returns:
        {(id_a, id_b): count, ...}
    """
    # Check cache
    if cache_file:
        cache_path = CACHE_DIR / cache_file
        if cache_path.exists():
            with open(cache_path) as f:
                return json.load(f)
    
    results = {}
    total = len(concept_ids) * (len(concept_ids) - 1) // 2
    done = 0
    
    for i, a in enumerate(concept_ids):
        for b in concept_ids[i+1:]:
            key = f"{a}|{b}"
            count = get_co_occurrence(a, b)
            results[key] = count
            done += 1
            if done % 10 == 0:
                print(f"  [{done}/{total}] co-occurrences...")
            time.sleep(0.1)
    
    # Save cache
    if cache_file:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_DIR / cache_file, 'w') as f:
            json.dump(results, f)
    
    return results


def search_structural_hole(domain_a: str, domain_b: str) -> dict:
    """
    Recherche rapide d'un trou structurel entre deux domaines.
    
    1. Trouve les concepts OpenAlex
    2. Mesure la co-occurrence
    3. Compare avec l'activité individuelle
    
    Retourne un diagnostic préliminaire.
    """
    concept_a = search_concept(domain_a)
    concept_b = search_concept(domain_b)
    
    if not concept_a or not concept_b:
        return {"error": f"Concept not found: {domain_a if not concept_a else domain_b}"}
    
    co_occ = get_co_occurrence(concept_a["id"], concept_b["id"])
    
    works_a = concept_a.get("works_count", 0)
    works_b = concept_b.get("works_count", 0)
    
    # Expected co-occurrence (if independent)
    # P(A∩B) = P(A) × P(B) approximation
    total_works = 250_000_000  # OpenAlex total
    expected = (works_a / total_works) * (works_b / total_works) * total_works
    
    ratio = co_occ / expected if expected > 0 else 0
    
    return {
        "domain_a": {"name": concept_a["display_name"], "works": works_a},
        "domain_b": {"name": concept_b["display_name"], "works": works_b},
        "co_occurrence": co_occ,
        "expected": round(expected),
        "ratio": round(ratio, 3),
        "diagnosis": (
            "🔥 PONT DENSE" if ratio > 2 else
            "🌡️ Connexion normale" if ratio > 0.5 else
            "❄️ TROU FROID" if ratio > 0.1 else
            "🕳️ TROU NOIR — potentiel conceptuel"
        )
    }
