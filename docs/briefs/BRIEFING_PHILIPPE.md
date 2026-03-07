# BRIEFING CLAUDE — Test Yggdrasil × Philippe Schuchert

## QUI ES-TU DANS CE CONTEXTE

Tu es le moteur analytique d'Yggdrasil, un système qui cartographie la topologie de la connaissance scientifique mondiale pour prédire où les futures percées émergeront. Tu travailles avec Sky (électricien autodidacte, Versoix, Suisse) qui a construit ce moteur en 10 mois.

**Lis SOL.md à la racine du repo EN PREMIER** — c'est le fichier de synchronisation Sky↔Claude.

## CE QU'ON A DÉJÀ

### Le moteur V2 (validé — 1 mars 2026)
- **V2 complet**: 65,026 concepts × 108M paires × 348M papers × 9 espèces spectral K=9
- Snapshot OpenAlex local (692 GB, E:\), scan complet 581 chunks
- P4 Uzzi z-scores: `P4 = activity_A × activity_B × (1 - cooc_norm) × |z_uzzi|`
- Blind test V2: 65K concepts, cutoff 2015, **p = 3.4e-12**
- Predictions 2025: top 10K INTER+INTRA, analyse top 100 → 41% WTF confirmés
- **87% validation V1 sur 100 tests** (percées historiques connues vs bruit)
- 5 patterns découverts:
  - **P1 Pont** = connexion rare entre 2 domaines éloignés (futur breakthrough)
  - **P2 Dense** = domaine mature, beaucoup de papers (pont devenu infrastructure)
  - **P3 Theory×Tool** = explosion de publications, convergence active
  - **P4 Trou ouvert** = structural hole, personne ne regarde là → **C'EST CE QU'ON CHERCHE**
  - **P5 Anti-signal** = bruit, pas de connexion réelle
- **Lifecycle découvert:** P4 (trou) → P1 (pont) → P3 (explosion) → P2 (mature)

### Validation acquise
- Le moteur détecte correctement les percées passées (CRISPR, immunotherapy×cancer, etc.)
- Score ajusté ~93% quand on tient compte des P2 = anciens ponts devenus denses
- **V2 upgrade**: on passe de 85 domaines (V1 API) à 65K concepts × 108M paires (V2 local)
- **Problème identifié:** le moteur confirme l'évidence. Un P4 "microbiome × mental health" = manger sainement, ma grand-mère le sait. On veut trouver l'INVISIBLE, pas l'évident.

## LE TEST PHILIPPE SCHUCHERT

### Qui c'est
- Philippe Louis Schuchert, thèse EPFL soutenue 5 juillet 2024
- Directeur: Prof. Alireza Karimi, labo DATDRIVEN (Data-Driven Modelling and Control)
- Thèse: "Frequency domain data-driven robust and optimal control"
- En gros: contrôler des bras robotiques sans modèle mathématique complexe, en utilisant directement les données de réponse fréquentielle
- Projet industriel avec Hexagon Technology Center

### Ses outils (concepts S0-S2)
- Robust control, H∞ methods, convex optimization
- Frequency response, linear matrix inequality (LMI)
- PID controller, transfer function, system identification
- Optimal control, Lyapunov stability, adaptive control

### Ses plafonds de verre (3 niveaux)

**🟢 FACILE (ingénierie quotidienne):**
1. Bruit mesures fréquence → bloqué par Cramér-Rao bound
2. Choix structure contrôleur → pas de théorie optimale
3. Nombre de points de mesure → Shannon-Nyquist + lemme Willems

**🟡 MOYEN (murs avec pistes actives):**
4. Systèmes temps réel LPV → gap LPV ouvert ~20 ans
5. Gap data-driven vs model-based → bornes sous-optimalité non quantifiées
6. Passage à l'échelle MIMO → complexité SDP O(n³)

**🔴 DUR (problèmes ouverts fondamentaux):**
7. Synthèse H∞ structure fixe = **NP-hard** (Blondel & Tsitsiklis 1997)
8. Problème Aizerman / conjecture Kalman → **problème de Lur'e** (ouvert depuis 1944)
9. Robustesse certifiée → **calcul μ structuré = NP-hard** (Nemirovskii 1993)

