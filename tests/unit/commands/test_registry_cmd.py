"""Tests for registry command dispatcher and subcommands.

Tests cover:
- cmd_registry dispatcher (routing to subcommands)
- _cmd_list: List repos with tier filtering
- _cmd_show: Show detailed repo config
- _cmd_set: Set tier/overrides
- _cmd_add: Add new repo (non-wizard path)
- _cmd_remove: Remove repo
- _cmd_diff: Show drift from registry
- _cmd_sync: Sync registry to configs
- _cmd_bootstrap: Import configs to registry
- _cmd_export: Export registry to JSON
- _cmd_import: Import registry from JSON
- _derive_hub_root_from_configs_dir: Hub root detection

These tests focus on command-layer behavior (argument handling, exit codes,
CommandResult structure) rather than registry service logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from cihub.commands.registry import (
    _derive_hub_root_from_configs_dir,
    cmd_registry,
)
from cihub.commands.registry.io import _cmd_export, _cmd_import
from cihub.commands.registry.modify import _cmd_add, _cmd_remove, _cmd_set
from cihub.commands.registry.query import _cmd_list, _cmd_show
from cihub.commands.registry.sync import _cmd_bootstrap, _cmd_diff, _cmd_sync
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_registry() -> dict:
    """Sample registry structure for testing."""
    return {
        "schema_version": "cihub-registry-v1",
        "tiers": {
            "standard": {
                "description": "Standard tier",
                "profile": "standard",
            },
            "critical": {
                "description": "Critical tier",
                "profile": "critical",
            },
        },
        "repos": {
            "test-repo": {
                "tier": "standard",
                "description": "Test repository",
            },
            "important-repo": {
                "tier": "critical",
            },
        },
    }


@pytest.fixture
def hub_structure(tmp_path: Path) -> Path:
    """Create a hub-like directory structure."""
    # Create required directories
    (tmp_path / "config" / "repos").mkdir(parents=True)
    (tmp_path / "templates" / "profiles").mkdir(parents=True)

    # Create defaults.yaml (required for hub root detection)
    (tmp_path / "config" / "defaults.yaml").write_text(
        yaml.safe_dump({"thresholds": {"coverage_min": 70}}),
        encoding="utf-8",
    )

    # Create standard profile
    (tmp_path / "templates" / "profiles" / "standard.yaml").write_text(
        yaml.safe_dump(
            {
                "thresholds": {
                    "coverage_min": 70,
                    "mutation_score_min": 70,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                }
            }
        ),
        encoding="utf-8",
    )

    # Create registry.json
    (tmp_path / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": "standard"}},
                "repos": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return tmp_path


# =============================================================================
# cmd_registry Dispatcher Tests
# =============================================================================


class TestCmdRegistryDispatcher:
    """Tests for the main cmd_registry dispatcher."""

    def test_unknown_subcommand_returns_usage_error(self) -> None:
        """Unknown subcommand returns EXIT_USAGE."""
        args = argparse.Namespace(subcommand="invalid")

        result = cmd_registry(args)

        assert result.exit_code == EXIT_USAGE
        assert "Unknown" in result.summary
        assert len(result.problems) == 1
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-UNKNOWN-SUBCOMMAND"

    def test_none_subcommand_returns_usage_error(self) -> None:
        """None subcommand returns EXIT_USAGE."""
        args = argparse.Namespace(subcommand=None)

        result = cmd_registry(args)

        assert result.exit_code == EXIT_USAGE

    def test_missing_subcommand_attribute(self) -> None:
        """Missing subcommand attribute returns EXIT_USAGE."""
        args = argparse.Namespace()  # No subcommand attribute

        result = cmd_registry(args)

        assert result.exit_code == EXIT_USAGE

    @patch("cihub.commands.registry.query.load_registry")
    @patch("cihub.commands.registry.query.list_repos")
    def test_routes_to_list_handler(
        self, mock_list_repos: MagicMock, mock_load: MagicMock
    ) -> None:
        """Routes 'list' subcommand to _cmd_list handler."""
        mock_load.return_value = {}
        mock_list_repos.return_value = []
        args = argparse.Namespace(subcommand="list", tier=None)

        result = cmd_registry(args)

        # Verify it routed to _cmd_list by checking the expected behavior
        assert result.exit_code == EXIT_SUCCESS
        mock_list_repos.assert_called_once()

    @patch("cihub.commands.registry.query.load_registry")
    @patch("cihub.commands.registry.query.get_repo_config")
    def test_routes_to_show_handler(
        self, mock_get: MagicMock, mock_load: MagicMock
    ) -> None:
        """Routes 'show' subcommand to _cmd_show handler."""
        mock_load.return_value = {}
        mock_get.return_value = None
        args = argparse.Namespace(subcommand="show", repo="test")

        result = cmd_registry(args)

        # Verify it routed to _cmd_show by checking the expected behavior
        mock_get.assert_called_once()


# =============================================================================
# _derive_hub_root_from_configs_dir Tests
# =============================================================================


class TestDeriveHubRoot:
    """Tests for _derive_hub_root_from_configs_dir function."""

    def test_derives_from_repos_dir(self, tmp_path: Path) -> None:
        """Derives hub root from config/repos path."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        result = _derive_hub_root_from_configs_dir(repos_dir)

        assert result == tmp_path

    def test_derives_from_config_dir(self, tmp_path: Path) -> None:
        """Derives hub root from config path."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)

        result = _derive_hub_root_from_configs_dir(config_dir)

        assert result == tmp_path

    def test_walks_up_to_find_hub_root(self, hub_structure: Path) -> None:
        """Walks up parent directories to find hub root."""
        nested_dir = hub_structure / "config" / "repos" / "nested"
        nested_dir.mkdir(parents=True)

        result = _derive_hub_root_from_configs_dir(nested_dir)

        assert result == hub_structure

    def test_returns_none_for_unrecognized_path(self, tmp_path: Path) -> None:
        """Returns None for unrecognized directory structure."""
        random_dir = tmp_path / "random" / "path"
        random_dir.mkdir(parents=True)

        result = _derive_hub_root_from_configs_dir(random_dir)

        assert result is None


# =============================================================================
# _cmd_list Tests
# =============================================================================


class TestCmdList:
    """Tests for _cmd_list function."""

    @patch("cihub.commands.registry.query.load_registry")
    @patch("cihub.commands.registry.query.list_repos")
    def test_lists_all_repos(self, mock_list_repos: MagicMock, mock_load: MagicMock) -> None:
        """Lists all repos when no tier filter."""
        mock_load.return_value = {}
        mock_list_repos.return_value = [
            {
                "name": "repo1",
                "tier": "standard",
                "has_threshold_overrides": False,
                "effective": {
                    "coverage_min": 70,
                    "mutation_score_min": 70,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                },
            }
        ]
        args = argparse.Namespace(tier=None)

        result = _cmd_list(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] == 1

    @patch("cihub.commands.registry.query.load_registry")
    @patch("cihub.commands.registry.query.list_repos")
    def test_filters_by_tier(self, mock_list_repos: MagicMock, mock_load: MagicMock) -> None:
        """Filters repos by tier when specified."""
        mock_load.return_value = {}
        mock_list_repos.return_value = [
            {
                "name": "repo1",
                "tier": "standard",
                "has_threshold_overrides": False,
                "effective": {
                    "coverage_min": 70,
                    "mutation_score_min": 70,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                },
            },
            {
                "name": "repo2",
                "tier": "critical",
                "has_threshold_overrides": False,
                "effective": {
                    "coverage_min": 90,
                    "mutation_score_min": 90,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                },
            },
        ]
        args = argparse.Namespace(tier="critical")

        result = _cmd_list(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] == 1
        assert result.data["repos"][0]["tier"] == "critical"

    @patch("cihub.commands.registry.query.load_registry")
    @patch("cihub.commands.registry.query.list_repos")
    def test_empty_list_returns_success(
        self, mock_list_repos: MagicMock, mock_load: MagicMock
    ) -> None:
        """Empty repo list returns SUCCESS with zero count."""
        mock_load.return_value = {}
        mock_list_repos.return_value = []
        args = argparse.Namespace(tier=None)

        result = _cmd_list(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] == 0


# =============================================================================
# _cmd_show Tests
# =============================================================================


class TestCmdShow:
    """Tests for _cmd_show function."""

    @patch("cihub.commands.registry.query.load_registry")
    @patch("cihub.commands.registry.query.get_repo_config")
    def test_shows_repo_config(self, mock_get: MagicMock, mock_load: MagicMock) -> None:
        """Shows detailed config for existing repo."""
        mock_load.return_value = {}
        mock_get.return_value = {
            "name": "test-repo",
            "tier": "standard",
            "description": "Test",
            "effective": {
                "coverage_min": 70,
                "mutation_score_min": 70,
                "max_critical_vulns": 0,
                "max_high_vulns": 0,
            },
            "overrides": {},
            "tier_defaults": {},
        }
        args = argparse.Namespace(repo="test-repo")

        result = _cmd_show(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["name"] == "test-repo"

    @patch("cihub.commands.registry.query.load_registry")
    @patch("cihub.commands.registry.query.get_repo_config")
    def test_not_found_returns_failure(self, mock_get: MagicMock, mock_load: MagicMock) -> None:
        """Returns FAILURE when repo not found."""
        mock_load.return_value = {}
        mock_get.return_value = None
        args = argparse.Namespace(repo="nonexistent")

        result = _cmd_show(args)

        assert result.exit_code == EXIT_FAILURE
        assert len(result.problems) == 1
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-NOT-FOUND"


# =============================================================================
# _cmd_set Tests
# =============================================================================


class TestCmdSet:
    """Tests for _cmd_set function."""

    @patch("cihub.commands.registry.modify.save_registry")
    @patch("cihub.commands.registry.modify.set_repo_override")
    @patch("cihub.commands.registry.modify.set_repo_tier")
    @patch("cihub.commands.registry.modify.load_registry")
    def test_sets_tier(
        self,
        mock_load: MagicMock,
        mock_set_tier: MagicMock,
        mock_set_override: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Sets tier for repo."""
        mock_load.return_value = {"repos": {"test": {"tier": "standard"}}}
        args = argparse.Namespace(
            repo="test", tier="critical", coverage=None, mutation=None, vulns_max=None
        )

        result = _cmd_set(args)

        assert result.exit_code == EXIT_SUCCESS
        mock_set_tier.assert_called_once()
        mock_save.assert_called_once()

    @patch("cihub.commands.registry.modify.load_registry")
    def test_no_changes_returns_usage_error(self, mock_load: MagicMock) -> None:
        """Returns USAGE error when no changes specified."""
        mock_load.return_value = {"repos": {"test": {"tier": "standard"}}}
        args = argparse.Namespace(
            repo="test", tier=None, coverage=None, mutation=None, vulns_max=None
        )

        result = _cmd_set(args)

        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-NO-CHANGES"


