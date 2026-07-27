"""Run the debugging agent over the QuixBugs benchmark and report a pass-rate.

Usage:
    python -m eval.evaluator                    # full run, gpt-5-mini, 3 attempts
    python -m eval.evaluator --model gpt-5-mini --limit 5
    python -m eval.evaluator --only gcd bucketsort

Outputs:
    eval/results/run_<timestamp>.json   per-program details
    eval/results/run_<timestamp>.md     headline pass-rate + table
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.debugger import run_debug_session
from agent.llm import DEFAULT_MODEL
from agent.executor import execute_code
from eval.quixbugs_loader import (
    QuixBugsProblem,
    iter_problems,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"


# --------------------------------------------------------------------------- #
# Test harness construction                                                   #
# --------------------------------------------------------------------------- #


_HARNESS_TEMPLATE = """\
# --- QuixBugs JSON test harness ---
import json as _json
import math as _math
import types as _t
_TESTCASES = _json.loads({testcases_json!r})

def _normalize(x):
    # Generators and tuples need to be unwrapped/coerced before comparison
    # against JSON-loaded expected values (which are always lists of scalars).
    if isinstance(x, _t.GeneratorType):
        return [_normalize(v) for v in x]
    if isinstance(x, tuple):
        return [_normalize(v) for v in x]
    if isinstance(x, list):
        return [_normalize(v) for v in x]
    return x

