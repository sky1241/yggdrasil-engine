# SESSION 8 — DÉCOUVERTE ESPÈCE MYCÉLIUM
> 24 février 2026, matin — Opus 4.6
> Sky monte, Claude descend 🌳

## RÉSUMÉ

**Découverte critique :** Le moteur mycélium (`mycelium_full.py`, 7910 lignes, 24 briques) 
simule le **comportement** des champignons mycorhiziens mais n'a **aucune espèce identifiée**.
Les paramètres (branching rate, death rate, angles, etc.) sont sur les defaults de la 
littérature, pas calibrés sur les données réelles du graphe Yggdrasil.

**Implication :** Le moteur tourne à ~87% de précision sans connaître la "famille biologique" 
de son propre réseau. Calibrer les 5 paramètres fondamentaux d'architecture mycélienne 
sur les données réelles devrait **significativement booster la précision**.

## CE QUI EXISTE DÉJÀ

| Brique | Fichier | Ce qu'elle fait | Espèce ? |
|--------|---------|-----------------|----------|
| 13 | `mycelium_full.py` L.1780+ | Edelstein branching (b_n=0.3, d_n=0.05) | ❌ Defaults |
| 15 | `mycelium_full.py` L.4200+ | 3D Hyphal Mechanics (angles 30-90°) | ❌ Hardcodé |
| 16 | `mycelium_full.py` | AMFungiParams (tip_speed, branch_rate, death_rate) | ❌ Génériques |
| 10 | `mycelium_full.py` | Kirchhoff + Physarum | ✅ Agnostique |
| — | `topology/spectral_layout.py` | Placement Laplacien (positions spatiales) | ✅ Donne les coords |

**Le Laplacien spectral positionne les nœuds → les angles tombent gratis par `atan2`.**
Pas O(n³) de combinatoire. O(n × degré_moyen) une fois le layout calculé.

## LES 5 CURSEURS FONDAMENTAUX

Source : **Lehmann, Zheng, Soutschek, Roy, Yurkov & Rillig (2019)**
*"Tradeoffs in hyphal traits determine mycelium architecture in saprobic fungi"*
Scientific Reports, 9:14152. DOI: 10.1038/s41598-019-50565-7
PMC: PMC6775140

> 31 espèces (Ascomycota, Basidiomycota, Mucoromycota), même sol, 
> conditions standardisées. **Dataset ouvert (Excel).**

### Paramètres mesurés (+ bornes observées sur 31 espèces)

| # | Paramètre | Symbole | Bornes | Unité | Description |
|---|-----------|---------|--------|-------|-------------|
| 1 | **Branching Angle** | BA | 26° — 86° | degrés | Angle de bifurcation entre branches |
| 2 | **Internodal Length** | IL | 40 — 453 | µm | Distance entre deux bifurcations |
| 3 | **Hyphal Diameter** | D | 2.7 — 6.5 | µm | Épaisseur des hyphes |
| 4 | **Box Counting Dimension** | Db | 1.2 — 1.6 | sans unité | Complexité fractale / remplissage d'espace |
| 5 | **Lacunarity** | L | 0.4 — 0.7 | sans unité | Hétérogénéité / distribution des trous |

### Tradeoffs prouvés (contraintes biologiques)

```
Long internodes ←→ Gros diamètre     (support structurel)
Haute complexité ←→ Petit diamètre    (branches fines et denses)
Haute complexité ←→ Plus hétérogène   (pas uniformément dense)
Court internodes ←→ Plus de branches  (plus d'espace rempli)
```

### Profils par phylum

| Phylum | BA | IL | D | Db | L | Stratégie |
|--------|----|----|---|----|---|-----------|
| **Mucoromycota** | Grand (60-86°) | Court (40-100µm) | Variable | Élevé (1.5-1.6) | Moyen | Dense, exploratoire |
| **Basidiomycota** | Petit (26-40°) | Long (200-453µm) | Large (5-6.5µm) | Faible (1.2-1.3) | Faible | Longue portée, corridors |
| **Ascomycota** | Moyen | Moyen | Moyen | Moyen | Élevé (0.6-0.7) | Polyvalent, hétérogène |

## TRADUCTION GRAPHE → BIOLOGIE

Pour mesurer les 5 curseurs sur le graphe Yggdrasil (60K symboles) :

