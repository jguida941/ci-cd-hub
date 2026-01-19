"""Guide command validation."""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path

from cihub.cli_parsers.builder import build_parser

from .types import AuditFinding, FindingCategory, FindingSeverity

CODE_FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
SEGMENT_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||;)\s*")
TRAILING_STRIP_CHARS = ".,:;)]}"
OUTPUT_TOKEN_RE = re.compile(r"^[vV]?\d")
GENERIC_TOKENS = {
    "cli",
    "command",
    "commands",
    "subcommand",
    "subcommands",
    "tool",
    "tools",
}


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:  # noqa: SLF001 - argparse internals
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return action.choices
    return {}


def _build_command_tree(parser: argparse.ArgumentParser) -> dict[str, dict[str, dict]]:
    tree: dict[str, dict[str, dict]] = {}
    for name, sub in _subparsers(parser).items():
        tree[name] = _build_command_tree(sub)
    return tree


def _strip_trailing_punct(token: str) -> str:
    return token.rstrip(TRAILING_STRIP_CHARS)


def _is_placeholder(token: str) -> bool:
    if token.startswith("<") or token.startswith("$"):
        return True
    return token.lower() in GENERIC_TOKENS


def _extract_cihub_tokens(tokens: list[str]) -> list[str] | None:
    if not tokens:
        return None
    # Drop shell prompts
    while tokens and tokens[0] in {"$", "#", ">", "%"}:
        tokens = tokens[1:]

    for idx, token in enumerate(tokens):
        cleaned = _strip_trailing_punct(token)
        if cleaned == "cihub":
            return tokens[idx + 1 :]
        if cleaned in {"python", "python3"} and [_strip_trailing_punct(t) for t in tokens[idx + 1 : idx + 3]] == [
            "-m",
            "cihub",
        ]:
            return tokens[idx + 3 :]
    return None


def _validate_command_tokens(tokens: list[str], command_tree: dict[str, dict[str, dict]]) -> tuple[str, str] | None:
    if not tokens:
        return None

    tokens = [_strip_trailing_punct(token) for token in tokens if token]
    if not tokens:
        return None

    first = tokens[0]
    if first.startswith("-") or _is_placeholder(first):
        return None

    if first not in command_tree:
        if len(tokens) == 1 and OUTPUT_TOKEN_RE.match(first):
            return None
        return ("cihub", first)

    current = command_tree[first]
    path = ["cihub", first]
    for token in tokens[1:]:
        if not token:
            continue
        if token.startswith("-") or token in {"--", "|", "||", "&&", ";"}:
            break
        if _is_placeholder(token):
            break
        token = _strip_trailing_punct(token)
        if token in current:
            current = current[token]
            path.append(token)
            continue
        if not current:
            break
        return (" ".join(path), token)

    return None


def _iter_guide_snippets(content: str) -> list[tuple[int, str]]:
    snippets: list[tuple[int, str]] = []
    in_fence = False
    fence_marker = ""

    for line_num, line in enumerate(content.splitlines(), 1):
        fence_match = CODE_FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif fence_marker == marker:
                in_fence = False
                fence_marker = ""
            continue

        if in_fence:
            snippets.append((line_num, line))

        for match in INLINE_CODE_RE.finditer(line):
            snippet = match.group(1)
            snippets.append((line_num, snippet))

    return snippets


def validate_guide_commands(repo_root: Path) -> list[AuditFinding]:
    """Validate cihub command mentions in docs/guides."""
    guides_dir = repo_root / "docs" / "guides"
    if not guides_dir.exists():
        return []

    command_tree = _build_command_tree(build_parser())
    findings: list[AuditFinding] = []

    for guide_path in guides_dir.rglob("*.md"):
        try:
            content = guide_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = str(guide_path.relative_to(repo_root))
        for line_num, snippet in _iter_guide_snippets(content):
            if "cihub" not in snippet:
                continue

            for segment in SEGMENT_SPLIT_RE.split(snippet):
                try:
                    tokens = shlex.split(segment)
                except ValueError:
                    tokens = segment.split()
                cihub_tokens = _extract_cihub_tokens(tokens)
                if cihub_tokens is None:
                    continue

                invalid = _validate_command_tokens(cihub_tokens, command_tree)
                if invalid is None:
                    continue

                path, token = invalid
                findings.append(
                    AuditFinding(
                        severity=FindingSeverity.WARNING,
                        category=FindingCategory.GUIDE_COMMAND,
                        message=f"Unknown CLI command in guide: '{path} {token}'",
                        file=rel_path,
                        line=line_num,
                        code="CIHUB-AUDIT-GUIDE-COMMAND",
                        suggestion="Update to a valid cihub command or remove the reference",
                    )
                )

    return findings
