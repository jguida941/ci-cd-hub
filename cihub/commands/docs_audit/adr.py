"""ADR metadata validation.

This module implements Part 12.L from DOC_AUTOMATION_AUDIT.md:
- Lint for required metadata (Status, Date)
- Validate Status values (accepted, proposed, superseded)
- Check optional Superseded-by field when status is superseded
"""

from __future__ import annotations

import re
from pathlib import Path

from .types import (
    ADR_DIR,
    ADR_VALID_STATUSES,
    ADRMetadata,
    AuditFinding,
    FindingCategory,
    FindingSeverity,
)


def get_adr_files(repo_root: Path) -> list[str]:
    """Get all ADR files in docs/adr/.

    ADRs follow the pattern: NNNN-title.md

    Args:
        repo_root: Repository root path

    Returns:
        List of relative ADR file paths
    """
    adr_dir = repo_root / ADR_DIR
    if not adr_dir.exists():
        return []

    files = []
    # Match ADR pattern: 4 digits followed by title
    adr_pattern = re.compile(r"^\d{4}-.*\.md$")

    for md_file in adr_dir.glob("*.md"):
        if adr_pattern.match(md_file.name):
            files.append(str(md_file.relative_to(repo_root)))

    return sorted(files)


def parse_adr_metadata(file_path: Path) -> ADRMetadata:
    """Parse ADR file to extract metadata.

    Looks for metadata in the first 30 lines:
    - Status: accepted|proposed|superseded
    - Date: YYYY-MM-DD
    - Superseded-by: ADR-NNNN (optional)

    Args:
        file_path: Path to ADR file

    Returns:
        Parsed ADR metadata
    """
    content = file_path.read_text(encoding="utf-8")
    lines = content.split("\n")[:30]

    metadata = ADRMetadata(file=str(file_path))

    # Extract title from first heading
    for line in lines:
        if line.startswith("# "):
            metadata.title = line[2:].strip()
            break

    # Patterns for metadata fields - handle markdown bold (**Field:** value)
    # The value might also have ** around it that needs stripping
    status_pattern = re.compile(r"^\*?\*?Status\*?\*?:\s*\*?\*?(.+?)\*?\*?\s*$", re.IGNORECASE)
    date_pattern = re.compile(r"^\*?\*?Date\*?\*?:\s*\*?\*?(.+?)\*?\*?\s*$", re.IGNORECASE)
    superseded_pattern = re.compile(r"^\*?\*?Superseded[- ]by\*?\*?:\s*\*?\*?(.+?)\*?\*?\s*$", re.IGNORECASE)

    for line in lines:
        line = line.strip()

        # Check for Status
        status_match = status_pattern.match(line)
        if status_match:
            metadata.status = status_match.group(1).strip().lower()
            continue

        # Check for Date
        date_match = date_pattern.match(line)
        if date_match:
            metadata.date = date_match.group(1).strip()
            continue

        # Check for Superseded-by
        superseded_match = superseded_pattern.match(line)
        if superseded_match:
            metadata.superseded_by = superseded_match.group(1).strip()
            continue

    # Check for missing required fields
    if not metadata.status:
        metadata.missing_fields.append("Status")
    if not metadata.date:
        metadata.missing_fields.append("Date")

    # Check for invalid status
    if metadata.status and metadata.status not in ADR_VALID_STATUSES:
        metadata.invalid_status = True

    return metadata


def validate_adr_metadata(adr_files: list[str], repo_root: Path) -> list[AuditFinding]:
    """Validate ADR metadata for all ADR files.

    Part 12.L requirements:
    - Required: Status, Date
    - Status must be: accepted, proposed, superseded, deprecated
    - Superseded ADRs should have Superseded-by field

    Args:
        adr_files: List of ADR file paths
        repo_root: Repository root path

    Returns:
        List of findings for ADR metadata issues
    """
    findings: list[AuditFinding] = []

    for adr_path in adr_files:
        full_path = repo_root / adr_path
        if not full_path.exists():
            continue

        metadata = parse_adr_metadata(full_path)

        # Report missing required fields
        for field in metadata.missing_fields:
            findings.append(
                AuditFinding(
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.ADR_METADATA,
                    message=f"ADR missing required field: {field}",
                    file=adr_path,
                    code="CIHUB-AUDIT-ADR-MISSING-FIELD",
                    suggestion=f"Add '{field}: <value>' to the ADR header",
                )
            )

        # Report invalid status
        if metadata.invalid_status and metadata.status:
            valid_list = ", ".join(sorted(ADR_VALID_STATUSES))
            findings.append(
                AuditFinding(
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.ADR_METADATA,
                    message=f"ADR has invalid status: '{metadata.status}'",
                    file=adr_path,
                    code="CIHUB-AUDIT-ADR-INVALID-STATUS",
                    suggestion=f"Use one of: {valid_list}",
                )
            )

        # Warn if superseded but no Superseded-by field
        if metadata.status == "superseded" and not metadata.superseded_by:
            findings.append(
                AuditFinding(
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.ADR_METADATA,
                    message="Superseded ADR missing Superseded-by field",
                    file=adr_path,
                    code="CIHUB-AUDIT-ADR-NO-SUPERSEDED-BY",
                    suggestion="Add 'Superseded-by: ADR-NNNN' to indicate the replacement",
                )
            )

        # Validate date format (YYYY-MM-DD)
        if metadata.date:
            date_format = re.compile(r"^\d{4}-\d{2}-\d{2}$")
            if not date_format.match(metadata.date):
                findings.append(
                    AuditFinding(
                        severity=FindingSeverity.WARNING,
                        category=FindingCategory.ADR_METADATA,
                        message=f"ADR date format should be YYYY-MM-DD, got: '{metadata.date}'",
                        file=adr_path,
                        code="CIHUB-AUDIT-ADR-DATE-FORMAT",
                        suggestion="Use ISO date format: YYYY-MM-DD",
                    )
                )

    return findings
