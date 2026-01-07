import argparse
import subprocess

from cihub.commands import preflight as preflight_module
from cihub.commands.preflight import cmd_preflight
from cihub.types import CommandResult


def test_preflight_json(monkeypatch) -> None:
    def fake_which(command: str) -> str | None:
        if command in {"git", "gh", "pytest", "ruff", "black", "isort"}:
            return f"/usr/bin/{command}"
        return None

    def fake_safe_run(cmd, **kwargs):  # noqa: ANN001 - test stub
        return subprocess.CompletedProcess(
            args=list(cmd),
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(preflight_module, "_command_exists", fake_which)
    monkeypatch.setattr(preflight_module, "safe_run", fake_safe_run)

    args = argparse.Namespace(json=True, full=True)
    result = cmd_preflight(args)
    assert isinstance(result, CommandResult)
    assert "checks" in result.data
