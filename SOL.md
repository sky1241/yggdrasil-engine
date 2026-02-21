# SOL.md — Fichier de Synchronisation Sky↔Claude
> Yggdrasil Engine — Versoix, 21 février 2026
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

## ÉTAT ACTUEL — 21 FÉV 2026 (session 3)
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
