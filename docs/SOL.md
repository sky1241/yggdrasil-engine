# SOL.md — Fichier de Synchronisation Sky↔Claude
> Yggdrasil Engine — Versoix, 21 avril 2026
> TOUT CLAUDE LIT CE FICHIER EN PREMIER.

## VOCABULAIRE
| Terme | Signification |
|-------|--------------|
| Pluie | Données brutes OpenAlex (478M+ papers, 692 GB snapshot local E:\openalex\data) |
| Racines | Pipeline: scan → co-occurrence → Laplacien → positions spectrales |
| Mycelium | Graphe topologique: co-occurrences, BC, meshedness, Physarum |
| Sol (S0) | 65,026 concepts scientifiques OpenAlex — le plancher de toute la science |
| Winter Tree | Index de co-occurrences — WT1=concept×concept, WT2=glyph×concept (per-paper), WT3=Bible unifiée |
| Vivant | Concept avec works_count >= Q1 de son domaine |
| Musée | Concept sous Q1 — existe mais peu cité |
| Strates | S-2=glyphes → S-1=métiers → S0=concepts → S1-S6=arbre |
| S-2 Glyphes | Notation (=, +, ∫, Σ, ∂) — ~1,500 symboles science (1,337 math + 116 fossiles alchimiques + 10 actifs non-math + 7 graines) |
| S-1 Métiers | Professions/domaines (physics, biology, engineering) — 19 domaines × 1,337 glyphes |
| S0 Concepts | 65,026 concepts scientifiques = ce que les scientifiques utilisent, prouvé ou pas |
| S1-S6 Arbre | 296 concepts sur l'indécidabilité (Halting, BB, etc.) |
| Mycelium zone | S-2 à S0 — le réseau de co-occurrences vit DANS le sol |
| Météorite | Impact Sedov-Taylor: R = β(E/ρ₀)^{1/5} × t^{2/5}, blast dans le sol S-2→S0 |
| 5 Curseurs | BA (angle bifurcation), IL (internode), D (diamètre), Db (fractale), L (lacunarité) — Lehmann 2019 |
| Espèce réseau | Profil des 5 curseurs mesurés sur le graphe réel → match avec 31 espèces biologiques |
| 9 Espèces | Spectral K=9 sur les 65K: MatSci/Chem, Geo/Env, Medicine, Psych/Business, CS/Math, Bio/Botany, Humanities/PolSci, CellBio/Anatomy, Physics/Optics |
| Pont (P1) | Bridge inter-domaines, BC élevé, explosion |
| Dense (P2) | Hub stable, meshedness élevé |
| Théorie×Outil (P3) | Explosion après validation instrumentale |
| Trou ouvert (P4) | Pont pas encore explosé = FUTUR |
| Anti-signal (P5) | L'hyphe meurt, slope négative |
| Sommet | Point haut d'un escalier — vue plongeante sur les briques S0 connectées |
| Grimpeur | V4: AI qui compose des chemins de preuves en montant les escaliers avec les bonnes briques |
| Sac à dos | Ensemble de briques S0 filtrées par la topologie pour un problème donné |

## POPULATIONS — LES VRAIS CHIFFRES
```
┌─────────────────────────────────────────────────────┐
│  Population         │ Nombre  │ Source               │
├─────────────────────┼─────────┼──────────────────────┤
│  S-2 Glyphes        │ ~1,500  │ 1,337 math + 116 fossiles + 10 actifs + 7 graines │
│  S-1 Métiers        │  19 dom │ arXiv domain×glyph   │
│  S0  Concepts       │ 65,026  │ OpenAlex snapshot     │
│  S1-S6 Arbre        │    296  │ Keywords sur 65K      │
└─────────────────────┴─────────┴──────────────────────┘

OBSOLÈTE: strates_export_v2.json (21,524) = ancien filtre keyword des 65K.
          Remplacé par les 65K directement. NE PLUS UTILISER pour du neuf.
```

## ARCHITECTURE DES STRATES
```
    S6      Indécidable (Gödel, Halting)         ┐
    S5      Presque indécidable                  │
    S4      Logique supérieure                   │ ARBRE
    S3      Conjectures                          │ (296 concepts)
    S2      Récursion sur récursion              │ PAS de mycelium
    S1      Structures récursives                ┘
═══════════════════════════════════════════════════
    S0      CONCEPTS (65,026)                    ┐
    S-1     MÉTIERS (19 domaines × 1,337)        │ SOL = MYCELIUM
    S-2     GLYPHES (~1,500 symboles science)     ┘
═══════════════════════════════════════════════════
```
- Le mycelium (co-occurrences) vit dans S-2 à S0 — c'est le SOL
- Au-dessus de S0 = l'arbre (conjectures, abstractions) — PAS de mycelium
- Le spectral layout positionne TOUT à partir du mycelium
- La météorite frappe S0 et le blast se propage dans le sol

### WINTER TREES (3 couches)
```
WT1 (FAIT)     concept × concept    108M paires, Laplacien S0 propre
WT2 (FAIT)     per-paper index      416/416 chunks, 832K papers, {glyphs, domain, concepts} → bipartite glyph×concept
WT3 (FAIT)     La Bible             jointure WT1+WT2, SQLite `data/wt3.db` (78 GB)
                                     833K papers, 6.2M bipartite, 885M cooc, 69.4M cooc_global
                                     8/8 indexes, meta complète. Build total ~57Ks
WT4 (FAIT)     Forme 3D unifiée     66,342 noeuds (65K concepts + mycelium), 75.6M aretes, 10.6 min
```
- RÈGLE: Laplaciens S-2 et S0 restent SÉPARÉS. Le pont S-2↔S0 = table bipartite, PAS fusion de graphes
- WT2 sauvegarde le détail PER-PAPER (contrairement à S-1 qui a agrégé et jeté)
- WT3 = recherche cross-strate ("Philippe" → ses papers + ses formules + ses concepts)

