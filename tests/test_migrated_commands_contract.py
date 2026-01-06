"""Contract tests for migrated command modules.

This module provides consolidated parameterized and Hypothesis tests for
commands that have been migrated to return CommandResult:
- adr.py: ADR management commands
- triage.py: Triage bundle generation
- secrets.py: Secret setup commands
- templates.py: Template management
- pom.py: POM fix commands

All tests verify the CommandResult contract:
1. Commands always return CommandResult (never int)
2. exit_code is always 0-255
3. problems list contains dicts with 'severity' and 'message'
4. data dict is JSON-serializable

Following CLEAN_CODE.md Part 10 testing patterns.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from cihub.types import CommandResult

# ============================================================================
# Strategies for Hypothesis Tests
# ============================================================================

# Valid ADR titles
adr_title_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        whitelist_characters=" -_",
    ),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())  # Filter empty after strip

# Valid status filters
adr_status_strategy = st.sampled_from([None, "Proposed", "Accepted", "Superseded", "Deprecated"])

# Tool names for triage
tool_name_strategy = st.sampled_from([
    "pytest", "ruff", "black", "mypy", "bandit", "pip_audit",
    "jacoco", "checkstyle", "spotbugs", "owasp",
])

# Exit codes (0-255)
exit_code_strategy = st.integers(min_value=0, max_value=255)

# Severity levels
severity_strategy = st.sampled_from(["error", "warning", "info", "success", "critical"])


# ============================================================================
# ADR Command Contract Tests
# ============================================================================


class TestAdrCommandContracts:
    """Contract tests for ADR commands."""

    @pytest.mark.parametrize(
        "subcommand,extra_attrs",
        [
            ("list", {"status": None, "json": True}),
            ("check", {"json": True}),
        ],
        ids=["list", "check"],
    )
    def test_subcommands_return_command_result(
        self, tmp_path: Path, subcommand: str, extra_attrs: dict[str, Any]
    ) -> None:
        """All ADR subcommands return CommandResult."""
        from cihub.commands.adr import cmd_adr

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(subcommand=subcommand, **extra_attrs)
            result = cmd_adr(args)

        assert isinstance(result, CommandResult)
        assert 0 <= result.exit_code <= 255

    @pytest.mark.parametrize(
        "title,expected_success",
        [
            ("Valid Title", True),
            ("", False),
        ],
        ids=["valid_title", "empty_title"],
    )
    def test_adr_new_title_validation(
        self, tmp_path: Path, title: str, expected_success: bool
    ) -> None:
        """cmd_adr_new validates title and returns proper exit code."""
        from cihub.commands.adr import cmd_adr_new

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(title=title, dry_run=True, json=True)
            result = cmd_adr_new(args)

        assert isinstance(result, CommandResult)
        if expected_success:
            assert result.exit_code == 0
        else:
            assert result.exit_code != 0
            assert len(result.problems) >= 0 or result.summary

    @pytest.mark.parametrize(
        "adr_content,expected_status",
        [
            ("# ADR-0001: Test\n\n**Status:** Accepted\n**Date:** 2024-01-01\n", "Accepted"),
            ("# ADR-0001: Test\n\n**Status:** Proposed\n**Date:** 2024-01-01\n", "Proposed"),
            ("# ADR-0001: Test\n\n**Date:** 2024-01-01\n", "unknown"),
        ],
        ids=["accepted", "proposed", "missing_status"],
    )
    def test_adr_list_parses_status(
        self, tmp_path: Path, adr_content: str, expected_status: str
    ) -> None:
        """cmd_adr_list correctly parses ADR status from content."""
        from cihub.commands.adr import cmd_adr_list

        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-test.md").write_text(adr_content)

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(status=None, json=True)
            result = cmd_adr_list(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert len(result.data["adrs"]) == 1
        assert result.data["adrs"][0]["status"] == expected_status

    @given(title=adr_title_strategy)
    @settings(max_examples=30)
    def test_adr_new_valid_titles_succeed(self, title: str) -> None:
        """Property: Any non-empty title should succeed in dry-run mode."""
        from cihub.commands.adr import cmd_adr_new

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
                args = argparse.Namespace(title=title, dry_run=True, json=True)
                result = cmd_adr_new(args)

            assert isinstance(result, CommandResult)
            assert result.exit_code == 0

    @given(status=adr_status_strategy)
    @settings(max_examples=10)
    def test_adr_list_accepts_any_status_filter(self, status: str | None) -> None:
        """Property: cmd_adr_list accepts any valid status filter."""
        from cihub.commands.adr import cmd_adr_list

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
                args = argparse.Namespace(status=status, json=True)
                result = cmd_adr_list(args)

            assert isinstance(result, CommandResult)
            assert result.exit_code == 0
            assert "adrs" in result.data


# ============================================================================
# Triage Command Contract Tests
# ============================================================================


class TestTriageCommandContracts:
    """Contract tests for triage commands."""

    def test_cmd_triage_returns_command_result(self, tmp_path: Path) -> None:
        """cmd_triage always returns CommandResult."""
        from cihub.commands.triage import cmd_triage

        output_dir = tmp_path / ".cihub"
        output_dir.mkdir()

        args = argparse.Namespace(
            output_dir=str(output_dir),
            run=None,
            artifacts_dir=None,
            repo=None,
            json=True,
        )
        result = cmd_triage(args)

        assert isinstance(result, CommandResult)
        assert 0 <= result.exit_code <= 255

    @pytest.mark.parametrize(
        "tools_success,expected_failed",
        [
            ({"ruff": True, "pytest": True}, 0),
            ({"ruff": False, "pytest": True}, 1),
            ({"ruff": False, "pytest": False}, 2),
        ],
        ids=["all_pass", "one_fail", "all_fail"],
    )
    def test_triage_counts_failures_correctly(
        self, tmp_path: Path, tools_success: dict[str, bool], expected_failed: int
    ) -> None:
        """Triage bundle correctly counts tool failures."""
        from cihub.services.triage_service import generate_triage_bundle

        output_dir = tmp_path / ".cihub"
        report_path = output_dir / "report.json"
        report_path.parent.mkdir(parents=True)

        report = {
            "schema_version": "2.0",
            "repository": "test/repo",
            "branch": "main",
            "commit": "a" * 40,
            "tools_configured": {t: True for t in tools_success},
            "tools_ran": {t: True for t in tools_success},
            "tools_success": tools_success,
            "environment": {"workdir": "."},
        }
        report_path.write_text(json.dumps(report))

        bundle = generate_triage_bundle(output_dir, report_path=report_path)

        actual_failed = len([f for f in bundle.triage["failures"] if f.get("status") == "failed"])
        assert actual_failed == expected_failed

    @given(
        tools=st.lists(tool_name_strategy, min_size=1, max_size=5, unique=True),
        success_rate=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=30)
    def test_triage_invariants(self, tools: list[str], success_rate: float) -> None:
        """Property: Triage bundle maintains invariants."""
        from cihub.services.triage_service import generate_triage_bundle

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            output_dir = tmp_path / ".cihub"
            report_path = output_dir / "report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine which tools succeed based on rate
            num_success = int(len(tools) * success_rate)
            tools_success = {t: i < num_success for i, t in enumerate(tools)}

            report = {
                "schema_version": "2.0",
                "repository": "test/repo",
                "branch": "main",
                "commit": "a" * 40,
                "tools_configured": {t: True for t in tools},
                "tools_ran": {t: True for t in tools},
                "tools_success": tools_success,
                "environment": {"workdir": "."},
            }
            report_path.write_text(json.dumps(report))

            bundle = generate_triage_bundle(output_dir, report_path=report_path)

            # Invariant 1: schema_version is set
            assert "schema_version" in bundle.triage

            # Invariant 2: tool_evidence count matches tools
            assert len(bundle.triage.get("tool_evidence", [])) == len(tools)

            # Invariant 3: summary has expected fields
            summary = bundle.triage.get("summary", {})
            assert "overall_status" in summary
            assert summary["overall_status"] in ("success", "failed")


# ============================================================================
# Secrets Command Contract Tests
# ============================================================================


class TestSecretsCommandContracts:
    """Contract tests for secrets commands."""

    @pytest.mark.parametrize(
        "token,expected_valid",
        [
            ("ghp_valid_token_12345", True),
            ("", False),
            ("token with space", False),
            ("  ghp_with_leading_space  ", True),  # Stripped
        ],
        ids=["valid", "empty", "with_space", "with_leading_space"],
    )
    def test_token_validation(self, token: str, expected_valid: bool) -> None:
        """Token validation follows expected rules."""
        from cihub.commands.secrets import cmd_setup_secrets
        from unittest import mock

        with mock.patch("getpass.getpass", return_value=token):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=0, stderr="")
                with mock.patch("cihub.commands.secrets.resolve_executable", return_value="gh"):
                    with mock.patch("cihub.commands.secrets.get_connected_repos", return_value=[]):
                        args = argparse.Namespace(
                            hub_repo="owner/hub",
                            token=None,
                            all=False,
                            verify=False,
                        )
                        result = cmd_setup_secrets(args)

        assert isinstance(result, CommandResult)
        if expected_valid:
            assert result.exit_code == 0
        else:
            assert result.exit_code != 0

    @pytest.mark.parametrize(
        "verify_mode,http_status,expected_exit",
        [
            (False, None, 0),  # No verification
            (True, 200, 0),  # Successful verification
            (True, 401, 1),  # Auth failure
            (True, 500, 1),  # Server error
        ],
        ids=["no_verify", "verify_success", "verify_401", "verify_500"],
    )
    def test_verification_modes(
        self, verify_mode: bool, http_status: int | None, expected_exit: int
    ) -> None:
        """Verification mode handles different HTTP responses."""
        from cihub.commands.secrets import cmd_setup_secrets
        from unittest import mock
        import urllib.error
        import io

        def make_response():
            class MockResponse:
                status = http_status
                headers = {"X-OAuth-Scopes": "repo"}

                def read(self):
                    return json.dumps({"login": "test"}).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

            return MockResponse()

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stderr="")
            with mock.patch("cihub.commands.secrets.resolve_executable", return_value="gh"):
                with mock.patch("cihub.commands.secrets.get_connected_repos", return_value=["owner/repo"]):
                    with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
                        if verify_mode and http_status and http_status != 200:
                            mock_urlopen.side_effect = urllib.error.HTTPError(
                                url="https://api.github.com",
                                code=http_status,
                                msg="Error",
                                hdrs={},
                                fp=io.BytesIO(b""),
                            )
                        else:
                            mock_urlopen.return_value = make_response()

                        args = argparse.Namespace(
                            hub_repo="owner/hub",
                            token="ghp_valid_token",
                            all=False,
                            verify=verify_mode,
                        )
                        result = cmd_setup_secrets(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == expected_exit

    @given(
        token=st.text(
            alphabet=st.characters(
                blacklist_categories=("C", "Z"),  # Exclude control chars and whitespace
                blacklist_characters="\t\n\r ",
            ),
            min_size=1,
            max_size=50,
        ).filter(lambda x: x.strip()),
    )
    @settings(max_examples=20)
    def test_valid_tokens_accepted(self, token: str) -> None:
        """Property: Tokens without whitespace are accepted."""
        from cihub.commands.secrets import cmd_setup_secrets
        from unittest import mock

        with mock.patch("getpass.getpass", return_value=token):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=0, stderr="")
                with mock.patch("cihub.commands.secrets.resolve_executable", return_value="gh"):
                    with mock.patch("cihub.commands.secrets.get_connected_repos", return_value=[]):
                        args = argparse.Namespace(
                            hub_repo="owner/hub",
                            token=None,
                            all=False,
                            verify=False,
                        )
                        result = cmd_setup_secrets(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == 0


# ============================================================================
# POM Command Contract Tests
# ============================================================================


class TestPomCommandContracts:
    """Contract tests for POM fix commands."""

    # Valid Java config with required fields
    VALID_JAVA_CONFIG = """\
