"""Phase 0: Module structure and import safety tests.

These tests establish baseline guarantees before modularization:
1. CLI help output remains stable (snapshot test)
2. All mock.patch targets are resolvable
3. Key modules import without circular dependencies
4. hub_ci command count is locked at 47
5. CLI facade exports remain accessible

See docs/modularization.md for the full plan.
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).parent.parent
TESTS_DIR = REPO_ROOT / "tests"
MUTANTS_TESTS_DIR = REPO_ROOT / "mutants" / "tests"
SNAPSHOTS_DIR = TESTS_DIR / "snapshots"


class TestCliHelpSnapshot:
    """Verify CLI --help output doesn't change unexpectedly."""

    def test_cli_help_unchanged(self) -> None:
        """CLI help output must match snapshot."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "--help"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, f"CLI help failed: {result.stderr}"

        snapshot_path = SNAPSHOTS_DIR / "cli_help.txt"
        assert snapshot_path.exists(), (
            f"Snapshot file missing: {snapshot_path}\n"
            "Create it with: python -m cihub --help > tests/snapshots/cli_help.txt"
        )

        expected = snapshot_path.read_text(encoding="utf-8").strip()
        actual = result.stdout.strip()

        assert actual == expected, (
            "CLI --help output changed! "
            "If intentional, update tests/snapshots/cli_help.txt"
        )


class TestImportSmoke:
    """Verify key modules import without circular dependency errors."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "cihub",
            "cihub.cli",
            "cihub.commands.hub_ci",
            "cihub.commands.report",
            "cihub.services.ci_engine",
            "cihub.config.loader",
        ],
    )
    def test_module_imports(self, module_path: str) -> None:
        """Module imports without errors."""
        try:
            importlib.import_module(module_path)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_path}: {e}")


class TestHubCiCommandCount:
    """Lock hub_ci command count to prevent silent command loss."""

    EXPECTED_COMMAND_COUNT = 47

    def test_command_count_locked(self) -> None:
        """Exactly 47 cmd_* functions must exist in hub_ci."""
        from cihub.commands import hub_ci

        cmd_funcs = [name for name in dir(hub_ci) if name.startswith("cmd_")]
        actual_count = len(cmd_funcs)

        assert actual_count == self.EXPECTED_COMMAND_COUNT, (
            f"hub_ci command count changed! Expected {self.EXPECTED_COMMAND_COUNT}, "
            f"found {actual_count}. Commands: {sorted(cmd_funcs)}"
        )


class TestCliFacadeExports:
    """Verify CLI facade exports remain accessible.

    These are the public API items that must remain importable from cihub.cli
    even after utilities are moved to cihub/utils/.
    """

    # All items that are imported from cihub.cli by other modules
    # Must remain accessible after modularization
    CLI_FACADE_EXPORTS = [
        # Core types and entry points
        "CommandResult",
        "build_parser",
        "main",
        # Path and validation utilities
        "hub_root",
        "validate_repo_path",
        "validate_subdir",
        # Executable resolution
        "resolve_executable",
        # Git utilities
        "GIT_REMOTE_RE",
        "get_git_branch",
        "get_git_remote",
        "parse_repo_from_remote",
        # GitHub API utilities
        "delete_remote_file",
        "fetch_remote_file",
        "gh_api_json",
        "update_remote_file",
        # Repo configuration
        "build_repo_config",
        "get_connected_repos",
        "get_repo_entries",
        "resolve_language",
        # Workflow rendering
        "render_dispatch_workflow",
        # HTTP utilities
        "safe_urlopen",
    ]

    def test_cli_facade_exports_accessible(self) -> None:
        """All CLI facade items must be importable from cihub.cli."""
        from cihub import cli

        missing = []
        for name in self.CLI_FACADE_EXPORTS:
            if not hasattr(cli, name):
                missing.append(name)

        assert not missing, f"Missing CLI facade exports: {missing}"