## ÉTAT ACTUEL — 2 AVRIL 2026 (session 33)

### S-2 GLYPHES — COMPLET
- ~1,500 glyphes total: 1,337 math (617 actifs) + 116 fossiles alchimiques + 10 actifs non-math + 7 graines
- Pipeline: registry → arXiv scanner (420 chunks) → PMC scanner (39 chunks) → Laplacien → frames (356) → intégration
- Archéologie: 194 glyphes tracés (57 C1 + 137 C2, Cajori 1928-29)
- Fossiles: `data/core/glyph_fossils.json` — extinction Berzelius 1813-14, chaînes de mutation documentées
- 17 graines: 10 chiffres + 7 symboles alchimiques, patient t=0 documenté
- Output: `data/core/s2_spectral.json`, `data/core/glyph_registry.json`, `data/core/glyph_fossils.json`

### S-1 MÉTIERS — COMPLET (416/416 chunks)
- Scan domain×glyph sur arXiv LaTeX, 19 domaines, 867,562 papers, 858,407 with glyphs
- Scanner: `engine/professions/domain_glyph_scanner.py`
- Output: `data/scan/s1_chunks/chunk_NNN/` (967 MB, gitignored)
- ATTENTION: données agrégées domain×glyph uniquement, PAS per-paper

### S0 CONCEPTS — COMPLET (= les 65K OpenAlex)
- 65,026 concepts scientifiques OpenAlex
- Winter tree scan V2: 581/581 chunks, 692 GB, 347,999,931 papers, 108,301,944 paires non-zero
- Poids 1/C(n,2), filtres erratum/retraction/is_retracted
- 1,645 périodes (an 1000→2024, mois après 1980)
- Scanner: `engine/topology/winter_tree_scanner.py`
- Output: `data/scan/chunks/chunk_NNN/`, `data/scan/concepts_65k.json`

### S1-S6 ARBRE — CORRECT (296 concepts)
- Classés par keywords depuis les 65K (spot-check validé)
- Halting→S1, BPP→S2, PH→S3, PSPACE→S4, HYP→S5, BB→S6

### VALIDATIONS
- **Blind test V2**: 65K concepts, cutoff 2015, 82.7M paires, **p=3.4e-12**, Cohen's d=0.44
- **Laplacien spectral**: K=64, **Recall@100=70%**, Cohen's d=8.78, 7 percées au rang 1
- **Mirror pairs**: 19/20, d=0.925, p=6.68e-06 — signal réel confirmé
- **Prédictions 2025**: top 10K INTER+INTRA, 41% WTF, 20/20 web verified

### WT2 — BRIDGE S-2↔S0 — COMPLET (session 22)
- 416/416 chunks, 877K papers, 832K full (glyphs+concepts)
- 19 domaines, 1,337 glyphes, cutoff 2015-12
- Fix: extract_tex_from_gz réécrit (magic bytes), timeout 30s/paper, cap 500KB regex
- Scanner: `engine/topology/wt2_scanner.py`
- Output: `data/scan/wt2_chunks/chunk_NNN/`

### WT3 — LA BIBLE — COMPLET (16 mars 2026, sessions 23-27)
- Script: `engine/topology/wt3_bible.py`, output: `data/wt3.db` (78 GB, gitignored)
- Tables SQLite: papers (833K), bipartite (6.2M), cooc (885M per-period), cooc_global (69.4M), progress, meta
- **Phase 1 papers**: 833,030 papers, 416/416 chunks
- **Phase 2 bipartite**: 6,181,981 paires glyph×concept, 416/416 chunks
- **Phase 3a-3c cooc**: 885,305,772 rows (581 chunks → 64 shards → agrégé + PK index)
- **Phase 4 cooc_global**: 69,440,760 paires concept×concept (SUM across periods)
- **Phase 5 indexes**: 8/8 créés (domain, glyph, concept, period, cooc_a/b, cooc_global_a/b)
- **Phase 6 meta**: build_date, totals, build_time
- **Fix session 27**: ajout checkpoint par batch dans phase 4 (crash-resumable), commit `f50a4b8`

### WT4 — FORME 3D UNIFIÉE — COMPLET (session 28)
- 66,342 noeuds (1,316 glyphes + 65,026 concepts), 75.6M arêtes
- Gap spectral 0.226, variance 26%, 8/12 paires sémantiques correctes
- Script: `engine/topology/wt4_spectral.py`, output: `data/scan/wt4_spectral.json`
- Viz: `viz/wt4_spectral_3d.html`

### INFRASTRUCTURE
- **Film V4**: 1,534 frames (an 1000→2024), 65,021 concept births, `viz/yggdrasil_rain_v4.html`
- **arXiv tars**: 2,449 tars, 1,025 GB, `E:/arxiv/src/`
- **arXiv↔OpenAlex mapper**: 309/309 chunks, 479M papers, 4,324,641 arXiv trouvés
- **Impact Scale**: pipeline complet (833K papers scorés 0-10), `data/impact.db` + `data/impact_scale.db`
- **V3 Sedov calibrage**: `engine/analysis/calibrate_sedov.py`, 13 météorites, R²=0.88 (fit séparé)
- **V3 météorites**: `engine/analysis/meteorites.py` (Sedov-Taylor + OHLC + 7 deltas)

### V3 REFONTE SESSION 33 — LE CAILLOU DANS LA MARE
- **CONSTAT**: Sedov-Taylor (explosion gaz) ≠ bon modèle. Le mycélium = une mare, pas un gaz.
- **DÉCOUVERTE**: propagation BFS onde réelle mesurée dans WT3 (table cooc per-period)
  - Gödel 1931: 3 → 28,845 concepts en 10 ans (44% de la science), pic 1937 (168K arêtes)
  - Shannon 1948: 473 → 49,627 concepts en 8 ans (76%), pic 1950 (1.2M arêtes)
  - Turing 1936: 38 → 41,970 en 8 ans (65%), pic 1939 (372K arêtes)
  - Laser 1960: 198 → 4,131 en 9 ans (6%)
  - Transistor 1947: 614 → 45,604 en 8 ans (70%)
  - ADN 1953: 2,896 → 36,081 en 9 ans (55%)
