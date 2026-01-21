"""Tests for CI output mirroring to GITHUB_WORKSPACE."""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path

from cihub.services.ci_engine import _mirror_output_dir_to_workspace


def test_mirror_output_dir_to_workspace_copies(tmp_path: Path) -> None:
    output_dir = tmp_path / "repo" / ".cihub"
    output_dir.mkdir(parents=True)
    (output_dir / "report.json").write_text("{}", encoding="utf-8")

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    problems: list[dict[str, str]] = []

    mirror = _mirror_output_dir_to_workspace(
        output_dir,
        {"GITHUB_WORKSPACE": str(workspace)},
        problems,
    )

    assert mirror == workspace / ".cihub"
    assert (mirror / "report.json").exists()
    assert problems == []


def test_mirror_output_dir_to_workspace_noop_when_inside(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    output_dir = workspace / ".cihub"
    output_dir.mkdir(parents=True)
    problems: list[dict[str, str]] = []

    mirror = _mirror_output_dir_to_workspace(
        output_dir,
        {"GITHUB_WORKSPACE": str(workspace)},
        problems,
    )

    assert mirror is None
    assert problems == []
