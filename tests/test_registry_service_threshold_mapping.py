"""Tests for registry_service threshold key mapping safety.

Phase 0.1 in SYSTEM_INTEGRATION_PLAN.md: registry sync/diff must use schema
threshold keys (coverage_min, mutation_score_min, max_*_vulns) and must not
write schema-incompatible keys (coverage, mutation_score, vulns_max).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


def _write_repo_config(path: Path, thresholds: dict) -> None:
    config = {
        "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
        "language": "python",
        "thresholds": thresholds,
    }
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def test_sync_to_configs_writes_schema_threshold_keys_and_removes_legacy_keys(tmp_path: Path) -> None:
    from cihub.services.registry_service import load_registry, sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            # legacy / wrong keys that must be removed
            "coverage": 12,
            "mutation_score": 34,
            "vulns_max": 56,
            # schema keys (will be overwritten to registry values)
            "coverage_min": 1,
            "mutation_score_min": 2,
            "max_critical_vulns": 3,
            "max_high_vulns": 4,
        },
    )

    # Minimal registry shape
    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "overrides": {
                "coverage": 70,
                "mutation": 80,
                "vulns_max": 0,
            },
        }
    }

    changes = sync_to_configs(registry, configs_dir, dry_run=False)
    assert any(c["repo"] == repo_name and c["action"] == "updated" for c in changes)

    updated = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    thresholds = updated["thresholds"]

    # Legacy keys removed
    assert "coverage" not in thresholds
    assert "mutation_score" not in thresholds
    assert "vulns_max" not in thresholds

    # Schema keys set
    assert thresholds["coverage_min"] == 70
    assert thresholds["mutation_score_min"] == 80
    assert thresholds["max_critical_vulns"] == 0
    assert thresholds["max_high_vulns"] == 0


def test_sync_to_configs_applies_tier_config_fragments(tmp_path: Path) -> None:
    """Registry sync should apply tier config fragments to repo configs."""
    from cihub.services.registry_service import load_registry, sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {
        "standard": {
            "description": "Standard",
            "profile": None,
            "config": {"repo": {"dispatch_enabled": False}},
        }
    }
    registry["repos"] = {repo_name: {"tier": "standard"}}

    changes = sync_to_configs(registry, configs_dir, dry_run=False)
    assert any(c["repo"] == repo_name and c["action"] == "updated" for c in changes)

    updated = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    assert updated["repo"]["dispatch_enabled"] is False


def test_sync_to_configs_applies_repo_config_thresholds_when_no_overrides(tmp_path: Path) -> None:
    """managedConfig.thresholds should be honored when explicit overrides are absent."""
    from cihub.services.registry_service import load_registry, sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "config": {"thresholds": {"coverage_min": 80}},
        }
    }

    sync_to_configs(registry, configs_dir, dry_run=False)
    updated = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    assert updated["thresholds"]["coverage_min"] == 80


def test_sync_to_configs_threshold_overrides_win_over_config_thresholds(tmp_path: Path) -> None:
    """Explicit overrides remain canonical over managedConfig.thresholds."""
    from cihub.services.registry_service import load_registry, sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "overrides": {"coverage_min": 90},
            "config": {"thresholds": {"coverage_min": 80}},
        }
    }

    sync_to_configs(registry, configs_dir, dry_run=False)
    updated = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    assert updated["thresholds"]["coverage_min"] == 90


def test_sync_to_configs_applies_profile_thresholds(tmp_path: Path) -> None:
    """Tier profile thresholds should influence effective thresholds written on sync."""
    from cihub.services.registry_service import load_registry, sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {
        "standard": {
            "description": "Standard",
            "profile": "python-coverage-gate",
        }
    }
    registry["repos"] = {repo_name: {"tier": "standard"}}

    sync_to_configs(registry, configs_dir, dry_run=False)
    updated = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    assert updated["thresholds"]["coverage_min"] == 90
    assert updated["thresholds"]["mutation_score_min"] == 80


def test_sync_to_configs_does_not_normalize_unmanaged_tool_booleans(tmp_path: Path) -> None:
    """Sync must not rewrite unrelated/unmanaged keys just because a fragment exists."""
    from cihub.services.registry_service import load_registry, sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    repo_path.write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
                "language": "python",
                # Unmanaged/unrelated: bool tool shorthand should remain a bool on sync.
                "python": {"tools": {"mypy": True}},
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
            # managed fragment exists, but does not touch python.tools
            "config": {"repo": {"dispatch_enabled": False}},
        }
    }
    registry["repos"] = {repo_name: {"tier": "standard"}}

    sync_to_configs(registry, configs_dir, dry_run=False)
    updated = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    assert updated["python"]["tools"]["mypy"] is True


def test_sync_to_configs_does_not_add_cvss_fallback_keys_from_fragments(tmp_path: Path) -> None:
    """Fragment normalization must not add derived CVSS keys into configs."""
    from cihub.services.registry_service import load_registry, sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
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
                    # Intentionally set only OWASP CVSS threshold (no Trivy CVSS threshold).
                    "owasp_cvss_fail": 9.0,
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
            # Force a write so we can observe whether new keys were introduced.
            "config": {"repo": {"dispatch_enabled": False}},
        }
    }
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "config": {"thresholds": {"owasp_cvss_fail": 9.0}},
        }
    }

    sync_to_configs(registry, configs_dir, dry_run=False)
    updated = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    thresholds = updated["thresholds"]
    assert thresholds["owasp_cvss_fail"] == 9.0
    assert "trivy_cvss_fail" not in thresholds


def test_compute_diff_uses_schema_threshold_keys(tmp_path: Path) -> None:
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 80,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "overrides": {
                "coverage": 70,
                "mutation": 80,
                "vulns_max": 0,
            },
        }
    }

    diffs = compute_diff(registry, configs_dir)
    assert diffs == []


@pytest.mark.parametrize(
    "thresholds",
    [
        {},
        {"coverage_min": 70, "mutation_score_min": 70},  # missing vuln keys defaults to 0
        {"coverage_min": 70, "mutation_score_min": 70, "max_critical_vulns": 0, "max_high_vulns": 0},
    ],
    ids=["empty", "partial", "full"],
)
def test_compute_diff_handles_missing_threshold_keys_gracefully(tmp_path: Path, thresholds: dict) -> None:
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(repo_path, thresholds=thresholds)

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "overrides": {"coverage": 70, "mutation": 70, "vulns_max": 0},
        }
    }

    # Should not throw; diffs may exist if keys missing/values differ.
    compute_diff(registry, configs_dir)


def test_compute_diff_reports_registry_repo_metadata_drift(tmp_path: Path) -> None:
    """If both legacy top-level repo fields and config.repo exist, they must not disagree."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            # legacy fields
            "language": "python",
            "dispatch_enabled": True,
            # canonical config fragment disagrees (should be drift)
            "config": {
                "repo": {"language": "java", "dispatch_enabled": False},
            },
        }
    }

    diffs = compute_diff(registry, configs_dir)
    fields = {(d["repo"], d["field"]) for d in diffs}
    assert (repo_name, "repo.language") in fields
    assert (repo_name, "repo.dispatch_enabled") in fields


