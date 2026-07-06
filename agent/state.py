"""Shared state schema for the debugging agent.

Defined at package level so both the plain while-loop prototype and the
LangGraph state machine can speak the same dialect.
"""

from __future__ import annotations

from typing import TypedDict


class HistoryEntry(TypedDict, total=False):
    attempt: int
    code: str
    success: bool
    error: str
    exception_type: str | None
    duration_ms: int
    rejected: bool
    llm_output: str | None


class DebugState(TypedDict, total=False):
    """Full state object passed through the graph.

    All fields are optional in the TypedDict sense (``total=False``) because
    LangGraph nodes return partial updates. In practice the entry point
    populates every field except ``error`` / ``exception_type`` /
    ``last_result`` before the graph runs.
    """

    code: str
    original_code: str
    tests: str | None
    error: str
    exception_type: str | None
    attempts: int
    max_attempts: int
    history: list[HistoryEntry]
    success: bool
    timeout: float
    model: str | None


def initial_state(
    code: str,
    *,
    tests: str | None = None,
    max_attempts: int = 3,
    timeout: float = 10.0,
    model: str | None = None,
) -> DebugState:
    """Convenience constructor with sensible defaults."""
    return DebugState(
        code=code,
        original_code=code,
        tests=tests,
        error="",
        exception_type=None,
        attempts=0,
        max_attempts=max_attempts,
        history=[],
        success=False,
        timeout=timeout,
        model=model,
    )
