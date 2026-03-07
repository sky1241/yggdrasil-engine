# WINTER TREE v2 — RÉFÉRENTIEL COMPLET DES FORMULES
# Organisé par blocs fonctionnels, sourcé, mappé
# Sky × Claude — 15 février 2026

---

## ARCHITECTURE GÉNÉRALE

```
BLOC A ─ AGENT (micro)        ← Comment 1 tip grandit
BLOC B ─ COLONIE (méso)       ← Comment la colonie évolue (PDEs)
BLOC C ─ ANASTOMOSE (fusion)  ← Comment l'arbre devient réseau
BLOC D ─ MÉTRIQUES RÉSEAU     ← Comment mesurer le réseau
BLOC E ─ TRANSPORT (flux)     ← Comment les ressources circulent
BLOC F ─ COMPUTATION          ← Comment le réseau calcule
BLOC G ─ TOPOLOGIE            ← Comment classifier le réseau
BLOC H ─ ALGORITHMES BIO      ← Inspirations complémentaires
```

Flux de construction :
```
A (tips) → B (colonie) → C (fusion) → D (mesure) → E (flux) → F (calcul)
                                                         ↑
                                                    G (topologie)
                                                    H (algo bio)
```

---
---

## BLOC A — AGENT / MICRO : Règles de croissance d'un tip

**Sources :** Meškauskas & Moore 2004a (Mycol. Res. 108:1241-1256), Meškauskas et al. 2004b (Mycol. Res. 108:1257-1274)

Ce bloc décrit le comportement d'UN SEUL tip hyphal. Pas de vision globale.
L'intelligence émerge de la somme des comportements individuels.

### A1 — Champ de densité local (auto-inhibition)

```
N_{S,p} = (l_c / |S_A|) × Σ(j=1→|S_A|) 1/|S_Aj - p|²
```

