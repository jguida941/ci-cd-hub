#!/usr/bin/env python3
"""
DEPRECATED: This script is a shim for backwards compatibility.

Use: cihub config apply-profile --profile <path> --target <path>

This shim will be removed in the next release.

The deep_merge symbol and load_yaml helper are kept for backwards
compatibility with existing tests and scripts.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any

import yaml

warnings.warn(
    "scripts.apply_profile is deprecated. Use 'cihub config apply-profile' instead. "
    "This shim will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export deep_merge from cihub.config.merge for backwards compatibility
from cihub.config.merge import deep_merge  # noqa: E402, F401


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict.

    Shim wrapper around cihub.config.io.load_yaml_file for backwards compatibility.

    Args:
        path: Path to the YAML file.

    Returns:
        Dictionary containing the YAML contents, or empty dict if file doesn't exist.

    Raises:
        ValueError: If the YAML root is not a mapping (dict).
    """
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping (dict), got {type(data).__name__}")
    return data


def main() -> int:
    """Apply profile to target config (backwards-compatible shim).

    This preserves the original behavior:
    - Works with arbitrary file paths (not just config/repos/*.yaml)
    - Supports --output option for writing to a different path
    """
    print(
        "[DEPRECATED] scripts/apply_profile.py: use 'cihub config apply-profile' instead",
        file=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Apply profile to target config (DEPRECATED)")
    parser.add_argument("profile", help="Path to profile YAML")
    parser.add_argument("target", help="Path to target config YAML")
    parser.add_argument("-o", "--output", help="Optional output path (defaults to target)")
    args = parser.parse_args()

    profile_path = Path(args.profile)
    target_path = Path(args.target)

    cmd = [
        sys.executable,
        "-m",
        "cihub",
        "config",
        "apply-profile",
        "--profile",
        str(profile_path),
        "--target",
        str(target_path),
    ]
    if args.output:
        cmd.extend(["--output", str(Path(args.output))])

    return subprocess.call(cmd)  # noqa: S603


if __name__ == "__main__":
    raise SystemExit(main())
