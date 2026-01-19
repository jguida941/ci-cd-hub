"""Hub production CI helpers package.

This package splits the hub_ci module into logical submodules while
maintaining backward compatibility by re-exporting all public symbols.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import threading
import urllib.request
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET  # noqa: F401 - re-export for submodules

from cihub import badges as badge_tools  # noqa: F401 - re-export
from cihub.config.io import load_yaml_file
from cihub.config.normalize import normalize_config
from cihub.config.paths import PathConfig
from cihub.config.schema import validate_config
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE  # noqa: F401 - re-export
from cihub.services.discovery import _THRESHOLD_KEYS, _TOOL_KEYS  # noqa: F401 - re-export
from cihub.services.types import RepoEntry  # noqa: F401 - re-export
from cihub.types import CommandResult, ToolResult
from cihub.utils.env import _parse_env_bool, env_bool
from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.github_context import OutputContext  # noqa: F401 - re-export
from cihub.utils.paths import hub_root  # noqa: F401 - re-export
from cihub.utils.progress import _bar  # noqa: F401 - re-export

# ============================================================================
# Shared Helpers (lines 33-151 from original hub_ci.py)
# ============================================================================


def _write_outputs(values: dict[str, str], output_path: Path | None) -> str | None:
    if output_path is None:
        return "\n".join(f"{key}={value}" for key, value in values.items())
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")
    return None


def _append_summary(text: str, summary_path: Path | None) -> str | None:
    if summary_path is None:
        return text
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")
    return None


def _resolve_output_path(path_value: str | None, github_output: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if github_output:
        env_path = os.environ.get("GITHUB_OUTPUT")
        return Path(env_path) if env_path else None
    return None


def _resolve_summary_path(path_value: str | None, github_summary: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if github_summary:
        env_path = os.environ.get("GITHUB_STEP_SUMMARY")
        return Path(env_path) if env_path else None
    return None


def _append_github_path(path_value: Path) -> None:
    env_path = os.environ.get("GITHUB_PATH")
    if not env_path:
        return
    with open(env_path, "a", encoding="utf-8") as handle:
        handle.write(f"{path_value}\n")


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


# ============================================================================
# Public GitHub Output/Summary Helpers (Phase 2 Consolidation)
# ============================================================================


def write_github_outputs(
    values: dict[str, str],
    output_path: str | None = None,
    github_output: bool = False,
) -> str | None:
    """Write key=value pairs to GitHub Actions output.

    Combines _resolve_output_path + _write_outputs into a single call.
    Eliminates the common 2-step pattern throughout hub-ci commands.

    Args:
        values: Dictionary of key=value pairs to write.
        output_path: Explicit path to write outputs (takes precedence).
        github_output: If True, write to GITHUB_OUTPUT env var path.

    Example:
        # Before (2 steps):
        output_path = _resolve_output_path(args.output, args.github_output)
        _write_outputs({"key": "value"}, output_path)

        # After (1 step):
        write_github_outputs({"key": "value"}, args.output, args.github_output)
    """
    resolved_path = _resolve_output_path(output_path, github_output)
    return _write_outputs(values, resolved_path)


def write_github_summary(
    text: str,
    summary_path: str | None = None,
    github_summary: bool = False,
) -> str | None:
    """Append text to GitHub Actions step summary.

    Combines _resolve_summary_path + _append_summary into a single call.

    Args:
        text: Markdown text to append to summary.
        summary_path: Explicit path to write summary (takes precedence).
        github_summary: If True, write to GITHUB_STEP_SUMMARY env var path.

    Example:
        # Before (2 steps):
        summary_path = _resolve_summary_path(args.summary, args.github_summary)
        _append_summary(md_text, summary_path)

        # After (1 step):
        write_github_summary(md_text, args.summary, args.github_summary)
    """
    resolved_path = _resolve_summary_path(summary_path, github_summary)
    return _append_summary(text, resolved_path)


# ============================================================================
# Tool Execution Helpers (Phase 2 Consolidation)
# ============================================================================


# ToolResult is now imported from cihub.types (canonical location)
# Re-exported via __all__ for backward compatibility


def ensure_executable(path: Path) -> bool:
    """Make a file executable if it exists.

    This consolidates the common pattern:
        if wrapper.exists():
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

    Args:
        path: Path to the file to make executable.

    Returns:
        True if file exists and was made executable, False otherwise.

    Example:
        # Before (verbose):
        mvnw = repo_path / "mvnw"
        if mvnw.exists():
            mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
            _run_command(["./mvnw", ...], repo_path)

        # After (clean):
        mvnw = repo_path / "mvnw"
        if ensure_executable(mvnw):
            _run_command(["./mvnw", ...], repo_path)

    Note:
        Uses try/except to handle race condition where file is deleted
        between exists() check and chmod() call.
    """
    try:
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return True
    except (FileNotFoundError, OSError):
        return False


def load_json_report(
    path: Path,
    default: Any = None,
) -> tuple[Any, str | None]:
    """Safely load a JSON report file with error handling.

    This consolidates the common pattern:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = default

    Args:
        path: Path to the JSON file.
        default: Value to return if file doesn't exist or JSON is invalid.

    Returns:
        Tuple of (parsed_data, error_message).
        - If successful: (data, None)
        - If file missing: (default, "File not found: {path}")
        - If invalid JSON: (default, "Invalid JSON: {error}")

    Example:
        # Before (verbose):
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            vulns = count_vulns(data)
        except json.JSONDecodeError:
            data = []
            vulns = 0

        # After (clean):
        data, error = load_json_report(report_path, default=[])
        if error:
            problems.append({"severity": "warning", "message": error})
        vulns = count_vulns(data)
    """
    if not path.exists():
        return default, f"File not found: {path}"
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as exc:
        return default, f"Invalid JSON in {path}: {exc}"


def run_tool_with_json_report(
    cmd: list[str],
    cwd: Path,
    report_path: Path,
    default_on_missing: str | None = None,
    env: dict[str, str] | None = None,
    *,
    tool_name: str = "",
) -> ToolResult:
    """Run a tool that produces JSON output and parse the result.

    This consolidates the common pattern found in security commands:
    1. Run tool with JSON output flag
    2. Check if report file was created
    3. Create fallback content if missing
    4. Parse JSON with error handling
    5. Return structured result

    Args:
        cmd: Command to run.
        cwd: Working directory.
        report_path: Path where the tool writes its JSON report.
        default_on_missing: JSON string to write if report not created.
            If None, no fallback is created.
        env: Optional environment variables.

    Returns:
        ToolResult with success status, parsed JSON data, and any errors.

    Example:
        # Before (verbose):
        proc = _run_command(["bandit", "-f", "json", "-o", str(report)], cwd)
        tool_status = "success"
        if not report.exists():
            report.write_text('{"results":[]}', encoding="utf-8")
            if proc.returncode != 0:
                tool_status = "failed"
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"results": []}
            tool_status = "failed"

        # After (clean):
        result = run_tool_with_json_report(
            cmd=["bandit", "-f", "json", "-o", str(report)],
            cwd=cwd,
            report_path=report,
            default_on_missing='{"results":[]}',
        )
        data = result.json_data or {"results": []}
        tool_status = "success" if result.success else "failed"
    """
    proc = _run_command(cmd, cwd, env=env)

    # Derive tool name from command if not provided
    resolved_tool = tool_name or (cmd[0] if cmd else "unknown")

    # Handle missing report file
    if not report_path.exists():
        if default_on_missing is not None:
            report_path.write_text(default_on_missing, encoding="utf-8")
        else:
            return ToolResult(
                tool=resolved_tool,
                success=False,
                returncode=proc.returncode,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                json_data=None,
                json_error=f"Tool did not create report: {report_path}",
                report_path=report_path,
            )

    # Parse JSON
    json_data, json_error = load_json_report(report_path)

    return ToolResult(
        tool=resolved_tool,
        success=proc.returncode == 0 and json_error is None,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        json_data=json_data,
        json_error=json_error,
        report_path=report_path,
    )


def _load_config(path: Path | None) -> tuple[dict[str, Any], list[str]]:
    if path is None:
        return {}, []
    try:
        raw = load_yaml_file(path)
        config = normalize_config(raw)
        warnings: list[str] = []

        # Validate config against schema (fixes Part 7.5.1 schema validation bypass)
        paths = PathConfig(str(hub_root()))
        errors = validate_config(config, paths)
        if errors:
            warnings.extend(errors)

        return config, warnings
    except Exception as exc:  # noqa: BLE001
        return {}, [f"Failed to load config: {exc}"]


def _run_command(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    verbose = env_bool("CIHUB_VERBOSE", default=False)
    if not verbose:
        # Use safe_run for non-streaming mode
        try:
            return safe_run(
                cmd,
                cwd=cwd,
                env=env,
                timeout=TIMEOUT_BUILD,  # 10 min default
            )
        except CommandNotFoundError as exc:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=127,
                stdout="",
                stderr=str(exc),
            )
        except CommandTimeoutError as exc:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=124,  # Standard timeout exit code
                stdout="",
                stderr=str(exc),
            )

    proc = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",  # Consistent with safe_run() per ADR-0045
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        bufsize=1,
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _reader(pipe, chunks: list[str]) -> None:
        if pipe is None:
            return
        for line in iter(pipe.readline, ""):
            chunks.append(line)
            sys.stderr.write(line)
            sys.stderr.flush()
        pipe.close()

    stdout_thread = threading.Thread(target=_reader, args=(proc.stdout, stdout_chunks))
    stderr_thread = threading.Thread(target=_reader, args=(proc.stderr, stderr_chunks))
    stdout_thread.start()
    stderr_thread.start()
    try:
        proc.wait(timeout=TIMEOUT_BUILD)  # Use constant instead of hardcoded 300
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise
    stdout_thread.join()
    stderr_thread.join()
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
    )


# ============================================================================
# CommandResult Helpers - reduce boilerplate for cmd_* functions
# ============================================================================


def result_ok(
    summary: str,
    *,
    data: dict[str, Any] | None = None,
    problems: list[dict[str, Any]] | None = None,
    files_generated: list[str] | None = None,
    files_modified: list[str] | None = None,
) -> CommandResult:
    """Create a successful CommandResult.

    Use this helper to reduce boilerplate when returning success from commands.

    Args:
        summary: Human-readable success message
        data: Optional structured data for --json output
        problems: Optional warnings (non-fatal issues)
        files_generated: Optional list of generated file paths
        files_modified: Optional list of modified file paths

    Returns:
        CommandResult with exit_code=EXIT_SUCCESS
    """
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data=data or {},
        problems=problems or [],
        files_generated=files_generated or [],
        files_modified=files_modified or [],
    )


def result_fail(
    summary: str,
    *,
    problems: list[dict[str, Any]] | None = None,
    data: dict[str, Any] | None = None,
) -> CommandResult:
    """Create a failed CommandResult.

    Use this helper to reduce boilerplate when returning errors from commands.

    Args:
        summary: Human-readable error message
        problems: List of problem dicts (severity, message, optionally code)
        data: Optional structured data for debugging

    Returns:
        CommandResult with exit_code=EXIT_FAILURE
    """
    # If no problems provided, create one from the summary
    if problems is None:
        problems = [{"severity": "error", "message": summary}]
    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=summary,
        problems=problems,
        data=data or {},
    )


def run_and_capture(
    cmd: list[str],
    cwd: Path,
    *,
    tool_name: str = "",
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a command and capture its output for structured results.

    Use this helper when you need to run a tool and capture its output
    for inclusion in a CommandResult.

    Args:
        cmd: Command and arguments to execute
        cwd: Working directory for the command
        tool_name: Name of the tool (for error messages)
        env: Optional environment variables

    Returns:
        Dict with keys: stdout, stderr, returncode, success, tool
    """
    proc = _run_command(cmd, cwd, env=env)
    return {
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "returncode": proc.returncode,
        "success": proc.returncode == 0,
        "tool": tool_name or cmd[0] if cmd else "",
    }


