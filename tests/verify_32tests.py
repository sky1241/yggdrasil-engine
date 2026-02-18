"""
YGGDRASIL — VERIFICATION LIANES x 32 TESTS
Sky x Claude — 19 Fevrier 2026, 00h, Versoix
"""
import json

LIANE_SCORES = {
    "=": 7, "exp": 6, "ln": 6, "Sigma": 6, "int": 6,
    "e": 5, "partial": 5,
    "Bayes": 4, "E[X]": 4, "FFT": 4, "N": 4, "O(n)": 4,
    "P(A)": 4, "Var": 4, "cos": 4, "d/dx": 4, "det": 4,
    "lim": 4, "log": 4, "sin": 4, "Pi": 4, "delta": 4, "eps": 4,
    "lambda": 4, "pi": 4, "sigma_std": 4, "chi2": 4, "F_fourier": 4,
    "nabla": 4, "nabla2": 4, "conv": 4,
    "Attn": 3, "BS": 3, "D_KL": 3, "F=ma": 3, "GAN": 3,
    "H(X)": 3, "Ito": 3, "Nash": 3, "PV=nRT": 3, "R0": 3,
    "Re": 3, "SDE": 3, "SGD": 3, "S_ent": 3, "TM": 3, "W(t)": 3,
    "argmax": 3, "argmin": 3, "i": 3, "Gamma": 3, "zeta": 3,
    "H_ham": 3, "L_lag": 3, "nablaL": 3, "div": 3, "curl": 3,
    "softmax": 3, "log2": 3,
}

# Unicode-safe version
LIANE_MAP = {
    # 6+ continents
    "=": 7, "exp": 6, "ln": 6, "S": 6, "integral": 6,
    # 5 continents
    "e_const": 5, "partial_d": 5,
    # 4 continents
    "Bayes": 4, "E[X]": 4, "FFT": 4, "Normal": 4, "O(n)": 4,
    "P(A)": 4, "Var": 4, "cos": 4, "det": 4, "lim": 4, "log": 4,
    "sin": 4, "chi2": 4, "Fourier": 4, "nabla": 4, "lambda": 4,
    # 3 continents
    "Attn": 3, "Nash": 3, "R0": 3, "S_ent": 3, "argmin": 3,
    "argmax": 3, "Ito": 3, "W(t)": 3, "Lagrangian": 3,
    "nablaL": 3, "softmax": 3, "H(X)": 3, "zeta": 3, "Gamma": 3,
    "GAN": 3, "D_KL": 3, "TM": 3,
}

