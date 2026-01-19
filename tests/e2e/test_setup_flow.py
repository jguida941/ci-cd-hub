"""Tests for setup command flow (R-002 wizard config persistence)."""

# TEST-METRICS:

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

from cihub.commands.setup import cmd_setup
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult


class _Prompt:
    def __init__(self, value):
        self._value = value

    def ask(self):
        return self._value


def _questionary_stub(confirm_value: bool = True) -> SimpleNamespace:
    def confirm(*_args, **_kwargs):
        return _Prompt(confirm_value)

    def select(*_args, **_kwargs):
        return _Prompt("existing")

    def text(*_args, **_kwargs):
        return _Prompt("test")

    return SimpleNamespace(confirm=confirm, select=select, text=text)


class TestSetupWizardConfigPersistence:
    """Tests that setup command persists wizard config to Step 5."""

    def test_setup_passes_wizard_config_to_step5(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        wizard_config = {
            "language": "python",
            "repo": {"owner": "wizard-owner", "name": "wizard-repo"},
        }
        init_calls: list[argparse.Namespace] = []

        def mock_cmd_init(args: argparse.Namespace) -> CommandResult:
            init_calls.append(args)
            if args.wizard and args.dry_run:
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary="Wizard complete",
                    data={"config": wizard_config},
                )
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Init complete",
                data={"language": "python"},
                files_generated=[str(tmp_path / ".ci-hub.yml")],
            )

        def mock_cmd_detect(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Detected", data={"language": "python"})

        def mock_cmd_validate(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Valid")

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="CI OK")

        monkeypatch.setattr("cihub.commands.setup.HAS_WIZARD", True)
        monkeypatch.setattr("cihub.commands.init.cmd_init", mock_cmd_init)
        monkeypatch.setattr("cihub.commands.detect.cmd_detect", mock_cmd_detect)
        monkeypatch.setattr("cihub.commands.validate.cmd_validate", mock_cmd_validate)
        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setitem(sys.modules, "questionary", _questionary_stub())

        args = argparse.Namespace(
            repo=str(tmp_path),
            new=False,
            skip_github=True,
            json=False,
            hub_mode=False,
            tier=None,
        )

        result = cmd_setup(args)

        assert result.exit_code == EXIT_SUCCESS
        assert len(init_calls) >= 2
        assert init_calls[1].config_override == wizard_config

    def test_setup_fails_if_wizard_config_missing(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        def mock_cmd_init(args: argparse.Namespace) -> CommandResult:
            if args.wizard:
                return CommandResult(exit_code=EXIT_SUCCESS, summary="Wizard complete", data={"language": "python"})
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Init complete", data={"language": "python"})

        def mock_cmd_detect(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Detected", data={"language": "python"})

        monkeypatch.setattr("cihub.commands.setup.HAS_WIZARD", True)
        monkeypatch.setattr("cihub.commands.init.cmd_init", mock_cmd_init)
        monkeypatch.setattr("cihub.commands.detect.cmd_detect", mock_cmd_detect)
        monkeypatch.setitem(sys.modules, "questionary", _questionary_stub())

        args = argparse.Namespace(
            repo=str(tmp_path),
            new=False,
            skip_github=True,
            json=False,
            hub_mode=False,
            tier=None,
        )

        result = cmd_setup(args)

        assert result.exit_code == EXIT_FAILURE
        assert any(problem.get("code") == "CIHUB-SETUP-002" for problem in (result.problems or []))


class TestSetupScaffoldPath:
    """Tests for setup --new scaffold path (R-001 arg wiring)."""

    def test_setup_new_calls_scaffold_with_correct_args(self, tmp_path: Path, monkeypatch) -> None:
        """Test that --new flag correctly wires scaffold args (R-001 fix).

        Regression test for setup.py:196 - verifies that:
        - scaffold receives correct arg names (path not dest)
        - All required flags are passed (list, github, wizard, force, json)
        """
        scaffold_calls: list[argparse.Namespace] = []

        def mock_cmd_scaffold(args: argparse.Namespace) -> CommandResult:
            scaffold_calls.append(args)
            # Create the scaffolded project structure
            project_path = Path(args.path)
            project_path.mkdir(parents=True, exist_ok=True)
            (project_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Scaffold complete",
                files_generated=[str(project_path / "pyproject.toml")],
            )

        def mock_cmd_detect(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Detected", data={"language": "python"})

        def mock_cmd_init(args: argparse.Namespace) -> CommandResult:
            if args.wizard and args.dry_run:
                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary="Wizard complete",
                    data={"config": {"language": "python"}},
                )
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Init complete",
                data={"language": "python"},
                files_generated=[str(tmp_path / ".ci-hub.yml")],
            )

        def mock_cmd_validate(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Valid")

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="CI OK")

        # Create questionary stub that returns different values for different select calls
        # First select: "new" (project type choice)
        # Second select: "python-pyproject" (scaffold type choice)
        select_call_counter = [0]  # Use list to allow mutation in closure

        def _questionary_stub_for_new() -> SimpleNamespace:
            def confirm(*_args, **_kwargs):
                return _Prompt(True)

            def select(*_args, **_kwargs):
                call_num = select_call_counter[0]
                select_call_counter[0] += 1
                if call_num == 0:
                    return _Prompt("new")  # First call: project type choice
                return _Prompt("python-pyproject")  # Second call: scaffold type

            def text(*_args, **_kwargs):
                return _Prompt("test")

            return SimpleNamespace(confirm=confirm, select=select, text=text)

        monkeypatch.setattr("cihub.commands.setup.HAS_WIZARD", True)
        monkeypatch.setattr("cihub.commands.scaffold.cmd_scaffold", mock_cmd_scaffold)
        monkeypatch.setattr("cihub.commands.detect.cmd_detect", mock_cmd_detect)
        monkeypatch.setattr("cihub.commands.init.cmd_init", mock_cmd_init)
        monkeypatch.setattr("cihub.commands.validate.cmd_validate", mock_cmd_validate)
        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setitem(sys.modules, "questionary", _questionary_stub_for_new())

        args = argparse.Namespace(
            repo=str(tmp_path),
            new=True,  # This triggers the scaffold path
            skip_github=True,
            json=False,
            hub_mode=False,
            tier=None,
        )

        result = cmd_setup(args)
        assert result.exit_code == EXIT_SUCCESS

        # Verify scaffold was called
        assert len(scaffold_calls) == 1, "Scaffold should be called once for --new"

        # Verify correct argument wiring (R-001 fix)
        scaffold_args = scaffold_calls[0]

        # R-001: path (not dest) should be set
        assert hasattr(scaffold_args, "path"), "scaffold should receive 'path' arg (not 'dest')"
        assert scaffold_args.path is not None, "scaffold path should be set"

        # R-001: type should be set from wizard selection
        assert hasattr(scaffold_args, "type"), "scaffold should receive 'type' arg"
        assert scaffold_args.type == "python-pyproject", "scaffold type should match wizard selection"

        # R-001: All required flags must be present
        assert hasattr(scaffold_args, "list"), "scaffold should receive 'list' flag"
        assert scaffold_args.list is False, "list should be False"

        assert hasattr(scaffold_args, "github"), "scaffold should receive 'github' flag"
        assert scaffold_args.github is False, "github should be False"

        assert hasattr(scaffold_args, "wizard"), "scaffold should receive 'wizard' flag"
        assert scaffold_args.wizard is False, "wizard should be False"

        assert hasattr(scaffold_args, "force"), "scaffold should receive 'force' flag"
        assert scaffold_args.force is False, "force should be False"

        assert hasattr(scaffold_args, "json"), "scaffold should receive 'json' flag"
        assert scaffold_args.json is False, "json should be False"

    def test_setup_new_propagates_scaffold_failure(self, tmp_path: Path, monkeypatch) -> None:
        """Test that scaffold failures are properly propagated to setup result."""

        def mock_cmd_scaffold(args: argparse.Namespace) -> CommandResult:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Scaffold failed: Invalid type",
                problems=[{"severity": "error", "message": "Invalid project type"}],
            )

        # Create questionary stub that returns "new" then "invalid-type"
        select_call_counter = [0]

        def _questionary_stub_for_fail() -> SimpleNamespace:
            def confirm(*_args, **_kwargs):
                return _Prompt(True)

            def select(*_args, **_kwargs):
                call_num = select_call_counter[0]
                select_call_counter[0] += 1
                if call_num == 0:
                    return _Prompt("new")  # First call: project type choice
                return _Prompt("invalid-type")  # Second call: scaffold type

            def text(*_args, **_kwargs):
                return _Prompt("test")

            return SimpleNamespace(confirm=confirm, select=select, text=text)

        monkeypatch.setattr("cihub.commands.setup.HAS_WIZARD", True)
        monkeypatch.setattr("cihub.commands.scaffold.cmd_scaffold", mock_cmd_scaffold)
        monkeypatch.setitem(sys.modules, "questionary", _questionary_stub_for_fail())

        args = argparse.Namespace(
            repo=str(tmp_path),
            new=True,
            skip_github=True,
            json=False,
            hub_mode=False,
            tier=None,
        )

        result = cmd_setup(args)

        assert result.exit_code == EXIT_FAILURE
        assert "Scaffold failed" in result.summary
