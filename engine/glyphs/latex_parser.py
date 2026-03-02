"""
Brique 2 — LaTeX Formula Parser
Extract math environments from .tex files and tokenize into glyph IDs.

Usage:
    python engine/glyphs/latex_parser.py --test     # run self-tests
"""
import re, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# ── Math environment extraction ─────────────────────────────────────
# Order matters: match $$ before $, \[ before \(
_MATH_PATTERNS = [
    # Display math
    re.compile(r"\$\$(.+?)\$\$", re.DOTALL),
    re.compile(r"\\\[(.+?)\\\]", re.DOTALL),
    # Environments
    re.compile(r"\\begin\{equation\*?\}(.+?)\\end\{equation\*?\}", re.DOTALL),
    re.compile(r"\\begin\{align\*?\}(.+?)\\end\{align\*?\}", re.DOTALL),
    re.compile(r"\\begin\{eqnarray\*?\}(.+?)\\end\{eqnarray\*?\}", re.DOTALL),
    re.compile(r"\\begin\{multline\*?\}(.+?)\\end\{multline\*?\}", re.DOTALL),
    re.compile(r"\\begin\{gather\*?\}(.+?)\\end\{gather\*?\}", re.DOTALL),
    re.compile(r"\\begin\{displaymath\}(.+?)\\end\{displaymath\}", re.DOTALL),
    re.compile(r"\\begin\{math\}(.+?)\\end\{math\}", re.DOTALL),
    # Inline math (must be last — greedy risk)
    re.compile(r"\\\((.+?)\\\)", re.DOTALL),
    re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL),
]

# Structural LaTeX commands to IGNORE (not glyphs)
_STRUCTURE_CMDS = {
    r"\frac", r"\dfrac", r"\tfrac", r"\cfrac",
    r"\sqrt", r"\root",
    r"\text", r"\textrm", r"\textbf", r"\textit", r"\textsf",
    r"\mathrm", r"\mathbf", r"\mathit", r"\mathsf", r"\mathcal",
    r"\mathfrak", r"\mathscr",
    r"\operatorname", r"\DeclareMathOperator",
    r"\left", r"\right", r"\bigl", r"\bigr", r"\Bigl", r"\Bigr",
    r"\big", r"\Big", r"\bigg", r"\Bigg",
    r"\begin", r"\end", r"\label", r"\tag", r"\nonumber", r"\notag",
    r"\hspace", r"\vspace", r"\quad", r"\qquad",
    r"\over", r"\atop", r"\above",
    r"\underbrace", r"\overbrace", r"\underset", r"\overset",
    r"\stackrel", r"\substack",
    r"\limits", r"\nolimits", r"\displaystyle", r"\textstyle",
    r"\scriptstyle", r"\scriptscriptstyle",
    r"\phantom", r"\hphantom", r"\vphantom",
    r"\color", r"\textcolor",
    r"\mbox", r"\hbox", r"\vbox",
    r"\rule", r"\strut", r"\smash",
}

# Common "function" names in LaTeX that aren't glyphs
_FUNC_CMDS = {
    r"\sin", r"\cos", r"\tan", r"\cot", r"\sec", r"\csc",
    r"\arcsin", r"\arccos", r"\arctan",
    r"\sinh", r"\cosh", r"\tanh", r"\coth",
    r"\log", r"\ln", r"\exp", r"\lg",
    r"\det", r"\dim", r"\ker", r"\hom",
    r"\lim", r"\limsup", r"\liminf",
    r"\sup", r"\inf", r"\max", r"\min",
    r"\arg", r"\deg", r"\gcd",
    r"\Pr", r"\mod", r"\bmod", r"\pmod",
}

# Regex to find LaTeX commands: \cmdname or \cmdname{arg}
_CMD_RE = re.compile(r"\\([a-zA-Z]+|[^a-zA-Z])")

# Regex to strip comments (lines starting with %)
_COMMENT_RE = re.compile(r"(?m)%.*$")


def strip_comments(tex: str) -> str:
    """Remove LaTeX comments (% to end of line)."""
    return _COMMENT_RE.sub("", tex)


def extract_math_envs(tex: str) -> list[str]:
    """Extract all math environments from a .tex string."""
    tex = strip_comments(tex)
    envs = []
    for pat in _MATH_PATTERNS:
        for m in pat.finditer(tex):
            envs.append(m.group(1))
    return envs


def tokenize_math(math_text: str, latex_to_id: dict, unicode_to_id: dict) -> set[int]:
    """
    Tokenize a math environment string into a set of glyph IDs.
    Returns deduplicated set (each glyph counted once per environment).
    """
    ids = set()

    # Pass 1: match LaTeX commands
    for m in _CMD_RE.finditer(math_text):
        cmd = "\\" + m.group(1)

        # Skip structural and function commands
        if cmd in _STRUCTURE_CMDS or cmd in _FUNC_CMDS:
            continue

        # Try direct lookup
        gid = latex_to_id.get(cmd)
        if gid is not None:
            ids.add(gid)
            continue

        # Try \mathbb{X} pattern
        pos = m.end()
        if cmd == r"\mathbb" and pos < len(math_text) and math_text[pos] == "{":
            close = math_text.find("}", pos)
            if close > pos:
                full_cmd = cmd + math_text[pos:close + 1]
                gid = latex_to_id.get(full_cmd)
                if gid is not None:
                    ids.add(gid)

    # Pass 2: match raw unicode characters in the text
    for ch in math_text:
        if ch in unicode_to_id:
            # Skip ASCII letters (a-z, A-Z) and digits — not glyphs
            if ch.isascii() and (ch.isalpha() or ch.isdigit()):
                continue
            # Skip whitespace and common non-math chars
            if ch in " \t\n\r{}^_&\\,;:.!?'\"":
                continue
            ids.add(unicode_to_id[ch])

    return ids


