#!/usr/bin/env python3
"""
DEPRECATED: This script is a shim for backwards compatibility.

Use: cihub hub-ci badges

This shim will be removed in the next release.
"""

from __future__ import annotations

import sys

from cihub.badges import main

print(
    "DEPRECATED: scripts/python_ci_badges is deprecated. Use 'cihub hub-ci badges' instead. "
    "This shim will be removed in the next release.",
    file=sys.stderr,
)


if __name__ == "__main__":
    raise SystemExit(main())
