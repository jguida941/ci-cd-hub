"""Tests for profile_cmd - profile management commands."""

from __future__ import annotations

from pathlib import Path

import yaml

from cihub.commands.profile_cmd import (
    _cmd_list,
    _cmd_show,
    _get_profiles_dir,
    _list_profiles,
    _load_profile,
    _save_profile,
    cmd_profile,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE


def _create_profile(profiles_dir: Path, name: str, content: dict) -> Path:
    """Helper to create a profile file."""
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_path = profiles_dir / f"{name}.yaml"
    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(content, f)
    return profile_path


class TestListProfiles:
    """Tests for _list_profiles helper and _cmd_list command."""

    def test_list_profiles_empty_dir(self, tmp_path: Path) -> None:
        """Empty profiles directory returns empty list."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()

        profiles = _list_profiles(profiles_dir)

        assert profiles == []

    def test_list_profiles_nonexistent_dir(self, tmp_path: Path) -> None:
        """Nonexistent directory returns empty list."""
        profiles_dir = tmp_path / "nonexistent"

        profiles = _list_profiles(profiles_dir)

        assert profiles == []

    def test_list_profiles_detects_language_type(self, tmp_path: Path) -> None:
        """Language profiles are detected from prefix."""
        profiles_dir = tmp_path / "profiles"
        _create_profile(profiles_dir, "python-standard", {"language": "python"})
        _create_profile(profiles_dir, "java-enterprise", {"language": "java"})

        profiles = _list_profiles(profiles_dir)

        assert len(profiles) == 2
        python_prof = next(p for p in profiles if p["name"] == "python-standard")
        java_prof = next(p for p in profiles if p["name"] == "java-enterprise")
        assert python_prof["language"] == "python"
        assert python_prof["type"] == "language"
        assert java_prof["language"] == "java"
        assert java_prof["type"] == "language"

    def test_list_profiles_detects_tier_type(self, tmp_path: Path) -> None:
        """Tier profiles are detected from prefix."""
        profiles_dir = tmp_path / "profiles"
        _create_profile(profiles_dir, "tier-strict", {"thresholds": {}})
        _create_profile(profiles_dir, "tier-relaxed", {"thresholds": {}})

        profiles = _list_profiles(profiles_dir)

        assert len(profiles) == 2
        for p in profiles:
            assert p["type"] == "tier"
            assert p["language"] is None

    def test_cmd_list_returns_all_profiles(self, tmp_path: Path, monkeypatch) -> None:
        """List command returns all profiles."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "python-standard", {})
        _create_profile(profiles_dir, "java-standard", {})
        _create_profile(profiles_dir, "tier-strict", {})
        monkeypatch.setattr(
            "cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir
        )

        # Create args namespace
        class Args:
            language = None
            type = None

        result = _cmd_list(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] == 3
        assert len(result.data["profiles"]) == 3

    def test_cmd_list_filters_by_language(self, tmp_path: Path, monkeypatch) -> None:
        """List command filters by language."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "python-standard", {})
        _create_profile(profiles_dir, "python-fast", {})
        _create_profile(profiles_dir, "java-standard", {})
        monkeypatch.setattr(
            "cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir
        )

        class Args:
            language = "python"
            type = None

        result = _cmd_list(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] == 2
        assert all(p["language"] == "python" for p in result.data["profiles"])

    def test_cmd_list_filters_by_type(self, tmp_path: Path, monkeypatch) -> None:
        """List command filters by type."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "python-standard", {})
        _create_profile(profiles_dir, "tier-strict", {})
        _create_profile(profiles_dir, "tier-relaxed", {})
        monkeypatch.setattr(
            "cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir
        )

        class Args:
            language = None
            type = "tier"

        result = _cmd_list(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] == 2
        assert all(p["type"] == "tier" for p in result.data["profiles"])

    def test_cmd_list_no_matches(self, tmp_path: Path, monkeypatch) -> None:
        """List command with no matches returns empty."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "python-standard", {})
        monkeypatch.setattr(
            "cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir
        )

        class Args:
            language = "java"
            type = None

        result = _cmd_list(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["profiles"] == []


class TestShowProfile:
    """Tests for _cmd_show command."""

    def test_show_existing_profile(self, tmp_path: Path, monkeypatch) -> None:
        """Show returns profile content."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profile_content = {
            "language": "python",
            "python": {"tools": {"ruff": {"enabled": True}}},
        }
        _create_profile(profiles_dir, "python-standard", profile_content)
        monkeypatch.setattr(
            "cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir
        )

        class Args:
            name = "python-standard"
            effective = False

        result = _cmd_show(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["name"] == "python-standard"
        assert result.data["profile"]["language"] == "python"

    def test_show_nonexistent_profile(self, tmp_path: Path, monkeypatch) -> None:
        """Show returns error for nonexistent profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir
        )

        class Args:
            name = "nonexistent"
            effective = False

        result = _cmd_show(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-NOT-FOUND"

    def test_show_invalid_yaml_profile(self, tmp_path: Path, monkeypatch) -> None:
        """Show returns error for invalid YAML."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        bad_yaml = profiles_dir / "bad.yaml"
        bad_yaml.write_text("{ invalid: yaml: content:", encoding="utf-8")
        monkeypatch.setattr(
            "cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir
        )

        class Args:
            name = "bad"
            effective = False

        result = _cmd_show(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-INVALID-YAML"


class TestLoadSaveProfile:
    """Tests for _load_profile and _save_profile helpers."""

    def test_load_profile_returns_content(self, tmp_path: Path) -> None:
        """Load returns profile content."""
        profiles_dir = tmp_path / "profiles"
        content = {"language": "python", "thresholds": {"coverage_min": 80}}
        _create_profile(profiles_dir, "test", content)

        loaded = _load_profile(profiles_dir, "test")

        assert loaded == content

    def test_load_profile_nonexistent(self, tmp_path: Path) -> None:
        """Load returns None for nonexistent profile."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()

        loaded = _load_profile(profiles_dir, "nonexistent")

        assert loaded is None

    def test_save_profile_creates_file(self, tmp_path: Path) -> None:
        """Save creates profile file."""
        profiles_dir = tmp_path / "profiles"
        content = {"language": "java"}

        path = _save_profile(profiles_dir, "java-custom", content)

        assert path.exists()
        loaded = yaml.safe_load(path.read_text())
        assert loaded == content

    def test_save_profile_creates_directory(self, tmp_path: Path) -> None:
        """Save creates profiles directory if needed."""
        profiles_dir = tmp_path / "nested" / "profiles"
        content = {"language": "python"}

        path = _save_profile(profiles_dir, "test", content)

        assert profiles_dir.exists()
        assert path.exists()


class TestProfileDispatcher:
    """Tests for cmd_profile dispatcher."""

    def test_unknown_subcommand(self, tmp_path: Path) -> None:
        """Unknown subcommand returns error."""

        class Args:
            subcommand = "unknown"

        result = cmd_profile(Args())

        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-UNKNOWN-SUBCOMMAND"

    def test_none_subcommand(self, tmp_path: Path) -> None:
        """None subcommand returns error."""

        class Args:
            subcommand = None

        result = cmd_profile(Args())

        assert result.exit_code == EXIT_USAGE

    def test_dispatches_to_list(self, tmp_path: Path, monkeypatch) -> None:
        """Dispatcher routes to list command."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir
        )

        class Args:
            subcommand = "list"
            language = None
            type = None

        result = cmd_profile(Args())

        assert result.exit_code == EXIT_SUCCESS


class TestGetProfilesDir:
    """Tests for _get_profiles_dir helper."""

    def test_returns_templates_profiles_path(self, tmp_path: Path, monkeypatch) -> None:
        """Returns correct path under hub root."""
        monkeypatch.setattr("cihub.commands.profile_cmd.hub_root", lambda: tmp_path)

        profiles_dir = _get_profiles_dir()

        assert profiles_dir == tmp_path / "templates" / "profiles"
