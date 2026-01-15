"""Tool command implementation for CI tool management."""

from __future__ import annotations

import argparse
import shutil
from typing import Any

import yaml

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.tools.registry import (
    JAVA_TOOLS,
    PYTHON_TOOLS,
    get_custom_tools_from_config,
    is_custom_tool,
)
from cihub.types import CommandResult
from cihub.utils.validation import validate_profile_name as _validate_profile_name

# Tool metadata: category, description, executable (if applicable)
TOOL_METADATA: dict[str, dict[str, Any]] = {
    # Python tools
    "pytest": {
        "language": "python",
        "category": "test",
        "description": "Python test runner with coverage",
        "executable": "pytest",
    },
    "ruff": {
        "language": "python",
        "category": "lint",
        "description": "Fast Python linter",
        "executable": "ruff",
    },
    "black": {
        "language": "python",
        "category": "format",
        "description": "Python code formatter",
        "executable": "black",
    },
    "isort": {
        "language": "python",
        "category": "format",
        "description": "Python import sorter",
        "executable": "isort",
    },
    "mypy": {
        "language": "python",
        "category": "lint",
        "description": "Static type checker for Python",
        "executable": "mypy",
    },
    "bandit": {
        "language": "python",
        "category": "security",
        "description": "Python security linter",
        "executable": "bandit",
    },
    "pip_audit": {
        "language": "python",
        "category": "security",
        "description": "Audit Python dependencies for vulnerabilities",
        "executable": "pip-audit",
    },
    "mutmut": {
        "language": "python",
        "category": "mutation",
        "description": "Mutation testing for Python",
        "executable": "mutmut",
    },
    "hypothesis": {
        "language": "python",
        "category": "test",
        "description": "Property-based testing for Python",
        "executable": None,  # pytest plugin
    },
    "semgrep": {
        "language": "both",
        "category": "security",
        "description": "Semantic code analysis",
        "executable": "semgrep",
    },
    "trivy": {
        "language": "both",
        "category": "security",
        "description": "Container and dependency vulnerability scanner",
        "executable": "trivy",
    },
    "codeql": {
        "language": "both",
        "category": "security",
        "description": "GitHub CodeQL analysis",
        "executable": None,  # GitHub Action
    },
    "sbom": {
        "language": "both",
        "category": "security",
        "description": "Software Bill of Materials generation",
        "executable": None,
    },
    "docker": {
        "language": "both",
        "category": "container",
        "description": "Docker container build and test",
        "executable": "docker",
    },
    # Java tools
    "jacoco": {
        "language": "java",
        "category": "coverage",
        "description": "Java code coverage",
        "executable": None,  # Maven/Gradle plugin
    },
    "pitest": {
        "language": "java",
        "category": "mutation",
        "description": "Mutation testing for Java",
        "executable": None,  # Maven/Gradle plugin
    },
    "jqwik": {
        "language": "java",
        "category": "test",
        "description": "Property-based testing for Java",
        "executable": None,  # JUnit extension
    },
    "checkstyle": {
        "language": "java",
        "category": "lint",
        "description": "Java code style checker",
        "executable": None,  # Maven/Gradle plugin
    },
    "spotbugs": {
        "language": "java",
        "category": "security",
        "description": "Java static analysis for bugs",
        "executable": None,  # Maven/Gradle plugin
    },
    "pmd": {
        "language": "java",
        "category": "lint",
        "description": "Java source code analyzer",
        "executable": None,  # Maven/Gradle plugin
    },
    "owasp": {
        "language": "java",
        "category": "security",
        "description": "OWASP dependency check",
        "executable": None,  # Maven/Gradle plugin
    },
}


def _get_tools_for_language(language: str | None) -> list[str]:
    """Get tool list for a language."""
    if language == "python":
        return PYTHON_TOOLS
    elif language == "java":
        return JAVA_TOOLS
    else:
        # Return all unique tools
        return sorted(set(PYTHON_TOOLS + JAVA_TOOLS))


def _get_tool_info(tool: str) -> dict[str, Any]:
    """Get metadata for a tool."""
    if tool in TOOL_METADATA:
        info = TOOL_METADATA[tool].copy()
        info["name"] = tool
        return info
    # Unknown tool - minimal info
    return {
        "name": tool,
        "language": "unknown",
        "category": "unknown",
        "description": f"Tool: {tool}",
        "executable": None,
    }


