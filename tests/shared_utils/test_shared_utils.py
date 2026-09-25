#!/usr/bin/env python3
"""Unit-level tests for shared_utils.py helpers."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

import io
import json
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Ensure tools/ is importable when running from repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import shared_utils  # noqa: E402


class FatalRaised(Exception):
    """Raised by test fatal callback to capture fatal messages."""


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


def main() -> int:
    test_error_prints_expected_prefix()
    test_make_log_helpers_info_and_error_output()
    test_make_log_helpers_fatal_exits()
    test_load_json_object_success_and_top_level_validation()
    print("test_shared_utils.py: all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
