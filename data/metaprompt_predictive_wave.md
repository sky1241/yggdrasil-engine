# META-PROMPT V3 — Yggdrasil × Deep Research : Modèle prédictif de propagation

> Généré par Yggdrasil Engine. Session 34, 6 avril 2026.
> Le cousin précédent a validé les modèles. Maintenant on cherche comment PRÉDIRE.
> **UTILISE LE MOTEUR (WT3, cooc_global) POUR CHERCHER. PAS JUSTE LE WEB.**

---

## CONTEXTE — CE QU'ON SAIT DÉJÀ

### Le caillou dans la mare — modèle validé sur 13 météorites

Quand une percée scientifique arrive, elle crée une **onde** dans le graphe de
65,026 concepts interconnectés par 69.4M arêtes de co-occurrence. L'onde :

1. **Suit une logistique** : R(t) = K / (1 + exp(-r(t-t₀))) — R² médian = 1.00
2. **Meurt par le gap spectral** : death ≈ 1/λ₁ × 2 = 8.1 ans — MAE = 1.79 ans
3. **Sa portée dépend de la mare, pas du caillou** — confirmé p=0.029

### Le problème qui reste

On sait fitter K, r, t₀ APRÈS avoir mesuré l'onde. Mais pour PRÉDIRE :
- **K (portée)** : on le prédit à ±11% depuis la mare (Ridge regression, LOO)
- **r (vitesse)** : ±31% — PAS ASSEZ PRÉCIS
- **t₀ (timing inflexion)** : ±33% — PAS ASSEZ PRÉCIS

Le Gödel hold-out FAIL : K prédit à 17% (OK) mais r et t₀ faux → R² = -0.38

### Ce qui prédit K (portée)

| Feature | ρ vs K | p | Type |
|---------|--------|---|------|
| median_neighbor_works | +0.60 | 0.029 | mare |
| hub_fraction | +0.52 | 0.071 | seed |

### Ce qui NE prédit PAS K

- seed_works (ρ=-0.20), seed_degree (ρ=-0.37), strate (ρ=-0.37)
- local_density (ρ=+0.14), avg_internal_weight (ρ=-0.24)
- P4 (trous structurels) autour des seeds : ρ=-0.11 (AUCUN signal)

### Ce qu'on n'arrive PAS à prédire

