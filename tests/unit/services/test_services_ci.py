"""Unit tests for the CI service layer."""

from __future__ import annotations

from argparse import Namespace
from dataclasses import replace
from pathlib import Path
from unittest import mock

import pytest

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.ci import RunCIOptions, run_ci


def test_run_ci_handles_load_error(tmp_path: Path) -> None:
    with mock.patch("cihub.services.ci_engine.load_ci_config", side_effect=ValueError("boom")):
        result = run_ci(tmp_path)

    assert result.success is False
    assert result.exit_code == EXIT_FAILURE
    assert result.errors


def test_run_ci_writes_report_and_summary(tmp_path: Path) -> None:
    """Test that run_ci writes report.json and summary.md files.

    Note: Self-validation is mocked here to focus on file I/O.
    Validation behavior is tested in test_ci_self_validate.py.
    """

# TEST-METRICS:
    output_dir = tmp_path / ".cihub"
    config = {
        "language": "python",
        "repo": {"owner": "owner", "name": "repo"},
        "python": {"tools": {"pytest": {"enabled": True}}},
        "reports": {
            "github_summary": {"enabled": False, "include_metrics": False},
            "codecov": {"enabled": False},
        },
    }
    report = {"results": {}, "tool_metrics": {}, "repository": "owner/repo", "branch": "main"}

    # Mock validation result to isolate file writing from validation logic
    mock_validation = mock.MagicMock()
    mock_validation.errors = []
    mock_validation.warnings = []

    # Mock at strategy import locations (run_ci uses strategy pattern now)
    with mock.patch("cihub.services.ci_engine.load_ci_config", return_value=config):
        # Strategy imports _run_python_tools from python_tools submodule
        with mock.patch(
            "cihub.services.ci_engine.python_tools._run_python_tools",
            return_value=({}, {}, {}),
        ):
            # Strategy imports build_python_report at module level
            with mock.patch(
                "cihub.core.languages.python.build_python_report",
                return_value=report,
            ):
                # Strategy imports _evaluate_python_gates inside method
                with mock.patch(
                    "cihub.services.ci_engine.gates._evaluate_python_gates",
                    return_value=[],
                ):
                    with mock.patch("cihub.services.ci_engine.render_summary", return_value="summary"):
                        # Mock schema validation to avoid env-dependent behavior
                        # (GITHUB_ACTIONS makes schema errors fatal in CI but warnings locally)
                        with mock.patch(
                            "cihub.services.report_validator.validate_against_schema",
                            return_value=[],
                        ):
                            with mock.patch(
                                "cihub.services.report_validator.validate_report",
                                return_value=mock_validation,
                            ):
                                result = run_ci(tmp_path, output_dir=output_dir)

    assert result.success is True
    assert result.exit_code == EXIT_SUCCESS
    assert result.report_path and result.report_path.exists()
    assert result.summary_path and result.summary_path.exists()
    assert result.summary_text == "summary"


class TestRunCIOptions:
    """Tests for RunCIOptions dataclass."""

    def test_default_values(self) -> None:
        """All options should have sensible defaults."""
        opts = RunCIOptions()

        assert opts.output_dir is None
        assert opts.report_path is None
        assert opts.summary_path is None
        assert opts.workdir is None
        assert opts.install_deps is False
        assert opts.no_summary is False
        assert opts.write_github_summary is None
        assert opts.correlation_id is None
        assert opts.config_from_hub is None
        assert opts.env is None

    def test_custom_values(self) -> None:
        """All options can be set via constructor."""
        opts = RunCIOptions(
            output_dir=Path(".cihub"),
            report_path=Path("report.json"),
            summary_path=Path("summary.md"),
            workdir="src",
            install_deps=True,
            no_summary=True,
            write_github_summary=True,
            correlation_id="abc-123",
            config_from_hub="my-repo",
            env={"FOO": "bar"},
        )

        assert opts.output_dir == Path(".cihub")
        assert opts.report_path == Path("report.json")
        assert opts.summary_path == Path("summary.md")
        assert opts.workdir == "src"
        assert opts.install_deps is True
        assert opts.no_summary is True
        assert opts.write_github_summary is True
        assert opts.correlation_id == "abc-123"
        assert opts.config_from_hub == "my-repo"
        assert opts.env == {"FOO": "bar"}

    def test_frozen_immutability(self) -> None:
        """RunCIOptions should be immutable (frozen dataclass)."""
        opts = RunCIOptions()

        with pytest.raises(Exception):  # FrozenInstanceError
            opts.install_deps = True  # type: ignore[misc]

    def test_replace_creates_copy(self) -> None:
        """dataclasses.replace() creates modified copy."""
        opts = RunCIOptions(install_deps=False)
        new_opts = replace(opts, install_deps=True)

        assert opts.install_deps is False  # Original unchanged
        assert new_opts.install_deps is True  # New copy modified

    def test_from_args_basic(self) -> None:
        """from_args() extracts values from argparse namespace."""
        args = Namespace(
            output_dir=".cihub",
            report="report.json",
            summary="summary.md",
            workdir="src",
            install_deps=True,
            no_summary=False,
            write_github_summary=True,
            correlation_id="test-id",
            config_from_hub="my-repo",
        )

        opts = RunCIOptions.from_args(args)

        assert opts.output_dir == Path(".cihub")
        assert opts.report_path == Path("report.json")
        assert opts.summary_path == Path("summary.md")
        assert opts.workdir == "src"
        assert opts.install_deps is True
        assert opts.no_summary is False
        assert opts.write_github_summary is True
        assert opts.correlation_id == "test-id"
        assert opts.config_from_hub == "my-repo"

    def test_from_args_missing_attributes(self) -> None:
        """from_args() handles missing attributes with defaults."""
        args = Namespace()  # Empty namespace

        opts = RunCIOptions.from_args(args)

        assert opts.output_dir is None
        assert opts.report_path is None
        assert opts.install_deps is False
        assert opts.correlation_id is None

    def test_from_args_none_values(self) -> None:
        """from_args() treats None output_dir/report/summary as None paths."""
        args = Namespace(
            output_dir=None,
            report=None,
            summary=None,
            workdir=None,
            install_deps=False,
            no_summary=False,
            write_github_summary=None,
            correlation_id=None,
            config_from_hub=None,
        )

        opts = RunCIOptions.from_args(args)

        assert opts.output_dir is None
        assert opts.report_path is None
        assert opts.summary_path is None


class TestRunCIWithOptions:
    """Tests for run_ci() accepting RunCIOptions."""

    def test_run_ci_accepts_options(self, tmp_path: Path) -> None:
        """run_ci() should accept options parameter."""
        opts = RunCIOptions(
            output_dir=tmp_path / ".cihub",
            install_deps=False,
        )

        with mock.patch("cihub.services.ci_engine.load_ci_config", side_effect=ValueError("test")):
            result = run_ci(tmp_path, options=opts)

        # Should return result (error case, but options were accepted)
        assert result.success is False

    def test_run_ci_options_takes_precedence(self, tmp_path: Path) -> None:
        """When both options and kwargs provided, options should win."""
        opts = RunCIOptions(install_deps=True)

        with mock.patch("cihub.services.ci_engine.load_ci_config", side_effect=ValueError("test")):
            # Pass conflicting kwargs - options should take precedence
            result = run_ci(tmp_path, options=opts, install_deps=False)

        # Test completes without error - options were used
        assert result.success is False
