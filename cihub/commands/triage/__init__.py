"""Triage command package - Generate triage bundle outputs from CI artifacts.

This package provides the `cihub triage` command for analyzing CI failures
and generating actionable triage bundles.

Architecture:
    - types.py: Constants, severity maps, filter helpers
    - github.py: GitHub API client (GitHubRunClient)
    - artifacts.py: Artifact finding utilities
    - log_parser.py: Log parsing for failures
    - remote.py: Remote bundle generation strategies
    - verification.py: Tool verification
    - output.py: Output formatting
    - watch.py: Watch mode

Usage:
    from cihub.commands.triage import cmd_triage
"""

from __future__ import annotations

# Re-export the main command handler from the original module
from cihub.commands.triage_cmd import cmd_triage as cmd_triage

# Re-export types for external use
# find_all_reports_in_artifacts is kept for backward compatibility.
from .artifacts import find_all_reports_in_artifacts
from .artifacts import find_all_reports_in_artifacts as _find_all_reports_in_artifacts
from .artifacts import (
    find_artifact_by_pattern,
    find_report_in_artifacts,
    find_tool_outputs_in_artifacts,
    get_reports_dir_from_report,
)
from .github import (
    GitHubRunClient,
    RunInfo,
    download_artifacts,
    fetch_failed_logs,
    fetch_run_info,
    get_current_repo,
    get_latest_failed_run,
    list_runs,
)
from .log_parser import (
    create_log_failure,
    infer_tool_from_step,
    parse_log_failures,
)
from .output import (
    format_flaky_output,
    format_gate_history_output,
)
from .remote import (
    generate_multi_report_triage,
    generate_remote_triage_bundle,
    triage_single_run,
)
from .types import (
    MAX_ERRORS_IN_TRIAGE,
    SEVERITY_ORDER,
    TriageFilterConfig,
    build_meta,
    filter_bundle,
)
from .verification import (
    format_verify_tools_output,
    verify_tools_from_report,
)
from .watch import (
    watch_for_failures,
)

# Backward compatibility aliases (underscore-prefixed versions)
_format_verify_tools_output = format_verify_tools_output
_verify_tools_from_report = verify_tools_from_report
_format_gate_history_output = format_gate_history_output
_format_flaky_output = format_flaky_output
_generate_remote_triage_bundle = generate_remote_triage_bundle
_generate_multi_report_triage = generate_multi_report_triage
_triage_single_run = triage_single_run
_watch_for_failures = watch_for_failures

__all__ = [
    # Main command
    "cmd_triage",
    # Types
    "MAX_ERRORS_IN_TRIAGE",
    "SEVERITY_ORDER",
    "TriageFilterConfig",
    "build_meta",
    "filter_bundle",
    # GitHub
    "GitHubRunClient",
    "RunInfo",
    "download_artifacts",
    "fetch_failed_logs",
    "fetch_run_info",
    "get_current_repo",
    "get_latest_failed_run",
    "list_runs",
    # Artifacts
    "find_all_reports_in_artifacts",
    "find_artifact_by_pattern",
    "find_report_in_artifacts",
    "find_tool_outputs_in_artifacts",
    "get_reports_dir_from_report",
    # Log parser
    "create_log_failure",
    "infer_tool_from_step",
    "parse_log_failures",
    # Output formatting
    "format_flaky_output",
    "format_gate_history_output",
    # Remote bundle generation
    "generate_multi_report_triage",
    "generate_remote_triage_bundle",
    "triage_single_run",
    # Verification
    "format_verify_tools_output",
    "verify_tools_from_report",
    # Watch mode
    "watch_for_failures",
    # Backward compatibility (private functions used by tests)
    "_find_all_reports_in_artifacts",
    "_format_flaky_output",
    "_format_gate_history_output",
    "_format_verify_tools_output",
    "_generate_multi_report_triage",
    "_generate_remote_triage_bundle",
    "_triage_single_run",
    "_verify_tools_from_report",
    "_watch_for_failures",
]
