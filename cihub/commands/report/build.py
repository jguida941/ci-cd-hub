"""Report build command logic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cihub.ci_config import load_ci_config
from cihub.ci_report import (
    build_java_report,
    build_python_report,
    resolve_thresholds,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.reporting import render_summary_from_path
from cihub.tools.registry import get_all_tools_from_config, is_custom_tool
from cihub.types import CommandResult
from cihub.utils import detect_java_project_type, hub_root
from cihub.utils.debug import emit_debug_context

from .helpers import (
    _build_context,
    _load_tool_outputs,
    _tool_enabled,
)


def _describe_path(path: Path) -> str:
    if path.exists():
        return str(path)
    return f"{path} (missing)"


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def _emit_build_debug_context(
    *,
    repo_path: Path,
    output_dir: Path,
    tool_dir: Path,
    report_path: Path,
    summary_path: Path,
    workdir: str | None,
    correlation_id: str | None,
    config: dict[str, object] | None,
    report: dict[str, object] | None,
    error: str | None = None,
) -> None:
    defaults_path = hub_root() / "config" / "defaults.yaml"
    config_sources = [
        _describe_path(repo_path / ".ci-hub.yml"),
        _describe_path(defaults_path),
    ]

    language = ""
    if config and isinstance(config.get("language"), str):
        language = str(config.get("language"))
    elif report:
        if "python_version" in report:
            language = "python"
        elif "java_version" in report:
            language = "java"

    _tools_configured = report.get("tools_configured", {}) if isinstance(report, dict) else {}
    _tools_ran = report.get("tools_ran", {}) if isinstance(report, dict) else {}
    _tools_success = report.get("tools_success", {}) if isinstance(report, dict) else {}
    tools_configured: dict[str, bool] = _tools_configured if isinstance(_tools_configured, dict) else {}
    tools_ran: dict[str, bool] = _tools_ran if isinstance(_tools_ran, dict) else {}
    tools_success: dict[str, bool] = _tools_success if isinstance(_tools_success, dict) else {}

    enabled_tools = [tool for tool, enabled in tools_configured.items() if enabled]
    disabled_tools = [tool for tool, enabled in tools_configured.items() if not enabled]
    skipped_tools = [tool for tool in enabled_tools if not tools_ran.get(tool, False)]
    failed_tools = [tool for tool in enabled_tools if tools_ran.get(tool, False) and not tools_success.get(tool, False)]

    entries = [
        ("repo_path", str(repo_path)),
        ("workdir", workdir or "."),
        ("language", language),
        ("config_sources", _format_list(config_sources)),
        ("tool_dir", str(tool_dir)),
        ("output_dir", str(output_dir)),
        ("report_path", str(report_path)),
        ("summary_path", str(summary_path)),
        ("correlation_id", correlation_id),
        ("tools_enabled", _format_list(sorted(enabled_tools))),
        ("tools_disabled", _format_list(sorted(disabled_tools))),
        ("tools_skipped", _format_list(sorted(skipped_tools))),
        ("tools_failed", _format_list(sorted(failed_tools))),
        ("error", error),
    ]
    emit_debug_context("report build", entries)


def _build_report(args: argparse.Namespace) -> CommandResult:
    """Build a report from tool outputs."""
    repo_path = Path(args.repo or ".").resolve()
    output_dir = Path(args.output_dir or ".cihub")
    tool_dir = Path(args.tool_dir) if args.tool_dir else output_dir / "tool-outputs"
    report_path = Path(args.report) if args.report else output_dir / "report.json"
    summary_path = Path(args.summary) if args.summary else output_dir / "summary.md"

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        _emit_build_debug_context(
            repo_path=repo_path,
            output_dir=output_dir,
            tool_dir=tool_dir,
            report_path=report_path,
            summary_path=summary_path,
            workdir=args.workdir,
            correlation_id=args.correlation_id,
            config=None,
            report=None,
            error=message,
        )
        return CommandResult(exit_code=EXIT_FAILURE, summary=message)

    language = config.get("language") or ""
    tool_outputs = _load_tool_outputs(tool_dir)

    if language == "python":
        # Include built-in and custom tools; custom tools default to enabled=True per schema
        all_tools = get_all_tools_from_config(config, "python")
        tools_configured = {
            tool: _tool_enabled(config, tool, "python", default=is_custom_tool(tool)) for tool in all_tools
        }
        tools_ran = {tool: False for tool in tools_configured}
        tools_success = {tool: False for tool in tools_configured}
        for tool, data in tool_outputs.items():
            tools_ran[tool] = bool(data.get("ran"))
            tools_success[tool] = bool(data.get("success"))
        if tools_configured.get("hypothesis"):
            tools_ran["hypothesis"] = tools_ran.get("pytest", False)
            tools_success["hypothesis"] = tools_success.get("pytest", False)
        thresholds = resolve_thresholds(config, "python")
        context = _build_context(repo_path, config, args.workdir or ".", args.correlation_id)
        report = build_python_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
    elif language == "java":
        # Include built-in and custom tools; custom tools default to enabled=True per schema
        all_tools = get_all_tools_from_config(config, "java")
        tools_configured = {
            tool: _tool_enabled(config, tool, "java", default=is_custom_tool(tool)) for tool in all_tools
        }
        tools_ran = {tool: False for tool in tools_configured}
        tools_success = {tool: False for tool in tools_configured}
        for tool, data in tool_outputs.items():
            tools_ran[tool] = bool(data.get("ran"))
            tools_success[tool] = bool(data.get("success"))

        if tools_configured.get("jqwik"):
            build_data = tool_outputs.get("build", {}) or {}
            tests_failed = int(build_data.get("metrics", {}).get("tests_failed", 0))
            build_success = bool(build_data.get("success", False))
            tools_ran["jqwik"] = bool(build_data)
            tools_success["jqwik"] = build_success and tests_failed == 0

        thresholds = resolve_thresholds(config, "java")
        build_tool = config.get("java", {}).get("build_tool", "maven").strip().lower() or "maven"
        project_type = detect_java_project_type(repo_path / (args.workdir or "."))
        docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
        context = _build_context(
            repo_path,
            config,
            args.workdir or ".",
            args.correlation_id,
            build_tool=build_tool,
            project_type=project_type,
            docker_compose_file=docker_cfg.get("compose_file"),
            docker_health_endpoint=docker_cfg.get("health_endpoint"),
        )
        report = build_java_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
    else:
        message = f"report build supports python or java (got '{language}')"
        return CommandResult(exit_code=EXIT_FAILURE, summary=message)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_text = render_summary_from_path(report_path)
    summary_path.write_text(summary_text, encoding="utf-8")

    _emit_build_debug_context(
        repo_path=repo_path,
        output_dir=output_dir,
        tool_dir=tool_dir,
        report_path=report_path,
        summary_path=summary_path,
        workdir=args.workdir,
        correlation_id=args.correlation_id,
        config=config,
        report=report,
        error=None,
    )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Report built",
        artifacts={"report": str(report_path), "summary": str(summary_path)},
        files_generated=[str(report_path), str(summary_path)],
    )