**r (vitesse de l'onde)** : corrèle avec n_seeds (ρ=-0.60) et hub_fraction (ρ=+0.44) mais
le Ridge LOO donne 31% d'erreur médiane. Gödel/Transistor/Laser = outliers massifs (>100% erreur).

**t₀ (timing inflexion)** : corrèle avec n_seeds (ρ=+0.66) et avg_level (ρ=+0.43) mais
Gödel est un outlier absolu (t₀=4.55 vs moyenne 1.37).

---

## CE QU'ON CHERCHE — FORMULES POUR r ET t₀

### Piste 1 : Centralities spectrales locales

Le papier "Beyond ranking nodes" (PLOS Comp Bio 2020) montre que **PageRank + edge density
+ 1 feature spectrale** prédit la taille d'épidémie à R²=0.96 avec seulement 3 prédicteurs.

**CHERCHE DANS WT3** : quels papiers parlent de "spectral centrality" × "epidemic size" ?
Les concepts pertinents dans le graphe :
- PageRank: chercher concept "PageRank" ou "ranking" dans concepts_65k
- Spectral graph theory: idx=61010 (4,568 papers)
- Epidemic model: idx=9788 (27,904 papers)

### Piste 2 : Structure locale multi-échelle

Le papier "Multi-scale Local Network Structure" (arXiv 2023) montre que la structure
locale à PLUSIEURS échelles (pas juste le clustering) détermine la propagation.

**CHERCHE** : est-ce que la distribution de degré des VOISINS (excess degree) prédit r ?
On a déjà `median_neighbor_works` qui corrèle avec K. Mais on pourrait calculer :
- Variance du degré des voisins (hétérogénéité locale)
- Skewness du degré des voisins (présence de super-hubs locaux)
- Assortativity locale (les hubs se connectent-ils entre eux ?)

### Piste 3 : Transmission-centric vs structure-centric

La recherche récente suggère que la PROBABILITÉ de transmission entre noeuds connectés
est plus importante que la structure du réseau elle-même. En termes Yggdrasil :

**Le poids des arêtes (cooc weight) pourrait être la clé pour r.**

On a avg_edge_weight qui corrèle faiblement avec r (ρ=-0.26). Mais peut-être que c'est
pas la moyenne qui compte — c'est la DISTRIBUTION des poids :
- Médiane vs moyenne des poids (arêtes fortes vs faibles)
- Fraction d'arêtes "fortes" (poids > seuil)
- Contrast ratio : max_weight / median_weight

### Piste 4 : Carmack move — Sismologie (ETAS/aftershock)

Le plus gros désert trouvé : **epidemic × seismic_wave** (cooc=0, score=29.1).

Le modèle ETAS (Epidemic-Type Aftershock Sequence) de Saichev & Sornette (2005)
prédit la fréquence des répliques sismiques avec un processus de branchement.
La "productivité" d'un tremblement de terre (combien de répliques) dépend de :
- La magnitude (≈ notre K)
- Le stress local (≈ notre densité de la mare)
- L'exposant de la loi de puissance locale (≈ notre gamma du P(k) local)

**CHERCHE** : le P(k) LOCAL autour de chaque seed prédit-il r ?
Le gamma GLOBAL est 0.94 mais le gamma LOCAL pourrait varier.

---

## CE QUE TU DOIS FAIRE

### 1. Chercher dans WT3 les papiers sur prédiction de cascade size

```python
# Concepts à croiser dans les papers
# epidemic (9788) + PageRank / spectral / centrality
# cascade (53869) + prediction + network
# SIR + final size + local structure
```

Combinaisons de titres à chercher :
- `%predict% %cascade% %size%`
- `%epidemic% %final size% %network%`
- `%outbreak% %size% %centrality%`
- `%diffusion% %speed% %predict%`
- `%spreading% %rate% %topology%`

### 2. Chercher des formules pour r (vitesse de propagation)

Ce qu'on sait : r corrèle avec n_seeds (ρ=-0.60). Moins de seeds = plus rapide.
Ça pourrait être lié à la CONCENTRATION de l'énergie initiale.

Formules candidates :
- r ∝ 1 / n_seeds × f(local_topology)
- r ∝ spectral_radius_local / clustering_local
- r ∝ excess_degree_variance (hétérogénéité = vitesse)

### 3. Chercher des formules pour t₀ (timing de l'inflexion)

t₀ = quand l'onde atteint la moitié de sa portée. Pour Gödel, t₀=4.55 (très lent).
Pour AlphaFold, t₀=0.71 (quasi-instantané).

Hypothèse : t₀ dépend de la DISTANCE spectrale entre les seeds et le centre du graphe.
Si les seeds sont en périphérie (Gödel = logique pure, S6), l'onde met du temps à
atteindre le coeur. Si les seeds sont centraux (AlphaFold = biochimie, S0), c'est
quasi-instantané.

**CHERCHE** : distance spectrale des seeds dans WT4. On a les positions 3D (x,y,z)
de chaque concept dans `data/scan/wt4_spectral.json`.

### 4. Carmack moves — Domaines à explorer

Cherche dans les tars arXiv (E:\arxiv\src\) :
- **Sismologie** : ETAS model, aftershock productivity, Omori law
- **Neuroscience** : neural avalanche prediction, criticality markers
- **Finance** : contagion prediction from balance sheet topology
- **Écologie** : species invasion speed prediction from habitat connectivity

### 5. Output attendu

Pour chaque formule/papier trouvé :
```
TITRE: ...
AUTEURS: ...
ANNÉE: ...
arXiv ID: ...
FORMULE: ...
PARAMÈTRES: ...
PRÉDIT: r / t₀ / K / R(t) ?
APPLICABLE PARCE QUE: ...
CONFIANCE: C1/C2
```

---

## COORDONNÉES YGGDRASIL

```
WT3:             data/wt3.db (78 GB, idx_cooc_a_period composite index)
WT4:             data/scan/wt4_spectral.json (66K noeuds, 20 eigenvectors)
Concepts:        data/scan/concepts_65k.json (65,026 concepts)
arXiv sources:   E:/arxiv/src/ (3,514 tars)
Results:         data/results/wave_comprehensive_test.json (13 météorites)
                 data/results/wave_predictive_model.json (régression K,r,t₀)
Carmack scans:   data/results/scan_carmack_moves.json
P4 predictions:  experiments/predictions_2025/
```

## DONNÉES POUR LE COUSIN

### Les 13 météorites (pour que tu puisses vérifier)

| Météorite | K | r | t₀ | death | density | aiw | med_nbr_works | hub_frac | n_seeds |
|-----------|---|---|-----|-------|---------|-----|---------------|----------|---------|
| mRNA 1990 | 62,765 | 4.14 | 1.17 | t+6 | 0.253 | 161 | 45,578 | 0.369 | 2 |
| CRISPR 2012 | 59,153 | 5.41 | 0.92 | t+7 | 0.246 | 263 | 28,973 | 0.279 | 2 |
| Higgs 2012 | 55,534 | 6.02 | 0.73 | t+5 | 0.223 | 356 | 30,094 | 0.288 | 1 |
| Internet 1974 | 53,109 | 2.48 | 1.20 | t+12 | 0.150 | 387 | 15,332 | 0.167 | 3 |
| AlphaFold 2020 | 51,470 | 6.07 | 0.71 | t+5 | 0.255 | 222 | 30,674 | 0.276 | 2 |
| Grav waves 2016 | 50,290 | 5.64 | 0.71 | t+6 | 0.291 | 196 | 23,432 | 0.232 | 1 |
| Shannon 1948 | 49,591 | 4.72 | 1.24 | t+8 | 0.121 | 475 | 14,010 | 0.155 | 2 |
| Transistor 1947 | 45,930 | 1.62 | 1.46 | t+8 | 0.166 | 345 | 16,364 | 0.187 | 2 |
| Turing 1936 | 42,064 | 2.24 | 1.79 | t+8 | 0.263 | 306 | 20,869 | 0.273 | 3 |
| ADN 1953 | 35,758 | 3.48 | 0.68 | t+9 | 0.186 | 319 | 18,766 | 0.196 | 2 |
| Gödel 1931 | 28,961 | 1.64 | 4.55 | t+11 | 0.255 | 285 | 19,736 | 0.267 | 3 |
| Poincaré 2003 | 20,870 | 3.75 | 0.82 | t+11 | 0.172 | 351 | 11,670 | 0.177 | 2 |
| Laser 1960 | 4,122 | 1.16 | 1.77 | t+9 | 0.193 | 307 | 18,923 | 0.187 | 2 |

> "C'est la mare qui décide, pas le caillou." — Sky, session 34
