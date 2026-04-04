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

## 8. RÉSUMÉ — QUEL MODÈLE UTILISER

| Modèle | Paramètres à fitter | Données nécessaires | On a ? |
|--------|--------------------|--------------------|--------|
| **Heat kernel** | 0 (juste t) | Laplacien WT4 | ✅ OUI |
| Onde de surface | 2 (v, alpha) | BFS per-year WT3 | ✅ OUI (6/13) |
| SIR | 2 (beta, gamma) | Adjacence + temporal | ✅ OUI |
| Galton-Watson | 0 (mesuré) | BFS per-year WT3 | ✅ OUI (6/13) |
| Sedov-Taylor | 2 (beta, alpha) | ~~frames globales~~ | ❌ INVALIDÉ |

**Recommandation**: heat kernel en premier (0 param, on a tout). Comparer avec les BFS mesurés.
