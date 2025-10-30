from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
import yaml

import scripts.enforce_concurrency_budget as budget


def _write_config(tmp_path: Path, workflows: dict[str, Any]) -> Path:
    config = {
        "version": 1,
        "defaults": {
            "require_cancel_in_progress": True,
            "allowed_runners": ["ubuntu-22.04"],
        },
        "workflows": workflows,
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "jguida941/ci-cd-hub")
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_RUN_ID", "100")


def test_budget_skip_when_not_defined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    config_path = _write_config(tmp_path, {})
    exit_code = budget.main(
        [
            "--workflow",
            "release.yml",
            "--config",
            str(config_path),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "no budget defined" in captured.out


def test_budget_allows_within_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    config_path = _write_config(tmp_path, {"release.yml": {"max_in_progress": 2}})

    def fake_list(*_args, **_kwargs):
        return [{"id": 90}, {"id": 100}]  # one other run plus current

    monkeypatch.setattr(budget, "_list_in_progress_runs", fake_list)
    exit_code = budget.main(
        [
            "--workflow",
            "release.yml",
            "--config",
            str(config_path),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "currently has 1 other in-progress runs" in captured.out


def test_budget_blocks_overage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = _write_config(tmp_path, {"release.yml": {"max_in_progress": 1}})

    def fake_list(*_args, **_kwargs):
        return [{"id": 90}, {"id": 91}]  # two other runs

    monkeypatch.setattr(budget, "_list_in_progress_runs", fake_list)
    with pytest.raises(SystemExit, match="already has 2 runs in progress"):
        budget.main(
            [
                "--workflow",
                "release.yml",
                "--config",
                str(config_path),
            ]
        )
