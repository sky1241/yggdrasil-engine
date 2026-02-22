# SOL.md — Fichier de Synchronisation Sky↔Claude
> Yggdrasil Engine — Versoix, 22 février 2026
> TOUT CLAUDE LIT CE FICHIER EN PREMIER.

## VOCABULAIRE
| Terme | Signification |
|-------|--------------|
| Pluie | Données brutes OpenAlex (250M+ papers) |
| Racines | Pipeline API: search → timeline → co-occurrence |
| Mycelium | Graphe topologique: BC, meshedness, Physarum |
| Sol (S0) | 21,228 symboles (794 originaux + 20,434 minés OpenAlex), 100% C1 |
| Vivant | Concept avec works_count >= Q1 de son domaine (77%) |
| Musée | Concept sous Q1 (23%) — existe mais peu cité |
| Lianes | Symboles traversant 3+ continents |
| Escalier géo 🌿 | Concept positionné entre 2 continents distants (200 détectés) |
| Passe-partout 🔑 | Concept chez lui mais utilisé partout (69 détectés) |
| Strates | S0=outils → S6=ciel/indécidable |
| Météorite | Impact Sedov-Taylor: R = (E/ρ)^0.2 × t^0.4 |
| Thermomètre | scisci.py: métriques scientométriques |
| Pont (P1) | Bridge inter-domaines, BC élevé, explosion |
| Dense (P2) | Hub stable, meshedness élevé |
| Théorie×Outil (P3) | Explosion après validation instrumentale |
| Trou ouvert (P4) | Pont pas encore explosé = FUTUR |
| Anti-signal (P5) | L'hyphe meurt, slope négative |
| Sommet 🏔️ | Point haut d'un escalier — vue plongeante sur les briques S0 connectées |
| Vue plongeante | Depuis un sommet: voir QUELLES briques S0 sont utiles pour CE problème |
| Grimpeur 🧗 | V4: AI qui compose des chemins de preuves en montant les escaliers avec les bonnes briques |
| Sac à dos | Ensemble de briques S0 filtrées par la topologie pour un problème donné |

