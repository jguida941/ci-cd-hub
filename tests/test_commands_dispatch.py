"""Tests for dispatch command helpers."""

from __future__ import annotations

import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from urllib import error as urllib_error

import pytest

from cihub.commands import dispatch as dispatch_cmd
from cihub.commands.dispatch import GitHubRequestResult
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def _base_trigger_args() -> argparse.Namespace:
    return argparse.Namespace(
        subcommand="trigger",
        owner="owner",
        repo="repo",
        workflow="hub-ci.yml",
        ref="main",
        correlation_id=None,
        token=None,
        token_env="HUB_DISPATCH_TOKEN",  # noqa: S106
        dispatch_enabled=True,
        timeout=5,
        json=False,
    )


def test_trigger_missing_token_json(monkeypatch: pytest.MonkeyPatch) -> None:
    args = _base_trigger_args()
    args.json = True
    monkeypatch.delenv("HUB_DISPATCH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    result = dispatch_cmd.cmd_dispatch(args)

    assert result.exit_code == EXIT_FAILURE
    assert "Missing token" in result.summary


def test_trigger_dispatch_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    args = _base_trigger_args()
    args.dispatch_enabled = False
    monkeypatch.setenv("HUB_DISPATCH_TOKEN", "token")

    result = dispatch_cmd.cmd_dispatch(args)

    assert result.exit_code == EXIT_SUCCESS
    assert "skipped" in result.artifacts


def test_trigger_success_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _base_trigger_args()
    monkeypatch.setenv("HUB_DISPATCH_TOKEN", "token")
    output_path = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))

    # Mock with GitHubRequestResult (dispatch returns successful result)
    dispatch_result = GitHubRequestResult(data={})
    with mock.patch.object(dispatch_cmd, "_dispatch_workflow", return_value=dispatch_result):
        with mock.patch.object(dispatch_cmd, "_poll_for_run_id", return_value="12345"):
            result = dispatch_cmd.cmd_dispatch(args)

    assert result.exit_code == EXIT_SUCCESS
    output_text = output_path.read_text(encoding="utf-8")
    assert "run_id=12345" in output_text
    assert "workflow_id=hub-ci.yml" in output_text


def test_trigger_poll_failure_json(monkeypatch: pytest.MonkeyPatch) -> None:
    args = _base_trigger_args()
    args.json = True
    monkeypatch.setenv("HUB_DISPATCH_TOKEN", "token")

    # Mock with GitHubRequestResult (dispatch succeeds but poll fails to find run ID)
    dispatch_result = GitHubRequestResult(data={})
    with mock.patch.object(dispatch_cmd, "_dispatch_workflow", return_value=dispatch_result):
        with mock.patch.object(dispatch_cmd, "_poll_for_run_id", return_value=None):
            result = dispatch_cmd.cmd_dispatch(args)

    assert result.exit_code == EXIT_FAILURE
    assert "could not determine run ID" in result.summary


def test_metadata_writes_file(tmp_path: Path) -> None:
    args = argparse.Namespace(
        subcommand="metadata",
        config_basename="repo-config",
        owner="owner",
        repo="repo",
        output_dir=str(tmp_path),
        subdir="src",
        language="python",
        branch="main",
        workflow="hub-ci.yml",
        run_id="42",
        correlation_id="corr-1",
        status="success",
        json=False,
    )

    result = dispatch_cmd.cmd_dispatch(args)

    assert result.exit_code == EXIT_SUCCESS
    metadata_path = tmp_path / "repo-config.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["repo"] == "owner/repo"
    assert payload["run_id"] == "42"


def test_metadata_writes_file_nested_basename(tmp_path: Path) -> None:
    args = argparse.Namespace(
        subcommand="metadata",
        config_basename="owner/repo-config",
        owner="owner",
        repo="repo",
        output_dir=str(tmp_path),
        subdir="src",
        language="python",
        branch="main",
        workflow="hub-ci.yml",
        run_id="42",
        correlation_id="corr-1",
        status="success",
        json=False,
    )

    result = dispatch_cmd.cmd_dispatch(args)

    assert result.exit_code == EXIT_SUCCESS
    metadata_path = tmp_path / "owner" / "repo-config.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["config"] == "owner/repo-config"
    assert payload["repo"] == "owner/repo"
    assert payload["run_id"] == "42"


def test_metadata_json_mode(tmp_path: Path) -> None:
    args = argparse.Namespace(
        subcommand="metadata",
        config_basename="repo-config",
        owner="owner",
        repo="repo",
        output_dir=str(tmp_path),
        subdir="",
        language="python",
        branch="main",
        workflow="hub-ci.yml",
        run_id="42",
        correlation_id="corr-1",
        status="success",
        json=True,
    )

    result = dispatch_cmd.cmd_dispatch(args)

    assert result.exit_code == EXIT_SUCCESS
    assert "Generated dispatch metadata" in result.summary


def test_github_request_http_error() -> None:
    error_body = io.BytesIO(b'{"message":"bad"}')
    error = urllib_error.HTTPError(
        url="https://api.github.com",
        code=403,
        msg="forbidden",
        hdrs=None,
        fp=error_body,
    )

    with mock.patch.object(dispatch_cmd.request, "urlopen", side_effect=error):
        result = dispatch_cmd._github_request("https://api.github.com", "token")
        # Now returns GitHubRequestResult with error instead of None
        assert not result.ok
        assert result.status_code == 403
        assert "403" in result.error


def test_poll_for_run_id_found(monkeypatch: pytest.MonkeyPatch) -> None:
    started_at = 1000.0
    times = iter([started_at, started_at + 1.0])
    monkeypatch.setattr(dispatch_cmd.time, "time", lambda: next(times))
    monkeypatch.setattr(dispatch_cmd.time, "sleep", lambda *_args, **_kwargs: None)

    created_at = datetime.fromtimestamp(started_at, timezone.utc).isoformat().replace("+00:00", "Z")
    run = {"created_at": created_at, "head_branch": "main", "status": "in_progress", "id": 123}
    # Return GitHubRequestResult instead of raw dict
    api_result = GitHubRequestResult(data={"workflow_runs": [run]})
    monkeypatch.setattr(dispatch_cmd, "_github_request", lambda *_args, **_kwargs: api_result)

    run_id = dispatch_cmd._poll_for_run_id(
        "owner",
        "repo",
        "hub-ci.yml",
        "main",
        started_at,
        "token",
        timeout_sec=5,
        initial_delay=0,
    )

    assert run_id == "123"
