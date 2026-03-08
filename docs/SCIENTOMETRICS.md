# Scientometrics — Formules récupérables pour Yggdrasil

> Session 21, 8 mars 2026. Ratissage littérature scientométrique.
> But: identifier les formules publiées et validées qu'on peut empiler sur nos données.

## Ce qu'on a déjà

| Métrique | Source | Implémenté dans |
|----------|--------|-----------------|
| Uzzi z-score (atypical combinations) | Uzzi et al. (Science, 2013) | P4 predictions — `predictions_2025/` |
| Laplacien spectral K=64 | Classique (algèbre linéaire) | `engine/analysis/glyph_laplacian.py` |
| Betweenness Centrality | Freeman 1977 | Mycelium |
| Co-occurrence 1/C(n,2) | Classique | Winter tree scanner V2 |

## TIER 1 — Directement applicables (zero rescan, calcul sur matrice existante)

### Adamic-Adar Index
- **Source**: Liben-Nowell & Kleinberg (2003)
- **Formule**: `AA(x,y) = Σ_{z ∈ Γ(x) ∩ Γ(y)} 1/log|Γ(z)|`
- **Idée**: Les voisins communs rares comptent plus que les hubs
- **On branche sur**: Matrice WT1 (108M paires)
- **Ref**: https://www.cs.cornell.edu/home/kleinber/link-pred.pdf

### Resource Allocation Index
- **Source**: Zhou et al. (2009)
- **Formule**: `RA(x,y) = Σ_{z ∈ Γ(x) ∩ Γ(y)} 1/|Γ(z)|`
- **Idée**: Comme AA mais plus punitif pour les hubs (pas de log)
- **On branche sur**: Matrice WT1 + WT2 bipartite
- **Extension bipartite**: STRA index (Zhou) pour réseaux bipartites
- **Ref**: https://networkx.org/documentation/stable/reference/algorithms/link_prediction.html

### Katz Index
- **Source**: Katz (1953)
- **Formule**: `Katz(x,y) = Σ_{l=1}^{∞} β^l × |paths_l(x,y)|`
- **Idée**: Tous les chemins entre deux noeuds, β < 1 amortit les longs chemins
- **Performance**: #1 dans les benchmarks de link prediction
- **On branche sur**: Matrice WT1
- **Attention**: Coûteux à calculer sur 65K. Approximation sparse nécessaire.

### Jaccard Coefficient
- **Source**: Classique
- **Formule**: `J(x,y) = |Γ(x) ∩ Γ(y)| / |Γ(x) ∪ Γ(y)|`
- **On branche sur**: Matrice WT1
- **Note**: Simple mais baseline utile

### Burt Constraint (Structural Holes)
- **Source**: Burt (1992)
- **Formule**: `C_i = Σ_j (p_ij + Σ_q p_iq × p_qj)²` pour q ≠ i,j
- **Idée**: Mesure si un noeud est "contraint" par son réseau. Faible constraint = trou structurel = brokerage
- **On branche sur**: Nos P4 — complémentaire au Laplacien spectral
- **Ref**: http://www.ronaldsburt.com/research/files/NNappB.pdf

## TIER 2 — Besoin des frames temporelles (on les a: 1,534 frames)

### Converging Semantic Distance
- **Source**: Cohen & Schvaneveldt (2010)
- **Formule**: Distance sémantique entre deux concepts converge AVANT qu'ils co-apparaissent
- **Idée**: Signal prédictif — la distance baisse progressivement avant la connexion réelle
- **On branche sur**: Nos 1,534 frames temporelles + spectral embeddings
- **Ref**: https://pubmed.ncbi.nlm.nih.gov/20841769/

### Structural Entropy
- **Source**: Xu & Luo (2022, Information Processing & Management)
- **Formule**: Entropie de Shannon sur la distribution des degrés du réseau à chaque timestep
- **Idée**: Tipping points = quand l'entropie change brusquement → breakthrough
- **On branche sur**: Frames temporelles du réseau
- **Ref**: https://www.sciencedirect.com/science/article/abs/pii/S0306457321003332

### Sleeping Beauty / Beauty Coefficient
- **Source**: Ke et al. (PNAS, 2015)
- **Formule**: B = max_t [(c_t - c_0) × (T_m - t)] — comparaison entre citation réelle et ligne de référence
- **Idée**: Papers dormants qui explosent des décennies plus tard. Power-law = mécanisme commun.
- **On branche sur**: Nos frames + concept_births (65,021 births)
- **Ref**: https://www.pnas.org/doi/10.1073/pnas.1424329112

### CD Index (Disruption)
- **Source**: Funk & Owen-Smith (2017)
- **Formule**: `CD = (NF - NB) / (NF + NB + NR)`
  - NF = papers citant SEULEMENT le focal paper
  - NB = papers citant le focal ET ses références
  - NR = papers citant les références MAIS PAS le focal
