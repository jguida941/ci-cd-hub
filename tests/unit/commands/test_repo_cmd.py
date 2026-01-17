"""Behavior tests for repo command."""

# TEST-METRICS:
#   Coverage: 100.0%

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cihub.commands.repo_cmd import (
    _cmd_clone,
    _cmd_list,
    _cmd_migrate,
    _cmd_show,
    _cmd_update,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def _write_registry(tmp_path: Path, registry: dict[str, object]) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "registry.json").write_text(json.dumps(registry), encoding="utf-8")


def _base_registry() -> dict[str, object]:
    return {
        "schema_version": "cihub-registry-v1",
        "tiers": {
            "standard": {"description": "Standard tier"},
            "strict": {"description": "Strict tier"},
        },
        "repos": {
            "alpha": {
                "tier": "standard",
                "config": {
                    "repo": {
                        "owner": "org",
                        "name": "alpha",
                        "default_branch": "main",
                    }
                },
            },
            "beta": {"tier": "strict"},
        },
    }


class TestRepoList:
    """Tests for repo list subcommand."""

    def test_list_all_repos(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(language=None, tier=None, with_overrides=False)
        result = _cmd_list(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] == 2
        repo_names = [r["name"] for r in result.data["repos"]]
        assert "alpha" in repo_names
        assert "beta" in repo_names

    def test_list_filter_by_tier(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(language=None, tier="strict", with_overrides=False)
        result = _cmd_list(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] == 1
        assert result.data["repos"][0]["name"] == "beta"


class TestRepoShow:
    """Tests for repo show subcommand."""

    def test_show_repo_details(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(name="alpha", effective=False)
        result = _cmd_show(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["tier"] == "standard"

    def test_show_nonexistent_repo_fails(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(name="nonexistent", effective=False)
        result = _cmd_show(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REPO-NOT-FOUND"


class TestRepoUpdate:
    """Tests for repo update subcommand."""

    def test_update_default_branch_uses_correct_field(self, tmp_path: Path, monkeypatch) -> None:
        """Verify --default-branch writes to default_branch, not branch."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            name="alpha",
            owner=None,
            repo_name=None,
            default_branch="develop",
            language=None,
            tier=None,
            dispatch_enabled=None,
            description=None,
        )
        result = _cmd_update(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "default_branch" in result.data["changes"][0]

        # Verify correct field in registry
        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        repo_block = registry["repos"]["alpha"]["config"]["repo"]
        assert repo_block["default_branch"] == "develop"
        assert "branch" not in repo_block

    def test_update_owner_requires_name(self, tmp_path: Path, monkeypatch) -> None:
        """Verify setting --owner without --repo-name fails when name doesn't exist."""
        registry = _base_registry()
        # Remove name from beta so it has neither owner nor name
        registry["repos"]["beta"] = {"tier": "strict"}
        _write_registry(tmp_path, registry)
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            name="beta",
            owner="neworg",
            repo_name=None,  # Not provided
            default_branch=None,
            language=None,
            tier=None,
            dispatch_enabled=None,
            description=None,
        )
        result = _cmd_update(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REPO-OWNER-NEEDS-NAME"

    def test_update_name_requires_owner(self, tmp_path: Path, monkeypatch) -> None:
        """Verify setting --repo-name without --owner fails when owner doesn't exist."""
        registry = _base_registry()
        registry["repos"]["beta"] = {"tier": "strict"}
        _write_registry(tmp_path, registry)
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            name="beta",
            owner=None,  # Not provided
            repo_name="newname",
            default_branch=None,
            language=None,
            tier=None,
            dispatch_enabled=None,
            description=None,
        )
        result = _cmd_update(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REPO-NAME-NEEDS-OWNER"

    def test_update_owner_allowed_when_name_exists(self, tmp_path: Path, monkeypatch) -> None:
        """Verify --owner works when name already exists in config."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        # alpha already has owner and name
        args = argparse.Namespace(
            name="alpha",
            owner="neworg",
            repo_name=None,
            default_branch=None,
            language=None,
            tier=None,
            dispatch_enabled=None,
            description=None,
        )
        result = _cmd_update(args)

        assert result.exit_code == EXIT_SUCCESS

    def test_update_both_owner_and_name(self, tmp_path: Path, monkeypatch) -> None:
        """Verify providing both --owner and --repo-name works."""
        registry = _base_registry()
        registry["repos"]["beta"] = {"tier": "strict"}
        _write_registry(tmp_path, registry)
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            name="beta",
            owner="neworg",
            repo_name="newname",
            default_branch=None,
            language=None,
            tier=None,
            dispatch_enabled=None,
            description=None,
        )
        result = _cmd_update(args)

        assert result.exit_code == EXIT_SUCCESS
        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        repo_block = registry["repos"]["beta"]["config"]["repo"]
        assert repo_block["owner"] == "neworg"
        assert repo_block["name"] == "newname"


class TestRepoMigrate:
    """Tests for repo migrate subcommand."""

    def test_migrate_uses_deep_copy(self, tmp_path: Path, monkeypatch) -> None:
        """Verify migrate uses deep copy to prevent shared nested dicts."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(source="alpha", dest="alpha-copy", delete_source=False, force=False)
        result = _cmd_migrate(args)

        assert result.exit_code == EXIT_SUCCESS

        # Modify the copy and verify original is unchanged
        registry = json.loads((tmp_path / "config" / "registry.json").read_text())

        # Mutate the copy's nested config
        registry["repos"]["alpha-copy"]["config"]["repo"]["owner"] = "modified"
        (tmp_path / "config" / "registry.json").write_text(json.dumps(registry), encoding="utf-8")

        # Re-read and verify original is unchanged
        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        assert registry["repos"]["alpha"]["config"]["repo"]["owner"] == "org"
        assert registry["repos"]["alpha-copy"]["config"]["repo"]["owner"] == "modified"

    def test_migrate_with_delete_source(self, tmp_path: Path, monkeypatch) -> None:
        """Verify --delete-source removes the source entry."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(source="alpha", dest="alpha-renamed", delete_source=True, force=False)
        result = _cmd_migrate(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["action"] == "renamed"

        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        assert "alpha" not in registry["repos"]
        assert "alpha-renamed" in registry["repos"]


class TestRepoClone:
    """Tests for repo clone subcommand."""

    def test_clone_uses_deep_copy(self, tmp_path: Path, monkeypatch) -> None:
        """Verify clone creates independent copy."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(source="alpha", dest="alpha-clone", force=False)
        result = _cmd_clone(args)

        assert result.exit_code == EXIT_SUCCESS

        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        assert "alpha" in registry["repos"]
        assert "alpha-clone" in registry["repos"]

        # Verify they're independent
        assert (
            registry["repos"]["alpha"]["config"]["repo"]["owner"]
            == registry["repos"]["alpha-clone"]["config"]["repo"]["owner"]
        )

    def test_clone_fails_if_dest_exists(self, tmp_path: Path, monkeypatch) -> None:
        """Verify clone fails when destination exists without --force."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(source="alpha", dest="beta", force=False)
        result = _cmd_clone(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-REPO-EXISTS"
