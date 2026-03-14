#!/usr/bin/env python3
"""Unit-level tests for tools/adoc_to_html.py."""

# pyright: reportMissingImports=false

import sys
from pathlib import Path

# Ensure tools/ is importable when running from repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from adoc_to_html import Adoc2HTML


def test_basic_formatting():
    text = "**bold** __italic__ ``mono``"
    expected = "<b>bold</b> <i>italic</i> <code>mono</code>"
    assert Adoc2HTML.convert(text) == expected


def test_nested_and_constrained_formatting():
    text = "A *_combo_* test"
    expected = "A <b><i>combo</i></b> test"
    assert Adoc2HTML.convert(text) == expected


def test_sub_super_and_entities():
    text = "2^32^ X~i~ A &amp;le; B and A &amp;#8800; B"
    expected = "2<sup>32</sup> X<sub>i</sub> A &#8804; B and A &#8800; B"
    assert Adoc2HTML.convert(text) == expected


def test_underline_and_unknown_entity_passthrough():
    text = "[.underline]#under# value &mystery; end"
    expected = '<span class="underline">under</span> value &mystery; end'
    assert Adoc2HTML.convert(text) == expected


def main() -> int:
    test_basic_formatting()
    test_nested_and_constrained_formatting()
    test_sub_super_and_entities()
    test_underline_and_unknown_entity_passthrough()
    print("test_adoc_to_html_unit.py: all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
