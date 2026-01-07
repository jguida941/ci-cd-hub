"""POM-related command handlers."""

from __future__ import annotations

import argparse
import difflib
from dataclasses import dataclass, field
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


@dataclass
class PomFixResult:
    """Result of a POM fix operation."""

    exit_code: int
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diff: str = ""
    files_modified: list[str] = field(default_factory=list)


def apply_pom_fixes(repo_path: Path, config: dict[str, Any], apply: bool) -> PomFixResult:
    """Apply plugin fixes to POM file.

    Args:
        repo_path: Path to repository root
        config: CI configuration
        apply: If True, write changes; if False, show diff

    Returns:
        PomFixResult with exit code and messages
    """
    result = PomFixResult(exit_code=EXIT_SUCCESS)

    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    pom_path = root_path / "pom.xml"

    if not pom_path.exists():
        result.exit_code = EXIT_FAILURE
        result.warnings.append("pom.xml not found")
        return result

    warnings, missing_plugins = collect_java_pom_warnings(repo_path, config)
    if warnings:
        result.messages.append("POM warnings:")
        for warning in warnings:
            result.messages.append(f"  - {warning}")
            result.warnings.append(warning)

    if not missing_plugins:
        result.messages.append("No pom.xml changes needed.")
        return result

    snippets = load_plugin_snippets()
    blocks = []
    for plugin_id in missing_plugins:
        snippet = snippets.get(plugin_id)
        if snippet:
            blocks.append(snippet)
        else:
            group_id, artifact_id = plugin_id
            msg = f"Missing snippet for plugin {group_id}:{artifact_id}"
            result.warnings.append(msg)
            result.messages.append(f"  - {msg}")

    if not blocks:
        result.exit_code = EXIT_FAILURE
        return result

    pom_text = pom_path.read_text(encoding="utf-8")
    plugin_block = "\n\n".join(blocks)
    updated_text, inserted = insert_plugins_into_pom(pom_text, plugin_block)

    if not inserted:
        result.exit_code = EXIT_FAILURE
        result.warnings.append("Failed to update pom.xml - unable to find insertion point.")
        return result

    if not apply:
        diff = difflib.unified_diff(
            pom_text.splitlines(),
            updated_text.splitlines(),
            fromfile=str(pom_path),
            tofile=str(pom_path),
            lineterm="",
        )
        result.diff = "\n".join(diff)
        return result

    pom_path.write_text(updated_text, encoding="utf-8")
    result.messages.append("pom.xml updated.")
    result.files_modified.append(str(pom_path))
    return result


def apply_dependency_fixes(repo_path: Path, config: dict[str, Any], apply: bool) -> PomFixResult:
    """Apply dependency fixes to POM files.

    Args:
        repo_path: Path to repository root
        config: CI configuration
        apply: If True, write changes; if False, show diff

    Returns:
        PomFixResult with exit code and messages
    """
    result = PomFixResult(exit_code=EXIT_SUCCESS)

    warnings, missing = collect_java_dependency_warnings(repo_path, config)
    if warnings:
        result.messages.append("Dependency warnings:")
        for warning in warnings:
            result.messages.append(f"  - {warning}")
            result.warnings.append(warning)

    if not missing:
        result.messages.append("No dependency changes needed.")
        return result

    snippets = load_dependency_snippets()
    per_pom: dict[Path, list[str]] = {}
    for pom_path, dep_id in missing:
        snippet = snippets.get(dep_id)
        if not snippet:
            group_id, artifact_id = dep_id
            msg = f"Missing snippet for dependency {group_id}:{artifact_id}"
            result.messages.append(msg)
            result.warnings.append(msg)
            continue
        per_pom.setdefault(pom_path, []).append(snippet)

    if not per_pom:
        result.exit_code = EXIT_FAILURE
        return result

    diffs: list[str] = []
    for pom_path, blocks in per_pom.items():
        pom_text = pom_path.read_text(encoding="utf-8")
        dep_block = "\n\n".join(blocks)
        updated_text, inserted = insert_dependencies_into_pom(pom_text, dep_block)

        if not inserted:
            result.exit_code = EXIT_FAILURE
            result.warnings.append(f"Failed to update {pom_path} - unable to find insertion point.")
            return result

        if not apply:
            diff = difflib.unified_diff(
                pom_text.splitlines(),
                updated_text.splitlines(),
                fromfile=str(pom_path),
                tofile=str(pom_path),
                lineterm="",
            )
            diffs.append("\n".join(diff))
        else:
            pom_path.write_text(updated_text, encoding="utf-8")
            result.messages.append(f"{pom_path} updated.")
            result.files_modified.append(str(pom_path))

    if diffs:
        result.diff = "\n\n".join(diffs)

    return result


