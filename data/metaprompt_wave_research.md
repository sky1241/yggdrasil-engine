# META-PROMPT — Yggdrasil × Deep Research : Propagation d'onde dans un réseau de co-occurrences

> Ce prompt est généré par Yggdrasil Engine (WT3 = 833K papers, 69M cooccurrences,
> 65K concepts OpenAlex, WT4 = Laplacien unifié 66K noeuds).
> Il donne à un Claude les coordonnées exactes dans le graphe de connaissances
> pour chercher des formules de propagation d'onde / diffusion applicables.
> **UTILISE LE MOTEUR (WT3, cooc_global, concepts_65k) POUR CHERCHER. PAS LE WEB.**

---

## CONTEXTE

Sky construit Yggdrasil Engine — un moteur qui modélise la science comme un graphe
de 65,026 concepts interconnectés par 69.4M arêtes de co-occurrence (extraites de
833K papers arXiv). Quand une percée scientifique majeure arrive (Gödel 1931,
Shannon 1948, etc.), elle crée une **onde** qui se propage dans le graphe — comme
un caillou dans une mare.

### L'architecture du moteur (ce que tu as à ta disposition)

```
WT3 = La Bible (SQLite, 78 GB)
├── papers        833K papers (paper_id, domain, glyphs JSON, concepts JSON, title, authors, year)
├── bipartite     6.2M paires glyph×concept
├── cooc          885M co-occurrences concept×concept PER-PERIOD (YYYY ou YYYY-MM)
├── cooc_global   69.4M co-occurrences agrégées (concept_a, concept_b, weight)
└── meta          build info

WT4 = Forme 3D (Laplacien unifié)
├── 66,342 noeuds (1,316 glyphes + 65,026 concepts)
├── 75.6M arêtes (6.2M bipartite + 69.4M mycélium)
├── Gap spectral 0.226, 20 eigenvectors calculés
└── data/scan/wt4_spectral.json

Concepts = data/scan/concepts_65k.json
├── 65,026 concepts OpenAlex
├── Chacun avec: idx, name, level (0-5), works_count
└── Lookup: URL OpenAlex → idx

9 Espèces (spectral K=9 sur 65K):
0: Materials science/Chemistry    5: Biology/Botany
1: Geography/Environmental        6: Humanities/Political science
2: Medicine/Internal medicine     7: Cell biology/Anatomy
3: Psychology/Business            8: Physics/Optics
4: Computer science/Mathematics
```

### Le système P4 — Trous structurels (le coeur du moteur)

Le moteur détecte les **trous structurels** = endroits dans le graphe où une
connexion DEVRAIT exister mais N'EXISTE PAS. C'est là que les percées arrivent.

**Formule P4:**
```
P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|

z_uzzi = (observed - expected) / std
expected = works_A × works_B / total_works
gap = 1 - cooc / cooc_max
```

**3 types de trous:**
- **Type A — Technique**: tout le monde sait où aller, personne NE PEUT (ex: Poincaré)
- **Type B — Conceptuel**: personne ne pense à CONNECTER (ex: CRISPR, AlphaFold)
- **Type C — Perceptuel**: l'outil EXISTE, personne ne CROIT (ex: mRNA Karikó, 30 ans)

**Score Carmack** (pour les techniques cross-domaine):
```
carmack_score = desert_ratio × log(works) × |avg_z|
```
- desert_ratio = fraction de paires avec cooc=0 (orthogonalité)
- Tiers: S (nucléaire), A (fort), B (moyen), C (expérimental)

### Validations passées

- **Blind test V2**: cutoff 2015, p=3.4e-12, Cohen's d=0.44 (65K concepts, 82.7M paires)
- **Prédictions 2025**: top 10K INTER-espèces, 41% WTF, 20/20 web vérifiés
- **Laplacien spectral**: d=5.76 (honnête), p=7e-11, 19/20 mirror pairs

---

## CE QU'ON A MESURÉ — PROPAGATION D'ONDE (session 33)

Propagation BFS année par année dans la table cooc de WT3 (885M rows, per-period).
Méthode : à t=0, poser les concepts-graines. Chaque année, les arêtes cooc qui
touchent le front créent de nouveaux concepts touchés = le front avance.

