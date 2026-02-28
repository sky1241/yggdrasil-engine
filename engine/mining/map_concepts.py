"""
YGGDRASIL ENGINE — Phase 2 : PIVOT
Mapper 794 symboles → concept_ids OpenAlex (snapshot local 65K concepts)

Stratégie de mapping (4 passes) :
  1. SYMBOL_MAP : mapping manuel direct (symboles → concept_id connu)
  2. FROM_TO_EN : traduction from name FR → EN → exact match
  3. Word match : mots-clés extraits → scoring sur concepts
  4. Domain fallback : symbol.domain → concept parent

Sortie : data/openalex_map.json
"""
import gzip
import json
import os
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent.parent
STRATES_FILE = ROOT / "data" / "core" / "strates_export.json"
CONCEPTS_DIR = Path("E:/openalex/data/concepts")
OUTPUT_FILE = ROOT / "data" / "core" / "openalex_map.json"

# ═══════════════════════════════════════════════════════════════
# Pass 1 : SYMBOL_MAP — mapping direct symbole → search terms EN
# Pour les symboles dont le 'from' est trop cryptique en FR
# ═══════════════════════════════════════════════════════════════
SYMBOL_MAP = {
    # --- Arithmétique / Nombres ---
    "+": "addition",
    "−": "subtraction",
    "×": "multiplication",
    "÷": "division",
    "=": "equality (mathematics)",
    "≠": "inequality (mathematics)",
    "<": "inequality (mathematics)",
    ">": "inequality (mathematics)",
    "≤": "inequality (mathematics)",
    "≥": "inequality (mathematics)",
    "≈": "approximation",
    "≡": "congruence relation",
    "∝": "proportionality (mathematics)",
    "±": "plus-minus sign",
    "√": "square root",
    "∛": "cube root",
    "!": "factorial",
    "ⁿ": "exponentiation",
    "%": "percentage",
    "mod": "modular arithmetic",
    "⌊x⌋": "floor and ceiling functions",
    "⌈x⌉": "floor and ceiling functions",
    "|x|": "absolute value",
    "∞": "infinity",
    "ℕ": "natural number",
    "ℤ": "integer",
    "ℚ": "rational number",
    "ℝ": "real number",
    "ℂ": "complex number",
    "ℍ": "quaternion",
    "𝕆": "octonion",
    "ℙ": "prime number",
    "𝔽ₚ": "finite field",
    "π": "pi",
    "e": "e (mathematical constant)",
    "i": "imaginary unit",
    "φ": "golden ratio",
    "γₑ": "euler-mascheroni constant",
    "0": "0",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    # --- Physique constantes ---
    "c": "speed of light",
    "G": "gravitational constant",
    "ℏ": "planck constant",
    "h": "planck constant",
    "kB": "boltzmann constant",
    "NA": "avogadro constant",
    "R": "gas constant",
    "e⁻": "elementary charge",
    "μ₀": "permeability (electromagnetism)",
    "ε₀": "permittivity",
    "σ_SB": "stefan-boltzmann law",
    "α_fs": "fine-structure constant",
    "mₑ": "electron",
    "mₚ": "proton",
    "mₙ": "neutron",
    "H₀": "hubble's law",
    "T_CMB": "cosmic microwave background",
    # --- Ensembles ---
    "∈": "element (mathematics)",
    "∉": "element (mathematics)",
    "∅": "empty set",
    "∪": "union (set theory)",
    "∩": "intersection (set theory)",
    "⊂": "subset",
    "⊆": "subset",
    "⊃": "subset",
    "⊇": "subset",
    "∖": "complement (set theory)",
    "△": "symmetric difference",
    "𝒫(A)": "power set",
    "A×B": "cartesian product",
    "|A|": "cardinality",
    "ℵ₀": "aleph number",
    "ℵ₁": "aleph number",
    "𝔠": "cardinality of the continuum",
    "ℶ": "beth number",
    "Aᶜ": "complement (set theory)",
    "⊔": "coproduct",
    "κ": "inaccessible cardinal",
    "cf": "cofinality",
    "Card": "cardinal number",
    # --- Logique ---
    "∧": "logical conjunction",
    "∨": "logical disjunction",
    "¬": "negation",
    "→": "material conditional",
    "↔": "logical biconditional",
    "⊤": "tautology (logic)",
    "⊥₀": "contradiction",
    "⊕": "exclusive or",
    "⊨": "model theory",
    "⊩": "forcing (mathematics)",
    "∴": "logical consequence",
    "∵": "logical consequence",
    # --- Calcul / Analyse ---
    "Σ": "summation",
    "∑": "summation",
    "Π_prod": "multiplication",
    "∏": "multiplication",
    "lim": "limit (mathematics)",
    "d/dx": "derivative",
    "∂": "partial derivative",
    "∫": "integral",
    "∮": "line integral",
    "∬": "surface integral",
    "∭": "volume integral",
    "∇": "del",
    "Δ": "laplace operator",
    "f'": "derivative",
    "ẋ": "derivative",
    "dy/dx": "derivative",
    "∂²/∂x²": "partial derivative",
    "f∘g": "function composition",
    "ln": "natural logarithm",
    "log": "logarithm",
    "exp": "exponential function",
    "sin": "trigonometric functions",
    "cos": "trigonometric functions",
    "tan": "trigonometric functions",
    "arcsin": "inverse trigonometric functions",
    "arccos": "inverse trigonometric functions",
    "arctan": "inverse trigonometric functions",
    "sinh": "hyperbolic function",
    "cosh": "hyperbolic function",
    "tanh": "hyperbolic function",
    "sup": "infimum and supremum",
    "inf": "infimum and supremum",
    "max": "maxima and minima",
    "min": "maxima and minima",
    "ε": "limit (mathematics)",
    "δ": "limit (mathematics)",
    "O()": "big o notation",
    "o()": "big o notation",
    "Θ()": "big o notation",
    "~": "asymptotic analysis",
    # --- Algèbre ---
    "det": "determinant",
    "tr": "trace (linear algebra)",
    "rank": "rank (linear algebra)",
    "dim": "dimension",
    "ker": "kernel (algebra)",
    "im": "image (mathematics)",
    "span": "linear span",
    "⊕_alg": "direct sum",
    "⊗": "tensor product",
    "×_grp": "direct product",
    "Aut": "automorphism",
    "Hom": "homomorphism",
    "End": "endomorphism",
    "Iso": "isomorphism",
    "[G:H]": "index of a subgroup",
    "|G|": "order (group theory)",
    "⋊": "semidirect product",
    "≅": "isomorphism",
    "⊲": "normal subgroup",
    "GL": "general linear group",
    "SL": "special linear group",
    "O(n)": "orthogonal group",
    "SO(n)": "orthogonal group",
    "SU(n)": "special unitary group",
    "U(n)": "unitary group",
    "Sp(n)": "symplectic group",
    "Sₙ": "symmetric group",
    "Aₙ": "alternating group",
    "ℤₙ": "cyclic group",
    "Dₙ": "dihedral group",
    "𝔤": "lie algebra",
    "Ad": "adjoint representation",
    "Gal": "galois group",
    "[K:F]": "degree of a field extension",
    "Frac": "field of fractions",
    "char": "characteristic (algebra)",
    "F[x]": "polynomial ring",
    "I": "ideal (ring theory)",
    "R/I": "quotient ring",
    "⟨a⟩": "generating set of a group",
    "Spec": "spectrum of a ring",
    "⊕_mod": "direct sum",
    "Ann": "annihilator (ring theory)",
    "Nil": "nilpotent",
    "Jac": "jacobson radical",
    "Max": "maximal ideal",
    "⊗_R": "tensor product",
    "Tor": "tor functor",
    "Ext": "ext functor",
    "ℤ[x]": "polynomial ring",
    "F_q": "finite field",
    # --- Topologie ---
    "τ": "topological space",
    "𝒪": "open set",
    "int": "interior (topology)",
    "cl": "closure (topology)",
    "∂_top": "boundary (topology)",
    "𝕊ⁿ": "n-sphere",
    "𝕋ⁿ": "torus",
    "ℝPⁿ": "real projective space",
    "ℂPⁿ": "complex projective space",
    "K(π,n)": "eilenberg-maclane space",
    "π₁": "fundamental group",
    "πₙ": "homotopy group",
    "Hₙ": "homology (mathematics)",
    "Hⁿ": "cohomology",
    "χ_euler": "euler characteristic",
    "β_betti": "betti number",
    "≃": "homotopy",
    "↪": "embedding",
    "↠": "surjection",
    # --- Géom diff ---
    "g_metric": "riemannian manifold",
    "Γⁱⱼₖ": "christoffel symbols",
    "R_ijkl": "riemann curvature tensor",
    "Ric": "ricci curvature",
    "R_scalar": "scalar curvature",
    "K_gauss": "gaussian curvature",
    "κ_curv": "curvature",
    "ω_form": "differential form",
    "dω": "exterior derivative",
    "∧_wedge": "exterior algebra",
    "★_hodge": "hodge star operator",
    "∇_conn": "connection (mathematics)",
    "TM": "tangent bundle",
    "T*M": "cotangent bundle",
    "χ(M)": "euler characteristic",
    "Vol": "volume form",
    "Exp": "exponential map (riemannian geometry)",
    "geod": "geodesic",
    "Hol": "holonomy",
    "Ω_curv": "curvature form",
    "J_cpx": "almost complex manifold",
    "Kähler": "kahler manifold",
    "ω_symp": "symplectic manifold",
    # --- Catégories ---
    "Obj": "category (mathematics)",
    "Mor": "morphism",
    "Func": "functor",
    "Nat": "natural transformation",
    "lim_cat": "limit (category theory)",
    "colim": "colimit",
    "Adj": "adjoint functors",
    "Yoneda": "yoneda lemma",
    "Set": "category of sets",
    "Grp": "category theory",
    "Top_cat": "category of topological spaces",
    "Ab": "abelian category",
    "Vect_K": "category of modules",
    "Ring_cat": "category theory",
    "Δ_simp": "simplicial set",
    "∞-Cat": "infinity category",
    "Kan": "kan extension",
    # --- Probabilités ---
    "P()": "probability",
    "E[]": "expected value",
    "Var": "variance",
    "σ²": "variance",
    "Cov": "covariance",
    "X": "random variable",
    "μ_distr": "probability distribution",
    "F_cdf": "cumulative distribution function",
    "f_pdf": "probability density function",
    "N(μ,σ²)": "normal distribution",
    "Exp(λ)": "exponential distribution",
    "Poi(λ)": "poisson distribution",
    "Bin(n,p)": "binomial distribution",
    "χ²": "chi-squared distribution",
    "t_student": "student's t-distribution",
    "B(t)": "brownian motion",
    "W(t)": "wiener process",
    "Eₓ": "expected value",
    "𝔼": "expected value",
    "ℙ_prob": "probability",
    "Mₜ": "martingale (probability theory)",
    "τ_stop": "stopping time",
    "σ-alg": "sigma-algebra",
    "ℱₜ": "filtration (probability theory)",
    "⊥_indep": "independence (probability theory)",
    # --- Mécanique / Physique ---
    "F": "force",
    "F=ma": "newton's laws of motion",
    "p=mv": "momentum",
    "E_k": "kinetic energy",
    "E_p": "potential energy",
    "L_lagr": "lagrangian mechanics",
    "H_hamilt": "hamiltonian mechanics",
    "S_action": "action (physics)",
    "{f,g}": "poisson bracket",
    "q": "generalized coordinates",
    "p_gen": "generalized coordinates",
    "ω_angular": "angular velocity",
    "τ_torque": "torque",
    "I_inertia": "moment of inertia",
    "J_angular": "angular momentum",
    # --- Thermo ---
    "S_entropy": "entropy",
    "T_temp": "temperature",
    "U_internal": "internal energy",
    "W_work": "work (thermodynamics)",
    "Q_heat": "heat",
    "dU": "first law of thermodynamics",
    "ΔS≥0": "second law of thermodynamics",
    "F_free": "helmholtz free energy",
    "G_gibbs": "gibbs free energy",
    "H_enthalpy": "enthalpy",
    "μ_chem": "chemical potential",
    "Z_partition": "partition function (statistical mechanics)",
    "β_thermo": "thermodynamic beta",
    # --- Quantique ---
    "|ψ⟩": "quantum state",
    "⟨ψ|": "bra-ket notation",
    "⟨ψ|φ⟩": "bra-ket notation",
    "Ĥ": "hamiltonian (quantum mechanics)",
    "Ĥ|ψ⟩=E|ψ⟩": "schrodinger equation",
    "iℏ∂ₜ": "schrodinger equation",
    "[Â,B̂]": "commutator",
    "σ_spin": "spin (physics)",
    "ΔxΔp≥ℏ/2": "uncertainty principle",
    "ρ̂": "density matrix",
    "Tr": "trace (linear algebra)",
    "U_gate": "quantum logic gate",
    "|0⟩+|1⟩": "qubit",
    "|00⟩+|11⟩": "quantum entanglement",
    "CNOT": "controlled not gate",
    "H_gate": "hadamard transform",
    "T_gate": "quantum logic gate",
    "Shor": "shor's algorithm",
    "Grover": "grover's algorithm",
    "QFT_gate": "quantum fourier transform",
    "VQE": "variational method (quantum mechanics)",
    "QAOA": "quantum approximate optimization algorithm",
    "BQP": "bqp",
    "QMA": "qma",
    "PostBQP": "postselection",
    # --- Complexité ---
    "P_class": "p (complexity)",
    "NP_class": "np (complexity)",
    "coNP": "co-np",
    "SAT": "boolean satisfiability problem",
    "3-SAT": "boolean satisfiability problem",
    "NP-C": "np-completeness",
    "NP-H": "np-hardness",
    "CLIQUE": "clique problem",
    "VERTEX": "vertex cover",
    "TSP": "travelling salesman problem",
    "P≟NP": "p versus np problem",
    "L_space": "l (complexity)",
    "NL_space": "nl (complexity)",
    "PSPACE": "pspace",
    "NC": "nc (complexity)",
    "AC": "circuit complexity",
    "TC": "circuit complexity",
    "BPP": "bpp (complexity)",
    "RP": "rp (complexity)",
    "coRP": "rp (complexity)",
    "ZPP": "zpp (complexity)",
    # --- Calculabilité ---
    "∃": "existential quantification",
    "K": "halting problem",
    "φₑ": "computable function",
    "↓": "halting problem",
    "↑": "halting problem",
    "∀": "universal quantification",
    "∃∀": "arithmetical hierarchy",
    "TOT": "computable function",
    "FIN": "computability theory",
    "∅'": "turing jump",
    "Wₑ": "computably enumerable set",
    "≤_T": "turing reduction",
    "≤_m": "many-one reduction",
    "≡_T": "turing degree",
    "0'": "turing jump",
    "≤_tt": "truth-table reduction",
    "RE": "recursively enumerable set",
    "coRE": "recursively enumerable set",
    "μ": "mu operator",
    "Post": "arithmetical hierarchy",
    "Lim": "limit computable",
    "Low": "low (computability)",
    "High": "turing degree",
    "INF": "computability theory",
    "Σ⁰₂": "arithmetical hierarchy",
    "Π⁰₂": "arithmetical hierarchy",
    # --- S3 named theorems (search by theorem name in English) ---
    "FermatWiles": "fermat's last theorem",
    "Milnor_K": "milnor k-theory",
    "BlochKato": "norm residue isomorphism theorem",
    "SatoTate": "sato-tate conjecture",
    "KazhLusz": "kazhdan-lusztig polynomial",
    "KadSinger": "kadison-singer problem",
    "VirtHaken": "haken manifold",
    "KakeyaFin": "kakeya set",
    "Onsager_c": "onsager reciprocal relations",
    "Poinc3": "poincare conjecture",
    "Geomtrz": "geometrization conjecture",
    "hCobord": "h-cobordism",
    "Freed4": "topological manifold",
    "SmithConj": "smith conjecture",
    "ExoticS7": "exotic sphere",
    "Surgery": "surgery theory",
    "Mordell": "faltings's theorem",
    "WeilConj": "weil conjectures",
    "CatalanM": "catalan's conjecture",
    "GoldWeak": "goldbach's weak conjecture",
    "BddGaps": "prime gap",
    "GrossZag": "gross-zagier formula",
    "HerbRibet": "herbrand's theorem (proof theory)",
    "IwasMain": "iwasawa theory",
    "SerreMod": "serre's modularity conjecture",
    "LaffFnF": "langlands program",
    "CFSG": "classification of finite simple groups",
    "Moonshine": "monstrous moonshine",
    "QuilSusl": "quillen-suslin theorem",
    "Bieberbach": "de branges's theorem",
    "CarlesonL2": "carleson's theorem",
    "KatoSqrt": "kato's conjecture",
    "CoronaTh": "corona theorem",
    "CalabiYau": "calabi-yau manifold",
    "PosMass": "positive mass theorem",
    "Kepler": "kepler conjecture",
    "Willmore": "willmore conjecture",
    "AtiyahSing": "atiyah-singer index theorem",
    "FourColor": "four color theorem",
    "RobSeym": "robertson-seymour theorem",
    "GreenTao": "green-tao theorem",
    "DensHJ": "hales-jewett theorem",
    "Kneser": "kneser's theorem",
    "SLE_thm": "schramm-loewner evolution",
    "ParisHarr": "paris-harrington theorem",
    "DPRM": "diophantine set",
    "Hironaka": "resolution of singularities",
    "FundLemma": "fundamental lemma (langlands program)",
    "Szemer": "szemeredi's theorem",
    "RothAP": "roth's theorem on arithmetic progressions",
    "MostowRig": "mostow rigidity theorem",
    "MargSup": "margulis superrigidity theorem",
    "Oppenh": "oppenheim conjecture",
    "Ratner": "ratner's theorems",
    "Tameness": "tameness conjecture",
    "EndLam": "ending lamination theorem",
    "DiffSph": "sphere theorem",
    "FeitThomp": "feit-thompson theorem",
    "Vinogr3P": "vinogradov's theorem",
    "PNT": "prime number theorem",
    "Waring": "waring's problem",
    "QRecip": "quadratic reciprocity",
    "Dirichlet": "dirichlet's theorem on arithmetic progressions",
    "Viaz8": "sphere packing",
    "Viaz24": "sphere packing",
    "DblBubble": "double bubble conjecture",
    "Einstein": "aperiodic tiling",
    "BrauerH0": "brauer's theorem",
    "Nagata": "nagata's conjecture",
    "ErdDiscrep": "erdos discrepancy problem",
    "GuthKatz": "erdos distinct distances problem",
    "RamseyExp": "ramsey theory",
    "BGS": "oracle machine",
    "NatProof": "natural proof",
    "Algebriz": "algebrization",
    "ImmSzel": "immerman-szelepcsenyi theorem",
    "SipLaut": "bpp (complexity)",
    "Perm#P": "permanent (mathematics)",
    "ImpWig": "derandomization",
    "ImpPad": "exponential time hypothesis",
    "BirkErg": "ergodic theory",
    "CLT": "central limit theorem",
    "SLLN": "law of large numbers",
    "Donsker": "donsker's theorem",
    "LDP": "large deviations theory",
    "OrnIsm": "ornstein isomorphism theorem",
    "DeGNM": "de giorgi-nash-moser",
    "NashEmb": "nash embedding theorem",
    "KAM": "kolmogorov-arnold-moser theorem",
    "deRham": "de rham cohomology",
    "BottPer": "bott periodicity theorem",
    "Uniformiz": "uniformization theorem",
    "GrotRR": "grothendieck-riemann-roch theorem",
    "ClassFT": "class field theory",
    "GodelInc": "godel's incompleteness theorems",
    "NoetherSy": "noether's theorem",
    "Shannon2": "noisy-channel coding theorem",
    "MIP*RE": "mip*",
    "WillACC": "circuit complexity",
    "RazMono": "circuit complexity",
    "RazSmol": "circuit complexity",
    "HasAC0": "circuit complexity",
    "BorelDet": "borel determinacy theorem",
    "CohenInd": "forcing (mathematics)",
    "BuchiMSO": "buchi automaton",
    "MyhNer": "myhill-nerode theorem",
    "RabinS2S": "rabin automaton",
    "DoobMart": "doob's martingale convergence theorems",
    "BaireCat": "baire category theorem",
    "BanOpen": "open mapping theorem (functional analysis)",
    # --- S4+ ---
    "AH": "arithmetical hierarchy",
    "∪ₙ": "arithmetical hierarchy",
    "ω_ord": "ordinal number",
    "Th(ℕ)": "decidability (logic)",
    "∅⁽ω⁾": "turing jump",
    "QIP": "quantum complexity theory",
    "EXPTIME": "exptime",
    "NEXP": "nexptime",
    "EXPSPACE": "expspace",
    "AP": "alternation (complexity)",
    "TQBF": "true quantified boolean formula",
    "IP_eq": "ip (complexity)",
    "2-EXP": "2-exptime",
    "ELEM": "elementary function",
    "E": "exponential time",
    "NE": "nexptime",
    "Tarski": "tarski's undefinability theorem",
    "ε₀_ord": "epsilon numbers (mathematics)",
    "ω₁ᶜᵏ": "church-kleene ordinal",
    "∅⁽α⁾": "turing jump",
    "Δ¹₁": "analytical hierarchy",
    "Σ¹₁": "analytical hierarchy",
    "Π¹₁": "analytical hierarchy",
    "O_Kl": "kleene's o",
    "HYP": "hyperarithmetical theory",
    "WO": "well-order",
    "Σ¹ₙ": "projective hierarchy",
    "Π¹ₙ": "projective hierarchy",
    "Det": "determinacy",
    "²E": "hyperarithmetical theory",
    "KP": "kripke-platek set theory",
    "Lα": "constructible universe",
    "Borel": "borel set",
    "AD": "axiom of determinacy",
    "Wadge": "wadge hierarchy",
    "Spect": "hyperarithmetical theory",
    "Σ⁰_α": "borel hierarchy",
    # --- S6 ---
    "Ω_Ch": "chaitin's constant",
    "BB(n)": "busy beaver",
    "⊥": "undecidable problem",
    "G_God": "godel's incompleteness theorems",
    "⊢": "formal proof",
    "⊬": "independence (mathematical logic)",
    "K(x)": "kolmogorov complexity",
    "HALT": "halting problem",
    "H10": "hilbert's tenth problem",
    "Σ(n)": "busy beaver",
    "WP_grp": "word problem for groups",
    "PCP": "post correspondence problem",
    "Rice": "rice's theorem",
    "ETM": "undecidable problem",
    "EQTM": "undecidable problem",
    "S(n)": "busy beaver",
    "Entsch": "entscheidungsproblem",
    "Diag": "cantor's diagonal argument",
    "Kolm": "kolmogorov complexity",
    "Wang": "wang tile",
    # --- Misc ---
    "Σ⁰ₙ": "arithmetical hierarchy",
    "Π⁰ₙ": "arithmetical hierarchy",
    "Δ⁰ₙ": "arithmetical hierarchy",
    "∅⁽ⁿ⁾": "turing jump",
    "ΣₖP": "polynomial hierarchy",
    "ΠₖP": "polynomial hierarchy",
    "ΔₖP": "polynomial hierarchy",
    "PH": "polynomial hierarchy",
    "#P": "sharp-p",
    "MA": "ma (complexity)",
    "AM": "arthur-merlin protocol",
    "PP": "pp (complexity)",
    "⊕P": "parity p",
    "Σ₂P": "polynomial hierarchy",
    "Π₂P": "polynomial hierarchy",
    "Toda": "toda's theorem",
    "#SAT": "sharp-sat",
    "GapP": "gap theorem",
    "C₌P": "counting complexity",
    "COF": "computability theory",
    "REC": "computability theory",
}

