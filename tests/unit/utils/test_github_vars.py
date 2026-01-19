"""Tests for GitHub repo variable helpers."""

from unittest import mock

from cihub.utils import github as github_utils


def test_set_repo_variables_requires_repo() -> None:
    ok, _messages, problems = github_utils.set_repo_variables("", {"HUB_REPO": "owner/repo"})
    assert not ok
    assert any(p.get("code") == "CIHUB-HUB-VARS-NO-REPO" for p in problems)


def test_set_repo_variables_auth_failure(monkeypatch) -> None:
    monkeypatch.setattr(github_utils, "check_gh_auth", lambda: (False, "no auth"))
    ok, _messages, problems = github_utils.set_repo_variables("owner/repo", {"HUB_REPO": "owner/repo"})
    assert not ok
    assert any(p.get("code") == "CIHUB-HUB-VARS-NO-GH" for p in problems)


def test_set_repo_variables_success(monkeypatch) -> None:
    monkeypatch.setattr(github_utils, "check_gh_auth", lambda: (True, ""))
    mock_proc = mock.Mock(returncode=0, stderr="")
    monkeypatch.setattr(github_utils, "safe_run", lambda *args, **kwargs: mock_proc)
    ok, messages, problems = github_utils.set_repo_variables(
        "owner/repo",
        {"HUB_REPO": "owner/repo", "HUB_REF": "v1"},
    )
    assert ok
    assert len(messages) == 2
    assert problems == []
