"""Cross-document consistency validation.

This module implements Part 13 from DOC_AUTOMATION_AUDIT.md:
- S. Duplicate Task Detection across planning docs
- T. Timestamp Freshness Validation
- V. Hardcoded Placeholder Detection

Note: Part 13.U (Checklist vs Reality) requires CLI introspection and is
deferred for a separate implementation.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from .types import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    PLANNING_DOCS,
    TIMESTAMP_ERROR_DAYS,
    TIMESTAMP_PATTERNS,
    TIMESTAMP_WARN_DAYS,
    AuditFinding,
    DuplicateTaskGroup,
    FindingCategory,
    FindingSeverity,
    TaskEntry,
)


def _normalize_task_text(text: str) -> str:
    """Normalize task text for matching.

    Removes markdown formatting, collapses whitespace, and lowercases.

    Args:
        text: Original task text

    Returns:
        Normalized string for comparison
    """
    # Remove backticks and their content
    normalized = re.sub(r"`[^`]+`", "", text)
    # Remove markdown links but keep text: [text](url) -> text
    normalized = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", normalized)
    # Remove bold/italic
    normalized = re.sub(r"\*+([^*]+)\*+", r"\1", normalized)
    # Collapse whitespace and lowercase
    normalized = " ".join(normalized.lower().split())
    return normalized


def _similarity(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings.

    Uses SequenceMatcher for fuzzy matching.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Float between 0 and 1 indicating similarity
    """
    return SequenceMatcher(None, s1, s2).ratio()


def parse_checklist_items(doc_path: Path, repo_root: Path | None = None) -> list[TaskEntry]:
    """Parse all checklist items from a planning doc.

    Finds markdown checklist items like:
    - [ ] Incomplete task
    - [x] Complete task
    * [ ] Another format

    Args:
        doc_path: Path to the markdown file
        repo_root: Optional repo root for computing relative paths

    Returns:
        List of TaskEntry objects
    """
    if not doc_path.exists():
        return []

    entries: list[TaskEntry] = []
    content = doc_path.read_text(encoding="utf-8")
    # Use repo-relative path if repo_root provided
    rel_path = str(doc_path.relative_to(repo_root)) if repo_root else str(doc_path)

    # Match: - [ ] task or - [x] task or * [ ] task
    pattern = re.compile(r"^[-*]\s*\[([ xX])\]\s*(.+)$")

    for line_num, line in enumerate(content.splitlines(), 1):
        line_stripped = line.strip()
        match = pattern.match(line_stripped)
        if match:
            status, task_text = match.groups()
            normalized = _normalize_task_text(task_text)
            entries.append(
                TaskEntry(
                    file=rel_path,
                    line=line_num,
                    text=task_text.strip(),
                    normalized=normalized,
                    completed=(status.lower() == "x"),
                )
            )

    return entries


def find_duplicate_tasks(repo_root: Path) -> tuple[list[DuplicateTaskGroup], list[AuditFinding]]:
    """Detect duplicate checklist items across planning docs.

    Part 13.S: Finds tasks that appear multiple times, which creates
    confusion about which is canonical and whether work is complete.

    Args:
        repo_root: Repository root path

    Returns:
        Tuple of (duplicate groups, findings)
    """
    all_tasks: list[TaskEntry] = []

    # Parse all planning docs
    for doc_rel in PLANNING_DOCS:
        doc_path = repo_root / doc_rel
        tasks = parse_checklist_items(doc_path, repo_root=repo_root)
        all_tasks.extend(tasks)

    # Group by normalized text using fuzzy matching
    groups: dict[str, list[TaskEntry]] = defaultdict(list)
    processed: set[int] = set()  # Track processed task indices

    for i, task in enumerate(all_tasks):
        if i in processed:
            continue

        # Find all similar tasks
        similar_tasks = [task]
        processed.add(i)

        for j, other in enumerate(all_tasks):
            if j in processed:
                continue
            if _similarity(task.normalized, other.normalized) >= DUPLICATE_SIMILARITY_THRESHOLD:
                similar_tasks.append(other)
                processed.add(j)

        if len(similar_tasks) > 1:
            # Use first task's normalized text as the key
            key = task.normalized[:50]  # Truncate for readability
            groups[key] = similar_tasks

    # Convert to DuplicateTaskGroup and create findings
    duplicate_groups: list[DuplicateTaskGroup] = []
    findings: list[AuditFinding] = []

    for normalized_text, entries in groups.items():
        duplicate_groups.append(
            DuplicateTaskGroup(normalized_text=normalized_text, entries=entries)
        )

        # Create finding
        locations = ", ".join(f"{e.file}:{e.line}" for e in entries)
        findings.append(
            AuditFinding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.DUPLICATE_TASK,
                message=f"Duplicate task found in {len(entries)} locations: '{entries[0].text[:60]}...'",
                file=entries[0].file,
                line=entries[0].line,
                code="CIHUB-AUDIT-DUPLICATE-TASK",
                suggestion=f"Consolidate to single canonical location. Found at: {locations}",
            )
        )

    return duplicate_groups, findings


