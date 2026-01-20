"""Tests for cihub.services.report_validator module."""

# TEST-METRICS:

from pathlib import Path

from cihub.services import ValidationResult, ValidationRules, validate_report, validate_report_file


def make_valid_python_report() -> dict:
    """Create a minimal valid Python report."""
    return {
        "schema_version": "2.0",
        "python_version": "3.12",
        "results": {
            "tests_passed": 10,
            "tests_failed": 0,
            "coverage": 85,
        },
        "tools_ran": {"pytest": True, "ruff": True},
        "tools_configured": {"pytest": True, "ruff": True},
        "tools_success": {"pytest": True, "ruff": True},
        "tool_metrics": {
            "ruff_errors": 0,
            "black_issues": 0,
            "isort_issues": 0,
            "bandit_high": 0,
            "pip_audit_vulns": 0,
        },
    }


def make_valid_java_report() -> dict:
    """Create a minimal valid Java report."""
    return {
        "schema_version": "2.0",
        "java_version": "21",
        "results": {
            "tests_passed": 20,
            "tests_failed": 0,
            "coverage": 80,
        },
        "tools_ran": {"jacoco": True, "checkstyle": True},
        "tools_configured": {"jacoco": True, "checkstyle": True},
        "tools_success": {"jacoco": True, "checkstyle": True},
        "tool_metrics": {
            "checkstyle_issues": 0,
            "spotbugs_issues": 0,
            "pmd_violations": 0,
            "owasp_critical": 0,
            "owasp_high": 0,
        },
    }


class TestValidationRules:
    """Tests for ValidationRules dataclass."""

    def test_defaults(self):
        """Default rules expect clean build with 70% coverage."""
        rules = ValidationRules()
        assert rules.expect_clean is True
        assert rules.coverage_min == 70
        assert rules.strict is False


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_property(self):
        """valid is True when no errors."""
        result = ValidationResult(success=True, errors=[], warnings=["some warning"])
        assert result.valid is True

        result = ValidationResult(success=False, errors=["some error"])
        assert result.valid is False


