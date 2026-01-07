"""Git operations for docs stale detection.

This module handles all git interactions needed for baseline comparison:
1. Checking if a path is in a git repo
2. Resolving git references
3. Getting changed/deleted/renamed files
4. Retrieving file content at specific refs
5. Comparing symbols between base and head
"""

from __future__ import annotations

from pathlib import Path

from cihub.utils.exec_utils import (
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)

from .extraction import extract_python_symbols, extract_symbols_from_file


def _run_git(args: list[str], cwd: Path, timeout: int = TIMEOUT_QUICK) -> tuple[int, str, str]:
    """Run a git command and return (exit_code, stdout, stderr).

    Args:
        args: Git command arguments (without 'git' prefix)
        cwd: Working directory for the command
        timeout: Maximum seconds to wait

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = safe_run(["git", *args], cwd=cwd, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except CommandTimeoutError:
        return -1, "", "Command timed out"
    except CommandNotFoundError:
        return -1, "", "git not found"


def is_git_repo(path: Path) -> bool:
    """Check if path is inside a git repository.

    Args:
        path: Path to check

    Returns:
        True if path is in a git repository
    """
    code, _, _ = _run_git(["rev-parse", "--git-dir"], path)
    return code == 0


def resolve_git_ref(ref: str, cwd: Path) -> str | None:
    """Resolve a git reference to a commit hash.

    Args:
        ref: Git reference (e.g., "HEAD~10", "main", "abc123")
        cwd: Working directory

    Returns:
        Commit hash string if valid, None if invalid
    """
    code, stdout, _ = _run_git(["rev-parse", ref], cwd)
    if code == 0:
        return stdout.strip()
    return None


def get_merge_base(ref1: str, ref2: str, cwd: Path) -> str | None:
    """Get the merge base of two refs.

    Useful for handling revision ranges like "origin/main..HEAD".

    Args:
        ref1: First reference
        ref2: Second reference
        cwd: Working directory

    Returns:
        Merge base commit hash, or None if not found
    """
    code, stdout, _ = _run_git(["merge-base", ref1, ref2], cwd)
    if code == 0:
        return stdout.strip()
    return None


def get_changed_files(since: str, cwd: Path) -> list[str]:
    """Get list of Python files changed since a ref.

    Args:
        since: Git reference to compare against
        cwd: Working directory

    Returns:
        List of changed Python file paths (relative to cwd)
    """
    code, stdout, _ = _run_git(
        ["diff", "--name-only", since, "--", "*.py"],
        cwd,
    )
    if code != 0:
        return []
    return [f for f in stdout.strip().split("\n") if f]


def get_file_status(since: str, cwd: Path) -> dict[str, str]:
    """Get file status (Added/Deleted/Modified/Renamed) since a ref.

    Uses git diff --name-status to detect file changes including renames.

    Args:
        since: Git reference to compare against
        cwd: Working directory

    Returns:
        Dict mapping file path to status (A/D/M/R)
    """
    code, stdout, _ = _run_git(
        ["diff", "--name-status", "--find-renames", since],
        cwd,
    )
    if code != 0:
        return {}

    status: dict[str, str] = {}
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            stat = parts[0][0]  # First char of status (A, D, M, R)
            path = parts[1]
            status[path] = stat
            # Handle renames: "R100\told_path\tnew_path"
            if stat == "R" and len(parts) >= 3:
                old_path = parts[1]
                new_path = parts[2]
                status[old_path] = "R"
                status[new_path] = "A"

    return status


def get_file_at_ref(ref: str, file_path: str, cwd: Path) -> str | None:
    """Get file content at a specific git ref.

    Uses `git show ref:path` to retrieve historical file content.

    Args:
        ref: Git reference (commit hash, branch, tag, etc.)
        file_path: Path to the file (relative to repo root)
        cwd: Working directory

    Returns:
        File content as string, or None if file doesn't exist at ref
    """
    code, stdout, _ = _run_git(["show", f"{ref}:{file_path}"], cwd)
    if code == 0:
        return stdout
    return None


def get_symbols_at_ref(ref: str, file_path: str, cwd: Path) -> set[str]:
    """Get symbol names from a file at a specific git ref.

    Retrieves the file content at the given ref and parses it with AST
    to extract symbol names.

    Args:
        ref: Git reference
        file_path: Path to the Python file
        cwd: Working directory

    Returns:
        Set of symbol names found in the file
    """
    content = get_file_at_ref(ref, file_path, cwd)
    if content is None:
        return set()
    symbols = extract_python_symbols(content, file_path)
    return {s.name for s in symbols}


def _similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings using SequenceMatcher.

    Uses difflib.SequenceMatcher which properly handles insertions, deletions,
    and substitutions - unlike naive position-by-position comparison.

    For example:
        _get_repo_name vs get_repo_name → 0.96 (very similar)
        _get_repo_name vs name → 0.36 (not similar)

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity ratio from 0.0 to 1.0
    """
    if not s1 or not s2:
        return 0.0

    from difflib import SequenceMatcher

    return SequenceMatcher(None, s1, s2).ratio()


