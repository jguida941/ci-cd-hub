"""Threshold command implementation for CI threshold management."""

from __future__ import annotations

import argparse
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult

# Threshold metadata: category, description, type
THRESHOLD_METADATA: dict[str, dict[str, Any]] = {
    # Coverage & Mutation
    "coverage_min": {
        "category": "coverage",
        "description": "Minimum code coverage percentage",
        "type": "int",
        "default": 70,
        "unit": "%",
    },
    "mutation_score_min": {
        "category": "mutation",
        "description": "Minimum mutation score percentage",
        "type": "int",
        "default": 70,
        "unit": "%",
    },
    # Security Vulnerabilities
    "max_critical_vulns": {
        "category": "security",
        "description": "Maximum allowed critical vulnerabilities",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    "max_high_vulns": {
        "category": "security",
        "description": "Maximum allowed high vulnerabilities",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    "max_pip_audit_vulns": {
        "category": "security",
        "description": "Maximum allowed pip-audit vulnerabilities",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    # CVSS Thresholds
    "owasp_cvss_fail": {
        "category": "security",
        "description": "CVSS score threshold for OWASP dependency check",
        "type": "float",
        "default": 7.0,
        "unit": "score",
    },
    "trivy_cvss_fail": {
        "category": "security",
        "description": "CVSS score threshold for Trivy scanner",
        "type": "float",
        "default": 7.0,
        "unit": "score",
    },
    # SAST Findings
    "max_semgrep_findings": {
        "category": "security",
        "description": "Maximum allowed Semgrep findings",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    # Python Linting
    "max_ruff_errors": {
        "category": "lint",
        "description": "Maximum allowed Ruff lint errors",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    "max_black_issues": {
        "category": "lint",
        "description": "Maximum allowed Black formatting issues",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    "max_isort_issues": {
        "category": "lint",
        "description": "Maximum allowed isort import order issues",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    # Java Linting/Static Analysis
    "max_checkstyle_errors": {
        "category": "lint",
        "description": "Maximum allowed Checkstyle errors",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    "max_spotbugs_bugs": {
        "category": "security",
        "description": "Maximum allowed SpotBugs findings",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
    "max_pmd_violations": {
        "category": "lint",
        "description": "Maximum allowed PMD violations",
        "type": "int",
        "default": 0,
        "unit": "count",
    },
}

# Float threshold keys (for type coercion)
_FLOAT_THRESHOLD_KEYS: frozenset[str] = frozenset({"owasp_cvss_fail", "trivy_cvss_fail"})


def _parse_threshold_value(key: str, value: str) -> int | float | None:
    """Parse a threshold value string to the appropriate type."""
    try:
        if key in _FLOAT_THRESHOLD_KEYS:
            return float(value)
        return int(value)
    except ValueError:
        return None


def _validate_threshold_key(key: str) -> str | None:
    """Validate a threshold key. Returns error message if invalid."""
    if key not in THRESHOLD_METADATA:
        valid_keys = ", ".join(sorted(THRESHOLD_METADATA.keys()))
        return f"Unknown threshold key '{key}'. Valid keys: {valid_keys}"
    return None


def cmd_threshold(args: argparse.Namespace) -> CommandResult:
    """Dispatch threshold subcommands."""
    subcommand: str | None = getattr(args, "subcommand", None)

    handlers = {
        "get": _cmd_get,
        "set": _cmd_set,
        "list": _cmd_list,
        "reset": _cmd_reset,
        "compare": _cmd_compare,
    }

    handler = handlers.get(subcommand or "")
    if handler is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown threshold subcommand: {subcommand}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Unknown subcommand '{subcommand}'",
                    "code": "CIHUB-THRESHOLD-UNKNOWN-SUBCOMMAND",
                }
            ],
        )

    return handler(args)


def _cmd_get(args: argparse.Namespace) -> CommandResult:
    """Get threshold value(s)."""
    key = getattr(args, "key", None)
    repo = getattr(args, "repo", None)
    tier = getattr(args, "tier", None)
    effective = getattr(args, "effective", False)

    # Validate key if provided
    if key:
        error = _validate_threshold_key(key)
        if error:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=error,
                problems=[
                    {
                        "severity": "error",
                        "message": error,
                        "code": "CIHUB-THRESHOLD-INVALID-KEY",
                    }
                ],
            )

    from cihub.services.registry_service import (
        _DEFAULT_THRESHOLDS,
        get_repo_config,
        load_registry,
    )

    registry = load_registry()

    if repo:
        # Get threshold(s) for specific repo
        repo_config = get_repo_config(registry, repo)
        if repo_config is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Repository '{repo}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Repository '{repo}' not in registry",
                        "code": "CIHUB-THRESHOLD-REPO-NOT-FOUND",
                    }
                ],
            )

        effective_thresholds = repo_config.get("effective", {})
        overrides = repo_config.get("overrides", {})
        tier_name = repo_config.get("tier", "standard")

        if key:
            # Single key - show effective or raw override based on --effective flag
            if effective:
                value = effective_thresholds.get(key, _DEFAULT_THRESHOLDS.get(key))
                is_override = key in overrides
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary=f"{key}={value} (repo: {repo}, effective)",
                    data={
                        "key": key,
                        "value": value,
                        "repo": repo,
                        "tier": tier_name,
                        "is_override": is_override,
                        "default": _DEFAULT_THRESHOLDS.get(key),
                        "mode": "effective",
                    },
                )
            else:
                # Return raw override only (None if not overridden)
                value = overrides.get(key)
                if value is None:
                    return CommandResult(
                        exit_code=EXIT_SUCCESS,
                        summary=f"{key} not overridden (repo: {repo})",
                        data={
                            "key": key,
                            "value": None,
                            "repo": repo,
                            "tier": tier_name,
                            "is_override": False,
                            "default": _DEFAULT_THRESHOLDS.get(key),
                            "mode": "raw",
                        },
                    )
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary=f"{key}={value} (repo: {repo}, override)",
                    data={
                        "key": key,
                        "value": value,
                        "repo": repo,
                        "tier": tier_name,
                        "is_override": True,
                        "default": _DEFAULT_THRESHOLDS.get(key),
                        "mode": "raw",
                    },
                )
        else:
            # All thresholds for repo
            thresholds = []
            for k, default in _DEFAULT_THRESHOLDS.items():
                if effective:
                    value = effective_thresholds.get(k, default)
                else:
                    value = overrides.get(k)  # None if not overridden
                thresholds.append(
                    {
                        "key": k,
                        "value": value,
                        "is_override": k in overrides,
                        "default": default,
                        "category": THRESHOLD_METADATA.get(k, {}).get("category", "unknown"),
                    }
                )
            mode = "effective" if effective else "raw"
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Thresholds for repo '{repo}' ({len(thresholds)} keys, {mode})",
                data={
                    "repo": repo,
                    "tier": tier_name,
                    "thresholds": thresholds,
                    "mode": mode,
                },
            )

    elif tier:
        # Get threshold(s) for specific tier
        tiers = registry.get("tiers", {})
        if tier not in tiers:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Tier '{tier}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Tier '{tier}' not in registry",
                        "code": "CIHUB-THRESHOLD-TIER-NOT-FOUND",
                    }
                ],
            )

        tier_cfg = tiers[tier]
        tier_thresholds = {}

        # Load tier thresholds from profile + tier config
        profile_name = tier_cfg.get("profile")
        if profile_name:
            from cihub.config.io import load_profile
            from cihub.config.paths import PathConfig
            from cihub.utils.paths import hub_root

            paths = PathConfig(str(hub_root()))
            profile_cfg = load_profile(paths, profile_name)
            if isinstance(profile_cfg.get("thresholds"), dict):
                tier_thresholds.update(profile_cfg["thresholds"])

        tier_fragment = tier_cfg.get("config", {})
        if isinstance(tier_fragment.get("thresholds"), dict):
            tier_thresholds.update(tier_fragment["thresholds"])

        # Legacy tier-level thresholds
        for k in _DEFAULT_THRESHOLDS:
            if k in tier_cfg:
                tier_thresholds[k] = tier_cfg[k]

        if key:
            value = tier_thresholds.get(key, _DEFAULT_THRESHOLDS.get(key))
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"{key}={value} (tier: {tier})",
                data={
                    "key": key,
                    "value": value,
                    "tier": tier,
                    "is_tier_default": key not in tier_thresholds,
                    "default": _DEFAULT_THRESHOLDS.get(key),
                },
            )
        else:
            thresholds = []
            for k, default in _DEFAULT_THRESHOLDS.items():
                value = tier_thresholds.get(k, default)
                thresholds.append(
                    {
                        "key": k,
                        "value": value,
                        "is_tier_default": k not in tier_thresholds,
                        "default": default,
                        "category": THRESHOLD_METADATA.get(k, {}).get("category", "unknown"),
                    }
                )
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Thresholds for tier '{tier}' ({len(thresholds)} keys)",
                data={
                    "tier": tier,
                    "thresholds": thresholds,
                },
            )

    else:
        # Get global defaults
        if key:
            key_default: int | float | None = _DEFAULT_THRESHOLDS.get(key)
            meta = THRESHOLD_METADATA.get(key, {})
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"{key}={key_default} (global default)",
                data={
                    "key": key,
                    "value": key_default,
                    "default": key_default,
                    "category": meta.get("category"),
                    "description": meta.get("description"),
                    "type": meta.get("type"),
                },
            )
        else:
            thresholds = []
            for k, default in _DEFAULT_THRESHOLDS.items():
                meta = THRESHOLD_METADATA.get(k, {})
                thresholds.append(
                    {
                        "key": k,
                        "value": default,
                        "default": default,
                        "category": meta.get("category"),
                        "description": meta.get("description"),
                        "type": meta.get("type"),
                    }
                )
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Global defaults ({len(thresholds)} keys)",
                data={"thresholds": thresholds},
            )


