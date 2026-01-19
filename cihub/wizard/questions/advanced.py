"""Advanced wizard questions for non-tool settings."""

from __future__ import annotations

from typing import Any

import questionary

from cihub.wizard.styles import get_style


def configure_gates(defaults: dict[str, Any]) -> dict[str, Any]:
    """Configure require_run_or_fail gate policy.

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
        "Customize tool run requirements (require_run_or_fail)?",
        default=False,
        style=get_style(),
    ).ask()

    if not customize:
        return gates_defaults

    require_run_default = bool(gates_defaults.get("require_run_or_fail", False))
    require_run = questionary.confirm(
        "Fail CI if a configured tool didn't run?",
        default=require_run_default,
        style=get_style(),
    ).ask()

    tool_defaults = gates_defaults.get("tool_defaults", {})
    if not isinstance(tool_defaults, dict):
        tool_defaults = {}

    overrides: dict[str, Any] = {}
    if tool_defaults:
        customize_tools = questionary.confirm(
            "Customize per-tool require_run_or_fail defaults?",
            default=False,
            style=get_style(),
        ).ask()
        if customize_tools:
            tool_keys = sorted(tool_defaults.keys())
            tool_choices = [
                {
                    "name": key.replace("_", "-"),
                    "value": key,
                    "checked": bool(tool_defaults.get(key, False)),
                }
                for key in tool_keys
            ]
            selected = questionary.checkbox(
                "Select tools that MUST run when configured:",
                choices=tool_choices,
                style=get_style(),
            ).ask()
            selected_set = set(selected or [])
            for key, default_value in tool_defaults.items():
                desired = key in selected_set
                if desired != bool(default_value):
                    overrides[key] = desired

    result: dict[str, Any] = {"require_run_or_fail": require_run}
    if overrides:
        result["tool_defaults"] = overrides

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

    result: dict[str, Any] = {}

    # Badges
    badges_defaults = reports_defaults.get("badges", {})
    badges_enabled_default = (
        bool(badges_defaults.get("enabled", True)) if isinstance(badges_defaults, dict) else bool(badges_defaults)
    )
    badges_branch_default = badges_defaults.get("branch", "main") if isinstance(badges_defaults, dict) else "main"
    badges_enabled = questionary.confirm(
        "Enable badge generation?",
        default=badges_enabled_default,
        style=get_style(),
    ).ask()
    if badges_enabled:
        badges_branch = questionary.text(
            "Badge branch (for status/badge links):",
            default=str(badges_branch_default),
            style=get_style(),
        ).ask()
        result["badges"] = {
            "enabled": True,
            "branch": badges_branch or badges_branch_default,
        }
    else:
        result["badges"] = {"enabled": False}

    # Codecov
    codecov_defaults = reports_defaults.get("codecov", {})
    codecov_enabled_default = (
        bool(codecov_defaults.get("enabled", True)) if isinstance(codecov_defaults, dict) else bool(codecov_defaults)
    )
    codecov_fail_default = (
        bool(codecov_defaults.get("fail_ci_on_error", False)) if isinstance(codecov_defaults, dict) else False
    )
    codecov_enabled = questionary.confirm(
        "Enable Codecov reporting?",
        default=codecov_enabled_default,
        style=get_style(),
    ).ask()
    if codecov_enabled:
        codecov_fail = questionary.confirm(
            "Fail CI if Codecov upload fails?",
            default=codecov_fail_default,
            style=get_style(),
        ).ask()
        result["codecov"] = {"enabled": True, "fail_ci_on_error": bool(codecov_fail)}
    else:
        result["codecov"] = {"enabled": False}

    # GitHub summary
    summary_defaults = reports_defaults.get("github_summary", {})
    summary_enabled_default = (
        bool(summary_defaults.get("enabled", True)) if isinstance(summary_defaults, dict) else bool(summary_defaults)
    )
    summary_include_default = (
        bool(summary_defaults.get("include_metrics", True)) if isinstance(summary_defaults, dict) else True
    )
    summary_enabled = questionary.confirm(
        "Enable GitHub summary output?",
        default=summary_enabled_default,
        style=get_style(),
    ).ask()
    if summary_enabled:
        summary_include = questionary.confirm(
            "Include metrics in GitHub summary?",
            default=summary_include_default,
            style=get_style(),
        ).ask()
        result["github_summary"] = {"enabled": True, "include_metrics": bool(summary_include)}
    else:
        result["github_summary"] = {"enabled": False}

    # Retention
    retention_default = int(reports_defaults.get("retention_days", 30))
    retention_raw = questionary.text(
        "Report retention days (1-365):",
        default=str(retention_default),
        style=get_style(),
    ).ask()
    try:
        retention_days = int(retention_raw) if retention_raw is not None else retention_default
    except (TypeError, ValueError):
        retention_days = retention_default
    result["retention_days"] = retention_days

    return result


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
        "Configure CI notifications (Slack, email)?",
        default=False,
        style=get_style(),
    ).ask()

    if not configure:
        return notifications_defaults

    result: dict[str, Any] = {}

    # Slack configuration
    slack_defaults = notifications_defaults.get("slack", {})
    slack_enabled_default = (
        bool(slack_defaults.get("enabled", False)) if isinstance(slack_defaults, dict) else bool(slack_defaults)
    )
    slack_enabled = questionary.confirm(
        "Enable Slack notifications?",
        default=slack_enabled_default,
        style=get_style(),
    ).ask()

    if slack_enabled:
        slack_defaults = slack_defaults if isinstance(slack_defaults, dict) else {}
        on_failure_default = bool(slack_defaults.get("on_failure", True))
        on_success_default = bool(slack_defaults.get("on_success", False))
        webhook_default = slack_defaults.get("webhook_env", "CIHUB_SLACK_WEBHOOK_URL")

        on_failure = questionary.confirm(
            "Notify on failures?",
            default=on_failure_default,
            style=get_style(),
        ).ask()
        on_success = questionary.confirm(
            "Notify on successes?",
            default=on_success_default,
            style=get_style(),
        ).ask()
        webhook_env = questionary.text(
            "Slack webhook env var:",
            default=webhook_default,
            style=get_style(),
        ).ask()

        result["slack"] = {
            "enabled": True,
            "on_failure": bool(on_failure),
            "on_success": bool(on_success),
            "webhook_env": webhook_env or webhook_default,
        }
    else:
        result["slack"] = {"enabled": False}

    # Email configuration
    email_defaults = notifications_defaults.get("email", {})
    email_enabled_default = (
        bool(email_defaults.get("enabled", False)) if isinstance(email_defaults, dict) else bool(email_defaults)
    )
    email_enabled = questionary.confirm(
        "Enable email notifications?",
        default=email_enabled_default,
        style=get_style(),
    ).ask()
    if email_enabled:
        result["email"] = {"enabled": True}
    else:
        result["email"] = {"enabled": False}

    return result


def configure_harden_runner(defaults: dict[str, Any]) -> dict[str, Any] | bool:
    """Configure GitHub Actions harden-runner settings.

    Args:
        defaults: Current config with defaults

    Returns:
        Harden runner configuration dict
    """
    harden_value: dict[str, Any] | bool = defaults.get("harden_runner", {})
    if isinstance(harden_value, bool):
        policy_default = "audit" if harden_value else "disabled"
    elif isinstance(harden_value, dict):
        policy_default = harden_value.get("policy", "audit")
    else:
        policy_default = "audit"
        harden_value = {}

    # Ask if user wants to configure hardening
    customize = questionary.confirm(
        "Customize GitHub Actions security hardening?",
        default=False,
        style=get_style(),
    ).ask()

    if not customize:
        return harden_value

    policy = questionary.select(
        "Harden-runner policy:",
        choices=[
            {"name": "audit - Log but allow all outbound", "value": "audit"},
            {"name": "block - Block unauthorized outbound (strict)", "value": "block"},
            {"name": "disabled - Do not run harden-runner", "value": "disabled"},
        ],
        default=policy_default,
        style=get_style(),
    ).ask()

    return {
        "policy": policy or "audit",
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
        "Configure advanced settings (gates, reports, notifications, harden_runner)?",
        default=False,
        style=get_style(),
    ).ask()

    if not configure:
        # Return defaults or empty
        for key in ("gates", "reports", "notifications", "harden_runner"):
            if key in defaults:
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
    if harden is not None:
        result["harden_runner"] = harden

    return result
