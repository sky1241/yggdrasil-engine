#!/usr/bin/env python3
"""
YGGDRASIL -- CARMACK MOVES HUNTER : NAVIER-STOKES
==================================================
Trouve les "Carmack moves" : techniques d'autres domaines
que personne n'a pense a appliquer au probleme du millenaire.

John Carmack >> fast inverse sqrt (Newton-Raphson x gamedev)
Nous >> [???] x Navier-Stokes regularity / existence / blow-up

Sources:
1. Co-occurrences WT3 (69M paires)
2. Activity (poids des concepts)
3. WT2 papers (bridge papers = preuve que ca existe deja)

Carmack score = desert_ratio x log(works) x |avg_z|
Plus c'est gros et vide, plus c'est juteux.

Sky x Claude -- 29 Mars 2026
"""

import json
import gzip
import os
import sys
import io
import time
import sqlite3
from collections import defaultdict, Counter

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "..", "..")

# ==================================================
# NS TARGETS -- le probleme du millenaire
# ==================================================
NS_TARGETS = {
    # L'equation elle-meme
    "Navier-Stokes equations":            43017,
    "RANS":                               53587,
    # Le probleme ouvert : regularite / existence
    "Weak solution":                      55591,
    "Existence theorem":                  21302,
    "Sobolev space":                      64985,
    "Partial differential equation":      64038,
    "Parabolic PDE":                      13544,
    # Quantites cles
    "Turbulence":                         15100,
    "Vorticity":                          15635,
    "Enstrophy":                          12351,
    "Dissipation":                         5522,
    "Helicity":                           18154,
    "Reynolds number":                    12926,
    "Viscosity":                           4289,
    "Boundary layer":                      1884,
    "Incompressible flow":                56500,
    "Euler equations":                    54512,
    "Pressure gradient":                  64747,
    "Fluid dynamics":                     63508,
    "Fluid mechanics":                    55268,
}

