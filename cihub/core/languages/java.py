"""Java language strategy implementation.

This module implements the LanguageStrategy interface for Java projects,
delegating to existing implementations in ci_engine and ci_runner modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from cihub.core.ci_report import RunContext, build_java_report, resolve_thresholds
from cihub.core.gate_specs import JAVA_THRESHOLDS
from cihub.core.gate_specs import JAVA_TOOLS as JAVA_TOOL_SPECS
from cihub.tools.registry import JAVA_TOOLS

from .base import LanguageStrategy

if TYPE_CHECKING:
    from cihub.core.gate_specs import ThresholdSpec, ToolSpec


class JavaStrategy(LanguageStrategy):
    """Strategy implementation for Java CI pipelines.

    Delegates to existing implementations:
    - Tool execution: cihub.services.ci_engine.java_tools._run_java_tools
    - Gate evaluation: cihub.services.ci_engine.gates._evaluate_java_gates
    - Report building: cihub.core.ci_report.build_java_report
    - Threshold resolution: cihub.core.ci_report.resolve_thresholds
    """

    @property
    def name(self) -> str:
        return "java"

    def get_runners(self) -> dict[str, Callable[..., Any]]:
        """Return Java tool runners from ci_runner module."""
        # Import here to avoid circular dependencies
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

        return {
            "build": run_java_build,
            "jacoco": run_jacoco,
            "pitest": run_pitest,
            "checkstyle": run_checkstyle,
            "spotbugs": run_spotbugs,
            "pmd": run_pmd,
            "owasp": run_owasp,
            "sbom": run_sbom,
            "semgrep": run_semgrep,
            "trivy": run_trivy,
            "docker": run_docker,
        }

    def get_default_tools(self) -> list[str]:
        """Return Java tools from registry.

        NOTE: This includes virtual tools like 'jqwik' that don't have runners.
        See get_virtual_tools() for the distinction.
        """
        return list(JAVA_TOOLS)

    def get_virtual_tools(self) -> list[str]:
        """Return Java virtual tools that mirror parent tool results.

        'jqwik' is a virtual tool that mirrors 'build' results.
        It doesn't have a runner - property-based testing is detected
        from build output when jqwik is in dependencies.
        """
        return ["jqwik", "codeql"]

    def get_allowed_kwargs(self) -> frozenset[str]:
        """Java run_tools() accepts build_tool kwarg."""
        return frozenset({"build_tool"})

    def get_thresholds(self) -> tuple[ThresholdSpec, ...]:
        """Return Java threshold specifications."""
        return JAVA_THRESHOLDS

    def get_tool_specs(self) -> tuple[ToolSpec, ...]:
        """Return Java tool specifications."""
        return JAVA_TOOL_SPECS

    def run_tools(
        self,
        config: dict[str, Any],
        repo_path: Path,
        workdir: str,
        output_dir: Path,
        problems: list[dict[str, Any]],
        *,
        build_tool: str | None = None,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
        """Execute Java tools by delegating to existing implementation.

        Args:
            config: CI configuration dictionary
            repo_path: Path to the repository root
            workdir: Working directory relative to repo_path
            output_dir: Directory for tool output artifacts
            problems: List to append warnings/errors to
            build_tool: Build tool to use (maven/gradle), auto-detected if None
        """
        # Import here to avoid circular dependencies
        from cihub.services.ci_engine.java_tools import _run_java_tools

        # Detect build tool if not provided by checking for build files
        if build_tool is None:
            workdir_path = repo_path / workdir
            # Check for Gradle files first (more specific)
            if (
                (workdir_path / "build.gradle").exists()
                or (workdir_path / "build.gradle.kts").exists()
                or (workdir_path / "settings.gradle").exists()
                or (workdir_path / "settings.gradle.kts").exists()
            ):
                build_tool = "gradle"
            else:
                # Default to maven (pom.xml or unknown)
                build_tool = "maven"

        runners = self.get_runners()
        return _run_java_tools(config, repo_path, workdir, output_dir, build_tool, problems, runners)

    def evaluate_gates(
        self,
        report: dict[str, Any],
        thresholds: dict[str, Any],
        tools_configured: dict[str, bool],
        config: dict[str, Any],
    ) -> list[str]:
        """Evaluate Java quality gates by delegating to existing implementation."""
        # Import here to avoid circular dependencies
        from cihub.services.ci_engine.gates import _evaluate_java_gates

        return _evaluate_java_gates(report, thresholds, tools_configured, config)

    def resolve_thresholds(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve Java thresholds from configuration."""
        return resolve_thresholds(config, "java")

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
        """Build Java CI report."""
        return build_java_report(
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
        """Detect if this is a Java project.

        Returns confidence based on presence of Java markers:
        - pom.xml: 0.9 (Maven)
        - build.gradle or build.gradle.kts: 0.9 (Gradle)
        - settings.gradle: 0.8 (Gradle multi-module)
        - *.java files in src/: 0.6
        """
        if (repo_path / "pom.xml").exists():
            return 0.9
        if (repo_path / "build.gradle").exists():
            return 0.9
        if (repo_path / "build.gradle.kts").exists():
            return 0.9
        if (repo_path / "settings.gradle").exists():
            return 0.8
        if (repo_path / "settings.gradle.kts").exists():
            return 0.8
        src_dir = repo_path / "src"
        if src_dir.exists() and any(src_dir.rglob("*.java")):
            return 0.6
        return 0.0

    def get_run_kwargs(
        self,
        config: dict[str, Any],
        **caller_kwargs: Any,
    ) -> dict[str, Any]:
        """Get Java-specific kwargs for run_tools().

        Java uses build_tool to specify maven/gradle. Auto-detected if not provided.
        Filters to only allowed kwargs for safety.
        """
        # Filter caller kwargs using base class
        kwargs = super().get_run_kwargs(config, **caller_kwargs)

        # Extract build_tool from config if not provided by caller
        if "build_tool" not in kwargs:
            build_tool = config.get("java", {}).get("build_tool", "").strip().lower()
            if build_tool and build_tool in {"maven", "gradle"}:
                kwargs["build_tool"] = build_tool
            # If invalid or empty, leave it out - strategy.run_tools() will auto-detect

        return kwargs

    def get_docker_compose_default(self) -> str | None:
        """Java has no default docker-compose file."""
        return None

    def get_context_extras(
        self,
        config: dict[str, Any],
        workdir_path: Path,
    ) -> dict[str, Any]:
        """Java adds build_tool and project_type to context."""
        from cihub.utils import detect_java_project_type

        # Get build_tool from config, default to maven
        build_tool = config.get("java", {}).get("build_tool", "maven").strip().lower() or "maven"
        if build_tool not in {"maven", "gradle"}:
            build_tool = "maven"

        return {
            "build_tool": build_tool,
            "project_type": detect_java_project_type(workdir_path),
        }
