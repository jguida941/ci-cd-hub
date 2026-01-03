"""CLI adapter for CI execution."""

from __future__ import annotations

from pathlib import Path

from cihub.cli import CommandResult
from cihub.services.ci import CiRunResult, run_ci


def _summary_for_result(result: CiRunResult) -> str:
    if result.errors and not result.report:
        return result.errors[0]
    return "CI completed with issues" if result.problems else "CI completed"


def _result_to_command_result(result: CiRunResult) -> CommandResult:
    return CommandResult(
        exit_code=result.exit_code,
        summary=_summary_for_result(result),
        problems=list(result.problems),
        artifacts=dict(result.artifacts),
        data=dict(result.data),
    )


def _print_result(result: CiRunResult) -> None:
    if result.report_path:
        print(f"Wrote report: {result.report_path}")
    if result.summary_path:
        print(f"Wrote summary: {result.summary_path}")
    if result.problems:
        print("CI findings:")
        for problem in result.problems:
            severity = problem.get("severity", "error")
            message = problem.get("message", "")
            print(f"  - [{severity}] {message}")


def cmd_ci(args) -> int | CommandResult:
    result = run_ci(
        repo_path=Path(args.repo or "."),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        report_path=Path(args.report) if args.report else None,
        summary_path=Path(args.summary) if args.summary else None,
        workdir=args.workdir,
        install_deps=args.install_deps,
        correlation_id=args.correlation_id,
        no_summary=args.no_summary,
        write_github_summary=args.write_github_summary,
        config_from_hub=args.config_from_hub,
    )

    if getattr(args, "json", False):
        return _result_to_command_result(result)

    _print_result(result)
    return result.exit_code
