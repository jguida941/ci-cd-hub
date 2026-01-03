"""CI service wrapper for GUI/programmatic access."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cihub.cli import CommandResult
from cihub.commands.ci import cmd_ci
from cihub.services.types import ServiceResult


@dataclass
class CiRunResult(ServiceResult):
    """Result of running cihub ci via the services layer."""

    exit_code: int = 0
    command_result: CommandResult | None = None
    report_path: Path | None = None
    summary_path: Path | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    problems: list[dict[str, Any]] = field(default_factory=list)


def run_ci(
    repo_path: Path,
    *,
    output_dir: Path | None = None,
    report_path: Path | None = None,
    summary_path: Path | None = None,
    workdir: str | None = None,
    install_deps: bool = False,
    correlation_id: str | None = None,
    no_summary: bool = False,
    write_github_summary: bool | None = None,
    config_from_hub: str | None = None,
) -> CiRunResult:
    """Run `cihub ci` in JSON mode and return a structured result."""
    args = argparse.Namespace(
        repo=str(repo_path),
        json=True,
        output_dir=str(output_dir) if output_dir else None,
        summary=str(summary_path) if summary_path else None,
        report=str(report_path) if report_path else None,
        workdir=workdir,
        install_deps=install_deps,
        correlation_id=correlation_id,
        no_summary=no_summary,
        write_github_summary=write_github_summary,
        config_from_hub=config_from_hub,
    )

    result = cmd_ci(args)
    if not isinstance(result, CommandResult):
        exit_code = int(result)
        return CiRunResult(
            success=exit_code == 0,
            errors=["cihub ci returned a non-JSON result"],
            exit_code=exit_code,
        )

    problems = list(result.problems)
    errors = [p.get("message", "") for p in problems if p.get("severity") == "error"]
    warnings = [p.get("message", "") for p in problems if p.get("severity") == "warning"]

    report_value = result.data.get("report_path") or result.artifacts.get("report")
    summary_value = result.data.get("summary_path") or result.artifacts.get("summary")

    return CiRunResult(
        success=result.exit_code == 0,
        errors=[e for e in errors if e],
        warnings=[w for w in warnings if w],
        exit_code=result.exit_code,
        command_result=result,
        report_path=Path(report_value) if report_value else None,
        summary_path=Path(summary_value) if summary_value else None,
        artifacts=dict(result.artifacts),
        data=dict(result.data),
        problems=problems,
    )
