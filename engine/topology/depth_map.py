#!/usr/bin/env python3
"""
depth_map.py — Placement des symboles par PROFONDEUR LOGIQUE
============================================================
Règle d'or : la position = dépendance logique, PAS popularité.

Axe radial  = profondeur (longueur de la plus longue chaîne de prérequis)
Axe angulaire = domaine

Centre absolu = "=" (Recorde, 1557). Sans =, rien n'existe.
"""
import math, json, os

# ═══════════════════════════════════════════════════════════════
# 1. PROFONDEUR LOGIQUE — symboles originaux (~549 en S0)
# ═══════════════════════════════════════════════════════════════
# Profondeur = longueur de la plus longue chaîne de prérequis.
# Exemple : ∫ a besoin de lim, qui a besoin de ε, <, ∀, ∃, nombres → depth 6

SYMBOL_DEPTH = {
    # ── Profondeur 0 : Le socle absolu ──
    '=': 0,

    # ── Profondeur 1 : Défini directement depuis = ──
    '0': 1, '≠': 1,
    '⊤': 1, '⊥₀': 1,
    '∧': 1, '∨': 1, '¬': 1,
    '∅': 1, '∈': 1,

    # ── Profondeur 2 : Nombres, opérations de base, quantificateurs ──
    '1': 2, '2': 2, '3': 2, '4': 2, '5': 2, '6': 2, '7': 2, '8': 2, '9': 2,
    '+': 2, '−': 2,
    '∃': 2, '∀': 2,
    '∉': 2, '⊂': 2, '⊆': 2, '⊃': 2, '⊇': 2,
    '∪': 2, '∩': 2, '∖': 2, '𝒫(A)': 2, 'A×B': 2,
    'Aᶜ': 2, '⊔': 2, '|A|': 2,
    'x': 2, 'y': 2, 'z': 2,

    # ── Profondeur 3 : Multiplication, ordre, implication ──
    '×': 3, '÷': 3, '<': 3, '>': 3, '≤': 3, '≥': 3,
    '→': 3, '↔': 3, '⟹': 3, '⟺': 3,
    '≡': 3, '∝': 3, '±': 3, 'mod': 3, '|x|': 3,
    '∃!': 3, '∄': 3, '∴': 3, '∵': 3,
    '⊕': 3, '⊨': 3, '⊩': 3,
    'r': 3, '∠': 3, 'θ': 3, '⊥_geom': 3, '∥': 3,

    # ── Profondeur 4 : Puissances, racines, structures numériques ──
    'ⁿ': 4, '!': 4, '%': 4, '√': 4, '∛': 4,
    '⌊x⌋': 4, '⌈x⌉': 4,
    'ℕ': 4, 'ℤ': 4,
    '∞': 4,
    '≈': 4,
    '≅_geom': 4, '∼_geom': 4,
    '⊩_forc': 4,
    '≡_mod': 4, 'gcd': 4, 'lcm': 4,
    'ℵ₀': 4, 'ℵ₁': 4, '𝔠': 4, 'ℶ': 4, 'κ': 4, 'cf': 4, 'Card': 4, 'Ord': 4,
    'Cₙ': 4, 'C(n,k)': 4,
    'ZF': 4, 'ZFC': 4,

    # ── Profondeur 5 : Corps, limites, convergence ──
    'ℚ': 5, 'ℝ': 5, 'ℂ': 5, 'ℍ': 5, '𝕆': 5, 'ℙ': 5, '𝔽ₚ': 5,
    'ε': 5, 'lim': 5, 'sup': 5, 'inf': 5, 'max': 5, 'min': 5,
    'Σ': 5, 'Π': 5, 'O(n)': 5, 'o(n)': 5, 'Θ(n)': 5,
    'Con': 5, 'CH': 5, 'GCH': 5, 'V=L': 5,
    '□': 5, '◇': 5,
    'φ_Eul': 5, 'μ_Mob': 5, 'π(x)': 5,
    'σ(n)': 5, 'τ(n)': 5, 'Λ(n)': 5,
    'P(A)': 5,

    # ── Profondeur 6 : Calcul, fonctions élémentaires, constantes ──
    'e': 6, 'π': 6, 'i': 6, 'φ': 6, 'γₑ': 6,
    'ln': 6, 'log': 6, 'log₂': 6, 'exp': 6,
    'sin': 6, 'cos': 6, 'tan': 6, 'cot': 6, 'sec': 6, 'csc': 6,
    'arcsin': 6, 'arccos': 6, 'arctan': 6,
    'sinh': 6, 'cosh': 6, 'tanh': 6,
    '∫': 6, '∂': 6, 'd/dx': 6, 'dx': 6, "f'": 6, 'ẋ': 6,
    'δ': 6, 'Δ': 6,
    'Fₙ': 6, 'Bₙ': 6,
    '(a/p)': 6, 'ℓ-adic': 6, 'ℤₚ': 6,
    'E[X]': 6, 'Var': 6, 'σ_std': 6, 'σ²': 6, 'μ_moy': 6,
    'Bayes': 6, 'N(μ,σ²)': 6, 'Bin': 6, 'Poi': 6, 'Exp_d': 6,
    '𝟙': 6, '⊥_ind': 6,
    'Kₙ': 6, 'χ_chrom': 6,
    'DFA': 6, 'NFA': 6, 'Reg': 6,
    # Constantes physiques (besoin de nombres + unités)
    'c': 6, 'G': 6, 'ℏ': 6, 'h': 6, 'kB': 6, 'NA': 6, 'R': 6,
    'e⁻': 6, 'μ₀': 6, 'ε₀': 6, 'mol': 6,

    # ── Profondeur 7 : Calcul avancé, algèbre linéaire, physique de base ──
    '∇': 7, '∇²': 7, '∇×': 7, '∇·': 7,
    '∬': 7, '∭': 7, '∮': 7,
    'det': 7, 'tr': 7, 'rank': 7, 'dim': 7, 'span': 7,
    'A⁻¹': 7, 'Aᵀ': 7, 'A†': 7,
    '⊗': 7, '⊕ₐ': 7, '‖v‖': 7, '⟨u,v⟩': 7, 'u×v': 7,
    'λ': 7, 'Iₙ': 7, 'diag': 7, '⊙': 7,
    'Cov': 7, 'Cor': 7,
    'χ²': 7, 't': 7, 'F_dist': 7,
    'H(X)': 7, 'I(X;Y)': 7,
    'μ_mes': 7, 'σ(F)': 7, 'λ_Leb': 7, 'a.e.': 7,
    'CFG': 7, 'PDA': 7, 'CFL': 7,
    # Physique classique
    'F': 7, 'm': 7, 'a_acc': 7, 'v': 7, 'p_mom': 7,
    'E_cin': 7, 'V_pot': 7, 'W_trav': 7, 'P_puis': 7,
    'τ_couple': 7, 'L_ang': 7, 'I_iner': 7, 'ω_ang': 7,
    'g_grav': 7, 'ρ_dens': 7, 'P_pres': 7,
    'σ_SB': 7, 'α_fs': 7,
    'mₑ': 7, 'mₚ': 7, 'mₙ': 7,
    'F=ma': 7, 'a²+b²=c²': 7,

    # ── Profondeur 8 : Fonctions spéciales, algèbre abstraite, physique avancée ──
    'Γ': 8, 'B': 8, 'ζ': 8, 'ξ': 8, 'η': 8, 'L(s,χ)': 8,
    'Ai': 8, 'Bi': 8, 'Jₙ': 8, 'Yₙ': 8, 'Pₙ': 8,
    'Yₗₘ': 8, 'Hₙ': 8, 'Lₙ': 8, 'Tₙ': 8,
    'erf': 8, 'erfc': 8, 'Φ': 8, 'W(x)': 8,
    'Li(x)': 8, 'Si(x)': 8, 'Ci(x)': 8, 'Ei(x)': 8,
    'Res': 8,
    'D_KL': 8, 'C_Sh': 8, 'H_Ren': 8,
    'Lp': 8, 'dμ': 8, 'RN': 8,
    'Cl(K)': 8,
    'Gal': 8, 'Aut': 8, 'Hom': 8, 'End': 8,
    'Ker': 8, 'Im': 8, '≅': 8, '⊲': 8,
    'G/H': 8, '⋊': 8,
    'Sₙ': 8, 'Zₙ': 8, '⟨g⟩': 8, '[G:H]': 8,
    'R[x]': 8, 'I⊲R': 8, 'F*/F': 8, 'Spec': 8,
    'τ_top': 8, 'S¹': 8, 'Sⁿ': 8, 'T²': 8,
    '∼': 8, '∂X': 8, 'cl(A)': 8, 'int(A)': 8,
    # EM, thermo
    'E_em': 8, 'B_em': 8, 'V_pot_em': 8, 'A_em': 8,
    'J_em': 8, 'ρ_ch': 8, 'Φ_B': 8,
    'S_ent': 8, 'T_temp': 8, 'U_int': 8,
    'Q_chal': 8, 'W_therm': 8,
    'F_helm': 8, 'G_gibb': 8, 'H_enth': 8,
    'S=kln W': 8, 'PV=nRT': 8,
    '∇·E=ρ/ε₀': 8, '∇·B=0': 8,
    'ODE': 8, 'PDE': 8, '∂u/∂t': 8, '∂²u/∂t²': 8,
    'ν_visc': 8, 'η_visc': 8, 'Re': 8, 'P_pres': 8,
    'pH': 8, 'Kₑq': 8, 'E°': 8,
    'TM': 8, 'UTM': 8, 'λ_calc': 8,
    'Chom': 8, 'PR': 8,
    'W(t)': 8, 'dW': 8, 'Mart': 8, 'E[·|F]': 8,

    # ── Profondeur 9 : Structures profondes ──
    'GL(n)': 9, 'SL(n)': 9, 'SO(n)': 9, 'SU(n)': 9, 'U(1)': 9,
    'Ob(C)': 9, 'Mor': 9, '∘': 9, 'Funct': 9, 'Nat': 9,
    '≃': 9, 'lim←': 9, 'colim→': 9, 'Yoneda': 9, 'Adj': 9,
    'Set': 9, 'Top': 9, 'Grp': 9, 'Ab': 9, 'Vect': 9, '↪': 9, '↠': 9,
    'π₁': 9, 'πₙ': 9, 'Hₙ_top': 9, 'Hⁿ': 9, 'χ': 9, 'g_top': 9,
    'RP²': 9, 'K_bot': 9,
    'gμν': 9, 'Rμν': 9, 'Rμνρσ': 9, 'R_sc': 9, 'Tμν': 9, 'Γᵢⱼₖ': 9,
    '∧_ext': 9, 'dω': 9, '★': 9, '£_X': 9, 'ωₐ': 9, 'Fₐᵦ': 9, 'd_ext': 9,
    'ℒ': 9, 'ℋ': 9, 'S_act': 9, 'δS=0': 9, '{f,g}': 9, 'q': 9, 'p_gen': 9,
    'Z_part': 9, 'β_inv': 9,
    'ds²': 9, 'γ_lor': 9, 'η_μν': 9, 'Gμν': 9, 'Λ_cos': 9, 'rs': 9,
    'E=mc²': 9, 'Gμν=8πGTμν': 9,
    'G_Grn': 9, 'Sturm': 9, 'NS': 9,
    'Ma': 9, 'Fr': 9,
    'δ_Dir': 9, 'Nyquist': 9,
    'ℱ': 9, 'ℱ⁻¹': 9, 'ℒ_Lap': 9, 'Z_tr': 9,
    'DFT': 9, 'FFT': 9, '∗_conv': 9, '⊛': 9,
    'Itô': 9, 'SDE': 9,
    'argmin': 9, 'argmax': 9, 'L_lag': 9, 'KKT': 9, 'LP': 9, '∇f=0': 9,
    'H_Hilb': 9, 'B_Ban': 9, '⟨·,·⟩_H': 9, 'X*': 9,
    'L²': 9, 'HB': 9, 'ℓ²': 9, 'W^k,p': 9,
    'Ack': 9,
    'ΔG': 9, 'ΔH': 9,
    'n_refr': 9, 'Snell': 9, 'λ_wave': 9, 'ν_freq': 9,
    'H₀': 9, 'T_CMB': 9,
    'DNA': 9, 'RNA': 9, 'ATP': 9,
    'Km': 9, 'Vmax': 9, 'R₀': 9,

    # ── Profondeur 10 : Quantique, QFT, applications avancées ──
    'ψ': 10, 'Ĥ': 10, '⟨ψ|': 10, '|ψ⟩': 10, '⟨ψ|ψ⟩': 10,
    '⟨Â⟩': 10, 'ΔxΔp': 10, '[Â,B̂]': 10,
    'ρ_dm': 10, 'Û': 10,
    'σₓ': 10, 'σᵧ': 10, 'σ_z': 10,
    '|0⟩': 10, '|1⟩': 10, 'H_gate': 10, 'CNOT': 10,
    'Hψ=Eψ': 10, 'E=hν': 10, 'Ψ_wav': 10,
    'Fμν': 10, 'Aμ': 10,
    'σ_xs': 10, 'τ_decay': 10, 'λ_decay': 10,
    'A_mass': 10, 'Z_at': 10, 'β_decay': 10, 'α_decay': 10,
    'SU(2)': 10, 'SU(3)': 10,
    'H(s)': 10, 'PID': 10, 'Bode': 10, 'Nyq_st': 10,
    'LV': 10, 'HW': 10, 'SIR': 10, 'logist': 10,
    'U_util': 10, 'S_D': 10, 'Nash': 10, 'Pareto': 10,
    'eⁱᵖ+1=0': 10,
    'P': 10, 'NL': 10, 'L_log': 10,
    'NC': 10, 'AC': 10, 'SC': 10,
    'DTIME': 10, 'NTIME': 10, 'DSPACE': 10, 'NSPACE': 10,
    'AC⁰': 10, 'TC⁰': 10,
    'L_lang': 10,
    'M☉': 10, 'L☉': 10, 'pc': 10,
    'z_red': 10, 'Ω_m': 10, 'Ω_Λ': 10,

    # ── Profondeur 11 : Hautement spécialisé ──
    'ℒ_QFT': 11, 'ψ̄': 11, 'γμ': 11, 'Dμ': 11, 'Aμ_YM': 11,
    'φ_Higgs': 11, 'v_Higgs': 11, 'αₛ': 11, 'g_w': 11, 'θ_W': 11,
    'CKM': 11, 'PMNS': 11, 'Feyn': 11,
    'RSA': 11, 'AES': 11, 'ECC': 11, 'SHA': 11, 'ZKP': 11,
    '∇L': 11, 'σ_sigm': 11, 'softmax': 11, 'ReLU': 11,
    'CE': 11, 'SGD': 11, 'BP': 11, 'Attn': 11, 'GAN': 11,
    'VC_dim': 11, 'PAC': 11,
    'BS': 11, 'σ_vol': 11, 'VaR': 11, 'CAPM': 11, 'GDP': 11,
    'π_payoff': 11,
    'FLRW': 11, 'a(t)': 11,
}


