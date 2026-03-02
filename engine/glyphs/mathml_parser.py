"""
Brique 3 — MathML Formula Parser
Extract glyphs from PMC JATS XML with MathML formulas.

Usage:
    python engine/glyphs/mathml_parser.py --test    # run self-tests
"""
import re, json, sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent.parent

# MathML namespaces (PMC uses mml: prefix)
MML_NS = "{http://www.w3.org/1998/Math/MathML}"

# Tags that contain glyph text
GLYPH_TAGS = {
    f"{MML_NS}mi",   # identifiers: α, β, f, x
    f"{MML_NS}mo",   # operators: +, ∑, ∫, =
    "mi", "mo",       # fallback without namespace
}

# Tags to skip (numbers, text)
SKIP_TAGS = {
    f"{MML_NS}mn", "mn",       # numbers: 2, 3.14
    f"{MML_NS}mtext", "mtext", # plain text
}

# Single ASCII letters are variable names, not glyphs
_ASCII_LETTER_RE = re.compile(r"^[a-zA-Z]$")

# Month from year threshold (same as winter tree)
MONTH_FROM_YEAR = 1980


def _extract_pub_date(root: ET.Element) -> tuple[int | None, str | None]:
    """
    Extract publication date from JATS XML.
    Returns (year, time_key) where time_key is "YYYY-MM" or "YYYY".
    Priority: epub > ppub > first found.
    """
    # Try namespaced and non-namespaced
    for ns in ["", "{http://www.ncbi.nlm.nih.gov/}", "{http://jats.nlm.nih.gov/}"]:
        # Search in front/article-meta
        for pub_date in root.iter(f"{ns}pub-date"):
            pub_type = pub_date.get("pub-type", "")
            if pub_type in ("epub", "ppub", ""):
                year_el = pub_date.find(f"{ns}year")
                if year_el is not None and year_el.text:
                    try:
                        year = int(year_el.text)
                    except ValueError:
                        continue
                    month_el = pub_date.find(f"{ns}month")
                    if month_el is not None and month_el.text:
                        try:
                            month = int(month_el.text)
                            if year >= MONTH_FROM_YEAR:
                                return year, f"{year}-{month:02d}"
                            else:
                                return year, str(year)
                        except ValueError:
                            pass
                    return year, str(year)

    # Fallback: look for <year> anywhere in front matter
    for year_el in root.iter("year"):
        if year_el.text:
            try:
                year = int(year_el.text)
                return year, str(year)
            except ValueError:
                continue

    return None, None


def _extract_math_glyphs(root: ET.Element, unicode_to_id: dict) -> set[int]:
    """Extract glyph IDs from all MathML elements in the XML tree."""
    glyph_ids = set()

    # Find all math elements (with and without namespace)
    math_elements = list(root.iter(f"{MML_NS}math")) + list(root.iter("math"))

    for math_el in math_elements:
        for el in math_el.iter():
            if el.tag in GLYPH_TAGS and el.text:
                text = el.text.strip()
                if not text:
                    continue
                # Skip single ASCII letters (variable names, not glyphs)
                if _ASCII_LETTER_RE.match(text):
                    continue
                # Skip pure numbers
                if text.replace(".", "").replace("-", "").isdigit():
                    continue
                # Try each character
                for ch in text:
                    gid = unicode_to_id.get(ch)
                    if gid is not None:
                        # Skip ASCII letters and digits
                        if ch.isascii() and (ch.isalpha() or ch.isdigit()):
                            continue
                        if ch in " \t\n":
                            continue
                        glyph_ids.add(gid)

    return glyph_ids


def parse_pmc_xml(xml_content: bytes | str, unicode_to_id: dict,
                  cutoff_year: int = 2015) -> tuple[list[int], str | None]:
    """
    Parse a PMC JATS XML article and extract glyphs + publication date.

    Returns:
        (glyph_ids, time_key) — sorted list of unique glyph IDs and period key
        ([], None) if no math found, parse error, or year > cutoff
    """
    try:
        if isinstance(xml_content, bytes):
            # Handle encoding declaration in XML
            root = ET.fromstring(xml_content)
        else:
            root = ET.fromstring(xml_content.encode("utf-8"))
    except ET.ParseError:
        return [], None

    # Extract date
    year, time_key = _extract_pub_date(root)
    if year is None or year > cutoff_year:
        return [], None

    # Extract glyphs
    glyph_ids = _extract_math_glyphs(root, unicode_to_id)
    if not glyph_ids:
        return [], time_key   # return time_key so scanner can distinguish nomath vs cutoff

    return sorted(glyph_ids), time_key


