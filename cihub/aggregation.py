"""Hub orchestration aggregation helpers.

Facade module that re-exports from cihub.core.aggregation for backward
compatibility.
"""

from __future__ import annotations

from cihub.core import aggregation as _core
from cihub.core.aggregation import *  # noqa: F403

__all__ = list(_core.__all__)
