"""Test metrics automation for hub CI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from cihub.types import CommandResult
from cihub.utils.github_context import GitHubContext
from cihub.utils.paths import project_root

from . import result_fail, result_ok, run_and_capture


def _resolve_path(value: str | Path, repo_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path


def _branch_name(ctx: GitHubContext) -> str | None:
    if ctx.ref_name:
        return ctx.ref_name
    if ctx.ref and ctx.ref.startswith("refs/heads/"):
        return ctx.ref.split("/", 2)[-1]
    return ctx.ref


def _normalize_readme(content: str) -> str:
    lines = [line for line in content.splitlines() if not line.strip().startswith("> Last updated:")]
    return "\n".join(lines).strip()


def _write_mode(args: argparse.Namespace, ctx: GitHubContext) -> tuple[bool, str | None]:
    if not getattr(args, "write", False):
        return False, None

    if not ctx.is_ci:
        return True, None

    if getattr(args, "allow_non_main", False):
        return True, None

    branch = _branch_name(ctx)
    if branch == "main":
        return True, None

    reason = f"Write disabled on non-main ref: {branch or 'unknown'}"
    return False, reason


def cmd_test_metrics(args: argparse.Namespace) -> CommandResult:
    """Run test metrics automation steps for hub CI."""
    repo_root = project_root()
    ctx = GitHubContext.from_env()

    coverage_file = _resolve_path(args.coverage_file, repo_root)
    coverage_db = _resolve_path(args.coverage_db, repo_root)
    mutation_file = _resolve_path(args.mutation_file, repo_root)
    tests_dir = _resolve_path(args.tests_dir, repo_root)
    readme_path = _resolve_path(args.readme, repo_root)

    scripts = {
        "update_test_metrics": repo_root / "scripts" / "update_test_metrics.py",
        "generate_test_readme": repo_root / "scripts" / "generate_test_readme.py",
        "check_test_drift": repo_root / "scripts" / "check_test_drift.py",
    }

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    data: dict[str, Any] = {
        "coverage_file": str(coverage_file),
        "coverage_db": str(coverage_db),
        "mutation_file": str(mutation_file),
        "tests_dir": str(tests_dir),
        "readme_path": str(readme_path),
        "steps": {},
    }

    for _name, path in scripts.items():
        if not path.exists():
            errors.append(
                {
                    "severity": "error",
                    "message": f"Missing required script: {path}",
                    "code": "CIHUB-TEST-METRICS-MISSING-SCRIPT",
                }
            )

    if not tests_dir.exists():
        errors.append(
            {
                "severity": "error",
                "message": f"Tests directory not found: {tests_dir}",
                "code": "CIHUB-TEST-METRICS-NO-TESTS",
            }
        )

    write_enabled, write_reason = _write_mode(args, ctx)
    data["write_requested"] = bool(getattr(args, "write", False))
    data["write_enabled"] = write_enabled
    if write_reason:
        data["write_skipped_reason"] = write_reason
        warnings.append(
            {
                "severity": "warning",
                "message": write_reason,
                "code": "CIHUB-TEST-METRICS-WRITE-SKIPPED",
            }
        )

    if errors:
        return result_fail("Test metrics prerequisites failed", problems=errors + warnings, data=data)

    coverage_generated = False
    if not coverage_file.exists():
        if coverage_db.exists():
            result = run_and_capture(
                [
                    sys.executable,
                    "-m",
                    "coverage",
                    "json",
                    "-o",
                    str(coverage_file),
                    "--data-file",
                    str(coverage_db),
                ],
                cwd=repo_root,
                tool_name="coverage-json",
            )
            data["steps"]["coverage_json"] = {
                "returncode": result["returncode"],
                "success": result["success"],
            }
            if result["returncode"] != 0:
                errors.append(
                    {
                        "severity": "error",
                        "message": "Failed to generate coverage.json",
                        "code": "CIHUB-TEST-METRICS-COVERAGE-JSON",
                    }
                )
            else:
                coverage_generated = True
        else:
            errors.append(
                {
                    "severity": "error",
                    "message": "coverage.json and .coverage not found; run pytest with coverage first",
                    "code": "CIHUB-TEST-METRICS-NO-COVERAGE",
                }
            )

    if errors:
        data["coverage_generated"] = coverage_generated
        return result_fail("Test metrics failed", problems=errors + warnings, data=data)

    data["coverage_generated"] = coverage_generated

    if write_enabled:
        update_result = run_and_capture(
            [
                sys.executable,
                str(scripts["update_test_metrics"]),
                "--coverage-file",
                str(coverage_file),
                "--mutation-file",
                str(mutation_file),
                "--tests-dir",
                str(tests_dir),
            ],
            cwd=repo_root,
            tool_name="update-test-metrics",
        )
        data["steps"]["update_test_metrics"] = {
            "returncode": update_result["returncode"],
            "success": update_result["success"],
        }
        if update_result["returncode"] != 0:
            errors.append(
                {
                    "severity": "error",
                    "message": "update_test_metrics failed",
                    "code": "CIHUB-TEST-METRICS-UPDATE-FAILED",
                }
            )

    if not getattr(args, "skip_readme", False):
        if write_enabled:
            readme_result = run_and_capture(
                [
                    sys.executable,
                    str(scripts["generate_test_readme"]),
                    "--coverage-file",
                    str(coverage_file),
                    "--tests-dir",
                    str(tests_dir),
                    "--output",
                    str(readme_path),
                ],
                cwd=repo_root,
                tool_name="generate-test-readme",
            )
            data["steps"]["generate_test_readme"] = {
                "returncode": readme_result["returncode"],
                "success": readme_result["success"],
            }
            if readme_result["returncode"] != 0:
                errors.append(
                    {
                        "severity": "error",
                        "message": "generate_test_readme failed",
                        "code": "CIHUB-TEST-METRICS-README-FAILED",
                    }
                )
        else:
            readme_result = run_and_capture(
                [
                    sys.executable,
                    str(scripts["generate_test_readme"]),
                    "--coverage-file",
                    str(coverage_file),
                    "--tests-dir",
                    str(tests_dir),
                    "--dry-run",
                ],
                cwd=repo_root,
                tool_name="generate-test-readme",
            )
            data["steps"]["generate_test_readme"] = {
                "returncode": readme_result["returncode"],
                "success": readme_result["success"],
            }
            if readme_result["returncode"] != 0:
                errors.append(
                    {
                        "severity": "error",
                        "message": "generate_test_readme dry-run failed",
                        "code": "CIHUB-TEST-METRICS-README-FAILED",
                    }
                )
            else:
                generated = readme_result["stdout"]
                if not readme_path.exists():
                    data["readme_status"] = "missing"
                    warnings.append(
                        {
                            "severity": "warning",
                            "message": "tests/README.md is missing",
                            "code": "CIHUB-TEST-METRICS-README-MISSING",
                        }
                    )
                else:
                    existing = readme_path.read_text(encoding="utf-8")
                    normalized_existing = _normalize_readme(existing)
                    normalized_generated = _normalize_readme(generated)
                    if normalized_existing != normalized_generated:
                        data["readme_status"] = "stale"
                        warnings.append(
                            {
                                "severity": "warning",
                                "message": "tests/README.md is out of date",
                                "code": "CIHUB-TEST-METRICS-README-STALE",
                            }
                        )
                    else:
                        data["readme_status"] = "ok"

    drift_result = run_and_capture(
        [
            sys.executable,
            str(scripts["check_test_drift"]),
            "--tests-dir",
            str(tests_dir),
            *(["--strict"] if getattr(args, "strict", False) else []),
        ],
        cwd=repo_root,
        tool_name="check-test-drift",
    )
    data["steps"]["check_test_drift"] = {
        "returncode": drift_result["returncode"],
        "success": drift_result["success"],
    }
    if drift_result["returncode"] != 0:
        errors.append(
            {
                "severity": "error",
                "message": "check_test_drift failed",
                "code": "CIHUB-TEST-METRICS-DRIFT",
            }
        )

    problems = errors + warnings
    if errors or (warnings and getattr(args, "strict", False)):
        return result_fail("Test metrics failed", problems=problems, data=data)

    files_modified = []
    if write_enabled and not getattr(args, "skip_readme", False):
        files_modified.append(str(readme_path))

    return result_ok(
        "Test metrics complete",
        data=data,
        problems=problems,
        files_modified=files_modified or None,
    )


__all__ = ["cmd_test_metrics"]
