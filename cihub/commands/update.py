"""Update command handler."""

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
    deep_merge,
    load_effective_config,
    read_yaml,
    render_caller_workflow,
    resolve_language,
    write_text,
    write_yaml,
)


def cmd_update(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    existing = read_yaml(config_path) if config_path.exists() else {}

    language = args.language or existing.get("language")
    if not language:
        language, _ = resolve_language(repo_path, None)

    owner = args.owner or existing.get("repo", {}).get("owner", "")
    name = args.name or existing.get("repo", {}).get("name", "")
    repo_existing = (
        existing.get("repo", {}) if isinstance(existing.get("repo"), dict) else {}
    )
    branch = args.branch or repo_existing.get("default_branch", "main")
    subdir = args.subdir or repo_existing.get("subdir")

    if not name:
        name = repo_path.name
    if not owner:
        owner = "unknown"
        print(
            "Warning: could not detect repo owner; set repo.owner manually.",
            file=sys.stderr,
        )

    base = build_repo_config(language, owner, name, branch, subdir=subdir)
    merged = deep_merge(base, existing)
    write_yaml(config_path, merged, args.dry_run)

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
                apply_pom_fixes(repo_path, effective, apply=True)
                apply_dependency_fixes(repo_path, effective, apply=True)
            else:
                print("Run: cihub fix-pom --repo . --apply")
    return 0
