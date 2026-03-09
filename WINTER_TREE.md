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

### WT3 — La Bible (jointure WT1+WT2) — A FAIRE
- Index unifie: paper → glyphs × domain × concepts × co-occurrences
- Muninn par-dessus = turbo

## Regle fondamentale
Laplaciens S-2 et S0 restent SEPARES. Le pont S-2↔S0 = table bipartite, PAS fusion de graphes.

## Populations
| Strate | Contenu | Taille |
|--------|---------|--------|
| S-2 | Glyphes | ~1,500 (1,337 math + 116 fossiles + 10 actifs + 7 graines) |
| S-1 | Metiers | 19 domaines x 1,337 glyphes |
| S0 | Concepts | 65,026 OpenAlex |
| S1-S6 | Arbre | 296 concepts |
