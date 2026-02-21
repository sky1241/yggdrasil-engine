# TODO — Yggdrasil Engine
> Dernière màj: 21 fév 2026, session nocturne Sky×Claude

## V1 — CARTE STATIQUE (✅ FAIT)
Mapper les 21,228 concepts, 9 continents, 7 strates.
Valider sur 100 tests historiques → 87%.

- [x] 794 symboles originaux + 20,434 minés OpenAlex
- [x] Matrice co-occurrence 85×85 domaines (296M papers)
- [x] Spectral layout (laplacien normalisé → positions)
- [x] 5 patterns: P1 Pont, P2 Dense, P3 Théorie×Outil, P4 Trou ouvert, P5 Anti-signal
- [x] 3 types de trous: A Technique, B Conceptuel, C Perceptuel
- [x] Mycelium Physarum (24 briques, 456 tests)
- [x] Validation 100 tests (87%)
- [x] Validation 32 tests historiques (97%)
- [x] Cross-analyse Physarum × works_count
- [x] Escaliers spectraux (150 geo + 69 passe-partout)
- [x] Viz La Pluie v3, Escaliers 2D
- [ ] Viz Escaliers 3D → routes mycelium (b2, WIP, 60%)

## V2 — TIMELAPSE HISTORIQUE (PROCHAIN)
Remonter à 0. Rejouer l'histoire de la science frame par frame.
Voir les continents se former, les strates apparaître.

### Résolution adaptative
- 1665-1900: par décennie (données rares)
- 1900-1950: par année
- 1950-2000: par mois si données suffisantes, sinon année
- 2000-2025: par mois (publication_date dispo sur OpenAlex)

### Chaque frame =
1. Filtrer papers ≤ date de la frame
2. Recalculer matrice co-occurrence
3. Recalculer spectral layout → positions des centroïdes
4. Recalculer Physarum flux
5. Recalculer P4 (trous ouverts)
6. Sauvegarder snapshot JSON

### Estimation temps de calcul
- ~2-3 min par frame (matrice + spectral + Physarum)
- ~300 frames total → ~10-15 heures
- Lancer la nuit, dormir, résultats au matin
- IMPORTANT: si les données locales OpenAlex ont publication_date → tout en local
- Sinon: API OpenAlex avec filtre par année/mois → plus lent mais faisable

### Livrables
- Séquence de snapshots JSON: `timelapse/frame_YYYY_MM.json`
- Viz timelapse animée (Three.js ou canvas)
- On voit les continents dériver comme la tectonique des plaques
- On voit les strates apparaître: plat en 1900 → Gödel 1931 crée S1 → Turing 1936 pose S6

## V3 — CANDLESTICKS OHLC & MÉTÉORITES (APRÈS V2)
Chaque percée majeure = un candlestick sur le mycelium.
Le V3 RÉUTILISE les frames du V2 → quasi gratuit en calcul.

### La bougie OHLC scientifique
- **Open** = date d'ÉMISSION du paper
- **High** = pic de reconfiguration maximale du mycelium
- **Low** = creux (résistance paradigme / stabilisation)
- **Close** = date de VALIDATION (accepté, prouvé, répliqué, explosion citations)
- **Longueur de la bougie** = temps de résistance du paradigme

### Corrélation bougie ↔ type de trou
- Trou Technique (A) → bougie moyenne (attente de l'outil)
- Trou Conceptuel (B) → bougie courte (idée → explosion rapide)
- Trou Perceptuel (C) → bougie LONGUE (Karikó mRNA: 30 ans de rejet)

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

## TEST EN COURS
- [x] Test semi-aveugle 2015→2025 lancé le 21 fév 2026
- [ ] Résultats attendus → blind_test/
- [ ] Verdict: PASS si recall@100 > 50% ET Mann-Whitney p < 0.05

## NOTES
- V2 est le goulot (calcul lourd). V3 = post-traitement sur les frames V2.
- Le timelapse V2 donne AUSSI les données pour refaire le test aveugle à n'importe quelle date.
- Tout Claude qui bosse sur ce repo: lis SOL.md EN PREMIER, puis ce TODO.
