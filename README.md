# YGGDRASIL ENGINE

**Moteur spectral de cartographie et prediction scientifique**

9 strates (S-2 a S6) | 65,026 concepts | 1,500 glyphes | 108M paires | 348M papers

---

## Signal

| Test | Resultat | p-value |
|------|----------|---------|
| Blind test spectral (cutoff 2015) | Cohen's d = 5.76 (honest) | 7.0e-11 |
| Mirror pairs (controle le + strict) | 19/20 wins, d = 0.925 | 6.68e-06 |
| Recall top 0.1% (82M paires) | 70% des percees retrouvees | — |
| Predictions 2025 (top 100 INTER) | 41% WTF, 20/20 web-verified | — |

---

## Architecture — 9 Strates (Hierarchie Arithmetique de Post)

```
S6  CIEL        BB(n), Omega               incompressible
S5  ...         conjectures ouvertes        Sigma_5
S4  ...         ...                         Sigma_4
S3  ...         Poincare, Fermat            Sigma_3
S2  ...         conjectures actives         Sigma_2
S1  ARBRE       296 concepts decidables     Sigma_1
S0  SOL         65,026 concepts OpenAlex    Delta_0 (100% C1)
S-1 METIERS     19 domaines x 1,337 glyphes professions scientifiques
S-2 GLYPHES     ~1,500 symboles (math + fossiles alchimiques)
```

- **Mycelium** = co-occurrences, vit dans S-2 a S0 (pas au-dessus)
- **Winter Trees** = 3 couches d'index (WT1 concept x concept, WT2 per-paper, WT3 Bible)
- **Laplaciens S-2 et S0 restent SEPARES** — le pont = table bipartite

---

## Structure du projet

```
yggdrasil-engine/
|
|-- engine/                         <- le moteur
|   |-- core/                       <- fondations
|   |   |-- symbols.py              <- symboles + strates
|   |   |-- holes.py                <- detection 3 types de trous
|   |   |-- scisci.py               <- Wang-Barabasi, Uzzi, Wu-Evans
|   |   +-- openalex.py             <- API OpenAlex
|   |-- mining/                     <- extraction de donnees
|   |   |-- mine_concepts.py        <- minage concepts OpenAlex
|   |   |-- map_concepts.py         <- mapping symboles -> OpenAlex IDs
|   |   |-- cleanup_s0.py           <- cleanup S0
|   |   |-- arxiv_openalex_mapper.py <- arXiv <-> OpenAlex (692 GB)
|   |   +-- build_arxiv_tree.py     <- inventaire arXiv tars
|   |-- topology/                   <- structure du reseau
|   |   |-- winter_tree_scanner.py  <- WT1: 65K x mois, 581 chunks
|   |   |-- wt2_scanner.py          <- WT2: per-paper glyph x concept
|   |   |-- frame_builder.py        <- 1,534 frames (an 1000->2024)
|   |   |-- concept_births.py       <- 65,021 naissances de concepts
|   |   |-- species_identifier.py   <- 9 especes spectral K=9
|   |   +-- escaliers_spectraux.py  <- lianes geo + passe-partout
|   |-- glyphs/                     <- strate S-2
|   |   |-- glyph_registry.py       <- registre 1,337 glyphes math
|   |   |-- latex_parser.py         <- extraction LaTeX
|   |   |-- arxiv_scanner.py        <- scan arXiv (420 chunks)
|   |   |-- pmc_scanner.py          <- scan PMC (39 chunks)
|   |   |-- glyph_laplacian.py      <- Laplacien spectral S-2
|   |   +-- glyph_frame_builder.py  <- frames S-2
|   |-- professions/                <- strate S-1
|   |   |-- domain_glyph_scanner.py <- 19 domaines x 1,337 glyphes
|   |   +-- build_domain_lookup.py  <- lookup domaine par paper
|   |-- analysis/                   <- analyses & validation
|   |   |-- glyph_laplacian.py      <- blind test spectral V2
|   |   |-- mirror_pairs_test.py    <- test miroir (controle strict)
|   |   |-- validation_honest.py    <- 3 corrections de biais
|   |   |-- meteorites.py           <- Sedov-Taylor + OHLC
|   |   +-- scan_philippe_v2.py     <- test Philippe Schuchert
|   |-- pipeline/                   <- validation V1 (legacy)
|   +-- vizgen/                     <- generation de viz
|
|-- data/
|   |-- core/                       <- donnees fondamentales
|   |   |-- glyph_registry.json     <- 1,337 glyphes
|   |   |-- glyph_fossils.json      <- 116 alchimiques + 10 actifs + 7 graines
|   |   |-- glyph_origins.json      <- 194 symboles traces (Cajori)
|   |   |-- s2_spectral.json        <- Laplacien S-2
|   |   +-- concepts_*.json         <- index concepts
|   |-- scan/                       <- winter trees + scans
|   |   |-- chunks/                 <- WT1: 581 chunks (cooc + activity)
|   |   |-- s1_chunks/              <- S-1: 416 chunks (19 dom x 1337 glyphes)
|   |   |-- glyph_chunks/           <- S-2: 420 chunks arXiv
|   |   |-- spectral_blind_test.json
|   |   |-- mirror_pairs_test.json
|   |   +-- spectral_embeddings.npy <- 64 eigenvectors
|   +-- results/                    <- resultats d'analyses
|
|-- predictions_2025/               <- predictions V2 (pipeline complet)
|-- blind_test_v2/                  <- blind test V2 (65K, cutoff 2015)
|-- _legacy/                        <- archives (blind test V1, etc.)
|
|-- viz/                            <- visualisations HTML
|   |-- yggdrasil_rain_v4.html      <- Film mycelium cube 3D
|   +-- escaliers_spectraux.html    <- Lianes 3D
|
|-- docs/
|   |-- SOL.md                      <- source de verite inter-sessions
|   |-- TODO.md                     <- roadmap par session
|   |-- RAPPORTS/                   <- journaux de session
|   |-- research/                   <- theorie & decouvertes
|   |-- reference/                  <- formules, roadmaps
|   +-- briefs/                     <- prompts & briefings
|
|-- hooks/                          <- pre-commit (winter-tree auto-update)
|-- tests/                          <- tests unitaires
+-- server.py                       <- Flask server
```

