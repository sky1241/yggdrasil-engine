# TODO — Yggdrasil Engine
> Dernière màj: 24 fév 2026 (session 9), Sky×Claude (Opus 4.6)

## ARCHITECTURE DES STRATES
```
S6  ☁️  Indécidable          ┐
S5      Presque indécidable   │ ARBRE (pas de mycelium)
S4      Logique supérieure    │
S3      Conjectures           │
S2      Récursion²            │
S1      Structures récursives ┘
════════════════════════════════
S0  🌍  Formules prouvées    ┐
S-1 🔧  Métiers              │ SOL = MYCELIUM (co-occurrences)
S-2 🔣  Glyphes              ┘
════════════════════════════════
```

## V1 — CARTE STATIQUE (✅ FAIT)
Mapper les 21,524 symboles (794 originaux + 20,730 minés), 9 continents, 9 strates (S-2→S6).
Valider sur 100 tests historiques → 87%.

- [x] 794 symboles originaux + 20,730 minés OpenAlex = 21,524 total
- [x] concept_id injecté dans 100% des symboles + index inverse (20,932 entries)
- [x] Matrice co-occurrence 85×85 domaines (296M papers, scan v4)
- [x] Spectral layout (laplacien normalisé → positions)
- [x] 5 patterns: P1 Pont, P2 Dense, P3 Théorie×Outil, P4 Trou ouvert, P5 Anti-signal
- [x] 3 types de trous: A Technique, B Conceptuel, C Perceptuel
- [x] Mycelium Physarum (24 briques, 456 tests)
- [x] Validation 100 tests (87%)
- [x] Validation 32 tests historiques (97%)
- [x] Cross-analyse Physarum × works_count
- [x] Escaliers spectraux (200 geo + 69 passe-partout)
- [x] Viz La Pluie v3, Escaliers 2D
- [ ] Viz Escaliers 3D → routes mycelium (b2, WIP, 60%)

## V2 — TIMELAPSE HISTORIQUE (EN COURS)
Remonter à l'an 1000+. Rejouer l'histoire de la science frame par frame.
Voir les continents se former, les strates apparaître.

### Étape 2A — Winter Tree Scan V2 (PRÊT — rechunked 24 fév 2026)
Scanner les 692 GB du snapshot OpenAlex complet (D:\) par chunks de ~1 GB.
Indexer les 65,026 concepts (levels 0-5) par année/mois.

- [x] Lookup 65,026 concepts OpenAlex → `data/scan/concepts_65k.json` (7 MB)
- [x] Plan V1: 1,492 fichiers → 393 chunks (abandonné — disque plein + legacy-data)
- [x] Nettoyage D:\ — legacy-data supprimé (173 GB), 174 GB libres (82%)
- [x] Scanner V2: filtres erratum/retraction/is_retracted + poids 1/C(n,2)
- [x] Re-init: 1,981 fichiers → 581 chunks × ~1 GB
- [x] Test chunk 1 OK: 662K papers, 14 skipped, 580K matched, 6.9M paires
- [ ] Lancer scan complet — **4/581 chunks** — commande PowerShell prête
- Script: `engine/topology/winter_tree_scanner.py` (--init, --chunks N, --status)
- Arbre: `data/scan/winter_tree.json` (mis à jour après chaque chunk)
- Chunks: `data/scan/chunks/chunk_NNN/` (cooc.json.gz + activity.json.gz + meta.json)

#### Poids 1/C(n,2) (session 9)
Chaque paper distribue exactement **1 point** au total sur toutes ses paires de concepts.
Un paper avec n concepts crée C(n,2) paires, chacune reçoit 1/C(n,2).
Dilue naturellement les reviews (beaucoup de concepts → poids mince par paire) sans les supprimer.

### Résolution adaptative (confirmée sur les données)
- Papers les plus anciens: an ~1000 (manuscrits rares)
- Avant 1980: par année (MONTH_FROM_YEAR = 1980 dans le scanner)
- 1980-2025: par mois (publication_date précise au jour)
- ~1,094 périodes distinctes (constaté à 5% du scan)
- **Décision**: garder 1980 pour le 1er pass. 2nd pass optionnel 1930-1979 si publication_date existe

