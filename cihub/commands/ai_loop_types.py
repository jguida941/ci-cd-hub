"""Types and configuration for the AI loop."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Safety configuration for AI loop (Section 4.1 of proposal)
# Keep in ai_loop_types.py initially; extract to config module later if needed
AI_LOOP_CONFIG: dict[str, Any] = {
    # Iteration limits
    "max_iterations": 10,
    "max_duration_seconds": 600,  # 10 minutes
    "no_change_threshold": 2,
    # File protection
    "max_files_per_iteration": 20,
    "forbidden_paths": [
        ".github/workflows/*",  # No workflow self-modification
        "*.env*",  # No secrets
        "pyproject.toml",  # No dependency changes (without approval)
        "setup.py",
        "requirements*.txt",
    ],
    # Validation requirements
    "require_test_pass": True,
    "require_lint_pass": True,
    "auto_rollback_on_regression": False,  # Disabled until Phase 3
    # Circuit breaker
    "circuit_breaker": {
        "consecutive_failures": 3,
        "same_error_threshold": 3,  # Stop if same error 3x
        "error_patterns": [
            "permission denied",
            "out of memory",
            "rate limit",
            "authentication failed",
        ],
    },
    # Audit trail
    "log_all_changes": True,
    "require_commit_per_iteration": False,  # Disabled by default
}


@dataclass
class Contract:
    """Parsed task contract data."""

    raw: dict[str, Any]
    output_promise: str | None
    success_criteria: list[dict[str, Any]]
    safety_rules: list[str]


@dataclass
class LoopState:
    """Track state across iterations."""

    iteration: int = 0
    max_iterations: int | None = 10
    max_duration_seconds: int = AI_LOOP_CONFIG["max_duration_seconds"]
    no_change_iterations: int = 0
    fixes_applied: list[str] = field(default_factory=list)
    failures_seen: list[str] = field(default_factory=list)
    last_failure_signature: frozenset[str] = field(default_factory=frozenset)
    consecutive_same_failures: int = 0
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str | None = None
    start_time: float = field(default_factory=time.time)


@dataclass
class SessionPaths:
    """Resolved session paths for the loop."""

    output_root: Path
    session_dir: Path
    ci_output_dir: Path
    history_path: Path
    lock_path: Path | None


@dataclass
class IterationArtifacts:
    """Per-iteration artifact paths."""

    iteration_dir: Path
    ci_result_path: Path
    state_path: Path
    metrics_path: Path
    review_path: Path
    bundle_json: Path | None
    bundle_md: Path | None


@dataclass
class RemoteRun:
    """Remote run metadata."""

    run_id: str
    conclusion: str
    status: str
    url: str


@dataclass
class LoopSettings:
    """Resolved CLI settings for the loop."""

    repo_path: Path
    output_root: Path
    max_iterations: int | None
    fix_mode: str
    emit_report: bool
    max_duration_seconds: int
    unsafe_unlimited: bool
    resume: bool
    contract: Contract | None
    contract_strict: bool
    review_command: str | None
    artifact_pack: bool
    bundle_dir: Path | None
    remote: bool
    remote_provider: str
    remote_repo: str | None
    workflow: str | None
    push: bool
    push_remote: str
    push_branch: str
    allow_protected_branch: bool
    allow_dirty: bool
    commit: bool
    commit_message: str
    triage_mode: str
    triage_run_id: str | None
    triage_output_dir: Path | None
    fallback: str
    remote_dry_run: bool
    correlation_id: str | None
    config_from_hub: str | None
    workdir: str | None
