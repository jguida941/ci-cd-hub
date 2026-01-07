"""Stale reference detection logic.

This module correlates documentation references with code changes to
find stale references. It implements the core "staleness" definition:

A doc reference is stale if it points to something that was REMOVED or RENAMED.
Added symbols are NEVER flagged as stale (this is the key insight from Part 11).
"""

from __future__ import annotations

from .types import (
    KIND_FILE_PATH,
    REASON_DELETED_FILE,
    REASON_REMOVED,
    REASON_RENAMED,
    DocReference,
    StaleReference,
)


def find_stale_references(
    doc_refs: list[DocReference],
    removed_symbols: set[str],
    renamed_symbols: list[tuple[str, str]],
    deleted_files: list[str],
    renamed_files: list[tuple[str, str]],
) -> list[StaleReference]:
    """Find documentation references that are stale.

    This is the core correlation function. It matches doc references against:
    1. Removed symbols - symbols that existed at base but not at head
    2. Renamed symbols - symbols that changed names (detected heuristically)
    3. Deleted files - files that were deleted
    4. Renamed files - files that were renamed

    IMPORTANT: Only flags REMOVED/RENAMED symbols, never ADDED.
    This prevents false positives when new features are added.

    Args:
        doc_refs: All references extracted from documentation
        removed_symbols: Symbol names that were removed from codebase
        renamed_symbols: List of (old_name, new_name) for renamed symbols
        deleted_files: File paths that were deleted
        renamed_files: List of (old_path, new_path) for renamed files

    Returns:
        List of StaleReference objects for each stale doc reference
    """
    stale: list[StaleReference] = []
    rename_map = dict(renamed_symbols)
    file_rename_map = dict(renamed_files)

    for ref in doc_refs:
        token = ref.reference

        # Check if it matches a removed symbol
        if token in removed_symbols:
            suggestion = "Symbol was removed from codebase"
            # Check if there's a likely rename - provide better suggestion
            if token in rename_map:
                suggestion = f"Consider updating to `{rename_map[token]}`"
            stale.append(
                StaleReference(
                    doc_file=ref.file,
                    doc_line=ref.line,
                    reference=token,
                    reason=REASON_REMOVED,
                    suggestion=suggestion,
                    context=ref.context,
                )
            )
            continue

        # Check if it matches a renamed symbol
        if token in rename_map:
            stale.append(
                StaleReference(
                    doc_file=ref.file,
                    doc_line=ref.line,
                    reference=token,
                    reason=REASON_RENAMED,
                    suggestion=f"Update to `{rename_map[token]}`",
                    context=ref.context,
                )
            )
            continue

        # Check if it references a deleted file
        if ref.kind == KIND_FILE_PATH:
            if token in deleted_files:
                suggestion = "File was deleted"
                if token in file_rename_map:
                    suggestion = f"File renamed to `{file_rename_map[token]}`"
                stale.append(
                    StaleReference(
                        doc_file=ref.file,
                        doc_line=ref.line,
                        reference=token,
                        reason=REASON_DELETED_FILE,
                        suggestion=suggestion,
                        context=ref.context,
                    )
                )

    return stale


def group_stale_by_file(stale_refs: list[StaleReference]) -> dict[str, list[StaleReference]]:
    """Group stale references by their documentation file.

    Useful for output formatting and per-file AI prompts.

    Args:
        stale_refs: List of stale references

    Returns:
        Dict mapping doc file path to list of stale references in that file
    """
    by_file: dict[str, list[StaleReference]] = {}
    for ref in stale_refs:
        by_file.setdefault(ref.doc_file, []).append(ref)
    return by_file


def filter_by_reason(
    stale_refs: list[StaleReference],
    reasons: set[str],
) -> list[StaleReference]:
    """Filter stale references by reason.

    Args:
        stale_refs: List of stale references
        reasons: Set of reasons to include (e.g., {"removed", "renamed"})

    Returns:
        Filtered list of stale references
    """
    return [ref for ref in stale_refs if ref.reason in reasons]
