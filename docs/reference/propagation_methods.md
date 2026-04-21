# Propagation Parameter Prediction — 4 Nouvelles Méthodes

> Session 38, 21 avril 2026 — Sky × Claude (Opus 4.6)
> Recherche motivée par le blocage V3: on sait simuler l'onde, mais pas prédire K (portée) et r (vitesse).

---

## Contexte

**Le problème**: 36 météorites mesurées par BFS sur WT3 (cooc per-period).
On connaît K (portée = nombre de concepts touchés) et r (vitesse logistique).
Toutes les tentatives de prédiction depuis les features locales ont échoué en test temporel:
- Session 37: K error 54%, r error 41%, R(t) R²=-0.53 (FAIL)
- Features testées: mare (degree, weight, species), scientométrie (fitness, D-index), mycélium (Lehmann curseurs), topologie WT4

**L'insight Markov/Nekrasov**: la littérature sur la propagation en réseaux offre 4 méthodes
qui capturent des aspects de la topologie que nos features manuelles ne captent pas.

---

## Méthode 1: Collective Influence (CI) — Makse et al.

### Référence
- Morone & Makse (2015). "Influence maximization in complex networks through optimal percolation." *Nature* 524, 65-68.
- Teng, Pei & Makse (2017). "Efficient collective influence maximization in cascading processes with first-order transitions." *Sci. Rep.* 7, 45240.

### Formule
```
CI_L(i) = (k_i - 1) × Σ_{j ∈ ∂Ball(i,L)} (k_j - 1)
```
Où:
- k_i = degré du noeud i
- ∂Ball(i,L) = frontière de la boule de rayon L autour de i (noeuds à distance exactement L)
- L = rayon (typiquement 2 ou 3)

Pour L=0: CI_0(i) = k_i (juste le degré)
Pour L=1: CI_1(i) = (k_i - 1) × Σ_{j∈neighbors(i)} (k_j - 1)

### Intuition
La puissance de propagation d'un noeud ne dépend pas de son degré seul, mais du nombre de
**chemins sous-critiques** qui partent de lui. Un noeud dans le core avec des voisins
bien connectés propage plus qu'un hub en périphérie.

### Application Yggdrasil
Calculer CI_L pour chaque seed de chaque météorite. Corréler avec K et r.
Hypothèse: CI capture le "potentiel de cascade" que degree seul ne voit pas.

### Complexité: O(N × L) par noeud, total O(N² × L) sur le graphe complet.
Sur les seeds seulement: O(n_seeds × |Ball(seed, L)|) — rapide.

---

## Méthode 2: Percolation Threshold — Radicchi (2015)

### Référence
- Radicchi (2015). "Predicting percolation thresholds in networks." *Phys. Rev. E* 91, 010801(R). DOI: 10.1103/PhysRevE.91.010801

### Trois estimateurs

**A. Moments de la distribution de degré:**
```
p̃_c = ⟨k⟩ / (⟨k²⟩ - ⟨k⟩)
```

**B. Inverse de la plus grande valeur propre de la matrice d'adjacence:**
```
p̄_c = 1 / λ_max(A)
```

**C. Inverse de la plus grande valeur propre de la matrice non-backtracking M:**
```
p̂_c = 1 / λ_max(M)

M = [A, -I; D-I, 0]  (matrice 2|E|×2|E|)
```
Où D = matrice diagonale des degrés.

### Intuition
Le seuil de percolation = la fraction minimale de liens qu'il faut pour qu'une composante géante existe.
Plus le seuil est bas → plus le réseau est "facile à traverser" → K devrait être grand.

### Application Yggdrasil
Calculer les 3 estimateurs sur le **sous-graphe local** (1-hop ou 2-hop) de chaque seed.
Corréler p_c local avec K. Hypothèse: une mare avec un seuil de percolation bas = facile à traverser = grand K.