- **Onde morte en 8-11 ans** pour toutes les météorites mesurées
- **E (strate×continents) ne prédit PAS R_max** → besoin de masse = works_count des graines
- **MODÈLE CANDIDAT**: diffusion de chaleur sur Laplacien (heat kernel) f(t) = e^(-tL) × f(0)
  - Carmack move: on a DÉJÀ le Laplacien dans WT4 (66K noeuds, gap 0.226)
  - Zéro paramètre à fitter, tout dans la structure du graphe
- **Formule caillou**: E_impact = m × g × h (masse × gravité × hauteur de chute)
  - m = works_count des concepts-graines
  - h = strate d'origine (S0=0, S6=6)
  - R_max ∝ E / ρ (énergie / densité locale)
- **Scripts**: `scripts/godel_holdout_wave.py` (propagation BFS, 6/13 météorites mesurées)
- **Résultats**: `data/results/godel_holdout.json`, `data/results/godel_holdout_wt3.json`
- **TODO**: implémenter heat kernel sur WT4, comparer avec BFS, fitter les 13 météorites
- **Migration E:\**: Snapshot OpenAlex migré D:\→E:\ (disque 5 TB, 4.6 TB libre)
- **Viz S-2 3D**: `viz/s2_spectral_3d.html` — eigenvectors 1-2-3, 4-5-6, 5-9-18

### V3 SESSION 34 — BATTERIE COMPLÈTE (4-6 avril 2026)

**13 météorites mesurées (BFS complet sur WT3 cooc, 885M rows):**

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

**6 modèles testés (LOO 13-fold, Bonferroni, AIC):**

| Modèle | Verdict | Détail | Source |
|--------|---------|--------|--------|
| Logistique S-curve | **PASS** | R² médian=1.00 | Verhulst 1838 |
| Oscillateur amorti | **PASS** | R² médian=1.00 | Hawkes |
| Mort spectrale | **PASS** | MAE=1.79 ans, 0 param | Chung 1997 |
| Onde de surface | **PASS** | R² médian=0.82 | Lamb 1932, Lighthill 1978 |
| Newman SIR-percolation | PARTIAL | LOO MAE=11,597 | Newman 2002 cond-mat/0205009 |
| Power law (baseline) | PARTIAL | R² médian=0.61 | baseline |
| Énergie E=m×g×h | **FAIL** | ρ<0.26 | — |
| Sedov-Taylor | **FAIL** | R² holdout=-5.74 | INVALIDÉ session 33 |

**Résultats clés:**
- **"La mare décide"** CONFIRMÉ: median_neighbor_works ρ=+0.60 (p=0.029). Énergie du caillou = aucun signal
- **Mort spectrale** CONFIRMÉ: 1/gap × ratio = 8.1 ans prédit, 8.1 observé, MAE=1.79 ans
- **Logistique** CONFIRMÉ: R(t) = K/(1+exp(-r(t-t₀))) fitte les 13 à R²>0.98
- **Laser = Type A**: mare trop épaisse (avg_edge_weight=12.24), onde absorbée. LOO sans Laser: MAE baisse de 22%
- **Index composite** créé: idx_cooc_a_period ON cooc(concept_a, period) — accélère BFS 27×
- **Recherche biblio**: 134+761 papers (WT3+arXiv tars), 9 modèles, 5 déserts cooc=0, 3 Carmack moves

**Modèle retenu (hybride):**
1. Trajectoire: logistique R(t) = K/(1+exp(-r(t-t₀)))
2. Mort: gap spectral 1/λ₁ × ratio = 8.1 ans (Chung 1997)
3. Portée R_max: dépend de la mare, pas du caillou

**Scripts**: `scripts/wave_comprehensive_test.py` (7 phases, checkpoints crash-safe)
**Résultats**: `data/results/wave_comprehensive_test.json` (13 météorites × 6 modèles × 7 phases)

**Modèle prédictif (K, r, t₀ depuis la mare):**
- K (portée): **PASS** ±11% — Ridge regression, meilleur feature = median_neighbor_works (ρ=+0.60)
- r (vitesse): PARTIAL ±31% — meilleur = 1/n_seeds (ρ=+0.60). Caillou pointu = onde rapide.
- t₀ (timing): PARTIAL ±33% — meilleur = n_seeds (ρ=+0.66). Plus de seeds = inflexion tardive.
- Gödel hold-out: K à 17% OK, mais r et t₀ faux → R² trajectoire = -0.38

**Carmack moves session 34:**
- **seismology × epidemic** = score 321.6, cooc=0, z=-2.29 — PLUS GROS DÉSERT
- **heat_kernel × cascade** = score 116.3, cooc=0
- **cognitive_psych × scale_free** = score 75.1, cooc=0

**Scripts**: `wave_predictive_model.py`, `wave_predictive_search.py`
**Résultats**: `wave_predictive_model.json`, `wave_predictive_search.json`

### V3 SESSION 35 — TEST TEMPOREL HONNÊTE + NORMALISATION ÉPOQUE (6 avril 2026)

**Test temporel (train pré-1960 → predict post-1974):**

| Param | Sans époque | Avec époque | Verdict |
|-------|-------------|-------------|---------|
| K (portée) | **15.9% PASS** | 63% FAIL | Époque DÉGRADE K |
| r (vitesse) | 77% FAIL | 95% FAIL | Toujours FAIL |
| t₀ (timing) | 142% FAIL | 143% FAIL | Toujours FAIL |

