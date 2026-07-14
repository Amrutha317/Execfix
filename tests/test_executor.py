"""Smoke tests for the hardened subprocess sandbox.

These run with plain ``pytest`` and don't touch the OpenAI API.
"""

from __future__ import annotations

import textwrap

from agent.executor import execute_code, scan_for_violations


# --------------------------------------------------------------------------- #
# Happy paths                                                                 #
# --------------------------------------------------------------------------- #


def test_clean_program_succeeds() -> None:
    result = execute_code("print('hello')")
    assert result.success is True
    assert "hello" in result.stdout
    assert result.stderr == ""
    assert result.exception_type is None
    assert result.was_rejected is False


def test_runtime_exception_is_captured() -> None:
    result = execute_code("print(1/0)")
    assert result.success is False
    assert result.exception_type == "ZeroDivisionError"
    assert "ZeroDivisionError" in result.stderr


def test_index_error_is_captured() -> None:
    result = execute_code("x = [1, 2, 3]\nprint(x[10])")
    assert result.success is False
    assert result.exception_type == "IndexError"


def test_syntax_error_is_captured() -> None:
    bad = textwrap.dedent(
        """
        def add(a, b)
            return a + b
        """
    )
    result = execute_code(bad)
    assert result.success is False
    assert result.exception_type == "SyntaxError"


# --------------------------------------------------------------------------- #
# Sandbox rejections                                                          #
# --------------------------------------------------------------------------- #


def test_socket_import_is_rejected_pre_run() -> None:
    result = execute_code("import socket\ns = socket.socket()")
    assert result.was_rejected
    assert result.exception_type == "SandboxRejection"
    assert "socket" in (result.rejected_reason or "")


def test_subprocess_import_is_rejected() -> None:
    result = execute_code("import subprocess\nsubprocess.run(['echo', 'hi'])")
    assert result.was_rejected
    assert "subprocess" in (result.rejected_reason or "")


def test_os_system_call_is_rejected() -> None:
    result = execute_code("import os\nos.system('echo hi')")
    assert result.was_rejected
    assert "os.system" in (result.rejected_reason or "")


def test_dunder_import_backdoor_is_rejected() -> None:
    result = execute_code("__import__('socket')")
    assert result.was_rejected


def test_eval_is_rejected() -> None:
    result = execute_code("eval(\"print('pwned')\")")
    assert result.was_rejected


def test_plain_os_path_is_allowed() -> None:
    """``os.path.join`` and other read-only helpers should still work."""
    result = execute_code("import os.path\nprint(os.path.join('a', 'b'))")
    assert result.success is True
    assert "a" in result.stdout and "b" in result.stdout


# --------------------------------------------------------------------------- #
# Timeout                                                                     #
# --------------------------------------------------------------------------- #


def test_infinite_loop_is_killed_by_timeout() -> None:
    result = execute_code("while True:\n    pass", timeout=1.0)
    assert result.success is False
    assert result.exception_type == "TimeoutError"
    assert "exceeded" in result.stderr


# --------------------------------------------------------------------------- #
# Pure scanner                                                                #
# --------------------------------------------------------------------------- #


def test_scan_for_violations_flags_blocked_import() -> None:
    violation, syntax_err = scan_for_violations("import socket")
    assert violation is not None
    assert syntax_err is None


def test_scan_for_violations_returns_syntax_error_for_unparseable() -> None:
    violation, syntax_err = scan_for_violations("def broken(:")
    assert violation is None
    assert syntax_err is not None
    assert "SyntaxError" in syntax_err
