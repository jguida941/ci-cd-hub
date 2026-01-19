"""Python language strategy implementation.

This module implements the LanguageStrategy interface for Python projects,
delegating to existing implementations in ci_engine and ci_runner modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from cihub.core.ci_report import RunContext, build_python_report, resolve_thresholds
from cihub.core.gate_specs import PYTHON_THRESHOLDS
from cihub.core.gate_specs import PYTHON_TOOLS as PYTHON_TOOL_SPECS
from cihub.tools.registry import PYTHON_TOOLS, get_runners

from .base import LanguageStrategy

if TYPE_CHECKING:
    from cihub.core.gate_specs import ThresholdSpec, ToolSpec


class PythonStrategy(LanguageStrategy):
    """Strategy implementation for Python CI pipelines.

    Delegates to existing implementations:
    - Tool execution: cihub.services.ci_engine.python_tools._run_python_tools
    - Gate evaluation: cihub.services.ci_engine.gates._evaluate_python_gates
    - Report building: cihub.core.ci_report.build_python_report
    - Threshold resolution: cihub.core.ci_report.resolve_thresholds
    """

    @property
    def name(self) -> str:
        return "python"

    def get_runners(self) -> dict[str, Callable[..., Any]]:
        """Return Python tool runners from centralized registry."""
        return get_runners("python")

    def get_default_tools(self) -> list[str]:
        """Return Python tools from registry.

        NOTE: This includes virtual tools like 'hypothesis' that don't have runners.
        See get_virtual_tools() for the distinction.
        """
        return list(PYTHON_TOOLS)

    def get_virtual_tools(self) -> list[str]:
        """Return Python virtual tools that mirror parent tool results.

        'hypothesis' is a virtual tool that mirrors 'pytest' results.
        It doesn't have a runner - property-based testing is detected
        from pytest output when hypothesis is installed.
        """
        return ["hypothesis", "codeql"]

    def get_allowed_kwargs(self) -> frozenset[str]:
        """Python run_tools() accepts install_deps kwarg."""
        return frozenset({"install_deps"})

    def get_thresholds(self) -> tuple[ThresholdSpec, ...]:
        """Return Python threshold specifications."""
        return PYTHON_THRESHOLDS

    def get_tool_specs(self) -> tuple[ToolSpec, ...]:
        """Return Python tool specifications."""
        return PYTHON_TOOL_SPECS

    def run_tools(
        self,
        config: dict[str, Any],
        repo_path: Path,
        workdir: str,
        output_dir: Path,
        problems: list[dict[str, Any]],
        *,
        install_deps: bool = False,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
        """Execute Python tools by delegating to existing implementation.

        Args:
            config: CI configuration dictionary
            repo_path: Path to the repository root
            workdir: Working directory relative to repo_path
            output_dir: Directory for tool output artifacts
            problems: List to append warnings/errors to
            install_deps: If True, install dependencies before running tools
        """
        # Import here to avoid circular dependencies
        from cihub.services.ci_engine.python_tools import (
            _install_python_dependencies,
            _run_python_tools,
        )

        # Install dependencies only if requested
        if install_deps:
            workdir_path = repo_path / workdir
            _install_python_dependencies(config, workdir_path, problems)

        # Run tools
        runners = self.get_runners()
        return _run_python_tools(config, repo_path, workdir, output_dir, problems, runners)

    def evaluate_gates(
        self,
        report: dict[str, Any],
        thresholds: dict[str, Any],
        tools_configured: dict[str, bool],
        config: dict[str, Any],
    ) -> list[str]:
        """Evaluate Python quality gates by delegating to existing implementation."""
        # Import here to avoid circular dependencies
        from cihub.services.ci_engine.gates import _evaluate_python_gates

        return _evaluate_python_gates(report, thresholds, tools_configured, config)

    def resolve_thresholds(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve Python thresholds from configuration."""
        return resolve_thresholds(config, "python")

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
        """Build Python CI report."""
        return build_python_report(
            config,
            tool_results,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
            tools_require_run=tools_require_run,
        )

    def detect(self, repo_path: Path) -> float:
        """Detect if this is a Python project.

        Returns confidence based on presence of Python markers:
        - pyproject.toml: 0.9
        - setup.py: 0.8
        - requirements.txt: 0.7
        - *.py files: 0.5
        """
        if (repo_path / "pyproject.toml").exists():
            return 0.9
        if (repo_path / "setup.py").exists():
            return 0.8
        if (repo_path / "requirements.txt").exists():
            return 0.7
        if any(repo_path.glob("*.py")):
            return 0.5
        return 0.0

    def detect_reasons(self, repo_path: Path) -> list[str]:
        reasons: list[str] = []
        if (repo_path / "pyproject.toml").exists():
            reasons.append("pyproject.toml")
        if (repo_path / "setup.py").exists():
            reasons.append("setup.py")
        if (repo_path / "requirements.txt").exists():
            reasons.append("requirements.txt")
        if any(repo_path.glob("*.py")):
            reasons.append("*.py")
        return reasons

    def get_run_kwargs(
        self,
        config: dict[str, Any],
        **caller_kwargs: Any,
    ) -> dict[str, Any]:
        """Get Python-specific kwargs for run_tools().

        Python uses install_deps to control dependency installation.
        Filters to only allowed kwargs for safety.
        """
        # Use base class filtering
        return super().get_run_kwargs(config, **caller_kwargs)

    def get_docker_compose_default(self) -> str | None:
        """Python defaults to docker-compose.yml when docker is configured."""
        return "docker-compose.yml"

    def get_context_extras(
        self,
        config: dict[str, Any],
        workdir_path: Path,
    ) -> dict[str, Any]:
        """Python has no extra context fields."""
        return {}
