"""Tool registry and definitions.

This module provides a single source of truth for all tool-related
definitions used across the cihub package.
"""

from __future__ import annotations

from cihub.tools.registry import (
    JAVA_ARTIFACTS,
    JAVA_LINT_METRICS,
    JAVA_SECURITY_METRICS,
    JAVA_SUMMARY_MAP,
    JAVA_TOOL_METRICS,
    JAVA_TOOLS,
    PYTHON_ARTIFACTS,
    PYTHON_LINT_METRICS,
    PYTHON_SECURITY_METRICS,
    PYTHON_SUMMARY_MAP,
    PYTHON_TOOL_METRICS,
    PYTHON_TOOLS,
    RESERVED_FEATURES,
    THRESHOLD_KEYS,
    TOOL_KEYS,
)

__all__ = [
    # Tool name lists
    "PYTHON_TOOLS",
    "JAVA_TOOLS",
    "RESERVED_FEATURES",
    # Workflow input keys
    "TOOL_KEYS",
    "THRESHOLD_KEYS",
    # Tool metrics (expected metric paths per tool)
    "PYTHON_TOOL_METRICS",
    "JAVA_TOOL_METRICS",
    # Lint/security metric names
    "PYTHON_LINT_METRICS",
    "PYTHON_SECURITY_METRICS",
    "JAVA_LINT_METRICS",
    "JAVA_SECURITY_METRICS",
    # Summary table label → tool key maps
    "PYTHON_SUMMARY_MAP",
    "JAVA_SUMMARY_MAP",
    # Artifact glob patterns per tool
    "PYTHON_ARTIFACTS",
    "JAVA_ARTIFACTS",
]
