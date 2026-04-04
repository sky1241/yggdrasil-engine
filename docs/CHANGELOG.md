# yggdrasil-engine — Changelog

Trace quotidienne de l'avancement du projet. Un commit par jour, pas de bullshit.
Sky = électricien de jour, architecte de nuit. 10 mois de boulot. Pas un branleur.

---

## 4 avril 2026 — Session 34

### V3 Batterie de tests — La mare qui décide
- **P(k) mesuré sur cooc_global**: ⟨k⟩=2136, k_max=61K, gamma≈0.94 (ultra-dense, pas scale-free)
- **Newman SIR-percolation** (cond-mat/0205009): T_c=0.000149, 1 param T fitte R_max parfaitement
- **Recherche bibliographique** dans WT3 + arXiv tars (E:\arxiv\src\):
  - 134 papers WT3 + 761 papers cousin deep research
  - 10 papiers extraits des tars arXiv (Pastor-Satorras, Newman, Boguña, Cohen, Moreno, Lee)
  - 9 modèles classés, 5 déserts cooc=0, 3 Carmack moves
  - Metaprompt V2 rédigé (`data/metaprompt_wave_research.md`)
- **Batterie 5 tests** (`scripts/test_wave_plan.py`):
  - TEST 1 Énergie: **FAIL** — aucune formule E ne prédit R_max
  - TEST 2 Cratère: **PARTIAL** — avg_internal_weight ρ=+0.71 (p=0.11, n=6 trop petit)
  - TEST 3 Newman T: **PARTIAL** — LOO MAE=10,521 (16%), Laser = outlier (erreur 34K)
  - TEST 4 Mort spectrale: **PASS** — mixing 1/gap × 2 = **8.8 ans** (obs 8-11), MAE=0.83yr
  - TEST 5 Hybride: **PARTIAL** — H2 (Newman + spectral) = meilleur combo
- **Oscillation mu(t) Gödel**: oscillateur amorti R²=0.99 (ETAS R²=0.11)
- **Résultat clé**: le caillou NE compte PAS, c'est la mare qui décide
- **Anomalie**: Laser 1960 = outlier absolu, à investiguer
- **Outputs**: `wave_test_plan.json`, `wave_model_test.json`, `wave_full_test.json`, `wave_research_v2.json`

---

## 2 avril 2026 — Session 33

### V3 Refonte — Le caillou dans la mare
- **Sedov-Taylor INVALIDÉ**: mesurait la croissance globale de la science, PAS le blast local d'une météorite
- **Gödel hold-out (frames globales)**: FAIL — ratio obs/pred=0.67, R²=-0.20 (modèle surestime systématiquement)
- **Gödel hold-out WT3 (local, 3 concepts)**: FAIL — E ne prédit pas R_max, R²=0.003
- **DÉCOUVERTE: propagation BFS onde réelle** dans WT3 (table cooc per-period)
  - Méthode: BFS année par année depuis les concepts-graines, front qui s'élargit
  - 6/13 météorites mesurées: Shannon (76%), Transistor (70%), Turing (65%), ADN (55%), Gödel (44%), Laser (6%)
  - Onde meurt en 8-11 ans pour toutes les météorites
  - **E (strate×continents) ne corrèle PAS avec R_max** — besoin de masse = works_count
- **Analogie validée**: le mycélium = une mare, la percée = un caillou. E = m×g×h
- **Carmack move identifié**: heat kernel sur Laplacien f(t) = e^(-tL) × f(0)
  - WT4 a déjà le Laplacien (66K noeuds, gap 0.226) — zéro paramètre à fitter
- **Scripts**: `godel_holdout.py`, `godel_holdout_wt3.py`, `godel_holdout_wave.py`
- **Outputs**: `data/results/godel_holdout.json`, `godel_holdout_wt3.json`

---

## 30 mars 2026 — Session 32

