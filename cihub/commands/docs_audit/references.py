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
    "docs/development/research/",  # Research logs are historical
    ".git/",
    "__pycache__/",
    "*.pyc",
    ".mypy_cache/",
    ".pytest_cache/",
    "node_modules/",
]

# Known valid references that don't need to exist as files
# (e.g., placeholders, examples, or pattern descriptions)
KNOWN_EXCEPTIONS = frozenset(
    {
        "docs/...",
        "docs/**",
        "docs/reference/**",
        "docs/development/active/**",
        "docs/development/archive/**",
        "docs/development/archive/.*",
        "docs/adr/**",
        # Template/example patterns
        "docs/adr/00xx-incident.md",  # Placeholder ADR number
        "docs/adr/0001-title.md",  # Example ADR pattern
        "docs/file.md",  # Generic example
        "docs/test.md",  # Test example
        "docs/modularization.md",  # Example
        # References to directories (not files)
        "docs/tests",
        "docs/ADRs/scripts/workflows",
        "docs/preflight/scaffold/smoke/check",
        "docs/README/guide/dev",
        "docs/development/execution/",
        "docs/documenting/yaml-style-guide/",
        "docs/docs/backlog.md",
        "docs/git-diff",
        "docs/sphinx-autoapi",
        # Active design doc templates
        "docs/development/active/FOO.md",
        "docs/development/active/BAR.md",
        "docs/development/active/NEW.md",
        # Wildcard ADR references (used in documentation)
        "docs/adr/0035-",
        "docs/adr/0045-",
        # Old paths now in archive
        "docs/development/audit.md",
        "docs/development/architecture/ARCHITECTURE_PLAN.md",
        "docs/development/ARCHITECTURE.md",
        "docs/development/execution/SMOKE_TEST.md",
        "docs/development/execution/SMOKE_TEST_REPOS.md",
        # Conceptual/planning references
        "docs/MAKE.md",
        "docs/analysis/scalability.md",
    }
)


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
    - docs/development/archive/CLEAN_CODE.md
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
            if not _is_valid_reference_start(line, match.start()):
                continue
            ref = match.group(0)
            # Clean up common trailing characters
            ref = ref.rstrip(")`'\",;:].")
            # Skip known exceptions
            if ref in KNOWN_EXCEPTIONS:
                continue
            # Skip if it looks like a glob pattern
            if "*" in ref or "..." in ref:
                continue
            # Skip if it's part of a URL (e.g., https://github.com/.../docs/checks.md)
            match_start = match.start()
            if match_start > 0:
                # Look back to see if this is in a URL
                prefix = line[:match_start]
                if "http://" in prefix or "https://" in prefix:
                    # Check if there's no space/bracket between URL and match
                    last_space = max(prefix.rfind(" "), prefix.rfind("("), prefix.rfind("["))
                    url_start = max(prefix.rfind("http://"), prefix.rfind("https://"))
                    if url_start > last_space:
                        continue  # This docs/ path is part of a URL
            references.append((line_num, ref))

    return references


def _is_valid_reference_start(line: str, match_start: int) -> bool:
    """Validate that a docs/ reference isn't embedded in another path."""
    if match_start == 0:
        return True

    prefix = line[:match_start]
    prev_char = prefix[-1]

    if prev_char.isalnum() or prev_char in "_-.":
        return False

    if prev_char == "/":
        # Allow relative references like ../docs/... or ./docs/...
        if re.search(r"(?:^|[^A-Za-z0-9_-])(?:\./|\.\./)+$", prefix):
            return True
        return False

    return True


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
