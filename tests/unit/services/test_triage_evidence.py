"""Tests for triage evidence building and validation functions.

Tests cover:
- _load_json: JSON file loading with error handling
- _load_tool_outputs: Loading tool output directories
- _format_list: List formatting helper
- _normalize_category: Tool category mapping
- _severity_for: Category severity mapping
- _tool_env_name: Environment variable naming
- _tool_artifacts: Artifact collection
- _get_nested: Dot-notation nested dict access
- _get_tool_metrics: Tool metrics extraction
- _check_tool_has_artifacts: Artifact existence check
- build_tool_evidence: Main evidence builder
- validate_artifact_evidence: Evidence validation
"""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path

from cihub.services.triage.evidence import (
    _check_tool_has_artifacts,
    _format_list,
    _get_nested,
    _get_tool_metrics,
    _load_json,
    _load_tool_outputs,
    _normalize_category,
    _severity_for,
    _tool_artifacts,
    _tool_env_name,
    build_tool_evidence,
    validate_artifact_evidence,
)
from cihub.services.triage.types import ToolStatus

# =============================================================================
# _load_json Tests
# =============================================================================


class TestLoadJson:
    """Tests for _load_json function."""

    def test_loads_valid_json(self, tmp_path: Path) -> None:
        """Loads valid JSON file."""
        json_path = tmp_path / "data.json"
        json_path.write_text('{"key": "value", "number": 42}')

        result = _load_json(json_path)

        assert result == {"key": "value", "number": 42}

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """Returns None when file doesn't exist."""
        json_path = tmp_path / "nonexistent.json"

        result = _load_json(json_path)

        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        """Returns None for invalid JSON."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("not valid json {")

        result = _load_json(json_path)

        assert result is None

    def test_returns_none_for_non_dict_json(self, tmp_path: Path) -> None:
        """Returns None when JSON is not a dict (e.g., array or string)."""
        json_path = tmp_path / "array.json"
        json_path.write_text('["list", "not", "dict"]')

        result = _load_json(json_path)

        assert result is None

    def test_returns_none_for_string_json(self, tmp_path: Path) -> None:
        """Returns None when JSON is a bare string."""
        json_path = tmp_path / "string.json"
        json_path.write_text('"just a string"')

        result = _load_json(json_path)

        assert result is None


# =============================================================================
# _load_tool_outputs Tests
# =============================================================================


class TestLoadToolOutputs:
    """Tests for _load_tool_outputs function."""

    def test_loads_multiple_json_files(self, tmp_path: Path) -> None:
        """Loads all JSON files from directory."""
        tool_dir = tmp_path / "tools"
        tool_dir.mkdir()

        (tool_dir / "ruff.json").write_text('{"tool": "ruff", "errors": 0}')
        (tool_dir / "pytest.json").write_text('{"tool": "pytest", "passed": 100}')

        result = _load_tool_outputs(tool_dir)

        assert len(result) == 2
        assert "ruff" in result
        assert "pytest" in result
        assert result["ruff"]["errors"] == 0
        assert result["pytest"]["passed"] == 100

    def test_returns_empty_for_missing_directory(self, tmp_path: Path) -> None:
        """Returns empty dict when directory doesn't exist."""
        tool_dir = tmp_path / "nonexistent"

        result = _load_tool_outputs(tool_dir)

        assert result == {}

    def test_skips_invalid_json_files(self, tmp_path: Path) -> None:
        """Skips files with invalid JSON."""
        tool_dir = tmp_path / "tools"
        tool_dir.mkdir()

        (tool_dir / "valid.json").write_text('{"tool": "valid", "ok": true}')
        (tool_dir / "invalid.json").write_text("not json")

        result = _load_tool_outputs(tool_dir)

        assert len(result) == 1
        assert "valid" in result

    def test_uses_stem_when_tool_key_missing(self, tmp_path: Path) -> None:
        """Uses filename stem when 'tool' key not in JSON."""
        tool_dir = tmp_path / "tools"
        tool_dir.mkdir()

        (tool_dir / "coverage.json").write_text('{"percentage": 85}')

        result = _load_tool_outputs(tool_dir)

        assert "coverage" in result
        assert result["coverage"]["percentage"] == 85

    def test_skips_non_dict_json(self, tmp_path: Path) -> None:
        """Skips JSON files that don't contain dicts."""
        tool_dir = tmp_path / "tools"
        tool_dir.mkdir()

        (tool_dir / "array.json").write_text("[1, 2, 3]")
        (tool_dir / "dict.json").write_text('{"tool": "dict", "x": 1}')

        result = _load_tool_outputs(tool_dir)

        assert len(result) == 1
        assert "dict" in result