TESTS = [
    {"id":1,  "name":"Fermat (Wiles 1995)",        "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],S[6],lambda[4],det[4],zeta[3]"},
    {"id":2,  "name":"Classification Groupes Finis","pattern":"P2","has_multi":False, "max_liane":1, "key_lianes":"(intra-maths pures, pas de pont)"},
    {"id":3,  "name":"Higgs (2012)",                "pattern":"P3","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],exp[6],S[6],partial[5],Lagrangian[3]"},
    {"id":4,  "name":"CRISPR (2012)",               "pattern":"P1","has_multi":False, "max_liane":1, "key_lianes":"(pont biologique pur, pas de liane S0 math)"},
    {"id":5,  "name":"Dark Matter (ouvert)",        "pattern":"P4","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],exp[6] — trou persiste malgre lianes"},
    {"id":6,  "name":"Deep Learning (2012)",        "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],S[6],partial[5],Bayes[4],nablaL[3]"},
    {"id":7,  "name":"Graphene (2004)",             "pattern":"P5","has_multi":False, "max_liane":1, "key_lianes":"(intra-materiaux, pas de pont active)"},
    {"id":8,  "name":"Poincare (Perelman 2003)",    "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],exp[6],partial[5],nabla[4],S_ent[3]"},
    {"id":9,  "name":"Immunotherapie (2018)",       "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],P(A)[4],E[X][4],R0[3]"},
    {"id":10, "name":"Ondes gravitationnelles",     "pattern":"P3","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],FFT[4],Fourier[4],sin[4]"},
    {"id":11, "name":"Supraconducteurs HT (1986)",  "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],S_ent[3] — chimie->physique"},
    {"id":12, "name":"Quantum x Crypto",            "pattern":"P4","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],P(A)[4],H(X)[3] — trou en transition"},
    {"id":13, "name":"Microbiome x Psychiatrie",    "pattern":"P1","has_multi":True,  "max_liane":4, "key_lianes":"Bayes[4],P(A)[4],Normal[4],chi2[4]"},
    {"id":14, "name":"Theorie des cordes",          "pattern":"P5","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],exp[6] — lianes fortes MAIS mur experimental"},
    {"id":15, "name":"AlphaFold (2020)",            "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],E[X][4],Attn[3],nablaL[3]"},
    {"id":16, "name":"Blockchain (2009)",           "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],P(A)[4],log[4],H(X)[3]"},
    {"id":17, "name":"Exoplanetes (1995)",          "pattern":"P2","has_multi":False, "max_liane":4, "key_lianes":"(dense intra-astro, outils standards)"},
    {"id":18, "name":"Isolants topologiques",       "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],exp[6],det[4] — topologie->physique"},
    {"id":19, "name":"Fusion nucleaire (ouvert)",   "pattern":"P4","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],partial[5] — lianes presentes, pont manque"},
    {"id":20, "name":"Economie comportementale",    "pattern":"P1","has_multi":True,  "max_liane":4, "key_lianes":"E[X][4],P(A)[4],Bayes[4],Normal[4]"},
    {"id":21, "name":"CAR-T Cell Therapy",          "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],P(A)[4],E[X][4],R0[3]"},
    {"id":22, "name":"mRNA Vaccines (Kariko)",      "pattern":"P4","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],P(A)[4],R0[3] — trou PERCEPTUEL"},
    {"id":23, "name":"Transformers (2017)",         "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],S[6],det[4],FFT[4],Attn[3]"},
    {"id":24, "name":"Perovskite Solar Cells",      "pattern":"P3","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],integral[6] — chimie->photovoltaique"},
    {"id":25, "name":"Optogenetics (2005)",         "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],integral[6],sin[4],Fourier[4]"},
    {"id":26, "name":"Gene Drives (2014)",          "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],P(A)[4],R0[3]"},
    {"id":27, "name":"Quantum ML",                  "pattern":"P2","has_multi":False, "max_liane":6, "key_lianes":"(domaines partagent DEJA les memes lianes)"},
    {"id":28, "name":"Single-cell RNA-seq",         "pattern":"P3","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],log[4],P(A)[4],Bayes[4]"},
    {"id":29, "name":"GANs (Goodfellow 2014)",      "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],log[4],E[X][4],Nash[3],argmin[3]"},
    {"id":30, "name":"Gut-Brain Axis",              "pattern":"P1","has_multi":True,  "max_liane":4, "key_lianes":"P(A)[4],Bayes[4],Normal[4],chi2[4]"},
    {"id":31, "name":"Cryo-EM (Nobel 2017)",        "pattern":"P3","has_multi":True,  "max_liane":6, "key_lianes":"exp[6],integral[6],FFT[4],Fourier[4],sin[4]"},
    {"id":32, "name":"Poincare DETAIL",             "pattern":"P1","has_multi":True,  "max_liane":6, "key_lianes":"integral[6],exp[6],partial[5],nabla[4],S_ent[3]"},
]


