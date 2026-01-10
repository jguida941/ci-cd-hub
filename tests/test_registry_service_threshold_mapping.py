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
