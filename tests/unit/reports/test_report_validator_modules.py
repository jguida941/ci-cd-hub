"""Tests for the report_validator package modular structure.

These tests verify the new modular split of report_validator works correctly
and maintains backward compatibility with existing import patterns.
"""

# TEST-METRICS:

from pathlib import Path


class TestPackageStructure:
    """Tests to verify the package structure is correct."""

    def test_package_has_all_expected_modules(self):
        """Verify all submodules exist and are importable."""
        from cihub.services.report_validator import artifact, content, schema, types

        # Verify they are modules
        assert hasattr(types, "__name__")
        assert hasattr(schema, "__name__")
        assert hasattr(artifact, "__name__")
        assert hasattr(content, "__name__")

    def test_types_module_exports(self):
        """Verify types module exports expected classes."""
        from cihub.services.report_validator.types import ValidationResult, ValidationRules

        # Can instantiate
        rules = ValidationRules()
        result = ValidationResult(success=True)

        assert rules.expect_clean is True
        assert result.valid is True

    def test_schema_module_exports(self):
        """Verify schema module exports expected functions."""
        from cihub.services.report_validator.schema import _load_schema, validate_against_schema

        # Functions are callable
        assert callable(validate_against_schema)
        assert callable(_load_schema)

    def test_artifact_module_exports(self):
        """Verify artifact module exports expected functions."""
        from cihub.services.report_validator.artifact import (
            check_artifacts_non_empty,
            iter_existing_patterns,
        )

        assert callable(iter_existing_patterns)
        assert callable(check_artifacts_non_empty)

    def test_content_module_exports(self):
        """Verify content module exports expected functions."""
        from cihub.services.report_validator.content import (
            validate_report,
            validate_report_file,
        )

        assert callable(validate_report)
        assert callable(validate_report_file)


class TestBackwardCompatibility:
    """Tests to verify backward compatibility with old import patterns."""

    def test_import_from_package_root(self):
        """Old import pattern: from cihub.services.report_validator import X."""
        from cihub.services.report_validator import (
            ValidationResult,
            ValidationRules,
            validate_against_schema,
            validate_report,
            validate_report_file,
        )

        assert ValidationRules is not None
        assert ValidationResult is not None
        assert validate_report is not None
        assert validate_report_file is not None
        assert validate_against_schema is not None

    def test_import_from_services(self):
        """Old import pattern: from cihub.services import X."""
        from cihub.services import (
            ValidationResult,
            ValidationRules,
            validate_report,
            validate_report_file,
        )

        assert ValidationRules is not None
        assert ValidationResult is not None
        assert validate_report is not None
        assert validate_report_file is not None

    def test_underscore_prefixed_functions_available(self):
        """Verify underscore-prefixed functions are available for internal use."""
        from cihub.services.report_validator import (
            _check_artifacts_non_empty,
            _iter_existing_patterns,
        )

        assert callable(_iter_existing_patterns)
        assert callable(_check_artifacts_non_empty)

    def test_registry_constants_reexported(self):
        """Verify registry constants are re-exported from package."""
        from cihub.services.report_validator import (
            JAVA_ARTIFACTS,
            JAVA_LINT_METRICS,
            JAVA_SECURITY_METRICS,
            JAVA_SUMMARY_MAP,
            JAVA_TOOL_METRICS,
            PYTHON_ARTIFACTS,
            PYTHON_LINT_METRICS,
            PYTHON_SECURITY_METRICS,
            PYTHON_SUMMARY_MAP,
            PYTHON_TOOL_METRICS,
        )

        # All are dicts
        assert isinstance(PYTHON_TOOL_METRICS, dict)
        assert isinstance(JAVA_TOOL_METRICS, dict)
        assert isinstance(PYTHON_ARTIFACTS, dict)
        assert isinstance(JAVA_ARTIFACTS, dict)
        assert isinstance(PYTHON_LINT_METRICS, (list, tuple))
        assert isinstance(JAVA_LINT_METRICS, (list, tuple))
        assert isinstance(PYTHON_SECURITY_METRICS, (list, tuple))
        assert isinstance(JAVA_SECURITY_METRICS, (list, tuple))
        assert isinstance(PYTHON_SUMMARY_MAP, dict)
        assert isinstance(JAVA_SUMMARY_MAP, dict)

    def test_registry_constants_are_same_objects(self):
        """Registry constants should be the exact same objects as in registry."""
        from cihub.services.report_validator import JAVA_TOOL_METRICS, PYTHON_TOOL_METRICS
        from cihub.tools.registry import (
            JAVA_TOOL_METRICS as ORIGINAL_JAVA,
        )
        from cihub.tools.registry import (
            PYTHON_TOOL_METRICS as ORIGINAL_PYTHON,
        )

        assert PYTHON_TOOL_METRICS is ORIGINAL_PYTHON
        assert JAVA_TOOL_METRICS is ORIGINAL_JAVA


