"""Build audit_cannon_muninn.json — navigation map for Muninn."""
import sqlite3, json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = sqlite3.connect(os.path.join(REPO, "data", "wt3.db"))
c = db.cursor()

# === 1. Key papers by role ===
key_papers_by_role = {
    "rubik": ["math/0512485", "0803.3435", "1105.1436", "1106.5229", "1401.3699"],
    "cayley_diameter": ["1109.3550", "1205.1596", "1111.3114", "1202.5888", "1511.09340", "math/0502221"],
    "spectral_growth": ["1001.4556", "1005.1858", "0904.1800", "0902.0727"],
    "carmack_bridges": ["math/0611221", "1512.02408"],
    "chess_gn": ["1409.1530"],
    "cayley_key": ["math/0012192", "math/0505624", "1310.4735", "1203.5624", "cs/0205005"],
    "fibonacci_spectral": ["cond-mat/0410187", "0707.2994", "1001.2552"],
}

all_pids = [p for v in key_papers_by_role.values() for p in v]
papers_meta = {}
for pid in all_pids:
    c.execute("SELECT paper_id, title, year, domain, concepts FROM papers WHERE paper_id = ?", (pid,))
    row = c.fetchone()
    if row:
        concepts = json.loads(row[4]) if row[4] else []
        cids = []
        for ci in concepts[:20]:
            cids.append(ci["id"] if isinstance(ci, dict) else ci)
        papers_meta[row[0]] = {
            "title": row[1], "year": row[2], "domain": row[3],
            "concept_ids": cids
        }

# === 2. Co-occurrence pairs ===
cooc_pairs_def = [
    (3217, 9157, "Cayley graph x Eigenvalues"),
    (3217, 4492, "Cayley graph x Symmetric group"),
    (3217, 63903, "Cayley graph x Permutation group"),
    (3217, 64319, "Cayley graph x Wreath product"),
    (3217, 28454, "Cayley graph x Spectral gap"),
    (3217, 8508, "Cayley graph x Expander graph"),
    (3217, 57247, "Cayley graph x Comb optimization"),
    (3217, 15562, "Cayley graph x CSP"),
    (63903, 15276, "Permutation group x PSPACE"),
    (13737, 3217, "Golden ratio x Cayley graph"),
    (13737, 28454, "Golden ratio x Spectral gap"),
    (13737, 9157, "Golden ratio x Eigenvalues"),
    (11524, 3217, "Fibonacci x Cayley graph"),
    (11524, 4492, "Fibonacci x Symmetric group"),
    (16301, 12499, "Protein folding x Comp complexity"),
    (16301, 3217, "Protein folding x Cayley graph"),
    (29774, 1997, "Partition function x Ramsey"),
    (64855, 1997, "Potts model x Ramsey"),
    (60204, 3217, "Renorm group x Cayley graph"),
    (60204, 63903, "Renorm group x Perm group"),
    (15129, 3217, "Electrical network x Cayley graph"),
    (59049, 3217, "Resistance distance x Cayley"),
    (61733, 3217, "Data compression x Cayley graph"),
    (34208, 3217, "Kolmogorov x Cayley graph"),
    (28454, 4492, "Spectral gap x Symmetric group"),
]

cooc_results = {}
for a, b, label in cooc_pairs_def:
    lo, hi = min(a, b), max(a, b)
    c.execute("SELECT weight FROM cooc_global WHERE concept_a=? AND concept_b=?", (lo, hi))
    row = c.fetchone()
    cooc_results[label] = {"concept_a": a, "concept_b": b, "weight": row[0] if row else 0.0}

