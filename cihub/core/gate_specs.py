"""Shared gate specifications for gates.py and reporting.py.

This module provides a single source of truth for:
- Threshold keys and display labels
- Tool configurations per language
- Gate evaluation specifications

Both gates.py (enforcement) and reporting.py (display) should use these
specs to prevent drift between evaluation logic and rendered output.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Comparator(Enum):
    """How to compare metric value against threshold."""

    GTE = "gte"  # value >= threshold is good (coverage, mutation)
    LTE = "lte"  # value <= threshold is good (errors, vulns)
    CVSS = "cvss"  # value >= threshold is bad (CVSS scores)


class Category(Enum):
    """Tool category for grouping in reports."""

    TESTING = "Testing"
    LINTING = "Linting"
    SECURITY = "Security"
    CONTAINER = "Container"


@dataclass(frozen=True, slots=True)
class ThresholdSpec:
    """Defines a threshold for display and evaluation."""

    label: str  # Display label, e.g., "Min Coverage"
    key: str  # Config key, e.g., "coverage_min"
    unit: str  # Display unit, e.g., "%" or ""
    comparator: Comparator  # How metric compares to threshold
    metric_key: str  # Key in tool_metrics or results
    failure_template: str  # Message template for gate failures


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Defines a tool for display in reports."""

    category: Category
    label: str  # Display label
    key: str  # Config/report key


# -----------------------------------------------------------------------------
# Python Gate Specifications
# -----------------------------------------------------------------------------

PYTHON_THRESHOLDS: tuple[ThresholdSpec, ...] = (
    ThresholdSpec(
        label="Min Coverage",
        key="coverage_min",
        unit="%",
        comparator=Comparator.GTE,
        metric_key="coverage",
        failure_template="coverage {value}% < {threshold}%",
    ),
    ThresholdSpec(
        label="Min Mutation Score",
        key="mutation_score_min",
        unit="%",
        comparator=Comparator.GTE,
        metric_key="mutation_score",
        failure_template="mutation score {value}% < {threshold}%",
    ),
    ThresholdSpec(
        label="Trivy CVSS Fail",
        key="trivy_cvss_fail",
        unit="",
        comparator=Comparator.CVSS,
        metric_key="trivy_max_cvss",
        failure_template="trivy max CVSS {value:.1f} >= {threshold:.1f}",
    ),
    ThresholdSpec(
        label="Max Critical Vulns",
        key="max_critical_vulns",
        unit="",
        comparator=Comparator.LTE,
        metric_key="trivy_critical",
        failure_template="trivy critical {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max High Vulns",
        key="max_high_vulns",
        unit="",
        comparator=Comparator.LTE,
        metric_key="bandit_high",  # Note: bandit uses this primarily
        failure_template="bandit high {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max pip-audit Vulns",
        key="max_pip_audit_vulns",
        unit="",
        comparator=Comparator.LTE,
        metric_key="pip_audit_vulns",
        failure_template="pip-audit vulns {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Semgrep Findings",
        key="max_semgrep_findings",
        unit="",
        comparator=Comparator.LTE,
        metric_key="semgrep_findings",
        failure_template="semgrep findings {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Ruff Errors",
        key="max_ruff_errors",
        unit="",
        comparator=Comparator.LTE,
        metric_key="ruff_errors",
        failure_template="ruff errors {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Black Issues",
        key="max_black_issues",
        unit="",
        comparator=Comparator.LTE,
        metric_key="black_issues",
        failure_template="black issues {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max isort Issues",
        key="max_isort_issues",
        unit="",
        comparator=Comparator.LTE,
        metric_key="isort_issues",
        failure_template="isort issues {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max mypy Errors",
        key="max_mypy_errors",
        unit="",
        comparator=Comparator.LTE,
        metric_key="mypy_errors",
        failure_template="mypy errors {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Bandit Medium",
        key="max_bandit_medium",
        unit="",
        comparator=Comparator.LTE,
        metric_key="bandit_medium",
        failure_template="bandit medium {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Bandit Low",
        key="max_bandit_low",
        unit="",
        comparator=Comparator.LTE,
        metric_key="bandit_low",
        failure_template="bandit low {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Trivy Critical",
        key="max_trivy_critical",
        unit="",
        comparator=Comparator.LTE,
        metric_key="trivy_critical",
        failure_template="trivy critical {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Trivy High",
        key="max_trivy_high",
        unit="",
        comparator=Comparator.LTE,
        metric_key="trivy_high",
        failure_template="trivy high {value} > {threshold}",
    ),
)

