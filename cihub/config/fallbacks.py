"""Fallback defaults for config loading when defaults.yaml is missing or empty.

AUTO-GENERATED from ci-hub-config.schema.json
To regenerate:
  python -c "from cihub.commands.schema_sync import generate_fallbacks_py; generate_fallbacks_py()"
"""

from __future__ import annotations

from typing import Any

FALLBACK_DEFAULTS: dict[str, Any] = {
    "cache_sentinel": {
        "enabled": False,
    },
    "canary": {
        "enabled": False,
    },
    "chaos": {
        "enabled": False,
    },
    "dr_drill": {
        "enabled": False,
    },
    "egress_control": {
        "enabled": False,
    },
    "gates": {
        "require_run_or_fail": False,
        "tool_defaults": {
            "pytest": True,
            "ruff": True,
            "bandit": True,
            "pip_audit": True,
            "mypy": False,
            "black": False,
            "isort": False,
            "mutmut": False,
            "hypothesis": False,
            "semgrep": False,
            "trivy": True,
            "codeql": True,
            "docker": False,
            "sbom": False,
            "jacoco": True,
            "checkstyle": True,
            "spotbugs": True,
            "pmd": False,
            "owasp": True,
            "pitest": False,
            "jqwik": False,
        },
    },
    "hub_ci": {
        "enabled": True,
        "thresholds": {
            "coverage_min": 70,
            "mutation_score_min": 70,
            "overrides": {},
        },
        "tools": {
            "actionlint": True,
            "bandit": True,
            "bandit_fail_high": True,
            "bandit_fail_medium": False,
            "bandit_fail_low": False,
            "dependency_review": True,
            "gitleaks": True,
            "license_check": True,
            "mutmut": True,
            "mypy": True,
            "pip_audit": True,
            "pytest": True,
            "ruff": True,
            "scorecard": True,
            "syntax": True,
            "trivy": True,
            "validate_configs": True,
            "validate_templates": True,
            "verify_matrix_keys": True,
            "yamllint": True,
            "zizmor": True,
        },
    },
    "java": {
        "version": "21",
        "distribution": "temurin",
        "build_tool": "maven",
        "tools": {
            "checkstyle": {
                "enabled": True,
                "fail_on_violation": True,
                "max_errors": 0,
                "require_run_or_fail": True,
            },
            "codeql": {
                "enabled": False,
                "fail_on_error": True,
                "languages": ["java"],
                "require_run_or_fail": True,
            },
            "docker": {
                "compose_file": "docker-compose.yml",
                "dockerfile": "Dockerfile",
                "enabled": False,
                "fail_on_error": True,
                "fail_on_missing_compose": False,
                "health_endpoint": "/actuator/health",
                "health_timeout": 300,
                "require_run_or_fail": False,
            },
            "jacoco": {
                "enabled": True,
                "min_coverage": 70,
                "require_run_or_fail": True,
            },
            "jqwik": {
                "enabled": False,
                "require_run_or_fail": False,
            },
            "owasp": {
                "enabled": True,
                "fail_on_cvss": 7,
                "require_run_or_fail": False,
                "use_nvd_api_key": True,
            },
            "pitest": {
                "enabled": True,
                "min_mutation_score": 70,
                "require_run_or_fail": False,
                "threads": 4,
                "timeout_multiplier": 2,
            },
            "pmd": {
                "enabled": True,
                "fail_on_violation": False,
                "max_violations": 0,
                "require_run_or_fail": False,
            },
            "semgrep": {
                "enabled": False,
                "fail_on_findings": False,
                "max_findings": 0,
                "require_run_or_fail": False,
            },
            "sbom": {
                "enabled": False,
                "format": "cyclonedx",
                "require_run_or_fail": False,
            },
            "spotbugs": {
                "effort": "max",
                "enabled": True,
                "fail_on_error": True,
                "max_bugs": 0,
                "require_run_or_fail": True,
                "threshold": "medium",
            },
            "trivy": {
                "enabled": False,
                "fail_on_critical": False,
                "fail_on_cvss": 7,
                "fail_on_high": False,
                "require_run_or_fail": True,
            },
        },
    },
    "kyverno": {
        "enabled": False,
    },
    "notifications": {
        "email": {
            "enabled": False,
            "recipients_env": "CIHUB_EMAIL_TO",
            "smtp_from_env": "SMTP_FROM",
            "smtp_host_env": "SMTP_HOST",
            "smtp_password_env": "SMTP_PASSWORD",
            "smtp_port_env": "SMTP_PORT",
            "smtp_starttls_env": "SMTP_STARTTLS",
            "smtp_user_env": "SMTP_USER",
        },
        "slack": {
            "enabled": False,
            "on_failure": True,
            "on_success": False,
            "webhook_env": "CIHUB_SLACK_WEBHOOK_URL",
        },
    },
    "python": {
        "version": "3.12",
        "tools": {
            "bandit": {
                "enabled": True,
                "fail_on_high": True,
                "fail_on_low": False,
                "fail_on_medium": False,
                "require_run_or_fail": True,
            },
            "black": {
                "enabled": True,
                "fail_on_format_issues": False,
                "max_issues": 0,
                "require_run_or_fail": False,
            },
            "codeql": {
                "enabled": False,
                "fail_on_error": True,
                "languages": ["python"],
                "require_run_or_fail": True,
            },
            "docker": {
                "compose_file": "docker-compose.yml",
                "enabled": False,
                "fail_on_error": True,
                "fail_on_missing_compose": False,
                "health_endpoint": "/actuator/health",
                "health_timeout": 300,
                "require_run_or_fail": False,
            },
            "hypothesis": {
                "enabled": True,
                "require_run_or_fail": False,
            },
            "isort": {
                "enabled": True,
                "fail_on_issues": False,
                "max_issues": 0,
                "require_run_or_fail": False,
            },
            "mutmut": {
                "enabled": False,
                "min_mutation_score": 70,
                "require_run_or_fail": False,
                "timeout_minutes": 15,
            },
            "mypy": {
                "enabled": False,
                "require_run_or_fail": False,
            },
            "pip_audit": {
                "enabled": True,
                "fail_on_vuln": True,
                "require_run_or_fail": True,
            },
            "pytest": {
                "enabled": True,
                "fail_fast": False,
                "min_coverage": 70,
                "require_run_or_fail": True,
            },
            "ruff": {
                "enabled": True,
                "fail_on_error": True,
                "max_errors": 0,
                "require_run_or_fail": True,
            },
            "sbom": {
                "enabled": False,
                "format": "cyclonedx",
                "require_run_or_fail": False,
            },
            "semgrep": {
                "enabled": False,
                "fail_on_findings": False,
                "max_findings": 0,
                "require_run_or_fail": False,
            },
            "trivy": {
                "enabled": False,
                "fail_on_critical": False,
                "fail_on_cvss": 7,
                "fail_on_high": False,
                "require_run_or_fail": True,
            },
        },
    },
    "repo": {
        "default_branch": "main",
        "dispatch_enabled": True,
        "dispatch_workflow": "hub-ci.yml",
        "force_all_tools": False,
        "repo_side_execution": False,
        "run_group": "full",
        "use_central_runner": True,
    },
    "cihub": {
        "debug": False,
        "verbose": False,
        "debug_context": False,
        "emit_triage": False,
    },
    "install": {
        "source": "pypi",
    },
    "reports": {
        "badges": {
            "branch": "main",
            "enabled": True,
        },
        "codecov": {
            "enabled": True,
            "fail_ci_on_error": False,
        },
        "github_summary": {
            "enabled": True,
            "include_metrics": True,
        },
        "retention_days": 30,
    },
    "harden_runner": {
        "policy": "audit",
    },
    "runner_isolation": {
        "enabled": False,
    },
    "supply_chain": {
        "enabled": False,
    },
    "telemetry": {
        "enabled": False,
    },
    "thresholds": {
        "coverage_min": 70,
        "max_black_issues": 0,
        "max_checkstyle_errors": 0,
        "max_critical_vulns": 0,
        "max_high_vulns": 0,
        "max_isort_issues": 0,
        "max_pip_audit_vulns": 0,
        "max_pmd_violations": 0,
        "max_ruff_errors": 0,
        "max_semgrep_findings": 0,
        "max_spotbugs_bugs": 0,
        "mutation_score_min": 70,
        "owasp_cvss_fail": 7,
        "trivy_cvss_fail": 7,
    },
}