def _wizard_set() -> CommandResult:
    """Interactive wizard for setting thresholds.

    Sources threshold keys from THRESHOLD_METADATA (CLI as source of truth).
    """
    try:
        import questionary

        from cihub.wizard.core import WizardCancelled, _check_cancelled
        from cihub.wizard.styles import get_style
    except ImportError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="questionary not installed (pip install questionary)",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode requires questionary",
                    "code": "CIHUB-THRESHOLD-NO-QUESTIONARY",
                }
            ],
        )

    try:
        from cihub.services.registry_service import list_repos, load_registry

        registry = load_registry()

        # Source threshold keys from THRESHOLD_METADATA
        threshold_choices = []
        for key, meta in sorted(THRESHOLD_METADATA.items()):
            label = f"{key} ({meta.get('category', 'unknown')})"
            threshold_choices.append(questionary.Choice(title=label, value=key))

        # Select threshold key
        selected_key: str = _check_cancelled(
            questionary.select(
                "Select threshold to set:",
                choices=threshold_choices,
                style=get_style(),
            ).ask(),
            "Threshold selection",
        )

        meta = THRESHOLD_METADATA[selected_key]
        default_val = meta.get("default", 0)
        value_type = meta.get("type", "int")
        unit = meta.get("unit", "")

        # Prompt for value with type-appropriate validation
        value_str: str = _check_cancelled(
            questionary.text(
                f"Enter value for {selected_key} ({value_type}, {unit}):",
                default=str(default_val),
                style=get_style(),
            ).ask(),
            "Value input",
        )

        # Validate value
        parsed_value = _parse_threshold_value(selected_key, value_str)
        if parsed_value is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Invalid value '{value_str}' (expected {value_type})",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Cannot parse '{value_str}' as {value_type}",
                        "code": "CIHUB-THRESHOLD-INVALID-VALUE",
                    }
                ],
            )

        # Select target: repo, tier, or all-repos
        repos = list_repos(registry)
        repo_names = [r.get("name", r.get("repo", "unknown")) for r in repos]
        tier_names = list(registry.get("tiers", {}).keys())

        target_choices = [
            questionary.Choice(title="Specific repository", value="repo"),
            questionary.Choice(title="Specific tier", value="tier"),
            questionary.Choice(title="All repositories", value="all_repos"),
        ]

        target: str = _check_cancelled(
            questionary.select(
                "Apply threshold to:",
                choices=target_choices,
                style=get_style(),
            ).ask(),
            "Target selection",
        )

        # Build args based on target
        args = argparse.Namespace(
            key=selected_key,
            value=value_str,
            repo=None,
            tier=None,
            all_repos=False,
        )

        if target == "repo":
            if not repo_names:
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary="No repositories in registry",
                    problems=[
                        {
                            "severity": "error",
                            "message": "Registry has no repos. Add repos first.",
                            "code": "CIHUB-THRESHOLD-NO-REPOS",
                        }
                    ],
                )
            selected_repo: str = _check_cancelled(
                questionary.select(
                    "Select repository:",
                    choices=repo_names,
                    style=get_style(),
                ).ask(),
                "Repo selection",
            )
            args.repo = selected_repo

        elif target == "tier":
            if not tier_names:
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary="No tiers in registry",
                    problems=[
                        {
                            "severity": "error",
                            "message": "Registry has no tiers defined.",
                            "code": "CIHUB-THRESHOLD-NO-TIERS",
                        }
                    ],
                )
            selected_tier: str = _check_cancelled(
                questionary.select(
                    "Select tier:",
                    choices=tier_names,
                    style=get_style(),
                ).ask(),
                "Tier selection",
            )
            args.tier = selected_tier

        else:  # all_repos
            args.all_repos = True

        # Call the actual _cmd_set with built args
        return _do_set(args)

    except WizardCancelled:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Wizard cancelled",
            data={"cancelled": True},
        )


