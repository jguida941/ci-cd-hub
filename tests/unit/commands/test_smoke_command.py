"""Tests for cihub.commands.smoke (unit-level, no real tool execution)."""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path

from cihub.commands import smoke as smoke_cmd
from cihub.types import CommandResult


def test_run_case_passes_required_ci_args(monkeypatch, tmp_path: Path) -> None:
    """Smoke's internal call to cmd_ci must pass required CLI args.

    Regression test: Smoke used to omit cmd_ci args like no_summary/write_github_summary,
    which caused AttributeError at runtime.
    """
    repo_path = tmp_path / "repo"
    repo_path.mkdir(parents=True, exist_ok=True)

    def fake_detect(_args):
        return CommandResult(exit_code=0, summary="ok", data={"language": "python"})

    def fake_init(_args):
        return CommandResult(exit_code=0, summary="ok")

    def fake_validate(_args):
        return CommandResult(exit_code=0, summary="ok")

    captured: dict[str, object] = {}

    def fake_ci(args):
        # These fields are required by cihub.commands.ci.cmd_ci
        assert hasattr(args, "no_summary")
        assert hasattr(args, "write_github_summary")
        assert hasattr(args, "config_from_hub")
        captured["ci_args"] = args
        return CommandResult(exit_code=0, summary="ok")

    monkeypatch.setattr(smoke_cmd, "cmd_detect", fake_detect)
    monkeypatch.setattr(smoke_cmd, "cmd_init", fake_init)
    monkeypatch.setattr(smoke_cmd, "cmd_validate", fake_validate)
    monkeypatch.setattr(smoke_cmd, "cmd_ci", fake_ci)
    monkeypatch.setattr(smoke_cmd, "_detect_java_build_tool", lambda _path: None)

    case = smoke_cmd.SmokeCase(name="fixture", repo_path=repo_path, subdir="", generated=False)
    steps, language = smoke_cmd._run_case(case, full=True, install_deps=False, relax=False, force=False)

    assert language == "python"
    assert steps, "Expected at least one smoke step"
    assert "ci_args" in captured