# ═══════════════════════════════════════════════════════════════
# 2. ANGLES PAR DOMAINE — secteurs autour du centre
# ═══════════════════════════════════════════════════════════════
# La carte est circulaire. Les domaines proches intellectuellement
# sont adjacents angulairement.
#
#              Logique (0°)
#         Finance /    \ Ensembles
#        Économie       Arithmétique
#           ML    \    / Nombres
#     Signal  ─── = ─── Combinatoire
#    Contrôle /    \ Algèbre
#     Physique      Catégories
#        Quantique  / Analyse
#          Thermo  Géométrie
#              Topologie (180°)
#           Probabilités

DOMAIN_ANGLE = {
    # === FONDEMENTS (Nord, 0°) ===
    'logique': 5,
    'ensembles': 22,
    'ordinaux': 15,

    # === ARITHMÉTIQUE (NNE, ~45°) ===
    'arithmétique': 42,
    'nombres': 52,

    # === THÉORIE DES NOMBRES (NE, ~70°) ===
    'nb théorie': 68,
    'nb premiers': 75,

    # === COMBINATOIRE (ENE, ~90°) ===
    'combinatoire': 90,

    # === ALGÈBRE (E, ~110°) ===
    'algèbre': 108,
    'algèbre lin': 118,
    'catégories': 130,

    # === ANALYSE (ESE, ~150°) ===
    'analyse': 145,
    'complexes': 150,
    'trigonométrie': 155,
    'analyse fonctionnelle': 165,
    'mesure': 172,
    'EDP': 178,

    # === GÉOMÉTRIE & TOPOLOGIE (S, ~195°) ===
    'géométrie': 188,
    'géom diff': 196,
    'géom algébrique': 200,
    'topologie': 208,
    'descriptive': 215,

    # === PROBABILITÉS (SSW, ~225°) ===
    'probabilités': 222,
    'statistiques': 228,
    'stochastique': 233,
    'information': 240,

    # === INFORMATIQUE (WSW, ~255°) ===
    'calculabilité': 248,
    'complexité': 254,
    'automates': 260,
    'crypto': 267,

    # === APPLICATIONS MATH (W, ~280°) ===
    'signal': 274,
    'contrôle': 279,
    'optimisation': 284,
    'ML': 290,
    'systèmes dynamiques': 237,

    # === PHYSIQUE (WNW, ~310°) ===
    'mécanique': 298,
    'mécanique analytique': 303,
    'fluides': 308,
    'thermo': 314,
    'mécanique stat': 318,
    'électromagn': 322,
    'optique': 326,
    'nucléaire': 330,
    'gravitation': 334,
    'relativité': 338,
    'quantique': 342,
    'QFT': 346,
    'particules': 350,

    # === COSMOS & SCIENCES (NNW, ~355°) ===
    'cosmologie': 354,
    'astronomie': 357,
    'chimie': 360,
    'biologie': 363,

    # === SCIENCES SOCIALES (N, ~368° = 8°) ===
    'économie': 368,
    'finance': 372,

    # === CATCH-ALL ===
    'mathématique': 90,  # generic math → combinatoire area
}


