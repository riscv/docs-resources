#!/usr/bin/env python3
"""Convert tag text to HTML."""

from typing import Optional

from def_text_to_html import convert_def_text_to_html


def convert_tag_text_to_html(
    tag_text: str,
    target_html_fname: Optional[str] = None,
) -> str:
    """Convert tag text to HTML and apply tag-specific display behavior."""
    text = convert_def_text_to_html(tag_text, target_html_fname)

    if text.strip() == "":
        text = "(No text available)"

    return text
