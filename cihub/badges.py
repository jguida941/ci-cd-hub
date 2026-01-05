"""Badge generation helpers for CI metrics.

Facade module that re-exports from cihub.core.badges for backward
compatibility.
"""

from __future__ import annotations

from cihub.core import badges as _core

ROOT = _core.ROOT
BADGES_DIR = _core.BADGES_DIR

_badge_enabled = _core._badge_enabled
_badge_dir = _core._badge_dir
_percent_color = _core._percent_color
_count_color = _core._count_color
percent_badge = _core.percent_badge
count_badge = _core.count_badge
status_badge = _core.status_badge
disabled_badge = _core.disabled_badge
load_zizmor = _core.load_zizmor
load_bandit = _core.load_bandit
load_pip_audit = _core.load_pip_audit
get_env_int = _core.get_env_int
get_env_float = _core.get_env_float
build_badges = _core.build_badges
main = _core.main

__all__ = [
    "ROOT",
    "BADGES_DIR",
    "_badge_enabled",
    "_badge_dir",
    "_percent_color",
    "_count_color",
    "percent_badge",
    "count_badge",
    "status_badge",
    "disabled_badge",
    "load_zizmor",
    "load_bandit",
    "load_pip_audit",
    "get_env_int",
    "get_env_float",
    "build_badges",
    "main",
]