# =============================================================================
# _cmd_add Tests
# =============================================================================


class TestCmdAdd:
    """Tests for _cmd_add function."""

    @patch("cihub.commands.registry.modify.save_registry")
    @patch("cihub.commands.registry.modify.load_registry")
    def test_adds_new_repo(self, mock_load: MagicMock, mock_save: MagicMock) -> None:
        """Adds new repo to registry."""
        mock_load.return_value = {
            "tiers": {"standard": {"profile": "standard"}},
            "repos": {},
        }
        args = argparse.Namespace(
            repo="new-repo",
            tier="standard",
            description="New repo",
            wizard=False,
            json=False,
            owner=None,
            name=None,
            language=None,
        )

        result = _cmd_add(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "new-repo" in result.summary
        mock_save.assert_called_once()

    @patch("cihub.commands.registry.modify.load_registry")
    def test_rejects_existing_repo(self, mock_load: MagicMock) -> None:
        """Rejects adding repo that already exists."""
        mock_load.return_value = {
            "tiers": {"standard": {}},
            "repos": {"existing": {"tier": "standard"}},
        }
        args = argparse.Namespace(
            repo="existing",
            tier="standard",
            description=None,
            wizard=False,
            json=False,
            owner=None,
            name=None,
            language=None,
        )

        result = _cmd_add(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-EXISTS"

    @patch("cihub.commands.registry.modify.load_registry")
    def test_rejects_unknown_tier(self, mock_load: MagicMock) -> None:
        """Rejects unknown tier."""
        mock_load.return_value = {
            "tiers": {"standard": {}},
            "repos": {},
        }
        args = argparse.Namespace(
            repo="new-repo",
            tier="unknown-tier",
            description=None,
            wizard=False,
            json=False,
            owner=None,
            name=None,
            language=None,
        )

        result = _cmd_add(args)

        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-INVALID-TIER"

    def test_wizard_json_conflict(self) -> None:
        """Rejects --wizard with --json."""
        args = argparse.Namespace(
            repo="test",
            tier="standard",
            wizard=True,
            json=True,
        )

        result = _cmd_add(args)

        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-WIZARD-JSON"

    def test_name_requires_owner(self) -> None:
        """Rejects --name without --owner."""
        with patch("cihub.commands.registry.modify.load_registry") as mock_load:
            mock_load.return_value = {
                "tiers": {"standard": {}},
                "repos": {},
            }
            args = argparse.Namespace(
                repo="test",
                tier="standard",
                description=None,
                wizard=False,
                json=False,
                owner=None,
                name="custom-name",  # Different from repo
                language=None,
            )

            result = _cmd_add(args)

            assert result.exit_code == EXIT_USAGE
            assert result.problems[0]["code"] == "CIHUB-REGISTRY-NAME-REQUIRES-OWNER"


# =============================================================================
# _cmd_remove Tests
# =============================================================================


class TestCmdRemove:
    """Tests for _cmd_remove function."""

    @patch("cihub.commands.registry.modify.hub_root")
    @patch("cihub.commands.registry.modify.save_registry")
    @patch("cihub.commands.registry.modify.load_registry")
    def test_removes_repo_with_confirm(
        self, mock_load: MagicMock, mock_save: MagicMock, mock_hub_root: MagicMock, tmp_path: Path
    ) -> None:
        """Removes repo when --yes is provided."""
        mock_hub_root.return_value = tmp_path
        mock_load.return_value = {"repos": {"test": {"tier": "standard"}}}
        args = argparse.Namespace(
            repo="test", delete_config=False, yes=True
        )

        result = _cmd_remove(args)

        assert result.exit_code == EXIT_SUCCESS
        mock_save.assert_called_once()

    @patch("cihub.commands.registry.modify.hub_root")
    @patch("cihub.commands.registry.modify.load_registry")
    def test_requires_confirmation(self, mock_load: MagicMock, mock_hub_root: MagicMock, tmp_path: Path) -> None:
        """Requires --yes for confirmation."""
        mock_hub_root.return_value = tmp_path
        mock_load.return_value = {"repos": {"test": {"tier": "standard"}}}
        args = argparse.Namespace(
            repo="test", delete_config=False, yes=False
        )

        result = _cmd_remove(args)

        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-CONFIRM-REQUIRED"

    @patch("cihub.commands.registry.modify.load_registry")
    def test_not_found_returns_failure(self, mock_load: MagicMock) -> None:
        """Returns FAILURE when repo not found."""
        mock_load.return_value = {"repos": {}}
        args = argparse.Namespace(repo="nonexistent", delete_config=False, yes=True)

        result = _cmd_remove(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-NOT-FOUND"


# =============================================================================
# _cmd_export Tests
# =============================================================================


class TestCmdExport:
    """Tests for _cmd_export function."""

    @patch("cihub.commands.registry.io.load_registry")
    def test_exports_registry(self, mock_load: MagicMock, tmp_path: Path) -> None:
        """Exports registry to JSON file."""
        mock_load.return_value = {
            "schema_version": "v1",
            "tiers": {"standard": {}},
            "repos": {"repo1": {"tier": "standard"}},
        }
        output_file = tmp_path / "export.json"
        args = argparse.Namespace(output=str(output_file), pretty=False)

        result = _cmd_export(args)

        assert result.exit_code == EXIT_SUCCESS
        assert output_file.exists()
        assert result.data["repo_count"] == 1

    @patch("cihub.commands.registry.io.load_registry")
    def test_exports_with_pretty_print(self, mock_load: MagicMock, tmp_path: Path) -> None:
        """Exports with pretty formatting when --pretty."""
        mock_load.return_value = {"tiers": {}, "repos": {}}
        output_file = tmp_path / "export.json"
        args = argparse.Namespace(output=str(output_file), pretty=True)

        result = _cmd_export(args)

        assert result.exit_code == EXIT_SUCCESS
        content = output_file.read_text()
        assert "\n" in content  # Pretty-printed has newlines


# =============================================================================
# _cmd_import Tests
# =============================================================================


class TestCmdImport:
    """Tests for _cmd_import function."""

    def test_rejects_both_merge_and_replace(self, tmp_path: Path) -> None:
        """Rejects --merge and --replace together."""
        import_file = tmp_path / "import.json"
        import_file.write_text("{}")
        args = argparse.Namespace(
            file=str(import_file), merge=True, replace=True, dry_run=False
        )

        result = _cmd_import(args)

        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-IMPORT-CONFLICT"

    def test_requires_merge_or_replace(self, tmp_path: Path) -> None:
        """Requires either --merge or --replace."""
        import_file = tmp_path / "import.json"
        import_file.write_text("{}")
        args = argparse.Namespace(
            file=str(import_file), merge=False, replace=False, dry_run=False
        )

        result = _cmd_import(args)

        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-IMPORT-MODE-REQUIRED"

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Returns FAILURE when import file not found."""
        args = argparse.Namespace(
            file=str(tmp_path / "nonexistent.json"),
            merge=True,
            replace=False,
            dry_run=False,
        )

        result = _cmd_import(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-IMPORT-NOT-FOUND"

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Returns FAILURE for invalid JSON."""
        import_file = tmp_path / "invalid.json"
        import_file.write_text("not json {")
        args = argparse.Namespace(
            file=str(import_file), merge=True, replace=False, dry_run=False
        )

        result = _cmd_import(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-IMPORT-PARSE-ERROR"

    def test_replace_requires_complete_registry(self, tmp_path: Path) -> None:
        """Replace mode requires schema_version, tiers, repos."""
        import_file = tmp_path / "incomplete.json"
        import_file.write_text('{"repos": {}}')  # Missing schema_version and tiers
        args = argparse.Namespace(
            file=str(import_file), merge=False, replace=True, dry_run=False
        )

        result = _cmd_import(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-IMPORT-INCOMPLETE"

    @patch("cihub.commands.registry.io.save_registry")
    @patch("cihub.commands.registry.io.load_registry")
    def test_merge_adds_new_repos(
        self, mock_load: MagicMock, mock_save: MagicMock, tmp_path: Path
    ) -> None:
        """Merge mode adds new repos."""
        mock_load.return_value = {
            "schema_version": "v1",
            "tiers": {"standard": {}},
            "repos": {"existing": {"tier": "standard"}},
        }
        import_file = tmp_path / "import.json"
        import_file.write_text(
            json.dumps({"repos": {"new-repo": {"tier": "standard"}}})
        )
        args = argparse.Namespace(
            file=str(import_file), merge=True, replace=False, dry_run=False
        )

        result = _cmd_import(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "new-repo" in result.data["added"]
        mock_save.assert_called_once()


# =============================================================================
# _cmd_diff Tests
# =============================================================================


class TestCmdDiff:
    """Tests for _cmd_diff function."""

    def test_missing_configs_dir(self, tmp_path: Path) -> None:
        """Returns FAILURE when configs dir doesn't exist."""
        with patch("cihub.commands.registry.sync.hub_root") as mock_hub:
            mock_hub.return_value = tmp_path
            args = argparse.Namespace(
                configs_dir=str(tmp_path / "nonexistent"),
                repos_root=None,
            )

            result = _cmd_diff(args)

            assert result.exit_code in (EXIT_FAILURE, EXIT_USAGE)


# =============================================================================
# _cmd_sync Tests
# =============================================================================


class TestCmdSync:
    """Tests for _cmd_sync function."""

    def test_missing_configs_dir(self, tmp_path: Path) -> None:
        """Returns FAILURE when configs dir doesn't exist."""
        with patch("cihub.commands.registry.sync.hub_root") as mock_hub:
            mock_hub.return_value = tmp_path
            args = argparse.Namespace(
                configs_dir=str(tmp_path / "nonexistent"),
                dry_run=True,
                yes=False,
            )

            result = _cmd_sync(args)

            assert result.exit_code in (EXIT_FAILURE, EXIT_USAGE)


# =============================================================================
# _cmd_bootstrap Tests
# =============================================================================


class TestCmdBootstrap:
    """Tests for _cmd_bootstrap function."""

    def test_missing_configs_dir(self, tmp_path: Path) -> None:
        """Returns FAILURE when configs dir doesn't exist."""
        with patch("cihub.commands.registry.sync.hub_root") as mock_hub:
            mock_hub.return_value = tmp_path
            args = argparse.Namespace(
                configs_dir=str(tmp_path / "nonexistent"),
                tier="standard",
                strategy="keep",
                dry_run=True,
                include_thresholds=False,
            )

            result = _cmd_bootstrap(args)

            assert result.exit_code in (EXIT_FAILURE, EXIT_USAGE)

    @patch("cihub.commands.registry.sync.bootstrap_from_configs")
    @patch("cihub.commands.registry.sync.hub_root")
    def test_bootstrap_error_handling(
        self, mock_hub: MagicMock, mock_bootstrap: MagicMock, hub_structure: Path
    ) -> None:
        """Handles bootstrap errors correctly."""
        mock_hub.return_value = hub_structure
        mock_bootstrap.return_value = {
            "error": "Failed to bootstrap",
            "imported": [],
            "skipped": [],
            "conflicts": [],
            "dry_run": False,
        }
        args = argparse.Namespace(
            configs_dir=None,
            tier="standard",
            strategy="keep",
            dry_run=False,
            include_thresholds=False,
        )

        result = _cmd_bootstrap(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REGISTRY-BOOTSTRAP-ERROR"