class TestValidateReport:
    """Tests for validate_report function."""

    def test_valid_python_report(self):
        """Valid Python report passes validation."""
        report = make_valid_python_report()
        result = validate_report(report)

        assert result.success is True
        assert result.valid is True
        assert result.language == "python"
        assert len(result.errors) == 0

    def test_valid_java_report(self):
        """Valid Java report passes validation."""
        report = make_valid_java_report()
        result = validate_report(report)

        assert result.success is True
        assert result.language == "java"
        assert len(result.errors) == 0

    def test_missing_schema_version(self):
        """Reports error when schema_version is wrong."""
        report = make_valid_python_report()
        report["schema_version"] = "1.0"
        result = validate_report(report)

        assert result.success is False
        assert any("schema_version" in e for e in result.errors)

    def test_missing_language(self):
        """Reports error when language can't be determined."""
        report = make_valid_python_report()
        del report["python_version"]
        result = validate_report(report)

        assert result.success is False
        assert any("language" in e for e in result.errors)

    def test_null_tests_passed(self):
        """Reports error when tests_passed is null."""
        report = make_valid_python_report()
        report["results"]["tests_passed"] = None
        result = validate_report(report)

        assert result.success is False
        assert any("tests_passed is null" in e for e in result.errors)

    def test_zero_tests_passed_clean_mode(self):
        """Reports error when tests_passed is 0 in clean mode."""
        report = make_valid_python_report()
        report["results"]["tests_passed"] = 0
        result = validate_report(report, ValidationRules(expect_clean=True))

        assert result.success is False
        assert any("tests_passed is 0" in e for e in result.errors)

    def test_tests_failed_in_clean_mode(self):
        """Reports error when tests_failed > 0 in clean mode."""
        report = make_valid_python_report()
        report["results"]["tests_failed"] = 2
        result = validate_report(report, ValidationRules(expect_clean=True))

        assert result.success is False
        assert any("tests_failed is 2" in e for e in result.errors)

    def test_coverage_below_threshold(self):
        """Reports error when coverage is below threshold."""
        report = make_valid_python_report()
        report["results"]["coverage"] = 50
        result = validate_report(report, ValidationRules(coverage_min=70))

        assert result.success is False
        assert any("coverage is 50%" in e for e in result.errors)

    def test_coverage_above_threshold(self):
        """Passes when coverage is above threshold."""
        report = make_valid_python_report()
        report["results"]["coverage"] = 90
        result = validate_report(report, ValidationRules(coverage_min=70))

        assert result.success is True

    def test_lint_issues_in_clean_mode(self):
        """Reports error when lint metrics > 0 in clean mode."""
        report = make_valid_python_report()
        report["tool_metrics"]["ruff_errors"] = 5
        result = validate_report(report, ValidationRules(expect_clean=True))

        assert result.success is False
        assert any("ruff_errors is 5" in e for e in result.errors)

    def test_expect_issues_mode(self):
        """expect_clean=False expects issues to exist."""
        report = make_valid_python_report()
        # No issues - should fail in expect_issues mode
        result = validate_report(report, ValidationRules(expect_clean=False))

        assert result.success is False
        assert any("failing fixture MUST have issues" in e for e in result.errors)

    def test_expect_issues_with_issues(self):
        """expect_clean=False passes when issues exist."""
        report = make_valid_python_report()
        report["tool_metrics"]["ruff_errors"] = 3
        result = validate_report(report, ValidationRules(expect_clean=False))

        assert result.success is True

    def test_drift_warning(self):
        """Warns when tool configured but didn't run."""
        report = make_valid_python_report()
        report["tools_configured"]["mypy"] = True
        report["tools_ran"]["mypy"] = False
        result = validate_report(report)

        assert any("DRIFT" in w for w in result.warnings)
        assert any("mypy" in w for w in result.warnings)

    def test_strict_mode_fails_on_warnings(self):
        """Strict mode fails when there are warnings."""
        report = make_valid_python_report()
        report["tools_configured"]["mypy"] = True
        report["tools_ran"]["mypy"] = False
        result = validate_report(report, ValidationRules(strict=True))

        assert result.success is False  # Strict mode fails on warnings

    def test_summary_cross_check_warns_on_mismatch(self):
        """Summary/report mismatch produces warnings."""
        report = make_valid_python_report()
        report["tools_ran"]["pytest"] = True
        report["tools_success"]["pytest"] = True

        summary_text = "\n".join(
            [
                "## Tools Enabled",
                "| Category | Tool | Configured | Ran | Success |",
                "|---|---|---|---|---|",
                "| Testing | pytest | true | false | false |",
            ]
        )

        result = validate_report(report, summary_text=summary_text)
        assert any("ran mismatch" in w for w in result.warnings)

    def test_artifact_fallback_skips_missing_metrics_warning(self, tmp_path: Path):
        """Non-empty artifacts allow passing tool validation when metrics are missing."""
        report = make_valid_python_report()
        report["tool_metrics"].pop("ruff_errors", None)
        report["tools_ran"]["ruff"] = True
        report["tools_success"]["ruff"] = True

        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        (reports_dir / "ruff-report.json").write_text("{}")  # Non-empty

        result = validate_report(report, reports_dir=reports_dir)
        assert not any("no proof found" in w for w in result.warnings)
        assert not any("empty output files" in w for w in result.warnings)

    def test_empty_artifact_triggers_warning(self, tmp_path: Path):
        """Empty artifact files trigger a warning."""
        report = make_valid_python_report()
        report["tool_metrics"].pop("ruff_errors", None)
        report["tools_ran"]["ruff"] = True
        report["tools_success"]["ruff"] = True

        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        (reports_dir / "ruff-report.json").write_text("")  # Empty file

        result = validate_report(report, reports_dir=reports_dir)
        assert any("empty output files" in w for w in result.warnings)

    def test_empty_artifact_with_metrics_is_debug_only(self, tmp_path: Path):
        """Empty artifacts are ignored when metrics exist."""
        report = make_valid_python_report()
        report["tool_metrics"]["ruff_errors"] = 0  # Has metrics
        report["tools_ran"]["ruff"] = True
        report["tools_success"]["ruff"] = True

        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        (reports_dir / "ruff-report.json").write_text("")  # Empty file

        result = validate_report(report, reports_dir=reports_dir)
        assert not any("empty output files" in w for w in result.warnings)


class TestValidateReportFile:
    """Tests for validate_report_file function."""

    def test_file_not_found(self, tmp_path: Path):
        """Returns error when file doesn't exist."""
        result = validate_report_file(tmp_path / "nonexistent.json")

        assert result.success is False
        assert any("not found" in e for e in result.errors)

    def test_invalid_json(self, tmp_path: Path):
        """Returns error when file contains invalid JSON."""
        report_path = tmp_path / "report.json"
        report_path.write_text("not valid json {")
        result = validate_report_file(report_path)

        assert result.success is False
        assert any("Invalid JSON" in e for e in result.errors)

    def test_valid_file(self, tmp_path: Path):
        """Validates file contents correctly."""
        import json

        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(make_valid_python_report()))
        result = validate_report_file(report_path)

        assert result.success is True
        assert result.language == "python"


