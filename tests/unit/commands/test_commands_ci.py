"""Tests for CI engine helpers and CLI adapter behavior."""

# TEST-METRICS:

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from cihub.commands import ci as ci_cmd
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import ci_engine
from cihub.services.triage.types import TriageBundle


def test_get_repo_name_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    assert ci_engine._get_repo_name({}, tmp_path) == "owner/repo"


def test_get_repo_name_from_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    config = {"repo": {"owner": "org", "name": "project"}}
    assert ci_engine._get_repo_name(config, tmp_path) == "org/project"


def test_get_repo_name_from_remote(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    with mock.patch("cihub.utils.project.get_git_remote", return_value="git@github.com:org/project.git"):
        with mock.patch("cihub.utils.project.parse_repo_from_remote", return_value=("org", "project")):
            assert ci_engine._get_repo_name({}, tmp_path) == "org/project"


def test_get_env_value_with_fallback() -> None:
    env = {"PRIMARY": "one", "FALLBACK": "two"}
    assert ci_engine._get_env_value(env, "PRIMARY") == "one"
    assert ci_engine._get_env_value(env, "MISSING", ["FALLBACK"]) == "two"
    assert ci_engine._get_env_value(env, None, ["MISSING"]) is None


def test_get_git_commit_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with mock.patch.object(ci_engine, "resolve_executable", return_value="git"):
        mock_result = mock.Mock(stdout="abc123\n")
        with mock.patch.object(subprocess, "run", return_value=mock_result):
            assert ci_engine._get_git_commit(tmp_path) == "abc123"


def test_get_git_commit_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with mock.patch.object(ci_engine, "resolve_executable", return_value="git"):
        with mock.patch.object(subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["git"])):
            assert ci_engine._get_git_commit(tmp_path) == ""


def test_resolve_workdir(tmp_path: Path) -> None:
    config = {"repo": {"subdir": "src"}}
    assert ci_engine._resolve_workdir(tmp_path, config, "override") == "override"
    assert ci_engine._resolve_workdir(tmp_path, config, None) == "src"
    assert ci_engine._resolve_workdir(tmp_path, {}, None) == "."


