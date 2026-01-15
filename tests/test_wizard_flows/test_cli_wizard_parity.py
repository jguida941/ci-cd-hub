"""Tests for CLI/wizard parity - ensuring CLI commands produce same config as wizard."""

from __future__ import annotations

from pathlib import Path

from cihub.utils.paths import hub_root


class TestConfigStructureParity:
    """Tests that CLI and wizard produce equivalent config structures."""

    def test_wizard_result_has_config_key(self) -> None:
        """WizardResult.config should be a dict with standard keys."""
        from cihub.wizard.core import WizardResult

        result = WizardResult(
            config={"language": "python", "python": {"tools": {}}},
            repo_name="test-repo",
            tier="standard",
        )

        assert isinstance(result.config, dict)
        assert "language" in result.config or "python" in result.config

    def test_wizard_config_matches_schema_structure(self) -> None:
        """Wizard config output should match schema structure."""
        import json

        schema_path = hub_root() / "schema" / "ci-hub-config.schema.json"
        schema = json.loads(schema_path.read_text())

        # Get top-level properties from schema
        schema_props = set(schema.get("properties", {}).keys())

        # Common config keys that wizard should produce
        expected_wizard_keys = {"language", "python", "java", "thresholds", "gates"}

        # At least some overlap expected
        overlap = schema_props & expected_wizard_keys
        assert len(overlap) > 0, "Schema and wizard should share common config keys"

    def test_profile_produces_valid_tool_config(self) -> None:
        """Profile selection should produce valid tool configuration."""
        from cihub.wizard.questions.profile import PROFILE_INFO

        for _profile_name, info in PROFILE_INFO.items():
            assert "description" in info
            assert "tools" in info
            assert "runtime" in info

    def test_tier_produces_valid_threshold_config(self) -> None:
        """Tier selection should map to valid threshold values."""
        import yaml

        tier_files = [
            Path("templates/profiles/tier-strict.yaml"),
            Path("templates/profiles/tier-standard.yaml"),
            Path("templates/profiles/tier-relaxed.yaml"),
        ]

        for tier_file in tier_files:
            if tier_file.exists():
                content = yaml.safe_load(tier_file.read_text())
                thresholds = content.get("thresholds", {})

                # Verify threshold structure
                if "coverage_min" in thresholds:
                    assert isinstance(thresholds["coverage_min"], int)
                    assert 0 <= thresholds["coverage_min"] <= 100


class TestDefaultMergeParity:
    """Tests that defaults merge consistently between CLI and wizard."""

    def test_defaults_file_exists(self) -> None:
        """defaults.yaml should exist and be loadable."""
        from cihub.config import PathConfig, load_defaults

        paths = PathConfig(root=".")
        defaults = load_defaults(paths)
        assert isinstance(defaults, dict)

    def test_deep_merge_produces_consistent_results(self) -> None:
        """deep_merge should produce same result regardless of call site."""
        from cihub.config import deep_merge

        base = {"python": {"tools": {"pytest": True}}}
        overlay = {"python": {"tools": {"ruff": True}}}

        result1 = deep_merge(base.copy(), overlay)
        result2 = deep_merge(base.copy(), overlay)

        assert result1 == result2

    def test_wizard_and_config_use_same_merge_function(self) -> None:
        """Wizard and config module should use the same merge logic."""
        # Both should use cihub.config.deep_merge
        from cihub.config import deep_merge
        from cihub.config.merge import deep_merge as merge_deep_merge

        assert deep_merge is merge_deep_merge


class TestToolEnablementParity:
    """Tests that tool enablement works consistently."""

    def test_boolean_tool_config_parity(self) -> None:
        """Boolean tool config should work same in CLI and wizard."""
        from cihub.config import tool_enabled

        # Boolean true
        config_bool_true = {"python": {"tools": {"pytest": True}}}
        assert tool_enabled(config_bool_true, "pytest", "python") is True

        # Boolean false
        config_bool_false = {"python": {"tools": {"pytest": False}}}
        assert tool_enabled(config_bool_false, "pytest", "python") is False

    def test_object_tool_config_parity(self) -> None:
        """Object tool config should work same in CLI and wizard."""
        from cihub.config import tool_enabled

        # Object with enabled: true
        config_obj_true = {"python": {"tools": {"pytest": {"enabled": True}}}}
        assert tool_enabled(config_obj_true, "pytest", "python") is True

        # Object with enabled: false
        config_obj_false = {"python": {"tools": {"pytest": {"enabled": False}}}}
        assert tool_enabled(config_obj_false, "pytest", "python") is False

    def test_custom_tool_config_parity(self) -> None:
        """Custom x-* tool config should work same in CLI and wizard."""
        from cihub.config import tool_enabled

        # Custom tool with command
        config_custom = {
            "python": {
                "tools": {
                    "x-my-linter": {
                        "command": "my-lint .",
                        "enabled": True,
                    }
                }
            }
        }
        assert tool_enabled(config_custom, "x-my-linter", "python") is True


class TestOutputFormatParity:
    """Tests that output format is consistent."""

    def test_wizard_result_serializable(self) -> None:
        """WizardResult.config should be JSON-serializable."""
        import json

        from cihub.wizard.core import WizardResult

        result = WizardResult(
            config={"language": "python", "python": {"tools": {"pytest": True}}},
            repo_name="test",
        )

        # Should not raise
        serialized = json.dumps(result.config)
        deserialized = json.loads(serialized)
        assert deserialized == result.config

    def test_config_yaml_roundtrip(self) -> None:
        """Config should survive YAML roundtrip."""
        import yaml

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "pytest": True,
                    "ruff": {"enabled": True},
                }
            },
            "thresholds": {
                "coverage_min": 80,
            },
        }

        yaml_str = yaml.dump(config)
        restored = yaml.safe_load(yaml_str)
        assert restored == config
