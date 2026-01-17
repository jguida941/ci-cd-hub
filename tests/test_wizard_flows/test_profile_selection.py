"""Tests for wizard profile selection flow."""

from __future__ import annotations

from cihub.utils.paths import hub_root


class TestProfileSelectionHelpers:
    """Tests for profile selection helper functions."""

    def test_get_available_profiles_returns_list(self) -> None:
        """get_available_profiles should return language-specific profiles."""
        from cihub.wizard.questions.profile import get_available_profiles

        python_profiles = get_available_profiles("python")
        assert isinstance(python_profiles, list)

    def test_get_available_profiles_java(self) -> None:
        """get_available_profiles should work for Java."""
        from cihub.wizard.questions.profile import get_available_profiles

        java_profiles = get_available_profiles("java")
        assert isinstance(java_profiles, list)


class TestTierProfileMapping:
    """Tests for tier to profile mapping."""

    def test_tier_strict_has_high_thresholds(self) -> None:
        """Strict tier should have coverage >= 85%."""
        import yaml

        tier_path = hub_root() / "templates" / "profiles" / "tier-strict.yaml"
        if tier_path.exists():
            content = yaml.safe_load(tier_path.read_text())
            thresholds = content.get("thresholds", {})
            coverage = thresholds.get("coverage_min", 0)
            assert coverage >= 85, f"Strict tier coverage should be >= 85, got {coverage}"

    def test_tier_relaxed_has_lower_thresholds(self) -> None:
        """Relaxed tier should have coverage <= 60%."""
        import yaml

        tier_path = hub_root() / "templates" / "profiles" / "tier-relaxed.yaml"
        if tier_path.exists():
            content = yaml.safe_load(tier_path.read_text())
            thresholds = content.get("thresholds", {})
            coverage = thresholds.get("coverage_min", 100)
            assert coverage <= 60, f"Relaxed tier coverage should be <= 60, got {coverage}"


class TestWizardResultStructure:
    """Tests for WizardResult dataclass."""

    def test_wizard_result_has_required_fields(self) -> None:
        """WizardResult should have config, tier, profile, repo_name fields."""
        from cihub.wizard.core import WizardResult

        result = WizardResult(
            config={"language": "python"},
            repo_name="test-repo",
        )
        assert result.config == {"language": "python"}
        assert result.repo_name == "test-repo"
        assert result.tier == "standard"  # default

    def test_wizard_result_optional_fields(self) -> None:
        """WizardResult should support optional tier and profile."""
        from cihub.wizard.core import WizardResult

        result = WizardResult(
            config={},
            repo_name="test",
            tier="strict",
            profile="fast",
        )
        assert result.tier == "strict"
        assert result.profile == "fast"
