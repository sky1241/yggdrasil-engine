#!/usr/bin/env python3
"""
YGGDRASIL — EQUATION EXTRACTOR
════════════════════════════════════════════════════
Extrait les équations LaTeX des tars arXiv pour les 7 pistes Muninn.
Cherche par mots-clés dans les .tex, extrait les environnements math.

Sky × Claude — 10 Mars 2026, Versoix
"""

import tarfile
import gzip
import re
import os
import sys
import time
import io
from collections import defaultdict

ARXIV_DIR = "E:/arxiv/src"

# ══════════════════════════════════════════════════
# PISTES — keywords to search + tar selection
# ══════════════════════════════════════════════════
PISTES = {
    "P1_immunology": {
        "keywords": [
            r"affinity\s+maturation", r"germinal\s+center",
            r"antibody\s+half.life", r"somatic\s+hypermutation",
            r"B.cell\s+selection", r"vaccination\s+spacing",
        ],
        "tar_patterns": ["q-bio", "physics"],  # q-bio papers
    },
    "P2_cascades": {
        "keywords": [
            r"MAPK\s+cascade", r"kinase\s+phosphatase",
            r"signal\s+transduction.*ODE", r"Michaelis.Menten.*cascade",
            r"phosphorylation\s+cascade", r"biochemical\s+network",
        ],
        "tar_patterns": ["q-bio", "physics"],
    },
    "P3_fitness": {
        "keywords": [
            r"fitness\s+function", r"selection\s+coefficient",
            r"Price\s+equation", r"evolutionary\s+dynamics",
            r"replicator\s+equation", r"adaptive\s+fitness",
            r"fitness\s+landscape",
        ],
        "tar_patterns": ["q-bio", "nlin", "cond-mat", "physics"],
    },
    "P4_finance_ema": {
        "keywords": [
            r"exponential\s+moving\s+average", r"EWMA",
            r"adaptive.*EMA", r"volatility.*exponential",
            r"moving\s+average.*adaptive", r"exponential\s+smoothing.*finance",
        ],
        "tar_patterns": ["cond-mat", "q-fin", "physics", "math"],
    },
    "P5_ecology_decay": {
        "keywords": [
            r"population\s+viability", r"minimum\s+viable\s+population",
            r"extinction\s+threshold", r"species\s+decay",
            r"population\s+decline.*exponential", r"extinction\s+probability",
            r"Allee\s+effect",
        ],
        "tar_patterns": ["q-bio", "nlin", "physics"],
    },
    "P6_protein_decay": {
        "keywords": [
            r"ubiquitin.*proteasome", r"protein\s+half.life",
            r"degradation\s+kinetics", r"protein\s+turnover",
            r"proteasomal\s+degradation",
        ],
        "tar_patterns": ["q-bio", "physics", "cond-mat"],
    },
    "P7_knowledge_halflife": {
        "keywords": [
            r"knowledge\s+half.life", r"obsolescence.*scientific",
            r"citation\s+decay", r"half.life\s+of\s+facts",
            r"knowledge\s+decay", r"scientometric.*decay",
        ],
        "tar_patterns": ["physics", "cs", "cond-mat"],
    },
}

# Math environment patterns
MATH_PATTERNS = [
    # Display math
    (r'\$\$(.+?)\$\$', 'display'),
    (r'\\\[(.+?)\\\]', 'bracket'),
    # Equation environments
    (r'\\begin\{equation\}(.*?)\\end\{equation\}', 'equation'),
    (r'\\begin\{equation\*\}(.*?)\\end\{equation\*\}', 'equation*'),
    (r'\\begin\{align\}(.*?)\\end\{align\}', 'align'),
    (r'\\begin\{align\*\}(.*?)\\end\{align\*\}', 'align*'),
    (r'\\begin\{eqnarray\}(.*?)\\end\{eqnarray\}', 'eqnarray'),
    (r'\\begin\{multline\}(.*?)\\end\{multline\}', 'multline'),
    (r'\\begin\{gather\}(.*?)\\end\{gather\}', 'gather'),
]


