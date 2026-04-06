# Physique du caillou dans la mare — Formules sourcées

> Yggdrasil Engine — Session 33, 2 avril 2026
> Toutes les formules avec sources peer-reviewed ou textbook.

---

## 1. ÉNERGIE À L'IMPACT

### Énergie potentielle (mécanique classique)

```
E_impact = m × g × h
v_impact = sqrt(2 × g × h)
```

- **m** = masse du corps
- **g** = accélération gravitationnelle (9.81 m/s²)
- **h** = hauteur de chute

**Source**: Newton, I. (1687). *Philosophiæ Naturalis Principia Mathematica*. Livre I, Prop. XXXIX.

### Mapping mycélium

| Physique | Mycélium |
|----------|----------|
| m (masse) | works_count ou degré des concepts-graines dans cooc_global |
| h (hauteur) | strate d'origine (S0=0, S1=1, ..., S6=6) |
| g (gravité) | constante à fitter (vitesse de propagation dans le graphe) |
| E_impact | énergie de la percée scientifique |

---

## 2. CRATÈRE D'IMPACT DANS L'EAU

### Diamètre du cratère (Worthington 1908)

```
D_crater / d_sphere = k × Fr^(1/4)
Fr = v² / (g × d)     [nombre de Froude]
```

- **d** = diamètre du caillou
- **v** = vitesse à l'impact
- **Fr** = nombre de Froude (ratio inertie/gravité)
- **k** ≈ 2-4 (empirique)

**Source**: Worthington, A.M. (1908). *A Study of Splashes*. Longmans, Green & Co.

### Profondeur du cratère (Pumphrey & Elmore 1990)

```
z_max = 0.44 × d × Fr^(0.25)
```

**Source**: Pumphrey, H.C. & Elmore, P.A. (1990). "The entrainment of bubbles by drop impacts." *J. Fluid Mech.*, 220, 539-567. DOI: 10.1017/S0022112090003378

### Mapping mycélium

| Physique | Mycélium |
|----------|----------|
| D_crater | nombre de concepts directement touchés (wave 1) |
| z_max | profondeur de pénétration (combien de strates traversées) |
| Fr | ratio énergie de la percée / densité locale du graphe |

---

## 3. ONDES DE SURFACE (capillaires + gravitaires)

### Vitesse de propagation

```
Eau profonde:     v_phase = sqrt(g × lambda / (2 × pi))
Eau peu profonde: v_phase = sqrt(g × h_eau)
```

