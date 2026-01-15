"""Internal path utilities for registry package.

This module provides a central import point for hub_root, allowing tests to
monkeypatch a single location.

For backward compatibility, tests can monkeypatch either:
- cihub.services.registry._paths.hub_root (preferred)
- cihub.services.registry_service.hub_root (legacy, still works)

The get_hub_root() function checks the registry_service module first for
backward compatibility with tests that monkeypatch there.
"""

from pathlib import Path

from cihub.utils.paths import hub_root as _original_hub_root

# This can be monkeypatched directly
hub_root = _original_hub_root


def get_hub_root() -> Path:
    """Get hub_root, checking for monkeypatched values.

    Checks cihub.services.registry_service.hub_root first for backward
    compatibility with tests that monkeypatch there, then falls back
    to this module's hub_root.
    """
    # Check if registry_service has a different hub_root (monkeypatched)
    try:
        import cihub.services.registry_service as rs_module

        rs_hub_root = getattr(rs_module, "hub_root", None)
        if rs_hub_root is not None and rs_hub_root is not hub_root:
            return Path(rs_hub_root())
    except ImportError:
        pass

    # Use this module's hub_root (may also be monkeypatched)
    return hub_root()


__all__ = ["hub_root", "get_hub_root"]