# === 3. Concept index ===
concept_index = {
    "cayley_graph": 3217, "wreath_product": 64319, "permutation_group": 63903,
    "symmetric_group": 4492, "coset": 62772, "group_theory": 62210, "cfsg": 59370,
    "spectral_gap": 28454, "expander_graph": 8508, "mixing_time": 64555,
    "eigenvalues": 9157, "laplacian": 2429, "random_walk": 3378,
    "csp": 15562, "pspace": 15276, "phase_transition": 7678,
    "p_versus_np": 13541, "comp_complexity": 12499, "np_complete": 3609,
    "boolean_sat": 60347, "turing_machine": 47107, "decidability": 8312,
    "godel_incompleteness": 12665, "proof_complexity": 933,
    "ramsey_theory": 1997, "ramseys_theorem": 55433,
    "fibonacci_number": 11524, "golden_ratio": 13737,
    "protein_folding": 16301, "partition_function": 29774,
    "renormalization_group": 60204, "ising_model": 56807,
    "potts_model": 64855, "spin_glass": 7925,
    "electrical_network": 15129, "resistance_distance": 59049,
    "data_compression": 61733, "kolmogorov_complexity": 34208,
    "entropy": 1033, "information_theory": 57221,
    "fitness_landscape": 63747, "power_law": 63029,
    "fractal_dimension": 17805, "cosmology": 17790,
    "holographic_principle": 13175, "penrose_tiling": 61412,
    "cellular_automaton": 54073, "simulated_annealing": 4263,
    "combinatorial_optimization": 57247,
}

