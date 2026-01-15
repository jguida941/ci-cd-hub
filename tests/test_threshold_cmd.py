"""Behavior tests for threshold command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from cihub.commands.threshold_cmd import (
    _cmd_compare,
    _cmd_get,
    _cmd_list,
    _cmd_reset,
    _cmd_set,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def _write_registry(tmp_path: Path, registry: dict[str, object]) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "registry.json").write_text(json.dumps(registry), encoding="utf-8")


def _base_registry() -> dict[str, object]:
    return {
        "schema_version": "cihub-registry-v1",
        "tiers": {
            "standard": {"description": "Standard tier"},
            "strict": {
                "description": "Strict tier",
                "config": {"thresholds": {"coverage_min": 90}},
            },
        },
        "repos": {
            "alpha": {"tier": "standard"},
            "beta": {"tier": "strict"},
            "gamma": {"tier": "standard", "overrides": {"coverage_min": 80}},
        },
    }


class TestThresholdGet:
    """Tests for threshold get subcommand."""

    def test_get_global_default(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            key="coverage_min", repo=None, tier=None, effective=False
        )
        result = _cmd_get(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["value"] == 70  # default
        assert result.data["default"] == 70

    def test_get_repo_effective_shows_tier_inheritance(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            key="coverage_min", repo="beta", tier=None, effective=True
        )
        result = _cmd_get(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["mode"] == "effective"
        # beta is in strict tier which has coverage_min=90
        assert result.data["value"] == 90

    def test_get_repo_raw_shows_overrides_only(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Verify --effective=False returns raw overrides, not effective values."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        # gamma has override coverage_min=80
        args = argparse.Namespace(
            key="coverage_min", repo="gamma", tier=None, effective=False
        )
        result = _cmd_get(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["mode"] == "raw"
        assert result.data["value"] == 80
        assert result.data["is_override"] is True

    def test_get_repo_raw_returns_none_when_not_overridden(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Verify raw mode returns None for non-overridden thresholds."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        # alpha has no overrides
        args = argparse.Namespace(
            key="coverage_min", repo="alpha", tier=None, effective=False
        )
        result = _cmd_get(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["mode"] == "raw"
        assert result.data["value"] is None
        assert result.data["is_override"] is False

    def test_get_invalid_key_fails(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            key="invalid_threshold", repo=None, tier=None, effective=False
        )
        result = _cmd_get(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-THRESHOLD-INVALID-KEY"


class TestThresholdSet:
    """Tests for threshold set subcommand."""

    def test_set_repo_override(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            key="coverage_min",
            value="85",
            repo="alpha",
            tier=None,
            all_repos=False,
        )
        result = _cmd_set(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["value"] == 85

        # Verify it was persisted
        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        assert registry["repos"]["alpha"]["overrides"]["coverage_min"] == 85

    def test_set_sparse_storage_skips_default_value(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Verify setting a value equal to effective default doesn't store it."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        # alpha is in standard tier, default coverage_min is 70
        args = argparse.Namespace(
            key="coverage_min",
            value="70",
            repo="alpha",
            tier=None,
            all_repos=False,
        )
        result = _cmd_set(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["action"] == "no_change"

        # Verify no override was stored
        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        assert "overrides" not in registry["repos"]["alpha"]

    def test_set_sparse_storage_removes_redundant_override(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Verify setting value equal to default removes existing override."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        # gamma has override coverage_min=80, setting to 70 (default) should remove it
        args = argparse.Namespace(
            key="coverage_min",
            value="70",
            repo="gamma",
            tier=None,
            all_repos=False,
        )
        result = _cmd_set(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["action"] == "removed_override"

        # Verify override was removed
        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        assert "coverage_min" not in registry["repos"]["gamma"].get("overrides", {})

    def test_set_float_threshold(self, tmp_path: Path, monkeypatch) -> None:
        """Verify CVSS thresholds are stored as floats."""
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(
            key="owasp_cvss_fail",
            value="8.5",
            repo="alpha",
            tier=None,
            all_repos=False,
        )
        result = _cmd_set(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["value"] == 8.5
        assert isinstance(result.data["value"], float)


class TestThresholdList:
    """Tests for threshold list subcommand."""

    def test_list_all_thresholds(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(category=None, repo=None, diff=False)
        result = _cmd_list(args)

        assert result.exit_code == EXIT_SUCCESS
        assert len(result.data["thresholds"]) == 14  # all 14 thresholds

    def test_list_by_category(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(category="security", repo=None, diff=False)
        result = _cmd_list(args)

        assert result.exit_code == EXIT_SUCCESS
        for t in result.data["thresholds"]:
            assert t["category"] == "security"


class TestThresholdReset:
    """Tests for threshold reset subcommand."""

    def test_reset_removes_override(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        # gamma has coverage_min override
        args = argparse.Namespace(
            key="coverage_min", repo="gamma", tier=None, all_repos=False
        )
        result = _cmd_reset(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "coverage_min" in result.data["reset"]

        # Verify it was removed
        registry = json.loads((tmp_path / "config" / "registry.json").read_text())
        assert "coverage_min" not in registry["repos"]["gamma"].get("overrides", {})


class TestThresholdCompare:
    """Tests for threshold compare subcommand."""

    def test_compare_finds_differences(self, tmp_path: Path, monkeypatch) -> None:
        _write_registry(tmp_path, _base_registry())
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        # alpha (standard, default 70) vs gamma (standard, override 80)
        args = argparse.Namespace(repo1="alpha", repo2="gamma", effective=True)
        result = _cmd_compare(args)

        assert result.exit_code == EXIT_SUCCESS
        assert len(result.data["differences"]) > 0
        coverage_diff = next(
            d for d in result.data["differences"] if d["key"] == "coverage_min"
        )
        assert coverage_diff["repo1_value"] == 70
        assert coverage_diff["repo2_value"] == 80
