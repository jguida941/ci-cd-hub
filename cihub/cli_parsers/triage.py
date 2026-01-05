"""Parser setup for triage commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_triage_command(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    triage = subparsers.add_parser("triage", help="Generate triage bundle outputs")
    add_json_flag(triage)
    triage.add_argument(
        "--output-dir",
        help="Output directory (default: .cihub)",
    )
    triage.add_argument(
        "--report",
        help="Path to report.json (default: <output-dir>/report.json)",
    )
    triage.add_argument(
        "--summary",
        help="Path to summary.md (default: <output-dir>/summary.md)",
    )
    # Remote run analysis
    triage.add_argument(
        "--run",
        metavar="RUN_ID",
        help="GitHub workflow run ID to analyze (fetches artifacts/logs via gh CLI)",
    )
    triage.add_argument(
        "--artifacts-dir",
        metavar="PATH",
        help="Path to pre-downloaded artifacts directory (offline mode)",
    )
    triage.add_argument(
        "--repo",
        metavar="OWNER/REPO",
        help="Target repository for remote run analysis (default: current repo)",
    )
    triage.set_defaults(func=handlers.cmd_triage)
