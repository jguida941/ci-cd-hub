"""Init command handlers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cihub.cli import (
    apply_dependency_fixes,
    apply_pom_fixes,
    build_repo_config,
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    get_git_branch,
    get_git_remote,
    hub_root,
    load_effective_config,
    parse_repo_from_remote,
    render_caller_workflow,
    resolve_language,
    write_text,
    write_yaml,
)
from cihub.config.paths import PathConfig
from cihub.wizard import HAS_WIZARD


def cmd_init(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    language, _ = resolve_language(repo_path, args.language)

    owner = args.owner or ""
    name = args.name or ""
    if not owner or not name:
        remote = get_git_remote(repo_path)
        if remote:
            git_owner, git_name = parse_repo_from_remote(remote)
            owner = owner or (git_owner or "")
            name = name or (git_name or "")

    if not name:
        name = repo_path.name
    if not owner:
        owner = "unknown"
        print(
            "Warning: could not detect repo owner; set repo.owner manually.",
            file=sys.stderr,
        )

    branch = args.branch or get_git_branch(repo_path) or "main"

    subdir = args.subdir or ""
    detected_config = build_repo_config(language, owner, name, branch, subdir=subdir)

    if args.wizard:
        if not HAS_WIZARD:
            print("Install wizard deps: pip install cihub[wizard]", file=sys.stderr)
            return 1
        from rich.console import Console

        from cihub.wizard.core import WizardRunner

        runner = WizardRunner(Console(), PathConfig(str(hub_root())))
        config = runner.run_init_wizard(detected_config)
        language = config.get("language", language)
    else:
        config = detected_config
    config_path = repo_path / ".ci-hub.yml"
    write_yaml(config_path, config, args.dry_run)

    workflow_path = repo_path / ".github" / "workflows" / "hub-ci.yml"
    workflow_content = render_caller_workflow(language)
    write_text(workflow_path, workflow_content, args.dry_run)

    if language == "java" and not args.dry_run:
        effective = load_effective_config(repo_path)
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        warnings = pom_warnings + dep_warnings
        if warnings:
            print("POM warnings:")
            for warning in warnings:
                print(f"  - {warning}")
            if args.fix_pom:
                status = apply_pom_fixes(repo_path, effective, apply=True)
                status = max(
                    status, apply_dependency_fixes(repo_path, effective, apply=True)
                )
                return status
            print("Run: cihub fix-pom --repo . --apply")

    return 0
