#!/usr/bin/env python3
"""
YGGDRASIL — PIONEER EQUATION EXTRACTOR
════════════════════════════════════════════════════
Extrait les équations des papers pionniers déjà identifiés par le scan.
Va directement dans les tars pour ces paper_ids spécifiques.

Sky × Claude — 10 Mars 2026, Versoix
"""

import tarfile
import gzip
import re
import os
import sys
import time
import io

ARXIV_DIR = "E:/arxiv/src"

# Pioneer papers from our scans
PIONEERS = {
    "P3_fitness_bio": [
        "cond-mat/0004072",   # Microevolution, Macroevolution, Viral quasispecies
        "nlin/0002032",       # Predation, Foraging, Coevolution, Food web
        "physics/0006080",    # Genome, Sequence
        "physics/0007096",    # Scaling law, biology
    ],
    "P4_finance_ema": [
        "cond-mat/0001117",   # Local volatility, Arbitrage, Portfolio
        "cond-mat/0002059",   # Econometrics, Bayesian, Stock market
        "cond-mat/0004376",   # Volatility, Rational expectations
    ],
    "P5_ecology": [
        "nlin/0009025",       # Biodiversity, Ecology, Trophic level
        "cond-mat/0202047",   # Ecology, Extinction, Abundance
        "cond-mat/0204612",   # Viral quasispecies, Evolutionary biology
    ],
    "P6_protein": [
        "cond-mat/0101229",   # HIV-1 protease, Protein folding
        "physics/0012003",    # Amino acid, Protein folding
    ],
    "P2_cascades_bio": [
        "cond-mat/0005495",   # Medicine
    ],
}


def paper_id_to_tar_prefix(paper_id):
    """Convert arXiv ID to tar file prefix.
    e.g. cond-mat/0001117 -> could be in arXiv_src_0001_NNN.tar
    or based on submission date.
    """
    # Old format: category/YYMMNNN
    parts = paper_id.split('/')
    if len(parts) == 2:
        yymm = parts[1][:4]  # first 4 chars = YYMM
        return yymm
    # New format: YYMM.NNNNN
    return paper_id[:4]


def extract_tex_from_tar_member(tar, member):
    """Extract tex content. Handles:
    - Direct .tex files
    - Gzipped .tex files
    - Gzipped tar bundles (tar.gz containing .tex + figures)
    """
    try:
        f = tar.extractfile(member)
        if f is None:
            return None
        data = f.read()
        f.close()

        if member.name.endswith('.gz') or data[:2] == b'\x1f\x8b':
            try:
                data = gzip.decompress(data)
            except Exception:
                pass

        # Check if decompressed data is itself a tar archive
        if data[:5] in (b'fig1.', b'fig_1', b'paper', b'main.', b'artic') or \
           (len(data) > 300 and b'\x00100644' in data[:500]):
            # Likely a tar archive — try to open it
            try:
                inner_tar = tarfile.open(fileobj=io.BytesIO(data))
                tex_contents = []
                for inner_member in inner_tar.getmembers():
                    if inner_member.name.endswith('.tex') and inner_member.isfile():
                        inner_f = inner_tar.extractfile(inner_member)
                        if inner_f:
                            inner_data = inner_f.read()
                            inner_f.close()
                            try:
                                tex = inner_data.decode('utf-8', errors='replace')
                            except Exception:
                                tex = inner_data.decode('latin-1', errors='replace')
                            if len(tex) > 100:
                                tex_contents.append(tex)
                inner_tar.close()
                if tex_contents:
                    # Return longest .tex file (usually the main paper)
                    tex_contents.sort(key=len, reverse=True)
                    return tex_contents[0]
            except Exception:
                pass

        try:
            text = data.decode('utf-8', errors='replace')
            return text
        except Exception:
            return data.decode('latin-1', errors='replace')
    except Exception:
        return None


def extract_all_math(tex):
    """Extract ALL math environments from tex."""
    equations = []

    patterns = [
        (r'\$\$(.+?)\$\$', 'display'),
        (r'\\\[(.+?)\\\]', 'bracket'),
        (r'\\begin\{equation\}(.*?)\\end\{equation\}', 'equation'),
        (r'\\begin\{equation\*\}(.*?)\\end\{equation\*\}', 'equation*'),
        (r'\\begin\{align\}(.*?)\\end\{align\}', 'align'),
        (r'\\begin\{align\*\}(.*?)\\end\{align\*\}', 'align*'),
        (r'\\begin\{eqnarray\}(.*?)\\end\{eqnarray\}', 'eqnarray'),
        (r'\\begin\{eqnarray\*\}(.*?)\\end\{eqnarray\*\}', 'eqnarray*'),
        (r'\\begin\{multline\}(.*?)\\end\{multline\}', 'multline'),
        (r'\\begin\{gather\}(.*?)\\end\{gather\}', 'gather'),
    ]

    for pattern, env_type in patterns:
        for m in re.finditer(pattern, tex, re.DOTALL):
            eq = m.group(1).strip()
            if len(eq) < 3 or len(eq) > 3000:
                continue

            start = max(0, m.start() - 400)
            end = min(len(tex), m.end() + 300)
            context = tex[start:end]
            context = re.sub(r'\s+', ' ', context)

            equations.append({
                "type": env_type,
                "latex": eq,
                "context": context[:600],
            })

    return equations