# ============================================================================
# Additional Shared Helpers
# ============================================================================


def _download_file(url: str, dest: Path, *, timeout: int = 60) -> None:
    """Download a file from URL with security validations.

    Args:
        url: URL to download from (must be https://)
        dest: Destination path for the downloaded file
        timeout: Request timeout in seconds (default: 60)

    Raises:
        ValueError: If URL scheme is not https
        urllib.error.URLError: If download fails
    """
    # Validate URL scheme (prevent file:// and other unsafe schemes)
    if not url.startswith("https://"):
        raise ValueError(f"Only https:// URLs allowed, got: {url}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "cihub"})  # noqa: S310

    # Stream to file to avoid OOM on large files
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        with dest.open("wb") as f:
            while chunk := response.read(8192):
                f.write(chunk)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_tarball_member(tar_path: Path, member_name: str, dest_dir: Path) -> Path:
    """Extract a single member from a tarball with path traversal protection.

    Validates that the extracted file stays within dest_dir to prevent
    CVE-2007-4559 path traversal attacks.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Validate extracted path is within dest_dir (CVE-2007-4559 protection)
    # Use is_relative_to() which is immune to the str().startswith() bypass
    # where "/tmp/safe" matches "/tmp/safevil/malicious"
    resolved_dest = dest_dir.resolve()
    extracted = (dest_dir / member_name).resolve()
    try:
        extracted.relative_to(resolved_dest)
    except ValueError:
        raise ValueError(f"Path traversal detected in tarball: {member_name}") from None

    with tarfile.open(tar_path, "r:gz") as tar:
        member = tar.getmember(member_name)
        # Reject symlinks and hardlinks (CVE-2007-4559 symlink variant)
        if member.issym() or member.islnk():
            raise ValueError(f"Symlinks/hardlinks not allowed in tarball: {member_name}")
        tar.extract(member, path=dest_dir)

    extracted.chmod(extracted.stat().st_mode | stat.S_IEXEC)
    return extracted


def _parse_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def _parse_float(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


# ============================================================================
# Helper functions exported for backward compatibility
# ============================================================================


def _extract_count(line: str, emoji: str) -> int:
    match = re.search(rf"{re.escape(emoji)}\s*(\d+)", line)
    if match:
        return int(match.group(1))
    return 0


def _compare_badges(expected_dir: Path, actual_dir: Path) -> list[str]:
    issues: list[str] = []
    if not expected_dir.exists():
        return [f"missing badges directory: {expected_dir}"]

    expected = {p.name: p for p in expected_dir.glob("*.json")}
    actual = {p.name: p for p in actual_dir.glob("*.json")}

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    for name in missing:
        issues.append(f"missing: {name}")
    for name in extra:
        issues.append(f"extra: {name}")

    for name in sorted(set(expected) & set(actual)):
        try:
            with expected[name].open(encoding="utf-8") as f:
                expected_data = json.load(f)
            with actual[name].open(encoding="utf-8") as f:
                actual_data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"invalid json: {name} ({exc})")
            continue
        if expected_data != actual_data:
            issues.append(f"diff: {name}")

    return issues


def _count_pip_audit_vulns(data: Any) -> int:
    if not isinstance(data, list):
        return 0
    total = 0
    for item in data:
        vulns = item.get("vulns") or item.get("vulnerabilities") or []
        total += len(vulns)
    return total


# Empty SARIF for fallback when zizmor fails
EMPTY_SARIF = (
    '{"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json",'
    '"runs":[{"tool":{"driver":{"name":"zizmor","version":"0.8.0"}},"results":[]}]}'
)


# ============================================================================
# Import and re-export all cmd_* functions from submodules
# These imports are intentionally at the bottom to avoid circular imports
# ============================================================================

from cihub.commands.hub_ci.badges import (  # noqa: E402
    cmd_badges,
    cmd_badges_commit,
    cmd_outputs,
)
from cihub.commands.hub_ci.java_tools import (  # noqa: E402
    cmd_codeql_build,
    cmd_smoke_java_build,
    cmd_smoke_java_checkstyle,
    cmd_smoke_java_coverage,
    cmd_smoke_java_spotbugs,
    cmd_smoke_java_tests,
)
from cihub.commands.hub_ci.python_tools import (  # noqa: E402
    cmd_black,
    cmd_coverage_verify,
    cmd_mutmut,
    cmd_mypy,
    cmd_ruff,
    cmd_ruff_format,
)
from cihub.commands.hub_ci.release import (  # noqa: E402
    cmd_actionlint,
    cmd_actionlint_install,
    cmd_enforce,
    cmd_gitleaks_summary,
    cmd_kyverno_install,
    cmd_kyverno_test,
    cmd_kyverno_validate,
    cmd_license_check,
    cmd_pytest_summary,
    cmd_release_parse_tag,
    cmd_release_update_tag,
    cmd_summary,
    cmd_trivy_install,
    cmd_trivy_summary,
    cmd_zizmor_check,
    cmd_zizmor_run,
)
from cihub.commands.hub_ci.router import cmd_hub_ci  # noqa: E402
from cihub.commands.hub_ci.security import (  # noqa: E402
    cmd_bandit,
    cmd_pip_audit,
    cmd_security_bandit,
    cmd_security_owasp,
    cmd_security_pip_audit,
    cmd_security_ruff,
)
from cihub.commands.hub_ci.smoke import (  # noqa: E402
    _last_regex_int,
    cmd_smoke_python_black,
    cmd_smoke_python_install,
    cmd_smoke_python_ruff,
    cmd_smoke_python_tests,
)
from cihub.commands.hub_ci.test_metrics import cmd_test_metrics  # noqa: E402
from cihub.commands.hub_ci.validation import (  # noqa: E402
    cmd_docker_compose_check,
    cmd_quarantine_check,
    cmd_repo_check,
    cmd_source_check,
    cmd_syntax_check,
    cmd_validate_configs,
    cmd_validate_profiles,
    cmd_validate_triage,
    cmd_verify_matrix_keys,
    cmd_yamllint,
)

# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Canonical types (from cihub.types, re-exported for backward compatibility)
    "ToolResult",
    # OutputContext (new pattern - replaces 2-step output/summary helpers)
    "OutputContext",
    # CommandResult helpers (reduce boilerplate)
    "result_ok",
    "result_fail",
    "run_and_capture",
    # Shared helpers (deprecated - use OutputContext instead)
    "_write_outputs",
    "_append_summary",
    "_resolve_output_path",
    "_resolve_summary_path",
    "_extract_count",
    "_compare_badges",
    "_count_pip_audit_vulns",
    "_parse_env_bool",
    # Constants
    "EMPTY_SARIF",
    # Python tools
    "cmd_ruff",
    "cmd_ruff_format",
    "cmd_black",
    "cmd_mypy",
    "cmd_coverage_verify",
    "cmd_mutmut",
    # Badges
    "cmd_badges",
    "cmd_badges_commit",
    "cmd_outputs",
    # Security
    "cmd_bandit",
    "cmd_pip_audit",
    "cmd_security_pip_audit",
    "cmd_security_bandit",
    "cmd_security_ruff",
    "cmd_security_owasp",
    # Validation
    "cmd_syntax_check",
    "cmd_yamllint",
    "cmd_repo_check",
    "cmd_source_check",
    "cmd_docker_compose_check",
    "cmd_validate_configs",
    "cmd_validate_profiles",
    "cmd_validate_triage",
    "cmd_verify_matrix_keys",
    "cmd_quarantine_check",
    # Java tools
    "cmd_codeql_build",
    "cmd_smoke_java_build",
    "cmd_smoke_java_tests",
    "cmd_smoke_java_coverage",
    "cmd_smoke_java_checkstyle",
    "cmd_smoke_java_spotbugs",
    # Smoke tests
    "cmd_smoke_python_install",
    "cmd_smoke_python_tests",
    "cmd_smoke_python_ruff",
    "cmd_smoke_python_black",
    "_last_regex_int",
    # Test metrics
    "cmd_test_metrics",
    # Release & tooling
    "cmd_release_parse_tag",
    "cmd_release_update_tag",
    "cmd_kyverno_install",
    "cmd_kyverno_validate",
    "cmd_kyverno_test",
    "cmd_trivy_install",
    "cmd_trivy_summary",
    "cmd_zizmor_run",
    "cmd_zizmor_check",
    "cmd_actionlint_install",
    "cmd_actionlint",
    "cmd_license_check",
    "cmd_gitleaks_summary",
    "cmd_pytest_summary",
    "cmd_summary",
    "cmd_enforce",
    # Router
    "cmd_hub_ci",
]
