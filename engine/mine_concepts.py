"""
YGGDRASIL ENGINE — Phase 3 : MINAGE v2
Extraire ~8,000-15,000 concepts TOUTES SCIENCES des 65K concepts OpenAlex.
Auto-classifier en strates S0-S6 + tags C1/C2.

Entrée  : D:/openalex/data/concepts/ (snapshot gzip)
Sortie  : data/mined_concepts.json (concepts classifiés)
          data/strates_export_v2.json (794 originaux + minés)
"""
import gzip
import json
import os
import re
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).parent.parent
CONCEPTS_DIR = Path("D:/openalex/data/concepts")
STRATES_FILE = ROOT / "data" / "strates_export.json"
OUTPUT_MINED = ROOT / "data" / "mined_concepts.json"
OUTPUT_STRATES_V2 = ROOT / "data" / "strates_export_v2.json"

# ═══════════════════════════════════════════════════════════
# FILTRES : ce qui EST science (TOUTES SCIENCES)
# ═══════════════════════════════════════════════════════════

# Keywords that indicate scientific content
# Checked against BOTH display_name AND description
INCLUDE_KEYWORDS = [
    # ── Pure math ──
    'mathematic', 'algebra', 'algebraic', 'topology', 'topological',
    'geometry', 'geometric', 'geometrical', 'arithmetic', 'arithmetical',
    'calculus', 'number theory', 'combinatoric', 'combinatorial',
    'probability', 'graph theory', 'set theory', 'category theory',
    'measure theory', 'group theory', 'ring theory', 'field theory',
    'fourier', 'hilbert', 'banach', 'sobolev', 'riemann', 'riemannian',
    'galois', 'diophantine', 'modular arithmetic', 'modular form',
    'elliptic curve', 'elliptic function',
    'homology', 'cohomology', 'homotopy', 'functor', 'sheaf', 'scheme',
    'manifold', 'fiber bundle', 'vector bundle',
    'polynomial', 'eigenvalue', 'eigenvector', 'determinant',
    'matrix', 'matrices', 'tensor', 'linear algebra',
    'differential equation', 'integral equation', 'integrable',
    'variational', 'optimization', 'convex',
    'stochastic', 'martingale', 'brownian', 'markov chain', 'markov process',
    'random variable', 'probability distribution', 'central limit',
    'theorem', 'conjecture', 'lemma', 'corollary', 'axiom',
    'proof', 'mathematical proof', 'formal proof',
    'prime number', 'factorization', 'divisor', 'congruence',
    'continued fraction', 'recurrence', 'fibonacci',
    'knot theory', 'braid group',
    'lie group', 'lie algebra', 'representation theory',
    'operator theory', 'spectral theory', 'functional analysis',
    'harmonic analysis', 'wavelet', 'approximation theory',
    'numerical analysis', 'finite element', 'interpolation',
    'ordinary differential', 'partial differential',
    'dynamical system', 'chaos theory', 'ergodic',
    'lattice theory', 'order theory', 'boolean algebra',
    'formal language', 'regular expression', 'context-free',
    'abstract algebra', 'commutative algebra', 'homological algebra',
    'algebraic geometry', 'differential geometry', 'symplectic',
    'projective geometry', 'affine geometry', 'euclidean geometry',
    'non-euclidean', 'hyperbolic geometry',

    # ── Logic & Computability ──
    'mathematical logic', 'formal logic', 'predicate logic',
    'propositional logic', 'modal logic', 'first-order logic',
    'computability', 'computable', 'recursive function',
    'turing machine', 'automata', 'automaton',
    'decidable', 'undecidable', 'halting problem',
    'complexity class', 'np-complete', 'np-hard', 'p vs np',
    'computational complexity', 'circuit complexity',
    'kolmogorov complexity', 'information theory',
    'coding theory', 'error-correcting', 'cryptograph',
    'lambda calculus', 'type theory', 'proof theory',

    # ── Physics ──
    'quantum mechanics', 'quantum field', 'quantum computing',
    'quantum information', 'quantum entanglement', 'quantum state',
    'hamiltonian', 'lagrangian', 'schrodinger', 'schrödinger',
    'thermodynamic', 'statistical mechanics', 'partition function',
    'entropy', 'boltzmann',
    'general relativity', 'special relativity', 'lorentz',
    'electromagnetism', 'electromagnetic', 'maxwell',
    'fluid mechanics', 'fluid dynamics', 'navier-stokes',
    'wave equation', 'heat equation', 'laplace equation',
    'classical mechanics', 'newtonian', 'analytical mechanics',
    'gauge theory', 'yang-mills', 'standard model',
    'string theory', 'conformal field', 'topological field',
    'condensed matter', 'solid state', 'superconducti',
    'nuclear physics', 'particle physics',
    'cosmolog', 'astrophysic',
    'gravitational', 'black hole', 'spacetime',
    'optics', 'photon', 'laser',
    'boson', 'fermion', 'quark', 'lepton', 'neutrino',
    'feynman', 'dirac equation', 'klein-gordon',
    'plasma', 'semiconductor', 'magnetism', 'magnetic',
    'acoustic', 'ultrasound', 'piezoelectric',
    'crystal', 'crystallograph', 'lattice',
    'spectroscop', 'diffraction', 'interferometr',

    # ── Applied math / CS theory ──
    'algorithm', 'data structure', 'sorting algorithm',
    'machine learning', 'neural network', 'deep learning',
    'artificial intelligence',
    'signal processing', 'image processing',
    'control theory', 'optimal control',
    'game theory', 'nash equilibrium',
    'linear programming', 'integer programming',
    'monte carlo', 'simulation',
    'information retrieval', 'data compression',
    'boolean satisfiability', 'constraint satisfaction',
    'computer vision', 'natural language processing',
    'robotics', 'autonomous', 'computer graphics',
    'database', 'distributed system', 'operating system',
    'compiler', 'programming language', 'software engineer',
    'network protocol', 'internet', 'wireless',
    'parallel computing', 'cloud computing', 'blockchain',

    # ── Named math objects ──
    'hilbert space', 'banach space', 'sobolev space',
    'lebesgue', 'hausdorff', 'cantor set',
    'mandelbrot', 'fractal', 'self-similar',
    'fibonacci', 'catalan number', 'bernoulli',
    'euler characteristic', 'betti number',
    'gaussian', 'poisson', 'exponential distribution',
    'normal distribution', 'binomial distribution',

    # ── Médecine & Biologie ──
    'epidemiolog', 'pandemic', 'endemic', 'pathogen',
    'pharmacolog', 'drug discovery', 'clinical trial',
    'bioinformatic', 'computational biology', 'systems biology',
    'genomic', 'proteomics', 'metabolomics', 'transcriptomics',
    'neuroscien', 'neurolog', 'brain imaging', 'cognitive science',
    'biostatistic', 'survival analysis', 'cox regression',
    'medical imaging', 'mri', 'ct scan', 'tomograph',
    'immunolog', 'antibod', 'antigen', 'vaccine',
    'cell biology', 'molecular biology', 'microbiology',
    'genetics', 'genetic', 'gene expression', 'dna', 'rna',
    'biochemistr', 'enzyme', 'protein', 'amino acid',
    'ecology', 'ecosystem', 'biodiversity', 'population dynamics',
    'evolution', 'evolutionary', 'natural selection', 'phylogenet',
    'anatomy', 'physiolog', 'patholog',
    'virology', 'bacteriology', 'parasitolog',
    'oncolog', 'cardiolog', 'endocrinol',
    'toxicolog', 'radiolog', 'anesthesi',
    'biomedical', 'biotechnolog', 'tissue engineering',
    'stem cell', 'regenerative', 'prosthetic',
    'surgery', 'surgical', 'transplant',
    'psychiatr', 'psychopharmacol',
    'public health', 'global health', 'health policy',
    'nutrition', 'dietetic',
    'veterinary', 'zoolog', 'entomolog', 'botan',

    # ── Chimie ──
    'chemistry', 'chemical', 'molecule', 'molecular',
    'organic chemistry', 'inorganic chemistry', 'physical chemistry',
    'polymer', 'catalys', 'electrochemist',
    'spectroscop', 'chromatograph', 'mass spectrometry',
    'nanomaterial', 'nanotechnolog', 'nanoparticle',
    'chemical reaction', 'reaction kinetics', 'thermochemist',
    'photochemist', 'surface chemistry', 'colloid',
    'analytical chemistry', 'synthesis', 'reagent',

    # ── Sciences de la Terre ──
    'geology', 'geological', 'geophysic', 'geochemist',
    'seismolog', 'seismic', 'earthquake', 'tectonic',
    'climatolog', 'climate', 'meteorolog', 'atmospheric',
    'oceanograph', 'hydrology', 'hydrogeolog',
    'volcanol', 'volcanic', 'magma', 'lava',
    'mineralog', 'petrograph', 'petrology',
    'paleontolog', 'fossil', 'stratigraphy',
    'glaciolog', 'permafrost', 'ice sheet',
    'remote sensing', 'gis', 'geographic information',
    'geodesy', 'cartograph',
    'soil science', 'pedology',
    'marine biology', 'limnolog',

    # ── Sciences sociales quantitatives ──
    'economics', 'economic', 'econometric', 'macroeconomic', 'microeconomic',
    'game theory', 'utility ', 'market equilibrium',
    'finance', 'financial', 'black-scholes', 'option pricing',
    'portfolio', 'risk management', 'actuarial',
    'demography', 'demographic', 'population',
    'psychometrics', 'cognitive psychology', 'behavioral',
    'sociometry', 'social network', 'network analysis',
    'linguistics', 'computational linguistics', 'phonetics',
    'anthropolog', 'ethnograph',

    # ── Ingénierie ──
    'engineering', 'mechanical', 'electrical', 'electronic',
    'civil engineering', 'structural', 'materials science',
    'aerospace', 'aerodynamic', 'propulsion',
    'chemical engineering', 'process engineering',
    'biomedical engineering', 'biomechanic',
    'telecommunication', 'antenna', 'radar',
    'power system', 'renewable energy', 'solar cell',
    'nuclear engineering', 'reactor', 'fusion energy',
    'robotics', 'mechatronics', 'automation',
    'manufacturing', 'industrial engineering',
    'hydraulic', 'pneumatic', 'thermodynamic',

    # ── Agronomie & Environnement ──
    'agronomy', 'agriculture', 'crop science', 'plant science',
    'forestry', 'silviculture', 'agroecolog',
    'environmental science', 'pollution', 'remediation',
    'sustainability', 'renewable resource',
    'aquaculture', 'fisheries science',
]

