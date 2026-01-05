"""Debug mode behavior tests for the CLI."""

from __future__ import annotations

import json
from unittest import mock

import pytest

from cihub.cli import main


def test_debug_mode_exception_behavior(monkeypatch, capsys):
    monkeypatch.setenv("CIHUB_DEBUG", "1")

    with mock.patch("cihub.cli.cmd_config") as mock_cmd:
        mock_cmd.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            main(["config", "--repo", "test", "show"])

    capsys.readouterr()  # Clear traceback/debug output

    with mock.patch("cihub.cli.cmd_config") as mock_cmd:
        mock_cmd.side_effect = RuntimeError("boom")
        result = main(["config", "--repo", "test", "show", "--json"])

    assert result != 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "error"
