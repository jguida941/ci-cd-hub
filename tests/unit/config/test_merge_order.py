"""Tests for config merge order and precedence."""

# TEST-METRICS:

from __future__ import annotations

import yaml

from cihub.utils.paths import hub_root


class TestConfigMergeOrder:
    """Tests for 3-tier config merge order."""

    def test_defaults_provide_base_values(self) -> None:
        """defaults.yaml should provide base configuration values."""
        defaults_path = hub_root() / "config" / "defaults.yaml"
        assert defaults_path.exists(), "defaults.yaml must exist"

        content = yaml.safe_load(defaults_path.read_text())
        assert "python" in content or "java" in content

    def test_deep_merge_preserves_nested_values(self) -> None:
        """deep_merge should preserve nested values from base."""
        from cihub.config import deep_merge

        base = {
            "python": {
                "tools": {
                    "pytest": {"enabled": True},
                    "ruff": {"enabled": True},
                }
            }
        }
        overlay = {
            "python": {
                "tools": {
                    "pytest": {"enabled": False},  # Override
                }
            }
        }

        merged = deep_merge(base, overlay)

        # Overlay should win
        assert merged["python"]["tools"]["pytest"]["enabled"] is False
        # Unspecified values preserved from base
        assert merged["python"]["tools"]["ruff"]["enabled"] is True

    def test_deep_merge_thresholds(self) -> None:
        """deep_merge should handle threshold overrides."""
        from cihub.config import deep_merge

        base = {
            "thresholds": {
                "coverage_min": 70,
            }
        }
        overlay = {
            "thresholds": {
                "coverage_min": 90,  # Override
            }
        }

        merged = deep_merge(base, overlay)

        # Overlay should win
        assert merged["thresholds"]["coverage_min"] == 90


class TestThresholdPrecedence:
    """Tests for threshold precedence rules."""

    def test_tier_profile_applies_thresholds(self) -> None:
        """Tier profile should set threshold values."""
        tier_strict = hub_root() / "templates" / "profiles" / "tier-strict.yaml"
        if tier_strict.exists():
            content = yaml.safe_load(tier_strict.read_text())
            assert "thresholds" in content

    def test_deep_merge_threshold_override(self) -> None:
        """Repo-specific thresholds should override tier defaults via deep_merge."""
        from cihub.config import deep_merge

        tier_thresholds = {
            "thresholds": {
                "coverage_min": 85,  # From tier-strict
            }
        }
        repo_override = {
            "thresholds": {
                "coverage_min": 95,  # Repo wants higher
            }
        }

        merged = deep_merge(tier_thresholds, repo_override)
        assert merged["thresholds"]["coverage_min"] == 95


class TestToolEnablement:
    """Tests for tool enablement precedence."""

    def test_tool_enabled_boolean_true(self) -> None:
        """tool_enabled should return True for tool: true."""
        from cihub.config import tool_enabled

        config = {
            "python": {
                "tools": {
                    "pytest": True,
                }
            }
        }
        assert tool_enabled(config, "pytest", "python") is True

    def test_tool_enabled_object_enabled_false(self) -> None:
        """tool_enabled should return False for tool: {enabled: false}."""
        from cihub.config import tool_enabled

        config = {
            "python": {
                "tools": {
                    "pytest": {"enabled": False},
                }
            }
        }
        assert tool_enabled(config, "pytest", "python") is False

    def test_tool_enabled_missing_uses_default(self) -> None:
        """Missing tool should use default value."""
        from cihub.config import tool_enabled

        config = {"python": {"tools": {}}}
        # Default is False for missing tools
        assert tool_enabled(config, "pytest", "python", default=False) is False
        assert tool_enabled(config, "pytest", "python", default=True) is True