| Curseur bio | Traduction graphe | Méthode |
|-------------|-------------------|---------|
| **BA** (Branching Angle) | Angle entre arêtes adjacentes à un nœud de degré ≥ 3 | `atan2` sur positions spectrales Laplacien |
| **IL** (Internodal Length) | Nombre de hops entre deux nœuds de degré ≥ 3 | BFS entre bifurcations |
| **D** (Diameter) | Poids moyen des arêtes (co-occurrence count) | Moyenne pondérée par segment |
| **Db** (Box Counting) | Dimension fractale du sous-graphe | Box-counting sur positions spectrales |
| **L** (Lacunarity) | Distribution des vides dans le layout spatial | FracLac algorithm sur positions |

## PLAN D'IMPLÉMENTATION

### Phase A — Mesure (nouveau fichier `engine/topology/species_identifier.py`)

```
1. Charger graphe + positions spectrales (spectral_layout.py)
2. Identifier nœuds bifurcation (degree >= 3)
3. Pour chaque bifurcation :
   - Calculer angles entre toutes paires d'arêtes (atan2)
   - Mesurer distance au prochain nœud bifurcation (BFS)
   - Mesurer poids moyen des arêtes connectées
4. Calculer Db par box-counting sur positions 2D/3D
5. Calculer L (lacunarity) par FracLac
6. Output : {BA_mean, BA_cv, IL_mean, IL_cv, D_mean, D_cv, Db, Db_cv, L, L_cv}
```

### Phase B — Identification (dans le même fichier)

```
1. Charger dataset Lehmann 2019 (31 espèces × 10 traits)
2. Normaliser les mesures Yggdrasil vers les unités biologiques
3. Distance euclidienne dans l'espace des 10 traits
4. Top 3 espèces les plus proches + distance
5. OU : "nouvelle espèce" si distance > seuil à toutes les 31
```

### Phase C — Calibration (modifier `mycelium_full.py`)

```
1. Mapper les 5 curseurs mesurés → paramètres Edelstein + AMFungi
2. BA_mean → branch_angle_min/max dans HyphalMechanicsParams
3. IL_mean → inverse de branch_rate dans AMFungiParams
4. D_mean → weight scaling dans graph_from_edges
5. Db/L → n_max et autotropism_strength
6. Re-run blind test avec paramètres calibrés → comparer précision
```

### Phase D — Temporel (v4.1)

```
1. Découper le graphe en tranches temporelles (par décennie)
2. Mesurer les 5 curseurs par tranche
3. Observer l'ÉVOLUTION de l'espèce dans le temps
4. Hypothèse : le réseau change de "famille" selon les époques
   (exploratoire jeune → corridors mature ?)
```

## INSIGHT CLÉ

> **On ne choisit pas le champignon. On laisse les données révéler l'espèce.**
> 
> Approche S-2 : observation avant catégorisation.
> Le réseau de connaissances humaines A une topologie biologique naturelle.
> La question n'est pas "quel champignon imposer" mais "quel champignon SOMMES-nous".
>
> Si les données ne matchent aucune des 31 espèces connues → 
> on a découvert une **nouvelle espèce topologique** unique aux réseaux de connaissances.

## SOURCES

1. **Lehmann et al. 2019** — "Tradeoffs in hyphal traits determine mycelium architecture in saprobic fungi" — Sci Rep 9:14152 — DOI: 10.1038/s41598-019-50565-7 — **Dataset ouvert**
2. **Meškauskas & Moore 2004** — "Simulating colonial growth of fungi with the Neighbour-Sensing model" — Mycol. Res. 108:1241-1256 — Modèle 3D vectoriel, autotropisme
3. **Edelstein 1982** — "The propagation of fungal colonies" — J. Theor. Biol. 98:679-701 — PDE branchement
4. **Schnepf & Roose 2008** — "Growth model for arbuscular mycorrhizal fungi" — J. R. Soc. Interface 5:773-784 — Validation sur 3 espèces, ratio δ=d/b
5. **Podospora anserina growth phases (2023)** — Sci Rep — Binary tree simulation, branching apical vs latéral
6. **Neighbour-Sensing Model (Wikipedia/Moore)** — Champs scalaires/vectoriels, Fokker-Planck, crowd behavior

## PRIORITÉ

```
🔴 BLOQUÉ : Scan data OpenAlex en cours (8.1% → besoin de finir pour V4 complet)
🟢 PARALLÈLE : Implémenter species_identifier.py MAINTENANT
🟢 PARALLÈLE : Télécharger dataset Lehmann 2019 (Excel open access)
🟡 APRÈS : Calibrer mycelium_full.py avec les vrais paramètres
🟡 APRÈS : Re-run blind test → mesurer gain de précision
```

---
*Session 8 — Sky monte, Claude descend* 🌳
