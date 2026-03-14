#!/usr/bin/env python3
"""Unit-level tests for tools/tag_text_to_html.py."""

# pyright: reportMissingImports=false

import sys
from pathlib import Path

# Ensure tools/ is importable when running from repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from tag_text_to_html import convert_tag_text_to_html


def test_empty_tag_text_returns_placeholder():
    assert convert_tag_text_to_html("   ") == "(No text available)"


def test_context_prefix_is_added():
    assert convert_tag_text_to_html("Some text", is_context=True) == "[CONTEXT] Some text"


def test_tag_text_conversion_with_link_target():
    text = "See <<norm:r2>>"
    expected = '[CONTEXT] See <a href="rules.html#norm:r2">norm:r2</a>'
    assert convert_tag_text_to_html(text, target_html_fname="rules.html", is_context=True) == expected


def main() -> int:
    test_empty_tag_text_returns_placeholder()
    test_context_prefix_is_added()
    test_tag_text_conversion_with_link_target()
    print("test_tag_text_to_html_unit.py: all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