class TestMockPatchTargets:
    """Verify all mock.patch string targets are resolvable.

    When modules move, mock.patch("old.path.func") silently mocks the wrong
    location. This test catches broken patches before they cause false passes.
    """

    @staticmethod
    def _extract_mock_patch_targets(file_path: Path) -> Iterator[tuple[int, str]]:
        """Extract mock.patch string arguments from a Python file."""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            is_patch = False

            # Check for mock.patch, unittest.mock.patch, patch
            if isinstance(func, ast.Attribute) and func.attr == "patch":
                is_patch = True
            elif isinstance(func, ast.Name) and func.id == "patch":
                is_patch = True

            if is_patch and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(
                    first_arg.value, str
                ):
                    target = first_arg.value
                    # Only check cihub targets
                    if target.startswith("cihub."):
                        yield (getattr(node, "lineno", 0), target)

    @staticmethod
    def _resolve_target(target: str) -> bool:
        """Check if a mock.patch target is resolvable.

        Handles chained attributes like 'cihub.module.imported_obj.method'.
        """
        parts = target.split(".")
        if len(parts) < 2:
            return False

        # Try progressively longer module paths
        for i in range(len(parts) - 1, 0, -1):
            module_path = ".".join(parts[:i])
            attr_chain = parts[i:]

            try:
                obj = importlib.import_module(module_path)
                # Walk the attribute chain
                for attr in attr_chain:
                    obj = getattr(obj, attr)
                return True
            except (ImportError, AttributeError):
                continue

        return False

    def test_mock_patches_in_tests(self) -> None:
        """All mock.patch targets in tests/ must be resolvable."""
        unresolvable = []

        for test_file in TESTS_DIR.rglob("test_*.py"):
            for line_no, target in self._extract_mock_patch_targets(test_file):
                if not self._resolve_target(target):
                    rel_path = test_file.relative_to(REPO_ROOT)
                    unresolvable.append(f"{rel_path}:{line_no} -> {target}")

        if unresolvable:
            pytest.fail(
                f"Unresolvable mock.patch targets in tests/:\n"
                + "\n".join(unresolvable[:20])
                + (f"\n... and {len(unresolvable) - 20} more" if len(unresolvable) > 20 else "")
            )

    def test_mock_patches_in_mutants(self) -> None:
        """All mock.patch targets in mutants/tests/ must be resolvable."""
        if not MUTANTS_TESTS_DIR.exists():
            pytest.skip("mutants/tests/ not found")

        unresolvable = []

        for test_file in MUTANTS_TESTS_DIR.rglob("test_*.py"):
            for line_no, target in self._extract_mock_patch_targets(test_file):
                if not self._resolve_target(target):
                    rel_path = test_file.relative_to(REPO_ROOT)
                    unresolvable.append(f"{rel_path}:{line_no} -> {target}")

        if unresolvable:
            pytest.fail(
                f"Unresolvable mock.patch targets in mutants/tests/:\n"
                + "\n".join(unresolvable[:20])
                + (f"\n... and {len(unresolvable) - 20} more" if len(unresolvable) > 20 else "")
            )


class TestPrivateHelperAccessibility:
    """Verify test-imported private helpers remain accessible.

    Tests import private functions (prefixed with _) from modules.
    These must remain accessible via facades after modularization.
    """

    def test_hub_ci_private_helpers(self) -> None:
        """Private helpers in hub_ci used by tests must be accessible."""
        from cihub.commands import hub_ci

        # Helpers known to be imported by tests
        required_helpers = [
            "_write_outputs",
            "_append_summary",
            "_parse_env_bool",
            "_bar",
            "EMPTY_SARIF",
        ]

        missing = [h for h in required_helpers if not hasattr(hub_ci, h)]
        assert not missing, f"Missing hub_ci helpers: {missing}"

    def test_report_private_helpers(self) -> None:
        """Private helpers in report used by tests must be accessible."""
        from cihub.commands import report

        # Helpers known to be imported by tests
        required_helpers = [
            "_append_summary",
            "_parse_env_bool",
            "_bar",
        ]

        missing = [h for h in required_helpers if not hasattr(report, h)]
        assert not missing, f"Missing report helpers: {missing}"


class TestAggregationPartialData:
    """Verify aggregation works with partial/missing data.

    Aggregate reports must render successfully even when some repos have
    failed or missing data. This is critical for dashboard reliability.
    """

    def test_aggregation_with_partial_reports(self, tmp_path: Path) -> None:
        """Aggregation succeeds when some reports are missing or invalid."""
        import json

        from cihub.aggregation import run_reports_aggregation
        from cihub.utils.paths import hub_root

        # Create reports directory
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        # Create a valid report
        valid_report = {
            "repo": "owner/valid-repo",
            "language": "python",
            "tools": {"pytest": {"passed": True}},
            "badges": {},
        }
        (reports_dir / "valid-repo.json").write_text(
            json.dumps(valid_report), encoding="utf-8"
        )

        # Create an invalid/empty report
        (reports_dir / "invalid-repo.json").write_text("{}", encoding="utf-8")

        # Create a malformed JSON file
        (reports_dir / "malformed.json").write_text("not json", encoding="utf-8")

        # Get defaults file from hub root
        defaults_file = hub_root() / "config" / "defaults.yaml"

        # Run aggregation - should not raise, should return result
        result = run_reports_aggregation(
            reports_dir=reports_dir,
            output_file=tmp_path / "aggregate.json",
            summary_file=tmp_path / "summary.md",
            defaults_file=defaults_file,
            hub_run_id="test-123",
            hub_event="workflow_dispatch",
            total_repos=3,
            strict=False,  # Allow partial data
        )

        # Aggregation should succeed despite partial data
        assert result is not None
        assert (tmp_path / "aggregate.json").exists()

        # Output should contain the valid repo data
        output_data = json.loads((tmp_path / "aggregate.json").read_text())
        assert "repos" in output_data or "reports" in output_data or "timestamp" in output_data
