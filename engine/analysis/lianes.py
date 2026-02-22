"""
YGGDRASIL — LIANES ENGINE
"L'escalier de secours. La porte dérobée. Le passage secret."

Hypothèse (Sky, 18 février 2026, 23h31):
Les symboles S0 utilisés par PLUSIEURS corps de métier sont les LIANES —
les escaliers de secours qui permettent de monter aux strates supérieures.
Plus un symbole traverse de continents-métiers, plus il est une clé
pour atteindre S3 et au-delà.

Perelman n'a pas pris l'ascenseur central (topologie pure).
Il a pris la LIANE entropie — symbole de physicien statisticien
que les géomètres n'avaient jamais touché. Passage secret.

Ce script:
1. Mappe chaque symbole S0 vers ses continents-métiers
2. Identifie les LIANES (symboles multi-continents)
3. Vérifie si les découvertes S3 validées utilisent des lianes
4. Génère la carte des escaliers de secours
"""

import json
from collections import defaultdict

# ══════════════════════════════════════════════════════════════
# CONTINENTS = CORPS DE MÉTIER (qui utilise quoi dans la vraie vie)
# ══════════════════════════════════════════════════════════════

CONTINENTS = {
    "Mathématiques Pures": {
        "color": "#1e3a8a",
        "domains": [
            "algèbre", "algèbre lin", "analyse", "analyse fonctionnelle", 
            "topologie", "géométrie", "géom diff", "géom algébrique", 
            "nb théorie", "nb premiers", "nombres", "catégories", 
            "ensembles", "logique", "descriptive", "mesure",
            "complexes", "arithmétique", "trigonométrie", "ordinaux",
            "combinatoire",
        ]
    },
    "Physique Fondamentale": {
        "color": "#7c3aed",
        "domains": [
            "quantique", "relativité", "QFT", "particules", 
            "cosmologie", "gravitation", "nucléaire", "mécanique stat",
            "mécanique", "mécanique analytique", "optique", "astronomie",
        ]
    },
    "Ingénierie & Électricité": {
        "color": "#ea580c",
        "domains": [
            "électromagn", "signal", "contrôle", "fluides", 
            "EDP", "thermo", "automates",
        ]
    },
    "Informatique & IA": {
        "color": "#06b6d4",
        "domains": [
            "calculabilité", "complexité", "ML", "crypto", 
            "information", "automates",
        ]
    },
    "Finance & Économie": {
        "color": "#eab308",
        "domains": [
            "finance", "économie", "statistiques", "probabilités",
            "stochastique", "optimisation",
        ]
    },
    "Biologie & Médecine": {
        "color": "#84cc16",
        "domains": ["biologie"],
    },
    "Chimie": {
        "color": "#f43f5e",
        "domains": ["chimie"],
    },
}

# Reverse lookup: domain → list of continents
DOMAIN_TO_CONTINENTS = defaultdict(list)
for continent, info in CONTINENTS.items():
    for domain in info["domains"]:
        DOMAIN_TO_CONTINENTS[domain].append(continent)


# ══════════════════════════════════════════════════════════════
# SYMBOLES MULTI-USAGE — Override manuel pour les symboles
# qui sont UTILISÉS par plusieurs métiers même si leur domaine
# d'origine est un seul. C'est ça la vraie liane.
# Exemple: ∫ est classé "analyse" mais utilisé par TOUT LE MONDE.
# ══════════════════════════════════════════════════════════════

