"""Java tool execution."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any

from cihub.ci_runner import ToolResult, run_java_build, run_maven_install
from cihub.core.ci_report import resolve_thresholds
from cihub.core.gate_specs import evaluate_threshold, get_threshold_spec_by_key
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
from cihub.utils.paths import hub_root
from cihub.utils.project import detect_java_project_type

from .helpers import _parse_env_bool, _tool_enabled, _tool_gate_enabled


def _threshold_passed(language: str, key: str, value: int | float, threshold: int | float) -> bool:
    spec = get_threshold_spec_by_key(language, key)
    if not spec:
        return True
    passed, _ = evaluate_threshold(spec, value, threshold)
    return passed


def _checkstyle_config_candidates(
    config: dict[str, Any],
    repo_path: Path,
    workdir_path: Path,
) -> list[Path]:
    java_cfg = config.get("java", {}) if isinstance(config.get("java"), dict) else {}
    tools_cfg = java_cfg.get("tools", {}) if isinstance(java_cfg.get("tools"), dict) else {}
    checkstyle_cfg = tools_cfg.get("checkstyle")
    config_file = None
    if isinstance(checkstyle_cfg, dict):
        config_file = checkstyle_cfg.get("config_file")
    if isinstance(config_file, str) and config_file.strip():
        config_file = config_file.strip()
        return [repo_path / config_file, workdir_path / config_file]
    return [
        workdir_path / "config/checkstyle/checkstyle.xml",
        workdir_path / "checkstyle/checkstyle.xml",
    ]


def _checkstyle_config_exists(
    config: dict[str, Any],
    repo_path: Path,
    workdir_path: Path,
) -> bool:
    for candidate in _checkstyle_config_candidates(config, repo_path, workdir_path):
        if candidate.exists():
            return True
    return False


def _ensure_checkstyle_config(
    config: dict[str, Any],
    repo_path: Path,
    workdir_path: Path,
    problems: list[dict[str, Any]],
) -> None:
    if _checkstyle_config_exists(config, repo_path, workdir_path):
        return
    default_src = hub_root() / "templates" / "java" / "config" / "checkstyle" / "checkstyle.xml"
    if not default_src.exists():
        problems.append(
            {
                "severity": "error",
                "message": "Checkstyle config missing from hub templates; cannot run checkstyle",
                "code": "CIHUB-CI-CHECKSTYLE-DEFAULT-MISSING",
            }
        )
        return
    target_path = workdir_path / "config" / "checkstyle" / "checkstyle.xml"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(default_src.read_text(encoding="utf-8"), encoding="utf-8")
    problems.append(
        {
            "severity": "warning",
            "message": "Checkstyle config not found; copied hub default to config/checkstyle/checkstyle.xml",
            "code": "CIHUB-CI-CHECKSTYLE-DEFAULT",
        }
    )


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
    thresholds = resolve_thresholds(config, "java")
    max_high_vulns = int(thresholds.get("max_high_vulns", 0) or 0)
    max_critical_vulns = int(thresholds.get("max_critical_vulns", 0) or 0)

    if _tool_enabled(config, "checkstyle", "java"):
        _ensure_checkstyle_config(config, repo_path, workdir_path, problems)

    jacoco_enabled = _tool_enabled(config, "jacoco", "java")
    build_result = run_java_build(workdir_path, output_dir, build_tool, jacoco_enabled)
    tool_outputs["build"] = build_result.to_payload()
    build_result.write_json(tool_output_dir / "build.json")

    if build_tool == "maven" and build_result.success:
        project_type = detect_java_project_type(workdir_path)
        if project_type.startswith("Multi-module"):
            install_tools = {"checkstyle", "spotbugs", "pmd", "pitest", "owasp"}
            if any(_tool_enabled(config, tool, "java") for tool in install_tools):
                install_result = run_maven_install(workdir_path, output_dir)
                install_result.write_json(tool_output_dir / "maven-install.json")
                if not install_result.success:
                    problems.append(
                        {
                            "severity": "error",
                            "message": "Maven install failed for multi-module project; tool runs may be incomplete",
                            "code": "CIHUB-CI-MAVEN-INSTALL",
                        }
                    )

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
                    timeout_seconds = tool_args.get("timeout_seconds")
                    if isinstance(timeout_seconds, str) and timeout_seconds.strip().isdigit():
                        timeout_seconds = int(timeout_seconds.strip())
                    elif isinstance(timeout_seconds, float):
                        timeout_seconds = int(timeout_seconds)
                    result = runner(
                        workdir_path,
                        output_dir,
                        build_tool,
                        tool_args.get("use_nvd_api_key", True),
                        timeout_seconds=timeout_seconds,
                    )
                elif tool == "pitest":
                    timeout_multiplier = tool_args.get("timeout_multiplier", 2)
                    try:
                        timeout_multiplier = int(timeout_multiplier)
                    except (TypeError, ValueError):
                        timeout_multiplier = 2
                    if timeout_multiplier < 1:
                        timeout_multiplier = 1
                    timeout_seconds = int(TIMEOUT_BUILD * timeout_multiplier)
                    result = runner(workdir_path, output_dir, build_tool, timeout_seconds=timeout_seconds)
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

        tools_ran[tool] = result.ran
        if tool == "jacoco":
            if not result.ran:
                tools_success[tool] = False
            else:
                report_found = bool(result.metrics.get("report_found", False))
                coverage_min = float(thresholds.get("coverage_min", 0) or 0)
                coverage = float(result.metrics.get("coverage", 0))
                tools_success[tool] = report_found and _threshold_passed(
                    "java",
                    "coverage_min",
                    coverage,
                    coverage_min,
                )
            result.success = tools_success[tool]
        elif tool == "pitest":
            if not result.ran:
                tools_success[tool] = False
            else:
                report_found = bool(result.metrics.get("report_found", False))
                mut_min = float(thresholds.get("mutation_score_min", 0) or 0)
                mut_score = float(result.metrics.get("mutation_score", 0))
                tools_success[tool] = report_found and _threshold_passed(
                    "java",
                    "mutation_score_min",
                    mut_score,
                    mut_min,
                )
            result.success = tools_success[tool]
        elif tool == "checkstyle":
            if not result.ran:
                tools_success[tool] = False
            else:
                report_found = bool(result.metrics.get("report_found", False))
                if not _tool_gate_enabled(config, "checkstyle", "java"):
                    tools_success[tool] = report_found
                else:
                    max_checkstyle = int(thresholds.get("max_checkstyle_errors", 0) or 0)
                    issues = int(result.metrics.get("checkstyle_issues", 0))
                    tools_success[tool] = report_found and _threshold_passed(
                        "java",
                        "max_checkstyle_errors",
                        issues,
                        max_checkstyle,
                    )
            result.success = tools_success[tool]
        elif tool == "spotbugs":
            if not result.ran:
                tools_success[tool] = False
            else:
                report_found = bool(result.metrics.get("report_found", False))
                if not _tool_gate_enabled(config, "spotbugs", "java"):
                    tools_success[tool] = report_found
                else:
                    max_spotbugs = int(thresholds.get("max_spotbugs_bugs", 0) or 0)
                    issues = int(result.metrics.get("spotbugs_issues", 0))
                    tools_success[tool] = report_found and _threshold_passed(
                        "java",
                        "max_spotbugs_bugs",
                        issues,
                        max_spotbugs,
                    )
            result.success = tools_success[tool]
        elif tool == "pmd":
            if not result.ran:
                tools_success[tool] = False
            else:
                report_found = bool(result.metrics.get("report_found", False))
                if not _tool_gate_enabled(config, "pmd", "java"):
                    tools_success[tool] = report_found
                else:
                    max_pmd = int(thresholds.get("max_pmd_violations", 0) or 0)
                    issues = int(result.metrics.get("pmd_violations", 0))
                    tools_success[tool] = report_found and _threshold_passed(
                        "java",
                        "max_pmd_violations",
                        issues,
                        max_pmd,
                    )
            result.success = tools_success[tool]
        elif tool == "owasp":
            if not result.ran:
                tools_success[tool] = False
            else:
                report_found = bool(result.metrics.get("report_found", False))
                fatal_errors = bool(result.metrics.get("owasp_fatal_errors", False))
                if not report_found or fatal_errors:
                    tools_success[tool] = False
                else:
                    critical = int(result.metrics.get("owasp_critical", 0))
                    high = int(result.metrics.get("owasp_high", 0))
                    max_critical = int(thresholds.get("max_critical_vulns", max_critical_vulns) or 0)
                    max_high = int(thresholds.get("max_high_vulns", max_high_vulns) or 0)
                    success = _threshold_passed("java", "max_critical_vulns", critical, max_critical)
                    success = success and _threshold_passed("java", "max_high_vulns", high, max_high)
                    owasp_cvss_fail = float(thresholds.get("owasp_cvss_fail", 0) or 0)
                    if owasp_cvss_fail:
                        max_cvss = float(result.metrics.get("owasp_max_cvss", 0))
                        success = success and _threshold_passed(
                            "java",
                            "owasp_cvss_fail",
                            max_cvss,
                            owasp_cvss_fail,
                        )
                    tools_success[tool] = success
            result.success = tools_success[tool]
        elif tool == "semgrep":
            if not result.ran:
                tools_success[tool] = False
            else:
                parse_error = bool(result.metrics.get("parse_error", False))
                if parse_error:
                    tools_success[tool] = False
                elif not _tool_gate_enabled(config, "semgrep", "java"):
                    tools_success[tool] = True
                else:
                    max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
                    findings = int(result.metrics.get("semgrep_findings", 0))
                    tools_success[tool] = _threshold_passed(
                        "java",
                        "max_semgrep_findings",
                        findings,
                        max_semgrep,
                    )
            result.success = tools_success[tool]
        elif tool == "trivy":
            if not result.ran:
                tools_success[tool] = False
            else:
                parse_error = bool(result.metrics.get("parse_error", False))
                if parse_error:
                    tools_success[tool] = False
                else:
                    trivy_cfg = config.get("java", {}).get("tools", {}).get("trivy", {}) or {}
                    if not _tool_gate_enabled(config, "trivy", "java"):
                        tools_success[tool] = True
                    else:
                        critical = int(result.metrics.get("trivy_critical", 0))
                        high = int(result.metrics.get("trivy_high", 0))
                        max_critical = int(thresholds.get("max_trivy_critical", max_critical_vulns) or 0)
                        max_high = int(thresholds.get("max_trivy_high", max_high_vulns) or 0)
                        success = True
                        if bool(trivy_cfg.get("fail_on_critical", True)):
                            success = success and _threshold_passed(
                                "java",
                                "max_trivy_critical",
                                critical,
                                max_critical,
                            )
                        if bool(trivy_cfg.get("fail_on_high", True)):
                            success = success and _threshold_passed(
                                "java",
                                "max_trivy_high",
                                high,
                                max_high,
                            )
                        trivy_cvss_fail = float(thresholds.get("trivy_cvss_fail", 0) or 0)
                        if trivy_cvss_fail:
                            max_cvss = float(result.metrics.get("trivy_max_cvss", 0))
                            success = success and _threshold_passed(
                                "java",
                                "trivy_cvss_fail",
                                max_cvss,
                                trivy_cvss_fail,
                            )
                        tools_success[tool] = success
            result.success = tools_success[tool]
        elif tool == "docker":
            if not result.ran:
                docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
                fail_on_missing = bool(docker_cfg.get("fail_on_missing_compose", False))
                tools_success[tool] = not fail_on_missing
            else:
                docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
                fail_on_error = bool(docker_cfg.get("fail_on_error", True))
                if not fail_on_error:
                    tools_success[tool] = True
                else:
                    tools_success[tool] = result.success
            result.success = tools_success[tool]
        else:
            tools_success[tool] = result.success
        tool_outputs[tool] = result.to_payload()
        if tool == "owasp" and result.metrics.get("owasp_data_missing"):
            problems.append(
                {
                    "severity": "warning",
                    "message": "OWASP NVD update failed (403/404); results may be stale",
                    "code": "CIHUB-OWASP-NO-DATA",
                }
            )
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
