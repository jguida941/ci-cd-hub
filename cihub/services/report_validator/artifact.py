"""Artifact validation helpers for CI reports.

This module contains functions for validating the existence and content
of tool output artifacts (e.g., report files, coverage files).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def iter_existing_patterns(root: Path, patterns: Iterable[str]) -> bool:
    """Check if any files matching patterns exist in root directory.

    Args:
        root: Directory to search in.
        patterns: Glob patterns to check (e.g., "*.json", "coverage.xml").

    Returns:
        True if any pattern matches at least one file, False otherwise.
    """
    for pattern in patterns:
        if list(root.glob(pattern)):
            return True
    return False


def check_artifacts_non_empty(root: Path, patterns: Iterable[str]) -> tuple[bool, list[str]]:
    """Check if artifacts exist AND are non-empty.

    Args:
        root: Directory to search in.
        patterns: Glob patterns to check.

    Returns:
        Tuple of (all_non_empty, list of empty file paths).
        - all_non_empty is True if at least one file was found and all are non-empty.
        - The list contains paths of empty or unreadable files.
    """
    empty_files: list[str] = []
    found_any = False

    for pattern in patterns:
        for path in root.glob(pattern):
            found_any = True
            if path.is_file():
                try:
                    size = path.stat().st_size
                    if size == 0:
                        empty_files.append(str(path))
                except OSError:
                    empty_files.append(f"{path} (unreadable)")

    return found_any and len(empty_files) == 0, empty_files