### Étape 2B — Frames cumulatives (APRÈS scan)
Reconstruire le film à partir du winter tree trié:
1. Pour chaque frame: additionner les co-occurrences ≤ date
2. Recalculer spectral layout → positions des centroïdes
3. Recalculer mycelium (BC, meshedness, Physarum)
4. Recalculer P4 (trous ouverts)
5. Sauvegarder snapshot JSON

### Blind test V2
- Entraînement: frames ≤ 2015 (calibration formules)
- Test aveugle: 2015→2025 (prédire, puis comparer au réel)
- 10 ans de marge pour valider les prédictions

### Livrables
- Winter tree complet: co-occurrences 65K concepts × mois
- Séquence de snapshots JSON: `timelapse/frame_YYYY_MM.json`
- Viz timelapse animée (Three.js ou canvas) — cube live pendant le scan
- On voit les continents dériver comme la tectonique des plaques
- On voit les strates apparaître: plat en 1900 → Gödel 1931 crée S1 → Turing 1936 pose S6

## V3 — CANDLESTICKS OHLC & MÉTÉORITES (APRÈS V2)
Chaque percée majeure = un candlestick sur le mycelium.
Le V3 RÉUTILISE les frames du V2 → quasi gratuit en calcul.
Blast Sedov-Taylor se propage dans le sol (S-2→S0). Calibration depuis 1948, test final Gödel 1931.
Voir `docs/formulas.tex` pour les formules complètes avec sources.

### Code V3 (sessions 7-8, 24 fév 2026)
- [x] `engine/meteorites.py` — module complet (763 lignes)
  - Sedov-Taylor: blast_radius, blast_velocity, energy_partition
  - 7 deltas: compute_deltas(before, after)
  - OHLC Candle + MeteoriteBox + MeteoriteRegistry
  - fit_sedov (curve_fit scipy), predict_godel
  - Catalogue 13 météorites (Shannon→AlphaFold)
  - classify_candle (corrélation bougie↔trou A/B/C)
- [x] Bugfix session 7: 8 bugs corrigés (4 meteorites + 4 core)
- [x] Audit session 8: 26 bugs fixés sur 14 fichiers + 2 derniers bugs meteorites.py
- [x] Tests meteorites.py passés: signature(), classify_candle(rho0=0), measure_impact(), summary()
- [ ] En attente des frames V2 pour mesure réelle sur les données

### La bougie OHLC scientifique
- **Open** = date d'ÉMISSION du paper
- **High** = pic de reconfiguration maximale du mycelium (dans S-2→S0)
- **Low** = creux (résistance paradigme / stabilisation)
- **Close** = date de VALIDATION (accepté, prouvé, répliqué, explosion citations)
- **Longueur de la bougie** = temps de résistance du paradigme

