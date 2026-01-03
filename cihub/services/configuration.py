"""Config service helpers for GUI/programmatic access."""

from __future__ import annotations

import io
from contextlib import redirect_stderr
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cihub.config.loader import ConfigValidationError, load_config
from cihub.services.types import ServiceResult


@dataclass
class ConfigLoadResult(ServiceResult):
    """Result of loading a repo config from the hub."""

    config: dict[str, Any] = field(default_factory=dict)


def load_repo_config(
    repo_name: str,
    hub_root: Path,
    repo_config_path: Path | None = None,
) -> ConfigLoadResult:
    """Load a repo config with validation and captured warnings."""
    stderr_capture = io.StringIO()
    warnings: list[str] = []

    try:
        with redirect_stderr(stderr_capture):
            cfg = load_config(
                repo_name=repo_name,
                hub_root=hub_root,
                repo_config_path=repo_config_path,
                exit_on_validation_error=False,
            )
    except ConfigValidationError as exc:
        errors = [f"{repo_name}: validation failed ({exc})"]
        stderr_output = stderr_capture.getvalue().strip()
        if stderr_output:
            errors.extend(f"{repo_name}: {line}" for line in stderr_output.splitlines())
        return ConfigLoadResult(success=False, errors=errors, warnings=warnings)
    except Exception as exc:
        errors = [f"{repo_name}: failed to load ({exc})"]
        stderr_output = stderr_capture.getvalue().strip()
        if stderr_output:
            errors.extend(f"{repo_name}: {line}" for line in stderr_output.splitlines())
        return ConfigLoadResult(success=False, errors=errors, warnings=warnings)

    stderr_output = stderr_capture.getvalue().strip()
    if stderr_output:
        warnings.extend(f"{repo_name}: {line}" for line in stderr_output.splitlines())

    return ConfigLoadResult(success=True, warnings=warnings, config=cfg)


def set_nested_value(config: dict[str, Any], path: str, value: Any) -> None:
    """Set a nested config value using dot-delimited path."""
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise ValueError("Empty path")
    cursor = config
    for key in parts[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[parts[-1]] = value


def resolve_tool_path(
    config: dict[str, Any],
    defaults: dict[str, Any],
    tool: str,
) -> str:
    """Resolve tool path for enable/disable operations."""
    language = None
    repo_block = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    if repo_block.get("language"):
        language = repo_block.get("language")
    elif config.get("language"):
        language = config.get("language")

    java_tools = defaults.get("java", {}).get("tools", {}) or {}
    python_tools = defaults.get("python", {}).get("tools", {}) or {}

    if language == "java":
        if tool not in java_tools:
            raise ValueError(f"Unknown tool: {tool}")
        return f"java.tools.{tool}.enabled"
    if language == "python":
        if tool not in python_tools:
            raise ValueError(f"Unknown tool: {tool}")
        return f"python.tools.{tool}.enabled"

    java_has = tool in java_tools
    python_has = tool in python_tools
    if java_has and not python_has:
        return f"java.tools.{tool}.enabled"
    if python_has and not java_has:
        return f"python.tools.{tool}.enabled"
    if java_has and python_has:
        raise ValueError("Tool exists in both java and python; set repo.language first")
    raise ValueError(f"Unknown tool: {tool}")


def set_tool_enabled(
    config: dict[str, Any],
    defaults: dict[str, Any],
    tool: str,
    enabled: bool,
) -> str:
    """Enable/disable a tool and return the resolved path."""
    tool_path = resolve_tool_path(config, defaults, tool)
    set_nested_value(config, tool_path, enabled)
    return tool_path
