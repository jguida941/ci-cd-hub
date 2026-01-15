"""Registry command package for centralized repo configuration."""

from __future__ import annotations

import argparse

from cihub.exit_codes import EXIT_USAGE
from cihub.types import CommandResult

# Import utility function first (no circular dependency)
from ._utils import _derive_hub_root_from_configs_dir

# Import handlers from submodules
from .io import _cmd_export, _cmd_import
from .modify import _cmd_add, _cmd_remove, _cmd_set
from .query import _cmd_list, _cmd_show
from .sync import _cmd_bootstrap, _cmd_diff, _cmd_sync


def cmd_registry(args: argparse.Namespace) -> CommandResult:
    """Dispatch registry subcommands."""
    subcommand: str | None = getattr(args, "subcommand", None)

    handlers = {
        "list": _cmd_list,
        "show": _cmd_show,
        "set": _cmd_set,
        "diff": _cmd_diff,
        "sync": _cmd_sync,
        "add": _cmd_add,
        "remove": _cmd_remove,
        "bootstrap": _cmd_bootstrap,
        "export": _cmd_export,
        "import": _cmd_import,
    }

    handler = handlers.get(subcommand or "")
    if handler is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown registry subcommand: {subcommand}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Unknown subcommand '{subcommand}'",
                    "code": "CIHUB-REGISTRY-UNKNOWN-SUBCOMMAND",
                }
            ],
        )

    return handler(args)


# Export all handlers for backward compatibility and direct access
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
