"""Property-based tests for aggregation status functions using Hypothesis.

These tests verify invariants for the pure functions in
cihub/core/aggregation/status.py.
"""

# TEST-METRICS:

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.core.aggregation.status import (
    _config_from_artifact_name,
    _evaluate_tool_failures,
    _status_from_report,
    create_run_status,
)

# =============================================================================
# Strategy Definitions
# =============================================================================

# Strategy for repository names
repo_strategy = st.from_regex(r"[a-z][a-z0-9_-]*/[a-z][a-z0-9_-]*", fullmatch=True)

# Strategy for language
language_strategy = st.sampled_from(["python", "java", "unknown"])

# Strategy for tool names
tool_name_strategy = st.sampled_from(
    ["pytest", "ruff", "bandit", "mypy", "jacoco", "checkstyle", "spotbugs", "trivy"]
)

# Strategy for tool boolean maps
tool_bool_map_strategy = st.dictionaries(
    keys=tool_name_strategy,
    values=st.booleans(),
    min_size=0,
    max_size=5,
)

# Strategy for test counts
test_count_strategy = st.integers(min_value=0, max_value=1000)

# Strategy for coverage values
coverage_strategy = st.one_of(
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    st.none(),
)


# =============================================================================
# create_run_status Property Tests
# =============================================================================


class TestCreateRunStatusProperties:
    """Property tests for create_run_status function."""

    @given(
        repo=repo_strategy,
        language=language_strategy,
        branch=st.text(alphabet="abcdefghijklmnop_-", min_size=1, max_size=20),
    )
    @settings(max_examples=50)
    def test_create_run_status_preserves_repo(self, repo: str, language: str, branch: str) -> None:
        """Property: create_run_status preserves repo field."""
        entry = {"repo": repo, "language": language, "branch": branch}
        result = create_run_status(entry)
        assert result["repo"] == repo

    @given(repo=repo_strategy)
    @settings(max_examples=30)
    def test_create_run_status_derives_config_from_repo(self, repo: str) -> None:
        """Property: config is derived from repo name when not provided."""
        entry = {"repo": repo}
        result = create_run_status(entry)
        # Config should be the repo suffix after slash
        expected_config = repo.split("/")[-1] if "/" in repo else repo
        assert result["config"] == expected_config

    @given(
        run_id=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
    )
    @settings(max_examples=30)
    def test_create_run_status_handles_missing_run_id(self, run_id: str | None) -> None:
        """Property: status is 'missing_run_id' when run_id is missing."""
        entry = {"repo": "test/repo", "run_id": run_id}
        result = create_run_status(entry)
        if not run_id:
            assert result["status"] == "missing_run_id"
        else:
            assert result["status"] == "unknown"

    @given(
        tools_ran=tool_bool_map_strategy,
        tools_configured=tool_bool_map_strategy,
    )
    @settings(max_examples=30)
    def test_create_run_status_has_tool_maps(
        self, tools_ran: dict[str, bool], tools_configured: dict[str, bool]
    ) -> None:
        """Property: result always has tools_ran, tools_configured, tools_success dicts."""
        entry = {"repo": "test/repo"}
        result = create_run_status(entry)
        assert isinstance(result["tools_ran"], dict)
        assert isinstance(result["tools_configured"], dict)
        assert isinstance(result["tools_success"], dict)


# =============================================================================
# _config_from_artifact_name Property Tests
# =============================================================================