- Les ondes en eau profonde sont **dispersives** (chaque longueur d'onde a sa vitesse)
- Les ondes en eau peu profonde sont **non-dispersives** (vitesse unique = front net)

**Source**: Lamb, H. (1932). *Hydrodynamics*, 6th ed. Cambridge University Press. §228-229.

### Amplitude en fonction de la distance

```
Géométrique pur:    A(r) = A_0 / sqrt(r)
Avec dissipation:   A(r) = A_0 / sqrt(r) × exp(-alpha × r)
```

- **A_0** ∝ sqrt(E_impact) — amplitude initiale
- **alpha** = coefficient d'amortissement visqueux
- La décroissance en 1/√r vient de la conservation d'énergie sur un cercle 2πr

**Source**: Lighthill, J. (1978). *Waves in Fluids*. Cambridge University Press. §1.5, 3.7.

### Fraction d'énergie dans les ondes

```
E_vagues ≈ 0.01 à 0.30 × E_impact
```

Seulement 1-30% de l'énergie part en vagues de surface. Le reste: splash, son, chaleur.

**Source**: Leng, L.J. (2001). "Splash formation by spherical drops." *J. Fluid Mech.*, 427, 73-105. DOI: 10.1017/S0022112000002500

### Mapping mycélium

| Physique | Mycélium |
|----------|----------|
| v_phase | vitesse de propagation BFS (noeuds/an) |
| A(r) | taille du front à distance r (nouveaux concepts par onde) |
| alpha | résistance du graphe (clusters denses absorbent l'onde) |
| dispersif vs non-dispersif | graphe hétérogène (dispersif) vs homogène (non-dispersif) |

---

## 4. CAILLOU QUI COULE (drag)

### Vitesse terminale

```
v_terminal = sqrt( 8 × r × Delta_rho × g / (3 × C_d × rho_eau) )
Delta_rho = rho_caillou - rho_eau
```

- **C_d** ≈ 0.47 (sphère lisse, Re > 1000)
- Le sillage derrière le caillou s'élargit en **sqrt(t)**

**Source**: Stokes, G.G. (1851). "On the Effect of the Internal Friction of Fluids on the Motion of Pendulums." *Trans. Cambridge Phil. Soc.*, 9, 8-106.

Pour le coefficient de traînée: Schlichting, H. (1979). *Boundary-Layer Theory*, 7th ed. McGraw-Hill. Ch. XXI.

---

## 5. DIFFUSION DE CHALEUR SUR GRAPHE (Carmack move)

### Heat kernel

```
f(t) = exp(-t × L) × f(0)
```

- **L** = Laplacien normalisé du graphe (L = I - D^(-1/2) × W × D^(-1/2))
- **f(0)** = vecteur initial (Dirac sur les concepts-graines: 1 sur les graines, 0 partout)
- **f(t)** = distribution de chaleur à temps t (influence de la percée sur chaque concept)
- **Zéro paramètre libre** — tout est dans le Laplacien

**Forme spectrale** (si on a les vecteurs propres):
```
f(t) = sum_k exp(-t × lambda_k) × <f(0), phi_k> × phi_k
```

- lambda_k = valeurs propres du Laplacien (on les a dans WT4: gap = 0.226)
- phi_k = vecteurs propres
- Les basses fréquences (petits lambda) propagent lentement = signal global
- Les hautes fréquences (grands lambda) se dissipent vite = signal local

**Source**: Chung, F.R.K. (1997). *Spectral Graph Theory*. AMS CBMS Regional Conference Series, No. 92. Ch. 1, 7.

**Source complémentaire**: Kondor, R.I. & Lafferty, J. (2002). "Diffusion Kernels on Graphs and Other Discrete Structures." *Proc. ICML*, 315-322.

### Mapping mycélium

| Physique | Mycélium |
|----------|----------|
| L | Laplacien WT4 (66,342 noeuds, gap 0.226, k=20 eigenvectors calculés) |
| f(0) | vecteur Dirac sur concepts Gödel (idx 12665, 8122, 1806) |
| f(t) | influence de Gödel sur chaque concept à temps t |
| lambda_k | taux de décroissance par mode spectral |

---

## 6. MODÈLE SIR ÉPIDÉMIQUE (alternative)

```
dS/dt = -(beta/N) × I × S
dI/dt = (beta/N) × I × S - gamma × I
dR/dt = gamma × I

R_0 = beta / gamma     [seuil épidémique]
```

Sur un réseau: seuil = 1 / lambda_max(A) où lambda_max = rayon spectral de la matrice d'adjacence.

**Source**: Kermack, W.O. & McKendrick, A.G. (1927). "A contribution to the mathematical theory of epidemics." *Proc. R. Soc. Lond. A*, 115(772), 700-721. DOI: 10.1098/rspa.1927.0118

Pour les réseaux: Pastor-Satorras, R. & Vespignani, A. (2001). "Epidemic Spreading in Scale-Free Networks." *Phys. Rev. Lett.*, 86(14), 3200-3203. DOI: 10.1103/PhysRevLett.86.3200

---

## 7. PROCESSUS DE BRANCHEMENT GALTON-WATSON

```
mu = sum_k k × p_k     [taux de reproduction moyen]
Supercritique si mu > 1 (cascade globale)
Sous-critique si mu < 1  (cascade meurt)
```

- p_k = probabilité qu'un concept activé en active k autres
- Sur un graphe: p_k ≈ distribution de degré normalisée

**Source**: Harris, T.E. (1963). *The Theory of Branching Processes*. Springer-Verlag. Ch. I.

### Mapping mycélium: taux de branchement mesuré

Gödel 1931 (session 33, mesuré dans WT3):
```
1932: mu = 9/3   = 3.0     (supercritique)
1933: mu = 485/9  = 53.9   (explosion)
1934: mu = 3563/485 = 7.3
1935: mu = 3402/3563 = 0.95 (subcritique → décélère)
1936: mu = 12105/3402 = 3.6 (rebond ! 2ème onde ?)
1937: mu = 7919/12105 = 0.65 (mort)
```

---

## 8. NEWMAN SIR-PERCOLATION (cadre théorique pour R_max)

```
SIR ≡ bond percolation avec transmissibilité T
S(T) = 1 - G₀(u)       [fraction infectée = R_max/N]
u résout: u = G₁(1-T+Tu)
G₀(x) = Σ_k p_k × x^k  [generating function du degré]
G₁(x) = G₀'(x) / G₀'(1) [excess degree]
T_c = ⟨k⟩ / (⟨k²⟩ - ⟨k⟩)  [seuil de percolation]
```

- **T** = transmissibilité (1 paramètre par météorite)
- **P(k)** = distribution de degré mesurée sur cooc_global
- Sur Yggdrasil: ⟨k⟩=2136, T_c=0.0002 (quasi-zéro = toute perturbation se propage)

**Source**: Newman, M.E.J. (2002). "Spread of epidemic disease on networks." *Phys. Rev. E* 66, 016128. arXiv: cond-mat/0205009

---

## 9. LOGISTIQUE S-CURVE (trajectoire R(t))

```
R(t) = K / (1 + exp(-r × (t - t₀)))
```

- **K** = capacité (≈ R_max)
- **r** = taux de croissance
- **t₀** = point d'inflexion

Testée sur 13 météorites: **R² médian = 0.9996**, K_error < 1% pour toutes.

**Source**: modèle de croissance logistique standard (Verhulst 1838).

---

## 10. RÉSULTATS SESSION 34 — BATTERIE COMPLÈTE (13 météorites)

### Modèles testés et verdicts

| Modèle | Params | Verdict | Détail | Source |
|--------|--------|---------|--------|--------|
| **Logistique S-curve** | 3 (K,r,t₀) | **PASS** | R² médian=1.00, K_err<1% | Verhulst 1838 |
| **Oscillateur amorti** | 5 | **PASS** | R² médian=1.00 sur mu(t) | Hawkes-type |
| **Mort spectrale** | 0 | **PASS** | Prédit 8.1 ans, MAE=1.79 ans | Chung 1997 |
| **Onde de surface** | 2 (A₀,α) | **PASS** | R² médian=0.82 | Lamb 1932 |
| Newman percolation | 1 (T) | PARTIAL | LOO MAE=11,597 | Newman 2002 |
| Power law (baseline) | 2 (a,b) | PARTIAL | R² médian=0.61 | baseline |
| Énergie E=m×g×h | divers | **FAIL** | ρ<0.26 pour tout | Newton 1687 |
| Sedov-Taylor | 2 (β,α) | **FAIL** | R² holdout=-5.74 | Taylor 1950 |

### Résultat principal: "C'est la mare qui décide"

L'énergie du caillou (works_count, strate, degré des seeds) NE prédit PAS R_max.
Les propriétés de la mare (median_neighbor_works ρ=+0.60, p=0.029) prédisent mieux.
Le Laser (4,131 = 6%) tombe dans une mare épaisse (avg_edge_weight=12.24, Type A).

### 13 météorites mesurées

| Météorite | R_max | % science | Mort | mu_peak |
|-----------|-------|-----------|------|---------|
| mRNA 1990 | 62,787 | 97% | t+6 | 219.7 |
| CRISPR 2012 | 59,315 | 91% | t+7 | 364.2 |
| Higgs 2012 | 55,558 | 85% | t+5 | 68.0 |
| Internet 1974 | 53,257 | 82% | t+12 | 116.7 |
| AlphaFold 2020 | 51,485 | 79% | t+5 | 64.8 |
| Grav waves 2016 | 50,302 | 77% | t+6 | 47.0 |
| Shannon 1948 | 49,627 | 76% | t+8 | 24.4 |
| Transistor 1947 | 45,604 | 70% | t+8 | 28.4 |
| Turing 1936 | 41,970 | 65% | t+8 | 183.5 |
| ADN 1953 | 36,081 | 55% | t+9 | 8.4 |
| Gödel 1931 | 28,845 | 44% | t+11 | 53.9 |
| Poincaré 2003 | 21,072 | 32% | t+11 | 24.1 |
| Laser 1960 | 4,131 | 6% | t+9 | 6.0 |

### Modèle retenu (hybride)

1. **Trajectoire**: logistique R(t) = K/(1+exp(-r(t-t₀))) — R²=1.00
2. **Mort**: gap spectral 1/λ₁ × ratio = 8.1 ans — MAE=1.79 ans, 0 paramètre
3. **Portée R_max**: dépend de la mare (median_neighbor_works), pas du caillou
4. **Amplitude front**: onde de surface A₀/√t × exp(-αt) — R²=0.82

Scripts: `scripts/wave_comprehensive_test.py`
Résultats: `data/results/wave_comprehensive_test.json`

---

## 11. MODÈLE PRÉDICTIF — Prédire K, r, t₀ depuis la mare

### K (portée) — PASS (±11%)

Ridge regression LOO 13-fold sur 13 features mare.
Meilleur prédicteur: `median_neighbor_works` (ρ=+0.60, p=0.029).

### r (vitesse) — PARTIAL (±31%)

Meilleur prédicteur: `1/n_seeds` (ρ=+0.60).
**Interprétation physique**: un caillou pointu (1 seed) perce plus vite qu'un caillou large (3 seeds).
La concentration de l'énergie initiale détermine la vitesse.

### t₀ (timing inflexion) — PARTIAL (±33%)

Meilleur prédicteur: `n_seeds` (ρ=+0.66, p=0.015).
Plus de seeds = inflexion plus tardive (énergie diluée = montée lente).

### Formule prédictive candidate (C2 — à valider)

```
K ≈ Ridge(mare_features)           [±11%, PASS]
r ≈ a / n_seeds + b                [±31%, C2]
t₀ ≈ c × n_seeds + d              [±33%, C2]
death ≈ 1/λ₁ × ratio = 8.1 ans    [MAE=1.79, PASS]
```

### Gödel hold-out
- K prédit à 17% (OK)
- r et t₀ faux → trajectoire R² = -0.38 (FAIL)
- Le timing de Gödel (t₀=4.55) est anomal — l'onde met 4 ans avant de décoller

### Carmack moves découverts

| Paire | Score | z | Status |
|-------|-------|---|--------|
| seismology × epidemic | 321.6 | -2.29 | DÉSERT |
| heat_kernel × cascade | 116.3 | -0.96 | DÉSERT |
| cognitive_psych × scale_free | 75.1 | -0.69 | DÉSERT |

Scripts: `scripts/wave_predictive_model.py`, `scripts/wave_predictive_search.py`
Résultats: `data/results/wave_predictive_model.json`, `data/results/wave_predictive_search.json`
