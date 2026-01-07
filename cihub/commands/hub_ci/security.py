"""Security scanning commands (bandit, pip-audit, OWASP, ruff security)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.env import _parse_env_bool
from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.github_context import OutputContext

from . import (
    _count_pip_audit_vulns,
    _run_command,
    ensure_executable,
)


def _validate_scan_paths(paths: list[str]) -> tuple[list[str], list[str]]:
    """Validate paths for security scanning tools.

    Returns:
        Tuple of (valid_paths, problems)
    """
    valid_paths: list[str] = []
    problems: list[str] = []
    cwd = Path.cwd().resolve()

    for path in paths:
        # Block path traversal attempts
        if ".." in path or path.startswith("/") or "\\" in path:
            problems.append(f"Invalid path (traversal blocked): {path}")
            continue
        # Verify path exists and is within cwd
        try:
            resolved = (cwd / path).resolve()
            resolved.relative_to(cwd)
            if resolved.exists():
                valid_paths.append(path)
            else:
                problems.append(f"Path does not exist: {path}")
        except ValueError:
            problems.append(f"Path escapes working directory: {path}")

    return valid_paths, problems


def cmd_bandit(args: argparse.Namespace) -> CommandResult:
    # Validate scan paths to prevent path traversal
    valid_paths, path_problems = _validate_scan_paths(args.paths)
    if not valid_paths:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="No valid paths to scan",
            problems=[{"severity": "error", "message": p, "code": "CIHUB-BANDIT-PATH"} for p in path_problems],
        )

    output_path = Path(args.output)
    cmd = [
        "bandit",
        "-r",
        *valid_paths,
        "-f",
        "json",
        "-o",
        str(output_path),
        "--severity-level",
        args.severity,
        "--confidence-level",
        args.confidence,
    ]
    _run_command(cmd, Path("."))

    # Count issues by severity
    high = 0
    medium = 0
    low = 0
    if output_path.exists():
        try:
            with output_path.open(encoding="utf-8") as f:
                data = json.load(f)
            results = data.get("results", []) if isinstance(data, dict) else []
            high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
            medium = sum(1 for item in results if item.get("issue_severity") == "MEDIUM")
            low = sum(1 for item in results if item.get("issue_severity") == "LOW")
        except json.JSONDecodeError:
            pass

    total = high + medium + low

    # Write summary with breakdown table
    ctx = OutputContext.from_args(args)
    fail_on_high = getattr(args, "fail_on_high", True)
    fail_on_medium = getattr(args, "fail_on_medium", False)
    fail_on_low = getattr(args, "fail_on_low", False)

    env_fail_high = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_HIGH"))
    env_fail_medium = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_MEDIUM"))
    env_fail_low = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_LOW"))
    if env_fail_high is not None:
        fail_on_high = env_fail_high
    if env_fail_medium is not None:
        fail_on_medium = env_fail_medium
    if env_fail_low is not None:
        fail_on_low = env_fail_low

    summary = (
        "## Bandit SAST\n\n"
        "| Severity | Count | Fail Threshold |\n"
        "|----------|-------|----------------|\n"
        f"| High | {high} | {'enabled' if fail_on_high else 'disabled'} |\n"
        f"| Medium | {medium} | {'enabled' if fail_on_medium else 'disabled'} |\n"
        f"| Low | {low} | {'enabled' if fail_on_low else 'disabled'} |\n"
        f"| **Total** | **{total}** | |\n"
    )
    ctx.write_summary(summary)

    # Check thresholds - fail if any enabled threshold is exceeded
    fail_reasons: list[str] = []

    if fail_on_high and high > 0:
        fail_reasons.append(f"{high} HIGH")
    if fail_on_medium and medium > 0:
        fail_reasons.append(f"{medium} MEDIUM")
    if fail_on_low and low > 0:
        fail_reasons.append(f"{low} LOW")

    result_data = {
        "high": high,
        "medium": medium,
        "low": low,
        "total": total,
        "report_path": str(output_path),
    }

    if fail_reasons:
        # Show details for failing severities (use validated paths)
        try:
            safe_run(
                ["bandit", "-r", *valid_paths, "--severity-level", "low"],
                timeout=TIMEOUT_NETWORK,
                capture_output=False,  # Let output go to terminal
            )
        except (CommandNotFoundError, CommandTimeoutError):
            pass  # Ignore errors in detail output
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Bandit found {', '.join(fail_reasons)} severity issues",
            problems=[{"severity": "error", "message": f"Found {', '.join(fail_reasons)} severity issues"}],
            data=result_data,
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Bandit SAST passed ({total} issues, none exceed thresholds)",
        data=result_data,
    )


def cmd_pip_audit(args: argparse.Namespace) -> CommandResult:
    output_path = Path(args.output)
    cmd = [
        "pip-audit",
        *sum([["-r", req] for req in args.requirements], []),
        "--format",
        "json",
        "--output",
        str(output_path),
    ]
    _run_command(cmd, Path("."))

    vulns = 0
    if output_path.exists():
        try:
            with output_path.open(encoding="utf-8") as f:
                data = json.load(f)
            vulns = _count_pip_audit_vulns(data)
        except json.JSONDecodeError:
            vulns = 0

    ctx = OutputContext.from_args(args)
    ctx.write_summary(f"## Dependency Vulnerabilities\nFound: {vulns}\n")

    result_data = {"vulnerabilities": vulns, "report_path": str(output_path)}

    if vulns > 0:
        try:
            markdown = safe_run(
                ["pip-audit", "--format", "markdown"],
                timeout=TIMEOUT_NETWORK,
            )
            if markdown.stdout:
                ctx.write_summary(markdown.stdout)
        except (CommandNotFoundError, CommandTimeoutError):
            pass  # Skip markdown summary on error
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Found {vulns} dependency vulnerabilities",
            problems=[{"severity": "error", "message": f"Found {vulns} dependency vulnerabilities"}],
            data=result_data,
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="No dependency vulnerabilities found",
        data=result_data,
    )


def cmd_security_pip_audit(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()
    requirements = args.requirements or []

    for req in requirements:
        req_path = repo_path / req
        if not req_path.exists():
            continue
        _run_command(["pip", "install", "-r", str(req_path)], repo_path)

    proc = _run_command(
        ["pip-audit", "--format=json", "--output", str(report_path)],
        repo_path,
    )

    tool_status = "success"
    problems: list[dict[str, str]] = []
    if not report_path.exists():
        report_path.write_text("[]", encoding="utf-8")
        if proc.returncode != 0:
            # Tool failed without producing output - warn but continue
            tool_status = "failed"
            problems.append(
                {
                    "severity": "warning",
                    "message": f"pip-audit failed (exit {proc.returncode}): {proc.stderr or 'no output'}",
                }
            )

    vulns = 0
    try:
        with report_path.open(encoding="utf-8") as f:
            data = json.load(f)
        vulns = _count_pip_audit_vulns(data)
    except json.JSONDecodeError:
        vulns = 0
        if proc.returncode != 0:
            tool_status = "failed"
            problems.append(
                {
                    "severity": "warning",
                    "message": f"pip-audit produced invalid JSON (exit {proc.returncode})",
                }
            )

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"vulnerabilities": str(vulns), "tool_status": tool_status})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"pip-audit: {vulns} vulnerabilities found (status: {tool_status})",
        problems=problems,
        data={"vulnerabilities": vulns, "tool_status": tool_status, "report_path": str(report_path)},
    )


def cmd_security_bandit(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()

    proc = _run_command(
        ["bandit", "-r", ".", "-f", "json", "-o", str(report_path)],
        repo_path,
    )

    tool_status = "success"
    problems: list[dict[str, str]] = []
    if not report_path.exists():
        report_path.write_text('{"results":[]}', encoding="utf-8")
        if proc.returncode != 0:
            # Tool failed without producing output - warn but continue
            tool_status = "failed"
            problems.append(
                {
                    "severity": "warning",
                    "message": f"bandit failed (exit {proc.returncode}): {proc.stderr or 'no output'}",
                }
            )

    high = 0
    try:
        with report_path.open(encoding="utf-8") as f:
            data = json.load(f)
        results = data.get("results", []) if isinstance(data, dict) else []
        high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
    except json.JSONDecodeError:
        high = 0
        if proc.returncode != 0:
            tool_status = "failed"
            problems.append(
                {
                    "severity": "warning",
                    "message": f"bandit produced invalid JSON (exit {proc.returncode})",
                }
            )

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"high": str(high), "tool_status": tool_status})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"bandit: {high} high severity issues (status: {tool_status})",
        problems=problems,
        data={"high": high, "tool_status": tool_status, "report_path": str(report_path)},
    )


def cmd_security_ruff(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()

    proc = _run_command(
        ["ruff", "check", ".", "--select=S", "--output-format=json"],
        repo_path,
    )
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")

    tool_status = "success"
    problems: list[dict[str, str]] = []
    issues = 0
    try:
        with report_path.open(encoding="utf-8") as f:
            data = json.load(f)
        issues = len(data) if isinstance(data, list) else 0
    except json.JSONDecodeError:
        issues = 0
        # ruff returns non-zero when issues found (normal), but invalid JSON is a problem
        tool_status = "failed"
        problems.append(
            {
                "severity": "warning",
                "message": f"ruff produced invalid JSON (exit {proc.returncode}): {proc.stderr or 'no output'}",
            }
        )

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"issues": str(issues), "tool_status": tool_status})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"ruff security: {issues} issues (status: {tool_status})",
        problems=problems,
        data={"issues": issues, "tool_status": tool_status, "report_path": str(report_path)},
    )


def cmd_security_owasp(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    tool_status = "success"
    problems: list[dict[str, str]] = []
    proc = None
    if ensure_executable(mvnw):
        proc = _run_command(
            ["./mvnw", "-B", "-ntp", "org.owasp:dependency-check-maven:check", "-DfailBuildOnCVSS=11"],
            repo_path,
        )
    else:
        tool_status = "skipped"

    reports = list(repo_path.rglob("dependency-check-report.json"))
    report_path = reports[0] if reports else None
    critical = 0
    high = 0
    if report_path and report_path.exists():
        try:
            with report_path.open(encoding="utf-8") as f:
                data = json.load(f)
            dependencies = data.get("dependencies", []) if isinstance(data, dict) else []
            for dep in dependencies:
                vulns = dep.get("vulnerabilities", []) if isinstance(dep, dict) else []
                for vuln in vulns:
                    severity = str(vuln.get("severity", "")).upper()
                    if severity == "CRITICAL":
                        critical += 1
                    elif severity == "HIGH":
                        high += 1
        except json.JSONDecodeError:
            critical = 0
            high = 0
            if proc and proc.returncode != 0:
                tool_status = "failed"
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"OWASP dependency-check produced invalid JSON (exit {proc.returncode})",
                    }
                )
    elif proc and proc.returncode != 0:
        # Tool ran but produced no report
        tool_status = "failed"
        problems.append(
            {
                "severity": "warning",
                "message": f"OWASP dependency-check failed (exit {proc.returncode}): no report generated",
            }
        )

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"critical": str(critical), "high": str(high), "tool_status": tool_status})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"OWASP: {critical} critical, {high} high (status: {tool_status})",
        problems=problems,
        data={
            "critical": critical,
            "high": high,
            "tool_status": tool_status,
            "report_path": str(report_path) if report_path else None,
        },
    )
