"""Run a single tool and emit JSON output."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config
from cihub.ci_runner import ToolResult
from cihub.config import tool_enabled as _tool_enabled_canonical
from cihub.tools.registry import get_runner, get_tool_runner_args
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.paths import validate_subdir

SUPPORTED_LANGUAGES = ("python", "java")


def _tool_enabled(config: dict[str, Any], tool: str, language: str) -> bool:
    """Check if a tool is enabled for a specific language."""
    return _tool_enabled_canonical(config, tool, language)


def _resolve_candidate_languages(tool: str) -> list[str]:
    candidates = []
    for language in SUPPORTED_LANGUAGES:
        if get_runner(tool, language):
            candidates.append(language)
    return candidates


def _detect_build_tool(workdir_path: Path, config: dict[str, Any]) -> str:
    build_tool = config.get("java", {}).get("build_tool", "").strip().lower()
    if build_tool in {"maven", "gradle"}:
        return build_tool
    if (
        (workdir_path / "build.gradle").exists()
        or (workdir_path / "build.gradle.kts").exists()
        or (workdir_path / "settings.gradle").exists()
        or (workdir_path / "settings.gradle.kts").exists()
    ):
        return "gradle"
    return "maven"


def _resolve_language(
    tool: str,
    config: dict[str, Any],
    candidates: list[str],
    explicit: str | None,
) -> tuple[str | None, str | None]:
    if explicit:
        if explicit not in candidates:
            return None, f"Unsupported language '{explicit}' for tool '{tool}'."
        return explicit, None
    enabled_langs = [lang for lang in candidates if _tool_enabled(config, tool, lang)]
    if len(enabled_langs) == 1:
        return enabled_langs[0], None
    repo_cfg = config.get("repo", {})
    if not isinstance(repo_cfg, dict):
        repo_cfg = {}
    config_lang = config.get("language") or repo_cfg.get("language")
    if isinstance(config_lang, str) and config_lang in candidates:
        return config_lang, None
    if len(candidates) == 1:
        return candidates[0], None
    if len(enabled_langs) > 1:
        return None, f"Tool '{tool}' is enabled for multiple languages; specify --language."
    return None, f"Tool '{tool}' is available for multiple languages; specify --language."


def cmd_run(args: argparse.Namespace) -> CommandResult:
    """Run a single CI tool and emit JSON output.

    Always returns CommandResult for consistent output handling.
    """
    repo_path = Path(args.repo or ".").resolve()
    tool = args.tool
    tool_key = "pip_audit" if tool == "pip-audit" else tool
    output_dir = Path(args.output_dir or ".cihub")
    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)
    output_name = tool_key
    output_path = Path(args.output) if args.output else tool_output_dir / f"{output_name}.json"

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-001"}],
        )

    workdir = args.workdir or config.get("repo", {}).get("subdir") or "."
    validate_subdir(workdir)
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        message = f"Workdir not found: {workdir_path}"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-002"}],
        )

    candidates = _resolve_candidate_languages(tool_key)
    if not candidates:
        message = f"Unsupported tool: {tool}"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-003"}],
        )

    language, language_error = _resolve_language(
        tool_key,
        config,
        candidates,
        getattr(args, "language", None),
    )
    if language is None:
        message = language_error or f"Unsupported tool: {tool}"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-003"}],
        )

    runner = get_runner(tool_key, language)
    if runner is None:
        message = f"Unsupported tool: {tool}"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-003"}],
        )

    if not args.force and not _tool_enabled(config, tool_key, language):
        result = ToolResult(tool=tool_key, ran=False, success=False)
        result.write_json(output_path)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"{tool_key} skipped (disabled)",
            artifacts={"output": str(output_path)},
            data={"items": [f"{tool_key} skipped (disabled)"]},
        )

    try:
        if language == "python":
            if tool_key == "pytest":
                tool_args = get_tool_runner_args(config, "pytest", "python")
                fail_fast = bool(tool_args.get("fail_fast", False))
                pytest_args = tool_args.get("args") or []
                pytest_env = tool_args.get("env")
                if not isinstance(pytest_args, list):
                    pytest_args = []
                if not isinstance(pytest_env, dict):
                    pytest_env = None
                result = runner(workdir_path, output_dir, fail_fast, pytest_args, pytest_env)
            elif tool_key == "isort":
                use_black_profile = _tool_enabled(config, "black", "python")
                result = runner(workdir_path, output_dir, use_black_profile)
            elif tool_key == "mutmut":
                timeout = config.get("python", {}).get("tools", {}).get("mutmut", {}).get("timeout_minutes", 15)
                result = runner(workdir_path, output_dir, int(timeout) * 60)
            elif tool_key == "sbom":
                tool_args = get_tool_runner_args(config, "sbom", "python")
                result = runner(workdir_path, output_dir, tool_args.get("format"))
            elif tool_key == "docker":
                tool_args = get_tool_runner_args(config, "docker", "python")
                result = runner(
                    workdir_path,
                    output_dir,
                    tool_args.get("compose_file", "docker-compose.yml"),
                    tool_args.get("health_endpoint"),
                    int(tool_args.get("health_timeout", 300)),
                )
            else:
                result = runner(workdir_path, output_dir)
        else:
            if tool_key in {"pitest", "checkstyle", "spotbugs", "pmd"}:
                build_tool = _detect_build_tool(workdir_path, config)
                result = runner(workdir_path, output_dir, build_tool)
            elif tool_key == "owasp":
                build_tool = _detect_build_tool(workdir_path, config)
                tool_args = get_tool_runner_args(config, "owasp", "java")
                result = runner(
                    workdir_path,
                    output_dir,
                    build_tool,
                    bool(tool_args.get("use_nvd_api_key", True)),
                )
            elif tool_key == "sbom":
                tool_args = get_tool_runner_args(config, "sbom", "java")
                result = runner(workdir_path, output_dir, tool_args.get("format"))
            elif tool_key == "docker":
                tool_args = get_tool_runner_args(config, "docker", "java")
                result = runner(
                    workdir_path,
                    output_dir,
                    tool_args.get("compose_file", "docker-compose.yml"),
                    tool_args.get("health_endpoint"),
                    int(tool_args.get("health_timeout", 300)),
                )
            else:
                result = runner(workdir_path, output_dir)
    except FileNotFoundError as exc:
        message = f"Tool '{tool}' not found: {exc}"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-RUN-004"}],
        )

    result.write_json(output_path)
    status = "passed" if result.success else "failed"
    return CommandResult(
        exit_code=EXIT_SUCCESS if result.success else EXIT_FAILURE,
        summary=f"{tool} {status}",
        artifacts={"output": str(output_path)},
        data={
            "items": [f"Wrote output: {output_path}"],
            "tool_result": result.to_payload(),
        },
    )
