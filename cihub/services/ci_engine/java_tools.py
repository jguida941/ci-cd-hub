"""Java tool execution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cihub.ci_runner import ToolResult, run_java_build
from cihub.tools.registry import JAVA_TOOLS

from .helpers import _parse_env_bool, _tool_enabled


def _run_java_tools(
    config: dict[str, Any],
    repo_path: Path,
    workdir: str,
    output_dir: Path,
    build_tool: str,
    problems: list[dict[str, Any]],
    runners: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        raise FileNotFoundError(f"Workdir not found: {workdir_path}")

    tool_outputs: dict[str, dict[str, Any]] = {}
    tools_ran: dict[str, bool] = {tool: False for tool in JAVA_TOOLS}
    tools_success: dict[str, bool] = {tool: False for tool in JAVA_TOOLS}

    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)

    jacoco_enabled = _tool_enabled(config, "jacoco", "java")
    build_result = run_java_build(workdir_path, output_dir, build_tool, jacoco_enabled)
    tool_outputs["build"] = build_result.to_payload()
    build_result.write_json(tool_output_dir / "build.json")

    use_nvd_api_key = bool(config.get("java", {}).get("tools", {}).get("owasp", {}).get("use_nvd_api_key", True))

    for tool in JAVA_TOOLS:
        if tool == "jqwik":
            continue
        enabled = _tool_enabled(config, tool, "java")
        if not enabled:
            continue
        runner = runners.get(tool)
        if runner is None:
            if tool == "codeql":
                external = _parse_env_bool(os.environ.get("CIHUB_CODEQL_RAN"))
                if external:
                    success = _parse_env_bool(os.environ.get("CIHUB_CODEQL_SUCCESS"))
                    if success is None:
                        success = True
                    result = ToolResult(tool=tool, ran=True, success=success)
                    if not success:
                        problems.append(
                            {
                                "severity": "warning",
                                "message": "CodeQL analysis failed or was skipped",
                                "code": "CIHUB-CI-CODEQL",
                            }
                        )
                    tool_outputs[tool] = result.to_payload()
                    tools_ran[tool] = True
                    tools_success[tool] = success
                    result.write_json(tool_output_dir / f"{tool}.json")
                    continue
            problems.append(
                {
                    "severity": "warning",
                    "message": (f"Tool '{tool}' is enabled but is not supported by cihub; run it via a workflow step."),
                    "code": "CIHUB-CI-UNSUPPORTED",
                }
            )
            ToolResult(tool=tool, ran=False, success=False).write_json(tool_output_dir / f"{tool}.json")
            continue
        try:
            if tool == "pitest":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "checkstyle":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "spotbugs":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "pmd":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "owasp":
                result = runner(workdir_path, output_dir, build_tool, use_nvd_api_key)  # type: ignore[operator]
            elif tool == "sbom":
                sbom_cfg = config.get("java", {}).get("tools", {}).get("sbom", {})
                if not isinstance(sbom_cfg, dict):
                    sbom_cfg = {}
                sbom_format = sbom_cfg.get("format", "cyclonedx")
                result = runner(workdir_path, output_dir, sbom_format)  # type: ignore[operator]
            elif tool == "docker":
                docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
                if not isinstance(docker_cfg, dict):
                    docker_cfg = {}
                compose_file = docker_cfg.get("compose_file", "docker-compose.yml")
                health_endpoint = docker_cfg.get("health_endpoint")
                health_timeout = docker_cfg.get("health_timeout", 300)
                result = runner(workdir_path, output_dir, compose_file, health_endpoint, health_timeout)  # type: ignore[operator]
            else:
                result = runner(workdir_path, output_dir)  # type: ignore[operator]
        except FileNotFoundError as exc:
            problems.append(
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found: {exc}",
                    "code": "CIHUB-CI-MISSING-TOOL",
                }
            )
            result = ToolResult(tool=tool, ran=False, success=False)

        tool_outputs[tool] = result.to_payload()
        tools_ran[tool] = result.ran
        tools_success[tool] = result.success
        if tool == "docker" and result.metrics.get("docker_missing_compose"):
            docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
            if not isinstance(docker_cfg, dict):
                docker_cfg = {}
            fail_on_missing = bool(docker_cfg.get("fail_on_missing_compose", False))
            problems.append(
                {
                    "severity": "error" if fail_on_missing else "warning",
                    "message": "Docker compose file not found; docker tool skipped",
                    "code": "CIHUB-CI-DOCKER-MISSING",
                }
            )
        if tool == "docker" and result.ran and not result.success and not result.metrics.get("docker_missing_compose"):
            problems.append(
                {
                    "severity": "warning",
                    "message": "Docker tool failed; check docker-compose log output",
                    "code": "CIHUB-CI-DOCKER-FAILED",
                }
            )
        result.write_json(tool_output_dir / f"{tool}.json")

    if _tool_enabled(config, "jqwik", "java"):
        tests_failed = int(build_result.metrics.get("tests_failed", 0))
        tools_ran["jqwik"] = True
        tools_success["jqwik"] = build_result.success and tests_failed == 0

    return tool_outputs, tools_ran, tools_success
