#!/usr/bin/env python3
"""Create one AsciiDoc table-row fragment file per parameter.

Input JSON must conform to schemas/params-schema.json.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from shared_utils import (
    NORM_RULES_BASE_URL,
    check_impldef_cat,
    check_kind,
    format_param_feature,
    load_json_object,
    load_yaml_object,
    make_log_helpers,
)

PN = "create_param_appendix.py"

ALLOWED_TABLE_COLUMNS = {
    "PARAM_NAME_AND_NORM_RULE_MAPPING",
    "TYPE",
    "FEATURES",
    "DEFINITION",
}

error, info, fatal = make_log_helpers(PN)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Create one AsciiDoc file per parameter from a params JSON file "
            "(schemas/params-schema.json)."
        )
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        metavar="FILE",
        help="Input params JSON file (conforms to schemas/params-schema.json)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        metavar="DIR",
        help="Directory where .adoc files will be written",
    )
    parser.add_argument(
        "-t",
        "--param-table",
        required=True,
        metavar="FILE",
        help=(
            "Input YAML parameter table layout file "
            "(conforms to schemas/param-table-schema.json)"
        ),
    )
    return parser.parse_args()


def load_params_json(pathname: str) -> Dict[str, Any]:
    """Load params JSON and validate top-level shape."""
    data = load_json_object(pathname, fatal)

    params_obj: Any = data.get("parameters")
    if not isinstance(params_obj, list):
        fatal(f"Expected parameters array in {pathname}")

    for idx, param in enumerate(params_obj):
        if not isinstance(param, dict):
            fatal(f"Expected parameters[{idx}] to be an object")
        name = param.get("name")
        if not isinstance(name, str) or not name:
            fatal(f"Expected parameters[{idx}].name to be a non-empty string")

        impl_defs = param.get("impl-defs")
        if impl_defs is None:
            continue
        if not isinstance(impl_defs, list):
            fatal(f"Expected parameters[{idx}].impl-defs to be an array")

        for impl_idx, impl_def in enumerate(impl_defs):
            if not isinstance(impl_def, dict):
                fatal(
                    f"Expected parameters[{idx}].impl-defs[{impl_idx}] to be an object"
                )

            rule_name = impl_def.get("name")
            nr_name = rule_name if isinstance(rule_name, str) else name

            kind = impl_def.get("kind")
            if kind is not None:
                if not isinstance(kind, str):
                    fatal(
                        f"Expected parameters[{idx}].impl-defs[{impl_idx}].kind "
                        f"to be a string"
                    )
                check_kind(kind, nr_name, None, fatal, PN)

            impldef_cat = impl_def.get("impl-def-category")
            if impldef_cat is not None:
                if not isinstance(impldef_cat, str):
                    fatal(
                        f"Expected parameters[{idx}].impl-defs[{impl_idx}].impl-def-category "
                        f"to be a string"
                    )
                check_impldef_cat(impldef_cat, nr_name, None, fatal, PN)

    return data


def load_param_table_yaml(pathname: str) -> List[Dict[str, Any]]:
    """Load and validate parameter table layout YAML."""
    data = load_yaml_object(pathname, fatal)

    columns_obj = data.get("columns")
    if not isinstance(columns_obj, list) or not columns_obj:
        fatal(f"Expected non-empty columns array in {pathname}")

    seen_column_ids = set()
    seen_column_names = set()

    for idx, col in enumerate(columns_obj):
        if not isinstance(col, dict):
            fatal(f"Expected columns[{idx}] to be an object")

        allowed_keys = {"name", "column", "width_pct"}
        unexpected_keys = sorted(set(col.keys()) - allowed_keys)
        if unexpected_keys:
            fatal(
                f"Unexpected properties in columns[{idx}]: "
                f"{', '.join(unexpected_keys)}"
            )

        for key in ["name", "column", "width_pct"]:
            if key not in col:
                fatal(f"Missing required property columns[{idx}].{key}")

        name = col.get("name")
        if not isinstance(name, str) or not name.strip():
            fatal(f"Expected columns[{idx}].name to be a non-empty string")

        column = col.get("column")
        if not isinstance(column, str):
            fatal(f"Expected columns[{idx}].column to be a string")
        if column not in ALLOWED_TABLE_COLUMNS:
            allowed = ", ".join(sorted(ALLOWED_TABLE_COLUMNS))
            fatal(
                f"Don't recognize columns[{idx}].column {column!r}; "
                f"allowed values are: {allowed}"
            )

        width_pct = col.get("width_pct")
        if not isinstance(width_pct, (int, float)) or isinstance(width_pct, bool):
            fatal(f"Expected columns[{idx}].width_pct to be a number")
        if width_pct <= 0 or width_pct > 100:
            fatal(f"Expected columns[{idx}].width_pct to be > 0 and <= 100")

        if column in seen_column_ids:
            fatal(f"Duplicate column identifier {column!r} in {pathname}")
        seen_column_ids.add(column)

        if name in seen_column_names:
            fatal(f"Duplicate column name {name!r} in {pathname}")
        seen_column_names.add(name)

    return columns_obj


def safe_filename(name: str) -> str:
    """Map a parameter name to a safe output filename stem."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def infer_type_string(param: Dict[str, Any]) -> str:
    """Render parameter type for table column 2."""
    param_type = param.get("type")
    param_range = param.get("range")

    if isinstance(param_type, list):
        if all(isinstance(v, str) for v in param_type):
            enum_values = ", ".join(param_type)
            return f"Enum ({enum_values})"
        if all(isinstance(v, int) for v in param_type):
            return "Integer"
        return "Enum"

    if isinstance(param_type, str):
        lowered = param_type.lower()
        if lowered == "boolean":
            return "Boolean"
        if lowered in {"bit", "byte", "hword", "word", "dword"}:
            return "Integer"

        uint_m = re.match(r"^uint(\d+)$", lowered)
        int_m = re.match(r"^int(\d+)$", lowered)
        if uint_m or int_m:
            return "Integer"

        return param_type

    if isinstance(param_range, list) and len(param_range) == 2:
        lo, hi = param_range
        if isinstance(lo, int) and isinstance(hi, int):
            return f"Integer {lo} to {hi}"

    return "(unspecified)"