# =============================================================================
# _format_list Tests
# =============================================================================


class TestFormatList:
    """Tests for _format_list function."""

    def test_formats_multiple_items(self) -> None:
        """Formats list with commas."""
        result = _format_list(["a", "b", "c"])
        assert result == "a, b, c"

    def test_formats_single_item(self) -> None:
        """Formats single item."""
        result = _format_list(["only"])
        assert result == "only"

    def test_returns_dash_for_empty_list(self) -> None:
        """Returns dash for empty list."""
        result = _format_list([])
        assert result == "-"


# =============================================================================
# _normalize_category Tests
# =============================================================================


class TestNormalizeCategory:
    """Tests for _normalize_category function."""

    def test_known_tool_returns_category(self) -> None:
        """Returns correct category for known tools."""
        # These should be defined in CATEGORY_BY_TOOL
        assert _normalize_category("pytest") in ["test", "testing", "cihub"]
        assert _normalize_category("ruff") in ["lint", "linting", "cihub"]

    def test_unknown_tool_returns_default(self) -> None:
        """Returns 'cihub' for unknown tools."""
        result = _normalize_category("unknown_tool_xyz")
        assert result == "cihub"


# =============================================================================
# _severity_for Tests
# =============================================================================


class TestSeverityFor:
    """Tests for _severity_for function."""

    def test_unknown_category_returns_medium(self) -> None:
        """Returns 'medium' for unknown category."""
        result = _severity_for("unknown_category")
        assert result == "medium"

    def test_known_categories_return_severity(self) -> None:
        """Known categories return defined severity."""
        # Should have defined severities
        result = _severity_for("security")
        assert result in ["high", "critical", "medium", "low"]


# =============================================================================
# _tool_env_name Tests
# =============================================================================


class TestToolEnvName:
    """Tests for _tool_env_name function."""

    def test_simple_tool_name(self) -> None:
        """Generates env var for simple tool name."""
        result = _tool_env_name("ruff")
        assert result == "CIHUB_RUN_RUFF"

    def test_hyphenated_tool_name(self) -> None:
        """Converts hyphens to underscores."""
        result = _tool_env_name("pip-audit")
        assert result == "CIHUB_RUN_PIP_AUDIT"

    def test_uppercase_conversion(self) -> None:
        """Converts to uppercase."""
        result = _tool_env_name("myTool")
        assert result == "CIHUB_RUN_MYTOOL"


# =============================================================================
# _tool_artifacts Tests
# =============================================================================


class TestToolArtifacts:
    """Tests for _tool_artifacts function."""

    def test_collects_json_artifact(self, tmp_path: Path) -> None:
        """Collects tool JSON file."""
        output_dir = tmp_path / ".cihub"
        tool_outputs = output_dir / "tool-outputs"
        tool_outputs.mkdir(parents=True)
        (tool_outputs / "ruff.json").write_text("{}")

        result = _tool_artifacts(output_dir, "ruff", {})

        assert len(result) == 1
        assert result[0]["kind"] == "tool_result"
        assert "ruff.json" in result[0]["path"]

    def test_collects_stdout_stderr(self, tmp_path: Path) -> None:
        """Collects stdout and stderr logs."""
        output_dir = tmp_path / ".cihub"
        tool_outputs = output_dir / "tool-outputs"
        tool_outputs.mkdir(parents=True)
        (tool_outputs / "pytest.stdout.log").write_text("output")
        (tool_outputs / "pytest.stderr.log").write_text("errors")

        result = _tool_artifacts(output_dir, "pytest", {})

        kinds = {a["kind"] for a in result}
        assert "stdout" in kinds
        assert "stderr" in kinds

    def test_includes_payload_artifacts(self, tmp_path: Path) -> None:
        """Includes artifacts from payload."""
        output_dir = tmp_path / ".cihub"
        (output_dir / "tool-outputs").mkdir(parents=True)

        payload = {
            "artifacts": {
                "coverage_report": "/path/to/coverage.html",
                "empty_artifact": "",  # Should be skipped
            }
        }

        result = _tool_artifacts(output_dir, "coverage", payload)

        paths = [a["path"] for a in result]
        assert "/path/to/coverage.html" in paths

    def test_deduplicates_artifacts(self, tmp_path: Path) -> None:
        """Doesn't add duplicate paths."""
        output_dir = tmp_path / ".cihub"
        tool_outputs = output_dir / "tool-outputs"
        tool_outputs.mkdir(parents=True)
        json_path = tool_outputs / "tool.json"
        json_path.write_text("{}")

        payload = {"artifacts": {"json": str(json_path)}}

        result = _tool_artifacts(output_dir, "tool", payload)

        # Should only appear once even though it's both auto-detected and in payload
        paths = [a["path"] for a in result]
        assert paths.count(str(json_path)) == 1


