"""Service functions that wrap existing agent/eval modules."""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

# Ensure project root imports work when running uvicorn from backend/.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.debugger import run_debug_session
from agent.llm import DEFAULT_MODEL
from eval.evaluator import _summarize, evaluate_problem
from eval.quixbugs_loader import iter_problems


def run_debug(
    *,
    code: str,
    tests: str | None,
    max_attempts: int,
    timeout: float,
    model: str | None,
) -> dict[str, Any]:
    """Run a single debugging session and return API-safe dict."""
    session = run_debug_session(
        code=code,
        tests=tests,
        max_attempts=max_attempts,
        timeout=timeout,
        model=model,
    )
    return {
        "success": session.success,
        "attempts_used": session.attempts_used,
        "final_code": session.final_code,
        "original_code": session.original_code,
        "final_error": session.final_error,
        "final_exception_type": session.final_exception_type,
        "history": session.history,
    }


def run_eval(
    *,
    model: str | None,
    max_attempts: int,
    timeout: float,
    limit: int | None,
    only: list[str] | None,
) -> dict[str, Any]:
    """Run evaluator synchronously and return JSON-serializable response."""
    problems = list(iter_problems(only=only))
    if limit:
        problems = problems[:limit]
    results = [
        evaluate_problem(
            p,
            max_attempts=max_attempts,
            timeout=timeout,
            model=model,
        )
        for p in problems
    ]
    summary = _summarize(results)
    payload_results = [dataclasses.asdict(r) for r in results]
    return {
        "model": model or DEFAULT_MODEL,
        "max_attempts": max_attempts,
        "summary": summary,
        "results": payload_results,
    }

