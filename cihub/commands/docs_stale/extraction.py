"""Symbol and reference extraction for docs stale detection.

This module handles:
1. Python symbol extraction via AST parsing (functions, classes, constants)
2. Markdown reference extraction (backticks, CLI commands, file paths, etc.)
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .types import (
    FALSE_POSITIVE_TOKENS,
    KIND_BACKTICK,
    KIND_CLI_COMMAND,
    KIND_CLI_FLAG,
    KIND_CONFIG_KEY,
    KIND_ENV_VAR,
    KIND_FILE_PATH,
    PARSED_FENCE_TYPES,
    SKIPPED_FENCE_TYPES,
    CodeSymbol,
    DocReference,
)

# =============================================================================
# Python Symbol Extraction (AST)
# =============================================================================


def extract_python_symbols(content: str, file_path: str = "<unknown>") -> list[CodeSymbol]:
    """Extract functions, classes, and constants from Python source.

    Uses Python's AST module to reliably parse source code and extract
    named definitions. This is more robust than regex-based approaches.

    Args:
        content: Python source code as a string
        file_path: Path for error reporting and symbol file attribution

    Returns:
        List of CodeSymbol objects representing all found symbols
    """
    symbols: list[CodeSymbol] = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Gracefully handle unparseable Python (e.g., syntax errors in old commits)
        return symbols

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            symbols.append(
                CodeSymbol(
                    name=node.name,
                    kind="function",
                    file=file_path,
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.AsyncFunctionDef):
            symbols.append(
                CodeSymbol(
                    name=node.name,
                    kind="async_function",
                    file=file_path,
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                CodeSymbol(
                    name=node.name,
                    kind="class",
                    file=file_path,
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.Assign):
            # Check for module-level constants (UPPER_CASE names)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    symbols.append(
                        CodeSymbol(
                            name=target.id,
                            kind="constant",
                            file=file_path,
                            line=node.lineno,
                        )
                    )

    return symbols


def extract_symbols_from_file(file_path: Path) -> list[CodeSymbol]:
    """Extract symbols from a Python file on disk.

    Args:
        file_path: Path to the Python file

    Returns:
        List of CodeSymbol objects, empty list if file can't be read/parsed
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        return extract_python_symbols(content, str(file_path))
    except (OSError, UnicodeDecodeError):
        return []


# =============================================================================
# Markdown Reference Extraction
# =============================================================================


def _parse_fenced_blocks(content: str) -> list[tuple[str, str, int, int]]:
    """Parse fenced code blocks from markdown content.

    Extracts all fenced code blocks (``` or ~~~) with their language
    tag and content. This is used to:
    1. Skip illustrative code examples (python, json, etc.)
    2. Parse CLI examples (bash, shell, etc.) for command references

    Args:
        content: Markdown content as a string

    Returns:
        List of (language, block_content, start_line, end_line) tuples
    """
    blocks: list[tuple[str, str, int, int]] = []
    lines = content.splitlines()
    in_block = False
    block_lang = ""
    block_content: list[str] = []
    block_start = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not in_block and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_block = True
            # Extract language from fence: ```python -> "python"
            block_lang = stripped[3:].strip().split()[0] if len(stripped) > 3 else ""
            block_start = i
            block_content = []
        elif in_block and (stripped == "```" or stripped == "~~~"):
            blocks.append((block_lang.lower(), "\n".join(block_content), block_start, i))
            in_block = False
            block_lang = ""
            block_content = []
        elif in_block:
            block_content.append(line)

    return blocks


def _is_false_positive(token: str) -> bool:
    """Check if a token is a common false positive.

    Filters out tokens that appear in backticks but aren't actual
    code symbols (e.g., "true", "http", single letters).

    Args:
        token: The extracted token to check

    Returns:
        True if the token should be skipped as a false positive
    """
    lower = token.lower()
    if lower in FALSE_POSITIVE_TOKENS:
        return True
    # Skip very short tokens (likely not meaningful symbols)
    if len(token) <= 2:
        return True
    # Skip file extensions alone
    if token.startswith("."):
        return True
    # Skip URLs
    if token.startswith("http://") or token.startswith("https://"):
        return True
    return False


def _get_context(line_num: int, lines: list[str], window: int = 1) -> str:
    """Get context around a line for AI output.

    Args:
        line_num: 1-based line number
        lines: All lines in the document
        window: Number of lines before and after to include

    Returns:
        Context string with surrounding lines
    """
    start = max(0, line_num - 1 - window)
    end = min(len(lines), line_num + window)
    return "\n".join(lines[start:end])


