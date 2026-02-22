"""
YGGDRASIL — VÉRIFICATION LIANES × 32 TESTS
"Est-ce que CHAQUE découverte a utilisé un escalier de secours?"

Sky × Claude — 18 Février 2026, 23h45, Versoix.
"""

import json
from collections import defaultdict

# ══════════════════════════════════════════════════════════════
# LIANES DATABASE (from lianes.py analysis)
# symbol → number of continents it bridges
# ══════════════════════════════════════════════════════════════

LIANE_SCORES = {
    # 🌿🌿🌿 UNIVERSELLES (6-7 continents)
    "=": 7, "exp": 6, "ln": 6, "Σ": 6, "∫": 6,
    # 🌿🌿 MAJEURES (4-5 continents)
    "e": 5, "∂": 5,
    "Bayes": 4, "E[X]": 4, "FFT": 4, "N(μ,σ²)": 4, "O(n)": 4,
    "P(A)": 4, "Var": 4, "cos": 4, "d/dx": 4, "det": 4, "lim": 4,
    "log": 4, "sin": 4, "Π": 4, "δ": 4, "ε": 4, "λ": 4, "π": 4,
    "σ_std": 4, "χ²": 4, "ℱ": 4, "∇": 4, "∇²": 4,
    "∬": 4, "∮": 4, "∗_conv": 4,
    # 🌿 LIANES (3 continents)
    "Attn": 3, "BS": 3, "D_KL": 3, "F=ma": 3, "GAN": 3, "H(X)": 3,
    "Itô": 3, "Nash": 3, "PV=nRT": 3, "Re": 3, "R₀": 3, "SDE": 3,
    "SGD": 3, "S_ent": 3, "TM": 3, "W(t)": 3, "argmax": 3, "argmin": 3,
    "i": 3, "Γ": 3, "ζ": 3, "ℋ": 3, "ℒ": 3, "∇L": 3, "∇·": 3, "∇×": 3,
    # 🌱 PONTS (2 continents) — seulement ceux utilisés dans les tests
    "Gal": 2, "gμν": 2, "ψ": 2, "Ĥ": 2, "DNA": 1, "RNA": 1,
    "softmax": 2, "ReLU": 2, "BP": 2, "σ_sigm": 2,
}

# ══════════════════════════════════════════════════════════════
# 32 TESTS COMPLETS — Identification des symboles S0 utilisés
# comme lianes dans chaque découverte
# ══════════════════════════════════════════════════════════════

