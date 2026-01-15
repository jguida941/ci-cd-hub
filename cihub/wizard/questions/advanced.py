"""Advanced wizard questions for non-tool settings."""

from __future__ import annotations

from typing import Any

import questionary

from cihub.wizard.styles import get_style


def configure_gates(defaults: dict[str, Any]) -> dict[str, Any]:
    """Configure CI gates (required/optional checks).

    Args:
        defaults: Current config with defaults

    Returns:
        Gates configuration dict
    """
    gates_defaults: dict[str, Any] = defaults.get("gates", {})
    if not isinstance(gates_defaults, dict):
        gates_defaults = {}

    # Ask if user wants to customize gates
    customize = questionary.confirm(
        "Customize CI gates (required/optional checks)?",
        default=False,
        style=get_style(),
    ).ask()

    if not customize:
        return gates_defaults

    # Required gates
    required_choices = [
        {"name": "lint - Code linting (ruff/checkstyle)", "value": "lint", "checked": True},
        {"name": "test - Unit tests (pytest/junit)", "value": "test", "checked": True},
        {"name": "security - Security scanning (bandit/owasp)", "value": "security", "checked": False},
        {"name": "coverage - Coverage gate", "value": "coverage", "checked": False},
        {"name": "mutation - Mutation testing", "value": "mutation", "checked": False},
    ]

    # Pre-check based on defaults
    default_required = gates_defaults.get("required", [])
    if isinstance(default_required, list):
        for choice in required_choices:
            choice["checked"] = choice["value"] in default_required

    required = questionary.checkbox(
        "Select required gates (CI fails if any fail):",
        choices=required_choices,
        style=get_style(),
    ).ask()

    # Optional gates
    optional_choices = [
        {"name": "mutation - Mutation testing", "value": "mutation", "checked": False},
        {"name": "sbom - Software bill of materials", "value": "sbom", "checked": False},
        {"name": "codeql - CodeQL analysis", "value": "codeql", "checked": False},
        {"name": "trivy - Container scanning", "value": "trivy", "checked": False},
    ]

    # Pre-check based on defaults
    default_optional = gates_defaults.get("optional", [])
    if isinstance(default_optional, list):
        for choice in optional_choices:
            choice["checked"] = choice["value"] in default_optional

    optional = questionary.checkbox(
        "Select optional gates (CI continues if they fail):",
        choices=optional_choices,
        style=get_style(),
    ).ask()

    result: dict[str, Any] = {}
    if required:
        result["required"] = required
    if optional:
        result["optional"] = optional

    return result


def configure_reports(defaults: dict[str, Any]) -> dict[str, Any]:
    """Configure CI report generation.

    Args:
        defaults: Current config with defaults

    Returns:
        Reports configuration dict
    """
    reports_defaults: dict[str, Any] = defaults.get("reports", {})
    if not isinstance(reports_defaults, dict):
        reports_defaults = {}

    # Ask if user wants to customize reports
    customize = questionary.confirm(
        "Customize report generation?",
        default=False,
        style=get_style(),
    ).ask()

    if not customize:
        return reports_defaults

    # Report options
    enabled = questionary.confirm(
        "Enable report generation?",
        default=reports_defaults.get("enabled", True),
        style=get_style(),
    ).ask()

    if not enabled:
        return {"enabled": False}

    format_choice = questionary.select(
        "Report format:",
        choices=[
            {"name": "JSON (machine-readable)", "value": "json"},
            {"name": "SARIF (GitHub Security)", "value": "sarif"},
            {"name": "HTML (human-readable)", "value": "html"},
        ],
        default=reports_defaults.get("format", "json"),
        style=get_style(),
    ).ask()

    return {
        "enabled": True,
        "format": format_choice or "json",
    }


def configure_notifications(defaults: dict[str, Any]) -> dict[str, Any]:
    """Configure CI notifications.

    Args:
        defaults: Current config with defaults

    Returns:
        Notifications configuration dict
    """
    notifications_defaults: dict[str, Any] = defaults.get("notifications", {})
    if not isinstance(notifications_defaults, dict):
        notifications_defaults = {}

    # Ask if user wants to configure notifications
    configure = questionary.confirm(
        "Configure CI notifications (Slack, email, etc.)?",
        default=False,
        style=get_style(),
    ).ask()

    if not configure:
        return notifications_defaults

    result: dict[str, Any] = {}

    # Slack configuration
    slack_enabled = questionary.confirm(
        "Enable Slack notifications?",
        default=bool(notifications_defaults.get("slack")),
        style=get_style(),
    ).ask()

    if slack_enabled:
        slack_defaults = notifications_defaults.get("slack", {})
        if not isinstance(slack_defaults, dict):
            slack_defaults = {}

        channel = questionary.text(
            "Slack channel (e.g., #ci-notifications):",
            default=slack_defaults.get("channel", "#ci"),
            style=get_style(),
        ).ask()

        on_failure = questionary.confirm(
            "Notify on failure only?",
            default=slack_defaults.get("on_failure_only", True),
            style=get_style(),
        ).ask()

        result["slack"] = {
            "channel": channel or "#ci",
            "on_failure_only": on_failure,
        }

    return result


def configure_harden_runner(defaults: dict[str, Any]) -> dict[str, Any]:
    """Configure GitHub Actions harden-runner settings.

    Args:
        defaults: Current config with defaults

    Returns:
        Harden runner configuration dict
    """
    harden_defaults: dict[str, Any] = defaults.get("harden_runner", {})
    if not isinstance(harden_defaults, dict):
        harden_defaults = {}

    # Ask if user wants to configure hardening
    customize = questionary.confirm(
        "Customize GitHub Actions security hardening?",
        default=False,
        style=get_style(),
    ).ask()

    if not customize:
        return harden_defaults

    egress_policy = questionary.select(
        "Egress policy (outbound network access):",
        choices=[
            {"name": "audit - Log but allow all outbound", "value": "audit"},
            {"name": "block - Block unauthorized outbound (strict)", "value": "block"},
        ],
        default=harden_defaults.get("egress_policy", "audit"),
        style=get_style(),
    ).ask()

    return {
        "egress_policy": egress_policy or "audit",
    }


def configure_advanced_settings(defaults: dict[str, Any]) -> dict[str, Any]:
    """Orchestrate all advanced setting prompts.

    Args:
        defaults: Current config with defaults

    Returns:
        Dict with all advanced settings
    """
    result: dict[str, Any] = {}

    # Ask if user wants to configure advanced settings at all
    configure = questionary.confirm(
        "Configure advanced settings (gates, reports, notifications)?",
        default=False,
        style=get_style(),
    ).ask()

    if not configure:
        # Return defaults or empty
        for key in ("gates", "reports", "notifications", "harden_runner"):
            if key in defaults and defaults[key]:
                result[key] = defaults[key]
        return result

    # Gates
    gates = configure_gates(defaults)
    if gates:
        result["gates"] = gates

    # Reports
    reports = configure_reports(defaults)
    if reports:
        result["reports"] = reports

    # Notifications
    notifications = configure_notifications(defaults)
    if notifications:
        result["notifications"] = notifications

    # Harden runner
    harden = configure_harden_runner(defaults)
    if harden:
        result["harden_runner"] = harden

    return result
