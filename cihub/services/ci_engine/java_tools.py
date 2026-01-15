"""Java tool execution."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any

from cihub.ci_runner import ToolResult, run_java_build
from cihub.tools.registry import (
    JAVA_TOOLS,
    get_custom_tools_from_config,
    get_tool_runner_args,
)
from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)

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
    # Initialize with built-in tools + custom tools
    custom_tools = get_custom_tools_from_config(config, "java")
    all_tool_names = list(JAVA_TOOLS) + list(custom_tools.keys())
    tools_ran: dict[str, bool] = {tool: False for tool in all_tool_names}
    tools_success: dict[str, bool] = {tool: False for tool in all_tool_names}

    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)

    jacoco_enabled = _tool_enabled(config, "jacoco", "java")
    build_result = run_java_build(workdir_path, output_dir, build_tool, jacoco_enabled)
    tool_outputs["build"] = build_result.to_payload()
    build_result.write_json(tool_output_dir / "build.json")

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
            # Get tool-specific config from centralized registry (Part 5.3)
            tool_args = get_tool_runner_args(config, tool, "java")

            if tool_args.get("needs_build_tool"):
                # Tools that need build_tool parameter: pitest, checkstyle, spotbugs, pmd
                if tool == "owasp":
                    result = runner(workdir_path, output_dir, build_tool, tool_args.get("use_nvd_api_key", True))
                else:
                    result = runner(workdir_path, output_dir, build_tool)
            elif tool == "sbom":
                result = runner(workdir_path, output_dir, tool_args.get("sbom_format", "cyclonedx"))
            elif tool == "docker":
                result = runner(
                    workdir_path,
                    output_dir,
                    tool_args.get("compose_file", "docker-compose.yml"),
                    tool_args.get("health_endpoint"),
                    tool_args.get("health_timeout", 300),
                )
            else:
                result = runner(workdir_path, output_dir)
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

    # Execute custom tools (x-* prefix)
    for tool_name, tool_cfg in custom_tools.items():
        # Schema says custom tools default to enabled=True
        if not _tool_enabled(config, tool_name, "java", default=True):
            continue
        # Extract command and fail_on_error from tool config
        tool_cfg_dict = tool_cfg if isinstance(tool_cfg, dict) else {}
        command = tool_cfg_dict.get("command")
        # Schema says fail_on_error defaults to True
        fail_on_error = tool_cfg_dict.get("fail_on_error", True)
        if not command:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Custom tool '{tool_name}' has no command configured",
                    "code": "CIHUB-CI-CUSTOM-TOOL",
                }
            )
            continue
        try:
            # Parse command string into list
            if isinstance(command, str):
                cmd_parts = shlex.split(command)
            else:
                cmd_parts = [str(p) for p in command]
            proc = safe_run(cmd_parts, cwd=workdir_path, timeout=TIMEOUT_BUILD)
            ran = True
            success = proc.returncode == 0
            result = ToolResult(
                tool=tool_name,
                ran=ran,
                success=success,
                returncode=proc.returncode,
                metrics={"exit_code": proc.returncode},
            )
            # Emit error if fail_on_error is True (affects exit code); otherwise no problem
            if not success and fail_on_error:
                problems.append(
                    {
                        "severity": "error",
                        "message": f"Custom tool '{tool_name}' failed with exit code {proc.returncode}",
                        "code": "CIHUB-CI-CUSTOM-TOOL",
                    }
                )
        except (CommandNotFoundError, CommandTimeoutError) as exc:
            # Honor fail_on_error: if True, emit error (affects CI exit code)
            severity = "error" if fail_on_error else "warning"
            problems.append(
                {
                    "severity": severity,
                    "message": f"Custom tool '{tool_name}' failed: {exc}",
                    "code": "CIHUB-CI-CUSTOM-TOOL",
                }
            )
            result = ToolResult(tool=tool_name, ran=False, success=False, returncode=-1)
        except Exception as exc:
            # Honor fail_on_error for unexpected errors too
            severity = "error" if fail_on_error else "warning"
            problems.append(
                {
                    "severity": severity,
                    "message": f"Custom tool '{tool_name}' error: {exc}",
                    "code": "CIHUB-CI-CUSTOM-TOOL",
                }
            )
            result = ToolResult(tool=tool_name, ran=False, success=False, returncode=-1)
        tool_outputs[tool_name] = result.to_payload()
        tools_ran[tool_name] = result.ran
        tools_success[tool_name] = result.success
        result.write_json(tool_output_dir / f"{tool_name}.json")

    if _tool_enabled(config, "jqwik", "java"):
        tests_failed = int(build_result.metrics.get("tests_failed", 0))
        tools_ran["jqwik"] = True
        tools_success["jqwik"] = build_result.success and tests_failed == 0

    return tool_outputs, tools_ran, tools_success