ALL_TESTS = {
    # === TESTS 1-20 (from RESULTATS_TESTS_REELS.md) ===
    
    1: {
        "name": "Fermat (Wiles 1995)",
        "domain": "Maths",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["Gal", "ζ", "∫", "Σ", "det", "λ", "∂", "lim", "log"],
        "liane_clé": "Gal (Galois) + courbes elliptiques → nb théorie",
        "note": "Taniyama-Shimura = pont modulaire. Lianes: intégrale, sommation, déterminant traversent Maths+Physique+Finance+Ingénierie.",
    },
    2: {
        "name": "Classification Groupes Finis (1983)",
        "domain": "Maths",
        "pattern": "P2 (Dense)",
        "status": "✅",
        "lianes_s0": ["det", "λ", "Σ", "∫"],
        "liane_clé": "Pas de liane inter-domaine — croissance INTERNE pure",
        "note": "100+ auteurs, 10000+ pages. Pattern Dense = pas besoin d'escalier de secours, l'ascenseur central suffit.",
    },
    3: {
        "name": "Higgs (2012)",
        "domain": "Physique",
        "pattern": "P3 (Théorie×Outil)",
        "status": "✅",
        "lianes_s0": ["ℒ", "∂", "∫", "exp", "Σ", "π", "ψ", "λ"],
        "liane_clé": "ℒ (Lagrangien) = Physique+Maths+Ingénierie",
        "note": "Théorie 1964, outil LHC 2012. Le Lagrangien traverse 3 continents. exp et ∫ sont universels.",
    },
    4: {
        "name": "CRISPR (Doudna & Charpentier 2012)",
        "domain": "Biologie",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["DNA", "RNA"],
        "liane_clé": "PAS de liane S0 mathématique — pont biologique pur",
        "note": "Système immunitaire bactérien → édition génomique. Les lianes ici sont des MOLÉCULES pas des symboles.",
    },
    5: {
        "name": "Dark Matter (non résolu)",
        "domain": "Physique",
        "pattern": "P4 (Trou ouvert)",
        "status": "✅",
        "lianes_s0": ["gμν", "ψ", "∫", "Σ", "ℒ", "∇²", "exp"],
        "liane_clé": "Trou ouvert — les lianes EXISTENT mais personne n'a trouvé la combinaison",
        "note": "DM↔QG = 1.5% stable 35 ans. Les outils S0 sont là, la combinaison manque.",
    },
    6: {
        "name": "Deep Learning (AlexNet 2012)",
        "domain": "IA",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["∇L", "exp", "σ_sigm", "∗_conv", "Σ", "argmin", "log", "SGD", "BP"],
        "liane_clé": "∇L + SGD + exp = gradient descent traverse IA+Maths+Finance",
        "note": "Convolution (∗_conv) = signal processing→vision. x675 post-pont.",
    },
    7: {
        "name": "Graphène (2004)",
        "domain": "Matériaux",
        "pattern": "P5 (Anti-signal)",
        "status": "⚠️",
        "lianes_s0": ["∂", "∫", "ψ", "exp"],
        "liane_clé": "Lianes universelles présentes MAIS pont semi-conducteur stagne",
        "note": "Seul test mitigé. Explosion x200 mais GR↔SC reste <2%. Les lianes S0 sont nécessaires mais pas suffisantes.",
    },
    8: {
        "name": "Poincaré (Perelman 2003)",
        "domain": "Maths",
        "pattern": "P1+P4 (Pont+Catalyseur)",
        "status": "✅",
        "lianes_s0": ["S_ent", "∂", "∫", "∇", "Γ", "exp", "lim", "gμν", "∇²"],
        "liane_clé": "S_ent (entropie Boltzmann) = Physique→Géométrie = PORTE DÉROBÉE",
        "note": "99 ans ouvert. Perelman importe la thermodynamique en topologie. Liane entropie = 3 continents.",
    },
    9: {
        "name": "Immunothérapie (Nobel 2018)",
        "domain": "Médecine",
        "pattern": "P1+P3",
        "status": "✅",
        "lianes_s0": ["R₀", "exp", "P(A)", "log", "Σ"],
        "liane_clé": "R₀ = Bio+Finance+Maths. exp = universel.",
        "note": "IC↔ONC↔TC 0 pendant 17 ans, puis explosion.",
    },
    10: {
        "name": "Ondes gravitationnelles (LIGO 2015)",
        "domain": "Physique",
        "pattern": "P3 (Théorie×Outil)",
        "status": "✅",
        "lianes_s0": ["gμν", "∂", "∫", "sin", "cos", "ℱ", "FFT", "∇²", "exp"],
        "liane_clé": "FFT = Ingénierie+IA+Physique+Finance. Fourier comme escalier de secours.",
        "note": "Einstein 1916 → LIGO 2015. FFT (4 continents) = outil de détection du signal.",
    },
    11: {
        "name": "Supraconducteurs HT (Bednorz 1986)",
        "domain": "Physique",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["ψ", "∂", "∫", "exp", "Σ", "∇²"],
        "liane_clé": "∂ et ∫ universels. ψ = Physique+Maths.",
        "note": "HTS↔CU 0 pendant 11 ans, x46 post-pont. Céramiques × supraconductivité.",
    },
    12: {
        "name": "Quantum×Crypto (en transition)",
        "domain": "CS/Crypto",
        "pattern": "P4 (Trou ouvert)",
        "status": "✅",
        "lianes_s0": ["ψ", "Ĥ", "exp", "log", "H(X)", "π"],
        "liane_clé": "H(X) (entropie Shannon) = IA+Physique+Finance",
        "note": "QC↔CR 2.4% lent. H(X) = pont informationnel entre quantique et crypto.",
    },
    13: {
        "name": "Microbiome×Psychiatrie (en formation)",
        "domain": "Médecine",
        "pattern": "P1 (en cours)",
        "status": "✅",
        "lianes_s0": ["R₀", "P(A)", "Bayes", "exp", "χ²"],
        "liane_clé": "Bayes (4 continents) + χ² (4 continents) = outils statistiques",
        "note": "12 ans de ZÉRO. Les lianes statistiques (Bayes, χ²) sont les escaliers pour ce pont.",
    },
    14: {
        "name": "Théorie des cordes (anti-signal)",
        "domain": "Physique",
        "pattern": "P5 (Anti-signal)",
        "status": "✅",
        "lianes_s0": ["ℒ", "∂", "∫", "exp", "Σ", "π", "ψ", "gμν"],
        "liane_clé": "TOUTES les lianes majeures sont là — mais SUSY↔LHC s'effondre",
        "note": "Lianes universelles ne suffisent pas si l'outil expérimental ne suit pas. Anti-signal.",
    },
    15: {
        "name": "AlphaFold (Nobel 2024)",
        "domain": "IA×Bio",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["Attn", "∇L", "exp", "argmin", "E[X]", "softmax", "Σ"],
        "liane_clé": "Attn (3 continents: IA+Bio+Finance) = le Transformer comme escalier",
        "note": "PF↔DL ZÉRO 15 ans. Attention mechanism = liane IA→Bio. Nobel 2024.",
    },
    16: {
        "name": "Blockchain (Bitcoin 2009)",
        "domain": "CS×Finance",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["H(X)", "log", "exp", "P(A)", "O(n)"],
        "liane_clé": "H(X) (entropie) = IA+Physique+Finance. Hash = pont crypto→finance.",
        "note": "BC↔CR trou puis x90. H(X) traverse 3 continents.",
    },
    17: {
        "name": "Exoplanètes (1995)",
        "domain": "Astronomie",
        "pattern": "P2 (Dense)",
        "status": "✅",
        "lianes_s0": ["sin", "cos", "ℱ", "∫", "Σ", "FFT", "exp"],
        "liane_clé": "Pas de liane inter-domaine nécessaire — croissance interne",
        "note": "EX↔AB 68% toujours dense. Pattern Dense = ascenseur central.",
    },
    18: {
        "name": "Isolants topologiques (2005)",
        "domain": "Physique",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["ψ", "Ĥ", "det", "∫", "exp", "π", "i"],
        "liane_clé": "det (4 continents) + i (3 continents) = algèbre→topologie→physique",
        "note": "Concept inexistant puis x85. Topologie mathématique → matériaux quantiques.",
    },
    19: {
        "name": "Fusion nucléaire (trou ouvert)",
        "domain": "Physique",
        "pattern": "P4 (Trou ouvert)",
        "status": "✅",
        "lianes_s0": ["∂", "∫", "∇²", "exp", "Σ", "PV=nRT", "Re"],
        "liane_clé": "PV=nRT (3 continents) + Re (3 continents) = thermodynamique×fluides",
        "note": "TOK↔HTS 0-3/an 40 ans. Les lianes thermo sont là mais la combinaison manque.",
    },
    20: {
        "name": "Économie comportementale (Kahneman)",
        "domain": "Sciences sociales",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["E[X]", "P(A)", "Bayes", "log", "Var", "N(μ,σ²)"],
        "liane_clé": "E[X] + P(A) + Bayes = Maths+Finance+IA+Bio (4 continents chacun)",
        "note": "BE↔CB 0 pendant 17 ans. Prospect theory = lianes probabilistes → psychologie.",
    },
    
    # === TESTS 21-32 (individual test files) ===
    
    21: {
        "name": "CAR-T Cell Therapy (2011)",
        "domain": "Médecine",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["R₀", "exp", "P(A)", "log", "Σ"],
        "liane_clé": "exp (6 continents) = croissance exponentielle modélisée partout",
        "note": "Gene therapy × oncologie. ZÉRO lien clinique 15+ ans. exp = liane universelle.",
    },
    22: {
        "name": "mRNA Vaccines (Karikó, Nobel 2023)",
        "domain": "Médecine",
        "pattern": "P4 (Trou+Catalyseur)",
        "status": "✅",
        "lianes_s0": ["RNA", "exp", "P(A)"],
        "liane_clé": "Trou PERCEPTUEL — pas technique. exp présent mais le blocage est social.",
        "note": "Plateau 15 ans. COVID = catalyseur externe. Karikó rejetée 30 ans. Type C.",
    },
    23: {
        "name": "Transformer (Vaswani 2017)",
        "domain": "IA",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["Attn", "exp", "softmax", "∇L", "Σ", "det", "∗_conv", "sin", "cos"],
        "liane_clé": "Attn (3) + exp (6) + sin/cos (4) = positional encoding emprunte à la trigonométrie",
        "note": "sin/cos dans positional encoding = LIANE trigonométrie→NLP. Qui aurait pensé?",
    },
    24: {
        "name": "Perovskite Solar (Miyasaka 2009)",
        "domain": "Chimie×Énergie",
        "pattern": "P3 (Théorie×Outil)",
        "status": "✅",
        "lianes_s0": ["exp", "∫", "∂", "ε", "λ"],
        "liane_clé": "exp + ∫ + ∂ = lianes universelles (5-6 continents)",
        "note": "Matériau connu depuis 1839. Dormance 3 ans post-bridge. λ (4 continents) = longueur d'onde.",
    },
    25: {
        "name": "Optogénétique (Deisseroth 2005)",
        "domain": "Bio×Physique",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["exp", "sin", "cos", "λ", "ψ"],
        "liane_clé": "λ (longueur d'onde, 4 continents) = optique→neuroscience",
        "note": "Opsines d'algues → contrôle neuronal. λ = liane physique×bio. sin/cos = modulation lumineuse.",
    },
    26: {
        "name": "Gene Drives (Esvelt 2014)",
        "domain": "Bio×Écologie",
        "pattern": "P1 (Pont+frein éthique)",
        "status": "✅",
        "lianes_s0": ["P(A)", "R₀", "exp", "log"],
        "liane_clé": "R₀ (3 continents) = reproduction number traverse Bio+Finance+Maths",
        "note": "CRISPR × pop genetics. Croissance freinée par éthique. R₀ modélise la propagation.",
    },
    27: {
        "name": "Quantum ML (en transition)",
        "domain": "IA×Physique",
        "pattern": "P2 (Dense)",
        "status": "✅",
        "lianes_s0": ["ψ", "Ĥ", "exp", "∇L", "argmin", "E[X]", "det", "λ"],
        "liane_clé": "Pas de pont unique — les 2 domaines partagent DÉJÀ les mêmes lianes",
        "note": "Croissance linéaire. Algèbre linéaire = socle commun. det, λ, exp = partagés.",
    },
    28: {
        "name": "Single-cell RNA-seq (10X Genomics 2015)",
        "domain": "Bio",
        "pattern": "P3 (Théorie×Outil)",
        "status": "✅",
        "lianes_s0": ["log", "exp", "Σ", "P(A)", "Bayes", "D_KL"],
        "liane_clé": "D_KL (3 continents: IA+Physique+Finance) = divergence pour clustering cellulaire",
        "note": "10X Genomics = outil. D_KL et Bayes = lianes statistiques pour l'analyse.",
    },
    29: {
        "name": "GANs (Goodfellow 2014)",
        "domain": "IA",
        "pattern": "P1 (Pont)",
        "status": "✅",
        "lianes_s0": ["∇L", "argmin", "argmax", "E[X]", "log", "exp", "Nash", "GAN"],
        "liane_clé": "Nash (3 continents: Finance+IA+Bio) = game theory→deep learning",
        "note": "x2453 = explosion record. Nash equilibrium = liane game theory. argmin/argmax (3 continents).",
    },
    30: {
        "name": "Gut-Brain Axis (en formation)",
        "domain": "Médecine",
        "pattern": "P1 (en cours)",
        "status": "✅",
        "lianes_s0": ["R₀", "P(A)", "Bayes", "exp", "χ²", "Var"],
        "liane_clé": "Bayes (4) + χ² (4) + Var (4) = lianes statistiques multi-continents",
        "note": "0 papers en 2005. Pont progressif. Les lianes stats sont les escaliers.",
    },
    31: {
        "name": "Cryo-EM (Nobel 2017)",
        "domain": "Physique×Bio",
        "pattern": "P3 (Théorie×Outil)",
        "status": "✅",
        "lianes_s0": ["ℱ", "FFT", "∫", "exp", "sin", "cos", "∇²"],
        "liane_clé": "FFT (4 continents) + ℱ (4 continents) = Fourier = LIANE MAJEURE",
        "note": "Microscopie depuis 1970s, résolution insuffisante. FFT/RELION = outil. Fourier traverse tout.",
    },
    32: {
        "name": "Poincaré — Millennium (Perelman 2003)",
        "domain": "Maths×Physique",
        "pattern": "P1+P4 (Pont quadruple)",
        "status": "✅",
        "lianes_s0": ["S_ent", "∂", "∫", "∇", "Γ", "exp", "lim", "gμν", "∇²", "ε", "δ"],
        "liane_clé": "S_ent (3) = PORTE DÉROBÉE thermodynamique → géométrie",
        "note": "99 ans ouvert. 4 domaines connectés. W-entropie = Boltzmann en topologie. TEST SUPRÊME.",
    },
}