PYTHON_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(Category.TESTING, "pytest", "pytest"),
    ToolSpec(Category.TESTING, "mutmut", "mutmut"),
    ToolSpec(Category.TESTING, "Hypothesis", "hypothesis"),
    ToolSpec(Category.LINTING, "Ruff", "ruff"),
    ToolSpec(Category.LINTING, "Black", "black"),
    ToolSpec(Category.LINTING, "isort", "isort"),
    ToolSpec(Category.LINTING, "mypy", "mypy"),
    ToolSpec(Category.SECURITY, "Bandit", "bandit"),
    ToolSpec(Category.SECURITY, "pip-audit", "pip_audit"),
    ToolSpec(Category.SECURITY, "Semgrep", "semgrep"),
    ToolSpec(Category.SECURITY, "Trivy", "trivy"),
    ToolSpec(Category.SECURITY, "CodeQL", "codeql"),
    ToolSpec(Category.SECURITY, "SBOM", "sbom"),
    ToolSpec(Category.CONTAINER, "Docker", "docker"),
)

# Tool keys for require_run_or_fail policy
# Keep this derived from the tool table so require_run_or_fail can apply to any
# configured tool (without duplicating tool lists elsewhere).
PYTHON_TOOL_KEYS: tuple[str, ...] = tuple(spec.key for spec in PYTHON_TOOLS)

# -----------------------------------------------------------------------------
# Java Gate Specifications
# -----------------------------------------------------------------------------

JAVA_THRESHOLDS: tuple[ThresholdSpec, ...] = (
    ThresholdSpec(
        label="Min Coverage",
        key="coverage_min",
        unit="%",
        comparator=Comparator.GTE,
        metric_key="coverage",
        failure_template="coverage {value}% < {threshold}%",
    ),
    ThresholdSpec(
        label="Min Mutation Score",
        key="mutation_score_min",
        unit="%",
        comparator=Comparator.GTE,
        metric_key="mutation_score",
        failure_template="mutation score {value}% < {threshold}%",
    ),
    ThresholdSpec(
        label="OWASP CVSS Fail",
        key="owasp_cvss_fail",
        unit="",
        comparator=Comparator.CVSS,
        metric_key="owasp_max_cvss",
        failure_template="owasp max CVSS {value:.1f} >= {threshold:.1f}",
    ),
    ThresholdSpec(
        label="Trivy CVSS Fail",
        key="trivy_cvss_fail",
        unit="",
        comparator=Comparator.CVSS,
        metric_key="trivy_max_cvss",
        failure_template="trivy max CVSS {value:.1f} >= {threshold:.1f}",
    ),
    ThresholdSpec(
        label="Max Critical Vulns",
        key="max_critical_vulns",
        unit="",
        comparator=Comparator.LTE,
        metric_key="owasp_critical",
        failure_template="owasp critical {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max High Vulns",
        key="max_high_vulns",
        unit="",
        comparator=Comparator.LTE,
        metric_key="owasp_high",
        failure_template="owasp high {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Semgrep Findings",
        key="max_semgrep_findings",
        unit="",
        comparator=Comparator.LTE,
        metric_key="semgrep_findings",
        failure_template="semgrep findings {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max PMD Violations",
        key="max_pmd_violations",
        unit="",
        comparator=Comparator.LTE,
        metric_key="pmd_violations",
        failure_template="pmd violations {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Checkstyle Errors",
        key="max_checkstyle_errors",
        unit="",
        comparator=Comparator.LTE,
        metric_key="checkstyle_issues",
        failure_template="checkstyle issues {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max SpotBugs Bugs",
        key="max_spotbugs_bugs",
        unit="",
        comparator=Comparator.LTE,
        metric_key="spotbugs_issues",
        failure_template="spotbugs issues {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Trivy Critical (Java)",
        key="max_trivy_critical",
        unit="",
        comparator=Comparator.LTE,
        metric_key="trivy_critical",
        failure_template="trivy critical {value} > {threshold}",
    ),
    ThresholdSpec(
        label="Max Trivy High (Java)",
        key="max_trivy_high",
        unit="",
        comparator=Comparator.LTE,
        metric_key="trivy_high",
        failure_template="trivy high {value} > {threshold}",
    ),
)

