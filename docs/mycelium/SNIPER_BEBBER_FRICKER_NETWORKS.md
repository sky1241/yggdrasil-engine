# SNIPER: Bebber 2007 + Fricker 2017 — Network Metrics for Winter Tree v2

**Status:** ✅ Recherche web complète
**Source:** PMC full-text (Bebber), PubMed/ResearchGate/ASM abstracts + citing papers (Fricker)
**Date:** 2026-02-15

---

## PAPER 5: Bebber et al. 2007 — "Biological solutions to transport network design"
**Proc. R. Soc. B, 274(1623), 2307-2315**
**Auteurs:** Bebber, Hynes, Darrah, Boddy, Fricker (Oxford/Cardiff)
**Organisme:** Phanerochaete velutina sur sol compressé

### CONTRIBUTION CLÉ
Premier papier à quantifier explicitement la structure réseau des mycelia fongiques et à démontrer qu'ils résolvent simultanément efficacité de transport ET robustesse aux dommages, avec un coût de construction décroissant.

### SETUP EXPÉRIMENTAL
- Blocs de hêtre (2×2×1 cm) inoculés P. velutina sur sol woodland compressé (plateaux 24×24 cm)
- 3 réplicats avec ressource additionnelle (bait) à 8cm, 3 contrôles
- Photos à 9, 18, 25, 31, 39 jours
- Extraction réseau: jonctions → nœuds, cords → liens (MatLab custom)
- Diamètre des cords estimé par intensité d'image (calibré par microscopie, r²=0.77)
- Réseaux pondérés planaires: ~700 nœuds, ~900 liens à maturité

### MÉTRIQUES RÉSEAU EXTRAITES

#### 1. Meshedness (coefficient alpha) α
```
α = (L - N + 1) / (2N - 5)
```
Où L = nombre de liens, N = nombre de nœuds.
- α = 0 → arbre pur (pas de boucles)
- α = 1 → réseau planaire maximal
- **Résultats:** α augmente de ~0 (initial, arbre) à 0.11±0.04 (contrôle) et 0.20±0.05 (avec bait)
- α_intérieur > α_extérieur (0.08 vs 0.05 pour baited) → plus de boucles dans le core consolidé
- **Signification:** Le réseau passe d'arbre exploratoire à réseau faiblement maillé par fusion + renforcement sélectif

#### 2. Coût matériel C et densité de coût
```
C = Σ(l × a)  [mm³]
```
Où l = longueur du lien, a = aire de section transversale du cord
- **Résultat clé:** La densité de coût (C/A, avec A = aire du convex hull) DIMINUE avec le temps
- Le réseau grandit spatialement mais le matériel total augmente beaucoup plus lentement
- → Recyclage actif du matériel redondant pendant la consolidation