class TestArtifactModule:
    """Unit tests for artifact validation functions."""

    def test_iter_existing_patterns_finds_files(self, tmp_path: Path):
        """iter_existing_patterns returns True when files match."""
        from cihub.services.report_validator.artifact import iter_existing_patterns

        # Create test files
        (tmp_path / "test.json").write_text("{}")
        (tmp_path / "data.xml").write_text("<root/>")

        assert iter_existing_patterns(tmp_path, ["*.json"]) is True
        assert iter_existing_patterns(tmp_path, ["*.xml"]) is True
        assert iter_existing_patterns(tmp_path, ["*.json", "*.xml"]) is True

    def test_iter_existing_patterns_no_match(self, tmp_path: Path):
        """iter_existing_patterns returns False when no files match."""
        from cihub.services.report_validator.artifact import iter_existing_patterns

        (tmp_path / "test.json").write_text("{}")

        assert iter_existing_patterns(tmp_path, ["*.xml"]) is False
        assert iter_existing_patterns(tmp_path, ["*.yaml"]) is False

    def test_iter_existing_patterns_empty_dir(self, tmp_path: Path):
        """iter_existing_patterns returns False on empty directory."""
        from cihub.services.report_validator.artifact import iter_existing_patterns

        assert iter_existing_patterns(tmp_path, ["*.json"]) is False

    def test_iter_existing_patterns_multiple_patterns(self, tmp_path: Path):
        """iter_existing_patterns checks multiple patterns."""
        from cihub.services.report_validator.artifact import iter_existing_patterns

        (tmp_path / "report.xml").write_text("<report/>")

        # First pattern doesn't match, second does
        assert iter_existing_patterns(tmp_path, ["*.json", "*.xml"]) is True

    def test_check_artifacts_non_empty_with_content(self, tmp_path: Path):
        """check_artifacts_non_empty returns True for non-empty files."""
        from cihub.services.report_validator.artifact import check_artifacts_non_empty

        (tmp_path / "report.json").write_text('{"data": true}')

        all_non_empty, empty_files = check_artifacts_non_empty(tmp_path, ["*.json"])
        assert all_non_empty is True
        assert empty_files == []

    def test_check_artifacts_non_empty_with_empty_file(self, tmp_path: Path):
        """check_artifacts_non_empty detects empty files."""
        from cihub.services.report_validator.artifact import check_artifacts_non_empty

        empty_file = tmp_path / "report.json"
        empty_file.write_text("")

        all_non_empty, empty_files = check_artifacts_non_empty(tmp_path, ["*.json"])
        assert all_non_empty is False
        assert str(empty_file) in empty_files

    def test_check_artifacts_non_empty_mixed(self, tmp_path: Path):
        """check_artifacts_non_empty handles mix of empty and non-empty."""
        from cihub.services.report_validator.artifact import check_artifacts_non_empty

        (tmp_path / "good.json").write_text('{"valid": true}')
        (tmp_path / "bad.json").write_text("")  # Empty

        all_non_empty, empty_files = check_artifacts_non_empty(tmp_path, ["*.json"])
        assert all_non_empty is False
        assert len(empty_files) == 1
        assert "bad.json" in empty_files[0]

    def test_check_artifacts_non_empty_no_matches(self, tmp_path: Path):
        """check_artifacts_non_empty returns False when no files found."""
        from cihub.services.report_validator.artifact import check_artifacts_non_empty

        all_non_empty, empty_files = check_artifacts_non_empty(tmp_path, ["*.json"])
        assert all_non_empty is False
        assert empty_files == []


