"""Round-trip invariant tests for registry -> config/repos -> load_config.

These tests validate Phase 2 direction: registry-managed config fragments should
sync into hub repo configs such that the merged effective config (via load_config)
reflects the registry intent.
"""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path

import yaml

from cihub.utils.paths import hub_root


def test_registry_sync_roundtrip_applies_repo_dispatch_enabled(tmp_path: Path) -> None:
    """Registry tier config fragment should impact effective config after sync."""
    from cihub.config.loader.core import load_config
    from cihub.services.registry_service import compute_diff, load_registry, sync_to_configs

    repo_name = "demo-repo"

    # Create an isolated hub root on disk for load_config().
    hub_root_path = tmp_path / "hub"
    (hub_root_path / "config" / "repos").mkdir(parents=True)
    (hub_root_path / "schema").mkdir(parents=True)

    # Copy real defaults + schema into the isolated hub root.
    data_root = hub_root()
    (hub_root_path / "config" / "defaults.yaml").write_text(
        (data_root / "config" / "defaults.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (hub_root_path / "schema" / "ci-hub-config.schema.json").write_text(
        (data_root / "schema" / "ci-hub-config.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    # Minimal repo override config.
    repo_override_path = hub_root_path / "config" / "repos" / f"{repo_name}.yaml"
    repo_override_path.write_text(
        yaml.safe_dump(
            {
                "repo": {
                    "owner": "o",
                    "name": "n",
                    "language": "python",
                    "default_branch": "main",
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

    # Registry sets dispatch_enabled=False at tier level (non-default vs defaults.yaml).
    registry = load_registry(registry_path=None)
    registry["tiers"] = {
        "standard": {
            "description": "Standard",
            "profile": None,
            "config": {"repo": {"dispatch_enabled": False}},
        }
    }
    registry["repos"] = {repo_name: {"tier": "standard"}}

    configs_dir = hub_root_path / "config" / "repos"
    sync_to_configs(registry, configs_dir, dry_run=False, hub_root_path=hub_root_path)

    cfg = load_config(repo_name=repo_name, hub_root=hub_root_path, exit_on_validation_error=False)
    assert cfg["repo"]["dispatch_enabled"] is False
    assert compute_diff(registry, configs_dir, hub_root_path=hub_root_path) == []


def test_registry_sync_roundtrip_applies_repo_tool_config(tmp_path: Path) -> None:
    """Registry repo config fragment should impact effective tool config after sync."""
    from cihub.config.loader.core import load_config
    from cihub.services.registry_service import compute_diff, load_registry, sync_to_configs

    repo_name = "demo-repo"

    hub_root_path = tmp_path / "hub"
    (hub_root_path / "config" / "repos").mkdir(parents=True)
    (hub_root_path / "schema").mkdir(parents=True)

    data_root = hub_root()
    (hub_root_path / "config" / "defaults.yaml").write_text(
        (data_root / "config" / "defaults.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (hub_root_path / "schema" / "ci-hub-config.schema.json").write_text(
        (data_root / "schema" / "ci-hub-config.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    repo_override_path = hub_root_path / "config" / "repos" / f"{repo_name}.yaml"
    repo_override_path.write_text(
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

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "config": {"python": {"tools": {"mypy": {"enabled": True}}}},
        }
    }

    configs_dir = hub_root_path / "config" / "repos"
    sync_to_configs(registry, configs_dir, dry_run=False, hub_root_path=hub_root_path)

    cfg = load_config(repo_name=repo_name, hub_root=hub_root_path, exit_on_validation_error=False)
    assert cfg["python"]["tools"]["mypy"]["enabled"] is True
    assert compute_diff(registry, configs_dir, hub_root_path=hub_root_path) == []


def test_registry_sync_roundtrip_applies_reports_and_gates(tmp_path: Path) -> None:
    """Registry tier config fragment should impact non-tool settings after sync."""
    from cihub.config.loader.core import load_config
    from cihub.services.registry_service import compute_diff, load_registry, sync_to_configs

    repo_name = "demo-repo"

    hub_root_path = tmp_path / "hub"
    (hub_root_path / "config" / "repos").mkdir(parents=True)
    (hub_root_path / "schema").mkdir(parents=True)

    data_root = hub_root()
    (hub_root_path / "config" / "defaults.yaml").write_text(
        (data_root / "config" / "defaults.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (hub_root_path / "schema" / "ci-hub-config.schema.json").write_text(
        (data_root / "schema" / "ci-hub-config.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    repo_override_path = hub_root_path / "config" / "repos" / f"{repo_name}.yaml"
    repo_override_path.write_text(
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

    registry = load_registry(registry_path=None)
    registry["tiers"] = {
        "standard": {
            "description": "Standard",
            "profile": None,
            "config": {
                "reports": {"github_summary": {"enabled": False}},
                "gates": {"require_run_or_fail": True},
            },
        }
    }
    registry["repos"] = {repo_name: {"tier": "standard"}}

    configs_dir = hub_root_path / "config" / "repos"
    sync_to_configs(registry, configs_dir, dry_run=False, hub_root_path=hub_root_path)

    cfg = load_config(repo_name=repo_name, hub_root=hub_root_path, exit_on_validation_error=False)
    assert cfg["reports"]["github_summary"]["enabled"] is False
    assert cfg["gates"]["require_run_or_fail"] is True
    assert compute_diff(registry, configs_dir, hub_root_path=hub_root_path) == []


def test_registry_sync_roundtrip_applies_tier_profile_and_diff_empty(tmp_path: Path) -> None:
    """Tier profile should be applied in sync_to_configs and reflected in load_config and diff."""
    from cihub.config.loader.core import load_config
    from cihub.services.registry_service import compute_diff, load_registry, sync_to_configs

    repo_name = "demo-repo"

    hub_root_path = tmp_path / "hub"
    (hub_root_path / "config" / "repos").mkdir(parents=True)
    (hub_root_path / "schema").mkdir(parents=True)
    (hub_root_path / "templates" / "profiles").mkdir(parents=True)

    data_root = hub_root()
    (hub_root_path / "config" / "defaults.yaml").write_text(
        (data_root / "config" / "defaults.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (hub_root_path / "schema" / "ci-hub-config.schema.json").write_text(
        (data_root / "schema" / "ci-hub-config.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    # Minimal profile: tweak thresholds and repo dispatch flag.
    (hub_root_path / "templates" / "profiles" / "custom.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": {"dispatch_enabled": False},
                "thresholds": {"coverage_min": 91, "mutation_score_min": 81},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    repo_override_path = hub_root_path / "config" / "repos" / f"{repo_name}.yaml"
    repo_override_path.write_text(
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

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": "custom"}}
    registry["repos"] = {repo_name: {"tier": "standard"}}

    configs_dir = hub_root_path / "config" / "repos"
    sync_to_configs(registry, configs_dir, dry_run=False, hub_root_path=hub_root_path)

    cfg = load_config(repo_name=repo_name, hub_root=hub_root_path, exit_on_validation_error=False)
    assert cfg["repo"]["dispatch_enabled"] is False
    assert cfg["thresholds"]["coverage_min"] == 91
    assert cfg["thresholds"]["mutation_score_min"] == 81
    assert compute_diff(registry, configs_dir, hub_root_path=hub_root_path) == []
