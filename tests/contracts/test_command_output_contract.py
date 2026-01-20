"""Tests enforcing the CommandResult output contract for commands.

This module ensures commands return structured CommandResult instead of
printing directly. The allowlist tracks files pending migration - as files
are migrated, remove them from the allowlist.

Contract Rules:
1. Commands MUST return CommandResult (not bare int, not print)
2. All user-facing output goes through OutputRenderer
3. No direct print() calls in command modules

This follows the "strangler fig" pattern - new code is enforced immediately,
existing code is migrated incrementally.
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import ast
from pathlib import Path

import pytest
import yaml

# Files pending migration - empty list means all commands follow the contract.
PRINT_ALLOWLIST: set[str] = set()

# Subpackages with their own allowlists (empty when fully migrated).
SUBPACKAGE_ALLOWLISTS: dict[str, set[str]] = {}


def get_commands_dir() -> Path:
    """Get the path to cihub/commands/ directory."""
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "cihub" / "commands"


def find_print_calls(filepath: Path) -> list[tuple[int, str]]:
    """Find all print() calls in a Python file using AST.

    Returns list of (line_number, code_snippet) tuples.
    """
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    prints = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for print() call
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                # Get the line from source
                lines = source.splitlines()
                if node.lineno <= len(lines):
                    line_content = lines[node.lineno - 1].strip()
                    prints.append((node.lineno, line_content))

    return prints


def get_all_command_files() -> list[Path]:
    """Get all Python files in cihub/commands/ (excluding __pycache__)."""
    commands_dir = get_commands_dir()
    files = []

    for path in commands_dir.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        files.append(path)

    return sorted(files)


class TestCommandOutputContract:
    """Tests enforcing the CommandResult output contract."""

    def test_no_print_in_migrated_commands(self) -> None:
        """Commands not in allowlist must not have print() calls.

        This test prevents regression - once a command is migrated,
        it cannot go back to using print().
        """
        commands_dir = get_commands_dir()
        violations = []

        for filepath in get_all_command_files():
            relative = filepath.relative_to(commands_dir)
            parts = relative.parts

            # Check if file is in allowlist
            if len(parts) == 1:
                # Top-level file (e.g., adr.py)
                if parts[0] in PRINT_ALLOWLIST:
                    continue
            elif len(parts) == 2:
                # Subpackage file (e.g., report/build.py)
                subpkg = parts[0]
                filename = parts[1]
                if subpkg in SUBPACKAGE_ALLOWLISTS:
                    if filename in SUBPACKAGE_ALLOWLISTS[subpkg]:
                        continue

            # File is NOT in allowlist - check for prints
            prints = find_print_calls(filepath)
            if prints:
                for line_no, code in prints:
                    violations.append(f"{relative}:{line_no}: {code}")

        if violations:
            msg = (
                f"Found {len(violations)} print() calls in migrated commands.\n"
                "Commands must return CommandResult, not print directly.\n\n"
                "Violations:\n" + "\n".join(f"  {v}" for v in violations[:20])
            )
            if len(violations) > 20:
                msg += f"\n  ... and {len(violations) - 20} more"
            pytest.fail(msg)

    def test_hub_ci_commands_migrated(self) -> None:
        """hub_ci/ command files should have no print() calls.

        Note: __init__.py is excluded because it contains infrastructure
        helpers (_write_outputs, _append_summary) that legitimately print
        for GitHub Actions output mechanism.
        """
        hub_ci_dir = get_commands_dir() / "hub_ci"
        if not hub_ci_dir.exists():
            pytest.skip("hub_ci directory not found")

        # Files with legitimate infrastructure prints
        infrastructure_files = {"__init__.py"}

        violations = []
        for filepath in hub_ci_dir.rglob("*.py"):
            if "__pycache__" in str(filepath):
                continue
            if filepath.name in infrastructure_files:
                continue  # Skip infrastructure files

            prints = find_print_calls(filepath)
            if prints:
                for line_no, code in prints:
                    violations.append(f"{filepath.relative_to(hub_ci_dir)}:{line_no}: {code}")

        if violations:
            pytest.fail(
                f"hub_ci/ commands should be migrated but found {len(violations)} "
                f"print() calls:\n" + "\n".join(f"  {v}" for v in violations)
            )

    def test_allowlist_files_exist(self) -> None:
        """All files in allowlist must exist (catch stale entries)."""
        commands_dir = get_commands_dir()
        missing = []

        for filename in PRINT_ALLOWLIST:
            if not (commands_dir / filename).exists():
                missing.append(filename)

        for subpkg, files in SUBPACKAGE_ALLOWLISTS.items():
            for filename in files:
                if not (commands_dir / subpkg / filename).exists():
                    missing.append(f"{subpkg}/{filename}")

        if missing:
            pytest.fail("Allowlist contains non-existent files (remove them):\n" + "\n".join(f"  {f}" for f in missing))

    def test_track_migration_progress(self) -> None:
        """Report current migration progress (informational)."""
        total_prints = 0
        migrated_prints = 0

        for filepath in get_all_command_files():
            prints = find_print_calls(filepath)
            count = len(prints)
            total_prints += count

            relative = filepath.relative_to(get_commands_dir())
            parts = relative.parts

            # Check if migrated (not in allowlist)
            is_allowlisted = False
            if len(parts) == 1 and parts[0] in PRINT_ALLOWLIST:
                is_allowlisted = True
            elif len(parts) == 2:
                subpkg, filename = parts
                if subpkg in SUBPACKAGE_ALLOWLISTS:
                    if filename in SUBPACKAGE_ALLOWLISTS[subpkg]:
                        is_allowlisted = True

            if not is_allowlisted:
                migrated_prints += count

        # This test always passes - it's for visibility
        print(f"\n[Migration Progress] {total_prints} total print() calls")
        print(f"  Allowlisted (pending): {total_prints - migrated_prints}")
        print(f"  In migrated files: {migrated_prints}")
        if migrated_prints > 0:
            print(f"  WARNING: {migrated_prints} prints in 'migrated' files!")


class TestCommandResultContract:
    """Tests verifying CommandResult usage patterns."""

    @pytest.mark.parametrize(
        "subcommand,expected_fields",
        [
            ("adr", ["summary", "data"]),
            ("check", ["summary", "problems"]),
            ("validate", ["summary", "problems"]),
            ("smoke", ["summary", "data"]),
            ("docs", ["summary", "data"]),
        ],
        ids=["adr", "check", "validate", "smoke", "docs"],
    )
    def test_command_result_has_expected_fields(
        self,
        subcommand: str,
        expected_fields: list[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Commands should populate expected CommandResult fields.

        This is a contract test - verifies commands return structured data
        appropriate to their category.
        """
        from cihub.types import CommandResult

        def assert_fields(result: CommandResult, fields: list[str]) -> None:
            for field in fields:
                assert hasattr(result, field), f"Missing CommandResult field: {field}"
                value = getattr(result, field)
                if field == "summary":
                    assert isinstance(value, str) and value.strip(), "summary should be a non-empty string"
                elif field == "data":
                    assert isinstance(value, dict), "data should be a dict"
                elif field == "problems":
                    assert isinstance(value, list), "problems should be a list"

        if subcommand == "adr":
            from cihub.commands import adr as adr_cmd

            adr_dir = Path(tmp_path) / "docs" / "adr"
            adr_dir.mkdir(parents=True)
            (adr_dir / "0001-test.md").write_text(
                "# ADR-0001: Test\n\n**Status:** Accepted\n**Date:** 2024-01-01\n",
                encoding="utf-8",
            )
            monkeypatch.setattr(adr_cmd, "project_root", lambda: Path(tmp_path))
            args = argparse.Namespace(subcommand="list", status=None, json=True)
            result = adr_cmd.cmd_adr(args)
            assert_fields(result, expected_fields)
            assert isinstance(result.data.get("adrs"), list)
            return

        if subcommand == "check":
            from cihub.commands import check as check_cmd

            def _ok_result(*_args, **_kwargs):  # type: ignore[no-untyped-def]
                return CommandResult(exit_code=0, summary="ok")

            monkeypatch.setattr(check_cmd, "_run_process", _ok_result)
            monkeypatch.setattr(check_cmd, "_run_optional", _ok_result)
            monkeypatch.setattr(check_cmd, "cmd_preflight", _ok_result)
            monkeypatch.setattr(check_cmd, "cmd_docs", _ok_result)
            monkeypatch.setattr(check_cmd, "cmd_docs_links", _ok_result)
            monkeypatch.setattr(check_cmd, "cmd_docs_audit", _ok_result)
            monkeypatch.setattr(check_cmd, "cmd_adr", _ok_result)
            monkeypatch.setattr(check_cmd, "check_schema_alignment", _ok_result)
            monkeypatch.setattr(check_cmd, "cmd_smoke", _ok_result)

            args = argparse.Namespace(json=True)
            result = check_cmd.cmd_check(args)
            assert_fields(result, expected_fields)
            return

        if subcommand == "validate":
            from cihub.commands.validate import cmd_validate

            config = {
                "version": "1.0",
                "language": "python",
                "repo": {"owner": "acme", "name": "demo"},
                "python": {},
            }
            config_path = Path(tmp_path) / ".ci-hub.yml"
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            args = argparse.Namespace(repo=str(tmp_path), json=True, strict=False)
            result = cmd_validate(args)
            assert_fields(result, expected_fields)
            return

        if subcommand == "smoke":
            from cihub.commands import smoke as smoke_cmd

            def _fake_run_case(case, *_args, **_kwargs):  # type: ignore[no-untyped-def]
                step = smoke_cmd.SmokeStep(name="detect", exit_code=0, summary="ok", problems=[])
                return [step], "python"

            monkeypatch.setattr(smoke_cmd, "_run_case", _fake_run_case)

            args = argparse.Namespace(
                repo=str(tmp_path),
                subdir="",
                all=False,
                type=None,
                keep=False,
                full=False,
                install_deps=False,
                relax=False,
                force=False,
            )
            result = smoke_cmd.cmd_smoke(args)
            assert_fields(result, expected_fields)
            assert isinstance(result.data.get("cases"), list)
            return

        if subcommand == "docs":
            from cihub.commands.docs import cmd_docs

            output_dir = Path(tmp_path) / "docs"
            args = argparse.Namespace(subcommand="generate", output=str(output_dir), check=False)
            result = cmd_docs(args)
            assert_fields(result, expected_fields)
            assert isinstance(result.data.get("items"), list)
            return

        raise AssertionError(f"Unknown subcommand for contract test: {subcommand}")


