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

### WT3 — La Bible (jointure WT1+WT2) — EN COURS
- Script: `engine/topology/wt3_bible.py`, output: `E:/yggdrasil/wt3.db`
- Tables SQLite: papers, bipartite, cooc, cooc_global, progress
- Streaming chunk par chunk (RAM safe), SQLite WAL mode, crash-resumable
- **Phase 1 papers**: FAIT — 833,030 papers, 416/416 chunks (21s)
- **Phase 2 bipartite**: FAIT — 6,181,981 paires glyph×concept, 416/416 chunks (693s)
- **Phase 3 cooc**: EN COURS — ingestion WT1 co-occurrences, 581 chunks, ~400K rows/s
- Muninn par-dessus = turbo (P39 prevu post-WT3)

### WT4 — Forme 3D unifiee (S-2 x S-1 x S0) — DESIGN
- Session 25: decouverte que Face 1 utilisait hauteur=papers (faux) au lieu de eigenvector 3 (vrai)
- Le Laplacien S-2 actuel est 2D (eigenvectors 1-2 seulement), pas de composante 3D
- Les 19 domaines (S-1) donnent un prior de clustering gratuit pour accelerer le calcul
- Les nd (nombre de domaines par glyphe) SONT la coordonnee verticale naturelle:
  - nd=2 (21 glyphes) = aretes/frontieres entre 2 territoires
  - nd=3 (34) = sommets ou 3 territoires se touchent
  - nd=4 (22) = carrefours a 4
  - nd=5-8 (13) = reseau profond
  - TROU nd=9-12 (0) = vide structurel
  - nd=13-19 (1,233) = tronc du champignon (ubiquistes)
- Forme champignon emerge naturellement (coherent avec core-periphery en network science)
- Necessite: Laplacien S-2 repondere avec masses S0 (papers/concepts par glyphe) + eigenvectors 1-2-3
- Prerequis: WT3 complet (la Bible fournit les masses S0 par glyphe)
- La regle "Laplaciens separes" reste pour le stockage; le Laplacien joint est un CALCUL DERIVE, pas une fusion de tables

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
