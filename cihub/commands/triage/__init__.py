"""Triage command package - Generate triage bundle outputs from CI artifacts.

This package provides the `cihub triage` command for analyzing CI failures
and generating actionable triage bundles.

Architecture:
    - types.py: Constants, severity maps, filter helpers
    - github.py: GitHub API client (GitHubRunClient)
    - artifacts.py: Artifact finding utilities
    - log_parser.py: Log parsing for failures
    - (future) remote.py: Remote bundle generation strategies
    - (future) verification.py: Tool verification
    - (future) output.py: Output formatting
    - (future) watch.py: Watch mode

Usage:
    from cihub.commands.triage import cmd_triage
"""

from __future__ import annotations

# Re-export the main command handler from the original module
# This will be replaced with local implementation in later phases
from cihub.commands.triage_cmd import cmd_triage as cmd_triage

# Re-export private functions for backward compatibility (used by tests)
# These will be moved to verification.py in Phase 2
from cihub.commands.triage_cmd import (
    _verify_tools_from_report,
    _format_verify_tools_output,
)

# Re-export types for external use
from .artifacts import (
    find_all_reports_in_artifacts,
    find_all_reports_in_artifacts as _find_all_reports_in_artifacts,  # backward compat
    find_report_in_artifacts,
    find_tool_outputs_in_artifacts,
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
from .types import (
    MAX_ERRORS_IN_TRIAGE,
    SEVERITY_ORDER,
    TriageFilterConfig,
    build_meta,
    filter_bundle,
)

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
    "find_report_in_artifacts",
    "find_tool_outputs_in_artifacts",
    # Log parser
    "create_log_failure",
    "infer_tool_from_step",
    "parse_log_failures",
    # Backward compatibility (private functions used by tests)
    "_find_all_reports_in_artifacts",
    "_verify_tools_from_report",
    "_format_verify_tools_output",
]
