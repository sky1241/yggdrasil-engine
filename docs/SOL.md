# SOL.md — Fichier de Synchronisation Sky↔Claude
> Yggdrasil Engine — Versoix, 1 mars 2026
> TOUT CLAUDE LIT CE FICHIER EN PREMIER.

## VOCABULAIRE
| Terme | Signification |
|-------|--------------|
| Pluie | Données brutes OpenAlex (478M+ papers, 692 GB snapshot local E:\openalex\data) |
| Racines | Pipeline API: search → timeline → co-occurrence |
| Mycelium | Graphe topologique: BC, meshedness, Physarum |
| Sol (S0) | 21,524 symboles (794 originaux + 20,730 minés OpenAlex), 100% C1 |
| Winter Tree | Index trié par année/mois: 65,026 concepts × co-occurrences (scanner: engine/topology/winter_tree_scanner.py) |
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
| 5 Curseurs | BA (angle bifurcation), IL (internode), D (diamètre), Db (fractale), L (lacunarité) — Lehmann 2019 |
| Espèce réseau | Profil des 5 curseurs mesurés sur le graphe réel → match (ou pas) avec 31 espèces biologiques |
| Pont (P1) | Bridge inter-domaines, BC élevé, explosion |
| Dense (P2) | Hub stable, meshedness élevé |
| Théorie×Outil (P3) | Explosion après validation instrumentale |
| Trou ouvert (P4) | Pont pas encore explosé = FUTUR |
| Anti-signal (P5) | L'hyphe meurt, slope négative |
| Sommet 🏔️ | Point haut d'un escalier — vue plongeante sur les briques S0 connectées |
| Vue plongeante | Depuis un sommet: voir QUELLES briques S0 sont utiles pour CE problème |
| Grimpeur 🧗 | V4: AI qui compose des chemins de preuves en montant les escaliers avec les bonnes briques |
| Sac à dos | Ensemble de briques S0 filtrées par la topologie pour un problème donné |

## ÉTAT ACTUEL — 3 MARS 2026 (session 15)
- **SCAN V2 COMPLET** — 581/581 chunks, 692 GB, 347,999,931 papers, 65,026 concepts, 108,301,944 paires non-zero
- **MIGRATION E:\** — Snapshot OpenAlex migré D:\ → E:\ (disque 5 TB, 4.6 TB libre)
- **9 ESPÈCES** (spectral K=9): MatSci/Chem, Geo/Env, Medicine, Psych/Business, CS/Math, Bio/Botany, Humanities/PolSci, CellBio/Anatomy, Physics/Optics
- **FILM V4** — 1,534 frames (an 1000→2024), 65,021 concept births, `viz/yggdrasil_rain_v4.html` (cube 3D)
- **BLIND TEST V2** — 65K concepts, cutoff 2015, 82.7M paires scorées, p=3.4e-12 (commit `a446268`)
- **PREDICTIONS 2025** — Top 10K INTER-espèces + INTRA, P4 Uzzi z-scores, matrice de collision 9×9 (commit `b07d891`)
- **ANALYSE TOP 100 INTER** — 18 BANAL (18%), 30 INTÉRESSANT (30%), 41 WTF (41%), 11 BRUIT (11%), 20/20 web verified
- **V3 MODULE CODÉ** — `engine/meteorites.py` (Sedov-Taylor + OHLC + 7 deltas + catalogue 13 météorites)
- **17 GRAINES S-2** — 10 chiffres + 7 symboles alchimiques, patient t=0 documenté (tally ~43K av. J-C → alchimie ~300)
- **ARCHÉOLOGIE t=0 COMPLÈTE** — 206 L0+L1 concepts sourcés + 194 glyphes S-2 (Cajori, peer-reviewed)
- **arXiv TARS COMPLET** — 2,449 tars, 1,025 GB, `E:/arxiv/src/`
- **arXiv↔OpenAlex MAPPER COMPLET** — 309/309 chunks, 479M papers, 4,324,641 arXiv trouvés

