#!/usr/bin/env python3
"""Create params JSON from normative rules JSON and parameter definition YAML files."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from def_text_to_html import (
    convert_def_text_to_html,
    tag2html_link,
)
from shared_utils import (
    IMPLDEF_CATEGORIES,
    STDS_OBJECT_KINDS,
    check_impldef_cat,
    check_kind,
    format_param_feature,
    load_json_object,
    load_yaml_object,
    make_log_helpers,
)
from tag_text_to_html import convert_tag_text_to_html

PN = "create_params.py"
PARAMS_CH_TABLE_NAME_PREFIX = "table-params-ch-"
PARAMS_NO_CH_TABLE_NAME = "table-params-no-ch"
CSRS_CH_TABLE_NAME_PREFIX = "table-csrs-ch-"
CSRS_NO_CH_TABLE_NAME = "table-csrs-no-ch"

error, info, fatal = make_log_helpers(PN)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Create params output from one normative rules JSON file and one or more "
            "parameter definition YAML files."
        )
    )
    parser.add_argument(
        "-j",
        action="store_const",
        const="json",
        dest="output_format",
        default="json",
        help="Set output format to JSON (default)",
    )
    parser.add_argument(
        "--html",
        action="store_const",
        const="html",
        dest="output_format",
        help="Set output format to HTML",
    )
    parser.add_argument(
        "-n",
        "--norm-rules",
        required=True,
        metavar="FILE",
        help="Normative rules JSON filename (conforms to schemas/norm-rules-schema.json)",
    )
    parser.add_argument(
        "-d",
        "--param-def",
        action="append",
        required=True,
        metavar="FILE",
        help="Parameter definition YAML filename (conforms to schemas/param-defs-schema.json). "
             "Specify one or more times.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        metavar="FILE",
        help="Output filename (JSON conforms to schemas/params-schema.json)",
    )
    return parser.parse_args()


def load_json_file(pathname: str) -> Dict[str, Any]:
    """Load a JSON file as a dict."""
    return load_json_object(pathname, fatal)


def load_yaml_file(pathname: str) -> Dict[str, Any]:
    """Load a YAML file as a dict."""
    return load_yaml_object(pathname, fatal)


def normalize_impldef_refs(
    entry: Dict[str, Any],
    src_filename: str,
    item_name: str,
    item_kind: str,
) -> List[str]:
    """Return impl-def references from one definition entry as a normalized array."""
    has_impldef = "impl-def" in entry
    has_impldefs = "impl-defs" in entry

    if has_impldef and has_impldefs:
        fatal(f"{item_kind} {item_name} in {src_filename} cannot define both impl-def and impl-defs")

    refs: List[str] = []
    if has_impldef:
        impl_def: Any = entry.get("impl-def")
        if not isinstance(impl_def, str):
            fatal(f"{item_kind} {item_name} in {src_filename} has non-string impl-def")
        refs = [impl_def]
    elif has_impldefs:
        impl_defs: Any = entry.get("impl-defs")
        if not isinstance(impl_defs, list):
            fatal(f"{item_kind} {item_name} in {src_filename} has non-list impl-defs")
        for impl_def in impl_defs:
            if not isinstance(impl_def, str):
                fatal(f"{item_kind} {item_name} in {src_filename} has non-string value in impl-defs")
        refs = list(impl_defs)

    return refs


def rules_by_name(norm_rules_data: Dict[str, Any], src_filename: str) -> Dict[str, Dict[str, Any]]:
    """Create lookup map from normative rule name to its JSON object."""
    rules_obj: Any = norm_rules_data.get("normative_rules")
    if not isinstance(rules_obj, list):
        fatal(f"Missing or invalid normative_rules array in {src_filename}")
    rules: List[Any] = rules_obj

    by_name: Dict[str, Dict[str, Any]] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            fatal(f"Found non-object entry in normative_rules array in {src_filename}")

        name: Any = rule.get("name")
        if not isinstance(name, str):
            fatal(f"Found normative rule without string name in {src_filename}")

        if name in by_name:
            fatal(f"Duplicate normative rule name {name} in {src_filename}")

        by_name[name] = rule

    return by_name


def resolve_impldef_entries(
    impl_defs: List[str],
    norm_rules_by_name: Dict[str, Dict[str, Any]],
    norm_rules_filename: str,
    src_filename: str,
    item_name: str,
    item_kind: str,
) -> List[Dict[str, Any]]:
    """Resolve impl-def names to normativeRuleEntry objects."""
    resolved: List[Dict[str, Any]] = []
    for impl_def in impl_defs:
        norm_rule_opt = norm_rules_by_name.get(impl_def)
        if norm_rule_opt is None:
            fatal(
                f"{item_kind} {item_name} in {src_filename} references impl-def {impl_def} "
                f"which is not present in normative rules {norm_rules_filename}"
            )
        assert norm_rule_opt is not None
        resolved_entry = dict(norm_rule_opt)

        kind = resolved_entry.get("kind")
        if kind is not None:
            if not isinstance(kind, str):
                fatal(
                    f"{item_kind} {item_name} in {src_filename} references impl-def {impl_def} "
                    f"with non-string kind ({type(kind).__name__}) "
                    f"in normative rules {norm_rules_filename}"
                )
            if kind not in STDS_OBJECT_KINDS:
                allowed_kinds = ",".join(STDS_OBJECT_KINDS)
                fatal(
                    f"{item_kind} {item_name} in {src_filename} references impl-def {impl_def} "
                    f"with invalid kind {kind!r} in normative rules {norm_rules_filename}. "
                    f"Allowed kinds are: {allowed_kinds}"
                )
            check_kind(kind, impl_def, None, fatal, PN)

        impldef_cat = resolved_entry.get("impl-def-category")
        if impldef_cat is not None:
            if not isinstance(impldef_cat, str):
                fatal(
                    f"{item_kind} {item_name} in {src_filename} references impl-def {impl_def} "
                    f"with non-string impl-def-category ({type(impldef_cat).__name__}) "
                    f"in normative rules {norm_rules_filename}"
                )
            if impldef_cat not in IMPLDEF_CATEGORIES:
                allowed_cats = ",".join(IMPLDEF_CATEGORIES)
                fatal(
                    f"{item_kind} {item_name} in {src_filename} references impl-def {impl_def} "
                    f"with invalid impl-def-category {impldef_cat!r} in normative rules "
                    f"{norm_rules_filename}. Allowed impl-def-categories are: {allowed_cats}"
                )
            check_impldef_cat(impldef_cat, impl_def, None, fatal, PN)

        resolved.append(resolved_entry)
    return resolved


def param_type_to_json_schema(
    param_type: Any,
    param_range: Any,
    param_array: Any,
    def_filename: str,
    name: str,
) -> Dict[str, Any]:
    """Convert a type/range plus optional array bounds to a JSON Schema object."""
    if param_range is not None:
        item_schema = {"type": "integer", "minimum": param_range[0], "maximum": param_range[1]}
    elif isinstance(param_type, list):
        all_int = all(isinstance(v, int) for v in param_type)
        all_str = all(isinstance(v, str) for v in param_type)
        if all_int:
            item_schema = {"type": "integer", "enum": list(param_type)}
        elif all_str:
            item_schema = {"type": "string", "enum": list(param_type)}
        else:
            item_schema = {"enum": list(param_type)}
    else:
        # Type matching is case-sensitive; only canonical lowercase tokens are accepted.
        if param_type == "boolean":
            item_schema = {"type": "boolean"}
        elif param_type == "bit":
            item_schema = {"type": "integer", "minimum": 0, "maximum": 1}
        elif param_type == "byte":
            item_schema = {"type": "integer", "minimum": 0, "maximum": 255}
        elif param_type == "hword":
            item_schema = {"type": "integer", "minimum": 0, "maximum": 65535}
        elif param_type == "word":
            item_schema = {"type": "integer", "minimum": 0, "maximum": 4294967295}
        elif param_type == "dword":
            item_schema = {"type": "integer", "minimum": 0, "maximum": 18446744073709551615}
        else:
            m = re.match(r'^uint(\d+)$', param_type)
            if m:
                n = int(m.group(1))
                if n < 2 or n > 64:
                    fatal(
                        f"Parameter {name} in {def_filename} has invalid unsigned width {n} "
                        f"for type {param_type!r} (expected 2–64 bits)"
                    )
                item_schema = {"type": "integer", "minimum": 0, "maximum": (1 << n) - 1}
            else:
                m = re.match(r'^int(\d+)$', param_type)
                if m:
                    n = int(m.group(1))
                    if n < 2 or n > 64:
                        fatal(
                            f"Parameter {name} in {def_filename} has invalid signed width {n} "
                            f"for type {param_type!r} (expected 2–64 bits)"
                        )
                    item_schema = {
                        "type": "integer",
                        "minimum": -(1 << (n - 1)),
                        "maximum": (1 << (n - 1)) - 1,
                    }
                else:
                    fatal(f"Parameter {name} in {def_filename} has unrecognized type {param_type!r}")
                    return {}  # unreachable

    if param_array is None:
        return item_schema

    array_len = param_array[1] - param_array[0] + 1
    return {
        "type": "array",
        "items": item_schema,
        "minItems": array_len,
        "maxItems": array_len,
    }


def add_parameter_entries(
    parameters: List[Dict[str, Any]],
    entry: Dict[str, Any],
    def_filename: str,
    chapter_name: str,
    norm_rules_by_name: Dict[str, Dict[str, Any]],
    norm_rules_filename: str,
):
    """Expand one parameter definition entry into one or more output parameter objects."""
    names: List[str] = []

    has_type = "type" in entry
    has_range = "range" in entry
    has_array = "array" in entry
    if has_type == has_range:
        fatal(f"Parameter entry in {def_filename} must define exactly one of type or range")

    param_type: Any = entry.get("type")
    param_range: Any = entry.get("range")
    param_array: Any = entry.get("array")
    if has_type:
        if isinstance(param_type, str):
            pass
        elif isinstance(param_type, list):
            for value in param_type:
                if not isinstance(value, (str, int)):
                    fatal(
                        f"Parameter entry in {def_filename} has invalid type array value "
                        f"{value!r}; expected string or integer"
                    )
        else:
            fatal(f"Parameter entry in {def_filename} has invalid type; expected string or array")

    if has_range:
        if not isinstance(param_range, list) or len(param_range) != 2:
            fatal(f"Parameter entry in {def_filename} has invalid range; expected array of 2 integers")
        if not isinstance(param_range[0], int) or not isinstance(param_range[1], int):
            fatal(f"Parameter entry in {def_filename} has invalid range; values must be integers")
        if param_range[0] >= param_range[1]:
            fatal(f"Parameter entry in {def_filename} has invalid range; first value must be less than second")

    if has_array:
        if not isinstance(param_array, list) or len(param_array) != 2:
            fatal(f"Parameter entry in {def_filename} has invalid array; expected array of 2 integers")
        if not isinstance(param_array[0], int) or not isinstance(param_array[1], int):
            fatal(f"Parameter entry in {def_filename} has invalid array; values must be integers")
        if param_array[0] < 0 or param_array[1] < 0:
            fatal(f"Parameter entry in {def_filename} has invalid array; values must be non-negative")
        if param_array[0] > param_array[1]:
            fatal(f"Parameter entry in {def_filename} has invalid array; first value must be less than or equal to second")

    if "name" in entry:
        name: Any = entry.get("name")
        if not isinstance(name, str):
            fatal(f"Found parameter entry with non-string name in {def_filename}")
        names = [name]
    elif "names" in entry:
        names_value: Any = entry.get("names")
        if not isinstance(names_value, list):
            fatal(f"Found parameter entry with non-list names in {def_filename}")
        for name in names_value:
            if not isinstance(name, str):
                fatal(f"Found non-string value in names array in {def_filename}")
        names = list(names_value)
    else:
        fatal(f"Found parameter entry without name/names in {def_filename}")

    for name in names:
        impl_defs = normalize_impldef_refs(entry, def_filename, name, "Parameter")

        out_entry: Dict[str, Any] = {
            "name": name,
            "def_filename": Path(def_filename).name,
            "chapter_name": chapter_name,
        }

        if has_type:
            out_entry["type"] = param_type
        if has_range:
            out_entry["range"] = list(param_range)
        if has_array:
            out_entry["array"] = list(param_array)

        out_entry["json-schema"] = param_type_to_json_schema(
            param_type, param_range, param_array, def_filename, name
        )

        note = entry.get("note")
        if note is not None:
            if not isinstance(note, str):
                fatal(f"Parameter {name} in {def_filename} has non-string note")
            out_entry["note"] = note

        description = entry.get("description")
        if description is not None:
            if not isinstance(description, str):
                fatal(f"Parameter {name} in {def_filename} has non-string description")
            out_entry["description"] = description

        if impl_defs:
            out_entry["impl-defs"] = resolve_impldef_entries(
                impl_defs,
                norm_rules_by_name,
                norm_rules_filename,
                def_filename,
                name,
                "Parameter",
            )

        parameters.append(out_entry)


def add_csr_entries(
    csrs: List[Dict[str, Any]],
    entry: Dict[str, Any],
    def_filename: str,
    chapter_name: str,
    norm_rules_by_name: Dict[str, Dict[str, Any]],
    norm_rules_filename: str,
):
    """Expand one CSR definition entry into one or more output CSR objects."""
    names: List[str] = []
    if "name" in entry:
        name: Any = entry.get("name")
        if not isinstance(name, str):
            fatal(f"Found CSR entry with non-string name in {def_filename}")
        names = [name]
    elif "names" in entry:
        names_value: Any = entry.get("names")
        if not isinstance(names_value, list):
            if isinstance(names_value, str):
                fatal(
                    f"Found CSR entry with non-list names in {def_filename}; "
                    f"received single name {names_value!r}. Use name: {names_value!r} instead"
                )
            fatal(f"Found CSR entry with non-list names in {def_filename}")
        for name in names_value:
            if not isinstance(name, str):
                fatal(f"Found non-string value in CSR names array in {def_filename}")
        names = list(names_value)
    else:
        fatal(f"Found CSR entry without name/names in {def_filename}")

    representative_name = names[0]

    # Resolve impl-defs at entry level (shared across all names in this entry).
    impl_def_refs = normalize_impldef_refs(entry, def_filename, representative_name, "CSR")
    if not impl_def_refs:
        fatal(
            f"CSR {representative_name} in {def_filename} has no impl-def(s); "
            "cannot derive type (impl-def-category required)"
        )
    resolved_impl_defs = resolve_impldef_entries(
        impl_def_refs,
        norm_rules_by_name,
        norm_rules_filename,
        def_filename,
        representative_name,
        "CSR",
    )

    # Derive type from impl-def-category; all impl-defs must agree.
    categories: List[str] = []
    for resolved in resolved_impl_defs:
        cat = resolved.get("impl-def-category")
        if not isinstance(cat, str):
            fatal(
                f"CSR {representative_name} in {def_filename} references impl-def "
                f"'{resolved.get('name')}' which has no impl-def-category "
                f"in normative rules {norm_rules_filename}"
            )
        assert isinstance(cat, str)
        categories.append(cat)

    if len(set(categories)) > 1:
        details = ", ".join(
            f"'{r.get('name')}': {r.get('impl-def-category')!r}"
            for r in resolved_impl_defs
        )
        fatal(
            f"CSR {representative_name} in {def_filename} has impl-defs with "
            f"conflicting impl-def-category values in normative rules {norm_rules_filename}: "
            f"{details}"
        )

    csr_type: str = categories[0]

    for name in names:
        out_entry: Dict[str, Any] = {
            "name": name,
            "def_filename": Path(def_filename).name,
            "chapter_name": chapter_name,
            "type": csr_type,
        }

        note = entry.get("note")
        if note is not None:
            if not isinstance(note, str):
                fatal(f"CSR {name} in {def_filename} has non-string note")
            out_entry["note"] = note

        description = entry.get("description")
        if description is not None:
            if not isinstance(description, str):
                fatal(f"CSR {name} in {def_filename} has non-string description")
            out_entry["description"] = description

        out_entry["impl-defs"] = resolved_impl_defs

        csrs.append(out_entry)


def create_params_hash(norm_rules_json: str, param_def_yaml_files: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Build params object that conforms to schemas/params-schema.json."""
    info(f"Loading normative rules JSON {norm_rules_json}")
    norm_rules_data = load_json_file(norm_rules_json)
    norm_rules_map = rules_by_name(norm_rules_data, norm_rules_json)

    parameters: List[Dict[str, Any]] = []
    csrs: List[Dict[str, Any]] = []
    saw_parameter_definitions = False
    saw_csr_definitions = False

    for def_file in param_def_yaml_files:
        info(f"Loading parameter definition file {def_file}")
        yaml_data = load_yaml_file(def_file)

        chapter_name_obj: Any = yaml_data.get("chapter_name")
        if not isinstance(chapter_name_obj, str):
            fatal(f"Missing or invalid chapter_name in {def_file}")
        chapter_name = chapter_name_obj

        parameter_definitions_obj: Any = yaml_data.get("parameter_definitions")
        if parameter_definitions_obj is not None:
            if not isinstance(parameter_definitions_obj, list):
                fatal(f"Invalid parameter_definitions array in {def_file}")
            saw_parameter_definitions = True
            parameter_definitions: List[Any] = parameter_definitions_obj
            for entry in parameter_definitions:
                if not isinstance(entry, dict):
                    fatal(f"Found non-object entry in parameter_definitions in {def_file}")
                add_parameter_entries(
                    parameters,
                    entry,
                    def_file,
                    chapter_name,
                    norm_rules_map,
                    norm_rules_json,
                )

        csr_definitions_obj: Any = yaml_data.get("csr_definitions")
        if csr_definitions_obj is not None:
            if not isinstance(csr_definitions_obj, list):
                fatal(f"Invalid csr_definitions array in {def_file}")
            saw_csr_definitions = True
            csr_definitions: List[Any] = csr_definitions_obj
            for entry in csr_definitions:
                if not isinstance(entry, dict):
                    fatal(f"Found non-object entry in csr_definitions in {def_file}")
                add_csr_entries(
                    csrs,
                    entry,
                    def_file,
                    chapter_name,
                    norm_rules_map,
                    norm_rules_json,
                )

        if parameter_definitions_obj is None and csr_definitions_obj is None:
            fatal(f"Missing parameter_definitions and csr_definitions arrays in {def_file}")

    output: Dict[str, List[Dict[str, Any]]] = {}
    # Always emit top-level keys so downstream tools can safely index
    # into data["parameters"] and data["csrs"], even if the lists are empty.
    output["parameters"] = parameters
    output["csrs"] = csrs
    return output


