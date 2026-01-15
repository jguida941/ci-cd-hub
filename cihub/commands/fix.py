"""Fix command - run auto-fixers or report issues for manual review.

cihub fix --safe: Run all auto-fixers (ruff --fix, black, isort for Python; spotless for Java)
cihub fix --report: Run all analyzers and report issues for manual review
cihub fix --report --ai: Generate AI-consumable markdown report
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.detection import detect_language
from cihub.types import CommandResult
from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)

# Tool categories for severity mapping
TOOL_CATEGORIES = {
    # Python tools
    "bandit": ("security", 8),
    "pip_audit": ("security", 8),
    "mypy": ("types", 6),
    "semgrep": ("security", 9),
    "trivy": ("security", 9),
    # Java tools
    "spotbugs": ("bugs", 7),
    "checkstyle": ("lint", 4),
    "pmd": ("lint", 4),
    "owasp": ("security", 8),
}


def _tool_installed(tool: str) -> bool:
    """Check if a tool is installed and available."""
    try:
        result = safe_run(["which", tool], timeout=5000)
        return result.returncode == 0
    except (CommandNotFoundError, CommandTimeoutError, FileNotFoundError):
        return False


def _run_tool(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a tool and return (returncode, stdout, stderr)."""
    try:
        result = safe_run(cmd, cwd=cwd, timeout=TIMEOUT_BUILD)
        return result.returncode, result.stdout or "", result.stderr or ""
    except CommandNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except CommandTimeoutError:
        return -1, "", f"Command timed out: {' '.join(cmd)}"


def _run_safe_fixes(repo_path: Path, language: str, dry_run: bool) -> CommandResult:
    """Run all auto-fixers for the detected language."""
    fixes_applied: list[str] = []
    errors: list[dict[str, Any]] = []

    if language == "python":
        python_tools = [
            (["ruff", "check", "--fix", "."], "ruff"),
            (["black", "."], "black"),
            (["isort", "."], "isort"),
        ]
        for cmd, name in python_tools:
            if dry_run:
                fixes_applied.append(f"{name} (dry-run)")
                continue
            if _tool_installed(name):
                rc, stdout, stderr = _run_tool(cmd, repo_path)
                if rc == 0:
                    fixes_applied.append(name)
                else:
                    errors.append(
                        {
                            "severity": "warning",
                            "message": f"{name} failed: {stderr[:200]}",
                            "code": f"CIHUB-FIX-{name.upper()}-FAILED",
                        }
                    )
            else:
                errors.append(
                    {
                        "severity": "warning",
                        "message": f"{name} not installed, skipping",
                        "code": f"CIHUB-FIX-{name.upper()}-MISSING",
                    }
                )

    elif language == "java":
        if (repo_path / "pom.xml").exists():
            cmd = ["mvn", "spotless:apply", "-q"]
            name = "spotless (maven)"
        elif (repo_path / "build.gradle").exists() or (repo_path / "build.gradle.kts").exists():
            cmd = ["./gradlew", "spotlessApply", "-q"]
            name = "spotless (gradle)"
        else:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="No pom.xml or build.gradle found",
                problems=[{"severity": "error", "message": "Cannot run spotless without build file"}],
            )

        if dry_run:
            fixes_applied.append(f"{name} (dry-run)")
        else:
            rc, stdout, stderr = _run_tool(cmd, repo_path)
            if rc == 0:
                fixes_applied.append(name)
            else:
                errors.append(
                    {
                        "severity": "error",
                        "message": f"spotless failed: {stderr[:200]}",
                        "code": "CIHUB-FIX-SPOTLESS-FAILED",
                    }
                )

    else:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Unsupported language: {language}",
            problems=[{"severity": "error", "message": f"fix --safe not supported for {language}"}],
        )

    if not fixes_applied and errors:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="No fixes applied due to errors",
            problems=errors,
            data={"fixes": [], "language": language},
        )

    verb = "Would apply" if dry_run else "Applied"
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"{verb} fixes: {', '.join(fixes_applied) or 'none'}",
        problems=errors if errors else [],
        data={"fixes": fixes_applied, "language": language},
    )


