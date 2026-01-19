"""Config management command handler."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from cihub.config.inputs import ConfigInputError, load_config_override
from cihub.config.io import (
    ensure_dirs,
    load_defaults,
    load_repo_config,
    load_yaml_file,
    save_repo_config,
)
from cihub.config.merge import build_effective_config
from cihub.config.paths import PathConfig
from cihub.exit_codes import (
    EXIT_FAILURE,
    EXIT_INTERRUPTED,
    EXIT_SUCCESS,
    EXIT_USAGE,
)
from cihub.types import CommandResult
from cihub.utils.paths import hub_root
from cihub.wizard import HAS_WIZARD, WizardCancelled


class ConfigError(RuntimeError):
    """Config command error."""


def _load_repo(paths: PathConfig, repo: str) -> dict[str, Any]:
    repo_path = Path(paths.repo_file(repo))
    if not repo_path.exists():
        raise ConfigError(f"Repo config not found: {repo_path}")
    config = load_repo_config(paths, repo)
    if not config:
        raise ConfigError(f"Repo config is empty: {repo_path}")
    return config


def _format_config(data: dict[str, Any]) -> str:
    """Format config as YAML for display."""
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False).rstrip()


def _set_nested(config: dict[str, Any], path: str, value: Any) -> None:
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise ConfigError("Empty path")
    cursor = config
    for key in parts[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[parts[-1]] = value


def _resolve_tool_path(
    config: dict[str, Any],
    defaults: dict[str, Any],
    tool: str,
) -> str:
    language = None
    repo_block = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    if repo_block.get("language"):
        language = repo_block.get("language")
    elif config.get("language"):
        language = config.get("language")

    java_tools = defaults.get("java", {}).get("tools", {}) or {}
    python_tools = defaults.get("python", {}).get("tools", {}) or {}

    if language == "java":
        if tool not in java_tools:
            raise ConfigError(f"Unknown tool: {tool}")
        return f"java.tools.{tool}.enabled"
    if language == "python":
        if tool not in python_tools:
            raise ConfigError(f"Unknown tool: {tool}")
        return f"python.tools.{tool}.enabled"

    java_has = tool in java_tools
    python_has = tool in python_tools
    if java_has and not python_has:
        return f"java.tools.{tool}.enabled"
    if python_has and not java_has:
        return f"python.tools.{tool}.enabled"
    if java_has and python_has:
        raise ConfigError("Tool exists in both java and python; set repo.language first")
    raise ConfigError(f"Unknown tool: {tool}")


def _apply_wizard(paths: PathConfig, existing: dict[str, Any]) -> dict[str, Any]:
    if not HAS_WIZARD:
        raise ConfigError("Install wizard deps: pip install cihub[wizard]")
    from rich.console import Console  # noqa: I001

    from cihub.wizard.core import WizardRunner  # noqa: I001

    runner = WizardRunner(Console(), paths)
    wizard_result = runner.run_config_wizard(existing)
    return wizard_result.config


def cmd_config(args: argparse.Namespace) -> CommandResult:
    """Manage CI-Hub configuration.

    Always returns CommandResult for consistent output handling.
    """
    paths = PathConfig(str(hub_root()))
    ensure_dirs(paths)

    repo = args.repo
    if not repo and args.subcommand != "apply-profile":
        message = "--repo is required"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-CONFIG-NO-REPO"}],
        )

    defaults = load_defaults(paths)

    try:
        config_override = load_config_override(
            getattr(args, "config_json", None),
            getattr(args, "config_file", None),
        )
    except ConfigInputError as exc:
        message = str(exc)
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-CONFIG-INPUT"}],
        )

    try:
        if args.subcommand in (None, "edit"):
            json_mode = getattr(args, "json", False)
            if config_override:
                if args.dry_run:
                    return CommandResult(
                        exit_code=EXIT_SUCCESS,
                        summary="Dry run complete",
                        data={"raw_output": _format_config(config_override), "config": config_override},
                    )
                save_repo_config(paths, repo, config_override, dry_run=False)
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary=f"Updated {paths.repo_file(repo)}",
                    data={"config": config_override},
                    files_modified=[str(paths.repo_file(repo))],
                )

            if json_mode:
                message = "config edit is not supported with --json"
                return CommandResult(
                    exit_code=EXIT_USAGE,
                    summary=message,
                    problems=[{"severity": "error", "message": message, "code": "CIHUB-CONFIG-EDIT-JSON"}],
                )
            existing = _load_repo(paths, repo)
            try:
                updated = _apply_wizard(paths, existing)
            except WizardCancelled:
                return CommandResult(exit_code=EXIT_INTERRUPTED, summary="Cancelled")
            if args.dry_run:
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary="Dry run complete",
                    data={"raw_output": _format_config(updated), "config": updated},
                )
            save_repo_config(paths, repo, updated, dry_run=False)
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Updated {paths.repo_file(repo)}",
                files_modified=[str(paths.repo_file(repo))],
            )

        if args.subcommand == "show":
            config = _load_repo(paths, repo)
            if args.effective:
                effective = build_effective_config(defaults, None, config)
                data = effective
            else:
                data = config
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Config loaded",
                data={"raw_output": _format_config(data), "config": data},
            )

        if args.subcommand == "set":
            config = _load_repo(paths, repo)
            value = yaml.safe_load(args.value)
            _set_nested(config, args.path, value)
            if args.dry_run:
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary="Dry run complete",
                    data={"raw_output": _format_config(config), "config": config},
                )
            save_repo_config(paths, repo, config, dry_run=False)
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Updated {paths.repo_file(repo)}",
                data={"config": config},
                files_modified=[str(paths.repo_file(repo))],
            )

        if args.subcommand in {"enable", "disable"}:
            config = _load_repo(paths, repo)
            tool_path = _resolve_tool_path(config, defaults, args.tool)
            _set_nested(config, tool_path, args.subcommand == "enable")
            if args.dry_run:
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary="Dry run complete",
                    data={"raw_output": _format_config(config), "config": config},
                )
            save_repo_config(paths, repo, config, dry_run=False)
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Updated {paths.repo_file(repo)}",
                data={"config": config},
                files_modified=[str(paths.repo_file(repo))],
            )

        if args.subcommand == "apply-profile":
            from cihub.config.merge import deep_merge

            profile_path = Path(args.profile)
            if not profile_path.exists():
                raise ConfigError(f"Profile not found: {profile_path}")

            profile_data = load_yaml_file(profile_path)

            target_path = Path(args.target) if args.target else None
            if target_path:
                target_data = load_yaml_file(target_path)
                merged = deep_merge(profile_data, target_data)
                output_path = Path(args.output) if args.output else target_path

                if args.dry_run:
                    return CommandResult(
                        exit_code=EXIT_SUCCESS,
                        summary="Dry run complete",
                        data={"raw_output": _format_config(merged), "config": merged},
                    )

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w", encoding="utf-8") as handle:
                    yaml.safe_dump(merged, handle, sort_keys=False, default_flow_style=False)
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary=f"Applied {profile_path} -> {output_path}",
                    data={"config": merged},
                    files_modified=[str(output_path)],
                )

            if not repo:
                raise ConfigError("--repo or --target is required for apply-profile")

            config = _load_repo(paths, repo)
            merged = deep_merge(profile_data, config)

            if args.dry_run:
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary="Dry run complete",
                    data={"raw_output": _format_config(merged), "config": merged},
                )

            save_repo_config(paths, repo, merged, dry_run=False)
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Applied {profile_path} -> {paths.repo_file(repo)}",
                data={"config": merged},
                files_modified=[str(paths.repo_file(repo))],
            )

        raise ConfigError(f"Unsupported config command: {args.subcommand}")
    except ConfigError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=str(exc),
            problems=[
                {
                    "severity": "error",
                    "message": str(exc),
                    "code": "CIHUB-CONFIG-001",
                }
            ],
        )