# ═══════════════════════════════════════════════════════════════
# 3. ESTIMATION DE PROFONDEUR POUR LES CONCEPTS MINÉS
# ═══════════════════════════════════════════════════════════════
# Les concepts OpenAlex ont un "level" (0-5).
# Level 0 = très général (Mathematics, Physics) → profondeur ~4
# Level 5 = très spécifique → profondeur ~10

# Base depth from OpenAlex level
LEVEL_TO_BASE_DEPTH = {
    0: 4,   # Mathematics, Physics → fondamental mais pas le plus basique
    1: 5,   # Algebra, Analysis → domaines de base
    2: 7,   # Linear algebra, Number theory → plus spécifique
    3: 8,   # Eigenvalue, Topology → concepts précis
    4: 9,   # Hilbert space, Manifold → très spécialisé
    5: 10,  # Ultra-spécialisé
}

# Keywords that DECREASE depth (more fundamental)
FUNDAMENTAL_KEYWORDS = {
    'number': -1, 'set': -1, 'function': -1, 'equation': -1,
    'space': -0.5, 'element': -1, 'operation': -1,
    'axiom': -2, 'definition': -2, 'property': -1,
    'theorem': 0, 'proof': 0,
    'integer': -1, 'real': -0.5, 'rational': -0.5,
    'addition': -2, 'multiplication': -1, 'subtraction': -2,
    'basic': -1, 'elementary': -1, 'fundamental': -1,
    'binary': -0.5, 'boolean': -1, 'logic': -1,
}