# ═══════════════════════════════════════════════════════════════
# Pass 2 : FROM_TO_EN — traduction termes FR → EN
# ═══════════════════════════════════════════════════════════════
FR_TO_EN = {
    "addition": "addition",
    "soustraction": "subtraction",
    "multiplication": "multiplication",
    "division": "division",
    "egalite": "equality (mathematics)",
    "inegalite": "inequality (mathematics)",
    "inferieur": "inequality (mathematics)",
    "superieur": "inequality (mathematics)",
    "approximativement": "approximation",
    "identique": "congruence relation",
    "congruence": "congruence relation",
    "proportionnel": "proportionality (mathematics)",
    "racine": "square root",
    "factorielle": "factorial",
    "puissance": "exponentiation",
    "exposant": "exponentiation",
    "pourcentage": "percentage",
    "modulo": "modular arithmetic",
    "partie entiere": "floor and ceiling functions",
    "valeur absolue": "absolute value",
    "infini": "infinity",
    "nombres naturels": "natural number",
    "entiers": "integer",
    "rationnels": "rational number",
    "reels": "real number",
    "complexes": "complex number",
    "quaternions": "quaternion",
    "octonions": "octonion",
    "nombres premiers": "prime number",
    "corps fini": "finite field",
    "nombre d'or": "golden ratio",
    "unite imaginaire": "imaginary unit",
    # Ensembles
    "appartenance": "element (mathematics)",
    "ensemble vide": "empty set",
    "union": "union (set theory)",
    "intersection": "intersection (set theory)",
    "inclusion": "subset",
    "difference": "complement (set theory)",
    "ensemble des parties": "power set",
    "produit cartesien": "cartesian product",
    "cardinal": "cardinality",
    "denombrable": "countable set",
    "complement": "complement (set theory)",
    "union disjointe": "coproduct",
    "cofinalite": "cofinality",
    # Logique
    "conjonction": "logical conjunction",
    "disjonction": "logical disjunction",
    "negation": "negation",
    "implication": "material conditional",
    "tautologie": "tautology (logic)",
    "contradiction": "contradiction",
    "satisfaction": "model theory",
    "forcing": "forcing (mathematics)",
    # Analyse
    "somme": "summation",
    "produit": "product (mathematics)",
    "limite": "limit (mathematics)",
    "derivee": "derivative",
    "derivee partielle": "partial derivative",
    "integrale": "integral",
    "gradient": "gradient",
    "divergence": "divergence",
    "rotationnel": "curl (mathematics)",
    "laplacien": "laplace operator",
    "composition": "function composition",
    "logarithme": "logarithm",
    "exponentielle": "exponential function",
    "convergence": "convergent series",
    "serie": "series (mathematics)",
    "serie entiere": "power series",
    "fourier": "fourier series",
    "taylor": "taylor series",
    "distribution": "distribution (mathematics)",
    "convolution": "convolution",
    "noyau": "kernel (algebra)",
    "mesure": "measure (mathematics)",
    "integrale de lebesgue": "lebesgue integration",
    "tribu": "sigma-algebra",
    "espace lp": "lp space",
    "espace de hilbert": "hilbert space",
    "espace de banach": "banach space",
    "espace de sobolev": "sobolev space",
    "operateur": "operator (mathematics)",
    "spectre": "spectral theory",
    "adjoint": "adjoint operator",
    "compact": "compact operator",
    "trace": "trace (linear algebra)",
    "determinant": "determinant",
    "rang": "rank (linear algebra)",
    "dimension": "dimension",
    "norme": "norm (mathematics)",
    "produit scalaire": "inner product space",
    "base orthonormee": "orthonormal basis",
    "valeur propre": "eigenvalues and eigenvectors",
    "vecteur propre": "eigenvalues and eigenvectors",
    "diagonalisation": "diagonalizable matrix",
    "matrice": "matrix (mathematics)",
    "transposee": "transpose",
    "inverse": "invertible matrix",
    # Topologie
    "espace topologique": "topological space",
    "ouvert": "open set",
    "interieur": "interior (topology)",
    "adherence": "closure (topology)",
    "frontiere": "boundary (topology)",
    "sphere": "n-sphere",
    "tore": "torus",
    "groupe fondamental": "fundamental group",
    "homologie": "homology (mathematics)",
    "cohomologie": "cohomology",
    "homotopie": "homotopy",
    # Physique
    "vitesse lumiere": "speed of light",
    "constante gravitationnelle": "gravitational constant",
    "planck": "planck constant",
    "boltzmann": "boltzmann constant",
    "avogadro": "avogadro constant",
    "gaz parfaits": "gas constant",
    "charge elementaire": "elementary charge",
    "permeabilite": "permeability (electromagnetism)",
    "permittivite": "permittivity",
    "structure fine": "fine-structure constant",
    "electron": "electron",
    "proton": "proton",
    "neutron": "neutron",
    "hubble": "hubble's law",
    "force": "force",
    "energie cinetique": "kinetic energy",
    "energie potentielle": "potential energy",
    "lagrangien": "lagrangian mechanics",
    "hamiltonien": "hamiltonian mechanics",
    "entropie": "entropy",
    "temperature": "temperature",
    "energie interne": "internal energy",
    "enthalpie": "enthalpy",
    "potentiel chimique": "chemical potential",
    "fonction de partition": "partition function (statistical mechanics)",
    "etat quantique": "quantum state",
    "equation schrodinger": "schrodinger equation",
    "commutateur": "commutator",
    "spin": "spin (physics)",
    "incertitude heisenberg": "uncertainty principle",
    "matrice densite": "density matrix",
    "qubit": "qubit",
    "intrication": "quantum entanglement",
    # Calculabilité
    "quantificateur existentiel": "existential quantification",
    "quantificateur universel": "universal quantification",
    "fonction partielle": "computable function",
    "converge": "halting problem",
    "diverge": "halting problem",
    "alternance": "arithmetical hierarchy",
    "saut turing": "turing jump",
    "enumerable": "recursively enumerable set",
    "recursif": "computable function",
    "reduction": "many-one reduction",
    "degre turing": "turing degree",
    "hierarchie": "arithmetical hierarchy",
    "indecidable": "undecidable problem",
    "incompletude": "godel's incompleteness theorems",
    "arret": "halting problem",
    # Variables
    "variable aleatoire": "random variable",
    "esperance": "expected value",
    "variance": "variance",
    "covariance": "covariance",
    "mouvement brownien": "brownian motion",
    "processus wiener": "wiener process",
    "martingale": "martingale (probability theory)",
    "temps arret": "stopping time",
    "independance": "independence (probability theory)",
}

