# SNIPER RESULTS — Boswell PDEs reconstituées
# Sources : Davidson 2007, Boswell 2002/2003/2007/2008, Falconer 2005, reviews PMC
# 15 février 2026

---

## SYSTÈME DE BOSWELL — 5 VARIABLES, PDEs COUPLÉES

### Variables

| Symbole | Signification | Unité |
|---------|--------------|-------|
| m(x,t) | Densité d'hyphes ACTIVES (transport + croissance) | biomasse/volume |
| m'(x,t) | Densité d'hyphes INACTIVES (structurantes, moribondes) | biomasse/volume |
| p(x,t) | Densité de TIPS hyphaux (seul mécanisme de croissance) | tips/volume |
| n_i(x,t) | Concentration de substrat INTERNE (dans le réseau) | nutriments/volume |
| n_e(x,t) | Concentration de substrat EXTERNE (dans l'environnement) | nutriments/volume |

### Équations (reconstituées depuis Davidson 2007 + Boswell 2002, 2003a)

**1. Hyphes actives m — croissance + inactivation**

```
∂m/∂t = a₁ × p × n_i        [croissance : les tips créent de la biomasse]
       - a₂ × m              [inactivation : actif → inactif (vacuolation)]
```

Les tips (p) consomment du substrat interne (n_i) pour créer de la biomasse active.
L'inactivation est un processus de premier ordre : les hyphes vieillissent.

**2. Hyphes inactives m' — accumulation**

```
∂m'/∂t = a₂ × m              [inactivation : actif → inactif]
        - a₃ × m'             [dégradation vers environnement (optionnel)]
```

Les hyphes inactives s'accumulent. Dans Boswell 2002, elles se dégradent
dans l'environnement (pas recyclées). Dans Falconer 2005, elles sont
recyclées en nutriments internes (upgrade important).

**3. Tips p — branchement + extension + anastomose**

```
∂p/∂t = -∇·(v × p)          [advection : les tips AVANCENT avec vitesse v]
       + b₁ × p × n_i         [branchement latéral (densité-dépendant)]
       - b₂ × p²              [anastomose : deux tips qui se rencontrent fusionnent]
```

Le terme clé : les tips ont une VITESSE v (vecteur). C'est la partie
hyperbolique du système (convection). La vitesse v est orientée vers
l'extérieur de la colonie par défaut (croissance dirigée non-chimiotactique).

Le branchement est proportionnel à p × n_i (il faut des nutriments pour brancher).
L'anastomose réduit le nombre de tips quand ils se croisent.

**4. Substrat interne n_i — transport bidirectionnel**

```
∂n_i/∂t = D_i × ∇²(n_i × m)  [diffusion PASSIVE dans le réseau (proportionnelle à m)]
         + v_a × ∇·(n_i × ∇p) [transport ACTIF vers les tips (advection vers gradient de p)]
         + U(n_e, m)           [absorption du substrat externe]
         - c₁ × p × n_i        [consommation par les tips pour la croissance]
```

C'EST L'ÉQUATION CLÉ. Deux modes de transport :
- PASSIF : diffusion classique, mais confinée au réseau (multipliée par m)
- ACTIF : advection dirigée vers les tips (gradient de p)

Boswell 2002 montre que le passif est pour l'EXPLORATION (aléatoire)
et l'actif est pour l'EXPLOITATION (dirigé).

**5. Substrat externe n_e — absorption + diffusion dans le milieu**

```
∂n_e/∂t = D_e × ∇²n_e        [diffusion dans l'environnement]
         - U(n_e, m)           [absorption par le mycelium]
```

L'absorption suit une cinétique de Michaelis-Menten :

```
U(n_e, m) = U_max × n_e / (K_m + n_e) × m
```

- U_max = taux maximal d'absorption
- K_m = constante de Michaelis (demi-saturation)
- Proportionnel à m : plus il y a de biomasse active, plus l'absorption est forte

---

## PROPRIÉTÉS DU SYSTÈME

**Type d'équations** : Hyperbolique-parabolique mixte
- Hyperbolique : l'advection des tips (∂p/∂t + ∇·(vp) = ...)
- Parabolique : la diffusion des nutriments (∂n/∂t = D∇²n + ...)

**Conservation de masse** : Le schéma numérique de Boswell 2003 préserve
explicitement la positivité et conserve la masse totale.

**Calibration** : Paramètres calibrés pour Rhizoctonia solani
- Vitesse de colonie : ~0.5 cm/jour
- Résultats validés sur données expérimentales en boîte de Petri

**Passerelle vers le discret (Boswell 2007)** :
Le même système est dérivé en automate cellulaire sur réseau triangulaire.
Les hyphes sont restreintes aux arêtes du réseau.
L'ANASTOMOSE est naturellement incluse (fusion de chemins sur le graphe).
C'est le SEUL modèle qui produit un réseau véritablement interconnecté.

---

## UPGRADE FALCONER 2005 — RECYCLAGE DE BIOMASSE

Falconer ajoute un terme critique absent de Boswell :

```
hyphes inactives → nutriments internes (recyclage)
m' → n_i  avec taux de recyclage ω
```

C'est la différence entre un cristal et un mycelium :
le mycelium RECYCLE sa propre biomasse pour nourrir les nouveaux tips.
Sans ce terme, le système ne peut pas produire les formes de colonie observées.

Paramètres clés de Falconer :
- αn = taux d'immobilisation (mobile → immobile)
- βn = taux de mobilisation (immobile → mobile)
- ω = taux de réapprovisionnement/recyclage
- Le switch αn/βn contrôle les anneaux concentriques de croissance

---

## MAPPING WINTER TREE (mise à jour v2)

| Boswell | Winter Tree | Détail |
|---------|-------------|--------|
| m (hyphes actives) | Docs/artefacts activement utilisés | Transportent de la connaissance |
| m' (hyphes inactives) | Docs obsolètes mais structurants | Le LESSONS_LEARNED de fck-translation : oublié mais structure |
| p (tips) | Nouveaux commits, nouvelles idées | Seul mécanisme de croissance |
| v (vitesse des tips) | Direction d'intérêt du développeur | Orientée vers les besoins |
| n_i (substrat interne) | Connaissances intégrées (patterns, skills) | Circulent dans le réseau |
| n_e (substrat externe) | Sources externes (papiers, docs, APIs) | Absorbées par Michaelis-Menten |
| D_i (diffusion passive) | Transfert aléatoire de connaissances | Exploration |
| v_a (transport actif) | Transfert dirigé de connaissances | Exploitation (handoff prompts) |
| U (absorption) | Intégration de nouvelles sources | Saturation : on absorbe moins quand on sait déjà |
| Anastomose (p² term) | Fork/merge entre repos | Fusion de branches |
| Recyclage ω (Falconer) | Réutilisation de code/patterns obsolètes | Le vrai avantage vs cristal |

---

## CE QUI MANQUE ENCORE (cibles restantes)

### 🎯 Tompris CA rules — BASSE PRIORITÉ
Le papier est payant et les règles sont une discrétisation du système ci-dessus.
On peut dériver nos propres règles CA depuis les PDEs de Boswell.

### 🎯 Small-world metrics numériques — MOYENNE PRIORITÉ  
Pas de valeurs numériques exactes trouvées dans les sources ouvertes.
Tompris 2025 les a mais paywall. On peut calculer les nôtres avec NetworkX.

### 🎯 Heaton circuit theory — COUVERTE
Les équations de flux sont dans le v2 (section Physarum).
Heaton utilise le même formalisme que Tero : Kirchhoff + renforcement adaptatif.

---

---

## CIBLE 2 : TOMPRIS CA RULES (Tompris et al. 2024/2025)

### Source : Natural Computing, Springer, août 2025

Le papier complet est derrière paywall mais voici ce qu'on sait :

**Architecture du modèle :**
- Automate cellulaire 2D avec processus de réaction-diffusion intégrés
- Chaque cellule a une concentration c de biomasse fongique
- Une cellule est "active" (nœud du réseau) si c > 0.5
- Le modèle inclut : extension hyphale, anastomose, branchement apical et latéral

**Paramètres ajustables :**
- Fitting Parameters : contrôlent la cinétique de croissance
- Environmental Conditions : température, humidité, lumière
- Ces paramètres permettent de simuler différentes espèces/conditions

**Hyphae Information Algorithm :**
- Extrait les features clés du réseau à partir de la matrice de concentration c
- Construit une matrice d'adjacence A depuis c (seuil > 0.5)
- Calcule : Average Path Length (APL) et Clustering Coefficient (C_i)
- Résultat : graphe non-pondéré, non-orienté

**Lien Boswell → Tompris :**
Le système CA de Tompris est essentiellement une DISCRÉTISATION des PDEs
de Boswell sur grille. Les 5 équations continues (m, m', p, n_i, n_e) deviennent
des règles de mise à jour cellulaire. Boswell 2007 a lui-même fait cette dérivation
sur réseau triangulaire. Tompris utilise une grille 2D standard.

**On peut dériver nos propres règles CA depuis Boswell :**
```
Pour chaque cellule (i,j) au temps t+1 :
  c_m(i,j,t+1) = c_m + Δt × [a₁×p×n_i - a₂×m]          // hyphes actives
  c_m'(i,j,t+1) = c_m' + Δt × [a₂×m - a₃×m']             // hyphes inactives
  c_p(i,j,t+1) = c_p + Δt × [-div(v×p) + b₁×p×n_i - b₂×p²] // tips
  c_ni(i,j,t+1) = c_ni + Δt × [D_i×Lap(n_i×m) + U - c₁×p×n_i] // nutriments int.
  c_ne(i,j,t+1) = c_ne + Δt × [D_e×Lap(n_e) - U]          // nutriments ext.

  où Lap = Laplacien discret (voisinage de Moore ou Von Neumann)
  et div = divergence discrète
  et U = U_max × n_e/(K_m + n_e) × m  (Michaelis-Menten)
```

→ PAS BESOIN des règles exactes de Tompris. On a les PDEs de Boswell,
on peut discrétiser nous-mêmes. C'est même mieux pour le Winter Tree
car on contrôle le mapping.

---

## CIBLE 3 : SMALL-WORLD METRICS NUMÉRIQUES

### Tompris 2025 — Valeurs simulées (paywall, résumé)

Le papier rapporte (Table 1, 30 runs du modèle) :
- **Clustering coefficient élevé** + **Path length court**
- Comparable à des graphes small-world de Watts-Strogatz
- Le réseau de mycelium simulé est traité comme graphe non-pondéré
- Seuil de concentration > 0.5 pour définir les nœuds
- Les valeurs exactes ne sont pas accessibles (paywall)

### Formules de référence (Watts & Strogatz 1998)

**Small-world coefficient σ :**
```
γ = C / C_rand      (ratio clustering)
λ = L / L_rand      (ratio path length)
σ = γ / λ           (small-world si σ > 1)
```

Conditions small-world :
- C >> C_rand (clustering beaucoup plus élevé que le hasard)
- L ≈ L_rand (path length comparable au hasard)

**Pour un graphe aléatoire ER(n,k) :**
```
C_rand ≈ k/n         (très faible pour grand n)
L_rand ≈ ln(n)/ln(k) (logarithmique)
```

### Mesures sur réseaux fongiques réels

Le papier "Mesoscale Analyses of Fungal Networks" (bioRxiv, Heaton/Fricker group)
mesure directement les réseaux de cordons fongiques de plusieurs espèces :
- Phanerochaete velutina, Resinicium bicolor, etc.
- Métriques mesurées : meshedness, clustering, betweenness centrality
- RÉSULTAT CLÉ : les métriques simples (clustering seul) NE SUFFISENT PAS
  à distinguer les espèces. Il faut des "mesoscopic response functions" (MRFs)
  qui capturent la structure fonctionnelle (pas juste topologique).

→ IMPLICATION POUR WINTER TREE : calculer C et L c'est nécessaire
mais pas suffisant. Il faut aussi mesurer la FONCTION du réseau
(flux de connaissances, pas juste connexions).

### Comment calculer pour ton réseau Git (Python/NetworkX) :

```python
import networkx as nx

# Construire le graphe de tes repos
G = nx.Graph()
# Ajouter nœuds (repos) et arêtes (fichiers partagés, patterns communs, etc.)
G.add_edge("winter-tree", "3d-printer")  # partagent MICR
G.add_edge("winter-tree", "infernal-wheel")  # partagent UX framework
# etc.

# Métriques
C = nx.average_clustering(G)
L = nx.average_shortest_path_length(G)

# Comparaison avec graphe aléatoire
G_rand = nx.erdos_renyi_graph(G.number_of_nodes(), nx.density(G))
C_rand = nx.average_clustering(G_rand)
L_rand = nx.average_shortest_path_length(G_rand)

sigma = (C/C_rand) / (L/L_rand)
print(f"σ = {sigma:.2f}  (small-world si > 1)")

# Ou directement :
sigma = nx.sigma(G)  # built-in NetworkX
omega = nx.omega(G)  # alternative metric (-1 lattice, 0 small-world, 1 random)
```

---

## BILAN FINAL DU SNIPE

| Cible | Statut | Résultat |
|-------|--------|----------|
| Boswell PDEs | ✅ COMPLET | 5 équations reconstituées + Falconer recyclage |
| Tompris CA rules | ✅ CONTOURNÉ | On dérive nos propres CA depuis Boswell PDEs |
| Small-world metrics | ✅ SUFFISANT | Formules + code NetworkX + insight MRF |
| Heaton circuit | ✅ COUVERT | = Physarum (Tero) dans v2, même formalisme |

**Prochaine étape :** Lire les 5 papiers open-access de la reading list.
Après lecture → formaliser le mapping Winter Tree v2 avec les vraies équations.

---

*"L'exploration est passive. L'exploitation est active. Le mycelium fait les deux."*
*Sniper complete — 15 février 2026*