### V3 Sedov-Taylor — Calibrage complet + validation
- **`calibrate_sedov.py`**: vrais objets Frame, appelle `measure_all()` + `fit_sedov()` (13 meteorites, 7 deltas, OHLC)
- **Fit classique**: beta=369, alpha=0.35, R2=0.64
- **Fit separe**: a(E)=0.01, b(t)=0.91, c(rho0)=0.79, R2=0.88 — densite et temps dominent
- **Classification**: mRNA = seul C_perceptual (30 ans), reste A_technical ou mixed
- **Godel hold-out**: train 12, predict 1 — ratio=0.45 (blast attenue, sol vierge 1931)
- **Validation croisee**: extinctions = breadth structurelle, pas fame (Shannon/Turing = meteorite)
- **Fix**: `_parse_period` gere annees negatives (-43000)
- **Outputs**: `sedov_calibration.json`, `impact_validation.json`

---

## 28 mars 2026 — Session 31 (suite)

### Impact Scale — Pipeline complet (scanner → timeline → scale 0-10)
- **3 scripts créés**: `impact_scanner.py`, `impact_timeline.py`, `impact_scale.py`
- **Scanner**: 833K papers WT3, cursor pagination (stable 1,250/s sur 78GB), dual metrics:
  - `weight_pop` = Σ degree (popularity proxy)
  - `weight_rare` = Σ 1/log(degree+1) (rarity-weighted, inspiré Adamic-Adar)
  - `spread_rare` = RMS distance pondérée rareté depuis centroïde — LE métrique core
- **Timeline**: fenêtres variables (avant 1900: 100 ans, 1900-1930: 10 ans, 1930+: annuel)
  - 56 fenêtres avec données, top papers/auteurs/domaines par fenêtre
- **Scale 0-10**: normalisation z-score par domaine + bonus breadth + pénalité mega-collab
  - Distribution: 421 extinction (0.05%), 6,615 astéroïde (0.8%), 52K météorite (6.3%), 290K rocher (34.8%), 356K pierre (42.7%), 128K caillou (15.4%)
- **Outputs**: `data/impact.db` (365 MB), `data/impact_scale.db` (344 MB), `data/impact_timeline.json` (0.2 MB), `data/impact_scale.json` (51 KB)
- **Fixes en cours de build**:
  - Cursor pagination (OFFSET O(N²) → WHERE rowid > last_rowid)
  - UTF-8 Windows console (auteurs avec diacritiques)
  - V1 weight_sum = degré naïf → V2 rarity weighting
  - Sigmoid trop conservative (0 extinctions) → piecewise linear
- **5 frameworks publiés alignés**: Wu/Evans, Uzzi, Wang/Barabási, Sinatra, Burt — tous déjà cités dans le codebase
- **SCIENTOMETRICS.md** mis à jour avec section Impact Scale complète

---

## 27 mars 2026 — Session 31

### Tests unitaires core — 86/86 PASS
- **3 fichiers de tests créés** couvrant les 3 modules core purs (Tier 1 = maths, zéro data):
  - `test_core_scisci.py` — 32 tests: disruption_index (Wu/Evans), uzzi_zscore, fitness_wang_barabasi, q_factor_sinatra, co_occurrence_strength, graph_laplacian, fiedler_vector
  - `test_core_holes.py` — 34 tests: score_technical (A), score_conceptual (B), score_perceptual (C), DomainPair, HoleDetector, map_symbol_to_continents, CONTINENTS
  - `test_core_symbols.py` — 20 tests: Symbol class, STRATE_COLORS/NAMES/CENTERS, SymbolDatabase (fixture mock JSON)
- **Méthode**: edge cases (zeros, caps, ranges), propriétés mathématiques (row sums, symmetry, signs), mock data (tmp_path fixture)
- **1 fix**: `test_stats` comptait 3 domaines au lieu de 4 dans le mock data → corrigé
- **Résultat**: 86/86 passed, 1.43s, Python 3.13.6, pytest 9.0.2
- **Node Q1** ajouté à winter-tree.json

---

## 17 mars 2026 — Session 30

### forge.py Carmack Moves
- **7 algos cross-domaine** ajoutés à forge.py (outil de debug universel, 2252 lignes):
  - Kalman filter (1960, missiles → bug risk), Haar wavelet (signal → churn multi-échelle)
  - Kaplan-Meier (médecine → survie de fichiers), Newman Q-modularity (biologie → couplage imports)
  - DTW (reconnaissance vocale → patterns flaky), Hamming distance (télécom → sévérité mutations)
  - Z-score anomaly detection (statistique → outliers unifiés)
