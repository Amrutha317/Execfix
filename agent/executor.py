"""Hardened subprocess sandbox for executing untrusted Python code.

Executes a candidate program in an isolated temp directory with:
- A pre-execution AST scan that rejects imports/calls in a blocklist.
- ``python -I -S`` (isolated mode, no site.py, no PYTHONPATH).
- Wall-clock timeout enforced by ``subprocess.run(timeout=...)``.
- ``cwd`` set to the temp directory so relative paths cannot reach the project tree.

This is best-effort sandboxing for an LLM coding loop, NOT adversarial-grade
isolation. For untrusted user input in production, wrap this in Docker or
gVisor instead.
"""

from __future__ import annotations

import ast
import dataclasses
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterable

# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #

# Top-level module names (or dotted prefixes) the candidate program is not
# allowed to import. Anything under these names is rejected before execution.
BLOCKED_IMPORTS: frozenset[str] = frozenset(
    {
        "subprocess",
        "shutil",
        "socket",
        "ssl",
        "requests",
        "urllib",
        "urllib2",
        "urllib3",
        "httplib",
        "http",
        "ftplib",
        "telnetlib",
        "smtplib",
        "ctypes",
        "multiprocessing",
        "threading",
        "asyncio",
        "pty",
        "pwd",
        "grp",
        "resource",
        "signal",
        "winreg",
        "msvcrt",
    }
)

# Attribute accesses on the ``os`` module that are always rejected.
BLOCKED_OS_ATTRS: frozenset[str] = frozenset(
    {
        "system",
        "popen",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "exec",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "fork",
        "forkpty",
        "kill",
        "killpg",
        "remove",
        "removedirs",
        "rmdir",
        "unlink",
        "rename",
        "replace",
        "chmod",
        "chown",
    }
)

DEFAULT_TIMEOUT_SECONDS: float = 10.0


# --------------------------------------------------------------------------- #
# Result type                                                                 #
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class ExecutionResult:
    """Outcome of a single sandboxed run."""

    success: bool
    stdout: str
    stderr: str
    exception_type: str | None
    duration_ms: int
    rejected_reason: str | None = None

    @property
    def was_rejected(self) -> bool:
        return self.rejected_reason is not None


# --------------------------------------------------------------------------- #
# Pre-execution AST scan                                                      #
# --------------------------------------------------------------------------- #


