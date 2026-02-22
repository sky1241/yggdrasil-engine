# DEEP RESEARCH MYCELIUM — v2 RÉSULTATS
# Issu du prompt v1, trié : or vs trous
# 15 février 2026

---

## STATUT PAR AXE

| Axe | Sujet | Statut | Manque |
|-----|-------|--------|-------|
| 1 | Neighbour-Sensing (Meškauskas) | ✅ ÉQUATIONS OK | — |
| 1 | Boswell PDE (3 composants) | ⚠️ DÉCRIT SANS ÉQUATIONS | PDEs exactes m, m', p |
| 1 | Tompris CA rules | ⚠️ DÉCRIT SANS DÉTAIL | Règles de transition |
| 2 | Multi-scale (Davidson) | ✅ CONCEPTUEL OK | Pas de formalisme unifié (n'existe pas) |
| 2 | Small-world metrics | ⚠️ QUALITATIF | Valeurs numériques réelles |
| 2 | Circuit theory (Heaton) | ⚠️ PRINCIPE OK | Équations complètes |
| 3 | ACOR (Socha & Dorigo) | ✅ MÉCANISME OK | — |
| 3 | L-Systems (Lindenmayer) | ✅ PRINCIPE OK | — |
| 3 | Physarum | ✅ ÉQUATIONS OK | — |
| 4 | Réaction-diffusion (Turing) | ✅ ÉQUATIONS OK | — |
| 4 | Automates cellulaires | ✅ PRINCIPE OK | — |
| 5 | Winter Tree application | ⚠️ CONCEPTUEL | À formaliser nous-mêmes |
| 5 | P=NP strates | ❌ PAS DE FORMALISME | Normal — ça n'existe pas encore |

---

## AXE 1 — ÉQUATIONS SOLIDES

### Neighbour-Sensing — Champ de densité (Meškauskas 2004)

**Champ local (court rayon, auto-inhibition) :**

```
N_{S,p} = (l_c / |S_A|) × Σ(j=1→|S_A|) 1/|S_Aj - p|²
```

- S_A = points échantillonnant la géométrie de la section hyphale S
- p = point d'intérêt (position du tip qui "sent")
- l_c = longueur de corrélation (facteur d'échelle du champ)
- Décroissance en 1/d² → champ local, courte portée

**Champ distant (long rayon, orientation) :**

```
M_{S,p} ∝ 1/d ou 1/√d → longue portée
```

**Vecteur de croissance :**

```
v_new = norm(S_growth + g(S, β))
```

- S_growth = vecteur antérograde (direction actuelle)
- g(S, β) = combinaison des tropismes (densité, gravité, substrat)
- β = angle dosant l'ampleur de chaque tropisme
- Résultat normalisé → direction + vitesse constante

**Branchement :**

```
SI densité_locale(R) > seuil ALORS
    SI random(0,100) < p_branch ALORS
        créer nouvelle branche
```

- R = rayon de détection local
- p_branch = probabilité de branchement (%)

### Physarum — Flux et adaptation (Tero et al.)

**Flux dans le réseau :**

```
Q_ij(t) = (D_ij(t) / L_ij) × (p_i - p_j)
Σ_j Q_ij(t) = 0  (conservation)
```

**Évolution des conductances :**

```
dD_ij/dt = f(|Q_ij(t)|) - r × D_ij(t)
```

- D_ij = conductance de l'arête ij
- L_ij = longueur de l'arête
- p_i, p_j = pressions aux nœuds
- r = taux de décroissance
- f(Q) = |Q| → renforcement proportionnel au flux
- Résultat : les canaux à fort flux se renforcent, les autres meurent

### ACOR — Phéromones (Socha & Dorigo 2008)

**Dépôt/évaporation :**

```
τ_ij(t+1) = (1-q) × τ_ij(t) + Σ(s∈S_bonnes) Δτ_ij^s
```

- q ∈ (0,1] = taux d'évaporation
- En continu : archive de k meilleures solutions → noyau gaussien multi-modal
- Nouvelles solutions = tirage normal depuis mélange gaussien pondéré par rang

### Réaction-Diffusion (Turing 1952)

```
∂u/∂t = D_u ∇²u + F(u,v)
∂v/∂t = D_v ∇²v + G(u,v)
```

- u, v = morphogènes (activateur/inhibiteur)
- D_u, D_v = coefficients de diffusion
- Instabilité de Turing → patterns émergents
- CRISTAL : champ figé après formation (mort)
- MYCELIUM : + terme d'advection interne + recyclage (vivant)

---

## AXE 1 — TROUS À SNIPER

### 🎯 CIBLE 1 : Boswell PDE (PRIORITÉ HAUTE)

Les 3 composants : hyphes actives (m), inactives (m'), tips (p)
+ nutriments internes (n_i) et externes (n_e)
+ absorption Michaelis-Menten
+ transport = diffusion + advection

→ BESOIN : les PDEs exactes de Boswell et al. 2003, Bulletin of Mathematical Biology 65:447-477

### 🎯 CIBLE 2 : Tompris CA rules

Les règles de transition de l'automate cellulaire
+ intégration température/humidité/lumière
+ Hyphae Information Algorithm

→ BESOIN : détail des Eqs (1)-(4) de Tompris et al. 2024/2025

### 🎯 CIBLE 3 : Small-world metrics numériques

Valeurs réelles de clustering coefficient et path length mesurées sur du vrai mycelium
→ BESOIN : données expérimentales ou simulées avec valeurs numériques

### 🎯 CIBLE 4 : Heaton circuit theory

Équations complètes du modèle de flux par théorie des circuits
→ BESOIN : Heaton et al. 2010, formules de redistribution

---

## AXE 2 — PONTS INTER-ÉCHELLES (résumé)

```
MICRO (Meškauskas)          MÉSO (Boswell)           MACRO (Tompris/Adamatzky)
1 tip, champs locaux   →   colonie, PDEs densité  →  topologie, small-world
                                                      
Comportement individuel     Propriétés collectives    Propriétés de réseau
Pas de plan central         Émergence de structure    Calcul distribué
Règles locales              Transport + recyclage     Reservoir computing
```

Passerelle micro→méso : la somme des champs individuels → densité continue (limite dense)
Passerelle méso→macro : la structure du réseau → propriétés topologiques (clustering, paths)
Modèle unifié : N'EXISTE PAS ENCORE (Davidson 2007)

---

## AXE 5 — APPLICATION WINTER TREE (conceptuel)

**Mapping proposé :**

| Biologie | Winter Tree |
|----------|-------------|
| Hyphe active (m) | Document/artefact utilisé activement |
| Hyphe inactive (m') | Document obsolète mais structurant |
| Tip (p) | Nouveau commit, nouvelle contribution |
| Nutriment externe (n_e) | Connaissance externe (citations, données) |
| Nutriment interne (n_i) | Connaissance interne (lessons learned, patterns) |
| Absorption Michaelis-Menten | Intégration progressive de nouvelles connaissances |
| Translocation | Transfert de patterns entre projets |
| Branchement | Création de nouveau document/feature |
| Champ de densité N_{S,p} | Saturation d'info dans un domaine (anti-redondance) |
| l_c (longueur corrélation) | Horizon cognitif (portée de l'influence passée) |
| Anastomose | Fork/merge entre repos |
| Small-world | Équilibre spécialisation locale / diffusion globale |

**Métriques de santé du réseau :**
- Clustering coefficient C (cohésion thématique)
- Path length moyen L̄ (vitesse de diffusion d'info)
- Ratio hyphes actives/inactives (dette technique)
- Densité de tips (taux d'innovation)
- Flux de Heaton (redistribution de connaissances)

**P=NP — strates bornées :**
- Pas de formalisme existant pour "épaisseur" des barrières
- Mais les barrières délimitent des CLASSES D'ARGUMENTS, pas des zones géographiques
- La méthode Mendeleïev = cartographier les classes connues, les trous = classes manquantes
- Sol = axiomes. Ciel = non-computabilité. Entre = tout l'explorable.
- Les deux faces d'une même pièce.

---

*"Le cristal est terminé. Le mycelium négocie."*
*v2 — 15 février 2026*
