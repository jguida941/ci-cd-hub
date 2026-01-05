"""Filesystem helpers for CLI operations."""

from __future__ import annotations

from pathlib import Path


def write_text(path: Path, content: str, dry_run: bool, emit: bool = True) -> None:
    if dry_run:
        if emit:
            print(f"# Would write: {path}")
            print(content)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
