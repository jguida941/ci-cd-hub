"""Tests for hub-ci test-metrics command."""

# TEST-METRICS:

from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def _base_args() -> argparse.Namespace:
    return argparse.Namespace(
        coverage_file="coverage.json",
        coverage_db=".coverage",
        mutation_file=".mutmut-cache/results.json",
        tests_dir="tests",
        readme="tests/README.md",
        write=False,
        allow_non_main=False,
        strict=False,
        skip_readme=False,
    )


def _write_scripts(repo_root: Path) -> None:
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for name in ("update_test_metrics.py", "generate_test_readme.py", "check_test_drift.py"):
        (scripts_dir / name).write_text("#!/usr/bin/env python3\n", encoding="utf-8")


def _fake_run_and_capture(readme_output: str = ""):
    def _runner(cmd, cwd, tool_name="", env=None):  # noqa: ANN001
        cmd_str = " ".join(str(c) for c in cmd)
        if "generate_test_readme.py" in cmd_str and "--dry-run" in cmd_str:
            return {
                "stdout": readme_output,
                "stderr": "",
                "returncode": 0,
                "success": True,
                "tool": tool_name,
            }
        return {
            "stdout": "",
            "stderr": "",
            "returncode": 0,
            "success": True,
            "tool": tool_name,
        }

    return _runner


def test_test_metrics_check_mode_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cihub.commands.hub_ci.test_metrics import cmd_test_metrics

    _write_scripts(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "coverage.json").write_text("{}", encoding="utf-8")
    readme_path = tmp_path / "tests" / "README.md"
    readme_path.write_text(
        "> Last updated: 2026-01-17 00:00:00\nREADME_CONTENT",
        encoding="utf-8",
    )

    monkeypatch.setattr("cihub.commands.hub_ci.test_metrics.project_root", lambda: tmp_path)
    monkeypatch.setattr(
        "cihub.commands.hub_ci.test_metrics.run_and_capture",
        _fake_run_and_capture(readme_output="> Last updated: 2026-01-17 01:00:00\nREADME_CONTENT"),
    )

    args = _base_args()
    result = cmd_test_metrics(args)

    assert result.exit_code == 0
    assert result.data["readme_status"] == "ok"


def test_test_metrics_strict_fails_on_stale_readme(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cihub.commands.hub_ci.test_metrics import cmd_test_metrics
    from cihub.exit_codes import EXIT_FAILURE

    _write_scripts(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "coverage.json").write_text("{}", encoding="utf-8")
    readme_path = tmp_path / "tests" / "README.md"
    readme_path.write_text("OLD_CONTENT", encoding="utf-8")

    monkeypatch.setattr("cihub.commands.hub_ci.test_metrics.project_root", lambda: tmp_path)
    monkeypatch.setattr(
        "cihub.commands.hub_ci.test_metrics.run_and_capture",
        _fake_run_and_capture(readme_output="NEW_CONTENT"),
    )

    args = _base_args()
    args.strict = True
    result = cmd_test_metrics(args)

    assert result.exit_code == EXIT_FAILURE
    assert any(p["code"] == "CIHUB-TEST-METRICS-README-STALE" for p in result.problems)


def test_test_metrics_write_skipped_on_non_main_ci(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cihub.commands.hub_ci.test_metrics import cmd_test_metrics

    _write_scripts(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "coverage.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr("cihub.commands.hub_ci.test_metrics.project_root", lambda: tmp_path)
    monkeypatch.setattr(
        "cihub.commands.hub_ci.test_metrics.run_and_capture",
        _fake_run_and_capture(),
    )

    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature/test")

    args = _base_args()
    args.write = True
    args.skip_readme = True
    result = cmd_test_metrics(args)

    assert result.data["write_enabled"] is False
    assert any(p["code"] == "CIHUB-TEST-METRICS-WRITE-SKIPPED" for p in result.problems)