| Symbole | Signification |
|---------|--------------|
| S_A | Points échantillonnant la géométrie de la section hyphale S |
| p | Position du tip qui "sent" |
| l_c | Longueur de corrélation (facteur d'échelle) |
| 1/d² | Décroissance courte portée |

**Rôle :** Chaque segment hyphal génère un champ répulsif local.
Les tips évitent les zones déjà occupées → exploration efficace.

### A2 — Champ de substrat (attraction/répulsion)

```
O_{T,p} = T_impact × Y(|p - T_center| - T_R) × 1/|T_center - p|²
```

| Symbole | Signification |
|---------|--------------|
| T_impact | Force du substrat (1000× plus fort qu'un segment hyphal) |
| T_center | Position du centre du substrat |
| T_R | Rayon du substrat |
| Y() | Fonction de Heaviside (actif seulement au-delà du rayon) |

**Rôle :** Substrat positif = attracteur. Négatif = inhibiteur/barrière.
Un substrat est 1000× plus fort qu'un segment → tropisme dominant.

### A3 — Vecteur de croissance résultant

```
v_new = norm(S_growth + g(S, β))
```

| Symbole | Signification |
|---------|--------------|
| S_growth | Vecteur antérograde (direction actuelle du tip) |
| g(S, β) | Combinaison pondérée des tropismes |
| β | Poids de chaque tropisme (densité, gravité, substrat) |
| norm() | Normalisation → direction seule, vitesse constante |

### A4 — Règle de branchement

```
SI densité_locale(R) > seuil ALORS
    SI random(0,100) < p_branch ALORS
        créer nouvelle branche à angle θ
```

| Symbole | Signification |
|---------|--------------|
| R | Rayon de détection local |
| p_branch | Probabilité de branchement (%) |
| θ | Angle de branchement (espèce-dépendant) |

### A5 — Galvanotropisme (formation de cords)

Chaque segment génère un champ vectoriel parallèle à son axe, décroissant en 1/d.
La somme vectorielle crée un champ d'orientation partagé.

**Résultat :** Les hyphes s'alignent spontanément → formation de cords (auto-accélérant).

### A6 — Trois types d'hyphes (différenciation)

| Type | Rôle | Sensibilité |
|------|------|------------|
| Standard | Croissance normale depuis le départ | Tous tropismes |
| Leading | Émergent en périphérie, organisent les cords | Insensible au galvanotropisme |
| Secondary | Remplissent les zones matures | Branchement tardif |

---
---

## BLOC B — COLONIE / MÉSO : PDEs de dynamique continue

**Sources :** Boswell et al. 2003 (Bull. Math. Biol. 65:447-477), Boswell 2007, Davidson 2007 (Fungal Biology Reviews 21:30-41), Falconer et al. 2005

Ce bloc décrit la colonie comme un CONTINUUM. Les tips individuels (Bloc A)
deviennent des densités. 5 variables couplées.

### Variables du système

| Symbole | Nom | Unité |
|---------|-----|-------|
| m(x,t) | Densité d'hyphes ACTIVES | biomasse/volume |
| m'(x,t) | Densité d'hyphes INACTIVES | biomasse/volume |
| p(x,t) | Densité de TIPS | tips/volume |
| n_i(x,t) | Substrat INTERNE (dans le réseau) | nutriments/volume |
| n_e(x,t) | Substrat EXTERNE (dans l'environnement) | nutriments/volume |

### B1 — Hyphes actives (croissance + inactivation)

```
∂m/∂t = a₁ × p × n_i  −  a₂ × m
```

| Terme | Signification |
|-------|--------------|
| a₁ × p × n_i | Croissance : les tips consomment du substrat interne pour créer de la biomasse |
| a₂ × m | Inactivation : hyphes actives → inactives (vieillissement, 1er ordre) |

### B2 — Hyphes inactives (accumulation + recyclage)

```
∂m'/∂t = a₂ × m  −  a₃ × m'
```

| Terme | Signification |
|-------|--------------|
| a₂ × m | Réception depuis les actives (inactivation) |
| a₃ × m' | Dégradation vers l'environnement |

**Upgrade Falconer 2005 :** Ajout du recyclage m' → n_i

```
∂m'/∂t = a₂ × m  −  ω × m'
```

| Terme | Signification |
|-------|--------------|
| ω × m' | Recyclage : biomasse inactive → nutriments internes |

C'est la différence cristal vs mycelium : le mycelium recycle sa propre biomasse.

### B3 — Tips (branchement + advection + anastomose)

```
∂p/∂t = −∇·(v × p)  +  b₁ × p × n_i  −  b₂ × p²
```

| Terme | Signification |
|-------|--------------|
| −∇·(v × p) | Advection : les tips AVANCENT avec vitesse v (partie hyperbolique) |
| b₁ × p × n_i | Branchement : proportionnel aux tips ET aux nutriments internes |
| b₂ × p² | Anastomose : deux tips se rencontrent → fusion (perte de tips) |

Note : le terme b₂ × p² est le PONT vers le Bloc C (anastomose).

### B4 — Substrat interne (transport bidirectionnel) ← ÉQUATION CLÉ

```
∂n_i/∂t = D_i × ∇²(n_i × m)  +  v_a × ∇·(n_i × ∇p)  +  U(n_e, m)  −  c₁ × p × n_i
```

| Terme | Signification | Mode |
|-------|--------------|------|
| D_i × ∇²(n_i × m) | Diffusion PASSIVE dans le réseau (confinée à m) | EXPLORATION |
| v_a × ∇·(n_i × ∇p) | Transport ACTIF vers les tips (advection vers ∇p) | EXPLOITATION |
| U(n_e, m) | Absorption du substrat externe | INPUT |
| c₁ × p × n_i | Consommation par les tips pour la croissance | OUTPUT |

Deux modes de transport :
- PASSIF (D_i) : aléatoire, exploration, connaissance qui diffuse naturellement
- ACTIF (v_a) : dirigé vers les tips, exploitation, handoff prompts ciblés

### B5 — Substrat externe (diffusion + absorption)

```
∂n_e/∂t = D_e × ∇²n_e  −  U(n_e, m)
```

Avec cinétique de Michaelis-Menten :

```
U(n_e, m) = U_max × n_e / (K_m + n_e) × m
```

| Symbole | Signification |
|---------|--------------|
| U_max | Taux maximal d'absorption |
| K_m | Constante de Michaelis (demi-saturation) |
| × m | Proportionnel à la biomasse active |

**Propriété :** Saturation. Plus K_m est petit → absorption efficace même à basse concentration.

### Propriétés du système B

| Propriété | Détail |
|-----------|--------|
| Type | Hyperbolique-parabolique mixte |
| Conservation | Positivité préservée, masse totale conservée |
| Calibration | Rhizoctonia solani, ~0.5 cm/jour |
| Passerelle CA | Boswell 2007 : mêmes PDEs → automate cellulaire sur réseau triangulaire |

### Paramètres additionnels Falconer 2005

| Symbole | Rôle |
|---------|------|
| αn | Taux d'immobilisation (mobile → immobile) |
| βn | Taux de mobilisation (immobile → mobile) |
| ω | Taux de recyclage (biomasse → nutriments) |

Le switch αn/βn contrôle les anneaux concentriques de croissance.

---
---

## BLOC C — ANASTOMOSE : L'arbre devient réseau

**Sources :** Edelstein 1982 (J. Theor. Biol.), Schnepf & Roose 2008 (J. R. Soc. Interface 5:773-784), Simonin 2013 (thèse, UC Berkeley), Glass et al. 2004

C'est LE bloc manquant qu'on a trouvé ce soir. Sans lui, on pouvait modéliser
la croissance mais pas la FORMATION DU RÉSEAU.

### C1 — Taux complet de création/destruction de tips (Edelstein 1982)

```
f = bₙ × n × (1 − n/n_max)  −  dₙ × n  −  a₂ × n × ρ  −  a₁ × n²
```

| Terme | Signification | Effet sur tips |
|-------|--------------|---------------|
| bₙ × n × (1 − n/n_max) | Branchement non-linéaire (sature à n_max) | + tips |
| dₙ × n | Mort des tips | − tips |
| **a₂ × n × ρ** | **Anastomose TIP-HYPHA** (pointe fusionne avec hyphe existant) | **− 1 tip, + 1 cycle** |
| **a₁ × n²** | **Anastomose TIP-TIP** (deux pointes fusionnent) | **− 2 tips, + 1 cycle** |

| Symbole | Signification |
|---------|--------------|
| n | Densité de tips |
| ρ | Densité de longueur hyphale |
| n_max | Densité maximale de tips |
| a₁ | Constante d'anastomose tip-tip |
| a₂ | Constante d'anastomose tip-hypha |
| bₙ | Taux de branchement |
| dₙ | Taux de mort |

### C2 — Équation de conservation des tips (intégration dans PDE)

Dans le système Schnepf-Roose, l'équation complète des tips est :

```
∂n/∂t = −∇·(n × v) + bₙ × n × (1 − n/n_max) − dₙ × n − a₂ × n × ρ − a₁ × n²
```

C'est la version ÉTENDUE de B3. Le terme b₂ × p² de Boswell = a₁ × n² d'Edelstein.
L'ajout de a₂ × n × ρ est la vraie nouveauté : fusion avec le réseau EXISTANT.

### C3 — Biologie de la fusion (Glass et al. 2004, Simonin 2013)

Deux mécanismes distincts selon le stade de développement :

| Stade | Mécanisme | Structures | Signalisation |
|-------|-----------|-----------|--------------|
| Précoce | CATs (Conidial Anastomosis Tubes) | Courts, fins, spécialisés | MAP kinase (MAK-2) |
| Mature | Fusion hyphale végétative | Branches latérales | WW domain (SO protein) |

**Communication alternée :** Les partenaires de fusion alternent entre émetteur et récepteur de signal (N. crassa). Mode de communication unique dans le vivant.

### C4 — Validation expérimentale (Simonin 2013, N. crassa)

| Mutant | Taux de fusion | Architecture | Translocation |
|--------|---------------|-------------|---------------|
| Wild type | 100% | Réseau interconnecté | Normale |
| Δso (soft) | 0% | Arbre pur hiérarchique | Sévèrement déficiente |
| ΔPrm-1 | ~50% | Intermédiaire | Intermédiaire |

**Résultat clé :** Sans anastomose (Δso), la colonie fonctionne comme un arbre pur.
Les noyaux suivent un flux "feeder hyphae → tips". Avec fusion, le flux est distribué.

### C5 — Lien avec meshedness (Pont C → D)

Chaque événement de fusion :
- Détruit 1 ou 2 tips
- CRÉE 1 cycle (boucle) dans le graphe
- Augmente α (meshedness) de 0 vers des valeurs positives
- Transforme l'arbre (α=0) en réseau maillé (α>0)

```
Δα par fusion ≈ +1 / (2N − 5)
```

---
---

## BLOC D — MÉTRIQUES RÉSEAU : Mesurer le réseau

**Sources :** Bebber et al. 2007 (Proc. R. Soc. B 274:2307-2315), Aguilar-Trigueros et al. 2022 (ISME Comm.), Latora & Marchiori 2001

Ce bloc fournit les OUTILS DE MESURE. On ne peut pas optimiser ce qu'on ne mesure pas.

### D1 — Meshedness α (coefficient alpha)

```
α = (L − N + 1) / (2N − 5)
```

| Symbole | Signification |
|---------|--------------|
| L | Nombre de liens |
| N | Nombre de nœuds |
| α = 0 | Arbre pur (pas de boucles) |
| α = 1 | Réseau planaire maximal |

**Données Bebber 2007 (P. velutina) :**
- Initial : α ≈ 0 (arbre exploratoire)
- Contrôle j39 : α = 0.11 ± 0.04
- Avec bait j39 : α = 0.20 ± 0.05
- α_intérieur > α_extérieur (core plus maillé que périphérie)

### D2 — Coût matériel C

```
C = Σ(l_i × a_i)  [mm³]
```

| Symbole | Signification |
|---------|--------------|
| l_i | Longueur du lien i |
| a_i | Aire de section transversale du lien i |

**Densité de coût :**
```
C_density = C / A_hull
```
Où A_hull = aire du convex hull. Diminue avec le temps → recyclage actif.

### D3 — Résistance fonctionnelle d'un lien

```
r_link = l / a  [mm⁻¹]
```

Modèle cylindre rempli d'hyphes parallèles. Plus court chemin par algorithme de Johnson.

### D4 — Efficacité globale (Latora-Marchiori)

```
E_global = (1 / N(N−1)) × Σᵢ≠ⱼ (1 / d_ij)
```

Transport multi-directionnel entre n'importe quels 2 nœuds.

### D5 — Efficacité root (unidirectionnelle)

```
E_root = (1 / (N−1)) × Σⱼ (1 / d_root,j)
```

Transport depuis l'inoculum (source) vers tout le réseau.

**Résultat clé Bebber :** E_root fonctionnel du réseau fongique > MST > DT.
Le renforcement différentiel des cords principaux bat même le minimum spanning tree.

### D6 — Volume-MST (overhead de construction)

```
V_MST = C_réel / C_MST
```

Ratio coût réel vs minimum possible. Mesure la "redondance architecturale".

### D7 — Robustesse (attaque séquentielle)

Protocole : supprimer les liens par ordre décroissant de betweenness centrality.
Mesurer la fraction du core connecté restant après X% de liens coupés.

**Résultat Bebber :** Après 30% de liens coupés, le réseau fongique pondéré
maintient un core connecté PLUS GRAND que MST, DT, et même le réseau non-pondéré.

### D8 — Les 15 traits réseau (Aguilar-Trigueros 2022)

**Morphologiques (5) :**
1. Longueur hyphale totale
2. Largeur des pointes
3. Largeur des hyphes principaux
4. Angle de branchement
5. Densité de longueur mycélienne

**Réseau (10) :**
6. Meshedness α
7. Root-efficiency (Reff)
8. Root-tip efficiency (R-Teff)
9. Global efficiency (Geff)
10. Volume-MST
11-15. 5 traits de robustesse (random attack, betweenness attack, weight attack, etc.)

### Données quantitatives (Table 1, Bebber 2007, P. velutina contrôle)

| Jour | Nœuds | Liens | Coût mm³ | Densité coût |
|------|-------|-------|----------|-------------|
| 18 | 515±70 | 644±127 | 234±6 | 1.0±0.1 |
| 25 | 738±87 | 946±159 | 294±10 | 0.8±0.0 |
| 31 | 805±131 | 1040±218 | 287±23 | 0.6±0.0 |
| 39 | 697±145 | 883±234 | 292±31 | 0.6±0.1 |

**Observation :** Nœuds DIMINUENT entre j31→j39 → pruning actif !

---
---

## BLOC E — TRANSPORT : Flux de ressources dans le réseau

**Sources :** Tero et al. 2010 (Science 327:439-442), Fricker et al. 2017 (Microbiol. Spectrum 5(3)), Heaton et al. 2010

Ce bloc décrit comment les ressources CIRCULENT une fois le réseau formé.

### E1 — Flux de Kirchhoff (Physarum/Tero)

```
Q_ij(t) = (D_ij(t) / L_ij) × (p_i − p_j)
```

Conservation aux nœuds :
```
Σⱼ Q_ij(t) = 0  ∀i (sauf source et puits)
```

| Symbole | Signification |
|---------|--------------|
| Q_ij | Flux dans le lien ij |
| D_ij | Conductance du lien ij |
| L_ij | Longueur du lien ij |
| p_i, p_j | Pressions aux nœuds |

### E2 — Évolution adaptative des conductances

```
dD_ij/dt = f(|Q_ij(t)|) − r × D_ij(t)
```

| Terme | Signification |
|-------|--------------|
| f(\|Q\|) = \|Q\| | Renforcement proportionnel au flux |
| r × D_ij | Décroissance naturelle |

**Résultat :** Les canaux à fort flux se renforcent, les autres meurent.
Converge vers solution optimale (Physarum résout le shortest path).

### E3 — Modèle ADD (Fricker 2017)

Le modèle Advection-Diffusion-Delivery :
- **Advection :** Transport par flux de masse (induit par croissance apicale)
- **Diffusion :** Mouvement stochastique des solutés dans le réseau
- **Delivery :** Absorption/livraison aux nœuds (uptake/release)

Corrélation modèle-expérience : r = 0.56 (Pearson) pour distribution de radiotraceur.

### E4 — Vitesses mesurées (Fricker 2017)

| Espèce | Vitesse de flux | Contexte |
|--------|----------------|---------|
| P. velutina | 20-100 mm/h | Flux de masse dans cords |
| S. lacrymans | jusqu'à 148 cm/h | Record mesuré |
| N. crassa (noyaux) | ~4 mm/h | Transport nucléaire |

Le flux volumétrique scale avec le nombre de tips en aval (downstream).

### E5 — Corrélation flux-centralité (Oyarte Galvez 2025, Nature)

```
v_flux ∝ BC(link)
```

Où BC = betweenness centrality du lien.
Mesuré sur >500,000 nœuds simultanément par robot d'imagerie.

---
---

## BLOC F — COMPUTATION : Le réseau qui calcule

**Sources :** Adamatzky 2018 (Interface Focus 8:20180029), Roberts et al. 2022 (BioSystems), Tompris et al. 2025

Ce bloc montre que la structure du réseau DÉTERMINE sa capacité de calcul.

### F1 — Automate fongique (Adamatzky 2018)

```
A = ⟨C, Q, r, θ, δ⟩
```

| Symbole | Signification |
|---------|--------------|
| C | Ensemble de cellules (nœuds du réseau) |
| Q | Ensemble d'états possibles par cellule |
| r | Rayon de voisinage |
| θ | Fonction de seuil (activation) |
| δ | Fonction de transition (mise à jour d'état) |

Principe : Géométrie → Computation. La forme du réseau détermine les fonctions calculées.

### F2 — Circuits booléens extraits (Roberts 2022)

- 3136 fonctions booléennes extraites expérimentalement de P. ostreatus
- 470 fonctions uniques parmi les 3136
- Classification Wolfram : Classe IV (edge of chaos)
- **Preuve de Turing-completeness** du substrat fongique

### F3 — Reservoir computing

Architecture :
```
Input layer → RESERVOIR (réseau fongique) → Output layer (linéaire)
```

```
ŷ = W × X
```

| Symbole | Signification |
|---------|--------------|
| X | Matrice N×M des états du réservoir (N nœuds, M pas de temps) |
| W | Matrice de poids (apprise par régression linéaire) |
| ŷ | Prédiction |

Performance : 97% MNIST avec réservoir mycelium-inspiré (Tompris 2025).

---
---

## BLOC G — TOPOLOGIE : Classifier et comparer les réseaux

**Sources :** Watts & Strogatz 1998 (Nature), Fricker et al. 2017, Humphries & Gurney 2008

### G1 — Coefficient small-world σ

```
γ = C / C_rand      (ratio clustering)
λ = L / L_rand      (ratio path length)
σ = γ / λ           (small-world si σ > 1)
```

Pour un graphe aléatoire ER(n,k) :
```
C_rand ≈ k/n
L_rand ≈ ln(n)/ln(k)
```

Small-world ⟺ C >> C_rand ET L ≈ L_rand.

### G2 — Coefficient omega ω (alternative à σ)

```
ω = L_rand/L − C/C_lattice
```

| Valeur | Type de réseau |
|--------|---------------|
| ω ≈ −1 | Lattice (régulier) |
| ω ≈ 0 | Small-world |
| ω ≈ +1 | Random |

### G3 — Stratégies Phalanx vs Guerrilla (Fricker 2017)

| Caractéristique | Phalanx | Guerrilla |
|----------------|---------|-----------|
| Branchement | Fréquent, angles larges | Rare |
| Vitesse | Lente | Rapide |
| Front | Large, synchrone | Étroit, indépendant |
| Portée | Court-range | Long-range |
| Densité | Dense | Éparse |
| Exemple | Phallus impudicus | Armillaria spp. |
| Connectivité | Haute | Basse |
| Robustesse | Haute | Basse |
| Coût | Élevé | Faible |
| E_root | Moyenne | Haute |
| E_global | Haute | Basse |

**Axe principal de variation (Aguilar-Trigueros 2022, analyse Pareto) :**
Les espèces se distribuent le long du gradient de connectivité.
Ce n'est PAS la taxonomie qui prédit la stratégie, mais l'environnement.

### G4 — Dimensions fractales

```
DBM = log(M(r)) / log(r)     (fractal dimension of mass)
DBS = log(S(r)) / log(r)     (fractal dimension of surface)
```

| Mesure | Signification |
|--------|--------------|
| DBM élevé | Remplissage dense de l'espace |
| DBS élevé | Front complexe, très ramifié |
| DBM/DBS diminuent | Sous compétition ou grazing |

---
---

## BLOC H — ALGORITHMES BIO-INSPIRÉS : Compléments

**Sources :** Socha & Dorigo 2008 (European J. Operational Research), Lindenmayer 1968, Turing 1952

### H1 — ACOR : Phéromones continues (Socha & Dorigo)

```
τ_ij(t+1) = (1−q) × τ_ij(t) + Σ(s∈S_bonnes) Δτ_ij^s
```

| Symbole | Signification |
|---------|--------------|
| τ_ij | Concentration de phéromone sur l'arête ij |
| q ∈ (0,1] | Taux d'évaporation |
| S_bonnes | k meilleures solutions trouvées |

En continu : archive → noyau gaussien multi-modal → tirage de nouvelles solutions.

### H2 — Réaction-Diffusion (Turing 1952)

```
∂u/∂t = D_u ∇²u + F(u,v)    (activateur)
∂v/∂t = D_v ∇²v + G(u,v)    (inhibiteur)
```

Instabilité de Turing → patterns émergents.
Différence cristal vs mycelium :
- Cristal : champ figé après formation (mort)
- Mycelium : + advection interne + recyclage (vivant)

### H3 — L-Systems (Lindenmayer 1968)

```
Axiome : F
Règle : F → F[+F]F[−F]F
```

Graine + règles simples = arbre complet.
Exactement le principe du Winter Tree plant mode.
Mais L-Systems = pas d'anastomose (arbre pur), pas de réseau.
→ L-Systems = v1, Mycelium = v2.

---
---

## MAPPING WINTER TREE v2 — SYNTHÈSE

### Par bloc

| Bloc | Biologie | Winter Tree v2 |
|------|----------|---------------|
| A1 | Champ de densité N_{S,p} | Saturation d'info dans un domaine (anti-redondance) |
| A2 | Champ de substrat O_{T,p} | Source de connaissance externe (attracteur) ou contrainte (inhibiteur) |
| A3 | Vecteur de croissance v_new | Direction d'intérêt du développeur |
| A4 | Branchement | Création de nouveau fichier/feature |
| A5 | Galvanotropisme | Alignement thématique entre repos ("veines") |
| A6 | 3 types d'hyphes | Standard=docs normaux, Leading=README/battle plans, Secondary=LESSONS_LEARNED |
| B1 | Hyphes actives m | Docs/artefacts activement utilisés |
| B2 | Hyphes inactives m' | Docs obsolètes mais structurants |
| B3 | Tips p | Nouveaux commits, nouvelles idées |
| B4 passif | Diffusion D_i | Transfert aléatoire de connaissances (exploration) |
| B4 actif | Advection v_a | Transfert dirigé : handoff prompts (exploitation) |
| B5 | Michaelis-Menten U() | Intégration de sources externes (sature quand on sait déjà) |
| Falconer ω | Recyclage m' → n_i | Réutilisation de code/patterns obsolètes |
| C1 | a₁ × n² (tip-tip) | Deux branches actives qui mergent (PR merge) |
| C1 | a₂ × n × ρ (tip-hypha) | Branche active se reconnecte à code existant (refactoring) |
| C4 | Mutant Δso (pas de fusion) | Repo sans merges ni refactoring → arbre pur, mauvaise redistribution |
| D1 | Meshedness α | Degré d'interconnexion entre modules |
| D4 | E_global | Communication facile entre n'importe quels 2 modules |
| D5 | E_root | Propagation efficace depuis l'entry point (main/index) |
| D6 | Volume-MST | Overhead architectural vs minimum |
| D7 | Robustesse | Fichiers/modules supprimables avant casse |
| E1-E2 | Flux adaptatif Kirchhoff | Renforcement des modules à fort trafic |
| F1 | Automate A | La structure du repo détermine ce qu'il peut "calculer" |
| G3 | Phalanx | Monorepo mature : tests extensifs, CI/CD, lent |
| G3 | Guerrilla | Micro-services : déploiement rapide, fragile |

### Formules clés pour l'implémentation

```
Résistance au changement :     r_module = complexity × coupling⁻¹
Trilemme Pareto :              min(Coût) + max(Efficacité) + max(Robustesse)
Santé du réseau :              f(α, E_root, E_global, σ, robustesse)
```

---
---

## ALGORITHMES À IMPLÉMENTER (par priorité)

### Priorité 1 — Core metrics

| # | Algorithme | Source | Lib Python |
|---|-----------|--------|-----------|
| 1 | Alpha coefficient (meshedness) | Bebber 2007 | Custom |
| 2 | Betweenness centrality | Bebber/Fricker | networkx.betweenness_centrality() |
| 3 | Johnson's shortest path | Bebber 2007 | networkx.johnson() |
| 4 | E_global (Latora-Marchiori) | Bebber 2007 | networkx.global_efficiency() |
| 5 | E_root (unidirectionnel) | Bebber 2007 | Custom |
| 6 | MST | Bebber 2007 | networkx.minimum_spanning_tree() |

### Priorité 2 — Robustesse et stratégie

| # | Algorithme | Source | Lib Python |
|---|-----------|--------|-----------|
| 7 | Attaque séquentielle (betweenness) | Bebber 2007 | Custom loop |
| 8 | Small-world σ | Watts-Strogatz | networkx.sigma() |
| 9 | Small-world ω | Humphries | networkx.omega() |
| 10 | Volume-MST ratio | Bebber 2007 | Custom |

### Priorité 3 — Dynamique et flux

| # | Algorithme | Source | Lib Python |
|---|-----------|--------|-----------|
| 11 | Conductance adaptative (Tero) | Tero 2010 | Custom ODE solver |
| 12 | ADD model (advection-diffusion) | Fricker 2017 | Custom PDE solver |
| 13 | Anastomose tip-tip / tip-hypha | Edelstein 1982 | Custom (termes a₁, a₂) |

---
---

## SOURCES COMPLÈTES

| # | Référence | Année | Blocs | Accès |
|---|-----------|-------|-------|-------|
| 1 | Meškauskas & Moore, Mycol. Res. 108:1241-1256 | 2004a | A | PDF gratuit |
| 2 | Meškauskas et al., Mycol. Res. 108:1257-1274 | 2004b | A | PDF gratuit |
| 3 | Edelstein, J. Theor. Biol. | 1982 | C | Référence historique |
| 4 | Boswell et al., Bull. Math. Biol. 65:447-477 | 2003 | B | Via Davidson |
| 5 | Falconer et al. | 2005 | B | Recyclage ω |
| 6 | Davidson, Fungal Biology Reviews 21:30-41 | 2007 | A,B | PDF gratuit |
| 7 | Bebber et al., Proc. R. Soc. B 274:2307-2315 | 2007 | D | PMC open |
| 8 | Schnepf & Roose, J. R. Soc. Interface 5:773-784 | 2008 | C | PMC open |
| 9 | Socha & Dorigo, Eur. J. Op. Research | 2008 | H | |
| 10 | Tero et al., Science 327:439-442 | 2010 | E | |
| 11 | Simonin, PhD thesis UC Berkeley | 2013 | C | Open access |
| 12 | Fricker et al., Microbiol. Spectrum 5(3) | 2017 | D,E,G | Chapter |
| 13 | Adamatzky, Interface Focus 8:20180029 | 2018 | F | Royal Soc. open |
| 14 | Roberts et al., BioSystems | 2022 | F | |
| 15 | Aguilar-Trigueros et al., ISME Comm. | 2022 | D,G | Open |
| 16 | Tompris et al., Natural Computing | 2025 | F | Paywall |
| 17 | Oyarte Galvez et al., Nature | 2025 | E | |

---
---

## STATUT GLOBAL

```
BLOC A — AGENT         ✅ COMPLET (6 formules, 2 papers)
BLOC B — COLONIE       ✅ COMPLET (5 PDEs + Falconer, 3 papers)
BLOC C — ANASTOMOSE    ✅ COMPLET (équation + validation, 3 papers)  ← NOUVEAU
BLOC D — MÉTRIQUES     ✅ COMPLET (8 métriques + 15 traits, 2 papers)
BLOC E — TRANSPORT     ✅ COMPLET (5 formules, 3 papers)
BLOC F — COMPUTATION   ✅ COMPLET (automate + reservoir, 3 papers)
BLOC G — TOPOLOGIE     ✅ COMPLET (σ, ω, strategies, fractales, 3 papers)
BLOC H — ALGO BIO      ✅ COMPLET (ACOR + Turing + L-Systems, 3 papers)
```

**Total : 8 blocs, ~30 formules, 17 sources, mapping complet.**

**Chaîne complète de construction :**
```
Tips grandissent (A) → Colonie émerge (B) → Fusions créent réseau (C)
→ On mesure le réseau (D) → Ressources circulent (E) → Le réseau calcule (F)
→ On classifie la stratégie (G) → Inspirations croisées (H)
```

---

*"L'arbre explore. Le mycelium connecte. La forêt pense."*
*Winter Tree v2 — Référentiel complet — 15 février 2026, 5h du mat*

---

## BRIQUE 15 — 3D Hyphal Mechanics

### Lockhart Equation [Money 2025]
```
v = φ · max(0, P - Y)
```
| Symbole | Signification | Valeur typique |
|---------|--------------|----------------|
| v | Extension rate | 0-1 (normalized) |
| φ | Wall extensibility | 1.0 |
| P | Turgor pressure | 0.1-1.0 MPa |
| Y | Yield threshold | 0.2 |

### Hyphoid Equation [Bartnicki-Garcia 1989]
```
y = x · cot(V·x / N)
diameter = π · N / V
```
| Symbole | Signification |
|---------|--------------|
| N | Vesicles released per unit time |
| V | VSC (Spitzenkörper) displacement rate |
| x, y | Tip shape coordinates |

### Autotropism Field [Meškauskas 2004]
```
F(node) = Σ (strength / d²) · (pos - other_pos) / |pos - other_pos|
```
Each hypha generates scalar field 1/d². Tips repelled from dense regions.

### Spitzenkörper Memory [Lew 2011]
```
growth_dir = normalize(spk_persistence × spk_direction + (1 - spk_persistence) × parent_direction)
```
| Param | Signification |
|-------|--------------|
| spk_persistence | 0-1, directional memory (gyroscope) |
| spk_direction | Stored on each tip node |

### Branching [Riquelme 2004, Meškauskas 2004]
```
P(branch) ≈ 0.15 per step
angle ∈ [30°, 90°]
branch_dir = rotate(growth_dir, angle, random_axis)  // Rodrigues
```

---

## Brique 16 — AM Fungi Root Growth [Schnepf & Roose 2008]

### Tip Conservation
```
∂n/∂t = -∇·(nv) + f
f = bₙ·n·(1 - n/nₘₐₓ) - dₙ·n - a₂·n·ρ - a₁·n²
```
| Term | Description |
|------|-------------|
| bₙ·n·(1-n/nₘₐₓ) | Logistic branching |
| dₙ·n | Tip death |
| a₂·n·ρ | Tip-hypha anastomosis (A. laevis) |
| a₁·n² | Tip-tip anastomosis (Glomus sp.) |

### Hyphal Length Density
```
∂ρ/∂t = n|v| - dρ
```

### Root Boundary Condition
```
n(r₀, t) = at + n₀,b
```
Root surface acts as continuous source of hyphal tips.

### Dimensionless Ratios
```
δ = d/b    (death/branching ratio)
```
| δ | Biomass distribution |
|---|---------------------|
| δ << 1 | Accumulated near root |
| δ >> 1 | At colony front |

### Colony Edge
```
xc = v·t
```

### VSC Tip Diameter (from brique 15)
```
d = π·N/V
```