def extract_tex_from_member(tar, member):
    """Extract tex content from a tar member (may be .tex or .gz)."""
    try:
        f = tar.extractfile(member)
        if f is None:
            return None
        data = f.read()
        f.close()

        # If it's gzipped
        if member.name.endswith('.gz'):
            try:
                data = gzip.decompress(data)
            except Exception:
                return None

        # Try UTF-8 then latin-1
        try:
            return data.decode('utf-8', errors='replace')
        except Exception:
            return data.decode('latin-1', errors='replace')
    except Exception:
        return None


def extract_equations(tex_content, context_lines=3):
    """Extract math environments from tex content."""
    equations = []

    for pattern, env_type in MATH_PATTERNS:
        for m in re.finditer(pattern, tex_content, re.DOTALL):
            eq = m.group(1).strip()
            if len(eq) < 5 or len(eq) > 2000:
                continue

            # Get context (text around the equation)
            start = max(0, m.start() - 300)
            end = min(len(tex_content), m.end() + 200)
            context = tex_content[start:end]
            # Clean up context
            context = re.sub(r'\s+', ' ', context)[:500]

            equations.append({
                "type": env_type,
                "latex": eq,
                "context": context,
            })

    return equations


def matches_keywords(tex_content, keywords):
    """Check if tex matches any keywords. Return matched keywords."""
    matched = []
    tex_lower = tex_content.lower()
    for kw in keywords:
        if re.search(kw, tex_lower):
            matched.append(kw)
    return matched


def get_relevant_tars(tar_patterns):
    """Get list of tar files matching patterns."""
    all_tars = sorted(os.listdir(ARXIV_DIR))
    relevant = []

    for tar_name in all_tars:
        if not tar_name.endswith('.tar'):
            continue
        # All tars could contain papers from any category
        # But we focus on recent ones (2000+) for bio/finance
        relevant.append(tar_name)

    return relevant


def scan_tar(tar_path, piste_name, keywords, max_papers=50):
    """Scan a single tar for matching papers."""
    results = []
    try:
        with tarfile.open(tar_path, 'r') as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                # Only .tex and .gz files
                if not (member.name.endswith('.tex') or member.name.endswith('.gz')):
                    continue
                if member.size > 2_000_000:  # Skip huge files
                    continue

                tex = extract_tex_from_member(tar, member)
                if tex is None or len(tex) < 100:
                    continue

                matched_kw = matches_keywords(tex, keywords)
                if not matched_kw:
                    continue

                equations = extract_equations(tex)
                if not equations:
                    continue

                # Extract paper ID from path
                paper_id = member.name.split('/')[0] if '/' in member.name else member.name
                paper_id = paper_id.replace('.tex', '').replace('.gz', '')

                results.append({
                    "paper_id": paper_id,
                    "file": member.name,
                    "matched_keywords": matched_kw,
                    "equations": equations,
                    "n_equations": len(equations),
                })

                if len(results) >= max_papers:
                    break
    except Exception as e:
        pass

    return results


def score_equation_relevance(eq_latex, piste):
    """Score how relevant an equation is to the piste."""
    latex = eq_latex.lower()
    score = 0

    if piste == "P1_immunology":
        for term in ['k_d', 'k_a', 'half', 'affinity', 'decay', 'e^{-', '2^{-',
                      't_{1/2}', 'lambda', 'booster', 'dose']:
            if term in latex:
                score += 1

    elif piste == "P2_cascades":
        for term in ['frac{d', 'frac{dx', 'k_{cat}', 'k_m', 'michaelis',
                      'phospho', 'cascade', 'mapk', 'v_{max}']:
            if term in latex:
                score += 1

    elif piste == "P3_fitness":
        for term in ['fitness', 'w_i', 'w_j', 'selection', 'sum', 'bar{w}',
                      'delta', 'replicator', 'cov(', 'price', 'overline']:
            if term in latex:
                score += 1

    elif piste == "P4_finance_ema":
        for term in ['alpha', 'ema', 'ewma', 's_t', 's_{t', 'sigma',
                      'volatil', '1-\\alpha', '(1-', 'moving']:
            if term in latex:
                score += 1

    elif piste == "P5_ecology_decay":
        for term in ['n_t', 'n_{t', 'extinction', 'lambda', 'e^{r',
                      'carrying', 'k', 'threshold', 'viable', 'allee',
                      'decline', 'n_{mvp']:
            if term in latex:
                score += 1

    elif piste == "P6_protein_decay":
        for term in ['k_{deg', 'ubiquitin', 'proteasome', 'half-life',
                      't_{1/2}', 'e^{-', 'degradation', 'turnover',
                      'frac{d[', 'k_d']:
            if term in latex:
                score += 1

    elif piste == "P7_knowledge_halflife":
        for term in ['half-life', 'obsolesc', 'decay', 'citation',
                      'e^{-', '2^{-', 'knowledge', 'h =', 'lambda']:
            if term in latex:
                score += 1

    return score


