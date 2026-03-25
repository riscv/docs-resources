#!/usr/bin/env python3
"""Shared helpers for appendix generators."""

import re
from typing import Any, Dict, List


def safe_filename(name: str) -> str:
    """Map a display name to a safe output filename stem."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def infer_normative_rules(item: Dict[str, Any]) -> List[str]:
    """Return unique normative rule names referenced by impl-defs."""
    impl_defs = item.get("impl-defs")
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


def render_table_cols_spec(columns: List[Dict[str, Any]]) -> str:
    """Render AsciiDoc cols specification from column widths."""
    return ",".join(f"{col['width_pct']}%" for col in columns)


def render_table_header_row(columns: List[Dict[str, Any]]) -> str:
    """Render AsciiDoc header row from configured display names."""
    return "| " + " | ".join(str(col["name"]) for col in columns)