def cmd_fix_pom(args: argparse.Namespace) -> CommandResult:
    """Fix POM plugins and dependencies."""
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"

    if not config_path.exists():
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Config not found: {config_path}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Config not found: {config_path}",
                    "code": "CIHUB-POM-NO-CONFIG",
                }
            ],
        )

    config = load_ci_config(repo_path)

    if config.get("language") != "java":
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="fix-pom is only supported for Java repos.",
            data={"skipped": True, "reason": "not_java"},
        )

    if config.get("java", {}).get("build_tool", "maven") != "maven":
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="fix-pom only supports Maven repos.",
            data={"skipped": True, "reason": "not_maven"},
        )

    # Apply plugin fixes
    plugin_result = apply_pom_fixes(repo_path, config, apply=args.apply)

    # Apply dependency fixes
    dep_result = apply_dependency_fixes(repo_path, config, apply=args.apply)

    # Merge results
    exit_code = max(plugin_result.exit_code, dep_result.exit_code)
    messages = plugin_result.messages + dep_result.messages
    warnings = plugin_result.warnings + dep_result.warnings
    files_modified = plugin_result.files_modified + dep_result.files_modified
    diffs = []
    if plugin_result.diff:
        diffs.append(plugin_result.diff)
    if dep_result.diff:
        diffs.append(dep_result.diff)

    problems = [{"severity": "warning", "message": w, "code": "CIHUB-POM-WARNING"} for w in warnings]

    summary = "POM fix applied" if args.apply else "POM fix dry-run complete"
    if exit_code == EXIT_FAILURE:
        summary = "POM fix failed"

    data: dict[str, Any] = {
        "applied": bool(args.apply),
        "items": messages,
    }
    if diffs:
        data["raw_output"] = "\n\n".join(diffs)

    return CommandResult(
        exit_code=exit_code,
        summary=summary,
        problems=problems,
        files_modified=files_modified,
        data=data,
    )


def cmd_fix_deps(args: argparse.Namespace) -> CommandResult:
    """Fix POM dependencies."""
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"

    if not config_path.exists():
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Config not found: {config_path}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Config not found: {config_path}",
                    "code": "CIHUB-DEPS-NO-CONFIG",
                }
            ],
        )

    config = load_ci_config(repo_path)

    if config.get("language") != "java":
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="fix-deps is only supported for Java repos.",
            data={"skipped": True, "reason": "not_java"},
        )

    if config.get("java", {}).get("build_tool", "maven") != "maven":
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="fix-deps only supports Maven repos.",
            data={"skipped": True, "reason": "not_maven"},
        )

    result = apply_dependency_fixes(repo_path, config, apply=args.apply)

    problems = [{"severity": "warning", "message": w, "code": "CIHUB-DEPS-WARNING"} for w in result.warnings]

    summary = "Dependencies applied" if args.apply else "Dependency dry-run complete"
    if result.exit_code == EXIT_FAILURE:
        summary = "Dependency fix failed"

    data: dict[str, Any] = {
        "applied": bool(args.apply),
        "items": result.messages,
    }
    if result.diff:
        data["raw_output"] = result.diff

    return CommandResult(
        exit_code=result.exit_code,
        summary=summary,
        problems=problems,
        files_modified=result.files_modified,
        data=data,
    )