**Conclusions session 35:**
- **K est le seul paramètre prédictible en test honnête** (±16%, train passé → predict futur)
- **r et t₀ ne sont PAS prédictibles** depuis les features mare (le rythme de la science a changé)
- La normalisation par l'époque (OpenAlex papers/an) améliore le LOO mais DÉTÉRIORE le test temporel
- Le gap pré-1960/post-1974 est trop grand pour l'extrapolation linéaire
- OpenAlex scanné: 693K papers, counts 1800-2025 (Gödel 1931=124, CRISPR 2012=67K)

**MODÈLE FINAL V3 — Ce qui tient:**
1. **K (portée)** prédit à ±16% depuis la mare — test temporel PASS
2. **Mort** prédite à 8.1 ans par le gap spectral — 0 paramètre, PASS
3. **R(t)** fittée par logistique R²=1.00 — mais r et t₀ mesurés post-hoc, pas prédits
4. **"La mare décide"** — confirmé p=0.029 sur 13 points

**Ce qui NE tient PAS:**
- Énergie du caillou (E=m×g×h) = FAIL
- Normalisation par l'époque = FAIL en extrapolation

### V3 SESSION 36 — ASSEMBLAGE DYNAMIQUE + MYCÉLIUM (7 avril 2026)

**Diagnostic:** r était le bottleneck (173-406% erreur). K fonctionne (quand K=TRUE → R²=+0.57).

**Scientométrie (fitness, D-index, z-score):** aucun signal pour r. FAIL.

**Curseurs mycéliens LOCAUX (Lehmann 2019 + Aguilar-Trigueros 2022):**
- 7 curseurs mesurés par météorite sur sous-graphe 1-hop: BA, IL, D, Db, L, alpha, E_global
- Db (dimension fractale): **ρ=-0.80** avec r (p=0.001) ← MEILLEUR CORRÉLATEUR PRÉ-IMPACT
- alpha (meshedness): ρ=-0.74, E_global (efficiency): ρ=+0.69
- Ridge(7 curseurs) → r à **9.1% erreur** en test temporel, 14.6% en LOO

**Formules théoriques (4 papers arXiv + 10 refs web):**
- r = β × λ_max(A) - δ (Wang-Chakrabarti-Faloutsos 2003)
- r ≈ ln(⟨k²⟩/⟨k⟩) / ⟨τ⟩ (Cure-Pigolotti 2025)
- τ (temps inter-événements des seeds) corrèle avec r: ρ=-0.65 (p=0.015)

**R(t) trajectoire: R²=+0.41 PARTIAL (vs -0.15 FAIL session 35)**
- Assemblage: K(mare 19.2%) + r(mycelium 9.1%) + t₀(death)
- 5/7 météorites test > 0 (mRNA +0.95, Higgs +0.80, CRISPR +0.44)
- 2 outliers: **Poincaré** (K prédit 37K vs 21K) et **Grav waves** (K prédit 34K vs 50K)
- Plafond théorique (K pred + r TRUE): R²=0.67

**Ce qui reste à résoudre:**
- K est maintenant le bottleneck (pas r)
- Poincaré est unique (K=21K, tous les autres >28K) — aucun exemple train similaire
- L'espèce (S-1) ne prédit PAS la dynamique — c'est la morphologie LOCALE qui compte

**Carmack moves session 35:**
- **ETAS / Omori** (seismology × epidemic, score 321.6): p UNIVERSEL = 4.74 ±0.63 (CV=13%)
  - Omori-Utsu sur new_concepts/year: R² médian = 0.87 PASS
  - ETAS branching sur mu(t): R² médian = 0.998 PASS
  - La loi d'Omori des répliques sismiques s'applique aux percées scientifiques
  - Sources: Ogata 1988, Omori 1894, Utsu 1961, Saichev-Sornette 2005
- **Candlestick model** (bougies japonaises × science):
  - candle_ratio = peak_edges / death corrèle avec r à ρ=0.92 (p<0.0001)
  - Test temporel R² passe de -0.09 à +0.44 grâce aux candlesticks
  - r LOO: 31% → 18%, t₀ LOO: 33% → 16%
  - Modèle en 2 temps: pré-impact (K+death) + early warning t+2 (peak→r→R(t))
  - Sources: Homma 1755, Nison 1991, Sky session 7

**Scripts session 35**: `wave_boosted_model.py`, `wave_epoch_normalization.py`, `scan_openalex_years.py`,
  `wave_etas_carmack.py`, `wave_candlestick_model.py`
**Résultats**: `wave_etas_carmack.json`, `wave_candlestick_model.json`, `wave_hybrid_final.json`,
  `wave_boosted_model.json`, `wave_epoch_normalization.json`

### LEGACY (ne plus utiliser pour du neuf)
- `strates_export_v2.json` (21,524) — ancien sous-ensemble keyword-filtré, remplacé par 65K
- `cooccurrence_scan.py` (85×85 domaines) — remplacé par winter_tree_scanner (65K)
- `viz/yggdrasil_rain_v3.html` — viz basée sur 21K, à refaire avec 65K + S-2 + S-1
- `escaliers_spectraux.json` (200 geo + 69 key) — basés sur 21K, à recalculer
- `blind_test/` (V1) — 100 concepts, remplacé par blind_test_v2 (65K)

