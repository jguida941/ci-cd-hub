"""Run a single tool and emit JSON output."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from cihub.ci_config import load_ci_config
from cihub.ci_runner import (
    ToolResult,
    run_bandit,
    run_black,
    run_isort,
    run_mutmut,
    run_mypy,
    run_pip_audit,
    run_pytest,
    run_ruff,
    run_semgrep,
    run_trivy,
)
from cihub.config import tool_enabled as _tool_enabled_canonical
from cihub.tools.registry import get_tool_runner_args
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.paths import validate_subdir

RUNNERS: dict[str, Callable[..., ToolResult]] = {
    "pytest": run_pytest,
    "ruff": run_ruff,
    "black": run_black,
    "isort": run_isort,
    "mypy": run_mypy,
    "bandit": run_bandit,
    "pip_audit": run_pip_audit,
    "pip-audit": run_pip_audit,
    "mutmut": run_mutmut,
    "semgrep": run_semgrep,
    "trivy": run_trivy,
}


def _tool_enabled(config: dict[str, Any], tool: str) -> bool:
    """Check if a Python tool is enabled. Delegates to canonical cihub.config.tool_enabled."""
    return _tool_enabled_canonical(config, tool, "python")


def cmd_run(args: argparse.Namespace) -> CommandResult:
    """Run a single CI tool and emit JSON output.

    Always returns CommandResult for consistent output handling.
    """
    repo_path = Path(args.repo or ".").resolve()
    tool = args.tool
    tool_key = "pip_audit" if tool == "pip-audit" else tool
    output_dir = Path(args.output_dir or ".cihub")
    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)
    output_name = tool_key
    output_path = Path(args.output) if args.output else tool_output_dir / f"{output_name}.json"

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-001"}],
        )

    workdir = args.workdir or config.get("repo", {}).get("subdir") or "."
    validate_subdir(workdir)
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        message = f"Workdir not found: {workdir_path}"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-002"}],
        )

    runner = RUNNERS.get(tool)
    if runner is None:
        message = f"Unsupported tool: {tool}"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-003"}],
        )

    if not args.force and not _tool_enabled(config, tool_key):
        result = ToolResult(tool=tool_key, ran=False, success=False)
        result.write_json(output_path)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"{tool_key} skipped (disabled)",
            artifacts={"output": str(output_path)},
            data={"items": [f"{tool_key} skipped (disabled)"]},
        )

    try:
        if tool == "pytest":
            tool_args = get_tool_runner_args(config, "pytest", "python")
            fail_fast = bool(tool_args.get("fail_fast", False))
            pytest_args = tool_args.get("args") or []
            pytest_env = tool_args.get("env")
            if not isinstance(pytest_args, list):
                pytest_args = []
            if not isinstance(pytest_env, dict):
                pytest_env = None
            result = runner(workdir_path, output_dir, fail_fast, pytest_args, pytest_env)
        elif tool == "isort":
            use_black_profile = _tool_enabled(config, "black")
            result = runner(workdir_path, output_dir, use_black_profile)
        elif tool == "mutmut":
            timeout = config.get("python", {}).get("tools", {}).get("mutmut", {}).get("timeout_minutes", 15)
            result = runner(workdir_path, output_dir, int(timeout) * 60)
        else:
            result = runner(workdir_path, output_dir)
    except FileNotFoundError as exc:
        message = f"Tool '{tool}' not found: {exc}"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-004"}],
        )

    result.write_json(output_path)
    status = "passed" if result.success else "failed"
    return CommandResult(
        exit_code=EXIT_SUCCESS if result.success else EXIT_FAILURE,
        summary=f"{tool} {status}",
        artifacts={"output": str(output_path)},
        data={
            "items": [f"Wrote output: {output_path}"],
            "tool_result": result.to_payload(),
        },
    )