# Keywords that INCREASE depth (more specialized)
SPECIALIZED_KEYWORDS = {
    'quantum': 1, 'relativistic': 1, 'stochastic': 0.5,
    'topological': 0.5, 'differential': 0.5, 'algebraic': 0,
    'spectral': 0.5, 'harmonic': 0.5, 'ergodic': 1,
    'homolog': 1, 'cohomolog': 1, 'homotop': 1,
    'sheaf': 1.5, 'scheme': 1, 'manifold': 0.5,
    'neural': 1, 'machine learning': 1, 'deep learning': 1.5,
    'cryptograph': 1, 'blockchain': 1.5,
    'particle': 0.5, 'nuclear': 0.5,
    'astrophys': 1, 'cosmolog': 1,
    'biomathematic': 1, 'bioinformatic': 1.5,
    'financial': 1, 'econometric': 1,
}


def estimate_mined_depth(concept):
    """Estimate logical depth for a mined OpenAlex concept."""
    level = concept.get('level', 2)
    name = concept.get('name', '').lower()
    desc = (concept.get('description', '') or '').lower()
    text = name + ' ' + desc

    # Base depth from level
    depth = LEVEL_TO_BASE_DEPTH.get(level, 7)

    # Adjust based on keywords
    for kw, adj in FUNDAMENTAL_KEYWORDS.items():
        if kw in text:
            depth += adj

    for kw, adj in SPECIALIZED_KEYWORDS.items():
        if kw in text:
            depth += adj

    # Clamp to reasonable range
    return max(2, min(12, round(depth)))