def infer_normative_rules(param: Dict[str, Any]) -> List[str]:
    """Return unique normative rule names referenced by impl-defs."""
    impl_defs = param.get("impl-defs")
    if not isinstance(impl_defs, list):
        return []

    names: List[str] = []
    seen = set()
    for impl_def in impl_defs:
        if not isinstance(impl_def, dict):
            continue
        name = impl_def.get("name")
        if isinstance(name, str) and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def has_block_content(text: str) -> bool:
    """Return True when text should be emitted in an AsciiDoc block cell."""
    if "!===" in text:
        return True
    return "\n\n" in text


def normalize_inline_text(text: str) -> str:
    """Collapse newlines/spacing for single-line table cells."""
    return re.sub(r"\s+", " ", text.strip())


def render_definition_cell(param: Dict[str, Any]) -> str:
    """Render column 4 (Definition)."""
    note = param.get("note")
    description = param.get("description")

    parts: List[str] = []
    if isinstance(note, str) and note.strip():
        parts.append(f"NOTE: {note.strip()}")
    if isinstance(description, str) and description.strip():
        parts.append(description.strip())

    if not parts:
        return "| See normative rule"

    text = "\n\n".join(parts)
    if has_block_content(text):
        return "a| " + text

    return "| " + normalize_inline_text(text)


def render_param_name_and_norm_rule_mapping_cell(
    name: str,
    norm_rules: List[str],
) -> str:
    """Render PARAM_NAME_AND_NORM_RULE_MAPPING column cell."""
    lines: List[str] = []

    lines.append("a|")
    lines.append(f"[#param:{name}]#{name}#")
    lines.append("")
    lines.append("Normative Rule(s):")
    lines.append("")

    if norm_rules:
        for rule_name in norm_rules:
            lines.append(f"* {NORM_RULES_BASE_URL}#{rule_name}[{rule_name}]")
    else:
        lines.append("* (none)")

    return "\n".join(lines)


def render_table_cols_spec(columns: List[Dict[str, Any]]) -> str:
    """Render AsciiDoc cols specification from column widths."""
    return ",".join(f"{col['width_pct']}%" for col in columns)


def render_table_header_row(columns: List[Dict[str, Any]]) -> str:
    """Render AsciiDoc header row from configured display names."""
    return "| " + " | ".join(str(col["name"]) for col in columns)


def format_param_count_label(count: int) -> str:
    """Render count label with singular/plural wording."""
    noun = "Parameter" if count == 1 else "Parameters"
    return f"{count} {noun}"


def render_parameter_row_fragment(
    param: Dict[str, Any],
    columns: List[Dict[str, Any]],
) -> str:
    """Render one AsciiDoc row fragment with configured columns."""
    name = param["name"]
    type_str = infer_type_string(param)
    feature = format_param_feature(param)
    norm_rules = infer_normative_rules(param)

    lines: List[str] = []

    for col in columns:
        col_id = col["column"]
        if col_id == "PARAM_NAME_AND_NORM_RULE_MAPPING":
            lines.append(render_param_name_and_norm_rule_mapping_cell(name, norm_rules))
        elif col_id == "TYPE":
            lines.append(f"| {type_str}")
        elif col_id == "FEATURES":
            lines.append(f"| {feature}")
        elif col_id == "DEFINITION":
            lines.append(render_definition_cell(param))
        else:
            fatal(f"Internal error: unsupported column identifier {col_id!r}")

    return "\n".join(lines) + "\n"


