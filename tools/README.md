# Tools Directory

This directory contains command-line generators and shared Python helper modules used by the docs-resources build and test flow.

## Python Scripts At A Glance

| Script | Type | Purpose |
|---|---|---|
| adoc_to_html.py | Helper module | Converts inline AsciiDoc formatting and entities to HTML. |
| def_text_to_html.py | Helper module | Converts definition text to HTML, including table and anchor-link handling. |
| tag_text_to_html.py | Helper module | Converts tag text to HTML and applies tag-specific display behavior. |
| shared_utils.py | Helper module | Shared constants, logging helpers, YAML/JSON loaders, and common validators/formatters. |
| create_normative_rules.py | CLI tool | Builds normative-rules JSON or HTML from rule-definition YAML and tag JSON files. |
| create_params.py | CLI tool | Builds params JSON or HTML from normative-rules JSON and parameter-definition YAML files. |
| create_param_appendix.py | CLI tool | Generates parameter-row AsciiDoc fragments plus table include files from params JSON and a table-layout YAML file. |
| detect_tag_changes.py | CLI tool | Compares two tag JSON files and reports additions, deletions, and modifications. |

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
- Imported by create_normative_rules.py, create_params.py, and tag_text_to_html.py.

### tag_text_to_html.py

Purpose:
- Converts one normative tag text string to display-ready HTML.

Key capabilities:
- Uses def_text_to_html conversion pipeline.
- Handles empty content with a placeholder.
- Adds optional [CONTEXT] prefix.

Usage:
- Imported by create_normative_rules.py and create_params.py.

### shared_utils.py

Purpose:
- Central shared utilities used by multiple scripts.

Key capabilities:
- Shared constants for standards object kinds and categories.
- Shared logging-helper factory.
- JSON and YAML loader wrappers with consistent fatal-error handling.
- Shared format_param_feature, check_kind, and check_impldef_cat routines.

Usage:
- Imported by create_normative_rules.py, create_params.py, and create_param_appendix.py.

### create_normative_rules.py

Purpose:
- Creates normative rules output from definition YAML and extracted tag JSON inputs.

Inputs:
- One or more normative-rule definition YAML files (-d).
- One or more tag JSON files (-t).
- Tag-file to URL mappings (-tag2url).

Outputs:
- JSON (default) or HTML output file.

Typical command:
```bash
python3 tools/create_normative_rules.py \
  -d tests/norm-rule/test-ch1.yaml \
  -d tests/norm-rule/test-ch2.yaml \
  -t /build/test-ch1-norm-tags.json \
  -t /build/test-ch2-norm-tags.json \
  -tag2url /build/test-ch1-norm-tags.json test-ch1.html \
  -tag2url /build/test-ch2-norm-tags.json test-ch2.html \
  build/test-norm-rules.json
```

### create_params.py

Purpose:
- Creates params output from normative-rules JSON plus parameter-definition YAML files.

Inputs:
- Normative-rules JSON (-n / --norm-rules).
- One or more parameter definition YAML files (-d / --param-def).

Outputs:
- JSON (default) or HTML file.

Typical commands:
```bash
python3 tools/create_params.py \
  --norm-rules build/test-norm-rules.json \
  --param-def tests/params/test-ch1.yaml \
  --param-def tests/params/test-ch2.yaml \
  --output build/test-params.json
```

```bash
python3 tools/create_params.py --html \
  --norm-rules build/test-norm-rules.json \
  --param-def tests/params/test-ch1.yaml \
  --param-def tests/params/test-ch2.yaml \
  --output build/test-params.html
```

Parameter Type Encoding:
- Each parameter definition must include exactly one of `type` or `range`.
- `type` may be one of:
  - Unsigned integers: `boolean`, `bit`, `byte`, `hword`, `word`, `dword`, `uint`
  - Signed integers: `int`
  - Enum composed of strings (e.g. `[ABC, DEF]`) or integers (e.g., `[32, 64]`)
- `width` (in bits) is required when `type` is `int` or `uint`.
  - Integer width: `2..64` (inclusive, use `bit` for 1-bit integers)
  - Or the name of another parameter that supplies the bit width
- `array` is optional and, when present, wraps the base integer/range/list as a fixed-length array.
  - Format: `[lo, hi]` where `lo >= 0` and `lo <= hi`
- `range` is an inclusive integer range of two integers.
  - Format: `[lo, hi]` where `lo < hi` (negative values are allowed)

Examples:
```yaml
# Scalar fixed-width integer
- name: UINT_OF_WIDTH_32
  impl-def: UINT32
  type: uint
  width: 32

# Scalar width derived from another parameter
- name: MXLEN
  type: [32, 64]
  description: Supported machine register widths.
- name: INT_MXLEN
  type: int
  width: MXLEN
  description: Signed integer whose width is MXLEN.

# Lists (AKA enums) values
- name: MODE
  impl-def: MODE
  type: [A, B, C]
- name: XLEN
  impl-defs: [XLEN1, XLEN2]
  type: [32, 64]

# Range form (inclusive)
- name: PRIORITY
  impl-def: PRIORITY
  range: [-10, 20]

# Array of uint values with fixed element count
- name: ARRAY_OF_UINT5
  impl-def: ARRAY
  type: uint
  width: 5
  array: [0, 3]

# Array of ranged integers
- name: ARRAY_OF_NEG10TO20
  impl-def: ARRAY
  range: [-10, 20]
  array: [0, 3]
```