def _wizard_reset() -> CommandResult:
    """Interactive wizard for resetting thresholds.

    Sources threshold keys from THRESHOLD_METADATA (CLI as source of truth).
    """
    try:
        import questionary

        from cihub.wizard.core import WizardCancelled, _check_cancelled
        from cihub.wizard.styles import get_style
    except ImportError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="questionary not installed (pip install questionary)",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode requires questionary",
                    "code": "CIHUB-THRESHOLD-NO-QUESTIONARY",
                }
            ],
        )

    try:
        from cihub.services.registry_service import list_repos, load_registry

        registry = load_registry()

        # Build threshold choices with option to reset all
        threshold_choices = [
            questionary.Choice(title="(All thresholds)", value="__all__"),
        ]
        for key, meta in sorted(THRESHOLD_METADATA.items()):
            label = f"{key} ({meta.get('category', 'unknown')})"
            threshold_choices.append(questionary.Choice(title=label, value=key))

        # Select threshold key(s) to reset
        selected_key: str = _check_cancelled(
            questionary.select(
                "Select threshold to reset (or reset all):",
                choices=threshold_choices,
                style=get_style(),
            ).ask(),
            "Threshold selection",
        )

        # Select target: repo, tier, or all-repos
        repos = list_repos(registry)
        repo_names = [r.get("name", r.get("repo", "unknown")) for r in repos]
        tier_names = list(registry.get("tiers", {}).keys())

        target_choices = []
        if repo_names:
            target_choices.append(questionary.Choice(title="Specific repo", value="repo"))
            target_choices.append(questionary.Choice(title="All repos", value="all_repos"))
        if tier_names:
            target_choices.append(questionary.Choice(title="Specific tier", value="tier"))

        if not target_choices:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="No repos or tiers in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": "Register repos or define tiers first",
                        "code": "CIHUB-THRESHOLD-NO-TARGETS",
                    }
                ],
            )

        target_type: str = _check_cancelled(
            questionary.select(
                "Reset for:",
                choices=target_choices,
                style=get_style(),
            ).ask(),
            "Target selection",
        )

        # Build args for _cmd_reset
        args = argparse.Namespace()
        args.key = selected_key if selected_key != "__all__" else None
        args.wizard = False  # Already processed
        args.repo = None
        args.tier = None
        args.all_repos = False

        if target_type == "repo":
            repo_name: str = _check_cancelled(
                questionary.select(
                    "Select repo:",
                    choices=repo_names,
                    style=get_style(),
                ).ask(),
                "Repo selection",
            )
            args.repo = repo_name
        elif target_type == "tier":
            tier_name: str = _check_cancelled(
                questionary.select(
                    "Select tier:",
                    choices=tier_names,
                    style=get_style(),
                ).ask(),
                "Tier selection",
            )
            args.tier = tier_name
        else:  # all_repos
            args.all_repos = True

        # Call actual reset with built args
        return _do_reset(args)

    except WizardCancelled:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Wizard cancelled",
            data={"cancelled": True},
        )


