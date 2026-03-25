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
| create_csr_appendix.py | CLI tool | Generates CSR-row AsciiDoc fragments plus table include files from the csrs array in params JSON and a CSR table-layout YAML file. |
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
- Converts tag text to HTML and applies tag-specific display behavior.

Key capabilities:
- Pipeline conversion via convert_tag_text_to_html.
- Returns a "(No text available)" placeholder for empty tag text.
- Prefixes context-only tag text with "[CONTEXT]".

Usage:
- Imported by create_normative_rules.py and create_params.py.

### shared_utils.py

Purpose:
- Provides shared constants, logging helpers, file loaders, and common validators/formatters used across tools scripts.

Key capabilities:
- make_log_helpers: creates script-scoped error/info/fatal callable helpers.
- load_json_object / load_yaml_object: safe JSON and YAML file loaders with error reporting.
- infer_param_type_string: renders human-readable parameter type strings for table output.
- format_param_feature: renders a parameter feature string from chapter name and impl-defs.
- Constants for standards object kinds, impl-def categories, and CSR category mappings.

Usage:
- Imported by create_normative_rules.py, create_params.py, and create_param_appendix.py.

### create_params.py

Purpose:
- Creates params JSON/HTML outputs from normative-rules JSON plus parameter-definition YAML files.

Inputs:
- Normative-rules JSON file (-n / --norm-rules)
- Parameter definition files (-d / --param-def)

Outputs:
- JSON (default) or HTML file.
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
- Every CSR/field entry must include `type` with one of:
  - `legal-enum` - Standard defines legal values and implementation supports a subset that doesn't use all possible bit encodings (e.g., 10 values in a 4-bit field). Implementation's config file provides:
    - A list of supported legal write values
    - An indication of whether illegal write values are ignored or map to one specified legal value
  - `var-width` - CSR/field is variable width and the `width-parameter` property provides the name of the parameter that provides its value.
  - `ro-mask` - CSR/field allows implementation to treat some bits as read-only. Implementation's config file provides:
    - mask: A bit mask (1 = read-only, 0 = read-write) of read-only bits
    - value: The value of those read-only bits. If they are all zero the value can be omitted.
  - `other` - CSR/field doesn't match any of the other `type` choices
- Every CSR entry must include `impl-def` or `impl-defs`.
  - At least one referenced normative rule must provide `impl-def-category`.
  - Any provided `impl-def-category` values across referenced impl-defs must agree.
  - The category is mapped into CSR category (`WARL`/`WLRL`) for output grouping.

Examples:
```yaml
# Legal-enum: Implementation's config file provides legal values and behavior when writing illegal values
- reg-name: mtvec
  field-name: MODE
  type: legal-enum
  impl-def: MTVEC_MODE_WARL

# Width-based CSR field (var-width parameter name provided by `width-parameter` property)
- reg-name: satp
  field-name: ASID
  type: var-width
  width-parameter: ASIDLEN
  impl-def: SATP_ASID_WARL

# Read-only-mask: Implementation's config file provides bit mask and value of read-only bits
- reg-name: zort
  type: ro-mask
  impl-def: ZORT_IMPL

# Explicitly "other" (doesn't match other `type` values)
- reg-name: mstatus
  field-name: MPP
  type: other
  impl-def: MSTATUS_MPP_WLRL
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

### create_csr_appendix.py

Purpose:
- Creates one AsciiDoc table-row fragment file per CSR from the `csrs` array in params JSON,
  and generates higher-level AsciiDoc include files for appendix assembly.

Inputs:
- Params JSON file (-i / --input).
- CSR table-layout YAML file (-t / --csr-table), conforming to schemas/csr-table-schema.json.

Outputs:
- Output directory containing:
  - Per-CSR row fragments grouped by AsciiDoc filename.
  - Per-adoc include files (`<adoc>/all_csrs.adoc`) in input JSON CSR order.
  - Top-level include files:
    - `all_csrs_a_to_z.adoc` (single table, sorted by CSR name).
    - `all_csrs_by_chapter.adoc` (one table per chapter in input JSON chapter encounter order).

Default columns and order (tools/default_csr_table.yaml):
- `Name` (from `reg-name`, optionally `reg-name.field-name`)
- `Type`
- `Feature(s)`
- `Implementation-defined Behavior(s)`

Typical command:
```bash
python3 tools/create_csr_appendix.py \
  --input build/test-params.json \
  --csr-table tools/default_csr_table.yaml \
  --output-dir build/test-csr-appendix-adoc-includes
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
