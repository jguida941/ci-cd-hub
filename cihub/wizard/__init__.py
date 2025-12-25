"""Interactive wizard module for CI/CD Hub."""

from __future__ import annotations

try:
    import questionary  # noqa: F401
    from rich.console import Console  # noqa: F401
except Exception:
    HAS_WIZARD = False
else:
    HAS_WIZARD = True

__all__ = ["HAS_WIZARD"]