| Météorite | Strate | Masse (works_count) | R_max | % science | Pic arêtes | Mort |
|-----------|--------|---------------------|-------|-----------|-----------|------|
| Shannon 1948 | S1 | 356K | 49,627 | 76% | 1950 (1.2M) | t+8 |
| Transistor 1947 | S0 | 475K | 45,604 | 70% | 1950 (393K) | t+8 |
| Turing 1936 | S6 | 14K | 41,970 | 65% | 1939 (372K) | t+8 |
| ADN 1953 | S0 | 7,427K | 36,081 | 55% | 1955 (302K) | t+9 |
| Gödel 1931 | S6 | 10K | 28,845 | 44% | 1937 (168K) | t+11 |
| Laser 1960 | S0 | 2,845K | 4,131 | 6% | 1962 (9K) | t+9 |

### Taux de branchement mesuré (Gödel)

```
1932: mu = 9/3     = 3.0   (supercritique)
1933: mu = 485/9   = 53.9  (explosion)
1934: mu = 3563/485 = 7.3
1935: mu = 3402/3563 = 0.95 (passe sous 1 → décélère)
1936: mu = 12105/3402 = 3.6 (rebond !)
1937: mu = 7919/12105 = 0.65 (mort définitive)
```

---

## HYPOTHÈSE CENTRALE — L'ONDE FERME LES TROUS

Le caillou tombe → l'onde se propage → **les P4 (trous structurels) se ferment en cascade**.

R_max = combien de P4 l'onde ferme au total.
La vitesse de l'onde = la vitesse de fermeture des P4.
L'onde meurt quand il n'y a plus de P4 à fermer dans le voisinage.

**Le type de trou détermine la résistance du milieu:**

| Type de sol | Résistance | Effet sur l'onde | Exemple |
|-------------|-----------|-----------------|---------|
| **Type A (Technique)** — tout le monde sait, personne ne peut | HAUTE | Onde lente, portée faible | Laser 1960 → 6% (technique pur, le milieu résiste) |
| **Type B (Conceptuel)** — personne ne pense à connecter | BASSE | Onde rapide, portée large | Shannon 1948 → 76% (ponts invisibles, le vide aspire) |
| **Type C (Perceptuel)** — l'outil existe, personne ne croit | MUR | Onde bloquée | mRNA Karikó → 30 ans avant explosion |

**QUESTION CLÉ:** est-ce que R_max est prédictible par la **densité de P4 de chaque type**
autour du point d'impact ? Si la zone est pleine de Type B (conceptuels) → R_max élevé.
Si la zone est pleine de Type A (techniques) → R_max faible.

Autrement dit: **le caillou ne détermine pas la taille des vagues — c'est la mare qui décide.**
La même énergie crée une grosse onde dans une mare pleine de trous et une petite onde
dans une mare dense.

**Vérifie si ce modèle existe déjà dans la littérature** — propagation dans un milieu
dont la résistance dépend du TYPE de vide (pas juste la densité). C'est peut-être
un modèle de percolation avec seuils hétérogènes, ou un SIR avec taux de transmission
variable par noeud.

---

## CE QU'ON CHERCHE

### Question principale