### Formule Sedov-Taylor adaptée au mycelium
`R(t) = β × (E/ρ₀)^{1/5} × t^{2/5}`
- E = strate_height × continents_touchés (énergie d'impact)
- ρ₀ = meshedness locale avant impact (densité du sol)
- R(t) = nombre de concepts affectés à t mois après publication
- β, γ = paramètres libres à calibrer depuis les boîtes de météorites

### Corrélation bougie ↔ type de trou (prédit par Sedov-Taylor + ρ₀)
- Trou Technique (A) → ρ₀ élevé → blast lent → bougie MOYENNE
- Trou Conceptuel (B) → ρ₀ faible (vide) → blast rapide → bougie COURTE
- Trou Perceptuel (C) → ρ₀ élevé + hostile → blast bloqué → bougie LONGUE (Karikó mRNA: 30 ans)

### 7 indicateurs techniques sous chaque bougie
Calculés comme DELTA entre frame avant et frame après la météorite:

```
CANDLESTICK: émission → validation
├── 1. volume      = nouvelles arêtes co-occurrence créées
├── 2. amplitude   = déplacement spectral des centroïdes (distance euclidienne)
├── 3. BC_delta    = delta betweenness centrality (nouveaux ponts vs obsolètes)
├── 4. alpha_delta = delta meshedness (réseau + ou - résilient)
├── 5. P4_delta    = trous fermés vs trous ouverts (net)
├── 6. physarum    = redistribution des flux (hyphes créées/mortes)
└── 7. births      = nouveaux concepts apparus / concepts morts
```

### Pondération de l'impact
`impact_météorite = strate_height × continents_touchés`
- Poincaré (S3 × 1 continent) = score moyen
- Shannon (S1 × 7 continents) = score massif
- Gödel (S6 × tout) = hors échelle

### Boîtes de mesure à accumuler
Chaque météorite mesurée = une boîte. On accumule:
Shannon 1948, ADN 1953, transistor, laser, internet, CRISPR, AlphaFold...
→ Moyenne des boîtes = SIGNATURE TYPE d'une météorite

### Test Gödel (TEST FINAL)
- Gödel 1931 = première météorite de l'histoire
- Avant lui: tout S0, plat, zéro strate au-dessus
- UNE seule mesure, pas de moyenne possible
- Appliquer la signature moyenne → prédire l'impact attendu
- Comparer à l'impact RÉEL
- Si ça colle → le modèle est validé du premier impact au dernier

## V3b — ESPÈCE MYCÉLIUM (APRÈS SCAN — session 8, 24 fév 2026)
Identifier quelle espèce de champignon le réseau Yggdrasil ressemble.
5 curseurs de Lehmann 2019 (31 espèces, dataset ouvert).
Voir `docs/SESSION_8_SPECIES_DISCOVERY.md` pour le plan complet.

- [ ] Phase A: Mesurer les 5 curseurs sur le graphe réel (`engine/topology/species_identifier.py`)
  - BA (Branching Angle): angles entre arêtes aux nœuds degré ≥ 3 (atan2 sur positions spectrales)
  - IL (Internodal Length): BFS entre bifurcations
  - D (Hyphal Diameter): poids moyen des arêtes
  - Db (Box Counting Dimension): fractale du sous-graphe
  - L (Lacunarity): distribution des vides (FracLac)
- [ ] Phase B: Identifier — distance euclidienne aux 31 espèces Lehmann 2019
- [ ] Phase C: Calibrer mycelium_full.py avec les vrais paramètres
- [ ] Phase D: Évolution temporelle (par décennie) — l'espèce change-t-elle avec le temps ?

## V4 — LE GRIMPEUR (VISION — après V3)
Le sommet de chaque escalier = un point de vue.
Regarder en bas = voir les briques S0 filtrées par la topologie.
L'AI grimpe avec le bon sac à dos.

### Le mécanisme
1. Problème ouvert → positionnement sur la carte
2. Trouver escaliers les plus proches (géo + passe-partout)
3. Vue plongeante → sac à dos de briques S0 filtrées
4. AI compose des chemins de preuves avec ces briques
5. Échec = donnée (P5 local) → réduction espace → autre sommet

### Modules à construire
- [ ] Moteur de positionnement: problème → coordonnées topologiques
- [ ] Moteur de proximité: coordonnées → top-N escaliers
- [ ] Vue plongeante: escalier → briques S0 connectées
- [ ] Compositeur: AI + sac à dos filtré → chemins candidats
- [ ] Mémoire d'échec: tentatives ratées → P5 locaux → carte se raffine

### Premier test: P=NP
- P=NP est S3-S4, PAS S6 (pas prouvé indécidable)
- 3 routes classiques sont P5 prouvés (diagonalisation, preuves naturelles, arithmétisation)
- Le moteur cherche les P4 = routes que personne n'a empruntées
- Les briques manquantes viendront → OpenAlex mine en continu → détection automatique

### Dépend de: V2 (timelapse) + V3 (candlesticks). PAS DE SAUT.

## TEST V1 (✅ FAIT)
- [x] Test semi-aveugle 2015→2025 lancé le 21 fév 2026
- [x] Résultats: SIGNAL DÉTECTÉ (p=0.00002, recall@100=50%, r=0.90)
- [x] Verdict: PASS (recall@100 = 50% ET Mann-Whitney p < 0.05)
- Attention: c'était sur 100 concepts / 21K. V2 sera sur 65K.

## NOTES
- Le winter tree scan est le goulot (lecture 467 GB). Après ça, tout est du post-traitement.
- V3 (formules météorites) réutilise les frames V2 → quasi gratuit.
- Le timelapse V2 donne AUSSI les données pour refaire le test aveugle à n'importe quelle date.
- Tout Claude qui bosse sur ce repo: lis SOL.md EN PREMIER, puis ce TODO.
