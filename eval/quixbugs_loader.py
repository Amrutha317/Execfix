"""Load buggy programs and JSON test cases from the QuixBugs benchmark.

QuixBugs ships:
- ``python_programs/<name>.py`` -- a buggy implementation of ``<name>``.
- ``correct_python_programs/<name>.py`` -- the reference (one-line-fix) solution.
- ``json_testcases/<name>.json`` -- one test case per line, each line is
  ``[input_args, expected_output]``.

We focus on the JSON-driven programs because they have a clean, programmatic
oracle. Graph/linked-list problems whose tests live only in
``python_testcases/`` (and require ``Node`` fixtures) are listed in
:data:`UNTESTED_PROGRAMS` so the README can document why they are excluded.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Iterator

QUIXBUGS_ROOT = Path(__file__).resolve().parent.parent / "data" / "QuixBugs"


# Programs whose tests don't have JSON oracles (they depend on Node fixtures
# defined in ``python_testcases/``). Excluded from the headline metric.
UNTESTED_PROGRAMS: frozenset[str] = frozenset(
    {
        "breadth_first_search",
        "depth_first_search",
        "detect_cycle",
        "minimum_spanning_tree",
        "reverse_linked_list",
        "shortest_path_length",
        "shortest_path_lengths",
        "shortest_paths",
        "topological_ordering",
    }
)


@dataclasses.dataclass(frozen=True)
class QuixBugsProblem:
    name: str
    buggy_code: str
    correct_code: str
    testcases: list[tuple[list, object]]
    """List of (input_args, expected_output) tuples."""

    @property
    def function_name(self) -> str:
        return self.name


def _load_json_testcases(path: Path) -> list[tuple[list, object]]:
    """QuixBugs json files are JSONL: one ``[input, expected]`` per line."""
    cases: list[tuple[list, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        record = json.loads(line)
        if not (isinstance(record, list) and len(record) == 2):
            raise ValueError(f"Malformed test case in {path}: {raw_line!r}")
        input_args, expected = record
        if not isinstance(input_args, list):
            input_args = [input_args]
        cases.append((input_args, expected))
    return cases


def iter_problems(
    *,
    root: Path | None = None,
    only: list[str] | None = None,
) -> Iterator[QuixBugsProblem]:
    """Yield every JSON-tested QuixBugs problem.

    Args:
        root: Override the QuixBugs checkout location (defaults to
            ``data/QuixBugs``).
        only: If given, restrict to this list of program names (in order).
    """
    base = root or QUIXBUGS_ROOT
    json_dir = base / "json_testcases"
    buggy_dir = base / "python_programs"
    correct_dir = base / "correct_python_programs"

    if not json_dir.exists():
        raise FileNotFoundError(
            f"QuixBugs not found at {base!s}. "
            "Run: git submodule update --init"
        )

    names: list[str]
    if only:
        names = list(only)
    else:
        names = sorted(p.stem for p in json_dir.glob("*.json"))

    for name in names:
        if name in UNTESTED_PROGRAMS:
            continue
        json_path = json_dir / f"{name}.json"
        buggy_path = buggy_dir / f"{name}.py"
        correct_path = correct_dir / f"{name}.py"
        if not (json_path.exists() and buggy_path.exists() and correct_path.exists()):
            continue
        yield QuixBugsProblem(
            name=name,
            buggy_code=buggy_path.read_text(encoding="utf-8"),
            correct_code=correct_path.read_text(encoding="utf-8"),
            testcases=_load_json_testcases(json_path),
        )


def list_problem_names(*, root: Path | None = None) -> list[str]:
    """Returns the names of all JSON-tested QuixBugs problems."""
    return [p.name for p in iter_problems(root=root)]
