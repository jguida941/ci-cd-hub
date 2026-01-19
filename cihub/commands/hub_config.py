"""Hub operational settings commands.

Manages config/hub-settings.yaml - controls how hub-internal workflows run.
Separate from repo configs (config/repos/*.yaml) which control per-repo tool settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from cihub.config.io import load_yaml_file, save_yaml_file
from cihub.exit_codes import EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.paths import hub_root


def _get_hub_settings_path() -> Path:
    """Get path to hub-settings.yaml."""
    return hub_root() / "config" / "hub-settings.yaml"


def _load_hub_settings() -> dict[str, Any]:
    """Load hub settings from config/hub-settings.yaml.

    Returns:
        Settings dict, or defaults if file doesn't exist
    """
    path = _get_hub_settings_path()
    if not path.exists():
        # Return defaults matching schema
        return {
            "execution": {
                "skip_mutation": False,
                "write_github_summary": True,
                "include_details": True,
            },
            "debug": {
                "enabled": False,
                "verbose": False,
                "debug_context": False,
                "emit_triage": False,
            },
            "security": {
                "harden_runner": {
                    "policy": "audit",
                },
            },
        }
    return load_yaml_file(path)


def _save_hub_settings(settings: dict[str, Any]) -> None:
    """Save hub settings to config/hub-settings.yaml."""
    path = _get_hub_settings_path()
    save_yaml_file(path, settings)


def _get_nested(data: dict, path: str) -> Any:
    """Get a nested value by dot path (e.g., 'debug.enabled')."""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _set_nested(data: dict, path: str, value: Any) -> None:
    """Set a nested value by dot path (e.g., 'debug.enabled')."""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _parse_value(value_str: str) -> Any:
    """Parse a string value into appropriate type."""
    lower = value_str.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in ("audit", "block", "disabled"):
        return lower
    # Try numeric
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    return value_str


def _flatten_settings(settings: dict, prefix: str = "") -> dict[str, Any]:
    """Flatten nested settings to dot-path keys for GitHub output."""
    result = {}
    for key, value in settings.items():
        full_key = f"{prefix}{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_settings(value, f"{full_key}_"))
        else:
            result[full_key] = value
    return result


def cmd_hub(args) -> CommandResult:
    """Handle hub operational settings commands.

    Subcommands:
        hub config show  - Display current settings
        hub config set   - Update a setting
        hub config load  - Load and output for GitHub Actions
    """
    hub_sub = getattr(args, "hub_subcommand", None)
    config_sub = getattr(args, "config_subcommand", None)

    # hub (no subcommand) - show help
    if not hub_sub:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Hub operational settings. Use: cihub hub config [show|set|load]",
        )

    # hub config (no subcommand) - show help
    if hub_sub == "config" and not config_sub:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Manage hub settings. Use: cihub hub config [show|set|load]",
        )

    settings = _load_hub_settings()

    # hub config show
    if config_sub == "show":
        output = yaml.dump(settings, default_flow_style=False, sort_keys=False)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Hub operational settings (config/hub-settings.yaml)",
            data={"settings": settings, "raw_output": output},
        )

    # hub config set <path> <value>
    if config_sub == "set":
        path = getattr(args, "path", None)
        value_str = getattr(args, "value", None)

        if not path or value_str is None:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary="Usage: cihub hub config set <path> <value>",
                problems=[{"severity": "error", "message": "Missing path or value", "code": "CIHUB-HUB-USAGE"}],
            )

        # Validate path exists
        current = _get_nested(settings, path)
        if current is None:
            valid_paths = [
                "execution.skip_mutation",
                "execution.write_github_summary",
                "execution.include_details",
                "debug.enabled",
                "debug.verbose",
                "debug.debug_context",
                "debug.emit_triage",
                "security.harden_runner.policy",
            ]
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=f"Unknown path: {path}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Unknown path: {path}. Valid paths: {', '.join(valid_paths)}",
                        "code": "CIHUB-HUB-INVALID-PATH",
                    }
                ],
            )

        value = _parse_value(value_str)
        _set_nested(settings, path, value)
        _save_hub_settings(settings)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Set {path} = {value}",
            data={"path": path, "value": value},
        )

    # hub config load
    if config_sub == "load":
        github_output = getattr(args, "github_output", False)

        # Apply CLI overrides (non-empty values take precedence over config)
        overrides = [
            ("override_skip_mutation", "execution.skip_mutation"),
            ("override_write_summary", "execution.write_github_summary"),
            ("override_include_details", "execution.include_details"),
            ("override_debug", "debug.enabled"),
            ("override_verbose", "debug.verbose"),
            ("override_debug_context", "debug.debug_context"),
            ("override_emit_triage", "debug.emit_triage"),
            ("override_harden_runner_policy", "security.harden_runner.policy"),
        ]
        for arg_name, setting_path in overrides:
            value_str = getattr(args, arg_name, "")
            if value_str:  # Non-empty means override
                _set_nested(settings, setting_path, _parse_value(value_str))

        flat = _flatten_settings(settings)

        if github_output:
            github_output_file = os.environ.get("GITHUB_OUTPUT")
            if github_output_file:
                with open(github_output_file, "a") as f:
                    for key, value in flat.items():
                        # Convert booleans to lowercase strings for GitHub Actions
                        if isinstance(value, bool):
                            value = str(value).lower()
                        f.write(f"{key}={value}\n")
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary=f"Wrote {len(flat)} settings to GITHUB_OUTPUT",
                    data={"settings": flat},
                )
            else:
                # Emit key=value output for local testing
                lines: list[str] = []
                for key, value in flat.items():
                    if isinstance(value, bool):
                        value = str(value).lower()
                    lines.append(f"{key}={value}")
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary="Hub settings (GITHUB_OUTPUT format)",
                    data={"settings": flat, "raw_output": "\n".join(lines)},
                )
        else:
            output = yaml.dump(settings, default_flow_style=False, sort_keys=False)
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Hub settings loaded",
                data={"settings": settings, "raw_output": output},
            )

    return CommandResult(
        exit_code=EXIT_USAGE,
        summary=f"Unknown subcommand: {config_sub}",
        problems=[{"severity": "error", "message": f"Unknown subcommand: {config_sub}", "code": "CIHUB-HUB-UNKNOWN"}],
    )
