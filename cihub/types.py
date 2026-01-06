"""Shared type definitions for cihub.

This module contains types that are used across multiple modules.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CommandResult:
    """Structured command result for JSON output."""

    exit_code: int = 0
    summary: str = ""
    problems: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    files_generated: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def to_payload(self, command: str, status: str, duration_ms: int) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "command": command,
            "status": status,
            "exit_code": self.exit_code,
            "duration_ms": duration_ms,
            "summary": self.summary,
            "artifacts": self.artifacts,
            "problems": self.problems,
            "suggestions": self.suggestions,
            "files_generated": self.files_generated,
            "files_modified": self.files_modified,
        }
        if self.data:
            payload["data"] = self.data
        return payload


@dataclass
class ToolResult:
    """Unified tool execution result.

    This canonical definition consolidates:
    - cihub.core.ci_runner.base.ToolResult (metrics-focused)
    - cihub.commands.hub_ci.ToolResult (execution-focused)

    Both original locations re-export this type for backward compatibility.

    Attributes:
        tool: Name of the tool that was run.
        success: Whether the tool ran successfully.
        returncode: Process exit code (0 = success).
        stdout: Captured standard output.
        stderr: Captured standard error.
        ran: Whether the tool actually executed (vs. was skipped).
        metrics: Parsed tool metrics (coverage, errors, etc.).
        artifacts: Output file paths produced by the tool.
        json_data: Parsed JSON output (None if not applicable).
        json_error: Error message if JSON parsing failed.
        report_path: Path where tool report was written.
    """

    # Core execution info
    tool: str
    success: bool
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    # Execution state (from ci_runner/base.py)
    ran: bool = True

    # Metrics and artifacts (from ci_runner/base.py)
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)

    # JSON handling (from hub_ci/__init__.py)
    json_data: Any = None
    json_error: str | None = None
    report_path: Path | None = None

    def to_payload(self) -> dict[str, Any]:
        """Serialize for report output (includes all fields for full fidelity)."""
        payload: dict[str, Any] = {
            "tool": self.tool,
            "ran": self.ran,
            "success": self.success,
            "returncode": self.returncode,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
        }
        # Include optional fields only if set (reduces JSON noise)
        if self.stdout:
            payload["stdout"] = self.stdout
        if self.stderr:
            payload["stderr"] = self.stderr
        if self.json_data is not None:
            payload["json_data"] = self.json_data
        if self.json_error:
            payload["json_error"] = self.json_error
        if self.report_path:
            payload["report_path"] = str(self.report_path)
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "ToolResult":
        """Deserialize from report (restores all fields from payload)."""
        report_path_str = data.get("report_path")
        return cls(
            tool=str(data.get("tool", "")),
            ran=bool(data.get("ran", False)),
            success=bool(data.get("success", False)),
            returncode=int(data.get("returncode", 0)),
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "")),
            metrics=dict(data.get("metrics", {}) or {}),
            artifacts=dict(data.get("artifacts", {}) or {}),
            json_data=data.get("json_data"),
            json_error=data.get("json_error"),
            report_path=Path(report_path_str) if report_path_str else None,
        )

    def write_json(self, path: Path) -> None:
        """Write to JSON file (preserves ci_runner/base.py behavior)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_payload(), indent=2), encoding="utf-8")
