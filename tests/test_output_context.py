"""Tests for GitHubContext (and OutputContext alias) dataclass.

This module tests the GitHubContext pattern used for GitHub Actions environment
variables, output files, and summary handling. It validates:
1. from_env() - reading GitHub environment variables
2. from_args() - reading CLI arguments for output config
3. with_output_config() - combining env context with output config
4. Helper properties (is_ci, owner_repo, short_sha, etc.)
5. Output/summary file writing behaviors
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from unittest import mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cihub.utils.github_context import GitHubContext, OutputContext


class TestOutputContextFromArgs:
    """Tests for OutputContext.from_args() factory method."""

    def test_extracts_all_attributes(self) -> None:
        """from_args extracts all four attributes from argparse namespace."""
        args = argparse.Namespace(
            output="/path/to/output.txt",
            github_output=True,
            summary="/path/to/summary.md",
            github_summary=True,
        )
        ctx = OutputContext.from_args(args)
        assert ctx.output_path == "/path/to/output.txt"
        assert ctx.github_output is True
        assert ctx.summary_path == "/path/to/summary.md"
        assert ctx.github_summary is True

    def test_uses_defaults_for_missing_attributes(self) -> None:
        """from_args uses None/False defaults for missing attributes."""
        args = argparse.Namespace()  # Empty namespace
        ctx = OutputContext.from_args(args)
        assert ctx.output_path is None
        assert ctx.github_output is False
        assert ctx.summary_path is None
        assert ctx.github_summary is False

    def test_partial_attributes(self) -> None:
        """from_args handles partial attribute sets correctly."""
        args = argparse.Namespace(output="/path/to/out.txt", github_summary=True)
        ctx = OutputContext.from_args(args)
        assert ctx.output_path == "/path/to/out.txt"
        assert ctx.github_output is False
        assert ctx.summary_path is None
        assert ctx.github_summary is True


class TestOutputContextResolveOutputPath:
    """Tests for OutputContext._resolve_output_path() method."""

    @pytest.mark.parametrize(
        "output_path,github_output,env_value,expected",
        [
            # Explicit path takes precedence
            ("/explicit/path.txt", False, None, "/explicit/path.txt"),
            ("/explicit/path.txt", True, "/env/path.txt", "/explicit/path.txt"),
            # GitHub flag uses env var
            (None, True, "/env/output.txt", "/env/output.txt"),
            # No path and no flag returns None
            (None, False, None, None),
            # Flag but no env var returns None
            (None, True, None, None),
        ],
        ids=[
            "explicit_path_no_flag",
            "explicit_path_overrides_env",
            "github_flag_uses_env",
            "no_path_no_flag",
            "flag_but_no_env",
        ],
    )
    def test_resolve_output_path(
        self,
        output_path: str | None,
        github_output: bool,
        env_value: str | None,
        expected: str | None,
    ) -> None:
        """Property: _resolve_output_path resolves paths with correct precedence."""
        ctx = OutputContext(output_path=output_path, github_output=github_output)
        env = {"GITHUB_OUTPUT": env_value} if env_value else {}
        with mock.patch.dict(os.environ, env, clear=True):
            result = ctx._resolve_output_path()
            if expected is None:
                assert result is None
            else:
                assert result == Path(expected)


class TestOutputContextResolveSummaryPath:
    """Tests for OutputContext._resolve_summary_path() method."""

    @pytest.mark.parametrize(
        "summary_path,github_summary,env_value,expected",
        [
            # Explicit path takes precedence
            ("/explicit/summary.md", False, None, "/explicit/summary.md"),
            ("/explicit/summary.md", True, "/env/summary.md", "/explicit/summary.md"),
            # GitHub flag uses env var
            (None, True, "/env/summary.md", "/env/summary.md"),
            # No path and no flag returns None
            (None, False, None, None),
            # Flag but no env var returns None
            (None, True, None, None),
        ],
        ids=[
            "explicit_path_no_flag",
            "explicit_path_overrides_env",
            "github_flag_uses_env",
            "no_path_no_flag",
            "flag_but_no_env",
        ],
    )
    def test_resolve_summary_path(
        self,
        summary_path: str | None,
        github_summary: bool,
        env_value: str | None,
        expected: str | None,
    ) -> None:
        """Property: _resolve_summary_path resolves paths with correct precedence."""
        ctx = OutputContext(summary_path=summary_path, github_summary=github_summary)
        env = {"GITHUB_STEP_SUMMARY": env_value} if env_value else {}
        with mock.patch.dict(os.environ, env, clear=True):
            result = ctx._resolve_summary_path()
            if expected is None:
                assert result is None
            else:
                assert result == Path(expected)


class TestOutputContextWriteOutputs:
    """Tests for OutputContext.write_outputs() method."""

    def test_writes_to_stdout_when_no_path(self, capsys) -> None:
        """write_outputs prints to stdout when no path is resolved."""
        ctx = OutputContext()  # No path, no flag
        with mock.patch.dict(os.environ, {}, clear=True):
            ctx.write_outputs({"key1": "value1", "key2": "value2"})
        captured = capsys.readouterr()
        assert "key1=value1" in captured.out
        assert "key2=value2" in captured.out

    def test_writes_to_file_when_path_provided(self, tmp_path: Path) -> None:
        """write_outputs appends to file when explicit path is set."""
        output_file = tmp_path / "output.txt"
        ctx = OutputContext(output_path=str(output_file))
        ctx.write_outputs({"issues": "5", "passed": "true"})
        content = output_file.read_text()
        assert "issues=5\n" in content
        assert "passed=true\n" in content

    def test_writes_via_github_output_env(self, tmp_path: Path) -> None:
        """write_outputs uses GITHUB_OUTPUT env var when github_output=True."""
        output_file = tmp_path / "github_output.txt"
        ctx = OutputContext(github_output=True)
        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            ctx.write_outputs({"status": "pass"})
        content = output_file.read_text()
        assert "status=pass\n" in content

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        """write_outputs appends to existing file content."""
        output_file = tmp_path / "output.txt"
        output_file.write_text("existing=value\n")
        ctx = OutputContext(output_path=str(output_file))
        ctx.write_outputs({"new": "data"})
        content = output_file.read_text()
        assert "existing=value\n" in content
        assert "new=data\n" in content

    def test_handles_empty_dict(self, tmp_path: Path) -> None:
        """write_outputs handles empty dictionary gracefully."""
        output_file = tmp_path / "output.txt"
        ctx = OutputContext(output_path=str(output_file))
        ctx.write_outputs({})
        # File should exist but be empty
        assert output_file.read_text() == ""


class TestOutputContextWriteSummary:
    """Tests for OutputContext.write_summary() method."""

    def test_prints_to_stdout_when_no_path(self, capsys) -> None:
        """write_summary prints to stdout when no path is resolved."""
        ctx = OutputContext()
        with mock.patch.dict(os.environ, {}, clear=True):
            ctx.write_summary("## Summary\nSome content")
        captured = capsys.readouterr()
        assert "## Summary" in captured.out
        assert "Some content" in captured.out

    def test_writes_to_file_when_path_provided(self, tmp_path: Path) -> None:
        """write_summary writes to file when explicit path is set."""
        summary_file = tmp_path / "summary.md"
        ctx = OutputContext(summary_path=str(summary_file))
        ctx.write_summary("## Test Results\n\n- Passed: 10")
        content = summary_file.read_text()
        assert "## Test Results" in content
        assert "- Passed: 10" in content

    def test_writes_via_github_summary_env(self, tmp_path: Path) -> None:
        """write_summary uses GITHUB_STEP_SUMMARY env var when github_summary=True."""
        summary_file = tmp_path / "step_summary.md"
        ctx = OutputContext(github_summary=True)
        with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            ctx.write_summary("## Results")
        content = summary_file.read_text()
        assert "## Results" in content

    def test_adds_newline_if_missing(self, tmp_path: Path) -> None:
        """write_summary adds trailing newline if text doesn't end with one."""
        summary_file = tmp_path / "summary.md"
        ctx = OutputContext(summary_path=str(summary_file))
        ctx.write_summary("No newline at end")
        content = summary_file.read_text()
        assert content.endswith("\n")

    def test_preserves_existing_newline(self, tmp_path: Path) -> None:
        """write_summary doesn't double newlines when text ends with one."""
        summary_file = tmp_path / "summary.md"
        ctx = OutputContext(summary_path=str(summary_file))
        ctx.write_summary("Has newline\n")
        content = summary_file.read_text()
        assert content == "Has newline\n"
        assert not content.endswith("\n\n")

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        """write_summary appends to existing file content."""
        summary_file = tmp_path / "summary.md"
        summary_file.write_text("## Existing\n\n")
        ctx = OutputContext(summary_path=str(summary_file))
        ctx.write_summary("## New Section")
        content = summary_file.read_text()
        assert "## Existing" in content
        assert "## New Section" in content