def _wizard_enable_disable(enable: bool) -> CommandResult:
    """Interactive wizard for enabling/disabling tools.

    Args:
        enable: True to enable, False to disable

    Returns:
        CommandResult from the enable/disable operation
    """
    try:
        import questionary

        from cihub.wizard.styles import get_style
    except ImportError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Wizard dependencies not installed",
            problems=[
                {
                    "severity": "error",
                    "message": "Install wizard deps: pip install cihub[wizard]",
                    "code": "CIHUB-TOOL-NO-WIZARD-DEPS",
                }
            ],
        )

    from cihub.services.registry_service import load_registry
    from cihub.utils.paths import hub_root

    action = "enable" if enable else "disable"

    # Select language first
    language = questionary.select(
        "Select language:",
        choices=["python", "java"],
        style=get_style(),
    ).ask()
    if language is None:
        return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")

    # Get tools for selected language
    tools = PYTHON_TOOLS if language == "python" else JAVA_TOOLS
    tool = questionary.select(
        f"Select tool to {action}:",
        choices=list(tools),
        style=get_style(),
    ).ask()
    if tool is None:
        return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")

    # Select target: repo, all repos, or profile
    registry = load_registry()
    repos = list(registry.get("repos", {}).keys())

    profiles_dir = hub_root() / "templates" / "profiles"
    profiles = []
    if profiles_dir.exists():
        profiles = [p.stem for p in profiles_dir.glob(f"{language}-*.yaml")]

    target_choices = []
    if repos:
        target_choices.append({"name": "Single repo", "value": "repo"})
        target_choices.append({"name": "All repos", "value": "all_repos"})
    if profiles:
        target_choices.append({"name": "Profile", "value": "profile"})

    if not target_choices:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="No repos or profiles found",
            problems=[
                {
                    "severity": "error",
                    "message": "Register repos or create profiles first",
                    "code": "CIHUB-TOOL-NO-TARGETS",
                }
            ],
        )

    target_type = questionary.select(
        f"Where to {action} '{tool}'?",
        choices=target_choices,
        style=get_style(),
    ).ask()
    if target_type is None:
        return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")

    # Handle the target selection
    if target_type == "repo":
        repo = questionary.select(
            "Select repo:",
            choices=repos,
            style=get_style(),
        ).ask()
        if repo is None:
            return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")
        if enable:
            return _enable_for_repo(tool, repo)
        else:
            return _disable_for_repo(tool, repo)

    elif target_type == "all_repos":
        if enable:
            return _enable_for_all_repos(tool)
        else:
            return _disable_for_all_repos(tool)

    elif target_type == "profile":
        profile = questionary.select(
            "Select profile:",
            choices=profiles,
            style=get_style(),
        ).ask()
        if profile is None:
            return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")
        if enable:
            return _enable_in_profile(tool, profile)
        else:
            return _disable_in_profile(tool, profile)

    return CommandResult(exit_code=EXIT_FAILURE, summary="Unknown target type")


def _wizard_configure() -> CommandResult:
    """Interactive wizard for configuring tool settings.

    Returns:
        CommandResult from the configure operation
    """
    try:
        import questionary

        from cihub.wizard.styles import get_style
    except ImportError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="questionary not installed (pip install questionary)",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode requires questionary",
                    "code": "CIHUB-TOOL-NO-QUESTIONARY",
                }
            ],
        )

    from cihub.services.registry_service import list_repos, load_registry
    from cihub.utils.paths import hub_root

    # Get available tools (built-in + custom)
    all_tools = list(PYTHON_TOOLS) + list(JAVA_TOOLS)

    # Also include custom tools from defaults if any
    try:
        from cihub.config import PathConfig, load_defaults

        paths = PathConfig(root=str(hub_root()))
        defaults = load_defaults(paths)
        custom_tools = get_custom_tools_from_config(defaults, "python")
        custom_tools.update(get_custom_tools_from_config(defaults, "java"))
        for ct in sorted(custom_tools.keys()):
            if ct not in all_tools:
                all_tools.append(f"{ct} (custom)")
    except Exception:  # noqa: S110, BLE001
        pass  # If loading fails, just use built-in tools

    tool = questionary.select(
        "Select tool to configure:",
        choices=all_tools,
        style=get_style(),
    ).ask()
    if tool is None:
        return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")

    # Strip " (custom)" suffix if present
    if tool.endswith(" (custom)"):
        tool = tool[:-9]

    # Get common parameters for this tool
    info = _get_tool_info(tool)
    common_params = ["enabled", "fail_on_error", "require_run_or_fail"]
    if info.get("category") == "test":
        common_params.extend(["min_coverage", "fail_fast"])
    elif info.get("category") == "security":
        common_params.extend(["fail_on_high", "fail_on_medium", "fail_on_low"])
    elif info.get("category") == "lint":
        common_params.extend(["max_errors"])

    param = questionary.select(
        f"Select parameter for '{tool}':",
        choices=common_params + ["(custom parameter)"],
        style=get_style(),
    ).ask()
    if param is None:
        return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")

    if param == "(custom parameter)":
        param = questionary.text(
            "Enter parameter name:",
            style=get_style(),
        ).ask()
        if not param:
            return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")

    # Get value
    if param == "enabled":
        value_choice = questionary.confirm(
            f"Enable {tool}?",
            default=True,
            style=get_style(),
        ).ask()
        value = str(value_choice).lower()
    elif param.startswith("fail_"):
        value_choice = questionary.confirm(
            f"{param}?",
            default=True,
            style=get_style(),
        ).ask()
        value = str(value_choice).lower()
    else:
        value = questionary.text(
            f"Enter value for '{param}':",
            style=get_style(),
        ).ask()
        if value is None:
            return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")

    # Select target (repo or profile)
    registry = load_registry()
    repos = [r["name"] for r in list_repos(registry)]

    # Scan for available profiles (all languages)
    profiles_dir = hub_root() / "templates" / "profiles"
    profiles = []
    if profiles_dir.exists():
        profiles = [p.stem for p in profiles_dir.glob("*.yaml")]

    target_choices = []
    if repos:
        target_choices.append({"name": "Repository", "value": "repo"})
    if profiles:
        target_choices.append({"name": "Profile", "value": "profile"})

    if not target_choices:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="No repos or profiles found",
            problems=[
                {
                    "severity": "error",
                    "message": "Register repos or create profiles first",
                    "code": "CIHUB-TOOL-NO-TARGETS",
                }
            ],
        )

    target_type = questionary.select(
        "Configure in:",
        choices=target_choices,
        style=get_style(),
    ).ask()
    if target_type is None:
        return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")

    # Parse value
    parsed_value: bool | float | int | str
    try:
        if value.lower() in ("true", "false"):
            parsed_value = value.lower() == "true"
        elif "." in value:
            parsed_value = float(value)
        else:
            parsed_value = int(value)
    except ValueError:
        parsed_value = value

    if target_type == "repo":
        repo = questionary.select(
            "Select repo:",
            choices=repos,
            style=get_style(),
        ).ask()
        if repo is None:
            return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")
        return _configure_for_repo(tool, param, parsed_value, repo)
    else:
        profile = questionary.select(
            "Select profile:",
            choices=profiles,
            style=get_style(),
        ).ask()
        if profile is None:
            return CommandResult(exit_code=EXIT_USAGE, summary="Cancelled")
        return _configure_in_profile(tool, param, parsed_value, profile)


