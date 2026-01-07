"""Python smoke test commands."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import defusedxml.ElementTree as ET  # Secure XML parsing

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.github_context import OutputContext

from . import _run_command


def _last_regex_int(pattern: str, text: str) -> int:
    matches = re.findall(pattern, text)
    if not matches:
        return 0
    try:
        return int(matches[-1])
    except ValueError:
        return 0


def cmd_smoke_python_install(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    problems: list[dict[str, str]] = []

    commands = [
        ["python", "-m", "pip", "install", "--upgrade", "pip"],
        ["pip", "install", "pytest", "pytest-cov"],
        ["pip", "install", "ruff", "black"],
    ]
    for cmd in commands:
        proc = _run_command(cmd, repo_path)
        if proc.returncode != 0:
            problems.append(
                {
                    "severity": "warning",
                    "message": proc.stdout or proc.stderr or "pip install failed",
                }
            )

    req_files = ["requirements.txt", "requirements-dev.txt"]
    installed_req_files: list[str] = []
    for req in req_files:
        req_path = repo_path / req
        if req_path.exists():
            _run_command(["pip", "install", "-r", str(req_path)], repo_path)
            installed_req_files.append(req)

    pyproject = repo_path / "pyproject.toml"
    pyproject_installed = False
    if pyproject.exists():
        proc = _run_command(["pip", "install", "-e", ".[dev]"], repo_path)
        if proc.returncode != 0:
            _run_command(["pip", "install", "-e", "."], repo_path)
        pyproject_installed = True

    summary = f"Python dependencies installed ({len(installed_req_files)} req files, pyproject: {pyproject_installed})"
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        problems=problems,
        data={
            "requirements_installed": installed_req_files,
            "pyproject_installed": pyproject_installed,
        },
    )


def cmd_smoke_python_tests(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    output_file = repo_path / args.output_file

    proc = _run_command(
        ["pytest", "--cov=.", "--cov-report=xml", "--cov-report=term", "-v"],
        repo_path,
    )
    output_text = (proc.stdout or "") + (proc.stderr or "")
    output_file.write_text(output_text, encoding="utf-8")

    passed = _last_regex_int(r"(\d+)\s+passed", output_text)
    failed = _last_regex_int(r"(\d+)\s+failed", output_text)
    skipped = _last_regex_int(r"(\d+)\s+skipped", output_text)

    coverage = 0
    coverage_file = repo_path / "coverage.xml"
    if coverage_file.exists():
        try:
            tree = ET.parse(coverage_file)  # noqa: S314 - trusted CI tool output
            root = tree.getroot()
            coverage = int(float(root.attrib.get("line-rate", "0")) * 100)
        except (ET.ParseError, ValueError):
            coverage = 0

    total = passed + failed + skipped
    ctx = OutputContext.from_args(args)
    ctx.write_outputs(
        {
            "total": str(total),
            "passed": str(passed),
            "failed": str(failed),
            "skipped": str(skipped),
            "coverage": str(coverage),
        }
    )

    # Return FAILURE if any tests failed, SUCCESS otherwise
    exit_code = EXIT_FAILURE if failed > 0 else EXIT_SUCCESS
    problems = []
    if failed > 0:
        problems.append(
            {
                "severity": "error",
                "message": f"{failed} test(s) failed",
                "code": "CIHUB-SMOKE-TEST-FAILURE",
            }
        )

    return CommandResult(
        exit_code=exit_code,
        summary=f"Tests: {passed} passed, {failed} failed, {skipped} skipped. Coverage: {coverage}%",
        problems=problems,
        data={
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "coverage": coverage,
            "output_file": str(output_file),
        },
    )


def cmd_smoke_python_ruff(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    report_path = repo_path / args.report

    proc = _run_command(["ruff", "check", ".", "--output-format=json"], repo_path)
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")

    errors = 0
    security = 0
    try:
        with report_path.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            errors = len(data)
            security = sum(1 for item in data if str(item.get("code", "")).startswith("S"))
    except json.JSONDecodeError:
        errors = 0
        security = 0

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"errors": str(errors), "security": str(security)})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Ruff: {errors} issues ({security} security-related)",
        data={"errors": errors, "security": security, "report_path": str(report_path)},
    )


def cmd_smoke_python_black(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    output_file = repo_path / args.output_file

    proc = _run_command(["black", "--check", "."], repo_path)
    output_text = (proc.stdout or "") + (proc.stderr or "")
    output_file.write_text(output_text, encoding="utf-8")

    issues = len([line for line in output_text.splitlines() if "would reformat" in line])
    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"issues": str(issues)})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Black: {issues} files need reformatting",
        data={"issues": issues, "output_file": str(output_file)},
    )
