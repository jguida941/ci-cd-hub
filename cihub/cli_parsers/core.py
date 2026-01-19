"""Parser setup for core CLI commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import (
    add_ai_flags,
    add_repo_args,
    add_report_args,
    add_summary_args,
    see_also_epilog,
)
from cihub.cli_parsers.types import CommandHandlers


def _add_preflight_parser(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
    name: str,
    help_text: str,
) -> None:
    parser = subparsers.add_parser(name, help=help_text, epilog=see_also_epilog(name))
    add_json_flag(parser)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Check optional toolchains and CI runners",
    )
    parser.set_defaults(func=handlers.cmd_preflight)


def add_core_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    detect = subparsers.add_parser("detect", help="Detect repo language and tools", epilog=see_also_epilog("detect"))
    add_json_flag(detect)
    add_repo_args(detect, required=True)
    detect.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    detect.add_argument("--explain", action="store_true", help="Show detection reasons")
    detect.set_defaults(func=handlers.cmd_detect)

    _add_preflight_parser(subparsers, add_json_flag, handlers, "preflight", "Check environment readiness")
    _add_preflight_parser(subparsers, add_json_flag, handlers, "doctor", "Alias for preflight")

    scaffold = subparsers.add_parser(
        "scaffold", help="Generate a minimal fixture project", epilog=see_also_epilog("scaffold")
    )
    add_json_flag(scaffold)
    scaffold.add_argument(
        "type",
        nargs="?",
        help=(
            "Fixture type (python-pyproject, python-setup, python-src-layout, "
            "java-maven, java-gradle, java-multi-module, monorepo)"
        ),
    )
    scaffold.add_argument("path", nargs="?", help="Destination path")
    scaffold.add_argument("--list", action="store_true", help="List available fixture types")
    scaffold.add_argument("--force", action="store_true", help="Overwrite destination if not empty")
    scaffold.add_argument(
        "--github",
        action="store_true",
        help="Create GitHub repo, add CI config, and push",
    )
    scaffold.add_argument(
        "--private",
        action="store_true",
        help="Make GitHub repo private (default: public)",
    )
    scaffold.add_argument(
        "--repo-name",
        help="Override GitHub repo name (default: directory name)",
    )
    scaffold.add_argument(
        "--no-init",
        action="store_true",
        help="Skip adding CI config (only with --github)",
    )
    scaffold.add_argument(
        "--no-push",
        action="store_true",
        help="Skip pushing to GitHub (only with --github)",
    )
    scaffold.add_argument(
        "--wizard",
        action="store_true",
        help="Run interactive wizard to configure tools (requires cihub[wizard])",
    )
    scaffold.set_defaults(func=handlers.cmd_scaffold)

    smoke = subparsers.add_parser("smoke", help="Run a local smoke test", epilog=see_also_epilog("smoke"))
    add_json_flag(smoke)
    smoke.add_argument(
        "repo",
        nargs="?",
        help="Path to repo (omit to scaffold fixtures)",
    )
    smoke.add_argument("--subdir", help="Subdirectory for monorepos")
    smoke.add_argument(
        "--type",
        action="append",
        help=(
            "Fixture type to generate (repeatable): python-pyproject, python-setup, "
            "python-src-layout, java-maven, java-gradle, java-multi-module, monorepo"
        ),
    )
    smoke.add_argument(
        "--all",
        action="store_true",
        help="Generate and test all fixture types",
    )
    smoke.add_argument(
        "--full",
        action="store_true",
        help="Run cihub ci after init/validate",
    )
    smoke.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies during cihub ci",
    )
    smoke.add_argument(
        "--force",
        action="store_true",
        help="Allow init to overwrite existing .ci-hub.yml",
    )
    smoke.add_argument(
        "--relax",
        action="store_true",
        help="Relax tool toggles and thresholds when running full",
    )
    smoke.add_argument(
        "--keep",
        action="store_true",
        help="Keep generated fixtures on disk",
    )
    smoke.set_defaults(func=handlers.cmd_smoke)

    smoke_validate = subparsers.add_parser(
        "smoke-validate", help="Validate smoke test setup/results", epilog=see_also_epilog("smoke")
    )
    add_json_flag(smoke_validate)
    smoke_validate.add_argument("--count", type=int, help="Repo count to validate")
    smoke_validate.add_argument("--min-count", type=int, default=2, help="Minimum required repos")
    smoke_validate.add_argument("--status", help="Smoke test job status (success/failure)")
    smoke_validate.set_defaults(func=handlers.cmd_smoke_validate)

    check = subparsers.add_parser("check", help="Run local validation checks", epilog=see_also_epilog("check"))
    add_json_flag(check)
    add_ai_flags(check)
    check.add_argument(
        "--smoke-repo",
        help="Path to repo for smoke test (omit to scaffold fixtures)",
    )
    check.add_argument(
        "--smoke-subdir",
        help="Subdirectory for monorepo smoke test",
    )
    check.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies during smoke test",
    )
    check.add_argument(
        "--relax",
        action="store_true",
        help="Relax tool toggles and thresholds during smoke test",
    )
    check.add_argument(
        "--keep",
        action="store_true",
        help="Keep generated fixtures on disk",
    )
    check.add_argument(
        "--install-missing",
        action="store_true",
        help="Prompt to install missing optional tools",
    )
    check.add_argument(
        "--require-optional",
        action="store_true",
        help="Fail if optional tools are missing",
    )
    # Tiered check modes
    check.add_argument(
        "--audit",
        action="store_true",
        help="Add drift detection checks (links, adr, configs)",
    )
    check.add_argument(
        "--security",
        action="store_true",
        help="Add security checks (bandit, pip-audit, trivy, gitleaks)",
    )
    check.add_argument(
        "--full",
        action="store_true",
        help="Add validation checks (templates, matrix, license, zizmor)",
    )
    check.add_argument(
        "--mutation",
        action="store_true",
        help="Add mutation testing with mutmut (~15min, very slow)",
    )
    check.add_argument(
        "--all",
        action="store_true",
        help="Run all checks (audit + security + full + mutation)",
    )
    check.set_defaults(func=handlers.cmd_check)

    verify = subparsers.add_parser(
        "verify", help="Verify workflow/template contracts", epilog=see_also_epilog("verify")
    )
    add_json_flag(verify)
    verify.add_argument(
        "--remote",
        action="store_true",
        help="Check connected repos for template drift (requires gh auth)",
    )
    verify.add_argument(
        "--integration",
        action="store_true",
        help="Clone connected repos and run cihub ci (slow, requires gh auth)",
    )
    verify.add_argument(
        "--repo",
        action="append",
        help="Target repo (owner/name). Repeatable.",
    )
    verify.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include repos with dispatch_enabled=false",
    )
    verify.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies during integration runs",
    )
    verify.add_argument(
        "--workdir",
        help="Optional base directory for cloned repos (integration mode)",
    )
    verify.add_argument(
        "--keep",
        action="store_true",
        help="Keep cloned repos on disk (integration mode)",
    )
    verify.set_defaults(func=handlers.cmd_verify)

    ci = subparsers.add_parser("ci", help="Run CI based on .ci-hub.yml", epilog=see_also_epilog("ci"))
    add_json_flag(ci)
    add_repo_args(ci)
    ci.add_argument("--workdir", help="Override workdir/subdir")
    ci.add_argument("--correlation-id", help="Hub correlation id")
    ci.add_argument(
        "--config-from-hub",
        metavar="BASENAME",
        help="Load config from hub's config/repos/<BASENAME>.yaml (for hub-run-all)",
    )
    ci.add_argument(
        "--output-dir",
        default=".cihub",
        help="Output directory for reports (default: .cihub)",
    )
    ci.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies before running tools",
    )
    add_report_args(ci, help_text="Override report.json path")
    add_summary_args(ci, summary_help="Override summary.md path")
    ci.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip writing summary.md file",
    )
    github_summary_group = ci.add_mutually_exclusive_group()
    github_summary_group.add_argument(
        "--write-github-summary",
        action="store_true",
        dest="write_github_summary",
        help="Write summary to GITHUB_STEP_SUMMARY if set (overrides config)",
    )
    github_summary_group.add_argument(
        "--no-write-github-summary",
        dest="write_github_summary",
        action="store_false",
        help="Do not write summary to GITHUB_STEP_SUMMARY (overrides config)",
    )
    ci.set_defaults(write_github_summary=None)
    ci.set_defaults(func=handlers.cmd_ci)

    ai_loop = subparsers.add_parser("ai-loop", help="Autonomous AI CI fix loop")
    add_json_flag(ai_loop)
    add_repo_args(ai_loop)
    ai_loop.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum iterations before stopping (default: 10)",
    )
    ai_loop.add_argument(
        "--fix-mode",
        choices=["safe", "report-only"],
        default="safe",
        help="Fix strategy: safe (auto-fix) or report-only (emit report pack only)",
    )
    ai_loop.add_argument(
        "--emit-report",
        action="store_true",
        help="Generate fix report prompt pack each iteration",
    )
    ai_loop.add_argument(
        "--output-dir",
        default=".cihub/ai-loop",
        help="Output directory for loop artifacts (default: .cihub/ai-loop)",
    )
    ai_loop.add_argument(
        "--max-minutes",
        type=int,
        default=60,
        help="Maximum runtime in minutes before stopping (default: 60)",
    )
    ai_loop.add_argument(
        "--unsafe-unlimited",
        action="store_true",
        help="Allow unlimited iterations (still respects --max-minutes)",
    )
    ai_loop.add_argument(
        "--resume",
        action="store_true",
        help="Resume from an existing session directory",
    )
    ai_loop.add_argument(
        "--contract-file",
        help="Path to contract file (Markdown with YAML front matter)",
    )
    ai_loop.add_argument(
        "--contract-strict",
        action="store_true",
        help="Require contract fields to be present",
    )
    ai_loop.add_argument(
        "--review-command",
        help="Shell command to run for per-iteration review",
    )
    ai_loop.add_argument(
        "--artifact-pack",
        action="store_true",
        help="Emit artifact bundle per iteration",
    )
    ai_loop.add_argument(
        "--bundle-dir",
        help="Override bundle output directory",
    )
    ai_loop.add_argument(
        "--remote",
        action="store_true",
        help="Enable remote mode (GitHub Actions loop)",
    )
    ai_loop.add_argument(
        "--remote-provider",
        choices=["gh"],
        default="gh",
        help="Remote provider for GitHub Actions (default: gh)",
    )
    ai_loop.add_argument(
        "--remote-repo",
        help="Remote repo in owner/repo format (default: infer from git)",
    )
    ai_loop.add_argument(
        "--workflow",
        help="Workflow name or ID filter for remote runs",
    )
    ai_loop.add_argument(
        "--push",
        action="store_true",
        help="Push changes to remote before each iteration",
    )
    ai_loop.add_argument(
        "--push-branch",
        default="ai/ci-loop",
        help="Branch to push for remote loop (default: ai/ci-loop)",
    )
    ai_loop.add_argument(
        "--push-remote",
        default="origin",
        help="Remote name to push (default: origin)",
    )
    ai_loop.add_argument(
        "--allow-protected-branch",
        action="store_true",
        help="Allow pushing to protected branches (main/master)",
    )
    ai_loop.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow starting remote loop with a dirty working tree",
    )
    ai_loop.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes before pushing each iteration",
    )
    ai_loop.add_argument(
        "--commit-message",
        default="AI loop iteration",
        help="Commit message prefix (default: 'AI loop iteration')",
    )
    ai_loop.add_argument(
        "--triage-mode",
        choices=["auto", "latest", "run", "none"],
        default="auto",
        help="Remote triage mode (default: auto)",
    )
    ai_loop.add_argument(
        "--triage-run-id",
        help="Explicit run ID for remote triage",
    )
    ai_loop.add_argument(
        "--triage-output-dir",
        help="Override remote triage output directory",
    )
    ai_loop.add_argument(
        "--fallback",
        choices=["local", "stop"],
        default="stop",
        help="Fallback behavior when remote triage fails (default: stop)",
    )
    ai_loop.add_argument(
        "--remote-dry-run",
        action="store_true",
        help="Remote mode without push; triage only",
    )
    ai_loop.set_defaults(func=handlers.cmd_ai_loop)

    run = subparsers.add_parser("run", help="Run one tool and emit JSON output", epilog=see_also_epilog("run"))
    add_json_flag(run)
    run.add_argument("tool", help="Tool name (pytest, ruff, bandit, etc.)")
    add_repo_args(run)
    run.add_argument("--workdir", help="Override workdir/subdir")
    run.add_argument(
        "--output-dir",
        default=".cihub",
        help="Output directory for tool outputs (default: .cihub)",
    )
    run.add_argument("--output", help="Override tool output path")
    run.add_argument(
        "--force",
        action="store_true",
        help="Run even if tool is disabled in config",
    )
    run.set_defaults(func=handlers.cmd_run)