class TestSchemaModule:
    """Unit tests for schema validation functions."""

    def test_load_schema_returns_dict(self):
        """_load_schema returns a dictionary."""
        from cihub.services.report_validator.schema import _load_schema

        schema = _load_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema or "type" in schema

    def test_load_schema_caches_result(self):
        """_load_schema caches the schema on second call."""
        from cihub.services.report_validator.schema import _load_schema

        schema1 = _load_schema()
        schema2 = _load_schema()
        assert schema1 is schema2  # Same object (cached)

    def test_validate_against_schema_empty_report(self):
        """validate_against_schema returns errors for empty report."""
        from cihub.services.report_validator.schema import validate_against_schema

        errors = validate_against_schema({})
        assert len(errors) > 0  # Should have schema errors

    def test_validate_against_schema_returns_list(self):
        """validate_against_schema always returns a list."""
        from cihub.services.report_validator.schema import validate_against_schema

        errors = validate_against_schema({"schema_version": "2.0"})
        assert isinstance(errors, list)


class TestTypesModule:
    """Unit tests for types dataclasses."""

    def test_validation_rules_defaults(self):
        """ValidationRules has correct defaults."""
        from cihub.services.report_validator.types import ValidationRules

        rules = ValidationRules()
        assert rules.expect_clean is True
        assert rules.coverage_min == 70
        assert rules.strict is False
        assert rules.validate_schema is False
        assert rules.consistency_only is False

    def test_validation_rules_custom_values(self):
        """ValidationRules accepts custom values."""
        from cihub.services.report_validator.types import ValidationRules

        rules = ValidationRules(
            expect_clean=False,
            coverage_min=80,
            strict=True,
            validate_schema=True,
            consistency_only=True,
        )
        assert rules.expect_clean is False
        assert rules.coverage_min == 80
        assert rules.strict is True
        assert rules.validate_schema is True
        assert rules.consistency_only is True

    def test_validation_result_valid_property(self):
        """ValidationResult.valid reflects errors list."""
        from cihub.services.report_validator.types import ValidationResult

        # No errors = valid
        result = ValidationResult(success=True, errors=[])
        assert result.valid is True

        # Has errors = not valid
        result = ValidationResult(success=False, errors=["error"])
        assert result.valid is False

    def test_validation_result_inherits_service_result(self):
        """ValidationResult inherits from ServiceResult."""
        from cihub.services.report_validator.types import ValidationResult
        from cihub.services.types import ServiceResult

        assert issubclass(ValidationResult, ServiceResult)

    def test_validation_result_extra_fields(self):
        """ValidationResult has report-specific fields."""
        from cihub.services.report_validator.types import ValidationResult

        result = ValidationResult(
            success=True,
            language="python",
            schema_errors=["schema error"],
            threshold_violations=["coverage below threshold"],
            tool_warnings=["drift detected"],
            debug_messages=["debug info"],
        )

        assert result.language == "python"
        assert "schema error" in result.schema_errors
        assert "coverage below threshold" in result.threshold_violations
        assert "drift detected" in result.tool_warnings
        assert "debug info" in result.debug_messages


