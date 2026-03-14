#!/usr/bin/env python3
"""Unit-level tests for shared_utils.py helpers."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

import io
import json
import sys
import tempfile
from importlib import util
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict, Optional

# Ensure tools/ is importable when running from repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import shared_utils  # noqa: E402


class FatalRaised(Exception):
    """Raised by test fatal callback to capture fatal messages."""


def expect_fatal(callable_obj, *args, **kwargs):
    """Call helper and return fatal message if fatal callback is invoked."""
    captured: Dict[str, Optional[str]] = {"message": None}

    def fatal_callback(message: str):
        captured["message"] = message
        raise FatalRaised(message)

    kwargs["fatal"] = fatal_callback
    try:
        callable_obj(*args, **kwargs)
    except FatalRaised:
        pass
    else:
        raise AssertionError("Expected fatal callback to be invoked")

    assert isinstance(captured["message"], str)
    return captured["message"]


def test_error_prints_expected_prefix():
    err = io.StringIO()
    with redirect_stderr(err):
        shared_utils.error("boom")
    assert err.getvalue() == "shared_utils.py: ERROR: boom\n"


def test_make_log_helpers_info_and_error_output():
    helper_error, helper_info, _ = shared_utils.make_log_helpers("sample.py")

    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        helper_info("hello")
        helper_error("bad")

    assert out.getvalue() == "sample.py: hello\n"
    assert err.getvalue() == "sample.py: ERROR: bad\n"


def test_make_log_helpers_fatal_exits():
    _, _, helper_fatal = shared_utils.make_log_helpers("sample.py")

    err = io.StringIO()
    try:
        with redirect_stderr(err):
            helper_fatal("stop")
    except SystemExit as ex:
        assert ex.code == 1
    else:
        raise AssertionError("Expected SystemExit from fatal helper")

    assert err.getvalue() == "sample.py: ERROR: stop\n"


def test_load_json_object_success_and_top_level_validation():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = tmp_path / "good.json"
        bad = tmp_path / "bad.json"

        good.write_text(json.dumps({"k": 1}), encoding="utf-8")
        bad.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

        fatal_messages = []

        def fatal_cb(msg: str):
            fatal_messages.append(msg)
            raise FatalRaised(msg)

        loaded = shared_utils.load_json_object(str(good), fatal_cb)
        assert loaded == {"k": 1}

        try:
            shared_utils.load_json_object(str(bad), fatal_cb)
        except FatalRaised:
            pass
        else:
            raise AssertionError("Expected fatal for non-object JSON")

        assert fatal_messages[-1] == f"Expected top-level JSON object in {bad}"


def test_load_yaml_object_success():
    if util.find_spec("yaml") is None:
        # The Makefile test path runs in a container with dependencies; skip locally.
        return

    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = Path(tmp) / "good.yaml"
        yaml_path.write_text("chapter_name: CH1\n", encoding="utf-8")

        def fatal_cb(msg: str):
            raise FatalRaised(msg)

        loaded = shared_utils.load_yaml_object(str(yaml_path), fatal_cb)
        assert loaded == {"chapter_name": "CH1"}


def test_format_param_feature_impldefs_and_fallbacks():
    param = {
        "impl-defs": [
            {"kind": "base", "instances": ["RV64I", "RV64I"]},
            {"kind": "extension", "instances": ["Zicsr"]},
            {"kind": "mystery", "instances": ["Xfoo"]},
        ]
    }
    err = io.StringIO()
    with redirect_stderr(err):
        assert shared_utils.format_param_feature(param) == "BASE:RV64I, EXT:Zicsr, Xfoo"
    assert "Unknown standards object kind 'mystery'" in err.getvalue()

    assert shared_utils.format_param_feature({"chapter_name": "CH2"}) == "CHAP:CH2"
    assert shared_utils.format_param_feature({}) == "(unspecified)"


def test_check_kind_validation():
    # Known kind should not invoke fatal.
    shared_utils.check_kind("base", "NR-1", None, lambda msg: (_ for _ in ()).throw(AssertionError(msg)), "x.py")

    message = expect_fatal(shared_utils.check_kind, "unknown", "NR-2", "tag-a", program_name="x.py")
    assert "Don't recognize kind 'unknown'" in message
    assert "tag tag-a in normative rule NR-2" in message
    assert "x.py: Allowed kinds are:" in message


def test_check_impldef_cat_validation():
    # Known category should not invoke fatal.
    shared_utils.check_impldef_cat("WARL", "NR-1", None, lambda msg: (_ for _ in ()).throw(AssertionError(msg)), "x.py")

    message = expect_fatal(shared_utils.check_impldef_cat, "BAD", "NR-2", "tag-b", program_name="x.py")
    assert "Don't recognize impl-def-category 'BAD'" in message
    assert "tag tag-b in normative rule NR-2" in message
    assert "x.py: Allowed impl-def-categories are:" in message


def main() -> int:
    test_error_prints_expected_prefix()
    test_make_log_helpers_info_and_error_output()
    test_make_log_helpers_fatal_exits()
    test_load_json_object_success_and_top_level_validation()
    test_load_yaml_object_success()
    test_format_param_feature_impldefs_and_fallbacks()
    test_check_kind_validation()
    test_check_impldef_cat_validation()
    print("test_shared_utils.py: all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
