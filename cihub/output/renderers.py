"""Output renderers for cihub CLI.

This module provides the OutputRenderer abstraction and concrete implementations.
All formatting logic is centralized here - commands just return CommandResult
with structured data and the renderer decides how to display it.

Classes:
    OutputRenderer: Abstract base class for renderers
    HumanRenderer: Renders CommandResult for human consumption
    JsonRenderer: Renders CommandResult as JSON
    AIRenderer: Renders CommandResult as AI-consumable markdown

Functions:
    get_renderer: Factory function to get appropriate renderer
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Sequence

from cihub.exit_codes import EXIT_SUCCESS

if TYPE_CHECKING:
    from cihub.types import CommandResult


class OutputRenderer(ABC):
    """Abstract base class for output renderers.

    All output formatting flows through renderers. Commands return CommandResult
    with structured data, and renderers transform it to the appropriate format.
    """

    @abstractmethod
    def render(self, result: "CommandResult", command: str, duration_ms: int) -> str:
        """Render a CommandResult to output string.

        Args:
            result: The CommandResult from a command.
            command: Name of the command that was executed.
            duration_ms: Execution time in milliseconds.

        Returns:
            Formatted output string.
        """
        pass


class HumanRenderer(OutputRenderer):
    """Renders CommandResult for human consumption.

    Handles different data types in result.data:
    - "items": List of strings -> bullet list
    - "table": {"headers": [], "rows": []} -> formatted table
    - "key_values": dict -> aligned key-value pairs
    - "raw_output": str -> preformatted text
    """

    def render(self, result: "CommandResult", command: str, duration_ms: int) -> str:
        """Render CommandResult as human-readable text."""
        lines: list[str] = []

        # Summary
        if result.summary:
            lines.append(result.summary)

        # Structured data
        if result.data:
            data_output = self._render_data(result.data)
            if data_output:
                if lines:
                    lines.append("")  # Blank line separator
                lines.append(data_output)

        # Problems
        if result.problems:
            if lines:
                lines.append("")
            lines.append(self._render_problems(result.problems))

        # Suggestions
        if result.suggestions:
            if lines:
                lines.append("")
            lines.append("Suggestions:")
            lines.append(self._render_list([s.get("message", "") for s in result.suggestions]))

        # File outputs
        if result.files_generated:
            if lines:
                lines.append("")
            lines.append(f"Generated: {', '.join(result.files_generated)}")

        if result.files_modified:
            if lines:
                lines.append("")
            lines.append(f"Modified: {', '.join(result.files_modified)}")

        return "\n".join(lines)

    def _render_data(self, data: dict[str, Any]) -> str:
        """Render the data dict based on known types."""
        parts: list[str] = []

        # Handle known data types
        if "items" in data:
            parts.append(self._render_list(data["items"]))

        if "table" in data:
            table_data = data["table"]
            parts.append(self._render_table(table_data.get("rows", []), table_data.get("headers")))

        if "key_values" in data:
            parts.append(self._render_key_values(data["key_values"]))

        if "raw_output" in data:
            parts.append(data["raw_output"])

        # For other data, show as formatted output if meaningful
        # Skip internal keys not meant for human display:
        # - *_report: For AIRenderer
        # - Keys with complex nested structures (lists, dicts)
        known_keys = {"items", "table", "key_values", "raw_output"}
        other_keys = {
            k
            for k in data.keys()
            if k not in known_keys
            and not k.endswith("_report")
            and not isinstance(data[k], (list, dict))  # Skip complex nested data
        }
        if other_keys and not parts:
            # Show simple data as key-value pairs
            other_data = {k: data[k] for k in other_keys}
            parts.append(self._render_key_values(other_data))

        return "\n".join(parts)

    def _render_list(self, items: Sequence[str], prefix: str = "  - ") -> str:
        """Render items as a bullet list."""
        if not items:
            return ""
        return "\n".join(f"{prefix}{item}" for item in items)

    def _render_table(
        self,
        rows: Sequence[dict[str, Any] | Sequence[Any]],
        headers: Sequence[str] | None = None,
    ) -> str:
        """Render rows as a formatted table."""
        if not rows:
            return ""

        # Determine headers
        first_row = rows[0]
        if headers is None:
            if isinstance(first_row, dict):
                headers = list(first_row.keys())
            else:
                headers = [f"col{i}" for i in range(len(first_row))]

        # Convert rows to lists of strings
        data_rows: list[list[str]] = []
        for row in rows:
            if isinstance(row, dict):
                data_rows.append([str(row.get(h, "")) for h in headers])
            else:
                data_rows.append([str(v) for v in row])

        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in data_rows:
            for i, val in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(val))

        # Cap widths at 50
        widths = [min(w, 50) for w in widths]

        # Build table
        sep = " | "
        header_line = sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))
        divider = sep.join("-" * widths[i] for i in range(len(headers)))

        formatted_rows = []
        for row in data_rows:
            cells = []
            for i, val in enumerate(row):
                width = widths[i] if i < len(widths) else 10
                if len(val) > width:
                    val = val[: width - 3] + "..."
                cells.append(val.ljust(width))
            formatted_rows.append(sep.join(cells))

        return "\n".join([header_line, divider] + formatted_rows)

    def _render_key_values(self, items: dict[str, Any]) -> str:
        """Render dict as aligned key-value pairs."""
        if not items:
            return ""

        key_width = max(len(str(k)) for k in items.keys())
        lines = []
        for key, value in items.items():
            lines.append(f"  {str(key).ljust(key_width)}: {value}")
        return "\n".join(lines)

    def _render_problems(self, problems: Sequence[dict[str, Any]]) -> str:
        """Render problems with severity icons.

        Note: We avoid using [warning] and [error] brackets because GitHub Actions
        parses these as annotations and corrupts the output.
        """
        # Format: "severity: icon message" - no brackets to avoid GitHub Actions parsing
        prefixes = {
            "error": "ERROR",
            "warning": "WARN",
            "info": "INFO",
            "success": "OK",
            "critical": "CRIT",
        }
        icons = {
            "error": "✗",
            "warning": "⚠",
            "info": "ℹ",
            "success": "✓",
            "critical": "☠",
        }

        lines = []
        for p in problems:
            severity = p.get("severity", "info")
            message = p.get("message", "Unknown issue")
            prefix = prefixes.get(severity.lower(), "INFO")
            icon = icons.get(severity.lower(), "•")
            lines.append(f"  {prefix}: {icon} {message}")

        return "\n".join(lines)


class JsonRenderer(OutputRenderer):
    """Renders CommandResult as JSON.

    Uses CommandResult.to_payload() for consistent JSON structure.
    """

    def render(self, result: "CommandResult", command: str, duration_ms: int) -> str:
        """Render CommandResult as JSON string."""
        status = "success" if result.exit_code == EXIT_SUCCESS else "failure"
        payload = result.to_payload(command, status, duration_ms)
        return json.dumps(payload, indent=2, default=str)


class AIRenderer(OutputRenderer):
    """Renders CommandResult as AI-consumable markdown.

    Uses a registry to look up command-specific formatters. Each command
    that supports --ai mode registers its formatter in ai_formatters.py.

    Falls back to a structured JSON prompt if no formatter is registered
    for the command.
    """

    def render(self, result: "CommandResult", command: str, duration_ms: int) -> str:
        """Render CommandResult using command-specific AI formatter."""
        from .ai_formatters import get_ai_formatter

        formatter = get_ai_formatter(command)

        if formatter:
            # Find report data in result.data
            # Convention: report objects under "*_report" keys
            report_key = self._find_report_key(result.data)
            if report_key:
                return formatter(result.data[report_key])

        # Fallback: format data as structured prompt
        return self._default_format(result, command)

    def _find_report_key(self, data: dict[str, Any]) -> str | None:
        """Find the report key in data dict.

        Looks for keys ending with '_report' (e.g., 'stale_report').
        """
        for key in data:
            if key.endswith("_report"):
                return key
        return None

    def _default_format(self, result: "CommandResult", command: str) -> str:
        """Default AI format when no specific formatter exists.

        Produces a structured prompt with summary and JSON data that
        any AI can process.
        """
        lines = [
            f"# {command} Output",
            "",
            f"**Summary:** {result.summary}",
            "",
        ]

        if result.problems:
            lines.extend(
                [
                    "## Problems",
                    "",
                ]
            )
            for p in result.problems:
                severity = p.get("severity", "info")
                message = p.get("message", "")
                lines.append(f"- [{severity}] {message}")
            lines.append("")

        if result.data:
            lines.extend(
                [
                    "## Data",
                    "",
                    "```json",
                    json.dumps(result.data, indent=2, default=str),
                    "```",
                ]
            )

        return "\n".join(lines)


def get_renderer(json_mode: bool = False, ai_mode: bool = False) -> OutputRenderer:
    """Get the appropriate renderer based on output mode.

    Priority: AI > JSON > Human (most specific mode wins).

    Args:
        json_mode: If True and not ai_mode, return JsonRenderer.
        ai_mode: If True, return AIRenderer (takes precedence over json_mode).

    Returns:
        The appropriate OutputRenderer instance.
    """
    if ai_mode:
        return AIRenderer()
    if json_mode:
        return JsonRenderer()
    return HumanRenderer()
