#!/usr/bin/env python3
"""Basic regression tests for Adoc2HTML formatting conversion."""

import sys
from pathlib import Path

# Ensure tools/ is importable when running from repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from adoc_to_html import Adoc2HTML


def test_unconstrained_bold_italics_and_code():
    text = "**bold** __italic__ ``mono``"
    expected = "<b>bold</b> <i>italic</i> <code>mono</code>"
    assert Adoc2HTML.convert(text) == expected


def test_constrained_and_nested():
    text = "A *_combo_* test"
    expected = "A <b><i>combo</i></b> test"
    assert Adoc2HTML.convert(text) == expected


def test_superscript_and_subscript():
    text = "2^32^ X~i~"
    expected = "2<sup>32</sup> X<sub>i</sub>"
    assert Adoc2HTML.convert(text) == expected


def test_underline():
    text = "[.underline]#under#"
    expected = "<span class=\"underline\">under</span>"
    assert Adoc2HTML.convert(text) == expected


def test_entity_conversion_and_escape_cleanup():
    text = "A &amp;le; B and A &amp;#8800; B"
    expected = "A &#8804; B and A &#8800; B"
    assert Adoc2HTML.convert(text) == expected


def test_unknown_entity_is_preserved():
    text = "value &mystery; end"
    expected = "value &mystery; end"
    assert Adoc2HTML.convert(text) == expected


def main() -> int:
    test_unconstrained_bold_italics_and_code()
    test_constrained_and_nested()
    test_superscript_and_subscript()
    test_underline()
    test_entity_conversion_and_escape_cleanup()
    test_unknown_entity_is_preserved()
    print("test_adoc_to_html.py: all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