def test_compute_diff_reports_managedconfig_repo_drift(tmp_path: Path) -> None:
    """Non-threshold drift should surface via registry diff (dry-run sync engine)."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    config = {
        "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main", "dispatch_enabled": True},
        "language": "python",
        "thresholds": {
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    }
    repo_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    registry = load_registry(registry_path=None)
    registry["tiers"] = {
        "standard": {
            "description": "Standard",
            "profile": None,
            "config": {"repo": {"dispatch_enabled": False}},
        }
    }
    registry["repos"] = {repo_name: {"tier": "standard"}}

    diffs = compute_diff(registry, configs_dir)
    assert any(
        d["repo"] == repo_name
        and d["field"] == "repo.dispatch_enabled"
        and d["registry_value"] is False
        and d["actual_value"] is True
        for d in diffs
    )


def test_compute_diff_flags_orphan_config_files(tmp_path: Path) -> None:
    """Full drift should flag repo config YAMLs that exist without a registry entry."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    # Orphan config file: no matching registry["repos"] entry.
    orphan_name = "orphan-repo"
    orphan_path = configs_dir / f"{orphan_name}.yaml"
    _write_repo_config(
        orphan_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {"tracked-repo": {"tier": "standard"}}

    diffs = compute_diff(registry, configs_dir)
    assert any(
        d["repo"] == orphan_name and d["field"] == "registry_entry" and d["registry_value"] == "missing"
        for d in diffs
    )


def test_compute_diff_flags_orphan_nested_config_files(tmp_path: Path) -> None:
    """Nested configs (owner/repo.yaml) should also be scanned."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    (configs_dir / "owner").mkdir(parents=True)

    orphan_name = "owner/orphan-repo"
    orphan_path = configs_dir / "owner" / "orphan-repo.yaml"
    _write_repo_config(
        orphan_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {}

    diffs = compute_diff(registry, configs_dir)
    assert any(d["repo"] == orphan_name and d["field"] == "registry_entry" for d in diffs)


def test_compute_diff_flags_unmanaged_top_level_keys(tmp_path: Path) -> None:
    """Full drift should flag config keys that are outside managedConfig allowlist."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    repo_path.write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
                "thresholds": {
                    "coverage_min": 70,
                    "mutation_score_min": 70,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                },
                # Valid in main schema but NOT currently in registry.managedConfig allowlist.
                "extra_tests": [{"name": "x", "command": "echo hi"}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {repo_name: {"tier": "standard"}}

    diffs = compute_diff(registry, configs_dir)
    assert any(
        d["repo"] == repo_name and d["field"] == "unmanaged_key.extra_tests" for d in diffs
    )


def test_compute_diff_flags_unknown_top_level_keys_as_errors(tmp_path: Path) -> None:
    """Schema-invalid keys should be flagged separately as unknown_key.* with error severity."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    repo_path.write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
                "thresholds": {
                    "coverage_min": 70,
                    "mutation_score_min": 70,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                },
                "typo_field": True,  # not in config schema
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {repo_name: {"tier": "standard"}}

    diffs = compute_diff(registry, configs_dir)
    assert any(
        d["repo"] == repo_name
        and d["field"] == "unknown_key.typo_field"
        and d["severity"] == "error"
        for d in diffs
    )


def test_compute_diff_surfaces_schema_load_failure(tmp_path: Path) -> None:
    """If config schema cannot be loaded, diff should surface an explicit error."""
    from cihub.services.registry_service import compute_diff, load_registry

    hub = tmp_path / "hub"
    configs_dir = hub / "config" / "repos"
    configs_dir.mkdir(parents=True)
    # NOTE: intentionally do NOT create hub/schema/ci-hub-config.schema.json

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )
    # Add a schema-invalid key to show classification is degraded when schema missing.
    data = yaml.safe_load(repo_path.read_text(encoding="utf-8"))
    data["typo_field"] = True
    repo_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {repo_name: {"tier": "standard"}}

    diffs = compute_diff(registry, configs_dir, hub_root_path=hub)
    assert any(d["repo"] == "<hub>" and d["field"] == "schema" and d["severity"] == "error" for d in diffs)

def test_compute_diff_dedupes_unreadable_yaml_errors(tmp_path: Path) -> None:
    """Unreadable repo YAML should not produce duplicate config_file diffs."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "bad-repo"
    (configs_dir / f"{repo_name}.yaml").write_text("repo: [\n", encoding="utf-8")  # invalid YAML

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {repo_name: {"tier": "standard"}}

    diffs = compute_diff(registry, configs_dir)
    errors = [d for d in diffs if d["repo"] == repo_name and d["field"] == "config_file"]
    assert len(errors) == 1


def test_compute_diff_reports_sparse_tier_config_values(tmp_path: Path) -> None:
    """Sparse audit should flag tier config values that match defaults."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {
        "standard": {
            "description": "Standard",
            "profile": None,
            "config": {"repo": {"dispatch_enabled": True}},
        }
    }
    registry["repos"] = {repo_name: {"tier": "standard"}}

    diffs = compute_diff(registry, configs_dir)
    fields = {(d["repo"], d["field"]) for d in diffs}
    assert ("tier:standard", "sparse.config.repo.dispatch_enabled") in fields


def test_compute_diff_reports_sparse_repo_config_values(tmp_path: Path) -> None:
    """Sparse audit should flag repo config values that match tier/default baseline."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    _write_repo_config(
        repo_path,
        thresholds={
            "coverage_min": 70,
            "mutation_score_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 0,
        },
    )

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "config": {"repo": {"dispatch_enabled": True}},
        }
    }

    diffs = compute_diff(registry, configs_dir)
    fields = {(d["repo"], d["field"]) for d in diffs}
    assert (repo_name, "sparse.config.repo.dispatch_enabled") in fields