def _validate_tool_language_for_repo(tool: str, repo_lang: str, repo_name: str) -> CommandResult | None:
    """Validate tool is compatible with the repo language.

    Custom tools (x-*) are always allowed - they apply to the repo's language.
    """
    # Custom tools are user-defined and apply to any language
    if is_custom_tool(tool):
        return None

    info = _get_tool_info(tool)
    tool_lang = info.get("language")

    if tool_lang == "unknown":
        if tool in PYTHON_TOOLS and tool in JAVA_TOOLS:
            tool_lang = "both"
        elif tool in PYTHON_TOOLS:
            tool_lang = "python"
        elif tool in JAVA_TOOLS:
            tool_lang = "java"

    if tool_lang in ("both", repo_lang):
        return None

    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=f"Tool '{tool}' does not apply to {repo_lang} repos",
        problems=[
            {
                "severity": "error",
                "message": f"Tool '{tool}' is for {tool_lang} repos; '{repo_name}' is {repo_lang}",
                "code": "CIHUB-TOOL-LANGUAGE-MISMATCH",
            }
        ],
    )


def cmd_tool(args: argparse.Namespace) -> CommandResult:
    """Dispatch tool subcommands."""
    subcommand: str | None = getattr(args, "subcommand", None)

    handlers = {
        "list": _cmd_list,
        "enable": _cmd_enable,
        "disable": _cmd_disable,
        "configure": _cmd_configure,
        "status": _cmd_status,
        "validate": _cmd_validate,
        "info": _cmd_info,
    }

    handler = handlers.get(subcommand or "")
    if handler is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown tool subcommand: {subcommand}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Unknown subcommand '{subcommand}'",
                    "code": "CIHUB-TOOL-UNKNOWN-SUBCOMMAND",
                }
            ],
        )

    return handler(args)


def _cmd_list(args: argparse.Namespace) -> CommandResult:
    """List available tools."""
    language = getattr(args, "language", None)
    category = getattr(args, "category", None)
    repo = getattr(args, "repo", None)
    enabled_only = getattr(args, "enabled_only", False)

    # Validate --enabled-only requires --repo
    if enabled_only and not repo:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--enabled-only requires --repo",
            problems=[
                {
                    "severity": "error",
                    "message": "--enabled-only filter requires --repo to check",
                    "code": "CIHUB-TOOL-REQUIRES-REPO",
                }
            ],
        )

    tools = _get_tools_for_language(language)

    # Build tool info list
    tool_infos = []
    for tool in tools:
        info = _get_tool_info(tool)

        # Filter by category
        if category and info.get("category") != category:
            continue

        # Filter by language (for shared tools)
        if language and info.get("language") not in (language, "both"):
            continue

        tool_infos.append(info)

    # If repo specified, check enabled status
    if repo:
        from cihub.services.registry_service import get_repo_config, load_registry

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
                        "code": "CIHUB-TOOL-REPO-NOT-FOUND",
                    }
                ],
            )

        config = repo_config.get("config", {})
        repo_lang = repo_config.get("language") or config.get("language")

        # Add custom tools from repo config
        if repo_lang:
            custom_tools = get_custom_tools_from_config(config, repo_lang)
            for tool_name, tool_cfg in custom_tools.items():
                # Skip if category filter doesn't match custom tools
                if category and category != "custom":
                    continue
                custom_info = {
                    "name": tool_name,
                    "language": repo_lang,
                    "category": "custom",
                    "description": f"Custom tool: {tool_name}",
                    "executable": None,
                }
                # Check enabled status
                if isinstance(tool_cfg, bool):
                    custom_info["enabled"] = tool_cfg
                elif isinstance(tool_cfg, dict):
                    custom_info["enabled"] = tool_cfg.get("enabled", True)
                    if "command" in tool_cfg:
                        custom_info["command"] = tool_cfg["command"]
                else:
                    custom_info["enabled"] = True
                tool_infos.append(custom_info)

        for info in tool_infos:
            tool_name = info["name"]
            # Check if tool is enabled in repo config
            lang_config = config.get(repo_lang, {}) if repo_lang else {}
            tools_config = lang_config.get("tools", {})
            tool_config = tools_config.get(tool_name, {})

            if isinstance(tool_config, bool):
                info["enabled"] = tool_config
            elif isinstance(tool_config, dict):
                info["enabled"] = tool_config.get("enabled", False)
            else:
                info["enabled"] = False

        if enabled_only:
            tool_infos = [t for t in tool_infos if t.get("enabled", False)]

    if not tool_infos:
        filter_desc = []
        if language:
            filter_desc.append(f"language={language}")
        if category:
            filter_desc.append(f"category={category}")
        filter_str = f" (filters: {', '.join(filter_desc)})" if filter_desc else ""
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"No tools found{filter_str}",
            data={"tools": []},
        )

    # Group by category for summary
    categories = set(t.get("category", "unknown") for t in tool_infos)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Found {len(tool_infos)} tool(s) in {len(categories)} category(ies)",
        data={"tools": tool_infos, "count": len(tool_infos)},
    )