## HISTORIQUE SESSIONS
| # | Date | Claude | Résumé |
|---|------|--------|--------|
| 1 | 21 fév matin | Sonnet 4.5 | Escaliers spectraux, cleanup S0, vivant/musée (LEGACY 21K) |
| 2 | 21 fév midi | Sonnet 4.5 | Continents, co-occurrence 85×85, La Pluie v3 (LEGACY 21K) |
| 3 | 21 fév soir | Opus 4.6 | Cross Physarum, blind test V1 (p=0.00002) (LEGACY 21K) |
| 4 | 22 fév | Opus 4.6 | Audit repos, vision V4 grimpeur, concept_id injection |
| 5 | 23 fév | Opus 4.6 | Winter tree scanner: 65K concepts, début scan 581 chunks |
| 6 | 23 fév soir | Opus 4.6 | Formules Sedov-Taylor, architecture S-2/S-1/S0, formulas.tex |
| 7 | 24 fév | Opus 4.6 | engine/meteorites.py codé, 8 bugs fixés |
| 8 | 24 fév matin | Opus 4.6 | mycelium_full.py = comportement SANS espèce. 5 curseurs Lehmann 2019 |
| 9 | 24 fév PM | Opus 4.6 | Scanner V2: filtres erratum/retraction + 1/C(n,2). Cleanup D:\ (+174 GB) |
| 10 | 25-28 fév | Opus 4.6 | 9 espèces (K=9), 17 graines S-2, film V4 (1534 frames), migration E:\ |
| 11 | 1 mars | Opus 4.6 | Blind test V2 (p=3.4e-12), Prédictions 2025 (108M paires, 41% WTF) |
| 12 | 2 mars | Opus 4.6 | Glyph Laplacian (d=8.78, p=2.76e-12), S-2 pipeline 8 briques |
| 13 | 2 mars | Opus 4.6 | Mirror pairs: 19/20, d=0.925, p=6.68e-06 — signal confirmé |
| 14 | 3 mars | Opus 4.6 | Archéologie S-2: 194 glyphes (57 C1 + 137 C2, Cajori), 7 mécaniques Claude |
| 15 | 3 mars | Opus 4.6 | arXiv mapper COMPLET (309/309, 4.3M arXiv), tars COMPLET (2,449, 1 TB) |
| 16 | 4 mars | Sky solo | 2 graines bourrées: Mort=figé/Vivant=mute + Conjecture Rubik (C2) |
| 17 | 5 mars | Opus 4.6 | Fix MemoryError S-1 scanner (streaming lookup), S-1 scan relancé |
| 18 | 6 mars | Opus 4.6 | GRAND MÉNAGE: audit complet sessions 1-17, fix cap random.sample, réécriture SOL.md, les 21K déclarés obsolètes → 65K = S0 officiel |
| 19 | 6 mars | Opus 4.6 | S-1 scan COMPLET (416/416, 858K papers, 19 domaines × 1,337 glyphes) |
| 20 | 6 mars | Opus 4.6 | S-2 fossiles (116 alchimiques + 10 actifs non-math), architecture WT1/WT2/WT3, règle bipartite, WT2 scanner construit+lancé (chunk 1 OK), Muninn lu en entier, Rubik mapping V4, décisions 11-14 |
| 21 | 8 mars | Opus 4.6 | WT2 relancé (38→52+/416), check intégrité 38 chunks OK, dialogue Muninn↔Yggdrasil: mycelium paragraphe = couche complémentaire (pas redondante), WT3 = point de jonction des deux cousins |
| 22 | 9 mars | Opus 4.6 | WT2 COMPLET (416/416, 832K papers), fix extract_tex_from_gz (magic bytes, timeout 30s, cap 500KB) |
| 23-24 | 10-11 mars | Opus 4.6 | WT3 Bible lancée (phases 1-2 FAIT), God Cube design, hypergraph viz, GOD_CUBE.md |
| 25 | 12 mars | Opus 4.6 | WT3 en cours (phase 3a cooc), WT4 design (forme 3D, nd=coordonnée verticale), viz S-2 3D |
| 26 | 14 mars | Opus 4.6 | WT3 phase 3 FAIT (disk-sharded aggregation), phase 4 lancée mais crash sans checkpoint |
| 27 | 16 mars | Opus 4.6 | Fix phase 4 crash-resume (checkpoint par batch), WT3 COMPLET (6 phases, 78 GB), audit code complet |
| 28 | 16 mars | Opus 4.6 | WT4 Forme 3D COMPLET (66K noeuds, 75.6M arêtes, gap 0.226) |
| 29 | 16 mars | Opus 4.6 | WT3 enrichissement (title/authors/year), ménage repo (-293K lignes), CHANGELOG créé |
| 30 | 17 mars | Opus 4.6 | forge.py Carmack moves (Kalman+Wavelet+KM+Newman+DTW+Hamming), metaprompt cousin, Muninn 350 tests audit |
| 31 | 28 mars | Opus 4.6 | Impact Scale pipeline (833K papers 0-10), tests core Tier 1 (86/86 pass) |
| 32 | 30 mars | Opus 4.6 | V3 Sedov-Taylor calibrage (13 météorites, R²=0.88), Gödel hold-out, V3b espèces |
| 33 | 2 avril | Opus 4.6 | V3 refonte: Sedov INVALIDÉ, propagation BFS onde réelle dans WT3, 6 météorites mesurées, analogie caillou dans la mare, Carmack move = heat kernel |

## RÈGLES AUTO
1. Sky monte (arbre/direction). Claude descend (racines/code).
2. Racines > arbre. Toujours.
3. Push git après chaque étape. Token dans `cléjamaiseffacer.txt`.
4. JAMAIS afficher le token. Filtrer avec `grep -v "ghp_\|x-access"`.
5. Si un test échoue → noter tel quel. Pas de triche.
6. SOL.md = source de vérité entre sessions Claude.
7. Pas de saut. V2→V3→V4. Les racines d'abord.