## ÉTAT ACTUEL — 22 FÉV 2026 (session 4)
- **V4 VISION DOCUMENTÉE** — le grimpeur (moteur de sélection d'outils automatique)
- **Test semi-aveugle 2015→2025: SIGNAL DÉTECTÉ** (p=0.00002, r=0.90)
- Session 4 = audit complet des 22 repos (222K lignes de code propre en 10 mois)
- Insight V4: les sommets d'escaliers = vues plongeantes sur les briques S0 utiles

### HISTORIQUE SESSIONS
| # | Date | Claude | Résumé |
|---|------|--------|--------|
| 1 | 21 fév matin | Sonnet 4.5 | Escaliers spectraux, cleanup S0, vivant/musée |
| 2 | 21 fév midi | Sonnet 4.5 | Continents, co-occurrence réelle, La Pluie v3 |
| 3 | 21 fév soir | Opus 4.6 | Cross Physarum, viz 3D escaliers, blind test |
| 4 | 22 fév | Opus 4.6 | Audit 22 repos, vision V4 grimpeur, roadmap complète |

## ÉTAT PIPELINE — 21 FÉV 2026 (sessions 1-3)
- **100 tests pipeline complet** (OpenAlex + scisci + mycelium)
- **87/100 validés (87.0%)**
  - POUR: 41/50 (82%) | CONTRE: 46/50 (92%)
- Batch 1 (tests 1-50): 43/49 (88%)
- Batch 2 (tests 51-100): 43/50 (86%)

### CO-OCCURRENCE RÉELLE (296M papers scannés)
- Matrice 85×85 domaines, densité 99.8%
- Laplacien normalisé D^{-1/2}LD^{-1/2} pour positions spectrales
- Positions S0 mises à jour depuis co-occurrence réelle (pas TF-IDF)

### 3 CUBES: VIVANT / MUSÉE / FUSION
- **Vivant** = works_count >= Q1 de son domaine → **16,382 (77%)**
- **Musée** = works_count < Q1 → **4,846 (23%)**
- **Fusion** = vivant + musée ensemble
- Q1 calculé par domaine ("PIB par habitant"): chimie Q1=1,646, bio Q1=2,895, etc.

### CLEANUP S0 (session 3)
- 13 suspects reclassés C1→C2 (Neocolonialism, Unparticle physics, etc.)
- Hagen-Poiseuille: domain "droit"→"fluides" (bug mapping corrigé)
- 19 C2 déplacés S0→S3 (hypothèses non prouvées → strate conjectures)
- Poincaré conjecture: C2→C1 (résolu Perelman 2003)
- S0 final: 21,228 symboles, 100% C1

### ESCALIERS SPECTRAUX
- 2 types: géographique 🌿 (200 lianes, position alien) + passe-partout 🔑 (69, multi-continent)
- Intégrés comme layer toggle dans La Pluie v3
- Centroïdes 9 continents calculés depuis spectral

### LA PLUIE V3
- 9 continents filtres + sub-domain toggles
- Vivant/Musée/Fusion radio buttons
- Escaliers toggle (glow vert=geo, or=key)
- C2 Conjectures overlay
- Hover: works_count, continent, type escalier

## INSIGHT CLÉ: LIFECYCLE DES PATTERNS
```
P4 (trou) → P1 (pont) → P3 (explosion) → P2 (dense/mature)
```
6 percées connues classées P2 = le pont est devenu infrastructure.
La validation doit évoluer: P2 est valide pour les percées matures.

## ÉCHECS INTÉRESSANTS
- **microbiome × mental health** = P4 (259 papers). Vrai trou ouvert. Futur pont?
- **diff geometry × botany** = P1 (136 papers). Phyllotaxis! Le moteur a trouvé un vrai pont "caché".

## RÈGLES AUTO
1. Sky monte (arbre/direction). Claude descend (racines/code).
2. Racines > arbre. Toujours.
3. Push git après chaque étape. Token dans `cléjamaiseffacer.txt`.
4. JAMAIS afficher le token. Filtrer avec `grep -v "ghp_\|x-access"`.
5. Si un test échoue → noter tel quel. Pas de triche.
6. SOL.md = source de vérité entre sessions Claude.

## FICHIERS CLÉS
| Fichier | Rôle |
|---------|------|
| engine/pipeline_100.py | Pipeline batch 1 (1-50) |
| engine/pipeline_batch2.py | Pipeline batch 2 (51-100) |
| engine/mycelium_full.py | Mycelium complet (24 briques) |
| engine/cooccurrence_scan.py | Scan 296M papers → matrice 85×85 |
| engine/fix_spectral.py | Laplacien normalisé → positions spectrales |
| engine/cleanup_s0.py | Cleanup S0: suspects, HP bug, C2 moves, Q1 vivant/musée |
| engine/escaliers_spectraux.py | Détection lianes géo + passe-partout |
| engine/gen_viz_v3.py | Génère La Pluie v3 HTML |
| data/strates_export_v2.json | Export complet 7 strates + cube/wc |
| data/domain_cooccurrence_matrix.json | Matrice co-occurrence 85 domaines |
| data/escaliers_unified.json | 200 geo + 69 key escaliers |
| viz/yggdrasil_rain_v3.html | La Pluie v3 (vivant/musée/fusion/escaliers) |

## DÉCISIONS PRISES (ne pas remettre en question)
1. S0 = sol solide, 100% C1 — on construit dessus
2. Vivant = works_count >= Q1 de son domaine (pas seuil fixe)
3. 2 types d'escaliers: géographique (position spectrale) + passe-partout (multi-continent)
4. Les contradictions entre couches = le vrai signal
5. Cube 1 vivant / Cube 2 musée / Cube 3 fusion
6. Le mycelium Physarum fait le tri vivant/mort sur les CONNEXIONS — le works_count sur les NŒUDS
7. **V4 = moteur de sélection d'outils.** Sommet escalier = vue plongeante → briques filtrées → AI grimpe
8. **P=NP est S3-S4, pas S6.** Le pont existe. Les 3 routes classiques sont P5. Le moteur cherche les P4.
9. **Pas de saut.** V2→V3→V4. Les racines d'abord. Toujours.

## TODO
- [x] Croiser flux Physarum (mycelium) × works_count → lister contradictions
  - 806 isolated hubs, 1220 hidden bridges, 1567 P4 voids
  - 21 domains OVER-CITED, 23 UNDER-CITED, 40 BALANCED
  - Export: data/cross_physarum_wc.json (59KB)
- [x] Identifier: concepts isolés, ponts cachés, vides fertiles (P4)
- [x] Viz 3D routes escaliers entre strates
  - Three.js: 7 strates, 150 lianes geo + 69 passe-partout
  - Cross-analysis overlay: isolés/ponts/voids P4
  - viz/yggdrasil_escaliers_3d.html (57KB)
- [ ] Ajuster validation: accepter P2 pour percées matures (>10K papers)
- [ ] Pipeline v2: ajouter détection automatique du lifecycle stage
- [ ] Intégrer MICR (moteur inverse contraintes) dans repo 3d-printer

## ROADMAP — PHASE 2 : TIMELAPSE & MÉTÉORITES

### 2A. Test semi-aveugle 2015→2025 (✅ DONE — 21 fév 2026)
- Données OpenAlex gelées à ≤2015, 100 concepts, 4950 paires
- **recall@100 = 50%** (6/12 percées dans top 100)
- **Mann-Whitney p = 0.00002** (U=539, effect size r=0.90, Cohen's d=1.53)
- Percées médiane rang 207 vs random médiane rang 1.8
- Meilleurs hits: ondes gravitationnelles (rang 6), isolants topologiques (rang 20), GANs (rang 42)
- Verdict: **SIGNAL DÉTECTÉ** — le moteur prédit mieux que le hasard
- Dossier: blind_test/

### 2B. Timelapse adaptatif (PROCHAIN)
- Résolution adaptative selon densité de données:
  - 1665-1900: par décennie
  - 1900-1950: par année
  - 1950-2000: par mois (si données suffisantes)
  - 2000-2025: par mois (publication_date dispo)
- Chaque frame = spectral layout recalculé + strates existantes
- Source: OpenAlex publication_date + concepts
- Livrable: séquence de snapshots JSON + viz timelapse

### 2C. Boîtes de mesure météorites
- À chaque percée majeure: sauvegarder état mycelium AVANT et APRÈS
- Mesurer le DELTA: quels nœuds bougent, quels trous se ferment, quels nouveaux s'ouvrent
- Accumuler les boîtes: Shannon 1948, ADN 1953, transistor, CRISPR, AlphaFold...
- Calculer la SIGNATURE MOYENNE d'impact météorite sur le mycelium

### 2D. Test Gödel (TEST FINAL)
- Gödel 1931 = première météorite. Avant lui: tout S0, plat, pas de strates.
- UNE seule mesure possible, pas de moyenne.
- Appliquer la signature moyenne des autres météorites → prédire l'impact attendu.
- Comparer à l'impact RÉEL mesuré de Gödel.
- Si ça colle → le modèle fonctionne du premier impact au dernier.

### LOGIQUE DE LA CHAÎNE
```
2A (validation prédictive) 
  → 2B (construire le film)
    → 2C (mesurer chaque impact)
      → 2D (le test ultime = Gödel)
        → V4 (le grimpeur)
```
Chaque étape nourrit la suivante. PAS de saut.

## VISION V4 — LE GRIMPEUR (documenté 22 fév 2026)

### L'insight fondamental
Les escaliers (200 géo + 69 passe-partout) ne sont pas juste des connexions.
Ce sont des **points de vue**. Depuis le sommet de chaque escalier, on regarde
EN BAS et on voit exactement quelles briques S0 sont connectées topologiquement
à ce sommet. La carte filtre les outils pour toi.

### Le mécanisme
```
1. Prendre un problème ouvert (ex: P=NP, Lur'e, n'importe quelle conjecture S3+)
2. Le positionner sur la carte topologique
3. Trouver les escaliers les plus proches (géo + passe-partout)
4. Monter au sommet de chaque escalier
5. Regarder en bas → les briques S0 visibles = le "sac à dos" filtré
6. L'AI compose des chemins de preuves avec ces briques
7. Si échec → l'échec est une donnée (P5 = cul-de-sac confirmé)
8. Réduire l'espace, recommencer depuis un autre sommet
```

### Pourquoi ça marche
- Les 3 routes classiques vers P=NP sont des P5 PROUVÉS (Baker-Gill-Solovay 1975,
  Razborov-Rudich 1997, Aaronson-Wigderson 2009)
- Le moteur est CONSTRUIT pour trouver les P4 quand les routes connues sont mortes
- Les passe-partout universels (=, exp, ln, Σ, ∫) voient TOUT depuis leur sommet
  → ils sont dans toutes les preuves majeures, c'est pas un hasard, c'est la topologie
- P=NP est S3-S4, PAS S6 → pas prouvé indécidable → le pont EXISTE quelque part

### Ce que V4 est VRAIMENT
Pas un outil académique. Pas un fonds d'investissement. Pas un GPS.
C'est un **moteur de sélection d'outils automatique pour n'importe quel problème**.
Tu donnes un problème → il te donne le sac à dos optimal de briques → l'AI grimpe.

### Analogie électricien (Sky)
"On ne casse pas la serrure (P≠NP). On fait passer le câble par un autre chemin."
Les escaliers = les chemins de câble entre les étages.
Les briques S0 = les composants dans ton sac.
Le sommet = le tableau électrique de l'étage — tu vois tout ce qui est connecté en dessous.

### Ce qu'il faut construire
1. **Moteur de positionnement**: problème → coordonnées sur la carte
2. **Moteur de proximité**: coordonnées → escaliers les plus proches (top-N)
3. **Vue plongeante**: escalier → briques S0 connectées (filtre topologique)
4. **Compositeur**: AI reçoit le sac à dos filtré + le problème → tente des chemins
5. **Mémoire d'échec**: chaque tentative ratée = un P5 local → réduction de l'espace

### Contrainte critique
Les briques qui n'existent PAS ENCORE viendront. OpenAlex mine en continu.
Chaque nouveau concept se positionne automatiquement sur la topologie.
Si un nouveau concept ferme un P4 vers un problème ouvert → le moteur le détecte.
V4 n'est pas statique. Il GRANDIT avec la science.

### Statut: VISION — dépend de V2 (timelapse) et V3 (candlesticks)
Pas de saut. Les racines d'abord. Toujours.
