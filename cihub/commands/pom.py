"""POM-related command handlers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cihub.cli import apply_dependency_fixes, apply_pom_fixes, load_effective_config


def cmd_fix_pom(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2
    config = load_effective_config(repo_path)
    if config.get("language") != "java":
        print("fix-pom is only supported for Java repos.")
        return 0
    if config.get("java", {}).get("build_tool", "maven") != "maven":
        print("fix-pom only supports Maven repos.")
        return 0
    return apply_pom_fixes(repo_path, config, apply=args.apply)


def cmd_fix_deps(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2
    config = load_effective_config(repo_path)
    if config.get("language") != "java":
        print("fix-deps is only supported for Java repos.")
        return 0
    if config.get("java", {}).get("build_tool", "maven") != "maven":
        print("fix-deps only supports Maven repos.")
        return 0
    return apply_dependency_fixes(repo_path, config, apply=args.apply)
