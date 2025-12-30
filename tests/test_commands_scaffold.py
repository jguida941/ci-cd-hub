import argparse
from pathlib import Path

from cihub.cli import CommandResult
from cihub.commands.scaffold import cmd_scaffold


def test_scaffold_python_pyproject(tmp_path: Path) -> None:
    dest = tmp_path / "fixture"
    args = argparse.Namespace(
        list=False,
        type="python-pyproject",
        path=str(dest),
        force=False,
        json=True,
    )
    result = cmd_scaffold(args)
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert (dest / "pyproject.toml").exists()
    assert (dest / "tests" / "test_app.py").exists()


def test_scaffold_list_json() -> None:
    args = argparse.Namespace(list=True, type=None, path=None, force=False, json=True)
    result = cmd_scaffold(args)
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "fixtures" in result.data