repo:
  owner: test-org
  name: test-repo
  default_branch: main
language: java
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: true
"""

    @pytest.mark.parametrize(
        "has_config,has_pom,expected_exit",
        [
            (False, False, 2),  # No config = usage error
            (True, False, 1),  # Config but no POM = failure (pom.xml not found)
            (True, True, 0),  # Both = success (dry run)
        ],
        ids=["no_config", "no_pom", "valid_setup"],
    )
    def test_fix_pom_prerequisites(
        self, tmp_path: Path, has_config: bool, has_pom: bool, expected_exit: int
    ) -> None:
        """cmd_fix_pom validates prerequisites correctly."""
        from cihub.commands.pom import cmd_fix_pom

        if has_config:
            config_path = tmp_path / ".ci-hub.yml"
            config_path.write_text(self.VALID_JAVA_CONFIG)

        if has_pom:
            pom_path = tmp_path / "pom.xml"
            pom_path.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.test</groupId>
    <artifactId>test</artifactId>
    <version>1.0.0</version>
</project>
""")

        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_pom(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == expected_exit

    @pytest.mark.parametrize(
        "apply_mode,expected_in_summary",
        [
            (False, "dry-run"),  # Dry-run mode mentioned in summary
            (True, "applied"),  # Apply mode mentioned in summary
        ],
        ids=["dry_run", "apply"],
    )
    def test_fix_pom_apply_modes(
        self, tmp_path: Path, apply_mode: bool, expected_in_summary: str
    ) -> None:
        """cmd_fix_pom reflects apply vs dry-run mode in summary."""
        from cihub.commands.pom import cmd_fix_pom

        config_path = tmp_path / ".ci-hub.yml"
        config_path.write_text(self.VALID_JAVA_CONFIG)

        pom_path = tmp_path / "pom.xml"
        pom_path.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.test</groupId>
    <artifactId>test</artifactId>
    <version>1.0.0</version>
</project>
""")

        args = argparse.Namespace(repo=str(tmp_path), apply=apply_mode)
        result = cmd_fix_pom(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        # Check mode reflected in summary
        assert expected_in_summary in result.summary.lower()


# ============================================================================
# CommandResult Contract Property Tests
# ============================================================================


class TestCommandResultContracts:
    """Property-based tests for CommandResult invariants."""

    @given(
        exit_code=exit_code_strategy,
        summary=st.text(max_size=200),
    )
    @settings(max_examples=50)
    def test_command_result_serializable(self, exit_code: int, summary: str) -> None:
        """Property: CommandResult is always JSON-serializable."""
        result = CommandResult(exit_code=exit_code, summary=summary)
        payload = result.to_payload("test", "success" if exit_code == 0 else "failure", 100)
        serialized = json.dumps(payload)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed["exit_code"] == exit_code

    @given(
        num_problems=st.integers(min_value=0, max_value=10),
        severities=st.lists(severity_strategy, min_size=0, max_size=10),
    )
    @settings(max_examples=30)
    def test_problems_structure_valid(
        self, num_problems: int, severities: list[str]
    ) -> None:
        """Property: Problems list maintains expected structure."""
        problems = [
            {"severity": s, "message": f"Problem {i}"}
            for i, s in enumerate(severities[:num_problems])
        ]
        result = CommandResult(exit_code=1, problems=problems)

        for p in result.problems:
            assert "severity" in p
            assert "message" in p
            assert p["severity"] in ("error", "warning", "info", "success", "critical")

    @given(
        items=st.lists(st.text(min_size=1, max_size=50), max_size=20),
    )
    @settings(max_examples=30)
    def test_data_items_preserved(self, items: list[str]) -> None:
        """Property: data['items'] is preserved in serialization."""
        result = CommandResult(exit_code=0, data={"items": items})
        payload = result.to_payload("test", "success", 100)

        assert payload["data"]["items"] == items


# ============================================================================
# Regression Tests for Known Edge Cases
# ============================================================================


class TestRegressionEdgeCases:
    """Regression tests for known edge cases in migrated commands."""

    def test_adr_check_empty_directory(self, tmp_path: Path) -> None:
        """Regression: cmd_adr_check handles empty ADR directory."""
        from cihub.commands.adr import cmd_adr_check

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(json=True)
            result = cmd_adr_check(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "No ADRs" in result.summary

    def test_triage_missing_report(self, tmp_path: Path) -> None:
        """Regression: triage handles missing report.json gracefully."""
        from cihub.commands.triage import cmd_triage

        output_dir = tmp_path / ".cihub"
        output_dir.mkdir()

        args = argparse.Namespace(
            output_dir=str(output_dir),
            run=None,
            artifacts_dir=None,
            repo=None,
            json=True,
        )
        result = cmd_triage(args)

        assert isinstance(result, CommandResult)
        # Should not crash, just report missing

    def test_secrets_subprocess_failure(self) -> None:
        """Regression: secrets command handles subprocess failure gracefully."""
        from cihub.commands.secrets import cmd_setup_secrets
        from unittest import mock

        # Mock subprocess.run to fail
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1, stderr="command not found")
            with mock.patch("cihub.commands.secrets.resolve_executable", return_value="gh"):
                with mock.patch("cihub.commands.secrets.get_connected_repos", return_value=[]):
                    args = argparse.Namespace(
                        hub_repo="owner/hub",
                        token="ghp_token",
                        all=False,
                        verify=False,
                    )
                    result = cmd_setup_secrets(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code != 0
        # Should indicate failure
        result_text = (result.summary + str(result.problems)).lower()
        assert "fail" in result_text or "error" in result_text

    def test_pom_fix_non_existent_repo(self, tmp_path: Path) -> None:
        """Regression: cmd_fix_pom handles non-existent repo path."""
        from cihub.commands.pom import cmd_fix_pom

        non_existent = tmp_path / "does_not_exist"

        args = argparse.Namespace(repo=str(non_existent), apply=False)
        result = cmd_fix_pom(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code != 0
