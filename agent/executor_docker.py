"""Docker-hardened sandbox backend.

Same AST pre-filter as ``agent/executor.py``, but the candidate program runs
inside a throwaway container instead of a bare subprocess:

- ``--network none``       -- no network namespace at all.
- ``--read-only`` rootfs   -- only a tmpfs ``/tmp`` is writable.
- ``--cap-drop ALL``       -- no Linux capabilities.
- ``--security-opt no-new-privileges``
- ``--pids-limit`` / ``--memory`` / ``--cpus`` -- hard resource ceiling.
- ``--user 65534:65534``   -- runs as an unprivileged, non-root UID.

Selected via ``SANDBOX_BACKEND=docker`` (see ``agent/executor.py::run_sandboxed``).
Requires a Docker daemon reachable from this machine and the sandbox image
built once via:

    docker build -t debugger-sandbox:latest -f Dockerfile.sandbox .

This is still not adversarial-grade isolation (shared kernel) -- see the
README's Sandbox section for where this sits relative to microVM approaches
like Firecracker/gVisor.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Iterable

from agent.executor import (
    BLOCKED_IMPORTS,
    DEFAULT_TIMEOUT_SECONDS,
    ExecutionResult,
    _extract_exception_type,
    _scan,
)

DEFAULT_IMAGE = "debugger-sandbox:latest"

# Extra wall-clock slack for container create/teardown on top of the
# candidate program's own timeout.
DOCKER_STARTUP_BUFFER_SECONDS = 10.0


def execute_code_docker(
    code: str,
    *,
    tests: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    extra_blocked: Iterable[str] | None = None,
    image: str = DEFAULT_IMAGE,
) -> ExecutionResult:
    """Docker-backed equivalent of :func:`agent.executor.execute_code`."""
    started = time.perf_counter()

    blocked = BLOCKED_IMPORTS | set(extra_blocked) if extra_blocked else BLOCKED_IMPORTS
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

    container_name = f"debugger_sbx_{uuid.uuid4().hex[:12]}"
    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,size=16m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "64",
        "--memory", "256m",
        "--cpus", "0.5",
        "--user", "65534:65534",
        "-v", f"{sandbox_dir}:/sandbox:ro",
        "-w", "/sandbox",
        image,
        "python", "-I", "-S", "candidate.py",
    ]

    try:
        completed = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout + DOCKER_STARTUP_BUFFER_SECONDS,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        success = completed.returncode == 0
        exc_type = None if success else _extract_exception_type(stderr)
    except subprocess.TimeoutExpired as exc:
        # Killing the `docker run` client doesn't reliably stop the
        # container itself -- kill it explicitly by name (best-effort).
        subprocess.run(
            ["docker", "kill", container_name],
            capture_output=True,
            check=False,
        )
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (
            (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        ) + f"\nTimeoutError: execution exceeded {timeout:.1f}s wall clock"
        success = False
        exc_type = "TimeoutError"
    except FileNotFoundError as exc:
        raise RuntimeError(
            "SANDBOX_BACKEND=docker requires the `docker` CLI on PATH "
            "(Docker Desktop must be installed and running)."
        ) from exc
    finally:
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