def test_detect_java_project_type(tmp_path: Path) -> None:
    pom = tmp_path / "pom.xml"
    pom.write_text("<modules><module>a</module><module>b</module></modules>", encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Multi-module (2 modules)"


def test_detect_java_project_type_gradle(tmp_path: Path) -> None:
    (tmp_path / "build.gradle").write_text("// gradle", encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Single module"


def test_tool_enabled_and_gate() -> None:
    config = {
        "python": {"tools": {"ruff": {"enabled": True, "fail_on_error": False}, "black": True}},
        "java": {"tools": {"spotbugs": {"enabled": True}}},
    }
    assert ci_engine._tool_enabled(config, "ruff", "python") is True
    assert ci_engine._tool_enabled(config, "bandit", "python") is False
    assert ci_engine._tool_gate_enabled(config, "ruff", "python") is False
    assert ci_engine._tool_gate_enabled(config, "black", "python") is True
    assert ci_engine._tool_gate_enabled(config, "spotbugs", "java") is True


def test_tool_gate_enabled_python_tools() -> None:
    """Test all Python tool gate options."""
    # Test each Python tool gate option
    config = {
        "python": {
            "tools": {
                "black": {"enabled": True, "fail_on_format_issues": False},
                "isort": {"enabled": True, "fail_on_issues": False},
                "bandit": {"enabled": True, "fail_on_high": False},
                "pip_audit": {"enabled": True, "fail_on_vuln": False},
                "semgrep": {"enabled": True, "fail_on_findings": False},
                "trivy": {"enabled": True, "fail_on_critical": False, "fail_on_high": False},
            }
        }
    }
    assert ci_engine._tool_gate_enabled(config, "black", "python") is False
    assert ci_engine._tool_gate_enabled(config, "isort", "python") is False
    assert ci_engine._tool_gate_enabled(config, "bandit", "python") is False
    assert ci_engine._tool_gate_enabled(config, "pip_audit", "python") is False
    assert ci_engine._tool_gate_enabled(config, "semgrep", "python") is False
    assert ci_engine._tool_gate_enabled(config, "trivy", "python") is False


def test_tool_gate_enabled_java_tools() -> None:
    """Test all Java tool gate options."""
    config = {
        "java": {
            "tools": {
                "checkstyle": {"enabled": True, "fail_on_violation": False},
                "pmd": {"enabled": True, "fail_on_violation": False},
                "semgrep": {"enabled": True, "fail_on_findings": False},
                "trivy": {"enabled": True, "fail_on_critical": False, "fail_on_high": False},
            }
        }
    }
    assert ci_engine._tool_gate_enabled(config, "checkstyle", "java") is False
    assert ci_engine._tool_gate_enabled(config, "pmd", "java") is False
    assert ci_engine._tool_gate_enabled(config, "semgrep", "java") is False
    assert ci_engine._tool_gate_enabled(config, "trivy", "java") is False


def test_warn_reserved_features_adds_problem() -> None:
    problems: list[dict[str, object]] = []
    config = {"chaos": {"enabled": True}}
    ci_engine._warn_reserved_features(config, problems)
    assert problems
    assert problems[0]["code"] == "CIHUB-CI-RESERVED-FEATURE"


def test_warn_reserved_features_kyverno() -> None:
    """Test that kyverno also triggers reserved feature warning."""
    problems: list[dict[str, object]] = []
    config = {"kyverno": {"enabled": True}}
    ci_engine._warn_reserved_features(config, problems)
    assert problems
    assert problems[0]["code"] == "CIHUB-CI-RESERVED-FEATURE"
    assert "Kyverno" in problems[0]["message"]


def test_get_env_name_returns_config_value() -> None:
    config = {"codecov_env_name": "CODECOV_CUSTOM"}
    assert ci_engine._get_env_name(config, "codecov_env_name", "CODECOV_TOKEN") == "CODECOV_CUSTOM"


def test_get_env_name_returns_default() -> None:
    config = {}
    assert ci_engine._get_env_name(config, "codecov_env_name", "CODECOV_TOKEN") == "CODECOV_TOKEN"


def test_get_env_name_ignores_whitespace_only() -> None:
    config = {"codecov_env_name": "   "}
    assert ci_engine._get_env_name(config, "codecov_env_name", "CODECOV_TOKEN") == "CODECOV_TOKEN"


def test_split_problems() -> None:
    problems = [
        {"severity": "error", "message": "Error 1"},
        {"severity": "warning", "message": "Warning 1"},
        {"severity": "error", "message": "Error 2"},
        {"severity": "info", "message": "Info 1"},
    ]
    errors, warnings = ci_engine._split_problems(problems)
    assert errors == ["Error 1", "Error 2"]
    assert warnings == ["Warning 1"]


def test_split_problems_empty_messages_filtered() -> None:
    problems = [
        {"severity": "error", "message": ""},
        {"severity": "warning", "message": "Valid warning"},
    ]
    errors, warnings = ci_engine._split_problems(problems)
    assert errors == []
    assert warnings == ["Valid warning"]


def test_detect_java_project_type_settings_gradle(tmp_path: Path) -> None:
    """Test detection of multi-module Gradle project via settings.gradle."""
    (tmp_path / "settings.gradle").write_text("include 'sub1', 'sub2'", encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Multi-module"


def test_detect_java_project_type_settings_gradle_kts(tmp_path: Path) -> None:
    """Test detection of multi-module Gradle project via settings.gradle.kts."""
    (tmp_path / "settings.gradle.kts").write_text('include("sub1")', encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Multi-module"


def test_detect_java_project_type_unknown(tmp_path: Path) -> None:
    """Test unknown project type when no build files present."""
    assert ci_engine._detect_java_project_type(tmp_path) == "Unknown"


def test_detect_java_project_type_pom_single_module(tmp_path: Path) -> None:
    """Test single module Maven project (pom without modules)."""
    (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Single module"


def test_apply_env_overrides_sets_tools_and_summary() -> None:
    config: dict[str, object] = {"python": {"tools": {}}, "reports": {"github_summary": {"enabled": True}}}
    env = {"CIHUB_RUN_PYTEST": "true", "CIHUB_WRITE_GITHUB_SUMMARY": "false"}
    problems: list[dict[str, object]] = []

    ci_engine._apply_env_overrides(config, "python", env, problems)

    tools = config["python"]["tools"]
    assert tools["pytest"]["enabled"] is True
    assert config["reports"]["github_summary"]["enabled"] is False
    assert problems == []


def test_apply_env_overrides_invalid_value_adds_warning() -> None:
    config: dict[str, object] = {"python": {"tools": {}}}
    env = {"CIHUB_RUN_RUFF": "maybe"}
    problems: list[dict[str, object]] = []

    ci_engine._apply_env_overrides(config, "python", env, problems)

    assert problems
    assert problems[0]["code"] == "CIHUB-CI-ENV-BOOL"


def test_collect_codecov_files(tmp_path: Path) -> None:
    coverage_file = tmp_path / "coverage.xml"
    coverage_file.write_text("data", encoding="utf-8")
    tool_outputs = {"pytest": {"artifacts": {"coverage": str(coverage_file)}}}

    files = ci_engine._collect_codecov_files("python", tmp_path, tool_outputs)

    assert files == [coverage_file]


def test_run_codecov_upload_with_no_files() -> None:
    problems: list[dict[str, object]] = []
    ci_engine._run_codecov_upload([], False, problems)
    assert problems
    assert problems[0]["code"] == "CIHUB-CI-CODECOV-NO-FILES"


def test_cmd_ci_python_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = repo / ".cihub"
    summary_path = repo / "summary.md"
    report_path = repo / "report.json"

    args = argparse.Namespace(
        repo=str(repo),
        json=True,
        output_dir=str(output_dir),
        summary=str(summary_path),
        report=str(report_path),
        workdir=None,
        install_deps=False,
        correlation_id=None,
        no_summary=False,
        write_github_summary=None,
        config_from_hub=None,
    )

    service_result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        report_path=report_path,
        summary_path=summary_path,
        artifacts={"report": str(report_path), "summary": str(summary_path)},
        data={"report_path": str(report_path), "summary_path": str(summary_path)},
    )

    with mock.patch.object(ci_cmd, "run_ci", return_value=service_result):
        result = ci_cmd.cmd_ci(args)

    assert result.exit_code == EXIT_SUCCESS
    assert result.data["report_path"] == str(report_path)
    assert result.data["summary_path"] == str(summary_path)


def test_cmd_ci_java_non_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = repo / ".cihub"

    args = argparse.Namespace(
        repo=str(repo),
        json=False,
        output_dir=str(output_dir),
        summary=None,
        report=None,
        workdir=None,
        install_deps=False,
        correlation_id=None,
        no_summary=False,
        write_github_summary=None,
        config_from_hub=None,
    )

    service_result = ci_engine.CiRunResult(success=True, exit_code=EXIT_SUCCESS)

    with mock.patch.object(ci_cmd, "run_ci", return_value=service_result):
        result = ci_cmd.cmd_ci(args)

    assert result.exit_code == EXIT_SUCCESS


def test_cmd_ci_unknown_language(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    args = argparse.Namespace(
        repo=str(repo),
        json=True,
        output_dir=str(repo / ".cihub"),
        summary=None,
        report=None,
        workdir=None,
        install_deps=False,
        correlation_id=None,
        no_summary=False,
        write_github_summary=None,
        config_from_hub=None,
    )
    service_result = ci_engine.CiRunResult(success=False, exit_code=EXIT_FAILURE, errors=["bad language"])

    with mock.patch.object(ci_cmd, "run_ci", return_value=service_result):
        result = ci_cmd.cmd_ci(args)

    assert result.exit_code == EXIT_FAILURE


def test_result_to_command_result_with_paths(tmp_path: Path) -> None:
    """Test _result_to_command_result includes file paths in files_generated."""
    report = tmp_path / "report.json"
    summary = tmp_path / "summary.md"
    ci_result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        report_path=report,
        summary_path=summary,
    )

    result = ci_cmd._result_to_command_result(ci_result)

    assert result.exit_code == EXIT_SUCCESS
    assert result.files_generated is not None
    assert str(report) in result.files_generated
    assert str(summary) in result.files_generated


def test_result_to_command_result_with_problems() -> None:
    """Test _result_to_command_result includes problems in result."""
    ci_result = ci_engine.CiRunResult(
        success=False,
        exit_code=EXIT_FAILURE,
        problems=[
            {"severity": "error", "message": "Test failed"},
            {"severity": "warning", "message": "Coverage low"},
        ],
    )

    result = ci_cmd._result_to_command_result(ci_result)

    assert result.exit_code == EXIT_FAILURE
    assert len(result.problems) == 2
    assert result.problems[0]["message"] == "Test failed"
    assert result.problems[1]["message"] == "Coverage low"


def test_summary_for_result_with_errors_no_report() -> None:
    """Test _summary_for_result returns first error when no report."""
    result = ci_engine.CiRunResult(
        success=False,
        exit_code=EXIT_FAILURE,
        errors=["First error", "Second error"],
        report={},
    )
    assert ci_cmd._summary_for_result(result) == "First error"


def test_summary_for_result_with_problems() -> None:
    """Test _summary_for_result returns issues message when problems exist."""
    result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        problems=[{"severity": "warning", "message": "Low coverage"}],
    )
    assert ci_cmd._summary_for_result(result) == "CI completed with issues"


def test_summary_for_result_success() -> None:
    """Test _summary_for_result returns success message."""
    result = ci_engine.CiRunResult(success=True, exit_code=EXIT_SUCCESS)
    assert ci_cmd._summary_for_result(result) == "CI completed"


def test_emit_triage_bundle_reads_ai_loop_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, dict[str, object]] = {}

    def fake_generate(
        *,
        output_dir: Path,
        report_path: Path | None = None,
        summary_path: Path | None = None,
        meta: dict[str, object] | None = None,
    ) -> TriageBundle:
        captured["meta"] = meta or {}
        return TriageBundle(triage={}, priority={}, markdown="", history_entry={})

    def fake_write(bundle: TriageBundle, output_dir: Path) -> dict[str, Path]:
        return {}

    args = argparse.Namespace(
        repo=str(tmp_path),
        output_dir=str(tmp_path / ".cihub"),
        correlation_id=None,
    )

    monkeypatch.setenv("CIHUB_EMIT_TRIAGE", "true")
    monkeypatch.setenv("CIHUB_AI_LOOP_ITERATION", "2")
    monkeypatch.setenv("CIHUB_AI_LOOP_MAX_ITERATIONS", "9")
    monkeypatch.setattr(ci_cmd, "generate_triage_bundle", fake_generate)
    monkeypatch.setattr(ci_cmd, "write_triage_bundle", fake_write)

    ci_cmd._emit_triage_bundle(args, None, error=None)

    meta = captured["meta"]
    assert meta["iteration"] == 2
    assert meta["max_iterations"] == 9


def test_result_to_command_result_sets_summary_and_artifacts() -> None:
    ci_result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        problems=[{"severity": "warning", "message": "Low coverage"}],
        artifacts={"report": "report.json"},
        data={"summary": "ok"},
    )

    result = ci_cmd._result_to_command_result(ci_result)

    assert result.summary == "CI completed with issues"
    assert result.artifacts == {"report": "report.json"}
    assert result.data == {"summary": "ok"}


def test_describe_path_and_format_list(tmp_path: Path) -> None:
    existing = tmp_path / "exists.txt"
    existing.write_text("ok", encoding="utf-8")
    missing = tmp_path / "missing.txt"

    assert ci_cmd._describe_path(existing) == str(existing)
    assert "(missing)" in ci_cmd._describe_path(missing)
    assert ci_cmd._format_list(["a", "b"]) == "a, b"
    assert ci_cmd._format_list([]) == "-"


def test_resolve_output_dir_relative_and_absolute(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    absolute = tmp_path / "out"
    args_relative = argparse.Namespace(repo=str(repo), output_dir=".cihub")
    args_absolute = argparse.Namespace(repo=str(repo), output_dir=str(absolute))

    assert ci_cmd._resolve_output_dir(args_relative) == (repo / ".cihub").resolve()
    assert ci_cmd._resolve_output_dir(args_absolute) == absolute.resolve()


def test_get_ai_loop_env_int_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    name = "CIHUB_AI_LOOP_ITERATION"
    monkeypatch.delenv(name, raising=False)
    assert ci_cmd._get_ai_loop_env_int(name) is None

    monkeypatch.setenv(name, "3")
    assert ci_cmd._get_ai_loop_env_int(name) == 3

    monkeypatch.setenv(name, "0")
    assert ci_cmd._get_ai_loop_env_int(name) is None

    monkeypatch.setenv(name, "-2")
    assert ci_cmd._get_ai_loop_env_int(name) is None

    monkeypatch.setenv(name, "abc")
    assert ci_cmd._get_ai_loop_env_int(name) is None


def test_emit_triage_bundle_prefers_args_and_result_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_generate(
        *,
        output_dir: Path,
        report_path: Path | None = None,
        summary_path: Path | None = None,
        meta: dict[str, object] | None = None,
    ) -> TriageBundle:
        captured["output_dir"] = output_dir
        captured["report_path"] = report_path
        captured["summary_path"] = summary_path
        captured["meta"] = meta or {}
        return TriageBundle(triage={}, priority={}, markdown="", history_entry={})

    def fake_write(bundle: TriageBundle, output_dir: Path) -> dict[str, Path]:
        return {}

    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = repo / ".cihub"
    report_path = output_dir / "report.json"
    summary_path = output_dir / "summary.md"
    args = argparse.Namespace(
        repo=str(repo),
        output_dir=str(output_dir),
        correlation_id="corr-123",
        ai_loop_iteration=4,
        ai_loop_max_iterations=9,
    )
    result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        report_path=report_path,
        summary_path=summary_path,
    )

    monkeypatch.setenv("CIHUB_EMIT_TRIAGE", "true")
    monkeypatch.setenv("CIHUB_AI_LOOP_ITERATION", "2")
    monkeypatch.setenv("CIHUB_AI_LOOP_MAX_ITERATIONS", "5")
    monkeypatch.setattr(ci_cmd, "generate_triage_bundle", fake_generate)
    monkeypatch.setattr(ci_cmd, "write_triage_bundle", fake_write)

    ci_cmd._emit_triage_bundle(args, result, error="boom")

    meta = captured["meta"]
    assert captured["output_dir"] == output_dir
    assert captured["report_path"] == report_path
    assert captured["summary_path"] == summary_path
    assert meta["command"] == "cihub ci"
    assert meta["args"] == []
    assert meta["iteration"] == 4
    assert meta["max_iterations"] == 9
    assert meta["correlation_id"] == "corr-123"
    assert meta["repo"] == str(repo.resolve())
    assert meta["branch"] == ""
    assert meta["commit_sha"] == ""
    assert meta["workflow_ref"] == ""
    assert meta["error"] == "boom"


def test_emit_triage_bundle_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(repo=".", output_dir=".cihub", correlation_id=None)

    def fake_generate(**_: object) -> TriageBundle:
        raise AssertionError("generate_triage_bundle should not be called")

    monkeypatch.delenv("CIHUB_EMIT_TRIAGE", raising=False)
    monkeypatch.setattr(ci_cmd, "generate_triage_bundle", fake_generate)

    ci_cmd._emit_triage_bundle(args, None, error=None)


def _capture_debug_context(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_emit(title: str, entries: list[tuple[str, object]]) -> None:
        captured["title"] = title
        captured["entries"] = entries

    monkeypatch.setattr(ci_cmd, "emit_debug_context", fake_emit)
    return captured


def test_emit_ci_debug_context_with_repo_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    hub_root = tmp_path / "hub"
    (hub_root / "config").mkdir(parents=True)
    defaults_path = hub_root / "config" / "defaults.yaml"
    defaults_path.write_text("defaults", encoding="utf-8")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".ci-hub.yml").write_text("repo", encoding="utf-8")
    output_dir = repo / ".cihub"
    report_path = output_dir / "report.json"
    summary_path = output_dir / "summary.md"

    args = argparse.Namespace(
        repo=str(repo),
        output_dir=".cihub",
        workdir="fallback",
        correlation_id="corr-123",
        install_deps=True,
        write_github_summary=True,
        no_summary=False,
        config_from_hub=None,
    )
    result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        report_path=report_path,
        summary_path=summary_path,
        report={
            "environment": {"workdir": "src"},
            "tools_configured": {"ruff": True, "pytest": True, "bandit": False},
            "tools_ran": {"ruff": True},
            "tools_success": {"ruff": False},
            "python_version": "3.12",
            "hub_correlation_id": "corr-456",
        },
    )

    captured = _capture_debug_context(monkeypatch)
    monkeypatch.setattr(ci_cmd, "hub_root", lambda: hub_root)

    ci_cmd._emit_ci_debug_context(args, result)

    entries = dict(captured["entries"])
    assert captured["title"] == "ci context"
    assert entries["repo_path"] == str(repo.resolve())
    assert entries["workdir"] == "src"
    assert entries["language"] == "python"
    assert entries["config_sources"] == f"{repo / '.ci-hub.yml'}, {defaults_path}"
    assert entries["output_dir"] == str((repo / ".cihub").resolve())
    assert entries["report_path"] == str(report_path)
    assert entries["summary_path"] == str(summary_path)
    assert entries["correlation_id"] == "corr-456"
    assert entries["install_deps"] == "True"
    assert entries["write_github_summary"] == "True"
    assert entries["no_summary"] == "False"
    assert entries["config_from_hub"] is None
    assert entries["tools_enabled"] == "pytest, ruff"
    assert entries["tools_disabled"] == "bandit"
    assert entries["tools_skipped"] == "pytest"
    assert entries["tools_failed"] == "ruff"
    assert entries["exit_code"] == str(EXIT_SUCCESS)


