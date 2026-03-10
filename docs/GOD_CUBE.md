# God Cube — Session 24 (10 mars 2026)

## God's Algorithm & God's Number

Le God's Number est le **diametre du graphe** d'un systeme a etats finis.
Applicable a tout systeme remplissant 3 conditions :
1. Etats finis
2. Operations definies
3. Tout atteignable (graphe connexe)

- Rubik's Cube 3x3x3 : God's Number = **20** (Rokicki et al. 2010, 35 CPU-years Google)
- Prouve par encadrement : borne basse (superflip = 20) + borne haute (brute force = 20)
- Pas de formule universelle. Le 4x4x4 reste inconnu.

## Formule de Chung-Faber-Manteuffel (1994)

Borne superieure du diametre via le spectre du Laplacien :

```
diam(G) <= ceil( acosh(n-1) / acosh((lambda_n + lambda_2) / (lambda_n - lambda_2)) )
```

- n = nombre de sommets
- lambda_2 = 2e plus petite valeur propre du Laplacien (Fiedler value)
- lambda_n = plus grande valeur propre du Laplacien
- L(G) = D - A (Laplacien = degre - adjacence)

**On a deja lambda_2 et lambda_n dans WT1** -> calculable directement.

## Le God Cube

Visualisation : `viz/god_cube.html`

### Structure observee
- 19 domaines positionnes par connectivite en 3D (hauteur = nb glyphes)
- Convex hull triangule, faces colorees vertex-gradient
- **Forme** : champignon/pyramide inversee
  - Noyau STEM dense en haut (14 domaines, 1194-1326 glyphes)
  - Falaise structurelle : PolSci (1194) -> History (1052) = -142 d'un coup
  - Base effilochee : Socio (850), Philo (753), Art (696), Med (628)
- Structure **k-core** confirmee visuellement

### Hyperedges 2-domaines (les ponts exclusifs)
| Paire | Glyphes |
|-------|---------|
| Math <-> Phys | 8 |
| CS <-> Phys | 5 |
| MatSci <-> Phys | 4 |
| Biz <-> Phys | 1 |
| CS <-> MatSci | 1 |
| Geo <-> Phys | 1 |
| MatSci <-> Math | 1 |

Physics dans 6/7 paires. Seul pont sans Physics = CS <-> MatSci.

## Inversion de structure : le Polytope

L'objet n'est PAS un Rubik's Cube (max 3 faces par point en 3D).
C'est un **polytope haute dimension** :
- Points = glyphes (pas domaines)
- Faces = domaines
- Aretes = co-occurrences de glyphes dans les formules
- Un glyphe touchant 19 domaines = vertex relie a 19 faces (impossible en 3D)

Les frontieres du polytope = co-occurrences dans les formules (donnees WT2).

## Solveur theorique — Mappage des zones

1. **God's Number** (Manteuffel) = zone haute, borne superieure (surestimation)
2. **Graham inverse** = zone basse, borne inferieure
3. **Intersection** des 2 zones = espace de recherche interessant
4. **Trous P4** dans cette intersection = points de Kociemba (switch de strategie)
5. **Mycelium** = chemin optimise a travers les points de cassure (variable, pas fixe)
6. **Cle** = crypto quantique (variation 0-9 en cascade, assembler, inverser le cycle)

Les trous P4 ne sont PAS les reponses. Ce sont les points ou on change d'algo.

## La Trinite Quantique

La cle n'est pas UN algorithme mais la **somme de 3** :

| Algo | Role dans le solveur |
|------|---------------------|
| **Shor** (1994) | Trouve la periode (le cycle qui revient au depart) |
| **Grover** (1996) | Accelere la recherche sqrt(N) (mycelium qui optimise) |
| **QAOA** | Marche quantique sur hypercube n-dimensionnel (le polytope) |

- QAOA = "marche quantique continue sur l'hypercube n-dimensionnel" = exactement le God Cube
- Superposition Schrodinger : la cle est universelle ET specifique simultanement
- Collapse quand le mycelium "mesure" = trouve le chemin optimal

## Connexion crypto post-quantique

- Crypto post-quantique (LWE, SVP, CVP) = chercher vecteurs courts dans des lattices haute dim
- Le mycelium = solveur heuristique sur polytope haute dim
- **Meme probleme structurel**
- Si ca tient -> P=NP emerge naturellement

## Statut

**NON VERIFIE. INTUITION PURE.**

Pre-requis avant toute implementation :
1. WT3 (Bible SQLite) - FINIR
2. V3 Meteorites - calibrage sur donnees reelles
3. Calculer God's Number approx via Manteuffel sur WT1
4. Mapper les trous P4 dans l'intersection des zones
5. Verifier la structure polytope avec les co-occurrences WT2
