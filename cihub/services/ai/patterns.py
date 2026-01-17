"""Pattern-based fix suggestions for the AI loop."""

from __future__ import annotations

from typing import Any

_TOOL_HINTS: dict[str, tuple[str, str]] = {
    "ruff": (
        "CIHUB-AI-TOOL-RUFF",
        "Run `cihub fix --safe` or `cihub run ruff` to address lint issues.",
    ),
    "black": (
        "CIHUB-AI-TOOL-BLACK",
        "Run `cihub fix --safe` or `cihub run black` to address formatting issues.",
    ),
    "isort": (
        "CIHUB-AI-TOOL-ISORT",
        "Run `cihub fix --safe` or `cihub run isort` to address import ordering issues.",
    ),
    "mypy": (
        "CIHUB-AI-TOOL-MYPY",
        "Inspect type errors in `.cihub/tool-outputs/mypy/` and rerun `cihub run mypy`.",
    ),
    "pytest": (
        "CIHUB-AI-TOOL-PYTEST",
        "Inspect `.cihub/tool-outputs/pytest/` and rerun `cihub run pytest`.",
    ),
    "bandit": (
        "CIHUB-AI-TOOL-BANDIT",
        "Review `.cihub/tool-outputs/bandit/` and address security findings.",
    ),
    "pip_audit": (
        "CIHUB-AI-TOOL-PIP-AUDIT",
        "Update vulnerable dependencies and rerun `cihub run pip-audit`.",
    ),
    "semgrep": (
        "CIHUB-AI-TOOL-SEMGREP",
        "Review `.cihub/tool-outputs/semgrep/` and address findings.",
    ),
    "trivy": (
        "CIHUB-AI-TOOL-TRIVY",
        "Review `.cihub/tool-outputs/trivy/` and address vulnerabilities.",
    ),
    "checkstyle": (
        "CIHUB-AI-TOOL-CHECKSTYLE",
        "Review `.cihub/tool-outputs/checkstyle/` for violations.",
    ),
    "spotbugs": (
        "CIHUB-AI-TOOL-SPOTBUGS",
        "Review `.cihub/tool-outputs/spotbugs/` for findings.",
    ),
    "pmd": (
        "CIHUB-AI-TOOL-PMD",
        "Review `.cihub/tool-outputs/pmd/` for violations.",
    ),
    "owasp": (
        "CIHUB-AI-TOOL-OWASP",
        "Review `.cihub/tool-outputs/owasp/` and address dependency risks.",
    ),
    "docker": (
        "CIHUB-AI-TOOL-DOCKER",
        "Verify docker-compose files and inspect `.cihub/tool-outputs/docker/`.",
    ),
}

_PROBLEM_HINTS: dict[str, tuple[str, str]] = {
    "CIHUB-CI-DEPS": (
        "CIHUB-AI-CI-DEPS",
        "Dependency install failed; rerun with `cihub ci --install-deps` or update dependency commands.",
    ),
    "CIHUB-CI-MISSING-TOOL": (
        "CIHUB-AI-CI-MISSING-TOOL",
        "Install the missing tool or disable it in `.ci-hub.yml`.",
    ),
    "CIHUB-CI-UNSUPPORTED": (
        "CIHUB-AI-CI-UNSUPPORTED",
        "Tool is unsupported by cihub; run it via a workflow step or remove it from config.",
    ),
    "CIHUB-CI-LANGUAGE": (
        "CIHUB-AI-CI-LANGUAGE",
        "Run `cihub detect` or set the repo language in `.ci-hub.yml`.",
    ),
}


def _add_suggestion(
    suggestions: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    code: str,
    message: str,
) -> None:
    key = (code, message)
    if key in seen:
        return
    seen.add(key)
    suggestions.append({"message": message, "code": code})


def suggest_from_failures(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for failure in failures:
        tool = str(failure.get("tool", "")).lower()
        status = str(failure.get("status", "")).lower()
        reason = str(failure.get("reason", "")).lower()

        if status == "required_not_run" or reason == "tool_required_not_run":
            _add_suggestion(
                suggestions,
                seen,
                "CIHUB-AI-TOOL-REQUIRED",
                "A required tool did not run; verify config and required files or disable the tool.",
            )

        hint = _TOOL_HINTS.get(tool)
        if hint:
            _add_suggestion(suggestions, seen, hint[0], hint[1])

    return suggestions


def suggest_from_problems(problems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for problem in problems:
        code = str(problem.get("code", "")).upper()
        hint = _PROBLEM_HINTS.get(code)
        if hint:
            _add_suggestion(suggestions, seen, hint[0], hint[1])

    return suggestions


def collect_suggestions(
    problems: list[dict[str, Any]] | None,
    failures: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for suggestion in suggest_from_problems(problems or []):
        _add_suggestion(combined, seen, suggestion["code"], suggestion["message"])

    for suggestion in suggest_from_failures(failures or []):
        _add_suggestion(combined, seen, suggestion["code"], suggestion["message"])

    return combined
