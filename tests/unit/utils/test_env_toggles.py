"""Environment toggle behavior tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from cihub.core.ci_runner import shared
from cihub.utils.debug import emit_debug_context


def test_emit_debug_context_opt_in(monkeypatch, capsys, tmp_path: Path):
    monkeypatch.delenv("CIHUB_DEBUG_CONTEXT", raising=False)

    repo_path = tmp_path / "repo"
    emit_debug_context("ci context", [("repo_path", str(repo_path))])
    captured = capsys.readouterr()
    assert captured.err == ""

    monkeypatch.setenv("CIHUB_DEBUG_CONTEXT", "True")
    emit_debug_context("ci context", [("repo_path", str(repo_path))])
    captured = capsys.readouterr()
    assert "[cihub debug]" in captured.err
    assert f"repo_path: {repo_path}" in captured.err


def test_run_tool_command_respects_verbose(monkeypatch, tmp_path: Path):
    calls: list[bool] = []

    def fake_run_command(cmd, workdir, timeout=None, env=None, stream_output=False):
        calls.append(bool(stream_output))
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(shared, "_run_command", fake_run_command)

    monkeypatch.setenv("CIHUB_VERBOSE", "False")
    shared._run_tool_command("demo", ["echo", "hi"], tmp_path, tmp_path)
    monkeypatch.setenv("CIHUB_VERBOSE", "True")
    shared._run_tool_command("demo", ["echo", "hi"], tmp_path, tmp_path)

    assert calls == [False, True]
