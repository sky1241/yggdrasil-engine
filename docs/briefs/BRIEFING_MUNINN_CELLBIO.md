# BRIEFING MUNINN — Cell Biology: Les 22 Blind Spots
## Addendum au Scan Yggdrasil du 10 Mars 2026

**De**: Yggdrasil Engine (Huginn)
**Pour**: Muninn (cousin)
**Sujet**: Les 22 paires Type C (perceptuelles) en biologie cellulaire
**Méthode**: Scan Uzzi (§1-6 du briefing principal) + WT2 papers + littérature

---

## 1. POURQUOI CE BRIEFING

Dans le scan principal, Cell Biology est le signal le plus fou: **22/23 paires sont Type C** (perceptuel). Ça veut dire que les deux côtés PUBLIENT activement, les structures mathématiques EXISTENT des deux côtés, mais personne ne fait le pont. Ce n'est pas un manque d'outils (Type A) ni un manque d'idée (Type B) — c'est un **angle mort collectif**.

Ce briefing détaille les 22 paires, les papers pionniers trouvés dans WT2 (22 papers sur 833K = 0.003%), et la littérature existante pour identifier ce qui est **actionable** pour Muninn.

---

## 2. LES 22 PAIRES TYPE C

3 concepts Muninn × 10 concepts Cell Bio = 22 paires (+ 1 Type B).

### F6 — Spectral (Eigenvalues + Markov chain) → 17 paires

| # | Muninn | × Cell Bio | z-score | cooc | Papers WT2 |
|---|--------|-----------|---------|------|------------|
| 1 | Eigenvalues | Immune system | -10.03 | 0.16 | **0** |
| 2 | Eigenvalues | Enzyme | -9.23 | 0.12 | **0** |
| 3 | Eigenvalues | Cell | -9.19 | 0.15 | **0** |
| 4 | Eigenvalues | Receptor | -9.17 | 0.10 | **0** |
| 5 | Eigenvalues | Antibody | -9.11 | 0.01 | **0** |
| 6 | Eigenvalues | In vitro | -8.64 | 0.01 | **0** |
| 7 | Eigenvalues | Gene expression | -8.53 | 0.08 | **0** |
| 8 | Eigenvalues | DNA | -8.17 | 0.78 | 2 |
| 9 | Eigenvalues | Virus | -8.12 | 0.22 | **0** |
| 10 | Eigenvalues | Cell culture | -7.94 | 0.02 | **0** |
| 11 | Markov chain | Immune system | -9.50 | 0.54 | **0** |
| 12 | Markov chain | Enzyme | -8.72 | 0.66 | **0** |
| 13 | Markov chain | Cell | -8.68 | 0.75 | 1 |
| 14 | Markov chain | Receptor | -8.63 | 0.95 | 1 |
| 15 | Markov chain | Antibody | -8.64 | 0.20 | **0** |
| 16 | Markov chain | In vitro | -8.22 | 0.01 | **0** |
| 17 | Markov chain | Gene expression | -8.00 | 1.05 | 5 |

### F1 — Ebbinghaus (Exponential function) → 5 paires

| # | Muninn | × Cell Bio | z-score | cooc | Papers WT2 |
|---|--------|-----------|---------|------|------------|
| 18 | Exp function | Immune system | -9.21 | 0.26 | 1 |
| 19 | Exp function | Enzyme | -8.35 | 1.19 | **0** |
| 20 | Exp function | Receptor | -8.38 | 0.54 | 1 |
| 21 | Exp function | Antibody | -8.32 | 0.46 | **0** |
| 22 | Exp function | Cell | -8.28 | 1.61 | 1 |

### Type B (le seul)

| # | Muninn | × Cell Bio | z-score | cooc | Pattern |
|---|--------|-----------|---------|------|---------|
| 0 | Eigenvalues | Immune system | -10.03 | 0.16 | P5 (anti-signal) |

---

## 3. PAPERS PIONNIERS WT2 (22 papers / 833K)

### Eigenvalues × DNA (2 papers — les SEULS eigenvalue-bio)

**`1101.3738`** [Chemistry] — *First-principles GW calculations for DNA and RNA nucleobases* (Faber et al.)
- Eigenvalues de quasiparticules pour énergies d'ionisation des bases ADN/ARN
- Pont chimie quantique → biologie moléculaire

**`1402.0654`** [Physics] — *Electron or hole transfer along DNA dimers, trimers and polymers* (Simserides)
- **DOUBLE PONT**: eigenvalues + exponential function sur transport de charge dans l'ADN
- Le SEUL paper avec 2 concepts Muninn simultanés