def get_domain_angle(domain):
    """Get angle in degrees for a domain."""
    if domain in DOMAIN_ANGLE:
        return DOMAIN_ANGLE[domain]
    # Try partial match
    for key, angle in DOMAIN_ANGLE.items():
        if key in domain or domain in key:
            return angle
    return 90  # default to combinatoire area


def get_symbol_depth(symbol_name):
    """Get depth for an original symbol, or estimate."""
    if symbol_name in SYMBOL_DEPTH:
        return SYMBOL_DEPTH[symbol_name]
    # Default: depth 8 (moderately specialized)
    return 8


# ═══════════════════════════════════════════════════════════════
# 4. PLACEMENT — polaire → cartésien
# ═══════════════════════════════════════════════════════════════
# radius = f(depth), angle = f(domain)
# On normalise le rayon pour que depth 0 = 0 et depth 12 ≈ 1.8

MAX_DEPTH = 12
MAX_RADIUS = 1.8  # max radius in the viz coordinate system

def depth_to_radius(depth):
    """Convert logical depth to radial distance.

    Uses sqrt scaling so inner rings aren't too cramped:
    - depth 0 → 0
    - depth 1 → 0.47
    - depth 6 → 1.27
    - depth 12 → 1.8
    """
    if depth <= 0:
        return 0.0
    t = depth / MAX_DEPTH
    return MAX_RADIUS * math.sqrt(t)


