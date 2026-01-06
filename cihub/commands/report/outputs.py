"""Report outputs command logic."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult


def _report_outputs(args: argparse.Namespace) -> CommandResult:
    """Extract outputs from a report.json file."""
    report_path = Path(args.report)
    try:
        with report_path.open(encoding="utf-8") as f:
            report = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return CommandResult(exit_code=EXIT_FAILURE, summary=f"Failed to read report: {exc}")

    results = report.get("results", {}) or {}
    status = results.get("build") or results.get("test")
    if status not in {"success", "failure", "skipped"}:
        tests_failed = int(results.get("tests_failed", 0))
        status = "failure" if tests_failed > 0 else "success"

    output_path = Path(args.output) if args.output else None
    if output_path is None:
        output_path_env = os.environ.get("GITHUB_OUTPUT")
        if output_path_env:
            output_path = Path(output_path_env)
    if output_path is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="No output target specified for report outputs",
        )

    output_text = (
        f"build_status={status}\n"
        f"coverage={results.get('coverage', 0)}\n"
        f"mutation_score={results.get('mutation_score', 0)}\n"
    )
    output_path.write_text(output_text, encoding="utf-8")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Report outputs written",
        artifacts={"outputs": str(output_path)},
        files_generated=[str(output_path)],
    )
