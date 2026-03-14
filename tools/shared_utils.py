"""Shared tables and helpers for tools scripts.

This module contains reusable constants and routines consumed by
multiple Python scripts in the tools directory.
"""

import sys
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
        return chapter_name if isinstance(chapter_name, str) and chapter_name else "(unspecified)"

    return ", ".join(features)


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
