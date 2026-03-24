"""Shared tables and helpers for tools scripts.

This module contains reusable constants and routines consumed by
multiple Python scripts in the tools directory.
"""

import sys
import traceback
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import json


STDS_OBJECT_KINDS: List[str] = [
    "base",
    "extension",
    "extension_dependency",
    "instruction",
    "csr",
    "csr_field",
]


IMPLDEF_CATEGORIES: List[str] = ["WARL", "WLRL"]

# Explicit mapping from impl-def-category values (implDefCategoryType in common-schema.json)
# to output CSR category values (csrCategory in param-common-schema.json).
# These use separate schema definitions so they cannot be assumed identical.
IMPLDEF_CATEGORY_TO_CSR_CATEGORY: Dict[str, str] = {
    "WARL": "WARL",
    "WLRL": "WLRL",
}


def impldef_category_to_csr_category(
    impldef_cat: str,
    fatal: Callable[[str], None],
) -> str:
    """Convert an impl-def-category value to its output CSR category.

    Uses an explicit mapping so that changes to either schema are caught
    at the mapping site rather than silently passed through.
    """
    result = IMPLDEF_CATEGORY_TO_CSR_CATEGORY.get(impldef_cat)
    if result is None:
        allowed_str = ", ".join(sorted(IMPLDEF_CATEGORY_TO_CSR_CATEGORY))
        fatal(
            f"No CSR category mapping for impl-def-category {impldef_cat!r}. "
            f"Allowed impl-def-categories are: {allowed_str}"
        )
        return ""  # unreachable; fatal() does not return
    return result


STDS_OBJECT_KIND_TO_FEATURE: Dict[str, str] = {
    "base": "BASE",
    "extension": "EXT",
    "csr": "CSR",
    "csr_field": "FLD",
    "extension_dependency": "EXT_DEP",
    "instruction": "INST",
}


NORM_RULES_BASE_URL = (
    "https://riscv.github.io/riscv-isa-manual/snapshot/norm-rules/norm-rules.html"
)

PN = "shared_utils.py"


def error(msg: str):
    """Print an error message."""
    print(f"{PN}: ERROR: {msg}", file=sys.stderr)


def make_log_helpers(program_name: str) -> Tuple[Callable[[str], None], Callable[[str], None], Callable[[str], None]]:
    """Create script-scoped error/info/fatal helper functions.

    Returns a tuple of (error, info, fatal) callables that prefix messages with
    the specified program name.
    """

    def error(msg: str):
        print(f"{program_name}: ERROR: {msg}", file=sys.stderr)

    def info(msg: str):
        print(f"{program_name}: {msg}")

    def fatal(msg: str):
        error(msg)
        traceback.print_stack(file=sys.stderr)
        sys.exit(1)

    return error, info, fatal


def load_json_object(pathname: str, fatal: Callable[[str], None]) -> Dict[str, Any]:
    """Load and validate a top-level JSON object from a file."""
    path = Path(pathname)
    data: Any = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        fatal(str(e))
    except json.JSONDecodeError as e:
        fatal(f"JSON parse error in {pathname}: {e}")
    except Exception as e:
        fatal(f"Error reading JSON file {pathname}: {e}")

    if not isinstance(data, dict):
        fatal(f"Expected top-level JSON object in {pathname}")

    return data


def load_yaml_object(pathname: str, fatal: Callable[[str], None]) -> Dict[str, Any]:
    """Load and validate a top-level YAML object from a file."""
    yaml_module: Any = None
    try:
        yaml_module = import_module("yaml")
    except ImportError:
        fatal("PyYAML is required but not installed. Run: pip install PyYAML")

    path = Path(pathname)
    data: Any = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml_module.safe_load(f)
    except FileNotFoundError as e:
        fatal(str(e))
    except yaml_module.YAMLError as e:
        fatal(f"YAML parse error in {pathname}: {e}")
    except Exception as e:
        fatal(f"Error reading YAML file {pathname}: {e}")

    if not isinstance(data, dict):
        fatal(f"Expected top-level YAML object in {pathname}")

    return data