# ==================================================
# CARMACK MOVE CANDIDATES
# ==================================================
CARMACK_CANDIDATES = {
    # ====== CONTINENT 1: ELECTROTECHNIQUE >> NS ======
    "Resistance distance": {
        "idx": 59049, "origin": "Theorie des circuits (753 papers)", "works": 753,
        "move": "La resistance distance dans un reseau electrique donne une BORNE "
                "sur les temps de diffusion. Le champ de vitesse NS vu comme un "
                "circuit : chaque streamline = fil, viscosite = resistance. "
                "La resistance effective borne le temps de dissipation.",
    },
    "Electrical network": {
        "idx": 15129, "origin": "Electrotechnique (85K papers)", "works": 84657,
        "move": "Kirchhoff (conservation courant = conservation masse). "
                "Rayleigh monotonicity : couper un fil augmente la resistance. "
                "Sur NS : retirer une direction d'ecoulement augmente la dissipation. "
                "Thomson energy = borne variationnelle sur l'energie du fluide.",
    },
    "Joule heating": {
        "idx": 2837, "origin": "Electrotechnique (24.5K papers)", "works": 24506,
        "move": "P = RI^2. La dissipation visqueuse de NS est EXACTEMENT un Joule heating "
                "generalise : mu|nabla u|^2 = 'chaleur' produite par le frottement. "
                "Borner la 'chaleur de Joule' du fluide = borner l'enstrophie. "
                "Si la chaleur totale est finie >> pas de blow-up.",
    },
    "Impedance matching": {
        "idx": 59034, "origin": "Electrotechnique (29K papers)", "works": 29438,
        "move": "L'impedance matching maximise le transfert d'energie entre systemes. "
                "Pour NS : l'impedance du fluide = ratio pression/debit. "
                "Le blow-up = une DESADAPTATION D'IMPEDANCE infinie entre "
                "les echelles. Borner le mismatch = regularite.",
    },
    "Ohm's law": {
        "idx": 10380, "origin": "Physique (892 papers)", "works": 892,
        "move": "V = IR. Pour NS : pression = viscosite x debit (loi de Poiseuille = "
                "Ohm pour les fluides). Mais en turbulent, la 'loi d'Ohm' devient "
                "non-lineaire. La transition laminaire>>turbulent = la transition "
                "ohmique>>non-ohmique. Les electriciens ont des outils pour ca.",
    },
    "RLC circuit": {
        "idx": 63454, "origin": "Electrotechnique (11.7K papers)", "works": 11744,
        "move": "Un RLC est un oscillateur amorti : L(d2q/dt2) + R(dq/dt) + q/C = V(t). "
                "NS linearise autour d'un ecoulement de base a EXACTEMENT cette forme. "
                "La viscosite = R (resistance), l'inertie = L (inductance), "
                "la compressibilite = 1/C (capacitance). Les criteres de stabilite "
                "des circuits (Routh-Hurwitz) s'appliquent directement.",
    },
    "Kirchhoff integral theorem": {
        "idx": 63544, "origin": "Physique (339 papers)", "works": 339,
        "move": "Kirchhoff integral = representation du champ a l'interieur "
                "d'un volume par ses valeurs au bord. Pour NS : connaitre la pression "
                "et vitesse AU BORD suffit a reconstruire la solution a l'interieur. "
                "Si la representation integrale reste bornee >> regularite.",
    },

    # ====== CONTINENT 2: PHYSIQUE STAT >> NS ======
    "Renormalization group": {
        "idx": 60204, "origin": "Physique QFT (62K papers)", "works": 61870,
        "move": "La renormalisation elimine les degres de liberte a chaque echelle. "
                "Pour la turbulence : chaque echelle de Kolmogorov est un 'shell'. "
                "Renormaliser = integrer les petites echelles pour obtenir une "
                "viscosite effective. Si la viscosite renormalisee reste finie >> pas de blow-up.",
    },
    "Ising model": {
        "idx": 56807, "origin": "Physique stat (48K papers)", "works": 48310,
        "move": "Ising = spins +/- sur un reseau. La vorticite de NS discretisee "
                "sur un lattice EST un modele d'Ising generalise. "
                "La transition de phase du modele d'Ising = la transition laminaire-turbulent. "
                "Les solutions exactes de Onsager 2D >> analogie avec NS 2D (ou ca marche).",
    },
    "Spin glass": {
        "idx": 7925, "origin": "Physique stat (20K papers)", "works": 20250,
        "move": "Le spin glass a un paysage d'energie frustre avec des minima locaux. "
                "Le champ de vitesse NS turbulent a la MEME structure : "
                "des configurations metastables (tourbillons coherents) separes "
                "par des barrieres d'energie. Les bornes de Parisi sur le temps "
                "de relaxation >> bornes sur le temps de dissipation NS.",
    },
    "Partition function (QFT)": {
        "idx": 29774, "origin": "Physique quantique (23K papers)", "works": 22648,
        "move": "Z = somme sur tous les etats. Pour NS : Z = integrale fonctionnelle "
                "sur tous les champs de vitesse, ponderee par e^(-S[u]/nu) "
                "ou S = action de NS. Le free energy F = -nu ln Z donne une "
                "BORNE THERMODYNAMIQUE sur l'energie totale du fluide.",
    },
    "Critical exponent": {
        "idx": 10021, "origin": "Physique stat (41K papers)", "works": 41301,
        "move": "Pres d'une transition de phase, les observables suivent des lois "
                "de puissance avec des exposants UNIVERSELS. La cascade de Kolmogorov "
                "E(k) ~ k^(-5/3) EST un exposant critique. L'universalite implique "
                "que les details microscopiques n'importent PAS >> simplification massive.",
    },
    "Percolation threshold": {
        "idx": 17933, "origin": "Physique stat (24K papers)", "works": 24489,
        "move": "Au seuil de percolation, un cluster geant apparait. "
                "Pour la turbulence : a quel Reynolds le reseau de tourbillons "
                "forme-t-il un cluster PERCOLANT ? Si oui, l'energie se propage "
                "a toutes les echelles >> blow-up potentiel. Le seuil = Re critique.",
    },
    "Phase transition": {
        "idx": 7678, "origin": "Physique (362K papers)", "works": 362325,
        "move": "La transition laminaire>>turbulent EST une transition de phase. "
                "Mais personne ne l'attaque avec les outils modernes des transitions : "
                "Landau-Ginzburg, parametre d'ordre, brisure de symetrie. "
                "Le parametre d'ordre de la turbulence = quoi ? Personne ne sait.",
    },
    "Boltzmann equation": {
        "idx": 10298, "origin": "Physique stat (27.5K papers)", "works": 27557,
        "move": "L'equation de Boltzmann est PLUS FONDAMENTALE que NS. "
                "NS est une LIMITE hydrodynamique de Boltzmann. "
                "Si on prouve la regularite au niveau Boltzmann, "
                "elle descend automatiquement vers NS. Attaquer PAR AU-DESSUS.",
    },

    # ====== CONTINENT 3: STOCHASTIQUE/FINANCE >> NS ======
    "Martingale": {
        "idx": 56120, "origin": "Probabilites (12.9K papers)", "works": 12901,
        "move": "Une martingale = processus sans drift (fair game). "
                "L'enstrophie de NS 3D : si c'est une sous-martingale (croissance en moyenne), "
                "blow-up possible. Si c'est une supermartingale >> l'enstrophie decroit "
                ">> pas de blow-up. Reinterpretation PROBABILISTE du probleme.",
    },
    "Stochastic calculus": {
        "idx": 59357, "origin": "Mathematiques (4.2K papers)", "works": 4163,
        "move": "Ito vs Stratonovich : le bruit dans NS n'est pas un detail, "
                "c'est le MOTEUR de la turbulence. Le calcul stochastique donne "
                "des estimations d'energie que le calcul deterministe ne peut pas. "
                "Formule d'Ito appliquee a ||u||^2 = estimation d'enstrophie.",
    },
    "Langevin equation": {
        "idx": 25979, "origin": "Physique (11.2K papers)", "works": 11178,
        "move": "L'equation de Langevin = force deterministe + bruit blanc. "
                "NS + bruit = NS stochastique. Paradoxe : les solutions de NS "
                "stochastique sont PLUS REGULIERES que NS deterministe. "
                "Le bruit regularise ! Approche par regularisation stochastique.",
    },
    "Wiener process": {
        "idx": 58888, "origin": "Probabilites (10.3K papers)", "works": 10350,
        "move": "Le processus de Wiener = mouvement Brownien. Les trajectoires "
                "sont continues mais nulle part derivables. "
                "Les solutions de NS 3D sont-elles dans l'espace de Wiener ? "
                "Si oui, les theoremes de regularite de Wiener s'appliquent.",
    },
    "Fokker-Planck equation": {
        "idx": 57869, "origin": "Physique stat (13K papers)", "works": 13000,
        "move": "Fokker-Planck decrit l'evolution de la densite de probabilite. "
                "Pour NS : la PDF de la vitesse en un point satisfait une "
                "equation de type Fokker-Planck. Borner la PDF = borner la vitesse "
                "= regularite. Les quants font ca tous les jours.",
    },

    # ====== CONTINENT 4: BIO/HEMODYNAMIQUE >> NS ======
    "Hemodynamics": {
        "idx": 12336, "origin": "Medecine (831K papers)", "works": 830645,
        "move": "830K papers qui UTILISENT NS pour le sang. Donnees empiriques "
                "massives sur des ecoulements NS REELS dans des geometries complexes "
                "(bifurcations arterielles, aneurysmes). Les medecins ont des "
                "cas ou NS EXPLOSE (stenose critique) et des cas ou ca reste lisse. "
                "Empirique >> guidage pour la theorie.",
    },
    "Aneurysm": {
        "idx": 19232, "origin": "Medecine (193K papers)", "works": 192729,
        "move": "Un anevrisme = un blow-up REEL de NS : la pression monte, "
                "la paroi se deforme, l'ecoulement devient turbulent, ca pete. "
                "Les chirurgiens ont des CRITERES empiriques de rupture. "
                "Ces criteres = conditions suffisantes pour le blow-up physique.",
    },
    "Protein folding": {
        "idx": 16301, "origin": "Biochimie (136K papers)", "works": 136159,
        "move": "Le paysage de folding = espace de configs exponentiellement grand "
                "mais le folding se fait en temps polynomial (paradoxe de Levinthal). "
                "NS a le MEME paradoxe : espace de solutions infini, mais le fluide "
                "'choisit' une solution en temps fini. Funnel landscape >> NS funnel ?",
    },
    "Fitness landscape": {
        "idx": 63747, "origin": "Biologie evolutive (11K papers)", "works": 11054,
        "move": "Le paysage de fitness a des pics, vallees, cols. "
                "L'espace des solutions NS a la MEME topologie. "
                "La question 'le blow-up existe-t-il ?' = 'y a-t-il un pic infini "
                "dans le paysage ?' Les outils de fitness landscapes (NK model, "
                "epistasie) pourraient cartographier le paysage NS.",
    },

    # ====== CONTINENT 5: TOPOLOGIE/GEOMETRIE >> NS ======
    "Algebraic topology": {
        "idx": 60802, "origin": "Mathematiques (8.5K papers)", "works": 8500,
        "move": "Les invariants topologiques (nombres de Betti, homologie) "
                "caractrisent les 'trous' dans un espace. Le champ de vitesse NS "
                "a une topologie (lignes de courant, surfaces de vorticite). "
                "Si cette topologie change >> singularite. Critere topologique "
                "pour le blow-up : reconnexion de lignes de vorticite.",
    },
    "Lie group": {
        "idx": 13717, "origin": "Mathematiques (46.5K papers)", "works": 46561,
        "move": "NS a des symetries (Galileen, scaling, rotation). Chaque symetrie "
                "= un generateur de Lie. Le groupe de symetrie COMPLET de NS "
                "n'est pas totalement classifie. Les symetries cachees de NS "
                "pourraient reveler des lois de conservation cachees >> bornes.",
    },
    "Symplectic geometry": {
        "idx": 10725, "origin": "Mathematiques (27K papers)", "works": 27266,
        "move": "NS est un systeme hamiltonien dissipation. En 2D, la structure "
                "symplectique de l'espace des phases est preservee. En 3D, "
                "la dissipation brise la symplectite. La MESURE de cette brisure "
                "= la 'distance a la regularite'. Borner la brisure symplectique "
                ">> borner le blow-up.",
    },
    "Morse theory": {
        "idx": 7450, "origin": "Mathematiques (11K papers)", "works": 11000,
        "move": "Morse classifie les points critiques d'une fonction par leur index. "
                "L'energie NS : E(u) = ||u||^2. Les points critiques de E "
                "= les solutions stationnaires. L'index de Morse = nombre de "
                "directions instables. Si l'index est borne >> regularite.",
    },

    # ====== CONTINENT 6: THEORIE DE L'INFORMATION >> NS ======
    "Kolmogorov complexity": {
        "idx": 34208, "origin": "Theorie de l'information (2K papers)", "works": 1974,
        "move": "K(x) = longueur du plus court programme qui produit x. "
                "Si K(champ_turbulent) est petit >> le champ est compressible "
                ">> il a une structure >> pas de blow-up aleatoire. "
                "Si K >> log(N) pour certaines configs >> configurations pathologiques "
                "incompressibles >> candidats au blow-up.",
    },
    "Data compression": {
        "idx": 61733, "origin": "Traitement signal (138K papers)", "works": 138084,
        "move": "La compressibilite du champ de vitesse turbulent dans une base "
                "d'ondelettes est un FAIT empirique. Si la turbulence est compressible "
                ">> les solutions sont dans un sous-espace de dimension finie effective "
                ">> regularite par compacite. Compression = regularisation.",
    },
    "Mutual information": {
        "idx": 8133, "origin": "Theorie de l'information (34.5K papers)", "works": 34501,
        "move": "I(X;Y) = combien X dit sur Y. Pour NS : I(petite echelle; grande echelle) "
                "= combien la micro-turbulence est correlee a la macro-turbulence. "
                "Si I est borne >> les echelles sont decouplees >> pas de cascade "
                "ascendante >> pas de blow-up. Budget informationnel du blow-up.",
    },

    # ====== CONTINENT 7: CONTROLE >> NS ======
    "Lyapunov function": {
        "idx": 58937, "origin": "Controle (56K papers)", "works": 55996,
        "move": "Une fonction de Lyapunov V(u) telle que dV/dt <= 0 prouve la stabilite. "
                "Pour NS : trouver V tel que V(u(t)) decroit le long des solutions. "
                "V = energie marche en 2D. En 3D, il faut une V plus subtile. "
                "Les controleurs savent construire des V non-triviales.",
    },
    "Optimal control": {
        "idx": 63699, "origin": "Controle (201K papers)", "works": 201380,
        "move": "La regularite de NS = un probleme de controle optimal : "
                "quel 'controle' (conditions initiales) minimise la norme de la solution ? "
                "Si le cout optimal est fini >> regularite. "
                "Le Pontryagin maximum principle s'applique directement.",
    },
    "Controllability": {
        "idx": 56079, "origin": "Controle (36K papers)", "works": 35949,
        "move": "Un systeme est controlable si on peut l'amener de tout etat "
                "a tout autre etat. NS est-il controlable en 3D ? "
                "Si oui, on peut FORCER la solution vers la regularite. "
                "Coron et al. ont montre la controlabilite de NS 2D. 3D = ouvert.",
    },

    # ====== CONTINENT 8: CHAOS/DYNAMIQUE >> NS ======
    "Strange attractor": {
        "idx": 43640, "origin": "Systemes dynamiques (5K papers)", "works": 5000,
        "move": "Les solutions NS 3D vivent-elles sur un attracteur etrange "
                "de dimension finie ? Si dim(attracteur) < infini >> les solutions "
                "sont confinee a un sous-espace >> regularite par compacite. "
                "Temam et al. : bornes sur dim(attracteur) pour NS 2D.",
    },
    "Lyapunov exponent": {
        "idx": 14299, "origin": "Dynamique (27.7K papers)", "works": 27752,
        "move": "Les exposants de Lyapunov mesurent la sensibilite aux conditions initiales. "
                "Pour NS : le plus grand exposant Lambda_1 controle la separation "
                "des trajectoires. Si Lambda_1 < infini >> pas de blow-up en temps fini. "
                "Borner Lambda_1 = regularite.",
    },
    "Ergodic theory": {
        "idx": 3508, "origin": "Mathematiques (24K papers)", "works": 23752,
        "move": "Un systeme ergodique visite tous les etats en temps fini. "
                "Les solutions NS sont-elles ergodiques ? Si oui, la moyenne "
                "temporelle = moyenne sur l'espace des solutions. "
                "Birkhoff >> l'enstrophie moyennee est finie >> regularite en moyenne.",
    },
    "Bifurcation": {
        "idx": 43340, "origin": "Dynamique (87K papers)", "works": 87399,
        "move": "Le blow-up NS = une bifurcation INFINIE. Mais les bifurcations "
                "finies sont classifiees (Hopf, saddle-node, period-doubling). "
                "Quelle SEQUENCE de bifurcations mene au blow-up ? "
                "Feigenbaum : les cascades de period-doubling sont universelles. "
                "La route vers le blow-up est-elle une cascade de Feigenbaum ?",
    },

    # ====== CONTINENT 9: QUANTUM/GAUGE >> NS ======
    "Gauge theory": {
        "idx": 12781, "origin": "Physique (128K papers)", "works": 127752,
        "move": "NS a une invariance de jauge : ajouter un gradient a la pression "
                "ne change rien. C'est une SYMETRIE DE JAUGE au sens de la physique. "
                "Les outils de la theorie de jauge (connexion, courbure, Chern-Simons) "
                "pourraient classifier les topologies de solutions NS.",
    },
    "Yang-Mills existence and mass gap": {
        "idx": 17884, "origin": "Physique/Math (436 papers)", "works": 436,
        "move": "Yang-Mills = autre probleme du millenaire Clay. NS et Yang-Mills "
                "partagent la MEME structure : champs de vecteurs avec self-interaction. "
                "Les techniques de Yang-Mills (lattice QCD, confinement) "
                "pourraient s'appliquer a NS. PERSONNE ne fait ce pont.",
    },
    "Conformal field theory": {
        "idx": 57822, "origin": "Physique (31K papers)", "works": 31181,
        "move": "En 2D, la CFT classifie TOUTES les theories conformes. "
                "La turbulence 2D est invariante conforme (Polyakov 1993). "
                "En 3D, la turbulence a une invariance conforme APPROCHEE. "
                "Les outils de la CFT (operateurs primaires, OPE) pourraient "
                "classifier les singularites NS en 3D.",
    },
    "Path integral formulation": {
        "idx": 8426, "origin": "Physique quantique (22.7K papers)", "works": 22738,
        "move": "L'integrale de chemin de Feynman = somme sur toutes les histoires. "
                "Pour NS : integrer sur tous les champs de vitesse possibles "
                "avec poids e^(-Action/nu). Le blow-up = une histoire de mesure nulle ? "
                "Ou de mesure non-nulle ? La reponse donne la regularite.",
    },

    # ====== CONTINENT 10: ML/PREUVE >> NS ======
    "Deep learning": {
        "idx": 1389, "origin": "IA (709K papers)", "works": 708578,
        "move": "Les PINN (Physics-Informed Neural Networks) resolvent NS numeriquement. "
                "Mais les reseaux de neurones sont des APPROXIMATEURS UNIVERSELS. "
                "Si un NN de taille finie approxime TOUTE solution NS >> "
                "les solutions vivent dans un espace de dimension finie effective "
                ">> compacite >> regularite. Preuve par approximation.",
    },
    "Automated theorem proving": {
        "idx": 16698, "origin": "Informatique (16.5K papers)", "works": 16517,
        "move": "Les assistants de preuve (Lean, Coq) ont verifie des resultats "
                "en analyse fonctionnelle. Formaliser les estimations d'energie NS "
                "en Lean >> identifier EXACTEMENT ou l'argument 2D echoue en 3D. "
                "Le gap precis = la cible du Carmack move.",
    },
    "Formal verification": {
        "idx": 1871, "origin": "Informatique (40.5K papers)", "works": 40511,
        "move": "La verification formelle prouve qu'un programme satisfait sa spec. "
                "NS = un 'programme' (EDP) et regularite = la 'spec'. "
                "Les model checkers explorent l'espace d'etats exhaustivement. "
                "Appliquer aux solutions discretisees >> prouver la regularite "
                "sur grille >> passage a la limite.",
    },
}

