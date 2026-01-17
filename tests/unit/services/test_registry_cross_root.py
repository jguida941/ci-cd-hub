"""Cross-root behavior tests for registry diff/sync.

Goal: When --configs-dir points at a different hub root, registry and profiles
should be loaded from that target root (not the current checkout).
"""

# TEST-METRICS:

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


def test_registry_sync_accepts_config_dir_and_maps_to_repos_dir(tmp_path: Path) -> None:
    """--configs-dir may point to <hub>/config and should map to <hub>/config/repos."""
    from cihub.commands.registry_cmd import _cmd_sync

    hub = tmp_path / "external-hub"
    configs_dir = hub / "config"
    repos_dir = configs_dir / "repos"
    profiles_dir = hub / "templates" / "profiles"
    repos_dir.mkdir(parents=True)
    profiles_dir.mkdir(parents=True)

    (profiles_dir / "custom.yaml").write_text(
        yaml.safe_dump(
            {
                "thresholds": {"coverage_min": 91, "mutation_score_min": 81},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

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

    repo_path = repos_dir / "demo-repo.yaml"
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
    assert updated["thresholds"]["coverage_min"] == 91
    assert updated["thresholds"]["mutation_score_min"] == 81


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


def test_registry_diff_errors_when_registry_missing_in_target_hub_root(tmp_path: Path) -> None:
    from cihub.commands.registry_cmd import _cmd_diff
    from cihub.exit_codes import EXIT_FAILURE

    hub = tmp_path / "external-hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    args = type("Args", (), {"configs_dir": str(configs_dir)})()
    result = _cmd_diff(args)
    assert result.exit_code == EXIT_FAILURE
    assert result.problems
    assert result.problems[0]["code"] == "CIHUB-REGISTRY-NO-REGISTRY-FILE"
    assert result.suggestions


def test_registry_diff_warns_when_repos_root_missing(tmp_path: Path) -> None:
    """--repos-root should warn when path doesn't exist."""
    from cihub.commands.registry_cmd import _cmd_diff

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": None}},
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
                "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
                "language": "python",
                "thresholds": {"coverage_min": 70},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Pass non-existent repos-root
    args = type(
        "Args",
        (),
        {"configs_dir": str(configs_dir), "repos_root": str(tmp_path / "nonexistent")},
    )()
    result = _cmd_diff(args)
    assert result.exit_code == 0  # Still succeeds, just warns
    assert result.problems is not None
    warning_codes = [p["code"] for p in result.problems]
    assert "CIHUB-REGISTRY-REPOS-ROOT-MISSING" in warning_codes


def test_registry_diff_warns_when_repos_root_empty(tmp_path: Path) -> None:
    """--repos-root should warn when no matching repo directories found."""
    from cihub.commands.registry_cmd import _cmd_diff

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    repos_root = tmp_path / "cloned-repos"
    configs_dir.mkdir(parents=True)
    repos_root.mkdir(parents=True)  # Empty directory

    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": None}},
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
                "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
                "language": "python",
                "thresholds": {"coverage_min": 70},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Pass empty repos-root (no demo-repo subdir)
    args = type(
        "Args",
        (),
        {"configs_dir": str(configs_dir), "repos_root": str(repos_root)},
    )()
    result = _cmd_diff(args)
    assert result.exit_code == 0  # Still succeeds, just warns
    assert result.problems is not None
    warning_codes = [p["code"] for p in result.problems]
    assert "CIHUB-REGISTRY-REPOS-ROOT-EMPTY" in warning_codes


def test_registry_bootstrap_imports_config_files(tmp_path: Path) -> None:
    """Bootstrap should import config/repos/*.yaml into registry."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    # Create registry with tiers
    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": None}},
                "repos": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Create config files
    (configs_dir / "repo-a.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "repo-a", "language": "python"},
                "language": "python",
                "thresholds": {"coverage_min": 80},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (configs_dir / "repo-b.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "repo-b", "language": "java"},
                "language": "java",
                "thresholds": {"coverage_min": 90},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",
            "strategy": "merge",
            "dry_run": True,
            "include_thresholds": False,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0
    assert result.data["imported_count"] == 2
    assert "repo-a" in result.data["imported"]
    assert "repo-b" in result.data["imported"]
    assert result.data["dry_run"] is True


def test_registry_bootstrap_with_include_thresholds(tmp_path: Path) -> None:
    """Bootstrap with --include-thresholds should import threshold values."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": None}},
                "repos": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (configs_dir / "repo-a.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "repo-a", "language": "python"},
                "language": "python",
                "thresholds": {"coverage_min": 85, "mutation_score_min": 75},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Run without dry-run to actually save
    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",
            "strategy": "merge",
            "dry_run": False,
            "include_thresholds": True,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0
    assert result.data["imported_count"] == 1

    # Verify registry was updated
    updated_registry = json.loads((hub / "config" / "registry.json").read_text())
    assert "repo-a" in updated_registry["repos"]
    assert updated_registry["repos"]["repo-a"]["overrides"]["coverage_min"] == 85
    assert updated_registry["repos"]["repo-a"]["overrides"]["mutation_score_min"] == 75


def test_registry_bootstrap_prefer_registry_skips_existing(tmp_path: Path) -> None:
    """Bootstrap with prefer-registry should skip repos already in registry."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": None}},
                "repos": {"existing-repo": {"tier": "standard"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (configs_dir / "existing-repo.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "existing-repo", "language": "python"},
                "language": "python",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",
            "strategy": "prefer-registry",
            "dry_run": True,
            "include_thresholds": False,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0
    assert result.data["imported_count"] == 0
    assert result.data["skipped_count"] == 1
    assert result.data["skipped"][0]["reason"] == "already in registry (prefer-registry)"


def test_registry_bootstrap_replace_strategy_replaces_existing(tmp_path: Path) -> None:
    """Bootstrap with replace strategy should completely replace existing entries."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    # Registry has existing repo with "strict" tier and overrides
    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {
                    "strict": {"description": "Strict", "profile": None},
                    "standard": {"description": "Standard", "profile": None},
                },
                "repos": {
                    "existing-repo": {
                        "tier": "strict",
                        "language": "java",
                        "overrides": {"coverage_min": 95},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Config file says python
    (configs_dir / "existing-repo.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "existing-repo", "language": "python"},
                "language": "python",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",  # default tier for import
            "strategy": "replace",
            "dry_run": False,
            "include_thresholds": False,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0
    assert result.data["imported_count"] == 1

    # Verify registry was replaced (tier should be standard, language python, no overrides)
    updated_registry = json.loads((hub / "config" / "registry.json").read_text())
    repo = updated_registry["repos"]["existing-repo"]
    assert repo["tier"] == "standard"  # Replaced with default tier
    assert repo["config"]["repo"]["language"] == "python"  # Replaced from config
    assert "language" not in repo  # Stored in config.repo (canonical)
    assert "overrides" not in repo  # Existing overrides cleared


def test_registry_bootstrap_prefer_config_keeps_tier_replaces_rest(tmp_path: Path) -> None:
    """Bootstrap with prefer-config should keep existing tier but replace other values."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    # Registry has existing repo with "strict" tier
    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {
                    "strict": {"description": "Strict", "profile": None},
                    "standard": {"description": "Standard", "profile": None},
                },
                "repos": {
                    "existing-repo": {
                        "tier": "strict",
                        "language": "java",
                        "overrides": {"coverage_min": 95},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Config file says python with gates
    (configs_dir / "existing-repo.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "existing-repo", "language": "python"},
                "language": "python",
                "gates": {"required": ["lint", "test"]},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",  # This won't be used - existing tier kept
            "strategy": "prefer-config",
            "dry_run": False,
            "include_thresholds": False,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0
    assert result.data["imported_count"] == 1

    # Verify: tier kept, language replaced, gates imported, overrides cleared
    updated_registry = json.loads((hub / "config" / "registry.json").read_text())
    repo = updated_registry["repos"]["existing-repo"]
    assert repo["tier"] == "strict"  # Kept existing tier
    assert repo["config"]["repo"]["language"] == "python"  # Replaced from config
    assert repo["config"]["gates"] == {"required": ["lint", "test"]}  # Imported managed config
    assert "overrides" not in repo  # Old overrides cleared


def test_registry_bootstrap_imports_managed_config_fragments(tmp_path: Path) -> None:
    """Bootstrap should import managed config fragments (gates, reports, etc.)."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": None}},
                "repos": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Config with various managed fragments
    (configs_dir / "repo-with-fragments.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "repo-with-fragments", "language": "python"},
                "gates": {"required": ["lint", "test"], "optional": ["mutation"]},
                "reports": {"enabled": True, "format": "sarif"},
                "notifications": {"slack": {"channel": "#ci"}},
                "harden_runner": {"egress_policy": "audit"},
                "thresholds_profile": "strict",
                "cihub": {"emit_triage": True},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",
            "strategy": "merge",
            "dry_run": False,
            "include_thresholds": False,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0
    assert result.data["imported_count"] == 1

    updated_registry = json.loads((hub / "config" / "registry.json").read_text())
    repo = updated_registry["repos"]["repo-with-fragments"]

    # Verify all managed fragments were imported
    assert repo["config"]["repo"]["language"] == "python"
    assert repo["config"]["gates"] == {"required": ["lint", "test"], "optional": ["mutation"]}
    assert repo["config"]["reports"] == {"enabled": True, "format": "sarif"}
    assert repo["config"]["notifications"] == {"slack": {"channel": "#ci"}}
    assert repo["config"]["harden_runner"] == {"egress_policy": "audit"}
    assert repo["config"]["thresholds_profile"] == "strict"
    assert repo["config"]["cihub"] == {"emit_triage": True}


def test_registry_bootstrap_sparse_thresholds(tmp_path: Path) -> None:
    """Bootstrap with --include-thresholds should only import non-default values."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)
    profiles_dir = hub / "templates" / "profiles"
    profiles_dir.mkdir(parents=True)

    (profiles_dir / "custom.yaml").write_text(
        yaml.safe_dump(
            {
                "thresholds": {"coverage_min": 80, "mutation_score_min": 60},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Tier defaults come from profile (coverage 80, mutation 60).
    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {
                    "standard": {
                        "description": "Standard",
                        "profile": "custom",
                    }
                },
                "repos": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Config has coverage_min=80 (matches tier) and mutation_score_min=75 (differs)
    (configs_dir / "repo-a.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "repo-a", "language": "python"},
                "language": "python",
                "thresholds": {"coverage_min": 80, "mutation_score_min": 75},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",
            "strategy": "merge",
            "dry_run": False,
            "include_thresholds": True,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0

    updated_registry = json.loads((hub / "config" / "registry.json").read_text())
    repo = updated_registry["repos"]["repo-a"]

    # Only mutation_score_min should be in overrides (coverage_min matches tier default)
    assert "overrides" in repo
    assert "coverage_min" not in repo["overrides"]  # Matches tier default, not stored
    assert repo["overrides"]["mutation_score_min"] == 75  # Differs from tier default


def test_registry_bootstrap_merge_detects_language_conflict(tmp_path: Path) -> None:
    """Bootstrap merge should detect language conflicts."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": None}},
                "repos": {"existing-repo": {"tier": "standard", "language": "java"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Config says python
    (configs_dir / "existing-repo.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "existing-repo", "language": "python"},
                "language": "python",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",
            "strategy": "merge",
            "dry_run": True,
            "include_thresholds": False,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0
    assert result.data["conflicts_count"] >= 1

    # Find language conflict
    lang_conflict = None
    for c in result.data["conflicts"]:
        if c["field"] == "language":
            lang_conflict = c
            break

    assert lang_conflict is not None
    assert lang_conflict["registry_value"] == "java"
    assert lang_conflict["config_value"] == "python"


def test_registry_bootstrap_merge_detects_config_fragment_conflict(tmp_path: Path) -> None:
    """Bootstrap merge should detect conflicts in managed config fragments."""
    from cihub.commands.registry_cmd import _cmd_bootstrap

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)

    (hub / "config" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {"standard": {"description": "Standard", "profile": None}},
                "repos": {
                    "existing-repo": {
                        "tier": "standard",
                        "config": {"gates": {"required": ["lint"]}},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (configs_dir / "existing-repo.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "existing-repo", "language": "python"},
                "language": "python",
                "gates": {"required": ["lint", "test"]},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "configs_dir": str(configs_dir),
            "tier": "standard",
            "strategy": "merge",
            "dry_run": True,
            "include_thresholds": False,
        },
    )()
    result = _cmd_bootstrap(args)

    assert result.exit_code == 0
    fields = {c["field"] for c in result.data["conflicts"]}
    assert "config.gates.required" in fields
