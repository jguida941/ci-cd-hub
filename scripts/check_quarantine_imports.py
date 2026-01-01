#!/usr/bin/env python3
"""
DEPRECATED: This script is a shim for backwards compatibility.

Use: cihub hub-ci quarantine-check

This shim will be removed in the next release.
"""

from __future__ import annotations

import subprocess
import sys
import warnings

warnings.warn(
    "scripts.check_quarantine_imports is deprecated. "
    "Use 'cihub hub-ci quarantine-check' instead. "
    "This shim will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> int:
    print(
        "[DEPRECATED] scripts/check_quarantine_imports.py: "
        "use 'cihub hub-ci quarantine-check' instead",
        file=sys.stderr,
    )
    return subprocess.call(["python", "-m", "cihub", "hub-ci", "quarantine-check"])


if __name__ == "__main__":
    raise SystemExit(main())
