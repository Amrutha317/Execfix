"""Smoke tests for the Docker-hardened sandbox backend.

Skipped automatically unless both the Docker CLI/daemon and the
``debugger-sandbox:latest`` image are available, so they don't break CI or a
plain ``pip install`` dev setup that hasn't opted into the Docker backend.
Build the image with: docker build -t debugger-sandbox:latest -f Dockerfile.sandbox .
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from agent.executor_docker import DEFAULT_IMAGE, execute_code_docker


def _docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
        subprocess.run(
            ["docker", "image", "inspect", DEFAULT_IMAGE],
            capture_output=True,
            timeout=5,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _docker_ready(),
    reason="Docker daemon or debugger-sandbox:latest image not available",
)


def test_clean_program_succeeds() -> None:
    result = execute_code_docker("print('hello')")
    assert result.success is True
    assert "hello" in result.stdout


def test_runtime_error_captured() -> None:
    result = execute_code_docker("print(1/0)")
    assert result.success is False
    assert result.exception_type == "ZeroDivisionError"


def test_network_is_unreachable() -> None:
    # socket is already AST-blocked, so this exercises the pre-filter, not
    # the container's --network none -- both layers reject it here.
    result = execute_code_docker("import socket\ns = socket.socket()")
    assert result.was_rejected is True


def test_timeout_kills_container() -> None:
    result = execute_code_docker("while True:\n    pass", timeout=1.0)
    assert result.success is False
    assert result.exception_type == "TimeoutError"
