"""Shared helpers for tool execution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from cihub.utils.exec_utils import resolve_executable


def _run_command(
    cmd: list[str],
    workdir: Path,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    resolved = [resolve_executable(cmd[0]), *cmd[1:]]
    venv_root = os.environ.get("VIRTUAL_ENV")
    venv_bin = None
    if venv_root:
        venv_bin = Path(venv_root) / ("Scripts" if os.name == "nt" else "bin")
    elif sys.prefix != sys.base_prefix:
        venv_bin = Path(sys.executable).parent
    if venv_bin:
        candidate = venv_bin / cmd[0]
        if os.name == "nt" and not candidate.suffix:
            candidate = candidate.with_suffix(".exe")
        if candidate.exists():
            resolved[0] = str(candidate)
    return subprocess.run(  # noqa: S603
        resolved,
        cwd=workdir,
        env=env or os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _parse_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(data, (dict, list)):
        return data
    return None


def _find_files(workdir: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(workdir.rglob(pattern))
    unique = {path.resolve() for path in files}
    return sorted(unique, key=lambda path: str(path))