# ═══════════════════════════════════════════════════════════════
# Domain → OpenAlex EN concept search terms
# ═══════════════════════════════════════════════════════════════
DOMAIN_TO_SEARCH = {
    "arithmétique":          ["arithmetic", "number theory", "elementary algebra"],
    "algèbre":               ["algebra", "abstract algebra"],
    "algèbre lin":           ["linear algebra"],
    "analyse":               ["mathematical analysis", "calculus"],
    "analyse fonctionnelle": ["functional analysis"],
    "géométrie":             ["geometry"],
    "géom diff":             ["differential geometry"],
    "géom algébrique":       ["algebraic geometry"],
    "topologie":             ["topology"],
    "logique":               ["mathematical logic", "logic"],
    "ensembles":             ["set theory"],
    "calculabilité":         ["computability theory", "theory of computation"],
    "complexité":            ["computational complexity theory", "algorithm"],
    "combinatoire":          ["combinatorics"],
    "probabilités":          ["probability theory", "probability"],
    "statistiques":          ["statistics"],
    "nb théorie":            ["number theory"],
    "nb premiers":           ["prime number"],
    "nombres":               ["number theory"],
    "ordinaux":              ["ordinal number", "set theory"],
    "descriptive":           ["descriptive set theory", "set theory"],
    "catégories":            ["category theory"],
    "stochastique":          ["stochastic process"],
    "mesure":                ["measure (mathematics)", "measure theory"],
    "trigonométrie":         ["trigonometry"],
    "complexes":             ["complex analysis"],
    "optimisation":          ["mathematical optimization"],
    "quantique":             ["quantum mechanics", "quantum physics"],
    "mécanique":             ["classical mechanics", "mechanics"],
    "mécanique analytique":  ["analytical mechanics", "lagrangian mechanics"],
    "mécanique stat":        ["statistical mechanics"],
    "thermo":                ["thermodynamics"],
    "fluides":               ["fluid mechanics", "fluid dynamics"],
    "relativité":            ["general relativity", "special relativity"],
    "cosmologie":            ["cosmology", "physical cosmology"],
    "gravitation":           ["gravitation", "gravity"],
    "particules":            ["particle physics"],
    "nucléaire":             ["nuclear physics"],
    "QFT":                   ["quantum field theory"],
    "électromagn":           ["electromagnetism", "classical electromagnetism"],
    "optique":               ["optics"],
    "EDP":                   ["partial differential equation"],
    "signal":                ["signal processing", "information theory"],
    "information":           ["information theory", "entropy"],
    "crypto":                ["cryptography"],
    "ML":                    ["machine learning", "artificial intelligence"],
    "automates":             ["automata theory", "formal language"],
    "biologie":              ["mathematical biology", "biology"],
    "chimie":                ["chemistry", "chemical kinetics"],
    "économie":              ["mathematical economics", "economics"],
    "finance":               ["mathematical finance", "financial economics"],
    "contrôle":              ["control theory", "optimal control"],
    "astronomie":            ["astronomy", "astrophysics"],
}


