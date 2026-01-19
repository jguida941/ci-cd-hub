"""Smoke test helper for the CLI."""

from __future__ import annotations

import argparse
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cihub.commands.ci import cmd_ci
from cihub.commands.detect import cmd_detect
from cihub.commands.init import cmd_init
from cihub.commands.scaffold import SCAFFOLD_TYPES, scaffold_fixture
from cihub.commands.validate import cmd_validate
from cihub.config.io import load_yaml_file, save_yaml_file
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.paths import validate_repo_path

DEFAULT_TYPES = ["python-pyproject", "java-maven"]
# Use keys from SCAFFOLD_TYPES to ensure consistency
ALL_TYPES = list(SCAFFOLD_TYPES.keys())


@dataclass
class SmokeStep:
    name: str
    exit_code: int
    summary: str
    problems: list[dict[str, Any]]


@dataclass
class SmokeCase:
    name: str
    repo_path: Path
    subdir: str
    generated: bool = False


def _as_command_result(result: int | CommandResult) -> CommandResult:
    if isinstance(result, CommandResult):
        return result
    return CommandResult(exit_code=int(result))


def _detect_java_build_tool(path: Path) -> str | None:
    if (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
        return "gradle"
    if (path / "pom.xml").exists():
        return "maven"
    return None


def _apply_smoke_overrides(
    repo_path: Path,
    language: str,
    subdir: str,
    build_tool: str | None,
    relax: bool,
) -> None:
    config_path = repo_path / ".ci-hub.yml"
    config = load_yaml_file(config_path)
    if not isinstance(config, dict):
        config = {}

    repo_block = config.get("repo", {})
    if not isinstance(repo_block, dict):
        repo_block = {}
    if subdir:
        repo_block["subdir"] = subdir
    config["repo"] = repo_block

    if relax:
        thresholds = config.get("thresholds", {})
        if not isinstance(thresholds, dict):
            thresholds = {}
        thresholds.update(
            {
                "coverage_min": 0,
                "mutation_score_min": 0,
                "max_critical_vulns": 999,
                "max_high_vulns": 999,
                "max_ruff_errors": 0,
                "max_black_issues": 0,
                "max_isort_issues": 0,
                "max_pip_audit_vulns": 999,
                "max_checkstyle_errors": 0,
                "max_spotbugs_bugs": 0,
                "max_pmd_violations": 0,
                "max_semgrep_findings": 999,
            }
        )
        config["thresholds"] = thresholds

    if language == "python" and relax:
        python_block = config.get("python", {})
        if not isinstance(python_block, dict):
            python_block = {}
        tools = python_block.get("tools", {})
        if not isinstance(tools, dict):
            tools = {}
        tools.update(
            {
                "pytest": {"enabled": True},
                "ruff": {"enabled": True, "fail_on_error": True, "max_errors": 0},
                "black": {"enabled": True, "fail_on_format_issues": False},
                "isort": {"enabled": True, "fail_on_issues": False},
                "bandit": {"enabled": False},
                "pip_audit": {"enabled": False},
                "mypy": {"enabled": False},
                "mutmut": {"enabled": False},
                "semgrep": {"enabled": False},
                "trivy": {"enabled": False},
                "codeql": {"enabled": False},
            }
        )
        python_block["tools"] = tools
        config["python"] = python_block

    if language == "java":
        java_block = config.get("java", {})
        if not isinstance(java_block, dict):
            java_block = {}
        if build_tool:
            java_block["build_tool"] = build_tool
        if relax:
            tools = java_block.get("tools", {})
            if not isinstance(tools, dict):
                tools = {}
            tools.update(
                {
                    "jacoco": {"enabled": False},
                    "checkstyle": {"enabled": False},
                    "spotbugs": {"enabled": False},
                    "owasp": {"enabled": False},
                    "pitest": {"enabled": False},
                    "jqwik": {"enabled": False},
                    "pmd": {"enabled": False},
                    "semgrep": {"enabled": False},
                    "trivy": {"enabled": False},
                    "codeql": {"enabled": False},
                    "docker": {"enabled": False},
                }
            )
            java_block["tools"] = tools
        config["java"] = java_block

    save_yaml_file(config_path, config, dry_run=False)


def _run_case(
    case: SmokeCase,
    full: bool,
    install_deps: bool,
    relax: bool,
    force: bool,
) -> tuple[list[SmokeStep], str | None]:
    steps: list[SmokeStep] = []
    detect_path = case.repo_path / case.subdir if case.subdir else case.repo_path

    detect_args = argparse.Namespace(
        repo=str(detect_path),
        language=None,
        explain=False,
        json=True,
    )
    detect_result = _as_command_result(cmd_detect(detect_args))
    steps.append(
        SmokeStep(
            name="detect",
            exit_code=detect_result.exit_code,
            summary=detect_result.summary,
            problems=detect_result.problems,
        )
    )
    if detect_result.exit_code != 0:
        return steps, None

    language = detect_result.data.get("language") if detect_result.data else None
    if not language:
        return steps, None

    init_args = argparse.Namespace(
        repo=str(case.repo_path),
        language=language,
        owner="local",
        name=case.repo_path.name,
        branch="main",
        subdir=case.subdir or None,
        fix_pom=False,
        apply=True,
        force=force,
        wizard=False,
        dry_run=False,
        json=True,
    )
    init_result = _as_command_result(cmd_init(init_args))
    steps.append(
        SmokeStep(
            name="init",
            exit_code=init_result.exit_code,
            summary=init_result.summary,
            problems=init_result.problems,
        )
    )
    if init_result.exit_code != 0:
        return steps, language

    validate_args = argparse.Namespace(repo=str(case.repo_path), json=True, strict=False)
    validate_result = _as_command_result(cmd_validate(validate_args))
    steps.append(
        SmokeStep(
            name="validate",
            exit_code=validate_result.exit_code,
            summary=validate_result.summary,
            problems=validate_result.problems,
        )
    )
    if validate_result.exit_code != 0:
        return steps, language

    if full:
        build_tool = _detect_java_build_tool(detect_path)
        if case.generated or relax:
            _apply_smoke_overrides(case.repo_path, language, case.subdir, build_tool, relax=True)
        elif language == "java" and build_tool:
            _apply_smoke_overrides(case.repo_path, language, case.subdir, build_tool, relax=False)

        validate_result = _as_command_result(cmd_validate(validate_args))
        steps.append(
            SmokeStep(
                name="validate (full)",
                exit_code=validate_result.exit_code,
                summary=validate_result.summary,
                problems=validate_result.problems,
            )
        )
        if validate_result.exit_code != 0:
            return steps, language

        ci_args = argparse.Namespace(
            repo=str(case.repo_path),
            workdir=None,
            correlation_id=None,
            output_dir=str(case.repo_path / ".cihub"),
            install_deps=install_deps,
            report=None,
            summary=None,
            no_summary=False,
            write_github_summary=False,
            config_from_hub=None,
            json=True,
        )
        ci_result = _as_command_result(cmd_ci(ci_args))
        steps.append(
            SmokeStep(
                name="ci",
                exit_code=ci_result.exit_code,
                summary=ci_result.summary,
                problems=ci_result.problems,
            )
        )

        # Issue 10: Report validation after ci run
        report_path = case.repo_path / ".cihub" / "report.json"
        if report_path.exists():
            from cihub.commands.report.validate import _validate_report

            validate_report_args = argparse.Namespace(
                report=str(report_path),
                expect="clean",
                coverage_min=0,  # Relaxed for smoke tests
                strict=True,
                verbose=False,
                summary=None,
                reports_dir=None,
                debug=False,
                json=True,
            )
            validate_report_result = _validate_report(validate_report_args)
            steps.append(
                SmokeStep(
                    name="report-validate",
                    exit_code=validate_report_result.exit_code,
                    summary=validate_report_result.summary,
                    problems=validate_report_result.problems,
                )
            )

    return steps, language


def _resolve_types(args: argparse.Namespace) -> list[str]:
    if args.all:
        return ALL_TYPES
    if args.type:
        # From CLI with action="append": args.type is a list
        # From tests with direct Namespace: args.type may be a string
        if isinstance(args.type, list):
            return list(args.type)
        return [args.type]
    return DEFAULT_TYPES


def cmd_smoke(args: argparse.Namespace) -> CommandResult:
    """Run smoke tests on repositories.

    Always returns CommandResult for consistent output handling.
    """
    if args.repo and (args.all or args.type):
        message = "--type/--all cannot be used with a repo path"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message}],
        )

    cases: list[SmokeCase] = []
    temp_dir: Path | None = None
    temp_dir_ctx: tempfile.TemporaryDirectory[str] | None = None  # Managed resource

    if args.repo:
        try:
            repo_path = validate_repo_path(Path(args.repo))
        except ValueError as exc:
            message = str(exc)
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        cases.append(
            SmokeCase(
                name=repo_path.name,
                repo_path=repo_path,
                subdir=args.subdir or "",
            )
        )
    else:
        types = _resolve_types(args)
        unknown = [name for name in types if name not in SCAFFOLD_TYPES]
        if unknown:
            message = f"Unknown fixture type(s): {', '.join(unknown)}"
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        if args.keep:
            temp_dir = Path(tempfile.mkdtemp(prefix="cihub-smoke-"))
        else:
            # Keep reference to context manager for cleanup
            temp_dir_ctx = tempfile.TemporaryDirectory(prefix="cihub-smoke-")
            temp_dir = Path(temp_dir_ctx.name)
        for fixture_type in types:
            if fixture_type == "monorepo":
                for subdir in ["java", "python"]:
                    name = f"monorepo-{subdir}"
                    repo_path = temp_dir / name
                    scaffold_fixture("monorepo", repo_path, force=True)
                    cases.append(
                        SmokeCase(
                            name=name,
                            repo_path=repo_path,
                            subdir=subdir,
                            generated=True,
                        )
                    )
            else:
                repo_path = temp_dir / fixture_type
                scaffold_fixture(fixture_type, repo_path, force=True)
                cases.append(
                    SmokeCase(
                        name=fixture_type,
                        repo_path=repo_path,
                        subdir="",
                        generated=True,
                    )
                )

    results: list[dict[str, Any]] = []
    items: list[str] = []  # Human-readable output
    failures = 0

    for case in cases:
        steps, language = _run_case(
            case,
            full=bool(args.full),
            install_deps=bool(args.install_deps),
            relax=bool(args.relax),
            force=bool(args.force),
        )
        success = all(step.exit_code == EXIT_SUCCESS for step in steps)
        failures += 0 if success else 1
        results.append(
            {
                "name": case.name,
                "repo": str(case.repo_path),
                "subdir": case.subdir,
                "language": language,
                "success": success,
                "steps": [
                    {
                        "name": step.name,
                        "exit_code": step.exit_code,
                        "summary": step.summary,
                        "problems": step.problems,
                    }
                    for step in steps
                ],
            }
        )
        # Collect human-readable output
        status = "OK" if success else "FAIL"
        items.append(f"[{status}] {case.name}")
        for step in steps:
            step_status = "OK" if step.exit_code == EXIT_SUCCESS else "FAIL"
            items.append(f"  - {step_status} {step.name}: {step.summary}")

    if temp_dir and args.keep:
        items.append(f"Fixtures preserved at: {temp_dir}")

    exit_code = EXIT_FAILURE if failures else EXIT_SUCCESS
    summary = "Smoke test failed" if failures else "Smoke test OK"

    # Clean up temporary directory if not keeping
    if temp_dir_ctx is not None:
        temp_dir_ctx.cleanup()

    return CommandResult(
        exit_code=exit_code,
        summary=summary,
        data={
            "cases": results,
            "fixtures_root": str(temp_dir) if temp_dir else None,
            "full": bool(args.full),
            "items": items,
        },
    )


def cmd_smoke_validate(args: argparse.Namespace) -> CommandResult:
    """Validate smoke test results.

    Always returns CommandResult for consistent output handling.
    """
    failures: list[str] = []

    if args.count is not None and args.count < args.min_count:
        failures.append(f"Expected at least {args.min_count} smoke test repos, found {args.count}")

    if args.status and args.status != "success":
        failures.append("Smoke test failed - check job results")

    if failures:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=failures[0],
            problems=[{"severity": "error", "message": msg} for msg in failures],
            data={
                "items": [f"::error::{msg}" for msg in failures],  # GitHub Actions format
            },
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Smoke validation passed",
        data={"items": ["Smoke validation passed."]},
    )