def find_paper_in_tars(paper_id):
    """Find a specific paper in arXiv tars.

    arXiv tar member names vary:
      - "0001/cond-mat0001117.gz"  (category slug WITHOUT hyphen + number)
      - "0204/cond-mat0204612.gz"  (same pattern)
      - "0009/nlin0009025.gz"
      - Sometimes nested: "cond-mat0001117/paper.tex"

    We must match BOTH the category slug AND the paper number to avoid
    cross-category collisions (e.g. astro-ph0004072 vs cond-mat0004072).
    """
    yymm = paper_id_to_tar_prefix(paper_id)

    matching_tars = sorted([
        t for t in os.listdir(ARXIV_DIR)
        if t.startswith(f"arXiv_src_{yymm}_") and t.endswith('.tar')
    ])

    if not matching_tars:
        return None, None

    parts = paper_id.split('/')
    if len(parts) == 2:
        category = parts[0]         # e.g. "cond-mat"
        number = parts[1]           # e.g. "0001117"
        # In tar members, category hyphen is removed: "cond-mat" -> "cond-mat" or "condmat"
        # Build patterns to match both forms
        cat_slug = category.replace('-', '')  # "condmat"
        # Match patterns: "cond-mat0001117" or "condmat0001117" or "/cond-mat/0001117"
        match_patterns = [
            f"{category}{number}",      # cond-mat0001117
            f"{cat_slug}{number}",       # condmat0001117
            f"{category}/{number}",      # cond-mat/0001117
        ]
    else:
        number = paper_id
        match_patterns = [paper_id]

    for tar_name in matching_tars:
        tar_path = os.path.join(ARXIV_DIR, tar_name)
        try:
            with tarfile.open(tar_path, 'r') as tar:
                # First pass: collect ALL matching members (prefer .tex over .gz)
                candidates = []
                for member in tar.getmembers():
                    name_lower = member.name.lower()
                    matched = any(pat.lower() in name_lower for pat in match_patterns)
                    if not matched:
                        continue

                    if member.name.endswith('.tex'):
                        candidates.append((0, member))  # priority 0 = best
                    elif member.name.endswith('.gz'):
                        candidates.append((1, member))
                    elif member.isfile() and member.size > 100:
                        candidates.append((2, member))

                # Sort by priority, try each
                candidates.sort(key=lambda x: x[0])
                for _, member in candidates:
                    tex = extract_tex_from_tar_member(tar, member)
                    if tex and len(tex) > 100:
                        # Sanity check: must look like LaTeX
                        if '\\' in tex[:2000] or '$' in tex[:2000]:
                            return tex, f"{tar_name}:{member.name}"
        except Exception as e:
            continue

    return None, None


def main():
    t0 = time.time()
    print("=" * 100)
    print("PIONEER EQUATION EXTRACTOR — Direct tar lookup")
    print("=" * 100)

    all_results = {}

    for piste, paper_ids in PIONEERS.items():
        print(f"\n{'='*80}")
        print(f"  PISTE: {piste}")
        print(f"{'='*80}")

        for paper_id in paper_ids:
            print(f"\n  --- Searching: {paper_id} ---")
            tex, location = find_paper_in_tars(paper_id)

            if tex is None:
                print(f"    NOT FOUND in tars")
                continue

            print(f"    Found at: {location}")
            print(f"    TeX size: {len(tex):,} chars")

            equations = extract_all_math(tex)
            print(f"    Equations found: {len(equations)}")

            if not equations:
                # Try inline math as fallback
                inline = re.findall(r'\$([^$]{10,200})\$', tex)
                print(f"    Inline math: {len(inline)}")

            # Print top equations (longest = usually most important)
            equations.sort(key=lambda x: len(x["latex"]), reverse=True)

            # Also filter for relevant ones
            relevant_kw = {
                "P3_fitness_bio": ['fitness', 'w_', 'selection', 'replicator',
                                   'mutation', 'payoff', 'sum', 'bar{'],
                "P4_finance_ema": ['alpha', 'sigma', 'volatil', 'ema', 'ewma',
                                    's_t', 'return', 'price', 'moving'],
                "P5_ecology": ['n_t', 'n_{', 'extinction', 'population',
                              'species', 'diversity', 'abundance', 'birth', 'death'],
                "P6_protein": ['k_', 'fold', 'energy', 'free', 'rate',
                              'protease', 'binding', 'substrate'],
                "P2_cascades_bio": ['frac{d', 'k_', 'cascade', 'signal',
                                    'enzyme', 'substrate'],
            }

            kws = relevant_kw.get(piste, [])
            scored = []
            for eq in equations:
                s = sum(1 for kw in kws if kw in eq["latex"].lower())
                if s > 0:
                    scored.append((s, eq))

            scored.sort(key=lambda x: x[0], reverse=True)

            print(f"\n    TOP RELEVANT EQUATIONS:")
            for i, (score, eq) in enumerate(scored[:8]):
                latex_clean = re.sub(r'\s+', ' ', eq["latex"])
                if len(latex_clean) > 200:
                    latex_clean = latex_clean[:200] + "..."
                print(f"    {i+1}. [score={score}, {eq['type']}]")
                print(f"       $$ {latex_clean} $$")

            if not scored:
                print(f"\n    ALL EQUATIONS (top 5 by length):")
                for i, eq in enumerate(equations[:5]):
                    latex_clean = re.sub(r'\s+', ' ', eq["latex"])[:200]
                    print(f"    {i+1}. [{eq['type']}] $$ {latex_clean} $$")

            all_results[f"{piste}/{paper_id}"] = {
                "location": location,
                "n_equations": len(equations),
                "top_relevant": [(s, eq["latex"][:500], eq["type"])
                                 for s, eq in scored[:10]],
                "all_equations_count": len(equations),
            }

    print(f"\n{'='*100}")
    print(f"DONE — {time.time()-t0:.0f}s")
    print(f"{'='*100}")

    # Summary
    found = sum(1 for v in all_results.values() if v["n_equations"] > 0)
    total = sum(len(ids) for ids in PIONEERS.values())
    print(f"  Found: {found}/{total} papers with equations")


if __name__ == "__main__":
    main()