### HISTORIQUE SESSIONS
| # | Date | Claude | Résumé |
|---|------|--------|--------|
| 1 | 21 fév matin | Sonnet 4.5 | Escaliers spectraux, cleanup S0, vivant/musée |
| 2 | 21 fév midi | Sonnet 4.5 | Continents, co-occurrence réelle, La Pluie v3 |
| 3 | 21 fév soir | Opus 4.6 | Cross Physarum, viz 3D escaliers, blind test |
| 4 | 22 fév | Opus 4.6 | Audit 22 repos, vision V4 grimpeur, roadmap complète |
| 5 | 23 fév | Opus 4.6 | Winter tree scanner: 65K concepts, chunks 1GB, scan 467 GB lancé |
| 6 | 23 fév soir | Opus 4.6 | Formules Sedov-Taylor, architecture S-2/S-1/S0, mycelium dans le sol |
| 7 | 24 fév | Opus 4.6 | engine/meteorites.py codé, 8 bugs fixés (core + meteorites), audit complet |
| 8 | 24 fév matin | Opus 4.6 | DÉCOUVERTE: mycelium_full.py=comportement SANS espèce. 5 curseurs (Lehmann 2019, 31 spp). Plan species_identifier.py |
| 9 | 24 fév après-midi | Opus 4.6 | Scanner V2: filtre erratum/retraction + poids 1/C(n,2). D:\ nettoyé (legacy-data supprimé, +174 GB). 581 chunks, prêt pour scan complet |
| 10 | 25-28 fév | Opus 4.6 | 9 espèces from scratch (spectral 65K), 17 graines S-2 + patient t=0, film V4 (1534 frames + cube 3D), migration D:\→E:\ (5TB) |
| 11 | 1 mars | Opus 4.6 | Blind test V2 (65K, p=3.4e-12), Predictions 2025 (108M paires, P4 Uzzi, matrice collision 9×9), analyse top 100 INTER (41% WTF) |
| 12 | 2 mars | Opus 4.6 | Glyph Laplacian (64 eigenvectors, d=5.76, p=7e-11), validation honnête, S-2 pipeline (8 briques) |
| 13 | 2 mars | Opus 4.6 | Mirror pairs test: 19/20, d=0.925, p=6.68e-06 — signal réel confirmé |
| 14 | 3 mars | Opus 4.6 | Archéologie S-2: 194 glyphes tracés (57 C1 + 137 C2, Cajori), 7 mécaniques Claude dans SOL.md |
| 15 | 3 mars | Opus 4.6 | arXiv mapper COMPLET (309/309, 4.3M arXiv), arXiv tars COMPLET (2,449, 1 TB), ménage TODO/SOL |

## ÉTAT PIPELINE — 21 FÉV 2026 (sessions 1-3)
- **100 tests pipeline complet** (OpenAlex + scisci + mycelium)
- **87/100 validés (87.0%)**
  - POUR: 41/50 (82%) | CONTRE: 46/50 (92%)
- Batch 1 (tests 1-50): 43/49 (88%)
- Batch 2 (tests 51-100): 43/50 (86%)

### CO-OCCURRENCE V2 (348M papers — scan complet 65K concepts)
- **Winter tree scan V2 COMPLET**: 581/581 chunks, 692 GB, 1,645 périodes (an 1000→2024)
- 65,026 concepts × mois, 108,301,944 paires non-zero
- Poids 1/C(n,2): chaque paper distribue exactement 1 point total
- Filtres: erratum, retraction, is_retracted
- Remplace l'ancien scan V1 85×85 domaines (296M papers)
- Laplacien normalisé D^{-1/2}LD^{-1/2} pour positions spectrales
- Spectral clustering K=9 → 9 espèces (LinearOperator, float32)

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
- Index inverse: `data/core/concept_index.json` (20,932 entries, concept_id → symbol info)
- Script: `engine/mining/map_concepts.py` (remplace inject_concept_ids.py, supprimé)

