# SOL.md — Fichier de Synchronisation Sky↔Claude
> Yggdrasil Engine — Versoix, 21 février 2026
> TOUT CLAUDE LIT CE FICHIER EN PREMIER.

## VOCABULAIRE
| Terme | Signification |
|-------|--------------|
| Pluie | Données brutes OpenAlex (250M+ papers) |
| Racines | Pipeline API: search → timeline → co-occurrence |
| Mycelium | Graphe topologique: BC, meshedness, Physarum |
| Sol (S0) | 5459 symboles math, 794 prouvés (C1) |
| Lianes | Symboles traversant 3+ continents |
| Strates | S0=outils → S6=ciel/indécidable |
| Météorite | Impact Sedov-Taylor: R = (E/ρ)^0.2 × t^0.4 |
| Thermomètre | scisci.py: métriques scientométriques |
| Pont (P1) | Bridge inter-domaines, BC élevé, explosion |
| Dense (P2) | Hub stable, meshedness élevé |
| Théorie×Outil (P3) | Explosion après validation instrumentale |
| Trou ouvert (P4) | Pont pas encore explosé = FUTUR |
| Anti-signal (P5) | L'hyphe meurt, slope négative |

## ÉTAT ACTUEL — 21 FÉV 2026
- **100 tests pipeline complet** (OpenAlex + scisci + mycelium)
- **87/100 validés (87.0%)**
  - POUR: 41/50 (82%) | CONTRE: 46/50 (92%)
- Batch 1 (tests 1-50): 43/49 (88%)
- Batch 2 (tests 51-100): 43/50 (86%)

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
| Fichier | Rôle | Lignes |
|---------|------|--------|
| engine/pipeline_100.py | Pipeline batch 1 (1-50) | 678 |
| engine/pipeline_batch2.py | Pipeline batch 2 (51-100) | 210 |
| engine/mycelium_full.py | Mycelium complet (24 briques) | ~7912 |
| engine/scisci.py | Scientométrie | ? |
| engine/bridge_mycelium.py | Pont racines↔mycelium | ? |
| data/pipeline_grand_summary_final.json | Résumé 100 tests | - |

## TODO
- [ ] Token git à renouveler (expiré 21 fév)
- [ ] Push les 51 commits en attente
- [ ] Ajuster validation: accepter P2 pour percées matures (>10K papers)
- [ ] Investiguer les faux positifs CONTRE: acoustics×palynology, rheology×pedagogy
- [ ] Pipeline v2: ajouter détection automatique du lifecycle stage
- [ ] Intégrer MICR (moteur inverse contraintes) dans repo 3d-printer