def _equal(actual, expected):
    if isinstance(actual, float) or isinstance(expected, float):
        # QuixBugs json values for iterative numerics (e.g. sqrt) were generated
        # with a slightly different float-op order than the reference; allow
        # 0.1% relative error so both the reference and a genuine fix pass.
        try:
            return _math.isclose(float(actual), float(expected), rel_tol=1e-3, abs_tol=1e-6)
        except (TypeError, ValueError):
            return False
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return False
        return all(_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected

_FN = {func_name}
_FAILURES = []
for _i, _case in enumerate(_TESTCASES):
    _inp, _expected = _case
    try:
        _actual = _FN(*_inp)
    except Exception as _e:
        _FAILURES.append((_i, _inp, _expected, f"raised {{type(_e).__name__}}: {{_e}}"))
        continue
    _actual = _normalize(_actual)
    if not _equal(_actual, _expected):
        _FAILURES.append((_i, _inp, _expected, _actual))

if _FAILURES:
    print("QUIXBUGS_FAIL")
    for _i, _inp, _expected, _got in _FAILURES[:3]:
        print(f"case {{_i}}: input={{_inp!r}} expected={{_expected!r}} got={{_got!r}}")
    raise AssertionError(
        f"{{len(_FAILURES)}}/{{len(_TESTCASES)}} test cases failed"
    )
else:
    print(f"QUIXBUGS_PASS {{len(_TESTCASES)}}")
"""


def build_harness(problem: QuixBugsProblem) -> str:
    """Build the test harness that will be appended to the candidate code."""
    return _HARNESS_TEMPLATE.format(
        testcases_json=json.dumps(problem.testcases),
        func_name=problem.function_name,
    )


# --------------------------------------------------------------------------- #
# Per-problem runner                                                          #
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class ProblemResult:
    name: str
    passed: bool
    attempts_used: int
    fixed_on_first_run: bool
    final_exception_type: str | None
    duration_ms: int
    final_code: str
    error_excerpt: str
    skipped_reason: str | None = None

    @property
    def repairs_used(self) -> int:
        """LLM fix calls made (the first run just surfaces the error, no API call)."""
        return max(0, self.attempts_used - 1)


def _short_error(text: str, limit: int = 240) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def evaluate_problem(
    problem: QuixBugsProblem,
    *,
    max_attempts: int,
    timeout: float,
    model: str | None,
) -> ProblemResult:
    started = time.perf_counter()
    harness = build_harness(problem)

    # Quick sanity check -- does the harness pass on the *correct* solution?
    # If not, our harness is buggy; skip the problem so we don't blame the agent.
    sanity = execute_code(problem.correct_code, tests=harness, timeout=timeout)
    if not sanity.success:
        return ProblemResult(
            name=problem.name,
            passed=False,
            attempts_used=0,
            fixed_on_first_run=False,
            final_exception_type=sanity.exception_type,
            duration_ms=int((time.perf_counter() - started) * 1000),
            final_code="",
            error_excerpt=_short_error(sanity.stderr),
            skipped_reason="harness_fails_on_reference",
        )

    session = run_debug_session(
        problem.buggy_code,
        tests=harness,
        max_attempts=max_attempts,
        timeout=timeout,
        model=model,
    )

    fixed_first = bool(session.history and session.history[0].get("success"))
    return ProblemResult(
        name=problem.name,
        passed=session.success,
        attempts_used=session.attempts_used,
        fixed_on_first_run=fixed_first,
        final_exception_type=session.final_exception_type,
        duration_ms=int((time.perf_counter() - started) * 1000),
        final_code=session.final_code,
        error_excerpt=_short_error(session.final_error),
    )


# --------------------------------------------------------------------------- #
# Reporting                                                                   #
# --------------------------------------------------------------------------- #


def _summarize(results: list[ProblemResult]) -> dict[str, Any]:
    evaluated = [r for r in results if r.skipped_reason is None]
    passed = [r for r in evaluated if r.passed]
    pass_rate = len(passed) / len(evaluated) if evaluated else 0.0
    avg_repairs = (
        sum(r.repairs_used for r in passed) / len(passed) if passed else 0.0
    )
    return {
        "total": len(results),
        "evaluated": len(evaluated),
        "skipped": len(results) - len(evaluated),
        "passed": len(passed),
        "pass_rate": pass_rate,
        "avg_repairs_when_passed": avg_repairs,
    }


def write_reports(
    results: list[ProblemResult],
    summary: dict[str, Any],
    *,
    model: str,
    max_attempts: int,
    out_dir: Path,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = out_dir / f"run_{timestamp}.json"
    md_path = out_dir / f"run_{timestamp}.md"

    json_payload = {
        "model": model,
        "max_attempts": max_attempts,
        "summary": summary,
        "results": [
            {**dataclasses.asdict(r), "repairs_used": r.repairs_used} for r in results
        ],
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append(f"# QuixBugs eval: {timestamp}")
    lines.append("")
    lines.append(f"- Model: `{model}`")
    lines.append(f"- Max attempts: {max_attempts}")
    lines.append(
        f"- **Pass rate: {summary['passed']}/{summary['evaluated']} "
        f"({summary['pass_rate'] * 100:.1f}%)**"
    )
    if summary["skipped"]:
        lines.append(f"- Skipped (harness sanity failed): {summary['skipped']}")
    lines.append(
        f"- Avg repairs when passed: {summary['avg_repairs_when_passed']:.2f}"
    )
    lines.append(
        "- \"Repairs\" = LLM fix calls; the first run just surfaces the error and isn't a repair."
    )
    lines.append("")
    lines.append("| Program | Result | Repairs | Final exception |")
    lines.append("|---|---|---|---|")
    for r in results:
        if r.skipped_reason:
            verdict = f"SKIP ({r.skipped_reason})"
        elif r.passed:
            verdict = "PASS"
        else:
            verdict = "FAIL"
        exc = r.final_exception_type or "-"
        lines.append(f"| {r.name} | {verdict} | {r.repairs_used} | {exc} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return json_path, md_path


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the agent on QuixBugs.")
    parser.add_argument("--model", default=None, help="OpenAI model (default: env DEBUGGER_MODEL or gpt-5-mini).")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-execution wall-clock timeout in seconds (default: 30).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N problems.")
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Run only these program names (e.g., --only gcd bucketsort).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Where to write run_<timestamp>.{json,md}.",
    )
    args = parser.parse_args()

    problems = list(iter_problems(only=args.only))
    if args.limit:
        problems = problems[: args.limit]

    if not problems:
        print("error: no problems to evaluate. Did you `git submodule update --init`?", file=sys.stderr)
        return 2

    print(f"Evaluating {len(problems)} QuixBugs problems...")
    results: list[ProblemResult] = []
    for i, problem in enumerate(problems, start=1):
        print(f"[{i}/{len(problems)}] {problem.name}... ", end="", flush=True)
        result = evaluate_problem(
            problem,
            max_attempts=args.max_attempts,
            timeout=args.timeout,
            model=args.model,
        )
        results.append(result)
        if result.skipped_reason:
            print(f"SKIP ({result.skipped_reason})")
        elif result.passed:
            print(f"PASS in {result.repairs_used} repair(s)")
        else:
            print(f"FAIL ({result.final_exception_type or 'wrong output'})")

    summary = _summarize(results)
    model = args.model or DEFAULT_MODEL
    json_path, md_path = write_reports(
        results,
        summary,
        model=model,
        max_attempts=args.max_attempts,
        out_dir=args.out_dir,
    )

    print()
    print(f"Pass rate: {summary['passed']}/{summary['evaluated']} ({summary['pass_rate'] * 100:.1f}%)")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
