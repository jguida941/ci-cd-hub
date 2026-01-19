"""Parser setup for repo initialization commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_repo_setup_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    new = subparsers.add_parser("new", help="Create hub-side repo config", epilog=see_also_epilog("new"))
    add_json_flag(new)
    new.add_argument("name", help="Repo config name (config/repos/<name>.yaml)")
    new.add_argument("--owner", help="Repo owner (GitHub user/org)")
    new.add_argument(
        "--language",
        choices=["java", "python"],
        help="Repo language",
    )
    new.add_argument("--branch", help="Default branch (e.g., main)")
    new.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    new.add_argument("--profile", help="Apply a profile from templates/profiles")
    new.add_argument("--tier", choices=["strict", "standard", "relaxed"], help="Tier for registry entry")
    new.add_argument(
        "--use-registry",
        action="store_true",
        help="Create via registry (enables sync to config/repos/*.yaml)",
    )
    new.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive wizard (requires cihub[wizard])",
    )
    new_config = new.add_mutually_exclusive_group()
    new_config.add_argument(
        "--config-json",
        help="Inline JSON config override (TypeScript wizard handoff)",
    )
    new_config.add_argument(
        "--config-file",
        help="Path to YAML/JSON config override (TypeScript wizard handoff)",
    )
    new.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    new.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    new.set_defaults(func=handlers.cmd_new)

    init = subparsers.add_parser("init", help="Generate .ci-hub.yml and hub-ci.yml", epilog=see_also_epilog("init"))
    add_json_flag(init)
    init.add_argument("--repo", required=True, help="Path to repo")
    init.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    init.add_argument("--owner", help="Repo owner (GitHub user/org)")
    init.add_argument("--name", help="Repo name")
    init.add_argument("--branch", help="Default branch (e.g., main)")
    init.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    init.add_argument("--workdir", dest="subdir", help="Alias for --subdir")
    init.add_argument(
        "--fix-pom",
        action="store_true",
        help="Fix pom.xml for Java repos (adds missing plugins/dependencies)",
    )
    init.add_argument(
        "--apply",
        action="store_true",
        help="Write files (default: dry-run)",
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="Override repo_side_execution guardrails",
    )
    init.add_argument(
        "--wizard",
        action="store_true",
        help="Run interactive wizard (requires cihub[wizard])",
    )
    init_config = init.add_mutually_exclusive_group()
    init_config.add_argument(
        "--config-json",
        help="Inline JSON config override (TypeScript wizard handoff)",
    )
    init_config.add_argument(
        "--config-file",
        help="Path to YAML/JSON config override (TypeScript wizard handoff)",
    )
    init.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    init.add_argument(
        "--install-from",
        choices=["pypi", "git", "local"],
        default="pypi",
        help="How cihub should be installed in CI: pypi (default), git, or local",
    )
    init.add_argument(
        "--hub-repo",
        help="Hub repo (owner/name) for setting HUB_REPO (default: CIHUB_HUB_REPO or template)",
    )
    init.add_argument(
        "--hub-ref",
        help="Hub ref (tag/sha/branch) for setting HUB_REF (default: CIHUB_HUB_REF or template)",
    )
    init.add_argument(
        "--set-hub-vars",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Set HUB_REPO/HUB_REF repo variables via gh (default: true)",
    )
    init.set_defaults(func=handlers.cmd_init)

    update = subparsers.add_parser(
        "update", help="Refresh hub-ci.yml and .ci-hub.yml", epilog=see_also_epilog("update")
    )
    add_json_flag(update)
    update.add_argument("--repo", required=True, help="Path to repo")
    update.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    update.add_argument("--owner", help="Repo owner (GitHub user/org)")
    update.add_argument("--name", help="Repo name")
    update.add_argument("--branch", help="Default branch (e.g., main)")
    update.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    update.add_argument("--workdir", dest="subdir", help="Alias for --subdir")
    update.add_argument(
        "--fix-pom",
        action="store_true",
        help="Fix pom.xml for Java repos (adds missing plugins/dependencies)",
    )
    update.add_argument(
        "--apply",
        action="store_true",
        help="Write files (default: dry-run)",
    )
    update.add_argument(
        "--force",
        action="store_true",
        help="Override repo_side_execution guardrails",
    )
    update.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    update.set_defaults(func=handlers.cmd_update)

    validate = subparsers.add_parser(
        "validate",
        help="Validate .ci-hub.yml against schema",
        epilog=see_also_epilog("validate"),
    )
    add_json_flag(validate)
    validate.add_argument("--repo", required=True, help="Path to repo")
    validate.add_argument("--strict", action="store_true", help="Fail if pom.xml warnings are found")
    validate.set_defaults(func=handlers.cmd_validate)

    # Complete setup wizard that orchestrates the full onboarding workflow
    setup = subparsers.add_parser(
        "setup",
        help="Complete setup wizard for onboarding repos to CI/CD Hub",
        description=(
            "Interactive wizard that guides you through the complete CI/CD setup process: "
            "scaffold → detect → configure → validate → run CI → push to GitHub"
        ),
        epilog=see_also_epilog("setup"),
    )
    add_json_flag(setup)
    setup.add_argument(
        "--repo",
        default=".",
        help="Path to repository (default: current directory)",
    )
    setup.add_argument(
        "--new",
        action="store_true",
        help="Force creation of a new project (scaffold)",
    )
    setup.add_argument(
        "--skip-github",
        action="store_true",
        help="Skip GitHub repository setup steps",
    )
    setup.add_argument(
        "--hub-repo",
        help="Hub repo (owner/name) for setting HUB_REPO (default: CIHUB_HUB_REPO or template)",
    )
    setup.add_argument(
        "--hub-ref",
        help="Hub ref (tag/sha/branch) for setting HUB_REF (default: CIHUB_HUB_REF or template)",
    )
    setup.add_argument(
        "--set-hub-vars",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Set HUB_REPO/HUB_REF repo variables via gh (default: true)",
    )
    setup.add_argument(
        "--hub-mode",
        action="store_true",
        help="Use registry-integrated hub-side mode (writes to registry + config/repos)",
    )
    setup.add_argument(
        "--tier",
        choices=["strict", "standard", "relaxed"],
        default=None,
        help="Quality tier for thresholds (prompts if not specified)",
    )
    setup.set_defaults(func=handlers.cmd_setup)
