"""Run a local validation suite that mirrors CI gates.

Tiered check modes:
- Default: Fast checks (lint, format, type, test, docs) ~30s
- --audit: + drift detection (links, adr, configs) ~45s
- --security: + security tools (bandit, pip-audit, trivy, gitleaks) ~2min
- --full: + validation (templates, contracts, matrix, license, zizmor, sync-check) ~3min
- --mutation: + mutmut (~15min, opt-in only)
- --all: Everything (unique set, no duplicates)
- --install-missing: Prompt to install missing optional tools
- --require-optional: Fail if optional tools are missing
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cihub.commands.adr import cmd_adr
from cihub.commands.docs import cmd_docs, cmd_docs_links
from cihub.commands.docs_audit import cmd_docs_audit
from cihub.commands.preflight import cmd_preflight
from cihub.commands.schema_sync import check_schema_alignment
from cihub.commands.smoke import cmd_smoke
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.output.events import emit_event, get_event_sink
from cihub.types import CommandResult
from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    TIMEOUT_EXTENDED,
    TIMEOUT_NETWORK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.paths import hub_root, project_root

# Longer timeout for pytest (full suite can exceed 10 minutes locally).
TIMEOUT_TEST = TIMEOUT_EXTENDED * 3

# Optional tools that can be auto-installed when requested.
OPTIONAL_TOOL_HINTS: dict[str, str] = {
    "zizmor": "python -m pip install zizmor",
    "gitleaks": "brew install gitleaks",
    "trivy": "brew install trivy",
    "actionlint": "brew install actionlint",
    "yamllint": "python -m pip install yamllint",
}

PIP_INSTALL_TOOLS: dict[str, str] = {
    "yamllint": "yamllint",
    "zizmor": "zizmor",
}

BREW_INSTALL_TOOLS: dict[str, str] = {
    "actionlint": "actionlint",
    "gitleaks": "gitleaks",
    "trivy": "trivy",
}


@dataclass
class CheckStep:
    name: str
    exit_code: int
    summary: str
    problems: list[dict[str, Any]]


def _as_command_result(result: int | CommandResult) -> CommandResult:
    if isinstance(result, CommandResult):
        return result
    return CommandResult(exit_code=int(result))


def _tail_output(output: str, limit: int = 12) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def _skipped_result(reason: str) -> CommandResult:
    return CommandResult(exit_code=EXIT_SUCCESS, summary=f"skipped ({reason})")


def _run_process(name: str, cmd: list[str], cwd: Path, timeout: int = TIMEOUT_BUILD) -> CommandResult:
    try:
        proc = safe_run(
            cmd,
            cwd=cwd,
            timeout=timeout,
        )
    except CommandNotFoundError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"{cmd[0]} not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"{name} failed (missing {cmd[0]})",
                    "command": " ".join(cmd),
                }
            ],
            suggestions=[
                {
                    "message": f"Install {cmd[0]} and re-run.",
                }
            ],
        )
    except CommandTimeoutError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"{name} timed out",
            problems=[
                {
                    "severity": "error",
                    "message": f"{name} timed out",
                    "command": " ".join(cmd),
                }
            ],
        )

    ok = proc.returncode == 0
    summary = "ok" if ok else f"failed (exit {proc.returncode})"
    problems: list[dict[str, Any]] = []
    if not ok:
        tail = _tail_output((proc.stdout or "") + (proc.stderr or ""))
        problems.append(
            {
                "severity": "error",
                "message": f"{name} failed",
                "detail": tail,
                "command": " ".join(cmd),
            }
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS if ok else EXIT_FAILURE,
        summary=summary,
        problems=problems,
    )


def _run_zizmor(cwd: Path) -> CommandResult:
    """Run zizmor with proper filtering and helpful suggestions."""
    cmd = ["zizmor", ".github/workflows/", "--min-severity", "high"]
    try:
        proc = safe_run(
            cmd,
            cwd=cwd,
            timeout=TIMEOUT_NETWORK,  # 2 min for zizmor
        )
    except CommandNotFoundError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="zizmor not found",
            problems=[{"severity": "error", "message": "zizmor not installed"}],
            suggestions=[{"message": "Install: pip install zizmor"}],
        )
    except CommandTimeoutError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="zizmor timed out",
            problems=[{"severity": "error", "message": "zizmor timed out"}],
        )

    if proc.returncode == 0:
        return CommandResult(exit_code=EXIT_SUCCESS, summary="ok")

    # Parse output to count findings and check for auto-fix availability
    output = (proc.stdout or "") + (proc.stderr or "")
    finding_count = proc.returncode  # zizmor exit code = number of findings
    has_autofix = "this finding has an auto-fix" in output

    problems = [
        {
            "severity": "error",
            "message": f"zizmor found {finding_count} high-severity workflow issues",
            "detail": _tail_output(output),
        }
    ]

    suggestions = []
    if has_autofix:
        suggestions.append({"message": "Auto-fix available: zizmor .github/workflows --fix=safe"})
    suggestions.append({"message": "See https://docs.zizmor.sh/audits/ for remediation guidance"})

    summary = f"found {finding_count} issues"
    if has_autofix:
        summary += " (auto-fix available)"

    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=summary,
        problems=problems,
        suggestions=suggestions,
    )


def _install_tool(tool: str) -> tuple[bool, str]:
    if tool in PIP_INSTALL_TOOLS:
        cmd = [sys.executable, "-m", "pip", "install", PIP_INSTALL_TOOLS[tool]]
    elif tool in BREW_INSTALL_TOOLS:
        if shutil.which("brew") is None:
            return False, "brew not found"
        cmd = ["brew", "install", BREW_INSTALL_TOOLS[tool]]
    else:
        return False, "no installer configured"

    try:
        proc = safe_run(cmd, timeout=TIMEOUT_NETWORK)
    except (CommandNotFoundError, CommandTimeoutError) as exc:
        return False, str(exc)
    ok = proc.returncode == 0
    detail = _tail_output((proc.stdout or "") + (proc.stderr or ""))
    return ok, detail


def _missing_tool_result(
    tool: str,
    *,
    required: bool,
    detail: str | None = None,
) -> CommandResult:
    hint = OPTIONAL_TOOL_HINTS.get(tool, f"install {tool}")
    summary = f"missing {tool}" if required else f"skipped (missing {tool})"
    problems = []
    if required:
        problems.append(
            {
                "severity": "error",
                "message": f"{tool} not installed",
                "detail": detail or "",
                "command": tool,
            }
        )
    return CommandResult(
        exit_code=EXIT_FAILURE if required else EXIT_SUCCESS,
        summary=summary,
        problems=problems,
        suggestions=[{"message": f"Install: {hint}"}],
    )


def _run_optional(
    name: str,
    cmd: list[str],
    cwd: Path,
    *,
    install_missing: bool,
    require_optional: bool,
    interactive: bool,
) -> CommandResult:
    """Run an optional tool, with optional install + required gating."""
    tool = cmd[0]
    if shutil.which(tool) is None:
        if install_missing and interactive:
            response = input(f"{tool} not found. Install now? [y/N] ").strip().lower()
            if response in {"y", "yes"}:
                ok, detail = _install_tool(tool)
                if not ok:
                    return _missing_tool_result(tool, required=require_optional, detail=detail)
            else:
                return _missing_tool_result(tool, required=require_optional)

        if shutil.which(tool) is None:
            return _missing_tool_result(tool, required=require_optional)

    return _run_process(name, cmd, cwd)


def _format_line(step: CheckStep) -> str:
    status = "OK" if step.exit_code == EXIT_SUCCESS else "FAIL"
    summary = f": {step.summary}" if step.summary else ""
    return f"[{status}] {step.name}{summary}"


def cmd_check(args: argparse.Namespace) -> CommandResult:
    """Run tiered local validation suite.

    Flags:
    - (default): Fast checks - lint, format, type, test, docs
    - --audit: + drift detection (links, adr, configs)
    - --security: + security tools (bandit, pip-audit, trivy, gitleaks)
    - --full: + validation (templates, matrix, license, zizmor)
    - --mutation: + mutmut (very slow, opt-in only)
    - --all: Everything (unique set)
    - --install-missing: Prompt to install missing optional tools
    - --require-optional: Fail if optional tools are missing
    """
    json_mode = getattr(args, "json", False)
    cli_test_mode = bool(getattr(args, "_cli_test_mode", False))
    cwd = Path.cwd().resolve()
    hub_root_path = project_root().resolve()
    project_root_path = hub_root_path if cwd.is_relative_to(hub_root_path) else cwd
    data_root = hub_root()
    install_missing = bool(getattr(args, "install_missing", False))
    require_optional = bool(getattr(args, "require_optional", False))
    interactive = bool(install_missing and not json_mode and sys.stdin.isatty())

    def run_optional(name: str, cmd: list[str]) -> CommandResult:
        return _run_optional(
            name,
            cmd,
            project_root_path,
            install_missing=install_missing,
            require_optional=require_optional,
            interactive=interactive,
        )

    # Parse flags - --all enables everything
    run_all = getattr(args, "all", False)
    run_audit = run_all or getattr(args, "audit", False)
    run_security = run_all or getattr(args, "security", False)
    run_full = run_all or getattr(args, "full", False)
    run_mutation = run_all or getattr(args, "mutation", False)

    steps: list[CheckStep] = []
    problems: list[dict[str, Any]] = []
    output_lines: list[str] = []
    completed_checks: set[str] = set()  # Track to avoid duplicates
    streaming = get_event_sink() is not None and not json_mode

    def emit_line(line: str) -> None:
        if streaming:
            emit_event("line", {"text": line})
        else:
            output_lines.append(line)

    def add_step(name: str, result: int | CommandResult) -> None:
        if name in completed_checks:
            return  # Skip duplicates
        completed_checks.add(name)

        outcome = _as_command_result(result)
        step = CheckStep(
            name=name,
            exit_code=outcome.exit_code,
            summary=outcome.summary,
            problems=outcome.problems,
        )
        steps.append(step)
        if outcome.exit_code != 0:
            problems.extend(outcome.problems)
        if not json_mode:
            emit_line(_format_line(step))
            if outcome.exit_code != 0:
                for problem in outcome.problems:
                    detail = problem.get("detail") or problem.get("message")
                    if detail:
                        emit_line(detail)
                # Capture suggestions for failed checks
                for suggestion in getattr(outcome, "suggestions", []) or []:
                    msg = suggestion.get("message", "")
                    if msg:
                        emit_line(f"  * {msg}")

    # ========== FAST MODE (always runs) ==========
    preflight_args = argparse.Namespace(json=True, full=True)
    add_step("preflight", cmd_preflight(preflight_args))

    # Lint
    add_step(
        "ruff-lint",
        _run_process("ruff-lint", ["ruff", "check", "."], project_root_path),
    )
    add_step(
        "ruff-format",
        _run_process("ruff-format", ["ruff", "format", "--check", "."], project_root_path),
    )

    # Black and isort for CI parity (optional but run if available)
    add_step(
        "black",
        _run_process("black", ["black", "--check", "."], project_root_path),
    )
    add_step(
        "isort",
        _run_process("isort", ["isort", "--check-only", "."], project_root_path),
    )

    # Type check
    add_step(
        "typecheck",
        _run_process(
            "typecheck",
            [sys.executable, "-m", "mypy", "cihub/", "scripts/"],
            project_root_path,
        ),
    )

    # YAML lint (optional tool)
    add_step(
        "yamllint",
        run_optional(
            "yamllint",
            [
                "yamllint",
                str(data_root / "config"),
                str(data_root / "templates"),
            ],
        ),
    )

    # Tests (with coverage gate matching CI)
    if cli_test_mode:
        add_step("test", _skipped_result("CLI test mode"))
    else:
        add_step(
            "test",
            _run_process(
                "test",
                [sys.executable, "-m", "pytest", "tests/", "--cov=cihub", "--cov=scripts", "--cov-fail-under=70"],
                project_root_path,
                timeout=TIMEOUT_TEST,
            ),
        )

    # Workflow lint (actionlint auto-discovers .github/workflows when run from repo root)
    add_step(
        "actionlint",
        run_optional("actionlint", ["actionlint"]),
    )

    # Docs check
    docs_args = argparse.Namespace(
        subcommand="check",
        output="docs/reference",
        json=True,
    )
    add_step("docs-check", cmd_docs(docs_args))

    # Smoke test
    smoke_args = argparse.Namespace(
        repo=getattr(args, "smoke_repo", None),
        subdir=getattr(args, "smoke_subdir", None),
        type=None,
        all=False,
        full=bool(run_full),
        install_deps=bool(getattr(args, "install_deps", False)),
        force=False,
        relax=bool(getattr(args, "relax", False)),
        keep=bool(getattr(args, "keep", False)),
        json=True,
    )
    if cli_test_mode:
        add_step("smoke", _skipped_result("CLI test mode"))
    else:
        add_step("smoke", cmd_smoke(smoke_args))

    # ========== AUDIT MODE (--audit or --all) ==========
    if run_audit:
        # Docs links check
        links_args = argparse.Namespace(json=True, external=False)
        add_step("docs-links", cmd_docs_links(links_args))

        # Docs audit (lifecycle + ADR metadata)
        # NOTE: --skip-references and --skip-consistency are intentional for fast CI.
        # The reference scan adds ~10s and consistency checks add ~5s with noise.
        # For full audit:
        #   cihub docs audit                  # Full scan (slower, all checks)
        #   cihub docs audit --skip-references --skip-consistency  # Fast mode
        # Write to .cihub/tool-outputs/ for triage integration
        tool_outputs_dir = project_root_path / ".cihub" / "tool-outputs"
        audit_args = argparse.Namespace(
            json=True,
            output_dir=str(tool_outputs_dir),
            skip_references=True,  # Fast mode; run full audit separately if needed
            skip_consistency=True,  # Part 13 checks can be noisy; run explicitly if needed
            github_summary=False,
        )
        add_step("docs-audit", cmd_docs_audit(audit_args))

        # ADR check
        adr_args = argparse.Namespace(subcommand="check", json=True)
        add_step("adr-check", cmd_adr(adr_args))

        # Config validation
        add_step(
            "validate-configs",
            _run_process(
                "validate-configs",
                [sys.executable, "-m", "cihub", "hub-ci", "validate-configs"],
                project_root_path,
            ),
        )
        add_step(
            "validate-profiles",
            _run_process(
                "validate-profiles",
                [sys.executable, "-m", "cihub", "hub-ci", "validate-profiles"],
                project_root_path,
            ),
        )

        # Report validation (Issue 10: enforce report consistency)
        report_path = project_root_path / ".cihub" / "report.json"
        if report_path.exists():
            add_step(
                "report-validate",
                _run_process(
                    "report-validate",
                    [sys.executable, "-m", "cihub", "report", "validate", "--report", str(report_path), "--strict"],
                    project_root_path,
                ),
            )

        # Schema-defaults alignment check (defaults.yaml + fallbacks.py)
        add_step("schema-alignment", check_schema_alignment())

    # ========== SECURITY MODE (--security or --all) ==========
    if run_security:
        add_step(
            "bandit",
            _run_process(
                "bandit",
                [
                    "bandit",
                    "-r",
                    "cihub",
                    "scripts",
                    "-f",
                    "json",
                    "-q",
                    "--severity-level",
                    "high",
                    "--confidence-level",
                    "high",
                ],
                project_root_path,
            ),
        )
        add_step(
            "pip-audit",
            _run_process(
                "pip-audit",
                [
                    "pip-audit",
                    "-r",
                    "requirements/requirements.txt",
                    "-r",
                    "requirements/requirements-dev.txt",
                ],
                project_root_path,
            ),
        )
        add_step(
            "gitleaks",
            run_optional(
                "gitleaks",
                ["gitleaks", "detect", "--source", ".", "--no-git"],
            ),
        )
        add_step(
            "trivy",
            run_optional(
                "trivy",
                ["trivy", "fs", ".", "--severity", "CRITICAL,HIGH", "--exit-code", "1"],
            ),
        )

    # ========== FULL MODE (--full or --all) ==========
    if run_full:
        # Zizmor workflow security (with severity filtering + auto-fix hints)
        add_step(
            "zizmor",
            (
                _run_zizmor(project_root_path)
                if shutil.which("zizmor")
                else _missing_tool_result("zizmor", required=require_optional)
            ),
        )

        # Template validation
        if cli_test_mode:
            add_step("validate-templates", _skipped_result("CLI test mode"))
        else:
            add_step(
                "validate-templates",
                _run_process(
                    "validate-templates",
                    [sys.executable, "-m", "pytest", "tests/integration/test_templates.py", "-v", "--tb=short"],
                    project_root_path,
                ),
            )

        # Template/workflow contract verification
        add_step(
            "verify-contracts",
            _run_process(
                "verify-contracts",
                [sys.executable, "-m", "cihub", "verify"],
                project_root_path,
            ),
        )

        # Matrix key verification
        add_step(
            "verify-matrix-keys",
            _run_process(
                "verify-matrix-keys",
                [sys.executable, "-m", "cihub", "hub-ci", "verify-matrix-keys"],
                project_root_path,
            ),
        )

        # License check
        add_step(
            "license-check",
            _run_process(
                "license-check",
                [sys.executable, "-m", "cihub", "hub-ci", "license-check"],
                project_root_path,
            ),
        )

        # Remote template sync check (requires GH_TOKEN)
        if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("HUB_DISPATCH_TOKEN"):
            add_step(
                "sync-templates-check",
                _run_process(
                    "sync-templates-check",
                    [sys.executable, "-m", "cihub", "sync-templates", "--check"],
                    project_root_path,
                ),
            )
        else:
            add_step(
                "sync-templates-check",
                _missing_tool_result(
                    "sync-templates-check",
                    required=require_optional,
                    detail=(
                        "GH_TOKEN, GITHUB_TOKEN, or HUB_DISPATCH_TOKEN not set; skipping remote template drift check"
                    ),
                ),
            )

    # ========== MUTATION MODE (--mutation or --all) ==========
    if run_mutation:
        add_step(
            "mutmut",
            _run_process(
                "mutmut",
                [sys.executable, "-m", "cihub", "hub-ci", "mutmut", "--min-score", "70"],
                project_root_path,
            ),
        )

    # ========== SUMMARY ==========
    failed = [step for step in steps if step.exit_code != 0]
    exit_code = EXIT_FAILURE if failed else EXIT_SUCCESS

    # Build mode description
    modes = []
    if run_audit:
        modes.append("audit")
    if run_security:
        modes.append("security")
    if run_full:
        modes.append("full")
    if run_mutation:
        modes.append("mutation")
    mode_str = f" ({'+'.join(modes)})" if modes else ""

    summary = f"{len(failed)} checks failed{mode_str}" if failed else f"All {len(steps)} checks passed{mode_str}"

    # Always return CommandResult (progress prints above are for real-time UX)
    data = {
        "steps": [
            {
                "name": step.name,
                "exit_code": step.exit_code,
                "summary": step.summary,
                "problems": step.problems,
            }
            for step in steps
        ],
        "modes": {
            "audit": run_audit,
            "security": run_security,
            "full": run_full,
            "mutation": run_mutation,
        },
    }
    if output_lines and not json_mode and not streaming:
        data["raw_output"] = "\n".join(output_lines)

    result = CommandResult(
        exit_code=exit_code,
        summary=summary,
        problems=problems,
        data=data,
    )
    if getattr(args, "ai", False):
        from cihub.ai import enhance_result

        result = enhance_result(result, mode="analyze")

    return result
