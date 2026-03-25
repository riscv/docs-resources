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

    stderr_output = err.getvalue()
    assert stderr_output.startswith("sample.py: ERROR: stop\n")
    assert "traceback.print_stack" in stderr_output


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


def test_infer_param_type_string_success_cases():
    # Core scalar keyword types.
    assert (
        shared_utils.infer_param_type_string(
            {"name": "P_BOOL", "type": "boolean"},
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "boolean"
    )
    assert (
        shared_utils.infer_param_type_string(
            {"name": "P_INT", "type": "int", "width": 32},
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "32-bit signed integer"
    )
    assert (
        shared_utils.infer_param_type_string(
            {"name": "P_UINT", "type": "uint", "width": "MXLEN"},
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "MXLEN-bit unsigned integer"
    )

    # Unknown string types are preserved (used by CSR paths such as WARL/WLRL).
    assert (
        shared_utils.infer_param_type_string(
            {"name": "P_CSR", "type": "WARL"},
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "WARL"
    )

    # Enumerations.
    assert (
        shared_utils.infer_param_type_string(
            {"name": "P_ENUM_S", "type": ["A", "B"]},
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "[A, B]"
    )
    assert (
        shared_utils.infer_param_type_string(
            {"name": "P_ENUM_I", "type": [1, 2, 3]},
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "[1, 2, 3]"
    )
    assert (
        shared_utils.infer_param_type_string(
            {
                "reg-name": "foo",
                "field-name": "ABC",
                "enum": {
                    "legal": [0, 3, 10],
                    "illegal-write-return": 0,
                },
            },
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "[0, 3, 10]"
    )

    # Range and array wrapping.
    assert (
        shared_utils.infer_param_type_string(
            {"name": "P_RANGE", "range": [0, 16]},
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "range 0 to 16"
    )
    assert (
        shared_utils.infer_param_type_string(
            {"name": "P_ARRAY", "type": "uint", "width": 8, "array": [0, 3]},
            lambda msg: (_ for _ in ()).throw(AssertionError(msg)),
        )
        == "array[0..3] of 8-bit unsigned integer"
    )


def test_infer_param_type_string_all_fatal_cases():
    cases = [
        (
            {"type": "boolean"},
            "Expected parameter name or CSR reg-name to be a non-empty string",
        ),
        (
            {"name": "P", "type": []},
            "has an empty type array",
        ),
        (
            {"name": "P", "type": ["A", 1]},
            "has invalid type array; expected all strings or all integers",
        ),
        (
            {"name": "P", "type": [True, False]},
            "has invalid type array; expected all strings or all integers",
        ),
        (
            {"name": "P", "type": "int"},
            "has type 'int' but no valid width",
        ),
        (
            {"name": "P", "type": "uint", "width": True},
            "has type 'uint' but no valid width",
        ),
        (
            {"name": "P", "type": ""},
            "has invalid type of ''",
        ),
        (
            {"name": "P", "range": [0]},
            "has invalid range array; expected exactly 2 values",
        ),
        (
            {"name": "P", "range": [3, 1]},
            "has min range value 3 greater than max range value 1",
        ),
        (
            {"name": "P", "range": ["0", 1]},
            "has non-integer min range value of '0'",
        ),
        (
            {"name": "P", "range": [0, "1"]},
            "has non-integer max range value of '1'",
        ),
        (
            {"name": "P", "range": [True, 1]},
            "has non-integer min range value of True",
        ),
        (
            {"name": "P", "range": [0, True]},
            "has non-integer max range value of True",
        ),
        (
            {"name": "P"},
            "has neither a valid type, enum, nor a valid range",
        ),
        (
            {"name": "P", "type": "boolean", "array": [0]},
            "has invalid array bounds; expected exactly 2 values",
        ),
        (
            {"name": "P", "type": "boolean", "array": ["0", 1]},
            "has non-integer min array value of '0'",
        ),
        (
            {"name": "P", "type": "boolean", "array": [True, 1]},
            "has non-integer min array value of True",
        ),
        (
            {"name": "P", "type": "boolean", "array": [0, "1"]},
            "has non-integer max array value of '1'",
        ),
        (
            {"name": "P", "type": "boolean", "array": [True, 1]},
            "has non-integer min array value of True",
        ),
        (
            {"name": "P", "type": "boolean", "array": [0, True]},
            "has non-integer max array value of True",
        ),
        (
            {"name": "P", "type": "boolean", "array": [0, False]},
            "has non-integer max array value of False",
        ),
        (
            {"name": "P", "type": "boolean", "array": [-1, 2]},
            "has invalid array bounds; values must be non-negative",
        ),
        (
            {"name": "P", "type": "boolean", "array": [4, 2]},
            "has min array value 4 greater than max array value 2",
        ),
    ]

    for param, expected_substring in cases:
        message = expect_fatal(shared_utils.infer_param_type_string, param)
        assert expected_substring in message


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
    test_infer_param_type_string_success_cases()
    test_infer_param_type_string_all_fatal_cases()
    test_check_kind_validation()
    test_check_impldef_cat_validation()
    print("test_shared_utils.py: all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
