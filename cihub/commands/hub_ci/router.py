"""Main dispatcher for hub-ci subcommands."""

from __future__ import annotations

import argparse

from cihub.exit_codes import EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult

from .badges import cmd_badges, cmd_badges_commit, cmd_outputs
from .java_tools import (
    cmd_codeql_build,
    cmd_smoke_java_build,
    cmd_smoke_java_checkstyle,
    cmd_smoke_java_coverage,
    cmd_smoke_java_spotbugs,
    cmd_smoke_java_tests,
)
from .python_tools import (
    cmd_black,
    cmd_coverage_verify,
    cmd_mutmut,
    cmd_mypy,
    cmd_ruff,
    cmd_ruff_format,
)
from .release import (
    cmd_actionlint,
    cmd_actionlint_install,
    cmd_enforce,
    cmd_gitleaks_summary,
    cmd_kyverno_install,
    cmd_kyverno_test,
    cmd_kyverno_validate,
    cmd_license_check,
    cmd_pytest_summary,
    cmd_release_parse_tag,
    cmd_release_update_tag,
    cmd_summary,
    cmd_trivy_install,
    cmd_trivy_summary,
    cmd_zizmor_check,
    cmd_zizmor_run,
)
from .security import (
    cmd_bandit,
    cmd_pip_audit,
    cmd_security_bandit,
    cmd_security_owasp,
    cmd_security_pip_audit,
    cmd_security_ruff,
)
from .smoke import (
    cmd_smoke_python_black,
    cmd_smoke_python_install,
    cmd_smoke_python_ruff,
    cmd_smoke_python_tests,
)
from .test_metrics import cmd_test_metrics
from .thresholds import cmd_thresholds
from .validation import (
    cmd_docker_compose_check,
    cmd_enforce_command_result,
    cmd_quarantine_check,
    cmd_repo_check,
    cmd_source_check,
    cmd_syntax_check,
    cmd_validate_configs,
    cmd_validate_profiles,
    cmd_validate_triage,
    cmd_verify_matrix_keys,
    cmd_yamllint,
)


def cmd_hub_ci(args: argparse.Namespace) -> CommandResult:
    """Dispatch hub-ci subcommands, returning CommandResult for --json support."""
    handlers = {
        "actionlint-install": cmd_actionlint_install,
        "actionlint": cmd_actionlint,
        "syntax-check": cmd_syntax_check,
        "yamllint": cmd_yamllint,
        "repo-check": cmd_repo_check,
        "source-check": cmd_source_check,
        "security-pip-audit": cmd_security_pip_audit,
        "security-bandit": cmd_security_bandit,
        "security-ruff": cmd_security_ruff,
        "security-owasp": cmd_security_owasp,
        "docker-compose-check": cmd_docker_compose_check,
        "codeql-build": cmd_codeql_build,
        "kyverno-install": cmd_kyverno_install,
        "trivy-install": cmd_trivy_install,
        "trivy-summary": cmd_trivy_summary,
        "kyverno-validate": cmd_kyverno_validate,
        "kyverno-test": cmd_kyverno_test,
        "smoke-java-build": cmd_smoke_java_build,
        "smoke-java-tests": cmd_smoke_java_tests,
        "smoke-java-coverage": cmd_smoke_java_coverage,
        "smoke-java-checkstyle": cmd_smoke_java_checkstyle,
        "smoke-java-spotbugs": cmd_smoke_java_spotbugs,
        "smoke-python-install": cmd_smoke_python_install,
        "smoke-python-tests": cmd_smoke_python_tests,
        "smoke-python-ruff": cmd_smoke_python_ruff,
        "smoke-python-black": cmd_smoke_python_black,
        "release-parse-tag": cmd_release_parse_tag,
        "release-update-tag": cmd_release_update_tag,
        "ruff": cmd_ruff,
        "ruff-format": cmd_ruff_format,
        "black": cmd_black,
        "mypy": cmd_mypy,
        "mutmut": cmd_mutmut,
        "coverage-verify": cmd_coverage_verify,
        "badges": cmd_badges,
        "badges-commit": cmd_badges_commit,
        "outputs": cmd_outputs,
        "bandit": cmd_bandit,
        "pip-audit": cmd_pip_audit,
        "zizmor-run": cmd_zizmor_run,
        "zizmor-check": cmd_zizmor_check,
        "validate-configs": cmd_validate_configs,
        "validate-profiles": cmd_validate_profiles,
        "validate-triage": cmd_validate_triage,
        "license-check": cmd_license_check,
        "gitleaks-summary": cmd_gitleaks_summary,
        "pytest-summary": cmd_pytest_summary,
        "summary": cmd_summary,
        "enforce": cmd_enforce,
        "verify-matrix-keys": cmd_verify_matrix_keys,
        "quarantine-check": cmd_quarantine_check,
        "enforce-command-result": cmd_enforce_command_result,
        "thresholds": cmd_thresholds,
        "test-metrics": cmd_test_metrics,
    }
    handler = handlers.get(args.subcommand)
    if handler is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown hub-ci subcommand: {args.subcommand}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Unknown subcommand '{args.subcommand}'",
                    "code": "CIHUB-UNKNOWN-SUBCOMMAND",
                }
            ],
        )

    # Execute handler - may return int (legacy) or CommandResult (migrated)
    result = handler(args)

    # If handler already returns CommandResult, use it directly
    if isinstance(result, CommandResult):
        return result

    # Legacy int return - always wrap in CommandResult for type safety
    status = "success" if result == EXIT_SUCCESS else "failed"
    return CommandResult(
        exit_code=result,
        summary=f"hub-ci {args.subcommand}: {status}",
        data={"subcommand": args.subcommand, "exit_code": result, "status": status},
    )
