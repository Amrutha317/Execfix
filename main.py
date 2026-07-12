"""CLI entry point: ``python main.py path/to/buggy.py``.

Reads a Python source file (or stdin via ``-``), runs it through the debugging
agent, and prints the fixed source + a small summary.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent.debugger import run_debug_session


def _read_source(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read()
    path = Path(arg)
    if not path.exists():
        raise SystemExit(f"error: file not found: {path}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the autonomous Python debugging agent on a source file.",
    )
    parser.add_argument("source", help="Path to the buggy .py file, or '-' for stdin.")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum debug iterations before giving up (default: 3).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-execution wall-clock timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the OpenAI model (default: env DEBUGGER_MODEL or gpt-5-mini).",
    )
    parser.add_argument(
        "--no-loop",
        action="store_true",
        help="Use the plain while-loop debugger instead of the LangGraph agent.",
    )
    args = parser.parse_args()

    code = _read_source(args.source)

    if args.no_loop:
        # Lazy import to keep startup snappy when we use the LangGraph path.
        from agent.debugger import debug_loop

        state = debug_loop(
            code,
            max_attempts=args.max_attempts,
            timeout=args.timeout,
            model=args.model,
            verbose=True,
        )
        success = state.get("success", False)
        attempts = state.get("attempts", 0)
        final_code = state.get("code", code)
        final_error = state.get("error", "")
    else:
        session = run_debug_session(
            code,
            max_attempts=args.max_attempts,
            timeout=args.timeout,
            model=args.model,
        )
        success = session.success
        attempts = session.attempts_used
        final_code = session.final_code
        final_error = session.final_error

    if success:
        print(f"# Fixed in {attempts} attempt(s).", file=sys.stderr)
        print(final_code)
        return 0

    print(f"# Gave up after {attempts} attempt(s).", file=sys.stderr)
    if final_error:
        print(f"# Last error:\n# {final_error.strip().splitlines()[-1] if final_error.strip() else ''}", file=sys.stderr)
    print(final_code)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
