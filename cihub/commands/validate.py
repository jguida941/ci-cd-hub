"""Validate command handler."""

from __future__ import annotations

import argparse
from pathlib import Path

from cihub.ci_config import load_ci_config
from cihub.config.io import ConfigParseError, load_yaml_file
from cihub.config.paths import PathConfig
from cihub.config.schema import validate_config as validate_config_schema
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils import collect_java_dependency_warnings, collect_java_pom_warnings
from cihub.utils.paths import hub_root


def cmd_validate(args: argparse.Namespace) -> CommandResult:
    """Validate CI-Hub configuration.

    Always returns CommandResult for consistent output handling.
    """
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    items: list[str] = []  # Human-readable output
    problems: list[dict[str, str]] = []

    if not config_path.exists():
        message = f"Config not found: {config_path}"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[
                {
                    "severity": "error",
                    "message": message,
                    "code": "CIHUB-VALIDATE-001",
                    "file": str(config_path),
                }
            ],
        )

    # Try to load and parse the YAML file
    try:
        config = load_yaml_file(config_path)
    except ConfigParseError as exc:
        # ConfigParseError wraps both YAML syntax errors and non-mapping errors
        message = str(exc)
        items.append(message)
        # Determine error code based on cause
        error_code = "CIHUB-VALIDATE-003"  # Default to YAML syntax error
        summary = "Invalid YAML syntax"
        if "Expected mapping" in message:
            error_code = "CIHUB-VALIDATE-004"
            summary = "Invalid config structure"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=summary,
            problems=[
                {
                    "severity": "error",
                    "message": message,
                    "code": error_code,
                    "file": str(config_path),
                }
            ],
            data={"items": items},
        )
    paths = PathConfig(str(hub_root()))
    errors = validate_config_schema(config, paths)

    if errors:
        validation_problems = [
            {
                "severity": "error",
                "message": err,
                "code": "CIHUB-VALIDATE-002",
                "file": str(config_path),
            }
            for err in errors
        ]
        items.append("Validation failed:")
        for err in errors:
            items.append(f"  - {err}")
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Validation failed",
            problems=validation_problems,
            data={"items": items},
        )

    items.append("Config OK")
    effective = load_ci_config(repo_path)

    if effective.get("language") == "java":
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        warnings = pom_warnings + dep_warnings
        if warnings:
            pom_problems = [
                {
                    "severity": "warning",
                    "message": warning,
                    "code": "CIHUB-POM-001",
                    "file": str(repo_path / "pom.xml"),
                }
                for warning in warnings
            ]
            problems.extend(pom_problems)
            items.append("POM warnings:")
            for warning in warnings:
                items.append(f"  - {warning}")
            exit_code = EXIT_FAILURE if args.strict else EXIT_SUCCESS
            summary = "POM warnings found"
            return CommandResult(
                exit_code=exit_code,
                summary=summary,
                problems=problems,
                data={"language": effective.get("language"), "items": items},
            )
        else:
            items.append("POM OK")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Config OK",
        problems=problems,
        data={"language": effective.get("language"), "items": items},
    )
