"""Python tool execution and dependency installation."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from cihub.ci_runner import ToolResult
from cihub.tools.registry import PYTHON_TOOLS
from cihub.utils import resolve_executable

from .helpers import _parse_env_bool, _tool_enabled


def _run_dep_command(
    cmd: list[str],
    workdir: Path,
    label: str,
    problems: list[dict[str, Any]],
) -> bool:
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=workdir,
        text=True,
        capture_output=True,
        check=False,
        timeout=300,  # 5 min for dependency installation
    )
    if proc.returncode == 0:
        return True
    message = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
    problems.append(
        {
            "severity": "error",
            "message": f"{label} failed: {message}",
            "code": "CIHUB-CI-DEPS",
        }
    )
    return False


def _install_python_dependencies(
    config: dict[str, Any],
    workdir: Path,
    problems: list[dict[str, Any]],
) -> None:
    deps_cfg = config.get("python", {}).get("dependencies", {}) or {}
    if isinstance(deps_cfg, dict):
        if deps_cfg.get("install") is False:
            return
        commands = deps_cfg.get("commands")
    else:
        commands = None

    python_bin = sys.executable or resolve_executable("python")
    if commands:
        for cmd in commands:
            if not cmd:
                continue
            if isinstance(cmd, list):
                parts = [str(part) for part in cmd if str(part)]
            else:
                cmd_str = str(cmd).strip()
                if not cmd_str:
                    continue
                parts = shlex.split(cmd_str)
            if not parts:
                continue
            _run_dep_command(parts, workdir, " ".join(parts), problems)
        return

    if (workdir / "requirements.txt").exists():
        _run_dep_command(
            [python_bin, "-m", "pip", "install", "-r", "requirements.txt"],
            workdir,
            "requirements.txt",
            problems,
        )
    if (workdir / "requirements-dev.txt").exists():
        _run_dep_command(
            [python_bin, "-m", "pip", "install", "-r", "requirements-dev.txt"],
            workdir,
            "requirements-dev.txt",
            problems,
        )
    if (workdir / "pyproject.toml").exists():
        ok = _run_dep_command(
            [python_bin, "-m", "pip", "install", "-e", ".[dev]"],
            workdir,
            "pyproject.toml [dev]",
            problems,
        )
        if not ok:
            _run_dep_command(
                [python_bin, "-m", "pip", "install", "-e", "."],
                workdir,
                "pyproject.toml",
                problems,
            )


def _run_python_tools(
    config: dict[str, Any],
    repo_path: Path,
    workdir: str,
    output_dir: Path,
    problems: list[dict[str, Any]],
    runners: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        raise FileNotFoundError(f"Workdir not found: {workdir_path}")

    mutants_dir = workdir_path / "mutants"
    if mutants_dir.exists():
        try:
            shutil.rmtree(mutants_dir)
        except OSError as exc:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Failed to remove mutmut artifacts: {exc}",
                    "code": "CIHUB-CI-MUTMUT-CLEANUP",
                }
            )

    tool_outputs: dict[str, dict[str, Any]] = {}
    tools_ran: dict[str, bool] = {tool: False for tool in PYTHON_TOOLS}
    tools_success: dict[str, bool] = {tool: False for tool in PYTHON_TOOLS}

    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)

    for tool in PYTHON_TOOLS:
        if tool == "hypothesis":
            continue
        enabled = _tool_enabled(config, tool, "python")
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
            if tool == "pytest":
                pytest_cfg = config.get("python", {}).get("tools", {}).get("pytest", {}) or {}
                fail_fast = bool(pytest_cfg.get("fail_fast", False))
                result = runner(workdir_path, output_dir, fail_fast)
            elif tool == "mutmut":
                timeout = config.get("python", {}).get("tools", {}).get("mutmut", {}).get("timeout_minutes", 15)
                result = runner(workdir_path, output_dir, int(timeout) * 60)
            elif tool == "sbom":
                sbom_cfg = config.get("python", {}).get("tools", {}).get("sbom", {})
                if not isinstance(sbom_cfg, dict):
                    sbom_cfg = {}
                sbom_format = sbom_cfg.get("format", "cyclonedx")
                result = runner(workdir_path, output_dir, sbom_format)
            elif tool == "docker":
                docker_cfg = config.get("python", {}).get("tools", {}).get("docker", {}) or {}
                if not isinstance(docker_cfg, dict):
                    docker_cfg = {}
                compose_file = docker_cfg.get("compose_file", "docker-compose.yml")
                health_endpoint = docker_cfg.get("health_endpoint")
                health_timeout = docker_cfg.get("health_timeout", 300)
                result = runner(workdir_path, output_dir, compose_file, health_endpoint, health_timeout)
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
            docker_cfg = config.get("python", {}).get("tools", {}).get("docker", {}) or {}
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

    if _tool_enabled(config, "hypothesis", "python"):
        tools_ran["hypothesis"] = tools_ran.get("pytest", False)
        tools_success["hypothesis"] = tools_success.get("pytest", False)

    return tool_outputs, tools_ran, tools_success
