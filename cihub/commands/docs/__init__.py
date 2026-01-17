"""Documentation commands package.

This package provides documentation generation and validation:
- generate: Generate CLI, config, and workflow reference docs
- check: Verify generated docs are up to date
- links: Check for broken links in documentation
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult

from .generate import (
    render_cli_reference,
    render_config_reference,
    render_env_reference,
    render_tools_reference,
    render_workflows_reference,
)
from .links import (
    _check_internal_links,
    _run_lychee,
    cmd_docs_links,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def cmd_docs(args: argparse.Namespace) -> CommandResult:
    """Generate or check reference documentation.

    Always returns CommandResult for consistent output handling.
    """
    output_dir = Path(getattr(args, "output", "docs/reference"))
    check = args.subcommand == "check" or bool(getattr(args, "check", False))

    outputs = {
        "CLI.md": render_cli_reference(),
        "CONFIG.md": render_config_reference(),
        "ENV.md": render_env_reference(),
        "TOOLS.md": render_tools_reference(),
        "WORKFLOWS.md": render_workflows_reference(),
    }

    missing: list[str] = []
    changed: list[str] = []
    files_generated: list[str] = []
    files_modified: list[str] = []

    for name, content in outputs.items():
        path = output_dir / name
        if check:
            if not path.exists():
                missing.append(str(path))
                continue
            existing = path.read_text(encoding="utf-8")
            if existing != content:
                changed.append(str(path))
            continue

        existed = path.exists()
        _write(path, content)
        if existed:
            files_modified.append(str(path))
        else:
            files_generated.append(str(path))

    if check:
        if missing or changed:
            summary = "Docs are out of date"
            problems = []
            for p in missing:
                problems.append(
                    {
                        "severity": "error",
                        "message": f"Missing generated doc: {p}",
                        "code": "CIHUB-DOCS-MISSING",
                    }
                )
            for p in changed:
                problems.append(
                    {
                        "severity": "error",
                        "message": f"Docs differ from generated output: {p}",
                        "code": "CIHUB-DOCS-DRIFT",
                    }
                )
            suggestions = [
                {
                    "message": "Run: cihub docs generate",
                    "code": "CIHUB-DOCS-GENERATE",
                }
            ]
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=summary,
                problems=problems,
                suggestions=suggestions,
            )

        return CommandResult(exit_code=EXIT_SUCCESS, summary="Docs are up to date")

    # Generate mode - format output for display
    items = ["Docs generated"]
    for p in files_generated:
        items.append(f"Generated: {p}")
    for p in files_modified:
        items.append(f"Updated: {p}")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Docs generated",
        files_generated=files_generated,
        files_modified=files_modified,
        data={"items": items},
    )


__all__ = [
    "cmd_docs",
    "cmd_docs_links",
    "render_cli_reference",
    "render_config_reference",
    "render_env_reference",
    "render_tools_reference",
    "render_workflows_reference",
    # Internal functions (for tests)
    "_check_internal_links",
    "_run_lychee",
]
