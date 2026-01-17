"""CLI adapter for CI execution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cihub.services.ci import CiRunResult, RunCIOptions, run_ci
from cihub.services.triage_service import generate_triage_bundle, write_triage_bundle
from cihub.types import CommandResult
from cihub.utils import hub_root
from cihub.utils.debug import emit_debug_context
from cihub.utils.env import env_bool, env_int


def _summary_for_result(result: CiRunResult) -> str:
    if result.errors and not result.report:
        return result.errors[0]
    return "CI completed with issues" if result.problems else "CI completed"


def _result_to_command_result(result: CiRunResult) -> CommandResult:
    """Convert CiRunResult to CommandResult with proper field mapping."""
    files_generated = []
    if result.report_path:
        files_generated.append(str(result.report_path))
    if result.summary_path:
        files_generated.append(str(result.summary_path))

    return CommandResult(
        exit_code=result.exit_code,
        summary=_summary_for_result(result),
        problems=list(result.problems),
        artifacts=dict(result.artifacts),
        data=dict(result.data),
        files_generated=files_generated or [],
    )


def _describe_path(path: Path) -> str:
    if path.exists():
        return str(path)
    return f"{path} (missing)"


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def _emit_ci_debug_context(args, result: CiRunResult) -> None:
    repo_path = Path(args.repo or ".").resolve()
    output_dir = Path(args.output_dir or ".cihub")
    if not output_dir.is_absolute():
        output_dir = repo_path / output_dir
    output_dir = output_dir.resolve()

    config_sources: list[str] = []
    defaults_path = hub_root() / "config" / "defaults.yaml"
    if args.config_from_hub:
        hub_config = hub_root() / "config" / "repos" / f"{args.config_from_hub}.yaml"
        config_sources.append(_describe_path(hub_config))
        local_path = repo_path / ".ci-hub.yml"
        if local_path.exists():
            config_sources.append(_describe_path(local_path))
    else:
        config_sources.append(_describe_path(repo_path / ".ci-hub.yml"))
    config_sources.append(_describe_path(defaults_path))

    report = result.report or {}
    environment = report.get("environment", {}) if isinstance(report.get("environment"), dict) else {}
    tools_configured = report.get("tools_configured", {}) if isinstance(report.get("tools_configured"), dict) else {}
    tools_ran = report.get("tools_ran", {}) if isinstance(report.get("tools_ran"), dict) else {}
    tools_success = report.get("tools_success", {}) if isinstance(report.get("tools_success"), dict) else {}

    enabled_tools = [tool for tool, enabled in tools_configured.items() if enabled]
    disabled_tools = [tool for tool, enabled in tools_configured.items() if not enabled]
    skipped_tools = [tool for tool in enabled_tools if not tools_ran.get(tool, False)]
    failed_tools = [tool for tool in enabled_tools if tools_ran.get(tool, False) and not tools_success.get(tool, False)]

    language = ""
    if "python_version" in report:
        language = "python"
    elif "java_version" in report:
        language = "java"

    entries = [
        ("repo_path", str(repo_path)),
        ("workdir", environment.get("workdir") or args.workdir or "."),
        ("language", language),
        ("config_sources", _format_list(config_sources)),
        ("output_dir", str(output_dir)),
        ("report_path", str(result.report_path) if result.report_path else None),
        ("summary_path", str(result.summary_path) if result.summary_path else None),
        ("correlation_id", report.get("hub_correlation_id") or args.correlation_id),
        ("install_deps", str(bool(args.install_deps))),
        ("write_github_summary", str(args.write_github_summary)),
        ("no_summary", str(bool(args.no_summary))),
        ("config_from_hub", args.config_from_hub),
        ("tools_enabled", _format_list(sorted(enabled_tools))),
        ("tools_disabled", _format_list(sorted(disabled_tools))),
        ("tools_skipped", _format_list(sorted(skipped_tools))),
        ("tools_failed", _format_list(sorted(failed_tools))),
        ("exit_code", str(result.exit_code)),
    ]
    emit_debug_context("ci context", entries)


def _resolve_output_dir(args) -> Path:
    repo_path = Path(args.repo or ".").resolve()
    output_dir = Path(args.output_dir or ".cihub")
    if not output_dir.is_absolute():
        output_dir = repo_path / output_dir
    return output_dir.resolve()


def _get_ai_loop_env_int(name: str) -> int | None:
    if name not in os.environ:
        return None
    value = env_int(name, default=0)
    return value if value > 0 else None


def _emit_triage_bundle(args, result: CiRunResult | None, error: str | None = None) -> None:
    if not env_bool("CIHUB_EMIT_TRIAGE", default=False):
        return

    output_dir = _resolve_output_dir(args)
    report_path = result.report_path if result else output_dir / "report.json"
    summary_path = result.summary_path if result else output_dir / "summary.md"
    iteration = getattr(args, "ai_loop_iteration", None)
    max_iterations = getattr(args, "ai_loop_max_iterations", None)
    if iteration is None:
        iteration = _get_ai_loop_env_int("CIHUB_AI_LOOP_ITERATION")
    if max_iterations is None:
        max_iterations = _get_ai_loop_env_int("CIHUB_AI_LOOP_MAX_ITERATIONS")
    meta = {
        "command": "cihub ci",
        "args": [],
        "correlation_id": args.correlation_id,
        "repo": str(Path(args.repo or ".").resolve()),
        "branch": "",
        "commit_sha": "",
        "workflow_ref": "",
        "error": error or "",
        "iteration": iteration,
        "max_iterations": max_iterations,
    }
    try:
        bundle = generate_triage_bundle(
            output_dir=output_dir,
            report_path=report_path,
            summary_path=summary_path,
            meta=meta,
        )
        write_triage_bundle(bundle, output_dir)
    except Exception as exc:  # noqa: BLE001 - best effort only
        sys.stderr.write(f"[triage] Failed to emit triage bundle: {exc}\n")


def cmd_ci(args) -> CommandResult:
    """Execute CI run and return structured result."""
    try:
        options = RunCIOptions.from_args(args)
        result = run_ci(
            repo_path=Path(args.repo or "."),
            options=options,
        )
    except Exception as exc:  # noqa: BLE001 - re-raise after triage
        _emit_triage_bundle(args, None, error=str(exc))
        raise

    _emit_ci_debug_context(args, result)
    _emit_triage_bundle(args, result)

    return _result_to_command_result(result)
