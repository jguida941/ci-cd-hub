"""Fallback defaults for config loading when defaults.yaml is missing or empty."""

from __future__ import annotations

from typing import Any

FALLBACK_DEFAULTS: dict[str, Any] = {
    "java": {
        "version": "21",
        "build_tool": "maven",
        "tools": {
            "jacoco": {"enabled": True, "min_coverage": 70},
            "checkstyle": {"enabled": True, "max_errors": 0},
            "spotbugs": {"enabled": True, "max_bugs": 0},
            "owasp": {"enabled": True, "fail_on_cvss": 7, "use_nvd_api_key": True},
            "pitest": {"enabled": True, "min_mutation_score": 70},
            "jqwik": {"enabled": False},
            "pmd": {"enabled": True, "max_violations": 0},
            "semgrep": {"enabled": False, "max_findings": 0},
            "sbom": {"enabled": False, "format": "cyclonedx"},
            "trivy": {"enabled": False},
            "codeql": {"enabled": False, "fail_on_error": True},
            "docker": {
                "enabled": False,
                "compose_file": "docker-compose.yml",
                "health_endpoint": "/actuator/health",
                "health_timeout": 300,
                "fail_on_error": True,
                "fail_on_missing_compose": False,
            },
        },
    },
    "python": {
        "version": "3.12",
        "tools": {
            "pytest": {"enabled": True, "min_coverage": 70},
            "ruff": {"enabled": True, "max_errors": 0},
            "black": {"enabled": True, "max_issues": 0},
            "isort": {"enabled": True, "max_issues": 0},
            "bandit": {"enabled": True},
            "pip_audit": {"enabled": True},
            "mypy": {"enabled": False},
            "mutmut": {"enabled": False, "min_mutation_score": 70},
            "hypothesis": {"enabled": True},
            "sbom": {"enabled": False, "format": "cyclonedx"},
            "semgrep": {"enabled": False, "max_findings": 0},
            "trivy": {"enabled": False, "fail_on_cvss": 7},
            "codeql": {"enabled": False, "fail_on_error": True},
            "docker": {
                "enabled": False,
                "compose_file": "docker-compose.yml",
                "health_endpoint": "/actuator/health",
                "health_timeout": 300,
                "fail_on_error": True,
                "fail_on_missing_compose": False,
            },
        },
    },
    "thresholds": {
        "coverage_min": 70,
        "mutation_score_min": 70,
        "max_critical_vulns": 0,
        "max_high_vulns": 0,
    },
    "reports": {"retention_days": 30},
}
