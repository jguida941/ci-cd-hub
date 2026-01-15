"""Parser setup for hub-ci release and infrastructure subcommands."""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Callable

from cihub.cli_parsers.common import (
    add_output_args,
    add_repo_args,
    add_summary_args,
)


def add_release_parsers(
    hub_ci_sub: _SubParsersAction,
    add_json_flag: Callable,
) -> None:
    """Add release and infrastructure subcommand parsers.

    Subcommands: actionlint-install, actionlint, release-parse-tag, release-update-tag,
    kyverno-install, kyverno-validate, kyverno-test, trivy-install, trivy-summary,
    zizmor-run, zizmor-check, license-check, gitleaks-summary, pytest-summary,
    summary, enforce
    """
    # Actionlint commands
    hub_ci_actionlint_install = hub_ci_sub.add_parser(
        "actionlint-install",
        help="Download the actionlint binary",
    )
    hub_ci_actionlint_install.add_argument(
        "--version",
        default="latest",
        help="Actionlint version (default: latest)",
    )
    hub_ci_actionlint_install.add_argument("--checksum", help="SHA256 checksum for tarball")
    hub_ci_actionlint_install.add_argument(
        "--dest",
        default=".cihub/tools",
        help="Destination directory for actionlint",
    )
    add_output_args(hub_ci_actionlint_install)
    add_json_flag(hub_ci_actionlint_install)

    hub_ci_actionlint = hub_ci_sub.add_parser(
        "actionlint",
        help="Run actionlint (optionally with reviewdog)",
    )
    hub_ci_actionlint.add_argument(
        "--workflow",
        default=".github/workflows/hub-production-ci.yml",
        help="Workflow file to lint",
    )
    hub_ci_actionlint.add_argument("--bin", help="Path to actionlint binary")
    hub_ci_actionlint.add_argument(
        "--reviewdog",
        action="store_true",
        help="Pipe output to reviewdog",
    )
    add_json_flag(hub_ci_actionlint)

    # Release tag commands
    hub_ci_release_parse = hub_ci_sub.add_parser(
        "release-parse-tag",
        help="Parse tag ref into version outputs",
    )
    hub_ci_release_parse.add_argument("--ref", help="Tag ref (defaults to GITHUB_REF)")
    add_output_args(hub_ci_release_parse)
    add_json_flag(hub_ci_release_parse)

    hub_ci_release_update = hub_ci_sub.add_parser(
        "release-update-tag",
        help="Update floating major tag",
    )
    add_repo_args(hub_ci_release_update)
    hub_ci_release_update.add_argument("--major", required=True, help="Major tag name (e.g., v1)")
    hub_ci_release_update.add_argument("--version", required=True, help="Release version")
    hub_ci_release_update.add_argument("--remote", default="origin", help="Git remote name")
    add_json_flag(hub_ci_release_update)

    # Kyverno commands
    hub_ci_kyverno_install = hub_ci_sub.add_parser(
        "kyverno-install",
        help="Download the kyverno CLI",
    )
    hub_ci_kyverno_install.add_argument(
        "--version",
        default="v1.16.1",
        help="Kyverno CLI version (default: v1.16.1)",
    )
    hub_ci_kyverno_install.add_argument(
        "--dest",
        default=".cihub/tools",
        help="Destination directory for kyverno",
    )
    add_output_args(hub_ci_kyverno_install)
    add_json_flag(hub_ci_kyverno_install)

    hub_ci_kyverno_validate = hub_ci_sub.add_parser(
        "kyverno-validate",
        help="Validate kyverno policy syntax",
    )
    hub_ci_kyverno_validate.add_argument(
        "--policies-dir",
        default="policies/kyverno",
        help="Policies directory",
    )
    hub_ci_kyverno_validate.add_argument(
        "--templates-dir",
        help="Templates directory",
    )
    hub_ci_kyverno_validate.add_argument("--bin", help="Path to kyverno binary")
    add_output_args(hub_ci_kyverno_validate)
    add_json_flag(hub_ci_kyverno_validate)

    hub_ci_kyverno_test = hub_ci_sub.add_parser(
        "kyverno-test",
        help="Test kyverno policies against fixtures",
    )
    hub_ci_kyverno_test.add_argument(
        "--policies-dir",
        default="policies/kyverno",
        help="Policies directory",
    )
    hub_ci_kyverno_test.add_argument(
        "--fixtures-dir",
        default="fixtures/kyverno",
        help="Fixtures directory",
    )
    hub_ci_kyverno_test.add_argument("--bin", help="Path to kyverno binary")
    hub_ci_kyverno_test.add_argument(
        "--fail-on-warn",
        default="false",
        help="Warn if policy tests produce warnings (true/false)",
    )
    add_json_flag(hub_ci_kyverno_test)

    # Trivy commands
    hub_ci_trivy_install = hub_ci_sub.add_parser(
        "trivy-install",
        help="Download the trivy CLI",
    )
    hub_ci_trivy_install.add_argument(
        "--version",
        default="0.55.0",
        help="Trivy CLI version (default: 0.55.0)",
    )
    hub_ci_trivy_install.add_argument(
        "--dest",
        default=".cihub/tools",
        help="Destination directory for trivy",
    )
    hub_ci_trivy_install.add_argument(
        "--github-path",
        action="store_true",
        help="Append destination dir to GITHUB_PATH",
    )
    add_output_args(hub_ci_trivy_install)
    add_json_flag(hub_ci_trivy_install)

    hub_ci_trivy_summary = hub_ci_sub.add_parser(
        "trivy-summary",
        help="Parse Trivy JSON output and generate summary with counts",
    )
    hub_ci_trivy_summary.add_argument(
        "--fs-json",
        help="Path to trivy filesystem scan JSON (vulnerabilities)",
    )
    hub_ci_trivy_summary.add_argument(
        "--config-json",
        help="Path to trivy config scan JSON (misconfigurations)",
    )
    hub_ci_trivy_summary.add_argument(
        "--github-summary",
        action="store_true",
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    hub_ci_trivy_summary.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )
    add_json_flag(hub_ci_trivy_summary)

    # Zizmor commands
    hub_ci_zizmor_run = hub_ci_sub.add_parser("zizmor-run", help="Run zizmor and produce SARIF (with fallback)")
    hub_ci_zizmor_run.add_argument("--output", "-o", default="zizmor.sarif", help="Path to write SARIF output")
    hub_ci_zizmor_run.add_argument("--workflows", default=".github/workflows/", help="Path to workflows directory")
    add_json_flag(hub_ci_zizmor_run)

    hub_ci_zizmor = hub_ci_sub.add_parser("zizmor-check", help="Check zizmor SARIF for high findings")
    hub_ci_zizmor.add_argument("--sarif", default="zizmor.sarif", help="Path to SARIF file")
    add_summary_args(hub_ci_zizmor)
    hub_ci_zizmor.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_zizmor)

    # License and secrets
    hub_ci_license = hub_ci_sub.add_parser("license-check", help="Run license checks for dependencies")
    add_summary_args(hub_ci_license)
    hub_ci_license.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_license)

    hub_ci_gitleaks = hub_ci_sub.add_parser("gitleaks-summary", help="Summarize gitleaks results")
    hub_ci_gitleaks.add_argument("--outcome", help="Gitleaks outcome")
    add_summary_args(hub_ci_gitleaks)
    hub_ci_gitleaks.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_gitleaks)

    # Summary and enforcement
    hub_ci_pytest_summary = hub_ci_sub.add_parser(
        "pytest-summary",
        help="Generate pytest test results summary",
    )
    hub_ci_pytest_summary.add_argument(
        "--junit-xml",
        default="test-results.xml",
        help="Path to pytest JUnit XML file",
    )
    hub_ci_pytest_summary.add_argument(
        "--coverage-xml",
        default="coverage.xml",
        help="Path to coverage XML file",
    )
    hub_ci_pytest_summary.add_argument(
        "--coverage-min",
        type=int,
        default=70,
        help="Minimum coverage percentage (default: 70)",
    )
    add_summary_args(hub_ci_pytest_summary)
    hub_ci_pytest_summary.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_pytest_summary)

    hub_ci_summary = hub_ci_sub.add_parser("summary", help="Generate hub CI summary")
    add_summary_args(hub_ci_summary)
    hub_ci_summary.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_summary)

    _hub_ci_enforce = hub_ci_sub.add_parser(  # noqa: F841
        "enforce",
        help="Fail if critical hub checks failed",
    )
    add_json_flag(_hub_ci_enforce)