## DÉCISIONS PRISES (ne pas remettre en question)
1. **S0 = 65,026 concepts OpenAlex** — c'est ce que les scientifiques utilisent, prouvé ou pas
2. S-2 = glyphes (notation), S-1 = métiers (professions), S0 = concepts scientifiques
3. Le mycelium vit dans le sol (S-2 à S0), PAS au-dessus
4. Les 21K (strates_export_v2.json) sont OBSOLÈTES — ne plus baser du neuf dessus
5. Les contradictions entre couches = le vrai signal
6. V4 = moteur de sélection d'outils. Sommet escalier = vue plongeante → briques filtrées → AI grimpe
7. P=NP est S3-S4, pas S6. Le pont existe. Les 3 routes classiques sont P5.
8. **S-2 = "glyphes inventés POUR la science"** — pas juste math. Inclut fossiles alchimiques et symboles scientifiques actifs
9. **Pont S-2↔S0 = BIPARTITE** — JAMAIS fusionner les Laplaciens S-2 et S0. Table de correspondance pondérée, pas graphe unique
10. **WT2 sauvegarde per-paper** — ne plus jeter le détail par paper comme S-1 l'a fait
11. **Blind test cutoff 2015 = MORT** — OpenAlex retags rétroactifs = fuite temporelle. Ne plus valider par cutoff. Validation = V3 météorites (propre)
12. **S-2 = horloge, S0 = carte** — S-2 est propre temporellement (LaTeX ne change pas). S0 pour naviguer, S-2 pour dater/prédire
13. **Grimpeur = solveur Rubik's cube** — mapper glyphes/domaines/escaliers sur structure de cube, utiliser algos de résolution existants (théorie des groupes). Voir Graine 2 enrichie
14. **PMC = après V3** — pas de nouveau téléchargement tant que le grimpeur ne le demande pas. arXiv suffit pour V2-V3

## PONT MUNINN ↔ YGGDRASIL (session 21, 8 mars 2026)

**Contexte sobre**: Muninn = compresseur mémoire LLM (repo frère). Son mycelium
tracke les co-occurrences entre concepts **au niveau paragraphe** (pas paper entier).
Yggdrasil tracke les co-occurrences **au niveau paper entier** (WT1, 108M paires).

**Pourquoi c'est complémentaire (pas redondant)**:
- Yggdrasil (WT1): "ces 2 concepts apparaissent dans le même paper" → granularité grossière, 348M papers
- Muninn (mycelium): "ces 2 concepts apparaissent dans le même paragraphe" → granularité fine, fusions auto
- Les fusions Muninn = concepts inséparables (toujours dans le même paragraphe)
- Les absences Muninn = structural holes paragraphe-level (plus fins que paper-level)

**Point de jonction = WT3 (la Bible)**:
1. WT1 donne la carte macro (concept × concept, paper-level)
2. WT2 donne le pont S-2↔S0 (glyph × concept, per-paper)
3. Muninn donnerait la carte micro (concept × concept, paragraphe-level)
4. Les trois ensemble = zoom multi-résolution sur la même réalité

**Réponses aux questions de Muninn**:
- Concept index = keywords hiérarchiques OpenAlex (65K), pas du texte brut
- Matrice co-occ = WT1, 108M paires sparse, poids 1/C(n,2), JSON compressé par chunks
- arXiv = LaTeX source (.tex), pas PDF — on parse les math environments
- Structural holes = Laplacien spectral (vecteurs propres), pas juste absence dans la matrice
- 65K × 65K = sparse (2.5% fill), Laplacien sur top-K=64 voisins, pas matrice pleine
- Scan S0 = ~48h sur 348M papers

**Décision**: Muninn sur WT3, APRÈS que WT2 soit fini et WT3 assemblé. Pas avant.