def test_save_registry_drops_legacy_repo_metadata_fields_when_equal(tmp_path: Path) -> None:
    """When legacy top-level repo fields match config.repo, save should drop legacy copies."""
    import json

    from cihub.services.registry_service import load_registry, save_registry

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {
        "demo": {
            "tier": "standard",
            # legacy copies
            "language": "python",
            "dispatch_enabled": True,
            # canonical
            "config": {"repo": {"language": "python", "dispatch_enabled": True}},
        }
    }

    path = tmp_path / "registry.json"
    save_registry(registry, registry_path=path)

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    repo = on_disk["repos"]["demo"]
    assert "language" not in repo
    assert "dispatch_enabled" not in repo


def test_load_registry_normalizes_legacy_threshold_keys_on_read_and_write(tmp_path: Path) -> None:
    """Regression: registry.json storage should not persist legacy keys.

    The registry must accept legacy keys for backward compatibility, but normalize
    to schema-aligned keys when loading/saving.
    """
    from cihub.services.registry_service import load_registry, save_registry

    registry_path = tmp_path / "registry.json"
    import json

    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cihub-registry-v1",
                "tiers": {
                    "standard": {
                        "description": "Standard",
                        "profile": None,
                        # legacy tier keys (should normalize)
                        "coverage": 70,
                        "mutation": 80,
                        "vulns_max": 0,
                    }
                },
                "repos": {
                    "demo": {
                        "tier": "standard",
                        "overrides": {
                            # legacy keys (should normalize)
                            "coverage": 75,
                            "mutation": 85,
                            "vulns_max": 1,
                        },
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = load_registry(registry_path=registry_path)
    tier = loaded["tiers"]["standard"]
    assert "coverage" not in tier
    assert "mutation" not in tier
    assert "vulns_max" not in tier
    assert tier["coverage_min"] == 70
    assert tier["mutation_score_min"] == 80
    assert tier["max_critical_vulns"] == 0
    assert tier["max_high_vulns"] == 0

    overrides = loaded["repos"]["demo"]["overrides"]
    assert "coverage" not in overrides
    assert "mutation" not in overrides
    assert "vulns_max" not in overrides
    assert overrides["coverage_min"] == 75
    assert overrides["mutation_score_min"] == 85
    assert overrides["max_critical_vulns"] == 1
    assert overrides["max_high_vulns"] == 1

    # Saving should not reintroduce legacy keys
    save_registry(loaded, registry_path=registry_path)
    on_disk = json.loads(registry_path.read_text(encoding="utf-8"))
    tier_on_disk = on_disk["tiers"]["standard"]
    assert "coverage" not in tier_on_disk
    assert "mutation" not in tier_on_disk
    assert "vulns_max" not in tier_on_disk
    overrides_on_disk = on_disk["repos"]["demo"]["overrides"]
    assert "coverage" not in overrides_on_disk
    assert "mutation" not in overrides_on_disk
    assert "vulns_max" not in overrides_on_disk


def test_save_registry_normalizes_legacy_override_keys_to_schema_keys(tmp_path: Path) -> None:
    """Saving registry should write schema-aligned keys (even if input uses legacy keys)."""
    from cihub.services.registry_service import save_registry

    registry_path = tmp_path / "registry.json"
    registry: dict = {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {"coverage": 70, "mutation": 70, "vulns_max": 0}},
        "repos": {
            "demo-repo": {
                "tier": "standard",
                "overrides": {"coverage": 75, "mutation": 80, "vulns_max": 1},
            }
        },
    }

    save_registry(registry, registry_path=registry_path)

    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    overrides = raw["repos"]["demo-repo"]["overrides"]
    assert "coverage" not in overrides
    assert "mutation" not in overrides
    assert "vulns_max" not in overrides
    assert overrides["coverage_min"] == 75
    assert overrides["mutation_score_min"] == 80
    assert overrides["max_critical_vulns"] == 1
    assert overrides["max_high_vulns"] == 1


def test_compute_diff_detects_ci_hub_yml_overrides(tmp_path: Path) -> None:
    """Phase 2.4: compute_diff should detect .ci-hub.yml overrides when repo_paths provided."""
    from cihub.services.registry_service import compute_diff, load_registry

    # Setup hub structure
    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
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

    # Create target repo with .ci-hub.yml that overrides thresholds
    target_repo_dir = tmp_path / "repos" / repo_name
    target_repo_dir.mkdir(parents=True)
    ci_hub_yml = target_repo_dir / ".ci-hub.yml"
    ci_hub_yml.write_text(
        yaml.safe_dump(
            {
                "thresholds": {
                    "coverage_min": 90,  # Override: 70 -> 90
                },
                "gates": {
                    "require_run_or_fail": True,  # Override: not in registry
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Setup registry
    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {repo_name: {"tier": "standard"}}

    # Run diff with repo_paths
    diffs = compute_diff(
        registry,
        configs_dir,
        repo_paths={repo_name: target_repo_dir},
    )

    # Should detect .ci-hub.yml overrides
    ci_hub_diffs = [d for d in diffs if d["field"].startswith("ci-hub-yml.")]
    assert len(ci_hub_diffs) >= 1, f"Expected .ci-hub.yml override detection, got {diffs}"

    # Should detect thresholds.coverage_min override
    coverage_diff = next(
        (d for d in ci_hub_diffs if "coverage_min" in d["field"]),
        None,
    )
    assert coverage_diff is not None, f"Expected coverage_min override, got {ci_hub_diffs}"
    assert coverage_diff["actual_value"] == 90
    assert coverage_diff["severity"] == "info"  # Overrides are expected, just surfacing


def test_compute_diff_skips_missing_ci_hub_yml(tmp_path: Path) -> None:
    """Phase 2.4: compute_diff should not error if repo has no .ci-hub.yml."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
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

    # Target repo exists but has NO .ci-hub.yml
    target_repo_dir = tmp_path / "repos" / repo_name
    target_repo_dir.mkdir(parents=True)

    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {repo_name: {"tier": "standard"}}

    # Should not error, should not report .ci-hub.yml diffs
    diffs = compute_diff(
        registry,
        configs_dir,
        repo_paths={repo_name: target_repo_dir},
    )

    ci_hub_diffs = [d for d in diffs if d["field"].startswith("ci-hub-yml.")]
    assert len(ci_hub_diffs) == 0, f"Should not have .ci-hub.yml diffs: {ci_hub_diffs}"


def test_compute_diff_no_override_when_registry_matches_ci_hub_yml(tmp_path: Path) -> None:
    """Phase 2.4 regression: no diff when registry override equals .ci-hub.yml value."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    repo_path.write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
                "language": "python",
                "thresholds": {"coverage_min": 80},  # synced from registry
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Target repo with .ci-hub.yml that has same coverage_min as registry override
    target_repo_dir = tmp_path / "repos" / repo_name
    target_repo_dir.mkdir(parents=True)
    ci_hub_yml = target_repo_dir / ".ci-hub.yml"
    ci_hub_yml.write_text(
        yaml.safe_dump(
            {
                "thresholds": {
                    "coverage_min": 80,  # Same as registry override
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Registry has explicit override for this repo
    registry = load_registry(registry_path=None)
    registry["tiers"] = {"standard": {"description": "Standard", "profile": None}}
    registry["repos"] = {
        repo_name: {
            "tier": "standard",
            "overrides": {"coverage_min": 80},  # Explicit override
        }
    }

    diffs = compute_diff(
        registry,
        configs_dir,
        repo_paths={repo_name: target_repo_dir},
    )

    # Should NOT report coverage_min as override since registry override equals .ci-hub.yml
    coverage_diffs = [d for d in diffs if "coverage_min" in d.get("field", "")]
    assert len(coverage_diffs) == 0, f"Expected no coverage_min diff, got {coverage_diffs}"


def test_compute_diff_repo_fragment_overrides_tier_thresholds(tmp_path: Path) -> None:
    """Phase 2.4 precedence: repo config.thresholds should override tier-level thresholds."""
    from cihub.services.registry_service import compute_diff, load_registry

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    repo_name = "demo-repo"
    repo_path = configs_dir / f"{repo_name}.yaml"
    repo_path.write_text(
        yaml.safe_dump(
            {
                "repo": {"owner": "o", "name": "n", "language": "python", "default_branch": "main"},
                "language": "python",
                "thresholds": {"coverage_min": 85},  # synced from registry (repo fragment wins)
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Target repo with .ci-hub.yml that has same coverage_min as repo fragment
    target_repo_dir = tmp_path / "repos" / repo_name
    target_repo_dir.mkdir(parents=True)
    ci_hub_yml = target_repo_dir / ".ci-hub.yml"
    ci_hub_yml.write_text(
        yaml.safe_dump(
            {
                "thresholds": {
                    "coverage_min": 85,  # Same as repo fragment
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Registry has tier-level coverage_min=90, but repo config overrides to 85
    registry = load_registry(registry_path=None)
    registry["tiers"] = {
        "strict": {
            "description": "Strict tier",
            "profile": None,
            "coverage_min": 90,  # Tier-level threshold
        }
    }
    registry["repos"] = {
        repo_name: {
            "tier": "strict",
            "config": {
                "thresholds": {"coverage_min": 85},  # Repo fragment overrides tier
            },
        }
    }

    diffs = compute_diff(
        registry,
        configs_dir,
        repo_paths={repo_name: target_repo_dir},
    )

    # Should NOT report coverage_min diff because repo fragment (85) wins over tier (90)
    # and .ci-hub.yml also has 85
    coverage_diffs = [d for d in diffs if "coverage_min" in d.get("field", "")]
    assert len(coverage_diffs) == 0, (
        f"Expected no coverage_min diff (repo fragment should override tier), got {coverage_diffs}"
    )


# =============================================================================
# Phase 4: Tests for created/would_create paths
# =============================================================================


def test_sync_to_configs_creates_new_config_when_registry_has_required_fields(tmp_path: Path) -> None:
    """sync_to_configs should create config files for new repos with required fields."""
    from cihub.services.registry_service import sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    # Registry with all required fields in config.repo
    registry = {
        "repos": {
            "new-repo": {
                "tier": "standard",
                "language": "python",
                "config": {
                    "repo": {
                        "owner": "test-org",
                        "name": "new-repo",
                        "language": "python",
                    }
                },
            }
        },
        "tiers": {"standard": {}},
    }

    changes = sync_to_configs(registry, configs_dir, dry_run=False, hub_root_path=tmp_path)

    # Should have created the config
    created = [c for c in changes if c.get("action") == "created"]
    assert len(created) == 1
    assert created[0]["repo"] == "new-repo"

    # File should exist
    config_path = configs_dir / "new-repo.yaml"
    assert config_path.exists()

    # File should have language set
    config = yaml.safe_load(config_path.read_text())
    assert config.get("language") == "python"


def test_sync_to_configs_skips_new_config_when_missing_required_fields(tmp_path: Path) -> None:
    """sync_to_configs should skip creating config if required fields are missing."""
    from cihub.services.registry_service import sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    # Registry missing repo.owner, repo.name
    registry = {
        "repos": {
            "incomplete-repo": {
                "tier": "standard",
                "language": "python",
                # No config.repo block with owner/name
            }
        },
        "tiers": {"standard": {}},
    }

    changes = sync_to_configs(registry, configs_dir, dry_run=False, hub_root_path=tmp_path)

    # Should have skipped
    skipped = [c for c in changes if c.get("action") == "skip"]
    assert len(skipped) == 1
    assert skipped[0]["repo"] == "incomplete-repo"
    assert "missing required fields" in skipped[0].get("reason", "")

    # File should NOT exist
    assert not (configs_dir / "incomplete-repo.yaml").exists()


def test_sync_to_configs_would_create_in_dry_run(tmp_path: Path) -> None:
    """sync_to_configs dry_run should report would_create without writing."""
    from cihub.services.registry_service import sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    registry = {
        "repos": {
            "new-repo": {
                "tier": "standard",
                "language": "python",
                "config": {
                    "repo": {
                        "owner": "test-org",
                        "name": "new-repo",
                        "language": "python",
                    }
                },
            }
        },
        "tiers": {"standard": {}},
    }

    changes = sync_to_configs(registry, configs_dir, dry_run=True, hub_root_path=tmp_path)

    # Should report would_create
    would_create = [c for c in changes if c.get("action") == "would_create"]
    assert len(would_create) == 1
    assert would_create[0]["repo"] == "new-repo"

    # File should NOT exist (dry run)
    assert not (configs_dir / "new-repo.yaml").exists()


def test_compute_diff_reports_would_create_for_missing_configs(tmp_path: Path) -> None:
    """compute_diff should report would_create when config file is missing but can be created."""
    from cihub.services.registry_service import compute_diff

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    # Write registry.json
    registry_path = tmp_path / "config" / "registry.json"
    registry = {
        "repos": {
            "missing-config-repo": {
                "tier": "standard",
                "language": "python",
                "config": {
                    "repo": {
                        "owner": "test-org",
                        "name": "missing-config-repo",
                        "language": "python",
                    }
                },
            }
        },
        "tiers": {"standard": {}},
    }
    registry_path.write_text(json.dumps(registry))

    diffs = compute_diff(registry, configs_dir, hub_root_path=tmp_path)

    # Should have a would_create diff entry
    would_create_diffs = [
        d for d in diffs
        if d.get("repo") == "missing-config-repo" and d.get("registry_value") == "would_create"
    ]
    assert len(would_create_diffs) == 1
    assert would_create_diffs[0]["field"] == "config_file"
    assert would_create_diffs[0]["actual_value"] == "missing"


def test_sync_to_configs_handles_malformed_config_null(tmp_path: Path) -> None:
    """sync_to_configs should not crash on malformed registry entries with config: null."""
    from cihub.services.registry_service import sync_to_configs

    configs_dir = tmp_path / "config" / "repos"
    configs_dir.mkdir(parents=True)

    # Registry with config: null (malformed)
    registry = {
        "repos": {
            "malformed-repo": {
                "tier": "standard",
                "language": "python",
                "config": None,  # Malformed: should be dict
            }
        },
        "tiers": {"standard": {}},
    }

    # Should not raise AttributeError
    changes = sync_to_configs(registry, configs_dir, dry_run=False, hub_root_path=tmp_path)

    # Should skip due to missing fields
    skipped = [c for c in changes if c.get("action") == "skip"]
    assert len(skipped) == 1
    assert "missing required fields" in skipped[0].get("reason", "")


# ─────────────────────────────────────────────────────────────────────────────
# Tests for registry add command with --owner/--name/--language flags
# ─────────────────────────────────────────────────────────────────────────────


def test_registry_add_with_owner_name_language(tmp_path: Path, monkeypatch) -> None:
    """registry add --owner --name --language populates config.repo block for sync."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_add
    from cihub.services.registry_service import load_registry, save_registry

    # Setup registry in tmp_path
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry_path = config_dir / "registry.json"
    registry = {
        "repos": {},
        "tiers": {"standard": {}, "strict": {}},
    }
    registry_path.write_text(json.dumps(registry))

    # Patch hub_root to return tmp_path
    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    # Build args with --owner, --name, --language
    args = argparse.Namespace(
        repo="new-repo",
        tier="standard",
        description="A new repo",
        owner="my-org",
        name="new-repo",
        language="python",
    )

    result = _cmd_add(args)

    assert result.exit_code == 0, f"Expected success, got: {result.summary}"
    assert result.data["repo"] == "new-repo"
    assert result.data["owner"] == "my-org"
    assert result.data["language"] == "python"
    assert result.data["can_sync"] is True

    # Verify registry content
    updated_registry = load_registry()
    entry = updated_registry["repos"]["new-repo"]

    # Normalization drops redundant top-level language when config.repo.language matches.
    # The canonical location is config.repo.language.
    assert "config" in entry
    assert "repo" in entry["config"]
    assert entry["config"]["repo"]["owner"] == "my-org"
    assert entry["config"]["repo"]["name"] == "new-repo"
    assert entry["config"]["repo"]["language"] == "python"

    # Top-level language is dropped by sparse storage normalization (matches canonical)
    assert entry.get("language") is None


def test_registry_add_without_owner_hints_sync_disabled(tmp_path: Path, monkeypatch) -> None:
    """registry add without --owner shows hint that sync is disabled."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_add

    # Setup registry
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry_path = config_dir / "registry.json"
    registry = {
        "repos": {},
        "tiers": {"standard": {}},
    }
    registry_path.write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    # Add repo without --owner or --language
    args = argparse.Namespace(
        repo="minimal-repo",
        tier="standard",
        description=None,
        owner=None,
        name=None,
        language=None,
    )

    result = _cmd_add(args)

    assert result.exit_code == 0
    assert result.data["can_sync"] is False
    assert "add --owner --language to enable sync" in result.summary


def test_registry_add_with_name_only_requires_owner(tmp_path: Path, monkeypatch) -> None:
    """registry add --name without --owner should fail (schema enforces both-or-none)."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_add
    from cihub.exit_codes import EXIT_USAGE

    # Setup registry
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry_path = config_dir / "registry.json"
    registry = {
        "repos": {},
        "tiers": {"standard": {}},
    }
    registry_path.write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    # Add repo with --name only (different from positional repo arg)
    args = argparse.Namespace(
        repo="alias-key",
        tier="standard",
        description=None,
        owner=None,
        name="actual-repo-name",  # Explicit name differs from repo key
        language=None,
    )

    result = _cmd_add(args)

    # Should fail with usage error - schema enforces owner/name as both-or-none
    assert result.exit_code == EXIT_USAGE
    assert "--name requires --owner" in result.summary
    assert result.problems[0]["code"] == "CIHUB-REGISTRY-NAME-REQUIRES-OWNER"


def test_registry_add_then_sync_creates_config(tmp_path: Path, monkeypatch) -> None:
    """Full flow: registry add with flags → sync creates config file."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_add
    from cihub.services.registry_service import load_registry, sync_to_configs

    # Setup hub structure
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)

    # Create defaults.yaml
    defaults = config_dir / "defaults.yaml"
    defaults.write_text("coverage_min: 80\nmutation_score_min: 60\n")

    # Create profiles
    profiles_dir = tmp_path / "templates" / "profiles" / "python" / "standard"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "quality.yaml").write_text("coverage_min: 85\n")

    # Create registry
    registry_path = config_dir / "registry.json"
    registry = {
        "repos": {},
        "tiers": {"standard": {"coverage_min": 85}},
    }
    registry_path.write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    # Step 1: Add repo with all required fields
    args = argparse.Namespace(
        repo="sync-test-repo",
        tier="standard",
        description="Test repo for sync",
        owner="test-org",
        name="sync-test-repo",
        language="python",
    )
    result = _cmd_add(args)
    assert result.exit_code == 0
    assert result.data["can_sync"] is True

    # Step 2: Sync to create config file
    updated_registry = load_registry()
    changes = sync_to_configs(updated_registry, repos_dir, dry_run=False, hub_root_path=tmp_path)

    # Should have created the config
    created = [c for c in changes if c.get("action") == "created"]
    assert len(created) == 1
    assert created[0]["repo"] == "sync-test-repo"

    # Verify file exists and has correct content
    config_file = repos_dir / "sync-test-repo.yaml"
    assert config_file.exists()

    import yaml

    with config_file.open() as f:
        config_content = yaml.safe_load(f)

    assert config_content["repo"]["owner"] == "test-org"
    assert config_content["repo"]["name"] == "sync-test-repo"
    assert config_content["repo"]["language"] == "python"


# ─────────────────────────────────────────────────────────────────────────────
# Tests for registry remove command
# ─────────────────────────────────────────────────────────────────────────────


def test_registry_remove_requires_confirmation(tmp_path: Path, monkeypatch) -> None:
    """registry remove without --yes should require confirmation."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_remove
    from cihub.exit_codes import EXIT_USAGE

    # Setup registry with a repo
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry_path = config_dir / "registry.json"
    registry = {
        "repos": {"existing-repo": {"tier": "standard"}},
        "tiers": {"standard": {}},
    }
    registry_path.write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)
    monkeypatch.setattr("cihub.commands.registry.modify.hub_root", lambda: tmp_path)

    args = argparse.Namespace(
        repo="existing-repo",
        delete_config=False,
        yes=False,
    )

    result = _cmd_remove(args)

    assert result.exit_code == EXIT_USAGE
    assert "Confirmation required" in result.summary
    assert result.problems[0]["code"] == "CIHUB-REGISTRY-CONFIRM-REQUIRED"


def test_registry_remove_with_yes_removes_repo(tmp_path: Path, monkeypatch) -> None:
    """registry remove --yes should remove the repo from registry."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_remove
    from cihub.services.registry_service import load_registry

    # Setup registry with a repo
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry_path = config_dir / "registry.json"
    registry = {
        "repos": {"to-remove": {"tier": "standard"}, "keep-me": {"tier": "standard"}},
        "tiers": {"standard": {}},
    }
    registry_path.write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)
    monkeypatch.setattr("cihub.commands.registry.modify.hub_root", lambda: tmp_path)

    args = argparse.Namespace(
        repo="to-remove",
        delete_config=False,
        yes=True,
    )

    result = _cmd_remove(args)

    assert result.exit_code == 0
    assert "Removed to-remove from registry" in result.summary

    # Verify repo is removed
    updated_registry = load_registry()
    assert "to-remove" not in updated_registry["repos"]
    assert "keep-me" in updated_registry["repos"]  # Other repos untouched


def test_registry_remove_not_found(tmp_path: Path, monkeypatch) -> None:
    """registry remove on non-existent repo should fail."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_remove
    from cihub.exit_codes import EXIT_FAILURE

    # Setup empty registry
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry_path = config_dir / "registry.json"
    registry = {"repos": {}, "tiers": {"standard": {}}}
    registry_path.write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)
    monkeypatch.setattr("cihub.commands.registry.modify.hub_root", lambda: tmp_path)

    args = argparse.Namespace(
        repo="nonexistent",
        delete_config=False,
        yes=True,
    )

    result = _cmd_remove(args)

    assert result.exit_code == EXIT_FAILURE
    assert "not in registry" in result.problems[0]["message"]


def test_registry_remove_with_delete_config(tmp_path: Path, monkeypatch) -> None:
    """registry remove --delete-config should also delete the config file."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_remove
    from cihub.services.registry_service import load_registry

    # Setup registry and config file
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    registry_path = config_dir / "registry.json"
    registry = {
        "repos": {"deletable": {"tier": "standard"}},
        "tiers": {"standard": {}},
    }
    registry_path.write_text(json.dumps(registry))

    # Create the config file
    config_file = repos_dir / "deletable.yaml"
    config_file.write_text("repo:\n  name: deletable\n")
    assert config_file.exists()

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)
    monkeypatch.setattr("cihub.commands.registry.modify.hub_root", lambda: tmp_path)

    args = argparse.Namespace(
        repo="deletable",
        delete_config=True,
        yes=True,
    )

    result = _cmd_remove(args)

    assert result.exit_code == 0
    assert "Removed deletable from registry" in result.summary
    assert "deleted" in result.summary
    assert result.data["config_deleted"] is True

    # Verify both registry and config file are removed
    updated_registry = load_registry()
    assert "deletable" not in updated_registry["repos"]
    assert not config_file.exists()


# ─────────────────────────────────────────────────────────────────────────────
# Tests for registry export command
# ─────────────────────────────────────────────────────────────────────────────


def test_registry_export_creates_backup_file(tmp_path: Path, monkeypatch) -> None:
    """registry export should create a JSON backup file."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_export

    # Setup registry
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry_path = config_dir / "registry.json"
    registry = {
        "schema_version": "cihub-registry-v1",
        "repos": {"repo-a": {"tier": "standard"}, "repo-b": {"tier": "strict"}},
        "tiers": {"standard": {}, "strict": {}},
    }
    registry_path.write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    output_file = tmp_path / "backup.json"
    args = argparse.Namespace(output=str(output_file), pretty=False)

    result = _cmd_export(args)

    assert result.exit_code == 0
    assert output_file.exists()
    assert result.data["repo_count"] == 2
    assert result.data["tier_count"] == 2

    # Verify content
    exported = json.loads(output_file.read_text())
    assert exported["repos"]["repo-a"]["tier"] == "standard"


# ─────────────────────────────────────────────────────────────────────────────
# Tests for registry import command
# ─────────────────────────────────────────────────────────────────────────────


def test_registry_import_requires_mode_flag(tmp_path: Path, monkeypatch) -> None:
    """registry import without --merge or --replace should fail."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_import
    from cihub.exit_codes import EXIT_USAGE

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "registry.json").write_text('{"repos": {}, "tiers": {}}')

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    import_file = tmp_path / "import.json"
    import_file.write_text('{"repos": {}, "tiers": {}}')

    args = argparse.Namespace(file=str(import_file), merge=False, replace=False, dry_run=False)

    result = _cmd_import(args)

    assert result.exit_code == EXIT_USAGE
    assert "Must specify --merge or --replace" in result.summary


def test_registry_import_merge_adds_repos(tmp_path: Path, monkeypatch) -> None:
    """registry import --merge should add new repos and update existing."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_import
    from cihub.services.registry_service import load_registry

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry = {
        "schema_version": "cihub-registry-v1",
        "repos": {"existing": {"tier": "standard"}},
        "tiers": {"standard": {}},
    }
    (config_dir / "registry.json").write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    # Import file with new and updated repos
    import_data = {
        "repos": {
            "existing": {"tier": "strict"},  # Update
            "new-repo": {"tier": "standard"},  # Add
        },
        "tiers": {"standard": {}, "strict": {}},
    }
    import_file = tmp_path / "import.json"
    import_file.write_text(json.dumps(import_data))

    args = argparse.Namespace(file=str(import_file), merge=True, replace=False, dry_run=False)

    result = _cmd_import(args)

    assert result.exit_code == 0
    assert result.data["added_count"] == 1
    assert result.data["updated_count"] == 1

    # Verify registry
    updated = load_registry()
    assert "new-repo" in updated["repos"]
    assert updated["repos"]["existing"]["tier"] == "strict"


def test_registry_import_replace_overwrites_all(tmp_path: Path, monkeypatch) -> None:
    """registry import --replace should replace entire registry."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_import
    from cihub.services.registry_service import load_registry

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    registry = {
        "schema_version": "cihub-registry-v1",
        "repos": {"old-repo": {"tier": "standard"}},
        "tiers": {"standard": {}},
    }
    (config_dir / "registry.json").write_text(json.dumps(registry))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    # Import file replaces everything
    import_data = {
        "schema_version": "cihub-registry-v1",
        "repos": {"new-only": {"tier": "strict"}},
        "tiers": {"strict": {}},
    }
    import_file = tmp_path / "import.json"
    import_file.write_text(json.dumps(import_data))

    args = argparse.Namespace(file=str(import_file), merge=False, replace=True, dry_run=False)

    result = _cmd_import(args)

    assert result.exit_code == 0
    assert result.data["removed_count"] == 1  # old-repo removed
    assert result.data["added_count"] == 1  # new-only added

    # Verify registry
    updated = load_registry()
    assert "old-repo" not in updated["repos"]
    assert "new-only" in updated["repos"]


def test_registry_import_rejects_invalid_repos_type(tmp_path: Path, monkeypatch) -> None:
    """registry import should reject repos that isn't a dict."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_import
    from cihub.exit_codes import EXIT_FAILURE

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "registry.json").write_text('{"repos": {}, "tiers": {}}')

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    # Invalid: repos is a list
    import_file = tmp_path / "bad.json"
    import_file.write_text('{"repos": ["not", "a", "dict"], "tiers": {}}')

    args = argparse.Namespace(file=str(import_file), merge=True, replace=False, dry_run=False)

    result = _cmd_import(args)

    assert result.exit_code == EXIT_FAILURE
    assert "must be a JSON object" in result.problems[0]["message"]


def test_registry_import_replace_requires_complete_structure(tmp_path: Path, monkeypatch) -> None:
    """registry import --replace should require schema_version, tiers, repos."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_import
    from cihub.exit_codes import EXIT_FAILURE

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "registry.json").write_text('{"schema_version": "v1", "repos": {}, "tiers": {}}')

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    # Missing schema_version
    import_file = tmp_path / "incomplete.json"
    import_file.write_text('{"repos": {}, "tiers": {}}')

    args = argparse.Namespace(file=str(import_file), merge=False, replace=True, dry_run=False)

    result = _cmd_import(args)

    assert result.exit_code == EXIT_FAILURE
    assert "missing schema_version" in result.summary


def test_registry_import_dry_run_no_changes(tmp_path: Path, monkeypatch) -> None:
    """registry import --dry-run should not modify registry."""
    import argparse

    from cihub.commands.registry_cmd import _cmd_import
    from cihub.services.registry_service import load_registry

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    original = {
        "schema_version": "cihub-registry-v1",
        "repos": {"original": {"tier": "standard"}},
        "tiers": {"standard": {}},
    }
    (config_dir / "registry.json").write_text(json.dumps(original))

    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    import_data = {
        "repos": {"new-repo": {"tier": "standard"}},
        "tiers": {"standard": {}},
    }
    import_file = tmp_path / "import.json"
    import_file.write_text(json.dumps(import_data))

    args = argparse.Namespace(file=str(import_file), merge=True, replace=False, dry_run=True)

    result = _cmd_import(args)

    assert result.exit_code == 0
    assert "Would import" in result.summary
    assert result.data["dry_run"] is True

    # Registry unchanged
    current = load_registry()
    assert "new-repo" not in current["repos"]
    assert "original" in current["repos"]
