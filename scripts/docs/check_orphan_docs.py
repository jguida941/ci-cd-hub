#!/usr/bin/env python3
"""
Detect orphan documentation (not linked from anywhere).
Uses existing pyyaml from requirements-dev.txt.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Set

from bs4 import BeautifulSoup  # noqa: F401
import yaml  # noqa: F401


def log(message: str) -> None:
    print(f"[orphan-check] {message}", file=sys.stderr)


def find_markdown_files(root: Path) -> Set[Path]:
    markdown_files = set()
    for path in root.rglob("*.md"):
        # Skip hidden and ignored directories
        if any(part.startswith(".") for part in path.parts):
            continue
        # Skip virtual environments and build artifacts
        if any(
            folder in path.parts
            for folder in (
                "node_modules",
                ".venv",
                "venv",
                "env",
                "dist",
                "build",
                "__pycache__",
                ".git",
                ".pytest_cache",
                ".doc-link-backup",
                "artifacts",
                "target",
            )
        ):
            continue
        markdown_files.add(path)
    return markdown_files


def find_linked_files(root: Path) -> Set[Path]:
    linked_files = set()

    for path in root.rglob("*.md"):
        if any(part.startswith(".") for part in path.parts):
            continue
        if path.name == "README.md":
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "(" in line and ".md" in line:
                    parts = line.split("(")
                    for part in parts[1:]:
                        target = part.split(")")[0]
                        if target.endswith(".md"):
                            target_path = (path.parent / target).resolve()
                            linked_files.add(target_path)
    return linked_files


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent
    log(f"Checking for orphan documentation in {repo_root}")

    markdown_files = find_markdown_files(repo_root)
    log(f"Found {len(markdown_files)} markdown files")

    linked_files = find_linked_files(repo_root)
    log(f"Found {len(linked_files)} referenced markdown files")

    orphan_files = {f for f in markdown_files if f.resolve() not in linked_files}

    if orphan_files:
        log("Orphan Markdown files detected:")
        for orphan in sorted(orphan_files):
            log(f"  {orphan.relative_to(repo_root)}")
        return 1

    log("✅ No orphan documents found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
