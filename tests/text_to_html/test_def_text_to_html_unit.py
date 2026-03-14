#!/usr/bin/env python3
"""Unit-level tests for tools/def_text_to_html.py."""

# pyright: reportMissingImports=false

import sys
from pathlib import Path

# Ensure tools/ is importable when running from repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from def_text_to_html import (
    convert_adoc_links_to_html,
    convert_def_text_to_html,
    convert_newlines_to_html,
    convert_tags_tables_to_html,
    extract_tags_table_cells,
    tag2html_link,
)


def test_tag2html_link_with_and_without_target():
    assert tag2html_link("norm:abc", "norm:abc") == '<a href="#norm:abc">norm:abc</a>'
    assert tag2html_link("norm:abc", "see rule", "rules.html") == '<a href="rules.html#norm:abc">see rule</a>'


def test_extract_tags_table_cells_and_newlines():
    assert extract_tags_table_cells("A | B | C ") == ["A", "B", "C"]
    assert extract_tags_table_cells("") == []
    assert convert_newlines_to_html("a\nb") == "a<br>b"


def test_convert_adoc_links_to_html_default_and_custom_text():
    text = "See <<norm:rule_1>> and <<norm:rule_2,Rule Two>>"
    expected = (
        'See <a href="#norm:rule_1">norm:rule_1</a> and '
        '<a href="#norm:rule_2">Rule Two</a>'
    )
    assert convert_adoc_links_to_html(text) == expected


def test_convert_adoc_links_to_html_with_unicode_escaped_delimiters():
    text = "Refer to &#60;&#60;norm:r1,Rule 1&#62;&#62;"
    expected = 'Refer to <a href="spec.html#norm:r1">Rule 1</a>'
    assert convert_adoc_links_to_html(text, "spec.html") == expected


def test_convert_tags_tables_to_html():
    text = "Col A | Col B===\n1 | 2¶3 | 4\n==="
    html = convert_tags_tables_to_html(text)
    assert "<table>" in html
    assert "<thead><tr><th>Col A</th><th>Col B</th></tr></thead>" in html
    assert "<tbody><tr><td>1</td><td>2</td></tr><tr><td>3</td><td>4</td></tr></tbody>" in html
    assert html.endswith("</table>")


def test_convert_def_text_to_html_pipeline():
    text = "Use <<norm:r1,Rule>>\nAnd **bold**"
    expected = 'Use <a href="x.html#norm:r1">Rule</a><br>And <b>bold</b>'
    assert convert_def_text_to_html(text, "x.html") == expected


def main() -> int:
    test_tag2html_link_with_and_without_target()
    test_extract_tags_table_cells_and_newlines()
    test_convert_adoc_links_to_html_default_and_custom_text()
    test_convert_adoc_links_to_html_with_unicode_escaped_delimiters()
    test_convert_tags_tables_to_html()
    test_convert_def_text_to_html_pipeline()
    print("test_def_text_to_html_unit.py: all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
