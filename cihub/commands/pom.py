"""POM-related command handlers."""

from __future__ import annotations

import argparse
import difflib
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.java_pom import (
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    insert_dependencies_into_pom,
    insert_plugins_into_pom,
    load_dependency_snippets,
    load_plugin_snippets,
)


def apply_pom_fixes(repo_path: Path, config: dict[str, Any], apply: bool) -> int:
    """Apply plugin fixes to POM file.

    Args:
        repo_path: Path to repository root
        config: CI configuration
        apply: If True, write changes; if False, show diff

    Returns:
        Exit code
    """
    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        print("pom.xml not found", file=sys.stderr)
        return EXIT_FAILURE

    warnings, missing_plugins = collect_java_pom_warnings(repo_path, config)
    if warnings:
        print("POM warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if not missing_plugins:
        print("No pom.xml changes needed.")
        return EXIT_SUCCESS

    snippets = load_plugin_snippets()
    blocks = []
    for plugin_id in missing_plugins:
        snippet = snippets.get(plugin_id)
        if snippet:
            blocks.append(snippet)
        else:
            group_id, artifact_id = plugin_id
            warnings.append(f"Missing snippet for plugin {group_id}:{artifact_id}")
    if not blocks:
        for warning in warnings:
            print(f"  - {warning}")
        return EXIT_FAILURE

    pom_text = pom_path.read_text(encoding="utf-8")
    plugin_block = "\n\n".join(blocks)
    updated_text, inserted = insert_plugins_into_pom(pom_text, plugin_block)
    if not inserted:
        print(
            "Failed to update pom.xml - unable to find insertion point.",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    if not apply:
        diff = difflib.unified_diff(
            pom_text.splitlines(),
            updated_text.splitlines(),
            fromfile=str(pom_path),
            tofile=str(pom_path),
            lineterm="",
        )
        print("\n".join(diff))
        return EXIT_SUCCESS

    pom_path.write_text(updated_text, encoding="utf-8")
    print("pom.xml updated.")
    return EXIT_SUCCESS


def apply_dependency_fixes(repo_path: Path, config: dict[str, Any], apply: bool) -> int:
    """Apply dependency fixes to POM files.

    Args:
        repo_path: Path to repository root
        config: CI configuration
        apply: If True, write changes; if False, show diff

    Returns:
        Exit code
    """
    warnings, missing = collect_java_dependency_warnings(repo_path, config)
    if warnings:
        print("Dependency warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if not missing:
        print("No dependency changes needed.")
        return EXIT_SUCCESS

    snippets = load_dependency_snippets()
    per_pom: dict[Path, list[str]] = {}
    for pom_path, dep_id in missing:
        snippet = snippets.get(dep_id)
        if not snippet:
            group_id, artifact_id = dep_id
            print(f"Missing snippet for dependency {group_id}:{artifact_id}")
            continue
        per_pom.setdefault(pom_path, []).append(snippet)

    if not per_pom:
        return EXIT_FAILURE

    for pom_path, blocks in per_pom.items():
        pom_text = pom_path.read_text(encoding="utf-8")
        dep_block = "\n\n".join(blocks)
        updated_text, inserted = insert_dependencies_into_pom(pom_text, dep_block)
        if not inserted:
            print(f"Failed to update {pom_path} - unable to find insertion point.")
            return EXIT_FAILURE
        if not apply:
            diff = difflib.unified_diff(
                pom_text.splitlines(),
                updated_text.splitlines(),
                fromfile=str(pom_path),
                tofile=str(pom_path),
                lineterm="",
            )
            print("\n".join(diff))
        else:
            pom_path.write_text(updated_text, encoding="utf-8")
            print(f"{pom_path} updated.")
    return EXIT_SUCCESS


def cmd_fix_pom(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo).resolve()
    json_mode = getattr(args, "json", False)
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        message = f"Config not found: {config_path}"
        if json_mode:
            return CommandResult(exit_code=EXIT_USAGE, summary=message)
        print(message, file=sys.stderr)
        return EXIT_USAGE
    config = load_ci_config(repo_path)
    if config.get("language") != "java":
        message = "fix-pom is only supported for Java repos."
        if json_mode:
            return CommandResult(exit_code=EXIT_SUCCESS, summary=message)
        print(message)
        return EXIT_SUCCESS
    if config.get("java", {}).get("build_tool", "maven") != "maven":
        message = "fix-pom only supports Maven repos."
        if json_mode:
            return CommandResult(exit_code=EXIT_SUCCESS, summary=message)
        print(message)
        return EXIT_SUCCESS
    if json_mode:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = apply_pom_fixes(repo_path, config, apply=args.apply)
            status = max(status, apply_dependency_fixes(repo_path, config, apply=args.apply))
        summary = "POM fix applied" if args.apply else "POM fix dry-run complete"
        return CommandResult(
            exit_code=status,
            summary=summary,
            data={"applied": bool(args.apply)},
        )
    status = apply_pom_fixes(repo_path, config, apply=args.apply)
    status = max(status, apply_dependency_fixes(repo_path, config, apply=args.apply))
    return status


def cmd_fix_deps(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo).resolve()
    json_mode = getattr(args, "json", False)
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        message = f"Config not found: {config_path}"
        if json_mode:
            return CommandResult(exit_code=EXIT_USAGE, summary=message)
        print(message, file=sys.stderr)
        return EXIT_USAGE
    config = load_ci_config(repo_path)
    if config.get("language") != "java":
        message = "fix-deps is only supported for Java repos."
        if json_mode:
            return CommandResult(exit_code=EXIT_SUCCESS, summary=message)
        print(message)
        return EXIT_SUCCESS
    if config.get("java", {}).get("build_tool", "maven") != "maven":
        message = "fix-deps only supports Maven repos."
        if json_mode:
            return CommandResult(exit_code=EXIT_SUCCESS, summary=message)
        print(message)
        return EXIT_SUCCESS
    if json_mode:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = apply_dependency_fixes(repo_path, config, apply=args.apply)
        summary = "Dependencies applied" if args.apply else "Dependency dry-run complete"
        return CommandResult(
            exit_code=status,
            summary=summary,
            data={"applied": bool(args.apply)},
        )
    return apply_dependency_fixes(repo_path, config, apply=args.apply)