def load_concepts():
    """Load all 65K concepts from snapshot."""
    concepts = []
    for root, dirs, files in os.walk(CONCEPTS_DIR):
        for f in files:
            if f.endswith('.gz'):
                path = os.path.join(root, f)
                with gzip.open(path, 'rt', encoding='utf-8') as gz:
                    for line in gz:
                        line = line.strip()
                        if line:
                            concepts.append(json.loads(line))
    return concepts


def build_index(concepts):
    """Build multiple indexes for fast lookup."""
    by_name = {}       # lowercase name -> concept
    by_word = defaultdict(set)  # word -> set of concept IDs
    by_id = {}         # ID -> concept

    for c in concepts:
        cid = c['id']
        name = c.get('display_name', '')
        by_id[cid] = c
        by_name[name.lower()] = c

        words = re.findall(r'[a-zA-Z]{3,}', name.lower())
        for w in words:
            by_word[w].add(cid)

    return by_name, by_word, by_id


def normalize(text):
    """Normalize text: lowercase, remove accents, strip punctuation."""
    import unicodedata
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def search_concept(query, by_name, by_word, by_id, max_results=5):
    """Search for a concept by query string. Returns list of (concept, score)."""
    query_lower = query.lower().strip()

    # Pass 1: Exact match
    if query_lower in by_name:
        return [(by_name[query_lower], 100)]

    # Pass 2: Substring match (require minimum query length to avoid noise)
    substring_matches = []
    if len(query_lower) >= 4:
        for name, c in by_name.items():
            if query_lower in name:
                score = 90 if name.startswith(query_lower) else 80
                substring_matches.append((c, score))
            elif len(name) >= 4 and name in query_lower:
                substring_matches.append((c, 60))

    if substring_matches:
        substring_matches.sort(key=lambda x: (-x[1], -x[0].get('works_count', 0)))
        return substring_matches[:max_results]

    # Pass 3: Word overlap
    query_words = set(re.findall(r'[a-zA-Z]{3,}', query_lower))
    if not query_words:
        return []

    candidate_ids = set()
    for w in query_words:
        candidate_ids |= by_word.get(w, set())

    scored = []
    for cid in candidate_ids:
        c = by_id[cid]
        name_words = set(re.findall(r'[a-zA-Z]{3,}', c['display_name'].lower()))
        overlap = query_words & name_words
        if overlap:
            score = (len(overlap) / max(len(query_words), len(name_words))) * 50
            # Boost if all query words match
            if query_words <= name_words:
                score = 70
            if score > 10:
                scored.append((c, score))

    scored.sort(key=lambda x: (-x[1], -x[0].get('works_count', 0)))
    return scored[:max_results]


