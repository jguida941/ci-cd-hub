"""CI execution engine for the services layer.

This package splits the ci_engine module into logical submodules while
maintaining backward compatibility by re-exporting all public symbols.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from cihub.ci_config import load_ci_config, load_hub_config
from cihub.ci_runner import run_java_build  # Keep for backward compat re-export
from cihub.core.languages import get_strategy
from cihub.exit_codes import EXIT_FAILURE, EXIT_INTERNAL_ERROR, EXIT_SUCCESS
from cihub.reporting import render_summary
from cihub.services.types import RunCIOptions, ServiceResult
from cihub.tools.registry import (
    JAVA_TOOLS,
    PYTHON_TOOLS,
    RESERVED_FEATURES,
    get_all_tools_from_config,
    get_runners,
    is_custom_tool,
)
from cihub.utils import (
    detect_java_project_type,
    get_git_branch,
    get_git_remote,
    get_repo_name,
    parse_repo_from_remote,
    resolve_executable,
    validate_subdir,
)

# Backward compatibility aliases (deprecated, use non-underscore versions)
_detect_java_project_type = detect_java_project_type
_get_repo_name = get_repo_name

# Import from submodules
from .gates import (
    _build_context,
    _check_require_run_or_fail,
    _evaluate_java_gates,
    _evaluate_python_gates,
    _tool_requires_run_or_fail,
)
from .helpers import (
    _apply_env_overrides,
    _apply_force_all_tools,
    _get_env_name,
    _get_env_value,
    _get_git_commit,
    _parse_env_bool,
    _resolve_workdir,
    _set_tool_enabled,
    _split_problems,
    _tool_enabled,
    _tool_gate_enabled,
    _warn_reserved_features,
)
from .io import _collect_codecov_files, _run_codecov_upload
from .java_tools import _run_java_tools
from .notifications import _notify, _send_email, _send_slack
from .python_tools import (
    _install_python_dependencies,
    _run_dep_command,
    _run_python_tools,
)
from .validation import _self_validate_report


@dataclass
class CiRunResult(ServiceResult):
    """Result of running cihub ci via the services layer."""

    exit_code: int = 0
    report_path: Path | None = None
    summary_path: Path | None = None
    report: dict[str, Any] = field(default_factory=dict)
    summary_text: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    problems: list[dict[str, Any]] = field(default_factory=list)


# Tool runner dictionaries (backward compatibility)
# New code should use: from cihub.tools.registry import get_runners
# These are lazily evaluated on first access.

# Mapping of deprecated run_* function names to (language, tool_name)
_RUNNER_COMPAT_MAP: dict[str, tuple[str, str]] = {
    "run_pytest": ("python", "pytest"),
    "run_ruff": ("python", "ruff"),
    "run_black": ("python", "black"),
    "run_isort": ("python", "isort"),
    "run_mypy": ("python", "mypy"),
    "run_bandit": ("python", "bandit"),
    "run_pip_audit": ("python", "pip_audit"),
    "run_mutmut": ("python", "mutmut"),
    "run_sbom": ("python", "sbom"),
    "run_semgrep": ("python", "semgrep"),
    "run_trivy": ("python", "trivy"),
    "run_docker": ("python", "docker"),
    "run_jacoco": ("java", "jacoco"),
    "run_pitest": ("java", "pitest"),
    "run_checkstyle": ("java", "checkstyle"),
    "run_spotbugs": ("java", "spotbugs"),
    "run_pmd": ("java", "pmd"),
    "run_owasp": ("java", "owasp"),
}


def __getattr__(name: str) -> Any:
    """Lazy module attribute access for backward compatibility.

    Provides backward-compatible access to:
    - PYTHON_RUNNERS, JAVA_RUNNERS dicts
    - Individual run_* functions (run_pytest, run_ruff, etc.)
    """
    if name == "PYTHON_RUNNERS":
        return dict(get_runners("python"))  # Return copy for isolation
    if name == "JAVA_RUNNERS":
        return dict(get_runners("java"))  # Return copy for isolation
    if name in _RUNNER_COMPAT_MAP:
        from cihub.tools.registry import get_runner

        lang, tool = _RUNNER_COMPAT_MAP[name]
        runner = get_runner(tool, lang)
        if runner is None:
            raise AttributeError(
                f"Runner '{name}' not found in registry for {lang}/{tool}. "
                f"Check cihub/tools/registry.py _load_{lang}_runners()."
            )
        return runner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def run_ci(
    repo_path: Path,
    *,
    options: RunCIOptions | None = None,
    output_dir: Path | None = None,
    report_path: Path | None = None,
    summary_path: Path | None = None,
    workdir: str | None = None,
    install_deps: bool = False,
    correlation_id: str | None = None,
    no_summary: bool = False,
    write_github_summary: bool | None = None,
    config_from_hub: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CiRunResult:
    """Run CI pipeline for a repository.

    Args:
        repo_path: Path to the repository root
        options: RunCIOptions object (preferred). If provided, individual kwargs are ignored.
        output_dir: Directory for output files (default: .cihub)
        report_path: Path for report.json (default: output_dir/report.json)
        summary_path: Path for summary.md (default: output_dir/summary.md)
        workdir: Subdirectory to run CI in
        install_deps: Whether to install Python dependencies
        correlation_id: Correlation ID for tracing
        no_summary: Skip writing summary file
        write_github_summary: Write to GITHUB_STEP_SUMMARY
        config_from_hub: Load config from hub config files
        env: Environment variable mapping (default: os.environ)

    Returns:
        CiRunResult with exit code, report, and any problems

    Example:
        # Using options (preferred)
        opts = RunCIOptions(install_deps=True)
        result = run_ci(repo_path, options=opts)

        # Using kwargs (backward compatible)
        result = run_ci(repo_path, install_deps=True)
    """
    # If options provided, extract values from it; otherwise use kwargs
    if options is not None:
        output_dir = options.output_dir
        report_path = options.report_path
        summary_path = options.summary_path
        workdir = options.workdir
        install_deps = options.install_deps
        correlation_id = options.correlation_id
        no_summary = options.no_summary
        write_github_summary = options.write_github_summary
        config_from_hub = options.config_from_hub
        env = options.env

    repo_path = repo_path.resolve()
    output_dir = Path(output_dir or ".cihub")
    if not output_dir.is_absolute():
        output_dir = repo_path / output_dir
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    env_map = dict(env) if env is not None else dict(os.environ)

    try:
        if config_from_hub:
            config = load_hub_config(config_from_hub, repo_path)
        else:
            config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        config_problems = [{"severity": "error", "message": message, "code": "CIHUB-CI-CONFIG"}]
        errors, warnings = _split_problems(config_problems)
        return CiRunResult(
            success=False,
            errors=errors,
            warnings=warnings,
            exit_code=EXIT_FAILURE,
            problems=config_problems,
        )

    language = config.get("language") or ""
    run_workdir = _resolve_workdir(repo_path, config, workdir)
    problems: list[dict[str, Any]] = []
    _apply_force_all_tools(config, language)
    _apply_env_overrides(config, language, env_map, problems)
    _warn_reserved_features(config, problems)

    # -------------------------------------------------------------------------
    # Language Strategy Pattern: get strategy early, fail fast for unsupported
    # -------------------------------------------------------------------------
    try:
        strategy = get_strategy(language)
    except ValueError:
        message = f"cihub ci supports python or java (got '{language}')"
        problems = [{"severity": "error", "message": message, "code": "CIHUB-CI-LANGUAGE"}]
        errors, warnings = _split_problems(problems)
        return CiRunResult(
            success=False,
            errors=errors,
            warnings=warnings,
            exit_code=EXIT_FAILURE,
            problems=problems,
        )

    report: dict[str, Any] = {}
    tool_outputs: dict[str, dict[str, Any]] = {}
    tools_ran: dict[str, bool] = {}
    tools_success: dict[str, bool] = {}
    gate_failures: list[str] = []

    # -------------------------------------------------------------------------
    # Run tools via strategy (language-specific kwargs merged via strategy)
    # -------------------------------------------------------------------------
    try:
        # Get language-specific kwargs merged with caller-provided kwargs
        run_kwargs = strategy.get_run_kwargs(config, install_deps=install_deps)
        tool_outputs, tools_ran, tools_success = strategy.run_tools(
            config,
            repo_path,
            run_workdir,
            output_dir,
            problems,
            **run_kwargs,
        )
    except Exception as exc:
        message = f"Tool execution failed: {exc}"
        problems.append(
            {
                "severity": "error",
                "message": message,
                "code": "CIHUB-CI-TOOL-FAILURE",
            }
        )
        errors, warnings = _split_problems(problems)
        return CiRunResult(
            success=False,
            errors=errors,
            warnings=warnings,
            exit_code=EXIT_INTERNAL_ERROR,
            problems=problems,
        )

    # -------------------------------------------------------------------------
    # Build tools_configured and tools_require_run using strategy
    # Include custom tools (x-* prefix) from config alongside built-in tools
    # -------------------------------------------------------------------------
    all_tools = get_all_tools_from_config(config, language)
    # Custom tools (x-* prefix) default to enabled=True per schema; built-in tools default to False
    tools_configured = {tool: _tool_enabled(config, tool, language, default=is_custom_tool(tool)) for tool in all_tools}
    tools_require_run = {tool: _tool_requires_run_or_fail(tool, config, language) for tool in all_tools}

    # -------------------------------------------------------------------------
    # Resolve thresholds via strategy
    # -------------------------------------------------------------------------
    thresholds = strategy.resolve_thresholds(config)

    # -------------------------------------------------------------------------
    # Extract docker config via strategy (encapsulates language-specific access)
    # -------------------------------------------------------------------------
    docker_cfg = strategy.get_docker_config(config)
    docker_compose = docker_cfg.get("compose_file")
    docker_health = docker_cfg.get("health_endpoint")
    # Apply language-specific default for compose_file
    if tools_configured.get("docker") and not docker_compose:
        docker_compose = strategy.get_docker_compose_default()
    # Only include docker config if docker is actually configured
    if not tools_configured.get("docker"):
        docker_compose = None
        docker_health = None

    # -------------------------------------------------------------------------
    # Build context (language-specific extras via strategy)
    # -------------------------------------------------------------------------
    context_kwargs: dict[str, Any] = {
        "docker_compose_file": docker_compose,
        "docker_health_endpoint": docker_health,
    }
    # Add language-specific context fields (e.g., Java's build_tool, project_type)
    context_extras = strategy.get_context_extras(config, repo_path / run_workdir)
    context_kwargs.update(context_extras)

    context = _build_context(repo_path, config, run_workdir, correlation_id, **context_kwargs)

    # -------------------------------------------------------------------------
    # Build report and evaluate gates via strategy
    # -------------------------------------------------------------------------
    report = strategy.build_report(
        config,
        tool_outputs,
        tools_configured,
        tools_ran,
        tools_success,
        thresholds,
        context,
        tools_require_run=tools_require_run,
    )
    gate_failures = strategy.evaluate_gates(report, thresholds, tools_configured, config)

    resolved_report_path = report_path or output_dir / "report.json"
    if not resolved_report_path.is_absolute():
        resolved_report_path = repo_path / resolved_report_path
    resolved_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    github_summary_cfg = config.get("reports", {}).get("github_summary", {}) or {}
    include_metrics = bool(github_summary_cfg.get("include_metrics", True))
    summary_text = render_summary(report, include_metrics=include_metrics)
    if write_github_summary is None:
        write_summary = bool(github_summary_cfg.get("enabled", True))
    else:
        write_summary = bool(write_github_summary)

    resolved_summary_path: Path | None = None
    if not no_summary:
        resolved_summary_path = summary_path or output_dir / "summary.md"
        if not resolved_summary_path.is_absolute():
            resolved_summary_path = repo_path / resolved_summary_path
        resolved_summary_path.write_text(summary_text, encoding="utf-8")

    github_summary_env = env_map.get("GITHUB_STEP_SUMMARY")
    if write_summary and github_summary_env:
        Path(github_summary_env).write_text(summary_text, encoding="utf-8")

    # Self-validation: catch contradictions between report and summary
    _self_validate_report(report, summary_text, output_dir, problems, env_map)

    codecov_cfg = config.get("reports", {}).get("codecov", {}) or {}
    if codecov_cfg.get("enabled", True):
        files = _collect_codecov_files(language, output_dir, tool_outputs)
        _run_codecov_upload(
            files,
            bool(codecov_cfg.get("fail_ci_on_error", False)),
            problems,
        )

    if gate_failures:
        problems.extend(
            [
                {
                    "severity": "error",
                    "message": failure,
                    "code": "CIHUB-CI-GATE",
                }
                for failure in gate_failures
            ]
        )

    has_errors = any(p.get("severity") == "error" for p in problems)
    _notify(not has_errors, config, report, problems, env_map)
    exit_code = EXIT_FAILURE if has_errors else EXIT_SUCCESS
    errors, warnings = _split_problems(problems)

    artifacts: dict[str, str] = {"report": str(resolved_report_path)}
    data: dict[str, str] = {"report_path": str(resolved_report_path)}
    if resolved_summary_path:
        artifacts["summary"] = str(resolved_summary_path)
        data["summary_path"] = str(resolved_summary_path)

    return CiRunResult(
        success=exit_code == EXIT_SUCCESS,
        errors=errors,
        warnings=warnings,
        exit_code=exit_code,
        report_path=resolved_report_path,
        summary_path=resolved_summary_path,
        report=report,
        summary_text=summary_text,
        artifacts=artifacts,
        data=data,
        problems=problems,
    )


# ============================================================================
# Public API - Re-exports for backward compatibility
# ============================================================================

__all__ = [
    # Main entry point
    "run_ci",
    "CiRunResult",
    "RunCIOptions",
    # Runner dictionaries
    "PYTHON_RUNNERS",
    "JAVA_RUNNERS",
    # Helpers from helpers.py
    "get_repo_name",
    "_get_git_commit",
    "_resolve_workdir",
    "detect_java_project_type",
    # Backward compatibility aliases (deprecated)
    "_get_repo_name",
    "_detect_java_project_type",
    "_tool_enabled",
    "_tool_gate_enabled",
    "_parse_env_bool",
    "_get_env_name",
    "_get_env_value",
    "_warn_reserved_features",
    "_set_tool_enabled",
    "_apply_env_overrides",
    "_apply_force_all_tools",
    "_split_problems",
    # Helpers from io.py
    "_collect_codecov_files",
    "_run_codecov_upload",
    # Helpers from notifications.py
    "_send_slack",
    "_send_email",
    "_notify",
    # Helpers from python_tools.py
    "_run_dep_command",
    "_install_python_dependencies",
    "_run_python_tools",
    # Helpers from java_tools.py
    "_run_java_tools",
    # Helpers from gates.py
    "_build_context",
    "_evaluate_python_gates",
    "_evaluate_java_gates",
    "_tool_requires_run_or_fail",
    "_check_require_run_or_fail",
    # Helpers from validation.py
    "_self_validate_report",
    # Re-exports from cihub.cli for backward compatibility
    "get_git_branch",
    "get_git_remote",
    "parse_repo_from_remote",
    "resolve_executable",
    "validate_subdir",
    # Re-exports from cihub.tools.registry
    "PYTHON_TOOLS",
    "JAVA_TOOLS",
    "RESERVED_FEATURES",
    # Re-exports from cihub.ci_runner for backward compatibility
    "run_java_build",
]
