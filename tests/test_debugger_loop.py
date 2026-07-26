"""End-to-end tests for the debug loop with the LLM mocked out.

Verifies that:
1. Already-passing code returns immediately.
2. The agent retries with the LLM's suggestion and converges in N attempts.
3. The agent gives up after ``max_attempts`` and surfaces the final error.

These tests do NOT touch the OpenAI API.
"""

from __future__ import annotations

import textwrap
from unittest.mock import patch

from agent import debugger as dbg


def test_already_clean_code_terminates_immediately() -> None:
    with patch.object(dbg, "fix_code") as mock_fix:
        session = dbg.run_debug_session("print('hello')", max_attempts=3)
    assert session.success is True
    assert session.attempts_used == 1
    assert mock_fix.call_count == 0
    assert len(session.history) == 1
    assert session.history[0]["success"] is True


def test_agent_converges_when_llm_returns_a_valid_fix() -> None:
    fixed = "x = [1, 2, 3]\nprint(x[0])"
    with patch.object(dbg, "fix_code", return_value=fixed) as mock_fix:
        session = dbg.run_debug_session(
            "x = [1, 2, 3]\nprint(x[10])",
            max_attempts=3,
        )
    assert session.success is True
    assert session.attempts_used == 2
    assert mock_fix.call_count == 1
    assert "x[0]" in session.final_code


def test_agent_gives_up_when_llm_keeps_returning_garbage() -> None:
    # LLM "fixes" produce code that still fails.
    bad_responses = ["1/0", "1/0", "1/0"]
    with patch.object(dbg, "fix_code", side_effect=bad_responses) as mock_fix:
        session = dbg.run_debug_session("1/0", max_attempts=3)
    assert session.success is False
    assert session.attempts_used == 3
    assert mock_fix.call_count == 2
    assert session.final_exception_type == "ZeroDivisionError"


def test_history_records_per_attempt_metadata() -> None:
    fixed = "print('done')"
    with patch.object(dbg, "fix_code", return_value=fixed):
        session = dbg.run_debug_session("raise ValueError('boom')", max_attempts=3)
    assert session.success is True
    assert len(session.history) == 2
    assert session.history[0]["success"] is False
    assert session.history[0]["exception_type"] == "ValueError"
    assert session.history[0]["llm_output"] == fixed
    assert session.history[1]["success"] is True


def test_plain_while_loop_matches_graph_behavior() -> None:
    fixed = "x = 1 + 1\nprint(x)"
    with patch.object(dbg, "fix_code", return_value=fixed):
        state = dbg.debug_loop("print(undefined_var)", max_attempts=3)
    assert state["success"] is True
    assert state["attempts"] == 1


def test_tests_payload_is_executed_alongside_candidate() -> None:
    candidate = textwrap.dedent(
        """
        def add(a, b):
            return a + b
        """
    )
    harness = "assert add(1, 2) == 3\nprint('OK')"
    with patch.object(dbg, "fix_code") as mock_fix:
        session = dbg.run_debug_session(candidate, tests=harness, max_attempts=2)
    assert session.success is True
    assert mock_fix.call_count == 0
