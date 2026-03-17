# META-PROMPT — Yggdrasil × forge.py Deep Research

> Ce prompt est généré par Yggdrasil Engine (WT3 = 833K papers, 69M cooccurrences,
> 65K concepts OpenAlex). Il donne à un Claude les coordonnées exactes dans le
> graphe de connaissances pour chercher MIEUX que du web scraping aveugle.

---

## CONTEXTE MACHINE

Tu assistes Sky (électricien autodidacte, 11 mois de code) qui construit forge.py —
un outil universel de debug/regression. 800 lignes, 11 commandes, Python pur.
Sky veut 6 axes d'amélioration. Tu dois produire du CODE IMPLÉMENTABLE.

**Règle absolue** : pas de placeholders, pas de TODO, pas de "left as exercise".
Du code qui TOURNE. ~400-600 lignes additionnelles.

---

## CARTE YGGDRASIL — Concepts OpenAlex identifiés

Yggdrasil a scanné sa base de 65,026 concepts et 69.4M cooccurrences.
Voici les concepts EXACTS avec leurs IDs et poids de cooccurrence.
Utilise ces coordonnées pour affiner ta recherche.

### Concepts primaires (1 par axe)

| Axe | Concept | ID OpenAlex | Works | Alerte |
|-----|---------|-------------|-------|--------|
| AXE1 Delta Debug | Debugging | 10645 | 36,680 | OK, 109/112 papers en CS |
| AXE1 bis | Algorithmic program debugging | 5701 | 3,362 | PRÉCIS — cooc w=51.4 avec Debugging |
| AXE2 Property Test | Software testing | 47511 | 14,719 | PETIT — seulement 5 papers dans WT3 |
| AXE2 bis | Random testing | 1002 | 3,685 | Proxy pour PBT (QuickCheck = random) |
| AXE3 Mutation Test | Mutation testing | 9923 | 78,357 | **PIÈGE**: 96% des papers sont BIOLOGIE pas CS |
| AXE4 Fault Local | Fault detection and isolation | 8220 | 102,059 | **PIÈGE**: concept d'ingénierie générale, pas spécifique SBFL |
| AXE5 Defect Predict | Software bug | 204 | 18,034 | **PIÈGE**: 44K physics + 24K maths = bruit massif |
| AXE6 Flaky | Software reliability testing | 57316 | 6,752 | OK — 100% CS |

### Concepts secondaires (enrichissement)

