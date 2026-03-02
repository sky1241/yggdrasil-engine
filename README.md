# 🌳 YGGDRASIL ENGINE

**Moteur de détection de trous structurels dans les réseaux scientifiques**

65,026 concepts × 9 espèces × 108M paires × 348M papers × P4 Uzzi z-scores

Blind test V2 (65K, cutoff 2015): **p = 3.4e-12** | Predictions 2025: **41% WTF** (top 100 verified)

## Architecture

```
CIEL (S6) ─── BB(n), Ω ─── incompressible
    │
    │   ☁️ conjectures flottent ici
    │
SOL (S0) ─── 65,026 concepts × 108M paires × 9 espèces ─── 100% C1
    │
    │   🌿 200 escaliers géographiques + 69 passe-partout
    │
MYCELIUM ─── 348M papers scannés × 1,534 frames (an 1000→2024) ─── connexions invisibles
```

## Résultats

| Métrique | V1 | V2 |
|----------|----|----|
| Concepts | 21,524 symboles | 65,026 concepts |
| Co-occurrence | 296M papers, 85×85 | 348M papers, 108M paires |
| Espèces | 9 continents manuels | 9 espèces spectral K=9 |
| Film | — | 1,534 frames (an 1000→2024) |
| Pipeline V1 | 87/100 (87%) | — |
| Blind test | p=0.00001, r=0.90 | p=3.4e-12, 82.7M paires |
| Predictions | — | Top 10K INTER+INTRA, P4 Uzzi |
| Analyse top 100 | — | 41% WTF, 30% intéressant, 18% banal |
| Escaliers | 200 geo + 69 passe-partout | — |
| Cross Physarum | 806 hubs, 1220 bridges, 1567 P4 | — |

### 9 Espèces (spectral clustering K=9)
| # | Espèce | Top collision |
|---|--------|--------------|
| 0 | Materials science / Chemistry | ×CS (43), ×Physics (45) |
| 1 | Geography / Environmental science | ×CS (43), ×Physics (52) |
| 2 | Medicine / Internal medicine | ×Physics (55), ×CS (52) |
| 3 | Psychology / Business | ×Physics (45), ×CS (33) |
| 4 | Computer science / Mathematics | ×Physics (82), ×Humanities (56) |
| 5 | Biology / Botany | ×Physics (34), ×CS (22) |
| 6 | Humanities / Political science | ×Physics (72), ×CS (56) |
| 7 | Cell biology / Anatomy | ×CS (12), ×Physics (6) |
| 8 | Physics / Optics | ×CS (82), ×Humanities (72) |

## 5 Patterns

| Pattern | Type | Lifecycle |
|---------|------|-----------|
| **P1** — Pont | Bridge inter-domaines, BC élevé | Explosion |
| **P2** — Dense | Hub stable, meshedness élevé | Mature |
| **P3** — Théorie×Outil | Explosion après validation instrumentale | Croissance |
| **P4** — Trou ouvert | Pont pas encore explosé | **FUTUR** |
| **P5** — Anti-signal | L'hyphe meurt, slope négative | Mort |

```
P4 (trou) → P1 (pont) → P3 (explosion) → P2 (dense/mature)
```

## 3 Types de Trous Structurels

| Type | Mécanisme | Détection |
|------|-----------|-----------|
| **A — Technique** | Tout le monde SAIT où aller, personne ne PEUT | fitness stagnante, D-index bas |
| **B — Conceptuel** | Personne n'a l'IDÉE de connecter | co-occurrence = 0, z-score << 0 |
| **C — Perceptuel** | L'outil EXISTE, personne n'y CROIT | fitness haute, citations basses |

## Structure

