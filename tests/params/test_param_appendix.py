#!/usr/bin/env python3
"""Test create_param_appendix.py output by building a combined AsciiDoc file.

Copies a template AsciiDoc file to the output path, replacing the marker
comment "// ALL GENERATED PARAMETER ADOC FILES" with include:: directives
for each generated parameter .adoc file found in the given directory
(alphabetical order, paths relative to the output file).
"""

import argparse
import os
import sys
from pathlib import Path

PN = "test_param_appendix.py"
MARKER = "// ALL GENERATED PARAMETER ADOC FILES"


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
            "Build a combined AsciiDoc file from a template and a directory of "
            "generated parameter adoc files."
        )
    )
    parser.add_argument(
        "--template",
        required=True,
        metavar="FILE",
        help="Template AsciiDoc file containing the marker comment",
    )
    parser.add_argument(
        "--adoc-dir",
        required=True,
        metavar="DIR",
        help="Directory containing generated parameter .adoc files",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="FILE",
        help="Output combined AsciiDoc file",
    )
    return parser.parse_args()


def main() -> int:
    """Program entry point."""
    args = parse_args()
    template_path = Path(args.template)
    adoc_dir = Path(args.adoc_dir)
    output_path = Path(args.output)

    # Read template.
    try:
        template_text = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fatal(f"Template file not found: {template_path}")
    except Exception as e:
        fatal(f"Error reading template {template_path}: {e}")

    # Validate the marker is present.
    if MARKER not in template_text:
        fatal(f"Marker {MARKER!r} not found in template {template_path}")

    # Collect .adoc files alphabetically.
    if not adoc_dir.is_dir():
        fatal(f"Adoc directory not found: {adoc_dir}")
    adoc_files = sorted(adoc_dir.glob("*.adoc"))
    if not adoc_files:
        fatal(f"No .adoc files found in {adoc_dir}")
    info(f"Found {len(adoc_files)} .adoc files in {adoc_dir}")

    # Compute include paths relative to the output file's parent directory.
    output_parent = output_path.resolve().parent
    rel_dir = Path(os.path.relpath(adoc_dir.resolve(), output_parent))

    # Build include directives.
    include_lines = "\n".join(
        f"include::{rel_dir / f.name}[]" for f in adoc_files
    )

    # Keep marker comment in output and place include directives below it.
    output_text = template_text.replace(MARKER, f"{MARKER}\n\n{include_lines}")

    # Write output.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(output_text, encoding="utf-8")
    except Exception as e:
        fatal(f"Error writing output {output_path}: {e}")

    info(f"Wrote combined AsciiDoc to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