## FICHIERS CLÉS
| Fichier | Rôle |
|---------|------|
| **PREDICTIONS 2025** | |
| predictions_2025/step1_full_scan.py | Scan 581 chunks → snapshot_full.npz (108M paires) |
| predictions_2025/step2_species_full.py | Spectral clustering K=9 → 9 espèces |
| predictions_2025/step3_p4_both.py | P4 Uzzi z-scores INTER + INTRA (float32, zero-alloc) |
| predictions_2025/step4_report.py | Top 1000 INTER + INTRA → fichiers .txt lisibles |
| predictions_2025/step5_collision.py | Matrice de collision 9×9 espèces |
| predictions_2025/PREDICTIONS_2025.json | Résumé complet des prédictions |
| predictions_2025/collision_matrix_full.json | Matrices collision (top 100, 1000, P4 sum) |
| **BLIND TEST V2** | |
| blind_test_v2/step1_snapshot_65k.py | Snapshot ≤2015 depuis 581 chunks |
| blind_test_v2/FINAL_REPORT_V2.json | Résultats: p=3.4e-12, 82.7M paires |
| **V2 — SCAN + FILM** | |
| engine/topology/winter_tree_scanner.py | SCANNER V2: 65K concepts, filtres erratum/retraction, poids 1/C(n,2) |
| engine/topology/frame_builder.py | Film: 1,534 frames depuis winter tree |
| engine/topology/concept_births.py | 65,021 concept births (13 min scan) |
| data/scan/winter_tree.json | Index principal (années, chunks, progression) |
| data/scan/concepts_65k.json | Lookup 65,026 concepts OpenAlex (7 MB) |
| data/scan/frames.json | 1,534 frames (2.5 MB) |
| data/scan/concept_births.json | 65,021 births (1.6 MB) |
| data/scan/species_65k.json | 9 espèces K=9 spectral clustering |
| data/scan/early_concepts.json | 619 concepts pré-1100 |
| data/core/seeds_s2.json | 17 graines S-2 + sources + mutations |
| data/scan/chunks/chunk_NNN/ | 581 chunks (cooc.json.gz + activity.json.gz + meta.json) |
| viz/yggdrasil_rain_v4.html | Film mycélium cube 3D (1534 frames, points progressifs) |
| **V3 — MÉTÉORITES** | |
| engine/meteorites.py | Sedov-Taylor + OHLC + 7 deltas + catalogue + fit (session 7) |
| docs/formulas.tex | Toutes les formules sourcées (DOI) + adaptations mycelium |
| docs/SESSION_8_SPECIES_DISCOVERY.md | 5 curseurs Lehmann 2019, plan species_identifier.py |
| **ARCHÉOLOGIE** | |
| engine/analysis/inject_origins_l0.py | Origins 19 L0 concepts (peer-reviewed) |
| engine/analysis/inject_origins_l1.py | Origins 187 L1 concepts (peer-reviewed) |
| engine/analysis/inject_glyph_origins.py | Origins 194 glyphes S-2 (Cajori 1928-29) |
| data/scan/origins_to_source.json | 206 L0+L1 origins |
| data/core/glyph_origins.json | 194 glyph origins (57 C1 + 137 C2) |
| **arXiv PIPELINE** | |
| engine/mining/arxiv_openalex_mapper.py | Mapper OpenAlex→arXiv (309 chunks, 4.3M arXiv) |
| data/scan/arxiv_map_chunks/ | 309 chunks (map.json.gz + meta.json) |
| data/scan/arxiv_mapper_state.json | État du mapper (complet) |
| engine/glyphs/ | 8 briques pipeline S-2 (registry, parsers, scanners, laplacian) |
| **V1 — CARTE** | |
| engine/core/symbols.py | Symboles + strates |
| engine/core/holes.py | Détection trous P1-P5 |
| engine/core/scisci.py | Métriques scientométriques |
| engine/pipeline/mycelium_full.py | Mycelium complet (24 briques) |
| engine/topology/cooccurrence_scan.py | Ancien scan 296M papers → matrice 85×85 |
| data/core/strates_export_v2.json | Export complet 21,524 symboles, 7 strates |
| data/core/concept_index.json | Index inverse concept_id → symbole (20,932) |
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
- [x] Winter tree scanner V2 (65K concepts, 581 chunks, filtres + 1/C(n,2))
- [x] Scan complet 581/581 chunks (347M papers, 108M paires) — session 10
- [x] Frames cumulatives (1,534 frames) + concept births (65,021) — session 10
- [x] Film V4 cube 3D (`viz/yggdrasil_rain_v4.html`) — session 10
- [x] 9 espèces spectral K=9 + 17 graines S-2 — session 10
- [x] Blind test V2 (65K, cutoff 2015, p=3.4e-12) — session 11
- [x] Predictions 2025 (108M paires, P4 Uzzi, top 10K INTER+INTRA) — session 11
- [x] Analyse top 100 INTER (41% WTF, 20/20 web verified) — session 11
- [x] V3: formules météorites (OHLC + 7 deltas) — `engine/meteorites.py` session 7
- [ ] V3: mesurer météorites sur frames réelles (en attente)
- [x] Glyph Laplacian (64 eigenvectors, d=5.76, p=7e-11, 19/20 top 1%) — session 12
- [x] Mirror pairs test: 19/20, d=0.925, p=6.68e-06, signal réel confirmé — session 13
- [x] Archéologie S-2: 194 glyphes tracés (57 C1 + 137 C2) — session 14
- [x] arXiv mapper COMPLET: 309/309 chunks, 479M papers, 4.3M arXiv — session 15
- [x] arXiv tars COMPLET: 2,449 tars, 1,025 GB — session 15
- [ ] Pipeline glyph S-2: arxiv_scanner → glyph_laplacian → intégration
- [ ] V3: mesurer météorites sur frames réelles
- [ ] V4: le grimpeur