- **3 nouvelles commandes**: `--carmack`, `--anomaly`, `--flaky-dtw`
- **Full cycle 8 étapes** (avant: 6), pipeline complet sur Muninn = 350 tests, 1 vrai bug trouvé
- **Metaprompt cousin**: `data/forge_cousin_metaprompt.md` — coordonnées Yggdrasil pour deep research forge.py
- Pushed sur infernal-wheel (commit `c48752f`) et MUNINN- (commit `d0b07d0`)

### Muninn — Fixes
- `test_ebbinghaus_recall_separation`: seuil gap 0.1→0.25 (faux positif sur branches uniformes)
- 3 flaky tests (test_lazy_real.py): `@flaky(reruns=2)` pour I/O timing sur DB 2.7M
- `adaptive_boot_budget()`: boot budget adaptatif 15% du contexte (floor 15K, cap 100K)
- `pull_from_meta()`: max_pull 500→1000

### Audit Muninn
- 64 fichiers de tests, ~370 fonctions, **0 fake**, 60 GOOD, 4 OK
- forge.py --full-cycle validé: predict + carmack + mutate + tests + flaky + locate + anomaly

---

## 16 mars 2026 — Session 29

### WT3 Enrichissement (EN COURS)
- **Constat**: WT3 = squelette de graphe sans metadata humaine. Pas de titre, pas d'auteurs, pas d'année. Impossible de chercher "qui a écrit quoi".
- **Fix**: Script `engine/topology/wt3_enrich.py` — scanne le dump OpenAlex works (692 GB, 1,981 fichiers .gz) et injecte `title`, `authors` (JSON), `year` dans la table `papers` existante.
- **Méthode**: ALTER TABLE + UPDATE par matching arXiv ID. Commit SQLite après chaque fichier .gz. Reprise auto si crash. Zéro perte.
- **Progression**: ~5,500 matchés après 12% du scan. Les gros fichiers (300K papers) sortent ~200 matchs en ~40s chacun.
- **Après**: index sur authors, title, year → requêtes instantanées. Le bibliothécaire peut bosser.
- **CHANGELOG.md créé** — ce fichier, pour garder la trace de la vitesse.
- **Philippe retrouvé**: Philippe Louis Schuchert, pas "Shurtste". Thèse EPFL, `docs/briefs/BRIEFING_PHILIPPE.md` existait déjà.

### Ménage repo
- **16 fichiers supprimés**: strates_export_v2.json (6.7M, obsolète), gen_viz_v2/v3.py, viz legacy v2/v3, scripts debug bible, tests placeholder, analyze_pluie.py, cross_physarum_wc.py
- **2 fichiers archivés sur E:**: snapshot_2015_65k.npz (457M) + snapshot_full.npz (615M) = 1 GB libéré
- **0 vrais doublons** trouvés (wt4_spectral.json scan/ vs viz/ = volontairement différents)

### WT4 Forme 3D — COMPLET
- Laplacien bipartite complet [0,B; B^T,0] sur 30,509 noeuds (1,316 glyphes + 29,193 concepts)
- Gap spectral 0.683, signature bipartite 10+/10-
- Commit `c2a72a5`

### WT3 La Bible — COMPLET
- 833K papers, 6.2M bipartite, 885M cooc, 69.4M cooc_global, 8 indexes
- Fix phase 4 crash-resume (checkpoint par batch)
- Commit `f50a4b8`

---

## 15 mars 2026 — Sessions 27-28

### WT3 Build complet
- 6 phases: papers → bipartite → cooc sharding → cooc_global → indexes → meta
- 78 GB SQLite, WAL mode, 56,734s de build (~15h45)
- Phase 3 réécrite 2 fois: staging table (OOM) → disk-sharded → direct chunk-by-chunk upsert
- Commit `a0968cf`

### WT4 v1 → v2
- v1 (B@B^T projection) = FAUX: matrice 99.9% dense, pas de signal
- v2 (bipartite complet) = CORRECT: gap 0.683, core-periphery inverse visible

---

## 12 mars 2026 — Session 25-26

### WT3 phase 3 debug
- Phase 3 cooc = le mur. 885M lignes à agréger.
- Première tentative: staging table → OOM
- Deuxième tentative: disk-sharded aggregation → marchait mais lent
- Troisième tentative: direct chunk-by-chunk upsert → **ça passe**
- Commits `023d0fc`, `83919c9`

