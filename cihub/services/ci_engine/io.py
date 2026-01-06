"""Codecov upload and file collection helpers."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)


def _collect_codecov_files(
    language: str,
    output_dir: Path,
    tool_outputs: dict[str, dict[str, Any]],
) -> list[Path]:
    files: list[Path] = []
    if language == "python":
        coverage_path = tool_outputs.get("pytest", {}).get("artifacts", {}).get("coverage")
        if coverage_path:
            files.append(Path(coverage_path))
        else:
            files.append(output_dir / "coverage.xml")
    elif language == "java":
        jacoco_path = tool_outputs.get("jacoco", {}).get("artifacts", {}).get("report")
        if jacoco_path:
            files.append(Path(jacoco_path))
    return [path for path in files if path and path.exists()]


def _run_codecov_upload(
    files: list[Path],
    fail_ci_on_error: bool,
    problems: list[dict[str, Any]],
) -> None:
    if not files:
        problems.append(
            {
                "severity": "warning",
                "message": "Codecov enabled but no coverage files were found",
                "code": "CIHUB-CI-CODECOV-NO-FILES",
            }
        )
        return
    codecov_bin = shutil.which("codecov")
    if not codecov_bin:
        problems.append(
            {
                "severity": "error" if fail_ci_on_error else "warning",
                "message": "Codecov enabled but uploader not found in PATH",
                "code": "CIHUB-CI-CODECOV-MISSING",
            }
        )
        return
    cmd = [codecov_bin]
    for path in files:
        cmd.extend(["-f", str(path)])
    try:
        proc = safe_run(cmd, timeout=TIMEOUT_NETWORK)
    except CommandNotFoundError:
        problems.append(
            {
                "severity": "error" if fail_ci_on_error else "warning",
                "message": "Codecov uploader not found",
                "code": "CIHUB-CI-CODECOV-MISSING",
            }
        )
        return
    except CommandTimeoutError:
        problems.append(
            {
                "severity": "error" if fail_ci_on_error else "warning",
                "message": "Codecov upload timed out",
                "code": "CIHUB-CI-CODECOV-TIMEOUT",
            }
        )
        return
    if proc.returncode != 0:
        problems.append(
            {
                "severity": "error" if fail_ci_on_error else "warning",
                "message": f"Codecov upload failed: {proc.stderr.strip() or proc.stdout.strip()}",
                "code": "CIHUB-CI-CODECOV-FAILED",
            }
        )
