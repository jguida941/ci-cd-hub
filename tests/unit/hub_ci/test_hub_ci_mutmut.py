"""Tests for mutmut hub-ci wrapper behavior."""

# TEST-METRICS:

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.commands.hub_ci.python_tools import cmd_mutmut  # noqa: E402
from cihub.exit_codes import EXIT_FAILURE  # noqa: E402


def test_cmd_mutmut_fallback_logs(tmp_path) -> None:
    args = argparse.Namespace(
        workdir=str(tmp_path),
        output_dir=str(tmp_path),
        min_mutation_score=70,
        output=None,
        github_output=False,
        summary=None,
        github_summary=False,
        json=True,
    )
    first_proc = subprocess.CompletedProcess(["mutmut", "run"], 1, stdout="", stderr="")
    fallback_proc = subprocess.CompletedProcess(
        ["mutmut", "run", "--max-children", "1"],
        1,
        stdout="Traceback (most recent call last):\nValueError: boom\n",
        stderr="",
    )

    with mock.patch(
        "cihub.commands.hub_ci.python_tools._run_command",
        side_effect=[first_proc, fallback_proc],
    ):
        result = cmd_mutmut(args)

    assert result.exit_code == EXIT_FAILURE
    assert result.data.get("fallback_used") is True
    assert "boom" in result.data.get("error", "")
    assert (tmp_path / "mutmut-run-fallback.log").exists()