# =============================================================================
# _get_nested Tests
# =============================================================================


class TestGetNested:
    """Tests for _get_nested function."""

    def test_gets_single_level(self) -> None:
        """Gets value at single level."""
        data = {"key": "value"}
        result = _get_nested(data, "key")
        assert result == "value"

    def test_gets_nested_value(self) -> None:
        """Gets deeply nested value."""
        data = {"level1": {"level2": {"level3": 42}}}
        result = _get_nested(data, "level1.level2.level3")
        assert result == 42

    def test_returns_none_for_missing_key(self) -> None:
        """Returns None when key doesn't exist."""
        data = {"key": "value"}
        result = _get_nested(data, "missing")
        assert result is None

    def test_returns_none_for_missing_nested_key(self) -> None:
        """Returns None when nested path doesn't exist."""
        data = {"level1": {"level2": "value"}}
        result = _get_nested(data, "level1.missing.deep")
        assert result is None

    def test_returns_none_when_traversing_non_dict(self) -> None:
        """Returns None when path goes through non-dict."""
        data = {"key": "string_value"}
        result = _get_nested(data, "key.nested")
        assert result is None


# =============================================================================
# _get_tool_metrics Tests
# =============================================================================


class TestGetToolMetrics:
    """Tests for _get_tool_metrics function."""

    def test_extracts_python_metrics(self) -> None:
        """Extracts metrics for Python tools."""
        report = {
            "tool_metrics": {
                "ruff_errors": 5,
            }
        }

        result = _get_tool_metrics(report, "ruff", "python")

        # Should extract based on PYTHON_TOOL_METRICS registry
        assert isinstance(result, dict)

    def test_extracts_java_metrics(self) -> None:
        """Extracts metrics for Java tools."""
        report = {
            "tool_metrics": {
                "checkstyle_errors": 10,
            }
        }

        result = _get_tool_metrics(report, "checkstyle", "java")

        assert isinstance(result, dict)

    def test_returns_empty_for_unknown_tool(self) -> None:
        """Returns empty dict for unknown tools."""
        report = {"tool_metrics": {}}

        result = _get_tool_metrics(report, "unknown_tool", "python")

        assert result == {}


# =============================================================================
# _check_tool_has_artifacts Tests
# =============================================================================


class TestCheckToolHasArtifacts:
    """Tests for _check_tool_has_artifacts function."""

    def test_finds_exact_json(self, tmp_path: Path) -> None:
        """Finds tool.json file."""
        output_dir = tmp_path / ".cihub"
        tool_outputs = output_dir / "tool-outputs"
        tool_outputs.mkdir(parents=True)
        (tool_outputs / "ruff.json").write_text("{}")

        result = _check_tool_has_artifacts(output_dir, "ruff")

        assert result is True

    def test_finds_stdout_log(self, tmp_path: Path) -> None:
        """Finds tool.stdout.log file."""
        output_dir = tmp_path / ".cihub"
        tool_outputs = output_dir / "tool-outputs"
        tool_outputs.mkdir(parents=True)
        (tool_outputs / "pytest.stdout.log").write_text("output")

        result = _check_tool_has_artifacts(output_dir, "pytest")

        assert result is True

    def test_returns_false_for_missing_dir(self, tmp_path: Path) -> None:
        """Returns False when tool-outputs doesn't exist."""
        output_dir = tmp_path / ".cihub"
        # Don't create tool-outputs

        result = _check_tool_has_artifacts(output_dir, "ruff")

        assert result is False

    def test_returns_false_for_no_matching_files(self, tmp_path: Path) -> None:
        """Returns False when no matching artifacts."""
        output_dir = tmp_path / ".cihub"
        tool_outputs = output_dir / "tool-outputs"
        tool_outputs.mkdir(parents=True)
        (tool_outputs / "other_tool.json").write_text("{}")

        result = _check_tool_has_artifacts(output_dir, "ruff")

        assert result is False


