# Tools Directory

This directory contains command-line generators and shared Python helper modules used by the docs-resources build and test flow.

## Python Scripts At A Glance

| Script | Type | Purpose |
|---|---|---|
| adoc_to_html.py | Helper module | Converts inline AsciiDoc formatting and entities to HTML. |
| def_text_to_html.py | Helper module | Converts definition text to HTML, including table and anchor-link handling. |
| tag_text_to_html.py | Helper module | Converts tag text to HTML and applies tag-specific display behavior. |
| shared_utils.py | Helper module | Shared logging helpers and JSON loader. |
| create_normative_rules.py | CLI tool | Builds normative-rules JSON or HTML from tag JSON files. |

## Script Details

### adoc_to_html.py

Purpose:
- Provides the Adoc2HTML class for converting common inline AsciiDoc notation to HTML.

Key capabilities:
- Constrained and unconstrained bold/italics/monospace conversion.
- Superscript and subscript conversion.
- Underline conversion for [.underline]#...#.
- Entity normalization (for example &amp;le; to &#8804;).

Usage:
- Imported by other tools and tests (not a standalone CLI entry point).

### def_text_to_html.py

Purpose:
- Converts definition text blocks to HTML for downstream reports/pages.

Key capabilities:
- Pipeline conversion via convert_def_text_to_html.
- Conversion of tagged-table blocks into HTML tables.
- Conversion of AsciiDoc anchor links (for example <<tag>> and <<tag,text>>).
- Newline conversion and link helper utilities.

Usage:
- Imported by create_normative_rules.py and tag_text_to_html.py.

### tag_text_to_html.py

Purpose:
- Converts tag text to HTML and applies tag-specific display behavior.

Key capabilities:
- Pipeline conversion via convert_tag_text_to_html.
- Returns a "(No text available)" placeholder for empty tag text.

Usage:
- Imported by create_normative_rules.py.

### shared_utils.py

Purpose:
- Provides shared logging helpers and a JSON file loader used across tools scripts.

Key capabilities:
- make_log_helpers: creates script-scoped error/info/fatal callable helpers.
- load_json_object: safe JSON file loader with error reporting.

Usage:
- Imported by create_normative_rules.py.

### create_normative_rules.py

Purpose:
- Creates the normative-rules JSON/HTML outputs for a standard from the tag JSON files that the tags.rb Asciidoctor backend extracts.
- Every tag is one normative rule. The rule name is the tag name without the "norm:" prefix; there is no separate rule definition and no mapping between rules and tags.

Key capabilities:
- Uses each tag file's section tree to give every rule the title of the chapter (level-1 section) containing its tag.
- JSON output conforms to schemas/norm-rules-schema.json (name, chapter_name, text, tag_filename, and stds_doc_url for each rule).
- HTML output has one table per chapter in document order, with an anchor per rule name and a link from each rule to its tag in the standard.
- Fails on duplicate tag names and on tag names without the "norm:" prefix.

Usage:
```bash
python3 tools/create_normative_rules.py -j -t build/test-ch1-norm-tags.json -tag2url build/test-ch1-norm-tags.json test-ch1.html build/test-norm-rules.json
python3 tools/create_normative_rules.py --html -t build/test-ch1-norm-tags.json -tag2url build/test-ch1-norm-tags.json test-ch1.html build/test-norm-rules.html
```

## Notes

- These scripts are exercised by targets in the repository Makefile.
- Unit-level tests for helper modules live under tests/adoc2html, tests/shared_utils, and tests/text_to_html.