def _cmd_enable(args: argparse.Namespace) -> CommandResult:
    """Enable a tool."""
    wizard = getattr(args, "wizard", False)
    tool = args.tool
    for_repo = getattr(args, "for_repo", None)
    all_repos = getattr(args, "all_repos", False)
    profile = getattr(args, "profile", None)

    # Reject --json with --wizard
    if getattr(args, "json", False) and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "--wizard is not supported with --json",
                    "code": "CIHUB-TOOL-WIZARD-JSON",
                }
            ],
        )

    # Wizard mode: interactive tool and target selection
    if wizard:
        return _wizard_enable_disable(enable=True)

    # Non-wizard mode requires tool name
    if not tool:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Tool name required (or use --wizard)",
            problems=[
                {
                    "severity": "error",
                    "message": "Specify tool name or use --wizard for interactive mode",
                    "code": "CIHUB-TOOL-NO-NAME",
                }
            ],
        )

    # Validate tool exists (built-in or custom x-* prefix)
    all_tools = set(PYTHON_TOOLS + JAVA_TOOLS)
    if tool not in all_tools and not is_custom_tool(tool):
        builtin_list = ", ".join(sorted(all_tools))
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Unknown tool: {tool}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found. Use a built-in tool ({builtin_list}) "
                    "or custom tool (x-<name>)",
                    "code": "CIHUB-TOOL-UNKNOWN",
                }
            ],
        )

    if profile:
        return _enable_in_profile(tool, profile)
    elif for_repo:
        return _enable_for_repo(tool, for_repo)
    elif all_repos:
        return _enable_for_all_repos(tool)
    else:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Specify --for-repo, --all-repos, or --profile",
            problems=[
                {
                    "severity": "error",
                    "message": "Must specify target: --for-repo <name>, --all-repos, or --profile <name>",
                    "code": "CIHUB-TOOL-NO-TARGET",
                }
            ],
        )


def _cmd_disable(args: argparse.Namespace) -> CommandResult:
    """Disable a tool."""
    wizard = getattr(args, "wizard", False)
    tool = args.tool
    for_repo = getattr(args, "for_repo", None)
    all_repos = getattr(args, "all_repos", False)
    profile = getattr(args, "profile", None)

    # Reject --json with --wizard
    if getattr(args, "json", False) and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "--wizard is not supported with --json",
                    "code": "CIHUB-TOOL-WIZARD-JSON",
                }
            ],
        )

    # Wizard mode: interactive tool and target selection
    if wizard:
        return _wizard_enable_disable(enable=False)

    # Non-wizard mode requires tool name
    if not tool:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Tool name required (or use --wizard)",
            problems=[
                {
                    "severity": "error",
                    "message": "Specify tool name or use --wizard for interactive mode",
                    "code": "CIHUB-TOOL-NO-NAME",
                }
            ],
        )

    # Validate tool exists (built-in or custom x-* prefix)
    all_tools = set(PYTHON_TOOLS + JAVA_TOOLS)
    if tool not in all_tools and not is_custom_tool(tool):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Unknown tool: {tool}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found. Use a built-in tool or custom tool (x-<name>)",
                    "code": "CIHUB-TOOL-UNKNOWN",
                }
            ],
        )

    if profile:
        return _disable_in_profile(tool, profile)
    elif for_repo:
        return _disable_for_repo(tool, for_repo)
    elif all_repos:
        return _disable_for_all_repos(tool)
    else:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Specify --for-repo, --all-repos, or --profile",
            problems=[
                {
                    "severity": "error",
                    "message": "Must specify target: --for-repo <name>, --all-repos, or --profile <name>",
                    "code": "CIHUB-TOOL-NO-TARGET",
                }
            ],
        )


def _cmd_configure(args: argparse.Namespace) -> CommandResult:
    """Configure a tool setting."""
    wizard = getattr(args, "wizard", False)

    # JSON-purity: reject --json with --wizard
    if getattr(args, "json", False) and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "--wizard is not supported with --json",
                    "code": "CIHUB-TOOL-WIZARD-JSON",
                }
            ],
        )

    # Check for wizard mode
    if wizard:
        return _wizard_configure()

    tool = getattr(args, "tool", None)
    param = getattr(args, "param", None)
    value = getattr(args, "value", None)
    repo = getattr(args, "repo", None)
    profile = getattr(args, "profile", None)

    # Require tool, param, value in non-wizard mode
    if not tool or not param or value is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Missing required arguments",
            problems=[
                {
                    "severity": "error",
                    "message": "Require: tool configure <tool> <param> <value> --repo/--profile, or use --wizard",
                    "code": "CIHUB-TOOL-MISSING-ARGS",
                }
            ],
        )

    # Validate tool exists (built-in or custom x-* prefix)
    all_tools = set(PYTHON_TOOLS + JAVA_TOOLS)
    if tool not in all_tools and not is_custom_tool(tool):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Unknown tool: {tool}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found. Use a built-in tool or custom tool (x-<name>)",
                    "code": "CIHUB-TOOL-UNKNOWN",
                }
            ],
        )

    # Parse value
    try:
        if value.lower() in ("true", "false"):
            parsed_value = value.lower() == "true"
        elif "." in value:
            parsed_value = float(value)
        else:
            parsed_value = int(value)
    except ValueError:
        parsed_value = value

    if profile:
        return _configure_in_profile(tool, param, parsed_value, profile)
    elif repo:
        return _configure_for_repo(tool, param, parsed_value, repo)
    else:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Specify --repo or --profile",
            problems=[
                {
                    "severity": "error",
                    "message": "Must specify target: --repo <name> or --profile <name>",
                    "code": "CIHUB-TOOL-NO-TARGET",
                }
            ],
        )


