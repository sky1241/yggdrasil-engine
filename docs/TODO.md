# TODO — Yggdrasil Engine
> Dernière màj: 14 mars 2026 (session 25), Sky×Claude (Opus 4.6)

## ARCHITECTURE DES STRATES
```
S6  ☁️  Indécidable          ┐
S5      Presque indécidable   │ ARBRE (pas de mycelium)
S4      Logique supérieure    │
S3      Conjectures           │
S2      Récursion²            │
S1      Structures récursives ┘
════════════════════════════════
S0  🌍  Formules prouvées    ┐
S-1 🔧  Métiers              │ SOL = MYCELIUM (co-occurrences)
S-2 🔣  Glyphes              ┘
════════════════════════════════
```

## V1 — CARTE STATIQUE (✅ FAIT)
Mapper les 21,524 symboles (794 originaux + 20,730 minés), 9 continents, 9 strates (S-2→S6).
Valider sur 100 tests historiques → 87%.

- [x] 794 symboles originaux + 20,730 minés OpenAlex = 21,524 total
- [x] concept_id injecté dans 100% des symboles + index inverse (20,932 entries)
- [x] Matrice co-occurrence 85×85 domaines (296M papers, scan v4)
- [x] Spectral layout (laplacien normalisé → positions)
- [x] 5 patterns: P1 Pont, P2 Dense, P3 Théorie×Outil, P4 Trou ouvert, P5 Anti-signal
- [x] 3 types de trous: A Technique, B Conceptuel, C Perceptuel
- [x] Mycelium Physarum (24 briques, 456 tests)
- [x] Validation 100 tests (87%)
- [x] Validation 32 tests historiques (97%)
- [x] Cross-analyse Physarum × works_count
- [x] Escaliers spectraux (200 geo + 69 passe-partout)
- [x] Viz La Pluie v3, Escaliers 2D
- [ ] Viz Escaliers 3D → routes mycelium (b2, WIP, 60%)

## V2 — TIMELAPSE HISTORIQUE (✅ FAIT)
Remonter à l'an 1000+. Rejouer l'histoire de la science frame par frame.

### Étape 2A — Winter Tree Scan V2 (✅ COMPLET — session 10, 25-28 fév 2026)
- [x] Lookup 65,026 concepts OpenAlex → `data/scan/concepts_65k.json` (7 MB)
- [x] Scanner V2: filtres erratum/retraction/is_retracted + poids 1/C(n,2)
- [x] 581 chunks × ~1 GB, 1,981 fichiers
- [x] **SCAN COMPLET**: 581/581 chunks, 347,999,931 papers, 108,301,944 paires non-zero
- [x] Migration D:\ → E:\ (disque 5 TB, 4.6 TB libre)
- [x] 1,645 périodes distinctes (an ~1000 → 2024)
- Script: `engine/topology/winter_tree_scanner.py`
- Chunks: `data/scan/chunks/chunk_000→580/`

### Étape 2B — Frames + Film (✅ COMPLET — session 10, 28 fév 2026)
- [x] **1,534 frames** (978 par année 1000-1979 + 556 par mois 1980-2024)
- [x] **65,021 concept births** documentés
- [x] Film cube 3D: `viz/yggdrasil_rain_v4.html` (points apparaissent progressivement)
- [x] Scripts: `engine/topology/frame_builder.py` + `engine/topology/concept_births.py`
- [x] Données: `data/scan/frames.json` (2.5 MB) + `data/scan/concept_births.json` (1.6 MB)

### Blind test V2 (✅ COMPLET — session 11, 1 mars 2026, commit `a446268`)
- [x] Snapshot ≤2015: 65,026 concepts, 184,511,629 papers, 82,700,789 paires
- [x] Spectral clustering K=9 sur données 2015 ONLY (pas de look-ahead)
- [x] **Mann-Whitney p = 3.4e-12**, Cohen's d = 0.44
- [x] Dossier: `blind_test_v2/` (7 étapes + FINAL_REPORT_V2.json)

### Glyph Laplacian S-2 (✅ COMPLET — session 12, 2 mars 2026)
- [x] Spectral embedding: 64 eigenvectors (glyphes) du laplacien normalisé
- [x] Score(i,j) = Σ_k √|λ_k| · v_k(i) · v_k(j), cutoff 2015
- [x] 3,348 prédictions spectrales zero-cooc (inter-espèces, level≥2)
- [x] 64 glyphes nommés: `data/scan/glyphs.json`
- [x] **Validation honnête** (3 biais corrigés):
  - Biais 1: Cohen's d apparié par décile de degré → **d=5.76** (vs 8.98 naïf, inflation 1.6×)
  - Biais 2: Rang dans l'espace complet (200K paires inter-espèces)
  - Biais 3: Recall plein espace: **30% top 0.001%**, **70% top 0.1%**, **95% top 1%**
  - p-value honnête = **7.0e-11** (ultra-significatif)
