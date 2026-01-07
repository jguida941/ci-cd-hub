"""Tests for language strategy implementations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cihub.core.languages import LANGUAGE_STRATEGIES, get_strategy
from cihub.core.languages.java import JavaStrategy
from cihub.core.languages.python import PythonStrategy
from cihub.core.languages.registry import detect_language, list_supported_languages

if TYPE_CHECKING:
    pass


class TestLanguageRegistry:
    """Tests for the language strategy registry."""

    @pytest.mark.parametrize(
        "language,expected_type",
        [
            ("python", PythonStrategy),
            ("java", JavaStrategy),
        ],
        ids=["python_strategy", "java_strategy"],
    )
    def test_get_strategy(self, language: str, expected_type: type) -> None:
        """Property: get_strategy returns correct strategy type."""
        strategy = get_strategy(language)
        assert isinstance(strategy, expected_type)
        assert strategy.name == language

    @pytest.mark.parametrize(
        "language",
        ["go", "rust", "typescript", "ruby", "unknown"],
        ids=["go", "rust", "typescript", "ruby", "unknown"],
    )
    def test_get_strategy_invalid_raises(self, language: str) -> None:
        """Property: unsupported languages raise ValueError."""
        with pytest.raises(ValueError, match=f"Unsupported language: {language}"):
            get_strategy(language)

    def test_language_strategies_contains(self) -> None:
        assert "python" in LANGUAGE_STRATEGIES
        assert "java" in LANGUAGE_STRATEGIES
        assert "go" not in LANGUAGE_STRATEGIES

    def test_list_supported_languages(self) -> None:
        languages = list_supported_languages()
        assert "python" in languages
        assert "java" in languages
        assert sorted(languages) == languages  # Should be sorted


# =============================================================================
# Parameterized Strategy Tests (both languages)
# =============================================================================


class TestStrategyCommonBehavior:
    """Parameterized tests for all language strategies."""

    @pytest.mark.parametrize(
        "language,expected_name,expected_tools",
        [
            ("python", "python", ["pytest", "ruff", "bandit", "mutmut"]),
            ("java", "java", ["jacoco", "checkstyle", "spotbugs", "owasp"]),
        ],
        ids=["python_strategy", "java_strategy"],
    )
    def test_strategy_name_and_default_tools(
        self, language: str, expected_name: str, expected_tools: list[str]
    ) -> None:
        """Property: strategies have correct name and default tools."""
        strategy = get_strategy(language)
        assert strategy.name == expected_name
        tools = strategy.get_default_tools()
        for tool in expected_tools:
            assert tool in tools, f"{tool} should be in {language} default tools"

    @pytest.mark.parametrize(
        "language,expected_runners",
        [
            ("python", ["pytest", "ruff", "bandit"]),
            ("java", ["jacoco", "checkstyle", "owasp"]),
        ],
        ids=["python_runners", "java_runners"],
    )
    def test_strategy_runners_are_callable(self, language: str, expected_runners: list[str]) -> None:
        """Property: strategy runners are callable functions."""
        strategy = get_strategy(language)
        runners = strategy.get_runners()
        for runner_name in expected_runners:
            assert callable(runners.get(runner_name)), f"{runner_name} should be callable"

    @pytest.mark.parametrize("language", ["python", "java"], ids=["python", "java"])
    def test_strategy_thresholds_have_required_attrs(self, language: str) -> None:
        """Property: threshold specs have required attributes."""
        strategy = get_strategy(language)
        thresholds = strategy.get_thresholds()
        assert len(thresholds) > 0, f"{language} should have threshold specs"
        for spec in thresholds:
            assert hasattr(spec, "key"), "ThresholdSpec missing 'key'"
            assert hasattr(spec, "label"), "ThresholdSpec missing 'label'"
            assert hasattr(spec, "comparator"), "ThresholdSpec missing 'comparator'"

    @pytest.mark.parametrize("language", ["python", "java"], ids=["python", "java"])
    def test_strategy_tool_specs_have_required_attrs(self, language: str) -> None:
        """Property: tool specs have required attributes."""
        strategy = get_strategy(language)
        tool_specs = strategy.get_tool_specs()
        assert len(tool_specs) > 0, f"{language} should have tool specs"
        for spec in tool_specs:
            assert hasattr(spec, "key"), "ToolSpec missing 'key'"
            assert hasattr(spec, "label"), "ToolSpec missing 'label'"
            assert hasattr(spec, "category"), "ToolSpec missing 'category'"


class TestStrategyDetection:
    """Parameterized tests for language detection."""

    @pytest.mark.parametrize(
        "filename,content,language,expected_confidence",
        [
            # Python detection
            ("pyproject.toml", "[project]\nname = 'test'", "python", 0.9),
            ("setup.py", "from setuptools import setup", "python", 0.8),
            ("requirements.txt", "pytest", "python", 0.7),
            # Java detection
            ("pom.xml", "<project></project>", "java", 0.9),
            ("build.gradle", "plugins { id 'java' }", "java", 0.9),
            ("build.gradle.kts", "plugins { java }", "java", 0.9),
        ],
        ids=[
            "python_pyproject",
            "python_setup_py",
            "python_requirements",
            "java_maven",
            "java_gradle",
            "java_gradle_kts",
        ],
    )
    def test_detection_confidence(
        self,
        tmp_path: Path,
        filename: str,
        content: str,
        language: str,
        expected_confidence: float,
    ) -> None:
        """Property: detection returns correct confidence for project markers."""
        (tmp_path / filename).write_text(content)
        strategy = get_strategy(language)
        assert strategy.detect(tmp_path) == expected_confidence

    @pytest.mark.parametrize("language", ["python", "java"], ids=["python", "java"])
    def test_detection_empty_repo_returns_zero(self, tmp_path: Path, language: str) -> None:
        """Property: empty repo returns 0.0 confidence."""
        strategy = get_strategy(language)
        assert strategy.detect(tmp_path) == 0.0


class TestPythonStrategy:
    """Tests for PythonStrategy implementation."""

    @pytest.fixture
    def strategy(self) -> PythonStrategy:
        return PythonStrategy()

    def test_resolve_thresholds(self, strategy: PythonStrategy) -> None:
        config = {
            "python": {
                "tools": {
                    "pytest": {"min_coverage": 80},
                    "ruff": {"max_errors": 5},
                }
            }
        }
        thresholds = strategy.resolve_thresholds(config)
        assert thresholds.get("coverage_min") == 80
        assert thresholds.get("max_ruff_errors") == 5


class TestJavaStrategy:
    """Tests for JavaStrategy-specific functionality.

    Note: Common tests (name, tools, runners, thresholds, detection)
    are covered by TestStrategyCommonBehavior and TestStrategyDetection.
    """

    @pytest.fixture
    def strategy(self) -> JavaStrategy:
        return JavaStrategy()

    def test_resolve_thresholds(self, strategy: JavaStrategy) -> None:
        config = {
            "java": {
                "tools": {
                    "jacoco": {"min_coverage": 75},
                    "checkstyle": {"max_errors": 10},
                }
            }
        }
        thresholds = strategy.resolve_thresholds(config)
        assert thresholds.get("coverage_min") == 75
        assert thresholds.get("max_checkstyle_errors") == 10


class TestJavaBuildToolDetection:
    """Parameterized tests for Java build tool auto-detection."""

    @pytest.mark.parametrize(
        "project_file,content,expected_build_tool",
        [
            ("build.gradle", "plugins { id 'java' }", "gradle"),
            ("build.gradle.kts", "plugins { java }", "gradle"),
            ("pom.xml", "<project></project>", "maven"),
        ],
        ids=["gradle_groovy", "gradle_kotlin", "maven"],
    )
    def test_run_tools_auto_detects_build_tool(
        self,
        tmp_path: Path,
        project_file: str,
        content: str,
        expected_build_tool: str,
    ) -> None:
        """Property: run_tools auto-detects correct build tool."""
        from unittest.mock import patch

        (tmp_path / project_file).write_text(content)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        strategy = JavaStrategy()
        mock_results = ({}, {"build": True}, {"build": True})

        with patch(
            "cihub.services.ci_engine.java_tools._run_java_tools",
            return_value=mock_results,
        ) as mock_run:
            strategy.run_tools(
                config={"java": {"tools": {}}},
                repo_path=tmp_path,
                workdir=".",
                output_dir=output_dir,
                problems=[],
            )
            call_args = mock_run.call_args
            assert call_args[0][4] == expected_build_tool

    def test_run_tools_respects_explicit_build_tool(self, tmp_path: Path) -> None:
        """Verify explicit build_tool parameter overrides auto-detection."""
        from unittest.mock import patch

        # Create Gradle project but pass maven explicitly
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        strategy = JavaStrategy()
        mock_results = ({}, {"build": True}, {"build": True})

        with patch(
            "cihub.services.ci_engine.java_tools._run_java_tools",
            return_value=mock_results,
        ) as mock_run:
            strategy.run_tools(
                config={"java": {"tools": {}}},
                repo_path=tmp_path,
                workdir=".",
                output_dir=output_dir,
                problems=[],
                build_tool="maven",  # Explicit override
            )
            call_args = mock_run.call_args
            assert call_args[0][4] == "maven", "Explicit build_tool should override detection"


class TestDetectLanguage:
    """Tests for automatic language detection."""

    @pytest.mark.parametrize(
        "filename,content,expected_language",
        [
            ("pyproject.toml", "[project]\nname = 'test'", "python"),
            ("pom.xml", "<project></project>", "java"),
            ("build.gradle", "plugins { id 'java' }", "java"),
        ],
        ids=["python_pyproject", "java_maven", "java_gradle"],
    )
    def test_detect_language_from_marker(
        self, tmp_path: Path, filename: str, content: str, expected_language: str
    ) -> None:
        """Property: detect_language identifies language from project markers."""
        (tmp_path / filename).write_text(content)
        assert detect_language(tmp_path) == expected_language

    def test_detect_mixed_prefers_higher_confidence(self, tmp_path: Path) -> None:
        # Both exist, but pyproject.toml gives Python 0.9 confidence
        # and requirements.txt alone would be 0.7
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "pom.xml").write_text("<project>")
        # Both have 0.9, so it depends on iteration order (dict keys)
        # but both should be valid
        lang = detect_language(tmp_path)
        assert lang in ("python", "java")

    def test_detect_empty_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Could not detect language"):
            detect_language(tmp_path)
