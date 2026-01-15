"""Configuration and utility helpers for the CI engine."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Mapping

from cihub.config import tool_enabled as _tool_enabled_canonical
from cihub.core.languages import get_strategy
from cihub.tools.registry import (
    JAVA_TOOLS,
    PYTHON_TOOLS,
    RESERVED_FEATURES,
    get_custom_tools_from_config,
)
from cihub.utils import (
    resolve_executable,
    validate_subdir,
)
from cihub.utils.env import _parse_env_bool as _parse_env_bool_base
from cihub.utils.exec_utils import (
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)


def _get_git_commit(repo_path: Path) -> str:
    try:
        git_bin = resolve_executable("git")
        result = safe_run(
            [git_bin, "-C", str(repo_path), "rev-parse", "HEAD"],
            timeout=TIMEOUT_QUICK,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, CommandNotFoundError, CommandTimeoutError):
        return ""


def _resolve_workdir(
    repo_path: Path,
    config: dict[str, Any],
    override: str | None,
) -> str:
    if override:
        validate_subdir(override)
        return override
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    subdir = repo_info.get("subdir")
    if isinstance(subdir, str) and subdir:
        validate_subdir(subdir)
        return subdir
    return "."


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


def _tool_gate_enabled(config: dict[str, Any], tool: str, language: str) -> bool:
    """Check if a tool's gate should fail the build.

    Delegates to centralized tool adapter registry (Part 5.3).
    """
    from cihub.tools.registry import is_tool_gate_enabled

    return is_tool_gate_enabled(config, tool, language)


def _parse_env_bool(value: str | None) -> bool | None:
    return _parse_env_bool_base(value)


def _get_env_name(config: dict[str, Any], key: str, default: str) -> str:
    value = config.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _get_env_value(
    env: Mapping[str, str],
    name: str | None,
    fallbacks: list[str] | None = None,
) -> str | None:
    if name:
        value = env.get(name)
        if value:
            return value
    if fallbacks:
        for fallback in fallbacks:
            value = env.get(fallback)
            if value:
                return value
    return None


def _warn_reserved_features(config: dict[str, Any], problems: list[dict[str, Any]]) -> None:
    for key, label in RESERVED_FEATURES:
        entry = config.get(key, {})
        enabled = False
        if isinstance(entry, dict):
            enabled = bool(entry.get("enabled", False))
        elif isinstance(entry, bool):
            enabled = entry
        if enabled:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"{label} is enabled but not implemented yet (toggle reserved).",
                    "code": "CIHUB-CI-RESERVED-FEATURE",
                }
            )


def _set_tool_enabled(
    config: dict[str, Any],
    language: str,
    tool: str,
    enabled: bool,
) -> None:
    lang_cfg = config.setdefault(language, {})
    tools = lang_cfg.setdefault("tools", {})
    entry = tools.get(tool)
    if isinstance(entry, dict):
        entry["enabled"] = enabled
    else:
        tools[tool] = {"enabled": enabled}


def _apply_env_overrides(
    config: dict[str, Any],
    language: str,
    env: dict[str, str],
    problems: list[dict[str, Any]],
) -> None:
    tool_env = {
        "python": {
            "pytest": "CIHUB_RUN_PYTEST",
            "ruff": "CIHUB_RUN_RUFF",
            "bandit": "CIHUB_RUN_BANDIT",
            "pip_audit": "CIHUB_RUN_PIP_AUDIT",
            "mypy": "CIHUB_RUN_MYPY",
            "black": "CIHUB_RUN_BLACK",
            "isort": "CIHUB_RUN_ISORT",
            "mutmut": "CIHUB_RUN_MUTMUT",
            "hypothesis": "CIHUB_RUN_HYPOTHESIS",
            "sbom": "CIHUB_RUN_SBOM",
            "semgrep": "CIHUB_RUN_SEMGREP",
            "trivy": "CIHUB_RUN_TRIVY",
            "codeql": "CIHUB_RUN_CODEQL",
            "docker": "CIHUB_RUN_DOCKER",
        },
        "java": {
            "jacoco": "CIHUB_RUN_JACOCO",
            "checkstyle": "CIHUB_RUN_CHECKSTYLE",
            "spotbugs": "CIHUB_RUN_SPOTBUGS",
            "owasp": "CIHUB_RUN_OWASP",
            "pitest": "CIHUB_RUN_PITEST",
            "jqwik": "CIHUB_RUN_JQWIK",
            "pmd": "CIHUB_RUN_PMD",
            "semgrep": "CIHUB_RUN_SEMGREP",
            "trivy": "CIHUB_RUN_TRIVY",
            "codeql": "CIHUB_RUN_CODEQL",
            "sbom": "CIHUB_RUN_SBOM",
            "docker": "CIHUB_RUN_DOCKER",
        },
    }
    overrides = tool_env.get(language, {})
    for tool, var in overrides.items():
        raw = env.get(var)
        if raw is None:
            continue
        parsed = _parse_env_bool(raw)
        if parsed is None:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Invalid boolean for {var}: {raw!r}",
                    "code": "CIHUB-CI-ENV-BOOL",
                }
            )
            continue
        _set_tool_enabled(config, language, tool, parsed)

    # Also apply env overrides for custom tools (x-* prefix)
    # Pattern: x-my-tool -> CIHUB_RUN_X_MY_TOOL
    custom_tools = get_custom_tools_from_config(config, language)
    for tool in custom_tools:
        # Convert x-my-tool to X_MY_TOOL
        env_suffix = tool.upper().replace("-", "_")
        var = f"CIHUB_RUN_{env_suffix}"
        raw = env.get(var)
        if raw is None:
            continue
        parsed = _parse_env_bool(raw)
        if parsed is None:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Invalid boolean for {var}: {raw!r}",
                    "code": "CIHUB-CI-ENV-BOOL",
                }
            )
            continue
        _set_tool_enabled(config, language, tool, parsed)

    summary_override = _parse_env_bool(env.get("CIHUB_WRITE_GITHUB_SUMMARY"))
    if summary_override is not None:
        reports = config.setdefault("reports", {})
        github_summary = reports.setdefault("github_summary", {})
        github_summary["enabled"] = summary_override


def _apply_force_all_tools(config: dict[str, Any], language: str) -> None:
    repo_cfg = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    if not repo_cfg.get("force_all_tools", False):
        return
    # Use strategy pattern to get language-specific tool list
    try:
        strategy = get_strategy(language)
        tool_list = strategy.get_default_tools()
    except ValueError:
        # Fall back to registry for unsupported languages
        tool_list = PYTHON_TOOLS if language == "python" else JAVA_TOOLS
    for tool in tool_list:
        _set_tool_enabled(config, language, tool, True)


def _split_problems(problems: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    errors = [p.get("message", "") for p in problems if p.get("severity") == "error"]
    warnings = [p.get("message", "") for p in problems if p.get("severity") == "warning"]
    return [e for e in errors if e], [w for w in warnings if w]
