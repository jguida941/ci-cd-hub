"""Security tool runners."""

from __future__ import annotations

from pathlib import Path

from . import shared
from .base import ToolResult


def run_semgrep(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "semgrep-report.json"
    cmd = ["semgrep", "--config=auto", "--json", "--output", str(report_path), "."]
    proc = shared._run_tool_command("semgrep", cmd, workdir, output_dir)
    data = shared._parse_json(report_path)
    parse_ok = data is not None
    findings = 0
    if isinstance(data, dict):
        findings = len(data.get("results", []) or [])
    return ToolResult(
        tool="semgrep",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={"semgrep_findings": findings, "parse_error": not parse_ok},
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_trivy(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "trivy-report.json"
    cmd = ["trivy", "fs", "--format", "json", "--output", str(report_path), "."]
    proc = shared._run_tool_command("trivy", cmd, workdir, output_dir)
    data = shared._parse_json(report_path)
    parse_ok = data is not None
    critical = 0
    high = 0
    medium = 0
    low = 0
    max_cvss: float = 0.0
    if isinstance(data, dict):
        for result in data.get("Results", []) or []:
            for vuln in result.get("Vulnerabilities", []) or []:
                severity = vuln.get("Severity")
                if severity == "CRITICAL":
                    critical += 1
                elif severity == "HIGH":
                    high += 1
                elif severity == "MEDIUM":
                    medium += 1
                elif severity == "LOW":
                    low += 1
                # Extract CVSS score from any provider (nvd, redhat, etc.)
                cvss_data = vuln.get("CVSS", {}) or {}
                for provider_data in cvss_data.values():
                    if isinstance(provider_data, dict):
                        # Try V3Score first, then V2Score
                        for key in ("V3Score", "V2Score"):
                            if key in provider_data:
                                try:
                                    score = float(provider_data[key])
                                    max_cvss = max(max_cvss, score)
                                except (ValueError, TypeError):
                                    pass
    return ToolResult(
        tool="trivy",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "trivy_critical": critical,
            "trivy_high": high,
            "trivy_medium": medium,
            "trivy_low": low,
            "trivy_max_cvss": max_cvss,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