CSR Definition Encoding:
- Use `csr_definitions` entries for CSRs, with `reg-name` (single CSR) or `reg-names` (multiple CSRs).
- A CSR entry must include exactly one selector property:
  - `type`
  - `width`
  - `ro-mask`
- `ro-value` is optional, but if present then `ro-mask` is required.
- CSR `width` must be a string naming an existing parameter that supplies the width.
- Every CSR entry must include `impl-def` or `impl-defs`.
  - At least one referenced normative rule must provide `impl-def-category`.
  - Any provided `impl-def-category` values across referenced impl-defs must agree.
  - The category is mapped into CSR category (`WARL`/`WLRL`) for output grouping.

CSR selector properties:
- `type`: List of legal integer values for the CSR (or CSR field).
  - Format: `[v0, v1, ...]` where each value is an integer.
- `width`: Name of a parameter that defines CSR width.
  - Format: `width: <parameter_name>`.
- `ro-mask`/`ro-value`: Bit-mask model for read-only bits.
  - `ro-mask` marks read-only bits (`1` = read-only, `0` = read-write).
  - `ro-value` provides the value for read-only bits.
  - If `ro-mask` is present and `ro-value` is omitted, read-only bits default to `0`.
  - Both accept decimal integer, hex string (`0x...`), or binary string (`0b...`).

Notes on output behavior:
- JSON output stores `ro-mask`/`ro-value` as integers.
- HTML output preserves the original authored literal text for `ro-mask`/`ro-value` when available (for example `0xF0F0` or `0b1100`).

Examples:
```yaml
# Type-based CSR field (potentially legal enumerated values)
- reg-name: mtvec
  field-name: MODE
  impl-def: MTVEC_MODE_WARL
  type: [0, 1]

# Width-based CSR field (width references an existing parameter)
- reg-name: satp
  field-name: ASID
  impl-def: SATP_ASID_WARL
  width: ASIDLEN

# Read-only-mask CSR (read-only, mask only, read-only bits default to 0)
- reg-name: zort
  impl-def: ZORT_IMPL
  ro-mask: 0xF0F0_F0F0

# Read-only-mask/value CSR field references multiple impl-defs
- reg-names: foo
  impl-defs: [FOO_IMPL, BAR_IMPL]
  ro-mask: 0b1111
  ro-value: 0b0011
```

### create_param_appendix.py

Purpose:
- Creates one AsciiDoc table-row fragment file per parameter from params JSON,
  and generates higher-level AsciiDoc include files for appendix assembly.

Inputs:
- Params JSON file (-i / --input).
- Parameter table-layout YAML file (-t / --param-table), conforming to schemas/param-table-schema.json.

Outputs:
- Output directory containing:
  - Per-parameter row fragments grouped by AsciiDoc filename
  - Per-adoc include files (`<adoc>/all_params.adoc`) in input JSON parameter order.
  - Top-level include files:
    - `all_params_a_to_z.adoc` (single table, sorted by parameter name).
    - `all_params_by_chapter.adoc` (one table per chapter in input JSON chapter encounter order).

Top-level table behavior:
- Table columns and widths are driven by the `columns` list in the layout YAML.
- Table header names come from each column `name` in the layout YAML.
- Table captions include parameter counts (for example `: 25 Parameters`).

Typical command:
```bash
python3 tools/create_param_appendix.py \
  --input build/test-params.json \
  --param-table tools/default_param_table.yaml \
  --output-dir build/test-param-appendix-adoc-includes
```

### detect_tag_changes.py

This section contains the content moved from the former README_detect_tag_changes.md, integrated into this consolidated README.

Purpose:
- Detects additions, deletions, and modifications between two normative-tag JSON files.

Usage:
```bash
python3 tools/detect_tag_changes.py [options] REFERENCE_TAGS.json CURRENT_TAGS.json
```

Options:
- -u, --update-reference: update the reference file by merging additions from current.
- -v, --verbose: print additional processing details.
- -h, --help: show help message.

Exit codes:
- 0: no changes or additions only.
- 1: one or more modifications or deletions detected.

Examples:
```bash
python3 tools/detect_tag_changes.py build/reference-tags.json build/current-tags.json
```

```bash
python3 tools/detect_tag_changes.py reference.json current.json --update-reference
```

```bash
python3 tools/detect_tag_changes.py -u -v reference.json current.json
```

Integration pattern:
```bash
if python3 tools/detect_tag_changes.py reference-tags.json current-tags.json; then
  echo "No breaking tag changes detected"
else
  echo "Tag modifications/deletions detected; review required"
  exit 1
fi
```

## Notes

- These scripts are exercised by targets in the repository Makefile.
- Unit-level tests for helper modules live under tests/adoc2html, tests/shared_utils, and tests/text_to_html.
