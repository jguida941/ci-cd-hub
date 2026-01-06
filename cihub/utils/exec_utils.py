"""Executable resolution and subprocess utilities.

This module provides safe, consistent subprocess execution with:
- Standardized timeouts (per ADR-0045)
- Consistent error handling for FileNotFoundError and TimeoutExpired
- UTF-8 encoding by default
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Sequence

# Timeout constants (seconds) - per ADR-0045
TIMEOUT_QUICK = 30  # Simple commands (git status, version checks)
TIMEOUT_NETWORK = 120  # Network operations (git clone, gh api)
TIMEOUT_BUILD = 600  # Build/test commands (pytest, mvn)
TIMEOUT_EXTENDED = 900  # Long-running operations (full CI pipeline)


class SubprocessError(RuntimeError):
    """Base error for subprocess execution failures."""

    pass


class CommandNotFoundError(SubprocessError):
    """Raised when the command executable is not found."""

    def __init__(self, cmd: str) -> None:
        self.cmd = cmd
        super().__init__(f"Command not found: {cmd}")


class CommandTimeoutError(SubprocessError):
    """Raised when command execution times out."""

    def __init__(self, cmd: str, timeout: int) -> None:
        self.cmd = cmd
        self.timeout = timeout
        super().__init__(f"Command timed out after {timeout}s: {cmd}")


def resolve_executable(name: str) -> str:
    """Resolve an executable name to its full path.

    Args:
        name: The executable name to resolve.

    Returns:
        The full path if found, otherwise the original name.
    """
    return shutil.which(name) or name


def safe_run(
    cmd: Sequence[str],
    *,
    cwd: Path | str | None = None,
    timeout: int = TIMEOUT_QUICK,
    check: bool = False,
    capture_output: bool = True,
    text: bool = True,
    env: dict[str, str] | None = None,
    input: str | None = None,  # noqa: A002 - shadowing builtin is intentional for subprocess compat
) -> subprocess.CompletedProcess[str]:
    """Run subprocess with consistent error handling and timeout.

    This is the canonical way to run subprocesses in cihub. It provides:
    - Standardized timeout handling with meaningful errors
    - FileNotFoundError converted to CommandNotFoundError
    - UTF-8 encoding by default
    - Consistent capture_output/text defaults

    Args:
        cmd: Command and arguments as sequence (e.g., ["git", "status"])
        cwd: Working directory for the command
        timeout: Timeout in seconds (default: TIMEOUT_QUICK=30)
        check: If True, raise CalledProcessError on non-zero exit
        capture_output: Capture stdout/stderr (default: True)
        text: Return strings instead of bytes (default: True)
        env: Environment variables override
        input: String to send to stdin (mutually exclusive with capture_output=False)

    Returns:
        CompletedProcess with stdout/stderr captured

    Raises:
        CommandNotFoundError: If the command executable is not found
        CommandTimeoutError: If command exceeds timeout
        subprocess.CalledProcessError: If check=True and command fails

    Example:
        >>> result = safe_run(["git", "status"], timeout=TIMEOUT_QUICK)
        >>> if result.returncode == 0:
        ...     print(result.stdout)
    """
    cmd_str = " ".join(str(c) for c in cmd)

    try:
        return subprocess.run(  # noqa: S603
            list(cmd),
            cwd=cwd,
            timeout=timeout,
            check=check,
            capture_output=capture_output,
            text=text,
            encoding="utf-8" if text else None,
            env=env,
            input=input,
        )
    except FileNotFoundError:
        raise CommandNotFoundError(str(cmd[0])) from None
    except subprocess.TimeoutExpired:
        raise CommandTimeoutError(cmd_str, timeout) from None
