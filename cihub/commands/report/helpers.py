"""Shared helper functions for report commands."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cihub.ci_report import RunContext
from cihub.config import tool_enabled as _tool_enabled_canonical
from cihub.utils import (
    _get_repo_name,
    get_git_branch,
)
from cihub.utils.env import _parse_env_bool, env_bool
from cihub.utils.github_context import GitHubContext


def _tool_enabled(config: dict[str, Any], tool: str, language: str, *, default: bool = False) -> bool:
    """Check if a tool is enabled. Delegates to canonical cihub.config.tool_enabled.

    Args:
        config: Full config dict
        tool: Tool name
        language: Language context
        default: Default value if not explicitly configured. For custom tools (x-*),
                 the schema specifies default=True, so callers should pass that.
    """
    return _tool_enabled_canonical(config, tool, language, default=default)


def _build_context(
    repo_path: Path,
    config: dict[str, Any],
    workdir: str,
    correlation_id: str | None,
    build_tool: str | None = None,
    project_type: str | None = None,
    docker_compose_file: str | None = None,
    docker_health_endpoint: str | None = None,
) -> RunContext:
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    ctx = GitHubContext.from_env()
    branch = ctx.ref_name or repo_info.get("default_branch")
    branch = branch or get_git_branch(repo_path) or ""
    return RunContext(
        repository=_get_repo_name(config, repo_path),
        branch=branch,
        run_id=ctx.run_id,
        run_number=ctx.run_number,
        commit=ctx.sha or "",
        correlation_id=correlation_id,
        workflow_ref=ctx.workflow_ref,
        workdir=workdir,
        build_tool=build_tool,
        retention_days=config.get("reports", {}).get("retention_days"),
        project_type=project_type,
        docker_compose_file=docker_compose_file,
        docker_health_endpoint=docker_health_endpoint,
    )


def _load_tool_outputs(tool_dir: Path) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    for path in tool_dir.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            tool = str(data.get("tool") or path.stem)
            outputs[tool] = data
        except json.JSONDecodeError:
            continue
    return outputs


def _resolve_write_summary(flag: bool | None) -> bool:
    if flag is not None:
        return flag
    return env_bool("CIHUB_WRITE_GITHUB_SUMMARY", default=True)


def _resolve_include_details(flag: bool | None) -> bool:
    if flag is not None:
        return flag
    return env_bool("CIHUB_REPORT_INCLUDE_DETAILS", default=False)


def _resolve_summary_path(path_value: str | None, write_summary: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if write_summary:
        env_path = os.environ.get("GITHUB_STEP_SUMMARY")
        return Path(env_path) if env_path else None
    return None


def _append_summary(text: str, summary_path: Path | None, emit_stdout: bool) -> str | None:
    if summary_path is None:
        return text if emit_stdout else None
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")
    return None


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    parsed = _parse_env_bool(str(value))
    if parsed is not None:
        return parsed
    return False
