"""Log parsing utilities for extracting failures from GitHub Actions logs.

This module handles parsing the output from `gh run view --log-failed`
to extract structured failure information when artifacts are unavailable.
"""

from __future__ import annotations

import re
from typing import Any

from cihub.services.triage_service import CATEGORY_BY_TOOL, SEVERITY_BY_CATEGORY

from .types import MAX_ERRORS_IN_TRIAGE


def extract_pytest_info(logs: str) -> dict[str, Any]:
    """Extract pytest-specific information from logs.

    Args:
        logs: Raw log content

    Returns:
        Dict with pytest metrics: failed_tests, passed, failed, error messages
    """
    info: dict[str, Any] = {"failed_tests": [], "summary": ""}

    # Find FAILED test lines: "FAILED tests/test_foo.py::TestClass::test_method"
    failed_pattern = re.compile(r"FAILED\s+(tests/\S+::\S+)")
    for match in failed_pattern.finditer(logs):
        info["failed_tests"].append(match.group(1))

    # Find summary line: "1 failed, 100 passed, 5 skipped"
    summary_pattern = re.compile(r"(\d+\s+failed.*(?:passed|skipped).*)")
    summary_match = summary_pattern.search(logs)
    if summary_match:
        info["summary"] = summary_match.group(1).strip()

    # Find assertion errors
    assertion_pattern = re.compile(r"AssertionError:\s*(.+?)(?:\n|$)")
    assertions = assertion_pattern.findall(logs)
    if assertions:
        info["assertions"] = assertions[:5]  # Limit to 5

    return info


def extract_mutmut_info(logs: str) -> dict[str, Any]:
    """Extract mutmut-specific information from logs.

    Args:
        logs: Raw log content

    Returns:
        Dict with mutmut metrics: mutation_score, killed, survived, etc.
    """
    info: dict[str, Any] = {}

    # Look for mutation score output patterns
    # Pattern: "Mutation score: 85%" or "mutation_score=85"
    score_pattern = re.compile(r"(?:mutation[_\s]?score|score)[:\s=]+(\d+)%?", re.IGNORECASE)
    score_match = score_pattern.search(logs)
    if score_match:
        info["mutation_score"] = int(score_match.group(1))

    # Look for killed/survived counts from mutmut output
    # mutmut uses emojis in output, but also has text summaries
    killed_pattern = re.compile(r"(?:killed|Killed)[:\s=]+(\d+)")
    survived_pattern = re.compile(r"(?:survived|Survived)[:\s=]+(\d+)")

    killed_match = killed_pattern.search(logs)
    survived_match = survived_pattern.search(logs)

    if killed_match:
        info["killed"] = int(killed_match.group(1))
    if survived_match:
        info["survived"] = int(survived_match.group(1))

    # Check for common mutmut failure messages
    if "mutmut run failed" in logs:
        info["error"] = "mutmut run failed"
    if "No mutants were tested" in logs:
        info["error"] = "No mutants were tested - check test coverage"
    if "check for import errors" in logs:
        info["hint"] = "Check for import errors or test failures in mutation targets"

    return info


def infer_tool_from_step(step: str) -> str:
    """Infer tool name from workflow step name.

    Args:
        step: Name of the workflow step (e.g., "[Python] Ruff Lint")

    Returns:
        Inferred tool name (e.g., "ruff")
    """
    step_lower = step.lower()

    if "mypy" in step_lower or "typecheck" in step_lower:
        return "mypy"
    if "ruff" in step_lower:
        return "ruff"
    if "mutmut" in step_lower or "mutation" in step_lower:
        return "mutmut"
    if "pytest" in step_lower or "unit test" in step_lower:
        return "pytest"
    if "bandit" in step_lower:
        return "bandit"
    if "pip-audit" in step_lower or "pip_audit" in step_lower:
        return "pip_audit"
    if "checkstyle" in step_lower:
        return "checkstyle"
    if "spotbugs" in step_lower:
        return "spotbugs"
    if "actionlint" in step_lower:
        return "actionlint"

    return "workflow"


def create_log_failure(
    job: str,
    step: str,
    errors: list[str],
    run_id: str = "",
    repo: str | None = None,
    raw_logs: str = "",
) -> dict[str, Any]:
    """Create a failure entry from log parsing.

    Args:
        job: Name of the failed job
        step: Name of the failed step
        errors: List of error messages extracted from logs
        run_id: GitHub workflow run ID (for reproduce command)
        repo: Repository in owner/repo format
        raw_logs: Full raw log content for tool-specific parsing

    Returns:
        Failure dict matching triage bundle schema
    """
    tool = infer_tool_from_step(step)
    category = CATEGORY_BY_TOOL.get(tool, "workflow")
    severity = SEVERITY_BY_CATEGORY.get(category, "medium")

    # Build reproduce command with run_id if available
    reproduce_cmd = f"gh run view {run_id} --log-failed" if run_id else "gh run view --log-failed"
    if repo:
        reproduce_cmd += f" --repo {repo}"

    # Start with default hints
    hints = [
        f"Review the {step} step output for details",
        "Check the error messages above for specific fixes",
    ]

    # Tool-specific parsing and hints
    tool_info: dict[str, Any] = {}

    if tool == "pytest" and raw_logs:
        tool_info = extract_pytest_info(raw_logs)
        if tool_info.get("failed_tests"):
            hints.insert(0, f"Failed tests: {', '.join(tool_info['failed_tests'][:3])}")
        if tool_info.get("summary"):
            hints.insert(0, f"Test summary: {tool_info['summary']}")

    elif tool == "mutmut" and raw_logs:
        tool_info = extract_mutmut_info(raw_logs)
        if tool_info.get("mutation_score") is not None:
            hints.insert(0, f"Mutation score: {tool_info['mutation_score']}%")
        if tool_info.get("killed") is not None and tool_info.get("survived") is not None:
            hints.insert(0, f"Mutants: {tool_info['killed']} killed, {tool_info['survived']} survived")
        if tool_info.get("error"):
            hints.insert(0, tool_info["error"])
        if tool_info.get("hint"):
            hints.insert(0, tool_info["hint"])

    return {
        "id": f"{tool}:{job}:{step}",
        "category": category,
        "severity": severity,
        "tool": tool,
        "status": "failed",
        "reason": "workflow_failed",
        "message": f"{job} / {step}: {len(errors)} error(s)",
        "job": job,
        "step": step,
        "errors": errors[:MAX_ERRORS_IN_TRIAGE],
        "artifacts": [],
        "reproduce": {"command": reproduce_cmd, "cwd": ".", "env": {}},
        "hints": hints,
        "tool_info": tool_info if tool_info else None,
    }