def _cmd_status(args: argparse.Namespace) -> CommandResult:
    """Show tool status."""
    repo = getattr(args, "repo", None)
    all_repos = getattr(args, "all", False)
    language = getattr(args, "language", None)

    from cihub.services.registry_service import list_repos, load_registry

    registry = load_registry()
    repos = list_repos(registry)

    if repo:
        repos = [r for r in repos if r["name"] == repo]
        if not repos:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Repository '{repo}' not found",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Repository '{repo}' not in registry",
                        "code": "CIHUB-TOOL-REPO-NOT-FOUND",
                    }
                ],
            )

    if language:
        repos = [r for r in repos if r.get("language") == language]

    if not all_repos and not repo:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Specify --repo or --all",
            problems=[
                {
                    "severity": "error",
                    "message": "Must specify --repo <name> or --all",
                    "code": "CIHUB-TOOL-NO-TARGET",
                }
            ],
        )

    # Build status for each repo
    status_list = []
    for r in repos:
        repo_name = r["name"]
        repo_lang = r.get("language")
        config = r.get("config", {})

        tools = list(_get_tools_for_language(repo_lang))
        lang_config = config.get(repo_lang, {}) if repo_lang else {}
        tools_config = lang_config.get("tools", {})

        # Add custom tools from config
        if repo_lang:
            custom_tools = get_custom_tools_from_config(config, repo_lang)
            tools.extend(custom_tools.keys())

        enabled_tools = []
        disabled_tools = []

        for tool in tools:
            tool_config = tools_config.get(tool, {})
            if isinstance(tool_config, bool):
                enabled = tool_config
            elif isinstance(tool_config, dict):
                enabled = tool_config.get("enabled", False)
            else:
                enabled = False

            if enabled:
                enabled_tools.append(tool)
            else:
                disabled_tools.append(tool)

        status_list.append(
            {
                "repo": repo_name,
                "language": repo_lang,
                "enabled_tools": enabled_tools,
                "disabled_tools": disabled_tools,
                "enabled_count": len(enabled_tools),
                "disabled_count": len(disabled_tools),
            }
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Tool status for {len(status_list)} repo(s)",
        data={"repos": status_list},
    )


def _cmd_validate(args: argparse.Namespace) -> CommandResult:
    """Validate tool installation."""
    tool = args.tool
    install_if_missing = getattr(args, "install_if_missing", False)

    info = _get_tool_info(tool)
    executable = info.get("executable")

    if executable is None:
        # Tool doesn't have a standalone executable (plugin, etc.)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Tool '{tool}' is a plugin/extension (no executable to validate)",
            data={"tool": tool, "type": "plugin", "installed": None},
        )

    # Check if executable exists
    found = shutil.which(executable)

    if found:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Tool '{tool}' found: {found}",
            data={"tool": tool, "executable": executable, "path": found, "installed": True},
        )
    else:
        if install_if_missing:
            # Attempt installation guidance
            install_hint = _get_install_hint(tool)
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Tool '{tool}' not found",
                data={
                    "tool": tool,
                    "executable": executable,
                    "installed": False,
                    "install_hint": install_hint,
                },
                suggestions=[{"message": install_hint, "code": "CIHUB-TOOL-INSTALL"}],
            )
        else:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Tool '{tool}' ({executable}) not found in PATH",
                data={"tool": tool, "executable": executable, "installed": False},
                problems=[
                    {
                        "severity": "warning",
                        "message": f"Executable '{executable}' not found",
                        "code": "CIHUB-TOOL-NOT-INSTALLED",
                    }
                ],
            )


def _cmd_info(args: argparse.Namespace) -> CommandResult:
    """Show detailed tool information."""
    tool = args.tool

    # Built-in tools have metadata, custom tools don't
    all_tools = set(PYTHON_TOOLS + JAVA_TOOLS)
    if tool not in all_tools and not is_custom_tool(tool):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Unknown tool: {tool}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found. Use a built-in tool or custom tool (x-<name>)",
                    "code": "CIHUB-TOOL-UNKNOWN",
                }
            ],
        )

    info = _get_tool_info(tool)

    # Add installation status
    executable = info.get("executable")
    if executable:
        found = shutil.which(executable)
        info["installed"] = found is not None
        info["path"] = found
    else:
        info["installed"] = None
        info["path"] = None

    # Add available settings
    info["settings"] = _get_tool_settings(tool)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Tool: {tool}",
        data=info,
    )


# =============================================================================
# Helper functions
# =============================================================================


def _enable_in_profile(tool: str, profile_name: str) -> CommandResult:
    """Enable a tool in a profile."""
    # Validate profile name
    validation_error = _validate_profile_name(profile_name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-TOOL-INVALID-PROFILE-NAME",
                }
            ],
        )

    from cihub.utils.paths import hub_root

    profiles_dir = hub_root() / "templates" / "profiles"
    profile_path = profiles_dir / f"{profile_name}.yaml"

    if not profile_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{profile_name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{profile_name}' does not exist",
                    "code": "CIHUB-TOOL-PROFILE-NOT-FOUND",
                }
            ],
        )

    # Load and update profile
    try:
        with open(profile_path, encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid YAML in profile: {profile_name}",
            problems=[{"severity": "error", "message": f"YAML parse error: {e}", "code": "CIHUB-TOOL-YAML-ERROR"}],
        )

    # Determine language from tool or profile name
    if is_custom_tool(tool):
        # Custom tools: determine language from profile name
        if profile_name.startswith("python-"):
            lang = "python"
        elif profile_name.startswith("java-"):
            lang = "java"
        elif "python" in content:
            lang = "python"
        elif "java" in content:
            lang = "java"
        else:
            lang = "python"  # Default
    else:
        info = _get_tool_info(tool)
        lang = str(info.get("language", "python"))
        if lang in ("both", "unknown"):
            # Check profile name for language hint
            if profile_name.startswith("python-"):
                lang = "python"
            elif profile_name.startswith("java-"):
                lang = "java"
            else:
                lang = "python"  # Default

    if lang not in content:
        content[lang] = {}
    if "tools" not in content[lang]:
        content[lang]["tools"] = {}

    tool_config = content[lang]["tools"].get(tool, {})
    if isinstance(tool_config, bool):
        content[lang]["tools"][tool] = {"enabled": True}
    elif isinstance(tool_config, dict):
        tool_config["enabled"] = True
        content[lang]["tools"][tool] = tool_config
    else:
        content[lang]["tools"][tool] = {"enabled": True}

    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Enabled '{tool}' in profile '{profile_name}'",
        data={"tool": tool, "profile": profile_name, "action": "enabled"},
        files_modified=[str(profile_path)],
    )