def _cmd_set(args: argparse.Namespace) -> CommandResult:
    """Set a threshold value."""
    wizard = getattr(args, "wizard", False)
    json_mode = getattr(args, "json", False)

    # JSON-purity: reject --json with --wizard
    if json_mode and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode (--wizard) cannot be used with --json output",
                    "code": "CIHUB-THRESHOLD-WIZARD-JSON",
                }
            ],
        )

    # Wizard mode
    if wizard:
        return _wizard_set()

    return _do_set(args)


def _do_set(args: argparse.Namespace) -> CommandResult:
    """Internal set implementation (shared by CLI and wizard)."""
    key = args.key
    value_str = args.value
    repo = getattr(args, "repo", None)
    tier = getattr(args, "tier", None)
    all_repos = getattr(args, "all_repos", False)

    # Check required fields
    if not key:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Threshold key required (or use --wizard)",
            problems=[
                {
                    "severity": "error",
                    "message": "Threshold key is required. Use --wizard for interactive mode.",
                    "code": "CIHUB-THRESHOLD-NO-KEY",
                }
            ],
        )

    if not value_str:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Threshold value required (or use --wizard)",
            problems=[
                {
                    "severity": "error",
                    "message": "Threshold value is required. Use --wizard for interactive mode.",
                    "code": "CIHUB-THRESHOLD-NO-VALUE",
                }
            ],
        )

    # Validate key
    error = _validate_threshold_key(key)
    if error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=error,
            problems=[
                {
                    "severity": "error",
                    "message": error,
                    "code": "CIHUB-THRESHOLD-INVALID-KEY",
                }
            ],
        )

    # Parse value
    value = _parse_threshold_value(key, value_str)
    if value is None:
        expected_type = "float" if key in _FLOAT_THRESHOLD_KEYS else "int"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid value '{value_str}' for {key} (expected {expected_type})",
            problems=[
                {
                    "severity": "error",
                    "message": f"Cannot parse '{value_str}' as {expected_type}",
                    "code": "CIHUB-THRESHOLD-INVALID-VALUE",
                }
            ],
        )

    from cihub.services.registry_service import (
        _DEFAULT_THRESHOLDS,
        _get_registry_path,
        get_repo_config,
        load_registry,
        save_registry,
    )

    registry = load_registry()

    if repo:
        # Set threshold for specific repo (as override)
        repo_config = get_repo_config(registry, repo)
        if repo_config is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Repository '{repo}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Repository '{repo}' not in registry",
                        "code": "CIHUB-THRESHOLD-REPO-NOT-FOUND",
                    }
                ],
            )

        # Check if value equals the tier/global default (what it would be without override)
        # We need to get the tier-inherited value, not the current effective (which includes override)
        # Inheritance chain: global defaults -> profile thresholds -> tier config thresholds -> legacy tier keys
        tier_name = repo_config.get("tier", "standard")
        tier_cfg = registry.get("tiers", {}).get(tier_name, {})

        # Start with global default
        inherited_default = _DEFAULT_THRESHOLDS.get(key)

        # Layer 1: Profile thresholds (if tier references a profile)
        profile_name = tier_cfg.get("profile")
        if profile_name:
            from cihub.config.io import load_profile
            from cihub.config.paths import PathConfig
            from cihub.utils.paths import hub_root

            try:
                paths = PathConfig(str(hub_root()))
                profile_cfg = load_profile(paths, profile_name)
                if isinstance(profile_cfg.get("thresholds"), dict):
                    profile_thresholds = profile_cfg["thresholds"]
                    if key in profile_thresholds:
                        inherited_default = profile_thresholds[key]
            except (FileNotFoundError, ValueError):
                pass  # Profile not found or invalid, skip

        # Layer 2: Tier config thresholds (override profile)
        tier_thresholds = tier_cfg.get("config", {}).get("thresholds", {})
        if key in tier_thresholds:
            inherited_default = tier_thresholds[key]

        # Layer 3: Legacy tier-level keys (override tier config)
        if key in tier_cfg and key in _DEFAULT_THRESHOLDS:
            inherited_default = tier_cfg[key]

        if value == inherited_default:
            # Sparse storage: don't store values that match the inherited default
            # If there's an existing override, remove it
            overrides = registry["repos"][repo].get("overrides", {})
            if key in overrides:
                del overrides[key]
                save_registry(registry)
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary=f"Removed override {key}={value} for repo '{repo}' (matches inherited default)",
                    data={"key": key, "value": value, "repo": repo, "action": "removed_override"},
                    files_modified=[str(_get_registry_path())],
                )
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"No change: {key}={value} already matches inherited default for repo '{repo}'",
                data={"key": key, "value": value, "repo": repo, "action": "no_change"},
            )

        if "overrides" not in registry["repos"][repo]:
            registry["repos"][repo]["overrides"] = {}
        registry["repos"][repo]["overrides"][key] = value

        save_registry(registry)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Set {key}={value} for repo '{repo}'",
            data={"key": key, "value": value, "repo": repo},
            files_modified=[str(_get_registry_path())],
        )

    elif tier:
        # Set threshold for tier
        tiers = registry.get("tiers", {})
        if tier not in tiers:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Tier '{tier}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Tier '{tier}' not in registry",
                        "code": "CIHUB-THRESHOLD-TIER-NOT-FOUND",
                    }
                ],
            )

        # Store in tier.config.thresholds (preferred) or legacy tier-level
        if "config" not in registry["tiers"][tier]:
            registry["tiers"][tier]["config"] = {}
        if "thresholds" not in registry["tiers"][tier]["config"]:
            registry["tiers"][tier]["config"]["thresholds"] = {}

        registry["tiers"][tier]["config"]["thresholds"][key] = value

        save_registry(registry)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Set {key}={value} for tier '{tier}'",
            data={"key": key, "value": value, "tier": tier},
            files_modified=[str(_get_registry_path())],
        )

    elif all_repos:
        # Set threshold for all repos
        repos = registry.get("repos", {})
        updated = []
        for repo_name in repos:
            if "overrides" not in registry["repos"][repo_name]:
                registry["repos"][repo_name]["overrides"] = {}
            registry["repos"][repo_name]["overrides"][key] = value
            updated.append(repo_name)

        save_registry(registry)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Set {key}={value} for {len(updated)} repo(s)",
            data={"key": key, "value": value, "repos": updated},
            files_modified=[str(_get_registry_path())],
        )

    else:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Specify --repo, --tier, or --all-repos",
            problems=[
                {
                    "severity": "error",
                    "message": "Must specify target: --repo <name>, --tier <name>, or --all-repos",
                    "code": "CIHUB-THRESHOLD-NO-TARGET",
                }
            ],
        )