## TODO
- [x] Winter tree scanner V2 (65K, 581/581 chunks, 348M papers) — session 10
- [x] Film V4 (1,534 frames + 65,021 births) — session 10
- [x] 9 espèces K=9 + 17 graines S-2 — session 10
- [x] Blind test V2 (65K, p=3.4e-12) — session 11
- [x] Prédictions 2025 (108M paires, 41% WTF) — session 11
- [x] Glyph Laplacian (d=8.78, Recall@100=70%) — session 12
- [x] Mirror pairs (19/20, d=0.925) — session 13
- [x] Archéologie S-2 (194 glyphes, Cajori) — session 14
- [x] arXiv mapper (309/309, 4.3M arXiv) — session 15
- [x] Pipeline S-2 COMPLET (420 arXiv + 39 PMC → Laplacien → s2_spectral.json) — sessions 12-15
- [x] V3 météorites codé (engine/meteorites.py) — session 7
- [x] Grand ménage: audit complet, 21K→65K officiel — session 18
- [x] S-1 Métiers COMPLET (416/416, 858K papers) — session 19
- [x] S-2 fossiles + scope étendu (~1,500 total) — session 20
- [x] WT2: scanner per-paper {glyphs, domain, concepts} — scanner construit, chunk 1 OK (11,834 papers, 539K paires bipartite)
- [x] WT2: scan complet (416/416 chunks) — session 22, 832K papers
- [x] WT3: La Bible COMPLET — 833K papers, 885M cooc, 69.4M cooc_global, 8 indexes — session 27
- [ ] WT4: Forme 3D (WT3 prêt, lancer quand décidé)
- [ ] Muninn sur WT3 (compression/accélération)
- [ ] Recalculer escaliers spectraux sur 65K (200 geo + 69 passe-partout actuels basés sur 21K)
- [ ] PMC bulk download + scan (bio/med/chimie — quand le grimpeur a besoin de disciplines hors arXiv)
- [ ] Refaire viz avec 3 couches du sol complètes
- [ ] V3: mesurer météorites sur frames réelles — calibrage du grimpeur
- [ ] V4: le grimpeur (mapping Rubik's cube — voir Graine 2 enrichie)

## FICHIERS CLÉS — ACTIFS

### S-2 Glyphes
| Fichier | Rôle |
|---------|------|
| engine/glyphs/ (8 fichiers) | Pipeline S-2: registry, parsers, scanners, laplacian, frames, integrate |
| data/core/glyph_registry.json | 1,337 glyphes (333 KB) |
| data/core/s2_spectral.json | 617 glyphes actifs, positions spectrales (72 KB) |
| data/core/glyph_origins.json | 194 origines archéologiques (166 KB) |
| data/core/glyph_fossils.json | 116 fossiles alchimiques + 10 actifs non-math + 7 graines (40 KB) |
| data/core/seeds_s2.json | 17 graines + sources + mutations (13 KB) |
| data/scan/glyph_chunks/ | 420 chunks arXiv scannés |
| data/scan/pmc_glyph_chunks/ | 39 chunks PMC scannés |
| data/scan/glyph_positions.json | Positions spectrales 2D (249 KB) |
| data/scan/glyph_frames.json | 356 frames timeline (73 KB) |

### S-1 Métiers (COMPLET)
| Fichier | Rôle |
|---------|------|
| engine/professions/domain_glyph_scanner.py | Scanner domain×glyph (18 KB) |
| engine/professions/build_domain_lookup.py | Lookup arXiv→domain (5.4 KB) |
| data/scan/s1_chunks/chunk_NNN/ | 416/416 chunks (domain_profile + domain_cooc + meta, 967 MB) |
| data/scan/s1_tree.json | Index S-1 (73 KB) |
| data/scan/arxiv_domain_lookup.json.gz | 2.8M arXiv→domain mappings (15 MB) |

### S0 Concepts (65K)
| Fichier | Rôle |
|---------|------|
| engine/topology/winter_tree_scanner.py | Scanner V2: 65K concepts, filtres, 1/C(n,2) (568 lignes) |
| engine/topology/frame_builder.py | Film: 1,534 frames (9.5 KB) |
| engine/topology/concept_births.py | 65,021 births (4.1 KB) |
| data/scan/chunks/chunk_NNN/ | 581 chunks (cooc + activity + meta) |
| data/scan/concepts_65k.json | Lookup 65,026 concepts (7 MB) |
| data/scan/species_65k.json | 9 espèces K=9 (7.5 MB) |
| data/scan/frames.json | 1,534 frames (2.6 MB) |
| data/scan/concept_births.json | 65,021 births (1.7 MB) |
| data/scan/early_concepts.json | 619 concepts pré-1100 (165 KB) |
| data/scan/winter_tree.json | Index principal (8 MB) |

### Blind tests & Prédictions
| Fichier | Rôle |
|---------|------|
| blind_test_v2/ | Blind test V2: 65K, cutoff 2015, p=3.4e-12 (487 MB) |
| blind_test_v2/snapshot_2015_65k.npz | Matrice ≤2015 (457 MB) |
| predictions_2025/ | Prédictions: 108M paires, P4 Uzzi (638 MB) |
| predictions_2025/snapshot_full.npz | Matrice complète (615 MB) |

### WT2 — Bridge S-2 <-> S0 (EN COURS)
| Fichier | Rôle |
|---------|------|
| engine/topology/wt2_scanner.py | Scanner per-paper: glyphs + domain + concepts (~350 lignes) |
| data/scan/wt2_tree.json | Index 416 chunks, 1093 tars, 531.4 GB |
| data/scan/wt2_chunks/chunk_NNN/ | papers.json.gz + bipartite.json.gz + meta.json par chunk |

### Spectral
| Fichier | Rôle |
|---------|------|
| engine/analysis/glyph_laplacian.py | Laplacien spectral K=64 (27 KB) |
| data/scan/glyphs.json | Eigenvecteurs (175 KB) |
| data/scan/spectral_predictions.json | 3,348 prédictions inter-espèces (947 KB) |
| data/scan/spectral_embeddings.npy | Embeddings 65K × 64 (32 MB) |
| data/scan/spectral_blind_test.json | Blind test spectral (12 KB) |

### arXiv Pipeline
| Fichier | Rôle |
|---------|------|
| engine/mining/arxiv_openalex_mapper.py | Mapper OpenAlex→arXiv (18 KB) |
| data/scan/arxiv_map_chunks/ | 309 chunks (4.3M arXiv matchés) |
| data/scan/arxiv_mapper_state.json | État mapper (complet, 133 KB) |

### V3 Météorites (code prêt, mesure en attente)
| Fichier | Rôle |
|---------|------|
| engine/meteorites.py | Sedov-Taylor + OHLC + 7 deltas (28 KB) |
| docs/formulas.tex | Toutes les formules sourcées DOI (20 KB) |

### Legacy (garder mais ne plus baser du neuf dessus)
| Fichier | Pourquoi legacy |
|---------|----------------|
| data/core/strates_export_v2.json | 21K = ancien filtre keyword, remplacé par 65K |
| data/core/concept_index.json | Index inverse pour les 21K (20,932 entries) |
| engine/topology/cooccurrence_scan.py | Ancien scan 85×85 domaines |
| data/topology/escaliers_spectraux.json | Basé sur 21K, à recalculer sur 65K |
| viz/yggdrasil_rain_v3.html | Viz basée sur 21K |
| blind_test/ | V1, 100 concepts, remplacé par V2 (65K) |
| engine/mining/mine_concepts.py | Script qui a créé les 21K |

## INSIGHT CLÉ: LIFECYCLE DES PATTERNS
```
P4 (trou) → P1 (pont) → P3 (explosion) → P2 (dense/mature)
```
6 percées connues classées P2 = le pont est devenu infrastructure.

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

## GRAINES SESSION 16 — 4 mars 2026 (Sky, bourré, 2h du mat)

Deux idées brutes capturées. À relire sobre.

### Graine 1 — Mort = figé, Vivant = mute

**L'insight**: en math classique, un théorème prouvé est "vivant" (C1, validé).
Mais dans Yggdrasil c'est l'inverse — un concept figé est **mort**. Un concept qui **mute**
(qui change de connexions, qui crée de nouveaux ponts) est **vivant**.

Implication V4: le grimpeur cherche les briques qui **mutent activement**.
Les concepts "morts" (figés) = outils fiables mais inertes.
Les concepts "vivants" (qui mutent) = outils instables mais c'est LÀ que les P4 se ferment.

> Statut: **C2** — à valider avec les données

### Graine 2 — Conjecture Rubik (auto-correction convergente) — ENRICHIE session 20

**L'insight**: le grimpeur V4 = solveur de Rubik's cube sur la topologie.

```
ÉTAT(t) → identifier PATTERN → appliquer MOUVEMENT → sauver ÉTAT(t+1) → répéter
```

Propriétés:
1. **Fini**: nombre d'états borné (65,026 concepts × 9 strates)
2. **Auto-correctif**: chaque P5 = chemin éliminé = l'espace se compresse
3. **Patterns répétables**: catalogue fini de mouvements
4. **Couche par couche**: résoudre S-2 → S-1 → S0 sans casser les couches précédentes

**MAPPING CONCRET (session 20)**:
Le Rubik's cube n'est PAS une métaphore. C'est le framework mathématique.

```
CUBE                          YGGDRASIL
─────────────────────────────────────────
Faces (6)                  =  Domaines/espèces (S-1)
Centre de face (fixe)      =  Glyphes purs d'un domaine (1 seul métier)
Arêtes (2 faces)           =  Lianes géographiques (200, relient 2 domaines)
Coins (3+ faces)           =  Passe-partout (69, traversent 3+ domaines)
État non résolu            =  Trous structurels dans le réseau
État résolu                =  Réseau complet (pas de trous P4)
Mouvements de résolution   =  Compositions de glyphes existants
God's number (20 max)      =  Nb max de compositions pour combler un trou ?
```

**Réduction de l'espace**: pas 1,337 glyphes comme mouvements. Seulement ~269 escaliers (200 geo + 69 passe-partout) = les pièces mobiles du cube. Les centres (glyphes d'un seul domaine) sont fixes.