class TestOutputContextHasMethods:
    """Tests for has_output() and has_summary() methods."""

    @pytest.mark.parametrize(
        "output_path,github_output,env_value,expected",
        [
            ("/explicit/path.txt", False, None, True),
            (None, True, "/env/path.txt", True),
            (None, False, None, False),
            (None, True, None, False),
        ],
        ids=["explicit_path", "github_env", "no_path", "flag_no_env"],
    )
    def test_has_output(
        self,
        output_path: str | None,
        github_output: bool,
        env_value: str | None,
        expected: bool,
    ) -> None:
        """has_output returns True only when output will be written to file."""
        ctx = OutputContext(output_path=output_path, github_output=github_output)
        env = {"GITHUB_OUTPUT": env_value} if env_value else {}
        with mock.patch.dict(os.environ, env, clear=True):
            assert ctx.has_output() is expected

    @pytest.mark.parametrize(
        "summary_path,github_summary,env_value,expected",
        [
            ("/explicit/summary.md", False, None, True),
            (None, True, "/env/summary.md", True),
            (None, False, None, False),
            (None, True, None, False),
        ],
        ids=["explicit_path", "github_env", "no_path", "flag_no_env"],
    )
    def test_has_summary(
        self,
        summary_path: str | None,
        github_summary: bool,
        env_value: str | None,
        expected: bool,
    ) -> None:
        """has_summary returns True only when summary will be written to file."""
        ctx = OutputContext(summary_path=summary_path, github_summary=github_summary)
        env = {"GITHUB_STEP_SUMMARY": env_value} if env_value else {}
        with mock.patch.dict(os.environ, env, clear=True):
            assert ctx.has_summary() is expected