USAGE_OVERRIDES = {
    # === LIANES MAJEURES (5+ continents) ===
    "∫":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Finance & Économie", "Biologie & Médecine", "Chimie"],
    "∂":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Finance & Économie", "Biologie & Médecine"],
    "Σ":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Finance & Économie", "Informatique & IA", "Biologie & Médecine"],
    "exp":    ["Mathématiques Pures", "Physique Fondamentale", "Finance & Économie", "Informatique & IA", "Biologie & Médecine", "Chimie"],
    "ln":     ["Mathématiques Pures", "Physique Fondamentale", "Finance & Économie", "Informatique & IA", "Biologie & Médecine", "Chimie"],
    "π":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Informatique & IA"],
    "e":      ["Mathématiques Pures", "Physique Fondamentale", "Finance & Économie", "Informatique & IA", "Biologie & Médecine"],
    "∞":      ["Mathématiques Pures", "Physique Fondamentale", "Informatique & IA", "Finance & Économie"],
    "lim":    ["Mathématiques Pures", "Physique Fondamentale", "Finance & Économie", "Ingénierie & Électricité"],
    "=":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Informatique & IA", "Finance & Économie", "Biologie & Médecine", "Chimie"],
    
    # === LIANES FORTES (4 continents) ===
    "∇":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Informatique & IA"],
    "∇²":     ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Chimie"],
    "sin":    ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Informatique & IA"],
    "cos":    ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Informatique & IA"],
    "λ":      ["Mathématiques Pures", "Physique Fondamentale", "Informatique & IA", "Finance & Économie"],
    "P(A)":   ["Mathématiques Pures", "Finance & Économie", "Informatique & IA", "Biologie & Médecine"],
    "E[X]":   ["Mathématiques Pures", "Finance & Économie", "Informatique & IA", "Biologie & Médecine"],
    "Var":    ["Mathématiques Pures", "Finance & Économie", "Informatique & IA", "Biologie & Médecine"],
    "N(μ,σ²)":["Mathématiques Pures", "Finance & Économie", "Biologie & Médecine", "Physique Fondamentale"],
    "Bayes":  ["Mathématiques Pures", "Finance & Économie", "Informatique & IA", "Biologie & Médecine"],
    "∬":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Chimie"],
    "∮":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Chimie"],
    "d/dx":   ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Finance & Économie"],
    "O(n)":   ["Mathématiques Pures", "Informatique & IA", "Finance & Économie", "Ingénierie & Électricité"],
    "ε":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Finance & Économie"],
    "δ":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Finance & Économie"],
    "Π":      ["Mathématiques Pures", "Physique Fondamentale", "Finance & Économie", "Informatique & IA"],
    "ℱ":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Informatique & IA"],
    "FFT":    ["Ingénierie & Électricité", "Informatique & IA", "Physique Fondamentale", "Finance & Économie"],
    "∗_conv": ["Ingénierie & Électricité", "Informatique & IA", "Physique Fondamentale", "Mathématiques Pures"],
    "log":    ["Mathématiques Pures", "Informatique & IA", "Finance & Économie", "Biologie & Médecine"],
    "det":    ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité", "Informatique & IA"],
    "σ_std":  ["Mathématiques Pures", "Finance & Économie", "Physique Fondamentale", "Biologie & Médecine"],
    "χ²":     ["Mathématiques Pures", "Finance & Économie", "Biologie & Médecine", "Physique Fondamentale"],
    
    # === LIANES MOYENNES (3 continents) ===
    "H(X)":   ["Informatique & IA", "Physique Fondamentale", "Finance & Économie"],
    "D_KL":   ["Informatique & IA", "Physique Fondamentale", "Finance & Économie"],
    "W(t)":   ["Finance & Économie", "Physique Fondamentale", "Mathématiques Pures"],
    "SDE":    ["Finance & Économie", "Physique Fondamentale", "Biologie & Médecine"],
    "Itô":    ["Finance & Économie", "Physique Fondamentale", "Mathématiques Pures"],
    "S_ent":  ["Physique Fondamentale", "Chimie", "Informatique & IA"],
    "F=ma":   ["Physique Fondamentale", "Ingénierie & Électricité", "Biologie & Médecine"],
    "PV=nRT": ["Physique Fondamentale", "Ingénierie & Électricité", "Chimie"],
    "∇L":     ["Informatique & IA", "Mathématiques Pures", "Finance & Économie"],
    "SGD":    ["Informatique & IA", "Finance & Économie", "Biologie & Médecine"],
    "argmin": ["Mathématiques Pures", "Informatique & IA", "Finance & Économie"],
    "argmax": ["Mathématiques Pures", "Informatique & IA", "Finance & Économie"],
    "R₀":     ["Biologie & Médecine", "Finance & Économie", "Mathématiques Pures"],
    "Nash":   ["Finance & Économie", "Informatique & IA", "Biologie & Médecine"],
    "∇×":     ["Physique Fondamentale", "Ingénierie & Électricité", "Mathématiques Pures"],
    "∇·":     ["Physique Fondamentale", "Ingénierie & Électricité", "Mathématiques Pures"],
    "Re":     ["Ingénierie & Électricité", "Physique Fondamentale", "Biologie & Médecine"],
    "BS":     ["Finance & Économie", "Mathématiques Pures", "Physique Fondamentale"],
    "TM":     ["Informatique & IA", "Mathématiques Pures", "Physique Fondamentale"],
    "Γ":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité"],
    "ζ":      ["Mathématiques Pures", "Physique Fondamentale", "Finance & Économie"],
    "i":      ["Mathématiques Pures", "Physique Fondamentale", "Ingénierie & Électricité"],
    "GAN":    ["Informatique & IA", "Biologie & Médecine", "Finance & Économie"],
    "Attn":   ["Informatique & IA", "Biologie & Médecine", "Finance & Économie"],
    "ℒ":      ["Physique Fondamentale", "Mathématiques Pures", "Ingénierie & Électricité"],
    "ℋ":      ["Physique Fondamentale", "Mathématiques Pures", "Informatique & IA"],
}

