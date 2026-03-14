#!/usr/bin/env python3
"""Create one AsciiDoc table-row fragment file per parameter.

Input JSON must conform to schemas/params-schema.json.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

PN = "create_param_adoc_files.py"
NORM_RULES_BASE_URL = (
    "https://riscv.github.io/riscv-isa-manual/snapshot/norm-rules/norm-rules.html"
)


def error(msg: str):
    """Print an error message."""
    print(f"{PN}: ERROR: {msg}", file=sys.stderr)


def fatal(msg: str):
    """Print an error and exit."""
    error(msg)
    sys.exit(1)


def info(msg: str):
    """Print an informational message."""
    print(f"{PN}: {msg}")


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
    return parser.parse_args()


def load_params_json(pathname: str) -> Dict[str, Any]:
    """Load params JSON and validate top-level shape."""
    try:
        with open(pathname, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        fatal(str(e))
    except json.JSONDecodeError as e:
        fatal(f"JSON parse error in {pathname}: {e}")
    except Exception as e:
        fatal(f"Error reading JSON file {pathname}: {e}")

    if not isinstance(data, dict):
        fatal(f"Expected top-level JSON object in {pathname}")

    params_obj: Any = data.get("parameters")
    if not isinstance(params_obj, list):
        fatal(f"Expected parameters array in {pathname}")

    for idx, param in enumerate(params_obj):
        if not isinstance(param, dict):
            fatal(f"Expected parameters[{idx}] to be an object")
        name = param.get("name")
        if not isinstance(name, str) or not name:
            fatal(f"Expected parameters[{idx}].name to be a non-empty string")

    return data


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


def infer_isa_feature(param: Dict[str, Any]) -> str:
    """Render ISA feature string for table column 3."""
    impl_defs = param.get("impl-defs")
    if not isinstance(impl_defs, list):
        chapter_name = param.get("chapter_name")
        return chapter_name if isinstance(chapter_name, str) and chapter_name else "(unspecified)"

    instance_aliases = {
        "A": "Atomic (Zalrsc extension)",
        "RV32I": "RV32I/RV64I Base ISA",
        "Zihpm": "Zicntr",
    }

    features: List[str] = []
    seen = set()
    for impl_def in impl_defs:
        if not isinstance(impl_def, dict):
            continue
        instances = impl_def.get("instances")
        if not isinstance(instances, list):
            continue
        for instance in instances:
            if not isinstance(instance, str):
                continue
            rendered = instance_aliases.get(instance, instance)
            if rendered not in seen:
                seen.add(rendered)
                features.append(rendered)

    if not features:
        chapter_name = param.get("chapter_name")
        return chapter_name if isinstance(chapter_name, str) and chapter_name else "(unspecified)"

    return ", ".join(features)


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


def render_parameter_row_fragment(param: Dict[str, Any]) -> str:
    """Render one AsciiDoc row fragment (4 columns)."""
    name = param["name"]
    type_str = infer_type_string(param)
    isa_feature = infer_isa_feature(param)
    norm_rules = infer_normative_rules(param)

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

    lines.append(f"| {type_str}")
    lines.append(f"| {isa_feature}")
    lines.append(render_definition_cell(param))

    return "\n".join(lines) + "\n"


def write_output_files(params: List[Dict[str, Any]], output_dir: Path):
    """Write one .adoc file per parameter."""
    output_dir.mkdir(parents=True, exist_ok=True)

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

        out_path = output_dir / f"{file_stem}.adoc"
        content = render_parameter_row_fragment(param)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            fatal(f"Error writing {out_path}: {e}")


def main() -> int:
    """Program entry point."""
    args = parse_args()
    data = load_params_json(args.input)
    params = data["parameters"]

    out_dir = Path(args.output_dir)
    info(f"Writing {len(params)} parameter AsciiDoc files to {out_dir}")
    write_output_files(params, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