class TestContentModule:
    """Unit tests for content validation functions."""

    def test_validate_report_detects_python(self):
        """validate_report correctly detects Python language."""
        from cihub.services.report_validator.content import validate_report

        report = {
            "schema_version": "2.0",
            "python_version": "3.12",
            "results": {"tests_passed": 10, "tests_failed": 0, "coverage": 80},
            "tools_ran": {"pytest": True},
            "tools_configured": {"pytest": True},
            "tools_success": {"pytest": True},
            "tool_metrics": {"ruff_errors": 0},
        }

        result = validate_report(report)
        assert result.language == "python"

    def test_validate_report_detects_java(self):
        """validate_report correctly detects Java language."""
        from cihub.services.report_validator.content import validate_report

        report = {
            "schema_version": "2.0",
            "java_version": "21",
            "results": {"tests_passed": 10, "tests_failed": 0, "coverage": 80},
            "tools_ran": {"jacoco": True},
            "tools_configured": {"jacoco": True},
            "tools_success": {"jacoco": True},
            "tool_metrics": {"checkstyle_issues": 0},
        }

        result = validate_report(report)
        assert result.language == "java"

    def test_validate_report_returns_validation_result(self):
        """validate_report returns ValidationResult type."""
        from cihub.services.report_validator.content import validate_report
        from cihub.services.report_validator.types import ValidationResult

        report = {"schema_version": "2.0", "python_version": "3.12", "results": {}}
        result = validate_report(report)

        assert isinstance(result, ValidationResult)

    def test_validate_report_file_handles_missing(self, tmp_path: Path):
        """validate_report_file handles missing file gracefully."""
        from cihub.services.report_validator.content import validate_report_file

        result = validate_report_file(tmp_path / "nonexistent.json")
        assert result.success is False
        assert any("not found" in e for e in result.errors)

    def test_validate_report_file_handles_invalid_json(self, tmp_path: Path):
        """validate_report_file handles invalid JSON gracefully."""
        from cihub.services.report_validator.content import validate_report_file

        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {")

        result = validate_report_file(bad_file)
        assert result.success is False
        assert any("Invalid JSON" in e for e in result.errors)


class TestModuleIntegration:
    """Integration tests for the modular package."""

    def test_end_to_end_validation_flow(self, tmp_path: Path):
        """Full validation flow works across modules."""
        import json

        from cihub.services.report_validator import (
            ValidationRules,
            validate_report_file,
        )

        # Create a valid report
        report = {
            "schema_version": "2.0",
            "python_version": "3.12",
            "results": {"tests_passed": 100, "tests_failed": 0, "coverage": 90},
            "tools_ran": {"pytest": True, "ruff": True},
            "tools_configured": {"pytest": True, "ruff": True},
            "tools_success": {"pytest": True, "ruff": True},
            "tool_metrics": {"ruff_errors": 0, "mypy_errors": 0},
            "thresholds": {"coverage_min": 80, "mutation_score_min": 50},
        }

        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report))

        # Validate with rules
        rules = ValidationRules(expect_clean=True, coverage_min=80)
        result = validate_report_file(report_path, rules)

        assert result.success is True
        assert result.language == "python"
        assert len(result.errors) == 0

    def test_schema_validation_integration(self):
        """Schema validation integrates with content validation."""
        from cihub.services.report_validator import ValidationRules, validate_report

        report = {
            "schema_version": "2.0",
            "python_version": "3.12",
            "results": {"tests_passed": 10, "tests_failed": 0, "coverage": 80},
            "tools_ran": {"pytest": True},
            "unknown_extra_field": "should fail schema",
        }

        # Without schema validation - should not have schema errors
        result_no_schema = validate_report(report, ValidationRules(validate_schema=False))
        assert len(result_no_schema.schema_errors) == 0

        # With schema validation - should fail due to extra field
        result_with_schema = validate_report(report, ValidationRules(validate_schema=True))
        assert len(result_with_schema.schema_errors) > 0

    def test_artifact_validation_integration(self, tmp_path: Path):
        """Artifact validation integrates with content validation."""
        from cihub.services.report_validator import validate_report

        report = {
            "schema_version": "2.0",
            "python_version": "3.12",
            "results": {"tests_passed": 10, "tests_failed": 0, "coverage": 80},
            "tools_ran": {"ruff": True},
            "tools_configured": {"ruff": True},
            "tools_success": {"ruff": True},
            "tool_metrics": {},  # No metrics - should check artifacts
        }

        # Create non-empty artifact
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        (reports_dir / "ruff-report.json").write_text('{"status": "ok"}')

        result = validate_report(report, reports_dir=reports_dir)
        # Should not warn about missing proof when artifact exists
        assert not any("no proof found" in w for w in result.warnings)