# ══════════════════════════════════════════════════════════════
# DÉCOUVERTES S3 — Quels symboles S0 ont servi de liane?
# ══════════════════════════════════════════════════════════════

S3_DISCOVERIES = {
    "Poincaré (Perelman 2003)": {
        "lianes_used": ["S_ent", "∂", "∫", "∇", "Γ", "exp", "lim", "gμν"],
        "pattern": "PONT",
        "type_trou": "A (Technique)",
        "note": "Liane entropie (S_ent) = Boltzmann→Géométrie. Porte dérobée thermodynamique.",
    },
    "Fermat (Wiles 1995)": {
        "lianes_used": ["Gal", "ζ", "∫", "Σ", "det", "λ"],
        "pattern": "PONT",
        "type_trou": "A (Technique)",
        "note": "Liane Galois (Gal) + courbes elliptiques → théorie des nombres. Taniyama-Shimura bridge.",
    },
    "GANs (Goodfellow 2014)": {
        "lianes_used": ["∇L", "argmin", "argmax", "E[X]", "log", "exp", "Nash"],
        "pattern": "PONT",
        "type_trou": "B (Conceptuel)",
        "note": "Liane Nash (game theory) → deep learning. min-max = symbole multi-continent.",
    },
    "CRISPR (Doudna & Charpentier 2012)": {
        "lianes_used": ["DNA", "RNA"],
        "pattern": "PONT",
        "type_trou": "B (Conceptuel)",
        "note": "Pas de liane S0 math — pont biologique pur. Exception qui confirme la règle?",
    },
    "AlphaFold (2020)": {
        "lianes_used": ["Attn", "∇L", "exp", "argmin", "E[X]"],
        "pattern": "PONT",
        "type_trou": "B (Conceptuel)",
        "note": "Liane Attention (Attn) = ML→Bio. Le Transformer comme escalier de secours.",
    },
    "mRNA Vaccines (Karikó)": {
        "lianes_used": ["RNA", "exp"],
        "pattern": "PONT",
        "type_trou": "C (Perceptuel)",
        "note": "Pas de liane S0 math directe. Trou perceptuel = blocage social, pas technique.",
    },
    "Higgs (2012)": {
        "lianes_used": ["ℒ", "φ_Higgs", "∂", "∫", "exp", "Σ"],
        "pattern": "THÉORIE × OUTIL",
        "type_trou": "A (Technique)",
        "note": "Liane Lagrangien (ℒ) traverse Physique+Maths+Ingénierie.",
    },
    "Immunothérapie CAR-T": {
        "lianes_used": ["R₀", "exp", "P(A)"],
        "pattern": "PONT",
        "type_trou": "B (Conceptuel)",
        "note": "Liane R₀ (reproduction number) = modèle épidémio appliqué à l'immunologie.",
    },
    "Black-Scholes (1973)": {
        "lianes_used": ["∂", "∫", "W(t)", "exp", "N(μ,σ²)", "S_ent", "Itô"],
        "pattern": "PONT",
        "type_trou": "B (Conceptuel)",
        "note": "Liane mouvement brownien (W(t)) = Physique→Finance. Einstein/Bachelier bridge.",
    },
    "Transformers (Vaswani 2017)": {
        "lianes_used": ["Attn", "exp", "softmax", "∇L", "Σ", "det"],
        "pattern": "PONT",
        "type_trou": "B (Conceptuel)",
        "note": "Liane softmax+exp = statistiques→architecture neurale.",
    },
}


