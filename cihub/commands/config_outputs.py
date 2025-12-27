"""Emit GitHub Actions outputs from .ci-hub.yml."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config
from cihub.cli import CommandResult
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def _get_str(data: dict[str, Any], path: list[str], default: str) -> str:
    cursor: Any = data
    for key in path:
        if not isinstance(cursor, dict):
            return default
        cursor = cursor.get(key)
    if cursor is None:
        return default
    return str(cursor)


def _get_int(data: dict[str, Any], path: list[str], default: int) -> int:
    value = _get_str(data, path, str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def cmd_config_outputs(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo)
    json_mode = getattr(args, "json", False)

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        print(message, file=sys.stderr)
        return EXIT_FAILURE

    language = (
        config.get("language")
        or _get_str(config, ["repo", "language"], "python")
        or "python"
    )

    workdir = args.workdir or _get_str(config, ["workdir"], "")
    if not workdir:
        workdir = _get_str(config, ["repo", "subdir"], ".")
    if not workdir:
        workdir = "."

    outputs: dict[str, str] = {
        "language": str(language),
        "python_version": _get_str(config, ["python", "version"], "3.12"),
        "java_version": _get_str(config, ["java", "version"], "21"),
        "build_tool": _get_str(config, ["java", "build_tool"], "maven"),
        "workdir": workdir,
        "retention_days": str(_get_int(config, ["reports", "retention_days"], 30)),
    }

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Config outputs generated",
            data={"outputs": outputs},
        )

    output_path = os.environ.get("GITHUB_OUTPUT") if args.github_output else None
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            for key, value in outputs.items():
                handle.write(f"{key}={value}\n")
        return EXIT_SUCCESS

    for key, value in outputs.items():
        print(f"{key}={value}")
    return EXIT_SUCCESS
