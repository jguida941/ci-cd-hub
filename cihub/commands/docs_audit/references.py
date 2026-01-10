"""Plain-text reference validation.

This module implements Part 12.N from DOC_AUTOMATION_AUDIT.md:
- Regex scanning for docs/... strings (not just Markdown links)
- Catch missing/moved paths referenced in prose, scripts, or ADRs
"""

from __future__ import annotations

import re
from pathlib import Path

from .types import (
    DOCS_PATH_PATTERN,
    AuditFinding,
    FindingCategory,
    FindingSeverity,
)

# Directories to scan for doc references
SCAN_DIRS = [
    "docs",
    "cihub",
    ".github",
    "scripts",
    "tests",
]

# File patterns to scan
SCAN_PATTERNS = ["*.md", "*.py", "*.yml", "*.yaml", "*.sh"]

# Patterns to exclude from scanning
EXCLUDE_PATTERNS = [
    "docs/development/archive/",  # Archived docs may have stale refs (expected)
    ".git/",
    "__pycache__/",
    "*.pyc",
    ".mypy_cache/",
    ".pytest_cache/",
    "node_modules/",
]

# Known valid references that don't need to exist as files
# (e.g., placeholders, examples, or pattern descriptions)
KNOWN_EXCEPTIONS = frozenset({
    "docs/...",
    "docs/**",
    "docs/reference/**",
    "docs/development/active/**",
    "docs/development/archive/**",
    "docs/development/archive/.*",
    "docs/adr/**",
})


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded from scanning.

    Args:
        path: Path to check

    Returns:
        True if path should be excluded
    """
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern.endswith("/"):
            if pattern[:-1] in path_str:
                return True
        elif pattern.startswith("*."):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str:
            return True
    return False


def extract_doc_references(content: str, file_path: str) -> list[tuple[int, str]]:
    """Extract all docs/ path references from file content.

    Finds references like:
    - docs/reference/CLI.md
    - docs/development/active/CLEAN_CODE.md
    - docs/adr/0001-title.md

    Args:
        content: File content to scan
        file_path: Path of the file being scanned (for context)

    Returns:
        List of (line_number, reference) tuples
    """
    references: list[tuple[int, str]] = []
    pattern = re.compile(DOCS_PATH_PATTERN)

    for line_num, line in enumerate(content.split("\n"), 1):
        for match in pattern.finditer(line):
            ref = match.group(0)
            # Clean up common trailing characters
            ref = ref.rstrip(")`'\",;:]")
            # Skip known exceptions
            if ref in KNOWN_EXCEPTIONS:
                continue
            # Skip if it looks like a glob pattern
            if "*" in ref or "..." in ref:
                continue
            references.append((line_num, ref))

    return references


def validate_doc_references(repo_root: Path) -> list[AuditFinding]:
    """Scan codebase for docs/ references and validate they exist.

    Part 12.N requirement:
    - Find docs/... strings in prose, scripts, and code
    - Verify referenced paths exist
    - Report missing/moved paths

    Args:
        repo_root: Repository root path

    Returns:
        List of findings for broken doc references
    """
    findings: list[AuditFinding] = []
    checked_refs: set[tuple[str, str]] = set()  # (file, ref) to avoid duplicates

    for scan_dir in SCAN_DIRS:
        dir_path = repo_root / scan_dir
        if not dir_path.exists():
            continue

        for pattern in SCAN_PATTERNS:
            for file_path in dir_path.rglob(pattern):
                if should_exclude(file_path):
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue

                rel_path = str(file_path.relative_to(repo_root))
                references = extract_doc_references(content, rel_path)

                for line_num, ref in references:
                    # Skip if already checked this exact reference from this file
                    check_key = (rel_path, ref)
                    if check_key in checked_refs:
                        continue
                    checked_refs.add(check_key)

                    # Strip anchors (#section) and query params before checking
                    ref_clean = ref.split("#")[0].split("?")[0]
                    if not ref_clean:
                        continue

                    # Check if the referenced path exists
                    # Handle both with and without file extension
                    ref_path = repo_root / ref_clean
                    exists = ref_path.exists()

                    # Also check if it might be a directory reference
                    if not exists and not ref_clean.endswith(".md"):
                        exists = (repo_root / ref_clean).is_dir()

                    if not exists:
                        findings.append(
                            AuditFinding(
                                severity=FindingSeverity.WARNING,
                                category=FindingCategory.REFERENCE,
                                message=f"Reference to non-existent path: {ref}",
                                file=rel_path,
                                line=line_num,
                                code="CIHUB-AUDIT-BROKEN-REF",
                                suggestion="Update reference to correct path or remove if obsolete",
                            )
                        )

    return findings