def write_json_file(pathname: str, data: Dict[str, Any]):
    """Write output dict to JSON file."""
    try:
        with open(pathname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except Exception as e:
        fatal(f"Error writing output file {pathname}: {e}")


def strip_internal_fields(obj: Any) -> Any:
    """Recursively remove internal keys (prefixed with underscore)."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for key, value in obj.items():
            if isinstance(key, str) and key.startswith("_"):
                continue
            out[key] = strip_internal_fields(value)
        return out
    if isinstance(obj, list):
        return [strip_internal_fields(x) for x in obj]
    return obj


def output_json(filename: str, params_hash: Dict[str, List[Dict[str, Any]]]):
    """Store parameters in JSON output file."""
    if not isinstance(filename, str):
        fatal(f"Need String for filename but passed a {type(filename).__name__}")
    if not isinstance(params_hash, dict):
        fatal(f"Need Dict for params_hash but passed a {type(params_hash).__name__}")

    clean_hash = strip_internal_fields(params_hash)
    if not isinstance(clean_hash, dict):
        fatal(f"Need Dict for clean_hash but got {type(clean_hash).__name__}")
    write_json_file(filename, clean_hash)


def output_html(filename: str, params_hash: Dict[str, List[Dict[str, Any]]]):
    """Store parameters in HTML output file."""
    if not isinstance(filename, str):
        fatal(f"Need String for filename but passed a {type(filename).__name__}")
    if not isinstance(params_hash, dict):
        fatal(f"Need Dict for params_hash but passed a {type(params_hash).__name__}")

    params_obj: Any = params_hash.get("parameters")
    if params_obj is not None and not isinstance(params_obj, list):
        fatal("Invalid parameters array")
    params: List[Dict[str, Any]] = params_obj if isinstance(params_obj, list) else []

    csrs_obj: Any = params_hash.get("csrs")
    if csrs_obj is not None and not isinstance(csrs_obj, list):
        fatal("Invalid csrs array")
    csrs: List[Dict[str, Any]] = csrs_obj if isinstance(csrs_obj, list) else []

    if not params and not csrs:
        fatal("Missing parameters/csrs arrays")

    chapter_names, params_by_chapter, params_no_chapter = params_by_chapter_name(params)
    csr_chapter_names, csrs_by_chapter, csrs_no_chapter = params_by_chapter_name(csrs)

    table_names: List[str] = []
    table_num = 1
    for _ in chapter_names:
        table_names.append(f"{PARAMS_CH_TABLE_NAME_PREFIX}{table_num}")
        table_num += 1
    if params_no_chapter:
        table_names.append(PARAMS_NO_CH_TABLE_NAME)

    csr_table_num = 1
    for _ in csr_chapter_names:
        table_names.append(f"{CSRS_CH_TABLE_NAME_PREFIX}{csr_table_num}")
        csr_table_num += 1
    if csrs_no_chapter:
        table_names.append(CSRS_NO_CH_TABLE_NAME)

    try:
        with open(filename, "w", encoding="utf-8") as f:
            html_head(f, table_names)
            f.write('<body>\n')
            f.write('  <div class="app">\n')

            if params:
                html_sidebar(f, chapter_names, params_by_chapter, params_no_chapter)
                if csrs:
                    html_sidebar_csrs(f, csr_chapter_names, csrs_by_chapter, csrs_no_chapter)
                else:
                    f.write('    </aside>\n')
            else:
                f.write('    <aside class="sidebar">\n')
                html_sidebar_csrs(f, csr_chapter_names, csrs_by_chapter, csrs_no_chapter)

            f.write('    <main>\n')
            f.write('      <style>.grand-total-heading { font-size: 24px; font-weight: bold; }</style>\n')
            f.write(f'      <h1 class="grand-total-heading">{get_params_counts_str(params, csrs)}</h1>\n')

            table_num = 1
            for chapter_name in chapter_names:
                chapter_params = params_by_chapter[chapter_name]
                html_params_table(
                    f,
                    f"{PARAMS_CH_TABLE_NAME_PREFIX}{table_num}",
                    f"Chapter {chapter_name}",
                    chapter_params,
                    chapter_name,
                )
                table_num += 1

            if params_no_chapter:
                html_params_table(
                    f,
                    PARAMS_NO_CH_TABLE_NAME,
                    "No chapter_name",
                    params_no_chapter,
                    None,
                )

            csr_table_num = 1
            for chapter_name in csr_chapter_names:
                chapter_csrs = csrs_by_chapter[chapter_name]
                html_csrs_table(
                    f,
                    f"{CSRS_CH_TABLE_NAME_PREFIX}{csr_table_num}",
                    f"Chapter {chapter_name}",
                    chapter_csrs,
                    chapter_name,
                )
                csr_table_num += 1

            if csrs_no_chapter:
                html_csrs_table(
                    f,
                    CSRS_NO_CH_TABLE_NAME,
                    "No chapter_name",
                    csrs_no_chapter,
                    None,
                )

            f.write('    </main>\n')
            f.write('  </div>\n')
            html_script(f)
            f.write('</body>\n')
            f.write('</html>\n')
    except Exception as e:
        fatal(f"Error writing HTML to {filename}: {e}")


def html_head(f, table_names: List[str]):
    """Write HTML head section."""
    if not isinstance(table_names, list):
        fatal(f"Need List for table_names but passed a {type(table_names).__name__}")

    css = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Parameters</title>
  <style>
    .underline {
      text-decoration: underline;
    }
    :root{
      --sidebar-width: 220px;
      --accent: #0366d6;
      --muted: #6b7280;
      --bg: #f8fafc;
      --card: #ffffff;
    }
    html{scroll-behavior:smooth}
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:var(--bg);color:#111}
    .app{display:grid;grid-template-columns:var(--sidebar-width) 1fr;min-height:100vh;}
    .sidebar{position:sticky;top:0;height:100vh;padding:24px;background:linear-gradient(180deg,#ffffff, #f1f5f9);border-right:1px solid rgba(15,23,42,0.04);box-sizing:border-box;overflow-y:auto;}
    .sidebar h2{margin:0 0 2px;font-size:18px}
    .nav{display:flex;flex-direction:column;gap:2px}
    .nav a{display:block;font-size:14px;padding:2px 10px;border-radius:6px;text-decoration:none;color:var(--accent);font-weight:600;}
    .nav a .subtitle{display:block;font-weight:400;color:var(--muted);font-size:12px}
    .nav a.active{background:rgba(3,102,214,0.12);color:var(--accent)}
    main{padding:28px 36px}
    .section{background:var(--card);border-radius:12px;padding:20px;margin-bottom:22px;box-shadow:0 1px 0 rgba(15,23,42,0.03)}
    table{border-collapse:collapse;width:100%;table-layout:fixed}
    caption{caption-side:top;text-align:left;font-weight:700;margin-bottom:8px}
    th,td{border:1px solid #d9e2ec;padding:8px 10px;vertical-align:top;word-wrap:break-word}
    thead th{background:#f1f5f9}
    .sticky-caption{position:sticky;top:0;background:#fff;padding:8px 0;z-index:1}
    .col-name{width:18%}
    .col-type{width:22%}
    .col-feature{width:18%}
    .col-descriptions{width:42%}
    @media (max-width: 1000px){
      .app{grid-template-columns:1fr}
      .sidebar{position:relative;height:auto}
      main{padding:16px}
    }
  </style>
</head>
'''
    f.write(css)


def html_sidebar(
    f,
    chapter_names: List[str],
    params_by_chapter: Dict[str, List[Dict[str, Any]]],
    params_no_chapter: List[Dict[str, Any]],
):
    """Write sidebar section."""
    if not isinstance(chapter_names, list):
        fatal(f"Need List for chapter_names but passed a {type(chapter_names).__name__}")
    if not isinstance(params_by_chapter, dict):
        fatal(f"Need Dict for params_by_chapter but passed a {type(params_by_chapter).__name__}")
    if not isinstance(params_no_chapter, list):
        fatal(f"Need List for params_no_chapter but passed a {type(params_no_chapter).__name__}")

    f.write('    <aside class="sidebar">\n')
    f.write('      <h2>Parameters by Chapter</h2>\n')
    f.write('      <nav class="nav">\n')

    table_num = 1
    for chapter_name in chapter_names:
        count = len(params_by_chapter[chapter_name])
        table_name = f"{PARAMS_CH_TABLE_NAME_PREFIX}{table_num}"
        f.write(
            f'        <a href="#{table_name}" data-target="{table_name}">'
            f'{chapter_name}<span class="subtitle">{count} entries</span></a>\n'
        )
        table_num += 1

    if params_no_chapter:
        f.write(
            f'        <a href="#{PARAMS_NO_CH_TABLE_NAME}" data-target="{PARAMS_NO_CH_TABLE_NAME}">'
            f'No chapter_name<span class="subtitle">{len(params_no_chapter)} entries</span></a>\n'
        )

    f.write('      </nav>\n')


def html_sidebar_csrs(
    f,
    chapter_names: List[str],
    csrs_by_chapter: Dict[str, List[Dict[str, Any]]],
    csrs_no_chapter: List[Dict[str, Any]],
):
    """Append CSR links in the existing sidebar section."""
    if not isinstance(chapter_names, list):
        fatal(f"Need List for chapter_names but passed a {type(chapter_names).__name__}")
    if not isinstance(csrs_by_chapter, dict):
        fatal(f"Need Dict for csrs_by_chapter but passed a {type(csrs_by_chapter).__name__}")
    if not isinstance(csrs_no_chapter, list):
        fatal(f"Need List for csrs_no_chapter but passed a {type(csrs_no_chapter).__name__}")

    f.write('      <h2 style="margin-top:24px">WARL/WLRL by Chapter</h2>\n')
    f.write('      <nav class="nav">\n')

    table_num = 1
    for chapter_name in chapter_names:
        count = len(csrs_by_chapter[chapter_name])
        table_name = f"{CSRS_CH_TABLE_NAME_PREFIX}{table_num}"
        f.write(
            f'        <a href="#{table_name}" data-target="{table_name}">'
            f'{chapter_name}<span class="subtitle">{count} entries</span></a>\n'
        )
        table_num += 1

    if csrs_no_chapter:
        f.write(
            f'        <a href="#{CSRS_NO_CH_TABLE_NAME}" data-target="{CSRS_NO_CH_TABLE_NAME}">'
            f'No chapter_name<span class="subtitle">{len(csrs_no_chapter)} entries</span></a>\n'
        )

    f.write('      </nav>\n')
    f.write('    </aside>\n')


def html_params_table(
    f,
    table_name: str,
    caption_prefix: str,
    params: List[Dict[str, Any]],
    chapter_name: Optional[str],
):
    """Write full parameters table."""
    html_table_header(f, table_name, f"{caption_prefix}: {len(params)} Parameters")
    for param in params:
        html_param_table_row(f, param, chapter_name)
    html_table_footer(f)


def html_csrs_table(
    f,
    table_name: str,
    caption_prefix: str,
    csrs: List[Dict[str, Any]],
    chapter_name: Optional[str],
):
    """Write full CSR table."""
    html_table_header(f, table_name, f"{caption_prefix}: {len(csrs)} CSRs", "CSR Name")
    for csr in csrs:
        html_param_table_row(f, csr, chapter_name)
    html_table_footer(f)


def html_table_header(f, table_name: str, table_caption: str, name_header: str = "Parameter Name"):
    """Write HTML table header."""
    f.write('\n')
    f.write(f'      <section id="{table_name}" class="section">\n')
    f.write('        <table>\n')
    f.write(f'          <caption class="sticky-caption">{table_caption}</caption>\n')
    f.write('          <colgroup>\n')
    f.write('            <col class="col-name">\n')
    f.write('            <col class="col-type">\n')
    f.write('            <col class="col-feature">\n')
    f.write('            <col class="col-descriptions">\n')
    f.write('          </colgroup>\n')
    f.write('          <thead>\n')
    f.write(
        f'            <tr><th>{name_header}</th><th>Type</th><th>Feature(s)</th>'
        '<th>Information (mostly Normative Rules)</th></tr>\n'
    )
    f.write('          </thead>\n')
    f.write('          <tbody>\n')


def format_param_type_for_html(param: Dict[str, Any]) -> str:
    """Render parameter type/range value for HTML table display."""
    scalar_display = "(unspecified)"
    param_type = param.get("type")
    if isinstance(param_type, str):
        scalar_display = param_type
    elif isinstance(param_type, list):
        values = ", ".join(str(value) for value in param_type)
        scalar_display = f"[{values}]"
    else:
        param_range = param.get("range")
        if isinstance(param_range, list) and len(param_range) == 2:
            scalar_display = f"range {param_range[0]} to {param_range[1]}"

    param_array = param.get("array")
    if isinstance(param_array, list) and len(param_array) == 2:
        return f"array[{param_array[0]}..{param_array[1]}] of {scalar_display}"

    return scalar_display


def html_param_table_row(f, param: Dict[str, Any], chapter_name: Optional[str]):
    """Write one parameter row with expanded details."""
    name = param.get("name", "")
    note = param.get("note")
    description = param.get("description")
    impl_defs_all = param.get("impl-defs")

    impl_defs = filter_impldefs_for_chapter(impl_defs_all, chapter_name)
    type_display = format_param_type_for_html(param)

    feature_param = dict(param)
    if isinstance(impl_defs_all, list):
        feature_param["impl-defs"] = impl_defs
    if chapter_name is not None:
        feature_param["chapter_name"] = chapter_name
    feature_str = format_param_feature(feature_param)

    descriptions: List[str] = []
    if isinstance(note, str):
        descriptions.append("NOTE: " + convert_def_text_to_html(note))
    if isinstance(description, str):
        descriptions.append("DESC: " + convert_def_text_to_html(description))
    for impl_def in impl_defs:
        if not isinstance(impl_def, dict):
            continue
        tags = impl_def.get("tags")
        if not isinstance(tags, list):
            continue
        for tag in tags:
            if not isinstance(tag, dict):
                continue
            tag_text = tag.get("text")
            tag_name = tag.get("name")
            target_html_fname = tag.get("stds_doc_url")
            is_context = bool(tag.get("context", False))
            if isinstance(tag_text, str):
                if not isinstance(tag_name, str):
                    fatal(
                        f"Invalid or missing tag name in normative rules JSON: {tag!r}"
                    )
                assert isinstance(tag_name, str)
                html = convert_tag_text_to_html(tag_text, target_html_fname, is_context)
                if re.search(r"<a\b", html):
                    text_with_link = html
                else:
                    text_with_link = tag2html_link(tag_name, html, target_html_fname)
                descriptions.append(text_with_link)

    if not descriptions:
        descriptions.append("(No description available)")

    row_span = len(descriptions)

    f.write('            <tr>\n')
    f.write(f'              <td rowspan={row_span} id="{name}">{name}</td>\n')
    f.write(f'              <td rowspan={row_span}>{type_display}</td>\n')
    f.write(f'              <td rowspan={row_span}>{feature_str}</td>\n')
    f.write(f'              <td>{descriptions[0]}</td>\n')
    f.write('            </tr>\n')

    for desc in descriptions[1:]:
        f.write('            <tr>\n')
        f.write(f'              <td>{desc}</td>\n')
        f.write('            </tr>\n')


def html_table_footer(f):
    """Write HTML table footer."""
    f.write('          </tbody>\n')
    f.write('        </table>\n')
    f.write('      </section>\n')


def param_chapter_names(param: Dict[str, Any]) -> List[str]:
    """Return sorted unique chapter names referenced by a parameter's impl-defs."""
    chapter_name = param.get("chapter_name")
    if isinstance(chapter_name, str):
        return [chapter_name]

    impl_defs = param.get("impl-defs")
    if not isinstance(impl_defs, list):
        return []

    names: List[str] = []
    seen = set()
    for impl_def in impl_defs:
        if not isinstance(impl_def, dict):
            continue
        name = impl_def.get("chapter_name")
        if isinstance(name, str) and name not in seen:
            seen.add(name)
            names.append(name)
    names.sort()
    return names


def params_by_chapter_name(
    params: List[Dict[str, Any]],
) -> Tuple[List[str], Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    """Group parameters by chapter_name values."""
    by_chapter: Dict[str, List[Dict[str, Any]]] = {}
    without_chapter: List[Dict[str, Any]] = []

    for param in params:
        chapters = param_chapter_names(param)
        if not chapters:
            without_chapter.append(param)
            continue
        for chapter in chapters:
            if chapter not in by_chapter:
                by_chapter[chapter] = []
            by_chapter[chapter].append(param)

    chapter_names = sorted(by_chapter.keys())
    return chapter_names, by_chapter, without_chapter


def filter_impldefs_for_chapter(impl_defs: Any, chapter_name: Optional[str]) -> List[Any]:
    """Filter impl-def objects for the specified chapter, preserving input order."""
    if not isinstance(impl_defs, list):
        return []
    if chapter_name is None:
        return list(impl_defs)

    filtered: List[Any] = []
    for impl_def in impl_defs:
        if not isinstance(impl_def, dict):
            continue
        impl_chapter = impl_def.get("chapter_name")
        if impl_chapter == chapter_name:
            filtered.append(impl_def)
    return filtered


def html_script(f):
    """Write HTML script section."""
    script = '''  <script>
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav a');

    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const id = entry.target.id;
        const link = document.querySelector('.nav a[data-target="'+id+'"]');
        if(entry.isIntersecting){
          navLinks.forEach(a=>a.classList.remove('active'));
          if(link) link.classList.add('active');
        }
      });
    }, {root:null,rootMargin:'-40% 0px -40% 0px',threshold:0});

    sections.forEach(s=>io.observe(s));
  </script>
'''
    f.write(script)


def get_params_counts_str(params: List[Dict[str, Any]], csrs: List[Dict[str, Any]]) -> str:
    """Build heading summary string for params output."""
    parts: List[str] = []
    if params:
        total_params = len(params)
        parts.append(f"{total_params} Parameter{'s' if total_params != 1 else ''}")
    if csrs:
        total_csrs = len(csrs)
        parts.append(f"{total_csrs} CSR{'s' if total_csrs != 1 else ''}")
    if not parts:
        return "0 Entries"
    return ", ".join(parts)


def main() -> int:
    """Program entry point."""
    args = parse_args()
    params = create_params_hash(args.norm_rules, args.param_def)
    info(f"Writing output file {args.output}")
    if args.output_format == "json":
        output_json(args.output, params)
    elif args.output_format == "html":
        output_html(args.output, params)
    else:
        fatal(f"Unknown output format {args.output_format}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
