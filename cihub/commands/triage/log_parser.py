"""Log parsing utilities for extracting failures from GitHub Actions logs.

This module handles parsing the output from `gh run view --log-failed`
to extract structured failure information when artifacts are unavailable.
"""

from __future__ import annotations

from typing import Any

from cihub.services.triage_service import CATEGORY_BY_TOOL, SEVERITY_BY_CATEGORY

from .types import MAX_ERRORS_IN_TRIAGE


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
    if "pytest" in step_lower or "test" in step_lower:
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
) -> dict[str, Any]:
    """Create a failure entry from log parsing.

    Args:
        job: Name of the failed job
        step: Name of the failed step
        errors: List of error messages extracted from logs
        run_id: GitHub workflow run ID (for reproduce command)
        repo: Repository in owner/repo format

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
        "hints": [
            f"Review the {step} step output for details",
            "Check the error messages above for specific fixes",
        ],
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
                    # Save previous errors
                    if error_lines and current_step:
                        failures.append(create_log_failure(current_job, current_step, error_lines, run_id, repo))
                    current_step = step
                    error_lines = []

        # Detect error annotations
        if "##[error]" in line:
            error_msg = line.split("##[error]", 1)[1].strip() if "##[error]" in line else line
            error_lines.append(error_msg)
        elif "error:" in line.lower() and current_step:
            error_lines.append(line.strip())

    # Save last batch
    if error_lines and current_step:
        failures.append(create_log_failure(current_job, current_step, error_lines, run_id, repo))

    return failures


__all__ = [
    "create_log_failure",
    "infer_tool_from_step",
    "parse_log_failures",
]