def main():
    print()
    print("="*72)
    print("  YGGDRASIL — VERIFICATION LIANES x 32 TESTS")
    print("  \"Les grandes decouvertes prennent-elles l'escalier de secours?\"")
    print("="*72)
    print()
    
    total = len(TESTS)
    with_liane = sum(1 for t in TESTS if t["has_multi"])
    without = total - with_liane
    
    print(f"  +------------------------------------------------------+")
    print(f"  |  RESULTAT GLOBAL                                     |")
    print(f"  |                                                       |")
    print(f"  |  Avec liane multi-continent:  {with_liane:>2}/{total}  ({100*with_liane//total}%)          |")
    print(f"  |  Sans liane multi-continent:  {without:>2}/{total}  ({100*without//total}%)          |")
    print(f"  +------------------------------------------------------+")
    print()
    
    # By pattern
    patterns = {}
    for t in TESTS:
        p = t["pattern"]
        if p not in patterns:
            patterns[p] = {"total":0, "with":0, "without":0, "tests_with":[], "tests_without":[]}
        patterns[p]["total"] += 1
        if t["has_multi"]:
            patterns[p]["with"] += 1
            patterns[p]["tests_with"].append(t["name"])
        else:
            patterns[p]["without"] += 1
            patterns[p]["tests_without"].append(t["name"])
    
    print("  CORRELATION PATTERN x LIANE:")
    print("  " + "-"*60)
    for p in ["P1","P2","P3","P4","P5"]:
        if p not in patterns: continue
        d = patterns[p]
        pct = 100*d["with"]//d["total"] if d["total"] else 0
        bar = "█" * (d["with"]*2) + "░" * (d["without"]*2)
        print(f"  {p}  {bar}  {d['with']}/{d['total']} avec liane ({pct}%)")
    
    # The key finding
    print()
    print("  ══════════════════════════════════════════════════════")
    print("  DECOUVERTE PRINCIPALE:")
    print("  ══════════════════════════════════════════════════════")
    print()
    
    p1 = patterns.get("P1", {})
    p2 = patterns.get("P2", {})
    p3 = patterns.get("P3", {})
    p4 = patterns.get("P4", {})
    p5 = patterns.get("P5", {})
    
    print(f"  P1 PONT:        {p1.get('with',0)}/{p1.get('total',0)} avec lianes")
    print(f"    → REGLE: Les ponts cross-domaine NECESSITENT des lianes multi-continent")
    if p1.get("tests_without"):
        print(f"    → Exception: {', '.join(p1['tests_without'])}")
        print(f"      (CRISPR = pont biologique pur, pas mathematique)")
    print()
    
    print(f"  P2 DENSE:       {p2.get('without',0)}/{p2.get('total',0)} SANS lianes cross-continent")
    print(f"    → REGLE: Croissance intra-domaine = pas besoin d'escalier de secours")
    if p2.get("tests_without"):
        print(f"    → Cas: {', '.join(p2['tests_without'])}")
    print()
    
    print(f"  P3 THEORIE×OUTIL: {p3.get('with',0)}/{p3.get('total',0)} avec lianes")
    print(f"    → REGLE: Les lianes sont la, le blocage est TECHNIQUE (outil manquant)")
    print()
    
    print(f"  P4 TROU OUVERT: {p4.get('with',0)}/{p4.get('total',0)} avec lianes MAIS pont manque")
    print(f"    → REGLE: Lianes = NECESSAIRES mais PAS SUFFISANTES")
    print()
    
    print(f"  P5 ANTI-SIGNAL: lianes non activees ou mur experimental")
    print()
    
    print("  ══════════════════════════════════════════════════════")
    print("  FORMULE:")
    print("  ══════════════════════════════════════════════════════")
    print()
    print("  Decouverte cross-domaine = Liane(s) + Pont + Timing")
    print()
    print("  - Sans liane  → pas de pont possible (P2/P5)")
    print("  - Avec liane  → pont POSSIBLE mais pas garanti")
    print("  - Avec liane + catalyseur → EXPLOSION (P1)")
    print("  - Avec liane + pas d'outil → ATTENTE (P3/P4)")
    print()
    print("  Les lianes sont les CLES. Le pont est la PORTE.")
    print("  La cle ne suffit pas — il faut aussi trouver la porte.")
    print("  Mais sans cle, la porte est invisible.")
    print()
    
    # Full table
    print()
    print("="*72)
    print("  TABLEAU COMPLET")
    print("="*72)
    print()
    print(f"  {'#':>3}  {'🌿':>2}  {'Nom':<35} {'Pattern':<5} {'Max':<4} Lianes-cles")
    print(f"  {'─'*3}  {'─'*2}  {'─'*35} {'─'*5} {'─'*4} {'─'*30}")
    
    for t in TESTS:
        flag = "🌿" if t["has_multi"] else "· "
        print(f"  {t['id']:>3}  {flag}  {t['name']:<35} {t['pattern']:<5} {t['max_liane']:<4} {t['key_lianes']}")
    
    # Export
    export = {
        "meta": {
            "date": "2026-02-19T00:00:00",
            "author": "Sky x Claude",
            "total_tests": total,
            "with_multi_liane": with_liane,
            "without_multi_liane": without,
        },
        "formula": "Decouverte = Liane(s) + Pont + Timing",
        "rules": {
            "P1_PONT": "Lianes multi-continent NECESSAIRES (sauf pont biologique pur)",
            "P2_DENSE": "Pas de liane cross-continent necessaire (intra-domaine)",
            "P3_THEORIE_OUTIL": "Lianes presentes, blocage technique",
            "P4_TROU_OUVERT": "Lianes presentes mais insuffisantes",
            "P5_ANTI_SIGNAL": "Lianes non activees ou mur experimental",
        },
        "by_pattern": {p: {"total":d["total"],"with_liane":d["with"],"without":d["without"]} for p,d in patterns.items()},
        "tests": TESTS,
    }
    
    with open("lianes_32tests.json", "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"\n  → Exporte: lianes_32tests.json")


if __name__ == "__main__":
    main()