def map_symbol(symbol, strate_id, by_name, by_word, by_id, domain_concepts):
    """Map a single symbol to OpenAlex concept(s)."""
    sym_name = symbol['s']
    from_name = symbol.get('from', '')
    domain = symbol.get('domain', '')

    result = {
        'symbol': sym_name,
        'from': from_name,
        'domain': domain,
        'strate': strate_id,
        'matches': [],
        'domain_concept': None,
        'best_match': None,
        'confidence': 0,
    }

    # --- Pass 1: Direct SYMBOL_MAP ---
    if sym_name in SYMBOL_MAP:
        en_term = SYMBOL_MAP[sym_name]
        matches = search_concept(en_term, by_name, by_word, by_id)
        for concept, score in matches:
            result['matches'].append({
                'id': concept['id'],
                'name': concept['display_name'],
                'level': concept.get('level', -1),
                'works_count': concept.get('works_count', 0),
                'score': round(min(score + 10, 100), 1),  # Boost for direct map
                'method': 'symbol_map',
            })

    # --- Pass 2: FR_TO_EN translation of 'from' name ---
    if not result['matches']:
        from_normalized = normalize(from_name)
        # Try to find in FR_TO_EN dict
        for fr_key, en_val in FR_TO_EN.items():
            if fr_key in from_normalized:
                matches = search_concept(en_val, by_name, by_word, by_id)
                for concept, score in matches[:2]:
                    result['matches'].append({
                        'id': concept['id'],
                        'name': concept['display_name'],
                        'level': concept.get('level', -1),
                        'works_count': concept.get('works_count', 0),
                        'score': round(score * 0.9, 1),
                        'method': 'fr_to_en',
                    })
                if result['matches']:
                    break

    # --- Pass 3: Direct search with 'from' name (works if name has English terms) ---
    if not result['matches']:
        # Extract multi-word English phrases from 'from' field (min 4 chars)
        en_words = re.findall(r'[A-Z][a-z]{3,}(?:\s+[A-Za-z]{3,})*', from_name)
        for term in en_words:
            if len(term) < 4:
                continue
            matches = search_concept(term.lower(), by_name, by_word, by_id)
            for concept, score in matches[:2]:
                # Reject obviously bad matches (generic concepts with low relevance)
                cname = concept['display_name'].lower()
                if cname in ('ion', 'p', 'ant', 'art', 'ray', 'mass', 'harm',
                             'normal', 'diagram', 'product', 'space', 'set',
                             'function', 'theorem', 'number'):
                    continue
                result['matches'].append({
                    'id': concept['id'],
                    'name': concept['display_name'],
                    'level': concept.get('level', -1),
                    'works_count': concept.get('works_count', 0),
                    'score': round(score * 0.8, 1),
                    'method': 'from_english',
                })
            if result['matches']:
                break

    # --- Pass 4: Word search on full 'from' field (only for long names) ---
    if not result['matches'] and len(from_name) >= 10:
        matches = search_concept(from_name, by_name, by_word, by_id)
        for concept, score in matches[:3]:
            # Only accept decent word-overlap scores
            if score < 25:
                continue
            cname = concept['display_name'].lower()
            # Reject generic garbage matches
            if len(cname) < 4 or cname in ('ion', 'p', 'ant', 'art', 'ray'):
                continue
            result['matches'].append({
                'id': concept['id'],
                'name': concept['display_name'],
                'level': concept.get('level', -1),
                'works_count': concept.get('works_count', 0),
                'score': round(score * 0.7, 1),
                'method': 'word_search',
            })

    # --- Domain fallback ---
    if domain in domain_concepts:
        result['domain_concept'] = domain_concepts[domain]

    # --- Pick best match ---
    # Deduplicate by concept ID
    seen_ids = set()
    unique_matches = []
    for m in result['matches']:
        if m['id'] not in seen_ids:
            seen_ids.add(m['id'])
            unique_matches.append(m)
    result['matches'] = unique_matches

    if result['matches']:
        best = max(result['matches'], key=lambda m: (m['score'], m['works_count']))
        result['best_match'] = best
        result['confidence'] = best['score']
    elif result['domain_concept']:
        result['best_match'] = result['domain_concept'][0]
        result['confidence'] = 25

    return result


