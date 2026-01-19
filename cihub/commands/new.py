"""New command handler (hub-side config creation)."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from cihub.config.inputs import ConfigInputError, load_config_override
from cihub.config.io import (
    ConfigParseError,
    ensure_dirs,
    load_defaults,
    load_profile_strict,
    save_yaml_file,
)
from cihub.config.merge import deep_merge
from cihub.config.paths import PathConfig
from cihub.exit_codes import (
    EXIT_FAILURE,
    EXIT_INTERRUPTED,
    EXIT_SUCCESS,
    EXIT_USAGE,
)
from cihub.services.templates import build_repo_config
from cihub.types import CommandResult
from cihub.utils.paths import hub_root, validate_subdir
from cihub.wizard import HAS_WIZARD, WizardCancelled


def _apply_repo_defaults(config: dict, defaults: dict) -> dict:
    repo_defaults = defaults.get("repo", {}) if isinstance(defaults, dict) else {}
    repo_block = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    for key in ("use_central_runner", "repo_side_execution"):
        if key in repo_defaults and key not in repo_block:
            repo_block[key] = repo_defaults[key]
    config["repo"] = repo_block
    return config


def _validate_profile_language(profile_cfg: dict, language: str) -> None:
    if not profile_cfg:
        return
    has_java = "java" in profile_cfg
    has_python = "python" in profile_cfg
    if has_java and language != "java":
        raise ValueError("Profile is Java-only; use --language java")
    if has_python and language != "python":
        raise ValueError("Profile is Python-only; use --language python")


def cmd_new(args: argparse.Namespace) -> CommandResult:
    """Create a new repo config file on the hub side.

    Always returns CommandResult for consistent output handling.
    """
    paths = PathConfig(str(hub_root()))
    ensure_dirs(paths)

    if getattr(args, "json", False) and args.interactive:
        message = "--interactive is not supported with --json"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message}],
        )

    name = args.name
    repo_file = Path(paths.repo_file(name))
    if repo_file.exists():
        message = f"Config already exists: {repo_file}"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-NEW-EXISTS"}],
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
            problems=[{"severity": "error", "message": message, "code": "CIHUB-NEW-CONFIG-INPUT"}],
        )

    if args.interactive:
        if config_override:
            message = "--config-json/--config-file is not supported with --interactive"
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=message,
                problems=[{"severity": "error", "message": message, "code": "CIHUB-NEW-CONFIG-INTERACTIVE"}],
            )
        if not HAS_WIZARD:
            message = "Install wizard deps: pip install cihub[wizard]"
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message, "code": "CIHUB-NEW-NO-WIZARD"}],
            )
        from rich.console import Console  # noqa: I001

        from cihub.wizard.core import WizardRunner  # noqa: I001

        runner = WizardRunner(Console(), paths)
        try:
            # Pass tier from CLI args if provided (wizard will skip tier prompt)
            cli_tier = getattr(args, "tier", None)
            wizard_result = runner.run_new_wizard(name, profile=args.profile, tier=cli_tier)
            config = wizard_result.config
            tier = wizard_result.tier
        except WizardCancelled:
            return CommandResult(
                exit_code=EXIT_INTERRUPTED,
                summary="Cancelled",
            )
        except FileNotFoundError as exc:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=str(exc),
                problems=[{"severity": "error", "message": str(exc), "code": "CIHUB-NEW-NOT-FOUND"}],
            )

        # Use wizard's repo name (may differ from CLI arg if user edited it)
        if wizard_result.repo_name and wizard_result.repo_name != name:
            name = wizard_result.repo_name
            repo_file = Path(paths.repo_file(name))
    else:
        if config_override:
            # If owner/language provided, build base config and merge overrides.
            if args.owner and args.language:
                subdir = validate_subdir(args.subdir or "")
                base = build_repo_config(
                    args.language,
                    args.owner,
                    name,
                    args.branch or "main",
                    subdir=subdir,
                )
                base = _apply_repo_defaults(base, defaults)
                config = deep_merge(base, config_override)
            else:
                config = _apply_repo_defaults(config_override, defaults)

            if args.profile:
                profile_language = None
                if isinstance(config.get("language"), str):
                    profile_language = config.get("language")
                profile_language = profile_language or args.language
                if not profile_language:
                    message = "--profile requires --language or config.language"
                    return CommandResult(
                        exit_code=EXIT_USAGE,
                        summary=message,
                        problems=[{"severity": "error", "message": message, "code": "CIHUB-NEW-PROFILE-NO-LANGUAGE"}],
                    )
                try:
                    profile_cfg = load_profile_strict(paths, args.profile)
                except FileNotFoundError as exc:
                    return CommandResult(
                        exit_code=EXIT_USAGE,
                        summary=str(exc),
                        problems=[{"severity": "error", "message": str(exc), "code": "CIHUB-NEW-PROFILE-NOT-FOUND"}],
                    )
                except ConfigParseError as exc:
                    return CommandResult(
                        exit_code=EXIT_FAILURE,
                        summary=f"Invalid YAML in profile: {args.profile}",
                        problems=[{"severity": "error", "message": str(exc), "code": "CIHUB-NEW-PROFILE-INVALID-YAML"}],
                    )
                _validate_profile_language(profile_cfg, profile_language)
                config = deep_merge(config, profile_cfg)
        else:
            if not args.owner or not args.language:
                message = "--owner and --language are required unless --interactive is set"
                return CommandResult(
                    exit_code=EXIT_USAGE,
                    summary=message,
                    problems=[{"severity": "error", "message": message, "code": "CIHUB-NEW-MISSING-ARGS"}],
                )
            # Validate subdir to prevent path traversal
            subdir = validate_subdir(args.subdir or "")
            config = build_repo_config(
                args.language,
                args.owner,
                name,
                args.branch or "main",
                subdir=subdir,
            )
            config = _apply_repo_defaults(config, defaults)
            if args.profile:
                try:
                    profile_cfg = load_profile_strict(paths, args.profile)
                except FileNotFoundError as exc:
                    return CommandResult(
                        exit_code=EXIT_USAGE,
                        summary=str(exc),
                        problems=[{"severity": "error", "message": str(exc), "code": "CIHUB-NEW-PROFILE-NOT-FOUND"}],
                    )
                except ConfigParseError as exc:
                    return CommandResult(
                        exit_code=EXIT_FAILURE,
                        summary=f"Invalid YAML in profile: {args.profile}",
                        problems=[{"severity": "error", "message": str(exc), "code": "CIHUB-NEW-PROFILE-INVALID-YAML"}],
                    )
                _validate_profile_language(profile_cfg, args.language)
                config = deep_merge(config, profile_cfg)
        # Get tier from args for non-interactive mode (interactive mode gets it from wizard)
        tier = getattr(args, "tier", None) or "standard"

    # Handle --use-registry for both interactive and non-interactive modes
    use_registry = getattr(args, "use_registry", False)
    if use_registry:
        from cihub.services.configuration import create_repo_via_registry

        # In non-interactive mode, get tier from args; in interactive, already set
        if not args.interactive:
            tier = getattr(args, "tier", None) or "standard"

        # Require --yes for non-interactive, non-dry-run writes (same as direct path)
        if not args.dry_run and not args.yes and not args.interactive:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary="Confirmation required; re-run with --yes",
                data={"config": config, "tier": tier},
            )

        result = create_repo_via_registry(
            name,
            config,
            tier=tier,
            sync=True,
            dry_run=args.dry_run,
        )
        if not result.success:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=result.errors[0] if result.errors else "Failed to create repo",
                problems=[
                    {"severity": "error", "message": e, "code": "CIHUB-NEW-REGISTRY-ERROR"} for e in result.errors
                ],
            )
        if args.dry_run:
            summary = f"Dry run: would create repo via registry: {name}"
        else:
            summary = f"Created repo via registry: {name}"
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=summary,
            data={
                "config": config,
                "tier": tier,
                "registry_entry": result.registry_entry,
            },
            files_generated=[result.config_file_path] if result.synced else [],
        )

    # Standard path: write config file directly
    payload = yaml.safe_dump(config, sort_keys=False, default_flow_style=False)
    if args.dry_run:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Dry run complete: would create {repo_file}",
            data={"config": config, "raw_output": payload},
            files_generated=[str(repo_file)],
        )

    if not args.yes:
        # In non-JSON mode, require --yes flag for non-interactive confirmation
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Confirmation required; re-run with --yes",
            data={"config": config, "file": str(repo_file)},
        )

    save_yaml_file(repo_file, config, dry_run=False)
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Created {repo_file}",
        data={"config": config},
        files_generated=[str(repo_file)],
    )