# ═══════════════════════════════════════════════════════════
# FILTRES : BRUIT PUR — aucun rapport avec la science
# ═══════════════════════════════════════════════════════════
EXCLUDE_KEYWORDS = [
    # Cuisine / Mode / Loisirs
    'cooking', 'food preparation', 'recipe',
    'fashion', 'textile design', 'clothing design',
    'sport', 'athletic', 'fitness', 'bodybuilding',
    'tourism', 'hospitality', 'hotel management',
    'photography', 'camera obscura',
    'hairstyl', 'cosmetolog', 'manicur',

    # Arts / Divertissement pur
    'cinema', 'film genre', 'screenplay',
    'popular music', 'rock music', 'jazz music', 'hip hop',
    'painting style', 'sculpture',
    'video game', 'board game', 'card game',
    'dance style', 'choreograph', 'ballet',
    'comic book', 'manga', 'anime',

    # Religion / Spiritualité pure
    'theological', 'sermon', 'worship',
    'astrology', 'horoscope', 'zodiac',

    # Administration / Bureaucratie
    'public administration', 'bureaucrac',
    'library science', 'archival',
    'real estate', 'property management',
    'human resources', 'personnel management',
    'office management', 'secretarial',
]

# ═══════════════════════════════════════════════════════════
# DOMAINE AUTO-DETECTION
# ═══════════════════════════════════════════════════════════
DOMAIN_RULES = [
    # (keywords_in_name_or_desc, domain_name)
    # Order matters — first match wins
    # ── MORE SPECIFIC domains first ──

    # Médecine & Bio spécialisés
    (['epidemiolog', 'pandemic', 'endemic', 'sir model',
      'disease spread', 'contact tracing', 'herd immunity'], 'épidémiologie'),
    (['pharmacolog', 'drug discovery', 'drug design', 'pharmaceutical',
      'pharmacokinetic', 'pharmacodynamic', 'dosimetry'], 'pharmacologie'),
    (['bioinformatic', 'computational biology', 'systems biology',
      'sequence alignment', 'gene network', 'protein folding'], 'bioinformatique'),
    (['neuroscien', 'neurolog', 'brain imaging', 'cognitive neuroscience',
      'neural pathway', 'synapse', 'neurotransmitter',
      'eeg', 'fmri', 'connectome'], 'neurosciences'),
    (['genomic', 'proteomics', 'metabolomics', 'transcriptomics',
      'gene expression', 'dna sequencing', 'crispr'], 'génomique'),
    (['immunolog', 'antibod', 'antigen', 'vaccine',
      'immune system', 'autoimmun', 'cytokine'], 'immunologie'),
    (['oncolog', 'cancer', 'tumor', 'metastasis',
      'chemotherapy', 'radiation therapy'], 'oncologie'),
    (['biomedical engineering', 'biomechanic', 'prosthetic',
      'medical imaging', 'mri', 'ct scan', 'tomograph',
      'tissue engineering', 'biocompatib'], 'biomédical'),
    (['medical', 'clinical', 'surgery', 'surgical',
      'cardiolog', 'endocrinol', 'radiolog',
      'anesthesi', 'psychiatr', 'patholog',
      'diagnosis', 'treatment', 'patient',
      'public health', 'global health'], 'médecine'),

    # Biologie
    (['ecology', 'ecosystem', 'biodiversity', 'habitat',
      'conservation biology', 'species richness'], 'écologie'),
    (['evolution', 'evolutionary', 'natural selection', 'phylogenet',
      'speciation', 'adaptation', 'darwinian'], 'évolution'),
    (['cell biology', 'molecular biology', 'microbiology',
      'virology', 'bacteriology', 'parasitolog',
      'biochemistr', 'enzyme', 'protein', 'amino acid',
      'dna', 'rna', 'genetics', 'genetic',
      'stem cell', 'regenerative', 'biotechnolog',
      'zoolog', 'entomolog', 'botan',
      'anatomy', 'physiolog', 'veterinary',
      'biology', 'population dynamics', 'lotka-volterra',
      'mathematical biology'], 'biologie'),

    # Sciences de la Terre
    (['seismolog', 'seismic', 'earthquake', 'tectonic',
      'lithosphere', 'mantle', 'richter'], 'sismologie'),
    (['climatolog', 'climate change', 'global warming',
      'greenhouse', 'carbon cycle', 'paleoclimate',
      'meteorolog', 'atmospheric', 'weather forecast'], 'climatologie'),
    (['volcanol', 'volcanic', 'magma', 'lava', 'eruption',
      'pyroclastic'], 'volcanologie'),
    (['oceanograph', 'marine science', 'ocean current',
      'deep sea', 'coral reef', 'marine biology', 'limnolog'], 'océanographie'),
    (['geology', 'geological', 'geophysic', 'geochemist',
      'mineralog', 'petrograph', 'petrology',
      'paleontolog', 'fossil', 'stratigraphy',
      'glaciolog', 'permafrost', 'ice sheet',
      'hydrology', 'hydrogeolog',
      'soil science', 'pedology',
      'remote sensing', 'gis', 'geographic information',
      'geodesy', 'cartograph'], 'géosciences'),

    # Chimie spécialisée
    (['nanomaterial', 'nanotechnolog', 'nanoparticle',
      'nanoscale', 'quantum dot'], 'nanotechnologie'),
    (['polymer', 'macromolecule', 'copolymer',
      'polymerization'], 'polymères'),
    (['organic chemistry', 'organic compound', 'aromatic',
      'alkane', 'alkene', 'functional group'], 'chimie organique'),
    (['electrochemist', 'electrolysis', 'galvanic',
      'battery', 'fuel cell', 'corrosion'], 'électrochimie'),
    (['chemistry', 'chemical', 'molecule', 'molecular',
      'inorganic chemistry', 'physical chemistry',
      'catalys', 'spectroscop', 'chromatograph',
      'mass spectrometry', 'chemical reaction',
      'reaction kinetics', 'thermochemist',
      'photochemist', 'surface chemistry', 'colloid',
      'analytical chemistry', 'synthesis', 'reagent'], 'chimie'),

    # Ingénierie
    (['aerospace', 'aerodynamic', 'propulsion', 'aircraft',
      'rocket', 'satellite', 'orbital mechanics'], 'aérospatiale'),
    (['telecommunication', 'antenna', 'radar', 'wireless',
      'network protocol', 'internet', '5g', 'fiber optic'], 'télécommunications'),
    (['power system', 'renewable energy', 'solar cell', 'wind turbine',
      'photovoltaic', 'nuclear energy', 'energy storage',
      'smart grid', 'power plant'], 'énergie'),
    (['materials science', 'metallurg', 'ceramic', 'composite',
      'alloy', 'crystal structure', 'semiconductor',
      'superconductor', 'thin film'], 'matériaux'),
    (['robotics', 'mechatronics', 'automation', 'autonomous',
      'actuator', 'sensor', 'embedded system'], 'robotique'),
    (['civil engineering', 'structural engineering', 'construction',
      'geotechnical', 'bridge', 'concrete',
      'mechanical engineering', 'electrical engineering',
      'electronic', 'chemical engineering',
      'manufacturing', 'industrial engineering',
      'hydraulic', 'pneumatic', 'engineering'], 'ingénierie'),

    # Agronomie & Environnement
    (['agronomy', 'agriculture', 'crop science', 'plant science',
      'forestry', 'silviculture', 'agroecolog',
      'aquaculture', 'fisheries', 'irrigation'], 'agronomie'),
    (['environmental science', 'pollution', 'remediation',
      'sustainability', 'waste management',
      'ecotoxicolog', 'environmental impact'], 'environnement'),

    # Sciences sociales quantitatives
    (['demography', 'demographic', 'population growth',
      'mortality rate', 'fertility rate', 'census'], 'démographie'),
    (['psychometrics', 'cognitive psychology', 'behavioral',
      'psychology', 'psycholog', 'perception',
      'memory', 'attention', 'learning theory'], 'psychologie'),
    (['sociometry', 'social network', 'network analysis',
      'sociology', 'sociolog', 'social structure'], 'sociologie'),
    (['linguistics', 'computational linguistics', 'phonetics',
      'morphology', 'language ', 'grammar', 'syntax',
      'natural language processing', 'nlp'], 'linguistique'),
    (['anthropolog', 'ethnograph', 'cultural',
      'archaeology', 'archeolog'], 'anthropologie'),
    (['political science', 'political', 'governance',
      'democracy', 'election', 'voting theory',
      'international relations'], 'science politique'),
    (['education', 'pedagogy', 'curriculum',
      'learning analytics', 'educational'], 'éducation'),
    (['history', 'historical', 'historiograph',
      'medieval', 'ancient '], 'histoire'),
    (['law ', 'legal', 'jurisprud',
      'constitutional', 'criminal law'], 'droit'),

    # ── DOMAINES ORIGINAUX (math/physique/CS) ──
    (['topology', 'topological', 'homotopy', 'homology', 'cohomology',
      'manifold', 'fiber bundle', 'knot theory', 'braid'], 'topologie'),
    (['linear algebra', 'matrix', 'matrices', 'eigenvalue', 'eigenvector',
      'determinant', 'vector space', 'linear map', 'tensor product'], 'algèbre lin'),
    (['algebra', 'algebraic', 'group theory', 'ring ', 'module ',
      'lie group', 'lie algebra', 'representation theory',
      'galois', 'field extension', 'ideal '], 'algèbre'),
    (['differential geometry', 'riemannian', 'curvature', 'geodesic',
      'connection ', 'christoffel', 'ricci'], 'géom diff'),
    (['algebraic geometry', 'scheme', 'sheaf', 'variety', 'divisor'], 'géom algébrique'),
    (['geometry', 'geometric', 'euclidean', 'projective', 'affine',
      'convex ', 'polyhedr', 'polygon', 'polytope'], 'géométrie'),
    (['number theory', 'prime number', 'diophantine', 'modular form',
      'elliptic curve', 'l-function', 'zeta function', 'continued fraction',
      'algebraic number', 'quadratic form'], 'nb théorie'),
    (['combinatoric', 'graph theory', 'ramsey', 'matroid', 'permutation',
      'partition ', 'catalan', 'fibonacci', 'generating function',
      'extremal graph', 'chromatic'], 'combinatoire'),
    (['probability', 'random variable', 'stochastic', 'martingale',
      'brownian', 'markov', 'central limit', 'law of large',
      'probability distribution', 'expected value'], 'probabilités'),
    (['statistic', 'regression', 'hypothesis test', 'estimation',
      'confidence interval', 'bayesian', 'likelihood', 'anova',
      'correlation', 'variance', 'biostatistic'], 'statistiques'),
    (['functional analysis', 'hilbert space', 'banach space', 'operator theory',
      'spectral theory', 'sobolev', 'distribution '], 'analyse fonctionnelle'),
    (['mathematical analysis', 'calculus', 'limit ', 'continuity',
      'derivative', 'integral', 'series ', 'convergence',
      'real analysis', 'complex analysis', 'measure theory',
      'lebesgue', 'fourier', 'taylor series'], 'analyse'),
    (['differential equation', 'ode', 'pde', 'partial differential',
      'boundary value', 'initial value', 'wave equation',
      'heat equation', 'laplace equation', 'navier-stokes',
      'finite element', 'numerical method'], 'EDP'),
    (['optimization', 'linear programming', 'convex optimization',
      'integer programming', 'constraint', 'simplex',
      'gradient descent', 'variational'], 'optimisation'),
    (['set theory', 'cardinality', 'ordinal', 'axiom of choice',
      'continuum hypothesis', 'well-order', 'zorn'], 'ensembles'),
    (['mathematical logic', 'formal logic', 'predicate', 'propositional',
      'model theory', 'proof theory', 'modal logic', 'first-order',
      'completeness theorem', 'compactness theorem'], 'logique'),
    (['computability', 'computable', 'recursive', 'turing machine',
      'halting problem', 'turing degree', 'church-turing',
      'recursively enumerable'], 'calculabilité'),
    (['computational complexity', 'complexity class', 'np-complete',
      'np-hard', 'p vs np', 'polynomial time', 'circuit complexity',
      'boolean satisfiability'], 'complexité'),
    (['automata', 'automaton', 'formal language', 'regular language',
      'context-free', 'pushdown', 'finite state'], 'automates'),
    (['category theory', 'functor', 'natural transformation', 'adjoint',
      'monad ', 'topos', 'abelian category'], 'catégories'),
    (['quantum mechanics', 'quantum field', 'quantum computing',
      'quantum information', 'quantum state', 'qubit',
      'entanglement', 'superposition', 'schrodinger', 'schrödinger',
      'wave function', 'hamiltonian', 'uncertainty principle'], 'quantique'),
    (['classical mechanics', 'newtonian', 'lagrangian', 'analytical mechanics',
      'rigid body', 'celestial mechanics'], 'mécanique'),
    (['statistical mechanics', 'ising model', 'phase transition',
      'mean field'], 'mécanique stat'),
    (['thermodynamic', 'entropy', 'temperature', 'heat ',
      'boltzmann', 'partition function', 'free energy',
      'carnot', 'second law'], 'thermo'),
    (['fluid mechanics', 'fluid dynamics', 'navier-stokes',
      'turbulence', 'viscosity', 'reynolds'], 'fluides'),
    (['general relativity', 'special relativity', 'spacetime',
      'lorentz', 'einstein field', 'schwarzschild',
      'gravitational wave'], 'relativité'),
    (['cosmolog', 'big bang', 'dark matter', 'dark energy',
      'cosmic microwave', 'hubble', 'inflation'], 'cosmologie'),
    (['electromagnetism', 'electromagnetic', 'maxwell',
      'electric field', 'magnetic field', 'coulomb',
      'faraday', 'ampere'], 'électromagn'),
    (['nuclear physics', 'radioactiv', 'fission', 'fusion',
      'isotope', 'decay '], 'nucléaire'),
    (['particle physics', 'standard model', 'higgs', 'boson',
      'fermion', 'quark', 'lepton', 'neutrino'], 'particules'),
    (['quantum field theory', 'gauge theory', 'yang-mills',
      'renormalization', 'feynman diagram', 'qed', 'qcd'], 'QFT'),
    (['optics', 'optical', 'photon', 'laser', 'refraction',
      'diffraction', 'interference'], 'optique'),
    (['information theory', 'entropy', 'channel capacity',
      'shannon', 'mutual information', 'data compression',
      'error-correcting', 'coding theory'], 'information'),
    (['signal processing', 'filter ', 'frequency', 'spectrum',
      'fourier transform', 'wavelet', 'convolution',
      'sampling'], 'signal'),
    (['cryptograph', 'encryption', 'cipher', 'rsa',
      'public key', 'hash function', 'digital signature'], 'crypto'),
    (['computer vision', 'image processing', 'object detection',
      'pattern recognition', 'image segmentation'], 'vision'),
    (['natural language processing', 'text mining', 'sentiment analysis',
      'machine translation', 'speech recognition'], 'NLP'),
    (['machine learning', 'deep learning', 'neural network',
      'artificial intelligence', 'classification', 'clustering',
      'reinforcement learning', 'supervised', 'unsupervised'], 'ML'),
    (['computer science', 'algorithm', 'data structure',
      'programming language', 'compiler', 'software',
      'database', 'distributed system', 'operating system',
      'computer graphics', 'parallel computing',
      'cloud computing', 'blockchain'], 'informatique'),
    (['economics', 'economic', 'econometric',
      'macroeconomic', 'microeconomic',
      'market equilibrium', 'general equilibrium'], 'économie'),
    (['finance', 'financial', 'black-scholes', 'option pricing',
      'portfolio', 'risk ', 'actuarial'], 'finance'),
    (['control theory', 'feedback', 'pid ', 'stability',
      'controllability', 'observability'], 'contrôle'),
    (['astronomy', 'astrophysic', 'stellar', 'galax',
      'planetary', 'orbit', 'exoplanet'], 'astronomie'),
    (['trigonometr', 'sine', 'cosine', 'tangent',
      'trigonometric'], 'trigonométrie'),
    (['dynamical system', 'chaos', 'attractor', 'bifurcation',
      'lyapunov', 'ergodic'], 'systèmes dynamiques'),
    (['numerical', 'approximation', 'interpolation',
      'quadrature', 'finite difference', 'runge-kutta'], 'analyse numérique'),
]

