# WINTER TREE v2 — PLAN D'IMPLÉMENTATION
# Pas les maths. Le CODE. Brique par brique.
# Sky × Claude — 15 février 2026

## LA RÉALITÉ

```
Ce qu'on a :  engine.py scan_repo() → import_graph = {fichier: set(imports)}
              C'est un graphe dirigé. C'est le pont.
              NetworkX 3.6.1 installé.

Ce qu'on a pas : tout le reste.

Le fichier à créer : mycelium.py (à côté de engine.py)
Le fichier test :    test_mycelium.py
```

## ARCHITECTURE

```
engine.py (v1, 3401L)          mycelium.py (v2, NOUVEAU)
   │                              │
   │ scan_repo()                  │ analyze_network(G)
   │   → import_graph             │   → dict de métriques
   │                              │
   └──── PONT ────────────────────┘
         repo_to_graph(import_graph) → nx.Graph
```

Un seul nouveau fichier. Un seul pont. engine.py reste intact.

---

## LES 13 BRIQUES — ORDRE EXACT

Chaque brique = 1 fonction + 1 test. On passe à la suivante QUE si la précédente marche.

### BRIQUE 0 — Le pont (sans ça, rien n'existe)

```python
def repo_to_graph(import_graph: dict) -> nx.DiGraph:
    """Convertit le dict scan_repo → graphe NetworkX."""
```

**Test :** graphe jouet à la main, vérifier nodes et edges.
**Taille estimée :** ~15 lignes
**Difficulté :** ★☆☆☆☆

---

### BRIQUE 1 — Alpha (meshedness)

```python
def meshedness(G: nx.Graph) -> float:
    """α = (L - N + 1) / (2N - 5)"""
```

**Test :** 
- Arbre pur (3 nodes, 2 edges) → α = 0.0
- Triangle (3 nodes, 3 edges) → α = 1.0
- Graphe Bebber simulé → α ≈ 0.11

**Taille estimée :** ~5 lignes
**Difficulté :** ★☆☆☆☆
**Source :** Bloc D1

---

### BRIQUE 2 — E_global (efficacité globale)

```python
def global_efficiency(G: nx.Graph) -> float:
    """E = (1/N(N-1)) × Σ 1/d_ij"""
```

**Test :** networkx.global_efficiency() existe → comparer notre résultat.
**Taille estimée :** ~8 lignes (ou 1 ligne si on wrappe nx)
**Difficulté :** ★☆☆☆☆
**Source :** Bloc D4

---

### BRIQUE 3 — E_root (efficacité depuis entry point)

```python
def root_efficiency(G: nx.Graph, root: str) -> float:
    """E_root = (1/(N-1)) × Σ 1/d(root,j)"""
```

**Test :** root = main.py ou index.dart → mesurer propagation
**Taille estimée :** ~10 lignes
**Difficulté :** ★★☆☆☆
**Source :** Bloc D5

---

### BRIQUE 4 — MST et Volume-MST ratio

```python
def volume_mst_ratio(G: nx.Graph) -> float:
    """Overhead = coût_réel / coût_MST"""
```