def _run_report(repo_path: Path, language: str) -> dict[str, list[dict[str, Any]]]:
    """Run all analyzers and collect issues."""
    all_issues: dict[str, list[dict[str, Any]]] = {}

    if language == "python":
        # mypy - type checking
        if _tool_installed("mypy"):
            rc, stdout, stderr = _run_tool(["mypy", ".", "--ignore-missing-imports"], repo_path)
            if rc != 0:
                issues = []
                for line in stdout.splitlines():
                    if ": error:" in line:
                        issues.append({"message": line.strip(), "severity": "error"})
                all_issues["mypy"] = issues

        # bandit - security
        if _tool_installed("bandit"):
            rc, stdout, stderr = _run_tool(["bandit", "-r", ".", "-f", "json", "-q"], repo_path)
            try:
                data = json.loads(stdout)
                issues = [
                    {
                        "message": f"{r['issue_text']} at {r['filename']}:{r['line_number']}",
                        "severity": r.get("issue_severity", "MEDIUM").lower(),
                        "location": f"{r['filename']}:{r['line_number']}",
                    }
                    for r in data.get("results", [])
                ]
                all_issues["bandit"] = issues
            except json.JSONDecodeError as e:
                all_issues["bandit"] = [
                    {"message": f"Failed to parse bandit JSON output: {e}", "severity": "error", "parse_error": True}
                ]

        # pip-audit - dependency vulnerabilities
        if _tool_installed("pip-audit"):
            rc, stdout, stderr = _run_tool(["pip-audit", "--format", "json"], repo_path)
            try:
                data = json.loads(stdout)
                issues = [
                    {
                        "message": f"{v['name']} {v['version']}: {v.get('description', 'vulnerability')}",
                        "severity": "high",
                        "package": v["name"],
                    }
                    for v in data
                    if isinstance(v, dict)
                ]
                all_issues["pip_audit"] = issues
            except json.JSONDecodeError as e:
                all_issues["pip_audit"] = [
                    {"message": f"Failed to parse pip-audit JSON output: {e}", "severity": "error", "parse_error": True}
                ]

    elif language == "java":
        # spotbugs
        if (repo_path / "pom.xml").exists():
            rc, stdout, stderr = _run_tool(["mvn", "spotbugs:check", "-q"], repo_path)
            if rc != 0:
                # Parse spotbugs output (simplified - actual parsing would need XML)
                all_issues["spotbugs"] = [{"message": "SpotBugs found issues", "severity": "medium"}]

            # checkstyle
            rc, stdout, stderr = _run_tool(["mvn", "checkstyle:check", "-q"], repo_path)
            if rc != 0:
                all_issues["checkstyle"] = [{"message": "Checkstyle found violations", "severity": "low"}]

            # pmd
            rc, stdout, stderr = _run_tool(["mvn", "pmd:check", "-q"], repo_path)
            if rc != 0:
                all_issues["pmd"] = [{"message": "PMD found issues", "severity": "low"}]

            # owasp dependency-check
            rc, stdout, stderr = _run_tool(["mvn", "dependency-check:check", "-q"], repo_path)
            if rc != 0:
                all_issues["owasp"] = [{"message": "OWASP found vulnerable dependencies", "severity": "high"}]

    return all_issues


