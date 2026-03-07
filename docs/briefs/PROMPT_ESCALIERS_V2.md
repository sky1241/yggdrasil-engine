🌿 PROMPT — ESCALIERS SPECTRAUX V2 + TRI VIVANT/MUSÉE

Copie-colle ce prompt au prochain Claude. Il aura tout.


QUI EST SKY
Électricien suisse (Versoix), autodidacte ADHD, code depuis 10 mois avec l'IA comme outil principal. Pense en architecte, pas en codeur — il dessine les systèmes dans sa tête et Claude implémente. Parle franglais. Sessions hyperfocus la nuit. Utilise des métaphores physiques (câbles, escaliers, bâtiment) pour conceptualiser.
Comment bosser avec lui:

Sky monte (direction, vision, arbre visible). Claude descend (racines, code).
Racines > arbre. Toujours.
Pas de blabla. Direct. Technique.
Il dit "cousin" pour parler d'un autre Claude qui bosse en parallèle.
Push git après chaque étape. Token dans cléjamaiseffacer.txt. JAMAIS l'afficher.

LE PROJET — YGGDRASIL ENGINE
Système pour cartographier TOUT le savoir scientifique humain et prédire où les futures découvertes vont émerger.
Repo: github.com/sky1241/yggdrasil-engine
Première action obligatoire: git pull puis lire SOL.md à la racine, puis docs/LISTE_COURSE_21FEV.md.

ARCHITECTURE DES 3 CUBES (décision du 21 fév)
Sky a défini 3 modes de visualisation. C'est l'architecture fondamentale.

CUBE 1 — LE VIVANT 🟢
Que ce qui est prouvé + utilisé activement. Le chantier livré. Les clés remises.
Critère: works_count >= Q1 (25e percentile) de son domaine.
Pourquoi Q1 par domaine: "PIB pondéré par habitant". La volcanologie (79 concepts, médiane 5,819) et la chimie (4,746 concepts, médiane 3,777) ont pas le même seuil. Un concept à 6,000 papers est vivant en volcanologie mais mort en écologie (médiane 19,048).
Résultat: 15,556 concepts vivants (75.1%) | 5,144 musée (24.9%)

CUBE 2 — LE MUSÉE 🔴
Tout ce qui N'EST PAS dans le Cube 1:
- Concepts prouvés mais peu utilisés (Halting problem: 5,050 papers, Gödel: 1,764)
- Conjectures ouvertes reconnues (Riemann, Goldbach, Hodge, abc)
- Niches de niches de chaque domaine (en dessous du Q1)
Le musée c'est pas "faux". C'est "mort" — personne le touche au quotidien.

CUBE 3 — FUSION
Les deux allumés ensemble. La carte complète.

