# SOL.md — Fichier de Synchronisation Sky↔Claude
> Yggdrasil Engine — Versoix, 22 février 2026
> TOUT CLAUDE LIT CE FICHIER EN PREMIER.

## VOCABULAIRE
| Terme | Signification |
|-------|--------------|
| Pluie | Données brutes OpenAlex (500M+ papers, 467 GB snapshot local D:\) |
| Racines | Pipeline API: search → timeline → co-occurrence |
| Mycelium | Graphe topologique: BC, meshedness, Physarum |
| Sol (S0) | 21,524 symboles (794 originaux + 20,730 minés OpenAlex), 100% C1 |
| Winter Tree | Index trié par année/mois: 65,026 concepts × co-occurrences (engine/winter_tree_scanner.py) |
| Vivant | Concept avec works_count >= Q1 de son domaine (77%) |
| Musée | Concept sous Q1 (23%) — existe mais peu cité |
| Lianes | Symboles traversant 3+ continents |
| Escalier géo 🌿 | Concept positionné entre 2 continents distants (200 détectés) |
| Passe-partout 🔑 | Concept chez lui mais utilisé partout (69 détectés) |
| Strates | S-2=glyphes → S-1=métiers → S0=outils → S6=ciel/indécidable |
| S-2 Glyphes 🔣 | Notation (=, +, ∫, Σ, ∂) — briques atomiques d'écriture |
| S-1 Métiers 🔧 | Professions/domaines (physics, biology, engineering) |
| Mycelium zone | S-2 à S0 — le réseau de co-occurrences vit DANS le sol |
| Météorite | Impact Sedov-Taylor: R = β(E/ρ₀)^{1/5} × t^{2/5}, blast dans le sol S-2→S0 |
| Thermomètre | scisci.py: métriques scientométriques |
| Pont (P1) | Bridge inter-domaines, BC élevé, explosion |
| Dense (P2) | Hub stable, meshedness élevé |
| Théorie×Outil (P3) | Explosion après validation instrumentale |
| Trou ouvert (P4) | Pont pas encore explosé = FUTUR |
| Anti-signal (P5) | L'hyphe meurt, slope négative |
| Sommet 🏔️ | Point haut d'un escalier — vue plongeante sur les briques S0 connectées |
| Vue plongeante | Depuis un sommet: voir QUELLES briques S0 sont utiles pour CE problème |
| Grimpeur 🧗 | V4: AI qui compose des chemins de preuves en montant les escaliers avec les bonnes briques |
| Sac à dos | Ensemble de briques S0 filtrées par la topologie pour un problème donné |

