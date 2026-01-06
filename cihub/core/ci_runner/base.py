"""Core tool result definitions.

This module re-exports ToolResult from cihub.types for backward compatibility.
The canonical definition is now in cihub/types.py.
"""

from __future__ import annotations

# Re-export from canonical location for backward compatibility
from cihub.types import ToolResult

__all__ = ["ToolResult"]
