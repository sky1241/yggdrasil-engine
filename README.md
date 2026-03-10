# Yggdrasil Engine

**Spectral engine for scientific cartography and prediction.**

9 strates (S-2 to S6) | 65,026 concepts | ~1,500 glyphs | 108M pairs | 348M papers

---

## Signal

| Test | Result | p-value |
|------|--------|---------|
| Blind test spectral (cutoff 2015) | Cohen's d = 5.76 | 7.0e-11 |
| Mirror pairs (strictest control) | 19/20 wins, d = 0.925 | 6.68e-06 |
| Recall top 0.1% (82M pairs) | 70% of breakthroughs found | -- |
| Predictions 2025 (top 100 INTER) | 41% WTF, 20/20 web-verified | -- |

---

## Architecture

### 9 Strates (Post's Arithmetical Hierarchy)

```
S6  CIEL        BB(n), Omega               incompressible
S5  ...         open conjectures            Sigma_5
S4  ...         ...                         Sigma_4
S3  ...         Poincare, Fermat            Sigma_3
S2  ...         active conjectures          Sigma_2
S1  ARBRE       296 decidable concepts      Sigma_1
S0  SOL         65,026 OpenAlex concepts    Delta_0 (100% C1)
S-1 METIERS     19 domains x 1,337 glyphs  scientific professions
S-2 GLYPHES     ~1,500 symbols (math + alchemical fossils)
```

### Key Principles

- **Mycelium** = co-occurrences, lives in S-2 to S0 (not above)
- **Winter Trees** = 3 index layers (WT1 concept x concept, WT2 per-paper, WT3 Bible)
- **S-2 and S0 Laplacians stay SEPARATE** -- the bridge is a bipartite table

---

## Project Structure

```
yggdrasil-engine/
|
|-- engine/                         # Core Python package
|   |-- core/                       # Foundations (symbols, holes, scisci, OpenAlex)
|   |-- glyphs/                     # S-2 pipeline (registry, LaTeX parser, scanners)
|   |-- professions/                # S-1 pipeline (19 domains x 1,337 glyphs)
|   |-- topology/                   # Network structure (winter trees, species, spectral)
|   |-- mining/                     # Data extraction (arXiv, OpenAlex mapper)
|   |-- analysis/                   # Validation & analysis (blind tests, mirror pairs)
|   |-- pipeline/                   # Batch validation pipelines
|   +-- viz/                        # Visualization generators
|
|-- data/
|   |-- core/                       # Foundational data (glyph registry, fossils, origins)
|   |-- scan/                       # Winter tree scan outputs (gitignored)
|   |-- bible/                      # WT3 SQLite database (gitignored)
|   |-- topology/                   # Winter tree metadata & stats
|   +-- results/                    # Analysis results
|
|-- experiments/                    # Reproducible experiments
|   |-- blind_test_v1/              # Blind test V1 (legacy, 21K concepts)
|   |-- blind_test_v2/              # Blind test V2 (65K concepts, cutoff 2015)
|   +-- predictions_2025/           # 108M-pair predictions (P4 Uzzi, INTER/INTRA)
|
|-- viz/                            # Interactive HTML visualizations
|   |-- god_cube.html               # God Cube polytope (k-core STEM)
|   |-- yggdrasil_rain_v4.html      # Mycelium timelapse (3D cube, 1,534 frames)
|   |-- escaliers_spectraux.html    # Spectral staircases (3D lianes)
|   |-- hypertree_decomp.html       # Hypertree decomposition
|   |-- data/                       # JSON data for visualizations
|   |-- lib/                        # JS dependencies (three.js)
|   +-- legacy/                     # Archived visualizations
|
|-- docs/
|   |-- SOL.md                      # Source of truth (inter-session state)
|   |-- GOD_CUBE.md                 # God's Algorithm theory
|   |-- SCIENTOMETRICS.md           # Literature survey & recoverable formulas
|   |-- TODO.md                     # Roadmap
|   |-- RAPPORTS/                   # Session reports
|   |-- research/                   # Theory & discoveries
|   |-- reference/                  # Formulas, roadmaps
|   +-- briefs/                     # Prompts & briefings
|
|-- tests/                          # Unit tests
|-- hooks/                          # Git hooks (winter-tree auto-update)
|-- server.py                       # Flask dev server
|-- pyproject.toml                  # Python packaging & tool config
+-- requirements.txt                # Pinned dependencies
```