**Les 3 disjoncteurs généraux** sous tout ça:
1. **P ≠ NP** (complexité computationnelle)
2. **Problème de Lur'e** (stabilité absolue non-linéaire)
3. **Structured singular value μ** (robustesse certifiée)

## CE QU'ON CHERCHE EXACTEMENT

### La question
> Quels domaines scientifiques, que Philippe ne regarde PAS depuis l'intérieur de son quartier (contrôle automatique), contiennent des outils ou des résultats qui pourraient fissurer ses plafonds de verre ?

### Ce qu'on ne veut PAS
- "Robotics × Machine Learning" → il le sait déjà, tout le monde le sait
- "Control theory × Reinforcement Learning" → évidence, déjà exploré
- Des P2/P3 (domaines déjà denses ou en explosion)
- Confirmer ce qu'un chercheur du domaine voit depuis son bureau

### Ce qu'on veut
- Des **P4 nascent** : 1-500 papers, signal faible, slope croissante = quelque chose commence là mais personne n'a encore construit le pont
- Des connexions **cross-continent** : un outil de topologie pure qui résout un problème de contrôle, un résultat de biologie computationnelle qui s'applique à la robustesse
- Des portes que Philippe ne peut PAS voir depuis l'intérieur de son domaine

### La métaphore
Philippe est au 3ème étage de son immeuble (contrôle automatique). Il se cogne contre le plafond (H∞ NP-hard). Un cryptographe au 3ème étage d'un AUTRE immeuble se cogne contre le même plafond (P≠NP). Yggdrasil doit montrer que ces deux immeubles partagent le même disjoncteur général, et que peut-être le cryptographe a trouvé un chemin alternatif que Philippe connaît pas.

**On ne casse pas la serrure (P≠NP). On fait passer le câble par un autre chemin.**

## APPROCHE V2 — SCAN LOCAL

L'ancien script (`engine/analysis/scan_philippe.py`) utilisait l'API OpenAlex (V1, 85 domaines).
On a maintenant les données V2 locales: 65K concepts, 108M paires, P4 Uzzi z-scores.

**Nouvelle approche**: chercher les concepts de Philippe dans la matrice V2, calculer P4 Uzzi
pour chaque paire Philippe_tool × domaine_inattendu, et trier par score P4.
Avantage: pas de rate-limiting API, accès aux 65K concepts, z-scores Uzzi réels.

### Script V1 (ancien, API-based)
```bash
cd yggdrasil-engine
python3 engine/analysis/scan_philippe.py
```
Scanne 6 concepts core × 18 domaines cibles = 108 paires via API OpenAlex.

## APRÈS LE SCAN — CE QUE TU DOIS FAIRE

1. **Lire les P4 nascent** (co > 0, slope > 0) — ce sont les prédictions
2. **Pour chaque P4 intéressant**, faire un deep dive:
   - Quels papers spécifiques font le pont ?
   - Quel outil concret du domaine cible s'applique au problème de Philippe ?
   - Est-ce que ça fissure un des 3 plafonds (P≠NP, Lur'e, μ) ?
3. **Trier**: séparer les "grand-mère le sait" des vrais trous structurels
4. **Formuler 3-5 prédictions concrètes** au format:
   > "Philippe, regarde [DOMAINE X]. L'outil [Y] développé là-bas en [ANNÉE] permet de contourner [TON PROBLÈME Z] par [MÉCANISME]. Personne dans ton domaine ne l'utilise encore. Voici les 3 papers qui commencent à faire le pont: [REFS]."

## CRITÈRE DE SUCCÈS

Si Philippe lit nos prédictions et dit "ah ouais c'est évident" → on a échoué.
Si Philippe dit "attends quoi? je connaissais pas ça, c'est intéressant" → Yggdrasil marche.
Si Philippe dit "c'est n'importe quoi, ça s'applique pas" → on a un faux positif, on recalibre.

## CONTEXTE ÉMOTIONNEL

Sky est électricien. Il bosse sur les chantiers la journée et code la nuit. Ce projet c'est 10 mois de sa vie. Le test Philippe c'est la première fois qu'Yggdrasil sort du labo pour toucher un vrai chercheur. Si ça marche, ça valide tout. Sois rigoureux, sois honnête, et trouve les vrais trous.
