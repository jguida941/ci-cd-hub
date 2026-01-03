"""Slack and email notification helpers."""

from __future__ import annotations

import json
import smtplib
import urllib.request
from email.message import EmailMessage
from typing import Any, Mapping

from .helpers import _get_env_name, _get_env_value, _parse_env_bool


def _send_slack(
    webhook_url: str,
    message: str,
    problems: list[dict[str, Any]],
) -> None:
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            if resp.status >= 400:
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Slack notification failed with status {resp.status}",
                        "code": "CIHUB-CI-SLACK-FAILED",
                    }
                )
    except Exception as exc:  # pragma: no cover - network dependent
        problems.append(
            {
                "severity": "warning",
                "message": f"Slack notification failed: {exc}",
                "code": "CIHUB-CI-SLACK-FAILED",
            }
        )


def _send_email(
    subject: str,
    body: str,
    problems: list[dict[str, Any]],
    email_cfg: dict[str, Any],
    env: Mapping[str, str],
) -> None:
    host_name = _get_env_name(email_cfg, "smtp_host_env", "SMTP_HOST")
    host = _get_env_value(env, host_name)
    if not host:
        problems.append(
            {
                "severity": "warning",
                "message": f"Email notifications enabled but {host_name} is not set",
                "code": "CIHUB-CI-EMAIL-MISSING",
            }
        )
        return
    port_name = _get_env_name(email_cfg, "smtp_port_env", "SMTP_PORT")
    port_value = _get_env_value(env, port_name)
    port = 25
    if port_value:
        try:
            port = int(port_value)
        except ValueError:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Email notifications enabled but {port_name} is not a valid port",
                    "code": "CIHUB-CI-EMAIL-MISSING",
                }
            )
            port = 25

    username = _get_env_value(env, _get_env_name(email_cfg, "smtp_user_env", "SMTP_USER"))
    password = _get_env_value(env, _get_env_name(email_cfg, "smtp_password_env", "SMTP_PASSWORD"))
    starttls_value = _get_env_value(
        env,
        _get_env_name(email_cfg, "smtp_starttls_env", "SMTP_STARTTLS"),
    )
    use_starttls = _parse_env_bool(starttls_value) or False
    sender = _get_env_value(env, _get_env_name(email_cfg, "smtp_from_env", "SMTP_FROM")) or "cihub@localhost"
    recipients_name = _get_env_name(email_cfg, "recipients_env", "CIHUB_EMAIL_TO")
    recipients = _get_env_value(env, recipients_name, ["SMTP_TO", "EMAIL_TO"])
    if not recipients:
        problems.append(
            {
                "severity": "warning",
                "message": (f"Email notifications enabled but no recipients set ({recipients_name}/SMTP_TO/EMAIL_TO)"),
                "code": "CIHUB-CI-EMAIL-MISSING",
            }
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipients
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as client:
            if use_starttls:
                client.starttls()
            if username and password:
                client.login(username, password)
            client.send_message(msg)
    except Exception as exc:  # pragma: no cover - network dependent
        problems.append(
            {
                "severity": "warning",
                "message": f"Email notification failed: {exc}",
                "code": "CIHUB-CI-EMAIL-FAILED",
            }
        )


def _notify(
    success: bool,
    config: dict[str, Any],
    report: dict[str, Any],
    problems: list[dict[str, Any]],
    env: Mapping[str, str],
) -> None:
    notifications = config.get("notifications", {}) or {}
    slack_cfg = notifications.get("slack", {}) or {}
    email_cfg = notifications.get("email", {}) or {}

    repo = report.get("repository", "") or report.get("repo", "") or "unknown"
    branch = report.get("branch", "") or "unknown"
    status = "SUCCESS" if success else "FAILURE"

    if slack_cfg.get("enabled", False):
        on_success = bool(slack_cfg.get("on_success", False))
        on_failure = bool(slack_cfg.get("on_failure", True))
        if (success and on_success) or (not success and on_failure):
            webhook_name = _get_env_name(slack_cfg, "webhook_env", "CIHUB_SLACK_WEBHOOK_URL")
            webhook = _get_env_value(env, webhook_name, ["SLACK_WEBHOOK_URL", "SLACK_WEBHOOK"])
            if not webhook:
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Slack notifications enabled but {webhook_name} is not set",
                        "code": "CIHUB-CI-SLACK-MISSING",
                    }
                )
            else:
                _send_slack(webhook, f"CIHUB {status}: {repo} ({branch})", problems)

    if email_cfg.get("enabled", False):
        _send_email(
            f"CIHUB {status}: {repo}",
            f"Repository: {repo}\nBranch: {branch}\nStatus: {status}\n",
            problems,
            email_cfg,
            env,
        )
