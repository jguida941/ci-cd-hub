"""Report building helpers for cihub ci.

Facade module that re-exports from cihub.core.ci_report for backward
compatibility.
"""

from __future__ import annotations

from cihub.core import ci_report as _core

RunContext = _core.RunContext
_timestamp = _core._timestamp
_set_threshold = _core._set_threshold
_get_metric = _core._get_metric
resolve_thresholds = _core.resolve_thresholds
build_python_report = _core.build_python_report
build_java_report = _core.build_java_report

__all__ = [
    "RunContext",
    "_timestamp",
    "_set_threshold",
    "_get_metric",
    "resolve_thresholds",
    "build_python_report",
    "build_java_report",
]