ALL_TECHNIQUE_IDXS = {v["idx"] for v in CARMACK_CANDIDATES.values()}
ALL_TARGET_IDXS = set(NS_TARGETS.values())


def search_wt2_papers(technique_idxs, target_idxs):
    """Search WT2 chunks for papers that bridge technique x target."""
    wt2_dir = os.path.join(REPO, "data", "pipeline", "wt2_chunks")
    if not os.path.isdir(wt2_dir):
        print(f"  WT2 dir not found: {wt2_dir}")
        return []

    bridges = []
    chunk_files = sorted([f for f in os.listdir(wt2_dir)
                         if f.startswith("papers") and f.endswith(".json.gz")])
    total = len(chunk_files)

    for ci, cf in enumerate(chunk_files):
        if ci % 50 == 0:
            print(f"    WT2 chunk {ci}/{total}...", end="\r")
        path = os.path.join(wt2_dir, cf)
        try:
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                papers = json.load(f)
        except Exception:
            continue

        for arxiv_id, pdata in papers.items():
            concepts = set(pdata.get("c", []))
            tech_hits = concepts & technique_idxs
            target_hits = concepts & target_idxs
            if tech_hits and target_hits:
                bridges.append({
                    "paper_id": arxiv_id,
                    "domain": pdata.get("d", "?"),
                    "tech_concepts": sorted(tech_hits),
                    "target_concepts": sorted(target_hits),
                    "n_total": len(concepts),
                })

    print(f"    WT2 done: {len(bridges)} bridge papers found")
    return bridges


