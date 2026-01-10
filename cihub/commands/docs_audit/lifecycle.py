"""Lifecycle validation for documentation.

This module implements Part 12.J from DOC_AUTOMATION_AUDIT.md:
- All design docs in progress live under docs/development/active/
- Every file in docs/development/active/ must be listed in STATUS.md
- Moves to docs/development/archive/ must include a Superseded header
- Path changes require updates to docs/README.md, MASTER_PLAN.md, STATUS.md
"""

from __future__ import annotations

import re
from pathlib import Path

from .types import (
    ACTIVE_DOCS_DIR,
    ARCHIVE_DOCS_DIR,
    STATUS_MD_PATH,
    SUPERSEDED_HEADER_PATTERNS,
    AuditFinding,
    FindingCategory,
    FindingSeverity,
)


def get_active_docs(repo_root: Path) -> list[str]:
    """Get all markdown files in docs/development/active/.

    Args:
        repo_root: Repository root path

    Returns:
        List of relative file paths
    """
    active_dir = repo_root / ACTIVE_DOCS_DIR
    if not active_dir.exists():
        return []

    files = []
    for md_file in active_dir.glob("*.md"):
        files.append(str(md_file.relative_to(repo_root)))
    return sorted(files)


def get_archive_docs(repo_root: Path) -> list[str]:
    """Get all markdown files in docs/development/archive/.

    Args:
        repo_root: Repository root path

    Returns:
        List of relative file paths
    """
    archive_dir = repo_root / ARCHIVE_DOCS_DIR
    if not archive_dir.exists():
        return []

    files = []
    for md_file in archive_dir.rglob("*.md"):
        files.append(str(md_file.relative_to(repo_root)))
    return sorted(files)


def parse_status_md_entries(repo_root: Path) -> list[str]:
    """Parse STATUS.md to extract Active Design Docs table entries.

    Looks specifically for the "Active Design Docs" table section and extracts
    links to files that should be in docs/development/active/.

    Args:
        repo_root: Repository root path

    Returns:
        List of doc names (just filenames) from the Active Design Docs table
    """
    status_path = repo_root / STATUS_MD_PATH
    if not status_path.exists():
        return []

    content = status_path.read_text(encoding="utf-8")
    entries = []

    # Find the "Active Design Docs" section
    # Look for table rows after the "## Active Design Docs" heading
    in_active_table = False
    table_started = False

    for line in content.split("\n"):
        # Detect the Active Design Docs heading
        if "## Active Design Docs" in line:
            in_active_table = True
            continue

        # Stop when we hit the next section
        if in_active_table and line.startswith("## "):
            break

        # Detect table start (header separator)
        if in_active_table and "|---" in line:
            table_started = True
            continue

        # Parse table rows
        if in_active_table and table_started and line.startswith("|"):
            # Extract links from table row: [Name](../active/FILE.md)
            link_pattern = re.compile(r'\[([^\]]+)\]\(\.\./active/([^)]+\.md)\)')
            for match in link_pattern.finditer(line):
                filename = match.group(2)
                entries.append(filename)

    return entries


def check_active_status_sync(
    active_docs: list[str],
    status_entries: list[str],
) -> list[AuditFinding]:
    """Check that active/ docs and STATUS.md are in sync.

    Part 12.J requirements:
    - Every file in docs/development/active/ must be listed in STATUS.md
    - Every entry in STATUS.md Active table must exist as a file

    Args:
        active_docs: Files found in active/ directory
        status_entries: Entries parsed from STATUS.md

    Returns:
        List of findings for sync issues
    """
    findings: list[AuditFinding] = []

    # Normalize paths for comparison
    active_set = {Path(p).name for p in active_docs}
    status_set = set()

    for entry in status_entries:
        # Extract just the filename for comparison
        if "/" in entry:
            name = Path(entry).name
        else:
            name = entry
        if name.endswith(".md"):
            status_set.add(name)

    # Files in active/ but not in STATUS.md
    missing_in_status = active_set - status_set
    for name in sorted(missing_in_status):
        findings.append(
            AuditFinding(
                severity=FindingSeverity.ERROR,
                category=FindingCategory.SYNC,
                message=f"Active doc not listed in STATUS.md: {name}",
                file=f"{ACTIVE_DOCS_DIR}/{name}",
                code="CIHUB-AUDIT-MISSING-IN-STATUS",
                suggestion=f"Add {name} to the Active Design Docs table in {STATUS_MD_PATH}",
            )
        )

    # Entries in STATUS.md but file doesn't exist
    missing_files = status_set - active_set
    for name in sorted(missing_files):
        findings.append(
            AuditFinding(
                severity=FindingSeverity.ERROR,
                category=FindingCategory.SYNC,
                message=f"STATUS.md references non-existent file: {name}",
                file=STATUS_MD_PATH,
                code="CIHUB-AUDIT-MISSING-FILE",
                suggestion=f"Remove {name} from STATUS.md or create the file in {ACTIVE_DOCS_DIR}/",
            )
        )

    return findings


def check_archive_superseded_headers(
    archive_docs: list[str],
    repo_root: Path,
) -> list[AuditFinding]:
    """Check that archived docs have Superseded headers.

    Part 12.J requirement:
    - Files in docs/development/archive/ must have a Superseded header

    Args:
        archive_docs: Files found in archive/ directory
        repo_root: Repository root path

    Returns:
        List of findings for missing superseded headers
    """
    findings: list[AuditFinding] = []

    for doc_path in archive_docs:
        full_path = repo_root / doc_path
        if not full_path.exists():
            continue

        content = full_path.read_text(encoding="utf-8")
        # Check first 50 lines for superseded header
        lines = content.split("\n")[:50]
        header_text = "\n".join(lines)

        has_superseded = False
        for pattern in SUPERSEDED_HEADER_PATTERNS:
            if re.search(pattern, header_text, re.MULTILINE):
                has_superseded = True
                break

        if not has_superseded:
            findings.append(
                AuditFinding(
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.LIFECYCLE,
                    message=f"Archived doc missing Superseded header: {doc_path}",
                    file=doc_path,
                    code="CIHUB-AUDIT-NO-SUPERSEDED",
                    suggestion="Add a '> **Superseded by:** [doc](path)' header at the top",
                )
            )

    return findings


def validate_lifecycle(repo_root: Path) -> tuple[list[AuditFinding], list[str], list[str], list[str]]:
    """Run all lifecycle validations.

    Args:
        repo_root: Repository root path

    Returns:
        Tuple of (findings, active_docs, status_entries, archive_docs)
    """
    findings: list[AuditFinding] = []

    # Gather inventory
    active_docs = get_active_docs(repo_root)
    archive_docs = get_archive_docs(repo_root)
    status_entries = parse_status_md_entries(repo_root)

    # Check STATUS.md exists
    status_path = repo_root / STATUS_MD_PATH
    if not status_path.exists():
        findings.append(
            AuditFinding(
                severity=FindingSeverity.ERROR,
                category=FindingCategory.LIFECYCLE,
                message=f"STATUS.md not found at {STATUS_MD_PATH}",
                code="CIHUB-AUDIT-NO-STATUS-MD",
                suggestion=f"Create {STATUS_MD_PATH} with Active Design Docs table",
            )
        )
    else:
        # Check sync
        findings.extend(check_active_status_sync(active_docs, status_entries))

    # Check archive headers
    findings.extend(check_archive_superseded_headers(archive_docs, repo_root))

    return findings, active_docs, status_entries, archive_docs