def load_symbols(filepath="strates_export.json"):
    """Charge les symboles depuis le JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    symbols = []
    for strate in data.get("strates", []):
        sid = strate["id"]
        for sym in strate.get("symbols", []):
            symbols.append({
                "s": sym["s"],
                "from": sym.get("from", ""),
                "domain": sym.get("domain", ""),
                "strate": sid,
            })
    return symbols


def get_continents(symbol):
    """
    Retourne les continents d'un symbole.
    Priorité: override manuel > lookup par domaine.
    """
    s = symbol["s"]
    
    # Override manuel (usage réel multi-métier)
    if s in USAGE_OVERRIDES:
        return USAGE_OVERRIDES[s]
    
    # Lookup par domaine
    domain = symbol["domain"]
    return DOMAIN_TO_CONTINENTS.get(domain, ["Non classé"])


def classify_liane(n_continents):
    """Classifie le type de liane selon le nombre de continents."""
    if n_continents >= 6:
        return "🌿🌿🌿 LIANE UNIVERSELLE"
    elif n_continents >= 4:
        return "🌿🌿 LIANE MAJEURE"
    elif n_continents >= 3:
        return "🌿 LIANE"
    elif n_continents >= 2:
        return "🌱 PONT"
    else:
        return "· local"


def analyze():
    """Analyse complète des lianes S0."""
    symbols = load_symbols()
    s0 = [s for s in symbols if s["strate"] == 0]
    s3 = [s for s in symbols if s["strate"] == 3]
    
    print(f"\n{'='*70}")
    print(f"  YGGDRASIL — ANALYSE DES LIANES")
    print(f"  \"L'escalier de secours. La porte dérobée.\"")
    print(f"{'='*70}\n")
    print(f"  S0: {len(s0)} symboles (le SOL)")
    print(f"  S3: {len(s3)} symboles (les MOTIFS — conjectures + preuves)")
    print(f"  Total: {len(symbols)} symboles\n")
    
    # === STEP 1: Map S0 symbols to continents ===
    liane_data = []
    for sym in s0:
        continents = get_continents(sym)
        n = len(continents)
        liane_data.append({
            "s": sym["s"],
            "domain": sym["domain"],
            "continents": continents,
            "n_continents": n,
            "type": classify_liane(n),
        })
    
    # Sort by number of continents (descending)
    liane_data.sort(key=lambda x: (-x["n_continents"], x["s"]))
    
    # === STEP 2: Stats ===
    universelles = [l for l in liane_data if l["n_continents"] >= 6]
    majeures = [l for l in liane_data if 4 <= l["n_continents"] < 6]
    lianes = [l for l in liane_data if l["n_continents"] == 3]
    ponts = [l for l in liane_data if l["n_continents"] == 2]
    locaux = [l for l in liane_data if l["n_continents"] <= 1]
    
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │  DISTRIBUTION DES LIANES S0                 │")
    print(f"  ├─────────────────────────────────────────────┤")
    print(f"  │  🌿🌿🌿 Universelles (6+ continents): {len(universelles):>4}  │")
    print(f"  │  🌿🌿  Majeures (4-5 continents):    {len(majeures):>4}  │")
    print(f"  │  🌿    Lianes (3 continents):         {len(lianes):>4}  │")
    print(f"  │  🌱    Ponts (2 continents):          {len(ponts):>4}  │")
    print(f"  │  ·     Locaux (1 continent):          {len(locaux):>4}  │")
    print(f"  └─────────────────────────────────────────────┘\n")
    
    # === STEP 3: Top lianes ===
    print(f"\n  TOP LIANES UNIVERSELLES (6+ continents)")
    print(f"  {'─'*60}")
    for l in universelles:
        conts = ", ".join(c.split()[0] for c in l["continents"])
        print(f"  {l['s']:>10}  [{l['n_continents']}]  {conts}")
    
    print(f"\n  TOP LIANES MAJEURES (4-5 continents)")
    print(f"  {'─'*60}")
    for l in majeures[:25]:
        conts = ", ".join(c.split()[0] for c in l["continents"])
        print(f"  {l['s']:>10}  [{l['n_continents']}]  {conts}")
    
    print(f"\n  LIANES (3 continents)")
    print(f"  {'─'*60}")
    for l in lianes[:25]:
        conts = ", ".join(c.split()[0] for c in l["continents"])
        print(f"  {l['s']:>10}  [{l['n_continents']}]  {conts}")
    
    # === STEP 4: Vérification découvertes S3 ===
    print(f"\n\n{'='*70}")
    print(f"  VÉRIFICATION: LES DÉCOUVERTES S3 UTILISENT-ELLES DES LIANES?")
    print(f"{'='*70}\n")
    
    # Build lookup
    liane_lookup = {l["s"]: l for l in liane_data}
    
    for name, disc in S3_DISCOVERIES.items():
        used = disc["lianes_used"]
        scores = []
        for s in used:
            if s in liane_lookup:
                scores.append(liane_lookup[s]["n_continents"])
            else:
                scores.append(1)  # bio/domain-specific
        
        max_score = max(scores) if scores else 0
        avg_score = sum(scores) / len(scores) if scores else 0
        has_liane = any(s >= 3 for s in scores)
        
        status = "✅ LIANE CONFIRMÉE" if has_liane else "⚠️ Pas de liane S0"
        
        print(f"  {name}")
        print(f"    Pattern: {disc['pattern']} | Type: {disc['type_trou']}")
        print(f"    Symboles-clés: {', '.join(used)}")
        print(f"    Score max: {max_score} continents | Moy: {avg_score:.1f}")
        print(f"    → {status}")
        print(f"    Note: {disc['note']}")
        print()
    
    # === STEP 5: Continent bridge matrix ===
    print(f"\n{'='*70}")
    print(f"  MATRICE DES PONTS INTER-CONTINENTS")
    print(f"  (combien de symboles S0 relient chaque paire)")
    print(f"{'='*70}\n")
    
    continent_names = list(CONTINENTS.keys())
    bridge_matrix = defaultdict(int)
    
    for l in liane_data:
        conts = l["continents"]
        for i, a in enumerate(conts):
            for b in conts[i+1:]:
                key = tuple(sorted([a, b]))
                bridge_matrix[key] += 1
    
    # Print matrix
    short = [c.split()[0][:8] for c in continent_names]
    print(f"  {'':>12}", end="")
    for s in short:
        print(f" {s:>8}", end="")
    print()
    
    for i, a in enumerate(continent_names):
        print(f"  {short[i]:>12}", end="")
        for j, b in enumerate(continent_names):
            if j <= i:
                key = tuple(sorted([a, b]))
                val = bridge_matrix.get(key, 0)
                if val > 0 and i != j:
                    print(f" {val:>8}", end="")
                else:
                    print(f" {'·':>8}", end="")
            else:
                print(f" {'':>8}", end="")
        print()
    
    # === STEP 6: Les trous — paires avec PEU de lianes ===
    print(f"\n\n  PAIRES LES MOINS CONNECTÉES (trous dans les lianes)")
    print(f"  {'─'*60}")
    
    all_pairs = []
    for i, a in enumerate(continent_names):
        for b in continent_names[i+1:]:
            key = tuple(sorted([a, b]))
            count = bridge_matrix.get(key, 0)
            all_pairs.append((a, b, count))
    
    all_pairs.sort(key=lambda x: x[2])
    for a, b, count in all_pairs[:10]:
        emoji = "🕳️" if count == 0 else "❄️" if count < 3 else "🌡️"
        print(f"  {emoji} {a} × {b}: {count} lianes")
    
    # === EXPORT JSON ===
    export = {
        "meta": {
            "date": "2026-02-18",
            "hypothesis": "Les symboles S0 multi-continents sont les escaliers de secours vers S3",
            "s0_total": len(s0),
            "s3_total": len(s3),
        },
        "stats": {
            "universelles": len(universelles),
            "majeures": len(majeures),
            "lianes": len(lianes),
            "ponts": len(ponts),
            "locaux": len(locaux),
        },
        "lianes": [
            {
                "symbol": l["s"],
                "domain": l["domain"],
                "continents": l["continents"],
                "n_continents": l["n_continents"],
                "type": l["type"],
            }
            for l in liane_data if l["n_continents"] >= 2
        ],
        "discoveries_check": {
            name: {
                "lianes_used": disc["lianes_used"],
                "has_multi_continent_liane": any(
                    liane_lookup.get(s, {}).get("n_continents", 1) >= 3
                    for s in disc["lianes_used"]
                ),
                "max_continents": max(
                    (liane_lookup.get(s, {}).get("n_continents", 1) for s in disc["lianes_used"]),
                    default=0
                ),
            }
            for name, disc in S3_DISCOVERIES.items()
        },
        "bridge_matrix": {
            f"{a} × {b}": count
            for (a, b), count in sorted(bridge_matrix.items(), key=lambda x: -x[1])
        },
    }
    
    with open("lianes_export.json", 'w', encoding='utf-8') as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"\n  → Exporté: lianes_export.json")
    
    return export


if __name__ == "__main__":
    analyze()
