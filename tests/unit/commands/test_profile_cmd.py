"""Tests for profile_cmd - profile management commands."""

from __future__ import annotations

from pathlib import Path

import yaml

from cihub.commands.profile_cmd import (
    _cmd_create,
    _cmd_delete,
    _cmd_export,
    _cmd_import,
    _cmd_list,
    _cmd_show,
    _cmd_validate,
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
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

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
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

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
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

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
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

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
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

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
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

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
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

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
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

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


class TestCreateProfile:
    """Tests for _cmd_create command."""

    def test_create_empty_profile(self, tmp_path: Path, monkeypatch) -> None:
        """Create makes an empty profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "custom-profile"
            language = None
            from_profile = None
            from_repo = None
            description = None
            force = False

        result = _cmd_create(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["name"] == "custom-profile"
        assert (profiles_dir / "custom-profile.yaml").exists()

    def test_create_profile_with_language(self, tmp_path: Path, monkeypatch) -> None:
        """Create with language initializes tools section."""
        profiles_dir = tmp_path / "templates" / "profiles"
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "python-custom"
            language = "python"
            from_profile = None
            from_repo = None
            description = "My custom profile"
            force = False

        result = _cmd_create(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert "python" in result.data["content"]
        assert result.data["content"]["python"]["tools"] == {}
        assert result.data["content"]["_description"] == "My custom profile"

    def test_create_from_existing_profile(self, tmp_path: Path, monkeypatch) -> None:
        """Create copies content from source profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        source_content = {"python": {"tools": {"ruff": {"enabled": True}}}}
        _create_profile(profiles_dir, "python-source", source_content)
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "python-copy"
            language = None
            from_profile = "python-source"
            from_repo = None
            description = None
            force = False

        result = _cmd_create(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["content"]["python"]["tools"]["ruff"]["enabled"] is True

    def test_create_fails_if_exists(self, tmp_path: Path, monkeypatch) -> None:
        """Create fails if profile already exists without force."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "existing", {"python": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "existing"
            language = None
            from_profile = None
            from_repo = None
            description = None
            force = False

        result = _cmd_create(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-EXISTS"

    def test_create_force_overwrites(self, tmp_path: Path, monkeypatch) -> None:
        """Create with force overwrites existing profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "existing", {"python": {"tools": {"old": {}}}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "existing"
            language = "java"
            from_profile = None
            from_repo = None
            description = None
            force = True

        result = _cmd_create(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert "java" in result.data["content"]

    def test_create_invalid_name_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Create fails with invalid profile name."""
        profiles_dir = tmp_path / "templates" / "profiles"
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "../etc/passwd"
            language = None
            from_profile = None
            from_repo = None
            description = None
            force = False

        result = _cmd_create(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-INVALID-NAME"


class TestDeleteProfile:
    """Tests for _cmd_delete command."""

    def test_delete_existing_profile(self, tmp_path: Path, monkeypatch) -> None:
        """Delete removes the profile file."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "to-delete", {"python": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "to-delete"
            force = False

        result = _cmd_delete(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert not (profiles_dir / "to-delete.yaml").exists()

    def test_delete_nonexistent_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Delete fails for nonexistent profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "nonexistent"
            force = False

        result = _cmd_delete(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-NOT-FOUND"

    def test_delete_builtin_requires_force(self, tmp_path: Path, monkeypatch) -> None:
        """Delete builtin profile requires --force."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "python-fast", {"python": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "python-fast"
            force = False

        result = _cmd_delete(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-BUILTIN"

    def test_delete_builtin_with_force_succeeds(self, tmp_path: Path, monkeypatch) -> None:
        """Delete builtin profile succeeds with --force."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "python-fast", {"python": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "python-fast"
            force = True

        result = _cmd_delete(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert not (profiles_dir / "python-fast.yaml").exists()


class TestExportProfile:
    """Tests for _cmd_export command."""

    def test_export_to_file(self, tmp_path: Path, monkeypatch) -> None:
        """Export writes profile to file."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profile_content = {"python": {"tools": {"ruff": {"enabled": True}}}}
        _create_profile(profiles_dir, "to-export", profile_content)
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        output_path = tmp_path / "exported.yaml"

        class Args:
            name = "to-export"
            output = str(output_path)

        result = _cmd_export(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert output_path.exists()
        with open(output_path) as f:
            exported = yaml.safe_load(f)
        assert exported["python"]["tools"]["ruff"]["enabled"] is True

    def test_export_nonexistent_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Export fails for nonexistent profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "nonexistent"
            output = str(tmp_path / "out.yaml")

        result = _cmd_export(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-NOT-FOUND"

    def test_export_creates_parent_dir(self, tmp_path: Path, monkeypatch) -> None:
        """Export creates parent directories if needed."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "test", {"python": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        output_path = tmp_path / "nested" / "dir" / "out.yaml"

        class Args:
            name = "test"
            output = str(output_path)

        result = _cmd_export(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert output_path.exists()


class TestImportProfile:
    """Tests for _cmd_import command."""

    def test_import_from_file(self, tmp_path: Path, monkeypatch) -> None:
        """Import loads profile from file."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        import_file = tmp_path / "import.yaml"
        with open(import_file, "w") as f:
            yaml.dump({"python": {"tools": {"ruff": {"enabled": True}}}}, f)

        class Args:
            file = str(import_file)
            name = "imported"
            force = False

        result = _cmd_import(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert (profiles_dir / "imported.yaml").exists()

    def test_import_uses_filename_as_name(self, tmp_path: Path, monkeypatch) -> None:
        """Import uses filename as profile name by default."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        import_file = tmp_path / "my-profile.yaml"
        with open(import_file, "w") as f:
            yaml.dump({"python": {}}, f)

        class Args:
            file = str(import_file)
            name = None
            force = False

        result = _cmd_import(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["name"] == "my-profile"

    def test_import_file_not_found_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Import fails if file doesn't exist."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            file = "/nonexistent/file.yaml"
            name = None
            force = False

        result = _cmd_import(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-FILE-NOT-FOUND"

    def test_import_already_exists_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Import fails if profile already exists."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "existing", {"python": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        import_file = tmp_path / "existing.yaml"
        with open(import_file, "w") as f:
            yaml.dump({"java": {}}, f)

        class Args:
            file = str(import_file)
            name = None
            force = False

        result = _cmd_import(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-EXISTS"

    def test_import_force_overwrites(self, tmp_path: Path, monkeypatch) -> None:
        """Import with force overwrites existing profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "existing", {"python": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        import_file = tmp_path / "existing.yaml"
        with open(import_file, "w") as f:
            yaml.dump({"java": {"tools": {"checkstyle": {}}}}, f)

        class Args:
            file = str(import_file)
            name = None
            force = True

        result = _cmd_import(Args())

        assert result.exit_code == EXIT_SUCCESS
        loaded = yaml.safe_load((profiles_dir / "existing.yaml").read_text())
        assert "java" in loaded


class TestValidateProfile:
    """Tests for _cmd_validate command."""

    def test_validate_valid_profile(self, tmp_path: Path, monkeypatch) -> None:
        """Validate passes for valid profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "valid", {"python": {"tools": {"ruff": {}}}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "valid"
            strict = False

        result = _cmd_validate(Args())

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["valid"] is True

    def test_validate_no_language_warns(self, tmp_path: Path, monkeypatch) -> None:
        """Validate warns when profile has no language section."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "no-lang", {"thresholds": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "no-lang"
            strict = False

        result = _cmd_validate(Args())

        assert result.exit_code == EXIT_SUCCESS  # Passes in non-strict mode
        assert any(p["code"] == "CIHUB-PROFILE-NO-LANGUAGE" for p in result.problems)

    def test_validate_no_language_fails_strict(self, tmp_path: Path, monkeypatch) -> None:
        """Validate fails in strict mode when no language section."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "no-lang", {"thresholds": {}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "no-lang"
            strict = True

        result = _cmd_validate(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.data["valid"] is False

    def test_validate_unknown_tool_warns(self, tmp_path: Path, monkeypatch) -> None:
        """Validate warns for unknown tools."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "unknown-tool", {"python": {"tools": {"unknown-tool-xyz": {}}}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "unknown-tool"
            strict = False

        result = _cmd_validate(Args())

        assert result.exit_code == EXIT_SUCCESS  # Passes in non-strict
        assert any("unknown-tool-xyz" in str(p) for p in result.problems)

    def test_validate_unknown_tool_fails_strict(self, tmp_path: Path, monkeypatch) -> None:
        """Validate fails in strict mode for unknown tools."""
        profiles_dir = tmp_path / "templates" / "profiles"
        _create_profile(profiles_dir, "unknown-tool", {"python": {"tools": {"unknown-tool-xyz": {}}}})
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "unknown-tool"
            strict = True

        result = _cmd_validate(Args())

        assert result.exit_code == EXIT_FAILURE

    def test_validate_nonexistent_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Validate fails for nonexistent profile."""
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)
        monkeypatch.setattr("cihub.commands.profile_cmd._get_profiles_dir", lambda: profiles_dir)

        class Args:
            name = "nonexistent"
            strict = False

        result = _cmd_validate(Args())

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-PROFILE-NOT-FOUND"
