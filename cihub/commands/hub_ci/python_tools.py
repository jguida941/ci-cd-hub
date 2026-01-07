"""Python linting and mutation testing commands."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.github_context import OutputContext

from . import (
    _extract_count,
    _run_command,
)

# Maximum characters to include in data fields for logs (prevents huge payloads)
MAX_LOG_PREVIEW_CHARS = 2000


def cmd_ruff(args: argparse.Namespace) -> CommandResult:
    cmd = ["ruff", "check", args.path]
    if args.force_exclude:
        cmd.append("--force-exclude")

    json_proc = _run_command(cmd + ["--output-format=json"], Path("."))
    issues = 0
    try:
        data = json.loads(json_proc.stdout or "[]")
        issues = len(data) if isinstance(data, list) else 0
    except json.JSONDecodeError:
        issues = 0

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"issues": str(issues)})

    try:
        github_proc = safe_run(
            cmd + ["--output-format=github"],
            timeout=TIMEOUT_NETWORK,
            capture_output=False,  # Let github-format output go to terminal
        )
        passed = github_proc.returncode == 0
    except (CommandNotFoundError, CommandTimeoutError):
        passed = False
    return CommandResult(
        exit_code=EXIT_SUCCESS if passed else EXIT_FAILURE,
        summary=f"Ruff: {issues} issues found" if issues else "Ruff: no issues",
        problems=[{"severity": "error", "message": f"Ruff found {issues} issues"}] if not passed else [],
        data={"issues": issues, "passed": passed},
    )


def cmd_black(args: argparse.Namespace) -> CommandResult:
    proc = _run_command(["black", "--check", args.path], Path("."))
    output = (proc.stdout or "") + (proc.stderr or "")
    issues = len(re.findall(r"would reformat", output))
    if proc.returncode != 0 and issues == 0:
        issues = 1
    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"issues": str(issues)})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Black: {issues} files need reformatting" if issues else "Black: all files formatted",
        data={"issues": issues},
    )


def _get_mutation_targets() -> list[str]:
    """Get mutation target paths from pyproject.toml."""
    import tomllib

    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return []

    try:
        config = tomllib.loads(pyproject.read_text())
        paths = config.get("tool", {}).get("mutmut", {}).get("paths_to_mutate", [])
        return list(paths) if isinstance(paths, (list, tuple)) else []
    except Exception:
        return []


def cmd_coverage_verify(args: argparse.Namespace) -> CommandResult:
    """Verify coverage database exists and is readable.

    Used before mutation testing to ensure the .coverage file
    was properly transferred from the unit tests job.
    """
    coverage_path = Path(args.coverage_file)
    ctx = OutputContext.from_args(args)

    if not coverage_path.exists():
        ctx.write_summary("## Coverage Verification\n\n**FAILED**: Coverage file not found\n")
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Coverage file not found: {coverage_path}",
            problems=[{"severity": "error", "message": f"Coverage file not found: {coverage_path}"}],
            data={"exists": False, "path": str(coverage_path)},
        )

    try:
        import coverage

        cov = coverage.Coverage()
        cov.load()
        data = cov.get_data()
        measured_files = list(data.measured_files())
        file_count = len(measured_files)

        # Normalize file paths for comparison
        measured_basenames = {Path(f).name for f in measured_files}

        # Check mutation targets
        mutation_targets = _get_mutation_targets()
        mutation_coverage = []
        for target in mutation_targets:
            target_path = Path(target)
            if target_path.is_dir():
                # Check if any file in the directory is covered
                covered = any(target in f for f in measured_files)
            else:
                covered = target_path.name in measured_basenames or any(target in f for f in measured_files)
            mutation_coverage.append((target, covered))

        # Show first few files for debugging
        sample_files = sorted(measured_files)[:10]

        summary = (
            "## Coverage Verification\n\n"
            f"**PASSED**: Coverage database loaded successfully\n\n"
            f"- **Measured files**: {file_count}\n"
        )

        if mutation_targets:
            summary += "\n### Mutation Target Coverage\n\n"
            for target, covered in mutation_coverage:
                status = "[covered]" if covered else "[NOT covered]"
                summary += f"- {status} `{target}`\n"

        summary += "\n### Sample Files\n"
        for f in sample_files:
            summary += f"- `{f}`\n"
        if file_count > 10:
            summary += f"- ... and {file_count - 10} more\n"

        ctx.write_summary(summary)
        ctx.write_outputs({"measured_files": str(file_count), "valid": "true"})

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Coverage database valid: {file_count} files measured",
            data={
                "exists": True,
                "valid": True,
                "measured_files": file_count,
                "sample_files": sample_files,
                "mutation_coverage": dict(mutation_coverage),
            },
        )
    except Exception as exc:
        ctx.write_summary(f"## Coverage Verification\n\n**FAILED**: {exc}\n")
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Failed to load coverage database: {exc}",
            problems=[{"severity": "error", "message": f"Failed to load coverage: {exc}"}],
            data={"exists": True, "valid": False, "error": str(exc)},
        )


def cmd_mutmut(args: argparse.Namespace) -> CommandResult:
    workdir = Path(args.workdir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "mutmut-run.log"

    proc = _run_command(["mutmut", "run"], workdir)
    log_text = (proc.stdout or "") + (proc.stderr or "")
    log_path.write_text(log_text, encoding="utf-8")
    if proc.returncode != 0:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="mutmut run failed - check for import errors or test failures",
            problems=[{"severity": "error", "message": "mutmut run failed"}],
            data={"log": log_text[:MAX_LOG_PREVIEW_CHARS]},
        )
    if "mutations/second" not in log_text:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="mutmut did not complete successfully",
            problems=[{"severity": "error", "message": "mutmut did not complete"}],
            data={"log": log_text[:MAX_LOG_PREVIEW_CHARS]},
        )

    final_line = ""
    for line in log_text.splitlines():
        if re.search(r"\d+/\d+", line):
            final_line = line
    if not final_line:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="mutmut output missing final counts",
            problems=[{"severity": "error", "message": "mutmut output missing final counts"}],
            data={},
        )

    killed = _extract_count(final_line, "\U0001f389")
    survived = _extract_count(final_line, "\U0001f641")
    timeout = _extract_count(final_line, "\u23f0")
    suspicious = _extract_count(final_line, "\U0001f914")
    skipped = _extract_count(final_line, "\U0001f507")

    tested = killed + survived + timeout + suspicious
    if tested == 0:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="No mutants were tested - check test coverage",
            problems=[{"severity": "error", "message": "No mutants were tested"}],
            data={},
        )

    score = (killed * 100) // tested

    ctx = OutputContext.from_args(args)
    ctx.write_outputs(
        {
            "mutation_score": str(score),
            "killed": str(killed),
            "survived": str(survived),
            "timeout": str(timeout),
            "suspicious": str(suspicious),
        }
    )
    summary = (
        "## Mutation Testing\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| **Score** | **{score}%** |\n"
        f"| Killed | {killed} |\n"
        f"| Survived | {survived} |\n"
        f"| Timeout | {timeout} |\n"
        f"| Suspicious | {suspicious} |\n"
        f"| Skipped | {skipped} |\n"
        f"| Total Tested | {tested} |\n"
    )

    result_data = {
        "mutation_score": score,
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "suspicious": suspicious,
        "skipped": skipped,
        "tested": tested,
        "min_score": args.min_score,
    }

    if score < args.min_score:
        summary += f"\n**FAILED**: Score {score}% below {args.min_score}% threshold\n"
        ctx.write_summary(summary)
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Mutation score {score}% below {args.min_score}% threshold",
            problems=[{"severity": "error", "message": f"Mutation score {score}% below {args.min_score}% threshold"}],
            data=result_data,
        )
    summary += f"\n**PASSED**: Score {score}% meets {args.min_score}% threshold\n"
    ctx.write_summary(summary)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Mutation testing passed: {score}% (threshold: {args.min_score}%)",
        data=result_data,
    )