def _cmd_list(args: argparse.Namespace) -> CommandResult:
    """List all threshold keys with descriptions."""
    category = getattr(args, "category", None)
    repo = getattr(args, "repo", None)
    diff_only = getattr(args, "diff", False)

    from cihub.services.registry_service import _DEFAULT_THRESHOLDS, get_repo_config, load_registry

    thresholds = []

    if repo:
        # List thresholds for specific repo with values
        registry = load_registry()
        repo_config = get_repo_config(registry, repo)
        if repo_config is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Repository '{repo}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Repository '{repo}' not in registry",
                        "code": "CIHUB-THRESHOLD-REPO-NOT-FOUND",
                    }
                ],
            )

        effective = repo_config.get("effective", {})
        overrides = repo_config.get("overrides", {})

        for key, meta in THRESHOLD_METADATA.items():
            if category and meta.get("category") != category:
                continue

            default = _DEFAULT_THRESHOLDS.get(key)
            value = effective.get(key, default)
            is_override = key in overrides
            is_different = value != default

            if diff_only and not is_different:
                continue

            thresholds.append(
                {
                    "key": key,
                    "value": value,
                    "default": default,
                    "is_override": is_override,
                    "is_different": is_different,
                    **meta,
                }
            )
    else:
        # List all threshold keys with defaults
        for key, meta in THRESHOLD_METADATA.items():
            if category and meta.get("category") != category:
                continue

            default = _DEFAULT_THRESHOLDS.get(key)
            thresholds.append(
                {
                    "key": key,
                    "value": default,
                    "default": default,
                    **meta,
                }
            )

    if not thresholds:
        filter_msg = f" (category={category})" if category else ""
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"No thresholds found{filter_msg}",
            data={"thresholds": []},
        )

    # Group by category for summary
    categories = set(t.get("category", "unknown") for t in thresholds)
    repo_suffix = f" for repo '{repo}'" if repo else ""

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"{len(thresholds)} threshold(s) in {len(categories)} category(ies){repo_suffix}",
        data={"thresholds": thresholds, "count": len(thresholds), "repo": repo},
    )


