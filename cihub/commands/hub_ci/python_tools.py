"""Python linting and mutation testing commands."""

from __future__ import annotations

import argparse
import json
import os
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

    json_mode = getattr(args, "json", False)
    if json_mode:
        # In JSON mode, stdout must remain JSON-only. Don't stream github-format output.
        passed = json_proc.returncode == 0
    else:
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


def cmd_ruff_format(args: argparse.Namespace) -> CommandResult:
    """Run ruff formatter in check mode.

    Note: In JSON mode, stdout must remain JSON-only. This command captures all tool output.
    """
    cmd = ["ruff", "format", "--check", args.path]
    if getattr(args, "force_exclude", False):
        cmd.append("--force-exclude")

    proc = _run_command(cmd, Path("."))
    output = (proc.stdout or "") + (proc.stderr or "")
    preview = output[:MAX_LOG_PREVIEW_CHARS]
    needs_format = proc.returncode != 0

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"needs_format": "true" if needs_format else "false"})

    problems = []
    if needs_format and preview.strip():
        problems = [{"severity": "error", "message": preview.strip()}]
    elif needs_format:
        problems = [{"severity": "error", "message": "Ruff format check failed"}]

    return CommandResult(
        exit_code=EXIT_FAILURE if needs_format else EXIT_SUCCESS,
        summary="Ruff format: needs reformatting" if needs_format else "Ruff format: clean",
        problems=problems,
        data={"needs_format": needs_format, "output_preview": preview},
    )


