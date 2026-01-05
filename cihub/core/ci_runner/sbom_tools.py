"""SBOM tool runner."""

from __future__ import annotations

import re
from pathlib import Path

from . import shared
from .base import ToolResult


def _normalize_sbom_format(format_value: str | None) -> tuple[str, str]:
    raw = (format_value or "cyclonedx").strip().lower()
    if not raw:
        raw = "cyclonedx"
    mapping = {
        "cyclonedx": "cyclonedx-json",
        "cyclonedx-json": "cyclonedx-json",
        "cyclonedxjson": "cyclonedx-json",
        "spdx": "spdx-json",
        "spdx-json": "spdx-json",
        "spdxjson": "spdx-json",
    }
    syft_format = mapping.get(raw, raw)
    if syft_format.startswith("spdx"):
        suffix = "spdx"
    elif syft_format.startswith("cyclonedx"):
        suffix = "cyclonedx"
    else:
        suffix = re.sub(r"[^a-z0-9]+", "-", raw).strip("-") or "sbom"
    return syft_format, suffix


def run_sbom(workdir: Path, output_dir: Path, format_value: str | None = None) -> ToolResult:
    syft_format, suffix = _normalize_sbom_format(format_value)
    output_path = output_dir / f"sbom.{suffix}.json"
    cmd = ["syft", "dir:.", "-o", syft_format]
    proc = shared._run_tool_command("sbom", cmd, workdir, output_dir)
    if proc.stdout:
        output_path.write_text(proc.stdout, encoding="utf-8")
    parse_ok = shared._parse_json(output_path) is not None
    return ToolResult(
        tool="sbom",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={"parse_error": not parse_ok},
        artifacts={"sbom": str(output_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