def _cmd_reset(args: argparse.Namespace) -> CommandResult:
    """Reset threshold(s) to default."""
    wizard = getattr(args, "wizard", False)
    json_mode = getattr(args, "json", False)

    # JSON-purity: reject --json with --wizard
    if json_mode and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode (--wizard) cannot be used with --json output",
                    "code": "CIHUB-THRESHOLD-WIZARD-JSON",
                }
            ],
        )

    if wizard:
        return _wizard_reset()

    return _do_reset(args)


def _do_reset(args: argparse.Namespace) -> CommandResult:
    """Actual reset implementation."""
    key = getattr(args, "key", None)
    repo = getattr(args, "repo", None)
    tier = getattr(args, "tier", None)
    all_repos = getattr(args, "all_repos", False)

    # Validate key if provided
    if key:
        error = _validate_threshold_key(key)
        if error:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=error,
                problems=[
                    {
                        "severity": "error",
                        "message": error,
                        "code": "CIHUB-THRESHOLD-INVALID-KEY",
                    }
                ],
            )

    from cihub.services.registry_service import (
        _DEFAULT_THRESHOLDS,
        _get_registry_path,
        get_repo_config,
        load_registry,
        save_registry,
    )

    registry = load_registry()

    if repo:
        # Reset threshold(s) for specific repo
        repo_config = get_repo_config(registry, repo)
        if repo_config is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Repository '{repo}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Repository '{repo}' not in registry",
                        "code": "CIHUB-THRESHOLD-REPO-NOT-FOUND",
                    }
                ],
            )

        overrides = registry["repos"][repo].get("overrides", {})
        reset_keys = []

        if key:
            if key in overrides:
                del overrides[key]
                reset_keys.append(key)
        else:
            # Reset all threshold overrides
            for k in list(overrides.keys()):
                if k in _DEFAULT_THRESHOLDS:
                    del overrides[k]
                    reset_keys.append(k)

        if not reset_keys:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"No overrides to reset for repo '{repo}'",
                data={"repo": repo, "reset": []},
            )

        save_registry(registry)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Reset {len(reset_keys)} threshold(s) for repo '{repo}'",
            data={"repo": repo, "reset": reset_keys},
            files_modified=[str(_get_registry_path())],
        )

    elif tier:
        # Reset threshold(s) for tier
        tiers = registry.get("tiers", {})
        if tier not in tiers:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Tier '{tier}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Tier '{tier}' not in registry",
                        "code": "CIHUB-THRESHOLD-TIER-NOT-FOUND",
                    }
                ],
            )

        tier_cfg = registry["tiers"][tier]
        tier_thresholds = tier_cfg.get("config", {}).get("thresholds", {})
        reset_keys = []

        if key:
            if key in tier_thresholds:
                del tier_thresholds[key]
                reset_keys.append(key)
            # Also check legacy tier-level keys
            if key in tier_cfg and key in _DEFAULT_THRESHOLDS:
                del tier_cfg[key]
                if key not in reset_keys:
                    reset_keys.append(key)
        else:
            # Reset all thresholds
            for k in list(tier_thresholds.keys()):
                del tier_thresholds[k]
                reset_keys.append(k)
            for k in list(tier_cfg.keys()):
                if k in _DEFAULT_THRESHOLDS:
                    del tier_cfg[k]
                    if k not in reset_keys:
                        reset_keys.append(k)

        if not reset_keys:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"No thresholds to reset for tier '{tier}'",
                data={"tier": tier, "reset": []},
            )

        save_registry(registry)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Reset {len(reset_keys)} threshold(s) for tier '{tier}'",
            data={"tier": tier, "reset": reset_keys},
            files_modified=[str(_get_registry_path())],
        )

    elif all_repos:
        # Reset threshold(s) for all repos
        repos = registry.get("repos", {})
        total_reset = 0
        repos_modified = []

        for repo_name in repos:
            overrides = registry["repos"][repo_name].get("overrides", {})
            reset_keys = []

            if key:
                if key in overrides:
                    del overrides[key]
                    reset_keys.append(key)
            else:
                for k in list(overrides.keys()):
                    if k in _DEFAULT_THRESHOLDS:
                        del overrides[k]
                        reset_keys.append(k)

            if reset_keys:
                total_reset += len(reset_keys)
                repos_modified.append(repo_name)

        if not repos_modified:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="No overrides to reset across repos",
                data={"repos": [], "total_reset": 0},
            )

        save_registry(registry)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Reset {total_reset} threshold(s) across {len(repos_modified)} repo(s)",
            data={"repos": repos_modified, "total_reset": total_reset},
            files_modified=[str(_get_registry_path())],
        )

    else:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Specify --repo, --tier, or --all-repos",
            problems=[
                {
                    "severity": "error",
                    "message": "Must specify target: --repo <name>, --tier <name>, or --all-repos",
                    "code": "CIHUB-THRESHOLD-NO-TARGET",
                }
            ],
        )


