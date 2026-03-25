#!/usr/bin/env python3
"""Create one AsciiDoc table-row fragment file per CSR.

Input JSON must conform to schemas/params-schema.json.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from appendix_shared_utils import (
    infer_normative_rules,
    render_table_cols_spec,
    render_table_header_row,
    safe_filename,
)

from shared_utils import (
    IMPLDEF_CATEGORIES,
    NORM_RULES_BASE_URL,
    check_impldef_cat,
    check_kind,
    format_param_feature,
    load_json_object,
    load_yaml_object,
    make_log_helpers,
)

PN = "create_csr_appendix.py"

ALLOWED_TABLE_COLUMNS = {
    "NAME",
    "TYPE",
    "FEATURES",
    "IMPLEMENTATION_DEFINED_BEHAVIORS",
}

error, info, fatal = make_log_helpers(PN)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Create one AsciiDoc file per CSR from a params JSON file "
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
        "--csr-table",
        required=True,
        metavar="FILE",
        help=(
            "Input YAML CSR table layout file "
            "(conforms to schemas/csr-table-schema.json)"
        ),
    )
    return parser.parse_args()


def load_params_json(pathname: str) -> Dict[str, Any]:
    """Load params JSON and validate top-level CSR shape."""
    data = load_json_object(pathname, fatal)

    csrs_obj: Any = data.get("csrs")
    if not isinstance(csrs_obj, list) or not csrs_obj:
        fatal(f"Expected non-empty csrs array in {pathname}")

    for idx, csr in enumerate(csrs_obj):
        if not isinstance(csr, dict):
            fatal(f"Expected csrs[{idx}] to be an object")

        reg_name = csr.get("reg-name")
        if not isinstance(reg_name, str) or not reg_name:
            fatal(f"Expected csrs[{idx}].reg-name to be a non-empty string")

        field_name = csr.get("field-name")
        if field_name is not None and (not isinstance(field_name, str) or not field_name):
            fatal(f"Expected csrs[{idx}].field-name to be a non-empty string when present")

        csr_type = csr.get("type")
        if not isinstance(csr_type, str) or not csr_type:
            fatal(f"Expected csrs[{idx}].type to be a non-empty string")

        impl_defs = csr.get("impl-defs")
        if impl_defs is None:
            continue
        if not isinstance(impl_defs, list):
            fatal(f"Expected csrs[{idx}].impl-defs to be an array")
        if not impl_defs:
            fatal(f"Expected csrs[{idx}].impl-defs to be a non-empty array")

        for impl_idx, impl_def in enumerate(impl_defs):
            if not isinstance(impl_def, dict):
                fatal(f"Expected csrs[{idx}].impl-defs[{impl_idx}] to be an object")

            rule_name = impl_def.get("name")
            csr_name = csr_display_name(csr)
            nr_name: str = rule_name if isinstance(rule_name, str) else csr_name

            kind = impl_def.get("kind")
            if kind is not None:
                if not isinstance(kind, str):
                    fatal(
                        f"Expected csrs[{idx}].impl-defs[{impl_idx}].kind "
                        f"to be a string"
                    )
                check_kind(kind, nr_name, None, fatal, PN)

            impldef_cat = impl_def.get("impl-def-category")
            if impldef_cat is not None:
                if not isinstance(impldef_cat, str):
                    fatal(
                        f"Expected csrs[{idx}].impl-defs[{impl_idx}].impl-def-category "
                        f"to be a string"
                    )
                check_impldef_cat(impldef_cat, nr_name, None, fatal, PN)

    return data


def load_csr_table_yaml(pathname: str) -> List[Dict[str, Any]]:
    """Load and validate CSR table layout YAML."""
    data = load_yaml_object(pathname, fatal)

    allowed_top_level_keys = {"columns", "$schema"}
    unexpected_top_level_keys = sorted(set(data.keys()) - allowed_top_level_keys)
    if unexpected_top_level_keys:
        fatal(
            f"Unexpected top-level properties in {pathname}: "
            f"{', '.join(unexpected_top_level_keys)}"
        )

    columns_obj = data.get("columns")
    if not isinstance(columns_obj, list) or not columns_obj:
        fatal(f"Expected non-empty columns array in {pathname}")
    assert isinstance(columns_obj, list)

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
        assert isinstance(width_pct, (int, float)) and not isinstance(width_pct, bool)
        if width_pct <= 0 or width_pct > 100:
            fatal(f"Expected columns[{idx}].width_pct to be > 0 and <= 100")

        if column in seen_column_ids:
            fatal(f"Duplicate column identifier {column!r} in {pathname}")
        seen_column_ids.add(column)

        if name in seen_column_names:
            fatal(f"Duplicate column name {name!r} in {pathname}")
        seen_column_names.add(name)

    return columns_obj


def csr_display_name(csr: Dict[str, Any]) -> str:
    """Return reg-name and optional field-name joined with a period."""
    reg_name = csr["reg-name"]
    field_name = csr.get("field-name")
    if isinstance(field_name, str) and field_name:
        return f"{reg_name}.{field_name}"
    return reg_name


def format_csr_count_label(count: int) -> str:
    """Render count label with singular/plural wording."""
    noun = "CSR" if count == 1 else "CSRs"
    return f"{count} {noun}"


def render_name_cell(csr: Dict[str, Any]) -> str:
    """Render NAME column cell."""
    return f"| {csr_display_name(csr)}"


def render_type_cell(csr: Dict[str, Any]) -> str:
    """Render TYPE column cell."""
    csr_type = csr.get("type")
    type_display = csr_type if isinstance(csr_type, str) and csr_type else "other"

    if type_display == "var-width":
        width_parameter = csr.get("width-parameter")
        if isinstance(width_parameter, str) and width_parameter:
            type_display = f"var-width = {width_parameter}"

    return f"| {type_display}"


def render_features_cell(csr: Dict[str, Any]) -> str:
    """Render FEATURES column cell."""
    return f"| {format_param_feature(csr)}"


def render_impl_defined_behavior_cell(csr: Dict[str, Any]) -> str:
    """Render IMPLEMENTATION_DEFINED_BEHAVIORS column cell."""
    lines: List[str] = ["a|"]

    norm_rules = infer_normative_rules(csr)
    if norm_rules:
        for rule_name in norm_rules:
            lines.append(f"* {NORM_RULES_BASE_URL}#{rule_name}[{rule_name}]")
    else:
        lines.append("* (none)")

    note = csr.get("note")
    if isinstance(note, str) and note.strip():
        lines.append("")
        lines.append(f"NOTE: {note.strip()}")

    description = csr.get("description")
    if isinstance(description, str) and description.strip():
        lines.append("")
        lines.append(description.strip())

    return "\n".join(lines)


def render_csr_row_fragment(
    csr: Dict[str, Any],
    columns: List[Dict[str, Any]],
) -> str:
    """Render one AsciiDoc row fragment with configured columns."""
    lines: List[str] = []

    for col in columns:
        col_id = col["column"]
        if col_id == "NAME":
            lines.append(render_name_cell(csr))
        elif col_id == "TYPE":
            lines.append(render_type_cell(csr))
        elif col_id == "FEATURES":
            lines.append(render_features_cell(csr))
        elif col_id == "IMPLEMENTATION_DEFINED_BEHAVIORS":
            lines.append(render_impl_defined_behavior_cell(csr))
        else:
            fatal(f"Internal error: unsupported column identifier {col_id!r}")

    return "\n".join(lines) + "\n"


def write_output_files(
    csrs: List[Dict[str, Any]],
    output_dir: Path,
    columns: List[Dict[str, Any]],
):
    """Write one .adoc file per CSR, organized by def_filename.

    Also writes one chapter-level include file per subdirectory that
    includes all CSR .adoc files in input CSR order.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    table_cols = render_table_cols_spec(columns)
    table_header = render_table_header_row(columns)

    chapter_files: Dict[Path, List[str]] = {}
    chapter_names: Dict[Path, str] = {}
    chapter_category_files: Dict[Tuple[Path, str], List[str]] = {}

    seen_names = set()
    for csr in csrs:
        name = csr_display_name(csr)
        file_stem = safe_filename(name)
        if file_stem in seen_names:
            fatal(
                f"Duplicate output filename stem {file_stem!r}; "
                "CSR names must be unique after filename sanitization"
            )
        seen_names.add(file_stem)

        def_filename = csr.get("def_filename", "")
        if not isinstance(def_filename, str) or not def_filename:
            fatal(f"Expected non-empty def_filename for CSR {name!r}")
        def_dir_name = Path(def_filename).stem
        if not def_dir_name:
            fatal(
                f"def_filename {def_filename!r} for CSR {name!r} "
                "has no usable stem for a chapter subdirectory name"
            )
        csr_dir = output_dir / def_dir_name
        csr_dir.mkdir(parents=True, exist_ok=True)

        chapter_name_value = csr.get("chapter_name")
        if not isinstance(chapter_name_value, str) or not chapter_name_value.strip():
            fatal(f"Expected non-empty chapter_name for CSR {name!r}")
        chapter_name = str(chapter_name_value)
        if csr_dir in chapter_names and chapter_names[csr_dir] != chapter_name:
            fatal(
                f"Conflicting chapter_name values for def_filename {def_filename!r}: "
                f"{chapter_names[csr_dir]!r} vs {chapter_name!r}"
            )
        chapter_names[csr_dir] = chapter_name

        out_path = csr_dir / f"{file_stem}.adoc"
        content = render_csr_row_fragment(csr, columns)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            fatal(f"Error writing {out_path}: {e}")

        chapter_files.setdefault(csr_dir, []).append(f"{file_stem}.adoc")

        category = csr.get("category", "")
        chapter_category_files.setdefault((csr_dir, category), []).append(f"{file_stem}.adoc")

    for csr_dir, filenames in chapter_files.items():
        include_lines = "\n".join(f"include::{fname}[]" for fname in filenames)
        chapter_include_path = csr_dir / "all_csrs.adoc"
        try:
            with open(chapter_include_path, "w", encoding="utf-8") as f:
                f.write(include_lines + "\n")
        except Exception as e:
            fatal(f"Error writing {chapter_include_path}: {e}")

        for category in IMPLDEF_CATEGORIES:
            cat_filenames = chapter_category_files.get((csr_dir, category), [])
            if not cat_filenames:
                continue
            cat_include_lines = "\n".join(f"include::{fname}[]" for fname in cat_filenames)
            cat_include_path = csr_dir / f"{category.lower()}_csrs.adoc"
            try:
                with open(cat_include_path, "w", encoding="utf-8") as f:
                    f.write(cat_include_lines + "\n")
            except Exception as e:
                fatal(f"Error writing {cat_include_path}: {e}")

    chapter_tables: List[str] = []
    for csr_dir in chapter_files.keys():
        chapter_tables.append(f"=== {chapter_names[csr_dir]}")
        chapter_tables.append("")
        for category in IMPLDEF_CATEGORIES:
            cat_filenames = chapter_category_files.get((csr_dir, category), [])
            if not cat_filenames:
                continue
            cat_count = len(cat_filenames)
            chapter_tables.append(
                f".Chapter {chapter_names[csr_dir]} {category}: "
                f"{format_csr_count_label(cat_count)}"
            )
            chapter_tables.append(f"[cols=\"{table_cols}\"]")
            chapter_tables.append("|===")
            chapter_tables.append("")
            chapter_tables.append(table_header)
            chapter_tables.append("")
            chapter_tables.append(f"include::{csr_dir.name}/{category.lower()}_csrs.adoc[]")
            chapter_tables.append("")
            chapter_tables.append("|===")
            chapter_tables.append("")
    top_include_lines = "\n".join(chapter_tables).rstrip()
    top_include_path = output_dir / "all_csrs_by_chapter.adoc"
    try:
        with open(top_include_path, "w", encoding="utf-8") as f:
            f.write(top_include_lines + "\n")
    except Exception as e:
        fatal(f"Error writing {top_include_path}: {e}")

    all_csr_entries = [
        (file_stem, csr_dir)
        for csr_dir, filenames in chapter_files.items()
        for file_stem in (Path(f).stem for f in filenames)
    ]
    a_to_z_include_lines = "\n".join(
        f"include::{csr_dir.name}/{stem}.adoc[]"
        for stem, csr_dir in sorted(all_csr_entries, key=lambda e: e[0])
    )
    a_to_z_count = len(all_csr_entries)
    a_to_z_lines = "\n".join(
        [
            (
                ".WARL/WLRL CSR Definitions (A-Z): "
                f"{format_csr_count_label(a_to_z_count)}"
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
    a_to_z_path = output_dir / "all_csrs_a_to_z.adoc"
    try:
        with open(a_to_z_path, "w", encoding="utf-8") as f:
            f.write(a_to_z_lines + "\n")
    except Exception as e:
        fatal(f"Error writing {a_to_z_path}: {e}")


def main() -> int:
    """Program entry point."""
    args = parse_args()
    data = load_params_json(args.input)
    columns = load_csr_table_yaml(args.csr_table)
    csrs = data["csrs"]

    out_dir = Path(args.output_dir)
    info(f"Writing {len(csrs)} CSR AsciiDoc files to {out_dir}")
    write_output_files(csrs, out_dir, columns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