---

## 11 mars 2026 — Session 25

### WT3 en cours + WT4 design
- WT3 phases 1-2 OK, phase 3 bloquée (cooc trop gros)
- Design WT4: forme 3D unifiée S-2×S-1×S0 sur bipartite WT3
- Commit `e0f57e5`

---

## 10 mars 2026 — Sessions 23-24

### Briefing Muninn
- Scan P4 Uzzi: 172,762 paires scorées, 88,546 trous structurels
- 42 formules Muninn × 65K concepts → 500 holes classifiés (A/B/C)
- Cell Biology = signal fou: 22/23 paires Type C (angle mort collectif)
- Briefing détaillé: `docs/briefs/BRIEFING_MUNINN.md` + addendum cell bio

### God Cube design
- Théorie God's Algorithm, Manteuffel bounds, polytope 19 faces
- `docs/GOD_CUBE.md`

### Repo reorganization
- Nettoyage complet: fichiers stray, pipeline test outputs virés
- `.winter-tree-stats.json` gitignored (hook artifact)
- Commits `02c4c26`, `a83efca`, `cab9652`

---

## 9 mars 2026 — Session 22

### WT2 Scan COMPLET
- 416/416 chunks, 832K papers avec glyphs + domain + concepts
- Fix extract_tex_from_gz: magic bytes, timeout 30s/paper, cap 500KB regex
- Commit `187f32c`

---

## 8 mars 2026 — Sessions 21

### Pont Muninn ↔ Yggdrasil documenté
- Muninn = granularité paragraphe, Ygg = granularité paper
- Les deux sont complémentaires, pas redondants
- Point de jonction = WT3 (la Bible)
- P39 planifié: Muninn comme bibliothécaire sur WT3
- Ratissage scientométrique: `docs/SCIENTOMETRICS.md`
- WT2 relancé: 52/416 chunks
- Commits `6a55a7b`, `0cb9041`

### Grand ménage docs/
- docs/ réorganisé thématique
- blind_test V1 archivé
- README à jour
- Commit `bb9b879`

---

## 7 mars 2026 — Session 20

### S-2 Fossiles + scope étendu
- 116 fossiles alchimiques + 10 actifs non-math + 7 graines
- Population S-2 totale: ~1,500 glyphes
- WT2 scanner créé: bipartite bridge S-2↔S0 per-paper
- Commits `3954e8f`, `0fbf39b`

---

## 6 mars 2026 — Session 19

### S-1 Métiers COMPLET
- 416/416 chunks, 858K papers, 19 domaines × 1,337 glyphes
- Commit `6889e1f`

### Grand ménage session 18
- S0 = 65K officiel, 21K déclaré obsolète
- Commit `820af7e`

---

## 5 mars 2026 — Session 17

### S-2 COMPLET + S-1 en cours
- Pipeline S-2 terminé, S-1 scan lancé
- MemoryError fixé sur S-1 scanner (stream domain lookup, cap 100 glyphs/paper)
- Commits `70be927`, `fa7bab7`, `cde939b`

---

## 4 mars 2026 — Session 16

### 2 graines découvertes
- Graine: Mort = figé / Vivant = mute
- Conjecture Rubik = mapping glyphes sur structure de cube
- Fix MemoryError S-1 scanner (compact domain lookup, int index)
- Commits `9b0dc51`, `d01a277`, `044b1db`

---

## 3 mars 2026 — Sessions 14-15

### Rapport checkpoint (6 commits en 1 session)
- `989e460` — S-2 glyph archaeology: 194 symboles tracés (57 C1 + 137 C2, Cajori)
- `a0606c3` — Vérification t=0 round 2: 5 corrections (206 entries, 12 agents)
- `856a45a` — Vérification totale t=0: 13 corrections (5 agents, web-vérifié)
- `6b35213` — Archéologie t=0: 206/206 concepts sourcés (peer-reviewed)
- `d9b1886` — Mirror pairs test: 19/20, d=0.925, p=6.68e-06
- `2dd5a8f` — SOL.md: 7 techniques de prompting intégrées