# ═══════════════════════════════════════════════════════════
# STRATE AUTO-CLASSIFICATION
# ═══════════════════════════════════════════════════════════
def classify_strate(name_lower, desc_lower):
    """Auto-classify into strate S0-S6."""
    text = name_lower + ' ' + desc_lower

    # S6: Undecidable, halting, Kolmogorov
    if any(k in text for k in [
        'undecidable', 'halting problem', 'kolmogorov complexity',
        'busy beaver', 'incompleteness', "rice's theorem",
        'post correspondence', 'word problem for groups',
        'entscheidungsproblem',
    ]):
        return 6

    # S5: Hyperarithmetical, analytical hierarchy
    if any(k in text for k in [
        'hyperarithmetic', 'analytical hierarchy', 'borel determinacy',
        'axiom of determinacy', 'wadge', 'projective hierarchy',
        'church-kleene', 'constructible universe',
    ]):
        return 5

    # S4: Full arithmetic hierarchy, PSPACE+
    if any(k in text for k in [
        'arithmetical hierarchy', 'pspace', 'exptime', 'expspace',
        'alternation (complexity)', 'interactive proof',
    ]):
        return 4

    # S3: Named theorems, PH, conjectures
    if any(k in text for k in [
        'conjecture', 'open problem', 'unsolved',
        'polynomial hierarchy', 'sharp-p', '#p',
        'np-hard', 'np-complete',
        'arthur-merlin', 'merlin-arthur',
    ]):
        return 3

    # S1: RE, halting basics, Σ⁰₁
    if any(k in text for k in [
        'recursively enumerable', 'computably enumerable',
        'halting', 'turing degree', 'turing jump',
        'many-one reduction', 'turing reduction',
    ]):
        return 1

    # S2: Σ⁰₂ level
    if any(k in text for k in [
        'limit computable', 'arithmetical hierarchy level 2',
    ]):
        return 2

    # S0: Everything else (decidable math, physics, CS)
    return 0


