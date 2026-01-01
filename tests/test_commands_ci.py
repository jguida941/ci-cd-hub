"""Tests for cihub.commands.ci helper logic."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from cihub.commands import ci as ci_cmd
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def test_get_repo_name_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    assert ci_cmd._get_repo_name({}, tmp_path) == "owner/repo"


def test_get_repo_name_from_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    config = {"repo": {"owner": "org", "name": "project"}}
    assert ci_cmd._get_repo_name(config, tmp_path) == "org/project"


def test_get_repo_name_from_remote(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    with mock.patch.object(ci_cmd, "get_git_remote", return_value="git@github.com:org/project.git"):
        with mock.patch.object(ci_cmd, "parse_repo_from_remote", return_value=("org", "project")):
            assert ci_cmd._get_repo_name({}, tmp_path) == "org/project"


def test_get_env_value_with_fallback() -> None:
    env = {"PRIMARY": "one", "FALLBACK": "two"}
    assert ci_cmd._get_env_value(env, "PRIMARY") == "one"
    assert ci_cmd._get_env_value(env, "MISSING", ["FALLBACK"]) == "two"
    assert ci_cmd._get_env_value(env, None, ["MISSING"]) is None


def test_get_git_commit_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with mock.patch.object(ci_cmd, "resolve_executable", return_value="git"):
        with mock.patch.object(subprocess, "check_output", return_value="abc123\n"):
            assert ci_cmd._get_git_commit(tmp_path) == "abc123"


def test_get_git_commit_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with mock.patch.object(ci_cmd, "resolve_executable", return_value="git"):
        with mock.patch.object(subprocess, "check_output", side_effect=subprocess.CalledProcessError(1, ["git"])):
            assert ci_cmd._get_git_commit(tmp_path) == ""


def test_resolve_workdir(tmp_path: Path) -> None:
    config = {"repo": {"subdir": "src"}}
    assert ci_cmd._resolve_workdir(tmp_path, config, "override") == "override"
    assert ci_cmd._resolve_workdir(tmp_path, config, None) == "src"
    assert ci_cmd._resolve_workdir(tmp_path, {}, None) == "."


def test_detect_java_project_type(tmp_path: Path) -> None:
    pom = tmp_path / "pom.xml"
    pom.write_text("<modules><module>a</module><module>b</module></modules>", encoding="utf-8")
    assert ci_cmd._detect_java_project_type(tmp_path) == "Multi-module (2 modules)"


def test_detect_java_project_type_gradle(tmp_path: Path) -> None:
    (tmp_path / "build.gradle").write_text("// gradle", encoding="utf-8")
    assert ci_cmd._detect_java_project_type(tmp_path) == "Single module"


def test_tool_enabled_and_gate() -> None:
    config = {
        "python": {"tools": {"ruff": {"enabled": True, "fail_on_error": False}, "black": True}},
        "java": {"tools": {"spotbugs": {"enabled": True}}},
    }
    assert ci_cmd._tool_enabled(config, "ruff", "python") is True
    assert ci_cmd._tool_enabled(config, "bandit", "python") is False
    assert ci_cmd._tool_gate_enabled(config, "ruff", "python") is False
    assert ci_cmd._tool_gate_enabled(config, "black", "python") is True
    assert ci_cmd._tool_gate_enabled(config, "spotbugs", "java") is True


def test_warn_reserved_features_adds_problem() -> None:
    problems: list[dict[str, object]] = []
    config = {"chaos": {"enabled": True}}
    ci_cmd._warn_reserved_features(config, problems)
    assert problems
    assert problems[0]["code"] == "CIHUB-CI-RESERVED-FEATURE"


def test_apply_env_overrides_sets_tools_and_summary() -> None:
    config: dict[str, object] = {"python": {"tools": {}}, "reports": {"github_summary": {"enabled": True}}}
    env = {"CIHUB_RUN_PYTEST": "true", "CIHUB_WRITE_GITHUB_SUMMARY": "false"}
    problems: list[dict[str, object]] = []

    ci_cmd._apply_env_overrides(config, "python", env, problems)

    tools = config["python"]["tools"]
    assert tools["pytest"]["enabled"] is True
    assert config["reports"]["github_summary"]["enabled"] is False
    assert problems == []


def test_apply_env_overrides_invalid_value_adds_warning() -> None:
    config: dict[str, object] = {"python": {"tools": {}}}
    env = {"CIHUB_RUN_RUFF": "maybe"}
    problems: list[dict[str, object]] = []

    ci_cmd._apply_env_overrides(config, "python", env, problems)

    assert problems
    assert problems[0]["code"] == "CIHUB-CI-ENV-BOOL"


def test_collect_codecov_files(tmp_path: Path) -> None:
    coverage_file = tmp_path / "coverage.xml"
    coverage_file.write_text("data", encoding="utf-8")
    tool_outputs = {"pytest": {"artifacts": {"coverage": str(coverage_file)}}}

    files = ci_cmd._collect_codecov_files("python", tmp_path, tool_outputs)

    assert files == [coverage_file]


def test_run_codecov_upload_with_no_files() -> None:
    problems: list[dict[str, object]] = []
    ci_cmd._run_codecov_upload([], False, problems)
    assert problems
    assert problems[0]["code"] == "CIHUB-CI-CODECOV-NO-FILES"


def test_cmd_ci_python_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = repo / ".cihub"
    summary_path = repo / "summary.md"
    report_path = repo / "report.json"
    github_summary = repo / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(github_summary))

    config = {
        "language": "python",
        "repo": {"owner": "owner", "name": "repo"},
        "reports": {
            "github_summary": {"enabled": True, "include_metrics": True},
            "codecov": {"enabled": True, "fail_ci_on_error": False},
        },
    }

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

    with mock.patch.object(ci_cmd, "load_ci_config", return_value=config):
        with mock.patch.object(ci_cmd, "_run_python_tools", return_value=({}, {}, {})):
            with mock.patch.object(ci_cmd, "build_python_report", return_value={"results": {}}):
                with mock.patch.object(ci_cmd, "_evaluate_python_gates", return_value=[]):
                    with mock.patch.object(ci_cmd, "render_summary", return_value="summary"):
                        with mock.patch.object(ci_cmd, "_collect_codecov_files", return_value=[]):
                            with mock.patch.object(ci_cmd, "_run_codecov_upload"):
                                with mock.patch.object(ci_cmd, "_notify"):
                                    result = ci_cmd.cmd_ci(args)

    assert result.exit_code == EXIT_SUCCESS
    assert summary_path.exists()
    assert report_path.exists()
    assert github_summary.exists()


def test_cmd_ci_java_non_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text("<project></project>", encoding="utf-8")
    output_dir = repo / ".cihub"

    config = {
        "language": "java",
        "java": {"build_tool": "maven"},
        "repo": {"owner": "owner", "name": "repo"},
        "reports": {"github_summary": {"enabled": False}},
    }

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

    with mock.patch.object(ci_cmd, "load_ci_config", return_value=config):
        with mock.patch.object(ci_cmd, "_run_java_tools", return_value=({}, {}, {})):
            with mock.patch.object(ci_cmd, "build_java_report", return_value={"results": {}}):
                with mock.patch.object(ci_cmd, "_evaluate_java_gates", return_value=[]):
                    with mock.patch.object(ci_cmd, "render_summary", return_value="summary"):
                        with mock.patch.object(ci_cmd, "_notify"):
                            result = ci_cmd.cmd_ci(args)

    assert result == EXIT_SUCCESS


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
    config = {"language": "go"}

    with mock.patch.object(ci_cmd, "load_ci_config", return_value=config):
        result = ci_cmd.cmd_ci(args)

    assert result.exit_code == EXIT_FAILURE