- [x] 19/20 percées dans le top 1% de 82M paires (seul outlier: Topological insulators)
- [x] Module: `engine/analysis/validation_honest.py` (réutilisable)
- [x] Script: `engine/analysis/glyph_laplacian.py` (631 lignes)
- [x] Résultats: `data/scan/spectral_blind_test.json` (version 2, honnête)

### Predictions 2025 (✅ COMPLET — session 11, 1 mars 2026, commit `b07d891`)
- [x] Scan complet sans cutoff: 348M papers, 108M paires, 568K périodes
- [x] P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|
- [x] Top 10K INTER-espèces + INTRA classés par P4 score
- [x] Matrice de collision 9×9 espèces
- [x] Analyse manuelle top 100 INTER: 18 BANAL (18%), 30 INTÉRESSANT (30%), 41 WTF (41%), 11 BRUIT (11%)
- [x] 20/20 vérifications web positives, 0 faux positif
- [x] Top collision: CS×Physics (82 dans top 1000, P4 sum=1,457)
- [x] Dossier: `predictions_2025/` (5 étapes + fichiers résultats)

## V3 — CANDLESTICKS OHLC & MÉTÉORITES (APRÈS V2)
Chaque percée majeure = un candlestick sur le mycelium.
Le V3 RÉUTILISE les frames du V2 → quasi gratuit en calcul.
Blast Sedov-Taylor se propage dans le sol (S-2→S0). Calibration depuis 1948, test final Gödel 1931.
Voir `docs/formulas.tex` pour les formules complètes avec sources.

### Code V3 (sessions 7-8, 24 fév 2026)
- [x] `engine/meteorites.py` — module complet (763 lignes)
  - Sedov-Taylor: blast_radius, blast_velocity, energy_partition
  - 7 deltas: compute_deltas(before, after)
  - OHLC Candle + MeteoriteBox + MeteoriteRegistry
  - fit_sedov (curve_fit scipy), predict_godel
  - Catalogue 13 météorites (Shannon→AlphaFold)
  - classify_candle (corrélation bougie↔trou A/B/C)
- [x] Bugfix session 7: 8 bugs corrigés (4 meteorites + 4 core)
- [x] Audit session 8: 26 bugs fixés sur 14 fichiers + 2 derniers bugs meteorites.py
- [x] Tests meteorites.py passés: signature(), classify_candle(rho0=0), measure_impact(), summary()
- [ ] En attente des frames V2 pour mesure réelle sur les données

### La bougie OHLC scientifique
- **Open** = date d'ÉMISSION du paper
- **High** = pic de reconfiguration maximale du mycelium (dans S-2→S0)
- **Low** = creux (résistance paradigme / stabilisation)
- **Close** = date de VALIDATION (accepté, prouvé, répliqué, explosion citations)
- **Longueur de la bougie** = temps de résistance du paradigme

