"""Data types and constants for docs audit.

This module contains all dataclasses and constants used by the docs_audit
package. Following the pattern from cihub/commands/docs_stale/types.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# =============================================================================
# Constants
# =============================================================================

# Required ADR metadata fields (Part 12.L)
ADR_REQUIRED_FIELDS = frozenset({"Status", "Date"})
ADR_OPTIONAL_FIELDS = frozenset({"Superseded-by", "Implementation"})
ADR_VALID_STATUSES = frozenset({"accepted", "proposed", "superseded", "deprecated", "implemented"})

# Required manual doc header fields (Part 12.Q)
DOC_HEADER_FIELDS = frozenset({"Status", "Owner", "Source-of-truth", "Last-reviewed"})
DOC_HEADER_OPTIONAL = frozenset({"Superseded-by"})
DOC_VALID_STATUSES = frozenset({"active", "archived", "reference"})
DOC_VALID_SOURCES = frozenset({"CLI", "schema", "workflow", "manual"})

# Superseded header pattern (Part 12.J)
# Flexible patterns to detect various superseded/archived header formats:
# - "> **WARNING: SUPERSEDED:**" or "> Superseded by" (blockquote with SUPERSEDED anywhere)
# - "# Superseded" (heading)
# - "> **Status:** Superseded" or "**Status:** Archived" (status line)
# - "Status: Archived" (plain status)
# - "> Legacy archive" or "> Historical Reference" (informal archive markers)
SUPERSEDED_HEADER_PATTERNS = [
    r"(?i)^\s*>\s*.*\bsuperseded\b",  # Blockquote containing "superseded" anywhere
    r"(?i)^\s*>\s*.*\barchived?\b",  # Blockquote containing "archive" or "archived"
    r"(?i)^\s*>\s*.*\blegacy\s+archive\b",  # "Legacy archive" marker
    r"(?i)^\s*>\s*.*\bhistorical\s+(reference|context)\b",  # Historical reference/context
    r"(?i)^#+\s*superseded",  # Heading "# Superseded"
    r"(?i)^\*?\*?status\*?\*?:?\s*(superseded|archived)",  # Status: superseded/archived
]

# Paths for lifecycle validation
ACTIVE_DOCS_DIR = "docs/development/active"
ARCHIVE_DOCS_DIR = "docs/development/archive"
STATUS_MD_PATH = "docs/development/status/STATUS.md"
README_PATH = "docs/README.md"
MASTER_PLAN_PATH = "docs/development/MASTER_PLAN.md"
ADR_DIR = "docs/adr"

# Reference patterns for plain-text scan (Part 12.N)
DOCS_PATH_PATTERN = r"docs/[a-zA-Z0-9_\-./]+"


# =============================================================================
# Enums
# =============================================================================


class FindingSeverity(str, Enum):
    """Severity levels for audit findings."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class FindingCategory(str, Enum):
    """Categories of audit findings."""

    LIFECYCLE = "lifecycle"
    ADR_METADATA = "adr_metadata"
    HEADER = "header"
    REFERENCE = "reference"
    SYNC = "sync"
    GUIDE_COMMAND = "guide_command"
    # Part 13 categories
    DUPLICATE_TASK = "duplicate_task"
    TIMESTAMP = "timestamp"
    CHECKLIST = "checklist"
    PLACEHOLDER = "placeholder"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AuditFinding:
    """A single audit finding.

    Represents an issue found during documentation audit, such as
    missing STATUS.md entries, invalid ADR metadata, or broken references.

    Attributes:
        severity: How critical the finding is (error, warning, info)
        category: The type of check that produced this finding
        message: Human-readable description of the issue
        file: The file where the issue was found (if applicable)
        line: The line number (if applicable)
        code: Machine-readable error code
        suggestion: Actionable fix suggestion
    """

    severity: FindingSeverity
    category: FindingCategory
    message: str
    file: str | None = None
    line: int | None = None
    code: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result: dict[str, Any] = {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "code": self.code,
        }
        if self.file:
            result["file"] = self.file
        if self.line is not None:
            result["line"] = self.line
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class AuditReport:
    """Complete documentation audit report.

    Aggregates all findings from a docs audit check across
    lifecycle, ADR, header, and reference validations.

    Attributes:
        findings: All audit findings
        active_docs: Files found in docs/development/active/
        status_entries: Entries parsed from STATUS.md
        adr_files: ADR files found
        archive_docs: Files found in docs/development/archive/
        inventory_summary: Optional doc inventory counts (when requested)
    """

    findings: list[AuditFinding] = field(default_factory=list)
    active_docs: list[str] = field(default_factory=list)
    status_entries: list[str] = field(default_factory=list)
    adr_files: list[str] = field(default_factory=list)
    archive_docs: list[str] = field(default_factory=list)
    inventory_summary: DocInventorySummary | None = None

    @property
    def error_count(self) -> int:
        """Count of error-level findings."""
        return sum(1 for f in self.findings if f.severity == FindingSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level findings."""
        return sum(1 for f in self.findings if f.severity == FindingSeverity.WARNING)

    @property
    def has_errors(self) -> bool:
        """True if any error-level findings exist."""
        return self.error_count > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict.

        Returns a structured dict suitable for JSON output mode.
        """
        data = {
            "stats": {
                "total_findings": len(self.findings),
                "errors": self.error_count,
                "warnings": self.warning_count,
                "active_docs": len(self.active_docs),
                "archive_docs": len(self.archive_docs),
                "adr_files": len(self.adr_files),
            },
            "findings": [f.to_dict() for f in self.findings],
            "inventory": {
                "active_docs": self.active_docs,
                "status_entries": self.status_entries,
                "adr_files": self.adr_files,
                "archive_docs": self.archive_docs,
            },
        }
        if self.inventory_summary is not None:
            data["inventory_summary"] = self.inventory_summary.to_dict()
        return data


@dataclass
class DocInventoryCategory:
    """Inventory counts for a documentation category."""

    files: int = 0
    lines: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to JSON-serializable dict."""
        return {"files": self.files, "lines": self.lines}


@dataclass
class DocInventorySummary:
    """Inventory summary for docs/ markdown files."""

    total_files: int = 0
    total_lines: int = 0
    categories: dict[str, DocInventoryCategory] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "categories": {name: category.to_dict() for name, category in self.categories.items()},
        }


@dataclass
class ADRMetadata:
    """Parsed ADR metadata.

    Represents the frontmatter/header metadata extracted from an ADR file.

    Attributes:
        file: The ADR file path
        status: The Status field value (if found)
        date: The Date field value (if found)
        superseded_by: The Superseded-by field value (if found)
        title: The ADR title (from # heading or filename)
        missing_fields: Required fields that are missing
        invalid_status: True if status value is not in valid set
    """

    file: str
    status: str | None = None
    date: str | None = None
    superseded_by: str | None = None
    title: str = ""
    missing_fields: list[str] = field(default_factory=list)
    invalid_status: bool = False


@dataclass
class TaskEntry:
    """A checklist task entry parsed from a planning doc.

    Used for duplicate detection (Part 13.S) and checklist verification (Part 13.U).

    Attributes:
        file: Source file path
        line: Line number in file
        text: Original task text
        normalized: Normalized text for matching (lowercase, no backticks)
        completed: True if marked [x], False if [ ]
    """

    file: str
    line: int
    text: str
    normalized: str
    completed: bool


@dataclass
class DuplicateTaskGroup:
    """A group of duplicate tasks found across planning docs.

    Represents tasks that are semantically the same but appear in multiple places.

    Attributes:
        normalized_text: The normalized key used for grouping
        entries: All task entries that match this group
    """

    normalized_text: str
    entries: list[TaskEntry] = field(default_factory=list)


@dataclass
class TimestampInfo:
    """Timestamp metadata parsed from a doc header.

    Used for timestamp freshness validation (Part 13.T).

    Attributes:
        file: Source file path
        line: Line number where timestamp was found
        header_type: Type of header (e.g., "Last Updated", "Last Verified")
        date_str: The date string as written in the doc
        days_old: Number of days since the timestamp
    """

    file: str
    line: int
    header_type: str
    date_str: str
    days_old: int


# =============================================================================
# Constants for Part 13
# =============================================================================

# Planning docs to scan for duplicates and checklists
PLANNING_DOCS = [
    "docs/development/MASTER_PLAN.md",
    "docs/development/active/TYPESCRIPT_CLI_DESIGN.md",
    "docs/development/active/AI_CI_LOOP_PROPOSAL.md",
    "docs/development/active/PYQT_PLAN.md",
]

# Timestamp header patterns (Part 13.T)
TIMESTAMP_PATTERNS = [
    (r"\*\*Last Updated:\*\*\s*(\d{4}-\d{2}-\d{2})", "Last Updated"),
    (r"\*\*Last Verified:\*\*\s*(\d{4}-\d{2}-\d{2})", "Last Verified"),
    (r"Last-reviewed:\s*(\d{4}-\d{2}-\d{2})", "Last-reviewed"),
    (r"\*Last updated:\s*(\d{4}-\d{2}-\d{2})\*", "Last updated"),
]

# Placeholder patterns (Part 13.V)
# NOTE: GitHub username detection was removed (too many false positives).
# Patterns are now defined inline in consistency.py::find_placeholders()
# to allow for easier tuning without changing the types module.

# Default thresholds
TIMESTAMP_WARN_DAYS = 7
TIMESTAMP_ERROR_DAYS = 30
DUPLICATE_SIMILARITY_THRESHOLD = 0.8
