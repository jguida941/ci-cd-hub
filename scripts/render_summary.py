#!/usr/bin/env python3
"""
DEPRECATED: This script is a shim for backwards compatibility.

Use: cihub report summary --report report.json [--output summary.md]

This shim will be removed in the next release.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import warnings

# Emit deprecation warning on import
warnings.warn(
    "scripts.render_summary is deprecated. Use 'cihub report summary' instead. "
    "This shim will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render workflow summary (DEPRECATED)")
    parser.add_argument("--report", required=True, help="Path to report.json")
    parser.add_argument("--output", help="Path to summary.md (optional)")
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "cihub", "report", "summary", "--report", args.report]
    if args.output:
        cmd.extend(["--output", args.output])

    print(
        "[DEPRECATED] scripts/render_summary.py: use 'cihub report summary' instead",
        file=sys.stderr,
    )
    return subprocess.call(cmd)  # noqa: S603


if __name__ == "__main__":
    raise SystemExit(main())
