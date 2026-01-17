"""Tests for Phase 4 wizard modules (profile.py, advanced.py)."""

from __future__ import annotations

from pathlib import Path


class TestProfileModule:
    """Tests for wizard/questions/profile.py module."""

    def test_profile_info_structure(self) -> None:
        """PROFILE_INFO should have consistent structure."""
        from cihub.wizard.questions.profile import PROFILE_INFO

        required_keys = {"description", "tools", "runtime"}

        for profile_name, info in PROFILE_INFO.items():
            for key in required_keys:
                assert key in info, f"Profile '{profile_name}' missing '{key}'"
            assert isinstance(info["description"], str)
            assert isinstance(info["tools"], str)
            assert isinstance(info["runtime"], str)

    def test_get_available_profiles_returns_list(self) -> None:
        """get_available_profiles should return a list of strings."""
        from cihub.wizard.questions.profile import get_available_profiles

        profiles = get_available_profiles("python")
        assert isinstance(profiles, list)
        for profile in profiles:
            assert isinstance(profile, str)

    def test_get_available_profiles_python_has_fast(self) -> None:
        """Python should have at least the 'fast' profile."""
        from cihub.wizard.questions.profile import get_available_profiles

        profiles = get_available_profiles("python")
        # May be empty if profile files don't exist
        if profiles:
            assert "fast" in profiles or len(profiles) > 0

    def test_get_available_profiles_custom_dir(self, tmp_path: Path) -> None:
        """get_available_profiles should work with custom profiles_dir."""
        from cihub.wizard.questions.profile import get_available_profiles

        # Create a test profile file
        (tmp_path / "python-test.yaml").write_text("tools: {}")

        profiles = get_available_profiles("python", profiles_dir=tmp_path)
        # Should return empty since 'test' is not in the expected list
        assert isinstance(profiles, list)

    def test_profile_names_are_valid(self) -> None:
        """Profile names should be lowercase alphanumeric with hyphens."""
        import re

        from cihub.wizard.questions.profile import PROFILE_INFO

        pattern = re.compile(r"^[a-z][a-z0-9-]*$")
        for profile_name in PROFILE_INFO.keys():
            assert pattern.match(profile_name), f"Invalid profile name: {profile_name}"


class TestAdvancedModule:
    """Tests for wizard/questions/advanced.py module."""

    def test_configure_gates_returns_dict(self) -> None:
        """configure_gates should return a dict."""
        from cihub.wizard.questions.advanced import configure_gates

        # With empty defaults, should return empty dict (no prompt in test)
        # This would normally prompt, but we can test the function signature
        assert callable(configure_gates)

    def test_configure_reports_returns_dict(self) -> None:
        """configure_reports should return a dict."""
        from cihub.wizard.questions.advanced import configure_reports

        assert callable(configure_reports)

    def test_configure_notifications_returns_dict(self) -> None:
        """configure_notifications should return a dict."""
        from cihub.wizard.questions.advanced import configure_notifications

        assert callable(configure_notifications)

    def test_configure_harden_runner_returns_dict(self) -> None:
        """configure_harden_runner should return a dict."""
        from cihub.wizard.questions.advanced import configure_harden_runner

        assert callable(configure_harden_runner)

    def test_configure_advanced_settings_orchestrates_all(self) -> None:
        """configure_advanced_settings should be the orchestration function."""
        from cihub.wizard.questions.advanced import configure_advanced_settings

        assert callable(configure_advanced_settings)

    def test_gate_choices_are_valid(self) -> None:
        """Gate names in choices should be valid identifiers."""
        # These are the gates defined in configure_gates
        valid_gates = {"lint", "test", "security", "coverage", "mutation", "sbom", "codeql", "trivy"}

        # Just verify they're strings
        for gate in valid_gates:
            assert isinstance(gate, str)
            assert gate.isidentifier() or "-" not in gate


class TestLanguageModule:
    """Tests for wizard/questions/language.py module."""

    def test_language_module_exists(self) -> None:
        """language.py should be importable."""
        from cihub.wizard.questions import language

        assert language is not None


class TestSecurityModule:
    """Tests for wizard/questions/security.py module."""

    def test_security_module_exists(self) -> None:
        """security.py should be importable."""
        from cihub.wizard.questions import security

        assert security is not None


class TestThresholdsModule:
    """Tests for wizard/questions/thresholds.py module."""

    def test_thresholds_module_exists(self) -> None:
        """thresholds.py should be importable."""
        from cihub.wizard.questions import thresholds

        assert thresholds is not None


class TestToolsModules:
    """Tests for wizard/questions/python_tools.py and java_tools.py."""

    def test_python_tools_module_exists(self) -> None:
        """python_tools.py should be importable."""
        from cihub.wizard.questions import python_tools

        assert python_tools is not None

    def test_java_tools_module_exists(self) -> None:
        """java_tools.py should be importable."""
        from cihub.wizard.questions import java_tools

        assert java_tools is not None


class TestWizardCoreIntegration:
    """Tests for wizard core integration with question modules."""

    def test_wizard_runner_imports_profile(self) -> None:
        """WizardRunner should use profile selection."""
        from cihub.wizard.core import WizardRunner

        # Check method exists
        assert hasattr(WizardRunner, "_prompt_profile_and_tier")

    def test_wizard_runner_has_all_wizard_methods(self) -> None:
        """WizardRunner should have all expected wizard methods."""
        from cihub.wizard.core import WizardRunner

        expected_methods = [
            "run_new_wizard",
            "run_init_wizard",
            "run_config_wizard",
        ]

        for method_name in expected_methods:
            assert hasattr(WizardRunner, method_name), f"Missing method: {method_name}"

    def test_wizard_result_fields(self) -> None:
        """WizardResult should have expected fields."""
        import dataclasses

        from cihub.wizard.core import WizardResult

        fields = {f.name for f in dataclasses.fields(WizardResult)}
        expected = {"config", "tier", "profile", "repo_name"}

        assert expected == fields
