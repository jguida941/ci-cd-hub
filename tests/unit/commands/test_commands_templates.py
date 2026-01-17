"""Tests for cihub.commands.templates module.

All command functions now return CommandResult (never int).
Tests check result.exit_code and result.data["items"] instead of
comparing result to int or checking capsys output.
"""

from __future__ import annotations

# isort: skip_file

import argparse
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE  # noqa: E402
from cihub.types import CommandResult  # noqa: E402
from cihub.commands.templates import cmd_sync_templates  # noqa: E402


# =============================================================================
# Helper Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def mock_gh_token(monkeypatch: pytest.MonkeyPatch):
    """Set GH_TOKEN for all tests so sync-templates proceeds past token check."""
    monkeypatch.setenv("GH_TOKEN", "test-token-for-mocked-api")
    yield


def make_repo_entry(
    *,
    full: str = "owner/repo",
    language: str = "python",
    dispatch_workflow: str = "hub-ci.yml",
    default_branch: str = "main",
) -> dict[str, str]:
    """Build a repo entry dict for template sync tests."""
    return {
        "full": full,
        "language": language,
        "dispatch_workflow": dispatch_workflow,
        "default_branch": default_branch,
    }


@pytest.fixture
def base_args() -> argparse.Namespace:
    """Create base arguments for cmd_sync_templates."""
    return argparse.Namespace(
        repo=None,
        include_disabled=False,
        check=False,
        dry_run=False,
        commit_message="Update workflow templates",
        update_tag=False,
        yes=False,
        json=False,
    )


# =============================================================================
# No Repos Tests
# =============================================================================


