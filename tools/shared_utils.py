"""Shared helpers for tools scripts.

This module contains reusable routines consumed by
multiple Python scripts in the tools directory.
"""

import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

import json


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
