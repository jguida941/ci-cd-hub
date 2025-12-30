import argparse
from pathlib import Path

from cihub.cli import CommandResult
from cihub.commands.scaffold import scaffold_fixture
from cihub.commands.smoke import cmd_smoke


def test_smoke_on_scaffolded_repo(tmp_path: Path) -> None:
    repo_path = tmp_path / "smoke-repo"
    scaffold_fixture("python-pyproject", repo_path, force=False)

    args = argparse.Namespace(
        repo=str(repo_path),
        subdir=None,
        full=False,
        install_deps=False,
        relax=False,
        force=False,
        keep=False,
        type=None,
        all=False,
        json=True,
    )
    result = cmd_smoke(args)
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert result.data["cases"][0]["success"] is True
