#!/usr/bin/env python3
"""
DEPRECATED: This script is a shim for backwards compatibility.

Use: cihub hub-ci verify-matrix-keys

This shim will be removed in the next release.
"""

from __future__ import annotations

import subprocess
import sys
import warnings

warnings.warn(
    "scripts.verify_hub_matrix_keys is deprecated. "
    "Use 'cihub hub-ci verify-matrix-keys' instead. "
    "This shim will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> int:
    print(
        "[DEPRECATED] scripts/verify_hub_matrix_keys.py: use 'cihub hub-ci verify-matrix-keys' instead",
        file=sys.stderr,
    )
    return subprocess.call([sys.executable, "-m", "cihub", "hub-ci", "verify-matrix-keys"])  # noqa: S603


if __name__ == "__main__":
    raise SystemExit(main())