---

## Populations

| Strate | Population | Source | Status |
|--------|-----------|--------|--------|
| S-2 Glyphes | ~1,500 (1,337 math + 116 fossiles + 10 actifs + 7 graines) | arXiv + PMC + Cajori | COMPLET |
| S-1 Metiers | 19 domaines x 1,337 glyphes | 416/416 chunks, 858K papers | COMPLET |
| S0 Concepts | 65,026 | OpenAlex snapshot (692 GB) | COMPLET |
| S1-S6 Arbre | 296 concepts | Hierarchie arithmetique | COMPLET |
| WT1 | 108M paires concept x concept | 581/581 chunks, 348M papers | COMPLET |
| WT2 | per-paper {glyphs, domain, concepts} | en cours (~415 chunks) | EN COURS |

---

## 5 Patterns

| Pattern | Type | Lifecycle |
|---------|------|-----------|
| **P1** | Pont inter-domaines | Explosion |
| **P2** | Hub dense stable | Mature |
| **P3** | Theorie x Outil | Croissance |
| **P4** | Trou ouvert | **FUTUR** |
| **P5** | Anti-signal | Mort |

```
P4 (trou) -> P1 (pont) -> P3 (explosion) -> P2 (dense/mature)
```

---

## 3 Types de Trous Structurels

| Type | Mecanisme | Detection |
|------|-----------|-----------|
| **A — Technique** | Tout le monde SAIT, personne ne PEUT | fitness stagnante |
| **B — Conceptuel** | Personne n'a l'IDEE de connecter | co-occurrence = 0 |
| **C — Perceptuel** | L'outil EXISTE, personne n'y CROIT | fitness haute, citations basses |

---

## 9 Especes (spectral clustering K=9)

| # | Espece | Exemples |
|---|--------|----------|
| 0 | Materials / Chemistry | Perovskites, polymers |
| 1 | Geography / Environment | Climate, ecology |
| 2 | Medicine / Internal | Oncology, cardiology |
| 3 | Psychology / Business | Cognitive science, economics |
| 4 | Computer science / Math | ML, algebra, algorithms |
| 5 | Biology / Botany | Genetics, plant science |
| 6 | Humanities / Political | History, sociology |
| 7 | Cell biology / Anatomy | Proteins, neuroscience |
| 8 | Physics / Optics | Quantum, photonics |

---

## Lancer

```bash
pip install flask numpy scipy
python server.py
```

### Predictions 2025

```bash
# Requiert snapshot OpenAlex sur E:\openalex\data\ (692 GB)
python predictions_2025/step1_full_scan.py
python predictions_2025/step2_species_full.py
python predictions_2025/step3_p4_both.py
python predictions_2025/step4_report.py
python predictions_2025/step5_collision.py
```

---

## Roadmap

- [x] **V1** — Carte statique: 21K symboles, 9 continents, 87% validation
- [x] **V2** — Timelapse: 1,534 frames, 65K concepts, film cube 3D
- [x] **Predictions 2025** — 108M paires, P4 Uzzi, 41% WTF
- [x] **S-2 Pipeline** — 1,500 glyphes, Laplacien spectral, blind test d=5.76
- [x] **S-1 Metiers** — 19 domaines x 1,337 glyphes, 416 chunks
- [x] **Mirror Pairs** — Controle strict: 19/20, d=0.925, p=6.68e-06
- [ ] **WT2** — Per-paper index (en cours)
- [ ] **V3 Meteorites** — Sedov-Taylor + OHLC sur frames reelles
- [ ] **WT3 La Bible** — Jointure WT1+WT2, index unifie
- [ ] **V4 Le Grimpeur** — Solveur Rubik sur escaliers spectraux

---

Sky — Versoix, CH — 2025-2026
