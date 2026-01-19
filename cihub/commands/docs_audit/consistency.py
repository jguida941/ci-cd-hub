"""Cross-document consistency validation.

This module implements Part 13 from DOC_AUTOMATION_AUDIT.md:
- R. Metrics/Counts Drift Detection
- S. Duplicate Task Detection across planning docs
- T. Timestamp Freshness Validation
- U. Checklist vs Reality Sync
- V. Hardcoded Placeholder Detection
- W. Cross-Doc Consistency (README.md ↔ active/)
- X. CHANGELOG Format Validation
- Guide command validation (docs/guides/)
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from .guides import validate_guide_commands
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
        duplicate_groups.append(DuplicateTaskGroup(normalized_text=normalized_text, entries=entries))

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


# =============================================================================
# Part 13.R: Metrics/Counts Drift Detection
# =============================================================================

# Patterns to detect numeric claims in docs (current state assertions)
# These look for phrases like "X tests", "over X commands", etc.
METRICS_PATTERNS = [
    (r"(\d+)\s*(?:CLI\s+)?commands?", "command_count"),
    (r"(\d+)\s*tests?", "test_count"),
    (r"(\d+)\s*ADRs?", "adr_count"),
]

# Keywords that indicate historical/delta context (not current-state claims)
# Be specific with transition words to avoid false negatives
METRICS_DELTA_KEYWORDS = frozenset(
    [
        "added",
        "add",
        "new",
        "created",
        "wrote",
        "introduced",
        "removed",
        "deleted",
        "fixed",
        "updated",
        "changed",
        "migrated",
        "+",
        "→",
        "->",
        # Transition patterns (more specific than just "from"/"to")
        "went from",
        "grew from",
        "increased from",
        "decreased from",
        "changed from",
        "moved from",
        "upgraded from",
    ]
)

# Keywords that indicate module/feature-specific context (not project-wide claims)
METRICS_LOCAL_CONTEXT_KEYWORDS = frozenset(
    [
        "in test",
        "for test",
        "tests for",
        "tests in",
        "test file",
        "in module",
        "for module",
        "module has",
        "modules,",
        "modular",
        "modularized",
        "package",
        "including",
        "of which",
        "across",
        "test_",
        ".py",  # File references
        "parameterized",
        "hypothesis",
        "property-based",  # Test type descriptors
        "cihub docs",
        "cihub hub-ci",  # Module-specific command references
    ]
)

# Drift thresholds
METRICS_WARN_THRESHOLD = 0.10  # 10% drift = warning
METRICS_ERROR_THRESHOLD = 0.50  # 50% drift = error


def _count_cli_commands(repo_root: Path) -> int:
    """Count CLI commands from argparse structure.

    Counts add_parser() calls in cli_parsers/*.py to get accurate command count.
    Also counts variable-based add_parser calls via helper function invocations.
    """
    cli_parsers_dir = repo_root / "cihub" / "cli_parsers"
    if not cli_parsers_dir.exists():
        return 0

    count = 0
    for py_file in cli_parsers_dir.glob("*.py"):
        # Skip internal modules
        if py_file.name.startswith("_") or py_file.name in ("types.py", "builder.py"):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")

            # Pattern 1: Direct add_parser("command_name", ...) calls
            parser_calls = re.findall(r'\.add_parser\(\s*["\']([^"\']+)["\']', content)
            for cmd_name in parser_calls:
                # Skip template/example commands
                if cmd_name not in ("my-command", "example"):
                    count += 1

            # Pattern 2: Helper function calls that add parsers with variable names
            # e.g., _add_preflight_parser(..., "preflight", "Check env")
            # Look for function calls with string command names as arguments
            helper_calls = re.findall(r'_add_\w+_parser\([^)]*,\s*["\']([^"\']+)["\']', content)
            count += len(helper_calls)

        except (OSError, UnicodeDecodeError):
            continue

    return count


def _count_pytest_tests(repo_root: Path) -> int:
    """Count pytest tests from test files.

    Returns approximate count by counting test_ functions.
    """
    tests_dir = repo_root / "tests"
    if not tests_dir.exists():
        return 0

    count = 0
    for test_file in tests_dir.rglob("test_*.py"):
        try:
            content = test_file.read_text(encoding="utf-8")
            # Count def test_ functions
            count += len(re.findall(r"^\s*def test_", content, re.MULTILINE))
            # Count @pytest.mark.parametrize multipliers (rough estimate)
            params = re.findall(r"@pytest\.mark\.parametrize\([^,]+,\s*\[([^\]]+)\]", content)
            for param in params:
                # Count items in parameter list
                items = param.count(",") + 1
                if items > 1:
                    count += items - 1  # Add extra test cases
        except (OSError, UnicodeDecodeError):
            continue

    return count


def _count_adrs(repo_root: Path) -> int:
    """Count ADR files."""
    adr_dir = repo_root / "docs" / "adr"
    if not adr_dir.exists():
        return 0
    return len(list(adr_dir.glob("0*.md")))


def get_actual_metrics(repo_root: Path) -> dict[str, int]:
    """Get current metrics from authoritative sources.

    Args:
        repo_root: Repository root path

    Returns:
        Dict mapping metric names to actual values
    """
    return {
        "command_count": _count_cli_commands(repo_root),
        "test_count": _count_pytest_tests(repo_root),
        "adr_count": _count_adrs(repo_root),
    }


def _is_delta_context(line: str) -> bool:
    """Check if line contains delta/historical context keywords.

    Args:
        line: Line of text to check

    Returns:
        True if line appears to be describing a change (not current state)
    """
    line_lower = line.lower()
    return any(kw in line_lower for kw in METRICS_DELTA_KEYWORDS)


def _is_local_context(line: str) -> bool:
    """Check if line contains module/feature-specific context.

    Args:
        line: Line of text to check

    Returns:
        True if line appears to describe a specific module, not project-wide counts
    """
    line_lower = line.lower()
    return any(kw in line_lower for kw in METRICS_LOCAL_CONTEXT_KEYWORDS)


def find_stale_metrics(repo_root: Path) -> list[AuditFinding]:
    """Find numeric claims in docs that don't match reality (Part 13.R).

    Scans docs for current-state numeric claims like "we have 80 tests"
    and compares to actual counts. Skips historical/delta references
    like "added 22 tests" in changelogs.

    Args:
        repo_root: Repository root path

    Returns:
        List of findings for stale metrics
    """
    findings: list[AuditFinding] = []
    actual = get_actual_metrics(repo_root)

    # Only scan docs that make current-state claims (NOT changelog - that's historical)
    docs_to_scan = [
        "docs/development/DEVELOPMENT.md",
        "docs/development/MASTER_PLAN.md",
        "CLAUDE.md",
        # Note: CHANGELOG.md is excluded - it contains historical deltas, not current claims
    ]

    for doc_rel_path in docs_to_scan:
        doc_path = repo_root / doc_rel_path
        if not doc_path.exists():
            continue

        try:
            content = doc_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for line_num, line in enumerate(content.split("\n"), 1):
            # Skip lines with delta/historical context
            if _is_delta_context(line):
                continue

            # Skip lines describing module-specific counts (not project-wide)
            if _is_local_context(line):
                continue

            for pattern, metric_key in METRICS_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    claimed = int(match.group(1))
                    actual_val = actual.get(metric_key, 0)

                    # Skip if actual is 0 (can't calculate drift)
                    if actual_val == 0:
                        continue

                    # Skip small numbers (likely not aggregate counts)
                    if claimed < 10:
                        continue

                    # Calculate drift
                    drift = abs(claimed - actual_val) / actual_val

                    if drift > METRICS_ERROR_THRESHOLD:
                        findings.append(
                            AuditFinding(
                                severity=FindingSeverity.ERROR,
                                category=FindingCategory.SYNC,
                                message=(
                                    f"Stale metric: claims {claimed} {metric_key.replace('_', ' ')}, "
                                    f"actual is {actual_val} ({drift:.0%} drift)"
                                ),
                                file=doc_rel_path,
                                line=line_num,
                                code="CIHUB-METRICS-DRIFT-ERROR",
                                suggestion=f"Update to reflect actual count: {actual_val}",
                            )
                        )
                    elif drift > METRICS_WARN_THRESHOLD:
                        findings.append(
                            AuditFinding(
                                severity=FindingSeverity.WARNING,
                                category=FindingCategory.SYNC,
                                message=(
                                    f"Stale metric: claims {claimed} {metric_key.replace('_', ' ')}, "
                                    f"actual is {actual_val} ({drift:.0%} drift)"
                                ),
                                file=doc_rel_path,
                                line=line_num,
                                code="CIHUB-METRICS-DRIFT-WARN",
                                suggestion=f"Update to reflect actual count: {actual_val}",
                            )
                        )

    return findings


# =============================================================================
# Part 13.U: Checklist vs Reality Sync
# =============================================================================

# Map task patterns to verification checks
# Key: lowercase pattern to match in task text
# Value: callable that returns True if the work is done
CHECKLIST_VERIFICATIONS: dict[str, tuple[str, Callable[[], bool]]] = {}


def _register_checklist_verifications(repo_root: Path) -> dict[str, tuple[str, Callable[[], bool]]]:
    """Build checklist verification map based on repo structure.

    Returns dict mapping task patterns to (description, verifier) tuples.
    """
    return {
        "extract language strategies": (
            "cihub/core/languages/ directory exists",
            lambda: (repo_root / "cihub/core/languages").is_dir(),
        ),
        "implement cihub docs stale": (
            "'stale' subcommand exists in docs CLI",
            lambda: (repo_root / "cihub/commands/docs_stale").is_dir(),
        ),
        "implement cihub docs audit": (
            "'audit' subcommand exists in docs CLI",
            lambda: (repo_root / "cihub/commands/docs_audit").is_dir(),
        ),
        "gatespec registry": (
            "gate_specs.py exists",
            lambda: (repo_root / "cihub/core/gate_specs.py").is_file(),
        ),
        "tool adapter": (
            "ToolAdapter in registry.py",
            lambda: _file_contains(repo_root / "cihub/tools/registry.py", "class ToolAdapter"),
        ),
        "commandresult migration": (
            "CommandResult type exists",
            lambda: (repo_root / "cihub/types.py").is_file()
            and _file_contains(repo_root / "cihub/types.py", "class CommandResult"),
        ),
        "github context": (
            "GitHubContext helper exists",
            lambda: (
                _file_contains(repo_root / "cihub/utils/github_context.py", "class GitHubContext")
                if (repo_root / "cihub/utils/github_context.py").is_file()
                else False
            ),
        ),
    }


def _file_contains(path: Path, pattern: str) -> bool:
    """Check if a file contains a pattern."""
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
        return pattern in content
    except (OSError, UnicodeDecodeError):
        return False


def verify_checklist_reality(repo_root: Path) -> list[AuditFinding]:
    """Check if unchecked items in design docs have completed implementations.

    Part 13.U: Finds `[ ]` items that actually correspond to completed work.

    Args:
        repo_root: Repository root path

    Returns:
        List of findings for mismatched checklist items
    """
    findings: list[AuditFinding] = []
    verifications = _register_checklist_verifications(repo_root)

    # Only check active design docs
    active_docs_dir = repo_root / "docs" / "development" / "active"
    if not active_docs_dir.exists():
        return findings

    for doc_path in active_docs_dir.glob("*.md"):
        try:
            content = doc_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        doc_rel_path = str(doc_path.relative_to(repo_root))

        for line_num, line in enumerate(content.split("\n"), 1):
            # Match unchecked items: - [ ] or * [ ]
            match = re.match(r"^[-*]\s*\[\s*\]\s*(.+)$", line.strip())
            if not match:
                continue

            task_text = match.group(1)
            task_lower = task_text.lower()

            # Check against verification patterns
            for pattern, (description, verifier) in verifications.items():
                if pattern in task_lower:
                    try:
                        if verifier():
                            findings.append(
                                AuditFinding(
                                    severity=FindingSeverity.WARNING,
                                    category=FindingCategory.SYNC,
                                    message=(
                                        f"Unchecked item appears complete: '{task_text[:60]}...'"
                                        if len(task_text) > 60
                                        else f"Unchecked item appears complete: '{task_text}'"
                                    ),
                                    file=doc_rel_path,
                                    line=line_num,
                                    code="CIHUB-CHECKLIST-REALITY",
                                    suggestion=f"Mark as [x] - {description}",
                                )
                            )
                    except Exception:  # noqa: S110, BLE001
                        # Skip verification if it fails (intentional)
                        pass
                    break  # Only report once per task

    return findings


# =============================================================================
# Part 13.X: CHANGELOG Format Validation
# =============================================================================


def validate_changelog(repo_root: Path) -> list[AuditFinding]:
    """Validate CHANGELOG.md format and ordering (Part 13.X).

    Checks:
    - Date headers are in reverse chronological order (most recent first)
    - No duplicate date headers
    - Section separators between entries

    Args:
        repo_root: Repository root path

    Returns:
        List of findings for changelog issues
    """
    findings: list[AuditFinding] = []

    # Try multiple common changelog locations
    changelog_paths = [
        repo_root / "docs" / "development" / "CHANGELOG.md",
        repo_root / "CHANGELOG.md",
    ]

    changelog_path = None
    for path in changelog_paths:
        if path.exists():
            changelog_path = path
            break

    if changelog_path is None:
        return findings

    try:
        content = changelog_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return findings

    rel_path = str(changelog_path.relative_to(repo_root))
    lines = content.split("\n")

    # Pattern to match date headers: ## YYYY-MM-DD
    date_pattern = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})")

    # Extract all date headers with line numbers
    date_entries: list[tuple[int, str]] = []
    for line_num, line in enumerate(lines, 1):
        match = date_pattern.match(line)
        if match:
            date_entries.append((line_num, match.group(1)))

    if not date_entries:
        return findings

    # Check chronological order (most recent first)
    for i in range(len(date_entries) - 1):
        curr_line, curr_date = date_entries[i]
        next_line, next_date = date_entries[i + 1]

        if curr_date < next_date:
            findings.append(
                AuditFinding(
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.SYNC,
                    message=(
                        f"CHANGELOG entries out of order: {curr_date} (line {curr_line}) "
                        f"comes before {next_date} (line {next_line})"
                    ),
                    file=rel_path,
                    line=curr_line,
                    code="CIHUB-CHANGELOG-ORDER",
                    suggestion="Reorder entries so most recent dates are first",
                )
            )

    # Check for duplicate dates (multiple H2 headers with same date)
    seen_dates: dict[str, int] = {}
    for line_num, date_str in date_entries:
        if date_str in seen_dates:
            findings.append(
                AuditFinding(
                    severity=FindingSeverity.INFO,
                    category=FindingCategory.SYNC,
                    message=f"Multiple CHANGELOG entries for {date_str} (also on line {seen_dates[date_str]})",
                    file=rel_path,
                    line=line_num,
                    code="CIHUB-CHANGELOG-DUPLICATE-DATE",
                    suggestion="Consider consolidating entries for the same date",
                )
            )
        else:
            seen_dates[date_str] = line_num

    return findings


# =============================================================================
# Part 13.W: Cross-Document Consistency Validation
# =============================================================================


def parse_readme_active_docs(repo_root: Path) -> list[str]:
    """Parse docs/README.md to extract Active Design Docs list.

    Looks for the "Active Design Docs" section and extracts file references.

    Args:
        repo_root: Repository root path

    Returns:
        List of doc filenames (relative to active/ dir) mentioned in README.md
    """
    readme_path = repo_root / "docs" / "README.md"
    if not readme_path.exists():
        return []

    content = readme_path.read_text(encoding="utf-8")
    active_docs: list[str] = []

    # Find the "Active Design Docs" section
    in_active_section = False
    for line in content.split("\n"):
        # Start of section
        if "**Active Design Docs**" in line or "Active Design Docs" in line and "(`" in line:
            in_active_section = True
            continue

        # End of section (next heading or empty line after list)
        if in_active_section:
            if line.startswith("**") and "Active Design Docs" not in line:
                break
            if line.startswith("---"):
                break

            # Extract markdown link references: [NAME.md](development/active/NAME.md)
            # or [NAME.md](path/to/NAME.md) patterns
            matches = re.findall(r"\[([A-Za-z0-9_.-]+\.md)\]\(", line)
            for match in matches:
                active_docs.append(match)

    return active_docs


def check_docs_index_consistency(repo_root: Path) -> list[AuditFinding]:
    """Check docs/README.md Active Design Docs matches actual files (Part 13.W).

    Args:
        repo_root: Repository root path

    Returns:
        List of findings for inconsistencies
    """
    findings: list[AuditFinding] = []

    # Get actual files in active/
    active_dir = repo_root / "docs" / "development" / "active"
    actual_files: set[str] = set()
    if active_dir.exists():
        for md_file in active_dir.glob("*.md"):
            actual_files.add(md_file.name)

    # Get files listed in README.md
    readme_files = set(parse_readme_active_docs(repo_root))

    # Find files missing from README.md
    missing_from_readme = actual_files - readme_files
    for filename in sorted(missing_from_readme):
        findings.append(
            AuditFinding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.SYNC,
                message=f"Active doc '{filename}' not listed in docs/README.md",
                file=f"docs/development/active/{filename}",
                line=0,
                code="CIHUB-README-MISSING-DOC",
                suggestion="Add to 'Active Design Docs' section in docs/README.md",
            )
        )

    # Find files listed in README.md that don't exist
    stale_in_readme = readme_files - actual_files
    for filename in sorted(stale_in_readme):
        findings.append(
            AuditFinding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.SYNC,
                message=f"docs/README.md lists '{filename}' but file doesn't exist in active/",
                file="docs/README.md",
                line=0,
                code="CIHUB-README-STALE-DOC",
                suggestion=f"Remove '{filename}' from 'Active Design Docs' or create the file",
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
    # TODO: Re-enable once duplicate tasks are cleaned up (see BACKLOG.md)
    # _, duplicate_findings = find_duplicate_tasks(repo_root)
    # findings.extend(duplicate_findings)

    # Part 13.T: Timestamp freshness
    findings.extend(validate_timestamps(repo_root))

    # Part 13.V: Placeholder detection
    findings.extend(find_placeholders(repo_root))

    # Part 13.R: Metrics drift detection
    findings.extend(find_stale_metrics(repo_root))

    # Part 13.U: Checklist vs reality sync
    findings.extend(verify_checklist_reality(repo_root))

    # Part 13.W: Cross-doc consistency (README.md ↔ active/)
    findings.extend(check_docs_index_consistency(repo_root))

    # Guide command validation (docs/guides/)
    findings.extend(validate_guide_commands(repo_root))

    # Part 13.X: CHANGELOG format validation
    findings.extend(validate_changelog(repo_root))

    return findings