JAVA_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(Category.TESTING, "Build", "__build__"),
    ToolSpec(Category.TESTING, "JaCoCo Coverage", "jacoco"),
    ToolSpec(Category.TESTING, "PITest", "pitest"),
    ToolSpec(Category.TESTING, "jqwik", "jqwik"),
    ToolSpec(Category.LINTING, "Checkstyle", "checkstyle"),
    ToolSpec(Category.LINTING, "PMD", "pmd"),
    ToolSpec(Category.LINTING, "SpotBugs", "spotbugs"),
    ToolSpec(Category.SECURITY, "OWASP Dependency-Check", "owasp"),
    ToolSpec(Category.SECURITY, "Semgrep", "semgrep"),
    ToolSpec(Category.SECURITY, "Trivy", "trivy"),
    ToolSpec(Category.SECURITY, "CodeQL", "codeql"),
    ToolSpec(Category.SECURITY, "SBOM", "sbom"),
    ToolSpec(Category.CONTAINER, "Docker", "docker"),
)

# Tool keys for require_run_or_fail policy
JAVA_TOOL_KEYS: tuple[str, ...] = tuple(spec.key for spec in JAVA_TOOLS if spec.key != "__build__")


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def get_thresholds(language: str) -> tuple[ThresholdSpec, ...]:
    """Get threshold specifications for a language."""
    if language == "java":
        return JAVA_THRESHOLDS
    return PYTHON_THRESHOLDS


def get_tools(language: str) -> tuple[ToolSpec, ...]:
    """Get tool specifications for a language."""
    if language == "java":
        return JAVA_TOOLS
    return PYTHON_TOOLS


def get_tool_keys(language: str) -> tuple[str, ...]:
    """Get tool keys for require_run_or_fail policy."""
    if language == "java":
        return JAVA_TOOL_KEYS
    return PYTHON_TOOL_KEYS


def threshold_rows(language: str) -> list[tuple[str, str, str]]:
    """Get threshold rows for reporting (label, key, unit)."""
    specs = get_thresholds(language)
    return [(s.label, s.key, s.unit) for s in specs]


def tool_rows(language: str) -> list[tuple[str, str, str]]:
    """Get tool rows for reporting (category, label, key)."""
    specs = get_tools(language)
    return [(s.category.value, s.label, s.key) for s in specs]


def evaluate_threshold(
    spec: ThresholdSpec,
    value: int | float,
    threshold: int | float,
) -> tuple[bool, str | None]:
    """Evaluate a single threshold gate.

    Returns:
        Tuple of (passed, failure_message).
        If passed is True, failure_message is None.
    """
    if spec.comparator == Comparator.GTE:
        # value must be >= threshold (coverage, mutation score)
        if value < threshold:
            msg = spec.failure_template.format(value=value, threshold=threshold)
            return False, msg
    elif spec.comparator == Comparator.LTE:
        # value must be <= threshold (errors, vulns)
        if value > threshold:
            msg = spec.failure_template.format(value=value, threshold=threshold)
            return False, msg
    elif spec.comparator == Comparator.CVSS:
        # value >= threshold is a failure (CVSS fail threshold)
        if threshold > 0 and value >= threshold:
            msg = spec.failure_template.format(value=value, threshold=threshold)
            return False, msg

    return True, None


def get_threshold_spec_by_key(language: str, key: str) -> ThresholdSpec | None:
    """Look up a threshold spec by its config key."""
    for spec in get_thresholds(language):
        if spec.key == key:
            return spec
    return None


def get_metric_value(
    spec: ThresholdSpec,
    results: dict[str, Any],
    tool_metrics: dict[str, Any],
) -> int | float:
    """Get metric value for a threshold spec from report data."""
    # Try tool_metrics first, then results
    value = tool_metrics.get(spec.metric_key)
    if value is None:
        value = results.get(spec.metric_key)
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value) if "." in str(value) else int(value)
    except (ValueError, TypeError):
        return 0