def _classify_reference(token: str) -> str:
    """Classify a backtick reference into a kind.

    Determines the type of reference based on its content pattern.

    Args:
        token: The backtick-enclosed token

    Returns:
        One of the KIND_* constants
    """
    if token.startswith("cihub "):
        return KIND_CLI_COMMAND
    if token.startswith("--"):
        return KIND_CLI_FLAG
    if "/" in token and token.endswith(".py"):
        return KIND_FILE_PATH
    if "." in token and token[0].islower():
        return KIND_CONFIG_KEY
    if token.isupper() and "_" in token:
        return KIND_ENV_VAR
    return KIND_BACKTICK


def extract_doc_references(
    content: str,
    file_path: str = "<unknown>",
    skip_fences: bool = False,
) -> list[DocReference]:
    """Extract code references from markdown content.

    Extracts various types of code references:
    - Backtick references (`symbol_name`)
    - CLI commands (`cihub ...`)
    - CLI flags (`--flag-name`)
    - File paths (`cihub/commands/...`)
    - Config keys (`repo.owner`, `python.pytest.enabled`)
    - Environment variables (`CIHUB_*`, `CI_HUB_*`)

    Args:
        content: Markdown content as a string
        file_path: Path for reporting
        skip_fences: If True, don't parse fenced blocks at all

    Returns:
        List of DocReference objects (deduplicated by reference+line)
    """
    refs: list[DocReference] = []
    lines = content.splitlines()
    blocks = _parse_fenced_blocks(content)

    # Track seen (reference, line) pairs to avoid duplicates from overlapping patterns
    seen: set[tuple[str, int]] = set()

    # Build line -> block mapping for quick lookup
    line_to_block: dict[int, tuple[str, str]] = {}
    for lang, block_content, start, end in blocks:
        for ln in range(start, end + 1):
            line_to_block[ln] = (lang, block_content)

    # Regex patterns for different reference types
    backtick_re = re.compile(r"`([^`]+)`")
    cli_command_re = re.compile(r"\bcihub\s+[\w-]+(?:\s+[\w-]+)*")
    file_path_re = re.compile(r"\b(cihub/[\w/.-]+\.py|templates/[\w/.-]+|config/[\w/.-]+)")
    env_var_re = re.compile(r"\b(CIHUB_[A-Z_]+|CI_HUB_[A-Z_]+|GITHUB_[A-Z_]+)\b")

    for line_num, line in enumerate(lines, 1):
        # Check if we're in a fenced block
        block_info = line_to_block.get(line_num)
        if block_info:
            lang, _ = block_info
            if skip_fences:
                continue
            if lang.lower() in SKIPPED_FENCE_TYPES:
                continue
            # Only parse CLI-like fences
            if lang.lower() not in PARSED_FENCE_TYPES:
                continue

        # Skip comment lines in fences
        stripped = line.strip()
        if stripped.startswith("#") and block_info:
            continue

        context = _get_context(line_num, lines)

        def _add_ref(
            reference: str,
            kind: str,
            *,
            _line: int = line_num,
            _ctx: str = context,
        ) -> None:
            """Add reference if not already seen (deduplication)."""
            key = (reference, _line)
            if key not in seen:
                seen.add(key)
                refs.append(
                    DocReference(
                        reference=reference,
                        kind=kind,
                        file=file_path,
                        line=_line,
                        context=_ctx,
                    )
                )

        # Extract backtick references
        for match in backtick_re.finditer(line):
            token = match.group(1)
            if _is_false_positive(token):
                continue

            kind = _classify_reference(token)
            _add_ref(token, kind)

        # Extract CLI commands in prose (not backticked)
        for match in cli_command_re.finditer(line):
            cmd = match.group(0)
            _add_ref(cmd, KIND_CLI_COMMAND)

        # Extract file paths
        for match in file_path_re.finditer(line):
            path = match.group(1)
            _add_ref(path, KIND_FILE_PATH)

        # Extract environment variables
        for match in env_var_re.finditer(line):
            env = match.group(1)
            _add_ref(env, KIND_ENV_VAR)

    return refs


def extract_refs_from_file(
    file_path: Path,
    skip_fences: bool = False,
) -> list[DocReference]:
    """Extract references from a markdown file on disk.

    Args:
        file_path: Path to the markdown file
        skip_fences: If True, skip fenced code blocks

    Returns:
        List of DocReference objects, empty list if file can't be read
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        return extract_doc_references(content, str(file_path), skip_fences)
    except (OSError, UnicodeDecodeError):
        return []