**Algorithmes de résolution = EXISTANTS**: théorie des groupes, permutations, 50 ans d'optimisation. Pas besoin d'inventer. Juste de MAPPER.

**Calibrage**: V3 (météorites) = vérité terrain. Les explosions passées correspondent-elles à des "rotations" du cube ?

**Insight clé**: les chercheurs n'inventent quasi jamais de nouveaux glyphes. Ils RECOMBINENT des glyphes existants. Le Rubik's cube a toutes ses pièces depuis le début — on les tourne pour résoudre.

> Statut: **C2 forte, mapping concret trouvé** — formalisation = mapper les données sur un cube de la bonne taille + brancher un solveur existant

## VISION V4 — LE GRIMPEUR

### L'insight fondamental
Les escaliers ne sont pas juste des connexions. Ce sont des **points de vue**.
Depuis le sommet, on regarde EN BAS et on voit quelles briques S0 sont connectées.
La carte filtre les outils pour toi.

### Le mécanisme
```
1. Prendre un problème ouvert (conjecture S3+)
2. Le positionner sur la carte topologique (65K spectral)
3. Trouver les escaliers les plus proches
4. Monter au sommet → les briques S0 visibles = le "sac à dos" filtré
5. L'AI compose des chemins de preuves avec ces briques
6. Si échec → P5 = cul-de-sac confirmé → réduction de l'espace
```

### Ce que V4 est VRAIMENT
Un **moteur de sélection d'outils automatique pour n'importe quel problème**.
Tu donnes un problème → il te donne le sac à dos optimal de briques → l'AI grimpe.

### Statut: VISION — dépend de V3 (météorites sur frames réelles)
Pas de saut. Les racines d'abord. Toujours.

## ROADMAP
```
S-2 COMPLET ✅ (~1,500 glyphes + fossiles)
  → S-1 COMPLET ✅ (416/416, 858K papers)
    → WT2 COMPLET ✅ (416/416, 832K papers)
      → WT3 La Bible ✅ COMPLET (16 mars 2026)
        → WT4 Forme 3D ✅ COMPLET (66K noeuds)
          → Impact Scale ✅ COMPLET (833K papers 0-10)
            → V3 météorites ← ON EST ICI (refonte: caillou dans la mare)
              → Heat kernel sur WT4 Laplacien
                → V4 le grimpeur
```

## MÉCANIQUES CLAUDE

<rules>
Boîte à outils de prompting Sky↔Claude.
</rules>

### 1. SANDWICH (Primauté + Récence)
Instructions critiques en HAUT, rappelées en BAS. Rappeler les 3 règles clés tous les 15-20 messages.

### 2. AMORCE (Bombe de glisse output)
Donner les 3 premières lignes de l'output attendu + "continue".

### 3. MONTRE, EXPLIQUE PAS
2 exemples concrets (bon + mauvais) battent 2 paragraphes d'instructions.

### 4. POSITIF AVANT NÉGATIF
"Fais Y" avant "Ne fais pas X". Claude lit le verbe dans l'interdiction.

### 5. XML TAGS (Murs d'attention)
`<rules>`, `<format>`, `<context>` compartimentent l'attention.

### 6. CHUNKING
Max 25-30 items par génération. Commit entre chaque chunk.

### 7. RAPPEL MID-SESSION
Tous les 15-20 messages: 3 règles clés, pas tout.

| # | Technique | Quand |
|---|-----------|-------|
| 1 | Sandwich | Tout prompt de mission |
| 2 | Amorce | Format JSON/code strict |
| 3 | Montre | Toute mission avec format |
| 4 | Positif d'abord | Toute interdiction |
| 5 | XML tags | Prompts 50+ lignes |
| 6 | Chunking | Données/code long |
| 7 | Rappel | Sessions 40+ messages |

> "Tu mets la bombe de glisse dans le tube avant, et le cousin passe le câble
> en un seul tir là où normalement il faudrait trois instances." — Sky, mars 2026

<rules>
RAPPEL (sandwich fermé):
- Mycelium = S-2 à S0 uniquement. Pas au-dessus.
- S0 = 65,026 concepts. Les 21K sont obsolètes.
- Token JAMAIS affiché.
</rules>