```
yggdrasil-engine/
├── engine/
│   ├── core/                        ← fondations
│   │   ├── symbols.py               ← symboles + strates
│   │   ├── holes.py                 ← détection 3 types de trous
│   │   ├── scisci.py                ← Wang-Barabási, Uzzi, Wu-Evans
│   │   └── openalex.py              ← API OpenAlex
│   ├── mining/                      ← extraction de données
│   │   ├── mine_concepts.py         ← minage 20,730 concepts OpenAlex
│   │   ├── map_concepts.py          ← mapping symboles → OpenAlex IDs
│   │   └── cleanup_s0.py            ← cleanup S0, Q1 vivant/musée
│   ├── topology/                    ← structure du réseau
│   │   ├── winter_tree_scanner.py   ← SCANNER V2: 65K × mois, 692 GB
│   │   ├── frame_builder.py         ← 1,534 frames depuis winter tree
│   │   ├── concept_births.py        ← 65,021 concept births
│   │   ├── build_cooccurrence.py    ← PLUIE V1: matrice depuis snapshot
│   │   ├── cooccurrence_scan.py     ← ancien scan 296M → 85×85
│   │   ├── escaliers_spectraux.py   ← lianes géo + passe-partout
│   │   ├── spectral_layout.py       ← laplacien normalisé
│   │   └── species_identifier.py    ← 5 curseurs Lehmann 2019
│   ├── pipeline/                    ← validation V1
│   │   ├── mycelium_full.py         ← mycelium 24 briques
│   │   └── pipeline_100.py          ← pipeline batch 1-100
│   └── analysis/                    ← analyses
│       ├── scan_philippe.py         ← test Philippe Schuchert
│       └── cross_physarum_wc.py     ← Physarum × works_count
├── predictions_2025/                ← PREDICTIONS V2
│   ├── step1_full_scan.py           ← scan 581 chunks → 108M paires
│   ├── step2_species_full.py        ← spectral K=9 → 9 espèces
│   ├── step3_p4_both.py             ← P4 Uzzi INTER + INTRA
│   ├── step4_report.py              ← top 1000 .txt lisibles
│   ├── step5_collision.py           ← matrice collision 9×9
│   ├── PREDICTIONS_2025.json        ← résumé complet
│   └── collision_matrix_full.json   ← matrices top 100/1000/P4 sum
├── blind_test/                      ← blind test V1 (100 concepts)
│   └── FINAL_REPORT.json            ← p=0.00001, r=0.90
├── blind_test_v2/                   ← blind test V2 (65K concepts)
│   └── FINAL_REPORT_V2.json         ← p=3.4e-12, 82.7M paires
├── data/
│   ├── core/                        ← données fondamentales
│   │   ├── strates_export_v2.json   ← 21,524 symboles
│   │   ├── seeds_s2.json            ← 17 graines S-2
│   │   └── concept_index.json       ← index inverse (20,932)
│   ├── scan/                        ← winter tree V2
│   │   ├── chunks/chunk_000→580/    ← 581 chunks (cooc + activity)
│   │   ├── frames.json              ← 1,534 frames (2.5 MB)
│   │   ├── concept_births.json      ← 65,021 births
│   │   ├── species_65k.json         ← 9 espèces K=9
│   │   └── concepts_65k.json        ← lookup 65K concepts
│   └── topology/                    ← données réseau V1
├── viz/                             ← visualisations
│   ├── yggdrasil_rain_v4.html       ← Film mycélium cube 3D
│   ├── yggdrasil_rain_v3.html       ← La Pluie v3
│   └── legacy/                      ← anciennes viz
├── docs/                            ← documentation
│   ├── SOL.md                       ← sync Sky↔Claude
│   └── TODO.md                      ← roadmap V1→V4
└── server.py                        ← Flask server
```

## Lancer

```bash
pip install flask numpy scipy
python server.py
# → http://localhost:5000 (viz v3)
# Pour v4 (film 3D): lancer depuis la RACINE du repo
```

### Predictions 2025 (pipeline complet)

```bash
# Requiert snapshot OpenAlex sur E:\openalex\data\ (692 GB)
python predictions_2025/step1_full_scan.py    # ~19 min, 108M paires
python predictions_2025/step2_species_full.py # spectral K=9
python predictions_2025/step3_p4_both.py      # P4 Uzzi INTER+INTRA
python predictions_2025/step4_report.py       # top 1000 .txt
python predictions_2025/step5_collision.py    # matrice 9×9
```

## Données

- 65,026 concepts OpenAlex (levels 0-5), 9 espèces spectral K=9
- 108,301,944 paires non-zero, 347,999,931 papers scannés
- 1,534 frames temporelles (an 1000→2024), 65,021 concept births
- 17 graines S-2 (10 chiffres + 7 symboles alchimiques, patient t=0 documenté)
- Strates basées sur la hiérarchie arithmétique (Post 1944)
- Validé V1: 100 tests pipeline (87%) + 32 découvertes historiques (97%)
- Blind test V2: Mann-Whitney p=3.4e-12, 82.7M paires, cutoff 2015
- Predictions 2025: top 10K INTER+INTRA, 41% WTF confirmés par web

---

## 🌿 LIANES — Les Escaliers de Secours

> "Perelman n'a pas pris l'ascenseur central. Il a pris la liane entropie."

### 2 types d'escaliers

| Type | Count | Description |
|------|-------|-------------|
| 🌿 Géographique | 200 | Position spectrale entre 2 continents distants |
| 🔑 Passe-partout | 69 | Multi-continent, utilisé partout |

### Distribution lianes

| Type | Count | Description |
|------|-------|-------------|
| 🌿🌿🌿 Universelle | 5 | 6+ continents (=, exp, ln, Σ, ∫) |
| 🌿🌿 Majeure | 29 | 4-5 continents |
| 🌿 Liane | 26 | 3 continents |
| 🌱 Pont | 9 | 2 continents |
| · Local | 480 | 1 continent |

Validation: 9/10 découvertes S3 utilisent des lianes multi-continents.
Seule exception: CRISPR (pont biologique pur, pas mathématique).

---

## 🏔️ VISION V4 — Le Grimpeur

> "On ne casse pas la serrure. On fait passer le câble par un autre chemin."

Les sommets d'escaliers = **vues plongeantes** sur les briques S0 connectées.
L'AI grimpe avec le bon sac à dos filtré par la topologie.

```
Problème ouvert → positionnement carte → escaliers proches
  → vue plongeante → sac à dos S0 filtré → AI compose des chemins
    → échec = P5 local → réduction espace → autre sommet
```

P=NP est S3-S4, pas S6. Les 3 routes classiques sont P5. Le moteur cherche les P4.

## Roadmap

- [x] **V1** — Carte statique: 21K symboles, 9 continents, 87% validation
- [x] **V2** — Timelapse: 1,534 frames, 65K concepts, 9 espèces, film cube 3D
- [x] **Predictions 2025** — 108M paires, P4 Uzzi, top 10K INTER+INTRA, 41% WTF
- [ ] **V3** — Candlesticks OHLC: mesurer l'impact des météorites sur les frames
- [ ] **Glyph Laplacian** — Décomposition S0→S-2, laplacien spectral sur glyphes
- [ ] **V4** — Le Grimpeur: moteur de sélection d'outils automatique

## Auteur

Sky — Versoix, CH — 2025-2026
