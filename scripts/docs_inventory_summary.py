#!/usr/bin/env python3
"""Print documentation inventory counts from cihub docs audit.

Usage:
  python scripts/docs_inventory_summary.py
  python scripts/docs_inventory_summary.py --format json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

from cihub.commands.docs_audit.inventory import CATEGORY_ORDER


def _run_docs_audit(python_bin: str) -> dict[str, Any]:
    cmd = [
        python_bin,
        "-m",
        "cihub",
        "docs",
        "audit",
        "--inventory",
        "--json",
        "--skip-references",
        "--skip-consistency",
        "--skip-headers",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603

    if not result.stdout.strip():
        raise RuntimeError("No JSON output received from docs audit")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from docs audit: {exc}") from exc


def _format_markdown(summary: dict[str, Any]) -> str:
    lines = ["| Category | Files | Lines |", "| --- | --- | --- |"]
    lines.append(f"| total | {summary.get('total_files', 0)} | {summary.get('total_lines', 0)} |")

    categories = summary.get("categories", {})
    ordered = [c for c in CATEGORY_ORDER if c in categories]
    for name in ordered:
        data = categories.get(name, {})
        lines.append(f"| {name} | {data.get('files', 0)} | {data.get('lines', 0)} |")

    for name in sorted(set(categories) - set(ordered)):
        data = categories.get(name, {})
        lines.append(f"| {name} | {data.get('files', 0)} | {data.get('lines', 0)} |")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--python",
        dest="python_bin",
        default=sys.executable,
        help="Python executable to use",
    )
    args = parser.parse_args()

    try:
        payload = _run_docs_audit(args.python_bin)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    summary = payload.get("data", {}).get("inventory_summary")
    if not summary:
        print("Error: docs audit did not return inventory_summary", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(summary, indent=2))
        return 0

    print(_format_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
