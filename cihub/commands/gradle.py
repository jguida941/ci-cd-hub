"""Gradle-related command handlers."""

from __future__ import annotations

import argparse
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.java_gradle import (
    collect_gradle_warnings,
    insert_configs_into_gradle,
    insert_plugins_into_gradle,
    load_gradle_config_snippets,
    load_gradle_plugin_snippets,
)


@dataclass
class GradleFixResult:
    """Result of a Gradle fix operation."""

    exit_code: int
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diff: str = ""
    files_modified: list[str] = field(default_factory=list)


def apply_gradle_fixes(repo_path: Path, config: dict[str, Any], apply: bool, include_configs: bool) -> GradleFixResult:
    """Apply plugin fixes to Gradle build file.

    Args:
        repo_path: Path to repository root
        config: CI configuration
        apply: If True, write changes; if False, show diff
        include_configs: If True, also insert configuration blocks

    Returns:
        GradleFixResult with exit code and messages
    """
    result = GradleFixResult(exit_code=EXIT_SUCCESS)

    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    build_path = root_path / "build.gradle"

    if not build_path.exists():
        # Check for Kotlin DSL
        kotlin_path = root_path / "build.gradle.kts"
        if kotlin_path.exists():
            result.exit_code = EXIT_FAILURE
            result.warnings.append(
                "Kotlin DSL (build.gradle.kts) detected; fix-gradle only supports Groovy DSL. "
                "Please manually add plugins to your build.gradle.kts file."
            )
            return result
        result.exit_code = EXIT_FAILURE
        result.warnings.append("build.gradle not found")
        return result

    warnings, missing_plugins = collect_gradle_warnings(repo_path, config)
    if warnings:
        result.messages.append("Gradle warnings:")
        for warning in warnings:
            result.messages.append(f"  - {warning}")
            result.warnings.append(warning)

    if not missing_plugins:
        result.messages.append("No build.gradle changes needed.")
        return result

    # Load snippets
    plugin_snippets = load_gradle_plugin_snippets()
    config_snippets = load_gradle_config_snippets()

    # Read current content
    build_text = build_path.read_text(encoding="utf-8")

    # Insert plugins
    updated_text, inserted = insert_plugins_into_gradle(build_text, missing_plugins, plugin_snippets)
    if not inserted:
        result.exit_code = EXIT_FAILURE
        result.warnings.append("Failed to update build.gradle - unable to find insertion point.")
        return result

    # Optionally insert configs
    if include_configs:
        updated_text, configs_inserted = insert_configs_into_gradle(updated_text, missing_plugins, config_snippets)
        if not configs_inserted:
            result.warnings.append("Warning: Could not insert some configuration blocks.")

    if not apply:
        diff = difflib.unified_diff(
            build_text.splitlines(),
            updated_text.splitlines(),
            fromfile=str(build_path),
            tofile=str(build_path),
            lineterm="",
        )
        result.diff = "\n".join(diff)
        return result

    build_path.write_text(updated_text, encoding="utf-8")
    result.messages.append("build.gradle updated.")
    result.files_modified.append(str(build_path))
    return result


def cmd_fix_gradle(args: argparse.Namespace) -> CommandResult:
    """Fix Gradle plugins."""
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
                    "code": "CIHUB-GRADLE-NO-CONFIG",
                }
            ],
        )

    config = load_ci_config(repo_path)

    if config.get("language") != "java":
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="fix-gradle is only supported for Java repos.",
            data={"skipped": True, "reason": "not_java"},
        )

    if config.get("java", {}).get("build_tool", "maven") != "gradle":
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="fix-gradle only supports Gradle repos.",
            data={"skipped": True, "reason": "not_gradle"},
        )

    include_configs = getattr(args, "with_configs", False)
    result = apply_gradle_fixes(repo_path, config, apply=args.apply, include_configs=include_configs)

    problems = [{"severity": "warning", "message": w, "code": "CIHUB-GRADLE-WARNING"} for w in result.warnings]

    summary = "Gradle fix applied" if args.apply else "Gradle fix dry-run complete"
    if result.exit_code == EXIT_FAILURE:
        summary = "Gradle fix failed"

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
