"""Single source of truth for tool definitions.

This module centralizes all tool-related definitions that were previously
scattered across ci_engine.py, discovery.py, and the report_validator package.

IMPORTANT: Do not modify tool lists without updating ALL related definitions.
Run tests/test_tool_registry.py after any changes to verify consistency.

Custom Tools (x- prefix):
    Users can define custom tools with the x- prefix in their config:
    ```yaml
    python:
      tools:
        x-custom-linter:
          enabled: true
          command: "my-linter --check ."
    ```
    Custom tools are preserved through normalization and reported in triage.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Callable

# =============================================================================
# CUSTOM TOOL PATTERN
# =============================================================================

CUSTOM_TOOL_PREFIX = "x-"
CUSTOM_TOOL_PATTERN = re.compile(r"^x-[a-zA-Z0-9_-]+$")

# =============================================================================
# TOOL NAME LISTS (from ci_engine.py)
# =============================================================================

PYTHON_TOOLS: list[str] = [
    "pytest",
    "ruff",
    "black",
    "isort",
    "mypy",
    "bandit",
    "pip_audit",
    "sbom",
    "semgrep",
    "trivy",
    "codeql",
    "docker",
    "hypothesis",
    "mutmut",
]

JAVA_TOOLS: list[str] = [
    "jacoco",
    "pitest",
    "jqwik",
    "checkstyle",
    "spotbugs",
    "pmd",
    "owasp",
    "semgrep",
    "trivy",
    "codeql",
    "sbom",
    "docker",
]

RESERVED_FEATURES: list[tuple[str, str]] = [
    ("chaos", "Chaos testing"),
    ("dr_drill", "Disaster recovery drills"),
    ("cache_sentinel", "Cache sentinel"),
    ("runner_isolation", "Runner isolation"),
    ("supply_chain", "Supply chain security"),
    ("egress_control", "Egress control"),
    ("canary", "Canary deployments"),
    ("telemetry", "Telemetry"),
    ("kyverno", "Kyverno policies"),
]

# =============================================================================
# WORKFLOW INPUT KEYS (from discovery.py)
# =============================================================================

# Keys to extract from generate_workflow_inputs()
TOOL_KEYS: tuple[str, ...] = (
    # Java tool flags
    "run_jacoco",
    "run_checkstyle",
    "run_spotbugs",
    "run_owasp",
    "use_nvd_api_key",
    "run_pitest",
    "run_jqwik",
    "run_pmd",
    # Python tool flags
    "run_pytest",
    "run_ruff",
    "run_bandit",
    "run_pip_audit",
    "run_mypy",
    "run_black",
    "run_isort",
    "run_mutmut",
    "run_hypothesis",
    "run_sbom",
    # Shared
    "run_semgrep",
    "run_trivy",
    "run_codeql",
    "run_docker",
)

THRESHOLD_KEYS: tuple[str, ...] = (
    "coverage_min",
    "mutation_score_min",
    "owasp_cvss_fail",
    "trivy_cvss_fail",
    "max_critical_vulns",
    "max_high_vulns",
    "max_semgrep_findings",
    "max_pmd_violations",
    "max_checkstyle_errors",
    "max_spotbugs_bugs",
    "max_ruff_errors",
    "max_black_issues",
    "max_isort_issues",
)

# =============================================================================
# TOOL METRICS (from report_validator package)
# Metrics expected for each tool (by language)
# =============================================================================

PYTHON_TOOL_METRICS: dict[str, list[str]] = {
    "pytest": ["results.tests_passed", "results.coverage"],
    "mutmut": ["results.mutation_score"],
    "ruff": ["tool_metrics.ruff_errors"],
    "black": ["tool_metrics.black_issues"],
    "isort": ["tool_metrics.isort_issues"],
    "mypy": ["tool_metrics.mypy_errors"],
    "bandit": ["tool_metrics.bandit_high", "tool_metrics.bandit_medium"],
    "pip_audit": ["tool_metrics.pip_audit_vulns"],
    "sbom": [],
    "semgrep": ["tool_metrics.semgrep_findings"],
    "trivy": ["tool_metrics.trivy_critical", "tool_metrics.trivy_high"],
    "hypothesis": ["results.tests_passed"],
    "codeql": [],
    "docker": [],
}

JAVA_TOOL_METRICS: dict[str, list[str]] = {
    "jacoco": ["results.coverage"],
    "pitest": ["results.mutation_score"],
    "checkstyle": ["tool_metrics.checkstyle_issues"],
    "spotbugs": ["tool_metrics.spotbugs_issues"],
    "pmd": ["tool_metrics.pmd_violations"],
    "owasp": ["tool_metrics.owasp_critical", "tool_metrics.owasp_high"],
    "semgrep": ["tool_metrics.semgrep_findings"],
    "trivy": ["tool_metrics.trivy_critical", "tool_metrics.trivy_high"],
    "sbom": [],
    "jqwik": ["results.tests_passed"],
    "codeql": [],
    "docker": [],
}

# =============================================================================
# LINT AND SECURITY METRIC NAMES (from report_validator package)
# Metrics that must be 0 for clean builds
# =============================================================================

PYTHON_LINT_METRICS: list[str] = ["ruff_errors", "black_issues", "isort_issues"]
PYTHON_SECURITY_METRICS: list[str] = ["bandit_high", "pip_audit_vulns"]
JAVA_LINT_METRICS: list[str] = ["checkstyle_issues", "spotbugs_issues", "pmd_violations"]
JAVA_SECURITY_METRICS: list[str] = ["owasp_critical", "owasp_high"]

# =============================================================================
# SUMMARY TABLE MAPS (from report_validator package)
# Summary table labels -> tool keys
# =============================================================================

JAVA_SUMMARY_MAP: dict[str, str] = {
    "JaCoCo Coverage": "jacoco",
    "PITest": "pitest",
    "Checkstyle": "checkstyle",
    "PMD": "pmd",
    "SpotBugs": "spotbugs",
    "OWASP Dependency-Check": "owasp",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
    "SBOM": "sbom",
    "jqwik": "jqwik",
    "CodeQL": "codeql",
    "Docker": "docker",
}

PYTHON_SUMMARY_MAP: dict[str, str] = {
    "pytest": "pytest",
    "mutmut": "mutmut",
    "Ruff": "ruff",
    "Black": "black",
    "isort": "isort",
    "mypy": "mypy",
    "Bandit": "bandit",
    "pip-audit": "pip_audit",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
    "Hypothesis": "hypothesis",
    "CodeQL": "codeql",
    "SBOM": "sbom",
    "Docker": "docker",
}

# =============================================================================
# ARTIFACT PATTERNS (from report_validator package)
# Artifact patterns used for backup validation when metrics are missing
# =============================================================================

JAVA_ARTIFACTS: dict[str, list[str]] = {
    "jacoco": ["**/target/site/jacoco/jacoco.xml"],
    "checkstyle": ["**/checkstyle-result.xml"],
    "spotbugs": ["**/spotbugsXml.xml"],
    "pmd": ["**/pmd.xml"],
    "owasp": ["**/dependency-check-report.json"],
    "pitest": ["**/target/pit-reports/mutations.xml"],
    "semgrep": ["**/semgrep-report.json"],
    "sbom": ["**/sbom*.json"],
    "trivy": ["**/trivy-report.json"],
}

PYTHON_ARTIFACTS: dict[str, list[str]] = {
    "pytest": ["**/coverage.xml", "**/test-results.xml", "**/pytest-junit.xml"],
    "ruff": ["**/ruff-report.json"],
    "bandit": ["**/bandit-report.json"],
    "pip_audit": ["**/pip-audit-report.json"],
    "black": ["**/black-output.txt"],
    "isort": ["**/isort-output.txt"],
    "mypy": ["**/mypy-output.txt"],
    "mutmut": ["**/mutmut-run.log"],
    "hypothesis": ["**/hypothesis-output.txt"],
    "semgrep": ["**/semgrep-report.json"],
    "sbom": ["**/sbom*.json"],
    "trivy": ["**/trivy-report.json"],
}

# =============================================================================
# TOOL ADAPTERS (Part 5.3: Consolidate special-case handling)
# Each tool's configuration extraction and gate evaluation logic in one place.
# =============================================================================


@dataclass
class ToolAdapter:
    """Adapter for tool-specific configuration and gate evaluation.

    Attributes:
        name: Tool name (e.g., "pytest", "ruff")
        language: Language context ("python" or "java")
        config_extractor: Function to extract runner args from config dict.
                         Signature: (config, language) -> dict of extra kwargs
        gate_keys: Config keys that determine if gate should fail build.
                   If any key is True, gate is enabled.
        gate_key_defaults: Per-key defaults (overrides gate_default for specific keys).
        gate_default: Default gate behavior when no config is present.
    """

    name: str
    language: str
    config_extractor: Callable[[dict, str], dict[str, Any]] | None = None
    gate_keys: list[str] = field(default_factory=list)
    gate_key_defaults: dict[str, bool] = field(default_factory=dict)
    gate_default: bool = True


def _extract_tool_config(config: dict, language: str, tool: str) -> dict:
    """Get tool config dict from nested config structure."""
    return config.get(language, {}).get("tools", {}).get(tool, {}) or {}


# -----------------------------------------------------------------------------
# Python Tool Adapters
# -----------------------------------------------------------------------------


def _pytest_config(config: dict, language: str) -> dict[str, Any]:
    """Extract pytest-specific runner arguments."""
    cfg = _extract_tool_config(config, language, "pytest")
    if not isinstance(cfg, dict):
        cfg = {}
    args_value = cfg.get("args")
    args: list[str] = []
    if isinstance(args_value, str):
        args = [part for part in shlex.split(args_value) if part]
    elif isinstance(args_value, list):
        args = [str(part) for part in args_value if str(part)]

    env_value = cfg.get("env")
    env: dict[str, str] = {}
    if isinstance(env_value, dict):
        for key, value in env_value.items():
            if value is None:
                continue
            env[str(key)] = str(value)

    return {
        "fail_fast": bool(cfg.get("fail_fast", False)),
        "args": args,
        "env": env,
    }


def _mutmut_config(config: dict, language: str) -> dict[str, Any]:
    """Extract mutmut-specific runner arguments."""
    cfg = _extract_tool_config(config, language, "mutmut")
    timeout_minutes = cfg.get("timeout_minutes", 15)
    return {"timeout_seconds": int(timeout_minutes) * 60}


def _sbom_config(config: dict, language: str) -> dict[str, Any]:
    """Extract SBOM-specific runner arguments."""
    cfg = _extract_tool_config(config, language, "sbom")
    if not isinstance(cfg, dict):
        cfg = {}
    return {"sbom_format": cfg.get("format", "cyclonedx")}


def _docker_config(config: dict, language: str) -> dict[str, Any]:
    """Extract docker-specific runner arguments."""
    cfg = _extract_tool_config(config, language, "docker")
    if not isinstance(cfg, dict):
        cfg = {}
    return {
        "compose_file": cfg.get("compose_file", "docker-compose.yml"),
        "health_endpoint": cfg.get("health_endpoint"),
        "health_timeout": cfg.get("health_timeout", 300),
    }


# -----------------------------------------------------------------------------
# Java Tool Adapters
# -----------------------------------------------------------------------------


def _owasp_config(config: dict, language: str) -> dict[str, Any]:
    """Extract OWASP-specific runner arguments."""
    cfg = _extract_tool_config(config, language, "owasp")
    return {
        "needs_build_tool": True,
        "use_nvd_api_key": bool(cfg.get("use_nvd_api_key", True)),
    }


def _build_tool_config(config: dict, language: str) -> dict[str, Any]:
    """Extract build-tool-dependent runner arguments (pitest, checkstyle, etc.)."""
    # Build tool is passed separately, not from config
    return {"needs_build_tool": True}


# -----------------------------------------------------------------------------
# Tool Adapter Registry
# Key: (tool_name, language) -> ToolAdapter
# -----------------------------------------------------------------------------

TOOL_ADAPTERS: dict[tuple[str, str], ToolAdapter] = {
    # Python tools with special config extraction
    ("pytest", "python"): ToolAdapter(
        name="pytest",
        language="python",
        config_extractor=_pytest_config,
    ),
    ("mutmut", "python"): ToolAdapter(
        name="mutmut",
        language="python",
        config_extractor=_mutmut_config,
    ),
    ("sbom", "python"): ToolAdapter(
        name="sbom",
        language="python",
        config_extractor=_sbom_config,
    ),
    ("docker", "python"): ToolAdapter(
        name="docker",
        language="python",
        config_extractor=_docker_config,
    ),
    # Python tools with gate configuration
    ("ruff", "python"): ToolAdapter(
        name="ruff",
        language="python",
        gate_keys=["fail_on_error"],
        gate_default=True,
    ),
    ("black", "python"): ToolAdapter(
        name="black",
        language="python",
        gate_keys=["fail_on_format_issues"],
        gate_default=True,
    ),
    ("isort", "python"): ToolAdapter(
        name="isort",
        language="python",
        gate_keys=["fail_on_issues"],
        gate_default=True,
    ),
    ("bandit", "python"): ToolAdapter(
        name="bandit",
        language="python",
        gate_keys=["fail_on_high", "fail_on_medium", "fail_on_low"],
        gate_key_defaults={"fail_on_high": True, "fail_on_medium": False, "fail_on_low": False},
        gate_default=False,
    ),
    ("pip_audit", "python"): ToolAdapter(
        name="pip_audit",
        language="python",
        gate_keys=["fail_on_vuln"],
        gate_default=True,
    ),
    ("semgrep", "python"): ToolAdapter(
        name="semgrep",
        language="python",
        gate_keys=["fail_on_findings"],
        gate_default=True,
    ),
    ("trivy", "python"): ToolAdapter(
        name="trivy",
        language="python",
        gate_keys=["fail_on_critical", "fail_on_high"],
        gate_default=True,
    ),
    # Java tools with special config extraction
    ("sbom", "java"): ToolAdapter(
        name="sbom",
        language="java",
        config_extractor=_sbom_config,
    ),
    ("docker", "java"): ToolAdapter(
        name="docker",
        language="java",
        config_extractor=_docker_config,
    ),
    ("owasp", "java"): ToolAdapter(
        name="owasp",
        language="java",
        config_extractor=_owasp_config,
    ),
    ("pitest", "java"): ToolAdapter(
        name="pitest",
        language="java",
        config_extractor=_build_tool_config,
    ),
    ("checkstyle", "java"): ToolAdapter(
        name="checkstyle",
        language="java",
        config_extractor=_build_tool_config,
        gate_keys=["fail_on_violation"],
        gate_default=True,
    ),
    ("spotbugs", "java"): ToolAdapter(
        name="spotbugs",
        language="java",
        config_extractor=_build_tool_config,
        gate_keys=["fail_on_error"],
        gate_default=True,
    ),
    ("pmd", "java"): ToolAdapter(
        name="pmd",
        language="java",
        config_extractor=_build_tool_config,
        gate_keys=["fail_on_violation"],
        gate_default=True,
    ),
    # Java tools with gate configuration only
    ("semgrep", "java"): ToolAdapter(
        name="semgrep",
        language="java",
        gate_keys=["fail_on_findings"],
        gate_default=True,
    ),
    ("trivy", "java"): ToolAdapter(
        name="trivy",
        language="java",
        gate_keys=["fail_on_critical", "fail_on_high"],
        gate_default=True,
    ),
}


def get_tool_adapter(tool: str, language: str) -> ToolAdapter | None:
    """Get adapter for a tool, or None if no special handling needed."""
    return TOOL_ADAPTERS.get((tool, language))


def get_tool_runner_args(
    config: dict[str, Any],
    tool: str,
    language: str,
) -> dict[str, Any]:
    """Extract tool-specific runner arguments from config.

    Returns empty dict if tool has no special config requirements.
    """
    adapter = get_tool_adapter(tool, language)
    if adapter and adapter.config_extractor:
        return adapter.config_extractor(config, language)
    return {}


def is_tool_gate_enabled(
    config: dict[str, Any],
    tool: str,
    language: str,
) -> bool:
    """Check if a tool's gate should fail the build.

    Uses tool adapter registry to determine gate behavior based on config keys.
    Returns True (fail on issues) by default.
    """
    adapter = get_tool_adapter(tool, language)
    if not adapter or not adapter.gate_keys:
        return True  # Default: gate enabled

    tool_config = _extract_tool_config(config, language, tool)
    if not isinstance(tool_config, dict):
        return adapter.gate_default

    # Check if any gate key is enabled (using per-key defaults if available)
    for key in adapter.gate_keys:
        key_default = adapter.gate_key_defaults.get(key, adapter.gate_default)
        if tool_config.get(key, key_default):
            return True

    return False


# =============================================================================
# TOOL RUNNER REGISTRY (Part 7.6.2: Centralize runner imports)
# Lazy-loaded runner functions to avoid circular imports.
# =============================================================================

_PYTHON_RUNNER_CACHE: dict[str, Callable[..., Any]] | None = None
_JAVA_RUNNER_CACHE: dict[str, Callable[..., Any]] | None = None


def _load_python_runners() -> dict[str, Callable[..., Any]]:
    """Lazy-load Python tool runners from ci_runner module."""
    global _PYTHON_RUNNER_CACHE
    if _PYTHON_RUNNER_CACHE is not None:
        return _PYTHON_RUNNER_CACHE
    from cihub.ci_runner import (
        run_bandit,
        run_black,
        run_docker,
        run_isort,
        run_mutmut,
        run_mypy,
        run_pip_audit,
        run_pytest,
        run_ruff,
        run_sbom,
        run_semgrep,
        run_trivy,
    )

    _PYTHON_RUNNER_CACHE = {
        "pytest": run_pytest,
        "ruff": run_ruff,
        "black": run_black,
        "isort": run_isort,
        "mypy": run_mypy,
        "bandit": run_bandit,
        "pip_audit": run_pip_audit,
        "mutmut": run_mutmut,
        "sbom": run_sbom,
        "semgrep": run_semgrep,
        "trivy": run_trivy,
        "docker": run_docker,
    }
    return _PYTHON_RUNNER_CACHE


def _load_java_runners() -> dict[str, Callable[..., Any]]:
    """Lazy-load Java tool runners from ci_runner module.

    NOTE: Includes 'build' runner even though JAVA_TOOLS doesn't list it.
    JAVA_TOOLS is for reporting/gates; runners are execution functions.
    The 'build' step runs before tool iterations in _run_java_tools().
    """
    global _JAVA_RUNNER_CACHE
    if _JAVA_RUNNER_CACHE is not None:
        return _JAVA_RUNNER_CACHE
    from cihub.ci_runner import (
        run_checkstyle,
        run_docker,
        run_jacoco,
        run_java_build,
        run_owasp,
        run_pitest,
        run_pmd,
        run_sbom,
        run_semgrep,
        run_spotbugs,
        run_trivy,
    )

    _JAVA_RUNNER_CACHE = {
        "build": run_java_build,  # Special: not in JAVA_TOOLS but needed for execution
        "jacoco": run_jacoco,
        "pitest": run_pitest,
        "checkstyle": run_checkstyle,
        "spotbugs": run_spotbugs,
        "pmd": run_pmd,
        "owasp": run_owasp,
        "semgrep": run_semgrep,
        "trivy": run_trivy,
        "sbom": run_sbom,
        "docker": run_docker,
    }
    return _JAVA_RUNNER_CACHE


def get_runner(tool: str, language: str) -> Callable[..., Any] | None:
    """Get runner function for a tool by name and language.

    Args:
        tool: Tool name (e.g., "pytest", "ruff", "jacoco")
        language: Language context ("python" or "java")

    Returns:
        Runner function or None if tool has no runner (e.g., codeql, hypothesis)
    """
    if language == "python":
        return _load_python_runners().get(tool)
    elif language == "java":
        return _load_java_runners().get(tool)
    return None


def get_runners(language: str) -> dict[str, Callable[..., Any]]:
    """Get all runners for a language.

    Args:
        language: Language context ("python" or "java")

    Returns:
        Dictionary mapping tool names to runner functions.
        Returns a copy to prevent callers from mutating global state.
    """
    if language == "python":
        return dict(_load_python_runners())
    elif language == "java":
        return dict(_load_java_runners())
    return {}


# =============================================================================
# CUSTOM TOOL HELPERS
# =============================================================================


def is_custom_tool(tool_name: str) -> bool:
    """Check if a tool name is a custom tool (x- prefix).

    Args:
        tool_name: Tool name to check

    Returns:
        True if tool name starts with x- and matches the valid pattern
    """
    return bool(CUSTOM_TOOL_PATTERN.match(tool_name))


def get_custom_tools_from_config(config: dict[str, Any], language: str) -> dict[str, Any]:
    """Extract custom tools from config for a language.

    Args:
        config: Full config dict
        language: Language context ("python" or "java")

    Returns:
        Dict of custom tool names to their configs
    """
    tools = config.get(language, {}).get("tools", {})
    if not isinstance(tools, dict):
        return {}
    return {name: cfg for name, cfg in tools.items() if is_custom_tool(name)}


def get_all_tools_from_config(config: dict[str, Any], language: str) -> list[str]:
    """Get all tool names (built-in + custom) from config.

    Args:
        config: Full config dict
        language: Language context ("python" or "java")

    Returns:
        List of all tool names (built-in first, then custom sorted)
    """
    builtin = PYTHON_TOOLS if language == "python" else JAVA_TOOLS
    custom = sorted(get_custom_tools_from_config(config, language).keys())
    return list(builtin) + custom


def is_tool_enabled(config: dict[str, Any], tool: str, language: str, *, default: bool = False) -> bool:
    """Check if a tool is enabled in config.

    Aligned with canonical tool_enabled in cihub/config/normalize.py.

    Args:
        config: Full config dict
        tool: Tool name
        language: Language context ("python" or "java")
        default: Default value if tool config is missing or has no enabled key.
                 For custom tools (x-* prefix), schema specifies default=True,
                 so callers should pass default=True for custom tools.

    Returns:
        True if tool is enabled
    """
    tool_cfg = config.get(language, {}).get("tools", {}).get(tool)
    if tool_cfg is None:
        return default
    if isinstance(tool_cfg, bool):
        return tool_cfg
    if isinstance(tool_cfg, dict):
        enabled = tool_cfg.get("enabled")
        if isinstance(enabled, bool):
            return enabled
        # If enabled not specified, use default (custom tools schema says default=true)
        return default
    return default


def get_custom_tool_command(config: dict[str, Any], tool: str, language: str) -> str | None:
    """Get the command for a custom tool.

    Args:
        config: Full config dict
        tool: Custom tool name (must start with x-)
        language: Language context ("python" or "java")

    Returns:
        Command string or None if not configured
    """
    if not is_custom_tool(tool):
        return None
    tool_cfg = config.get(language, {}).get("tools", {}).get(tool)
    if isinstance(tool_cfg, dict):
        return tool_cfg.get("command")
    return None
