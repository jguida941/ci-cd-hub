"""Documentation link checking functionality."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.paths import project_root

# Regex to match markdown links: [text](path) or [text](path#anchor)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
FENCED_BLOCK_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
REFERENCE_DEF_RE = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)


def _strip_fenced_blocks(content: str) -> str:
    return FENCED_BLOCK_RE.sub("", content)


def _link_is_external(link_target: str) -> bool:
    return link_target.startswith(("http://", "https://", "mailto:", "tel:"))


def _resolve_link(md_file: Path, repo_root: Path, link_target: str) -> Path:
    if link_target.startswith("/"):
        return (repo_root / link_target.lstrip("/")).resolve()
    return (md_file.parent / link_target).resolve()


def _format_doc_path(md_file: Path, docs_dir: Path, repo_root: Path) -> str:
    try:
        return str(md_file.relative_to(docs_dir))
    except ValueError:
        try:
            return str(md_file.relative_to(repo_root))
        except ValueError:
            return str(md_file)


def _normalize_link_target(link_target: str) -> str:
    cleaned = link_target.split("#", 1)[0]
    return cleaned.split("?", 1)[0]


def _check_internal_links(docs_dir: Path) -> list[dict[str, Any]]:
    """Check internal markdown links without external tools.

    Scans all .md files for relative links and verifies targets exist.
    """
    problems: list[dict[str, Any]] = []
    repo_root = docs_dir.parent
    md_files = list(docs_dir.rglob("*.md"))
    root_readme = repo_root / "README.md"
    if docs_dir.name == "docs" and root_readme.exists():
        md_files.append(root_readme)

    for md_file in md_files:
        # Archived docs are historical; they are excluded from link checking to avoid
        # requiring churn to keep old/superseded docs up to date.
        try:
            rel = md_file.relative_to(docs_dir).as_posix()
            if rel.startswith("development/archive/"):
                continue
        except ValueError:
            # Root README.md is checked too; keep it in scope.
            pass

        content = md_file.read_text(encoding="utf-8")
        content = _strip_fenced_blocks(content)

        for match in REFERENCE_DEF_RE.finditer(content):
            ref_id, link_target = match.groups()
            if link_target.startswith("#") or _link_is_external(link_target):
                continue
            target_path = _normalize_link_target(link_target)
            if not target_path:
                continue
            resolved = _resolve_link(md_file, repo_root, target_path)
            if not resolved.exists():
                problems.append(
                    {
                        "severity": "error",
                        "message": (
                            f"Broken reference link in "
                            f"{_format_doc_path(md_file, docs_dir, repo_root)}: "
                            f"[{ref_id}]: {link_target}"
                        ),
                        "code": "CIHUB-DOCS-BROKEN-LINK",
                        "file": str(md_file),
                        "target": link_target,
                    }
                )
        for match in MARKDOWN_LINK_RE.finditer(content):
            link_text, link_target = match.groups()

            # Skip external links, anchors-only, and mailto
            if link_target.startswith("#") or _link_is_external(link_target):
                continue

            # Handle anchor in link
            target_path = _normalize_link_target(link_target)
            if not target_path:
                continue

            # Resolve relative to the markdown file's directory
            resolved = _resolve_link(md_file, repo_root, target_path)

            if not resolved.exists():
                problems.append(
                    {
                        "severity": "error",
                        "message": (
                            f"Broken link in "
                            f"{_format_doc_path(md_file, docs_dir, repo_root)}: "
                            f"[{link_text}]({link_target})"
                        ),
                        "code": "CIHUB-DOCS-BROKEN-LINK",
                        "file": str(md_file),
                        "target": link_target,
                    }
                )

    return problems


def _run_lychee(docs_dir: Path, external: bool) -> tuple[int, list[dict[str, Any]]]:
    """Run lychee link checker.

    Args:
        docs_dir: Directory to check.
        external: If True, check external links too. If False, offline mode.

    Returns:
        Tuple of (exit_code, problems).
    """
    repo_root = docs_dir.parent
    inputs = ["docs"]
    if (repo_root / "README.md").exists():
        inputs.append("README.md")

    cmd = [
        "lychee",
        *inputs,
        "--no-progress",
        "--mode",
        "plain",
        "--format",
        "json",
        "--root-dir",
        str(repo_root),
        "--exclude-path",
        r"docs/development/archive/.*",
    ]
    if not external:
        cmd.append("--offline")

    try:
        result = safe_run(
            cmd,
            cwd=repo_root,
            timeout=TIMEOUT_BUILD,  # Link checking can be slow
        )
    except CommandNotFoundError:
        return -1, []  # lychee not found
    except CommandTimeoutError:
        return -1, [{"severity": "error", "message": "lychee timed out", "code": "CIHUB-DOCS-TIMEOUT"}]

    problems: list[dict[str, Any]] = []
    if result.returncode != 0:
        # Parse lychee JSON output for broken links.
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            payload = {}

        error_map = payload.get("error_map") if isinstance(payload, dict) else None
        if isinstance(error_map, dict):
            for doc_path, entries in error_map.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    url = str(entry.get("url") or "-")
                    status_raw = entry.get("status")
                    status: dict[str, Any] = status_raw if isinstance(status_raw, dict) else {}
                    status_text = str(status.get("text") or "").strip()
                    status_details = str(status.get("details") or "").strip()

                    extra = ""
                    if status_text and status_details:
                        extra = f" | {status_text} ({status_details})"
                    elif status_text:
                        extra = f" | {status_text}"

                    problems.append(
                        {
                            "severity": "error",
                            "message": f"{doc_path}: {url}{extra}",
                            "code": "CIHUB-DOCS-LYCHEE",
                            "file": str(doc_path),
                            "url": url,
                            "status": status_text,
                            "details": status_details,
                        }
                    )

        # Fallback: surface lychee stderr/stdout if JSON parsing failed or provided no details.
        if not problems:
            detail = (result.stderr or "").strip() or (result.stdout or "").strip()
            problems.append(
                {
                    "severity": "error",
                    "message": f"lychee failed with exit {result.returncode}",
                    "detail": detail,
                    "code": "CIHUB-DOCS-LYCHEE",
                }
            )

    return result.returncode, problems


def cmd_docs_links(args: argparse.Namespace) -> CommandResult:
    """Check documentation for broken links.

    Always returns CommandResult for consistent output handling.
    """
    external = getattr(args, "external", False)
    docs_dir = project_root() / "docs"

    # Try lychee first
    has_lychee = shutil.which("lychee") is not None
    warnings: list[dict[str, Any]] = []

    if has_lychee:
        exit_code, problems = _run_lychee(docs_dir, external)
        if exit_code < 0:
            has_lychee = False
        else:
            tool_used = "lychee"

    if not has_lychee:
        # Fallback to internal checker (always offline)
        if external:
            warnings.append(
                {
                    "severity": "warning",
                    "message": "--external requires lychee. Install with: brew install lychee",
                    "code": "CIHUB-DOCS-NO-LYCHEE",
                }
            )
        problems = _check_internal_links(docs_dir)
        exit_code = EXIT_FAILURE if problems else EXIT_SUCCESS
        tool_used = "internal"

    failed = exit_code != EXIT_SUCCESS
    summary = f"Link check ({tool_used}): {len(problems)} issues" if failed else f"Link check ({tool_used}): OK"

    # Combine warnings and problems
    all_problems = warnings + problems

    # Format problem messages for human-readable output
    items = [summary]
    for problem in problems:
        items.append(f"  {problem['message']}")

    return CommandResult(
        exit_code=EXIT_FAILURE if failed else EXIT_SUCCESS,
        summary=summary,
        problems=all_problems,
        data={"tool": tool_used, "external": external, "items": items},
    )