class TestSchemaValidation:
    """Tests for JSON schema validation feature."""

    def test_validate_schema_default_off(self):
        """validate_schema defaults to False."""
        rules = ValidationRules()
        assert rules.validate_schema is False

    def test_valid_report_passes_schema_validation(self):
        """A schema-compliant report passes schema validation."""
        from cihub.services.report_validator import validate_against_schema

        # Create a minimal valid report matching schema requirements
        report = {
            "schema_version": "2.0",
            "metadata": {
                "workflow_version": "1.0.0",
                "workflow_ref": "main",
                "generated_at": "2024-01-01T00:00:00Z",
            },
            "repository": "test/repo",
            "run_id": "123",
            "run_number": "1",
            "commit": "a" * 40,
            "branch": "main",
            "timestamp": "2024-01-01T00:00:00Z",
            "python_version": "3.12",
            "results": {
                "tests_passed": 10,
                "tests_failed": 0,
                "coverage": 85,
                "mutation_score": 70,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "tool_metrics": {"ruff_errors": 0},
            "tools_ran": {"pytest": True, "ruff": True},
        }

        errors = validate_against_schema(report)
        assert len(errors) == 0, f"Unexpected schema errors: {errors}"

    def test_invalid_schema_version_fails_schema_validation(self):
        """Schema validation catches wrong schema_version."""
        from cihub.services.report_validator import validate_against_schema

        report = {
            "schema_version": "9.9",  # Wrong version
            "metadata": {
                "workflow_version": "1.0",
                "workflow_ref": "main",
                "generated_at": "2024-01-01T00:00:00Z",
            },
            "repository": "test/repo",
            "run_id": "123",
            "run_number": "1",
            "commit": "a" * 40,
            "branch": "main",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {
                "coverage": 0,
                "mutation_score": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "tool_metrics": {},
            "tools_ran": {},
        }

        errors = validate_against_schema(report)
        assert len(errors) > 0
        assert any("schema_version" in e or "2.0" in e for e in errors)

    def test_unknown_field_fails_schema_validation(self):
        """Schema validation catches unknown fields due to additionalProperties=false."""
        from cihub.services.report_validator import validate_against_schema

        report = {
            "schema_version": "2.0",
            "metadata": {
                "workflow_version": "1.0",
                "workflow_ref": "main",
                "generated_at": "2024-01-01T00:00:00Z",
            },
            "repository": "test/repo",
            "run_id": "123",
            "run_number": "1",
            "commit": "a" * 40,
            "branch": "main",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {
                "coverage": 0,
                "mutation_score": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "tool_metrics": {},
            "tools_ran": {},
            "unknown_field_that_shouldnt_exist": "oops",
        }

        errors = validate_against_schema(report)
        assert len(errors) > 0
        assert any("unknown_field" in e.lower() or "additional" in e.lower() for e in errors)

    def test_missing_required_field_fails_schema_validation(self):
        """Schema validation catches missing required fields."""
        from cihub.services.report_validator import validate_against_schema

        # Missing 'results' which is required
        report = {
            "schema_version": "2.0",
            "metadata": {
                "workflow_version": "1.0",
                "workflow_ref": "main",
                "generated_at": "2024-01-01T00:00:00Z",
            },
            "repository": "test/repo",
            "run_id": "123",
            "run_number": "1",
            "commit": "a" * 40,
            "branch": "main",
            "timestamp": "2024-01-01T00:00:00Z",
            "tool_metrics": {},
            "tools_ran": {},
        }

        errors = validate_against_schema(report)
        assert len(errors) > 0
        assert any("results" in e for e in errors)

    def test_schema_validation_integrated_with_validate_report(self):
        """Schema errors are included in validate_report result when enabled."""
        report = {
            "schema_version": "2.0",
            "python_version": "3.12",
            "unknown_field": "bad",  # This will fail schema validation
            "results": {
                "tests_passed": 10,
                "tests_failed": 0,
                "coverage": 85,
                "mutation_score": 70,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "metadata": {
                "workflow_version": "1.0",
                "workflow_ref": "main",
                "generated_at": "2024-01-01T00:00:00Z",
            },
            "repository": "test/repo",
            "run_id": "123",
            "run_number": "1",
            "commit": "a" * 40,
            "branch": "main",
            "timestamp": "2024-01-01T00:00:00Z",
            "tool_metrics": {},
            "tools_ran": {},
        }

        # Without schema validation - passes
        result_no_schema = validate_report(report, ValidationRules(validate_schema=False))
        assert len(result_no_schema.schema_errors) == 0

        # With schema validation - fails due to unknown_field
        result_with_schema = validate_report(report, ValidationRules(validate_schema=True))
        assert len(result_with_schema.schema_errors) > 0
        assert result_with_schema.success is False


class TestThresholdCompletenessValidation:
    """Tests for threshold completeness warning (Issue Section 7)."""

    def test_warns_when_coverage_min_missing(self):
        """Should warn when coverage_min threshold is missing."""
        report = make_valid_python_report()
        # No thresholds at all
        report["thresholds"] = {}
        result = validate_report(report)

        assert any("coverage_min" in w for w in result.warnings)
        assert any("will render as '-'" in w for w in result.warnings)

    def test_warns_when_mutation_score_min_missing(self):
        """Should warn when mutation_score_min threshold is missing."""
        report = make_valid_python_report()
        report["thresholds"] = {"coverage_min": 80}  # Has coverage, missing mutation
        result = validate_report(report)

        assert any("mutation_score_min" in w for w in result.warnings)
        assert not any("coverage_min" in w for w in result.warnings)

    def test_no_warning_when_thresholds_complete(self):
        """Should not warn when all core thresholds are present."""
        report = make_valid_python_report()
        report["thresholds"] = {
            "coverage_min": 80,
            "mutation_score_min": 60,
        }
        result = validate_report(report)

        # Should have no threshold-related warnings
        threshold_warnings = [
            w for w in result.warnings if "threshold" in w.lower() or "coverage_min" in w or "mutation_score_min" in w
        ]
        assert len(threshold_warnings) == 0

    def test_warns_when_threshold_is_null(self):
        """Should warn when threshold exists but value is null."""
        report = make_valid_python_report()
        report["thresholds"] = {
            "coverage_min": None,  # Explicitly null
            "mutation_score_min": 60,
        }
        result = validate_report(report)

        assert any("coverage_min" in w for w in result.warnings)

    def test_warns_when_thresholds_key_missing(self):
        """Should warn when thresholds key is entirely missing from report."""
        report = make_valid_python_report()
        # Ensure thresholds key doesn't exist
        report.pop("thresholds", None)
        result = validate_report(report)

        assert any("coverage_min" in w for w in result.warnings)
        assert any("mutation_score_min" in w for w in result.warnings)


class TestToolsRequireRunValidation:
    """Tests for tools_require_run validation logic."""

    def test_required_tool_not_run_is_error(self):
        """Should error when required tool was configured but not run."""
        report = make_valid_python_report()
        report["tools_configured"] = {"pytest": True, "bandit": True}
        report["tools_ran"] = {"pytest": True, "bandit": False}  # bandit didn't run
        report["tools_require_run"] = {"bandit": True}  # bandit is required

        result = validate_report(report)

        assert not result.success
        assert any("REQUIRED TOOL NOT RUN" in e and "bandit" in e for e in result.errors)

    def test_required_tool_that_ran_is_ok(self):
        """Should not error when required tool ran successfully."""
        report = make_valid_python_report()
        report["tools_configured"] = {"pytest": True, "bandit": True}
        report["tools_ran"] = {"pytest": True, "bandit": True}
        report["tools_require_run"] = {"bandit": True}

        result = validate_report(report)

        # Should not have required tool errors
        assert not any("REQUIRED TOOL NOT RUN" in e for e in result.errors)

    def test_optional_tool_not_run_is_warning(self):
        """Should only warn (not error) when optional tool didn't run."""
        report = make_valid_python_report()
        report["tools_configured"] = {"pytest": True, "mutmut": True}
        report["tools_ran"] = {"pytest": True, "mutmut": False}
        report["tools_require_run"] = {"mutmut": False}  # mutmut is optional

        result = validate_report(report)

        # Should have drift warning but no error
        assert any("DRIFT" in w and "mutmut" in w for w in result.warnings)
        assert not any("REQUIRED TOOL NOT RUN" in e for e in result.errors)

    def test_empty_tools_require_run_is_handled(self):
        """Should handle missing or empty tools_require_run gracefully."""
        report = make_valid_python_report()
        report["tools_configured"] = {"pytest": True}
        report["tools_ran"] = {"pytest": False}
        # No tools_require_run field

        result = validate_report(report)

        # Should only have drift warning, no required tool error
        assert any("DRIFT" in w for w in result.warnings)
        assert not any("REQUIRED TOOL NOT RUN" in e for e in result.errors)
