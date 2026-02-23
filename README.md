# 🌳 YGGDRASIL ENGINE

**Moteur de détection de trous structurels dans les réseaux scientifiques**

21,524 symboles × 7 strates × 9 continents × 5 patterns × 24 briques mycelium

Test semi-aveugle 2015→2025: **p = 0.00001**, effect size r = 0.90

## Architecture

```
CIEL (S6) ─── BB(n), Ω ─── incompressible
    │
    │   ☁️ conjectures flottent ici
    │
SOL (S0) ─── 21,524 symboles (794 originaux + 20,730 minés OpenAlex) ─── 100% C1
    │
    │   🌿 200 escaliers géographiques + 69 passe-partout
    │
MYCELIUM ─── Physarum (24 briques) + co-occurrence 296M papers ─── connexions invisibles
```

## Résultats

| Métrique | Valeur |
|----------|--------|
| Symboles total | 21,524 (794 originaux + 20,730 minés) |
| Vivant / Musée | 16,382 (77%) / 4,846 (23%) |
| Continents | 9 (avec 85 domaines) |
| Co-occurrence | 296M papers scannés → matrice 85×85 |
| Pipeline 100 tests | 87/100 (87.0%) |
| Blind test 2015→2025 | p = 0.00001, r = 0.90, recall@100 = 50% |
| Escaliers | 200 géographiques 🌿 + 69 passe-partout 🔑 |
| Cross Physarum | 806 isolated hubs, 1,220 hidden bridges, 1,567 P4 voids |

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
│   │   ├── symbols.py               ← 794 symboles, 7 strates
│   │   ├── holes.py                 ← détection 3 types de trous
│   │   ├── scisci.py                ← Wang-Barabási, Uzzi, Wu-Evans
│   │   └── openalex.py              ← API OpenAlex (250M+ papers)
│   ├── mining/                      ← extraction de données
│   │   ├── mine_concepts.py         ← minage 20,730 concepts OpenAlex
│   │   ├── map_concepts.py          ← mapping symboles → OpenAlex IDs
│   │   └── cleanup_s0.py            ← cleanup S0, Q1 vivant/musée
│   ├── topology/                    ← structure du réseau
│   │   ├── build_cooccurrence.py    ← PLUIE: 5,459×5,459 depuis 400GB
│   │   ├── cooccurrence_scan.py     ← scan 296M papers → matrice 85×85
│   │   ├── escaliers_spectraux.py   ← lianes géo + passe-partout
│   │   ├── spectral_layout.py       ← laplacien normalisé
│   │   ├── depth_map.py             ← carte de profondeur
│   │   └── fix_spectral.py          ← corrections spectrales
│   ├── pipeline/                    ← validation
│   │   ├── mycelium_full.py         ← mycelium 24 briques (7,912 lignes)
│   │   ├── bridge_mycelium.py       ← pont mycelium × 101 tests
│   │   ├── battery_mycelium.py      ← batterie tests mycelium
│   │   ├── pipeline_100.py          ← pipeline batch 1 (1-50)
│   │   ├── pipeline_batch2.py       ← pipeline batch 2 (51-100)
│   │   └── verify_32tests.py        ← 32 découvertes historiques
│   ├── analysis/                    ← analyses croisées
│   │   ├── analyze_pluie.py         ← post-analyse PLUIE
│   │   ├── cross_physarum_wc.py     ← Physarum × works_count
│   │   ├── cross_projects.py        ← lianes cross-projets
│   │   ├── cross_roots.py           ← racines cross-projets
│   │   ├── lianes.py                ← lianes multi-continents
│   │   └── fourier_infernal.py      ← Fourier × Infernal Wheel
│   └── vizgen/                      ← génération de viz
│       ├── gen_viz_v3.py            ← La Pluie v3
│       ├── gen_escaliers_3d.py      ← escaliers 3D Three.js
│       └── gen_viz_v2.py            ← La Pluie v2
├── blind_test/                      ← test semi-aveugle 2015→2025
│   ├── step1→step6                  ← pipeline 6 étapes
│   └── FINAL_REPORT.json            ← p=0.00001, r=0.90
├── data/
│   ├── core/                        ← données fondamentales
│   │   ├── strates_export_v2.json   ← 21,524 symboles + méta
│   │   └── openalex_map.json        ← mapping symboles → OpenAlex
│   ├── topology/                    ← données réseau
│   │   ├── domain_cooccurrence_matrix.json
│   │   ├── escaliers_unified.json   ← 200 géo + 69 passe-partout
│   │   └── domain_spectral_positions.json
│   ├── pipeline/                    ← résultats 100 tests
│   ├── discoveries/                 ← 20 découvertes majeures
│   ├── cross/                       ← analyses croisées
│   ├── lianes/                      ← données lianes
│   └── results/                     ← résultats batterie
├── viz/                             ← 10 visualisations HTML
│   ├── yggdrasil_rain_v3.html       ← La Pluie v3
│   ├── yggdrasil_escaliers_3d.html  ← escaliers 3D Three.js
│   ├── yggdrasil_rain_v2.html       ← La Pluie v2
│   └── legacy/                      ← anciennes viz
├── tests/                           ← 67+ tests
│   ├── test_pluie_bulletproof.py    ← 63 tests PLUIE
│   ├── test_engine.py               ← tests moteur
│   ├── verify_32tests.py            ← 32 découvertes
│   └── generate_mock_data.py        ← mock OpenAlex
├── docs/                            ← documentation
│   ├── SOL.md                       ← sync Sky↔Claude
│   ├── TODO.md                      ← roadmap V1→V4
│   ├── mycelium/                    ← recherche mycelium
│   └── ...
├── winter-tree.json                 ← arbre du projet (source de vérité)
└── server.py                        ← Flask server
```

## Lancer

```bash
pip install flask numpy scipy
python server.py
# → http://localhost:5000
```

### PLUIE — Co-occurrence depuis OpenAlex snapshot (400GB)

```bash
# Test rapide (mock)
python tests/generate_mock_data.py
YGG_WORKS_DIR="/tmp/mock_openalex/works" python engine/topology/build_cooccurrence.py --test 5

# Full run (6-12h)
python engine/topology/build_cooccurrence.py
python engine/analysis/analyze_pluie.py
```

## Données

- 21,524 symboles classifiés en 7 strates (S0-S6)
- 794 originaux + 20,730 minés depuis OpenAlex
- Strates basées sur la hiérarchie arithmétique (Post 1944)
- Validé: 100 tests pipeline (87%) + 32 découvertes historiques (97%)
- Blind test: Mann-Whitney p = 0.00001, effect size r = 0.90
- Co-occurrence: 296M papers, matrice 85×85 domaines
- Mycelium Physarum: 24 briques, flux optimaux, BC, meshedness

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
- [ ] **V2** — Timelapse: rejouer l'histoire de la science frame par frame
- [ ] **V3** — Candlesticks OHLC: mesurer l'impact des météorites scientifiques
- [ ] **V4** — Le Grimpeur: moteur de sélection d'outils automatique

## Auteur

Sky — Versoix, CH — 2025-2026

99 commits · 41 modules · 32K lignes Python · 10 visualisations · 273 fichiers