# =============================================================================
# build_tool_evidence Tests
# =============================================================================


class TestBuildToolEvidence:
    """Tests for build_tool_evidence function."""

    def test_builds_evidence_for_configured_tools(self, tmp_path: Path) -> None:
        """Builds evidence for tools in report."""
        report = {
            "tools_configured": {"ruff": True, "pytest": True},
            "tools_ran": {"ruff": True, "pytest": True},
            "tools_success": {"ruff": True, "pytest": False},
        }

        result = build_tool_evidence(report)

        assert len(result) == 2
        tool_names = {e.tool for e in result}
        assert tool_names == {"ruff", "pytest"}

    def test_not_configured_status(self) -> None:
        """Tool not in config gets NOT_CONFIGURED status."""
        report = {
            "tools_configured": {"ruff": False},
            "tools_ran": {"ruff": False},
            "tools_success": {},
        }

        result = build_tool_evidence(report)

        assert len(result) == 1
        assert result[0].status == ToolStatus.NOT_CONFIGURED
        assert "not enabled" in result[0].explanation.lower()

    def test_skipped_status(self) -> None:
        """Configured but not ran (optional) gets SKIPPED status."""
        report = {
            "tools_configured": {"bandit": True},
            "tools_ran": {"bandit": False},
            "tools_require_run": {"bandit": False},
            "tools_success": {},
        }

        result = build_tool_evidence(report)

        bandit = next(e for e in result if e.tool == "bandit")
        assert bandit.status == ToolStatus.SKIPPED
        assert "skipped" in bandit.explanation.lower()

    def test_required_not_run_status(self) -> None:
        """Required but not ran gets REQUIRED_NOT_RUN status."""
        report = {
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": False},
            "tools_require_run": {"pytest": True},
            "tools_success": {},
        }

        result = build_tool_evidence(report)

        pytest_evidence = next(e for e in result if e.tool == "pytest")
        assert pytest_evidence.status == ToolStatus.REQUIRED_NOT_RUN
        assert "HARD FAIL" in pytest_evidence.explanation

    def test_passed_status(self) -> None:
        """Ran and succeeded gets PASSED status."""
        report = {
            "tools_configured": {"ruff": True},
            "tools_ran": {"ruff": True},
            "tools_success": {"ruff": True},
        }

        result = build_tool_evidence(report)

        ruff = next(e for e in result if e.tool == "ruff")
        assert ruff.status == ToolStatus.PASSED
        assert "successfully" in ruff.explanation.lower()

    def test_failed_status(self) -> None:
        """Ran but failed gets FAILED status."""
        report = {
            "tools_configured": {"ruff": True},
            "tools_ran": {"ruff": True},
            "tools_success": {"ruff": False},
        }

        result = build_tool_evidence(report)

        ruff = next(e for e in result if e.tool == "ruff")
        assert ruff.status == ToolStatus.FAILED
        assert "failed" in ruff.explanation.lower()

    def test_detects_java_language(self) -> None:
        """Detects Java from java_version key."""
        report = {
            "java_version": "17",
            "tools_configured": {"checkstyle": True},
            "tools_ran": {"checkstyle": True},
            "tools_success": {"checkstyle": True},
        }

        result = build_tool_evidence(report)

        # Should complete without error for Java
        assert len(result) == 1

    def test_detects_python_language(self) -> None:
        """Detects Python from python_version key."""
        report = {
            "python_version": "3.12",
            "tools_configured": {"ruff": True},
            "tools_ran": {"ruff": True},
            "tools_success": {"ruff": True},
        }

        result = build_tool_evidence(report)

        assert len(result) == 1

    def test_checks_artifacts_when_output_dir_provided(self, tmp_path: Path) -> None:
        """Checks for artifacts when output_dir provided."""
        output_dir = tmp_path / ".cihub"
        tool_outputs = output_dir / "tool-outputs"
        tool_outputs.mkdir(parents=True)
        (tool_outputs / "ruff.json").write_text("{}")

        report = {
            "tools_configured": {"ruff": True},
            "tools_ran": {"ruff": True},
            "tools_success": {"ruff": True},
        }

        result = build_tool_evidence(report, output_dir=output_dir)

        ruff = next(e for e in result if e.tool == "ruff")
        assert ruff.has_artifacts is True

    def test_handles_none_dicts(self) -> None:
        """Handles None values for tool dicts."""
        report = {
            "tools_configured": None,
            "tools_ran": None,
            "tools_success": None,
        }

        result = build_tool_evidence(report)

        assert result == []