def main():
    t0 = time.time()
    print("=" * 100)
    print("EQUATION EXTRACTOR — 7 pistes Muninn")
    print("Scanning arXiv tars for LaTeX equations")
    print("=" * 100)

    all_tars = sorted([t for t in os.listdir(ARXIV_DIR) if t.endswith('.tar')])
    print(f"Available tars: {len(all_tars)}")

    # Strategy: scan a subset of tars per piste
    # Focus on 2000-2024 (YYMM >= 0001)
    # For bio: q-bio started ~2003, but bio-physics papers are in cond-mat/physics
    # Sample: every 10th tar for broad coverage, then focused tars

    # Select ~200 tars spread across the archive for broad coverage
    sample_indices = list(range(0, len(all_tars), 15))  # every 15th = ~234 tars
    sample_tars = [all_tars[i] for i in sample_indices]

    all_results = {}

    for piste_name, piste_def in PISTES.items():
        print(f"\n{'='*80}")
        print(f"PISTE: {piste_name}")
        print(f"Keywords: {piste_def['keywords'][:3]}...")
        print(f"{'='*80}")

        piste_results = []
        tars_scanned = 0

        for tar_name in sample_tars:
            tar_path = os.path.join(ARXIV_DIR, tar_name)
            results = scan_tar(tar_path, piste_name, piste_def["keywords"],
                              max_papers=10)
            tars_scanned += 1

            if results:
                piste_results.extend(results)
                for r in results:
                    print(f"  FOUND: {r['paper_id']} ({r['n_equations']} eqs, "
                          f"kw: {r['matched_keywords'][:2]})")

            if tars_scanned % 50 == 0:
                print(f"  ... {tars_scanned} tars scanned, {len(piste_results)} papers found, "
                      f"{time.time()-t0:.0f}s")

            # Stop if we have enough
            if len(piste_results) >= 30:
                break

        print(f"\n  Total: {len(piste_results)} papers, {tars_scanned} tars scanned")

        # Score and rank equations
        if piste_results:
            all_equations = []
            for paper in piste_results:
                for eq in paper["equations"]:
                    score = score_equation_relevance(eq["latex"], piste_name)
                    if score > 0:
                        all_equations.append({
                            "paper_id": paper["paper_id"],
                            "score": score,
                            "type": eq["type"],
                            "latex": eq["latex"],
                            "context": eq["context"][:300],
                        })

            all_equations.sort(key=lambda x: x["score"], reverse=True)

            print(f"\n  TOP EQUATIONS (scored):")
            for i, eq in enumerate(all_equations[:10]):
                latex_clean = re.sub(r'\s+', ' ', eq["latex"])[:120]
                print(f"    {i+1}. [score={eq['score']}] {eq['paper_id']}")
                print(f"       $$ {latex_clean} $$")
                ctx = eq["context"][:150]
                print(f"       ctx: {ctx}")

        all_results[piste_name] = piste_results

    # ══════════════════════════════════════════════════
    # SAVE
    # ══════════════════════════════════════════════════
    import json
    outfile = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "results", "muninn_equations.json"
    )
    output = {
        "scan": "muninn_equations_v1",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    for piste_name, papers in all_results.items():
        scored = []
        for paper in papers:
            for eq in paper["equations"]:
                s = score_equation_relevance(eq["latex"], piste_name)
                if s > 0:
                    scored.append({
                        "paper_id": paper["paper_id"],
                        "score": s,
                        "latex": eq["latex"][:500],
                        "type": eq["type"],
                        "context": eq["context"][:300],
                    })
        scored.sort(key=lambda x: x["score"], reverse=True)
        output[piste_name] = {
            "n_papers": len(papers),
            "n_scored_equations": len(scored),
            "top_equations": scored[:20],
        }

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {outfile}")
    print(f"Total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