### Limitation connue
"In more than 40% of cases, the non-backtracking eigenvalue is less predictive than the naive
degree-based estimator." (Radicchi 2015). Notre graphe est dense (⟨k⟩=2136), ce qui est favorable.

---

## Méthode 3: K-shell Decomposition

### Références
- Kitsak et al. (2010). "Identification of influential spreaders in complex networks." *Nature Physics* 6, 888-893.
- Bae & Kim (2014). "Identifying and ranking influential spreaders in complex networks by neighborhood coreness." *Physica A* 395, 549-559.
- Liu et al. (2015). "Improving the accuracy of the k-shell method by removing redundant links." *Sci. Rep.* 5, 13172.

### Algorithme
```
Répéter:
  1. Trouver tous les noeuds de degré ≤ k
  2. Retirer ces noeuds et leurs arêtes
  3. Recalculer les degrés
  4. k-shell de ces noeuds = k
  5. Incrémenter k, répéter sur le graphe résiduel
```

Le k-shell index (coreness) d'un noeud = le plus grand k tel que le noeud appartient au k-core.

### Intuition
Les superspreaders sont dans le **core** du réseau, pas en périphérie.
Un noeud avec un k-shell élevé est profondément enchâssé dans la structure dense.
Degree élevé ≠ k-shell élevé (un hub en périphérie a bas k-shell).

### Application Yggdrasil
Calculer le k-shell index de chaque seed sur cooc_global.
Corréler avec K et r. Hypothèse: seeds dans le core (haut k-shell) → grand K.

### Limitation connue
"Core-like groups" = clusters denses mais locaux qui ont un k-shell élevé
sans être de vrais superspreaders. Solution: filtrer les liens redondants (Liu 2015).

---

## Méthode 4: Monte Carlo Random Walk — Features de cascade

### Références
- Kempe, Kleinberg & Tardos (2003). "Maximizing the spread of influence through a social network." *KDD* 137-146.
- Tao Wu et al. (2015). "Full-scale Cascade Dynamics Prediction with a Local-First Approach." arXiv:1512.08455.
- Leskovec et al. (2007). "The dynamics of viral marketing." *ACM TOIT* 7(1), 5.

### Méthode
Au lieu de chercher des features analytiques, simuler directement la propagation:
```
Pour chaque seed s:
  Lancer N random walks (N=1000)
  Chaque walker:
    - Part de s
    - À chaque pas: saute vers un voisin avec probabilité ∝ poids de l'arête
    - S'arrête après T pas (T=8, la durée de vie observée)
  Mesurer:
    - reach = nombre de noeuds uniques visités (proxy de K)
    - speed = noeuds uniques visités aux premiers pas (proxy de r)
    - diversity = nombre d'espèces touchées
    - bottleneck = fraction de walkers qui restent dans la même communauté
```

### Intuition
Le random walk "ressent" la topologie sans la réduire à une seule feature.
Il capture les bottlenecks, les hubs, les ponts, les cul-de-sacs — tout en même temps.

### Application Yggdrasil
Lancer N=1000 walks depuis chaque seed sur cooc_global.
Extraire reach, speed, diversity, bottleneck.
Corréler avec K et r.

### Avantage vs features analytiques
Les features analytiques (degré, k-shell, CI) réduisent la topologie à un nombre.
Le random walk laisse la topologie "parler" via la distribution des destinations.
C'est ce que fait PageRank, et ça a plutôt bien marché pour Google.

---

## Plan de test

Pour chaque méthode, on calcule la/les features sur les 36 météorites, puis:
1. Corrélation Spearman avec K et r
2. Test temporel honnête: train pre-1960 → predict post-1973
3. Comparer avec les meilleures features actuelles (mare: 19.2% K, mycelium: 9.1% r)

**Ordre de test**: CI → Percolation → K-shell → Monte Carlo (du plus rapide au plus lent)

**Critère de succès**: une feature qui corrèle avec K à |ρ| > 0.5 ET tient en test temporel.