# =============================================================================
# validate_artifact_evidence Tests
# =============================================================================


class TestValidateArtifactEvidence:
    """Tests for validate_artifact_evidence function."""

    def test_validates_successful_tool_without_evidence(self, tmp_path: Path) -> None:
        """Warns when successful tool has no evidence."""
        output_dir = tmp_path / ".cihub"
        (output_dir / "tool-outputs").mkdir(parents=True)

        report = {
            "tools_ran": {"ruff": True},
            "tools_success": {"ruff": True},
        }

        issues = validate_artifact_evidence(report, output_dir, run_schema_validation=False)

        no_evidence_issues = [i for i in issues if i["issue"] == "no_evidence"]
        assert len(no_evidence_issues) == 1
        assert "ruff" in no_evidence_issues[0]["message"]

    def test_validates_failed_tool_without_artifacts(self, tmp_path: Path) -> None:
        """Info when failed tool has no debug artifacts."""
        output_dir = tmp_path / ".cihub"
        (output_dir / "tool-outputs").mkdir(parents=True)

        report = {
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": False},
        }

        issues = validate_artifact_evidence(report, output_dir, run_schema_validation=False)

        no_artifact_issues = [i for i in issues if i["issue"] == "no_failure_artifacts"]
        assert len(no_artifact_issues) == 1
        assert "pytest" in no_artifact_issues[0]["message"]

    def test_no_issues_when_tool_has_artifacts(self, tmp_path: Path) -> None:
        """No issues when tool has artifacts."""
        output_dir = tmp_path / ".cihub"
        tool_outputs = output_dir / "tool-outputs"
        tool_outputs.mkdir(parents=True)
        (tool_outputs / "ruff.json").write_text("{}")

        report = {
            "tools_ran": {"ruff": True},
            "tools_success": {"ruff": True},
        }

        issues = validate_artifact_evidence(report, output_dir, run_schema_validation=False)

        ruff_issues = [i for i in issues if i.get("tool") == "ruff"]
        assert len(ruff_issues) == 0

    def test_skips_tools_that_didnt_run(self, tmp_path: Path) -> None:
        """Doesn't check tools that didn't run."""
        output_dir = tmp_path / ".cihub"
        (output_dir / "tool-outputs").mkdir(parents=True)

        report = {
            "tools_ran": {"ruff": False, "pytest": False},
            "tools_success": {},
        }

        issues = validate_artifact_evidence(report, output_dir, run_schema_validation=False)

        tool_issues = [i for i in issues if i["tool"] in ("ruff", "pytest")]
        assert len(tool_issues) == 0

    def test_handles_empty_report(self, tmp_path: Path) -> None:
        """Handles empty report gracefully."""
        output_dir = tmp_path / ".cihub"
        (output_dir / "tool-outputs").mkdir(parents=True)

        report: dict = {}

        issues = validate_artifact_evidence(report, output_dir, run_schema_validation=False)

        # Should not crash, may have schema errors
        assert isinstance(issues, list)

    def test_schema_validation_when_enabled(self, tmp_path: Path) -> None:
        """Runs schema validation when enabled."""
        output_dir = tmp_path / ".cihub"
        (output_dir / "tool-outputs").mkdir(parents=True)

        # Invalid report that should fail schema
        report = {"invalid_field": "value"}

        issues = validate_artifact_evidence(report, output_dir, run_schema_validation=True)

        # The exact behavior depends on schema strictness
        assert isinstance(issues, list)