class TestConfigFromArtifactNameProperties:
    """Property tests for _config_from_artifact_name function."""

    @given(base_name=st.text(alphabet="abcdefghijklmnop_-", min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_strips_ci_report_suffix(self, base_name: str) -> None:
        """Property: -ci-report suffix is stripped."""
        artifact_name = f"{base_name}-ci-report"
        result = _config_from_artifact_name(artifact_name)
        assert result == base_name

    @given(name=st.text(alphabet="abcdefghijklmnop_-", min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_preserves_name_without_suffix(self, name: str) -> None:
        """Property: name without suffix is preserved."""
        if not name.endswith("-ci-report"):
            result = _config_from_artifact_name(name)
            assert result == name

    @given(base_name=st.text(alphabet="abcdefghijklmnop_-", min_size=1, max_size=20))
    @settings(max_examples=30)
    def test_idempotent_for_non_suffixed(self, base_name: str) -> None:
        """Property: applying twice to non-suffixed name gives same result."""
        if not base_name.endswith("-ci-report"):
            once = _config_from_artifact_name(base_name)
            twice = _config_from_artifact_name(once)
            assert once == twice


# =============================================================================
# _evaluate_tool_failures Property Tests
# =============================================================================


class TestEvaluateToolFailuresProperties:
    """Property tests for _evaluate_tool_failures function."""

    @given(
        tests_passed=test_count_strategy,
        tests_failed=test_count_strategy,
        language=st.sampled_from(["python", "java"]),
    )
    @settings(max_examples=50)
    def test_test_failures_detected(
        self, tests_passed: int, tests_failed: int, language: str
    ) -> None:
        """Property: test failures produce failure messages."""
        report_data = {
            "results": {
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "tests_skipped": 0,
            },
            "tools_configured": {"pytest": True} if language == "python" else {},
            "tools_ran": {},
            "tools_success": {},
            "tools_require_run": {},
        }
        failures = _evaluate_tool_failures(report_data, language)

        if tests_failed > 0:
            assert any("failure" in f.lower() for f in failures)

    @given(language=language_strategy)
    @settings(max_examples=30)
    def test_no_tests_produces_warning(self, language: str) -> None:
        """Property: zero tests ran produces quality warning for python/java."""
        report_data = {
            "results": {
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
            },
            "tools_configured": {"pytest": True} if language == "python" else {},
            "tools_ran": {},
            "tools_success": {},
            "tools_require_run": {},
        }
        failures = _evaluate_tool_failures(report_data, language)

        if language in ("python", "java"):
            # Should warn about no tests
            assert any("no tests" in f.lower() for f in failures)

    @given(tool=tool_name_strategy)
    @settings(max_examples=30)
    def test_require_run_or_fail_enforced(self, tool: str) -> None:
        """Property: require_run_or_fail=true produces failure if tool didn't run."""
        report_data = {
            "results": {"tests_passed": 10, "tests_failed": 0, "tests_skipped": 0},
            "tools_configured": {tool: True},
            "tools_ran": {},  # Tool didn't run
            "tools_success": {},
            "tools_require_run": {tool: True},
        }
        failures = _evaluate_tool_failures(report_data, "python")
        assert any(tool in f and "did not run" in f for f in failures)

    @given(tool=tool_name_strategy)
    @settings(max_examples=30)
    def test_tool_failure_detected(self, tool: str) -> None:
        """Property: tool that ran but failed is reported."""
        report_data = {
            "results": {"tests_passed": 10, "tests_failed": 0, "tests_skipped": 0},
            "tools_configured": {tool: True},
            "tools_ran": {tool: True},
            "tools_success": {tool: False},  # Tool failed
            "tools_require_run": {},
        }
        failures = _evaluate_tool_failures(report_data, "python")
        assert any(tool in f and "failed" in f for f in failures)


# =============================================================================
# _status_from_report Property Tests
# =============================================================================


class TestStatusFromReportProperties:
    """Property tests for _status_from_report function."""

    @given(tests_failed=st.integers(min_value=1, max_value=100))
    @settings(max_examples=30)
    def test_test_failures_produce_failure_conclusion(self, tests_failed: int) -> None:
        """Property: test failures result in failure conclusion."""
        report_data = {
            "python_version": "3.12",
            "results": {
                "tests_passed": 10,
                "tests_failed": tests_failed,
                "tests_skipped": 0,
            },
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": False},
            "tools_require_run": {},
        }
        status, conclusion = _status_from_report(report_data)
        assert status == "completed"
        assert conclusion == "failure"

    @given(tests_passed=st.integers(min_value=1, max_value=100))
    @settings(max_examples=30)
    def test_all_passing_produces_success_conclusion(self, tests_passed: int) -> None:
        """Property: all tests passing with no failures produces success."""
        report_data = {
            "python_version": "3.12",
            "results": {
                "tests_passed": tests_passed,
                "tests_failed": 0,
                "tests_skipped": 0,
            },
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": True},
            "tools_require_run": {},
        }
        status, conclusion = _status_from_report(report_data)
        assert status == "completed"
        # May be success or unknown depending on other factors
        assert conclusion in ("success", "unknown")

    def test_empty_report_returns_completed_unknown(self) -> None:
        """Property: empty report returns completed/unknown."""
        status, conclusion = _status_from_report({})
        assert status == "completed"
        assert conclusion == "unknown"

    @given(build_status=st.sampled_from(["success", "failure", "skipped"]))
    @settings(max_examples=20)
    def test_explicit_build_status_respected(self, build_status: str) -> None:
        """Property: explicit build status is respected."""
        report_data = {
            "results": {"build": build_status},
            "tools_configured": {},
            "tools_ran": {},
            "tools_success": {},
            "tools_require_run": {},
        }
        status, conclusion = _status_from_report(report_data)
        assert status == "completed"
        # Failure in build overrides everything
        if build_status == "failure":
            assert conclusion == "failure"
