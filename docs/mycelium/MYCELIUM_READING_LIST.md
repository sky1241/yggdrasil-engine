# MYCELIUM — LISTE DE LECTURE
# Winter Tree v2 : la forêt, pas les arbres
# 15 février 2026, 3h du mat, après une bière et de la rage

---

## LES 5 PAPIERS (tous gratuits)

### 1. LES FORMULES DU BAS — Neighbour-Sensing Model
**Meškauskas & Moore, 2004** — Université de Manchester
- Chaque hyphe génère un champ, chaque tip "sent" ses voisins
- 4 propriétés par tip : position 3D, vecteur croissance, longueur, branchement
- L'intelligence émerge du comportement de foule des tips
- PDF : https://markfricker.org/wp-content/uploads/2015/12/meskuaskas_et_al-2004-mycol_res-108-1241.pdf

### 2. LA CARTE DU TERRITOIRE — Question of Scale
**Davidson, 2007** — le papier qui unifie les 3 échelles
- Micro (1 hyphe) → Méso (colonie) → Macro (réseau)
- Les propriétés à chaque échelle émergent de l'échelle précédente
- Personne a encore fait le modèle unifié multi-scale
- PDF via ResearchGate : https://www.researchgate.net/publication/222562719

### 3. LE COMPUTER FONGIQUE — Towards Fungal Computer
**Adamatzky, 2018** — Royal Society (open access)
- Information = spikes électriques
- Calcul = réseau de mycelium
- Interface = fruit bodies (champignons)
- Transfert d'information à distance entre champignons
- PDF : https://royalsocietypublishing.org/doi/10.1098/rsfs.2018.0029

### 4. LES CIRCUITS LOGIQUES — Mining Logical Circuits in Fungi
**Adamatzky, 2022** — Nature Scientific Reports (open access)
- Le mycelium implémente des circuits booléens
- La GÉOMÉTRIE du réseau détermine les fonctions calculées
- Premier prototype de reservoir computer fongique
- PDF : https://www.nature.com/articles/s41598-022-20080-3.pdf

### 5. LES CHIPS PHYSIQUES — Mycelium Chips for Reservoir Computing
**bioRxiv, août 2025** — preprint gratuit
- Vrais chips physiques en mycelium
- Workflow : "design-grow-compute"
- La complexité morphologique influence la capacité de calcul
- PDF : https://www.biorxiv.org/content/10.1101/2025.08.20.671348v1.full.pdf

---

## LES 3 ÉCHELLES (complémentaires, pas dissociables)

```
MICRO  — Neighbour-Sensing (Meškauskas 2004)
         1 tip, 1 champ, comportement individuel
         Variables : position, vecteur, branchement
              |
              | les tips produisent le réseau
              v
MÉSO   — Hybride discret-continu (Boswell 2003-2008)
         La colonie : hyphes actives + inactives + tips
         Nutriments internes/externes, Michaelis-Menten
         Transport : diffusion + advection vers les tips
              |
              | le réseau produit la topologie
              v
MACRO  — Topologie small-world (Tompris et al. 2025)
         Clustering élevé + chemins courts
         = même topologie que réseaux neuronaux et internet
         → reservoir computing, 97% MNIST
```

## LE PONT WINTER TREE

```
v1 = L'ARBRE    (méso — un projet, ses nœuds, ses niveaux)
v2 = LE MYCELIUM (micro — les connexions entre projets)
v3 = LA FORÊT    (macro — la topologie qui émerge)
```

Le v2 c'est pas juste "connecter les arbres".
C'est formaliser comment les tips (repos) sentent leurs voisins (docs partagées),
comment les nutriments (connaissances) circulent entre hyphes actives et inactives,
et pourquoi la forme du réseau détermine ce qu'il peut calculer.

---

## AUSSI CITÉ DANS TON README P=NP

- **Socha & Dorigo 2008 (ACOR)** — colonies de fourmis pour domaines continus
  → phéromones = tes LESSONS_LEARNED
  → pas de chef central, intelligence émergente

- **Lindenmayer 1968 (L-Systems)** — grammaire de croissance biologique
  → graine + règles simples = arbre complet
  → exactement le principe du Winter Tree plant mode

---

## LIVRE COMPLET (payant mais référence ultime)

**"Fungal Machines: Sensing and Computing with Fungi"**
Adamatzky, 2023, Springer
→ Le livre qui compile tout. Si un jour t'as 50€ à mettre.

---

Né d'une nuit de rage, de bière, et de racines.
