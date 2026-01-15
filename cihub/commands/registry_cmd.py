"""Backward compatibility shim for registry command.

This module re-exports all symbols from the new registry package
to maintain backward compatibility with existing imports like:
    from cihub.commands.registry_cmd import cmd_registry

The implementation has been moved to cihub.commands.registry/
"""

from __future__ import annotations

# Re-export everything from the new registry package
from cihub.commands.registry import (
    _cmd_add,
    _cmd_bootstrap,
    _cmd_diff,
    _cmd_export,
    _cmd_import,
    _cmd_list,
    _cmd_remove,
    _cmd_set,
    _cmd_show,
    _cmd_sync,
    _derive_hub_root_from_configs_dir,
    cmd_registry,
)

__all__ = [
    "cmd_registry",
    "_derive_hub_root_from_configs_dir",
    "_cmd_list",
    "_cmd_show",
    "_cmd_set",
    "_cmd_add",
    "_cmd_remove",
    "_cmd_diff",
    "_cmd_sync",
    "_cmd_bootstrap",
    "_cmd_export",
    "_cmd_import",
]
