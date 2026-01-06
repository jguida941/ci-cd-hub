"""Shared helpers for tool execution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from cihub.utils.env import env_bool
from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    CommandNotFoundError,
    CommandTimeoutError,
    resolve_executable,
    safe_run,
)


def _run_command(
    cmd: list[str],
    workdir: Path,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
    stream_output: bool = False,
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
    if not stream_output:
        # Use safe_run for non-streaming mode
        try:
            return safe_run(
                resolved,
                cwd=workdir,
                env=env or os.environ.copy(),
                timeout=timeout or TIMEOUT_BUILD,
            )
        except CommandNotFoundError as exc:
            # Return a failed CompletedProcess for consistency
            return subprocess.CompletedProcess(
                args=resolved,
                returncode=127,
                stdout="",
                stderr=str(exc),
            )
        except CommandTimeoutError as exc:
            return subprocess.CompletedProcess(
                args=resolved,
                returncode=124,  # Standard timeout exit code
                stdout="",
                stderr=str(exc),
            )

    proc = subprocess.Popen(  # noqa: S603
        resolved,
        cwd=workdir,
        env=env or os.environ.copy(),
        text=True,
        encoding="utf-8",  # Consistent with safe_run() per ADR-0045
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _reader(pipe, chunks: list[str]) -> None:
        if pipe is None:
            return
        for line in iter(pipe.readline, ""):
            chunks.append(line)
            sys.stderr.write(line)
            sys.stderr.flush()
        pipe.close()

    stdout_thread = threading.Thread(target=_reader, args=(proc.stdout, stdout_chunks))
    stderr_thread = threading.Thread(target=_reader, args=(proc.stderr, stderr_chunks))
    stdout_thread.start()
    stderr_thread.start()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.wait()
        stdout_thread.join()
        stderr_thread.join()
        stdout_text = "".join(stdout_chunks)
        stderr_text = "".join(stderr_chunks)
        raise subprocess.TimeoutExpired(
            cmd=exc.cmd,
            timeout=exc.timeout,
            output=stdout_text,
            stderr=stderr_text,
        ) from exc
    stdout_thread.join()
    stderr_thread.join()
    return subprocess.CompletedProcess(
        args=resolved,
        returncode=proc.returncode,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
    )


def _append_text(path: Path, content: str) -> None:
    if not content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)


def _write_tool_logs(tool: str, output_dir: Path, stdout: str, stderr: str, cmd: list[str] | None = None) -> None:
    logs_dir = output_dir / "tool-outputs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_dir / f"{tool}.stdout.log"
    stderr_path = logs_dir / f"{tool}.stderr.log"
    header = f"$ {' '.join(cmd)}\n" if cmd else ""
    _append_text(stdout_path, header + (stdout or ""))
    _append_text(stderr_path, header + (stderr or ""))


def _run_tool_command(
    tool: str,
    cmd: list[str],
    workdir: Path,
    output_dir: Path,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    verbose = env_bool("CIHUB_VERBOSE", default=False)
    proc = _run_command(cmd, workdir, timeout=timeout, env=env, stream_output=verbose)
    _write_tool_logs(tool, output_dir, proc.stdout, proc.stderr, cmd=cmd)
    return proc


def _parse_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
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
