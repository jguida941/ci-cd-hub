"""Tests for cihub.services.repo_config module."""

# TEST-METRICS:
#   Coverage: 89.5%

from __future__ import annotations

from pathlib import Path

from cihub.services import repo_config


class TestGetConnectedRepos:
    """Tests for get_connected_repos function."""

    def test_returns_repos_with_dispatch_enabled(self, tmp_path: Path, monkeypatch: object) -> None:
        """Returns repos where dispatch_enabled is True or not set."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "repo1.yaml").write_text("repo:\n  owner: org1\n  name: repo1\n  dispatch_enabled: true\n")
        (repos_dir / "repo2.yaml").write_text("repo:\n  owner: org2\n  name: repo2\n")
        (repos_dir / "repo3.yaml").write_text("repo:\n  owner: org3\n  name: repo3\n  dispatch_enabled: false\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        repos = repo_config.get_connected_repos(only_dispatch_enabled=True)
        assert "org1/repo1" in repos
        assert "org2/repo2" in repos
        assert "org3/repo3" not in repos

    def test_returns_all_repos_when_dispatch_disabled_filter_off(self, tmp_path: Path, monkeypatch: object) -> None:
        """Returns all repos when only_dispatch_enabled=False."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "repo1.yaml").write_text("repo:\n  owner: org1\n  name: repo1\n  dispatch_enabled: false\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        repos = repo_config.get_connected_repos(only_dispatch_enabled=False)
        assert "org1/repo1" in repos

    def test_filters_by_language(self, tmp_path: Path, monkeypatch: object) -> None:
        """Filters repos by language."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "py.yaml").write_text("repo:\n  owner: org\n  name: py-repo\n  language: python\n")
        (repos_dir / "java.yaml").write_text("repo:\n  owner: org\n  name: java-repo\n  language: java\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        repos = repo_config.get_connected_repos(only_dispatch_enabled=False, language_filter="python")
        assert "org/py-repo" in repos
        assert "org/java-repo" not in repos

    def test_skips_disabled_files(self, tmp_path: Path, monkeypatch: object) -> None:
        """Skips files ending in .disabled."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "repo1.yaml.disabled").write_text("repo:\n  owner: org\n  name: disabled\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        repos = repo_config.get_connected_repos(only_dispatch_enabled=False)
        assert "org/disabled" not in repos

    def test_handles_malformed_yaml(self, tmp_path: Path, monkeypatch: object, capsys: object) -> None:
        """Handles malformed YAML gracefully."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "bad.yaml").write_text("invalid: yaml: :\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        repos = repo_config.get_connected_repos(only_dispatch_enabled=False)
        assert repos == []
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "Warning" in captured.err

    def test_deduplicates_repos(self, tmp_path: Path, monkeypatch: object) -> None:
        """Deduplicates repos by full name."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "repo1.yaml").write_text("repo:\n  owner: org\n  name: repo\n")
        (repos_dir / "repo2.yaml").write_text("repo:\n  owner: org\n  name: repo\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        repos = repo_config.get_connected_repos(only_dispatch_enabled=False)
        assert repos.count("org/repo") == 1


class TestGetRepoEntries:
    """Tests for get_repo_entries function."""

    def test_returns_repo_entries(self, tmp_path: Path, monkeypatch: object) -> None:
        """Returns repo metadata entries."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "repo.yaml").write_text(
            "repo:\n  owner: org\n  name: myrepo\n  language: python\n"
            "  default_branch: develop\n  dispatch_workflow: custom.yml\n"
        )

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        entries = repo_config.get_repo_entries(only_dispatch_enabled=False)
        assert len(entries) == 1
        assert entries[0]["full"] == "org/myrepo"
        assert entries[0]["language"] == "python"
        assert entries[0]["default_branch"] == "develop"
        assert entries[0]["dispatch_workflow"] == "custom.yml"

    def test_uses_default_values(self, tmp_path: Path, monkeypatch: object) -> None:
        """Uses default values for missing fields."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "repo.yaml").write_text("repo:\n  owner: org\n  name: repo\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        entries = repo_config.get_repo_entries(only_dispatch_enabled=False)
        assert entries[0]["dispatch_workflow"] == "hub-ci.yml"
        assert entries[0]["default_branch"] == "main"
        assert entries[0]["language"] == ""

    def test_skips_repos_without_owner_or_name(self, tmp_path: Path, monkeypatch: object) -> None:
        """Skips repos missing owner or name."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "noowner.yaml").write_text("repo:\n  name: repo\n")
        (repos_dir / "noname.yaml").write_text("repo:\n  owner: org\n")
        (repos_dir / "valid.yaml").write_text("repo:\n  owner: org\n  name: repo\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        entries = repo_config.get_repo_entries(only_dispatch_enabled=False)
        assert len(entries) == 1
        assert entries[0]["full"] == "org/repo"

    def test_deduplicates_by_repo_and_workflow(self, tmp_path: Path, monkeypatch: object) -> None:
        """Deduplicates by repo + dispatch_workflow combination."""
        repos_dir = tmp_path / "config" / "repos"
        repos_dir.mkdir(parents=True)

        (repos_dir / "a.yaml").write_text("repo:\n  owner: org\n  name: repo\n  dispatch_workflow: a.yml\n")
        (repos_dir / "b.yaml").write_text("repo:\n  owner: org\n  name: repo\n  dispatch_workflow: b.yml\n")
        (repos_dir / "c.yaml").write_text("repo:\n  owner: org\n  name: repo\n  dispatch_workflow: a.yml\n")

        monkeypatch.setattr(repo_config, "hub_root", lambda: tmp_path)  # type: ignore[attr-defined]
        entries = repo_config.get_repo_entries(only_dispatch_enabled=False)
        # Should have 2 entries: one for a.yml, one for b.yml
        assert len(entries) == 2
