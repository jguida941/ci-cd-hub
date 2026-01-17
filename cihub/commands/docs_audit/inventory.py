"""Documentation inventory helpers."""

from __future__ import annotations

from pathlib import Path

from .types import DocInventoryCategory, DocInventorySummary

CATEGORY_ORDER = (
    "root",
    "adr",
    "reference",
    "guides",
    "development",
    "archive",
    "research",
    "other",
)


def _classify_doc_path(rel_path: Path) -> str:
    """Classify a docs/ markdown file into an inventory category."""
    parts = rel_path.parts
    if not parts or parts[0] != "docs":
        return "other"
    if len(parts) == 2:
        return "root"
    if parts[1] == "adr":
        return "adr"
    if parts[1] == "reference":
        return "reference"
    if parts[1] == "guides":
        return "guides"
    if parts[1] == "development":
        if len(parts) > 2 and parts[2] == "archive":
            return "archive"
        if len(parts) > 2 and parts[2] == "research":
            return "research"
        return "development"
    if parts[1] == "research":
        return "research"
    return "other"


def _count_lines(path: Path) -> int:
    """Return a line count for a markdown file."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    return len(content.splitlines())


def build_doc_inventory(repo_root: Path) -> DocInventorySummary:
    """Build a markdown inventory for docs/."""
    summary = DocInventorySummary(categories={name: DocInventoryCategory() for name in CATEGORY_ORDER})
    docs_dir = repo_root / "docs"
    if not docs_dir.exists():
        return summary

    for md_file in docs_dir.rglob("*.md"):
        if not md_file.is_file():
            continue
        rel_path = md_file.relative_to(repo_root)
        category = _classify_doc_path(rel_path)
        line_count = _count_lines(md_file)

        summary.total_files += 1
        summary.total_lines += line_count
        summary.categories[category].files += 1
        summary.categories[category].lines += line_count

    return summary