**Test :** arbre pur → ratio = 1.0 (pas d'overhead)
**Taille estimée :** ~10 lignes
**Difficulté :** ★★☆☆☆
**Source :** Bloc D6

---

### BRIQUE 5 — Betweenness centrality (bottlenecks)

```python
def find_bottlenecks(G: nx.Graph, top_n=5) -> list:
    """Les N nœuds les plus critiques (betweenness)."""
```

**Test :** sur un graphe étoile → le centre a BC max
**Taille estimée :** ~8 lignes (wrapper nx)
**Difficulté :** ★☆☆☆☆
**Source :** Bloc D7 (prep)

---

### BRIQUE 6 — Robustesse (attaque séquentielle)

```python
def robustness_test(G: nx.Graph, attack="betweenness") -> list:
    """Supprime les nœuds un par un, mesure le core restant.
    Retourne [(pct_removed, pct_connected), ...]"""
```

**Test :** arbre → s'effondre vite. Graphe dense → résiste.
**Taille estimée :** ~25 lignes
**Difficulté :** ★★★☆☆ (boucle + recalcul)
**Source :** Bloc D7

---

### BRIQUE 7 — Small-world σ

```python
def small_world_sigma(G: nx.Graph) -> float:
    """σ = (C/C_rand) / (L/L_rand). Small-world si σ > 1."""
```

**Test :** nx.sigma() existe → comparer. Attention : LENT sur gros graphes.
**Taille estimée :** ~5 lignes (wrapper) ou ~20 (custom rapide)
**Difficulté :** ★★☆☆☆
**Source :** Bloc G1

---

### BRIQUE 8 — Small-world ω

```python
def small_world_omega(G: nx.Graph) -> float:
    """ω = L_rand/L - C/C_lattice. -1=lattice, 0=SW, +1=random."""
```

**Taille estimée :** ~5 lignes (wrapper nx.omega())
**Difficulté :** ★★☆☆☆
**Source :** Bloc G2

---

### BRIQUE 9 — Stratégie phalanx/guerrilla

```python
def classify_strategy(metrics: dict) -> str:
    """Basé sur α, E_root, E_global, robustesse → phalanx ou guerrilla."""
```

**Test :** monorepo dense → phalanx. Microservices → guerrilla.
**Taille estimée :** ~20 lignes (seuils à calibrer)
**Difficulté :** ★★★☆☆ (besoin des briques 1-8 d'abord)
**Source :** Bloc G3

---

### BRIQUE 10 — Kirchhoff / flux adaptatif

```python
def adaptive_flow(G: nx.Graph, source: str, sink: str, steps=100) -> nx.Graph:
    """Simule le flux adaptatif de Tero. Retourne G avec poids mis à jour."""
```

**Test :** sur un graphe avec 2 chemins → le plus court se renforce.
**Taille estimée :** ~40 lignes (ODE simple, Euler)
**Difficulté :** ★★★★☆ (premier vrai algo numérique)
**Source :** Bloc E1-E2

---

### BRIQUE 11 — Anastomose (détection de fusions)

```python
def detect_anastomosis(git_log: list) -> dict:
    """Analyse l'historique git pour détecter les événements de fusion.
    tip-tip (PR merge) et tip-hypha (refactoring vers code existant)."""
```

**Test :** repo avec merges → détecte les fusions. Repo linéaire → 0 fusions.
**Taille estimée :** ~50 lignes (parsing git log)
**Difficulté :** ★★★★☆ (interface git + heuristiques)
**Source :** Bloc C1

---

### BRIQUE 12 — Rapport complet

```python
def full_report(repo_path: str) -> dict:
    """Scan → graphe → toutes les métriques → diagnostic."""
```

**Test :** lancer sur le repo tree/ lui-même.
**Taille estimée :** ~30 lignes (orchestre les briques 0-11)
**Difficulté :** ★★☆☆☆ (si les briques marchent)

---

## GRAPHE DE DÉPENDANCES

```
BRIQUE 0 (pont)
  ├── BRIQUE 1 (α)
  ├── BRIQUE 2 (E_global) 
  ├── BRIQUE 3 (E_root)
  ├── BRIQUE 4 (Volume-MST)
  ├── BRIQUE 5 (betweenness)
  │     └── BRIQUE 6 (robustesse)
  ├── BRIQUE 7 (σ)
  ├── BRIQUE 8 (ω)
  └── BRIQUE 10 (Kirchhoff)

BRIQUES 1-8 → BRIQUE 9 (stratégie)
BRIQUE 0 + git → BRIQUE 11 (anastomose)
TOUT → BRIQUE 12 (rapport)
```

Briques 1-5 sont INDÉPENDANTES entre elles → parallélisable.
Briques 7-8 sont INDÉPENDANTES entre elles.
Brique 6 dépend de 5.
Brique 9 dépend de tout le Bloc D.
Briques 10-11 sont les plus dures et peuvent attendre.

---

## SESSION 1 — CE SOIR OU PROCHAIN CRÉNEAU

Objectif réaliste : **Briques 0 à 5**. Ça donne déjà :
- α (le réseau est-il maillé ou arbre pur ?)
- E_global (les modules communiquent bien ?)
- E_root (l'entry point irrigue tout ?)
- Volume-MST (y'a de l'overhead ?)
- Bottlenecks (quels fichiers sont critiques ?)

Avec ça tu peux déjà scanner n'importe quel repo et avoir un DIAGNOSTIC.

```bash
python mycelium.py analyze /path/to/repo
# → α=0.15, E_global=0.42, E_root=0.68, overhead=1.3x
# → Bottlenecks: engine.py (BC=0.45), utils.py (BC=0.22)
# → Stratégie: proto-phalanx (dense mais petit)
```

## SESSION 2

Briques 6-9 : robustesse + small-world + stratégie.

## SESSION 3

Briques 10-12 : flux adaptatif + anastomose + rapport complet.

---

## RÈGLES DE CONSTRUCTION

1. **1 brique = 1 commit.** Pas de commit de 200 lignes.
2. **Chaque brique a son test.** Graphe jouet → résultat attendu → assert.
3. **Si le test passe pas, on avance PAS.**
4. **On teste sur tree/ à chaque étape.** Le système sur le système.
5. **Les formules sont dans FORMULAS.md. Le code est dans mycelium.py.** Jamais mélanger.