def format_param_feature(
    param: Dict[str, Any],
) -> str:
    """Render a parameter feature string from chapter name and impl-defs."""
    impl_defs = param.get("impl-defs")
    if not isinstance(impl_defs, list):
        chapter_name = param.get("chapter_name")
        if isinstance(chapter_name, str) and chapter_name:
            return f"CHAP:{chapter_name}"
        return "(unspecified)"

    features: List[str] = []
    seen = set()
    warned_unknown_kinds = set()
    for impl_def in impl_defs:
        if not isinstance(impl_def, dict):
            continue
        kind = impl_def.get("kind")
        prefix = None
        if isinstance(kind, str):
            prefix = STDS_OBJECT_KIND_TO_FEATURE.get(kind)
            if prefix is None and kind not in warned_unknown_kinds:
                warned_unknown_kinds.add(kind)
                error(
                    "Unknown standards object kind "
                    f"{kind!r}; expected one of {', '.join(STDS_OBJECT_KINDS)}"
                )
        elif kind is not None:
            kind_type = type(kind).__name__
            marker = f"type:{kind_type}"
            if marker not in warned_unknown_kinds:
                warned_unknown_kinds.add(marker)
                error(
                    "Unknown standards object kind type "
                    f"{kind_type!r}; expected string kind values"
                )
        instances = impl_def.get("instances")
        if not isinstance(instances, list):
            continue
        for instance in instances:
            if not isinstance(instance, str):
                continue
            rendered = f"{prefix}:{instance}" if prefix else instance
            if rendered not in seen:
                seen.add(rendered)
                features.append(rendered)

    if not features:
        chapter_name = param.get("chapter_name")
        if isinstance(chapter_name, str) and chapter_name:
            return f"CHAP:{chapter_name}"
        return "(unspecified)"

    return ", ".join(features)


