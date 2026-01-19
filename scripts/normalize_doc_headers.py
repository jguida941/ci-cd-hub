#!/usr/bin/env python3
"""Normalize header line breaks in markdown docs.

Adds two trailing spaces to header metadata lines (Status, Date, etc.) so
renderers preserve line breaks without <br> tags.
"""

from __future__ import annotations

import argparse
from pathlib import Path

HEADER_LABELS = {
    "Status",
    "Owner",
    "Source-of-truth",
    "Last-reviewed",
    "Date",
    "Last Updated",
    "Priority",
    "Depends On",
    "Can Parallel",
    "Problem",
    "Developer",
    "Last Reviewed",
    "Superseded-by",
    "Superseded by",
}

FENCE_MARKERS = ("```", "~~~")


def _extract_label(line: str) -> str | None:
    trimmed = line.lstrip()
    if trimmed.startswith(">"):
        trimmed = trimmed[1:].lstrip()

    if trimmed.startswith("**"):
        end = trimmed.find("**", 2)
        if end != -1:
            label = trimmed[2:end].strip().rstrip(":")
            return label

    if ":" in trimmed:
        label = trimmed.split(":", 1)[0].strip()
        return label

    return None


def _should_update_line(line: str) -> bool:
    label = _extract_label(line)
    if not label:
        return False
    return label in HEADER_LABELS


def _ensure_trailing_spaces(line: str) -> str:
    if line.endswith("\n"):
        core = line[:-1]
        newline = "\n"
    else:
        core = line
        newline = ""
    core = core.rstrip(" ")
    for suffix in ("<br>", "<br/>", "<br />"):
        if core.endswith(suffix):
            core = core[: -len(suffix)].rstrip(" ")
            break
    return f"{core}  {newline}"


def _normalize_file(path: Path, check_only: bool) -> bool:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    in_fence = False
    updated = False
    new_lines: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        if any(stripped.startswith(marker) for marker in FENCE_MARKERS):
            in_fence = not in_fence
            new_lines.append(line)
            continue

        if not in_fence and _should_update_line(line) and not line.rstrip("\n").endswith("  "):
            new_lines.append(_ensure_trailing_spaces(line))
            updated = True
        else:
            new_lines.append(line)

    if updated and not check_only:
        path.write_text("".join(new_lines), encoding="utf-8")

    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=["docs"],
        help="Paths to scan (default: docs)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report files that need updates without writing",
    )
    args = parser.parse_args()

    changed_files: list[str] = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_dir():
            files = sorted(path.rglob("*.md"))
        elif path.is_file() and path.suffix == ".md":
            files = [path]
        else:
            continue

        for file_path in files:
            if _normalize_file(file_path, args.check):
                changed_files.append(str(file_path))

    if changed_files:
        for changed_path in changed_files:
            print(changed_path)
        return 1 if args.check else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