#### 3. Résistance fonctionnelle
```
r_link = l × a⁻¹  [mm⁻¹]
```
(longueur / section transversale — modèle de cylindre rempli d'hyphes parallèles)
- Plus court chemin calculé par algorithme de Johnson
- **Résultat:** Résistance augmente non-linéairement avec la distance au centre
- Mais DIMINUE au fil du temps pour les mêmes distances → renforcement progressif
- La ressource additionnelle (bait) obtient une résistance INFÉRIEURE aux autres nœuds à même distance euclidienne → renforcement ciblé

#### 4. Efficacité de transport — Comparaison avec réseaux modèles

Trois réseaux de référence (mêmes nœuds):
- **MST (Minimum Spanning Tree):** coût minimal, très vulnérable, pas de boucles
- **DT (Delaunay Triangulation):** bien connecté, robuste, CHER
- **Réseau fongique réel:** intermédiaire

**Deux modes d'efficacité:**
```
E_global = (1/N(N-1)) × Σᵢ≠ⱼ (1/d_ij)     [efficacité multi-directionnelle]
E_root  = (1/(N-1)) × Σⱼ (1/d_root,j)       [efficacité uni-directionnelle depuis l'inoculum]
```

**Résultats (Euclidiens, non-pondérés):**
- E_global: DT > Fongique > MST (fongique intermédiaire)
- E_root: DT ≈ Fongique >> MST (fongique aussi bon que DT !)

**Résultats (Fonctionnels, pondérés par section):**
- E_global_fonctionnel: MST > Fongique (MST gagne car pas de matériel "gaspillé" en boucles)
- **E_root_fonctionnel: FONGIQUE > tous les autres** ← LE résultat clé

→ Le réseau fongique pondéré bat même le MST pour le transport depuis la source, grâce au renforcement différentiel des cords principaux.

#### 5. Robustesse aux dommages (attaque par coupure de liens)
- Suppression progressive de liens par ordre décroissant de centralité (betweenness)
- Mesure: fraction du "core" connecté restant
- **Euclidien:** DT > Fongique > MST (fongique intermédiaire)
- **Fonctionnel (pondéré):** Après ~30% de liens coupés, le réseau fongique pondéré maintient un core connecté PLUS GRAND que tous les autres modèles
- → Les gros cords survivent aux attaques et maintiennent la connectivité

### INSIGHT FONDAMENTAL BEBBER 2007
> Le réseau fongique résout le **trilemme coût-efficacité-robustesse** par renforcement sélectif et recyclage. Il n'optimise pas un seul critère mais trouve un compromis Pareto-optimal entre les trois.

---

## PAPER 6: Fricker et al. 2017 — "The Mycelium as a Network"
**Microbiol. Spectrum 5(3): FUNK-0033-2017**
**Auteurs:** Fricker, Heaton, Jones, Boddy (Oxford/Imperial/Cardiff)
**Type:** Review/synthèse de 33 pages, chapitre dans "The Fungal Kingdom"

### CONTRIBUTION CLÉ
Synthèse définitive reliant structure réseau → flux de ressources → adaptation écologique à travers les échelles. Formalise les métriques réseau, le modèle ADD (Advection-Diffusion-Delivery), et la taxonomie de réseaux.

### CONCEPTS MAJEURS EXTRAITS

#### 1. Flux induit par la croissance (Growth-Induced Mass Flow)
- La croissance apicale crée un flux de masse vers les pointes
- Vélocités mesurées: 20-100 mm/h dans P. velutina, jusqu'à 148 cm/h dans S. lacrymans
- Le flux volumétrique scale avec le nombre de pointes en aval (downstream tips)
- Noyaux transportés jusqu'à 4 mm/h par mass flow

#### 2. Modèle ADD (Advection-Diffusion-Delivery)
- Advection: transport par flux de masse
- Diffusion: mouvement stochastique des solutés
- Delivery: livraison/absorption aux nœuds
- Corrélation modèle-expérience: Pearson r = 0.56 pour prédire la distribution de radiotraceur dans un réseau complexe
- Input: croissance mesurée au niveau des cords individuels → prédiction de flux réseau

#### 3. Stratégies de fourragement: Phalanx vs Guerrilla

| Caractéristique | Phalanx | Guerrilla |
|----------------|---------|-----------|
| Branchement | Fréquent, angles larges | Rare |
| Vitesse | Lente | Rapide |
| Front | Large, synchrone | Étroit, indépendant |
| Portée | Court-range | Long-range |
| Densité | Dense | Éparse |
| Exemple | Phallus impudicus | Armillaria spp. |
| Réseau | Haute connectivité, robuste, cher | Basse connectivité, efficient, fragile |

**Pour Winter Tree:** Phalanx = monorepo dense, bien testé, lent à évoluer. Guerrilla = micro-services épars, rapides à déployer, fragiles.

#### 4. Dimension fractale comme métrique écologique
- DBM (fractal dimension of mass): mesure remplissage de l'espace par la biomasse
- DBS (fractal dimension of surface): mesure complexité du front
- Varie entre espèces ET avec les conditions (taille inoculum, nutriments sol, compétition)
- Diminue avec la compétition et le grazing

#### 5. Taxonomie de réseaux (Mesoscale Analysis)
- 270 réseaux fongiques analysés par structure communautaire
- Méthode: optimisation de modularité avec "path score" (PS) comme poids
- Dendrogramme produit à partir de la structure mésoscopique
- **Résultat:** Les espèces se groupent par stratégie de fourragement, pas par taxonomie
- Facteurs discriminants: niveau de ressources, substrat (agar/sable/sol), compétition, grazing

#### 6. Suite complète de métriques réseau (formalisée dans Aguilar-Trigueros 2022)

Les 15 traits réseau définis:

**Morphologiques (5):**
1. Longueur hyphale
2. Largeur des pointes
3. Largeur des hyphes principaux
4. Angle de branchement
5. Densité de longueur mycélienne

**Réseau (10):**
6. **Meshedness α** — connectivité topologique (cycles / max possible)
7. **Root-efficiency (Reff)** — transport unidirectionnel inoculum → tout nœud
8. **Root-tip efficiency (R-Teff)** — transport unidirectionnel inoculum → pointes seulement
9. **Global efficiency (Geff)** — transport multi-directionnel entre n'importe quels 2 points
10. **Volume-MST** — coût de construction relatif vs MST (minimum possible)
11-15. **5 traits de robustesse** — nombre de liens à supprimer pour réduire à 50% la connectivité au root, sous différents types d'attaque (aléatoire, par betweenness, par poids, etc.)

**Résultat clé de l'analyse Pareto:**
> La variation principale entre espèces se fait le long d'un gradient de CONNECTIVITÉ. Haute connectivité = haute robustesse + haute efficacité globale + coût élevé (phalanx). Basse connectivité = haute efficacité root + faible robustesse + faible coût (guerrilla).

#### 7. Robustesse in silico
- P. velutina (réseau plus dense) se décompose plus LENTEMENT sous attaque aléatoire
- P. impudicus (réseau plus dense encore) encore plus robuste
- Les espèces montrent des profils de robustesse différents selon le type d'attaque

#### 8. Recyclage et mémoire écologique
- Les mycelia recyclent activement les régions non-productives
- "Ecological memory": le réseau se reconfigure quand de nouvelles ressources apparaissent
- Migration complète possible si la nouvelle ressource est assez grande
- Décision de migration influencée par taille du bait, distance, et état de l'inoculum original

---

## MAPPING WINTER TREE v2

### Métriques réseau → Métriques de santé repo

| Métrique fongique | Formule | Winter Tree v2 |
|-------------------|---------|----------------|
| **Meshedness α** | (L-N+1)/(2N-5) | Degré d'interconnexion entre modules. α≈0 = code spaghetti linéaire. α élevé = modules bien cross-linkés |
| **Root-efficiency** | Σ 1/d(root,j) normalisé | Facilité de propager un changement depuis le point d'entrée (main, index) vers tout le code |
| **Root-tip efficiency** | Σ 1/d(root,tips) | Efficacité de propagation vers les points actifs de développement (branches, PRs) |
| **Global efficiency** | Σ 1/d(i,j) ∀i,j | Facilité de communication entre n'importe quels 2 modules |
| **Volume-MST** | Cost_réel / Cost_MST | Overhead architectural — combien de "liens" redondants vs le minimum |
| **Robustesse** | Liens à couper pour 50% déconnexion | Combien de fichiers/modules peut-on supprimer avant que le système ne casse |
| **Coût densité** | Σ(l×a) / Area | Quantité de code par unité de fonctionnalité couverte |

### Stratégies de fourragement → Stratégies de développement

| Fongique | Winter Tree v2 |
|----------|----------------|
| Phalanx (dense, lent, robuste) | Monorepo mature: tests extensifs, CI/CD complet, refactoring continu, lent à évoluer |
| Guerrilla (éparse, rapide, fragile) | Micro-services/multi-repo: déploiement rapide, peu de tests, fragile, exploration rapide |
| Transition phalanx→guerrilla | Repo mûr qui splitté en micro-services pour explorer de nouveaux domaines |
| Renforcement sélectif | Modules critiques reçoivent plus de tests, docs, reviews (épaisseur de cord) |
| Recyclage | Suppression de code mort, deprecation de features, archivage de branches mortes |

### Résistance fonctionnelle → Résistance au changement
```
r_module = complexity × coupling⁻¹
```
- Module long et mal connecté = haute résistance (changement difficile à propager)
- Module court et bien connecté = basse résistance (changement se propage facilement)
- Le réseau optimise en renforçant les "cords" critiques (modules centraux bien testés)

### Trilemme Pareto → Architecture Decision Records
Tout repo fait un compromis entre:
1. **Coût** (quantité de code/infra) — minimiser
2. **Efficacité** (vitesse de propagation des changements) — maximiser  
3. **Robustesse** (tolérance aux pannes/suppressions) — maximiser

Le point optimal dépend de la stratégie (phalanx vs guerrilla) qui elle-même dépend de l'environnement (ressources disponibles, compétition, prédation/bugs).

---

## DONNÉES QUANTITATIVES CLÉS (pour implémentation)

### Table 1: Caractéristiques réseau P. velutina (Bebber 2007)

| Jour | Nœuds (C) | Liens (C) | Coût mm³ (C) | Densité coût (C) |
|------|-----------|-----------|-------------|-----------------|
| 18 | 515±70 | 644±127 | 234±6 | 1.0±0.1 |
| 25 | 738±87 | 946±159 | 294±10 | 0.8±0.0 |
| 31 | 805±131 | 1040±218 | 287±23 | 0.6±0.0 |
| 39 | 697±145 | 883±234 | 292±31 | 0.6±0.1 |

**Observation:** Le nombre de nœuds DIMINUE entre j31 et j39 → pruning actif !

### Algorithmes à implémenter pour Winter Tree v2

1. **Johnson's shortest path** — pour calculer toutes les résistances fonctionnelles
2. **Alpha coefficient** — meshedness du graphe de dépendances
3. **MST (Minimum Spanning Tree)** — baseline de coût minimal
4. **DT (Delaunay Triangulation)** — upper bound de connectivité max
5. **Betweenness centrality** — identifier les liens critiques (cords principaux)
6. **Attaque séquentielle** — robustesse par suppression de liens (par betweenness décroissant)
7. **Efficacité Latora-Marchiori** — E_global et E_root normalisés

---

## SYNTHÈSE AVEC LES AUTRES PAPERS

| Paper | Échelle | Contribution | Status |
|-------|---------|-------------|--------|
| Meškauskas 2004a,b | Agent (pointe hyphale) | Règles de croissance, tropismes, champs | ✅ |
| Boswell 2003 (via Davidson) | PDE continu | 5 variables: n,a,s_i,s_e,ρ | ✅ |
| Davidson 2007 | Multi-échelle | Hiérarchie micro/meso/macro | ✅ |
| Adamatzky 2018 | Automate CA | Géométrie → computation | ✅ |
| Roberts 2022 | Expérimental | Reservoir computing, Turing-complet | ✅ |
| **Bebber 2007** | **Réseau** | **Métriques transport + robustesse** | **✅** |
| **Fricker 2017** | **Synthèse** | **Taxonomie réseau, stratégies, ADD** | **✅** |

### Architecture Winter Tree v2 complète:

```
v1: ARBRE (visualisation, croissance)
    └── Meškauskas: règles agent, tropismes, différenciation

v2: MYCELIUM (réseau souterrain, interconnexion)
    ├── Boswell PDEs: dynamique continue (5 variables)
    ├── Adamatzky CA: computation sur graphe irrégulier
    ├── Roberts: preuve que la topologie = ordinateur
    ├── Bebber: métriques réseau (α, Eglobal, Eroot, robustesse)
    └── Fricker: stratégies (phalanx/guerrilla), taxonomie, ADD model

v3: FORÊT (multi-repos, écosystème)
    └── Interactions inter-repos, wood-wide web
```

---

## BONUS: Paper récent découvert pendant la recherche

### Aguilar-Trigueros et al. 2022 — "Network traits predict ecological strategies in fungi"
**ISME Communications**
- Pipeline automatisée: images de mycelia → graphes pondérés → 15 traits réseau
- Analyse de Pareto sur 4 propriétés: connectivité, coût, efficacité, robustesse
- Confirme le gradient phalanx-guerrilla comme AXE PRINCIPAL de variation
- Taxonomie de 270 réseaux par structure mésoscopique
- **Directement implémentable dans Winter Tree v2**

### Oyarte Galvez et al. 2025 — "A travelling-wave strategy for plant-fungal trade"  
**Nature (Feb 2025)**
- Robot custom d'imagerie: >500,000 nœuds fongiques simultanés
- ~100,000 trajectoires de flux cytoplasmique mesurées
- Les champignons mycorhiziens construisent des réseaux comme des **ondes voyageuses auto-régulatrices**
- La densité du mycélium est auto-régulée par la fusion
- Vitesse de flux corrèle avec betweenness centrality du lien
- **Insight pour Winter Tree:** L'activité d'un module devrait corréler avec sa centralité dans le graphe de dépendances

---

## READING LIST: STATUS FINAL

| # | Paper | Status | Verdict |
|---|-------|--------|---------|
| 1 | Meškauskas 2004a (Fruit bodies) | ✅ PDF analysé | 🟢 Clé |
| 2 | Meškauskas 2004b (Colonial growth) | ✅ PDF analysé | 🟡 Complément |
| 3 | Davidson 2007 | ✅ PDF analysé | 🟡 Validation |
| 4 | Adamatzky 2018 | ✅ PDF analysé | 🟢 Clé |
| 5 | Roberts 2022 | ✅ PDF analysé | 🟡 Complément |
| 6 | **Bebber 2007** | ✅ Web sniper | 🟢 **Clé** |
| 7 | **Fricker 2017** | ✅ Web sniper | 🟢 **Clé** |

**READING LIST COMPLÈTE. Toutes les 7 sources analysées.**
