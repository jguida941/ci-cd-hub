#!/usr/bin/env python3
"""
DEPRECATED: This module is a shim for backwards compatibility.

All functionality has moved to cihub.config.loader.
This shim will be removed in the next release.

Use:
    from cihub.config.loader import load_config, generate_workflow_inputs
"""

import warnings

# Emit deprecation warning on import
warnings.warn(
    "scripts.load_config is deprecated. Use cihub.config.loader instead. "
    "This shim will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all public functions from the new location
from cihub.config.loader import (  # noqa: F401, E402
    ConfigValidationError,
    deep_merge,
    generate_workflow_inputs,
    get_tool_config,
    get_tool_enabled,
    load_config,
    load_yaml_file,
)


def main() -> None:
    """CLI entry point - delegates to cihub.config.loader._main."""
    from cihub.config.loader import _main

    _main()


if __name__ == "__main__":
    main()