def check_timestamp_freshness(
    doc_path: Path,
    warn_days: int = TIMESTAMP_WARN_DAYS,
    error_days: int = TIMESTAMP_ERROR_DAYS,
    repo_root: Path | None = None,
) -> list[AuditFinding]:
    """Validate timestamp headers are reasonably fresh.

    Part 13.T: Checks "Last Updated", "Last Verified", etc. headers
    and warns if they're stale.

    Args:
        doc_path: Path to the document to check
        warn_days: Days old before warning (default 7)
        error_days: Days old before error (default 30)
        repo_root: Optional repo root for computing relative paths

    Returns:
        List of findings for stale timestamps
    """
    if not doc_path.exists():
        return []

    findings: list[AuditFinding] = []
    content = doc_path.read_text(encoding="utf-8")
    # Use repo-relative path if repo_root provided
    rel_path = str(doc_path.relative_to(repo_root)) if repo_root else str(doc_path)
    today = date.today()

    for line_num, line in enumerate(content.splitlines(), 1):
        for pattern, header_type in TIMESTAMP_PATTERNS:
            match = re.search(pattern, line)
            if match:
                date_str = match.group(1)
                try:
                    header_date = date.fromisoformat(date_str)
                    days_old = (today - header_date).days

                    if header_date > today:
                        # Future date is always an error
                        findings.append(
                            AuditFinding(
                                severity=FindingSeverity.ERROR,
                                category=FindingCategory.TIMESTAMP,
                                message=f"Future date in {header_type}: {date_str}",
                                file=rel_path,
                                line=line_num,
                                code="CIHUB-AUDIT-FUTURE-DATE",
                                suggestion=f"Update {header_type} to today's date: {today.isoformat()}",
                            )
                        )
                    elif days_old > error_days:
                        findings.append(
                            AuditFinding(
                                severity=FindingSeverity.ERROR,
                                category=FindingCategory.TIMESTAMP,
                                message=f"{header_type} is {days_old} days old (>{error_days} threshold)",
                                file=rel_path,
                                line=line_num,
                                code="CIHUB-AUDIT-STALE-TIMESTAMP",
                                suggestion=f"Update {header_type} to today: {today.isoformat()}",
                            )
                        )
                    elif days_old > warn_days:
                        findings.append(
                            AuditFinding(
                                severity=FindingSeverity.WARNING,
                                category=FindingCategory.TIMESTAMP,
                                message=f"{header_type} is {days_old} days old (>{warn_days} threshold)",
                                file=rel_path,
                                line=line_num,
                                code="CIHUB-AUDIT-AGING-TIMESTAMP",
                                suggestion=f"Consider updating {header_type} if doc content changed",
                            )
                        )

                except ValueError:
                    # Invalid date format
                    findings.append(
                        AuditFinding(
                            severity=FindingSeverity.ERROR,
                            category=FindingCategory.TIMESTAMP,
                            message=f"Invalid date format in {header_type}: {date_str}",
                            file=rel_path,
                            line=line_num,
                            code="CIHUB-AUDIT-INVALID-DATE",
                            suggestion="Use ISO format: YYYY-MM-DD",
                        )
                    )

    return findings


def validate_timestamps(repo_root: Path) -> list[AuditFinding]:
    """Validate timestamps across all relevant docs.

    Scans development/ and active/ docs for timestamp freshness.
    Skips archive/ docs (historical).

    Args:
        repo_root: Repository root path

    Returns:
        List of findings for stale timestamps
    """
    findings: list[AuditFinding] = []

    # Scan development/ docs (except archive/)
    dev_dir = repo_root / "docs" / "development"
    if dev_dir.exists():
        for md_file in dev_dir.rglob("*.md"):
            # Skip archive - historical docs are expected to have old dates
            if "archive" in str(md_file):
                continue
            findings.extend(check_timestamp_freshness(md_file, repo_root=repo_root))

    return findings


def find_placeholders(repo_root: Path) -> list[AuditFinding]:
    """Detect hardcoded placeholders in docs.

    Part 13.V: Finds placeholder markers and hardcoded local paths.

    NOTE: GitHub username detection is disabled (too many false positives).
    We only scan for explicit placeholder markers (YOUR_*, CHANGE_ME, TODO:)
    and hardcoded local paths (/Users/..., /home/...).

    Args:
        repo_root: Repository root path

    Returns:
        List of findings for placeholder issues
    """
    findings: list[AuditFinding] = []

    # Only scan for high-confidence patterns (not GitHub usernames)
    # The github_username pattern has too many false positives
    scan_patterns = [
        (r"\b(YOUR_[A-Z_]+|CHANGE_ME|TODO:|FIXME:|XXX:)\b", "placeholder_marker"),
        (r"(/Users/[^/\s]+|/home/[^/\s]+|C:\\\\Users\\\\[^\\\\]+)", "local_path"),
    ]

    # Scan docs/ directory
    docs_dir = repo_root / "docs"
    if not docs_dir.exists():
        return findings

    for md_file in docs_dir.rglob("*.md"):
        # Skip archive - may have historical references
        if "archive" in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = str(md_file.relative_to(repo_root))

        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, placeholder_type in scan_patterns:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    value = match.group(1) if match.groups() else match.group(0)

                    findings.append(
                        AuditFinding(
                            severity=FindingSeverity.WARNING,
                            category=FindingCategory.PLACEHOLDER,
                            message=f"Potential placeholder detected ({placeholder_type}): {value}",
                            file=rel_path,
                            line=line_num,
                            code="CIHUB-AUDIT-PLACEHOLDER",
                            suggestion="Replace with generic value or ensure this is intentional",
                        )
                    )

    return findings


def validate_consistency(repo_root: Path) -> list[AuditFinding]:
    """Run all Part 13 consistency checks.

    Args:
        repo_root: Repository root path

    Returns:
        Combined findings from all consistency checks
    """
    findings: list[AuditFinding] = []

    # Part 13.S: Duplicate task detection
    _, duplicate_findings = find_duplicate_tasks(repo_root)
    findings.extend(duplicate_findings)

    # Part 13.T: Timestamp freshness
    findings.extend(validate_timestamps(repo_root))

    # Part 13.V: Placeholder detection
    findings.extend(find_placeholders(repo_root))

    return findings