def _disable_in_profile(tool: str, profile_name: str) -> CommandResult:
    """Disable a tool in a profile."""
    # Validate profile name
    validation_error = _validate_profile_name(profile_name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-TOOL-INVALID-PROFILE-NAME",
                }
            ],
        )

    from cihub.utils.paths import hub_root

    profiles_dir = hub_root() / "templates" / "profiles"
    profile_path = profiles_dir / f"{profile_name}.yaml"

    if not profile_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{profile_name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{profile_name}' does not exist",
                    "code": "CIHUB-TOOL-PROFILE-NOT-FOUND",
                }
            ],
        )

    try:
        with open(profile_path, encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid YAML in profile: {profile_name}",
            problems=[{"severity": "error", "message": f"YAML parse error: {e}", "code": "CIHUB-TOOL-YAML-ERROR"}],
        )

    # Determine target language for the tool
    if is_custom_tool(tool):
        # Custom tools: determine language from profile name or content
        if profile_name.startswith("python-"):
            lang = "python"
        elif profile_name.startswith("java-"):
            lang = "java"
        elif "python" in content:
            lang = "python"
        elif "java" in content:
            lang = "java"
        else:
            lang = "python"  # Default to python
    else:
        info = _get_tool_info(tool)
        lang = str(info.get("language", "python"))
        if lang in ("both", "unknown"):
            # Check profile name for language hint
            if profile_name.startswith("python-"):
                lang = "python"
            elif profile_name.startswith("java-"):
                lang = "java"
            elif "python" in content:
                lang = "python"
            elif "java" in content:
                lang = "java"
            else:
                lang = "python"

    if lang not in content:
        content[lang] = {}
    if "tools" not in content[lang]:
        content[lang]["tools"] = {}

    tool_config = content[lang]["tools"].get(tool, {})
    if isinstance(tool_config, bool):
        content[lang]["tools"][tool] = {"enabled": False}
    elif isinstance(tool_config, dict):
        tool_config["enabled"] = False
        content[lang]["tools"][tool] = tool_config
    else:
        content[lang]["tools"][tool] = {"enabled": False}

    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Disabled '{tool}' in profile '{profile_name}'",
        data={"tool": tool, "profile": profile_name, "action": "disabled"},
        files_modified=[str(profile_path)],
    )


def _enable_for_repo(tool: str, repo_name: str) -> CommandResult:
    """Enable a tool for a specific repo."""
    from cihub.services.registry_service import get_repo_config, load_registry, save_registry

    registry = load_registry()
    repo_config = get_repo_config(registry, repo_name)

    if repo_config is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{repo_name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{repo_name}' not in registry",
                    "code": "CIHUB-TOOL-REPO-NOT-FOUND",
                }
            ],
        )

    # Get language
    config = repo_config.get("config", {})
    lang = repo_config.get("language") or config.get("language")

    if not lang:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{repo_name}' has no language set",
            problems=[
                {
                    "severity": "error",
                    "message": "Cannot determine language for repo",
                    "code": "CIHUB-TOOL-NO-LANGUAGE",
                }
            ],
        )

    language_check = _validate_tool_language_for_repo(tool, lang, repo_name)
    if language_check:
        return language_check

    # Update config in registry
    if "config" not in registry["repos"][repo_name]:
        registry["repos"][repo_name]["config"] = {}
    if lang not in registry["repos"][repo_name]["config"]:
        registry["repos"][repo_name]["config"][lang] = {}
    if "tools" not in registry["repos"][repo_name]["config"][lang]:
        registry["repos"][repo_name]["config"][lang]["tools"] = {}

    tools = registry["repos"][repo_name]["config"][lang]["tools"]
    tool_config = tools.get(tool, {})
    if isinstance(tool_config, bool):
        tools[tool] = {"enabled": True}
    elif isinstance(tool_config, dict):
        tool_config["enabled"] = True
        tools[tool] = tool_config
    else:
        tools[tool] = {"enabled": True}

    save_registry(registry)

    from cihub.services.registry_service import _get_registry_path

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Enabled '{tool}' for repo '{repo_name}'",
        data={"tool": tool, "repo": repo_name, "action": "enabled"},
        files_modified=[str(_get_registry_path())],
    )


