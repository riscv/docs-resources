#!/usr/bin/env python3
"""
create_param_tables.py

Generates AsciiDoc table-row fragment files and include files for parameters and/or CSRs from a params JSON file.

Usage:
  python3 tools/create_param_tables.py --input <params.json> [--param-table <param-table.yaml>] [--csr-table <csr-table.yaml>] --output-dir <output_dir>

- If --param-table is given, generates parameter appendix files (like create_param_appendix.py)
- If --csr-table is given, generates CSR appendix files (like create_csr_appendix.py)
- If both are given, generates both under separate subdirectories in the output directory

Input JSON must conform to schemas/params-schema.json.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    infer_param_type_string,
    load_json_object,
    load_yaml_object,
    make_log_helpers,
)

PN = "create_param_tables.py"

PARAM_ALLOWED_TABLE_COLUMNS = {
    "PARAM_NAME_AND_NORM_RULE_MAPPING",
    "TYPE",
    "FEATURES",
    "DEFINITION",
}
CSR_ALLOWED_TABLE_COLUMNS = {
    "NAME",
    "TYPE",
    "FEATURES",
    "IMPLEMENTATION_DEFINED_BEHAVIORS",
}

error, info, fatal = make_log_helpers(PN)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate AsciiDoc appendix files for parameters and/or CSRs from params JSON."
    )
    parser.add_argument("-i", "--input", required=True, metavar="FILE", help="Input params JSON file (conforms to schemas/params-schema.json)")
    parser.add_argument("-o", "--output-dir", required=True, metavar="DIR", help="Directory where .adoc files will be written")
    parser.add_argument("--param-table", metavar="FILE", help="Input YAML parameter table layout file (schemas/param-table-schema.json)")
    parser.add_argument("--csr-table", metavar="FILE", help="Input YAML CSR table layout file (schemas/csr-table-schema.json)")
    return parser.parse_args()

def load_params_json(pathname: str) -> Dict[str, Any]:
    data = load_json_object(pathname, fatal)
    return data

def load_param_table_yaml(pathname: str) -> List[Dict[str, Any]]:
    data = load_yaml_object(pathname, fatal)
    columns_obj = data.get("columns")
    if not isinstance(columns_obj, list) or not columns_obj:
        fatal(f"Expected non-empty columns array in {pathname}")
    for idx, col in enumerate(columns_obj):
        column = col.get("column")
        if column not in PARAM_ALLOWED_TABLE_COLUMNS:
            allowed = ", ".join(sorted(PARAM_ALLOWED_TABLE_COLUMNS))
            fatal(f"Don't recognize columns[{idx}].column {column!r}; allowed values are: {allowed}")
    return columns_obj

def load_csr_table_yaml(pathname: str) -> List[Dict[str, Any]]:
    data = load_yaml_object(pathname, fatal)
    columns_obj = data.get("columns")
    if not isinstance(columns_obj, list) or not columns_obj:
        fatal(f"Expected non-empty columns array in {pathname}")
    for idx, col in enumerate(columns_obj):
        column = col.get("column")
        if column not in CSR_ALLOWED_TABLE_COLUMNS:
            allowed = ", ".join(sorted(CSR_ALLOWED_TABLE_COLUMNS))
            fatal(f"Don't recognize columns[{idx}].column {column!r}; allowed values are: {allowed}")
    return columns_obj

def has_block_content(text: str) -> bool:
    if "!===" in text:
        return True
    return "\n\n" in text

def normalize_inline_text(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", text.strip())

def render_definition_cell(param: Dict[str, Any]) -> str:
    note = param.get("note")
    description = param.get("description")
    parts = []
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

def render_param_name_and_norm_rule_mapping_cell(name: str, norm_rules: List[str]) -> str:
    lines = ["a|", f"[#param:{name}]#{name}#", "", "Normative Rule(s):", ""]
    if norm_rules:
        for rule_name in norm_rules:
            lines.append(f"* {NORM_RULES_BASE_URL}#{rule_name}[{rule_name}]")
    else:
        lines.append("* (none)")
    return "\n".join(lines)

def format_param_count_label(count: int) -> str:
    noun = "Parameter" if count == 1 else "Parameters"
    return f"{count} {noun}"

def render_parameter_row_fragment(param: Dict[str, Any], columns: List[Dict[str, Any]]) -> str:
    name = param["name"]
    type_str = infer_param_type_string(param, fatal)
    feature = format_param_feature(param)
    norm_rules = infer_normative_rules(param)
    lines = []
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

def write_param_output_files(params: List[Dict[str, Any]], output_dir: Path, columns: List[Dict[str, Any]]):
    output_dir.mkdir(parents=True, exist_ok=True)
    table_cols = render_table_cols_spec(columns)
    table_header = render_table_header_row(columns)
    chapter_files = {}
    chapter_names = {}
    seen_names = set()
    for param in params:
        name = param["name"]
        file_stem = safe_filename(name)
        if file_stem in seen_names:
            fatal(f"Duplicate output filename stem {file_stem!r}; parameter names must be unique after filename sanitization")
        seen_names.add(file_stem)
        def_filename = param.get("def_filename", "")
        if not isinstance(def_filename, str) or not def_filename:
            fatal(f"Expected non-empty def_filename for parameter {name!r}")
        def_dir_name = Path(def_filename).stem
        if not def_dir_name:
            fatal(f"def_filename {def_filename!r} for parameter {name!r} has no usable stem for a chapter subdirectory name")
        chapter_dir = output_dir / def_dir_name
        param_dir = chapter_dir / "params"
        param_dir.mkdir(parents=True, exist_ok=True)
        chapter_name = param.get("chapter_name")
        if not isinstance(chapter_name, str) or not chapter_name.strip():
            fatal(f"Expected non-empty chapter_name for parameter {name!r}")
        if chapter_dir in chapter_names and chapter_names[chapter_dir] != chapter_name:
            fatal(f"Conflicting chapter_name values for def_filename {def_filename!r}: {chapter_names[chapter_dir]!r} vs {chapter_name!r}")
        chapter_names[chapter_dir] = chapter_name
        out_path = param_dir / f"{file_stem}.adoc"
        content = render_parameter_row_fragment(param, columns)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        chapter_files.setdefault(chapter_dir, []).append(f"{file_stem}.adoc")
    for chapter_dir, filenames in chapter_files.items():
        include_lines = "\n".join(f"include::{fname}[]" for fname in filenames)
        chapter_include_path = chapter_dir / "params" / "all_params.adoc"
        with open(chapter_include_path, "w", encoding="utf-8") as f:
            f.write(include_lines + "\n")
    all_param_entries = [
        (file_stem, chapter_dir)
        for chapter_dir, filenames in chapter_files.items()
        for file_stem in (Path(f).stem for f in filenames)
    ]
    return {
        "table_cols": table_cols,
        "table_header": table_header,
        "chapter_files": chapter_files,
        "chapter_names": chapter_names,
        "chapter_order": list(chapter_files.keys()),
        "all_entries": all_param_entries,
    }

def csr_display_name(csr: Dict[str, Any]) -> str:
    reg_name = csr["reg-name"]
    field_name = csr.get("field-name")
    if isinstance(field_name, str) and field_name:
        return f"{reg_name}.{field_name}"
    return reg_name

def format_csr_count_label(count: int) -> str:
    noun = "CSR" if count == 1 else "CSRs"
    return f"{count} {noun}"

def render_name_cell(csr: Dict[str, Any]) -> str:
    return f"| {csr_display_name(csr)}"

def render_type_cell(csr: Dict[str, Any]) -> str:
    csr_type = csr.get("type")
    type_display = csr_type if isinstance(csr_type, str) and csr_type else "Other"
    if type_display == "VarWidth":
        width_parameter = csr.get("width-parameter")
        if isinstance(width_parameter, str) and width_parameter:
            type_display = f"VarWidth = {width_parameter}"
    func_of_reg_name = csr.get("func-of-reg-name")
    func_of_field_name = csr.get("func-of-field-name")
    if (isinstance(func_of_reg_name, str) and func_of_reg_name) or (isinstance(func_of_field_name, str) and func_of_field_name):
        base_reg_name = ""
        if isinstance(func_of_reg_name, str) and func_of_reg_name:
            base_reg_name = func_of_reg_name
        elif isinstance(func_of_field_name, str) and func_of_field_name:
            reg_name = csr.get("reg-name")
            if isinstance(reg_name, str) and reg_name:
                base_reg_name = reg_name
        func_of_target = base_reg_name
        if isinstance(func_of_field_name, str) and func_of_field_name:
            if func_of_target:
                func_of_target = f"{func_of_target}.{func_of_field_name}"
            else:
                func_of_target = func_of_field_name
        return f"a| {type_display} +\nfunc-of: {func_of_target}"
    return f"| {type_display}"

def render_features_cell(csr: Dict[str, Any]) -> str:
    return f"| {format_param_feature(csr)}"

def render_impl_defined_behavior_cell(csr: Dict[str, Any]) -> str:
    lines = ["a|"]
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

def render_csr_row_fragment(csr: Dict[str, Any], columns: List[Dict[str, Any]]) -> str:
    lines = []
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

def write_csr_output_files(csrs: List[Dict[str, Any]], output_dir: Path, columns: List[Dict[str, Any]]):
    output_dir.mkdir(parents=True, exist_ok=True)
    table_cols = render_table_cols_spec(columns)
    table_header = render_table_header_row(columns)
    chapter_files = {}
    chapter_names = {}
    seen_names = set()
    for csr in csrs:
        name = csr_display_name(csr)
        file_stem = safe_filename(name)
        if file_stem in seen_names:
            fatal(f"Duplicate output filename stem {file_stem!r}; CSR names must be unique after filename sanitization")
        seen_names.add(file_stem)
        def_filename = csr.get("def_filename", "")
        if not isinstance(def_filename, str) or not def_filename:
            fatal(f"Expected non-empty def_filename for CSR {name!r}")
        def_dir_name = Path(def_filename).stem
        if not def_dir_name:
            fatal(f"def_filename {def_filename!r} for CSR {name!r} has no usable stem for a chapter subdirectory name")
        chapter_dir = output_dir / def_dir_name
        csr_dir = chapter_dir / "csrs"
        csr_dir.mkdir(parents=True, exist_ok=True)
        chapter_name_value = csr.get("chapter_name")
        if not isinstance(chapter_name_value, str) or not chapter_name_value.strip():
            fatal(f"Expected non-empty chapter_name for CSR {name!r}")
        chapter_name = str(chapter_name_value)
        if chapter_dir in chapter_names and chapter_names[chapter_dir] != chapter_name:
            fatal(f"Conflicting chapter_name values for def_filename {def_filename!r}: {chapter_names[chapter_dir]!r} vs {chapter_name!r}")
        chapter_names[chapter_dir] = chapter_name
        out_path = csr_dir / f"{file_stem}.adoc"
        content = render_csr_row_fragment(csr, columns)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        chapter_files.setdefault(chapter_dir, []).append(f"{file_stem}.adoc")
        category_value = csr.get("category")
        if not isinstance(category_value, str) or not category_value:
            fatal(f"Expected non-empty category for CSR {name!r}")
        category = category_value
        if category not in IMPLDEF_CATEGORIES:
            allowed_str = ", ".join(IMPLDEF_CATEGORIES)
            fatal(f"Unrecognized category {category!r} for CSR {name!r}; allowed values are: {allowed_str}")
        # Keep category validation for input quality checks, but top-level outputs list all CSRs.
    for chapter_dir, filenames in chapter_files.items():
        include_lines = "\n".join(f"include::{fname}[]" for fname in filenames)
        chapter_include_path = chapter_dir / "csrs" / "all_csrs.adoc"
        with open(chapter_include_path, "w", encoding="utf-8") as f:
            f.write(include_lines + "\n")
    all_csr_entries = [
        (file_stem, chapter_dir)
        for chapter_dir, filenames in chapter_files.items()
        for file_stem in (Path(f).stem for f in filenames)
    ]
    return {
        "table_cols": table_cols,
        "table_header": table_header,
        "chapter_files": chapter_files,
        "chapter_names": chapter_names,
        "chapter_order": list(chapter_files.keys()),
        "all_entries": all_csr_entries,
    }

def write_combined_top_level_files(
    output_dir: Path,
    param_summary: Optional[Dict[str, Any]],
    csr_summary: Optional[Dict[str, Any]],
):
    output_dir.mkdir(parents=True, exist_ok=True)

    chapter_order: List[Path] = []
    if param_summary is not None:
        chapter_order.extend(param_summary["chapter_order"])
    if csr_summary is not None:
        for chapter_dir in csr_summary["chapter_order"]:
            if chapter_dir not in chapter_order:
                chapter_order.append(chapter_dir)

    # Write per-chapter combined files as standalone tables for params then csrs.
    for chapter_dir in chapter_order:
        combined_lines: List[str] = []
        if param_summary is not None:
            param_stems = sorted(Path(fname).stem for fname in param_summary["chapter_files"].get(chapter_dir, []))
            if param_stems:
                combined_lines.append(f".Parameter Definitions (A-Z): {format_param_count_label(len(param_stems))}")
                combined_lines.append(f"[cols=\"{param_summary['table_cols']}\"]")
                combined_lines.append("|===")
                combined_lines.append("")
                combined_lines.append(param_summary["table_header"])
                combined_lines.append("")
                for stem in param_stems:
                    combined_lines.append(f"include::params/{stem}.adoc[]")
                combined_lines.append("")
                combined_lines.append("|===")
                combined_lines.append("")
        if csr_summary is not None:
            csr_stems = sorted(Path(fname).stem for fname in csr_summary["chapter_files"].get(chapter_dir, []))
            if csr_stems:
                combined_lines.append(f".WARL/WLRL CSR Definitions (A-Z): {format_csr_count_label(len(csr_stems))}")
                combined_lines.append(f"[cols=\"{csr_summary['table_cols']}\"]")
                combined_lines.append("|===")
                combined_lines.append("")
                combined_lines.append(csr_summary["table_header"])
                combined_lines.append("")
                for stem in csr_stems:
                    combined_lines.append(f"include::csrs/{stem}.adoc[]")
                combined_lines.append("")
                combined_lines.append("|===")
                combined_lines.append("")
        combined_path = chapter_dir / "all_params.adoc"
        with open(combined_path, "w", encoding="utf-8") as f:
            if combined_lines:
                f.write("\n".join(combined_lines).rstrip() + "\n")
            else:
                f.write("")

    a_to_z_lines: List[str] = []
    if param_summary is not None:
        all_param_entries = [
            (Path(fname).stem, chapter_dir)
            for chapter_dir in chapter_order
            for fname in param_summary["chapter_files"].get(chapter_dir, [])
        ]
        a_to_z_lines.append(f".Parameter Definitions (A-Z): {format_param_count_label(len(all_param_entries))}")
        a_to_z_lines.append(f"[cols=\"{param_summary['table_cols']}\"]")
        a_to_z_lines.append("|===")
        a_to_z_lines.append("")
        a_to_z_lines.append(param_summary["table_header"])
        a_to_z_lines.append("")
        for stem, chapter_dir in sorted(all_param_entries, key=lambda e: e[0]):
            a_to_z_lines.append(f"include::{chapter_dir.name}/params/{stem}.adoc[]")
        a_to_z_lines.append("")
        a_to_z_lines.append("|===")
        a_to_z_lines.append("")

    if csr_summary is not None:
        all_csr_entries = [
            (Path(fname).stem, chapter_dir)
            for chapter_dir in chapter_order
            for fname in csr_summary["chapter_files"].get(chapter_dir, [])
        ]
        a_to_z_lines.append(f".WARL/WLRL CSR Definitions (A-Z): {format_csr_count_label(len(all_csr_entries))}")
        a_to_z_lines.append(f"[cols=\"{csr_summary['table_cols']}\"]")
        a_to_z_lines.append("|===")
        a_to_z_lines.append("")
        a_to_z_lines.append(csr_summary["table_header"])
        a_to_z_lines.append("")
        for stem, chapter_dir in sorted(all_csr_entries, key=lambda e: e[0]):
            a_to_z_lines.append(f"include::{chapter_dir.name}/csrs/{stem}.adoc[]")
        a_to_z_lines.append("")
        a_to_z_lines.append("|===")
        a_to_z_lines.append("")
    a_to_z_path = output_dir / "all_params_a_to_z.adoc"
    with open(a_to_z_path, "w", encoding="utf-8") as f:
        f.write("\n".join(a_to_z_lines).rstrip() + "\n")

    chapter_lines: List[str] = []
    for chapter_dir in chapter_order:
        chapter_name = None
        if param_summary is not None:
            chapter_name = param_summary["chapter_names"].get(chapter_dir)
        if chapter_name is None and csr_summary is not None:
            chapter_name = csr_summary["chapter_names"].get(chapter_dir)
        if chapter_name is None:
            continue
        chapter_lines.append(f"=== {chapter_name}")
        chapter_lines.append("")

        if param_summary is not None:
            param_filenames = param_summary["chapter_files"].get(chapter_dir, [])
            if param_filenames:
                chapter_count = len(param_filenames)
                chapter_lines.append(f".Chapter {chapter_name} Parameter Definitions: {format_param_count_label(chapter_count)}")
                chapter_lines.append(f"[cols=\"{param_summary['table_cols']}\"]")
                chapter_lines.append("|===")
                chapter_lines.append("")
                chapter_lines.append(param_summary["table_header"])
                chapter_lines.append("")
                chapter_lines.append(f"include::{chapter_dir.name}/params/all_params.adoc[]")
                chapter_lines.append("")
                chapter_lines.append("|===")
                chapter_lines.append("")

        if csr_summary is not None:
            csr_filenames = csr_summary["chapter_files"].get(chapter_dir, [])
            if csr_filenames:
                csr_count = len(csr_filenames)
                chapter_lines.append(f".Chapter {chapter_name} WARL/WLRL CSR Definitions: {format_csr_count_label(csr_count)}")
                chapter_lines.append(f"[cols=\"{csr_summary['table_cols']}\"]")
                chapter_lines.append("|===")
                chapter_lines.append("")
                chapter_lines.append(csr_summary["table_header"])
                chapter_lines.append("")
                chapter_lines.append(f"include::{chapter_dir.name}/csrs/all_csrs.adoc[]")
                chapter_lines.append("")
                chapter_lines.append("|===")
                chapter_lines.append("")

    by_chapter_path = output_dir / "all_params_by_chapter.adoc"
    with open(by_chapter_path, "w", encoding="utf-8") as f:
        f.write("\n".join(chapter_lines).rstrip() + "\n")

def main() -> int:
    args = parse_args()
    data = load_params_json(args.input)
    out_dir = Path(args.output_dir)
    did_any = False
    param_summary: Optional[Dict[str, Any]] = None
    csr_summary: Optional[Dict[str, Any]] = None
    if args.param_table:
        if "parameters" not in data or not isinstance(data["parameters"], list):
            fatal("Input JSON does not contain a 'parameters' array.")
        columns = load_param_table_yaml(args.param_table)
        params = data["parameters"]
        info(f"Writing {len(params)} parameter AsciiDoc files under chapter params/ subdirectories in {out_dir}")
        param_summary = write_param_output_files(params, out_dir, columns)
        did_any = True
    if args.csr_table:
        if "csrs" not in data or not isinstance(data["csrs"], list):
            fatal("Input JSON does not contain a 'csrs' array.")
        columns = load_csr_table_yaml(args.csr_table)
        csrs = data["csrs"]
        info(f"Writing {len(csrs)} CSR AsciiDoc files under chapter csrs/ subdirectories in {out_dir}")
        csr_summary = write_csr_output_files(csrs, out_dir, columns)
        did_any = True
    if not did_any:
        fatal("Must specify at least one of --param-table or --csr-table.")
    write_combined_top_level_files(out_dir, param_summary, csr_summary)
    return 0

if __name__ == "__main__":
    sys.exit(main())