class _BlocklistVisitor(ast.NodeVisitor):
    """Walks an AST and records the first violation it sees."""

    def __init__(self) -> None:
        self.violation: str | None = None

    def _flag(self, reason: str) -> None:
        if self.violation is None:
            self.violation = reason

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top = alias.name.split(".", 1)[0]
            if top in BLOCKED_IMPORTS:
                self._flag(f"import of blocked module '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            top = node.module.split(".", 1)[0]
            if top in BLOCKED_IMPORTS:
                self._flag(f"from-import of blocked module '{node.module}'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Catch obvious patterns like ``os.system(...)`` even if ``os`` itself is allowed.
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == "os"
            and node.attr in BLOCKED_OS_ATTRS
        ):
            self._flag(f"call to blocked os.{node.attr}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Reject ``__import__('subprocess')`` style backdoors.
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            if node.args and isinstance(node.args[0], ast.Constant):
                target = str(node.args[0].value).split(".", 1)[0]
                if target in BLOCKED_IMPORTS:
                    self._flag(f"__import__ of blocked module '{target}'")
        # Reject ``eval`` / ``exec`` of arbitrary strings as a backdoor for
        # bypassing the AST scan itself.
        if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            self._flag(f"use of {node.func.id}() is not permitted in the sandbox")
        self.generic_visit(node)


def scan_for_violations(code: str) -> tuple[str | None, str | None]:
    """Return ``(violation_reason, syntax_error)``.

    - ``violation_reason`` is non-None if the AST contains a blocked construct.
    - ``syntax_error`` is non-None if the code can't be parsed at all; in that
      case we let the subprocess run anyway so the LLM gets the real Python
      ``SyntaxError`` traceback (which is what we want to fix).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return None, f"{type(exc).__name__}: {exc.msg} (line {exc.lineno})"
    visitor = _BlocklistVisitor()
    visitor.visit(tree)
    return visitor.violation, None


# --------------------------------------------------------------------------- #
# Exception-type extraction                                                   #
# --------------------------------------------------------------------------- #


def _extract_exception_type(stderr: str) -> str | None:
    """Pull the final exception class name out of a Python traceback."""
    if not stderr:
        return None
    for line in reversed(stderr.strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        # A traceback's last line looks like ``ZeroDivisionError: division by zero``.
        head = line.split(":", 1)[0]
        if head.isidentifier() and (head.endswith("Error") or head.endswith("Exception") or head == "SystemExit"):
            return head
    return None


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #


def execute_code(
    code: str,
    *,
    tests: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    extra_blocked: Iterable[str] | None = None,
) -> ExecutionResult:
    """Run ``code`` (optionally appended with ``tests``) in a sandboxed subprocess.

    Args:
        code: The candidate Python source.
        tests: Optional additional source appended after ``code``. Used by the
            QuixBugs evaluator to call the candidate function on each test
            case and assert the expected output.
        timeout: Wall-clock seconds before the child is killed.
        extra_blocked: Additional top-level module names to add to the blocklist
            for this single run.

    Returns:
        :class:`ExecutionResult`.
    """
    started = time.perf_counter()

    if extra_blocked:
        blocked = BLOCKED_IMPORTS | set(extra_blocked)
    else:
        blocked = BLOCKED_IMPORTS

    full_source = code if tests is None else f"{code}\n\n# --- injected test harness ---\n{tests}\n"

    violation, _syntax_err = _scan(full_source, blocked)
    if violation:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"SandboxRejection: {violation}",
            exception_type="SandboxRejection",
            duration_ms=int((time.perf_counter() - started) * 1000),
            rejected_reason=violation,
        )

    sandbox_dir = Path(tempfile.mkdtemp(prefix="debugger_sbx_"))
    script_path = sandbox_dir / "candidate.py"
    script_path.write_text(full_source, encoding="utf-8")

    # Minimal, clean environment. ``-I`` already disables PYTHONPATH/user-site,
    # but stripping the env is belt-and-suspenders.
    env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # required on Windows
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(sandbox_dir),
            env=env,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        success = completed.returncode == 0
        exc_type = None if success else _extract_exception_type(stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (
            (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        ) + f"\nTimeoutError: execution exceeded {timeout:.1f}s wall clock"
        success = False
        exc_type = "TimeoutError"
    finally:
        # Best-effort cleanup; the sandbox dir is small and harmless if it lingers.
        try:
            for child in sandbox_dir.iterdir():
                child.unlink(missing_ok=True)
            sandbox_dir.rmdir()
        except OSError:
            pass

    return ExecutionResult(
        success=success,
        stdout=stdout,
        stderr=stderr,
        exception_type=exc_type,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


# --------------------------------------------------------------------------- #
# Internals exposed for tests                                                 #
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# Backend dispatch                                                            #
# --------------------------------------------------------------------------- #


def _resolve_backend() -> str:
    return os.environ.get("SANDBOX_BACKEND", "subprocess").strip().lower()


def run_sandboxed(
    code: str,
    *,
    tests: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    extra_blocked: Iterable[str] | None = None,
) -> ExecutionResult:
    """Run ``code`` through the sandbox backend selected by ``SANDBOX_BACKEND``.

    ``subprocess`` (default) uses :func:`execute_code` directly. ``docker``
    additionally isolates the run in a hardened, network-less container --
    see ``agent/executor_docker.py`` and the README's Sandbox section for
    what that buys you over the bare subprocess backend.
    """
    if _resolve_backend() == "docker":
        from agent.executor_docker import execute_code_docker

        return execute_code_docker(code, tests=tests, timeout=timeout, extra_blocked=extra_blocked)
    return execute_code(code, tests=tests, timeout=timeout, extra_blocked=extra_blocked)


def _scan(code: str, blocked: Iterable[str]) -> tuple[str | None, str | None]:
    """Variant of :func:`scan_for_violations` parameterized by blocklist."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return None, f"{type(exc).__name__}: {exc.msg} (line {exc.lineno})"
    visitor = _BlocklistVisitor()
    # Patch the module-level constant for this visit only.
    blocked_set = set(blocked)
    original = BLOCKED_IMPORTS
    try:
        globals()["BLOCKED_IMPORTS"] = frozenset(blocked_set)
        visitor.visit(tree)
    finally:
        globals()["BLOCKED_IMPORTS"] = original
    return visitor.violation, None