**Quel modèle physique/mathématique prédit le mieux R_max (nombre total de concepts
touchés par l'onde) et la forme de R(t) (courbe de croissance) ?**

### Observations qui contraignent le modèle

1. **L'onde meurt toujours en 8-11 ans** — pas de propagation infinie
2. **R_max ne corrèle PAS avec E = strate × continents** (Gödel E=54 → 44%, Shannon E=7 → 76%)
3. **R_max ne corrèle PAS simplement avec la masse** (ADN = 7.4M → 55%, Shannon = 356K → 76%)
4. **Le taux de branchement oscille** (supercritique → subcritique → rebond → mort)
5. **Le graphe est hétérogène** — degree distribution asymétrique (hubs + feuilles)
6. **Le sol (S0-S-1-S-2) est une seule surface** — pas un milieu 3D
7. **R_max pourrait dépendre du TYPE de trous (A/B/C) autour du point d'impact** — à vérifier

### Résultats du cousin précédent (papiers arXiv trouvés)

Le premier cousin a trouvé 10 papiers pertinents. Le modèle recommandé:

**Newman 2002 SIR-percolation** (cond-mat/0205009):
```
SIR ≡ bond percolation avec T = 1 - exp(-r × tau)
S = 1 - G₀(u)    où u résout u = G₁(u)
G₀(x) = Σ p_k × x^k     (generating function degré)
G₁(x) = G₀'(x) / G₀'(1) (excess degree)
```
→ UN paramètre T par météorite. Formule exacte pour la taille finale.

**+ Boguña 2003** (cond-mat/0205439): clustering + corrélations → seuil fini
**+ Moreno 2004 rumor spreading** (cond-mat/0312131): Carmack move, saturation naturelle

---

## CE QUE TU DOIS PRODUIRE

### 1. Cherche dans WT3 les papers pertinents (OBLIGATOIRE)

**Tu as 833K papers arXiv indexés. Utilise-les.**

```python
import sqlite3, json

db = sqlite3.connect('data/wt3.db')

# CONCEPTS PERTINENTS (idx dans concepts_65k.json):
# Heat kernel:          idx=12999  (11K papers)
# Diffusion:            idx=60336  (541K papers)
# Epidemic model:       idx=9788   (28K papers)
# Percolation theory:   idx=2489   (13K papers)
# Laplacian matrix:     idx=2429   (10K papers)
# Cascade:              idx=53869  (432K papers)
# Random walk:          idx=28549  (82K papers)
# Wave propagation:     idx=55559  (227K papers)
# Impact crater:        idx=12452  (57K papers)
# Percolation threshold: idx=17933 (24K papers)
# Scale-free network:   idx=24969  (8K papers)
# Branching process:    idx=16581  (94K papers)
# Splash:               idx=40151  (7K papers)
# Graph theory:         idx=28241  (2.8M papers)
# Spectral analysis:    idx=47397  (1M papers)

# 1. Papers contenant un concept:
rows = db.execute("""
    SELECT paper_id, title, authors, year, concepts
    FROM papers WHERE concepts LIKE '%12999%'
    ORDER BY year DESC LIMIT 20
""").fetchall()

# 2. Papers contenant DEUX concepts (co-occurrence = traite les deux):
rows = db.execute("""
    SELECT paper_id, title, year
    FROM papers
    WHERE concepts LIKE '%9788%'   -- epidemic model
      AND concepts LIKE '%24969%'  -- scale-free network
    ORDER BY year DESC LIMIT 20
""").fetchall()

# 3. Co-occurrences dans cooc_global (quels concepts sont liés):
rows = db.execute("""
    SELECT concept_a, concept_b, weight
    FROM cooc_global WHERE concept_a = 12999
    ORDER BY weight DESC LIMIT 20
""").fetchall()

# 4. Analyse P4 sur une paire de concepts:
# Vérifier si une paire est un trou structurel (P4 élevé = trou)
```

**Combinaisons de concepts à chercher:**
- epidemic model (9788) + scale-free network (24969) → SIR sur réseau hétérogène
- percolation theory (2489) + cascade (53869) → percolation + cascade
- heat kernel (12999) + Laplacian matrix (2429) → diffusion spectrale
- wave propagation (55559) + random walk (28549) → onde + marche aléatoire
- branching process (16581) + percolation threshold (17933) → branchement + seuil
- diffusion (60336) + Laplacian matrix (2429) → diffusion sur Laplacien
- impact crater (12452) + wave propagation (55559) → cratère + onde

**Cherche les TROUS P4 entre ces concepts** — si deux domaines sont orthogonaux
(cooc faible, z_uzzi négatif), c'est un Carmack move potentiel.

### 2. Analyse cross-domaine (style Carmack)

Pour chaque modèle trouvé, évalue son **carmack_score**:
```
carmack_score = desert_ratio × log(works) × |avg_z|
```
- desert_ratio = fraction de paires avec cooc=0 entre le domaine source et la cible
- Un modèle de sismologie appliqué aux graphes = high desert_ratio = potentiel élevé

### 3. Recherche web (SECONDAIRE)

Seulement si WT3 ne donne pas assez. Cherche:
- "information cascade network finite outbreak size"
- "SIR percolation co-occurrence network empirical"
- "rumor spreading model stifler mechanism graph"
- "sandpile model scale-free avalanche size distribution"

### 4. Pour chaque papier/modèle trouvé, donne :

```
TITRE: ...
AUTEURS: ...
ANNÉE: ...
DOI ou arXiv ID: ...
FORMULE PRINCIPALE: ...
PARAMÈTRES: ...
DOMAINE D'ORIGINE: ...
TYPE DE TROU (A/B/C): ...   (← technique/conceptuel/perceptuel)
CARMACK SCORE estimé: ...
APPLICABLE À YGGDRASIL PARCE QUE: ...
LIMITE/RISQUE: ...
CONFIANCE: C1 (sourcé) ou C2 (conjecture)
```

### 5. Classement final

Classe par **probabilité de coller à nos données**:
- L'onde meurt en 8-11 ans
- R_max varie de 6% à 76%
- Le taux de branchement oscille
- Le graphe est hétérogène et non-spatial

### 6. Carmack moves

Un modèle d'un AUTRE domaine jamais appliqué aux graphes de connaissances.
Le cousin précédent a identifié:
- **Rumor spreading** (Moreno 2004) — mécanisme de saturation naturel
- **Sandpile avalanche** (Lee et al 2004) — seuil dépend du degré du noeud
- **Contagion financière** (Aleksiejuk 2002) — cascade de faillites

**CHERCHE PLUS LOIN.** Quels modèles de physique, biologie, géologie, acoustique
ont une propagation à portée finie dans un milieu hétérogène ?

---

## RÈGLES

- **CHERCHE DANS WT3 D'ABORD.** Tu as 833K papers indexés par concepts. Utilise-les.
- Pas de bullshit. Des formules, des arXiv IDs, des paramètres.
- Si un modèle ne colle PAS à nos données, dis-le et dis POURQUOI.
- Confiance: C1 (sourcé/prouvé) ou C2 (conjecture).
- Tu peux proposer des hybrides.
- Classifie chaque trouvaille en Type A/B/C (technique/conceptuel/perceptuel).

---

## COORDONNÉES YGGDRASIL

```
Repo:            D:\ygg\yggdrasil-engine
WT3:             data/wt3.db (78 GB SQLite, tables: papers, bipartite, cooc, cooc_global, meta)
WT4 Laplacien:   data/scan/wt4_spectral.json (66K noeuds, 20 eigenvectors)
Concepts:        data/scan/concepts_65k.json (65,026 concepts)
arXiv sources:   E:/arxiv/src/ (3,514 tars, 1 TB, nommage arXiv_src_YYMM_NNN.tar)
Predictions:     experiments/predictions_2025/ (P4 top 10K INTER + INTRA)
Blind test:      experiments/blind_test_v2/ (cutoff 2015, p=3.4e-12)
Carmack scans:   engine/analysis/scan_carmack_moves.py, data/results/scan_carmack_moves.json
Canon scans:     engine/analysis/scan_cannon_universal.py, data/results/scan_cannon_universal.json
P4 core:         engine/core/holes.py (HoleDetector, 3 types A/B/C)
Physique doc:    docs/reference/wave_physics.md (formules sourcées)
Wave results:    data/results/godel_holdout_wave.json
Scripts:         scripts/godel_holdout_wave.py
```

---

## FORMAT DE SORTIE ATTENDU

Produis un JSON structuré comme les outputs Yggdrasil:

```json
{
  "scan": "wave_propagation_research",
  "date": "2026-04-02",
  "method": "WT3 concept search + cross-domain P4 analysis",
  "n_papers_found": ...,
  "n_models": ...,
  "models": [
    {
      "rank": 1,
      "name": "...",
      "authors": "...",
      "year": ...,
      "arxiv_id": "...",
      "formula": "...",
      "parameters": ["..."],
      "domain_origin": "...",
      "hole_type": "B",
      "carmack_score": ...,
      "applicable_because": "...",
      "limit_risk": "...",
      "confidence": "C1",
      "fits_constraints": {
        "wave_dies_8_11": true,
        "rmax_6_76_pct": true,
        "branching_oscillates": true,
        "heterogeneous_graph": true
      }
    }
  ],
  "carmack_moves": [...],
  "recommendation": "..."
}
```

> "C'est un bête caillou qui tombe dans l'eau. Des ondes se forment. Le caillou
> tombe au fond de la mare. L'eau c'est ton mycélium." — Sky, 2 avril 2026