def _generate_ai_report(repo_path: Path, language: str, all_issues: dict[str, list[dict[str, Any]]]) -> str:
    """Generate AI-consumable markdown report."""
    now = datetime.now(timezone.utc).isoformat()
    total = sum(len(v) for v in all_issues.values())

    # Group by severity
    by_severity: dict[str, list[tuple[str, dict[str, Any]]]] = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": [],
    }

    for tool, issues in all_issues.items():
        category, default_sev = TOOL_CATEGORIES.get(tool, ("other", 5))
        for issue in issues:
            sev = issue.get("severity", "medium").lower()
            if sev in by_severity:
                by_severity[sev].append((tool, issue))

    lines = [
        "# Fix Report",
        "",
        f"**Repo:** {repo_path.resolve().name}",
        f"**Language:** {language}",
        f"**Time:** {now}",
        "",
        "## Summary",
        f"- Total issues: {total}",
    ]

    # Add category summaries
    for tool, issues in all_issues.items():
        category, _ = TOOL_CATEGORIES.get(tool, ("other", 5))
        lines.append(f"- {category.title()} ({tool}): {len(issues)}")

    lines.extend(["", "## Critical Issues (fix first)"])

    if by_severity["critical"] or by_severity["high"]:
        lines.append("| Sev | Tool | Issue | Location |")
        lines.append("|-----|------|-------|----------|")
        for sev_name in ["critical", "high"]:
            for tool, issue in by_severity[sev_name]:
                loc = issue.get("location", "-")
                msg = issue.get("message", "")[:60]
                lines.append(f"| {sev_name.upper()} | {tool} | {msg} | {loc} |")
    else:
        lines.append("No critical or high severity issues found.")

    lines.extend(["", "## By Tool"])
    for tool, issues in all_issues.items():
        if issues:
            lines.append(f"### {tool} ({len(issues)} issues)")
            for issue in issues[:10]:  # Limit to first 10
                sev = issue.get("severity", "medium").upper()
                msg = issue.get("message", "Unknown issue")
                lines.append(f"- [{sev}] {msg}")
            if len(issues) > 10:
                lines.append(f"- ... and {len(issues) - 10} more")
            lines.append("")

    return "\n".join(lines)


def cmd_fix(args: argparse.Namespace) -> CommandResult:
    """Run fixers or report issues for manual review."""
    repo_path = Path(getattr(args, "repo", None) or ".").resolve()
    safe_mode = getattr(args, "safe", False)
    report_mode = getattr(args, "report", False)
    ai_mode = getattr(args, "ai", False)
    dry_run = getattr(args, "dry_run", False)

    # Validate flag combinations
    if safe_mode and ai_mode:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--ai requires --report mode",
            problems=[
                {
                    "severity": "error",
                    "message": "--ai only works with --report, not --safe",
                    "code": "CIHUB-FIX-INVALID-FLAGS",
                }
            ],
        )

    if report_mode and dry_run:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--dry-run requires --safe mode",
            problems=[
                {
                    "severity": "error",
                    "message": "--dry-run only works with --safe, not --report",
                    "code": "CIHUB-FIX-INVALID-FLAGS",
                }
            ],
        )

    if not safe_mode and not report_mode:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Must specify --safe or --report",
            problems=[{"severity": "error", "message": "Use --safe for auto-fixes or --report for analysis"}],
        )

    if not repo_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repo path not found: {repo_path}",
            problems=[{"severity": "error", "message": f"Path does not exist: {repo_path}"}],
        )

    # Detect language
    language, reasons = detect_language(repo_path)
    if not language:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Could not detect language",
            problems=[{"severity": "error", "message": f"Detection failed: {', '.join(reasons)}"}],
        )

    if safe_mode:
        return _run_safe_fixes(repo_path, language, dry_run)

    # Report mode
    all_issues = _run_report(repo_path, language)
    total = sum(len(v) for v in all_issues.values())

    if ai_mode:
        ai_report = _generate_ai_report(repo_path, language, all_issues)
        output_dir = repo_path / ".cihub"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "fix-report.md"
        output_file.write_text(ai_report, encoding="utf-8")

        return CommandResult(
            exit_code=EXIT_SUCCESS if total == 0 else EXIT_FAILURE,
            summary=f"Found {total} issues across {len(all_issues)} tools (AI report: {output_file})",
            files_generated=[str(output_file)],
            data={
                "issues": all_issues,
                "language": language,
                "total": total,
                "ai_output": str(output_file),
            },
        )

    # Human-readable output
    problems = []
    for tool, issues in all_issues.items():
        for issue in issues:
            problems.append(
                {
                    "severity": issue.get("severity", "warning"),
                    "message": f"[{tool}] {issue.get('message', 'Issue found')}",
                    "code": f"CIHUB-FIX-{tool.upper()}",
                }
            )

    return CommandResult(
        exit_code=EXIT_SUCCESS if total == 0 else EXIT_FAILURE,
        summary=f"Found {total} issues across {len(all_issues)} tools",
        problems=problems,
        data={"issues": all_issues, "language": language, "total": total},
    )
