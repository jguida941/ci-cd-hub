"""Cross-root behavior tests for registry diff/sync.

Goal: When --configs-dir points at a different hub root, registry and profiles
should be loaded from that target root (not the current checkout).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml


def test_registry_sync_uses_target_hub_root_for_registry_and_profiles(tmp_path: Path) -> None:
    from cihub.commands.registry_cmd import _cmd_sync

    hub = tmp_path / "external-hub"
    configs_dir = hub / "config" / "repos"
    profiles_dir = hub / "templates" / "profiles"
    configs_dir.mkdir(parents=True)
    profiles_dir.mkdir(parents=True)

    # Create a custom profile in the external hub root.
    (profiles_dir / "custom.yaml").write_text(
        yaml.safe_dump(
            {
                "thresholds": {"coverage_min": 91, "mutation_score_min": 81},
                "repo": {"dispatch_enabled": False},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Create a registry.json in the external hub root referencing that profile.
    (hub / "config").mkdir(exist_ok=True)
    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": "custom"}},
                "repos": {"demo-repo": {"tier": "standard"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Existing repo config starts at defaults (coverage 70) and will be updated to profile values.
    repo_path = configs_dir / "demo-repo.yaml"
    repo_path.write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
                "language": "python",
                "thresholds": {
                    "coverage_min": 70,
                    "mutation_score_min": 70,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Run sync via the command handler to ensure it derives hub root and loads registry correctly.
    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "dry_run": False,
            "yes": True,
        },
    )()
    result = _cmd_sync(args)
    assert result.exit_code == 0

    updated = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    assert updated["repo"]["dispatch_enabled"] is False
    assert updated["thresholds"]["coverage_min"] == 91
    assert updated["thresholds"]["mutation_score_min"] == 81


def test_registry_diff_uses_target_hub_root_for_registry_and_profiles(tmp_path: Path) -> None:
    """Cross-root diff should read registry + profiles from the target hub root."""
    from cihub.commands.registry_cmd import _cmd_diff

    hub = tmp_path / "external-hub"
    configs_dir = hub / "config" / "repos"
    profiles_dir = hub / "templates" / "profiles"
    configs_dir.mkdir(parents=True)
    profiles_dir.mkdir(parents=True)

    (profiles_dir / "custom.yaml").write_text(
        yaml.safe_dump(
            {
                "thresholds": {"coverage_min": 91, "mutation_score_min": 81},
                "repo": {"dispatch_enabled": False},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    (hub / "config").mkdir(exist_ok=True)
    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": "custom"}},
                "repos": {"demo-repo": {"tier": "standard"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    repo_path = configs_dir / "demo-repo.yaml"
    repo_path.write_text(
        yaml.safe_dump(
            {
                "repo": {
                    "owner": "o",
                    "name": "n",
                    "language": "python",
                    "default_branch": "main",
                    "dispatch_enabled": True,
                },
                "language": "python",
                "thresholds": {
                    "coverage_min": 70,
                    "mutation_score_min": 70,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type("Args", (), {"configs_dir": str(configs_dir)})()
    result = _cmd_diff(args)
    assert result.exit_code == 0
    diffs = result.data["diffs"]
    fields = {(d["repo"], d["field"], d["registry_value"]) for d in diffs}
    assert ("demo-repo", "repo.dispatch_enabled", False) in fields
    assert ("demo-repo", "thresholds.coverage_min", 91) in fields
    assert ("demo-repo", "thresholds.mutation_score_min", 81) in fields


def test_registry_diff_errors_when_hub_root_cannot_be_derived(tmp_path: Path) -> None:
    from cihub.commands.registry_cmd import _cmd_diff
    from cihub.exit_codes import EXIT_USAGE

    weird = tmp_path / "weird-layout"
    weird.mkdir(parents=True)

    args = type("Args", (), {"configs_dir": str(weird)})()
    result = _cmd_diff(args)
    assert result.exit_code == EXIT_USAGE
    assert result.suggestions


def test_registry_sync_errors_when_registry_missing_in_target_hub_root(tmp_path: Path) -> None:
    from cihub.commands.registry_cmd import _cmd_sync
    from cihub.exit_codes import EXIT_FAILURE

    hub = tmp_path / "external-hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "dry_run": True,
            "yes": True,
        },
    )()
    result = _cmd_sync(args)
    assert result.exit_code == EXIT_FAILURE
    assert result.suggestions