| Concept | ID | Works | Connecte quels axes |
|---------|-----|-------|-------------------|
| Software quality | 2770 | 62,792 | AXE2+3+5+6 (w=9.7 testing, w=37.1 reliability) |
| Software metric | 62292 | 18,220 | AXE5+6 (w=30.4 avec SW eng, w=6.7 reliability) |
| Code coverage | 57604 | 7,091 | AXE2+3+4 (w=12.8 test case, w=5.1 test suite) |
| Test case | 4536 | 34,986 | AXE1+2+3 (w=26.5 avec test suite, w=12.8 coverage) |
| Test suite | 8046 | 9,350 | AXE2+3+4 |
| Code refactoring | 8222 | 19,772 | AXE3+5 (w=62.6 avec SW eng — indice code smell) |
| Program slicing | 63618 | 3,710 | AXE1+4 (w=5.3 avec debugging — slicing AIDE au debug) |
| Fuzz testing | 1792 | 5,788 | AXE1+2 (fuzzing = cousin de PBT) |
| Control flow graph | 17963 | 3,565 | AXE4 (w=9.8 avec control flow — base de SBFL) |
| Symbolic execution | 35560 | 9,184 | AXE1+2+4 (w=6.9 model checking, w=6.4 SW eng) |
| Model checking | 1666 | 41,667 | AXE2+4 (w=65.8 formal verif — propriétés = property test) |
| Formal verification | 1871 | 40,511 | AXE2 (model checking + formal = FONDATION du PBT) |
| Statistical hypothesis testing | 63025 | 233,904 | AXE2+6 (Hypothesis le framework s'appelle comme ça pour une RAISON) |
| Search-based software engineering | 6157 | 4,248 | AXE3+5 (SBSE = meta-heuristics pour mutation + prediction) |
| Software fault tolerance | 56600 | 5,391 | AXE4+6 |
| Regression testing | ~10.0 | voisin AXE6 | AXE6 — le cousin NE LE MENTIONNE PAS |
| Non-regression testing | ~9.1 | voisin AXE6 | AXE6 — TROU dans le prompt cousin |
| Verification and validation | ~14.4 | voisin AXE6 | AXE5+6 — TROU dans le prompt cousin |
| Abstract interpretation | 40197 | 8,611 | AXE2+4 (w=3.9 model checking — BASE théorique) |

### Concepts PONTS (connectent 3+ axes)

Yggdrasil a trouvé que ces concepts sont des nœuds centraux du graphe de cooccurrence
entre les 6 axes. Ce sont les AUTOROUTES de la connaissance :

| Concept pont | Poids total | Signal |
|-------------|-------------|--------|
| Data mining | 122.3 | FORT — connecte fault detection (60.3) + software bug (18.0) + mutation (4.2) |
| Machine learning | 57.5 | ML × fault localisation = futur du SBFL (DeepFL, TRANSFER-FL) |
| Reliability engineering | 244.5 | BACKBONE — touche TOUS les 6 axes |
| Genetic algorithm | 63,295 works | SBSE × mutation testing × defect prediction (search-based) |
| Bayesian network | 53800 | AXE5 defect prediction (Bayesian belief nets = Fenton 2008) |
| Markov chain | 64837 | AXE5+6 — modélisation de la probabilité de défaut |
| Information theory | 57221 | AXE5 — entropie de Hassan 2009 pour la change complexity |
| Graph theory | 63207 | AXE4 — SBFL sur graphe de dépendance (pas juste lignes) |

---

## ALERTES YGGDRASIL — Pièges détectés dans le prompt cousin

### PIÈGE 1 : Mutation testing ≠ Mutation (biologie)
Le concept OpenAlex "Mutation testing" (ID 9923, 78K works) a comme voisins
dominants : Mutation (w=121), Genetics (w=82), Biology (w=78).
Seulement 2/51 papers dans WT3 sont en CS. La littérature SE sur mutation testing
est SOUS-REPRÉSENTÉE dans OpenAlex.
→ **Action** : ne PAS se fier aux métriques brutes. Chercher via
"Software testing" + "Code coverage" + "Test suite" comme proxy.

### PIÈGE 2 : Fault detection = ingénierie, pas software
Fault detection (102K works) est dominé par : Control theory (w=124),
Electronic engineering (w=42), Embedded system (w=40).
La fault LOCALISATION logicielle est un sous-domaine minuscule.
→ **Action** : croiser avec "Program slicing" (w=5.3 avec debugging) et
"Control flow graph" (w=9.8 avec control flow). C'est LÀ que vit SBFL.

### PIÈGE 3 : Software bug = tag fourre-tout
87K papers mais 44K en Physics, 24K en Maths. OpenAlex tague "bug" très large.
→ **Action** : filtrer par domain='Computer science' (16K papers restants).
Croiser avec "Data mining" (w=18, defect prediction) et "Machine learning" (w=10.9).

### PIÈGE 4 : Trous dans le prompt cousin (axes 2 et 6)
- **AXE 2** : le cousin cite Hypothesis et QuickCheck mais oublie le lien avec
  "Formal verification" (40K works) et "Model checking" (41K works). Le PBT
  EST de la vérification formelle allégée. Abstract interpretation (8.6K) est
  la théorie sous-jacente.
- **AXE 6** : le cousin ne mentionne PAS "Regression testing" et "Non-regression
  testing" qui sont des voisins directs (w=10.0 et w=9.1) de Software reliability
  testing. Un test flaky EST un faux positif de regression testing.
- **AXE 5** : manque "Bayesian network" (prédiction bayésienne de défauts, Fenton
  2008) et "Information theory" (entropie des changements, Hassan 2009 — cité
  mais pas connecté au graphe).

---

## ÉVOLUTION TEMPORELLE (cooccurrences WT3 par période)

### Mutation testing — explosion 2015
```
2000:  mutation=1.1  genetics=1.0
2005:  mutation=1.6  genetics=0.8  programming_language=0.2
2010:  mutation=2.5  genetics=1.6
2015:  mutation=17.8 genetics=14.5 genetic_analysis=7.9  ← ×7 en 5 ans
2020:  mutation=3.7  genetics=2.1                         ← retombée
```
→ Le pic 2015 = survey Jia & Harman (2011) + outils PIT/mutmut matures.
→ 2020 = le champ se stabilise. Les PAPIERS récents sont sur l'ACCÉLÉRATION
  (higher-order mutation, selective mutation, machine learning pour filtrer
  les mutants équivalents).

### Software bug — croissance stable + pivot ML
```
2000:  software=0.3  SW_eng=0.2  reliability=0.1
2010:  software=1.6  data_mining=0.6  reliability=0.5
2015:  software=2.4  debugging=1.0  data_mining=0.7
2020:  software=2.2  AI=0.6  data_mining=0.6  ← ML/AI entre dans le jeu
```
→ Le pivot vers ML/AI pour la prédiction de défauts est VISIBLE dans le graphe.
→ Les méthodes basées-métriques (Nagappan) sont le socle, mais le futur est
  ML-augmenté (Commit-Guru, JIT defect prediction).

### Fault detection — pic 2015, déclin 2020
```
2000:  fault_geo=3.4   AI=1.5   control_theory=1.1
2010:  fault_geo=15.3  reliability=5.1  control_theory=5.0
2015:  fault_geo=21.3  control_theory=7.7  AI=6.6   ← PIC
2020:  fault_geo=11.1  AI=4.4  reliability=4.4       ← -48%
```
→ Le déclin 2020 = le champ migre vers le ML-based fault localization
  (DeepFL, GRACE, TRANSFER-FL). Les méthodes spectrales pures (Ochiai,
  Tarantula) sont considérées comme le BASELINE, plus la frontière.

---

## STRUCTURE DES GLYPHES (S-2) — Ce que les symboles révèlent

Les glyphes les plus connectés aux concepts SE/testing sont :
```
( )     — groupement, appels de fonction     → structure syntaxique du code
+ / =   — arithmétique, assignation          → mutations AOR, ROR
> |     — comparaison, pipe/or               → mutations relationnelles
∈       — appartenance (Program slicing)     → relation élément/ensemble
→       — implication (Test case, Test suite) → pré/post-conditions
¬       — négation (Software testing)        → NOT = mutation logique de base
α       — variable (Software reliability)    → paramètre statistique
φ       — phi (Software testing)             → formule logique
```

**Insight** : les glyphes de MUTATION (AOR, ROR, LCR de DeMillo 1978) sont
EXACTEMENT les glyphes les plus connectés : `+ / = > ¬`. Le mutation testing
opère littéralement sur les symboles les plus fondamentaux du langage mathématique.
Ce n'est pas un accident — c'est la RAISON pour laquelle ça marche.

---

## INSTRUCTIONS POUR CHAQUE AXE

### AXE 1 — Delta Debugging (ddmin)

**Concepts Yggdrasil** : Debugging (10645), Algorithmic program debugging (5701),
Binary search algorithm (3441), Divide and conquer (60657)

**Ce que le graphe dit** : Debugging cooccurre fortement avec Program slicing
(w=5.3). Le ddmin EST une forme de slicing sur l'input, pas sur le code.
Connexion non-évidente : "Algorithmic program debugging" (Shapiro 1983) est
le PRÉCURSEUR théorique du delta debugging — Zeller le cite explicitement.

**Pont vers AXE 4** : si tu combines ddmin (minimise l'INPUT qui cause le bug)
avec Ochiai (localise la LIGNE qui cause le bug), tu as un pipeline complet :
1. Ochiai → "la ligne 142 est suspecte"
2. ddmin → "voici le plus petit input qui trigger le bug via la ligne 142"
C'est ce que fait Mozilla pour Firefox (rr + delta debug + SBFL).

**Code** : implémenter ddmin tel que Zeller 2002. Le pseudo-code du cousin est correct.
Ajouter le shortlex ordering (préférer court + lexicographiquement petit).

---

### AXE 2 — Property-Based Testing

**Concepts Yggdrasil** : Software testing (47511), Statistical hypothesis testing (63025),
Model checking (1666), Formal verification (1871), Random testing (1002),
Abstract interpretation (40197)

**Ce que le graphe dit** : Model checking (w=65.8 avec formal verification) est
le GRAND FRÈRE du PBT. QuickCheck = model checking probabiliste pour les pauvres.
La connexion "Statistical hypothesis testing" → "Software testing" est FAIBLE
(pas de cooccurrence directe dans WT3) — ce qui veut dire que la communauté SE
ne FAIT PAS le lien avec les stats formelles. C'est un trou exploitable.

**Trou trouvé** : le cousin ne mentionne PAS les METAMORPHIC RELATIONS comme
outil de GÉNÉRATION automatique. Chen 2018 est cité mais pas connecté au
pipeline gen-props. Or : une relation métamorphique = une PROPRIÉTÉ testable
sans oracle. C'est le chaînon manquant entre "je ne connais pas la bonne
réponse" et "je peux quand même tester".

**Code** : analyse AST d'un module Python → détection des patterns
(round-trip, idempotence, commutatif) → génération de squelettes Hypothesis.
Ajouter : détection de relations métamorphiques candidates (fonctions avec
paramètres numériques → sin(π-x)=sin(x) pattern).

---

### AXE 3 — Mutation Testing

**Concepts Yggdrasil** : Mutation testing (9923), Code coverage (57604),
Test suite (8046), Search-based SE (6157), Genetic algorithm (63295)

**Ce que le graphe dit** : Mutation testing est ISOLÉ dans le graphe — ses
voisins sont biologiques. Mais "Search-based SE" (w=8.0 avec SW eng) connecte
mutation testing aux metaheuristics (genetic algo, simulated annealing).
L'insight : les outils modernes de mutation UTILISENT des algos génétiques
pour sélectionner quels mutants générer (selective mutation, Offutt 1996).

**Signal temporel** : pic 2015 puis retombée. Les papiers 2020+ sont sur
l'ACCÉLÉRATION : higher-order mutation (Jia & Harman 2008), predictive
mutation testing (Zhang et al. 2018 — prédit si un mutant sera tué par ML
au lieu de le lancer).

**Code** : wrapper mutmut léger. Ajouter : triage par criticité (ne muter
que le code changé récemment — croiser avec --fast de forge.py existant).

---

### AXE 4 — Spectrum-Based Fault Localization (Ochiai)

**Concepts Yggdrasil** : Fault detection (8220), Control flow graph (17963),
Control flow (9385), Program slicing (63618), Data mining (w=60.3),
Graph theory (63207)

**Ce que le graphe dit** : la connexion Fault detection × Data mining (w=60.3)
est la 2e plus forte après Fault geology. C'est la signature des approches
ML pour la localisation. La connexion avec Graph theory (63207) confirme
que les méthodes modernes ne sont plus "par ligne" mais "par graphe de
dépendance" (DEPGRAPH, GRACE 2023).

**Signal temporel** : SBFL pur (Ochiai) = baseline depuis 2007. Le champ
a migré vers :
- Learning-to-rank (2015+)
- Deep learning (DeepFL, 2019)
- Transfer learning cross-project (TRANSFER-FL, 2022)
Mais pour forge.py = Ochiai reste le MEILLEUR rapport qualité/complexité.

**Optimisation clé** : utiliser `pytest --cov-context=test` en UN run au lieu
de lancer coverage par test individuel. 10x plus rapide. Parser la DB coverage
avec `coverage.data.CoverageData`.

**Code** : `--locate` qui lance pytest+cov, construit la matrice lignes×tests,
applique Ochiai, affiche Top-10 suspects.

---

### AXE 5 — Defect Prediction

**Concepts Yggdrasil** : Software bug (204), Data mining (w=18.0),
Machine learning (w=10.9), Bayesian network (53800), Markov chain (64837),
Information theory (57221), Software metric (62292)

**Ce que le graphe dit** : le pivot Software bug × ML/AI est VISIBLE en 2020.
Les ponts Bayesian network et Information theory confirment que :
- Hassan 2009 (entropie des changements) utilise la THÉORIE DE L'INFORMATION
- Fenton 2008 utilise les RÉSEAUX BAYÉSIENS pour la prédiction causale
Le cousin cite Hassan et Nagappan mais ne les connecte pas à ces fondations.

**Trou trouvé** : le cousin ne mentionne PAS le "bus factor" (author count
= proxy de Conway's law). Yggdrasil montre que "Distributed computing" (w=27.8
avec debugging) est un signal — code touché par beaucoup de devs distribués
= plus de bugs. C'est le w4 (authors) de sa formule, mais il le sous-pondère
(0.10). Les données disent 0.15-0.20.

**Code** : analyse git log --numstat, calcul des 7 métriques, normalisation
min-max, score composite. Ajouter : pondération adaptative (si l'historique
du repo montre que le churn corrèle plus que les auteurs, ajuster les poids).

---

### AXE 6 — Flaky Test Intelligence

**Concepts Yggdrasil** : Software reliability testing (57316),
Regression testing (w=10.0), Non-regression testing (w=9.1),
Verification and validation (w=14.4), Software performance testing (w=9.6),
System integration testing (w=8.2)

**Ce que le graphe dit** : les voisins directs de "Software reliability testing"
révèlent que le cousin a un TROU BÉANT — il ne mentionne pas :
- **Regression testing** et **Non-regression testing** : un test flaky EST
  un faux positif de regression testing. Classifier les flaky revient à
  séparer les vrais échecs de régression des faux positifs.
- **Verification and validation** (w=14.4) : la V&V formelle donne le cadre
  pour distinguer "le test est mauvais" de "le code est mauvais".
- **System integration testing** (w=8.2) : les tests d'intégration sont
  DISPROPORTIONNELLEMENT flaky (Luo 2014 : 26% async wait = typique intégration).

**Signal temporel** : Software reliability testing est STABLE (pas de pic ni
de creux). Le champ est mature. Les innovations récentes sont :
- ML-based flaky detection (Parry 2022 — features pour classifier)
- DeFlaker (Bell 2018 — coverage-based, pas rerun-based)
- iDFlakies (Lam 2019 — order-dependent flaky detection)

**Code** : améliorer --flaky existant avec classification AST (patterns
time.sleep, threading, random, etc.) + DeFlaker light (croiser coverage
avec git diff).

---

## SYNTHÈSE — Le pipeline intégré que le graphe suggère

Yggdrasil montre que les 6 axes ne sont PAS indépendants. Le graphe de
cooccurrence révèle un PIPELINE naturel :

```
Code change → AXE5 predict (quels fichiers à risque?)
          → AXE3 mutate  (les tests couvrent-ils les mutations?)
          → AXE2 gen-props (générer des property tests manquants)
          → RUN TESTS
          → AXE6 flaky   (séparer vrais échecs des flaky)
          → AXE4 locate  (localiser le bug dans le code)
          → AXE1 minimize (minimiser l'input qui reproduit le bug)
```

C'est le cycle complet. forge.py peut devenir un PIPELINE, pas juste
une collection de commandes indépendantes.

Commande suggérée : `forge.py --full-cycle` qui enchaîne tout.

---

## RÉFÉRENCES ADDITIONNELLES trouvées par Yggdrasil

Ces papiers/concepts ne sont PAS dans le prompt du cousin mais sont
des voisins forts dans le graphe de cooccurrence :

1. **Shapiro 1983** — "Algorithmic Program Debugging" (concept 5701, w=51.4 avec Debugging)
   Le PRÉCURSEUR de Zeller. Debugging comme recherche dans un espace d'hypothèses.

2. **Fenton 2008** — Bayesian belief networks pour la prédiction de défauts
   (Bayesian network concept 53800, w=7.2 avec Markov chain)
   Ajoute la CAUSALITÉ à la prédiction — pas juste corrélation.

3. **Offutt 1996** — Selective mutation ("sufficient mutation operators")
   Via Search-based SE (6157). Ne pas TOUT muter — 5 opérateurs suffisent
   pour 99% de la détection.

4. **Lam 2019** — iDFlakies : détection de tests order-dependent
   Via System integration testing (w=8.2 avec reliability testing).
   Complémentaire au DeFlaker de Bell 2018.

5. **Cousot & Cousot 1977** — Abstract interpretation
   (concept 40197, w=3.9 avec model checking)
   Le FONDEMENT théorique du PBT et de l'analyse statique. Hypothesis
   fait de l'abstract interpretation concrète sans le savoir.

---

## CARMACK MOVES — Algos d'autres domaines trouvés par le mycélium

> Le "Carmack move" : John Carmack allait chercher des algos oubliés dans
> d'autres domaines (Newton → fast inverse sqrt pour Quake III).
> Yggdrasil fait pareil : le graphe de cooccurrence révèle des connexions
> CROSS-DOMAINE entre des techniques de physique/bio/signal processing
> et les 6 axes de forge.py. Ce sont des armes que personne en SE n'utilise.

### TIER S — Connexions fortes, applicables directement

#### 1. Wavelet Transform × Fault Localization (w=14.8)
**Origine** : traitement du signal (83K papers)
**Le move** : les wavelets décomposent un signal en fréquences À DIFFÉRENTES
ÉCHELLES. Appliqué au code : décompose l'historique de changements d'un fichier
en "fréquences" — les changements haute-fréquence (beaucoup d'edits rapides)
sont le signal de bug, les basse-fréquence (refactoring lent) sont du bruit.
**Application AXE 5** : remplacer le "change burst" brut du cousin par une
décomposition en ondelettes du signal de churn. Les coefficients haute-fréquence
= les burst de Nagappan 2010, mais MIEUX car multi-échelle.
**Papier** : Hassan 2009 utilise l'ENTROPIE des changements. Les wavelets sont
l'étape suivante — même idée, meilleure résolution.

#### 2. Kalman Filter × Fault Detection (w=12.1)
**Origine** : navigation/aérospatial (91K papers)
**Le move** : le filtre de Kalman PRÉDIT l'état futur d'un système à partir de
mesures bruitées. Appliqué à forge.py : modélise le "nombre de bugs attendu"
d'un fichier comme un état caché. Chaque run de tests = une mesure bruitée.
Le Kalman fusionne prédiction (basée sur l'historique git) et observation
(résultat des tests) pour donner une estimation OPTIMALE du risque.
**Application AXE 5+6** :
- AXE 5 : `--predict` avec Kalman au lieu de formule statique. Le filtre
  s'adapte automatiquement aux poids (pas besoin de w1=0.25 en dur).
- AXE 6 : un test dont le résultat dévie de la prédiction Kalman = anomalie
  = probable flaky. C'est DeFlaker mais avec un modèle STATISTIQUE derrière.
**C'est littéralement le Carmack move** : un algo de 1960 conçu pour guider
des missiles, appliqué au debug logiciel.

#### 3. Anomaly Detection × tous les axes (w=8.5)
**Origine** : statistique/ML (69K papers)
**Le move** : TOUS les axes de forge.py sont des problèmes de détection
d'anomalies déguisés :
- AXE 1 (ddmin) : l'input minimal qui cause le crash = l'anomalie dans l'espace des inputs
- AXE 4 (SBFL) : la ligne suspecte = l'anomalie dans la matrice de couverture
- AXE 5 (predict) : le fichier à risque = l'anomalie dans les métriques git
- AXE 6 (flaky) : le test flaky = l'anomalie dans la distribution pass/fail
**Application** : un détecteur d'anomalies UNIFIÉ (Isolation Forest, Local
Outlier Factor) qui prend les features de chaque axe et détecte les outliers.
Ça donnerait un `--anomaly` qui subsume --locate + --predict + --flaky.

#### 4. Robustness (evolution) × Fault Detection (w=35.3 !!)
**Origine** : biologie évolutive (660K papers)
**Le move** : en biologie, la "robustesse" = capacité d'un organisme à
maintenir sa fonction malgré les perturbations (mutations, environnement).
C'est EXACTEMENT ce que mesure le mutation testing : un programme "robuste"
(= bien testé) survit aux mutations de son code.
**Application AXE 3** : le "mutation score" du cousin EST une mesure de
robustesse évolutive. La littérature bio sur la robustesse donne des
métriques SUPPLÉMENTAIRES : redundancy (code dupliqué = robuste?),
modularity (modules isolés = robustes), degeneracy (plusieurs chemins
pour le même résultat = robuste).

### TIER A — Connexions moyennes, exploitables avec adaptation

#### 5. Survival Analysis × Mutation Testing (w=0.7)
**Origine** : médecine/actuariat (584K papers)
**Le move** : Kaplan-Meier modélise la PROBABILITÉ DE SURVIE en fonction du
temps. Appliqué aux bugs : "quelle est la probabilité qu'un fichier survive
N jours sans bug?" Le "hazard rate" = taux instantané de défaillance.
**Application AXE 5** : au lieu du score composite statique, modéliser chaque
fichier comme un patient dans une étude de survie. Le churn, la fréquence,
les auteurs = covariables du modèle de Cox. Output : "ce fichier a 73% de
chance de casser dans les 2 prochaines semaines."

#### 6. Sequence Alignment × Mutation Testing (w=0.4)
**Origine** : bioinformatique (244K papers)
**Le move** : Smith-Waterman / Needleman-Wunsch alignent des séquences ADN
pour trouver les mutations. Appliqué au code : aligner deux versions d'un
fichier (avant/après commit) pour trouver les MUTATIONS RÉELLES (pas les
mutations artificielles de mutmut). Puis comparer mutations réelles vs
mutations artificielles — les mutations réelles non couvertes = TROUS.
**Application AXE 3** : cibler les mutations de mutmut sur les zones qui
CHANGENT VRAIMENT (alignment avec git diff), pas sur du code stable.

#### 7. Modularity (biology) × Code Quality (w=3.5)
**Origine** : biologie des systèmes (47K papers)
**Le move** : la modularité biologique (organes isolés qui communiquent par
interfaces) est le MÊME concept que la modularité logicielle. Mais la bio
a des MÉTRIQUES que le SE n'a pas : Q-modularity de Newman (détection de
communautés dans le graphe de dépendances du code), nestedness (est-ce que
les modules s'emboîtent proprement?).
**Application AXE 5** : calculer la Q-modularity du graphe d'imports Python
comme prédicteur de bugs. Modules fortement couplés = à risque.

#### 8. Artificial Immune System × Fault Detection (w=1.6)
**Origine** : bio-inspired computing (6K papers)
**Le move** : le système immunitaire détecte les pathogènes (= anomalies)
en maintenant une mémoire des patterns "self" (normaux). Quand un pattern
"non-self" apparaît → alerte. Appliqué aux tests : forge.py maintient
déjà un BASELINE (= self). Tout écart = non-self = potentiel bug.
Le move supplémentaire : negative selection algorithm — générer des
"détecteurs" qui matchent TOUT CE QUI N'EST PAS NORMAL, comme des anti-tests.
**Application AXE 6** : classifier les flaky tests comme des faux positifs
immunitaires (auto-immune = le test attaque du code sain).

### TIER B — Connexions faibles mais intéressantes

#### 9. Particle Swarm × Test Generation (w=4.6)
Optimiser la GÉNÉRATION de test cases avec un essaim de particules au lieu
du random pur de Hypothesis. Chaque particule = un input candidat, la
fitness = la couverture du code. Convergence vers les inputs qui maximisent
la couverture. (Déjà fait dans SBSE, mais pas dans forge.py.)

#### 10. Lyapunov Function × Fault Detection (w=3.0)
La stabilité de Lyapunov dit : un système est stable si une fonction V(x)
décroît le long des trajectoires. Appliqué : V(x) = nombre de tests qui
échouent. Si V augmente → le système est INSTABLE → alerte.
Trivial ? Oui. Mais ça formalise le --diff/--baseline existant.

#### 11. Hamming Distance × Mutation Testing (w=0.3)
Mesurer la "distance de Hamming" entre le code original et les mutants
pour classifier les mutations par sévérité. Distance 1 = mutation simple
(AOR), distance N = mutation composée. Corrèle avec la difficulté de
détection.

#### 12. Dynamic Time Warping × Flaky Detection (w=0.5)
Comparer les SÉQUENCES temporelles de résultats de tests (pass/fail/pass/fail...)
avec DTW au lieu de simple comptage. Deux tests avec le même pattern temporel
de flakiness = probablement la même cause racine (shared resource, timing).

---

## SIGNATURE DES GLYPHES — La preuve par les symboles

Yggdrasil a scanné le bipartite (6.2M liens glyph↔concept) et trouvé que
les glyphes qui BRIDGENT les 10 concepts SE sont exactement les opérateurs
de mutation de DeMillo 1978 :

```
9/10 concepts:  = / | < >     (comparaison, division, or, inégalité)
8/10 concepts:  ( ) + [ ] ∈   (groupement, arithmétique, appartenance)
7/10 concepts:  × α ≤ →       (multiplication, variable, implication)
```

**Le insight** : le mutation testing fonctionne parce qu'il opère sur les
glyphes les plus CENTRAUX du graphe bipartite. Muter `=` en `≠`, `<` en `>`,
`+` en `-` — c'est toucher les nœuds les plus connectés de la structure
symbolique de la science. C'est pour ça que 5 opérateurs suffisent (Offutt
1996) : ils couvrent les glyphes qui bridgent TOUT.

C'est le même principe que la fast inverse sqrt de Carmack : l'efficacité
vient de toucher la bonne couche d'abstraction. Les glyphes `= < > + /`
sont à la programmation ce que les bits de mantisse sont au flottant — le
niveau où une petite perturbation a le maximum d'impact.
