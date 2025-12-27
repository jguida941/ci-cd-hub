"""Tool execution helpers for cihub ci."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET

from cihub.cli import resolve_executable


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


def _run_command(
    cmd: list[str],
    workdir: Path,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    resolved = [resolve_executable(cmd[0]), *cmd[1:]]
    return subprocess.run(  # noqa: S603
        resolved,
        cwd=workdir,
        env=env or os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _parse_junit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "tests_runtime_seconds": 0.0,
        }
    root = ET.parse(path).getroot()
    if root.tag.endswith("testsuites"):
        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
        for suite in root:
            totals["tests"] += int(suite.attrib.get("tests", 0))
            totals["failures"] += int(suite.attrib.get("failures", 0))
            totals["errors"] += int(suite.attrib.get("errors", 0))
            totals["skipped"] += int(suite.attrib.get("skipped", 0))
            totals["time"] += float(suite.attrib.get("time", 0.0))
    else:
        totals = {
            "tests": int(root.attrib.get("tests", 0)),
            "failures": int(root.attrib.get("failures", 0)),
            "errors": int(root.attrib.get("errors", 0)),
            "skipped": int(root.attrib.get("skipped", 0)),
            "time": float(root.attrib.get("time", 0.0)),
        }
    failed = totals["failures"] + totals["errors"]
    passed = max(totals["tests"] - failed - totals["skipped"], 0)
    return {
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_skipped": totals["skipped"],
        "tests_runtime_seconds": totals["time"],
    }


def _parse_coverage(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "coverage": 0,
            "coverage_lines_covered": 0,
            "coverage_lines_total": 0,
        }
    root = ET.parse(path).getroot()
    line_rate = float(root.attrib.get("line-rate", 0))
    lines_covered = int(root.attrib.get("lines-covered", 0))
    lines_total = int(
        root.attrib.get("lines-valid", root.attrib.get("lines-total", 0))
    )
    coverage = int(round(line_rate * 100))
    return {
        "coverage": coverage,
        "coverage_lines_covered": lines_covered,
        "coverage_lines_total": lines_total,
    }


def _parse_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def run_pytest(workdir: Path, output_dir: Path) -> ToolResult:
    junit_path = output_dir / "pytest-junit.xml"
    coverage_path = output_dir / "coverage.xml"
    cmd = [
        "pytest",
        "--cov=.",
        f"--cov-report=xml:{coverage_path}",
        f"--junitxml={junit_path}",
        "-v",
    ]
    proc = _run_command(cmd, workdir)
    metrics = {}
    metrics.update(_parse_junit(junit_path))
    metrics.update(_parse_coverage(coverage_path))
    return ToolResult(
        tool="pytest",
        ran=True,
        success=proc.returncode == 0,
        metrics=metrics,
        artifacts={
            "junit": str(junit_path),
            "coverage": str(coverage_path),
        },
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_ruff(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "ruff-report.json"
    cmd = ["ruff", "check", ".", "--output-format", "json"]
    proc = _run_command(cmd, workdir)
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")
    data = _parse_json(report_path)
    parse_ok = data is not None
    errors = len(data) if isinstance(data, list) else 0
    security = 0
    if isinstance(data, list):
        security = sum(1 for item in data if str(item.get("code", "")).startswith("S"))
    return ToolResult(
        tool="ruff",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "ruff_errors": errors,
            "ruff_security": security,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_black(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "black-output.txt"
    cmd = ["black", "--check", "."]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    issues = len(re.findall(r"would reformat", proc.stdout + proc.stderr))
    return ToolResult(
        tool="black",
        ran=True,
        success=proc.returncode == 0,
        metrics={"black_issues": issues},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_isort(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "isort-output.txt"
    cmd = ["isort", "--check-only", "--diff", "."]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    issues = len(re.findall(r"^ERROR:", proc.stdout, flags=re.MULTILINE))
    return ToolResult(
        tool="isort",
        ran=True,
        success=proc.returncode == 0,
        metrics={"isort_issues": issues},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_mypy(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "mypy-output.txt"
    cmd = ["mypy", ".", "--ignore-missing-imports"]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    errors = len(re.findall(r"\berror:", proc.stdout))
    return ToolResult(
        tool="mypy",
        ran=True,
        success=proc.returncode == 0,
        metrics={"mypy_errors": errors},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_bandit(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "bandit-report.json"
    cmd = ["bandit", "-r", ".", "-f", "json", "-o", str(report_path)]
    proc = _run_command(cmd, workdir)
    data = _parse_json(report_path)
    parse_ok = data is not None
    results = data.get("results", []) if isinstance(data, dict) else []
    high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
    medium = sum(1 for item in results if item.get("issue_severity") == "MEDIUM")
    low = sum(1 for item in results if item.get("issue_severity") == "LOW")
    return ToolResult(
        tool="bandit",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "bandit_high": high,
            "bandit_medium": medium,
            "bandit_low": low,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _count_pip_audit_vulns(data: Any) -> int:
    if isinstance(data, list):
        total = 0
        for item in data:
            vulns = item.get("vulns") or item.get("vulnerabilities") or []
            total += len(vulns)
        return total
    return 0


def run_pip_audit(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "pip-audit-report.json"
    cmd = ["pip-audit", "--format=json", "--output", str(report_path)]
    proc = _run_command(cmd, workdir)
    data = _parse_json(report_path)
    parse_ok = data is not None
    vulns = _count_pip_audit_vulns(data)
    return ToolResult(
        tool="pip_audit",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={"pip_audit_vulns": vulns, "parse_error": not parse_ok},
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _detect_mutmut_paths(workdir: Path) -> str:
    src_dir = workdir / "src"
    if src_dir.exists():
        return "src/"
    for entry in workdir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name in {"tests", "test", "venv", ".venv", "build", "dist"}:
            continue
        if (entry / "__init__.py").exists():
            return f"{entry.name}/"
    return "."


def _ensure_mutmut_config(workdir: Path) -> tuple[Path | None, str | None]:
    pyproject = workdir / "pyproject.toml"
    if pyproject.exists() and "[tool.mutmut]" in pyproject.read_text(encoding="utf-8"):
        return None, None
    setup_cfg = workdir / "setup.cfg"
    if setup_cfg.exists() and "[mutmut]" in setup_cfg.read_text(encoding="utf-8"):
        return None, None

    original_text = (
        setup_cfg.read_text(encoding="utf-8") if setup_cfg.exists() else None
    )
    mutate_path = _detect_mutmut_paths(workdir)
    snippet = f"\n[mutmut]\npaths_to_mutate={mutate_path}\n"
    if setup_cfg.exists():
        setup_cfg.write_text(original_text + snippet, encoding="utf-8")
    else:
        setup_cfg.write_text(snippet.lstrip(), encoding="utf-8")
    return setup_cfg, original_text


def run_mutmut(workdir: Path, output_dir: Path, timeout_seconds: int) -> ToolResult:
    log_path = output_dir / "mutmut-run.log"
    config_path, original = _ensure_mutmut_config(workdir)
    proc = None
    try:
        proc = _run_command(
            ["mutmut", "run"],
            workdir,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(exc.stdout or "", encoding="utf-8")
        return ToolResult(
            tool="mutmut",
            ran=True,
            success=False,
            metrics={"mutation_score": 0, "mutation_killed": 0, "mutation_survived": 0},
            artifacts={"log": str(log_path)},
        )
    finally:
        if config_path:
            if original is None:
                config_path.unlink(missing_ok=True)
            else:
                config_path.write_text(original, encoding="utf-8")

    log_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    results_proc = _run_command(["mutmut", "results"], workdir)
    results_text = (results_proc.stdout or "") + (results_proc.stderr or "")
    killed = len(re.findall(r"\bkilled\b", results_text, flags=re.IGNORECASE))
    survived = len(re.findall(r"\bsurvived\b", results_text, flags=re.IGNORECASE))
    total = killed + survived
    score = int(round((killed / total) * 100)) if total > 0 else 0
    return ToolResult(
        tool="mutmut",
        ran=True,
        success=proc.returncode == 0,
        metrics={
            "mutation_score": score,
            "mutation_killed": killed,
            "mutation_survived": survived,
        },
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_semgrep(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "semgrep-report.json"
    cmd = ["semgrep", "--config=auto", "--json", "--output", str(report_path), "."]
    proc = _run_command(cmd, workdir)
    data = _parse_json(report_path)
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
    proc = _run_command(cmd, workdir)
    data = _parse_json(report_path)
    parse_ok = data is not None
    critical = 0
    high = 0
    medium = 0
    low = 0
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
    return ToolResult(
        tool="trivy",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "trivy_critical": critical,
            "trivy_high": high,
            "trivy_medium": medium,
            "trivy_low": low,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
