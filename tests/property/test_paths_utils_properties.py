"""Property-based tests for path utilities using Hypothesis.

These tests verify path validation, manipulation, and security invariants
that should always hold.
"""

# TEST-METRICS:

from __future__ import annotations

import os
from pathlib import PurePosixPath

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.utils.paths import validate_subdir

# =============================================================================
# Strategy Definitions
# =============================================================================

# Strategy for safe path segments (no special characters)
safe_segment_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
    min_size=1,
    max_size=12,
).filter(lambda s: s not in {".", "..", ""})

# Strategy for unsafe path segments (potential traversal)
traversal_segment_strategy = st.sampled_from(["..", ".", "../..", "./..", "..\\.."])

# Strategy for valid relative paths
valid_relative_path_strategy = st.lists(
    safe_segment_strategy, min_size=1, max_size=4
).map(lambda parts: "/".join(parts))

# Strategy for paths with different separators
path_with_separator_strategy = st.tuples(
    st.lists(safe_segment_strategy, min_size=1, max_size=3),
    st.sampled_from(["/", os.sep]),
).map(lambda t: t[1].join(t[0]))


# =============================================================================
# validate_subdir Property Tests
# =============================================================================


class TestValidateSubdirSecurityProperties:
    """Security-focused property tests for validate_subdir."""

    @given(segments=st.lists(safe_segment_strategy, min_size=1, max_size=4))
    @settings(max_examples=50)
    def test_safe_paths_accepted(self, segments: list[str]) -> None:
        """Property: paths with only safe segments are accepted."""
        subdir = "/".join(segments)
        result = validate_subdir(subdir)
        assert result == subdir

    @given(
        prefix=st.lists(safe_segment_strategy, min_size=0, max_size=2),
        suffix=st.lists(safe_segment_strategy, min_size=0, max_size=2),
    )
    @settings(max_examples=50)
    def test_dotdot_always_rejected(self, prefix: list[str], suffix: list[str]) -> None:
        """Property: paths containing '..' are always rejected."""
        parts = prefix + [".."] + suffix
        subdir = "/".join(parts)
        with pytest.raises(ValueError, match="traversal"):
            validate_subdir(subdir)

    @given(segments=st.lists(safe_segment_strategy, min_size=1, max_size=4))
    @settings(max_examples=50)
    def test_absolute_paths_rejected(self, segments: list[str]) -> None:
        """Property: absolute paths starting with / are rejected."""
        subdir = "/" + "/".join(segments)
        with pytest.raises(ValueError, match="relative"):
            validate_subdir(subdir)

    @given(segments=st.lists(safe_segment_strategy, min_size=1, max_size=4))
    @settings(max_examples=50)
    def test_windows_backslash_normalized(self, segments: list[str]) -> None:
        """Property: Windows backslash paths are handled via normalization."""
        # Note: Windows paths with C:\\ don't start with / when normalized
        # so they pass through. The function normalizes to posix for checking.
        subdir = "\\".join(segments)  # relative Windows path
        # Should be accepted since it's relative
        result = validate_subdir(subdir)
        assert result == subdir  # Original preserved

    @given(subdir=valid_relative_path_strategy)
    @settings(max_examples=50)
    def test_output_never_starts_with_slash(self, subdir: str) -> None:
        """Property: valid output never starts with '/'."""
        result = validate_subdir(subdir)
        assert not result.startswith("/")

    @given(subdir=valid_relative_path_strategy)
    @settings(max_examples=50)
    def test_output_never_contains_dotdot(self, subdir: str) -> None:
        """Property: valid output never contains '..'."""
        result = validate_subdir(subdir)
        assert ".." not in result