L'INSIGHT CLÉ: LES CONTRADICTIONS ENTRE COUCHES
Le works_count (multimètre sur la prise) et le mycelium Physarum (pince ampèremétrique sur le câble) mesurent tous les deux "vivant ou mort" mais pas au même niveau.
Les cas intéressants sont les CONTRADICTIONS:
1. Concept vivant + connexions mortes → CONCEPT ISOLÉ (bizarre, à investiguer)
2. Concept mort + connexions vivantes → PONT CACHÉ (personne le regarde mais tout le monde l'utilise)
3. Zone de vivants avec TROU au milieu → P4 = VIDE FERTILE (prochaine découverte)
Ces contradictions sont le vrai signal. Pas les cas où les deux sont d'accord.

LES 2 TYPES D'ESCALIERS SPECTRAUX (découverte du 21 fév)
L'ancien modèle disait: symboles multi-continents = lianes = escaliers de secours.
Le spectral a révélé que c'est FAUX en partie. Il y a 2 mécanismes:

TYPE 1: LIANE GÉOGRAPHIQUE 🌿 (détectée par position spectrale)
Le concept a DÉMÉNAGÉ. Sa position spectrale (px, pz) est plus proche d'un continent alien que de son propre continent.
Exemples: Perovskite (chimie→ingénierie), Nuclear astrophysics (physique→chimie)
Score = excentricité × portée inter-centroïdes
Résultat: 4,548 détectées, top routes = PHYSIQUE↔BIO (1.18), PHYSIQUE↔CHIMIE (0.95), MATH↔PHYSIQUE (0.74)
Le bruit BIO↔TERRE (2,583 lianes) est NATURELLEMENT filtré car portée = 0.208 (centroïdes quasi collés)

TYPE 2: PASSE-PARTOUT 🔑 (détecté par multi-continent historique)
Le concept reste CHEZ LUI (collé au centroïde Math) mais tout le monde l'emprunte.
Comme le tableau électrique: il est dans l'entrée mais il alimente toute la maison.
Exemples: exp (6C), ∫ (6C), Σ (6C), ln (6C)
INVISIBLE en spectral car position = moyenne pondérée → tirée vers Math où ils apparaissent le plus
69 passe-partout identifiés dans l'ancien dataset

MÉTAPHORE DE SKY: pont = tu traverses le câble dans le mur. Clé = tu viens brancher au tableau.

NETTOYAGE S0 (fait le 21 fév)
Scan complet des 20,692 concepts S0 C1:
- 99.90% propres
- 13 vrais suspects à virer (Black hole information paradox, Homotopy hypothesis, Non-standard cosmology, Unparticle physics, Multiple chemical sensitivity, Group selection, International Linear Collider, Neocolonialism, Creative class, Bertrand paradox economics, Ridge push, Phylogenetic nomenclature, Superselection)
- 1 bug mapping: Hagen-Poiseuille flow classé "droit" au lieu de "fluides"
- 8 concepts C2 traînent en S0 (Convergence economics, Expected utility hypothesis, etc.)
- Poincaré conjecture marquée C2 mais RÉSOLUE par Perelman → doit passer C1

CENTROÏDES CONTINENTS (calculés)
BIO         (5,983) → px=-0.4203, pz=+0.2748
CHIMIE      (5,232) → px=-0.0854, pz=+0.7691
MATH        (2,636) → px=+0.1940, pz=-0.1604
INGENIERIE  (1,933) → px=+0.0628, pz=+0.1251
TRANSVERSAL (1,864) → px=+0.0158, pz=+0.0085
TERRE       (1,138) → px=-0.2124, pz=+0.2713
HUMAINES    (1,069) → px=-0.2376, pz=-0.4796
INFO          (949) → px=+0.0432, pz=-0.4816
PHYSIQUE      (445) → px=+0.7578, pz=+0.3259

FICHIERS CLÉS NOUVEAUX (créés le 21 fév)
docs/LISTE_COURSE_21FEV.md          → ✅/❌ FAIT/PAS FAIT — ta todo list, lis ça en deuxième après SOL.md
engine/escaliers_spectraux.py (350L) → Moteur détection lianes géo + passe-partout + export unifié
data/escaliers_spectraux.json        → 500 top lianes géographiques
data/escaliers_unified.json          → Export unifié (200 geo + 69 key) pour viz
viz/escaliers_spectraux.html         → Viz 2D interactive Canvas (lianes + passe-partout + toggle continents)

FICHIERS EXISTANTS (rappel)
SOL.md                              → LIRE EN PREMIER
engine/gen_viz_v3.py       (501L)   → Générateur La Pluie v3
viz/yggdrasil_rain_v3.html (392L)   → Visualisation 3D avec filtres continents
data/strates_export_v2.json         → TOUT le dataset (21,524 concepts, positions spectrales)
data/mined_concepts.json   (8MB)    → Dataset OpenAlex avec works_count + cited_by_count
engine/mycelium_full.py    (7912L)  → Mycelium complet (24 briques, Physarum, BC)

CE QU'IL RESTE À FAIRE

1. Implémenter le tri vivant/musée dans La Pluie v3
   - Ajouter le works_count à chaque concept dans strates_export_v2.json (croiser avec mined_concepts.json)
   - Calculer Q1 par domaine
   - Cube 1 = vivant (>= Q1), Cube 2 = musée (< Q1), Cube 3 = fusion
   - Toggle dans l'interface (les checkboxes C1/C2/C3 Fusion existent déjà)

2. Nettoyage S0
   - Virer les 13 suspects vers la bonne strate/classe
   - Fixer le bug Hagen-Poiseuille (droit → fluides)
   - Déplacer les 8 C2 de S0 vers leur vraie strate
   - Poincaré conjecture: C2 → C1

3. Détection de contradictions works_count vs mycelium
   - Croiser le flux Physarum (connexions) avec le works_count (nœuds)
   - Lister les concepts isolés (vivant + connexions mortes)
   - Lister les ponts cachés (mort + connexions vivantes)
   - Lister les vides fertiles (P4 entre zones vivantes)

4. Intégrer les escaliers spectraux dans La Pluie v3
   - Layer toggle pour lianes géographiques (lignes orange)
   - Layer toggle pour passe-partout (tirets bleus)
   - Tooltip avec score et route

5. Visualisation 3D des routes
   - Les escaliers en 3D entre les strates
   - Potentiellement voir des patterns dans le vide entre vivant et musée

RAPPELS
- SOL.md = source de vérité. Le lire EN PREMIER.
- Push git régulièrement. Token dans cléjamaiseffacer.txt.
- JAMAIS afficher le token. Filtrer avec grep -v "ghp_\|x-access".
- Sky pense en architecte. Il donne la direction. Claude code.
- Si un résultat est surprenant → noter tel quel. Pas de triche.
- Le mot "escalier" = liane = pont inter-continent dans l'espace spectral.
- Le mot "ascenseur" = chemin vertical intra-continent (Pattern Dense P2).
- Le mot "vivant" = concept au-dessus du Q1 de son domaine en works_count.
- Le mot "musée" = concept en dessous du Q1 = mort mais pas faux.
- Le mot "tableau électrique" = passe-partout (exp, ∫, Σ) qui reste chez lui mais alimente tout.
- Le mot "câble dans le mur" = liane géographique qui traverse physiquement entre 2 continents.

Sky × Claude — 21 Février 2026, matin, Versoix.
Un électricien, un café, et 3 cubes.