def test_emit_ci_debug_context_with_hub_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    hub_root = tmp_path / "hub"
    repo_config = hub_root / "config" / "repos"
    repo_config.mkdir(parents=True)
    defaults_path = hub_root / "config" / "defaults.yaml"
    defaults_path.write_text("defaults", encoding="utf-8")
    hub_config = repo_config / "sample.yaml"
    hub_config.write_text("config", encoding="utf-8")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".ci-hub.yml").write_text("repo", encoding="utf-8")

    args = argparse.Namespace(
        repo=str(repo),
        output_dir=str(repo / ".cihub"),
        workdir="work",
        correlation_id="corr-789",
        install_deps=False,
        write_github_summary=False,
        no_summary=True,
        config_from_hub="sample",
    )
    result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        report={
            "java_version": "17",
            "tools_configured": {"checkstyle": True},
            "tools_ran": {"checkstyle": True},
            "tools_success": {"checkstyle": True},
        },
    )

    captured = _capture_debug_context(monkeypatch)
    monkeypatch.setattr(ci_cmd, "hub_root", lambda: hub_root)

    ci_cmd._emit_ci_debug_context(args, result)

    entries = dict(captured["entries"])
    assert entries["language"] == "java"
    assert entries["workdir"] == "work"
    assert entries["correlation_id"] == "corr-789"
    assert entries["config_from_hub"] == "sample"
    assert entries["config_sources"] == f"{hub_config}, {repo / '.ci-hub.yml'}, {defaults_path}"