# === 4. Build output ===
output = {
    "audit": "cannon_audit_v1",
    "date": "2026-03-26",
    "source": "WT3 (833K papers, 69M cooc) + web verification",

    "paths": {
        "wt3_db": "data/wt3.db",
        "wt2_chunks": "data/scan/wt2_chunks/",
        "wt2_chunk_pattern": "data/scan/wt2_chunks/chunk_{NNN}/papers.json.gz",
        "wt2_chunks_count": 416,
        "cannon_results": "data/results/scan_cannon_universal.json",
        "typed_results": "data/results/scan_cannon_typed.json",
        "carmack_results": "data/results/scan_carmack_moves.json",
        "metaprompt": "data/scan/metaprompt_cannon_muninn.md",
        "concept_births": "data/scan/concept_births.json",
        "spectral_births": "data/scan/spectral_births.json",
        "arxiv_tars": "E:/arxiv/src/",
        "openalex": "E:/openalex/data/",
    },

    "sql_queries": {
        "find_paper": "SELECT paper_id, title, year, domain, concepts FROM papers WHERE paper_id = ?",
        "cooc_weight": "SELECT weight FROM cooc_global WHERE concept_a = min(A,B) AND concept_b = max(A,B)",
        "top_partners": "SELECT concept_b, weight FROM cooc_global WHERE concept_a = ? ORDER BY weight DESC LIMIT 30",
        "bridge_papers": "Use bipartite: JOIN on glyph_id for papers touching both concept_id = X and concept_id = Y",
        "search_title": "SELECT paper_id, title, year FROM papers WHERE title LIKE '%keyword%'",
    },

    "concept_index": concept_index,

    "papers": {
        "by_role": key_papers_by_role,
        "metadata": papers_meta,
    },

    "cooc_pairs": cooc_results,

    "carmack_bridges": {
        "protein_folding_x_pnp": {
            "bridges": 1, "paper": "math/0611221", "cooc": 0.1175,
            "status": "QUASI-DESERT",
            "web_note": "Well-populated in journals: Fraenkel 1993, Berger & Leighton 1998, Ngo/Marks/Karplus 1994 — but absent from arXiv",
        },
        "protein_folding_x_cayley": {
            "bridges": 0, "paper": None, "cooc": 0.0,
            "status": "DESERT",
        },
        "partition_function_x_ramsey": {
            "bridges": 0, "paper": None, "cooc": 0.0,
            "status": "DESERT",
            "web_note": "Wouters et al. 2022 (arXiv:2112.11426) exists but post-cutoff",
        },
        "potts_model_x_ramsey": {
            "bridges": 0, "paper": None, "cooc": 0.0,
            "status": "DESERT",
            "web_note": "2-hop path exists via chromatic polynomial (Sokal) but no direct bridge",
        },
        "renorm_group_x_cayley": {
            "bridges": 1, "paper": "1512.02408", "cooc": 0.026,
            "status": "QUASI-DESERT",
            "paper_title": "The signed permutation group on Feynman graphs",
        },
        "electrical_x_cayley": {
            "bridges": 0, "paper": None, "cooc": 0.028,
            "status": "DESERT",
            "web_note": "Spectral gap -> diameter path established (Shkredov 2020). Resistance framing novel.",
        },
        "compression_x_cayley": {
            "bridges": 0, "paper": None, "cooc": 0.0,
            "status": "DESERT_TOTAL",
        },
    },

    "verdicts": {
        "R1_W_linear": {
            "verdict": "ACCIDENT",
            "detail": "2-point calibration. True scaling = Theta(n^2/log n) (Demaine ESA 2011). No precedent in 833K papers.",
            "key_papers": ["1109.3550", "1205.1596", "1111.3114", "1202.5888"],
            "asymptotic": "Theta(n^2/log n) — superlinear",
            "demaine_ref": "arXiv:1106.5736 (NOT in our dataset)",
            "cayley_diameter_papers": 19,
            "cayley_graph_papers_total": 467,
        },
        "R2_GN4_bounds": {
            "verdict": "INCONNU",
            "detail": "GN(4) unsolved. Best estimate 37-38 OBTM (Kociemba).",
            "bounds_SSTM": {"lower": 32, "upper": 53, "estimate": 35},
            "bounds_OBTM": {"lower": 35, "upper": 55, "estimate": "37-38"},
            "bounds_BTM": {"lower": 29, "upper": 53},
            "gn4_32_is": "SSTM lower bound, NOT proven value",
            "rubik_papers_in_wt3": 5,
            "papers_about_4x4": 0,
            "key_papers": ["math/0512485", "0803.3435", "1105.1436"],
        },
        "R3_phi_symmetry": {
            "verdict": "NON_JUSTIFIE",
            "detail": "Zero papers bridging phi with Cayley graphs. No sandwich theorem for diameter.",
            "golden_ratio_x_cayley": {"papers": 0, "cooc": 0.0},
            "fibonacci_x_cayley": {"papers": 1, "cooc": 0.126, "paper": "1310.4735", "note": "tangential - Leavitt path algebras"},
            "fibonacci_x_spectral_gap": {"papers": 4, "note": "all condensed matter quasicrystals"},
            "spectral_gap_x_symmetric_group": {"papers": 2, "list": ["0904.1800", "1310.6156"]},
        },
        "R4_carmack_bridges": {
            "verdict": "5_SUR_7_DESERTS_CONFIRMES",
            "true_deserts": [
                "protein_folding_x_cayley",
                "partition_function_x_ramsey",
                "potts_model_x_ramsey",
                "electrical_x_cayley",
                "compression_x_cayley",
            ],
            "quasi_deserts": ["protein_folding_x_pnp", "renorm_group_x_cayley"],
        },
    },

    "structural_holes": [
        {"pair": "Cayley graph x CSP", "cooc": 0.0, "papers": 0},
        {"pair": "Cayley graph x PSPACE", "cooc": 0.0, "papers": 0},
        {"pair": "Permutation group x PSPACE", "cooc": 0.0, "papers": 0},
        {"pair": "Golden ratio x Cayley graph", "cooc": 0.0, "papers": 0},
        {"pair": "Golden ratio x Spectral gap", "cooc": 0.0, "papers": 0},
        {"pair": "Protein folding x Cayley graph", "cooc": 0.0, "papers": 0},
        {"pair": "Partition function x Ramsey", "cooc": 0.0, "papers": 0},
        {"pair": "Potts model x Ramsey", "cooc": 0.0, "papers": 0},
        {"pair": "Data compression x Cayley graph", "cooc": 0.0, "papers": 0},
        {"pair": "Kolmogorov complexity x Cayley graph", "cooc": 0.0, "papers": 0},
    ],
}

out_path = os.path.join(REPO, "data", "results", "audit_cannon_muninn.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Written: {out_path}")
print(f"Papers: {len(papers_meta)}, Cooc: {len(cooc_results)}, Concepts: {len(concept_index)}, Holes: {len(output['structural_holes'])}")
db.close()