def parse_log_failures(
    logs: str,
    run_id: str = "",
    repo: str | None = None,
) -> list[dict[str, Any]]:
    """Parse failure information from gh run view --log-failed output.

    The log format is:
        JobName\\tStepName\\tTimestamp Message
        ...
        ##[error]Error message

    Args:
        logs: Raw log output from gh run view --log-failed
        run_id: GitHub workflow run ID (for reproduce commands)
        repo: Repository in owner/repo format

    Returns:
        List of failure dicts extracted from logs
    """
    failures: list[dict[str, Any]] = []
    current_job = ""
    current_step = ""
    error_lines: list[str] = []
    step_logs: list[str] = []  # Collect all lines for current step

    for line in logs.split("\n"):
        # Detect job/step headers (format: "JobName\tStepName\tTimestamp Message")
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 2:
                job = parts[0].strip()
                step = parts[1].strip()
                if job and job != current_job:
                    current_job = job
                if step and step != current_step:
                    # Save previous errors with raw logs for tool-specific parsing
                    if error_lines and current_step:
                        raw_step_logs = "\n".join(step_logs)
                        failures.append(
                            create_log_failure(current_job, current_step, error_lines, run_id, repo, raw_step_logs)
                        )
                    current_step = step
                    error_lines = []
                    step_logs = []

        # Collect all lines for current step (for tool-specific parsing)
        step_logs.append(line)

        # Detect error annotations
        if "##[error]" in line:
            error_msg = line.split("##[error]", 1)[1].strip() if "##[error]" in line else line
            error_lines.append(error_msg)
        elif "error:" in line.lower() and current_step:
            error_lines.append(line.strip())
        # Also capture FAILED test lines for pytest
        elif "FAILED " in line and current_step:
            error_lines.append(line.strip())

    # Save last batch
    if error_lines and current_step:
        raw_step_logs = "\n".join(step_logs)
        failures.append(create_log_failure(current_job, current_step, error_lines, run_id, repo, raw_step_logs))

    return failures


def _is_unknown_label(value: str, label: str) -> bool:
    text = value.strip().upper()
    return text.startswith(label)


def _select_failed_step(steps: list[dict[str, Any]]) -> str | None:
    failure_conclusions = {"failure", "cancelled", "timed_out", "action_required"}
    for step in steps:
        conclusion = str(step.get("conclusion", "")).lower()
        if conclusion in failure_conclusions:
            name = step.get("name")
            if name:
                return str(name)
    return None


def _select_failed_job(jobs: list[dict[str, Any]]) -> dict[str, Any] | None:
    failure_conclusions = {"failure", "cancelled", "timed_out", "action_required"}
    for job in jobs:
        conclusion = str(job.get("conclusion", "")).lower()
        if conclusion in failure_conclusions:
            return job
    return None


def resolve_unknown_steps(
    failures: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Replace UNKNOWN STEP entries using run metadata from gh --json jobs."""
    if not failures or not jobs:
        return failures, 0

    jobs_by_name = {job.get("name"): job for job in jobs if job.get("name")}
    resolved = 0

    for failure in failures:
        step_name = str(failure.get("step", ""))
        if not _is_unknown_label(step_name, "UNKNOWN STEP"):
            continue

        job_name = str(failure.get("job", ""))
        job = jobs_by_name.get(job_name)
        if not job and (not job_name or _is_unknown_label(job_name, "UNKNOWN JOB")):
            job = _select_failed_job(jobs)
        if not job:
            continue

        resolved_step = _select_failed_step(job.get("steps") or [])
        if not resolved_step:
            continue

        if not job_name or _is_unknown_label(job_name, "UNKNOWN JOB"):
            job_label = job.get("name")
            if job_label:
                job_name = str(job_label)
                failure["job"] = job_name

        tool = infer_tool_from_step(resolved_step)
        category = CATEGORY_BY_TOOL.get(tool, "workflow")
        severity = SEVERITY_BY_CATEGORY.get(category, "medium")

        errors = failure.get("errors") or []
        failure["step"] = resolved_step
        failure["tool"] = tool
        failure["category"] = category
        failure["severity"] = severity
        failure["id"] = f"{tool}:{job_name}:{resolved_step}"
        failure["message"] = f"{job_name} / {resolved_step}: {len(errors)} error(s)"

        hints = list(failure.get("hints") or [])
        if hints:
            hints[0] = f"Review the {resolved_step} step output for details"
        else:
            hints = [f"Review the {resolved_step} step output for details"]
        failure["hints"] = hints

        resolved += 1

    return failures, resolved


__all__ = [
    "create_log_failure",
    "extract_mutmut_info",
    "extract_pytest_info",
    "infer_tool_from_step",
    "parse_log_failures",
    "resolve_unknown_steps",
]
