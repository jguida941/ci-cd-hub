"""Tests for discover command handler."""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import pytest

from cihub.commands import discover as discover_cmd
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import DiscoveryResult
from cihub.services.types import RepoEntry


def test_discover_conflicting_filters() -> None:
    args = argparse.Namespace(
        hub_root=None,
        json=False,
        run_group="",
        repos="",
        central_only=True,
        dispatch_only=True,
        github_output=False,
    )

    result = discover_cmd.cmd_discover(args)

    assert result.exit_code == EXIT_FAILURE
    assert "Choose only one" in result.summary


def test_discover_json_with_github_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entry = RepoEntry(
        config_basename="repo1",
        name="repo1",
        owner="owner",
        language="python",
        branch="main",
        subdir="",
        subdir_safe="",
        run_group="full",
        dispatch_enabled=True,
        dispatch_workflow="hub-ci.yml",
        use_central_runner=True,
        tools={"run_pytest": True},
        thresholds={},
        java_version=None,
        python_version="3.12",
        build_tool=None,
        retention_days=30,
        write_github_summary=True,
    )
    result_obj = DiscoveryResult(success=True, entries=[entry], warnings=[])

    args = argparse.Namespace(
        hub_root=str(tmp_path),
        json=True,
        run_group="",
        repos="",
        central_only=False,
        dispatch_only=False,
        github_output=True,
    )

    output_file = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    with mock.patch.object(discover_cmd, "discover_repositories", return_value=result_obj):
        result = discover_cmd.cmd_discover(args)

    assert result.exit_code == EXIT_SUCCESS
    assert result.data["count"] == 1
    output_text = output_file.read_text(encoding="utf-8")
    assert "matrix=" in output_text
    assert "count=1" in output_text
    payload = json.loads(output_text.split("matrix=", 1)[1].splitlines()[0])
    assert payload["include"][0]["name"] == "repo1"


def test_discover_no_entries_json(tmp_path: Path) -> None:
    result_obj = DiscoveryResult(success=True, entries=[], warnings=[])
    args = argparse.Namespace(
        hub_root=str(tmp_path),
        json=True,
        run_group="",
        repos="",
        central_only=False,
        dispatch_only=False,
        github_output=False,
    )

    with mock.patch.object(discover_cmd, "discover_repositories", return_value=result_obj):
        result = discover_cmd.cmd_discover(args)

    assert result.exit_code == EXIT_FAILURE
    assert "No repositories found" in result.summary
