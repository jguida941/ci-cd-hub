"""Tests for registry service functionality."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestRegistryServiceBasics:
    """Basic tests for registry service."""

    @pytest.fixture
    def temp_registry(self, tmp_path: Path) -> Path:
        """Create a temporary registry file."""
        registry_path = tmp_path / "registry.json"
        registry_path.write_text(json.dumps({"repos": {}}))
        return registry_path

    def test_list_repos_with_registry(self, temp_registry: Path) -> None:
        """list_repos should return list from registry data."""
        from cihub.services.registry_service import list_repos

        registry = {"repos": {"test-repo": {"language": "python"}}}
        result = list_repos(registry)
        # Returns a list of repo info dicts
        assert isinstance(result, list)

    def test_list_repos_empty_registry(self) -> None:
        """list_repos should return empty list for empty registry."""
        from cihub.services.registry_service import list_repos

        registry = {"repos": {}}
        result = list_repos(registry)
        assert result == []

    def test_get_registry_path_returns_path(self) -> None:
        """_get_registry_path should return a Path object."""
        from cihub.services.registry_service import _get_registry_path

        path = _get_registry_path()
        assert isinstance(path, Path)


class TestRegistryThresholdNormalization:
    """Tests for threshold key normalization in registry."""

    def test_normalize_threshold_dict_handles_integers(self) -> None:
        """_normalize_threshold_dict_inplace should preserve integers."""
        from cihub.services.registry_service import _normalize_threshold_dict_inplace

        thresholds = {
            "coverage_min": 80,
            "mutation_score_min": 70,
        }
        _normalize_threshold_dict_inplace(thresholds)

        # Should preserve integer values
        assert thresholds.get("coverage_min") == 80

    def test_as_int_converts_strings(self) -> None:
        """_as_int should convert string numbers to integers."""
        from cihub.services.registry_service import _as_int

        assert _as_int("80") == 80
        assert _as_int(80) == 80
        assert _as_int(None) is None


class TestRegistrySyncToConfigs:
    """Tests for sync_to_configs functionality."""

    def test_sync_to_configs_callable(self) -> None:
        """sync_to_configs should be callable."""
        from cihub.services.registry_service import sync_to_configs

        assert callable(sync_to_configs)


class TestRegistryDriftDetection:
    """Tests for registry drift detection."""

    def test_compute_diff_callable(self) -> None:
        """compute_diff should be callable."""
        from cihub.services.registry_service import compute_diff

        assert callable(compute_diff)

    def test_compute_diff_with_empty_registry(self, tmp_path: Path) -> None:
        """compute_diff should work with empty registry."""
        from cihub.services.registry_service import compute_diff

        registry = {"repos": {}}
        configs_dir = tmp_path / "config" / "repos"
        configs_dir.mkdir(parents=True)

        diff = compute_diff(registry, configs_dir)
        # Returns a list of diff entries
        assert isinstance(diff, list)


class TestRegistryBootstrap:
    """Tests for registry bootstrap from existing configs."""

    def test_bootstrap_from_configs_callable(self) -> None:
        """bootstrap_from_configs should be callable."""
        from cihub.services.registry_service import bootstrap_from_configs

        assert callable(bootstrap_from_configs)
