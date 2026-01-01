#!/usr/bin/env python3
"""
DEPRECATED: This script is a shim for backwards compatibility.

Use: cihub config --repo <name> apply-profile --profile <path>

This shim will be removed in the next release.

The functions deep_merge and load_yaml are re-exported from cihub.config.*
for backwards compatibility with existing tests and scripts.
"""

from __future__ import annotations

import argparse
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
    output_path = Path(args.output) if args.output else target_path

    # Load profile and target
    profile_data = load_yaml(profile_path)
    target_data = load_yaml(target_path)

    # Merge: profile provides defaults, target overrides
    merged = deep_merge(profile_data, target_data)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, default_flow_style=False, sort_keys=False)

    print(f"Profile applied: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
