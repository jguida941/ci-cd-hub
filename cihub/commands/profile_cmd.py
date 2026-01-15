"""Profile command implementation for CI profile management."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from cihub.exit_codes import EXIT_FAILURE, EXIT_INTERRUPTED, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.paths import hub_root
from cihub.utils.validation import validate_profile_name as _validate_profile_name


def _get_profiles_dir() -> Path:
    """Get the profiles directory (templates/profiles)."""
    root = hub_root()
    return root / "templates" / "profiles"


def _list_profiles(profiles_dir: Path) -> list[dict[str, Any]]:
    """List all profiles from the profiles directory.

    Returns a list of profile metadata dicts with keys:
        - name: Profile name (without .yaml extension)
        - path: Full path to profile file
        - type: 'language' or 'tier'
        - language: 'python', 'java', or None (for tier profiles)
    """
    profiles: list[dict[str, str | None]] = []
    if not profiles_dir.exists():
        return profiles

    for path in profiles_dir.glob("*.yaml"):
        name = path.stem
        profile_type = "tier" if name.startswith("tier-") else "language"

        # Determine language from prefix
        language = None
        if name.startswith("python-"):
            language = "python"
        elif name.startswith("java-"):
            language = "java"

        profiles.append(
            {
                "name": name,
                "path": str(path),
                "type": profile_type,
                "language": language,
            }
        )

    return sorted(profiles, key=lambda p: p["name"])


def _load_profile(profiles_dir: Path, name: str) -> dict[str, Any] | None:
    """Load a profile by name.

    Args:
        profiles_dir: Path to profiles directory
        name: Profile name (without .yaml extension)

    Returns:
        Profile content as dict, or None if not found

    Raises:
        yaml.YAMLError: If the profile file contains invalid YAML
    """
    profile_path = profiles_dir / f"{name}.yaml"
    if not profile_path.exists():
        return None

    with open(profile_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _yaml_error_result(name: str, error: yaml.YAMLError) -> CommandResult:
    """Create a CommandResult for YAML parse errors."""
    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=f"Invalid YAML in profile '{name}'",
        problems=[
            {
                "severity": "error",
                "message": f"YAML parse error: {error}",
                "code": "CIHUB-PROFILE-INVALID-YAML",
            }
        ],
    )


def _save_profile(profiles_dir: Path, name: str, content: dict[str, Any]) -> Path:
    """Save a profile.

    Args:
        profiles_dir: Path to profiles directory
        name: Profile name (without .yaml extension)
        content: Profile content to save

    Returns:
        Path to saved profile
    """
    profile_path = profiles_dir / f"{name}.yaml"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False)

    return profile_path


def cmd_profile(args: argparse.Namespace) -> CommandResult:
    """Dispatch profile subcommands."""
    subcommand: str | None = getattr(args, "subcommand", None)

    handlers = {
        "list": _cmd_list,
        "show": _cmd_show,
        "create": _cmd_create,
        "edit": _cmd_edit,
        "delete": _cmd_delete,
        "export": _cmd_export,
        "import": _cmd_import,
        "validate": _cmd_validate,
    }

    handler = handlers.get(subcommand or "")
    if handler is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown profile subcommand: {subcommand}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Unknown subcommand '{subcommand}'",
                    "code": "CIHUB-PROFILE-UNKNOWN-SUBCOMMAND",
                }
            ],
        )

    return handler(args)


def _cmd_list(args: argparse.Namespace) -> CommandResult:
    """List available profiles."""
    profiles_dir = _get_profiles_dir()
    profiles = _list_profiles(profiles_dir)

    # Apply filters
    language_filter = getattr(args, "language", None)
    type_filter = getattr(args, "type", None)

    if language_filter:
        profiles = [p for p in profiles if p["language"] == language_filter]
    if type_filter:
        profiles = [p for p in profiles if p["type"] == type_filter]

    if not profiles:
        filter_desc = []
        if language_filter:
            filter_desc.append(f"language={language_filter}")
        if type_filter:
            filter_desc.append(f"type={type_filter}")
        filter_str = f" (filters: {', '.join(filter_desc)})" if filter_desc else ""
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"No profiles found{filter_str}",
            data={"profiles": []},
        )

    # Group by type for summary
    language_profiles = [p for p in profiles if p["type"] == "language"]
    tier_profiles = [p for p in profiles if p["type"] == "tier"]

    # Build summary for non-JSON output
    summary_parts = []
    if language_profiles:
        summary_parts.append(f"{len(language_profiles)} language profile(s)")
    if tier_profiles:
        summary_parts.append(f"{len(tier_profiles)} tier profile(s)")
    summary = f"Found {', '.join(summary_parts)}"

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data={"profiles": profiles, "count": len(profiles)},
    )


def _cmd_show(args: argparse.Namespace) -> CommandResult:
    """Show profile details."""
    name = args.name
    effective = getattr(args, "effective", False)

    # Validate profile name
    validation_error = _validate_profile_name(name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-PROFILE-INVALID-NAME",
                }
            ],
        )

    profiles_dir = _get_profiles_dir()
    try:
        profile = _load_profile(profiles_dir, name)
    except yaml.YAMLError as e:
        return _yaml_error_result(name, e)
    if profile is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{name}' does not exist in {profiles_dir}",
                    "code": "CIHUB-PROFILE-NOT-FOUND",
                }
            ],
        )

    if effective:
        # Load defaults and merge
        from cihub.config.io import load_defaults
        from cihub.config.paths import PathConfig

        paths = PathConfig(root=str(hub_root()))
        defaults = load_defaults(paths)
        # Merge profile on top of defaults
        merged = _deep_merge(defaults, profile)
        display_profile = merged
        summary = f"Effective config for profile '{name}'"
    else:
        display_profile = profile
        summary = f"Profile '{name}'"

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data={"name": name, "profile": display_profile, "effective": effective},
    )


def _cmd_create(args: argparse.Namespace) -> CommandResult:
    """Create a new profile."""
    name = args.name
    language = getattr(args, "language", None)
    from_profile = getattr(args, "from_profile", None)
    from_repo = getattr(args, "from_repo", None)
    description = getattr(args, "description", None)
    force = getattr(args, "force", False)

    # Validate profile name
    validation_error = _validate_profile_name(name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-PROFILE-INVALID-NAME",
                }
            ],
        )

    # Validate source profile name if copying
    if from_profile:
        validation_error = _validate_profile_name(from_profile)
        if validation_error:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Invalid source profile name: {validation_error}",
                problems=[
                    {
                        "severity": "error",
                        "message": validation_error,
                        "code": "CIHUB-PROFILE-INVALID-NAME",
                    }
                ],
            )

    profiles_dir = _get_profiles_dir()

    # Check if profile already exists
    try:
        existing = _load_profile(profiles_dir, name)
    except yaml.YAMLError as e:
        return _yaml_error_result(name, e)
    if existing and not force:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{name}' already exists (use --force to overwrite)",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{name}' already exists",
                    "code": "CIHUB-PROFILE-EXISTS",
                }
            ],
        )

    # Build profile content
    content: dict[str, Any] = {}

    if from_profile:
        # Copy from existing profile
        try:
            source = _load_profile(profiles_dir, from_profile)
        except yaml.YAMLError as e:
            return _yaml_error_result(from_profile, e)
        if source is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Source profile '{from_profile}' not found",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Cannot copy from non-existent profile '{from_profile}'",
                        "code": "CIHUB-PROFILE-SOURCE-NOT-FOUND",
                    }
                ],
            )
        content = source.copy()
    elif from_repo:
        # Extract from repo config
        from cihub.services.registry_service import get_repo_config, load_registry

        registry = load_registry()
        repo_config = get_repo_config(registry, from_repo)
        if repo_config is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Repository '{from_repo}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Cannot extract profile from non-existent repo '{from_repo}'",
                        "code": "CIHUB-PROFILE-REPO-NOT-FOUND",
                    }
                ],
            )
        # Extract tool configuration from repo
        config = repo_config.get("config", {})
        if language:
            if language in config:
                content = {language: config[language]}
        else:
            # Try to detect language from config
            for lang in ["python", "java"]:
                if lang in config:
                    content = {lang: config[lang]}
                    language = lang
                    break
    else:
        # Create empty profile
        if language:
            content = {language: {"tools": {}}}
        else:
            content = {}

    # Add description as comment (in the header)
    if description:
        content["_description"] = description

    # Save the profile
    path = _save_profile(profiles_dir, name, content)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Created profile '{name}'",
        data={"name": name, "path": str(path), "content": content},
        files_modified=[str(path)],
    )


def _cmd_edit(args: argparse.Namespace) -> CommandResult:
    """Edit an existing profile."""
    name = args.name
    wizard = getattr(args, "wizard", False)
    enable = getattr(args, "enable", None) or []
    disable = getattr(args, "disable", None) or []
    settings = getattr(args, "settings", None) or []

    # Reject --json with --wizard (interactive mode corrupts JSON output)
    if getattr(args, "json", False) and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "--wizard is not supported with --json",
                    "code": "CIHUB-PROFILE-WIZARD-JSON",
                }
            ],
        )

    # Validate profile name
    validation_error = _validate_profile_name(name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-PROFILE-INVALID-NAME",
                }
            ],
        )

    profiles_dir = _get_profiles_dir()
    try:
        profile = _load_profile(profiles_dir, name)
    except yaml.YAMLError as e:
        return _yaml_error_result(name, e)

    if profile is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{name}' does not exist",
                    "code": "CIHUB-PROFILE-NOT-FOUND",
                }
            ],
        )

    if wizard:
        # Check for wizard dependencies
        try:
            import questionary
            from rich.console import Console

            from cihub.wizard.questions.java_tools import configure_java_tools
            from cihub.wizard.questions.python_tools import configure_python_tools
            from cihub.wizard.styles import get_style
        except ImportError:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Wizard dependencies not installed",
                problems=[
                    {
                        "severity": "error",
                        "message": "Install wizard deps: pip install cihub[wizard]",
                        "code": "CIHUB-PROFILE-NO-WIZARD-DEPS",
                    }
                ],
            )

        # Detect language from profile name or content
        language = None
        if name.startswith("python-"):
            language = "python"
        elif name.startswith("java-"):
            language = "java"
        elif "python" in profile:
            language = "python"
        elif "java" in profile:
            language = "java"
        else:
            # Ask user to select language
            language = questionary.select(
                "Select language for this profile:",
                choices=["python", "java"],
                style=get_style(),
            ).ask()
            if language is None:
                return CommandResult(
                    exit_code=EXIT_INTERRUPTED,
                    summary="Cancelled",
                )

        console = Console()
        console.print(f"\n[bold]Editing profile: {name}[/bold] (language: {language})\n")

        # Ensure language section exists
        if language not in profile:
            profile[language] = {}
        if "tools" not in profile[language]:
            profile[language]["tools"] = {}

        # Configure tools interactively
        try:
            from cihub.wizard import WizardCancelled

            if language == "python":
                profile[language]["tools"] = configure_python_tools(profile)
            else:
                profile[language]["tools"] = configure_java_tools(profile)
        except WizardCancelled:
            return CommandResult(
                exit_code=EXIT_INTERRUPTED,
                summary="Cancelled",
            )

        # Save updated profile
        profile_path = profiles_dir / f"{name}.yaml"
        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(profile, f, sort_keys=False, default_flow_style=False)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Updated profile '{name}' via wizard",
            data={"profile": profile},
            files_modified=[str(profile_path)],
        )

    changes = []

    # Detect language from profile name or content
    language = None
    if name.startswith("python-"):
        language = "python"
    elif name.startswith("java-"):
        language = "java"
    elif "python" in profile:
        language = "python"
    elif "java" in profile:
        language = "java"

    if not language and (enable or disable or settings):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Cannot determine language for profile",
            problems=[
                {
                    "severity": "error",
                    "message": "Profile must have a language prefix (python-* or java-*) or language section",
                    "code": "CIHUB-PROFILE-NO-LANGUAGE",
                }
            ],
        )

    if language:
        # Ensure language section exists
        if language not in profile:
            profile[language] = {}
        if "tools" not in profile[language]:
            profile[language]["tools"] = {}

        tools = profile[language]["tools"]

        # Enable tools
        for tool in enable:
            if tool not in tools:
                tools[tool] = {"enabled": True}
            elif isinstance(tools[tool], dict):
                tools[tool]["enabled"] = True
            else:
                tools[tool] = {"enabled": True}
            changes.append(f"enabled {tool}")

        # Disable tools
        for tool in disable:
            if tool not in tools:
                tools[tool] = {"enabled": False}
            elif isinstance(tools[tool], dict):
                tools[tool]["enabled"] = False
            else:
                tools[tool] = {"enabled": False}
            changes.append(f"disabled {tool}")

        # Set settings
        for key, value in settings:
            parts = key.split(".")
            if len(parts) == 2:
                tool_name, setting = parts
                if tool_name not in tools:
                    tools[tool_name] = {}
                elif not isinstance(tools[tool_name], dict):
                    tools[tool_name] = {"enabled": True}

                # Try to parse value as int/float/bool
                try:
                    if value.lower() in ("true", "false"):
                        parsed_value = value.lower() == "true"
                    elif "." in value:
                        parsed_value = float(value)
                    else:
                        parsed_value = int(value)
                except ValueError:
                    parsed_value = value

                tools[tool_name][setting] = parsed_value
                changes.append(f"set {key}={value}")
            else:
                changes.append(f"skipped invalid key '{key}'")

    if not changes:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"No changes made to profile '{name}'",
            data={"name": name, "changes": []},
        )

    # Save updated profile
    path = _save_profile(profiles_dir, name, profile)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Updated profile '{name}' ({len(changes)} change(s))",
        data={"name": name, "changes": changes, "path": str(path)},
        files_modified=[str(path)],
    )


def _cmd_delete(args: argparse.Namespace) -> CommandResult:
    """Delete a profile."""
    name = args.name
    force = getattr(args, "force", False)

    # Validate profile name
    validation_error = _validate_profile_name(name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-PROFILE-INVALID-NAME",
                }
            ],
        )

    profiles_dir = _get_profiles_dir()
    profile_path = profiles_dir / f"{name}.yaml"

    if not profile_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{name}' does not exist",
                    "code": "CIHUB-PROFILE-NOT-FOUND",
                }
            ],
        )

    # Check if it's a built-in profile (protection against accidental deletion)
    builtin_profiles = [
        "python-fast",
        "python-quality",
        "python-security",
        "python-minimal",
        "python-compliance",
        "python-coverage-gate",
        "java-fast",
        "java-quality",
        "java-security",
        "java-minimal",
        "java-compliance",
        "java-coverage-gate",
        "tier-strict",
        "tier-relaxed",
    ]

    if name in builtin_profiles and not force:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Cannot delete built-in profile '{name}' without --force",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{name}' is a built-in profile. Use --force to delete.",
                    "code": "CIHUB-PROFILE-BUILTIN",
                }
            ],
        )

    # Delete the profile
    profile_path.unlink()

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Deleted profile '{name}'",
        data={"name": name, "path": str(profile_path)},
        files_modified=[str(profile_path)],
    )


def _cmd_export(args: argparse.Namespace) -> CommandResult:
    """Export a profile to a file."""
    name = args.name
    output = Path(args.output)

    # Validate profile name
    validation_error = _validate_profile_name(name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-PROFILE-INVALID-NAME",
                }
            ],
        )

    profiles_dir = _get_profiles_dir()
    try:
        profile = _load_profile(profiles_dir, name)
    except yaml.YAMLError as e:
        return _yaml_error_result(name, e)

    if profile is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{name}' does not exist",
                    "code": "CIHUB-PROFILE-NOT-FOUND",
                }
            ],
        )

    # Write to output file
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        yaml.dump(profile, f, default_flow_style=False, sort_keys=False)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Exported profile '{name}' to {output}",
        data={"name": name, "output": str(output), "profile": profile},
        files_modified=[str(output)],
    )


def _cmd_import(args: argparse.Namespace) -> CommandResult:
    """Import a profile from a file."""
    input_file = Path(args.file)
    name = getattr(args, "name", None)
    force = getattr(args, "force", False)

    # Validate profile name if provided
    if name:
        validation_error = _validate_profile_name(name)
        if validation_error:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Invalid profile name: {validation_error}",
                problems=[
                    {
                        "severity": "error",
                        "message": validation_error,
                        "code": "CIHUB-PROFILE-INVALID-NAME",
                    }
                ],
            )

    if not input_file.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Input file '{input_file}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"File '{input_file}' does not exist",
                    "code": "CIHUB-PROFILE-FILE-NOT-FOUND",
                }
            ],
        )

    # Load the input file
    try:
        with open(input_file, encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid YAML in '{input_file}'",
            problems=[
                {
                    "severity": "error",
                    "message": f"YAML parse error: {exc}",
                    "code": "CIHUB-PROFILE-INVALID-YAML",
                }
            ],
        )

    # Determine profile name
    if name is None:
        name = input_file.stem
        # Validate the derived name from filename
        validation_error = _validate_profile_name(name)
        if validation_error:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Invalid profile name derived from filename: {validation_error}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Filename '{input_file.name}' produces invalid profile name: {validation_error}",
                        "code": "CIHUB-PROFILE-INVALID-NAME",
                    }
                ],
            )

    profiles_dir = _get_profiles_dir()

    # Check if profile already exists
    try:
        existing = _load_profile(profiles_dir, name)
    except yaml.YAMLError as e:
        return _yaml_error_result(name, e)
    if existing and not force:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{name}' already exists (use --force to overwrite)",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{name}' already exists",
                    "code": "CIHUB-PROFILE-EXISTS",
                }
            ],
        )

    # Save the profile
    path = _save_profile(profiles_dir, name, content)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Imported profile '{name}' from {input_file}",
        data={"name": name, "path": str(path), "source": str(input_file)},
        files_modified=[str(path)],
    )


def _cmd_validate(args: argparse.Namespace) -> CommandResult:
    """Validate a profile."""
    name = args.name
    strict = getattr(args, "strict", False)

    # Validate profile name
    validation_error = _validate_profile_name(name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-PROFILE-INVALID-NAME",
                }
            ],
        )

    profiles_dir = _get_profiles_dir()
    try:
        profile = _load_profile(profiles_dir, name)
    except yaml.YAMLError as e:
        return _yaml_error_result(name, e)

    if profile is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{name}' does not exist",
                    "code": "CIHUB-PROFILE-NOT-FOUND",
                }
            ],
        )

    problems: list[dict[str, Any]] = []
    warnings: list[str] = []

    # Check for valid language sections
    valid_languages = {"python", "java"}
    found_languages = set()

    for key in profile:
        if key.startswith("_"):
            continue  # Skip metadata keys like _description
        if key in valid_languages:
            found_languages.add(key)
        elif key not in ("thresholds", "gates", "reports", "notifications"):
            warnings.append(f"Unknown top-level key: {key}")

    if not found_languages:
        problems.append(
            {
                "severity": "warning" if not strict else "error",
                "message": "Profile has no language section (python or java)",
                "code": "CIHUB-PROFILE-NO-LANGUAGE",
            }
        )

    # Validate tool names
    from cihub.tools.registry import JAVA_TOOLS, PYTHON_TOOLS

    for lang in found_languages:
        tools = profile.get(lang, {}).get("tools", {})
        known_tools = PYTHON_TOOLS if lang == "python" else JAVA_TOOLS

        for tool_name in tools:
            if tool_name not in known_tools:
                msg = f"Unknown {lang} tool: {tool_name}"
                if strict:
                    problems.append(
                        {
                            "severity": "error",
                            "message": msg,
                            "code": "CIHUB-PROFILE-UNKNOWN-TOOL",
                        }
                    )
                else:
                    warnings.append(msg)

    # Add warnings to problems list
    if warnings:
        for w in warnings:
            problems.append({"severity": "warning", "message": w, "code": "CIHUB-PROFILE-VALIDATION"})

    # In strict mode, warnings also count as errors
    has_errors = any(p["severity"] == "error" for p in problems)
    has_warnings = any(p["severity"] == "warning" for p in problems)
    fail_on_warnings = strict and has_warnings

    exit_code = EXIT_FAILURE if (has_errors or fail_on_warnings) else EXIT_SUCCESS

    summary_parts = []
    error_count = sum(1 for p in problems if p["severity"] == "error")
    warning_count = sum(1 for p in problems if p["severity"] == "warning")
    if error_count:
        summary_parts.append(f"{error_count} error(s)")
    if warning_count:
        summary_parts.append(f"{warning_count} warning(s)")
        if strict:
            summary_parts.append("(strict mode: warnings fail)")
    if not summary_parts:
        summary_parts.append("valid")

    return CommandResult(
        exit_code=exit_code,
        summary=f"Profile '{name}': {', '.join(summary_parts)}",
        data={"name": name, "valid": exit_code == EXIT_SUCCESS, "warnings": warnings},
        problems=problems if problems else [],
    )


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dicts, overlay values take precedence."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
