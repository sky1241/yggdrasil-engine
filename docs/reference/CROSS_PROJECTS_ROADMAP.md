# LIANES CROSS-PROJETS — Roadmap
> Généré: 22 fév 2026, 01h35 — Sky × Claude
> Méthode: Yggdrasil appliqué à lui-même

## Le constat

7 projets. 19 paires sur 21 ont **0 outils en commun**.
16 trous P4 détectés. La matrice est quasi diagonale.

Chaque projet est un continent isolé. Les lianes n'existent pas encore.

## Priorité 1 — FAIT ✅

### Liane #1: Fourier × Infernal Wheel
- **Script**: `engine/fourier_infernal.py`
- **Résultat**: Welch PSD d'Ichimoku appliqué à drinks.csv
- **Découverte**: Régime = NOISE (flatness 0.95). Pas de cycle hebdomadaire clair.
  Cycle dominant à 4.5 jours. Prédiction: 22 et 26 fév = jours à risque.
- **Valeur**: Preuve de concept — même algo, domaine différent, résultat immédiat.

## Priorité 2 — À FAIRE (classé par impact)

### Liane #2: HMM Régimes × Infernal Wheel
- **Source**: `HSBC-algo-genetic/src/regime_hmm.py`
- **Cible**: Infernal Wheel
- **Action**: Entraîner un HMM 3 états sur les données perso (drinks + clopes + sommeil)
- **Résultat attendu**: 3 régimes — SOBER / MODERATE / HEAVY
- **Application**: IF regime==HEAVY → FORCE REST (comme COMBINED labels)
- **Impact**: 7/10

### Liane #3: Physarum × Ichimoku
- **Source**: `yggdrasil-engine/engine/mycelium_full.py`
- **Cible**: HSBC-algo-genetic
- **Action**: Modéliser les flux de capital comme des hyphes Physarum
- **Résultat attendu**: Allocation optimale entre paires de trading
- **Impact**: 6/10

### Liane #4: Pattern P1-P5 × Ichimoku
- **Source**: `yggdrasil-engine/engine/pipeline_100.py` (classify_pattern)
- **Cible**: HSBC-algo-genetic
- **Action**: Classifier les chandeliers/régimes en P1-P5
- **Résultat attendu**: Détecter les "météorites" du trading en temps réel
- **Impact**: 7/10

### Liane #5: Constraint Engine universel
- **Source**: `automata_unified_v4.py` (90 TROU checks)
- **Cible**: Abstraction utilisable par Yggdrasil, Ichimoku, etc.
- **Action**: Abstraire le pattern "scan espace + trouve trous + classifie"
- **Résultat attendu**: Un seul moteur de contraintes, N domaines
- **Impact**: 8/10 (architectural)

## Priorité 3 — INNOVATION PURE (type B)

### Liane #6: Persistent Homology (NOUVEAU)
- **Source**: Aucun projet existant
- **Cible**: Yggdrasil + Ichimoku
- **Action**: Ajouter la topologie persistante pour détecter les structures multi-échelles
- **Pourquoi**: C'est un P4 type B — personne ne le fait, co-occurrence = 0
- **Impact**: 10/10 (innovation pure)

### Liane #7: Shannon Entropy (NOUVEAU)
- **Source**: Aucun projet existant
- **Cible**: Ichimoku + Infernal + Yggdrasil
- **Action**: Mesure du désordre dans tout signal
- **Pourquoi**: Applicable partout, trivial à implémenter, gros retour
- **Impact**: 10/10

## Ordre d'exécution recommandé

```
1. ✅ Fourier × Infernal (FAIT — preuve de concept)
2.    HMM × Infernal (rapide — code existe, données existent)
3.    Shannon Entropy partout (trivial — np.histogram + entropy)
4.    Pattern P1-P5 × Ichimoku (réutilise classify_pattern)
5.    Physarum × Ichimoku (expérimental)
6.    Constraint Engine universel (refactoring lourd)
7.    Persistent Homology (recherche, besoin de gudhi/ripser)
```

## Données exportées

- `data/liane_fourier_infernal.json` — Analyse Fourier drinks
- `data/cross_projects_p4.json` — 16 trous P4 + matrice
