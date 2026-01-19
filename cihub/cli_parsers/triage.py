"""Parser setup for triage commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import add_ai_flags, see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_triage_command(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    triage = subparsers.add_parser("triage", help="Generate triage bundle outputs", epilog=see_also_epilog("triage"))
    add_json_flag(triage)
    add_ai_flags(triage)
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
        "--latest",
        action="store_true",
        help="Auto-triage the most recent failed workflow run (no run ID needed)",
    )
    triage.add_argument(
        "--watch",
        action="store_true",
        help="Watch for new failed runs and auto-triage them (background daemon)",
    )
    triage.add_argument(
        "--interval",
        type=int,
        default=30,
        metavar="SECONDS",
        help="Polling interval for --watch mode (default: 30 seconds)",
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
    # Remote run filtering
    triage.add_argument(
        "--workflow",
        metavar="NAME",
        help="Filter remote runs by workflow name (e.g., 'hub-ci.yml')",
    )
    triage.add_argument(
        "--branch",
        metavar="NAME",
        help="Filter remote runs by branch name (e.g., 'main')",
    )
    # Multi-report mode
    triage.add_argument(
        "--multi",
        action="store_true",
        help="Enable multi-report mode (aggregate multiple report.json files)",
    )
    triage.add_argument(
        "--aggregate",
        action="store_true",
        help="Force aggregated output for multi-report mode (single combined bundle)",
    )
    triage.add_argument(
        "--per-repo",
        action="store_true",
        dest="per_repo",
        help="Force per-repo output for multi-report mode (separate bundles with index)",
    )
    triage.add_argument(
        "--reports-dir",
        metavar="PATH",
        help="Directory containing multiple report.json files (for --multi mode)",
    )
    # Flaky detection
    triage.add_argument(
        "--detect-flaky",
        action="store_true",
        dest="detect_flaky",
        help="Analyze triage history for flaky test patterns",
    )
    # Gate history tracking
    triage.add_argument(
        "--gate-history",
        action="store_true",
        dest="gate_history",
        help="Analyze triage history for gate status changes over time",
    )
    # Output filtering
    triage.add_argument(
        "--min-severity",
        metavar="LEVEL",
        choices=["blocker", "high", "medium", "low"],
        help="Only show failures at or above this severity level (blocker > high > medium > low)",
    )
    triage.add_argument(
        "--category",
        metavar="CAT",
        choices=["workflow", "security", "test", "lint", "docs", "build", "cihub"],
        help="Only show failures in this category",
    )
    # Tool verification
    triage.add_argument(
        "--verify-tools",
        action="store_true",
        dest="verify_tools",
        help="Verify that configured tools actually ran and have proof (metrics/artifacts)",
    )
    triage.set_defaults(func=handlers.cmd_triage)
