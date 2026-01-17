"""Tests for cihub.utils.validation module."""

from __future__ import annotations

from cihub.utils.validation import validate_profile_name


class TestValidateProfileName:
    """Tests for validate_profile_name function."""

    def test_valid_profile_name(self) -> None:
        """Valid profile names return None."""
        assert validate_profile_name("python-fast") is None
        assert validate_profile_name("java_standard") is None
        assert validate_profile_name("tier-1") is None
        assert validate_profile_name("myProfile123") is None

    def test_empty_name(self) -> None:
        """Empty name returns error."""
        result = validate_profile_name("")
        assert result == "Profile name cannot be empty"

    def test_forward_slash(self) -> None:
        """Forward slash returns error."""
        result = validate_profile_name("path/to/profile")
        assert result == "Profile name cannot contain path separators"

    def test_backslash(self) -> None:
        """Backslash returns error."""
        result = validate_profile_name("path\\to\\profile")
        assert result == "Profile name cannot contain path separators"

    def test_parent_directory(self) -> None:
        """Parent directory traversal returns error."""
        result = validate_profile_name("..evil")
        assert result == "Profile name cannot contain '..'"
        result2 = validate_profile_name("path..escape")
        assert result2 == "Profile name cannot contain '..'"

    def test_hidden_file(self) -> None:
        """Hidden file (starts with dot) returns error."""
        result = validate_profile_name(".hidden")
        assert result == "Profile name cannot start with '.'"

    def test_invalid_characters(self) -> None:
        """Invalid characters return error."""
        result = validate_profile_name("profile@name")
        assert result == "Profile name can only contain letters, numbers, dashes, and underscores"
        result2 = validate_profile_name("profile name")
        assert result2 == "Profile name can only contain letters, numbers, dashes, and underscores"