def _cmd_compare(args: argparse.Namespace) -> CommandResult:
    """Compare thresholds between two repos."""
    repo1 = args.repo1
    repo2 = args.repo2
    effective = getattr(args, "effective", False)

    from cihub.services.registry_service import _DEFAULT_THRESHOLDS, get_repo_config, load_registry

    registry = load_registry()

    # Get both repo configs
    config1 = get_repo_config(registry, repo1)
    if config1 is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{repo1}' not found in registry",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{repo1}' not in registry",
                    "code": "CIHUB-THRESHOLD-REPO-NOT-FOUND",
                }
            ],
        )

    config2 = get_repo_config(registry, repo2)
    if config2 is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{repo2}' not found in registry",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{repo2}' not in registry",
                    "code": "CIHUB-THRESHOLD-REPO-NOT-FOUND",
                }
            ],
        )

    # Get thresholds
    if effective:
        thresholds1 = config1.get("effective", {})
        thresholds2 = config2.get("effective", {})
    else:
        thresholds1 = config1.get("overrides", {})
        thresholds2 = config2.get("overrides", {})

    # Compare
    differences = []
    same = []

    for key in sorted(_DEFAULT_THRESHOLDS.keys()):
        default = _DEFAULT_THRESHOLDS[key]
        val1 = thresholds1.get(key, default) if effective else thresholds1.get(key)
        val2 = thresholds2.get(key, default) if effective else thresholds2.get(key)

        if val1 != val2:
            differences.append(
                {
                    "key": key,
                    "repo1_value": val1,
                    "repo2_value": val2,
                    "default": default,
                    "category": THRESHOLD_METADATA.get(key, {}).get("category"),
                }
            )
        else:
            same.append(
                {
                    "key": key,
                    "value": val1 if val1 is not None else default,
                    "default": default,
                }
            )

    comparison_type = "effective" if effective else "override"

    if not differences:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"No {comparison_type} threshold differences between '{repo1}' and '{repo2}'",
            data={
                "repo1": repo1,
                "repo2": repo2,
                "comparison_type": comparison_type,
                "differences": [],
                "same_count": len(same),
            },
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Found {len(differences)} {comparison_type} threshold difference(s) between '{repo1}' and '{repo2}'",
        data={
            "repo1": repo1,
            "repo2": repo2,
            "comparison_type": comparison_type,
            "differences": differences,
            "same_count": len(same),
        },
    )
