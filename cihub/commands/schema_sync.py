"""Schema sync commands - generate and validate config files from schema.

Commands:
- cihub schema-sync generate-defaults: Generate defaults.yaml from schema
- cihub schema-sync generate-fallbacks: Generate fallbacks.py from schema
- cihub schema-sync check: Validate fallbacks.py matches schema (for CI audit)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from cihub.config.schema_extract import (
    compare_with_current,
    extract_all_defaults,
    generate_fallbacks_dict,
    load_schema,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.paths import hub_root


class _IndentDumper(yaml.SafeDumper):
    """YAML dumper that indents sequences to satisfy yamllint rules."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def _format_python_dict(data: dict[str, Any], indent: int = 0) -> str:
    """Format a dict as Python code with proper indentation.

    Args:
        data: Dict to format.
        indent: Current indentation level.

    Returns:
        Python code string.
    """
    lines: list[str] = []
    prefix = "    " * indent

    lines.append("{")
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        comma = "," if i < len(items) - 1 else ","
        if isinstance(value, dict):
            nested = _format_python_dict(value, indent + 1)
            lines.append(f'{prefix}    "{key}": {nested}{comma}')
        elif isinstance(value, bool):
            lines.append(f'{prefix}    "{key}": {value}{comma}')
        elif isinstance(value, str):
            lines.append(f'{prefix}    "{key}": {json.dumps(value)}{comma}')
        elif isinstance(value, (int, float)):
            lines.append(f'{prefix}    "{key}": {value}{comma}')
        elif isinstance(value, list):
            list_str = repr(value)
            lines.append(f'{prefix}    "{key}": {list_str}{comma}')
        else:
            lines.append(f'{prefix}    "{key}": {value!r}{comma}')
    lines.append(f"{prefix}}}")

    return "\n".join(lines)


def generate_defaults_yaml(
    output_path: Path | None = None,
    dry_run: bool = False,
) -> CommandResult:
    """Generate defaults.yaml from schema.

    Args:
        output_path: Output path (defaults to cihub/data/config/defaults.yaml).
        dry_run: If True, only print what would be generated.

    Returns:
        CommandResult with success status.
    """
    try:
        schema = load_schema()
        defaults = extract_all_defaults(schema)

        # Add header comment
        header = """# ============================================================================
# CI/CD Hub - Global Defaults
# ============================================================================
# AUTO-GENERATED from ci-hub-config.schema.json
# To regenerate:
#   python -c "from cihub.commands.schema_sync import generate_defaults_yaml; generate_defaults_yaml()"
#
# These settings apply to ALL repos unless overridden in the repo's .ci-hub.yml
# or in config/repos/<repo-name>.yaml
# ============================================================================

"""

        yaml_content = yaml.dump(
            defaults,
            Dumper=_IndentDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )

        full_content = header + yaml_content

        if dry_run:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Dry run - would generate defaults.yaml",
                data={"content": full_content, "keys": list(defaults.keys())},
            )

        if output_path is None:
            output_path = hub_root() / "config" / "defaults.yaml"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_content, encoding="utf-8")

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Generated {output_path}",
            files_generated=[str(output_path)],
            data={"path": str(output_path), "keys": list(defaults.keys())},
        )

    except Exception as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Failed to generate defaults.yaml: {exc}",
            problems=[{"severity": "error", "message": str(exc)}],
        )


