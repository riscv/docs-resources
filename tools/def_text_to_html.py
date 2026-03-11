#!/usr/bin/env python3
"""Shared utilities for converting definition text to HTML."""

import re
from typing import List, Optional

from adoc_to_html import Adoc2HTML

# Constants
MAX_TABLE_ROWS = 12
LT_UNICODE_STR = "&#60;"
GT_UNICODE_STR = "&#62;"


def tag2html_link(tag_ref: str, link_text: str, target_html_fname: Optional[str] = None) -> str:
    """Create HTML link to tag. If no target_html_fname is provided, assumes anchor is in same HTML file as link."""
    if target_html_fname is None:
        target_html_fname = ""

    return f'<a href="{target_html_fname}#{tag_ref}">{link_text}</a>'


def convert_def_text_to_html(text: str, target_html_fname: Optional[str] = None) -> str:
    """Convert all the various definition text formats to HTML."""
    text = Adoc2HTML.convert(text)
    text = convert_tags_tables_to_html(text)
    text = convert_newlines_to_html(text)
    text = convert_adoc_links_to_html(text, target_html_fname)

    return text


def convert_tags_tables_to_html(text: str) -> str:
    """Convert the tagged text containing entire tables. Uses format created by "tags" Asciidoctor backend."""

    def replacer(match):
        # Found a "tags" formatted table
        heading = match.group(1).rstrip('\n')
        rows_text = match.group(2)
        rows = rows_text.split("¶")  # Split into list of rows

        ret = "<table>"  # Start html table

        # Add heading if present
        heading_cells = extract_tags_table_cells(heading)
        if heading_cells:
            ret += "<thead>"
            ret += "<tr>"
            ret += "".join(f"<th>{cell}</th>" for cell in heading_cells)
            ret += "</tr>"
            ret += "</thead>"

        # Add each row
        ret += "<tbody>"
        for index, row in enumerate(rows):
            if index < MAX_TABLE_ROWS:
                ret += "<tr>"
                row_cells = extract_tags_table_cells(row)
                ret += "".join(f"<td>{cell}</td>" for cell in row_cells)
                ret += "</tr>"
            elif index == MAX_TABLE_ROWS:
                ret += "<tr>"
                row_cells = extract_tags_table_cells(row)
                ret += "".join("<td>...</td>" for _ in row_cells)
                ret += "</tr>"

        ret += "</tbody>"
        ret += "</table>"  # End html table

        return ret

    pattern = r'(.*?)===\n(.+)\n==='
    return re.sub(pattern, replacer, text, flags=re.DOTALL)


def extract_tags_table_cells(row: str) -> List[str]:
    """Return list of table columns from one row/header of a table.

    Returns empty list if row is None or the empty string.
    """
    if not row:
        return []

    # Split row fields with pipe symbol. The -1 passed to split ensures trailing null fields are not suppressed.
    return [cell.strip() for cell in row.split('|')]


def convert_newlines_to_html(text: str) -> str:
    """Convert newlines to <br>."""
    return text.replace('\n', '<br>')


def convert_adoc_links_to_html(text: str, target_html_fname: Optional[str] = None) -> str:
    """Convert adoc links to HTML links.

    Supported adoc link formats:
        <<link>>
        <<link,custom text>>

    If target_html_fname is not provided, link will assume anchor is in the same HTML file as the link.
    """

    def replacer(match):
        link_content = match.group(2)

        # Look to see if custom text has been provided.
        split_texts = [t.strip() for t in link_content.split(",")]

        if len(split_texts) == 0:
            return link_content
        elif len(split_texts) == 1:
            return tag2html_link(split_texts[0], split_texts[0], target_html_fname)
        elif len(split_texts) == 2:
            return tag2html_link(split_texts[0], split_texts[1], target_html_fname)
        else:
            return link_content

    # Note that I'm using the non-greedy regular expression (? after +) otherwise the regular expression
    # will return multiple <<link>> in the same text as one.
    pattern = rf'(<<|{re.escape(LT_UNICODE_STR)}{re.escape(LT_UNICODE_STR)})(.+?)(>>|{re.escape(GT_UNICODE_STR)}{re.escape(GT_UNICODE_STR)})'
    return re.sub(pattern, replacer, text)
