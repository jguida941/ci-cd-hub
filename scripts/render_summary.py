#!/usr/bin/env python3
"""
Render a unified workflow summary from report.json.

Usage:
  python scripts/render_summary.py --report report.json [--output summary.md]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cihub.reporting import render_summary_from_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render workflow summary")
    parser.add_argument("--report", required=True, help="Path to report.json")
    parser.add_argument("--output", help="Path to summary.md (optional)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_text = render_summary_from_path(Path(args.report))
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
    else:
        sys.stdout.write(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