def analyze_all():
    """Vérifie la théorie des lianes sur les 32 tests."""
    
    print(f"\n{'='*75}")
    print(f"  YGGDRASIL — VÉRIFICATION LIANES × 32 TESTS")
    print(f"  \"Chaque découverte a-t-elle pris l'escalier de secours?\"")
    print(f"{'='*75}\n")
    
    results = {
        "liane_confirmed": [],    # Has multi-continent liane (3+)
        "universal_liane": [],     # Has universal liane (6+)
        "no_liane": [],            # No multi-continent liane
        "dense_no_need": [],       # Pattern Dense — doesn't NEED lianes
    }
    
    all_lianes_used = defaultdict(int)
    pattern_liane_scores = defaultdict(list)
    
    for num in sorted(ALL_TESTS.keys()):
        test = ALL_TESTS[num]
        lianes = test["lianes_s0"]
        
        # Score each liane
        scores = []
        for s in lianes:
            score = LIANE_SCORES.get(s, 1)
            scores.append((s, score))
            all_lianes_used[s] += 1
        
        max_score = max(s for _, s in scores) if scores else 0
        avg_score = sum(s for _, s in scores) / len(scores) if scores else 0
        has_universal = any(s >= 6 for _, s in scores)
        has_liane = any(s >= 3 for _, s in scores)
        
        pattern = test["pattern"]
        pattern_liane_scores[pattern].append(max_score)
        
        # Classify
        is_dense = "P2" in pattern
        
        if is_dense:
            results["dense_no_need"].append(num)
            status = "🔵 DENSE (pas besoin)"
        elif has_universal:
            results["universal_liane"].append(num)
            results["liane_confirmed"].append(num)
            status = "🌿🌿🌿 LIANE UNIVERSELLE"
        elif has_liane:
            results["liane_confirmed"].append(num)
            status = "🌿 LIANE CONFIRMÉE"
        else:
            results["no_liane"].append(num)
            status = "⚠️ PAS DE LIANE S0"
        
        # Print
        top_lianes = sorted(scores, key=lambda x: -x[1])[:3]
        top_str = ", ".join(f"{s}({n})" for s, n in top_lianes)
        
        print(f"  #{num:>2} {test['name'][:42]:<42} {status}")
        print(f"       {test['pattern']:<20} Top: {top_str}")
        print(f"       Clé: {test['liane_clé'][:70]}")
        print()
    
    # === SUMMARY ===
    total = len(ALL_TESTS)
    confirmed = len(results["liane_confirmed"])
    universal = len(results["universal_liane"])
    dense = len(results["dense_no_need"])
    no_liane = len(results["no_liane"])
    
    # For the real ratio, Dense patterns don't count (they don't NEED lianes)
    testable = total - dense
    
    print(f"\n{'='*75}")
    print(f"  RÉSULTATS GLOBAUX")
    print(f"{'='*75}\n")
    
    print(f"  Total tests:                          {total}")
    print(f"  Pattern Dense (pas besoin de liane):  {dense}  ({', '.join(f'#{n}' for n in results['dense_no_need'])})")
    print(f"  Tests avec liane nécessaire:          {testable}")
    print(f"  ─────────────────────────────────────────")
    print(f"  🌿🌿🌿 Avec liane universelle (6+):    {universal}")
    print(f"  🌿    Avec liane (3+):                 {confirmed}")
    print(f"  ⚠️    Sans liane S0:                   {no_liane}  ({', '.join(f'#{n}' for n in results['no_liane'])})")
    print()
    
    ratio = confirmed / testable * 100 if testable > 0 else 0
    print(f"  ┌─────────────────────────────────────────────────┐")
    print(f"  │                                                 │")
    print(f"  │   TAUX DE VALIDATION: {confirmed}/{testable} = {ratio:.0f}%{' '*17}│")
    print(f"  │                                                 │")
    print(f"  │   Sur {testable} découvertes qui NÉCESSITENT un pont,    │")
    print(f"  │   {confirmed} ont utilisé une liane multi-continent.    │")
    print(f"  │                                                 │")
    print(f"  └─────────────────────────────────────────────────┘\n")
    
    # === TOP LIANES USED ===
    print(f"  TOP 15 LIANES LES PLUS UTILISÉES DANS LES DÉCOUVERTES")
    print(f"  {'─'*60}")
    top_used = sorted(all_lianes_used.items(), key=lambda x: (-x[1], -LIANE_SCORES.get(x[0], 0)))
    for s, count in top_used[:15]:
        continents = LIANE_SCORES.get(s, 1)
        bar = "█" * count
        print(f"  {s:>10}  [{continents} cont.]  {count:>2}× utilisé  {bar}")
    
    # === PATTERN × LIANE CORRELATION ===
    print(f"\n\n  CORRÉLATION PATTERN × SCORE LIANE MAXIMAL")
    print(f"  {'─'*60}")
    for pattern in sorted(pattern_liane_scores.keys()):
        scores = pattern_liane_scores[pattern]
        avg = sum(scores) / len(scores)
        mn = min(scores)
        mx = max(scores)
        print(f"  {pattern:<30}  avg={avg:.1f}  min={mn}  max={mx}  (n={len(scores)})")
    
    # === EXCEPTIONS ANALYSIS ===
    if results["no_liane"]:
        print(f"\n\n  ANALYSE DES EXCEPTIONS (sans liane S0)")
        print(f"  {'─'*60}")
        for num in results["no_liane"]:
            test = ALL_TESTS[num]
            print(f"  #{num} {test['name']}")
            print(f"    → {test['note']}")
            print()
    
    # === KEY INSIGHT ===
    print(f"\n{'='*75}")
    print(f"  INSIGHT FINAL")
    print(f"{'='*75}\n")
    print(f"  Les lianes S0 multi-continents sont les ESCALIERS DE SECOURS.")
    print(f"  Les Pattern Dense (P2) prennent l'ASCENSEUR CENTRAL.")
    print(f"  Les Pattern Anti-signal (P5) ont les lianes mais PAS l'outil.")
    print(f"")
    print(f"  La COMBINAISON qui prédit une découverte:")
    print(f"    1. Trou structurel détecté (co-occurrence ~0)")
    print(f"    2. Lianes multi-continents disponibles (symboles S0 partagés)")
    print(f"    3. Quelqu'un prend l'escalier de secours au lieu de l'ascenseur")
    print(f"")
    print(f"  exp (6 continents) est LA liane #1 — utilisée dans {all_lianes_used.get('exp',0)}/32 tests.")
    print(f"  ∫ et Σ suivent — les opérations fondamentales qui traversent TOUT.")
    print(f"  Puis ∂ — la dérivée partielle qui connecte Finance, Physique, Maths, Ingénierie.")
    print(f"")
    print(f"  La seule vraie exception: CRISPR (#4) — un pont purement biologique.")
    print(f"  Les lianes mathématiques ne couvrent pas les ponts moléculaires.")
    print(f"  Mais c'est normal: la carte des 794 symboles est MATHÉMATIQUE.")
    print(f"  Les lianes biologiques sont un AUTRE TYPE d'escalier de secours.")
    
    # === EXPORT ===
    export = {
        "meta": {
            "date": "2026-02-18T23:45",
            "total_tests": total,
            "testable": testable,
            "confirmed": confirmed,
            "ratio": f"{ratio:.0f}%",
        },
        "results": {
            num: {
                "name": ALL_TESTS[num]["name"],
                "pattern": ALL_TESTS[num]["pattern"],
                "lianes": ALL_TESTS[num]["lianes_s0"],
                "max_continents": max(LIANE_SCORES.get(s, 1) for s in ALL_TESTS[num]["lianes_s0"]),
                "has_liane_3plus": any(LIANE_SCORES.get(s, 1) >= 3 for s in ALL_TESTS[num]["lianes_s0"]),
                "liane_clé": ALL_TESTS[num]["liane_clé"],
            }
            for num in sorted(ALL_TESTS.keys())
        },
        "top_lianes": [
            {"symbol": s, "continents": LIANE_SCORES.get(s, 1), "used_in_n_tests": c}
            for s, c in top_used[:20]
        ],
    }
    
    with open("verification_32tests.json", 'w', encoding='utf-8') as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"\n  → Exporté: verification_32tests.json")
    
    return export


if __name__ == "__main__":
    analyze_all()
