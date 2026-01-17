"""Emit GitHub Actions outputs from .ci-hub.yml."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config
from cihub.config import tool_enabled as _tool_enabled_canonical
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult


def _get_value(data: dict[str, Any], path: list[str], default: Any) -> Any:
    cursor: Any = data
    for key in path:
        if not isinstance(cursor, dict):
            return default
        cursor = cursor.get(key)
    if cursor is None:
        return default
    return cursor


def _get_str(data: dict[str, Any], path: list[str], default: str) -> str:
    return str(_get_value(data, path, default))


def _get_int(data: dict[str, Any], path: list[str], default: int) -> int:
    value = _get_value(data, path, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _tool_entry(config: dict[str, Any], language: str, tool: str) -> Any:
    tools = config.get(language, {}).get("tools", {}) or {}
    if not isinstance(tools, dict):
        return {}
    return tools.get(tool, {})


def _tool_enabled(
    config: dict[str, Any],
    language: str,
    tool: str,
    default: bool,
) -> bool:
    """Check if a tool is enabled. Delegates to canonical cihub.config.tool_enabled."""
    return _tool_enabled_canonical(config, tool, language, default=default)


def _tool_int(
    config: dict[str, Any],
    language: str,
    tool: str,
    key: str,
    default: int,
) -> int:
    entry = _tool_entry(config, language, tool)
    if isinstance(entry, dict):
        value = entry.get(key, default)
    else:
        value = default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def cmd_config_outputs(args: argparse.Namespace) -> CommandResult:
    """Generate config outputs for CI workflow consumption."""
    repo_path = Path(args.repo)

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message}],
        )

    language = config.get("language") or _get_str(config, ["repo", "language"], "python") or "python"

    workdir = args.workdir or _get_str(config, ["workdir"], "")
    if not workdir:
        workdir = _get_str(config, ["repo", "subdir"], ".")
    if not workdir:
        workdir = "."

    python_thresholds = {
        "coverage_min": _tool_int(config, "python", "pytest", "min_coverage", 70),
        "mutation_score_min": _tool_int(config, "python", "mutmut", "min_mutation_score", 70),
        "trivy_cvss_fail": _tool_int(config, "python", "trivy", "fail_on_cvss", 7),
        "max_semgrep_findings": _tool_int(config, "python", "semgrep", "max_findings", 0),
        "max_ruff_errors": _tool_int(config, "python", "ruff", "max_errors", 0),
        "max_black_issues": _tool_int(config, "python", "black", "max_issues", 0),
        "max_isort_issues": _tool_int(config, "python", "isort", "max_issues", 0),
        "max_pip_audit_vulns": _tool_int(config, "python", "pip_audit", "max_vulns", 0),
    }
    python_thresholds["owasp_cvss_fail"] = python_thresholds["trivy_cvss_fail"]

    java_thresholds = {
        "coverage_min": _tool_int(config, "java", "jacoco", "min_coverage", 70),
        "mutation_score_min": _tool_int(config, "java", "pitest", "min_mutation_score", 70),
        "owasp_cvss_fail": _tool_int(config, "java", "owasp", "fail_on_cvss", 7),
        "max_semgrep_findings": _tool_int(config, "java", "semgrep", "max_findings", 0),
        "max_checkstyle_errors": _tool_int(config, "java", "checkstyle", "max_errors", 0),
        "max_spotbugs_bugs": _tool_int(config, "java", "spotbugs", "max_bugs", 0),
        "max_pmd_violations": _tool_int(config, "java", "pmd", "max_violations", 0),
    }
    java_thresholds["trivy_cvss_fail"] = java_thresholds["owasp_cvss_fail"]

    global_thresholds = config.get("thresholds", {}) or {}
    # All schema-defined threshold keys that can be globally overridden
    all_threshold_keys = (
        "coverage_min",
        "mutation_score_min",
        "owasp_cvss_fail",
        "trivy_cvss_fail",
        "max_semgrep_findings",
        "max_ruff_errors",
        "max_black_issues",
        "max_isort_issues",
        "max_pip_audit_vulns",
        "max_checkstyle_errors",
        "max_spotbugs_bugs",
        "max_pmd_violations",
    )
    for key in all_threshold_keys:
        if key in global_thresholds and global_thresholds[key] is not None:
            threshold_value = int(global_thresholds[key])
            if key in python_thresholds:
                python_thresholds[key] = threshold_value
            if key in java_thresholds:
                java_thresholds[key] = threshold_value

    max_critical = _get_int(config, ["thresholds", "max_critical_vulns"], 0)
    max_high = _get_int(config, ["thresholds", "max_high_vulns"], 0)
    github_summary_enabled = _get_value(config, ["reports", "github_summary", "enabled"], True)

    # Extract harden_runner config
    harden_runner_config = config.get("harden_runner", True)  # default: enabled
    if isinstance(harden_runner_config, bool):
        run_harden_runner = harden_runner_config
        harden_runner_egress_policy = "audit"  # default policy
    elif isinstance(harden_runner_config, dict):
        policy = harden_runner_config.get("policy", "audit")
        run_harden_runner = policy != "disabled"
        harden_runner_egress_policy = policy if policy != "disabled" else "audit"
    else:
        run_harden_runner = True
        harden_runner_egress_policy = "audit"

    lang_for_shared = "java" if language == "java" else "python"

    outputs: dict[str, str] = {
        "language": str(language),
        "python_version": _get_str(config, ["python", "version"], "3.12"),
        "java_version": _get_str(config, ["java", "version"], "21"),
        "build_tool": _get_str(config, ["java", "build_tool"], "maven"),
        "workdir": workdir,
        "retention_days": str(_get_int(config, ["reports", "retention_days"], 30)),
        "write_github_summary": _bool_str(github_summary_enabled is not False),
        # Python tool toggles
        "run_pytest": _bool_str(_tool_enabled(config, "python", "pytest", True)),
        "run_ruff": _bool_str(_tool_enabled(config, "python", "ruff", True)),
        "run_bandit": _bool_str(_tool_enabled(config, "python", "bandit", True)),
        "run_pip_audit": _bool_str(_tool_enabled(config, "python", "pip_audit", True)),
        "run_mypy": _bool_str(_tool_enabled(config, "python", "mypy", False)),
        "run_black": _bool_str(_tool_enabled(config, "python", "black", True)),
        "run_isort": _bool_str(_tool_enabled(config, "python", "isort", True)),
        "run_mutmut": _bool_str(_tool_enabled(config, "python", "mutmut", True)),
        "run_hypothesis": _bool_str(_tool_enabled(config, "python", "hypothesis", True)),
        "run_sbom": _bool_str(_tool_enabled(config, lang_for_shared, "sbom", False)),
        "run_semgrep": _bool_str(_tool_enabled(config, lang_for_shared, "semgrep", False)),
        "run_trivy": _bool_str(_tool_enabled(config, lang_for_shared, "trivy", False)),
        "run_codeql": _bool_str(_tool_enabled(config, lang_for_shared, "codeql", False)),
        "run_docker": _bool_str(_tool_enabled(config, lang_for_shared, "docker", False)),
        # Java tool toggles
        "run_jacoco": _bool_str(_tool_enabled(config, "java", "jacoco", True)),
        "run_checkstyle": _bool_str(_tool_enabled(config, "java", "checkstyle", True)),
        "run_spotbugs": _bool_str(_tool_enabled(config, "java", "spotbugs", True)),
        "run_owasp": _bool_str(_tool_enabled(config, "java", "owasp", True)),
        "use_nvd_api_key": _bool_str(
            _tool_enabled(config, "java", "owasp", True)
            and _get_value(config, ["java", "tools", "owasp", "use_nvd_api_key"], True) is not False
        ),
        "run_pmd": _bool_str(_tool_enabled(config, "java", "pmd", True)),
        "run_pitest": _bool_str(_tool_enabled(config, "java", "pitest", True)),
        "run_jqwik": _bool_str(_tool_enabled(config, "java", "jqwik", False)),
        # Thresholds
        "coverage_min": str(python_thresholds["coverage_min"]),
        "mutation_score_min": str(python_thresholds["mutation_score_min"]),
        "owasp_cvss_fail": str(python_thresholds["owasp_cvss_fail"]),
        "trivy_cvss_fail": str(python_thresholds["trivy_cvss_fail"]),
        "max_semgrep_findings": str(python_thresholds["max_semgrep_findings"]),
        "max_ruff_errors": str(python_thresholds["max_ruff_errors"]),
        "max_black_issues": str(python_thresholds["max_black_issues"]),
        "max_isort_issues": str(python_thresholds["max_isort_issues"]),
        "max_pip_audit_vulns": str(python_thresholds["max_pip_audit_vulns"]),
        "max_checkstyle_errors": str(java_thresholds["max_checkstyle_errors"]),
        "max_spotbugs_bugs": str(java_thresholds["max_spotbugs_bugs"]),
        "max_pmd_violations": str(java_thresholds["max_pmd_violations"]),
        "max_critical_vulns": str(max_critical),
        "max_high_vulns": str(max_high),
        # Harden runner config
        "run_harden_runner": _bool_str(run_harden_runner),
        "harden_runner_egress_policy": harden_runner_egress_policy,
    }

    if language == "java":
        outputs["coverage_min"] = str(java_thresholds["coverage_min"])
        outputs["mutation_score_min"] = str(java_thresholds["mutation_score_min"])
        outputs["owasp_cvss_fail"] = str(java_thresholds["owasp_cvss_fail"])
        outputs["trivy_cvss_fail"] = str(java_thresholds["trivy_cvss_fail"])
        outputs["max_semgrep_findings"] = str(java_thresholds["max_semgrep_findings"])

    # Write to GITHUB_OUTPUT if requested
    output_path = os.environ.get("GITHUB_OUTPUT") if args.github_output else None
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            for key, value in outputs.items():
                handle.write(f"{key}={value}\n")

    # Build raw output for human mode (key=value lines)
    raw_output = "\n".join(f"{key}={value}" for key, value in outputs.items())

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Config outputs generated",
        data={"outputs": outputs, "raw_output": raw_output},
    )
