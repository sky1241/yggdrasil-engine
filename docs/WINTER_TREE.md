# yggdrasil-engine — Winter Trees

## Vue d'ensemble

Trois couches de scan, chacune un arbre hivernal (graphe de co-occurrences).

### WT1 — Concept x Concept (S0↔S0) — COMPLET
- **581/581 chunks**, 348M papers, 108M paires non-zero
- Scanner: `engine/topology/winter_tree_scanner.py`
- Output: `data/scan/chunks/chunk_NNN/`
- Laplacien spectral K=64, Recall@100=70%, Cohen's d=8.78

### WT2 — Per-paper Bipartite Bridge (S-2↔S0) — COMPLET
- **416/416 chunks**, 877K papers, 832K full (glyphs+concepts)
- Scanner: `engine/topology/wt2_scanner.py`
- Output: `data/scan/wt2_chunks/chunk_NNN/`
  - `papers.json.gz` — {arxiv_id: {glyphs, domain, concepts}}
  - `bipartite.json.gz` — {"glyph_id|concept_idx": weight}
  - `meta.json`
- 19 domaines, 1,337 glyphes, cutoff 2015-12
- Fix session 22: extract_tex_from_gz reecrit (magic bytes), timeout 30s/paper, cap 500KB regex

### WT3 — La Bible (jointure WT1+WT2) — COMPLET (16 mars 2026)
- Script: `engine/topology/wt3_bible.py`, output: `data/wt3.db` (78 GB)
- Tables SQLite: papers (833K), bipartite (6.2M), cooc (885M), cooc_global (69.4M), progress, meta
- Streaming chunk par chunk (RAM safe), SQLite WAL mode, crash-resumable
- **Phase 1 papers**: 833,030 papers, 416/416 chunks
- **Phase 2 bipartite**: 6,181,981 paires glyph×concept, 416/416 chunks
- **Phase 3a cooc sharding**: 581/581 chunks → 64 shards disk
- **Phase 3b cooc aggregation**: 64/64 shards → 885,305,772 cooc rows
- **Phase 3c PK index**: idx_cooc_pk ON cooc(concept_a, concept_b, period)
- **Phase 4 cooc_global**: 69,440,760 paires concept×concept (agrégé cross-period)
- **Phase 5 indexes**: 8/8 index créés (papers, bipartite, cooc, cooc_global)
- **Phase 6 meta**: build_date, totals, build_time
- Muninn par-dessus = turbo (P39 prevu post-WT3)

### WT4 — Forme 3D unifiee (S-2 x S-1 x S0) — COMPLET (16 mars 2026)
- Script: `engine/topology/wt4_spectral.py`, output: `data/scan/wt4_spectral.json` (941 KB)
- **Methode**: Graphe UNIFIE glyphes + 65K concepts + mycelium
- **Matrice**: 66,342 noeuds (1,316 glyphes + 65,026 concepts), 75,622,741 aretes
  - 6,181,981 aretes bipartite glyph↔concept (pont S-2↔S0)
  - 69,440,760 aretes concept↔concept (cooc_global = LE MYCELIUM)
  - densite 3.44%
- **Laplacien normalise**: L_sym = I - D^{-1/2} A D^{-1/2}, eigsh k=20
- **Gap spectral**: lambda_1=1.000, lambda_2=0.774, gap=0.226
  - gap 2→3: 0.044, gap 3→4: 0.085
- **Variance eigenvectors 1-3**: 10.1% + 8.9% + 7.0% = 26% (bon pour 66K noeuds)
- **nd** (domaines par glyphe): range 1-19, mean=13.4, median=13
- **Paires semantiques**: 8/12 plus proches que la mediane (67%)
  - ∫↔∂, Σ↔Π, =↔≠, (↔), <↔>, [↔], Σ↔∫, ∪↔∩ = CLOSER
- **Domaines**: Physics/Math/CS spread~0.45 (compacts), Art/Medicine spread~0.72 (etales)
- **Runtime**: 10.6 min (charge 69.4M mycelium + eigsh sur 66K noeuds)
- **Viz**: `viz/wt4_spectral_3d.html` (Three.js, toggle couleur domaine/nd/groupe)
- **Exports**: wt4_spectral.json (full), viz/data/wt4_spectral.json (glyphes), viz/data/wt4_full.json (glyphes + top 5K concepts)
- Utilise TOUTES les tables WT3: bipartite + cooc_global + papers
- La regle "Laplaciens separes" respectee: WT4 = calcul DERIVE, pas fusion de tables

## Regle fondamentale
Laplaciens S-2 et S0 restent SEPARES en stockage. Le pont S-2↔S0 = table bipartite dans WT3.
Le Laplacien joint (WT4) est un calcul derive pour la forme 3D, pas une fusion des graphes de base.

## Populations
| Strate | Contenu | Taille |
|--------|---------|--------|
| S-2 | Glyphes | ~1,500 (1,337 math + 116 fossiles + 10 actifs + 7 graines) |
| S-1 | Metiers | 19 domaines x 1,337 glyphes |
| S0 | Concepts | 65,026 OpenAlex |
| S1-S6 | Arbre | 296 concepts |
