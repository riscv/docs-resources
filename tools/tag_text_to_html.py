#!/usr/bin/env python3
"""Convert tag text to HTML."""

from html import escape, unescape
from typing import Optional

from def_text_to_html import convert_def_text_to_html


def convert_tag_text_to_html(
    tag_text: str,
    target_html_fname: Optional[str] = None,
    *,
    context: Optional[str] = None,
    decode_entities: bool = False,
) -> str:
    """Convert tag text to HTML and apply tag-specific display behavior."""
    if context in ("listing", "literal"):
        # Preserve the display of Asciidoctor entities and keep all code as text.
        text = unescape(tag_text) if decode_entities else tag_text
        return f"<pre><code>{escape(text, quote=False)}</code></pre>"

    text = convert_def_text_to_html(tag_text, target_html_fname)

    if text.strip() == "":
        text = "(No text available)"

    return text
