"""Single source of truth for tool definitions.

This module centralizes all tool-related definitions that were previously
scattered across ci_engine.py, discovery.py, and report_validator.py.

IMPORTANT: Do not modify tool lists without updating ALL related definitions.
Run tests/test_tool_registry.py after any changes to verify consistency.
"""

from __future__ import annotations

# =============================================================================
# TOOL NAME LISTS (from ci_engine.py)
# =============================================================================

PYTHON_TOOLS: list[str] = [
    "pytest",
    "ruff",
    "black",
    "isort",
    "mypy",
    "bandit",
    "pip_audit",
    "sbom",
    "semgrep",
    "trivy",
    "codeql",
    "docker",
    "hypothesis",
    "mutmut",
]

JAVA_TOOLS: list[str] = [
    "jacoco",
    "pitest",
    "jqwik",
    "checkstyle",
    "spotbugs",
    "pmd",
    "owasp",
    "semgrep",
    "trivy",
    "codeql",
    "sbom",
    "docker",
]

RESERVED_FEATURES: list[tuple[str, str]] = [
    ("chaos", "Chaos testing"),
    ("dr_drill", "Disaster recovery drills"),
    ("cache_sentinel", "Cache sentinel"),
    ("runner_isolation", "Runner isolation"),
    ("supply_chain", "Supply chain security"),
    ("egress_control", "Egress control"),
    ("canary", "Canary deployments"),
    ("telemetry", "Telemetry"),
    ("kyverno", "Kyverno policies"),
]

# =============================================================================
# WORKFLOW INPUT KEYS (from discovery.py)
# =============================================================================

# Keys to extract from generate_workflow_inputs()
TOOL_KEYS: tuple[str, ...] = (
    # Java tool flags
    "run_jacoco",
    "run_checkstyle",
    "run_spotbugs",
    "run_owasp",
    "use_nvd_api_key",
    "run_pitest",
    "run_jqwik",
    "run_pmd",
    # Python tool flags
    "run_pytest",
    "run_ruff",
    "run_bandit",
    "run_pip_audit",
    "run_mypy",
    "run_black",
    "run_isort",
    "run_mutmut",
    "run_hypothesis",
    "run_sbom",
    # Shared
    "run_semgrep",
    "run_trivy",
    "run_codeql",
    "run_docker",
)

THRESHOLD_KEYS: tuple[str, ...] = (
    "coverage_min",
    "mutation_score_min",
    "owasp_cvss_fail",
    "trivy_cvss_fail",
    "max_critical_vulns",
    "max_high_vulns",
    "max_semgrep_findings",
    "max_pmd_violations",
    "max_checkstyle_errors",
    "max_spotbugs_bugs",
    "max_ruff_errors",
    "max_black_issues",
    "max_isort_issues",
)

# =============================================================================
# TOOL METRICS (from report_validator.py)
# Metrics expected for each tool (by language)
# =============================================================================

PYTHON_TOOL_METRICS: dict[str, list[str]] = {
    "pytest": ["results.tests_passed", "results.coverage"],
    "mutmut": ["results.mutation_score"],
    "ruff": ["tool_metrics.ruff_errors"],
    "black": ["tool_metrics.black_issues"],
    "isort": ["tool_metrics.isort_issues"],
    "mypy": ["tool_metrics.mypy_errors"],
    "bandit": ["tool_metrics.bandit_high", "tool_metrics.bandit_medium"],
    "pip_audit": ["tool_metrics.pip_audit_vulns"],
    "sbom": [],
    "semgrep": ["tool_metrics.semgrep_findings"],
    "trivy": ["tool_metrics.trivy_critical", "tool_metrics.trivy_high"],
    "hypothesis": ["results.tests_passed"],
    "codeql": [],
    "docker": [],
}

JAVA_TOOL_METRICS: dict[str, list[str]] = {
    "jacoco": ["results.coverage"],
    "pitest": ["results.mutation_score"],
    "checkstyle": ["tool_metrics.checkstyle_issues"],
    "spotbugs": ["tool_metrics.spotbugs_issues"],
    "pmd": ["tool_metrics.pmd_violations"],
    "owasp": ["tool_metrics.owasp_critical", "tool_metrics.owasp_high"],
    "semgrep": ["tool_metrics.semgrep_findings"],
    "trivy": ["tool_metrics.trivy_critical", "tool_metrics.trivy_high"],
    "sbom": [],
    "jqwik": ["results.tests_passed"],
    "codeql": [],
    "docker": [],
}

# =============================================================================
# LINT AND SECURITY METRIC NAMES (from report_validator.py)
# Metrics that must be 0 for clean builds
# =============================================================================

PYTHON_LINT_METRICS: list[str] = ["ruff_errors", "black_issues", "isort_issues"]
PYTHON_SECURITY_METRICS: list[str] = ["bandit_high", "pip_audit_vulns"]
JAVA_LINT_METRICS: list[str] = ["checkstyle_issues", "spotbugs_issues", "pmd_violations"]
JAVA_SECURITY_METRICS: list[str] = ["owasp_critical", "owasp_high"]

# =============================================================================
# SUMMARY TABLE MAPS (from report_validator.py)
# Summary table labels -> tool keys
# =============================================================================

JAVA_SUMMARY_MAP: dict[str, str] = {
    "JaCoCo Coverage": "jacoco",
    "PITest": "pitest",
    "Checkstyle": "checkstyle",
    "PMD": "pmd",
    "SpotBugs": "spotbugs",
    "OWASP Dependency-Check": "owasp",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
    "SBOM": "sbom",
    "jqwik": "jqwik",
    "CodeQL": "codeql",
    "Docker": "docker",
}

PYTHON_SUMMARY_MAP: dict[str, str] = {
    "pytest": "pytest",
    "mutmut": "mutmut",
    "Ruff": "ruff",
    "Black": "black",
    "isort": "isort",
    "mypy": "mypy",
    "Bandit": "bandit",
    "pip-audit": "pip_audit",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
    "Hypothesis": "hypothesis",
    "CodeQL": "codeql",
    "SBOM": "sbom",
    "Docker": "docker",
}

# =============================================================================
# ARTIFACT PATTERNS (from report_validator.py)
# Artifact patterns used for backup validation when metrics are missing
# =============================================================================

JAVA_ARTIFACTS: dict[str, list[str]] = {
    "jacoco": ["**/target/site/jacoco/jacoco.xml"],
    "checkstyle": ["**/checkstyle-result.xml"],
    "spotbugs": ["**/spotbugsXml.xml"],
    "pmd": ["**/pmd.xml"],
    "owasp": ["**/dependency-check-report.json"],
    "pitest": ["**/target/pit-reports/mutations.xml"],
    "semgrep": ["**/semgrep-report.json"],
    "sbom": ["**/sbom*.json"],
    "trivy": ["**/trivy-report.json"],
}

PYTHON_ARTIFACTS: dict[str, list[str]] = {
    "pytest": ["**/coverage.xml", "**/test-results.xml", "**/pytest-junit.xml"],
    "ruff": ["**/ruff-report.json"],
    "bandit": ["**/bandit-report.json"],
    "pip_audit": ["**/pip-audit-report.json"],
    "black": ["**/black-output.txt"],
    "isort": ["**/isort-output.txt"],
    "mypy": ["**/mypy-output.txt"],
    "mutmut": ["**/mutmut-run.log"],
    "hypothesis": ["**/hypothesis-output.txt"],
    "semgrep": ["**/semgrep-report.json"],
    "sbom": ["**/sbom*.json"],
    "trivy": ["**/trivy-report.json"],
}
