"""Python tool execution and dependency installation."""

from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any

from cihub.ci_runner import ToolResult
from cihub.tools.registry import (
    PYTHON_TOOLS,
    get_custom_tools_from_config,
    get_tool_runner_args,
)
from cihub.utils import resolve_executable
from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)

from .helpers import _parse_env_bool, _tool_enabled


def _run_dep_command(
    cmd: list[str],
    workdir: Path,
    label: str,
    problems: list[dict[str, Any]],
) -> bool:
    try:
        proc = safe_run(
            cmd,
            cwd=workdir,
            timeout=TIMEOUT_BUILD,  # 10 min for dependency installation
        )
    except (CommandNotFoundError, CommandTimeoutError) as exc:
        problems.append(
            {
                "severity": "error",
                "message": f"{label} failed: {exc}",
                "code": "CIHUB-CI-DEPS",
            }
        )
        return False
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


def _file_mentions_qt_deps(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return "pyside" in content or "pyqt" in content


def _should_install_qt_deps(workdir: Path) -> bool:
    if not sys.platform.startswith("linux"):
        return False
    for filename in ("pyproject.toml", "requirements.txt", "requirements-dev.txt"):
        if _file_mentions_qt_deps(workdir / filename):
            return True
    return False


def _install_qt_system_deps(workdir: Path, problems: list[dict[str, Any]]) -> None:
    if not _should_install_qt_deps(workdir):
        return
    apt_get = shutil.which("apt-get")
    if not apt_get:
        problems.append(
            {
                "severity": "warning",
                "message": "apt-get not available; skipping Qt system deps",
                "code": "CIHUB-CI-QT-DEPS",
            }
        )
        return
    sudo = shutil.which("sudo")
    prefix = [sudo] if sudo else []
    _run_dep_command(prefix + [apt_get, "update"], workdir, "apt-get update", problems)
    _run_dep_command(
        prefix
        + [
            apt_get,
            "install",
            "-y",
            "libegl1",
            "xvfb",
            "libgl1",
            "libx11-xcb1",
            "libxcb1",
            "libxcb-icccm4",
            "libxcb-image0",
            "libxcb-keysyms1",
            "libxcb-randr0",
            "libxcb-render-util0",
            "libxcb-cursor0",
            "libxcb-shape0",
            "libxcb-shm0",
            "libxcb-sync1",
            "libxcb-xkb1",
            "libxcb-xinerama0",
            "libxcb-xfixes0",
            "libdbus-1-3",
            "libopengl0",
            "libxkbcommon-x11-0",
            "libxrender1",
            "libxi6",
            "libxtst6",
            "libxrandr2",
            "libxdamage1",
            "libxcomposite1",
            "libxcursor1",
            "libglib2.0-0",
            "libfontconfig1",
            "libfreetype6",
            "xauth",
            "xfonts-base",
        ],
        workdir,
        "apt-get install qt libs",
        problems,
    )


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

    _install_qt_system_deps(workdir, problems)

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
    # Initialize with built-in tools + custom tools
    custom_tools = get_custom_tools_from_config(config, "python")
    all_tool_names = list(PYTHON_TOOLS) + list(custom_tools.keys())
    tools_ran: dict[str, bool] = {tool: False for tool in all_tool_names}
    tools_success: dict[str, bool] = {tool: False for tool in all_tool_names}

    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)

    for tool in PYTHON_TOOLS:
        if tool == "hypothesis":
            continue
        enabled = _tool_enabled(config, tool, "python")
        if not enabled:
            continue
        runner = runners.get(tool)
        bandit_gate: dict[str, bool] | None = None
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
            tool_args = get_tool_runner_args(config, tool, "python")
            if tool == "bandit":
                bandit_gate = {
                    "fail_on_high": bool(tool_args.get("fail_on_high", True)),
                    "fail_on_medium": bool(tool_args.get("fail_on_medium", False)),
                    "fail_on_low": bool(tool_args.get("fail_on_low", False)),
                }

            if tool == "pytest":
                pytest_args = tool_args.get("args") or []
                pytest_env = tool_args.get("env")
                if not isinstance(pytest_args, list):
                    pytest_args = []
                if not isinstance(pytest_env, dict):
                    pytest_env = None
                result = runner(
                    workdir_path,
                    output_dir,
                    tool_args.get("fail_fast", False),
                    pytest_args,
                    pytest_env,
                )
            elif tool == "isort":
                use_black_profile = _tool_enabled(config, "black", "python")
                result = runner(workdir_path, output_dir, use_black_profile)
            elif tool == "mutmut":
                result = runner(workdir_path, output_dir, tool_args.get("timeout_seconds", 900))
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
        if tool == "bandit" and bandit_gate is not None:
            if not result.ran:
                tools_success[tool] = False
            else:
                parse_error = bool(result.metrics.get("parse_error", False))
                if parse_error:
                    tools_success[tool] = False
                else:
                    bandit_high = int(result.metrics.get("bandit_high", 0))
                    bandit_medium = int(result.metrics.get("bandit_medium", 0))
                    bandit_low = int(result.metrics.get("bandit_low", 0))
                    success = True
                    if bandit_gate["fail_on_high"] and bandit_high > 0:
                        success = False
                    if bandit_gate["fail_on_medium"] and bandit_medium > 0:
                        success = False
                    if bandit_gate["fail_on_low"] and bandit_low > 0:
                        success = False
                    tools_success[tool] = success
        else:
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

    # Execute custom tools (x-* prefix)
    for tool_name, tool_cfg in custom_tools.items():
        # Schema says custom tools default to enabled=True
        if not _tool_enabled(config, tool_name, "python", default=True):
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

    if _tool_enabled(config, "hypothesis", "python"):
        tools_ran["hypothesis"] = tools_ran.get("pytest", False)
        tools_success["hypothesis"] = tools_success.get("pytest", False)

    return tool_outputs, tools_ran, tools_success
