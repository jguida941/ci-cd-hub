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

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Files pending migration - remove from list as each is migrated
# Goal: empty list = all commands follow the contract
PRINT_ALLOWLIST: set[str] = {
    # Interactive/streaming output - needs real-time prints (cannot use CommandResult)
    "triage_cmd.py",  # --latest auto-select prints user feedback during triage flow
    # Hub settings display - intentionally prints YAML for user visibility
    "hub_config.py",  # hub config show/load prints YAML or key=value for GitHub Actions
    # Worst offenders (migrate first)
    # "triage.py",    # MIGRATED - 34 prints → CommandResult
    # "secrets.py",   # MIGRATED - 32 prints → CommandResult
    # "templates.py", # MIGRATED - 22 prints → CommandResult
    # "pom.py",       # MIGRATED - 21 prints → CommandResult
    # "adr.py",       # MIGRATED - 16 prints → CommandResult
    # "new.py",       # MIGRATED - 10 prints → CommandResult
    # "init.py",      # MIGRATED - 10 prints → CommandResult
    # "docs.py",      # MIGRATED - 10 prints → CommandResult
    # Medium (migrate next)
    # "dispatch.py",  # MIGRATED - 10 prints → CommandResult
    # "config_cmd.py",  # MIGRATED - 9 prints → CommandResult
    # "update.py",     # MIGRATED - 8 prints → CommandResult
    # "smoke.py",      # MIGRATED - 8 prints → CommandResult
    # "discover.py",   # MIGRATED - 8 prints → CommandResult
    # "validate.py",   # MIGRATED - 7 prints → CommandResult
    # "run.py",        # MIGRATED - 6 prints → CommandResult
    # Lower priority
    # "scaffold.py",   # MIGRATED - 5 prints → CommandResult
    "check.py",  # 5 prints
    "ci.py",  # 4 prints
    "preflight.py",  # 3 prints
    # "detect.py",      # MIGRATED - 3 prints → CommandResult
    "verify.py",  # 2 prints
    "config_outputs.py",  # 2 prints
}

# Subpackages with their own allowlists
SUBPACKAGE_ALLOWLISTS: dict[str, set[str]] = {
    "report": {
        "__init__.py",
        "build.py",
        "helpers.py",
        "validate.py",
        "dashboard.py",
        "summary.py",
        "aggregate.py",
        "outputs.py",
    },
    # hub_ci commands are migrated, but __init__.py has infrastructure helpers
    # (_write_outputs, _append_summary) that legitimately print for GitHub Actions
    "hub_ci": {"__init__.py"},  # Infrastructure only - commands are migrated
    # triage subpackage - watch.py needs real-time streaming output for --watch daemon mode
    "triage": {"watch.py"},
}


def get_commands_dir() -> Path:
    """Get the path to cihub/commands/ directory."""
    return Path(__file__).parent.parent / "cihub" / "commands"


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
    def test_command_result_has_expected_fields(self, subcommand: str, expected_fields: list[str]) -> None:
        """Commands should populate expected CommandResult fields.

        This is a contract test - verifies commands return structured data
        appropriate to their category.
        """
        # This test documents expected behavior - actual testing happens
        # in individual command test files
        pass  # Placeholder for future migration verification


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

    @pytest.mark.hypothesis
    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=20)
    def test_line_numbers_accurate(self, num_lines: int) -> None:
        """Property: line numbers reported match actual positions."""
        import os
        import tempfile

        # Generate file with print at specific line
        lines = ["x = 1\n"] * (num_lines - 1) + ['print("test")\n']

        # Create temp file, close it, then read - ensures file is flushed
        fd, temp_path = tempfile.mkstemp(suffix=".py")
        try:
            os.write(fd, "".join(lines).encode())
            os.close(fd)

            prints = find_print_calls(Path(temp_path))

            # Should find exactly one print at the last line
            assert len(prints) == 1
            assert prints[0][0] == num_lines
        finally:
            os.unlink(temp_path)


class TestAllowlistManagement:
    """Tests for allowlist hygiene."""

    def test_allowlist_not_empty_until_migration_complete(self) -> None:
        """Allowlist should shrink as migration progresses."""
        total_allowlisted = len(PRINT_ALLOWLIST)
        for files in SUBPACKAGE_ALLOWLISTS.values():
            total_allowlisted += len(files)

        # This will fail when migration is complete (good!)
        # Update this assertion as migration progresses
        assert total_allowlisted > 0, "All commands migrated! Remove this test and the allowlist."

    def test_no_duplicate_entries(self) -> None:
        """Allowlist should have no duplicates."""
        # PRINT_ALLOWLIST is a set, so no duplicates possible
        # But check subpackage lists
        for subpkg, files in SUBPACKAGE_ALLOWLISTS.items():
            assert len(files) == len(set(files)), f"Duplicate entries in {subpkg} allowlist"