def main():
    import numpy as np
    t0 = time.time()
    print("=" * 120)
    print("CARMACK MOVES HUNTER -- NAVIER-STOKES EDITION")
    print(f"Fast inverse sqrt pour le probleme du millenaire")
    print(f"{len(CARMACK_CANDIDATES)} techniques candidates x {len(NS_TARGETS)} cibles NS")
    print("=" * 120)

    # === 1. Load concept names ===
    print("\n[1] Loading concepts...")
    with open(os.path.join(REPO, "data", "scan", "concepts_65k.json"),
              'r', encoding='utf-8') as f:
        cdata = json.load(f)
    idx_to_name = {info["idx"]: info["name"] for info in cdata["concepts"].values()}

    # === 2. Load co-occurrences from WT3 ===
    print("[2] Loading co-occurrences from WT3...")
    db = sqlite3.connect(os.path.join(REPO, "data", "wt3.db"))
    cursor = db.cursor()

    all_idxs = sorted(ALL_TECHNIQUE_IDXS | ALL_TARGET_IDXS)
    placeholders = ",".join(str(i) for i in all_idxs)
    cursor.execute(f"""
        SELECT concept_a, concept_b, weight
        FROM cooc_global
        WHERE concept_a IN ({placeholders}) AND concept_b IN ({placeholders})
    """)

    cooc = {}
    for a, b, w in cursor.fetchall():
        cooc[(min(a, b), max(a, b))] = float(w)
    db.close()
    print(f"  {len(cooc)} pairs loaded")

    # === 3. Load activity ===
    print("[3] Loading activity...")
    with open(os.path.join(REPO, "experiments", "predictions_2025",
              "activity_full.json"), 'r', encoding='utf-8') as f:
        activity = np.array(json.load(f)["activity"], dtype=np.float64)
    total_works = float(activity.sum())

    # === 4. Score each Carmack move ===
    print("\n[4] Scoring Carmack moves...")

    moves = []
    for tech_name, tech_info in CARMACK_CANDIDATES.items():
        tech_idx = tech_info["idx"]
        wa = float(activity[tech_idx])

        total_cooc = 0.0
        n_deserts = 0
        n_pairs = 0
        z_sum = 0.0
        pair_details = []

        for tgt_name, tgt_idx in NS_TARGETS.items():
            pair = (min(tech_idx, tgt_idx), max(tech_idx, tgt_idx))
            observed = cooc.get(pair, 0.0)
            wb = float(activity[tgt_idx])
            if wb == 0:
                continue

            E = wa * wb / total_works
            pa, pb = wa / total_works, wb / total_works
            std = max(np.sqrt(max(E * (1 - pa) * (1 - pb), 0.0)), 1.0)
            z = (observed - E) / std

            n_pairs += 1
            total_cooc += observed
            z_sum += z
            if observed == 0:
                n_deserts += 1

            pair_details.append({
                "target": tgt_name,
                "cooc": observed,
                "expected": E,
                "z": z,
            })

        if n_pairs == 0:
            continue

        avg_z = z_sum / n_pairs
        desert_ratio = n_deserts / n_pairs

        # Carmack score = how UNKNOWN x how BIG the technique is
        carmack_score = desert_ratio * np.log1p(wa) * abs(avg_z)

        # Tier assignment
        if desert_ratio >= 0.8 and wa > 10000:
            tier = "S"
        elif desert_ratio >= 0.5 and wa > 5000:
            tier = "A"
        elif desert_ratio >= 0.3:
            tier = "B"
        else:
            tier = "C"

        moves.append({
            "technique": tech_name,
            "tech_idx": tech_idx,
            "origin": tech_info["origin"],
            "works": tech_info["works"],
            "move": tech_info["move"],
            "carmack_score": carmack_score,
            "tier": tier,
            "avg_z": avg_z,
            "total_cooc": total_cooc,
            "n_deserts": n_deserts,
            "n_pairs": n_pairs,
            "desert_ratio": desert_ratio,
            "pairs": sorted(pair_details, key=lambda x: x["z"]),
        })

    moves.sort(key=lambda x: -x["carmack_score"])

    # === 5. Search WT2 for bridge papers ===
    print("\n[5] Searching WT2 for bridge papers...")
    bridge_papers = search_wt2_papers(ALL_TECHNIQUE_IDXS, ALL_TARGET_IDXS)

    paper_by_tech = defaultdict(list)
    for p in bridge_papers:
        for tidx in p["tech_concepts"]:
            for tname, tinfo in CARMACK_CANDIDATES.items():
                if tinfo["idx"] == tidx:
                    paper_by_tech[tname].append(p)

    # === 6. Display ===
    print(f"\n{'='*120}")
    print("CARMACK MOVES -- CLASSEMENT PAR TIER")
    print(f"{'='*120}")

    for tier_label in ["S", "A", "B", "C"]:
        tier_moves = [m for m in moves if m["tier"] == tier_label]
        if not tier_moves:
            continue

        tier_desc = {"S": "ARME NUCLEAIRE", "A": "FORT", "B": "MOYEN", "C": "EXPERIMENTAL"}
        print(f"\n{'='*120}")
        print(f"TIER {tier_label} -- {tier_desc[tier_label]}")
        print(f"{'='*120}")

        for m in tier_moves:
            papers = paper_by_tech.get(m["technique"], [])

            print(f"\n  {'-'*110}")
            print(f"  {m['technique']} x NAVIER-STOKES "
                  f"[score={m['carmack_score']:.2f}, tier={m['tier']}]")
            print(f"  Origine: {m['origin']} ({m['works']:,} papers)")
            print(f"  Deserts: {m['n_deserts']}/{m['n_pairs']} ({m['desert_ratio']:.0%})"
                  f" | z moyen: {m['avg_z']:.2f}"
                  f" | cooc total: {m['total_cooc']:.1f}")
            print(f"  Le move: {m['move']}")

            if papers:
                print(f"  Bridge papers ({len(papers)}):")
                for p in papers[:5]:
                    tech_names = [idx_to_name.get(i, f"?{i}") for i in p["tech_concepts"]]
                    tgt_names = [idx_to_name.get(i, f"?{i}") for i in p["target_concepts"]]
                    print(f"    [{p['paper_id']}] {p['domain']}"
                          f" | tech: {', '.join(tech_names[:3])}"
                          f" | target: {', '.join(tgt_names[:3])}")
            else:
                print(f"  Bridge papers: AUCUN -- DESERT CONFIRME")

            # Show worst pairs (biggest holes)
            for pd in m["pairs"][:5]:
                status = "DESERT" if pd["cooc"] == 0 else f"cooc={pd['cooc']:.1f}"
                print(f"    x {pd['target']:35s} | {status:15s}"
                      f" | E={pd['expected']:.2f} | z={pd['z']:.2f}")

    # === 7. Continent ranking ===
    print(f"\n{'='*120}")
    print("CLASSEMENT PAR CONTINENT D'ORIGINE")
    print(f"{'='*120}")

    # Group by origin continent
    continent_map = {}
    for m in moves:
        origin = m["origin"].split("(")[0].strip()
        if origin not in continent_map:
            continent_map[origin] = {"moves": [], "total_score": 0, "s_count": 0, "a_count": 0}
        continent_map[origin]["moves"].append(m)
        continent_map[origin]["total_score"] += m["carmack_score"]
        if m["tier"] == "S": continent_map[origin]["s_count"] += 1
        if m["tier"] == "A": continent_map[origin]["a_count"] += 1

    for origin, data in sorted(continent_map.items(), key=lambda x: -x[1]["total_score"]):
        print(f"\n  {origin}")
        print(f"    {len(data['moves'])} moves | score total={data['total_score']:.2f}"
              f" | {data['s_count']} tier-S | {data['a_count']} tier-A")
        for m in sorted(data["moves"], key=lambda x: -x["carmack_score"])[:3]:
            print(f"      [{m['tier']}] {m['technique']:35s} | score={m['carmack_score']:.2f}"
                  f" | desert={m['desert_ratio']:.0%}")

    # === 8. Bridge papers summary ===
    print(f"\n{'='*120}")
    print(f"BRIDGE PAPERS ({len(bridge_papers)} trouves)")
    print(f"{'='*120}")

    domain_counts = Counter(p["domain"] for p in bridge_papers)
    print(f"  Par domaine:")
    for d, c in domain_counts.most_common(15):
        print(f"    {d:30s} | {c:4d} papers")

    bridge_papers.sort(key=lambda x: len(x["tech_concepts"]) + len(x["target_concepts"]),
                       reverse=True)
    print(f"\n  Top 20 papers les plus connectes:")
    for i, p in enumerate(bridge_papers[:20]):
        tech_names = [idx_to_name.get(i2, f"?{i2}") for i2 in p["tech_concepts"][:3]]
        tgt_names = [idx_to_name.get(i2, f"?{i2}") for i2 in p["target_concepts"][:3]]
        print(f"    {i+1:2d}. [{p['paper_id']}] {p['domain']:15s}"
              f" | tech: {', '.join(tech_names)}"
              f" | target: {', '.join(tgt_names)}")

    # === 9. Summary ===
    print(f"\n{'='*120}")
    print("SUMMARY")
    print(f"{'='*120}")
    s_moves = [m for m in moves if m["tier"] == "S"]
    a_moves = [m for m in moves if m["tier"] == "A"]
    print(f"  Total moves: {len(moves)}")
    print(f"  Tier S (arme nucleaire): {len(s_moves)}")
    print(f"  Tier A (fort): {len(a_moves)}")
    print(f"  Bridge papers: {len(bridge_papers)}")
    print(f"  Temps: {time.time()-t0:.0f}s")

    if s_moves:
        print(f"\n  TIER S -- LES CARMACK MOVES LES PLUS JUTEUX:")
        for m in s_moves:
            print(f"    >> {m['technique']} ({m['origin']}) | score={m['carmack_score']:.2f}")

    # === 10. Save ===
    os.makedirs(os.path.join(REPO, "data", "results"), exist_ok=True)
    outfile = os.path.join(REPO, "data", "results", "scan_carmack_ns.json")
    save = {
        "scan": "carmack_moves_navier_stokes",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_techniques": len(CARMACK_CANDIDATES),
        "n_targets": len(NS_TARGETS),
        "n_moves": len(moves),
        "moves": moves,
        "bridge_papers": bridge_papers[:200],
        "bridge_paper_count": len(bridge_papers),
        "continent_ranking": {k: {"total_score": v["total_score"],
                                   "n_moves": len(v["moves"]),
                                   "s_count": v["s_count"],
                                   "a_count": v["a_count"]}
                              for k, v in continent_map.items()},
    }
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(save, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")


if __name__ == "__main__":
    main()
