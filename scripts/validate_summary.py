#!/usr/bin/env python3
"""
DEPRECATED: This script is a shim for backwards compatibility.

Use: cihub report validate --report <report.json> [--summary summary.md]
     [--reports-dir <dir>] [--strict] [--debug]

This shim will be removed in the next release.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import warnings

warnings.warn(
    "scripts.validate_summary is deprecated. Use 'cihub report validate' instead. "
    "This shim will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate summaries and artifacts (DEPRECATED)")
    parser.add_argument("--report", required=True, help="Path to report.json")
    parser.add_argument("--summary", help="Path to summary markdown (optional)")
    parser.add_argument("--reports-dir", help="Directory containing tool artifacts (optional)")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings")
    parser.add_argument("--debug", action="store_true", help="Show debug output for validation")
    args = parser.parse_args()

    cmd = ["python", "-m", "cihub", "report", "validate", "--report", args.report]
    if args.summary:
        cmd.extend(["--summary", args.summary])
    if args.reports_dir:
        cmd.extend(["--reports-dir", args.reports_dir])
    if args.strict:
        cmd.append("--strict")
    if args.debug:
        cmd.append("--debug")

    print("[DEPRECATED] scripts/validate_summary.py: use 'cihub report validate' instead", file=sys.stderr)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
