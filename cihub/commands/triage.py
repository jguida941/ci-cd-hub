"""Generate triage bundle outputs from existing report artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.triage_service import generate_triage_bundle, write_triage_bundle
from cihub.types import CommandResult


def _build_meta(args: argparse.Namespace) -> dict[str, object]:
    return {
        "command": "cihub triage",
        "args": [str(arg) for arg in vars(args).values() if arg is not None],
    }


def cmd_triage(args: argparse.Namespace) -> int | CommandResult:
    json_mode = getattr(args, "json", False)
    output_dir = Path(args.output_dir or ".cihub")
    report_path = Path(args.report) if args.report else None
    summary_path = Path(args.summary) if args.summary else None

    try:
        bundle = generate_triage_bundle(
            output_dir=output_dir,
            report_path=report_path,
            summary_path=summary_path,
            meta=_build_meta(args),
        )
        artifacts = write_triage_bundle(bundle, output_dir)
    except Exception as exc:  # noqa: BLE001 - surface error in CLI
        message = f"Failed to generate triage bundle: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Triage bundle generated",
            artifacts={key: str(path) for key, path in artifacts.items()},
            data={
                "schema_version": bundle.triage.get("schema_version", ""),
                "failure_count": bundle.triage.get("summary", {}).get("failure_count", 0),
            },
        )

    print(f"Wrote triage: {artifacts['triage']}")
    print(f"Wrote priority: {artifacts['priority']}")
    print(f"Wrote prompt pack: {artifacts['markdown']}")
    print(f"Updated history: {artifacts['history']}")
    return EXIT_SUCCESS
