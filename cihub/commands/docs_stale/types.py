"""Data types and constants for docs stale detection.

This module contains all dataclasses and constants used by the docs_stale
package. Following the pattern from cihub/services/triage/types.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# =============================================================================
# Constants (from Part 11 of DOC_AUTOMATION_AUDIT.md)
# =============================================================================

# Default git revision range
DEFAULT_SINCE = "HEAD~10"

# Fence types to parse for CLI examples (Part 11 Decision 1)
# CLI examples are almost always in bash/shell fences
PARSED_FENCE_TYPES = frozenset({"bash", "shell", "console", "sh", "zsh", ""})

# Fence types to skip (illustrative code examples)
SKIPPED_FENCE_TYPES = frozenset(
    {
        "python",
        "json",
        "yaml",
        "xml",
        "java",
        "javascript",
        "typescript",
        "go",
        "rust",
        "sql",
        "html",
        "css",
    }
)

# Default exclusion patterns (Part 11 Decision 2)
DEFAULT_EXCLUDE_PATTERNS = [
    "docs/reference/**",  # Generated docs - use `cihub docs check` instead
    "docs/development/archive/**",  # Archived docs - historical
]

# False positive filters (Part 11)
# Common tokens that appear in backticks but aren't code symbols
FALSE_POSITIVE_TOKENS = frozenset(
    {
        # Boolean/null literals
        "true",
        "false",
        "none",
        "null",
        "yes",
        "no",
        # Log levels
        "ok",
        "error",
        "warning",
        "info",
        "debug",
        # Protocol/network
        "http",
        "https",
        "localhost",
        "github",
        # File extensions
        "md",
        "py",
        "json",
        "yaml",
        "yml",
        "txt",
        # Single letters (often used as variables in examples)
        "a",
        "b",
        "c",
        "i",
        "j",
        "k",
        "n",
        "x",
        "y",
        "z",
    }
)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CodeSymbol:
    """A symbol extracted from Python code.

    Represents functions, classes, async functions, and module-level constants
    discovered via AST parsing.

    Attributes:
        name: The symbol name (e.g., "load_config", "MyClass", "DEFAULT_VALUE")
        kind: The symbol type - "function", "async_function", "class", or "constant"
        file: The source file path
        line: The line number where the symbol is defined
    """

    name: str
    kind: str  # "function", "async_function", "class", "constant"
    file: str
    line: int


@dataclass
class DocReference:
    """A reference extracted from documentation.

    Represents code references found in markdown files, including
    backtick code spans, CLI commands, flags, file paths, config keys,
    and environment variables.

    Attributes:
        reference: The extracted reference text (e.g., "load_config", "--json")
        kind: The reference type - see KIND_* constants below
        file: The documentation file path
        line: The line number where the reference appears
        context: Surrounding text for AI output (typically ±1 line)
    """

    reference: str
    kind: str  # "backtick", "cli_command", "cli_flag", "file_path", "config_key", "env_var"
    file: str
    line: int
    context: str


# Reference kinds for DocReference.kind
KIND_BACKTICK = "backtick"
KIND_CLI_COMMAND = "cli_command"
KIND_CLI_FLAG = "cli_flag"
KIND_FILE_PATH = "file_path"
KIND_CONFIG_KEY = "config_key"
KIND_ENV_VAR = "env_var"


@dataclass
class StaleReference:
    """A documentation reference that may be stale.

    Represents a doc reference that points to a symbol or file that has been
    removed, renamed, or deleted since the base git revision.

    Attributes:
        doc_file: The documentation file containing the stale reference
        doc_line: The line number of the stale reference
        reference: The stale reference text
        reason: Why it's stale - "removed", "renamed", or "deleted_file"
        suggestion: Actionable suggestion (e.g., "Update to `new_name`")
        context: Surrounding text for AI output
    """

    doc_file: str
    doc_line: int
    reference: str
    reason: str  # "removed", "renamed", "deleted_file"
    suggestion: str
    context: str


# Reason constants for StaleReference.reason
REASON_REMOVED = "removed"
REASON_RENAMED = "renamed"
REASON_DELETED_FILE = "deleted_file"


@dataclass
class StaleReport:
    """Complete report of stale references.

    Aggregates all findings from a docs stale check, including
    symbol changes, file changes, and the stale references found.

    Attributes:
        git_range: The git revision range used (e.g., "HEAD~10")
        changed_symbols: All symbols that changed (removed + added + renamed)
        removed_symbols: Symbols that were removed (existed at base, not at head)
        added_symbols: Symbols that were added (not at base, exist at head)
        renamed_symbols: Symbols that were renamed as (old_name, new_name) pairs
        deleted_files: Files that were deleted
        renamed_files: Files that were renamed as (old_path, new_path) pairs
        stale_references: All stale references found in documentation
    """

    git_range: str
    changed_symbols: list[str] = field(default_factory=list)
    removed_symbols: list[str] = field(default_factory=list)
    added_symbols: list[str] = field(default_factory=list)
    renamed_symbols: list[tuple[str, str]] = field(default_factory=list)  # (old, new)
    deleted_files: list[str] = field(default_factory=list)
    renamed_files: list[tuple[str, str]] = field(default_factory=list)  # (old, new)
    stale_references: list[StaleReference] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict.

        Returns a structured dict suitable for JSON output mode.
        """
        return {
            "git_range": self.git_range,
            "stats": {
                "removed_symbols": len(self.removed_symbols),
                "added_symbols": len(self.added_symbols),
                "renamed_symbols": len(self.renamed_symbols),
                "deleted_files": len(self.deleted_files),
                "renamed_files": len(self.renamed_files),
                "stale_refs": len(self.stale_references),
            },
            "changed_symbols": {
                "removed": self.removed_symbols,
                "added": self.added_symbols,
                "renamed": [{"old": old, "new": new} for old, new in self.renamed_symbols],
            },
            "file_changes": {
                "deleted": self.deleted_files,
                "renamed": [{"old": old, "new": new} for old, new in self.renamed_files],
            },
            "stale_references": [
                {
                    "doc_file": ref.doc_file,
                    "doc_line": ref.doc_line,
                    "reference": ref.reference,
                    "reason": ref.reason,
                    "suggestion": ref.suggestion,
                    "context": ref.context,
                }
                for ref in self.stale_references
            ],
        }