### Formule Sedov-Taylor adaptée au mycelium
`R(t) = β × (E/ρ₀)^{1/5} × t^{2/5}`
- E = strate_height × continents_touchés (énergie d'impact)
- ρ₀ = meshedness locale avant impact (densité du sol)
- R(t) = nombre de concepts affectés à t mois après publication
- β, γ = paramètres libres à calibrer depuis les boîtes de météorites

### Corrélation bougie ↔ type de trou (prédit par Sedov-Taylor + ρ₀)
- Trou Technique (A) → ρ₀ élevé → blast lent → bougie MOYENNE
- Trou Conceptuel (B) → ρ₀ faible (vide) → blast rapide → bougie COURTE
- Trou Perceptuel (C) → ρ₀ élevé + hostile → blast bloqué → bougie LONGUE (Karikó mRNA: 30 ans)

### 7 indicateurs techniques sous chaque bougie
Calculés comme DELTA entre frame avant et frame après la météorite:

```
CANDLESTICK: émission → validation
├── 1. volume      = nouvelles arêtes co-occurrence créées
├── 2. amplitude   = déplacement spectral des centroïdes (distance euclidienne)
├── 3. BC_delta    = delta betweenness centrality (nouveaux ponts vs obsolètes)
├── 4. alpha_delta = delta meshedness (réseau + ou - résilient)
├── 5. P4_delta    = trous fermés vs trous ouverts (net)
├── 6. physarum    = redistribution des flux (hyphes créées/mortes)
└── 7. births      = nouveaux concepts apparus / concepts morts
```

### Pondération de l'impact
`impact_météorite = strate_height × continents_touchés`
- Poincaré (S3 × 1 continent) = score moyen
- Shannon (S1 × 7 continents) = score massif
- Gödel (S6 × tout) = hors échelle

### Boîtes de mesure à accumuler
Chaque météorite mesurée = une boîte. On accumule:
Shannon 1948, ADN 1953, transistor, laser, internet, CRISPR, AlphaFold...
→ Moyenne des boîtes = SIGNATURE TYPE d'une météorite

### Test Gödel (TEST FINAL)
- Gödel 1931 = première météorite de l'histoire
- Avant lui: tout S0, plat, zéro strate au-dessus
- UNE seule mesure, pas de moyenne possible
- Appliquer la signature moyenne → prédire l'impact attendu
- Comparer à l'impact RÉEL
- Si ça colle → le modèle est validé du premier impact au dernier

## V3b — ESPÈCE MYCÉLIUM (APRÈS SCAN — session 8, 24 fév 2026)
~~Identifier quelle espèce de champignon le réseau Yggdrasil ressemble.~~
**REFONTE session 10 (25 fév 2026): PAS un champignon — une FORÊT de champignons.**
5 curseurs de Lehmann 2019 (31 espèces, dataset ouvert).
Voir `docs/SESSION_8_SPECIES_DISCOVERY.md` pour le plan complet.

### V1 — Preuve de concept (FAIT mais NON FIABLE)
- [x] Phase A: 5 curseurs mesurés sur V1 85×85 (`engine/topology/species_identifier.py`)
  - BA = 77.99° (cv=0.679) — sparsification P90 (357/3563 arêtes)
  - IL = 1.81 hops (cv=0.251) — BFS sur graphe sparse
  - D = 3.96 log10 (cv=0.289) — log10(co-occ) tombe dans range Lehmann
  - Db = 0.351 (R²=0.639) — limitation N=85 pour box counting
  - L = 1.3 (cv=0.448) — σ²/μ² sans +1 (Lehmann convention)
- [x] Phase B: Identification globale → **Ascomycota** (polyvalent, hétérogène)
  - Confiance 28.5%, marge 0.30 vs Mucoromycota (2ème)
  - Résultat: `data/topology/species_profile.json`
- [x] Phase B2: Robustesse P90 vs Max-K (K=3,4,5,6) → STABLE (toujours Ascomycota)
  - **NON FIABLE**: 85 nœuds = 99.8% dense, 3/5 curseurs insensibles au K
  - **Conclusion V1 = preuve de concept seulement**

### V2 — MULTI-ESPÈCES (APRÈS SCAN — insight session 10)
**Insight clé: c'est pas UN champignon, c'est une FORÊT.**
- Chaque continent = son propre mycélium = sa propre espèce (9 espèces)
- Mathematics = **Glomeromycota** (connecteur universel, 63% des domaines, comme 80% des plantes en nature)
- Les connexions entre continents = anastomose inter-espèces
- Degré 3-4 = contrainte physique (Murray's Law 1926, transport de fluide en tubes)

#### P4 inter-espèce (NOUVEAU — potentiellement game-changer)
Chaque P4 (trou ouvert) entre deux continents a une probabilité pondérée par les espèces des deux côtés:
- Explorateur × Explorateur → probabilité haute (les deux foncent)
- Corridor × Corridor → probabilité basse (personne explore)
- Explorateur × Corridor → probabilité moyenne
→ Améliore potentiellement le recall du blind test (V1 = 50% avec probabilité uniforme)

#### Plan V2 (partiellement réalisé via spectral K=9)
- [x] 9 espèces identifiées par spectral clustering K=9 (65K concepts) — session 10
- [x] P4 inter-espèce calculé et classé (Predictions 2025) — session 11
- [ ] Phase E: Mesurer 5 curseurs PAR espèce (9 mesures, pas 1)
- [ ] Phase F: Calibrer mycelium_full.py avec les vrais paramètres par espèce
- [ ] Phase G: Évolution temporelle — l'espèce de chaque continent change-t-elle avec le temps ?

#### Risques identifiés
- L'analogie biologique est poétique mais peut ne pas ajouter de pouvoir prédictif
- Les 9 continents sont des groupements humains, pas naturels
- Seuls les TESTS sur V2 trancheront — zéro risque car on ne change rien au modèle existant

### V2d — Archéologie t=0 (sessions 13-14, 2-3 mars 2026)
**Objectif: sourcer le vrai t=0 de chaque concept (pas le birth OpenAlex, le VRAI).**

#### Level 0+1 origins (✅ COMPLET — session 13, 2 mars 2026)
- [x] 206/206 concepts (19 L0 + 187 L1) sourcés avec peer-reviewed
- [x] Vérification round 1: 13 corrections (5 agents, web-vérifié) — commit `856a45a`
- [x] Vérification round 2: 5 corrections (12 agents, web-vérifié) — commit `a0606c3`
- [x] Données: `data/scan/origins_to_source.json` (206 entries, 0 missing)
- [x] Scripts: `engine/analysis/inject_origins_l0.py` + `inject_origins_l1.py`

#### S-2 Glyph Archaeology (✅ COMPLET — session 14, 3 mars 2026)
- [x] 194/1337 glyphes mathématiques tracés (source: Cajori 1928-29 + Halmos 1950)
- [x] 57 C1 (haute confiance) + 137 C2 (confiance moyenne)
- [x] Données: `data/core/glyph_origins.json` (194 entries)
- [x] Script: `engine/analysis/inject_glyph_origins.py`
- [ ] Compléter les 1143 glyphes restants (priorité basse — 194 couvrent les plus importants)

#### SOL.md MÉCANIQUES CLAUDE (✅ — session 14, 3 mars 2026)
- [x] 7 techniques de prompting intégrées dans SOL.md — commit `2dd5a8f`

### V3c — GRAINES S-2 + PATIENT t=0 (session 10b, 27 fév 2026)
**Objectif: remonter au patient zéro absolu — les graines S-2 avant l'an 1000.**

#### Résultats validés
- [x] 17 graines S-2 identifiées: 10 chiffres (0-9) + 7 symboles alchimiques (☉☽♂♀♃♄☿)
- [x] Patient t=0 de chaque graine avec preuve scientifique:
  - Tally | : ~43,000 av. J-C (Os de Lebombo, 24 datations radiocarbone)
  - Brahmi 1-9 : ~257 av. J-C (Édits d'Ashoka, datation épigraphique)
  - Zéro 0 : 628 ap. J-C (Brahmagupta, Brāhmasphuṭasiddhānta)
  - 7 métaux ☉☽♂♀♃♄☿ : ~300 ap. J-C (Zosimos, Papyrus Leyde/Stockholm)
- [x] Mutation documentée peer-reviewed: ☉→Au→79 (Wentrup 2024 ChemPlusChem)
- [x] Zodiac EXCLU de S-2 (pas de mutation scientifique = ésotérique)
- [x] Alphabet latin/grec EXCLU de S-2 (substrat emprunté, pas inventé pour la science)
- [x] Fichier: `data/core/seeds_s2.json` (17 graines + sources + mutations)
- [x] 9 espèces classifiées from scratch (spectral clustering 65K concepts): `data/scan/species_65k.json`
- [x] Types mycologiques: endo (Physiq, BioCli), ecto (TerGeo), sapro (HumEco, BioLab)
- [x] 619 concepts pré-1100 extraits: `data/scan/early_concepts.json`
- [x] Audit data complet: 581/581 chunks, 1645 périodes, 2.2G occurrences, 0 trou

#### Décisions architecturales
- S-2 = ADN partagé par les 9 espèces (les glyphes sont universels, comme A/T/G/C)
- La différenciation en espèces émerge aux niveaux S-1 (combinaisons) et S0 (formules)
- Les 9 espèces sont 9 spores indépendantes avec t=0 différents, pas UN champignon qui se divise
- Exception: Aristote (~350 av. J-C) = mega-hub, 1 spore → 4 espèces (spéciation naturelle)

#### Prochaine étape
- [x] Film chronologique FAIT: 1,534 frames (an 1000→2024), 65,021 births
- [ ] Calibrer l'évolution sur la réalité historique (Gutenberg 1440, Rév. scientifique 1600, Lumières 1750...)
- [x] Glyph Laplacian: 64 glyphes S-2, cutoff 2015, d=5.76 (honnête), p=7e-11

## V4 — LE GRIMPEUR (VISION — après V3)
Le sommet de chaque escalier = un point de vue.
Regarder en bas = voir les briques S0 filtrées par la topologie.
L'AI grimpe avec le bon sac à dos.

### Le mécanisme
1. Problème ouvert → positionnement sur la carte
2. Trouver escaliers les plus proches (géo + passe-partout)
3. Vue plongeante → sac à dos de briques S0 filtrées
4. AI compose des chemins de preuves avec ces briques
5. Échec = donnée (P5 local) → réduction espace → autre sommet

### Modules à construire
- [ ] Moteur de positionnement: problème → coordonnées topologiques
- [ ] Moteur de proximité: coordonnées → top-N escaliers
- [ ] Vue plongeante: escalier → briques S0 connectées
- [ ] Compositeur: AI + sac à dos filtré → chemins candidats
- [ ] Mémoire d'échec: tentatives ratées → P5 locaux → carte se raffine

### Premier test: P=NP
- P=NP est S3-S4, PAS S6 (pas prouvé indécidable)
- 3 routes classiques sont P5 prouvés (diagonalisation, preuves naturelles, arithmétisation)
- Le moteur cherche les P4 = routes que personne n'a empruntées
- Les briques manquantes viendront → OpenAlex mine en continu → détection automatique

### Dépend de: V2 (timelapse) + V3 (candlesticks). PAS DE SAUT.

## TEST V1 (✅ FAIT)
- [x] Test semi-aveugle V1 2015→2025: p=0.00002, recall@100=50%, r=0.90
- Dossier: blind_test/

## TEST V2 (✅ FAIT — session 11-12, 1-2 mars 2026)
- [x] Blind test V2 (P4): 65K concepts, cutoff 2015, 82.7M paires — p=3.4e-12, d=0.44
- [x] Blind test spectral (Glyph Laplacian): 64 eigenvectors, validation honnête
  - Cohen's d honnête = 5.76 (apparié par degré), p = 7.0e-11
  - Recall@100 filtré = 70%, Recall top 0.1% espace complet = 70%
  - 19/20 percées dans le top 1% des 82M paires
- [x] Espèces K=9 sur données 2015 ONLY (pas de look-ahead)
- [x] Mirror pairs test (session 13, 2 mars 2026):
  - Contrôle: même décile de degré + même distance spectrale (±15%) + zero-cooc + inter-espèces
  - **19/20 victoires** (seul échec: Topological insulators)
  - **Cohen's d = 0.925**, Wilcoxon p = 6.68e-06, mean beats = 94.7%
  - Verdict: signal réel — le Laplacien détecte autre chose que la centralité
  - Script: `engine/analysis/mirror_pairs_test.py`
  - Résultats: `data/scan/mirror_pairs_test.json`
- Dossiers: `blind_test_v2/` + `data/scan/spectral_blind_test.json`

## S-2 PIPELINE SPECTRAL (✅ COMPLET — session 15, 3 mars 2026)
Pipeline 8 briques: registry → parsers → scanners → laplacien → frames → intégration.

### arXiv Glyph Scanner (✅ COMPLET — session 12)
- [x] 420/420 chunks, 978,919 papers, 950,237 avec glyphes (97%), 610M paires
- [x] Cutoff 2015-12, poids 1/C(n,2)
- [x] Résultats: `data/scan/glyph_chunks/chunk_001→420/`
- Script: `engine/glyphs/arxiv_scanner.py`

### PMC Glyph Scanner (✅ COMPLET — session 12)
- [x] 39/39 chunks, 72,502 papers avec glyphes
- [x] Résultats: `data/scan/pmc_glyph_chunks/`
- Script: `engine/glyphs/pmc_scanner.py`

### Glyph Laplacien spectral (✅ COMPLET — session 15)
- [x] 459 chunks (420 arXiv + 39 PMC) → matrice 1337×1337, densité 6.9%
- [x] eigsh(k=9), 617/1337 glyphes actifs
- [x] Sanity check: ∫↔∂=0.024, ∀↔∃=0.020, (↔)=0.0003, ∧↔∨=0.043
- [x] Positions: `data/scan/glyph_positions.json`
- Script: `engine/glyphs/glyph_laplacian.py`

### Glyph Frames + Intégration (✅ COMPLET — session 15)
- [x] 356 frames (4 historiques + 352 data, 1959→2015-12)
- [x] `data/scan/glyph_frames.json` + `data/core/s2_spectral.json`
- Scripts: `engine/glyphs/glyph_frame_builder.py` + `engine/glyphs/integrate.py`

## SOURCES ANNEXES — arXiv + PMC (✅ COMPLET)

### arXiv Source Tars (✅ COMPLET — session 15)
- [x] 2,282 tars, 1,025 GB, `E:/arxiv/src/` — archive.org gratuit (1992-2019)
- Script: `engine/mining/build_arxiv_tree.py`

### arXiv↔OpenAlex Mapper (✅ COMPLET — session 15)
- [x] **309/309 chunks**: 479,290,643 papers, 4,324,641 arXiv trouvés
- [ ] Auto-merge → `data/scan/arxiv_openalex_map.json.gz` (nice-to-have)
- Script: `engine/mining/arxiv_openalex_mapper.py`

## WT2 — BRIDGE S-2↔S0 (✅ COMPLET — session 22, 9 mars 2026)
- [x] **416/416 chunks**, 877K papers, 832K full (glyphs+concepts)
- [x] 19 domaines, 1,337 glyphes, cutoff 2015-12
- [x] Fix extract_tex_from_gz: magic bytes, timeout 30s/paper, cap 500KB regex
- Scanner: `engine/topology/wt2_scanner.py`
- Output: `data/scan/wt2_chunks/chunk_NNN/`

## WT3 — LA BIBLE (EN COURS — sessions 23-25, crashé phase 4)
Jointure WT1+WT2 dans SQLite unifié. Script: `engine/topology/wt3_bible.py`

- [x] **Phase 1 papers**: 833,030 papers, 416/416 chunks
- [x] **Phase 2 bipartite**: 6,181,981 paires glyph×concept, 416/416 chunks
- [x] **Phase 3a cooc**: 6.4B rows, 64 shards dans `data/cooc_shards/` (20 GB)
- [x] **Phase 3b cooc_shard_agg**: 64/64 shards agrégés (terminé 12 mars 15:35)
- [ ] **Phase 4 cooc_global**: CRASHÉ — 61.6M rows mais marker "done" absent → potentiellement incomplet
- [ ] **Phase 5 indexes**: 7/8 index manquants
- [ ] **Phase 6 meta**: vide
- Output: `data/wt3.db` (74 GB), SQLite WAL mode, crash-resumable

### God Cube + WT4 design (sessions 23-25)
- [x] `docs/GOD_CUBE.md` — théorie God's Algorithm, Manteuffel, polytope, trinité quantique
- [x] `viz/god_cube.html` — prototype polytope
- [x] `viz/s2_spectral_3d.html` — S-2 3D embedding (eigenvectors 1-2-3)
- [x] `viz/hypertree_decomp.html`, `viz/hypergraph_s2s1.html` — nouvelles viz
- [x] WT4 design: forme champignon, nd = coordonnée verticale, Laplacien joint = calcul dérivé
- [ ] WT4 implémentation (attend WT3 complet)

## NOTES
- Winter tree scan V2 COMPLET (581/581 chunks, 692 GB, 348M papers). Le goulot est passé.
- **WT2 COMPLET** (416/416, 832K papers) — session 22.
- **WT3 crashé phase 4** — cooc_global potentiellement incomplet, indexes manquants. Relancer le script.
- V3 (formules météorites) réutilise les 1,534 frames V2 → quasi gratuit.
- Predictions 2025 produites sans cutoff. Blind test V2 avec cutoff 2015.
- Glyph Laplacian FAIT avec validation honnête: d=5.76, p=7e-11, recall top 0.1%=70%.
- **Mirror pairs test PASSÉ**: 19/20, d=0.925, p=6.68e-06 → signal réel confirmé.
- **Archéologie t=0 COMPLÈTE**: 206 L0+L1 concepts + 194 glyphes S-2 sourcés (Cajori, peer-reviewed).
- **arXiv mapper COMPLET**: 309/309 chunks, 479M papers, 4.3M arXiv trouvés (session 15).
- ⚠️ `pytest` non installé — tests non exécutables. Installer: `pip install pytest`.
- ⚠️ D:\ contient encore le snapshot OpenAlex (~692 GB) après migration E:\. À nettoyer si besoin d'espace.
- **Pipeline S-2 COMPLET**: 459 chunks, 617 glyphes actifs, positions spectrales calculées.
- **S-1 Métiers COMPLET**: 416/416 chunks, 858K papers, 19 domaines (session 19).
- **Prochaine étape**: finir WT3 (relancer wt3_bible.py), puis WT4, Muninn, viz, V3, V4.
- Tout Claude qui bosse sur ce repo: lis SOL.md EN PREMIER, puis ce TODO.
