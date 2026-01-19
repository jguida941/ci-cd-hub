"""Centralized registry of environment variables used by cihub.

This module serves as the single source of truth for environment variables.
Both runtime code and documentation generation read from this registry,
preventing drift between actual usage and documented variables.

Usage:
    from cihub.utils.env_registry import ENV_REGISTRY, get_env_var

    # Get a specific env var definition
    debug_var = ENV_REGISTRY["CIHUB_DEBUG"]

    # Check if env var is enabled at runtime
    from cihub.utils.env import env_bool
    debug_enabled = env_bool("CIHUB_DEBUG")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class EnvVarDef:
    """Definition of an environment variable."""

    name: str
    var_type: Literal["bool", "string", "int"]
    default: str
    category: Literal["Debug", "Report", "Auth", "Context", "Notify", "Tools"]
    description: str


# =============================================================================
# Environment Variable Registry
# =============================================================================
# This is the single source of truth for all cihub environment variables.
# Add new variables here, not in the docs generation helper or elsewhere.

_ENV_VARS: list[EnvVarDef] = [
    # ---------------------------------------------------------------------
    # Debug/Developer toggles
    # ---------------------------------------------------------------------
    EnvVarDef(
        name="CIHUB_DEBUG",
        var_type="bool",
        default="false",
        category="Debug",
        description="Enable tracebacks and verbose error output.",
    ),
    EnvVarDef(
        name="CIHUB_VERBOSE",
        var_type="bool",
        default="false",
        category="Debug",
        description="Stream tool stdout/stderr to console.",
    ),
    EnvVarDef(
        name="CIHUB_DEBUG_CONTEXT",
        var_type="bool",
        default="false",
        category="Debug",
        description="Emit decision/context debug blocks to stderr.",
    ),
    EnvVarDef(
        name="CIHUB_EMIT_TRIAGE",
        var_type="bool",
        default="false",
        category="Debug",
        description="Generate triage bundles for CI failure analysis.",
    ),
    EnvVarDef(
        name="CIHUB_DEV_MODE",
        var_type="bool",
        default="false",
        category="Debug",
        description="Auto-run AI enhancement on failures for local debugging.",
    ),
    # ---------------------------------------------------------------------
    # Report settings
    # ---------------------------------------------------------------------
    EnvVarDef(
        name="CIHUB_WRITE_GITHUB_SUMMARY",
        var_type="bool",
        default="true",
        category="Report",
        description="Write results to GitHub Actions step summary.",
    ),
    EnvVarDef(
        name="CIHUB_REPORT_INCLUDE_DETAILS",
        var_type="bool",
        default="false",
        category="Report",
        description="Include extra detail fields in report output.",
    ),
    # ---------------------------------------------------------------------
    # GitHub tokens
    # ---------------------------------------------------------------------
    EnvVarDef(
        name="GH_TOKEN",
        var_type="string",
        default="",
        category="Auth",
        description="GitHub CLI token (preferred for gh commands).",
    ),
    EnvVarDef(
        name="GITHUB_TOKEN",
        var_type="string",
        default="",
        category="Auth",
        description="GitHub Actions automatic token.",
    ),
    EnvVarDef(
        name="HUB_DISPATCH_TOKEN",
        var_type="string",
        default="",
        category="Auth",
        description="Token for hub workflow dispatch operations.",
    ),
    # ---------------------------------------------------------------------
    # CI context
    # ---------------------------------------------------------------------
    EnvVarDef(
        name="CIHUB_OWNER",
        var_type="string",
        default="",
        category="Context",
        description="Default repository owner (fallback for --owner flag).",
    ),
    EnvVarDef(
        name="CIHUB_REPO",
        var_type="string",
        default="",
        category="Context",
        description="Default repository name (fallback for --repo/--name flag).",
    ),
    EnvVarDef(
        name="CIHUB_HUB_REPO",
        var_type="string",
        default="",
        category="Context",
        description="Hub repo (owner/name) for workflow installs and setup.",
    ),
    EnvVarDef(
        name="CIHUB_HUB_REF",
        var_type="string",
        default="",
        category="Context",
        description="Hub ref (tag/branch/sha) for workflow installs and setup.",
    ),
    EnvVarDef(
        name="CIHUB_AI_LOOP_ITERATION",
        var_type="int",
        default="0",
        category="Context",
        description="Current AI loop iteration number (hook/internal use).",
    ),
    EnvVarDef(
        name="CIHUB_AI_LOOP_MAX_ITERATIONS",
        var_type="int",
        default="0",
        category="Context",
        description="AI loop max iterations (hook/internal use).",
    ),
    EnvVarDef(
        name="CIHUB_AI_PROVIDER",
        var_type="string",
        default="claude",
        category="Context",
        description="AI provider for optional enhancements (default: claude).",
    ),
    # ---------------------------------------------------------------------
    # Notifications
    # ---------------------------------------------------------------------
    EnvVarDef(
        name="CIHUB_EMAIL_TO",
        var_type="string",
        default="",
        category="Notify",
        description="Email recipients for CI notifications.",
    ),
    EnvVarDef(
        name="CIHUB_SLACK_WEBHOOK_URL",
        var_type="string",
        default="",
        category="Notify",
        description="Slack webhook URL for CI notifications.",
    ),
    # ---------------------------------------------------------------------
    # Tool overrides
    # ---------------------------------------------------------------------
    EnvVarDef(
        name="CIHUB_BANDIT_FAIL_HIGH",
        var_type="bool",
        default="",
        category="Tools",
        description="Override bandit fail-on-high setting.",
    ),
    EnvVarDef(
        name="CIHUB_BANDIT_FAIL_MEDIUM",
        var_type="bool",
        default="",
        category="Tools",
        description="Override bandit fail-on-medium setting.",
    ),
    EnvVarDef(
        name="CIHUB_BANDIT_FAIL_LOW",
        var_type="bool",
        default="",
        category="Tools",
        description="Override bandit fail-on-low setting.",
    ),
    EnvVarDef(
        name="CIHUB_CODEQL_RAN",
        var_type="bool",
        default="",
        category="Tools",
        description="Set by external CodeQL action when it ran.",
    ),
    EnvVarDef(
        name="CIHUB_CODEQL_SUCCESS",
        var_type="bool",
        default="",
        category="Tools",
        description="Set by external CodeQL action with pass/fail result.",
    ),
    # Dynamic tool run toggles
    EnvVarDef(
        name="CIHUB_RUN_*",
        var_type="bool",
        default="",
        category="Tools",
        description=(
            "Per-tool enable/disable toggle. Replace * with tool name "
            "(e.g., CIHUB_RUN_PYTEST, CIHUB_RUN_RUFF, CIHUB_RUN_BANDIT)."
        ),
    ),
]

# Build lookup dict for fast access
ENV_REGISTRY: dict[str, EnvVarDef] = {v.name: v for v in _ENV_VARS}


def get_env_var(name: str) -> EnvVarDef | None:
    """Get an environment variable definition by name."""
    return ENV_REGISTRY.get(name)


def get_all_env_vars() -> list[EnvVarDef]:
    """Get all environment variable definitions."""
    return list(_ENV_VARS)


def get_env_vars_by_category(category: str) -> list[EnvVarDef]:
    """Get environment variables filtered by category."""
    return [v for v in _ENV_VARS if v.category == category]


# Category display order for documentation
CATEGORY_ORDER: list[str] = ["Debug", "Report", "Auth", "Context", "Notify", "Tools"]
