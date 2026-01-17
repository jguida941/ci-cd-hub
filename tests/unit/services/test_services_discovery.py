"""Tests for cihub.services.discovery module."""

# TEST-METRICS:

import json
from pathlib import Path

from cihub.services import DiscoveryFilters, DiscoveryResult, RepoEntry, discover_repositories


class TestRepoEntry:
    """Tests for RepoEntry dataclass."""

    def test_full_property(self):
        """full property returns owner/name."""
        entry = RepoEntry(
            config_basename="test",
            name="my-repo",
            owner="my-org",
            language="python",
            branch="main",
        )
        assert entry.full == "my-org/my-repo"

    def test_to_matrix_entry_flattens_tools(self):
        """to_matrix_entry flattens tools dict."""
        entry = RepoEntry(
            config_basename="test",
            name="repo",
            owner="owner",
            language="java",
            branch="main",
            tools={"run_jacoco": True, "run_spotbugs": False},
            thresholds={"coverage_min": 80},
        )
        matrix = entry.to_matrix_entry()

        assert matrix["run_jacoco"] is True
        assert matrix["run_spotbugs"] is False
        assert matrix["coverage_min"] == 80
        assert matrix["language"] == "java"


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    def test_count_property(self):
        """count returns number of entries."""
        result = DiscoveryResult(
            success=True,
            entries=[
                RepoEntry(
                    config_basename="a",
                    name="a",
                    owner="o",
                    language="python",
                    branch="main",
                ),
                RepoEntry(
                    config_basename="b",
                    name="b",
                    owner="o",
                    language="java",
                    branch="main",
                ),
            ],
        )
        assert result.count == 2

    def test_to_matrix_format(self):
        """to_matrix returns GitHub Actions matrix format."""
        entry = RepoEntry(
            config_basename="test",
            name="repo",
            owner="owner",
            language="python",
            branch="main",
        )
        result = DiscoveryResult(success=True, entries=[entry])
        matrix = result.to_matrix()

        assert "matrix" in matrix
        assert "include" in matrix["matrix"]
        assert matrix["count"] == 1
        assert matrix["matrix"]["include"][0]["name"] == "repo"


class TestDiscoverRepositories:
    """Tests for discover_repositories function."""

    def test_returns_error_when_repos_dir_missing(self, tmp_path: Path):
        """Returns error when config/repos doesn't exist."""
        result = discover_repositories(tmp_path)

        assert result.success is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0]

    def test_discovers_repos_from_config_dir(self, tmp_path: Path):
        """Discovers repos from config/repos/*.yaml."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        # Create a minimal config
        (repos_dir / "test-repo.yaml").write_text(
            """
repo:
  owner: test-owner
  name: test-repo
  language: python
"""
        )

        result = discover_repositories(tmp_path)

        assert result.success is True
        assert result.count == 1
        assert result.entries[0].name == "test-repo"
        assert result.entries[0].owner == "test-owner"
        assert result.entries[0].language == "python"

    def test_discovers_nested_repo_configs(self, tmp_path: Path):
        """Discovers repos from nested config/repos/**.yaml paths."""
        repos_dir = tmp_path / "config" / "repos" / "owner"
        repos_dir.mkdir(parents=True)

        # Create a minimal config in a nested directory.
        (repos_dir / "nested.yaml").write_text("repo:\n  owner: test-owner\n  name: nested\n  language: python\n")

        result = discover_repositories(tmp_path)

        assert result.success is True
        assert result.count == 1
        assert result.entries[0].config_basename == "owner/nested"
        assert result.entries[0].name == "nested"
        assert result.entries[0].owner == "test-owner"

    def test_applies_repo_filter(self, tmp_path: Path):
        """Filters by repo name."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "repo-a.yaml").write_text("repo:\n  owner: o\n  name: repo-a\n  language: python")
        (repos_dir / "repo-b.yaml").write_text("repo:\n  owner: o\n  name: repo-b\n  language: java")

        filters = DiscoveryFilters(repos=["repo-a"])
        result = discover_repositories(tmp_path, filters)

        assert result.count == 1
        assert result.entries[0].name == "repo-a"

    def test_applies_run_group_filter(self, tmp_path: Path):
        """Filters by run_group."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "quick.yaml").write_text(
            "repo:\n  owner: o\n  name: quick\n  language: python\n  run_group: quick"
        )
        (repos_dir / "full.yaml").write_text("repo:\n  owner: o\n  name: full\n  language: python\n  run_group: full")

        filters = DiscoveryFilters(run_groups=["quick"])
        result = discover_repositories(tmp_path, filters)

        assert result.count == 1
        assert result.entries[0].run_group == "quick"

    def test_applies_central_runner_filter(self, tmp_path: Path):
        """Filters by repo.use_central_runner."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "central.yaml").write_text(
            "repo:\n  owner: o\n  name: central\n  language: python\n  use_central_runner: true"
        )
        (repos_dir / "dispatch.yaml").write_text(
            "repo:\n  owner: o\n  name: dispatch\n  language: python\n  use_central_runner: false"
        )

        filters = DiscoveryFilters(use_central_runner=True)
        result = discover_repositories(tmp_path, filters)

        assert result.count == 1
        assert result.entries[0].name == "central"

    def test_warns_on_invalid_config(self, tmp_path: Path):
        """Warns but continues when config is invalid."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        # Invalid config (missing language)
        (repos_dir / "bad.yaml").write_text("repo:\n  owner: o\n  name: bad")
        # Valid config
        (repos_dir / "good.yaml").write_text("repo:\n  owner: o\n  name: good\n  language: python")

        result = discover_repositories(tmp_path)

        assert result.success is True
        assert result.count == 1
        assert result.entries[0].name == "good"
        assert len(result.warnings) >= 1
        assert any("bad" in w for w in result.warnings)

    def test_no_prints_to_stderr(self, tmp_path: Path, capsys):
        """Service captures loader output as warnings, doesn't print."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "test.yaml").write_text("repo:\n  owner: o\n  name: test\n  language: python")

        result = discover_repositories(tmp_path)
        captured = capsys.readouterr()

        assert result.success is True
        assert captured.err == ""  # No stderr output
        assert captured.out == ""  # No stdout output

    def test_validation_errors_preserved_in_warnings(self, tmp_path: Path, capsys):
        """Validation errors with details are preserved in warnings."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        # Provide defaults + schema to trigger validation errors deterministically
        defaults_path = tmp_path / "config" / "defaults.yaml"
        defaults_path.write_text("thresholds: {}\n")

        schema_dir = tmp_path / "schema"
        schema_dir.mkdir()
        schema_path = schema_dir / "ci-hub-config.schema.json"
        schema_path.write_text(
            json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "object",
                            "properties": {"language": {"type": "string"}},
                            "required": ["language"],
                        }
                    },
                    "required": ["repo"],
                }
            )
        )

        # Config with validation error (missing required fields)
        (repos_dir / "invalid.yaml").write_text(
            "repo:\n  owner: o\n  name: invalid"  # Missing language
        )

        result = discover_repositories(tmp_path)
        captured = capsys.readouterr()

        assert result.success is True  # Still succeeds (skips invalid)
        assert result.count == 0
        assert captured.err == ""  # No stderr leakage
        # Error details are in warnings
        assert len(result.warnings) >= 1
        assert any("invalid" in w for w in result.warnings)
        assert any("validation failed" in w for w in result.warnings)
        assert any("required property" in w for w in result.warnings)