def infer_param_type_string(
    param: Dict[str, Any],
    fatal: Callable[[str], None],
) -> str:
    """Render a parameter type string for table output.

    The input shape mirrors entries in params JSON output, including support for
    scalar type/range forms and optional array bounds.
    """
    param_type = param.get("type")
    param_range = param.get("range")
    param_array = param.get("array")
    param_width = param.get("width")

    param_name = "<unknown>"
    param_name_obj = param.get("name")
    if isinstance(param_name_obj, str) and param_name_obj:
        param_name = param_name_obj
    else:
        reg_name_obj = param.get("reg-name")
        field_name_obj = param.get("field-name")
        if isinstance(reg_name_obj, str) and reg_name_obj:
            if isinstance(field_name_obj, str) and field_name_obj:
                param_name = f"{reg_name_obj}.{field_name_obj}"
            else:
                param_name = reg_name_obj
        else:
            fatal("Expected parameter name or CSR reg-name to be a non-empty string")

    scalar_type = ""

    if isinstance(param_type, list):
        if not param_type:
            fatal(f"Parameter {param_name!r} has an empty type array")
        if all(isinstance(v, str) for v in param_type):
            enum_values = ", ".join(param_type)
            scalar_type = f"[{enum_values}]"
        elif all(isinstance(v, int) and not isinstance(v, bool) for v in param_type):
            enum_values = ", ".join(map(str, param_type))
            scalar_type = f"[{enum_values}]"
        else:
            fatal(
                f"Parameter {param_name!r} has invalid type array; expected all strings "
                "or all integers"
            )

    elif isinstance(param_type, str):
        if param_type in {"boolean", "bit", "byte", "hword", "word", "dword"}:
            scalar_type = param_type

        if param_type in {"int", "uint"}:
            if isinstance(param_width, int) and not isinstance(param_width, bool):
                signedness = "signed" if param_type == "int" else "unsigned"
                scalar_type = f"{param_width}-bit {signedness} integer"
            elif isinstance(param_width, str):
                signedness = "signed" if param_type == "int" else "unsigned"
                scalar_type = f"{param_width}-bit {signedness} integer"
            else:
                fatal(
                    f"Parameter {param_name!r} has type {param_type!r} but no valid width"
                )

        if not scalar_type:
            # Keep unknown string types representable for callers that include
            # non-parameter objects (e.g. CSR categories like WARL/WLRL).
            scalar_type = param_type

        if not scalar_type:
            fatal(f"Parameter {param_name!r} has invalid type of {param_type!r}")

    elif isinstance(param_range, list):
        if len(param_range) != 2:
            fatal(
                f"Parameter {param_name!r} has invalid range array; expected exactly 2 values"
            )

        lo, hi = param_range

        if isinstance(lo, int) and not isinstance(lo, bool) and isinstance(hi, int) and not isinstance(hi, bool):
            if lo > hi:
                fatal(
                    f"Parameter {param_name!r} has min range value {lo!r} greater than max range value {hi!r}"
                )
            scalar_type = f"range {lo} to {hi}"

        if not isinstance(lo, int) or isinstance(lo, bool):
            fatal(
                f"Parameter {param_name!r} has non-integer min range value of {lo!r}"
            )

        if not isinstance(hi, int) or isinstance(hi, bool):
            fatal(
                f"Parameter {param_name!r} has non-integer max range value of {hi!r}"
            )

    else:
        fatal(
            f"Parameter {param_name!r} has neither a valid type nor a valid range"
        )

    if isinstance(param_array, list):
        if len(param_array) != 2:
            fatal(
                f"Parameter {param_name!r} has invalid array bounds; expected exactly 2 values"
            )

        lo, hi = param_array
        if not isinstance(lo, int) or isinstance(lo, bool):
            fatal(
                f"Parameter {param_name!r} has non-integer min array value of {lo!r}"
            )
        if not isinstance(hi, int) or isinstance(hi, bool):
            fatal(
                f"Parameter {param_name!r} has non-integer max array value of {hi!r}"
            )
        if lo < 0 or hi < 0:
            fatal(
                f"Parameter {param_name!r} has invalid array bounds; values must be non-negative"
            )
        if lo > hi:
            fatal(
                f"Parameter {param_name!r} has min array value {lo!r} greater than max array value {hi!r}"
            )
        return f"array[{lo}..{hi}] of {scalar_type}"

    return scalar_type


def check_kind(
    kind: str,
    nr_name: str,
    name: Optional[str],
    fatal: Callable[[str], None],
    program_name: str = "create_normative_rules.py",
):
    """Fatal if kind is not recognized.

    The name is None if this is called in the normative rule definition.
    """
    if kind not in STDS_OBJECT_KINDS:
        tag_str = "" if name is None else f"tag {name} in "
        allowed_str = ",".join(STDS_OBJECT_KINDS)
        fatal(
            f"Don't recognize kind '{kind}' for {tag_str}normative rule {nr_name}\n"
            f"{program_name}: Allowed kinds are: {allowed_str}"
        )


def check_impldef_cat(
    impldef_cat: str,
    nr_name: str,
    name: Optional[str],
    fatal: Callable[[str], None],
    program_name: str = "create_normative_rules.py",
):
    """Fatal if impl-def-category is not recognized.

    The name is None if this is called in the normative rule definition.
    """
    if impldef_cat not in IMPLDEF_CATEGORIES:
        tag_str = "" if name is None else f"tag {name} in "
        allowed_str = ",".join(IMPLDEF_CATEGORIES)
        fatal(
            f"Don't recognize impl-def-category '{impldef_cat}' for {tag_str}normative rule {nr_name}\n"
            f"{program_name}: Allowed impl-def-categories are: {allowed_str}"
        )