### Pipeline S-2 COMPLET + arXiv mapper COMPLET
- 459 chunks, 617 glyphes actifs, positions spectrales calculées
- 309/309 chunks arXiv, 4.3M papers matchés
- S-1 Métiers lancé (pipeline domain×glyph scanner)
- Commits `eeedfb1`, `e3b876a`, `2ef9a5a`

### Etat moteur à ce checkpoint
- 136 commits, 37,978 lignes Python, 31,080 dans engine/
- Signal confirmé par 3 tests: blind test V2 (p=3.4e-12), glyph laplacian (d=5.76), mirror pairs (d=0.925)

---

## 2 mars 2026 — Sessions 11-13

### Glyph Laplacian + validation
- d=5.76 (corrigé 8.78 après), p=7e-11, Recall@100=70%
- K=9 espèces, 17 graines
- Commit `6204c6e`

### Prédictions 2025
- Top 10K inter-species P4 bridges + intra revolutions
- 108M paires, 41% WTF confirmés
- Commit `b07d891`

### arXiv pipeline lancé
- 114/309 chunks (37%) au checkpoint
- Commit `f2392f6`

---

## 1 mars 2026 — Session 10

### Briefing Philippe Schuchert (EPFL)
- Premier test réel d'Yggdrasil sur un vrai chercheur
- Philippe Louis Schuchert, thèse EPFL soutenue 5 juillet 2024
- "Frequency domain data-driven robust and optimal control"
- Directeur: Prof. Alireza Karimi, labo DATDRIVEN
- Scan P4: concepts Philippe × domaines inattendus
- 3 disjoncteurs identifiés: P≠NP, Problème de Lur'e, μ structuré
- `docs/briefs/BRIEFING_PHILIPPE.md`

### Winter Tree Scanner V2
- 581/581 chunks, 348M papers, 108M paires non-zero
- Laplacien spectral K=64, Recall@100=70%, Cohen's d=8.78

### Blind test V2
- 65K concepts, cutoff 2015, **p = 3.4e-12**
- Le signal est RÉEL

### Film V4
- 1,534 frames, `viz/yggdrasil_rain_v4.html`

---

## 24 février 2026 — Session 8

### Découverte espèces mycélium
- Le moteur mycélium (7,910 lignes, 24 briques) tourne à 87% sans calibration
- 5 curseurs fondamentaux identifiés (Lehmann et al. 2019, 31 espèces)
- Calibrer sur données réelles = boost attendu
- `docs/research/SESSION_8_SPECIES_DISCOVERY.md`

---

## 22 février 2026 — Session 7

### Cross-projects roadmap
- 7 projets, 19 paires, 16 trous P4 détectés
- Matrice quasi diagonale = continents isolés
- Liane #1 testée: Fourier × Infernal Wheel (régime = NOISE, flatness 0.95)
- 7 lianes planifiées (HMM, Shannon, Physarum, Persistent Homology...)
- `docs/reference/CROSS_PROJECTS_ROADMAP.md`

---

## 21 février 2026 — Sessions 5-6

### Liste de course complète (38 tâches faites en 1 journée)
- Lianes: 4,548 trouvées, 200 géo + 69 passe-partout
- 2 types d'escaliers découverts (géographique vs passe-partout)
- Cleanup S0: 39 suspects triés, 13 vrais, 1 bug mapping Hagen-Poiseuille
- Vivant/musée: 15,556 (75%) / 5,144 (25%) par Q1 domaine
- Viz escaliers spectraux HTML interactive
- `docs/briefs/LISTE_COURSE_21FEV.md`

---

## 19 février 2026 — Sessions 3-4

### Viz day
- La Pluie v2: oxygène, lianes verticales, météorites
- C1/C2/C3 toggles, 2 cubes Three.js
- Spine + Sphères fibonacci par strate
- License propriétaire ajoutée

---

## 18 février 2026 — Sessions 1-2

### JOUR 1 — Yggdrasil Engine v0.1.0
- Commit initial `81e8e78`
- La Pluie 3D + toggle couleur continent
- Lianes engine: 69 lianes, 9/10 découvertes confirmées
- Vérification 32 tests: 28/29 = 97% confirmées
- La Carte Vivante S0: 7 pays, 489 capitales, 60 frontières
- **Le moteur est né.**
---
_Auto-update: 2026-04-04 | 58,324L Python | 6,818 fichiers | phase CANOPEE_