def write_output_files(
    params: List[Dict[str, Any]],
    output_dir: Path,
    columns: List[Dict[str, Any]],
):
    """Write one .adoc file per parameter, organized by def_filename.

    Also writes one chapter-level include file per subdirectory that
    includes all parameter .adoc files in that directory (alphabetical order).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    table_cols = render_table_cols_spec(columns)
    table_header = render_table_header_row(columns)

    # Map from chapter subdirectory -> list of parameter .adoc filenames written.
    chapter_files: Dict[Path, List[str]] = {}
    chapter_names: Dict[Path, str] = {}

    seen_names = set()
    for param in params:
        name = param["name"]
        file_stem = safe_filename(name)
        if file_stem in seen_names:
            fatal(
                f"Duplicate output filename stem {file_stem!r}; "
                "parameter names must be unique after filename sanitization"
            )
        seen_names.add(file_stem)

        def_filename = param.get("def_filename", "")
        def_dir_name = Path(def_filename).stem
        param_dir = output_dir / def_dir_name
        param_dir.mkdir(parents=True, exist_ok=True)

        chapter_name = param.get("chapter_name")
        if not isinstance(chapter_name, str) or not chapter_name.strip():
            fatal(f"Expected non-empty chapter_name for parameter {name!r}")
        if param_dir in chapter_names and chapter_names[param_dir] != chapter_name:
            fatal(
                f"Conflicting chapter_name values for def_filename {def_filename!r}: "
                f"{chapter_names[param_dir]!r} vs {chapter_name!r}"
            )
        chapter_names[param_dir] = chapter_name

        out_path = param_dir / f"{file_stem}.adoc"
        content = render_parameter_row_fragment(param, columns)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            fatal(f"Error writing {out_path}: {e}")

        chapter_files.setdefault(param_dir, []).append(f"{file_stem}.adoc")

    # Write one chapter-level include file per subdirectory.
    for param_dir, filenames in chapter_files.items():
        include_lines = "\n".join(
            f"include::{fname}[]" for fname in sorted(filenames)
        )
        chapter_include_path = param_dir / "all_params.adoc"
        try:
            with open(chapter_include_path, "w", encoding="utf-8") as f:
                f.write(include_lines + "\n")
        except Exception as e:
            fatal(f"Error writing {chapter_include_path}: {e}")

    # Write one table per chapter to the top-level by-chapter file.
    chapter_tables: List[str] = []
    for param_dir in sorted(chapter_files.keys(), key=lambda p: (chapter_names[p], p.name)):
        chapter_count = len(chapter_files[param_dir])
        chapter_tables.append(
            f".Chapter {chapter_names[param_dir]} Parameter Definitions: "
            f"{format_param_count_label(chapter_count)}"
        )
        chapter_tables.append(f"[cols=\"{table_cols}\"]")
        chapter_tables.append("|===")
        chapter_tables.append("")
        chapter_tables.append(table_header)
        chapter_tables.append("")
        chapter_tables.append(f"include::{param_dir.name}/all_params.adoc[]")
        chapter_tables.append("")
        chapter_tables.append("|===")
        chapter_tables.append("")
    top_include_lines = "\n".join(chapter_tables).rstrip()
    top_include_path = output_dir / "all_params_by_chapter.adoc"
    try:
        with open(top_include_path, "w", encoding="utf-8") as f:
            f.write(top_include_lines + "\n")
    except Exception as e:
        fatal(f"Error writing {top_include_path}: {e}")

    # Write one table containing all parameters sorted alphabetically.
    all_param_entries = [
        (file_stem, param_dir)
        for param_dir, filenames in chapter_files.items()
        for file_stem in (Path(f).stem for f in filenames)
    ]
    a_to_z_include_lines = "\n".join(
        f"include::{param_dir.name}/{stem}.adoc[]"
        for stem, param_dir in sorted(all_param_entries, key=lambda e: e[0])
    )
    a_to_z_count = len(all_param_entries)
    a_to_z_lines = "\n".join(
        [
            (
                ".Parameter Definitions (A-Z): "
                f"{format_param_count_label(a_to_z_count)}"
            ),
            f"[cols=\"{table_cols}\"]",
            "|===",
            "",
            table_header,
            "",
            a_to_z_include_lines,
            "",
            "|===",
        ]
    )
    a_to_z_path = output_dir / "all_params_a_to_z.adoc"
    try:
        with open(a_to_z_path, "w", encoding="utf-8") as f:
            f.write(a_to_z_lines + "\n")
    except Exception as e:
        fatal(f"Error writing {a_to_z_path}: {e}")


def main() -> int:
    """Program entry point."""
    args = parse_args()
    data = load_params_json(args.input)
    columns = load_param_table_yaml(args.param_table)
    params = data["parameters"]

    out_dir = Path(args.output_dir)
    info(f"Writing {len(params)} parameter AsciiDoc files to {out_dir}")
    write_output_files(params, out_dir, columns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