def place_symbol(depth, domain, index=0, total_in_ring=1):
    """Place a symbol at (x, y) based on depth and domain.

    index/total_in_ring: when multiple symbols share same depth+domain,
    spread them slightly around the nominal angle.
    """
    radius = depth_to_radius(depth)
    base_angle_deg = get_domain_angle(domain)

    # Spread symbols that share the same depth+domain
    if total_in_ring > 1:
        spread = min(8.0, 15.0 / total_in_ring)  # degrees of spread
        offset = (index - (total_in_ring - 1) / 2) * spread
        base_angle_deg += offset

    angle_rad = math.radians(base_angle_deg)

    x = round(radius * math.cos(angle_rad), 3)
    y = round(radius * math.sin(angle_rad), 3)
    return x, y


def place_all_s0(original_symbols, mined_symbols, mined_concepts_data):
    """Place ALL S0 symbols by logical depth.

    Returns list of [name, x, y, isCentre, domain] arrays.
    """
    # Build a lookup from mined symbol name → concept data (for level info)
    mined_lookup = {}
    if mined_concepts_data:
        for c in mined_concepts_data:
            key = c['name'][:20]  # truncated name as used in strates_export_v2
            mined_lookup[key] = c

    # Collect all symbols with their depths
    all_syms = []

    # Original symbols
    for sym in original_symbols:
        name = sym['s']
        domain = sym['domain']
        depth = get_symbol_depth(name)
        all_syms.append({
            'name': name, 'domain': domain, 'depth': depth,
            'is_centre': name == '=',
        })

    # Mined symbols
    for sym in mined_symbols:
        name = sym['s']
        domain = sym['domain']
        concept = mined_lookup.get(name, {})
        depth = estimate_mined_depth(concept) if concept else 8
        all_syms.append({
            'name': name, 'domain': domain, 'depth': depth,
            'is_centre': False,
        })

    # Group by (depth, domain) for spreading
    from collections import defaultdict
    groups = defaultdict(list)
    for s in all_syms:
        key = (s['depth'], s['domain'])
        groups[key].append(s)

    # Place each symbol
    result = []
    for (depth, domain), syms in groups.items():
        for idx, s in enumerate(syms):
            if s['is_centre']:
                result.append([s['name'], 0, 0, 1, s['domain']])
            else:
                x, y = place_symbol(depth, domain, idx, len(syms))
                result.append([s['name'], x, y, 0, s['domain']])

    return result


if __name__ == '__main__':
    # Quick test
    print("=== Depth Map Test ===")
    for sym in ['=', '0', '+', '×', 'Σ', 'lim', '∫', 'ζ', 'ψ', 'CKM']:
        d = get_symbol_depth(sym)
        r = depth_to_radius(d)
        print(f"  {sym:10s} depth={d:2d}  radius={r:.3f}")

    print("\n=== Domain Angles ===")
    for domain in ['logique', 'arithmétique', 'algèbre', 'analyse',
                    'topologie', 'probabilités', 'complexité', 'quantique']:
        a = get_domain_angle(domain)
        print(f"  {domain:25s} angle={a}°")