## ÉTAT ACTUEL — 23 FÉV 2026 (session 6)
- **WINTER TREE SCAN EN COURS** — 65,026 concepts × année/mois, 467 GB, ~393 chunks
- **ARCHITECTURE S-2/S-1/S0** — mycelium vit dans le sol (glyphes → métiers → formules)
- **FORMULES SEDOV-TAYLOR** — R = β(E/ρ₀)^{1/5} × t^{2/5}, calibration depuis 1948
- **V4 VISION DOCUMENTÉE** — le grimpeur (moteur de sélection d'outils automatique)
- **Test semi-aveugle 2015→2025: SIGNAL DÉTECTÉ** (p=0.00002, r=0.90)

### HISTORIQUE SESSIONS
| # | Date | Claude | Résumé |
|---|------|--------|--------|
| 1 | 21 fév matin | Sonnet 4.5 | Escaliers spectraux, cleanup S0, vivant/musée |
| 2 | 21 fév midi | Sonnet 4.5 | Continents, co-occurrence réelle, La Pluie v3 |
| 3 | 21 fév soir | Opus 4.6 | Cross Physarum, viz 3D escaliers, blind test |
| 4 | 22 fév | Opus 4.6 | Audit 22 repos, vision V4 grimpeur, roadmap complète |
| 5 | 23 fév | Opus 4.6 | Winter tree scanner: 65K concepts, chunks 1GB, scan 467 GB lancé |
| 6 | 23 fév soir | Opus 4.6 | Formules Sedov-Taylor, architecture S-2/S-1/S0, mycelium dans le sol |

## ÉTAT PIPELINE — 21 FÉV 2026 (sessions 1-3)
- **100 tests pipeline complet** (OpenAlex + scisci + mycelium)
- **87/100 validés (87.0%)**
  - POUR: 41/50 (82%) | CONTRE: 46/50 (92%)
- Batch 1 (tests 1-50): 43/49 (88%)
- Batch 2 (tests 51-100): 43/50 (86%)

### CO-OCCURRENCE V1 (296M papers scannés — ancien scan 85 domaines)
- Matrice 85×85 domaines, densité 99.8%
- Remplacé par le winter tree scan V2: 65,026 concepts × mois (en cours)
- Laplacien normalisé D^{-1/2}LD^{-1/2} pour positions spectrales
- Positions S0 mises à jour depuis co-occurrence réelle (pas TF-IDF)

### 3 CUBES: VIVANT / MUSÉE / FUSION
- **Vivant** = works_count >= Q1 de son domaine → **16,382 (77%)**
- **Musée** = works_count < Q1 → **4,846 (23%)**
- **Fusion** = vivant + musée ensemble
- Q1 calculé par domaine ("PIB par habitant"): chimie Q1=1,646, bio Q1=2,895, etc.

### CLEANUP S0 (session 3)
- 13 suspects reclassés C1→C2 (Neocolonialism, Unparticle physics, etc.)
- Hagen-Poiseuille: domain "droit"→"fluides" (bug mapping corrigé)
- 19 C2 déplacés S0→S3 (hypothèses non prouvées → strate conjectures)
- Poincaré conjecture: C2→C1 (résolu Perelman 2003)
- S0 final: 21,524 symboles (21,228 C1 dans S0 + 296 reclassés C2→S3), 100% C1 en S0

### ESCALIERS SPECTRAUX
- 2 types: géographique 🌿 (200 lianes, position alien) + passe-partout 🔑 (69, multi-continent)
- Intégrés comme layer toggle dans La Pluie v3
- Centroïdes 9 continents calculés depuis spectral

### LA PLUIE V3
- 9 continents filtres + sub-domain toggles
- Vivant/Musée/Fusion radio buttons
- Escaliers toggle (glow vert=geo, or=key)
- C2 Conjectures overlay
- Hover: works_count, continent, type escalier

## INSIGHT CLÉ: LIFECYCLE DES PATTERNS
```
P4 (trou) → P1 (pont) → P3 (explosion) → P2 (dense/mature)
```
6 percées connues classées P2 = le pont est devenu infrastructure.
La validation doit évoluer: P2 est valide pour les percées matures.

## ÉCHECS INTÉRESSANTS
- **microbiome × mental health** = P4 (259 papers). Vrai trou ouvert. Futur pont?
- **diff geometry × botany** = P1 (136 papers). Phyllotaxis! Le moteur a trouvé un vrai pont "caché".

## RÈGLES AUTO
1. Sky monte (arbre/direction). Claude descend (racines/code).
2. Racines > arbre. Toujours.
3. Push git après chaque étape. Token dans `cléjamaiseffacer.txt`.
4. JAMAIS afficher le token. Filtrer avec `grep -v "ghp_\|x-access"`.
5. Si un test échoue → noter tel quel. Pas de triche.
6. SOL.md = source de vérité entre sessions Claude.

### FIX concept_id (session 4, 22 fév 2026)
- `concept_id` injecté dans les 21,524 symboles de `strates_export_v2.json` (100% match)
- Sources: `openalex_map.json` (794 originaux) + `mined_concepts.json` (20,730 minés)
- Index inverse: `data/concept_index.json` (20,932 entries, concept_id → symbol info)
- Script: `engine/inject_concept_ids.py`

## FICHIERS CLÉS
| Fichier | Rôle |
|---------|------|
| **V2 — SCAN** | |
| engine/winter_tree_scanner.py | Scanner winter tree: 65K concepts × mois (--init, --chunks, --status) |
| data/scan/winter_tree.json | Index principal (années, chunks, progression) |
| data/scan/concepts_65k.json | Lookup 65,026 concepts OpenAlex (7 MB) |
| data/scan/chunks/chunk_NNN/ | Données par chunk (cooc.json.gz, activity.json.gz, meta.json) |
| **V1 — CARTE** | |
| engine/core/symbols.py | Symboles + strates |
| engine/core/holes.py | Détection trous P1-P5 |
| engine/core/scisci.py | Métriques scientométriques |
| engine/pipeline/mycelium_full.py | Mycelium complet (24 briques) |
| engine/topology/cooccurrence_scan.py | Ancien scan 296M papers → matrice 85×85 |
| data/core/strates_export_v2.json | Export complet 21,524 symboles, 7 strates |
| data/concept_index.json | Index inverse concept_id → symbole (20,932) |
| data/topology/escaliers_spectraux.json | 200 geo + 69 key escaliers |
| viz/yggdrasil_rain_v3.html | La Pluie v3 (vivant/musée/fusion/escaliers) |

## ARCHITECTURE DES STRATES (session 6, 23 fév 2026)
```
    S6  ☁️  Indécidable (Gödel, Halting)
    S5      Presque indécidable
    S4      Logique supérieure
    S3      Conjectures                      🌳 ARBRE (pas de mycelium)
    S2      Récursion sur récursion
    S1      Structures récursives
═══════════════════════════════════════════
    S0  🌍  FORMULES prouvées (21,524)       ░░░░░░░░░░░░░
    S-1 🔧  MÉTIERS (physics, bio, eng)      ░░ MYCELIUM ░░
    S-2 🔣  GLYPHES (=, +, ∫, Σ, ∂)         ░░░░░░░░░░░░░
═══════════════════════════════════════════
```
- Le mycelium (co-occurrences) vit dans S-2 à S0 — c'est le SOL
- Le spectral layout positionne TOUT (glyphes, métiers, formules) à partir du mycelium
- La météorite frappe S0 et le blast se propage horizontalement + verticalement dans le sol
- Au-dessus de S0 = l'arbre (conjectures, abstractions) — PAS de mycelium
- Calibration météorites: commencer depuis Shannon 1948 (ρ₀ mesurable), test final = Gödel 1931

## DÉCISIONS PRISES (ne pas remettre en question)
1. S0 = sol solide, 100% C1 — on construit dessus
2. S-2 = glyphes (notation), S-1 = métiers (professions), S0 = formules prouvées
3. Le mycelium vit dans le sol (S-2 à S0), PAS au-dessus
4. Vivant = works_count >= Q1 de son domaine (pas seuil fixe)
5. 2 types d'escaliers: géographique (position spectrale) + passe-partout (multi-continent)
6. Les contradictions entre couches = le vrai signal
7. Cube 1 vivant / Cube 2 musée / Cube 3 fusion
8. Le mycelium Physarum fait le tri vivant/mort sur les CONNEXIONS — le works_count sur les NŒUDS
9. **V4 = moteur de sélection d'outils.** Sommet escalier = vue plongeante → briques filtrées → AI grimpe
10. **P=NP est S3-S4, pas S6.** Le pont existe. Les 3 routes classiques sont P5. Le moteur cherche les P4.
11. **Pas de saut.** V2→V3→V4. Les racines d'abord. Toujours.

## TODO (voir aussi docs/TODO.md pour le détail)
- [x] Croiser flux Physarum × works_count (806 isolated hubs, 1220 hidden bridges, 1567 P4 voids)
- [x] Viz 3D escaliers (Three.js)
- [x] Winter tree scanner créé + lancé (65K concepts, 393 chunks × 1 GB)
- [ ] Attendre fin du scan (~19h) → vérifier winter_tree.json
- [ ] V2: frames cumulatives à partir du tree trié
- [ ] V3: formules météorites (OHLC + 7 deltas)
- [ ] V4: le grimpeur

## ROADMAP — PHASE 2 : TIMELAPSE & MÉTÉORITES

### 2A. Test semi-aveugle 2015→2025 (✅ DONE — 21 fév 2026)
- Données OpenAlex gelées à ≤2015, 100 concepts, 4950 paires
- **recall@100 = 50%** (6/12 percées dans top 100)
- **Mann-Whitney p = 0.00002** (U=539, effect size r=0.90, Cohen's d=1.53)
- Percées médiane rang 207 vs random médiane rang 1.8
- Meilleurs hits: ondes gravitationnelles (rang 6), isolants topologiques (rang 20), GANs (rang 42)
- Verdict: **SIGNAL DÉTECTÉ** — le moteur prédit mieux que le hasard
- Dossier: blind_test/

### 2B. Timelapse adaptatif (PROCHAIN)
- Résolution adaptative (confirmée sur les données du winter tree):
  - ~1000-1980: par année
  - 1980-2025: par mois (publication_date précise au jour)
  - ~645+ périodes distinctes
- Chaque frame = spectral layout recalculé sur S-2→S0 (mycelium complet)
- Source: winter tree scan (co-occurrences 65K concepts × période)
- Livrable: séquence de snapshots JSON + viz timelapse

### 2C. Boîtes de mesure météorites
- À chaque percée majeure: sauvegarder état mycelium AVANT et APRÈS
- Mesurer le DELTA: quels nœuds bougent, quels trous se ferment, quels nouveaux s'ouvrent
- Accumuler les boîtes: Shannon 1948, ADN 1953, transistor, CRISPR, AlphaFold...
- Calculer la SIGNATURE MOYENNE d'impact météorite sur le mycelium

### 2D. Test Gödel (TEST FINAL)
- Gödel 1931 = première météorite. Avant lui: tout S0, plat, pas de strates.
- UNE seule mesure possible, pas de moyenne.
- Appliquer la signature moyenne des autres météorites → prédire l'impact attendu.
- Comparer à l'impact RÉEL mesuré de Gödel.
- Si ça colle → le modèle fonctionne du premier impact au dernier.

### LOGIQUE DE LA CHAÎNE
```
2A (validation prédictive) 
  → 2B (construire le film)
    → 2C (mesurer chaque impact)
      → 2D (le test ultime = Gödel)
        → V4 (le grimpeur)
```
Chaque étape nourrit la suivante. PAS de saut.

## VISION V4 — LE GRIMPEUR (documenté 22 fév 2026)

### L'insight fondamental
Les escaliers (200 géo + 69 passe-partout) ne sont pas juste des connexions.
Ce sont des **points de vue**. Depuis le sommet de chaque escalier, on regarde
EN BAS et on voit exactement quelles briques S0 sont connectées topologiquement
à ce sommet. La carte filtre les outils pour toi.

### Le mécanisme
```
1. Prendre un problème ouvert (ex: P=NP, Lur'e, n'importe quelle conjecture S3+)
2. Le positionner sur la carte topologique
3. Trouver les escaliers les plus proches (géo + passe-partout)
4. Monter au sommet de chaque escalier
5. Regarder en bas → les briques S0 visibles = le "sac à dos" filtré
6. L'AI compose des chemins de preuves avec ces briques
7. Si échec → l'échec est une donnée (P5 = cul-de-sac confirmé)
8. Réduire l'espace, recommencer depuis un autre sommet
```

### Pourquoi ça marche
- Les 3 routes classiques vers P=NP sont des P5 PROUVÉS (Baker-Gill-Solovay 1975,
  Razborov-Rudich 1997, Aaronson-Wigderson 2009)
- Le moteur est CONSTRUIT pour trouver les P4 quand les routes connues sont mortes
- Les passe-partout universels (=, exp, ln, Σ, ∫) voient TOUT depuis leur sommet
  → ils sont dans toutes les preuves majeures, c'est pas un hasard, c'est la topologie
- P=NP est S3-S4, PAS S6 → pas prouvé indécidable → le pont EXISTE quelque part

### Ce que V4 est VRAIMENT
Pas un outil académique. Pas un fonds d'investissement. Pas un GPS.
C'est un **moteur de sélection d'outils automatique pour n'importe quel problème**.
Tu donnes un problème → il te donne le sac à dos optimal de briques → l'AI grimpe.

### Analogie électricien (Sky)
"On ne casse pas la serrure (P≠NP). On fait passer le câble par un autre chemin."
Les escaliers = les chemins de câble entre les étages.
Les briques S0 = les composants dans ton sac.
Le sommet = le tableau électrique de l'étage — tu vois tout ce qui est connecté en dessous.

### Ce qu'il faut construire
1. **Moteur de positionnement**: problème → coordonnées sur la carte
2. **Moteur de proximité**: coordonnées → escaliers les plus proches (top-N)
3. **Vue plongeante**: escalier → briques S0 connectées (filtre topologique)
4. **Compositeur**: AI reçoit le sac à dos filtré + le problème → tente des chemins
5. **Mémoire d'échec**: chaque tentative ratée = un P5 local → réduction de l'espace

### Contrainte critique
Les briques qui n'existent PAS ENCORE viendront. OpenAlex mine en continu.
Chaque nouveau concept se positionne automatiquement sur la topologie.
Si un nouveau concept ferme un P4 vers un problème ouvert → le moteur le détecte.
V4 n'est pas statique. Il GRANDIT avec la science.

### Statut: VISION — dépend de V2 (timelapse) et V3 (candlesticks)
Pas de saut. Les racines d'abord. Toujours.