class TestPrintPatternDetection:
    """Tests for the print detection utility itself."""

    def test_detects_simple_print(self, tmp_path: Path) -> None:
        """Detects basic print() calls."""
        test_file = tmp_path / "test.py"
        test_file.write_text('print("hello")\n')

        prints = find_print_calls(test_file)
        assert len(prints) == 1
        assert prints[0][0] == 1
        assert "print" in prints[0][1]

    def test_detects_print_with_fstring(self, tmp_path: Path) -> None:
        """Detects print() with f-strings."""
        test_file = tmp_path / "test.py"
        test_file.write_text('x = 1\nprint(f"value: {x}")\n')

        prints = find_print_calls(test_file)
        assert len(prints) == 1
        assert prints[0][0] == 2

    def test_ignores_print_in_string(self, tmp_path: Path) -> None:
        """Does not flag 'print' in strings."""
        test_file = tmp_path / "test.py"
        test_file.write_text('msg = "do not print this"\n')

        prints = find_print_calls(test_file)
        assert len(prints) == 0

    def test_ignores_print_method(self, tmp_path: Path) -> None:
        """Does not flag obj.print() method calls."""
        test_file = tmp_path / "test.py"
        test_file.write_text('printer.print("hello")\n')

        prints = find_print_calls(test_file)
        assert len(prints) == 0

    def test_detects_multiple_prints(self, tmp_path: Path) -> None:
        """Detects all print() calls in a file."""
        test_file = tmp_path / "test.py"
        test_file.write_text('print("one")\nx = 1\nprint("two")\nprint("three")\n')

        prints = find_print_calls(test_file)
        assert len(prints) == 3
        assert [p[0] for p in prints] == [1, 3, 4]

    def test_line_numbers_accurate_parametrized(self, tmp_path: Path) -> None:
        """Property: line numbers reported match actual positions.

        Note: This was converted from a hypothesis test to parametrized test
        because hypothesis has known issues running in mutmut's subprocess
        environment (database path issues, subprocess isolation).
        """
        # Test a range of line counts to cover the same cases hypothesis would
        for num_lines in [1, 5, 10, 25, 50]:
            # Generate file with print at specific line
            lines = ["x = 1\n"] * (num_lines - 1) + ['print("test")\n']

            test_file = tmp_path / f"test_{num_lines}.py"
            test_file.write_text("".join(lines))

            prints = find_print_calls(test_file)

            # Should find exactly one print at the last line
            assert len(prints) == 1, f"Expected 1 print at line {num_lines}, got {len(prints)}"
            assert prints[0][0] == num_lines, f"Expected line {num_lines}, got {prints[0][0]}"


class TestAllowlistManagement:
    """Tests for allowlist hygiene."""

    def test_allowlist_empty_after_migration_complete(self) -> None:
        """Allowlist should be empty once migration is complete."""
        total_allowlisted = len(PRINT_ALLOWLIST)
        for files in SUBPACKAGE_ALLOWLISTS.values():
            total_allowlisted += len(files)

        assert total_allowlisted == 0, "Allowlist should be empty after migration."

    def test_no_duplicate_entries(self) -> None:
        """Allowlist should have no duplicates."""
        # PRINT_ALLOWLIST is a set, so no duplicates possible
        # But check subpackage lists
        for subpkg, files in SUBPACKAGE_ALLOWLISTS.items():
            assert len(files) == len(set(files)), f"Duplicate entries in {subpkg} allowlist"