def classify_c1_c2(name_lower, desc_lower):
    """Classify as C1 (proven) or C2 (conjecture/hypothesis)."""
    text = name_lower + ' ' + desc_lower

    # C1 exceptions: these use "hypothesis" in the statistical sense, not as conjecture
    c1_exceptions = [
        'hypothesis test', 'null hypothesis', 'alternative hypothesis',
        'bayesian', 'p-value', 'z-test', 't-test', 'chi-squared test',
        'statistical hypothesis', 'test statistic',
        'homotopy hypothesis',  # This is actually proven (Grothendieck)
        'learning with errors',  # Cryptographic assumption, not open conjecture
    ]
    if any(ex in text for ex in c1_exceptions):
        return 'C1'

    if any(k in text for k in [
        'conjecture', 'hypothesis', 'open problem', 'unsolved',
        'unproven', 'unresolved',
    ]):
        return 'C2'
    return 'C1'


def detect_domain(name_lower, desc_lower):
    """Auto-detect domain from concept name and description."""
    text = name_lower + ' ' + desc_lower
    for keywords, domain in DOMAIN_RULES:
        if any(kw in text for kw in keywords):
            return domain
    return 'science générale'  # Generic fallback


def is_math_concept(concept):
    """Filter: is this concept scientifically relevant?
    v2: accepte TOUTES les sciences, rejette uniquement le bruit pur."""
    name = concept.get('display_name', '').lower()
    desc = (concept.get('description') or '').lower()
    text = name + ' ' + desc

    # Reject pure noise
    if any(ex in text for ex in EXCLUDE_KEYWORDS):
        # Exception: if it has ANY scientific signal, keep it
        strong_science = ['theorem', 'conjecture', 'algebra', 'topology',
                          'geometry', 'calculus', 'equation', 'mathematical',
                          'hilbert', 'banach', 'riemann', 'fourier',
                          'quantum', 'computability', 'complexity class',
                          'molecule', 'chemical', 'reaction',
                          'cell ', 'protein', 'gene', 'dna',
                          'epidemic', 'vaccine', 'clinical trial',
                          'geology', 'seismic', 'climate',
                          'engineering', 'algorithm', 'neural',
                          'ecology', 'species', 'evolution']
        if not any(sm in text for sm in strong_science):
            return False

    # Must match at least one include keyword
    return any(kw in text for kw in INCLUDE_KEYWORDS)


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


