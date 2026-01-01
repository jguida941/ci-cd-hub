#!/usr/bin/env python3
"""
DEPRECATED: This script is a shim that forwards to the CLI.

Use `cihub report dashboard` instead:
    cihub report dashboard --reports-dir REPORTS_DIR --output OUTPUT [--format {json,html}]

This shim will be removed in a future release.
"""

import argparse
import subprocess
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/aggregate_reports.py is deprecated. "
    "Use 'cihub report dashboard' instead. "
    "This shim will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate CI/CD Hub reports (DEPRECATED)")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path(__file__).parent.parent / "reports",
        help="Directory containing report JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output file path",
    )
    parser.add_argument(
        "--format",
        choices=["json", "html"],
        default="html",
        help="Output format",
    )
    parser.add_argument(
        "--schema-mode",
        choices=["warn", "strict"],
        default="warn",
        help="Schema validation mode",
    )

    args = parser.parse_args()

    # Build CLI command
    cmd = [
        sys.executable,
        "-m",
        "cihub",
        "report",
        "dashboard",
        "--reports-dir",
        str(args.reports_dir),
        "--output",
        str(args.output),
        "--format",
        args.format,
        "--schema-mode",
        args.schema_mode,
    ]

    print(
        f"DEPRECATED: Running 'cihub report dashboard' instead. "
        f"Please update your scripts to use the CLI directly.",
        file=sys.stderr,
    )

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
