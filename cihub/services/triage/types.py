"""Triage data types and constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Schema versions
TRIAGE_SCHEMA_VERSION = "cihub-triage-v2"  # Bumped for tool_evidence addition
PRIORITY_SCHEMA_VERSION = "cihub-priority-v1"
MULTI_TRIAGE_SCHEMA_VERSION = "cihub-multi-triage-v1"

# Threshold for test count drop warning (Issue 16)
TEST_COUNT_DROP_THRESHOLD = 0.10  # 10% drop triggers warning


class ToolStatus(Enum):
    """Status of a tool in the CI run."""

    PASSED = "passed"  # Ran successfully, met thresholds
    FAILED = "failed"  # Ran but failed (threshold or execution error)
    SKIPPED = "skipped"  # Configured but didn't run (soft skip)
    REQUIRED_NOT_RUN = "required_not_run"  # require_run=true but didn't run (hard fail)
    NOT_CONFIGURED = "not_configured"  # Tool not enabled in config


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolEvidence:
    """Evidence about a tool's status in a CI run.

    This provides artifact-first explainability: from just the report.json,
    a consumer can understand why a tool passed/failed/skipped.
    """

    tool: str
    configured: bool
    ran: bool
    require_run: bool
    success: bool | None  # None if didn't run
    status: ToolStatus
    explanation: str
    metrics: dict[str, Any] = field(default_factory=dict)
    has_artifacts: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "tool": self.tool,
            "configured": self.configured,
            "ran": self.ran,
            "require_run": self.require_run,
            "success": self.success,
            "status": self.status.value,
            "explanation": self.explanation,
            "metrics": self.metrics,
            "has_artifacts": self.has_artifacts,
        }


@dataclass(slots=True, kw_only=True)
class MultiTriageResult:
    """Result of multi-report triage aggregation."""

    schema_version: str
    generated_at: str
    repo_count: int
    passed_count: int
    failed_count: int
    repos: list[dict[str, Any]]
    failures_by_tool: dict[str, list[str]]  # tool -> list of repos that failed
    failures_by_repo: dict[str, list[str]]  # repo -> list of tools that failed
    summary_markdown: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_count": self.repo_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "repos": self.repos,
            "failures_by_tool": self.failures_by_tool,
            "failures_by_repo": self.failures_by_repo,
        }


@dataclass(frozen=True, slots=True)
class TriageBundle:
    """Complete triage output bundle."""

    triage: dict[str, Any]
    priority: dict[str, Any]
    markdown: str
    history_entry: dict[str, Any]


# Tool categorization constants
SEVERITY_ORDER = {"blocker": 0, "high": 1, "medium": 2, "low": 3}
CATEGORY_ORDER = ["workflow", "security", "test", "lint", "docs", "build", "cihub"]

CATEGORY_BY_TOOL = {
    "pytest": "test",
    "mutmut": "test",
    "hypothesis": "test",
    "build": "build",
    "jacoco": "test",
    "pitest": "test",
    "checkstyle": "lint",
    "spotbugs": "lint",
    "pmd": "lint",
    "ruff": "lint",
    "black": "lint",
    "isort": "lint",
    "mypy": "lint",
    "bandit": "security",
    "pip_audit": "security",
    "semgrep": "security",
    "trivy": "security",
    "owasp": "security",
    "codeql": "security",
    "sbom": "security",
    "docker": "build",
}

SEVERITY_BY_CATEGORY = {
    "workflow": "blocker",
    "security": "high",
    "test": "medium",
    "lint": "low",
    "docs": "low",
    "build": "medium",
    "cihub": "blocker",
}
