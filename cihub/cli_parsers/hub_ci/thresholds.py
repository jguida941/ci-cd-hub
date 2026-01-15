"""Parser setup for hub-ci thresholds subcommand."""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Callable


def add_thresholds_parsers(
    hub_ci_sub: _SubParsersAction,
    add_json_flag: Callable,
) -> None:
    """Add thresholds subcommand parser.

    Subcommands: thresholds (with actions: show, list, get, set)
    """
    hub_ci_thresholds = hub_ci_sub.add_parser(
        "thresholds",
        help="Read/write thresholds from config/defaults.yaml",
    )
    hub_ci_thresholds.add_argument(
        "thresholds_action",
        nargs="?",
        default="show",
        choices=["show", "list", "get", "set"],
        help="Action to perform (default: show)",
    )
    hub_ci_thresholds.add_argument(
        "key",
        nargs="?",
        help="Threshold key (for get/set)",
    )
    hub_ci_thresholds.add_argument(
        "value",
        nargs="?",
        help="Threshold value (for set)",
    )
    add_json_flag(hub_ci_thresholds)