class TestSyncTemplatesNoRepos:
    """Tests for cmd_sync_templates when no repos found."""

    def test_no_repos_returns_success(self, base_args: argparse.Namespace) -> None:
        """Returns CommandResult with exit_code 0 when no repos to sync."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = []

            result = cmd_sync_templates(base_args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == EXIT_SUCCESS
            assert "No repos" in result.summary

    def test_no_repos_json_mode(self, base_args: argparse.Namespace) -> None:
        """Returns CommandResult when no repos in JSON mode."""
        base_args.json = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = []

            result = cmd_sync_templates(base_args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == EXIT_SUCCESS
            assert "No repos" in result.summary


# =============================================================================
# No Token Tests (skip gracefully in check/dry-run mode)
# =============================================================================


class TestSyncTemplatesNoToken:
    """Tests for cmd_sync_templates when no token is available."""

    def test_check_mode_skips_without_token(
        self, base_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns CommandResult with exit_code 0 (skip) when --check and no token."""
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("HUB_DISPATCH_TOKEN", raising=False)
        base_args.check = True

        result = cmd_sync_templates(base_args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data.get("skipped") is True
        assert "Missing GitHub token" in result.summary

    def test_dry_run_skips_without_token(self, base_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns CommandResult with exit_code 0 (skip) when --dry-run and no token."""
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("HUB_DISPATCH_TOKEN", raising=False)
        base_args.dry_run = True

        result = cmd_sync_templates(base_args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data.get("skipped") is True

    def test_check_mode_json_skips_without_token(
        self, base_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns CommandResult with skipped=True in JSON mode."""
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("HUB_DISPATCH_TOKEN", raising=False)
        base_args.check = True
        base_args.json = True

        result = cmd_sync_templates(base_args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data.get("skipped") is True
        assert result.data.get("reason") == "no_token"

    def test_actual_sync_fails_without_token(
        self, base_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns EXIT_USAGE when actual sync (not check/dry-run) and no token."""
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("HUB_DISPATCH_TOKEN", raising=False)
        # base_args has check=False, dry_run=False by default

        result = cmd_sync_templates(base_args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_USAGE
        assert "Missing GitHub token" in result.summary


# =============================================================================
# Repo Not Found Tests
# =============================================================================


class TestSyncTemplatesRepoNotFound:
    """Tests for cmd_sync_templates when specified repo not found."""

    def test_repo_not_found_returns_error(self, base_args: argparse.Namespace) -> None:
        """Returns EXIT_USAGE when specified repo not in config."""
        base_args.repo = ["owner/nonexistent"]

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [{"full": "owner/existing", "language": "python"}]

            result = cmd_sync_templates(base_args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == EXIT_USAGE
            assert "not found" in result.summary.lower()

    def test_repo_not_found_json_mode(self, base_args: argparse.Namespace) -> None:
        """Returns CommandResult when repo not found in JSON mode."""
        base_args.repo = ["owner/nonexistent"]
        base_args.json = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [{"full": "owner/existing", "language": "python"}]

            result = cmd_sync_templates(base_args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == EXIT_USAGE


# =============================================================================
# Workflow Rendering Error Tests
# =============================================================================


class TestSyncTemplatesRenderError:
    """Tests for cmd_sync_templates when workflow rendering fails."""

    def test_render_error_continues(self, base_args: argparse.Namespace) -> None:
        """Continues processing other repos when one fails to render."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(full="owner/repo1", language="invalid"),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.side_effect = ValueError("Unsupported language")

                result = cmd_sync_templates(base_args)
                assert isinstance(result, CommandResult)
                assert result.exit_code == EXIT_FAILURE
                # Check that error message is in items
                items = result.data.get("items", [])
                assert any("ERROR" in item for item in items)


# =============================================================================
# Up-to-Date Tests
# =============================================================================


class TestSyncTemplatesUpToDate:
    """Tests for cmd_sync_templates when workflows are up to date."""

    def test_up_to_date_returns_success(self, base_args: argparse.Namespace) -> None:
        """Returns success when workflow is up to date."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI\n",
                        "sha": "abc123",
                    }

                    result = cmd_sync_templates(base_args)
                    assert isinstance(result, CommandResult)
                    assert result.exit_code == EXIT_SUCCESS
                    # Check that success message is in items
                    items = result.data.get("items", [])
                    assert any("[OK]" in item and "up to date" in item for item in items)


# =============================================================================
# Check Mode Tests
# =============================================================================


class TestSyncTemplatesCheckMode:
    """Tests for cmd_sync_templates in check mode."""

    def test_check_mode_out_of_date_fails(self, base_args: argparse.Namespace) -> None:
        """Check mode returns failure when workflow is out of date."""
        base_args.check = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI v2\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI v1\n",
                        "sha": "abc123",
                    }

                    result = cmd_sync_templates(base_args)
                    assert isinstance(result, CommandResult)
                    assert result.exit_code == EXIT_FAILURE
                    # Check that failure message is in items
                    items = result.data.get("items", [])
                    assert any("[FAIL]" in item and "out of date" in item for item in items)

    def test_check_mode_stale_workflow_fails(self, base_args: argparse.Namespace) -> None:
        """Check mode returns failure when stale workflow exists."""
        base_args.check = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    # First call for hub-ci.yml (up to date)
                    # Second+ calls for stale workflows
                    def fetch_side_effect(repo, path, branch):
                        if "hub-ci.yml" in path:
                            return {"content": "name: CI\n", "sha": "abc123"}
                        elif "hub-java-ci.yml" in path:
                            return {"content": "stale\n", "sha": "stale123"}
                        return None

                    mock_fetch.side_effect = fetch_side_effect

                    result = cmd_sync_templates(base_args)
                    assert isinstance(result, CommandResult)
                    assert result.exit_code == EXIT_FAILURE
                    # Check that stale message is in items
                    items = result.data.get("items", [])
                    assert any("stale" in item.lower() for item in items)


# =============================================================================
# Dry Run Tests
# =============================================================================


class TestSyncTemplatesDryRun:
    """Tests for cmd_sync_templates in dry run mode."""

    def test_dry_run_does_not_update(self, base_args: argparse.Namespace) -> None:
        """Dry run shows what would be updated without actually updating."""
        base_args.dry_run = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI v2\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI v1\n",
                        "sha": "abc123",
                    }

                    with mock.patch("cihub.commands.templates.update_remote_file") as mock_update:
                        result = cmd_sync_templates(base_args)
                        assert isinstance(result, CommandResult)
                        assert result.exit_code == EXIT_SUCCESS
                        # Check that "Would update" message is in items
                        items = result.data.get("items", [])
                        assert any("Would update" in item for item in items)
                        # Should NOT actually call update
                        mock_update.assert_not_called()


# =============================================================================
# Update Tests
# =============================================================================


class TestSyncTemplatesUpdate:
    """Tests for cmd_sync_templates update functionality."""

    def test_update_success(self, base_args: argparse.Namespace) -> None:
        """Successfully updates out-of-date workflow."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI v2\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI v1\n",
                        "sha": "abc123",
                    }

                    with mock.patch("cihub.commands.templates.update_remote_file") as mock_update:
                        result = cmd_sync_templates(base_args)
                        assert isinstance(result, CommandResult)
                        assert result.exit_code == EXIT_SUCCESS
                        # Check that success message is in items
                        items = result.data.get("items", [])
                        assert any("[OK]" in item and "updated" in item for item in items)
                        mock_update.assert_called_once()

    def test_update_failure(self, base_args: argparse.Namespace) -> None:
        """Handles update failure gracefully."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI v2\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI v1\n",
                        "sha": "abc123",
                    }

                    with mock.patch("cihub.commands.templates.update_remote_file") as mock_update:
                        mock_update.side_effect = RuntimeError("API error")

                        result = cmd_sync_templates(base_args)
                        assert isinstance(result, CommandResult)
                        assert result.exit_code == EXIT_FAILURE
                        # Check that failure message is in items
                        items = result.data.get("items", [])
                        assert any("[FAIL]" in item and "failed" in item for item in items)


# =============================================================================
# Stale Workflow Cleanup Tests
# =============================================================================


class TestSyncTemplatesStaleCleanup:
    """Tests for stale workflow cleanup."""

    def test_deletes_stale_workflows(self, base_args: argparse.Namespace) -> None:
        """Deletes stale workflows after successful sync."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:

                    def fetch_side_effect(repo, path, branch):
                        if "hub-ci.yml" in path:
                            return {"content": "name: CI\n", "sha": "abc123"}
                        elif "hub-java-ci.yml" in path:
                            return {"content": "stale\n", "sha": "stale123"}
                        return None

                    mock_fetch.side_effect = fetch_side_effect

                    with mock.patch("cihub.commands.templates.delete_remote_file") as mock_delete:
                        result = cmd_sync_templates(base_args)
                        assert isinstance(result, CommandResult)
                        assert result.exit_code == EXIT_SUCCESS
                        # Check that delete message is in items
                        items = result.data.get("items", [])
                        assert any("deleted" in item.lower() for item in items) or any("[OK]" in item for item in items)
                        mock_delete.assert_called()

    def test_stale_delete_failure(self, base_args: argparse.Namespace) -> None:
        """Handles stale workflow deletion failure gracefully."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:

                    def fetch_side_effect(repo, path, branch):
                        if "hub-ci.yml" in path:
                            return {"content": "name: CI\n", "sha": "abc123"}
                        elif "hub-java-ci.yml" in path:
                            return {"content": "stale\n", "sha": "stale123"}
                        return None

                    mock_fetch.side_effect = fetch_side_effect

                    with mock.patch("cihub.commands.templates.delete_remote_file") as mock_delete:
                        mock_delete.side_effect = RuntimeError("Delete failed")

                        result = cmd_sync_templates(base_args)
                        # Should still succeed (deletion failure is a warning)
                        assert isinstance(result, CommandResult)
                        # Check that warning is in items
                        items = result.data.get("items", [])
                        assert any("delete failed" in item.lower() or "[WARN]" in item for item in items)


# =============================================================================
# JSON Mode Tests
# =============================================================================


class TestSyncTemplatesJsonMode:
    """Tests for cmd_sync_templates JSON output mode."""

    def test_json_mode_success(self, base_args: argparse.Namespace) -> None:
        """JSON mode returns proper CommandResult on success."""
        base_args.json = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = [
                make_repo_entry(),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI\n",
                        "sha": "abc123",
                    }

                    result = cmd_sync_templates(base_args)
                    assert isinstance(result, CommandResult)
                    assert result.exit_code == EXIT_SUCCESS
                    assert "complete" in result.summary.lower()
                    assert "repos" in result.data
                    assert result.data["failures"] == 0

    def test_json_mode_failure(self, base_args: argparse.Namespace) -> None:
        """JSON mode returns proper CommandResult on failure."""
        base_args.json = True
        base_args.check = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            # Use custom dispatch_workflow to avoid stale workflow checks
            mock_get_entries.return_value = [
                make_repo_entry(dispatch_workflow="custom-ci.yml"),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI v2\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI v1\n",
                        "sha": "abc123",
                    }

                    result = cmd_sync_templates(base_args)
                    assert isinstance(result, CommandResult)
                    assert result.exit_code == EXIT_FAILURE
                    assert result.data["failures"] == 1


# =============================================================================
# Tag Update Tests
# =============================================================================


class TestSyncTemplatesTagUpdate:
    """Tests for v1 tag update functionality."""

    def test_tag_update_dry_run(self, base_args: argparse.Namespace) -> None:
        """Dry run shows tag update would happen."""
        base_args.update_tag = True
        base_args.dry_run = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            # Need at least one repo so function doesn't return early
            mock_get_entries.return_value = [
                make_repo_entry(dispatch_workflow="custom-ci.yml"),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    # Workflow is up to date
                    mock_fetch.return_value = {
                        "content": "name: CI\n",
                        "sha": "abc123",
                    }

                    result = cmd_sync_templates(base_args)
                    assert isinstance(result, CommandResult)
                    assert result.exit_code == EXIT_SUCCESS
                    # Check that "Would update v1 tag" message is in items
                    items = result.data.get("items", [])
                    assert any("Would update v1 tag" in item for item in items)

    def test_tag_update_requires_confirmation(self, base_args: argparse.Namespace) -> None:
        """Tag update without --yes in JSON mode returns error."""
        base_args.update_tag = True
        base_args.json = True
        base_args.yes = False

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            # Need at least one repo so function doesn't return early
            mock_get_entries.return_value = [
                make_repo_entry(dispatch_workflow="custom-ci.yml"),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI\n",
                        "sha": "abc123",
                    }

                    with mock.patch("cihub.commands.templates.resolve_executable") as mock_exec:
                        mock_exec.return_value = "/usr/bin/git"

                        with mock.patch("subprocess.run") as mock_run:
                            # HEAD and v1 return different SHAs (triggers confirmation)
                            mock_run.side_effect = [
                                mock.Mock(stdout="head123\n", returncode=0),  # HEAD
                                mock.Mock(stdout="v1old\n", returncode=0),  # v1
                            ]

                            result = cmd_sync_templates(base_args)
                            assert isinstance(result, CommandResult)
                            assert result.exit_code == EXIT_USAGE
                            assert "confirmation" in result.summary.lower() or "--yes" in result.summary

    def test_tag_already_at_head(self, base_args: argparse.Namespace) -> None:
        """Tag update skipped when already at HEAD."""
        base_args.update_tag = True
        base_args.yes = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            # Need at least one repo so function doesn't return early
            mock_get_entries.return_value = [
                make_repo_entry(dispatch_workflow="custom-ci.yml"),
            ]

            with mock.patch("cihub.commands.templates.render_dispatch_workflow") as mock_render:
                mock_render.return_value = "name: CI\n"

                with mock.patch("cihub.commands.templates.fetch_remote_file") as mock_fetch:
                    mock_fetch.return_value = {
                        "content": "name: CI\n",
                        "sha": "abc123",
                    }

                    with mock.patch("cihub.commands.templates.resolve_executable") as mock_exec:
                        mock_exec.return_value = "/usr/bin/git"

                        with mock.patch("subprocess.run") as mock_run:
                            # Both HEAD and v1 return same SHA
                            mock_run.return_value = mock.Mock(stdout="abc123\n", returncode=0)

                            result = cmd_sync_templates(base_args)
                            assert isinstance(result, CommandResult)
                            assert result.exit_code == EXIT_SUCCESS
                            # Check that "already at HEAD" message is in items
                            items = result.data.get("items", [])
                            assert any("already at HEAD" in item for item in items)


# =============================================================================
# Include Disabled Tests
# =============================================================================


class TestSyncTemplatesIncludeDisabled:
    """Tests for --include-disabled flag."""

    def test_include_disabled_flag(self, base_args: argparse.Namespace) -> None:
        """Include disabled flag passes to get_repo_entries."""
        base_args.include_disabled = True

        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = []

            cmd_sync_templates(base_args)
            mock_get_entries.assert_called_once_with(only_dispatch_enabled=False)

    def test_exclude_disabled_by_default(self, base_args: argparse.Namespace) -> None:
        """Disabled repos excluded by default."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as mock_get_entries:
            mock_get_entries.return_value = []

            cmd_sync_templates(base_args)
            mock_get_entries.assert_called_once_with(only_dispatch_enabled=True)
