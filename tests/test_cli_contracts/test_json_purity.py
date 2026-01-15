"""JSON purity contract tests.

Phase 0.3 in SYSTEM_INTEGRATION_PLAN.md:
- Non-interactive commands must emit a single JSON payload on stdout when --json is used.
- Interactive commands must reject --json with a CommandResult (still JSON output).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _assert_single_json_payload(text: str) -> dict:
    stripped = text.strip()
    # Basic sanity: stdout must be JSON, not mixed with extra prints.
    payload = json.loads(stripped)
    assert isinstance(payload, dict)
    return payload


def test_detect_json_pure(capsys, tmp_path: Path) -> None:
    from cihub.cli import main

    # Make it a predictable Python repo shape
    (tmp_path / "pyproject.toml").write_text('[project]\nname="demo"\nversion="0.1.0"\n', encoding="utf-8")

    code = main(["detect", "--repo", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    assert code == 0
    payload = _assert_single_json_payload(captured.out)
    assert payload.get("command") == "detect"


def test_new_dry_run_json_pure(capsys, tmp_path: Path) -> None:
    from cihub.cli import main

    code = main(
        [
            "new",
            "demo",
            "--owner",
            "o",
            "--language",
            "python",
            "--dry-run",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    payload = _assert_single_json_payload(captured.out)
    assert payload.get("command") == "new"


def test_init_dry_run_json_pure(capsys, tmp_path: Path) -> None:
    from cihub.cli import main

    # Minimal repo to init
    (tmp_path / "pyproject.toml").write_text('[project]\nname="demo"\nversion="0.1.0"\n', encoding="utf-8")

    code = main(["init", "--repo", str(tmp_path), "--dry-run", "--json"])
    captured = capsys.readouterr()
    assert code == 0
    payload = _assert_single_json_payload(captured.out)
    assert payload.get("command") == "init"


def test_setup_rejects_json_cleanly(capsys, tmp_path: Path) -> None:
    from cihub.cli import main

    # Even if wizard deps are not installed, the contract is: setup rejects --json
    code = main(["setup", "--repo", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    assert code != 0
    payload = _assert_single_json_payload(captured.out)
    assert payload.get("command") == "setup"


def _write_min_ci_hub_config(repo_path: Path) -> None:
    """Write a minimal valid .ci-hub.yml for validate/config-outputs tests."""
    (repo_path / ".ci-hub.yml").write_text(
        "\n".join(
            [
                'version: "1.0"',
                "repo:",
                "  owner: o",
                "  name: demo",
                "  language: python",
                "  default_branch: main",
                "language: python",
                "python:",
                '  version: "3.12"',
                "  tools:",
                "    pytest:",
                "      enabled: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "argv,expected_command",
    [
        (["adr", "list", "--json"], "adr list"),
        (["registry", "list", "--json"], "registry list"),
        (["hub-ci", "repo-check", "--path", "<repo>", "--json"], "hub-ci repo-check"),
        (["hub-ci", "source-check", "--path", "<repo>", "--language", "python", "--json"], "hub-ci source-check"),
        (["validate", "--repo", "<repo>", "--json"], "validate"),
        (["config-outputs", "--repo", "<repo>", "--json"], "config-outputs"),
    ],
    ids=["adr-list", "registry-list", "hub-ci-repo-check", "hub-ci-source-check", "validate", "config-outputs"],
)
def test_representative_commands_json_pure(capsys, tmp_path: Path, argv: list[str], expected_command: str) -> None:
    """Representative sample across command groups to prevent JSON regressions."""
    from cihub.cli import main

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "pyproject.toml").write_text('[project]\nname="demo"\nversion="0.1.0"\n', encoding="utf-8")
    (repo_path / "x.py").write_text("print('hi')\n", encoding="utf-8")
    _write_min_ci_hub_config(repo_path)

    resolved = [str(repo_path) if a == "<repo>" else a for a in argv]
    code = main(resolved)
    captured = capsys.readouterr()

    # Success is preferred, but the core contract is JSON purity.
    assert isinstance(code, int)
    payload = _assert_single_json_payload(captured.out)
    assert payload.get("command") == expected_command
