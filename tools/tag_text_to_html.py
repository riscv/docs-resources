#!/usr/bin/env python3
"""Convert tag text to HTML."""

from typing import Optional

from def_text_to_html import convert_def_text_to_html


def convert_tag_text_to_html(
    tag_text: str,
    target_html_fname: Optional[str] = None,
    is_context: bool = False,
) -> str:
    """Convert tag text to HTML and apply tag-specific display behavior."""
    text = convert_def_text_to_html(tag_text, target_html_fname)

    if text.strip() == "":
        text = "(No text available)"

    if is_context:
        text = "[CONTEXT] " + text

    return text
