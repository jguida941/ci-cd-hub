"""Contract tests for registry.schema.json.

Goal: registry schema should validate the current config/registry.json, and should
explicitly validate the threshold override keys used by registry_service.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_SCHEMA_PATH = ROOT / "schema" / "registry.schema.json"
REGISTRY_JSON_PATH = ROOT / "config" / "registry.json"
CIHUB_CONFIG_SCHEMA_PATH = ROOT / "schema" / "ci-hub-config.schema.json"


def test_registry_schema_is_valid_json() -> None:
    json.loads(REGISTRY_SCHEMA_PATH.read_text(encoding="utf-8"))


def _get_registry_validator() -> jsonschema.Draft7Validator:
    registry_schema = json.loads(REGISTRY_SCHEMA_PATH.read_text(encoding="utf-8"))
    cihub_schema = json.loads(CIHUB_CONFIG_SCHEMA_PATH.read_text(encoding="utf-8"))

    # Use a local store so external $ref URIs resolve without network access.
    store = {
        registry_schema.get("$id"): registry_schema,
        cihub_schema.get("$id"): cihub_schema,
    }
    resolver = jsonschema.RefResolver.from_schema(registry_schema, store=store)
    return jsonschema.Draft7Validator(registry_schema, resolver=resolver)


def test_registry_json_validates_against_registry_schema() -> None:
    registry = json.loads(REGISTRY_JSON_PATH.read_text(encoding="utf-8"))
    _get_registry_validator().validate(registry)


def test_registry_schema_accepts_schema_aligned_overrides() -> None:
    registry = {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {"description": "Standard", "profile": None}},
        "repos": {
            "demo": {
                "tier": "standard",
                "overrides": {
                    "coverage_min": 80,
                    "mutation_score_min": 70,
                    "max_critical_vulns": 0,
                    "max_high_vulns": 0,
                },
            }
        },
    }
    _get_registry_validator().validate(registry)


def test_registry_schema_accepts_legacy_override_aliases() -> None:
    registry = {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {"description": "Standard", "profile": None}},
        "repos": {
            "demo": {
                "tier": "standard",
                "overrides": {
                    "coverage": 80,
                    "mutation": 70,
                    "vulns_max": 0,
                },
            }
        },
    }
    _get_registry_validator().validate(registry)


def test_registry_schema_rejects_unknown_override_keys() -> None:
    registry = {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {"description": "Standard", "profile": None}},
        "repos": {
            "demo": {
                "tier": "standard",
                "overrides": {"coverage_min": 80, "bogus": 123},
            }
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        _get_registry_validator().validate(registry)


def test_registry_schema_allows_allowlisted_config_fragment_via_ref() -> None:
    """Exercise $ref plumbing: registry.config should validate against ci-hub-config subschemas."""
    registry = {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {"description": "Standard", "profile": None}},
        "repos": {
            "demo": {
                "tier": "standard",
                "config": {
                    "language": "python",
                    "python": {"tools": {"pytest": {"enabled": True, "min_coverage": 80}}},
                    "thresholds": {"coverage_min": 80},
                    "cihub": {"debug": True},
                },
            }
        },
    }
    _get_registry_validator().validate(registry)


def test_registry_schema_allows_sparse_repo_metadata_in_config_repo() -> None:
    """Sparse registry storage: config.repo must NOT require owner/name."""
    registry = {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {"description": "Standard", "profile": None}},
        "repos": {
            "demo": {
                "tier": "standard",
                "config": {
                    "repo": {
                        # intentionally omit owner/name
                        "default_branch": "main",
                        "repo_side_execution": False,
                        "use_central_runner": True,
                    }
                },
            }
        },
    }
    _get_registry_validator().validate(registry)


@pytest.mark.parametrize(
    "repo_block",
    [
        {"owner": "o"},
        {"name": "n"},
    ],
    ids=["owner_only", "name_only"],
)
def test_registry_schema_rejects_partial_owner_name_in_sparse_repo(repo_block: dict[str, str]) -> None:
    """Contract: owner/name are both-or-none when provided in config.repo."""
    registry = {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {"description": "Standard", "profile": None}},
        "repos": {"demo": {"tier": "standard", "config": {"repo": repo_block}}},
    }
    with pytest.raises(jsonschema.ValidationError):
        _get_registry_validator().validate(registry)
