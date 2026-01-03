"""Core tool result definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolResult:
    tool: str
    ran: bool
    success: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "ran": self.ran,
            "success": self.success,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> ToolResult:
        return cls(
            tool=str(data.get("tool", "")),
            ran=bool(data.get("ran", False)),
            success=bool(data.get("success", False)),
            metrics=dict(data.get("metrics", {}) or {}),
            artifacts=dict(data.get("artifacts", {}) or {}),
        )

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_payload(), indent=2), encoding="utf-8")
