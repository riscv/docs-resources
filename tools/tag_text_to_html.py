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
) -> str:
    """Convert tag text to HTML and apply tag-specific display behavior."""
    if context in ("listing", "literal") and tag_text.strip() != "":
        # Show the code as a browser displays Asciidoctor's HTML output: decode the
        # entities the substitutions emitted, then escape everything as text.
        return f"<pre><code>{escape(unescape(tag_text), quote=False)}</code></pre>"

    text = convert_def_text_to_html(tag_text, target_html_fname)

    if text.strip() == "":
        text = "(No text available)"

    return text