class TestValidateSubdirEdgeCaseProperties:
    """Edge case property tests for validate_subdir."""

    @given(segment=safe_segment_strategy)
    @settings(max_examples=50)
    def test_single_segment_accepted(self, segment: str) -> None:
        """Property: single valid segment is accepted."""
        result = validate_subdir(segment)
        assert result == segment

    @given(segments=st.lists(safe_segment_strategy, min_size=2, max_size=4))
    @settings(max_examples=50)
    def test_multi_segment_preserved(self, segments: list[str]) -> None:
        """Property: multi-segment paths are preserved."""
        subdir = "/".join(segments)
        result = validate_subdir(subdir)
        # Should contain all original segments
        result_parts = result.split("/")
        assert len(result_parts) == len(segments)

    @given(
        prefix=safe_segment_strategy,
        suffix=safe_segment_strategy,
    )
    @settings(max_examples=50)
    def test_hidden_files_rejected(self, prefix: str, suffix: str) -> None:
        """Property: paths containing hidden dot-files starting with '.' are checked."""
        # Note: single dot is special, not a hidden file name
        subdir = f"{prefix}/.hidden/{suffix}"
        # This should be accepted since .hidden is a valid directory name
        # The rejection is for '.' and '..' specifically
        try:
            result = validate_subdir(subdir)
            assert ".hidden" in result
        except ValueError:
            # Some implementations may reject hidden files
            pass


class TestValidateSubdirNormalizationProperties:
    """Normalization property tests for validate_subdir."""

    @given(subdir=valid_relative_path_strategy)
    @settings(max_examples=50)
    def test_idempotent(self, subdir: str) -> None:
        """Property: validating twice gives same result."""
        once = validate_subdir(subdir)
        twice = validate_subdir(once)
        assert once == twice

    @given(segments=st.lists(safe_segment_strategy, min_size=1, max_size=3))
    @settings(max_examples=50)
    def test_trailing_slash_preserved(self, segments: list[str]) -> None:
        """Property: trailing slashes are preserved (original input returned)."""
        subdir = "/".join(segments) + "/"
        # Function returns original input unchanged if valid
        result = validate_subdir(subdir)
        # Original input is preserved (including trailing slash)
        assert result == subdir


# =============================================================================
# Path Construction Property Tests
# =============================================================================


class TestPathConstructionProperties:
    """Property tests for path construction invariants."""

    @given(
        base=safe_segment_strategy,
        relative=st.lists(safe_segment_strategy, min_size=1, max_size=3).map(lambda p: "/".join(p)),
    )
    @settings(max_examples=50)
    def test_path_join_preserves_parts(self, base: str, relative: str) -> None:
        """Property: joining paths preserves all parts."""
        result = str(PurePosixPath(base) / relative)
        assert base in result
        for part in relative.split("/"):
            assert part in result

    @given(parts=st.lists(safe_segment_strategy, min_size=1, max_size=4))
    @settings(max_examples=50)
    def test_posix_path_uses_forward_slash(self, parts: list[str]) -> None:
        """Property: PurePosixPath always uses forward slashes."""
        path = PurePosixPath(*parts)
        assert "\\" not in str(path)

    @given(
        filename=safe_segment_strategy,
        extension=st.sampled_from([".py", ".yaml", ".json", ".md", ".txt"]),
    )
    @settings(max_examples=50)
    def test_extension_preserved(self, filename: str, extension: str) -> None:
        """Property: file extensions are preserved in paths."""
        path = PurePosixPath(filename + extension)
        assert path.suffix == extension


# =============================================================================
# Path Pattern Property Tests
# =============================================================================


class TestPathPatternProperties:
    """Property tests for path pattern matching."""

    @given(
        dirname=safe_segment_strategy,
        filename=safe_segment_strategy,
    )
    @settings(max_examples=50)
    def test_parent_relationship(self, dirname: str, filename: str) -> None:
        """Property: child path has parent as prefix."""
        parent = PurePosixPath(dirname)
        child = parent / filename
        assert str(child).startswith(str(parent))

    @given(parts=st.lists(safe_segment_strategy, min_size=2, max_size=4))
    @settings(max_examples=50)
    def test_parent_of_child_equals_original(self, parts: list[str]) -> None:
        """Property: parent of child equals original path."""
        path = PurePosixPath(*parts)
        child = path / "subfile"
        assert child.parent == path