def cmd_mypy(args: argparse.Namespace) -> CommandResult:
    """Run mypy type checking."""
    cmd = ["mypy", args.path]
    if getattr(args, "ignore_missing_imports", False):
        cmd.append("--ignore-missing-imports")
    if getattr(args, "show_error_codes", False):
        cmd.append("--show-error-codes")

    proc = _run_command(cmd, Path("."))
    output = (proc.stdout or "") + (proc.stderr or "")
    preview = output[:MAX_LOG_PREVIEW_CHARS]
    errors = len(re.findall(r":\s*error:", output))
    if proc.returncode != 0 and errors == 0:
        errors = 1

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"errors": str(errors)})

    return CommandResult(
        exit_code=EXIT_SUCCESS if proc.returncode == 0 else EXIT_FAILURE,
        summary=f"Mypy: {errors} error(s)" if errors else "Mypy: no errors",
        problems=[{"severity": "error", "message": preview.strip() or "mypy failed"}] if proc.returncode != 0 else [],
        data={"errors": errors, "output_preview": preview},
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


def _clean_mutmut_log(log_text: str) -> str:
    """Clean mutmut log output by removing spinner characters and finding actual errors.

    mutmut uses rich/spinner output that pollutes logs with unicode spinner chars.
    This function extracts actual error messages from the noise.
    """
    normalized = log_text.replace("\r", "\n")
    # Spinner characters used by mutmut
    spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    lines = []
    seen_lines: set[str] = set()

    for line in normalized.split("\n"):
        # Skip lines that are just spinner + "Generating mutants"
        stripped = line.strip()
        if stripped.startswith(tuple(spinner_chars)) and "Generating mutants" in stripped:
            continue
        # Skip lines that are just spinner + "Testing mutants"
        if stripped.startswith(tuple(spinner_chars)) and "Testing mutants" in stripped:
            continue
        # Skip duplicate lines (spinners create many identical lines)
        if stripped in seen_lines:
            continue
        seen_lines.add(stripped)
        # Keep non-empty, non-spinner lines
        if stripped and not all(c in spinner_chars for c in stripped):
            lines.append(stripped)

    return "\n".join(lines)


def _extract_mutmut_error(log_text: str) -> str:
    """Extract the actual error message from mutmut output."""
    # First, clean the log to remove spinner noise
    cleaned = _clean_mutmut_log(log_text)

    # Look for Python traceback - capture the full traceback block
    traceback_match = re.search(
        r"(Traceback \(most recent call last\):.*?(?:\w+Error|\w+Exception):.*?)(?:\n\n|\Z)",
        cleaned,
        re.DOTALL,
    )
    if traceback_match:
        return traceback_match.group(1).strip()

    # Look for common error patterns with context
    error_patterns = [
        (r"((?:Import|Syntax|Module|File|Type|Value|Key|Attribute)Error:.+)", re.IGNORECASE),
        (r"((?:Error|Exception):.+)", re.IGNORECASE),
        (r"(Coverage.*error.+)", re.IGNORECASE),
        (r"(No (?:lines|module|file|coverage) found.+)", re.IGNORECASE),
        (r"(Failed to.+)", re.IGNORECASE),
        (r"(FAILED.+)", 0),  # pytest failure lines
    ]

    for pattern, flags in error_patterns:
        match = re.search(pattern, cleaned, flags | re.MULTILINE)
        if match:
            return match.group(1).strip()

    # If no specific error found, return cleaned log preview
    if cleaned:
        # Return last few non-empty lines which often contain the error
        last_lines = [ln for ln in cleaned.split("\n") if ln.strip()][-5:]
        return "\n".join(last_lines) if last_lines else "No error details available"

    return "No error details available"


def _mutmut_fallback_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("TERM", "dumb")
    env.setdefault("CI", "1")
    env.setdefault("RICH_DISABLE", "1")
    env.setdefault("PYTHONFAULTHANDLER", "1")
    return env


def _run_mutmut(
    workdir: Path,
    *,
    max_children: int | None = None,
    env: dict[str, str] | None = None,
):
    cmd = ["mutmut", "run"]
    if max_children is not None:
        cmd += ["--max-children", str(max_children)]
    return _run_command(cmd, workdir, env=env)


def cmd_mutmut(args: argparse.Namespace) -> CommandResult:
    workdir = Path(args.workdir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "mutmut-run.log"
    fallback_log_path = output_dir / "mutmut-run-fallback.log"

    ctx = OutputContext.from_args(args)

    proc = _run_mutmut(workdir)
    log_text = (proc.stdout or "") + (proc.stderr or "")
    log_path.write_text(log_text, encoding="utf-8")
    if proc.returncode != 0:
        # Extract actual error from the log
        error_detail = _extract_mutmut_error(log_text)
        cleaned_log = _clean_mutmut_log(log_text)
        fallback_used = False
        fallback_log = ""
        fallback_exit_code: int | None = None
        fallback_cleaned = ""
        fallback_error = ""

        if not cleaned_log or error_detail == "No error details available":
            fallback_used = True
            fallback_proc = _run_mutmut(workdir, max_children=1, env=_mutmut_fallback_env())
            fallback_exit_code = fallback_proc.returncode
            fallback_log = (fallback_proc.stdout or "") + (fallback_proc.stderr or "")
            fallback_log_path.write_text(fallback_log, encoding="utf-8")
            fallback_cleaned = _clean_mutmut_log(fallback_log)
            fallback_error = _extract_mutmut_error(fallback_log)
            if fallback_cleaned:
                cleaned_log = fallback_cleaned
            if fallback_error != "No error details available":
                error_detail = fallback_error
            elif fallback_exit_code == 139:
                error_detail = "mutmut crashed (signal 11) during mutant generation"

        # Write error summary to GitHub
        error_summary = (
            "## Mutation Testing\n\n"
            "**FAILED**: mutmut run failed\n\n"
            "### Error Details\n\n"
            f"```\n{error_detail[:1000]}\n```\n\n"
        )
        if cleaned_log:
            error_summary += f"### Cleaned Log\n\n```\n{cleaned_log[:1000]}\n```\n"
        if fallback_used:
            error_summary += (
                f"\n### Fallback Run\n\n- exit_code: {fallback_exit_code}\n- log_path: {fallback_log_path}\n"
            )

        ctx.write_summary(error_summary)

        log_preview = cleaned_log[:MAX_LOG_PREVIEW_CHARS] if cleaned_log else log_text[:MAX_LOG_PREVIEW_CHARS]
        data = {
            "log": log_preview,
            "error": error_detail,
            "log_path": str(log_path),
        }
        if fallback_used:
            fallback_preview = fallback_cleaned or fallback_log
            data.update(
                {
                    "fallback_used": True,
                    "fallback_exit_code": fallback_exit_code,
                    "fallback_log": fallback_preview[:MAX_LOG_PREVIEW_CHARS] if fallback_preview else "",
                    "fallback_log_path": str(fallback_log_path),
                }
            )

        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="mutmut run failed - check for import errors or test failures",
            problems=[{"severity": "error", "message": f"mutmut run failed: {error_detail[:200]}"}],
            data=data,
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

    min_mutation_score = getattr(args, "min_mutation_score", getattr(args, "min_score", 70))

    result_data = {
        "mutation_score": score,
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "suspicious": suspicious,
        "skipped": skipped,
        "tested": tested,
        # Canonical key (schema/inputs use min_mutation_score). Keep min_score as alias for compatibility.
        "min_mutation_score": min_mutation_score,
        "min_score": min_mutation_score,
    }

    if score < min_mutation_score:
        summary += f"\n**FAILED**: Score {score}% below {min_mutation_score}% threshold\n"
        ctx.write_summary(summary)
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Mutation score {score}% below {min_mutation_score}% threshold",
            problems=[
                {"severity": "error", "message": f"Mutation score {score}% below {min_mutation_score}% threshold"}
            ],
            data=result_data,
        )
    summary += f"\n**PASSED**: Score {score}% meets {min_mutation_score}% threshold\n"
    ctx.write_summary(summary)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Mutation testing passed: {score}% (threshold: {min_mutation_score}%)",
        data=result_data,
    )