class TestOutputContextPropertyBased:
    """Property-based tests using Hypothesis for invariant verification."""

    @given(
        output_path=st.one_of(st.none(), st.text(min_size=1, max_size=50).map(lambda x: f"/path/{x}")),
        github_output=st.booleans(),
        summary_path=st.one_of(st.none(), st.text(min_size=1, max_size=50).map(lambda x: f"/path/{x}")),
        github_summary=st.booleans(),
    )
    def test_from_args_preserves_values(
        self,
        output_path: str | None,
        github_output: bool,
        summary_path: str | None,
        github_summary: bool,
    ) -> None:
        """Property: from_args preserves all attribute values from namespace."""
        args = argparse.Namespace(
            output=output_path,
            github_output=github_output,
            summary=summary_path,
            github_summary=github_summary,
        )
        ctx = OutputContext.from_args(args)
        assert ctx.output_path == output_path
        assert ctx.github_output == github_output
        assert ctx.summary_path == summary_path
        assert ctx.github_summary == github_summary

    @given(
        keys=st.lists(
            st.text(alphabet=st.characters(whitelist_categories=("L", "N")), min_size=1, max_size=10),
            min_size=0,
            max_size=5,
        ),
        # Use printable ASCII (no control chars like \r\n) - matches real GitHub output values
        values=st.lists(
            st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=0, max_size=20),
            min_size=0,
            max_size=5,
        ),
    )
    def test_write_outputs_preserves_all_keys(self, keys: list[str], values: list[str]) -> None:
        """Property: write_outputs writes all key-value pairs provided."""
        import tempfile

        # Pad values to match keys length
        values = values + [""] * (len(keys) - len(values))
        data = dict(zip(keys[: len(values)], values, strict=False))

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            ctx = OutputContext(output_path=str(output_file))
            ctx.write_outputs(data)
            content = output_file.read_text()
            for key, value in data.items():
                assert f"{key}={value}" in content

    @given(text=st.text(min_size=1, max_size=200))
    def test_write_summary_always_ends_with_newline(self, text: str) -> None:
        """Property: write_summary always ensures content ends with newline."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            summary_file = Path(tmpdir) / "summary.md"
            ctx = OutputContext(summary_path=str(summary_file))
            ctx.write_summary(text)
            content = summary_file.read_text()
            assert content.endswith("\n"), f"Content should end with newline: {repr(content)}"


class TestOutputContextIntegration:
    """Integration tests for OutputContext used in realistic scenarios."""

    def test_typical_cli_usage_pattern(self, tmp_path: Path) -> None:
        """Simulates typical CLI usage: from_args -> write_outputs -> write_summary."""
        output_file = tmp_path / "output.txt"
        summary_file = tmp_path / "summary.md"

        # Simulate argparse namespace from CLI
        args = argparse.Namespace(
            output=str(output_file),
            github_output=False,
            summary=str(summary_file),
            github_summary=False,
        )

        ctx = OutputContext.from_args(args)
        ctx.write_outputs({"tests_passed": "42", "coverage": "85"})
        ctx.write_summary("## Test Results\n\n| Metric | Value |\n|--------|-------|\n| Tests | 42 |")

        # Verify outputs
        output_content = output_file.read_text()
        assert "tests_passed=42" in output_content
        assert "coverage=85" in output_content

        # Verify summary
        summary_content = summary_file.read_text()
        assert "## Test Results" in summary_content
        assert "| Tests | 42 |" in summary_content

    def test_github_actions_environment(self, tmp_path: Path) -> None:
        """Simulates GitHub Actions environment with env vars."""
        github_output = tmp_path / "GITHUB_OUTPUT"
        github_summary = tmp_path / "GITHUB_STEP_SUMMARY"

        args = argparse.Namespace(
            github_output=True,
            github_summary=True,
        )

        ctx = OutputContext.from_args(args)
        env = {
            "GITHUB_OUTPUT": str(github_output),
            "GITHUB_STEP_SUMMARY": str(github_summary),
        }
        with mock.patch.dict(os.environ, env, clear=True):
            ctx.write_outputs({"status": "success"})
            ctx.write_summary("## ✅ All checks passed")

        assert "status=success" in github_output.read_text()
        assert "## ✅ All checks passed" in github_summary.read_text()

    def test_multiple_writes_append_correctly(self, tmp_path: Path) -> None:
        """Multiple write calls append rather than overwrite."""
        output_file = tmp_path / "output.txt"
        summary_file = tmp_path / "summary.md"

        ctx = OutputContext(output_path=str(output_file), summary_path=str(summary_file))

        # First write
        ctx.write_outputs({"step1": "done"})
        ctx.write_summary("## Step 1\nCompleted")

        # Second write
        ctx.write_outputs({"step2": "done"})
        ctx.write_summary("## Step 2\nCompleted")

        output_content = output_file.read_text()
        assert "step1=done" in output_content
        assert "step2=done" in output_content

        summary_content = summary_file.read_text()
        assert "## Step 1" in summary_content
        assert "## Step 2" in summary_content


class TestGitHubContextFromEnv:
    """Tests for GitHubContext.from_env() factory method."""

    def test_reads_all_github_env_vars(self) -> None:
        """from_env reads all GITHUB_* environment variables."""
        env = {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REF_NAME": "main",
            "GITHUB_SHA": "abc123def456",
            "GITHUB_RUN_ID": "12345",
            "GITHUB_RUN_NUMBER": "42",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_WORKSPACE": "/home/runner/work/repo",
            "GITHUB_WORKFLOW_REF": "owner/repo/.github/workflows/ci.yml@refs/heads/main",
            "GITHUB_TOKEN": "ghs_token123",
        }
        ctx = GitHubContext.from_env(env)
        assert ctx.repository == "owner/repo"
        assert ctx.ref == "refs/heads/main"
        assert ctx.ref_name == "main"
        assert ctx.sha == "abc123def456"
        assert ctx.run_id == "12345"
        assert ctx.run_number == "42"
        assert ctx.actor == "testuser"
        assert ctx.event_name == "push"
        assert ctx.workspace == Path("/home/runner/work/repo")
        assert ctx.workflow_ref == "owner/repo/.github/workflows/ci.yml@refs/heads/main"
        assert ctx.token == "ghs_token123"

    def test_handles_missing_env_vars(self) -> None:
        """from_env handles missing environment variables gracefully."""
        ctx = GitHubContext.from_env({})
        assert ctx.repository is None
        assert ctx.sha is None
        assert ctx.run_id is None
        assert ctx.workspace is None
        assert ctx.token is None

    def test_prefers_github_token_over_gh_token(self) -> None:
        """from_env prefers GITHUB_TOKEN over GH_TOKEN when both are set."""
        env = {"GITHUB_TOKEN": "github_token", "GH_TOKEN": "gh_token"}
        ctx = GitHubContext.from_env(env)
        assert ctx.token == "github_token"

    def test_falls_back_to_gh_token(self) -> None:
        """from_env falls back to GH_TOKEN when GITHUB_TOKEN is not set."""
        env = {"GH_TOKEN": "gh_token"}
        ctx = GitHubContext.from_env(env)
        assert ctx.token == "gh_token"

    def test_uses_os_environ_by_default(self) -> None:
        """from_env uses os.environ when no env mapping is provided."""
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "test/repo"}, clear=True):
            ctx = GitHubContext.from_env()
            assert ctx.repository == "test/repo"


class TestGitHubContextProperties:
    """Tests for GitHubContext helper properties."""

    def test_is_ci_true_when_run_id_set(self) -> None:
        """is_ci returns True when run_id is set."""
        ctx = GitHubContext(run_id="12345")
        assert ctx.is_ci is True

    def test_is_ci_false_when_run_id_none(self) -> None:
        """is_ci returns False when run_id is None."""
        ctx = GitHubContext()
        assert ctx.is_ci is False

    def test_owner_repo_splits_correctly(self) -> None:
        """owner_repo returns (owner, repo) tuple."""
        ctx = GitHubContext(repository="myorg/myrepo")
        assert ctx.owner_repo == ("myorg", "myrepo")

    def test_owner_repo_handles_nested_paths(self) -> None:
        """owner_repo handles repositories with slashes in name."""
        ctx = GitHubContext(repository="myorg/my/nested/repo")
        assert ctx.owner_repo == ("myorg", "my/nested/repo")

    def test_owner_repo_none_when_no_repository(self) -> None:
        """owner_repo returns None when repository is not set."""
        ctx = GitHubContext()
        assert ctx.owner_repo is None

    def test_owner_repo_none_when_no_slash(self) -> None:
        """owner_repo returns None when repository has no slash."""
        ctx = GitHubContext(repository="invalid")
        assert ctx.owner_repo is None

    def test_owner_property(self) -> None:
        """owner property extracts repository owner."""
        ctx = GitHubContext(repository="myorg/myrepo")
        assert ctx.owner == "myorg"

    def test_repo_property(self) -> None:
        """repo property extracts repository name."""
        ctx = GitHubContext(repository="myorg/myrepo")
        assert ctx.repo == "myrepo"

    def test_short_sha_truncates(self) -> None:
        """short_sha returns first 7 characters of SHA."""
        ctx = GitHubContext(sha="abc123def456789")
        assert ctx.short_sha == "abc123d"

    def test_short_sha_none_when_no_sha(self) -> None:
        """short_sha returns None when sha is not set."""
        ctx = GitHubContext()
        assert ctx.short_sha is None


class TestGitHubContextWithOutputConfig:
    """Tests for GitHubContext.with_output_config() method."""

    def test_adds_output_config_from_args(self) -> None:
        """with_output_config adds output configuration from args."""
        ctx = GitHubContext(repository="owner/repo", sha="abc123")
        args = argparse.Namespace(
            output="/path/to/output.txt",
            github_output=True,
            summary="/path/to/summary.md",
            github_summary=True,
        )
        new_ctx = ctx.with_output_config(args)
        # Original env vars preserved
        assert new_ctx.repository == "owner/repo"
        assert new_ctx.sha == "abc123"
        # Output config added
        assert new_ctx.output_path == "/path/to/output.txt"
        assert new_ctx.github_output is True
        assert new_ctx.summary_path == "/path/to/summary.md"
        assert new_ctx.github_summary is True

    def test_original_context_unchanged(self) -> None:
        """with_output_config returns new context, original unchanged."""
        ctx = GitHubContext(repository="owner/repo")
        args = argparse.Namespace(output="/path/to/output.txt")
        new_ctx = ctx.with_output_config(args)
        assert ctx.output_path is None
        assert new_ctx.output_path == "/path/to/output.txt"

    def test_explicit_kwargs_override_args(self) -> None:
        """with_output_config explicit kwargs override args values."""
        ctx = GitHubContext()
        args = argparse.Namespace(output="/from/args.txt", github_output=True)
        new_ctx = ctx.with_output_config(args, output_path="/from/kwarg.txt", github_output=False)
        assert new_ctx.output_path == "/from/kwarg.txt"
        assert new_ctx.github_output is False

    def test_kwargs_only_mode(self) -> None:
        """with_output_config works with kwargs only (no args)."""
        ctx = GitHubContext(repository="owner/repo")
        new_ctx = ctx.with_output_config(github_output=True, github_summary=True)
        assert new_ctx.repository == "owner/repo"
        assert new_ctx.github_output is True
        assert new_ctx.github_summary is True


class TestGitHubContextBackwardCompatibility:
    """Tests ensuring OutputContext alias works correctly."""

    def test_output_context_is_github_context(self) -> None:
        """OutputContext is an alias for GitHubContext."""
        assert OutputContext is GitHubContext

    def test_output_context_from_args_works(self) -> None:
        """OutputContext.from_args() works as before."""
        args = argparse.Namespace(output="/path.txt", github_output=True)
        ctx = OutputContext.from_args(args)
        assert isinstance(ctx, GitHubContext)
        assert ctx.output_path == "/path.txt"
