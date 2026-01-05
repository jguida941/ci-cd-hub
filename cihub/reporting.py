"""Render unified workflow summaries from report.json.

Facade module that re-exports from cihub.core.reporting for backward
compatibility.
"""

from __future__ import annotations

from cihub.core import reporting as _core
from cihub.core.gate_specs import threshold_rows, tool_rows

# Backward compatibility: derive these from the gate_specs registry
JAVA_TOOL_ROWS = tool_rows("java")
PYTHON_TOOL_ROWS = tool_rows("python")
JAVA_THRESHOLD_ROWS = threshold_rows("java")
PYTHON_THRESHOLD_ROWS = threshold_rows("python")
BAR_WIDTH = _core.BAR_WIDTH
BAR_FULL = _core.BAR_FULL
BAR_EMPTY = _core.BAR_EMPTY
ENV_ROWS = _core.ENV_ROWS

load_report = _core.load_report
detect_language = _core.detect_language
fmt_bool = _core.fmt_bool
fmt_value = _core.fmt_value
fmt_percent = _core.fmt_percent
fmt_retention = _core.fmt_retention
fmt_workdir = _core.fmt_workdir
format_number = _core.format_number
render_bar = _core.render_bar
build_tools_table = _core.build_tools_table
build_thresholds_table = _core.build_thresholds_table
build_environment_table = _core.build_environment_table
build_java_metrics = _core.build_java_metrics
build_python_metrics = _core.build_python_metrics
build_dependency_severity = _core.build_dependency_severity
build_quality_gates = _core.build_quality_gates
render_summary = _core.render_summary
render_summary_from_path = _core.render_summary_from_path

__all__ = [
    "JAVA_TOOL_ROWS",
    "BAR_WIDTH",
    "BAR_FULL",
    "BAR_EMPTY",
    "PYTHON_TOOL_ROWS",
    "JAVA_THRESHOLD_ROWS",
    "PYTHON_THRESHOLD_ROWS",
    "ENV_ROWS",
    "load_report",
    "detect_language",
    "fmt_bool",
    "fmt_value",
    "fmt_percent",
    "fmt_retention",
    "fmt_workdir",
    "format_number",
    "render_bar",
    "build_tools_table",
    "build_thresholds_table",
    "build_environment_table",
    "build_java_metrics",
    "build_python_metrics",
    "build_dependency_severity",
    "build_quality_gates",
    "render_summary",
    "render_summary_from_path",
]