---

## Populations

| Strate | Population | Source | Status |
|--------|-----------|--------|--------|
| S-2 Glyphs | ~1,500 (1,337 math + 116 fossils + 10 active + 7 seeds) | arXiv + PMC + Cajori | DONE |
| S-1 Professions | 19 domains x 1,337 glyphs | 416/416 chunks, 858K papers | DONE |
| S0 Concepts | 65,026 | OpenAlex snapshot (692 GB) | DONE |
| S1-S6 Tree | 296 concepts | Arithmetical hierarchy | DONE |
| WT1 | 108M concept x concept pairs | 581/581 chunks, 348M papers | DONE |
| WT2 | per-paper {glyphs, domain, concepts} | 416/416 chunks, 832K papers | DONE |
| WT3 Bible | WT1 + WT2 joined in SQLite | papers + bipartite + cooc | DONE |

---

## 5 Structural Patterns

| Pattern | Type | Lifecycle |
|---------|------|-----------|
| **P1** | Inter-domain bridge | Explosion |
| **P2** | Dense stable hub | Mature |
| **P3** | Theory x Tool | Growth |
| **P4** | Structural hole | **FUTURE** |
| **P5** | Anti-signal | Death |

```
P4 (hole) -> P1 (bridge) -> P3 (explosion) -> P2 (dense/mature)
```

---

## 3 Types of Structural Holes

| Type | Mechanism | Detection |
|------|-----------|-----------|
| **A -- Technical** | Everyone KNOWS, nobody CAN | stagnant fitness |
| **B -- Conceptual** | Nobody thinks to CONNECT | co-occurrence = 0 |
| **C -- Perceptual** | The tool EXISTS, nobody BELIEVES | high fitness, low citations |

---

## 9 Species (spectral clustering K=9)

| # | Species | Examples |
|---|---------|----------|
| 0 | Materials / Chemistry | Perovskites, polymers |
| 1 | Geography / Environment | Climate, ecology |
| 2 | Medicine / Internal | Oncology, cardiology |
| 3 | Psychology / Business | Cognitive science, economics |
| 4 | Computer Science / Math | ML, algebra, algorithms |
| 5 | Biology / Botany | Genetics, plant science |
| 6 | Humanities / Political | History, sociology |
| 7 | Cell Biology / Anatomy | Proteins, neuroscience |
| 8 | Physics / Optics | Quantum, photonics |

---

## Quickstart

```bash
pip install -e .                  # install engine package
pip install -e ".[server]"        # with Flask server
pip install -e ".[dev]"           # with dev tools (pytest, ruff)

python server.py                  # http://localhost:5000
```

### Run experiments

```bash
# Requires local OpenAlex snapshot on E:\openalex\data\ (692 GB)
python experiments/predictions_2025/step1_full_scan.py
python experiments/predictions_2025/step2_species_full.py
python experiments/predictions_2025/step3_p4_both.py
python experiments/predictions_2025/step4_report.py
```

### Run tests

```bash
pytest tests/
```

---

## Roadmap

- [x] **V1** -- Static map: 21K symbols, 9 continents, 87% validation
- [x] **V2** -- Timelapse: 1,534 frames, 65K concepts, 3D cube film
- [x] **Predictions 2025** -- 108M pairs, P4 Uzzi, 41% WTF
- [x] **S-2 Pipeline** -- 1,500 glyphs, spectral Laplacian, blind test d=5.76
- [x] **S-1 Professions** -- 19 domains x 1,337 glyphs, 416 chunks
- [x] **Mirror Pairs** -- Strictest control: 19/20, d=0.925, p=6.68e-06
- [x] **WT2** -- Per-paper index (416/416, 832K papers)
- [x] **WT3 Bible** -- WT1+WT2 joined in SQLite (833K papers, 110M bipartite)
- [ ] **V3 Meteorites** -- Sedov-Taylor + OHLC on real frames
- [ ] **V4 God Cube** -- Polytope solver on spectral staircases

---

## License

MIT

---

Sky -- Versoix, CH -- 2025-2026