def generate_fallbacks_py(
    output_path: Path | None = None,
    dry_run: bool = False,
) -> CommandResult:
    """Generate fallbacks.py from schema.

    Args:
        output_path: Output path (defaults to cihub/config/fallbacks.py).
        dry_run: If True, only print what would be generated.

    Returns:
        CommandResult with success status.
    """
    try:
        schema = load_schema()
        fallbacks = generate_fallbacks_dict(schema)

        # Format as Python module
        python_dict = _format_python_dict(fallbacks)
        content = f'''"""Fallback defaults for config loading when defaults.yaml is missing or empty.

AUTO-GENERATED from ci-hub-config.schema.json
To regenerate:
  python -c "from cihub.commands.schema_sync import generate_fallbacks_py; generate_fallbacks_py()"
"""

from __future__ import annotations

from typing import Any

FALLBACK_DEFAULTS: dict[str, Any] = {python_dict}
'''

        if dry_run:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Dry run - would generate fallbacks.py",
                data={"content": content, "keys": list(fallbacks.keys())},
            )

        if output_path is None:
            output_path = hub_root().parent / "config" / "fallbacks.py"
            # Fallback to source path if not in hub_root
            if not output_path.parent.exists():
                output_path = Path(__file__).parent.parent / "config" / "fallbacks.py"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not content.endswith("\n"):
            content += "\n"
        output_path.write_text(content, encoding="utf-8")

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Generated {output_path}",
            files_generated=[str(output_path)],
            data={"path": str(output_path), "keys": list(fallbacks.keys())},
        )

    except Exception as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Failed to generate fallbacks.py: {exc}",
            problems=[{"severity": "error", "message": str(exc)}],
        )


def check_schema_alignment() -> CommandResult:
    """Check that defaults.yaml and fallbacks.py match schema defaults.

    This is designed to run in CI as part of `cihub check --audit`.

    Returns:
        CommandResult with drift messages if misaligned.
    """
    try:
        schema = load_schema()
        schema_defaults = extract_all_defaults(schema)
        schema_fallbacks = generate_fallbacks_dict(schema)

        # Import current fallbacks
        from cihub.config.fallbacks import FALLBACK_DEFAULTS

        fallback_drifts = compare_with_current(schema_fallbacks, FALLBACK_DEFAULTS, label="fallbacks")

        defaults_path = hub_root() / "config" / "defaults.yaml"
        defaults_payload: dict[str, Any] = {}
        if defaults_path.exists():
            defaults_payload = yaml.safe_load(defaults_path.read_text()) or {}
        defaults_drifts = compare_with_current(schema_defaults, defaults_payload, label="defaults")

        drifts = fallback_drifts + defaults_drifts

        if drifts:
            suggestions = []
            if defaults_drifts:
                suggestions.append(
                    {
                        "message": (
                            "Run: python -c "
                            '"from cihub.commands.schema_sync import generate_defaults_yaml; '
                            'generate_defaults_yaml()"'
                        ),
                    }
                )
            if fallback_drifts:
                suggestions.append(
                    {
                        "message": (
                            "Run: python -c "
                            '"from cihub.commands.schema_sync import generate_fallbacks_py; '
                            'generate_fallbacks_py()"'
                        ),
                    }
                )
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Schema-defaults drift detected",
                problems=[{"severity": "error", "message": d} for d in drifts],
                suggestions=suggestions,
                data={
                    "drift_count": len(drifts),
                    "defaults_drift_count": len(defaults_drifts),
                    "fallbacks_drift_count": len(fallback_drifts),
                },
            )

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Schema defaults are aligned",
            data={
                "checked_keys": list(schema_defaults.keys()),
                "checked_fallback_keys": list(schema_fallbacks.keys()),
            },
        )

    except Exception as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Schema alignment check failed: {exc}",
            problems=[{"severity": "error", "message": str(exc)}],
        )


def run_schema_sync(
    subcommand: str,
    output: Path | None = None,
    dry_run: bool = False,
) -> CommandResult:
    """Run schema-sync subcommand.

    Args:
        subcommand: One of "generate-defaults", "generate-fallbacks", "check".
        output: Optional output path.
        dry_run: If True, don't write files.

    Returns:
        CommandResult with operation status.
    """
    if subcommand == "generate-defaults":
        return generate_defaults_yaml(output, dry_run)
    elif subcommand == "generate-fallbacks":
        return generate_fallbacks_py(output, dry_run)
    elif subcommand == "check":
        return check_schema_alignment()
    else:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Unknown subcommand: {subcommand}",
            problems=[{"severity": "error", "message": "Valid: generate-defaults, generate-fallbacks, check"}],
        )
