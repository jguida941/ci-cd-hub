"""Hub-CI thresholds command - read/write thresholds to defaults.yaml."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.paths import hub_root


def _get_defaults_path() -> Path:
    """Get path to config/defaults.yaml."""
    return hub_root() / "config" / "defaults.yaml"


def _load_defaults() -> dict:
    """Load defaults.yaml as dict."""
    path = _get_defaults_path()
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_defaults(data: dict) -> None:
    """Save dict back to defaults.yaml, preserving comments where possible."""
    path = _get_defaults_path()
    # Note: This will lose comments. A more robust solution would use ruamel.yaml
    # to preserve comments, but for now we use safe_dump with explicit settings.
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def cmd_thresholds(args: argparse.Namespace) -> CommandResult:
    """Handle hub-ci thresholds subcommand.

    Subactions:
        show: Display current thresholds (default)
        get <key>: Get a specific threshold
        set <key> <value>: Set a threshold
        list: List all threshold keys
    """
    action = getattr(args, "thresholds_action", "show")
    key = getattr(args, "key", None)
    value = getattr(args, "value", None)

    defaults = _load_defaults()
    thresholds = defaults.get("thresholds", {})

    if action == "show":
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Global thresholds ({len(thresholds)} keys)",
            data={"thresholds": thresholds, "source": str(_get_defaults_path())},
        )

    if action == "list":
        keys = sorted(thresholds.keys())
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"{len(keys)} threshold keys",
            data={"keys": keys},
        )

    if action == "get":
        if not key:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Missing threshold key",
                problems=[
                    {"severity": "error", "message": "Key required for 'get'", "code": "CIHUB-THRESHOLDS-NO-KEY"}
                ],
            )
        if key not in thresholds:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Unknown threshold: {key}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Threshold '{key}' not found",
                        "code": "CIHUB-THRESHOLDS-NOT-FOUND",
                    }
                ],
                data={"available_keys": sorted(thresholds.keys())},
            )
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"{key} = {thresholds[key]}",
            data={"key": key, "value": thresholds[key]},
        )

    if action == "set":
        if not key:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Missing threshold key",
                problems=[
                    {"severity": "error", "message": "Key required for 'set'", "code": "CIHUB-THRESHOLDS-NO-KEY"}
                ],
            )
        if value is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Missing threshold value",
                problems=[
                    {"severity": "error", "message": "Value required for 'set'", "code": "CIHUB-THRESHOLDS-NO-VALUE"}
                ],
            )

        # Parse value - try int, then float, then string
        parsed_value: int | float | str
        try:
            parsed_value = int(value)
        except ValueError:
            try:
                parsed_value = float(value)
            except ValueError:
                parsed_value = value

        old_value = thresholds.get(key, "<not set>")
        thresholds[key] = parsed_value
        defaults["thresholds"] = thresholds

        _save_defaults(defaults)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Set {key}: {old_value} -> {parsed_value}",
            data={"key": key, "old_value": old_value, "new_value": parsed_value},
        )

    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=f"Unknown action: {action}",
        problems=[
            {"severity": "error", "message": f"Unknown action '{action}'", "code": "CIHUB-THRESHOLDS-UNKNOWN-ACTION"}
        ],
    )