def parse_tex_glyphs(tex_content: str, latex_to_id: dict, unicode_to_id: dict,
                     min_envs: int = 1) -> list[int]:
    """
    Full pipeline: tex string → deduplicated list of glyph IDs found in the paper.
    Returns empty list if fewer than min_envs math environments found.
    """
    envs = extract_math_envs(tex_content)
    if len(envs) < min_envs:
        return []

    all_ids = set()
    for env in envs:
        all_ids.update(tokenize_math(env, latex_to_id, unicode_to_id))

    return sorted(all_ids)


def parse_tex_bytes(tex_bytes: bytes, latex_to_id: dict, unicode_to_id: dict,
                    min_envs: int = 1) -> list[int]:
    """
    Bytes-safe version for reading from tar.extractfile().
    Tries utf-8, falls back to latin-1.
    """
    try:
        text = tex_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = tex_bytes.decode("latin-1", errors="replace")
    return parse_tex_glyphs(text, latex_to_id, unicode_to_id, min_envs)


# ── Self-tests ──────────────────────────────────────────────────────
_SAMPLE_TEX = r"""
\documentclass{article}
\begin{document}
The heat equation:
\begin{equation}
    \frac{\partial \phi}{\partial t} = \nabla^2 \phi + \alpha \phi
\end{equation}
Let $x \in \mathbb{R}$ and consider $\sum_{k=0}^{\infty} a_k$.

%% This is a comment with \beta — should be ignored
Also $$E = mc^2$$ and \[ F = ma \]
\end{document}
"""

_SAMPLE_TEX_2 = r"""
\begin{align}
    \int_0^\infty e^{-x^2} dx &= \frac{\sqrt{\pi}}{2} \\
    \forall \epsilon > 0, \exists \delta > 0
\end{align}
"""


def _run_tests():
    from engine.glyphs.glyph_registry import load_registry
    reg, lat, uni = load_registry()

    errors = 0

    # Test 1: extraction
    envs = extract_math_envs(_SAMPLE_TEX)
    if len(envs) < 4:
        print(f"  FAIL: expected >= 4 envs, got {len(envs)}: {envs}")
        errors += 1
    else:
        print(f"  OK: {len(envs)} math environments extracted")

    # Test 2: comments stripped
    full = strip_comments(_SAMPLE_TEX)
    if r"\beta" in full:
        print("  FAIL: comment not stripped")
        errors += 1
    else:
        print("  OK: comments stripped")

    # Test 3: glyph extraction from sample 1
    gids = parse_tex_glyphs(_SAMPLE_TEX, lat, uni)
    syms = {reg["glyphs"][str(g)]["symbol"] for g in gids}
    must_have = {"∂", "∇", "α", "∈", "∑", "∞"}
    missing = must_have - syms
    if missing:
        print(f"  FAIL: missing glyphs: {missing} (got: {syms})")
        errors += 1
    else:
        print(f"  OK: sample 1 → {len(gids)} glyphs, includes {must_have}")

    # Test 4: \mathbb{R} → ℝ
    if "ℝ" not in syms:
        # ℝ might not be in source file — check
        if uni.get("ℝ") is not None:
            print(f"  FAIL: \\mathbb{{R}} not found (syms: {syms})")
            errors += 1
        else:
            print("  SKIP: ℝ not in registry source")
    else:
        print("  OK: \\mathbb{R} → ℝ")

    # Test 5: sample 2 — integral, forall, exists
    gids2 = parse_tex_glyphs(_SAMPLE_TEX_2, lat, uni)
    syms2 = {reg["glyphs"][str(g)]["symbol"] for g in gids2}
    must2 = {"∫", "∀", "∃"}
    missing2 = must2 - syms2
    if missing2:
        print(f"  FAIL: sample 2 missing: {missing2} (got: {syms2})")
        errors += 1
    else:
        print(f"  OK: sample 2 → {len(gids2)} glyphs, includes {must2}")

    # Test 6: structural commands NOT in output
    struct_syms = {"frac", "sqrt", "begin", "end"}
    names = {reg["glyphs"][str(g)]["name"] for g in gids}
    bad = {n for n in names if any(s in n.lower() for s in struct_syms)}
    if bad:
        print(f"  FAIL: structural pollution: {bad}")
        errors += 1
    else:
        print("  OK: no structural command pollution")

    # Test 7: bytes version
    gids_b = parse_tex_bytes(_SAMPLE_TEX.encode("utf-8"), lat, uni)
    if gids_b != gids:
        print(f"  FAIL: bytes version differs from string version")
        errors += 1
    else:
        print("  OK: bytes version matches string version")

    return errors


if __name__ == "__main__":
    if "--test" in sys.argv:
        print("=== LaTeX Parser Self-tests ===")
        errs = _run_tests()
        print(f"\n{'ALL PASSED' if errs == 0 else f'{errs} FAILURES'}")
        sys.exit(errs)
    else:
        print("Usage: python engine/glyphs/latex_parser.py --test")