def load_existing_symbols():
    """Load existing 794 symbols from strates_export.json."""
    with open(STRATES_FILE, encoding='utf-8') as f:
        return json.load(f)


def run():
    print("=" * 60)
    print("YGGDRASIL -- Phase 3 : MINAGE v2 -- 65K -> TOUTES SCIENCES")
    print("=" * 60)

    # Load concepts
    print("\n[1/5] Loading 65K OpenAlex concepts...")
    concepts = load_concepts()
    print(f"  -> {len(concepts)} concepts loaded")

    # Filter math concepts
    print("\n[2/5] Filtering ALL science concepts...")
    math_concepts = [c for c in concepts if is_math_concept(c)]
    math_concepts.sort(key=lambda x: -x.get('works_count', 0))
    print(f"  -> {len(math_concepts)} science-related concepts found")

    # Load existing symbols to avoid duplicates
    print("\n[3/5] Loading existing 794 symbols...")
    existing = load_existing_symbols()
    existing_names = set()
    for st in existing['strates']:
        for sym in st['symbols']:
            existing_names.add(sym['s'].lower())
            existing_names.add(sym.get('from', '').lower())

    # Classify and deduplicate
    print("\n[4/5] Classifying and deduplicating...")
    mined = []
    seen_ids = set()
    seen_names = set()
    stats = {
        'total_scanned': len(math_concepts),
        'dedup_existing': 0,
        'dedup_name': 0,
        'accepted': 0,
    }
    by_strate = Counter()
    by_domain = Counter()
    by_class = Counter()

    for c in math_concepts:
        cid = c['id']
        name = c.get('display_name', '')
        name_lower = name.lower()
        desc = (c.get('description') or '').lower()

        # Skip duplicates
        if cid in seen_ids:
            continue
        seen_ids.add(cid)

        if name_lower in seen_names:
            stats['dedup_name'] += 1
            continue
        seen_names.add(name_lower)

        # Skip if already in existing symbols
        if name_lower in existing_names:
            stats['dedup_existing'] += 1
            continue

        # Classify
        strate = classify_strate(name_lower, desc)
        c1c2 = classify_c1_c2(name_lower, desc)
        domain = detect_domain(name_lower, desc)

        entry = {
            'concept_id': cid,
            'name': name,
            'description': c.get('description', ''),
            'wikidata': c.get('wikidata', ''),
            'level': c.get('level', -1),
            'works_count': c.get('works_count', 0),
            'cited_by_count': c.get('cited_by_count', 0),
            'strate': strate,
            'class': c1c2,
            'domain': domain,
        }

        mined.append(entry)
        stats['accepted'] += 1
        by_strate[strate] += 1
        by_domain[domain] += 1
        by_class[c1c2] += 1

    # Build output
    print("\n[5/5] Building output...")
    output = {
        'meta': {
            'total_mined': stats['accepted'],
            'total_scanned': stats['total_scanned'],
            'dedup_existing': stats['dedup_existing'],
            'dedup_name': stats['dedup_name'],
            'source': '65K OpenAlex concepts snapshot',
        },
        'by_strate': {str(s): by_strate[s] for s in sorted(by_strate)},
        'by_class': dict(by_class),
        'by_domain': dict(sorted(by_domain.items(), key=lambda x: -x[1])),
        'concepts': mined,
    }

    # Save mined concepts
    OUTPUT_MINED.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MINED, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # === Build strates_export_v2.json ===
    # Add mined concepts to existing strates
    import math as mathlib
    strates_v2 = json.loads(json.dumps(existing))  # Deep copy
    strates_v2['meta']['source'] = 'strates_export.json + 65K OpenAlex mined concepts'

    # Group mined by strate
    mined_by_strate = defaultdict(list)
    for m in mined:
        mined_by_strate[m['strate']].append(m)

    for st in strates_v2['strates']:
        sid = st['id']
        new_syms = mined_by_strate.get(sid, [])

        # Generate positions for new symbols (spiral layout outside existing)
        existing_count = len(st['symbols'])
        for i, m in enumerate(new_syms):
            # Spiral placement
            angle = (existing_count + i) * 0.618033988 * 2 * mathlib.pi  # Golden angle
            radius = 0.3 + 0.02 * mathlib.sqrt(existing_count + i)
            px = radius * mathlib.cos(angle)
            pz = radius * mathlib.sin(angle)

            st['symbols'].append({
                's': m['name'][:20],  # Truncate for display
                'from': m['name'],
                'domain': m['domain'],
                'px': round(px, 4),
                'pz': round(pz, 4),
                'class': m['class'],
                'mined': True,
                'concept_id': m['concept_id'],
                'works_count': m['works_count'],
            })

    # Update totals
    total = sum(len(st['symbols']) for st in strates_v2['strates'])
    strates_v2['meta']['total_symbols'] = total
    strates_v2['meta']['mined_symbols'] = stats['accepted']
    strates_v2['meta']['original_symbols'] = 794

    with open(OUTPUT_STRATES_V2, 'w', encoding='utf-8') as f:
        json.dump(strates_v2, f, ensure_ascii=False, indent=2)

    # Print results
    print(f"\n{'=' * 60}")
    print(f"RESULTAT MINAGE:")
    print(f"  Concepts scannes:     {stats['total_scanned']}")
    print(f"  Acceptes:             {stats['accepted']}")
    print(f"  Deja existants:       {stats['dedup_existing']}")
    print(f"  Doublons nom:         {stats['dedup_name']}")
    print(f"\n  C1 (prouve):          {by_class['C1']}")
    print(f"  C2 (hypothese):       {by_class.get('C2', 0)}")

    print(f"\n  Par strate:")
    for s in sorted(by_strate):
        existing_count = len([sym for sym in existing['strates'][s]['symbols']])
        new_count = by_strate[s]
        print(f"    S{s}: {existing_count:4d} existants + {new_count:4d} mines = {existing_count + new_count:5d}")

    total_after = 794 + stats['accepted']
    print(f"\n  TOTAL: 794 originaux + {stats['accepted']} mines = {total_after} symboles")

    print(f"\n  Top 15 domaines:")
    for domain, count in sorted(by_domain.items(), key=lambda x: -x[1])[:15]:
        print(f"    {domain:30s} : {count}")

    print(f"\n  -> {OUTPUT_MINED}")
    print(f"  -> {OUTPUT_STRATES_V2}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    run()