def run():
    print("=" * 60)
    print("YGGDRASIL — Phase 2 : PIVOT — Mapping 794 symboles")
    print("=" * 60)

    # Load concepts
    print("\n[1/4] Loading 65K OpenAlex concepts from snapshot...")
    concepts = load_concepts()
    print(f"  -> {len(concepts)} concepts loaded")

    # Build index
    print("\n[2/4] Building search index...")
    by_name, by_word, by_id = build_index(concepts)
    print(f"  -> {len(by_name)} names, {len(by_word)} word keys")

    # Pre-resolve domain concepts
    print("\n[3/4] Resolving domain concepts...")
    domain_concepts = {}
    for domain, search_terms in DOMAIN_TO_SEARCH.items():
        matches = []
        for term in search_terms:
            results = search_concept(term, by_name, by_word, by_id)
            for c, score in results:
                matches.append({
                    'id': c['id'],
                    'name': c['display_name'],
                    'level': c.get('level', -1),
                    'works_count': c.get('works_count', 0),
                    'score': round(score, 1),
                })
        if matches:
            seen = set()
            unique = []
            for m in matches:
                if m['id'] not in seen:
                    seen.add(m['id'])
                    unique.append(m)
            domain_concepts[domain] = unique
            print(f"  {domain:30s} -> {unique[0]['name']} ({unique[0]['works_count']:,} works)")
        else:
            print(f"  {domain:30s} -> *** NO MATCH ***")

    # Load symbols
    print("\n[4/4] Mapping symbols...")
    with open(STRATES_FILE, encoding='utf-8') as f:
        strates_data = json.load(f)

    all_mappings = []
    stats = {'total': 0, 'high': 0, 'medium': 0, 'low': 0, 'domain_only': 0, 'no_match': 0}
    by_strate = defaultdict(lambda: {'total': 0, 'matched': 0})
    by_method = defaultdict(int)

    for st in strates_data['strates']:
        strate_id = st['id']
        for sym in st['symbols']:
            mapping = map_symbol(sym, strate_id, by_name, by_word, by_id, domain_concepts)
            all_mappings.append(mapping)
            stats['total'] += 1
            by_strate[strate_id]['total'] += 1

            conf = mapping['confidence']
            if conf >= 80:
                stats['high'] += 1
                by_strate[strate_id]['matched'] += 1
            elif conf >= 50:
                stats['medium'] += 1
                by_strate[strate_id]['matched'] += 1
            elif conf >= 25:
                stats['low'] += 1
            else:
                stats['no_match'] += 1

            if mapping['best_match'] and 'method' in mapping['best_match']:
                by_method[mapping['best_match']['method']] += 1

    # Build output
    output = {
        'meta': {
            'total_symbols': stats['total'],
            'high_confidence': stats['high'],
            'medium_confidence': stats['medium'],
            'low_confidence': stats['low'],
            'no_match': stats['no_match'],
            'total_concepts_scanned': len(concepts),
            'coverage_pct': round((stats['high'] + stats['medium'] + stats['low']) / stats['total'] * 100, 1),
            'by_method': dict(by_method),
        },
        'by_strate': {},
        'mappings': [],
    }

    for st in strates_data['strates']:
        sid = st['id']
        output['by_strate'][str(sid)] = {
            'name': st['name'],
            'total': by_strate[sid]['total'],
            'matched': by_strate[sid]['matched'],
        }

    # Compact mappings
    total_works = 0
    unique_concepts = set()
    for m in all_mappings:
        entry = {
            's': m['symbol'],
            'from': m['from'],
            'domain': m['domain'],
            'strate': m['strate'],
            'confidence': m['confidence'],
        }
        if m['best_match']:
            entry['concept_id'] = m['best_match']['id']
            entry['concept_name'] = m['best_match']['name']
            entry['works_count'] = m['best_match'].get('works_count', 0)
            total_works += entry['works_count']
            unique_concepts.add(entry['concept_id'])
        if m['domain_concept']:
            entry['domain_concept_id'] = m['domain_concept'][0]['id']
            entry['domain_concept_name'] = m['domain_concept'][0]['name']

        output['mappings'].append(entry)

    output['meta']['unique_concepts_mapped'] = len(unique_concepts)
    output['meta']['total_works_covered'] = total_works

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"RESULTAT:")
    print(f"  Total symboles:      {stats['total']}")
    print(f"  High confidence:     {stats['high']} (>=80)")
    print(f"  Medium confidence:   {stats['medium']} (>=50)")
    print(f"  Low confidence:      {stats['low']} (>=25)")
    print(f"  Sans match:          {stats['no_match']}")
    print(f"  Couverture:          {output['meta']['coverage_pct']}%")
    print(f"  Concepts uniques:    {len(unique_concepts)}")
    print(f"  Works couverts:      {total_works:,}")
    print(f"\n  Par methode: {dict(by_method)}")
    print(f"\n  -> {OUTPUT_FILE}")
    print(f"{'=' * 60}")

    print("\nPar strate:")
    for st in strates_data['strates']:
        sid = st['id']
        s = by_strate[sid]
        pct = s['matched'] / s['total'] * 100 if s['total'] > 0 else 0
        print(f"  S{sid}: {s['matched']:3d}/{s['total']:3d} ({pct:5.1f}%) {st['name']}")

    # Show unmatched
    unmatched = [m for m in all_mappings if m['confidence'] == 0]
    if unmatched:
        print(f"\nNon mappes ({len(unmatched)}):")
        for m in unmatched[:20]:
            print(f"  S{m['strate']} {m['symbol']:10s} | {m['from'][:50]}")


if __name__ == '__main__':
    run()
