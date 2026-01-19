"""Base class for language-specific CI strategies.

This module defines the LanguageStrategy abstract base class that encapsulates
all language-specific behavior for the CI engine. By implementing this interface,
new languages can be added without modifying existing code.

Design rationale (per CLEAN_CODE.md Part 2.1):
- Eliminates 46+ if-language conditionals scattered across 20 files
- Adding Go/Rust/TypeScript = one new file, zero modifications to existing code
- Testing: mock strategy, verify calls
- No more duplicate gate logic
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from cihub.core.ci_report import RunContext


class LanguageStrategy(ABC):
    """Abstract base class for language-specific CI behavior.

    Each language (Python, Java, etc.) implements this interface to provide:
    - Tool runner mappings
    - Default tool execution order
    - Gate evaluation logic
    - Language detection heuristics
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Language identifier (e.g., 'python', 'java').

        This is used as the key in the strategy registry and must match
        the language value in configuration files.
        """

    @abstractmethod
    def get_runners(self) -> dict[str, Callable[..., Any]]:
        """Return tool name -> runner function mapping.

        NOTE: This returns only tools with actual runner functions.
        Derived/virtual tools (e.g., hypothesis, jqwik) and external tools
        (e.g., codeql) are NOT included here - they are handled specially
        in run_tools() via delegation to existing _run_*_tools() functions.

        Returns:
            Dictionary mapping tool names (e.g., 'pytest', 'ruff') to their
            runner functions from cihub.core.ci_runner.
        """

    @abstractmethod
    def get_default_tools(self) -> list[str]:
        """Return all tools for this language (from registry).

        NOTE: This returns ALL tools in scope for the language, including:
        - Runnable tools (have entries in get_runners())
        - Derived/virtual tools (e.g., hypothesis mirrors pytest, jqwik mirrors build)
        - External tools (e.g., codeql, tracked via env vars)

        Returns:
            List of tool names from the tool registry for this language.
        """

    @abstractmethod
    def get_thresholds(self) -> tuple[Any, ...]:
        """Return threshold specifications for this language.

        Returns:
            Tuple of ThresholdSpec objects defining quality gates.
        """

    @abstractmethod
    def get_tool_specs(self) -> tuple[Any, ...]:
        """Return tool specifications for this language.

        Returns:
            Tuple of ToolSpec objects defining available tools.
        """

    @abstractmethod
    def run_tools(
        self,
        config: dict[str, Any],
        repo_path: Path,
        workdir: str,
        output_dir: Path,
        problems: list[dict[str, Any]],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
        """Execute all enabled tools, return results.

        Args:
            config: CI configuration dictionary
            repo_path: Path to the repository root
            workdir: Working directory relative to repo_path
            output_dir: Directory for tool output artifacts
            problems: List to append warnings/errors to

        Returns:
            Tuple of (tool_outputs, tools_ran, tools_success) dictionaries.
        """

    @abstractmethod
    def evaluate_gates(
        self,
        report: dict[str, Any],
        thresholds: dict[str, Any],
        tools_configured: dict[str, bool],
        config: dict[str, Any],
    ) -> list[str]:
        """Evaluate quality gates, return list of failure messages.

        Args:
            report: The CI report with results and metrics
            thresholds: Effective threshold values
            tools_configured: Which tools are configured/enabled
            config: Full CI configuration

        Returns:
            List of gate failure messages. Empty list means all gates pass.
        """

    @abstractmethod
    def resolve_thresholds(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve effective threshold values from configuration.

        Args:
            config: CI configuration dictionary

        Returns:
            Dictionary of threshold keys to their effective values.
        """

    @abstractmethod
    def build_report(
        self,
        config: dict[str, Any],
        tool_results: dict[str, dict[str, Any]],
        tools_configured: dict[str, bool],
        tools_ran: dict[str, bool],
        tools_success: dict[str, bool],
        thresholds: dict[str, Any],
        context: RunContext,
        *,
        tools_require_run: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Build the CI report for this language.

        Args:
            config: CI configuration dictionary
            tool_results: Results from tool execution
            tools_configured: Which tools are configured
            tools_ran: Which tools actually ran
            tools_success: Which tools succeeded
            thresholds: Effective threshold values
            context: Run context with metadata
            tools_require_run: Tools with require_run_or_fail policy

        Returns:
            The complete CI report dictionary.
        """

    def detect(self, repo_path: Path) -> float:
        """Return confidence 0.0-1.0 that this language applies to the repo.

        Override this method to implement language detection heuristics.
        The strategy with the highest confidence above 0.5 wins.

        Args:
            repo_path: Path to the repository root

        Returns:
            Confidence score between 0.0 and 1.0
        """
        return 0.0

    def detect_reasons(self, repo_path: Path) -> list[str]:
        """Return detection markers found for this language.

        Used by CLI detection explain output. Defaults to empty list.
        """
        return []

    def get_allowed_kwargs(self) -> frozenset[str]:
        """Return the set of kwargs that run_tools() accepts.

        Override in subclasses to specify which kwargs are valid for run_tools().
        This enables safe filtering to prevent unexpected kwargs from being passed.

        Returns:
            Frozenset of allowed kwarg names
        """
        return frozenset()

    def get_run_kwargs(
        self,
        config: dict[str, Any],
        **caller_kwargs: Any,
    ) -> dict[str, Any]:
        """Get language-specific kwargs for run_tools(), merged with caller kwargs.

        Override this to provide language-specific parameters like install_deps (Python)
        or build_tool (Java). The base implementation filters to allowed kwargs.

        Args:
            config: CI configuration dictionary
            **caller_kwargs: Kwargs from the caller (e.g., install_deps from CLI)

        Returns:
            Merged dictionary of kwargs for run_tools(), filtered to allowed kwargs
        """
        allowed = self.get_allowed_kwargs()
        if not allowed:
            return dict(caller_kwargs)
        # Filter to only allowed kwargs to prevent unexpected parameters
        return {k: v for k, v in caller_kwargs.items() if k in allowed}

    def get_virtual_tools(self) -> list[str]:
        """Return tools that don't have runners but are tracked in reports.

        Virtual/derived tools mirror the results of their parent tools:
        - Python: 'hypothesis' mirrors 'pytest' (property-based testing)
        - Java: 'jqwik' mirrors 'build' (property-based testing)

        These tools are included in get_default_tools() but NOT in get_runners().
        This method makes that distinction explicit for documentation and safety.

        Returns:
            List of virtual tool names that have no runner
        """
        return []

    def get_docker_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Extract docker configuration for this language.

        Encapsulates language-specific docker config access. This moves the
        config[language].tools.docker extraction into the strategy.

        Args:
            config: CI configuration dictionary

        Returns:
            Dict with docker config keys: compose_file, health_endpoint, etc.
        """
        lang_cfg = config.get(self.name, {})
        if not isinstance(lang_cfg, dict):
            return {}
        tools_cfg = lang_cfg.get("tools", {})
        if not isinstance(tools_cfg, dict):
            return {}
        docker_cfg = tools_cfg.get("docker", {})
        if not isinstance(docker_cfg, dict):
            return {}
        return dict(docker_cfg)

    def get_docker_compose_default(self) -> str | None:
        """Get default docker-compose file for this language.

        Python defaults to 'docker-compose.yml', Java has no default.

        Returns:
            Default compose filename or None
        """
        return None

    def get_context_extras(
        self,
        config: dict[str, Any],
        workdir_path: Path,
    ) -> dict[str, Any]:
        """Get extra context fields for this language.

        Java adds build_tool and project_type. Python has none.

        Args:
            config: CI configuration dictionary
            workdir_path: Absolute path to working directory

        Returns:
            Dictionary of extra context fields
        """
        return {}