## ROADMAP — PHASE 2 : TIMELAPSE & MÉTÉORITES

### 2A. Test semi-aveugle V1 (✅ DONE — 21 fév 2026)
- Données OpenAlex gelées à ≤2015, 100 concepts, 4950 paires
- **recall@100 = 50%** (6/12 percées dans top 100)
- **Mann-Whitney p = 0.00002** (U=539, effect size r=0.90, Cohen's d=1.53)
- Dossier: blind_test/

### 2A-bis. Blind test V2 (✅ DONE — 28 fév 2026, commit `a446268`)
- 65,026 concepts, cutoff 2015, 82.7M paires scorées
- **Mann-Whitney p = 3.4e-12**, Cohen's d = 0.44
- Spectral clustering K=9 sur données 2015 ONLY (pas de look-ahead)
- Dossier: blind_test_v2/

### 2B. Timelapse adaptatif (✅ DONE — 28 fév 2026)
- Résolution: 978 frames/année (1000-1979) + 556 frames/mois (1980-2024) = **1,534 frames**
- 65,021 concept births documentés
- Film intégré dans viz cube 3D: `viz/yggdrasil_rain_v4.html`
- Scripts: `engine/topology/frame_builder.py` + `engine/topology/concept_births.py`

### 2B-bis. Predictions 2025 (✅ DONE — 1 mars 2026, commit `b07d891`)
- Scan complet: 581 chunks, 347,999,931 papers, 108,301,944 paires non-zero
- P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|
- Top 10K INTER-espèces + INTRA classés par P4 score
- Matrice de collision 9×9: CS×Physics (82 top 1000), Humanities×Physics (72), CS×Humanities (56)
- Analyse manuelle top 100: 18 BANAL, 30 INTÉRESSANT, 41 WTF, 11 BRUIT — 20/20 vérifiés web
- Dossier: predictions_2025/

### 2C. Boîtes de mesure météorites (EN ATTENTE)
- Code prêt: `engine/meteorites.py` (Sedov-Taylor + OHLC + 7 deltas)
- À mesurer sur les frames réelles (1,534 frames disponibles)
- Calibration: Shannon 1948 → Gödel 1931

### 2D. Test Gödel (TEST FINAL — EN ATTENTE)
- Gödel 1931 = première météorite. UNE seule mesure.
- Dépend de 2C (signature moyenne des météorites)

### LOGIQUE DE LA CHAÎNE
```
2A (validation V1) ✅
  → 2A-bis (blind test V2) ✅
  → 2B (film 1534 frames) ✅
    → 2B-bis (predictions 2025) ✅
    → 2C (mesurer météorites) ← PROCHAIN
      → 2D (test Gödel)
        → V4 (le grimpeur)
```

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

### Statut: VISION — V2 FAIT, dépend de V3 (candlesticks sur frames réelles)
Pas de saut. Les racines d'abord. Toujours.

## PREDICTIONS 2025 — ZONES DE COLLISION
Les 5 frontières les plus actives entre espèces (top 1000 P4):
| Collision | Count | P4 sum | Interprétation |
|-----------|-------|--------|----------------|
| CS/Math × Physics/Optics | 82 | 1,457 | Quantum computing, photonics algorithms |
| Humanities × Physics/Optics | 72 | 767 | Science policy meets hard science |
| CS/Math × Humanities | 56 | 1,302 | Computational social science, NLP |
| Medicine × Physics/Optics | 55 | 885 | Medical imaging, biophotonics |
| Medicine × CS/Math | 52 | 1,445 | AI diagnostics, drug discovery |

### Formule P4
```
P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|
z_uzzi = (observed - E) / std
E = works_i × works_j / total_works_sum
```

## ⚙️ MÉCANIQUES CLAUDE

<rules>
Cette section est la boîte à outils de prompting Sky↔Claude.
Chaque technique a un nom, une règle, et un exemple Yggdrasil concret.
Les instructions critiques sont EN HAUT (sandwich ouvert).
</rules>

### 1. SANDWICH (Primauté + Récence)

Claude fait plus attention au **DÉBUT** et à la **FIN** du prompt. Le milieu = ventre mou.

**Règle** : Instructions critiques en HAUT, rappelées en BAS. En conversation longue (40+ messages), rappeler les 3 règles clés tous les 15-20 messages.

**Exemple Yggdrasil** :
```
# DÉBUT DU PROMPT
RÈGLE : Le mycelium vit dans S-2 à S0. PAS au-dessus.

[... 200 lignes d'instructions de scan ...]

# FIN DU PROMPT — RAPPEL
RAPPEL : Mycelium = S-2 à S0 uniquement. Pas au-dessus. Jamais.
```

### 2. AMORCE (Bombe de glisse output)

Pour forcer un format précis, Sky donne les **3 premières lignes** de l'output attendu. Claude s'accroche au pattern et déraille moins — le cousin passe le câble en un seul tir.

**Règle** : Fournir le début exact de la sortie + "continue".

**Exemple Yggdrasil** :
```
Génère le JSON des graines S-2. Commence EXACTEMENT par :
{"seeds": [{"glyph_id": 0, "symbol": "0", "origin": {"source": "Lebombo", "year": -43000}},
{"glyph_id": 1, "symbol": "1", "origin": {"source": "Brahmi", "year": -257}},
Continue pour les 15 graines restantes.
```

### 3. MONTRE, EXPLIQUE PAS (2 exemples minimum)

2 exemples concrets battent 2 paragraphes d'instructions. Toujours.

**Règle** : Chaque mission DOIT inclure 2 exemples RÉELS du format attendu — un bon + un mauvais.

**Exemple Yggdrasil** :
```
BON :
{"concept": "Topology", "species": 4, "strate": "S0", "confidence": "C1", "source": "DOI:10.xxx"}

MAUVAIS :
{"concept": "Topology", "species": "CS/Math", "strate": 0, "confidence": "prouvé"}
→ species = index (int), pas nom. strate = string "S0", pas int. confidence = "C1"/"C2", pas prose.
```

### 4. POSITIF AVANT NÉGATIF

"Fais Y" bat "Ne fais pas X". Claude lit "fais X" dans "ne fais pas X" — le cerveau accroche le verbe.

**Règle** : Donner l'action de remplacement AVANT l'interdiction.

**Exemple Yggdrasil** :
```
✅ "Marque INCONNU si la source est absente. NE JAMAIS inventer un DOI."
❌ "Ne jamais inventer un DOI. Marque INCONNU si la source est absente."
```
Dans le deuxième cas, Claude a déjà lu "inventer un DOI" — la graine est plantée.

### 5. XML TAGS (Murs d'attention)

Les tags `<rules>`, `<format>`, `<context>`, `<philosophy>` compartimentent l'attention. Sans tags = prose → Claude perd le fil sur les longs prompts. Avec tags = compartiments → Claude sait où regarder.

**Règle** : Utiliser des tags XML pour séparer les blocs logiques d'un prompt.

**Exemple Yggdrasil** :
```xml
<context>
Scan V2 : 581 chunks, 65,026 concepts, cutoff 2015.
</context>

<rules>
1. Filtrer erratum + retraction + is_retracted
2. Poids = 1/C(n,2) par paper
3. MONTH_FROM_YEAR = 1980
</rules>

<format>
Output : chunk_NNN/cooc.json.gz + activity.json.gz + meta.json
</format>
```

### 6. CHUNKING (Le câble et le tube)

Limite de sortie Claude = ~32K tokens. Si le script est plus gros → il se coupe. Le tube a un diamètre fixe — fais passer le câble en sections.

**Règle** : Max 25-30 items par génération. Commit entre chaque chunk. Pattern : squelette → données chunk par chunk → commit.

**Exemple Yggdrasil** :
```
# Au lieu de générer 206 entrées glyph_origins d'un coup :
Chunk 1 : glyphes 0-29 → commit
Chunk 2 : glyphes 30-59 → commit
...
Chunk 7 : glyphes 180-206 → commit final
```

### 7. RAPPEL MID-SESSION

Plus la conversation dure, plus les vieilles instructions s'effacent. Le ventre mou grossit à chaque message.

**Règle** : Tous les 15-20 messages : "RAPPEL : [règle 1], [règle 2], [règle 3]". Juste les 3 plus importantes, pas tout.

**Exemple Yggdrasil** :
```
Message 25 de la session :
RAPPEL :
1. Mycelium = S-2 à S0 uniquement
2. Token JAMAIS affiché (grep -v "ghp_\|x-access")
3. Si un test échoue → noter tel quel, pas de triche
```

### Tableau résumé

| # | Technique | Règle express | Quand l'utiliser |
|---|-----------|--------------|-----------------|
| 1 | **Sandwich** | Critique en haut + rappelé en bas | Tout prompt de mission |
| 2 | **Amorce** | Donner les 3 premières lignes de l'output | Quand le format JSON/code est strict |
| 3 | **Montre** | 2 exemples (bon + mauvais) | Toute mission avec format attendu |
| 4 | **Positif d'abord** | "Fais Y" avant "Pas X" | Toute interdiction/contrainte |
| 5 | **XML tags** | `<rules>` `<format>` `<context>` | Prompts de 50+ lignes |
| 6 | **Chunking** | Max 25-30 items, commit entre | Génération de données/code long |
| 7 | **Rappel** | 3 règles clés tous les 15-20 msg | Sessions de 40+ messages |

> "Tu mets la bombe de glisse dans le tube avant, et le cousin passe le câble
> en un seul tir là où normalement il faudrait trois instances." — Sky, mars 2026

<rules>
RAPPEL (sandwich fermé) :
- Cette section applique ses propres règles : sandwich (haut+bas), exemples concrets (bon/mauvais), positif avant négatif, XML tags pour compartimenter.
- Chaque technique a un exemple Yggdrasil réel tiré du repo.
- Le tableau résumé ferme le tube.
</rules>