def compare_symbols(
    since: str,
    code_path: Path,
    cwd: Path,
) -> tuple[set[str], set[str], list[tuple[str, str]]]:
    """Compare symbols between base and head.

    This is the core baseline comparison function. It:
    1. Gets all Python files that changed since the base ref
    2. For each file, compares symbols at base vs head
    3. Computes removed, added, and likely renamed symbols

    Args:
        since: Git reference for the base
        code_path: Path to code directory (relative to cwd)
        cwd: Working directory

    Returns:
        Tuple of:
        - removed: Symbols that existed at base but not at head
        - added: Symbols that exist at head but not at base
        - renamed: List of (old_name, new_name) for likely renames
    """
    changed_files = get_changed_files(since, cwd)

    base_symbols: set[str] = set()
    head_symbols: set[str] = set()

    for file_path in changed_files:
        # Get symbols at base
        base = get_symbols_at_ref(since, file_path, cwd)
        base_symbols.update(base)

        # Get symbols at head (current working tree)
        full_path = cwd / file_path
        if full_path.exists():
            head = {s.name for s in extract_symbols_from_file(full_path)}
            head_symbols.update(head)

    removed = base_symbols - head_symbols
    added = head_symbols - base_symbols

    # Try to detect renames using similarity scoring
    # A rename is when a removed symbol has a highly similar added symbol
    # We find the BEST match for each removed symbol, not the first match
    renamed: list[tuple[str, str]] = []
    used_added: set[str] = set()

    # Minimum similarity threshold for considering a rename
    # 0.7 catches most renames while avoiding false positives
    MIN_SIMILARITY = 0.7

    for old in list(removed):
        best_match: str | None = None
        best_score = 0.0

        for new in added:
            if new in used_added:
                continue

            # Use proper string similarity that handles insertions/deletions
            score = _similarity_ratio(old, new)

            if score > best_score and score >= MIN_SIMILARITY:
                best_score = score
                best_match = new

        if best_match:
            renamed.append((old, best_match))
            removed.discard(old)
            used_added.add(best_match)

    # Remove used symbols from added set
    added -= used_added

    return removed, added, renamed


def get_renamed_files(since: str, cwd: Path) -> list[tuple[str, str]]:
    """Get list of renamed files since a ref.

    Args:
        since: Git reference to compare against
        cwd: Working directory

    Returns:
        List of (old_path, new_path) tuples for renamed files
    """
    code, stdout, _ = _run_git(
        ["diff", "--name-status", "--find-renames", since],
        cwd,
    )
    if code != 0:
        return []

    renamed: list[tuple[str, str]] = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].startswith("R"):
            old_path = parts[1]
            new_path = parts[2]
            renamed.append((old_path, new_path))

    return renamed
