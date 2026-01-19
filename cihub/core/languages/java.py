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
from cihub.tools.registry import JAVA_TOOLS, get_runners

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
        """Return Java tool runners from centralized registry."""
        return get_runners("java")

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
        workdir_path = repo_path / workdir
        if build_tool is None:
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

        # Auto-fix build files before running tools (CLI-first architecture)
        self._auto_fix_build_files(workdir_path, config, build_tool, problems)

        runners = self.get_runners()
        return _run_java_tools(config, repo_path, workdir, output_dir, build_tool, problems, runners)

    def _auto_fix_build_files(
        self,
        workdir_path: Path,
        config: dict[str, Any],
        build_tool: str,
        problems: list[dict[str, Any]],
    ) -> None:
        """Auto-fix build files to add missing plugins before tool execution.

        This ensures Gradle/Maven projects have the required plugins declared
        so tools can produce output files. Part of CLI-first architecture.
        """
        if build_tool == "gradle":
            self._auto_fix_gradle(workdir_path, config, problems)
        elif build_tool == "maven":
            self._auto_fix_maven(workdir_path, config, problems)

    def _auto_fix_gradle(
        self,
        workdir_path: Path,
        config: dict[str, Any],
        problems: list[dict[str, Any]],
    ) -> None:
        """Auto-fix Gradle build.gradle to add missing plugins."""
        build_path = workdir_path / "build.gradle"
        if not build_path.exists():
            return  # Kotlin DSL or missing - skip

        try:
            from cihub.utils.java_gradle import (
                GRADLE_TOOL_PLUGINS,
                get_gradle_tool_flags,
                insert_configs_into_gradle,
                insert_plugins_into_gradle,
                load_gradle_config_snippets,
                load_gradle_plugin_snippets,
                parse_gradle_plugins,
            )

            # Check build_tool - must be gradle
            build_tool = config.get("java", {}).get("build_tool", "maven")
            if build_tool != "gradle":
                return

            # Parse existing plugins directly from the build.gradle
            declared_plugins, error = parse_gradle_plugins(build_path)
            if error:
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Gradle auto-fix: {error}",
                        "code": "CIHUB-CI-GRADLE-AUTOFIX-FAILED",
                    }
                )
                return

            # Check which tools are enabled and which plugins are missing
            tool_flags = get_gradle_tool_flags(config)
            missing_plugins = []
            enabled_plugins = []
            for tool, enabled in tool_flags.items():
                if tool not in GRADLE_TOOL_PLUGINS or not enabled:
                    continue
                plugin_id = GRADLE_TOOL_PLUGINS[tool]
                enabled_plugins.append(plugin_id)
                if plugin_id not in declared_plugins:
                    missing_plugins.append(plugin_id)

            plugins_added = 0
            configs_added = 0
            files_added = 0

            # Add missing plugins and their config blocks
            if missing_plugins:
                plugin_snippets = load_gradle_plugin_snippets()
                build_text = build_path.read_text(encoding="utf-8")
                updated_text, success = insert_plugins_into_gradle(build_text, missing_plugins, plugin_snippets)

                if success and updated_text != build_text:
                    plugins_added = len(missing_plugins)
                    # Also add corresponding config blocks for added plugins
                    config_snippets = load_gradle_config_snippets()
                    updated_text, config_success = insert_configs_into_gradle(
                        updated_text, missing_plugins, config_snippets
                    )
                    if config_success:
                        configs_added = len([p for p in missing_plugins if p in config_snippets])

                    build_path.write_text(updated_text, encoding="utf-8")

            # Always scaffold missing config files for ALL enabled plugins (not just newly added)
            files_added = self._scaffold_gradle_config_files(workdir_path, enabled_plugins, tool_flags)

            # Report what was fixed
            if plugins_added or configs_added or files_added:
                msg_parts = []
                if plugins_added:
                    msg_parts.append(f"{plugins_added} missing plugins")
                if configs_added:
                    msg_parts.append(f"{configs_added} config blocks")
                if files_added:
                    msg_parts.append(f"{files_added} config files")
                problems.append(
                    {
                        "severity": "info",
                        "message": f"Auto-fixed build.gradle: added {', '.join(msg_parts)}",
                        "code": "CIHUB-CI-GRADLE-AUTOFIX",
                    }
                )
        except Exception as exc:  # noqa: BLE001 - best effort, don't break CI
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Gradle auto-fix failed: {exc}",
                    "code": "CIHUB-CI-GRADLE-AUTOFIX-FAILED",
                }
            )

    def _scaffold_gradle_config_files(
        self,
        workdir_path: Path,
        added_plugins: list[str],
        tool_flags: dict[str, bool],
    ) -> int:
        """Scaffold missing config files for Gradle plugins.

        Returns:
            Number of files added
        """
        import shutil

        from cihub.utils.paths import hub_root

        files_added = 0
        templates_dir = hub_root() / "templates" / "java" / "config"

        # Map of plugin IDs to their required config file paths
        plugin_config_files: dict[str, list[tuple[str, str]]] = {
            # List of (relative_target_path, template_subpath) tuples
            "checkstyle": [("config/checkstyle/checkstyle.xml", "checkstyle/checkstyle.xml")],
            "org.owasp.dependencycheck": [("config/owasp/suppressions.xml", "owasp/suppressions.xml")],
        }

        for plugin_id in added_plugins:
            if plugin_id not in plugin_config_files:
                continue

            for target_rel, template_subpath in plugin_config_files[plugin_id]:
                target_path = workdir_path / target_rel
                template_path = templates_dir / template_subpath

                # Only scaffold if template exists and target doesn't
                if template_path.exists() and not target_path.exists():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(template_path, target_path)
                    files_added += 1

        return files_added

    def _auto_fix_maven(
        self,
        workdir_path: Path,
        config: dict[str, Any],
        problems: list[dict[str, Any]],
    ) -> None:
        """Auto-fix Maven pom.xml to add missing plugins."""
        pom_path = workdir_path / "pom.xml"
        if not pom_path.exists():
            return

        try:
            from cihub.utils.java_pom import (
                JAVA_TOOL_PLUGINS,
                get_java_tool_flags,
                insert_plugins_into_pom,
                load_plugin_snippets,
                parse_pom_plugins,
                plugin_matches,
            )

            # Check build_tool - must be maven
            build_tool = config.get("java", {}).get("build_tool", "maven")
            if build_tool != "maven":
                return

            # Parse existing plugins directly from the pom.xml
            plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom_path)
            if error:
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Maven auto-fix: {error}",
                        "code": "CIHUB-CI-MAVEN-AUTOFIX-FAILED",
                    }
                )
                return

            # Check which tools are enabled and which plugins are missing
            tool_flags = get_java_tool_flags(config)
            missing_plugins = []
            for tool, enabled in tool_flags.items():
                if tool not in JAVA_TOOL_PLUGINS or not enabled:
                    continue
                group_id, artifact_id = JAVA_TOOL_PLUGINS[tool]
                if plugin_matches(plugins, group_id, artifact_id):
                    continue
                if plugin_matches(plugins_mgmt, group_id, artifact_id):
                    continue  # In pluginManagement is ok for auto-fix purposes
                missing_plugins.append((group_id, artifact_id))

            if not missing_plugins:
                return  # Nothing to fix

            # Load snippets and fix
            snippets = load_plugin_snippets()
            blocks = []
            for plugin_id in missing_plugins:
                snippet = snippets.get(plugin_id)
                if snippet:
                    blocks.append(snippet)

            if not blocks:
                return

            pom_text = pom_path.read_text(encoding="utf-8")
            plugin_block = "\n\n".join(blocks)
            updated_text, success = insert_plugins_into_pom(pom_text, plugin_block)

            if success and updated_text != pom_text:
                pom_path.write_text(updated_text, encoding="utf-8")
                problems.append(
                    {
                        "severity": "info",
                        "message": f"Auto-fixed pom.xml: added {len(missing_plugins)} missing plugins",
                        "code": "CIHUB-CI-MAVEN-AUTOFIX",
                    }
                )
        except Exception as exc:  # noqa: BLE001 - best effort, don't break CI
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Maven auto-fix failed: {exc}",
                    "code": "CIHUB-CI-MAVEN-AUTOFIX-FAILED",
                }
            )

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

    def detect_reasons(self, repo_path: Path) -> list[str]:
        reasons: list[str] = []
        if (repo_path / "pom.xml").exists():
            reasons.append("pom.xml")
        if (repo_path / "build.gradle").exists():
            reasons.append("build.gradle")
        if (repo_path / "build.gradle.kts").exists():
            reasons.append("build.gradle.kts")
        if (repo_path / "settings.gradle").exists():
            reasons.append("settings.gradle")
        if (repo_path / "settings.gradle.kts").exists():
            reasons.append("settings.gradle.kts")
        src_dir = repo_path / "src"
        if src_dir.exists() and any(src_dir.rglob("*.java")):
            reasons.append("src/**/*.java")
        return reasons

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