def _disable_for_repo(tool: str, repo_name: str) -> CommandResult:
    """Disable a tool for a specific repo."""
    from cihub.services.registry_service import get_repo_config, load_registry, save_registry

    registry = load_registry()
    repo_config = get_repo_config(registry, repo_name)

    if repo_config is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{repo_name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{repo_name}' not in registry",
                    "code": "CIHUB-TOOL-REPO-NOT-FOUND",
                }
            ],
        )

    config = repo_config.get("config", {})
    lang = repo_config.get("language") or config.get("language")

    if not lang:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{repo_name}' has no language set",
            problems=[
                {
                    "severity": "error",
                    "message": "Cannot determine language for repo",
                    "code": "CIHUB-TOOL-NO-LANGUAGE",
                }
            ],
        )

    language_check = _validate_tool_language_for_repo(tool, lang, repo_name)
    if language_check:
        return language_check

    if "config" not in registry["repos"][repo_name]:
        registry["repos"][repo_name]["config"] = {}
    if lang not in registry["repos"][repo_name]["config"]:
        registry["repos"][repo_name]["config"][lang] = {}
    if "tools" not in registry["repos"][repo_name]["config"][lang]:
        registry["repos"][repo_name]["config"][lang]["tools"] = {}

    tools = registry["repos"][repo_name]["config"][lang]["tools"]
    tool_config = tools.get(tool, {})
    if isinstance(tool_config, bool):
        tools[tool] = {"enabled": False}
    elif isinstance(tool_config, dict):
        tool_config["enabled"] = False
        tools[tool] = tool_config
    else:
        tools[tool] = {"enabled": False}

    save_registry(registry)

    from cihub.services.registry_service import _get_registry_path

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Disabled '{tool}' for repo '{repo_name}'",
        data={"tool": tool, "repo": repo_name, "action": "disabled"},
        files_modified=[str(_get_registry_path())],
    )


def _enable_for_all_repos(tool: str) -> CommandResult:
    """Enable a tool for all repos."""
    from cihub.services.registry_service import list_repos, load_registry, save_registry

    registry = load_registry()
    repos = list_repos(registry)

    info = _get_tool_info(tool)
    tool_lang = info.get("language")

    updated = []
    skipped = []

    for repo in repos:
        repo_name = repo["name"]
        repo_lang = repo.get("language")

        # Skip if language mismatch
        if tool_lang not in ("both", repo_lang):
            skipped.append(repo_name)
            continue

        if not repo_lang:
            skipped.append(repo_name)
            continue

        if "config" not in registry["repos"][repo_name]:
            registry["repos"][repo_name]["config"] = {}
        if repo_lang not in registry["repos"][repo_name]["config"]:
            registry["repos"][repo_name]["config"][repo_lang] = {}
        if "tools" not in registry["repos"][repo_name]["config"][repo_lang]:
            registry["repos"][repo_name]["config"][repo_lang]["tools"] = {}

        tools = registry["repos"][repo_name]["config"][repo_lang]["tools"]
        tool_config = tools.get(tool, {})
        if isinstance(tool_config, bool):
            tools[tool] = {"enabled": True}
        elif isinstance(tool_config, dict):
            tool_config["enabled"] = True
            tools[tool] = tool_config
        else:
            tools[tool] = {"enabled": True}

        updated.append(repo_name)

    save_registry(registry)

    from cihub.services.registry_service import _get_registry_path

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Enabled '{tool}' for {len(updated)} repo(s), skipped {len(skipped)}",
        data={"tool": tool, "updated": updated, "skipped": skipped},
        files_modified=[str(_get_registry_path())],
    )


def _disable_for_all_repos(tool: str) -> CommandResult:
    """Disable a tool for all repos."""
    from cihub.services.registry_service import list_repos, load_registry, save_registry

    registry = load_registry()
    repos = list_repos(registry)

    info = _get_tool_info(tool)
    tool_lang = info.get("language")

    updated = []
    skipped = []

    for repo in repos:
        repo_name = repo["name"]
        repo_lang = repo.get("language")

        if tool_lang not in ("both", repo_lang):
            skipped.append(repo_name)
            continue

        if not repo_lang:
            skipped.append(repo_name)
            continue

        if "config" not in registry["repos"][repo_name]:
            registry["repos"][repo_name]["config"] = {}
        if repo_lang not in registry["repos"][repo_name]["config"]:
            registry["repos"][repo_name]["config"][repo_lang] = {}
        if "tools" not in registry["repos"][repo_name]["config"][repo_lang]:
            registry["repos"][repo_name]["config"][repo_lang]["tools"] = {}

        tools = registry["repos"][repo_name]["config"][repo_lang]["tools"]
        tool_config = tools.get(tool, {})
        if isinstance(tool_config, bool):
            tools[tool] = {"enabled": False}
        elif isinstance(tool_config, dict):
            tool_config["enabled"] = False
            tools[tool] = tool_config
        else:
            tools[tool] = {"enabled": False}

        updated.append(repo_name)

    save_registry(registry)

    from cihub.services.registry_service import _get_registry_path

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Disabled '{tool}' for {len(updated)} repo(s), skipped {len(skipped)}",
        data={"tool": tool, "updated": updated, "skipped": skipped},
        files_modified=[str(_get_registry_path())],
    )