- **Valeurs**: +1 = disruptif total, -1 = consolidation pure
- **On branche sur**: Données citations OpenAlex
- **Attention**: Critiqué pour inflation de citations (2024). Utiliser avec prudence.
- **Ref**: https://direct.mit.edu/qss/article/5/4/975/124268

### Rao-Stirling Diversity (Interdisciplinarité)
- **Source**: Stirling (2007), Rafols & Meyer (2010)
- **Formule**: `Δ = Σ_{i≠j} d_ij × p_i × p_j`
  - d_ij = distance entre catégories i et j
  - p_i = proportion de références dans la catégorie i
- **Idée**: Mesure variety × balance × disparity d'un paper/concept
- **On branche sur**: Nos 9 espèces + matrice WT1
- **Ref**: https://www.sciencedirect.com/science/article/pii/S1751157718303535

## TIER 3 — Embeddings alternatifs (complément au Laplacien)

### Node2Vec
- **Source**: Grover & Leskovec (2016)
- **Formule**: Random walks biaisés (paramètres p, q) → Word2Vec sur les séquences
- **Idée**: Embeddings qui capturent homophilie (p) et rôle structurel (q)
- **On branche sur**: Graphe WT1 — alternative/complément aux eigenvecteurs spectraux
- **Avantage**: Scalable à 65K noeuds, captures non-linéaires

### FutureRank
- **Source**: Sayyadi & Getoor (SIAM, 2009)
- **Formule**: PageRank prédictif = réseau de citations + réseau d'auteurs + date de publication
- **On branche sur**: Données citations OpenAlex
- **Ref**: https://epubs.siam.org/doi/10.1137/1.9781611972795.46

## TIER 4 — Signaux faibles / Topic detection

### BERTrend
- **Source**: 2024, NLP
- **Formule**: Topic modeling neural en mode online, classifie en noise/weak/strong signals
- **Utilisable**: PEUT-ÊTRE — nécessite texte brut (abstracts), pas juste co-occurrences
- **Ref**: https://arxiv.org/html/2411.05930v1

### Temporal Motifs
- **Source**: Scientometrics 2025
- **Formule**: Motifs temporels dans les réseaux de citations term-to-term
- **On branche sur**: Nos frames temporelles
- **Ref**: https://link.springer.com/article/10.1007/s11192-025-05434-8

## Plan d'intégration

**Phase 1 (après WT3)**: Tier 1 — Adamic-Adar, Katz, Burt Constraint sur la matrice existante
- Zero rescan, pur calcul
- Chaque métrique donne un angle différent sur les mêmes trous
- Si 4/5 métriques disent "il manque un lien ici" → prédiction plus fiable

**Phase 2 (avec V3 météorites)**: Tier 2 — Converging distance, Structural entropy, Sleeping Beauty
- Exploite les frames temporelles qu'on a déjà
- Valide les prédictions par rapport au passé

**Phase 3 (V4 grimpeur)**: Tier 3 — Node2Vec + ensemble de métriques
- Combine Laplacien spectral + Node2Vec + link prediction scores
- Le grimpeur utilise le consensus multi-métriques

## Ce qui est UNIQUE à Yggdrasil (pas dans la littérature)

1. **Multi-strate**: glyphes (S-2) + domaines (S-1) + concepts (S0) empilés — personne ne lie symboles math aux concepts
2. **Bipartite glyph×concept** (WT2) — inexistant dans la littérature
3. **Échelle**: 348M papers, 65K concepts, 108M paires, 1,337 glyphes
4. **Laplacien spectral sur co-occurrences** (pas juste link prediction classique)
5. **Rubik's cube mapping** pour la navigation topologique
6. **Oracle avec timestamps git** — prédictions datées vérifiables

## Refs complètes

- Uzzi et al. "Atypical Combinations and Scientific Impact" Science 2013
- Liben-Nowell & Kleinberg "The Link Prediction Problem" 2003
- Zhou et al. "Predicting missing links via local information" 2009
- Katz "A new status index" 1953
- Burt "Structural Holes" 1992
- Cohen & Schvaneveldt "Converging Semantic Distance" 2010
- Xu & Luo "Structural Entropy for Breakthrough Detection" IPM 2022
- Ke et al. "Sleeping Beauties in Science" PNAS 2015
- Funk & Owen-Smith "CD Index" 2017
- Stirling "A General Framework for Diversity" 2007
- Grover & Leskovec "Node2Vec" KDD 2016
- Sayyadi & Getoor "FutureRank" SIAM 2009
- Rafols & Meyer "Diversity and Interdisciplinarity" 2010
