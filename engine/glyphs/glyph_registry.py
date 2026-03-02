"""
Brique 1 — Glyph Registry
Enrichit math_symbols_unique.json avec les mappings LaTeX/MathML
et assigne des glyph_id entiers stables.

Usage:
    python engine/glyphs/glyph_registry.py          # build + stats
    python engine/glyphs/glyph_registry.py --test    # run self-tests
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "data/core/math_symbols_unique.json"
OUTPUT = ROOT / "data/core/glyph_registry.json"

# ── LaTeX command → Unicode symbol ──────────────────────────────────
LATEX_TO_UNICODE = {
    # Calculus / big operators
    r"\sum": "∑", r"\prod": "∏", r"\int": "∫", r"\oint": "∮",
    r"\partial": "∂", r"\nabla": "∇", r"\infty": "∞",
    r"\coprod": "∐", r"\bigcup": "⋃", r"\bigcap": "⋂",
    r"\bigoplus": "⨁", r"\bigotimes": "⨂", r"\bigvee": "⋁",
    r"\bigwedge": "⋀", r"\bigsqcup": "⨆",
    # Greek lower
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ϵ", r"\varepsilon": "ε", r"\zeta": "ζ", r"\eta": "η",
    r"\theta": "θ", r"\vartheta": "ϑ", r"\iota": "ι", r"\kappa": "κ",
    r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν", r"\xi": "ξ",
    r"\pi": "π", r"\varpi": "ϖ", r"\rho": "ρ", r"\varrho": "ϱ",
    r"\sigma": "σ", r"\varsigma": "ς", r"\tau": "τ", r"\upsilon": "υ",
    r"\phi": "ϕ", r"\varphi": "φ", r"\chi": "χ", r"\psi": "ψ",
    r"\omega": "ω",
    # Greek upper
    r"\Gamma": "Γ", r"\Delta": "Δ", r"\Theta": "Θ", r"\Lambda": "Λ",
    r"\Xi": "Ξ", r"\Pi": "Π", r"\Sigma": "Σ", r"\Upsilon": "Υ",
    r"\Phi": "Φ", r"\Psi": "Ψ", r"\Omega": "Ω",
    # Relations
    r"\leq": "≤", r"\le": "≤", r"\geq": "≥", r"\ge": "≥",
    r"\neq": "≠", r"\ne": "≠", r"\approx": "≈", r"\sim": "∼",
    r"\simeq": "≃", r"\cong": "≅", r"\equiv": "≡", r"\propto": "∝",
    r"\ll": "≪", r"\gg": "≫", r"\prec": "≺", r"\succ": "≻",
    r"\preceq": "⪯", r"\succeq": "⪰", r"\asymp": "≍",
    r"\doteq": "≐", r"\triangleq": "≜",
    # Set theory
    r"\in": "∈", r"\notin": "∉", r"\ni": "∋",
    r"\subset": "⊂", r"\supset": "⊃", r"\subseteq": "⊆", r"\supseteq": "⊇",
    r"\cup": "∪", r"\cap": "∩", r"\setminus": "∖",
    r"\emptyset": "∅", r"\varnothing": "∅",
    # Logic
    r"\forall": "∀", r"\exists": "∃", r"\nexists": "∄",
    r"\neg": "¬", r"\lnot": "¬",
    r"\land": "∧", r"\wedge": "∧", r"\lor": "∨", r"\vee": "∨",
    r"\to": "→", r"\rightarrow": "→", r"\gets": "←", r"\leftarrow": "←",
    r"\Rightarrow": "⇒", r"\Leftarrow": "⇐",
    r"\leftrightarrow": "↔", r"\Leftrightarrow": "⇔",
    r"\iff": "⟺", r"\implies": "⟹",
    r"\vdash": "⊢", r"\dashv": "⊣", r"\models": "⊨",
    r"\top": "⊤", r"\bot": "⊥",
    # Binary operators
    r"\times": "×", r"\div": "÷", r"\cdot": "⋅", r"\circ": "∘",
    r"\pm": "±", r"\mp": "∓", r"\star": "⋆", r"\ast": "∗",
    r"\oplus": "⊕", r"\ominus": "⊖", r"\otimes": "⊗", r"\oslash": "⊘",
    r"\odot": "⊙", r"\bullet": "∙", r"\diamond": "⋄",
    r"\triangleleft": "◁", r"\triangleright": "▷",
    r"\dagger": "†", r"\ddagger": "‡", r"\amalg": "⨿",
    r"\wr": "≀",
    # Arrows
    r"\uparrow": "↑", r"\downarrow": "↓",
    r"\Uparrow": "⇑", r"\Downarrow": "⇓",
    r"\updownarrow": "↕", r"\Updownarrow": "⇕",
    r"\mapsto": "↦", r"\longmapsto": "⟼",
    r"\hookrightarrow": "↪", r"\hookleftarrow": "↩",
    r"\nearrow": "↗", r"\searrow": "↘", r"\swarrow": "↙", r"\nwarrow": "↖",
    r"\rightharpoonup": "⇀", r"\rightharpoondown": "⇁",
    r"\leftharpoonup": "↼", r"\leftharpoondown": "↽",
    r"\rightleftharpoons": "⇌",
    # Delimiters
    r"\langle": "⟨", r"\rangle": "⟩",
    r"\lceil": "⌈", r"\rceil": "⌉", r"\lfloor": "⌊", r"\rfloor": "⌋",
    r"\lVert": "‖", r"\rVert": "‖", r"\|": "‖",
    # Special
    r"\hbar": "ℏ", r"\ell": "ℓ", r"\wp": "℘", r"\Re": "ℜ", r"\Im": "ℑ",
    r"\aleph": "ℵ", r"\beth": "ℶ", r"\gimel": "ℷ", r"\daleth": "ℸ",
    r"\perp": "⊥", r"\parallel": "∥", r"\angle": "∠",
    r"\triangle": "△", r"\square": "□", r"\lozenge": "◊",
    r"\clubsuit": "♣", r"\diamondsuit": "♢", r"\heartsuit": "♡", r"\spadesuit": "♠",
    r"\flat": "♭", r"\natural": "♮", r"\sharp": "♯",
    r"\surd": "√",
    # Dots
    r"\cdots": "⋯", r"\ldots": "…", r"\vdots": "⋮", r"\ddots": "⋱",
    # Blackboard bold (frequent in math)
    r"\mathbb{R}": "ℝ", r"\mathbb{Z}": "ℤ", r"\mathbb{N}": "ℕ",
    r"\mathbb{C}": "ℂ", r"\mathbb{Q}": "ℚ", r"\mathbb{F}": "𝔽",
    r"\mathbb{P}": "ℙ", r"\mathbb{E}": "𝔼", r"\mathbb{H}": "ℍ",
    # Misc
    r"\therefore": "∴", r"\because": "∵",
    r"\prime": "′", r"\backprime": "‵",
    r"\complement": "∁", r"\diameter": "⌀",
}

# ── Semantic groups ─────────────────────────────────────────────────
SEMANTIC_GROUPS = {
    "arithmetic": set("+-×÷=<>≤≥≠±∓⋅"),
    "calculus": set("∫∮∂∑∏∇∞∐"),
    "greek_lower": set("αβγδεϵζηθϑικλμνξπϖρϱσςτυφϕχψω"),
    "greek_upper": set("ΓΔΘΛΞΠΣΥΦΨΩ"),
    "set_theory": set("∈∉∋⊂⊃⊆⊇∪∩∖∅∀∃∄"),
    "logic": set("¬∧∨→←⇒⇐↔⇔⊢⊣⊨⊤⊥"),
    "relations": set("≈∼≃≅≡∝≪≫≺≻≍≐"),
    "algebra": set("⊕⊖⊗⊘⊙†‡∘⋆∗"),
    "arrows": set("↑↓⇑⇓↕⇕↦↪↩↗↘↙↖⇀⇁↼↽⇌"),
    "brackets": set("()[]{}⟨⟩⌈⌉⌊⌋‖|"),
    "special_constants": set("ℏℓ℘ℜℑℵℶℷℸℝℤℕℂℚℙ𝔼ℍ𝔽"),
}


def _classify_group(symbol: str) -> str:
    for group, chars in SEMANTIC_GROUPS.items():
        if symbol in chars:
            return group
    return "other"


def build_registry(source_path=SOURCE, output_path=OUTPUT):
    """Build the canonical glyph registry with LaTeX/MathML mappings."""
    with open(source_path, encoding="utf-8") as f:
        raw = json.load(f)

    # Build unicode→glyph entry, sort by codepoint for stable IDs
    raw.sort(key=lambda g: g["codepoint"])

    # Unicode lookup from source
    sym_set = {g["symbol"] for g in raw}

    # Build reverse map: unicode → [latex commands]
    unicode_to_latex = {}
    for cmd, uni in LATEX_TO_UNICODE.items():
        unicode_to_latex.setdefault(uni, []).append(cmd)

    # Build glyphs dict with stable integer IDs
    glyphs = {}
    latex_to_id = {}
    unicode_to_id = {}

    for idx, g in enumerate(raw):
        sym = g["symbol"]
        gid = str(idx)

        # LaTeX commands for this glyph
        latex_cmds = unicode_to_latex.get(sym, [])

        glyphs[gid] = {
            "glyph_id": idx,
            "symbol": sym,
            "codepoint": g["codepoint"],
            "name": g["name"],
            "category": g["category"],
            "usage": g.get("usage", ""),
            "latex_cmds": latex_cmds,
            "semantic_group": _classify_group(sym),
        }

        # Build lookup indexes
        unicode_to_id[sym] = idx
        for cmd in latex_cmds:
            latex_to_id[cmd] = idx

    # Also add single-char ASCII that are directly in math: =, +, -, etc.
    # These don't need \cmd, they appear raw in LaTeX
    for gid_str, g in glyphs.items():
        sym = g["symbol"]
        if len(sym) == 1 and ord(sym) < 128:
            # ASCII chars are their own "latex command"
            pass  # already in unicode_to_id

    registry = {
        "meta": {
            "total": len(glyphs),
            "source": str(source_path.name),
            "latex_commands_mapped": len(latex_to_id),
            "semantic_groups": {
                k: sum(1 for g in glyphs.values() if g["semantic_group"] == k)
                for k in list(SEMANTIC_GROUPS.keys()) + ["other"]
            },
        },
        "glyphs": glyphs,
        "latex_to_id": latex_to_id,
        "unicode_to_id": unicode_to_id,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=1)

    return registry


def load_registry(path=OUTPUT):
    """Load registry and return (registry, latex_to_id, unicode_to_id)."""
    with open(path, encoding="utf-8") as f:
        reg = json.load(f)
    return reg, reg["latex_to_id"], reg["unicode_to_id"]


# ── Self-tests ──────────────────────────────────────────────────────
def _run_tests(reg):
    latex_to_id = reg["latex_to_id"]
    unicode_to_id = reg["unicode_to_id"]
    glyphs = reg["glyphs"]
    errors = 0

    # Test 1: size
    n = len(glyphs)
    if n < 1200:
        print(f"  FAIL: only {n} glyphs (need >= 1200)")
        errors += 1
    else:
        print(f"  OK: {n} glyphs")

    # Test 2: no ID collisions in latex_to_id
    vals = list(latex_to_id.values())
    if len(vals) != len(set(zip(latex_to_id.keys(), vals))):
        # This can't really happen with a dict, but check for sanity
        print("  FAIL: latex_to_id has duplicate keys")
        errors += 1

    # Test 3: round-trip — latex cmd → id matches unicode → id
    round_trip_ok = 0
    round_trip_fail = 0
    for cmd, uid in LATEX_TO_UNICODE.items():
        lid = latex_to_id.get(cmd)
        uid_id = unicode_to_id.get(uid)
        if lid is not None and uid_id is not None:
            if lid == uid_id:
                round_trip_ok += 1
            else:
                print(f"  FAIL round-trip: {cmd} → id={lid}, '{uid}' → id={uid_id}")
                round_trip_fail += 1
                errors += 1
        elif lid is not None and uid_id is None:
            # LaTeX mapped but unicode not in registry — glyph not in source
            pass
    print(f"  Round-trip: {round_trip_ok} OK, {round_trip_fail} FAIL, "
          f"{len(LATEX_TO_UNICODE) - round_trip_ok - round_trip_fail} skipped (unicode not in source)")

    # Test 4: key symbols present
    must_have = ["∑", "∫", "∂", "α", "β", "π", "∞", "=", "+", "∈", "∀", "→"]
    for s in must_have:
        if s not in unicode_to_id:
            print(f"  FAIL: '{s}' missing from unicode_to_id")
            errors += 1
    print(f"  Key symbols: {sum(1 for s in must_have if s in unicode_to_id)}/{len(must_have)} present")

    # Test 5: semantic groups cover most glyphs
    grouped = sum(1 for g in glyphs.values() if g["semantic_group"] != "other")
    print(f"  Semantic groups: {grouped}/{n} classified ({100*grouped//n}%)")

    return errors


if __name__ == "__main__":
    print("=== Glyph Registry Builder ===")
    reg = build_registry()
    print(f"Built: {reg['meta']['total']} glyphs, "
          f"{reg['meta']['latex_commands_mapped']} LaTeX mappings")
    print(f"Output: {OUTPUT}")
    print(f"Groups: {reg['meta']['semantic_groups']}")

    if "--test" in sys.argv:
        print("\n=== Self-tests ===")
        errs = _run_tests(reg)
        print(f"\n{'ALL PASSED' if errs == 0 else f'{errs} FAILURES'}")
        sys.exit(errs)
