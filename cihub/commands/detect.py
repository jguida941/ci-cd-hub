"""Detect command handler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.detection import resolve_language
from cihub.types import CommandResult


def cmd_detect(args: argparse.Namespace) -> CommandResult:
    """Detect project language from markers.

    Always returns CommandResult for consistent output handling.
    """
    repo_path = Path(args.repo).resolve()
    items: list[str] = []  # Human-readable output

    try:
        language, reasons = resolve_language(repo_path, args.language)
    except ValueError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=str(exc),
            problems=[
                {
                    "severity": "error",
                    "message": str(exc),
                    "code": "CIHUB-DETECT-001",
                }
            ],
            data={"items": [f"Error: {exc}"]},
        )

    payload: dict[str, Any] = {"language": language}
    if args.explain:
        payload["reasons"] = reasons

    # Human-readable output (JSON format for backwards compatibility)
    items.append(json.dumps(payload, indent=2))

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Detected language: {language}",
        data={**payload, "items": items, "raw_output": json.dumps(payload, indent=2)},
    )