def _configure_in_profile(tool: str, param: str, value: Any, profile_name: str) -> CommandResult:
    """Configure a tool setting in a profile."""
    # Validate profile name
    validation_error = _validate_profile_name(profile_name)
    if validation_error:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid profile name: {validation_error}",
            problems=[
                {
                    "severity": "error",
                    "message": validation_error,
                    "code": "CIHUB-TOOL-INVALID-PROFILE-NAME",
                }
            ],
        )

    from cihub.utils.paths import hub_root

    profiles_dir = hub_root() / "templates" / "profiles"
    profile_path = profiles_dir / f"{profile_name}.yaml"

    if not profile_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Profile '{profile_name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Profile '{profile_name}' does not exist",
                    "code": "CIHUB-TOOL-PROFILE-NOT-FOUND",
                }
            ],
        )

    try:
        with open(profile_path, encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid YAML in profile: {profile_name}",
            problems=[{"severity": "error", "message": f"YAML parse error: {e}", "code": "CIHUB-TOOL-YAML-ERROR"}],
        )

    # Determine target language for the tool
    if is_custom_tool(tool):
        # Custom tools: determine language from profile name or content
        if profile_name.startswith("python-"):
            lang = "python"
        elif profile_name.startswith("java-"):
            lang = "java"
        elif "python" in content:
            lang = "python"
        elif "java" in content:
            lang = "java"
        else:
            lang = "python"  # Default to python
    else:
        info = _get_tool_info(tool)
        lang = str(info.get("language", "python"))
        if lang in ("both", "unknown"):
            # Check profile name for language hint
            if profile_name.startswith("python-"):
                lang = "python"
            elif profile_name.startswith("java-"):
                lang = "java"
            elif "python" in content:
                lang = "python"
            elif "java" in content:
                lang = "java"
            else:
                lang = "python"

    if lang not in content:
        content[lang] = {}
    if "tools" not in content[lang]:
        content[lang]["tools"] = {}
    if tool not in content[lang]["tools"]:
        content[lang]["tools"][tool] = {}

    tool_config = content[lang]["tools"][tool]
    if isinstance(tool_config, bool):
        content[lang]["tools"][tool] = {"enabled": tool_config, param: value}
    else:
        tool_config[param] = value

    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Set {tool}.{param}={value} in profile '{profile_name}'",
        data={"tool": tool, "param": param, "value": value, "profile": profile_name},
        files_modified=[str(profile_path)],
    )


def _configure_for_repo(tool: str, param: str, value: Any, repo_name: str) -> CommandResult:
    """Configure a tool setting for a repo."""
    from cihub.services.registry_service import get_repo_config, load_registry, save_registry

    registry = load_registry()
    repo_config = get_repo_config(registry, repo_name)

    if repo_config is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{repo_name}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{repo_name}' not in registry",
                    "code": "CIHUB-TOOL-REPO-NOT-FOUND",
                }
            ],
        )

    config = repo_config.get("config", {})
    lang = repo_config.get("language") or config.get("language")

    if not lang:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{repo_name}' has no language set",
            problems=[
                {
                    "severity": "error",
                    "message": "Cannot determine language for repo",
                    "code": "CIHUB-TOOL-NO-LANGUAGE",
                }
            ],
        )

    language_check = _validate_tool_language_for_repo(tool, lang, repo_name)
    if language_check:
        return language_check

    if "config" not in registry["repos"][repo_name]:
        registry["repos"][repo_name]["config"] = {}
    if lang not in registry["repos"][repo_name]["config"]:
        registry["repos"][repo_name]["config"][lang] = {}
    if "tools" not in registry["repos"][repo_name]["config"][lang]:
        registry["repos"][repo_name]["config"][lang]["tools"] = {}
    if tool not in registry["repos"][repo_name]["config"][lang]["tools"]:
        registry["repos"][repo_name]["config"][lang]["tools"][tool] = {}

    tool_config = registry["repos"][repo_name]["config"][lang]["tools"][tool]
    if isinstance(tool_config, bool):
        registry["repos"][repo_name]["config"][lang]["tools"][tool] = {"enabled": tool_config, param: value}
    else:
        tool_config[param] = value

    save_registry(registry)

    from cihub.services.registry_service import _get_registry_path

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Set {tool}.{param}={value} for repo '{repo_name}'",
        data={"tool": tool, "param": param, "value": value, "repo": repo_name},
        files_modified=[str(_get_registry_path())],
    )


def _get_install_hint(tool: str) -> str:
    """Get installation hint for a tool."""
    hints = {
        "ruff": "pip install ruff",
        "black": "pip install black",
        "isort": "pip install isort",
        "mypy": "pip install mypy",
        "bandit": "pip install bandit",
        "pip_audit": "pip install pip-audit",
        "mutmut": "pip install mutmut",
        "semgrep": "pip install semgrep",
        "trivy": "brew install trivy  # or see https://trivy.dev/",
        "docker": "Install Docker Desktop from https://docker.com/",
    }
    return hints.get(tool, f"Install {tool} using your package manager")


def _get_tool_settings(tool: str) -> list[dict[str, Any]]:
    """Get available settings for a tool."""
    # Common settings by tool
    settings_map = {
        "pytest": [
            {"name": "enabled", "type": "bool", "default": True},
            {"name": "min_coverage", "type": "int", "default": 70},
            {"name": "fail_fast", "type": "bool", "default": False},
        ],
        "ruff": [
            {"name": "enabled", "type": "bool", "default": True},
            {"name": "fail_on_error", "type": "bool", "default": True},
            {"name": "max_errors", "type": "int", "default": 0},
        ],
        "black": [
            {"name": "enabled", "type": "bool", "default": True},
            {"name": "fail_on_format_issues", "type": "bool", "default": False},
        ],
        "bandit": [
            {"name": "enabled", "type": "bool", "default": True},
            {"name": "fail_on_high", "type": "bool", "default": True},
            {"name": "fail_on_medium", "type": "bool", "default": False},
            {"name": "fail_on_low", "type": "bool", "default": False},
        ],
        "mutmut": [
            {"name": "enabled", "type": "bool", "default": False},
            {"name": "min_mutation_score", "type": "int", "default": 70},
        ],
        "trivy": [
            {"name": "enabled", "type": "bool", "default": False},
            {"name": "fail_on_critical", "type": "bool", "default": True},
            {"name": "fail_on_high", "type": "bool", "default": True},
            {"name": "fail_on_cvss", "type": "float", "default": 7.0},
        ],
    }
    return settings_map.get(tool, [{"name": "enabled", "type": "bool", "default": False}])