def count_math_elements(xml_content: bytes | str) -> int:
    """Quick count of <mml:math> / <math> elements without full parsing."""
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode("utf-8", errors="replace")
    return xml_content.count("<mml:math") + xml_content.count("<math ")


# ── Self-tests ──────────────────────────────────────────────────────
_SAMPLE_PMC_1 = """<?xml version="1.0" encoding="UTF-8"?>
<article xmlns:mml="http://www.w3.org/1998/Math/MathML">
  <front><article-meta>
    <pub-date pub-type="epub"><year>2010</year><month>3</month></pub-date>
  </article-meta></front>
  <body><p>The equation
    <mml:math>
      <mml:mi>\u03b1</mml:mi>
      <mml:mo>+</mml:mo>
      <mml:mi>\u03b2</mml:mi>
      <mml:mo>=</mml:mo>
      <mml:mi>\u03b3</mml:mi>
    </mml:math>
    and also
    <mml:math>
      <mml:mo>\u222b</mml:mo>
      <mml:mi>f</mml:mi>
      <mml:mo>(</mml:mo>
      <mml:mi>x</mml:mi>
      <mml:mo>)</mml:mo>
      <mml:mi>d</mml:mi>
      <mml:mi>x</mml:mi>
    </mml:math>
  </p></body>
</article>
""".encode("utf-8")

_SAMPLE_PMC_2020 = _SAMPLE_PMC_1.replace(b"<year>2010</year>", b"<year>2020</year>")
_SAMPLE_PMC_NOMATH = b"""<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front><article-meta>
    <pub-date pub-type="epub"><year>2005</year><month>7</month></pub-date>
  </article-meta></front>
  <body><p>No math here.</p></body>
</article>
"""


def _run_tests():
    from engine.glyphs.glyph_registry import load_registry
    reg, _, uni = load_registry()

    errors = 0

    # Test 1: basic parsing
    gids, tk = parse_pmc_xml(_SAMPLE_PMC_1, uni)
    syms = {reg["glyphs"][str(g)]["symbol"] for g in gids}
    if not gids:
        print(f"  FAIL: no glyphs extracted from sample 1")
        errors += 1
    else:
        print(f"  OK: sample 1 → {len(gids)} glyphs: {syms}")

    # Test 2: date extraction
    if tk != "2010-03":
        print(f"  FAIL: expected time_key '2010-03', got '{tk}'")
        errors += 1
    else:
        print(f"  OK: time_key = '{tk}'")

    # Test 3: expected glyphs present
    must_have = {"α", "β", "γ", "+", "="}
    missing = must_have - syms
    if missing:
        print(f"  FAIL: missing {missing}")
        errors += 1
    else:
        print(f"  OK: key symbols {must_have} present")

    # Test 4: integral present
    if "∫" in syms:
        print("  OK: ∫ (integral) found")
    else:
        print(f"  WARN: ∫ not found in {syms} (might not be in unicode_to_id)")

    # Test 5: cutoff 2015
    gids2, tk2 = parse_pmc_xml(_SAMPLE_PMC_2020, uni, cutoff_year=2015)
    if gids2:
        print(f"  FAIL: 2020 paper should be filtered (cutoff=2015)")
        errors += 1
    else:
        print("  OK: 2020 paper filtered by cutoff")

    # Test 6: no math → empty
    gids3, tk3 = parse_pmc_xml(_SAMPLE_PMC_NOMATH, uni)
    if gids3:
        print(f"  FAIL: no-math paper should return empty")
        errors += 1
    else:
        print("  OK: no-math paper → empty")

    # Test 7: count_math_elements
    cnt = count_math_elements(_SAMPLE_PMC_1)
    if cnt >= 2:
        print(f"  OK: count_math_elements = {cnt}")
    else:
        print(f"  FAIL: count_math_elements = {cnt}, expected >= 2")
        errors += 1

    # Test 8: single ASCII letters not counted as glyphs
    # 'f', 'x', 'd' from the integral formula should NOT be in output
    ascii_glyphs = {s for s in syms if len(s) == 1 and s.isascii() and s.isalpha()}
    if ascii_glyphs:
        print(f"  WARN: ASCII letters in output: {ascii_glyphs} — might be intentional")
    else:
        print("  OK: no single ASCII letters in output")

    return errors


if __name__ == "__main__":
    if "--test" in sys.argv:
        print("=== MathML Parser Self-tests ===")
        errs = _run_tests()
        print(f"\n{'ALL PASSED' if errs == 0 else f'{errs} FAILURES'}")
        sys.exit(errs)
    else:
        print("Usage: python engine/glyphs/mathml_parser.py --test")