### Markov chain × Gene expression (5 papers — le plus fertile)

**`0803.3942`** [CS] — *Hidden spatial-temporal Markov random field for gene expression data* (Wei & Li)
- HMM spatio-temporel sur voies KEGG, appliqué à l'inflammation
- Pont direct CS → bio systems

**`1112.4694`** [Biology] — *A stochastic model for virus growth in a cell population* (Bjornberg et al.)
- Markov chain × {Cell, Virus} — stratégie virale optimale par couplage de processus Markov

**`1504.04322`** [CS] — *Capacity of Level and Type Modulation in Molecular Communication* (Aminian et al.)
- Markov chain pour dynamique de blocage ligand-récepteur

### Exponential function × Immune system (1 paper)

**`1309.3332`** [Biology] — *Non-linear model of cell turnover and tumorigenesis in intestinal crypt* (d'Onofrio & Tomlinson)
- Bifurcation de croissance exponentielle irréversible dans le développement tumoral

### ZÉRO papers trouvés pour 13 paires sur 22
Les trous les plus profonds: Eigenvalues × {Immune system, Enzyme, Cell, Receptor, Antibody, Gene expression, Virus}. **Aucun paper arXiv ne connecte les eigenvalues à ces concepts bio.** C'est le désert.

---

## 4. CE QUI EXISTE DANS LA LITTÉRATURE (hors arXiv)

Le scan WT2 ne voit que arXiv (physique, CS, maths). La littérature bio/med publie ailleurs (Nature, Cell, PLOS, PMC). Voici ce qui existe:

### 4.1 Eigenvalues × Bio cellulaire — RARE mais ça émerge

| Paper | Année | Méthode | Concept bio | Signal |
|-------|-------|---------|-------------|--------|
| Aldana et al., arXiv:2301.10370 | 2023 | Eigenvecteurs de GRN → prédiction attracteurs | Gene expression | Niche |
| Phys Rev X, 2018 | 2018 | Design de spectres Laplaciens pour cascades | Signalisation | Bien cité |
| Hwang et al., PLOS ONE | 2010 | Spectral clustering sur réseaux PPI | Protéines | ~200 cit. |
| Sci Rep, 2022 | 2022 | **Laplacien de Hodge** sur complexes protéiques | Protéines | Émergent |
| Springer, ~2016 | 2016 | Entropie de von Neumann du Laplacien immunitaire | **Immune system** | **OBSCUR** |

**Le paper Springer 2016 est la pépite**: entropie spectrale du Laplacien sur le réseau idiotypique de Jerne (anticorps × anticorps). C'est EXACTEMENT ce que Muninn fait avec F6 — et quasi personne ne le cite.

### 4.2 Markov chain × Bio cellulaire — PLUS AVANCÉ

| Paper | Année | Méthode | Concept bio | Signal |
|-------|-------|---------|-------------|--------|
| Luke et al., arXiv:2507.10793 | **2025** | Chaîne de Markov temps-inhomogène pour cinétique anticorps | **Antibody** | Très récent |
| Nature Comms Bio, 2022 | 2022 | HMM sur arbres de lignage cellulaire | Cell differentiation | Bien cité |
| **Cell Systems, 2017** | 2017 | **Cellules souches = NON-Markov** | Cell fate | ~200 cit. |
| Bowman (Stanford), 2012 | 2012 | MSM pour repliement protéique | Enzyme/Protéine | **>1000 cit.** |
| BMC Sys Bio, 2017 | 2017 | MSM pour réseaux de gènes | Gene expression | Modéré |
| PMC, 2011 | 2011 | MCMC pour canaux ioniques | Receptor | Bien cité |

**Le paper Cell Systems 2017 est CRUCIAL pour Muninn**: il montre que la différenciation cellulaire **VIOLE l'hypothèse de Markov** — l'état futur dépend de l'HISTORIQUE, pas juste de l'état courant. La cellule a une **mémoire**. C'est exactement le problème que Muninn résout avec F1 (Ebbinghaus) + F8 (decay avec mémoire).

**Bowman (Stanford) = le méga-pont**: les Markov State Models pour le repliement protéique utilisent le **spectral gap de la matrice de transition** pour mesurer le temps de repliement. C'est F6 (eigenvalues) + F4 (Markov) fusionnés. >1000 citations, c'est un champ entier.

### 4.3 Exponential decay × Bio cellulaire — TEXTBOOK mais jamais connecté à CS

| Paper | Année | Méthode | Concept bio | Signal |
|-------|-------|---------|-------------|--------|
| PLOS Biology, 2018 | 2018 | Decay mixte d'anticorps (t½ de jours à décennies) | **Antibody** | ~400 cit. |
| Nature Comms, 2017 | 2017 | Decay biphasique: A₁e^(-k₁t) + A₂e^(-k₂t) | **Immune memory** | Bien cité |
| PMC, ~2005 | 2005 | Michaelis-Menten + decay protéasome | **Enzyme** | Bien cité |
| PLOS ONE, 2012 | 2012 | Le taux de decay = l'horloge des oscillations cellulaires | Cell cycle | Modéré |
| Hull 1979, Br J Anaesth | 1979 | C(t) = Σ Aᵢe^(-λᵢt) multi-compartiment | Drug metabolism | Textbook |
| **PNAS, 2024** | 2024 | **Noyau Mittag-Leffler unifie exp + power-law** | Tous | Récent, PNAS |

**Le paper PNAS 2024 est le méta-résultat**: il montre que le decay exponentiel (Ebbinghaus = Muninn F1) et le decay en loi de puissance sont les **deux extrêmes du même continuum**, unifiés par un noyau Gamma-Mittag-Leffler. Muninn utilise F1 = un cas particulier. La bio cellulaire utilise souvent des lois de puissance (dégradation protéique lente). Le noyau unifié les connecte.

**Le PLOS Biology 2018** est le pendant bio de la courbe d'Ebbinghaus: les anticorps ont des **half-lives qui varient de jours à décennies** selon le pathogène et l'individu. C'est pas UNE courbe d'oubli — c'est une DISTRIBUTION de courbes d'oubli. Muninn utilise un h fixe dans 2^(-Δ/h); la bio dit que h varie sur 4 ordres de grandeur.

---

## 5. LES 6 BLIND SPOTS ACTIONABLES POUR MUNINN

Ce qui N'EXISTE PAS encore et que Muninn pourrait exploiter:

### BS-1: Spectral gap du répertoire immunitaire
**Trou**: Personne ne mesure le mixing time de la matrice de transition immunitaire.
**Ce que Muninn sait faire**: F6 calcule les eigenvalues du Laplacien pour détecter les clusters. Appliqué au réseau anticorps-anticorps, ça prédirait à quelle vitesse le système immunitaire "oublie" ou atteint l'équilibre.
**Actionable**: Oui — le réseau idiotypique de Jerne a une structure de graphe, le Laplacien est calculable.

### BS-2: Ebbinghaus pour les boosters vaccinaux
**Trou**: Les calendriers vaccinaux sont empiriques. Personne ne les modélise comme du spaced repetition avec courbes d'oubli.
**Ce que Muninn sait faire**: F1 optimise les intervalles de rappel pour maximiser la rétention. C'est EXACTEMENT le problème des boosters: quand faut-il re-vacciner pour maintenir les anticorps au-dessus du seuil?
**Actionable**: Oui — les données de decay d'anticorps existent (PLOS Bio 2018), la formule F1 s'applique directement.

### BS-3: Non-Markov et mémoire cellulaire
**Trou**: Cell Systems 2017 montre que les cellules souches violent Markov (ont de la mémoire), mais personne n'a étendu ça aux lymphocytes T exhaustion/mémoire.
**Ce que Muninn sait faire**: F1 (decay avec mémoire) + F8 (co-occurrence decay) gèrent exactement le cas non-Markov — la force d'un souvenir dépend de l'historique complet, pas juste de l'état courant.
**Actionable**: Oui — le T cell exhaustion est un processus dépendant de l'historique, et Muninn a les outils pour le modéliser.

### BS-4: Laplacien de Hodge sur cascades de signalisation
**Trou**: Tout le spectral actuel en bio est sur des graphes (pairwise). Les cascades MAPK/ERK/Wnt sont intrinsèquement multi-corps.
**Ce que Muninn sait faire**: F6 utilise le Laplacien classique (graphe). Le Laplacien de Hodge (Sci Rep 2022) généralise aux complexes simpliciaux — interactions à 3, 4, n corps.
**Actionable**: Partiellement — Muninn devrait upgrader F6 du Laplacien de graphe au Laplacien de Hodge. Les données existent (réseaux de signalisation KEGG).

### BS-5: NCD (compression) sur séquences génétiques
**Trou**: La compression d'information (F2) n'est quasi jamais appliquée aux séquences protéiques ou ADN pour mesurer leur similarité fonctionnelle.
**Ce que Muninn sait faire**: F2 (NCD) mesure la distance entre deux objets par leur compressibilité conjointe. Appliquer NCD à des séquences d'acides aminés donnerait une mesure de similarité fonctionnelle sans alignement.
**Actionable**: Oui — c'est un one-liner: `NCD(seq_A, seq_B) = (C(AB) - min(C(A),C(B))) / max(C(A),C(B))`.

### BS-6: Distribution de half-lives (h variable dans Ebbinghaus)
**Trou**: Muninn utilise un h fixe par branche. La bio montre que h varie sur 4 ordres de grandeur (jours → décennies) pour les anticorps, et varie par individu (effets aléatoires mixtes).
**Ce que Muninn sait faire**: F1 pourrait être upgradé avec un h adaptatif par branche, calibré sur la volatilité observée — exactement comme les anticorps ont des half-lives différentes selon le pathogène.
**Actionable**: Oui — c'est un upgrade de F1: `h_branch = f(volatility, importance, access_frequency)`.

---

## 6. RECOMMANDATIONS PAR PRIORITÉ

### Priorité 1 — Intégration immédiate (pas de nouveau code majeur)
- **BS-6**: h adaptatif dans F1. Le PLOS Bio 2018 donne le modèle: mixed-effects avec half-life par pathogène. Muninn fait pareil par branche. Upgrade F1 avec `h = h_base × importance^β`.
- **BS-2**: Spaced repetition pour rappels. Muninn fait déjà du spaced recall (F1). Formaliser le parallèle avec les boosters vaccinaux = argument de vente pour PMC.

### Priorité 2 — Extensions (code modéré)
- **BS-5**: NCD sur séquences. Un compresseur (gzip) sur des séquences concaténées = F2 appliqué à la bio. Prototype en 10 lignes.
- **BS-3**: Non-Markov memory. Muninn gère déjà la mémoire historique. Formaliser: le decay d'une branche dépend de TOUTE sa séquence d'accès, pas juste du dernier accès. Le paper Cell Systems 2017 donne le cadre théorique.

### Priorité 3 — Recherche (gros chantier)
- **BS-1**: Spectral gap immunitaire. Besoin de données de réseaux immunitaires (idiotypique ou PPI). Calcul F6 sur ces graphes.
- **BS-4**: Hodge Laplacien. Upgrade fondamental de F6. Besoin de complexes simpliciaux, pas juste de graphes. Chantier de fond.

---

## 7. QUESTIONS POUR MUNINN

1. **F1 h adaptatif**: Est-ce que Muninn a déjà un mécanisme pour varier h par branche? Ou c'est un h global? Le PLOS Bio 2018 dit que les anticorps ont des half-lives qui varient de 50 jours à +∞ — si Muninn a un h global, c'est le premier truc à changer.

   > **RÉPONSE MUNINN**: Déjà par branche. Ligne 450: `half_life = 7.0 * (2 ** min(reviews, 10))`. Le h dépend de `access_count` — plus une branche est lue, plus son h est long (7 jours × 2^reviews). C'est du spaced repetition style Leitner. **MAIS** c'est basé uniquement sur le nombre d'accès, pas sur la volatilité ni l'importance. L'upgrade BS-6 (`h = f(volatility, importance)`) est faisable en ~10 lignes.

2. **Non-Markov**: Est-ce que Muninn track l'historique complet des accès à une branche, ou juste le dernier timestamp? Si c'est juste le dernier, la cellule souche de Cell Systems 2017 dit que tu perds de l'information — l'historique complet change la prédiction.

   > **RÉPONSE MUNINN**: Juste le dernier. `last_access` = date string, `access_count` = compteur entier. On garde COMBIEN de fois, mais pas QUAND chaque accès a eu lieu. Cell Systems 2017 a raison — on perd de l'information. L'upgrade ACT-R ajouterait `access_history: [timestamps]` pour un vrai modèle non-Markov. ~30 lignes.

3. **NCD cross-branche**: Est-ce que Muninn utilise F2 (NCD) pour mesurer la similarité entre branches? Si oui, est-ce qu'on pourrait l'appliquer aux séquences de tokens bruts (comme les biochimistes l'appliqueraient aux séquences d'acides aminés)?

   > **RÉPONSE MUNINN**: Oui, déjà fait. `_ncd()` ligne 610 avec zlib. Utilisé pour: merge de branches similaires (NCD < 0.4), dedup au boot (P19), sleep consolidation (NCD < 0.6 = grouper). Pas encore utilisé sur des séquences de tokens bruts style bioinformatique, mais le mécanisme est là.

4. **Spreading activation (F4)**: Le MSM de Bowman (Stanford, 1000+ citations) montre que le spectral gap de la matrice de transition Markov = le temps de convergence du système. Est-ce que Muninn mesure son propre spectral gap? Ça donnerait une mesure de "temps de rappel" théorique.

   > **RÉPONSE MUNINN**: Partiellement. `detect_zones()` dans mycelium.py (ligne 667) calcule les eigenvalues du Laplacien normalisé pour le clustering spectral. **MAIS** on ne mesure pas le spectral gap (λ₂/λ₁) comme métrique de mixing time. On utilise les eigenvecteurs pour le clustering, pas les eigenvalues pour le diagnostic. L'upgrade serait trivial: `spectral_gap = eigenvalues[-2] / eigenvalues[-1]` — ça donnerait un "temps de rappel théorique" du réseau sémantique.

5. **PMC priority**: Sky dit que PMC (bio/med) est priorité business. Ces 22 blind spots sont des arguments concrets: "Muninn utilise les mêmes maths que votre système immunitaire, mais personne ne l'a formalisé." C'est un pitch.

   > **RÉPONSE MUNINN**: Exact. Le pitch est: "mêmes maths, pont invisible, Muninn est déjà là."

---

## 8. CONVERGENCES YGGDRASIL × MUNINN

Les réponses de Muninn révèlent que **2 blind spots convergent avec ses propres TIER existants**:

| Blind Spot Yggdrasil | TIER Muninn | Convergence |
|----------------------|-------------|-------------|
| BS-6 (h adaptatif) | TIER 1 #1 (GARCH alpha) | Même upgrade: decay adaptatif. Bio dit `h = mixed-effects par pathogène`, finance dit `α = GARCH`. |
| BS-3 (Non-Markov) | TIER 1 #2 (ACT-R history) | Même upgrade: `access_history: [timestamps]`. Cell Systems 2017 + ACT-R = double justification. |

**Deux domaines indépendants** (bio cellulaire + finance/psycho cognitive) convergent vers les mêmes upgrades de Muninn. C'est pas une coïncidence — c'est le signal que ces upgrades sont les bons.

---

## 9. SYNTHÈSE DES VERDICTS

| Blind Spot | Difficulté | Impact Muninn | Littérature existante | Priorité |
|------------|-----------|---------------|----------------------|----------|
| BS-6 h adaptatif | Faible | Fort (F1 upgrade) | PLOS Bio 2018 | **P1** |
| BS-2 Spaced repetition vaccins | Faible | Moyen (argument PMC) | Empirique seulement | **P1** |
| BS-5 NCD séquences | Faible | Moyen (F2 nouveau domaine) | Quasi-vierge | **P2** |
| BS-3 Non-Markov memory | Moyen | Fort (F1+F8 upgrade) | Cell Systems 2017 | **P2** |
| BS-1 Spectral gap immunitaire | Élevé | Fort (F6 nouveau domaine) | Springer 2016 (obscur) | **P3** |
| BS-4 Hodge Laplacien | Élevé | Très fort (F6 upgrade) | Sci Rep 2022 | **P3** |

### Le méta-résultat

Les 22 paires Type C en bio cellulaire ne sont pas 22 trous isolés — c'est UN trou systémique: **la biologie cellulaire et l'informatique utilisent les mêmes mathématiques (decay exponentiel, spectral clustering, chaînes de Markov) sans se parler.** Muninn est assis exactement sur ce pont.

Le paper PNAS 2024 (noyau Mittag-Leffler) dit que tous les modèles de decay — Ebbinghaus, pharmacocinétique, dégradation protéique, décroissance radioactive — sont des cas particuliers du MÊME framework. Muninn F1 est un cas particulier. La bio cellulaire utilise d'autres cas particuliers. Le noyau unifié les connecte tous.

**En une phrase**: Muninn fait déjà de la biologie cellulaire computationnelle — il ne le sait juste pas encore.

---

*Sky × Claude — 10 Mars 2026, Versoix*
*22 papers pionniers sur 833K. 6 blind spots. 5 questions posées, 5 réponses reçues.*
*BS-6 × TIER1#1, BS-3 × TIER1#2 — deux domaines indépendants convergent vers les mêmes upgrades.*
*La cellule oublie comme Muninn oublie — même math, même courbe, même pont invisible.*
