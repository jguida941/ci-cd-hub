"""Tests for CI engine notification functions.

Split from test_ci_engine.py for better organization.
Tests: _collect_codecov_files, _run_codecov_upload, _send_slack, _send_email, _notify
"""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from cihub.services.ci_engine import (
    _collect_codecov_files,
    _notify,
    _run_codecov_upload,
    _send_email,
    _send_slack,
)


class TestCollectCodecovFiles:
    """Tests for _collect_codecov_files function."""

    def test_collects_python_coverage(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        tool_outputs = {"pytest": {"artifacts": {"coverage": str(coverage)}}}
        files = _collect_codecov_files("python", tmp_path, tool_outputs)
        assert len(files) == 1
        assert files[0] == coverage

    def test_fallback_coverage_path(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        tool_outputs: dict = {}
        files = _collect_codecov_files("python", tmp_path, tool_outputs)
        assert len(files) == 1

    def test_collects_java_jacoco(self, tmp_path: Path) -> None:
        jacoco = tmp_path / "jacoco.xml"
        jacoco.write_text("<report/>")
        tool_outputs = {"jacoco": {"artifacts": {"report": str(jacoco)}}}
        files = _collect_codecov_files("java", tmp_path, tool_outputs)
        assert len(files) == 1


class TestRunCodecovUpload:
    """Tests for _run_codecov_upload function."""

    def test_warns_when_no_files(self) -> None:
        problems: list = []
        _run_codecov_upload([], False, problems)
        assert len(problems) == 1
        assert "no coverage files" in problems[0]["message"].lower()

    def test_warns_when_codecov_missing(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        problems: list = []
        with patch("shutil.which", return_value=None):
            _run_codecov_upload([coverage], False, problems)
        assert len(problems) == 1
        assert "uploader not found" in problems[0]["message"].lower()

    def test_runs_codecov_successfully(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("shutil.which", return_value="/usr/bin/codecov"):
            with patch("subprocess.run", return_value=mock_proc):
                _run_codecov_upload([coverage], False, problems)
        assert len(problems) == 0

    def test_reports_codecov_failure(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "upload failed"
        mock_proc.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/codecov"):
            with patch("subprocess.run", return_value=mock_proc):
                _run_codecov_upload([coverage], False, problems)
        assert len(problems) == 1
        assert "upload failed" in problems[0]["message"]


class TestSendSlack:
    """Tests for _send_slack function."""

    def test_sends_notification(self) -> None:
        problems: list = []
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            _send_slack("https://hooks.slack.com/test", "Test message", problems)
        assert len(problems) == 0

    def test_reports_failure_status(self) -> None:
        problems: list = []
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            _send_slack("https://hooks.slack.com/test", "Test message", problems)
        assert len(problems) == 1
        assert problems[0]["code"] == "CIHUB-CI-SLACK-FAILED"


class TestSendEmail:
    """Tests for _send_email function."""

    def test_warns_when_host_missing(self) -> None:
        problems: list = []
        email_cfg: dict = {}
        env: dict = {}
        _send_email("Subject", "Body", problems, email_cfg, env)
        assert len(problems) == 1
        assert "SMTP_HOST" in problems[0]["message"]

    def test_warns_when_recipients_missing(self) -> None:
        problems: list = []
        email_cfg: dict = {}
        env = {"SMTP_HOST": "mail.example.com"}
        _send_email("Subject", "Body", problems, email_cfg, env)
        assert len(problems) == 1
        assert "recipients" in problems[0]["message"].lower()

    def test_warns_on_invalid_port(self) -> None:
        problems: list = []
        email_cfg: dict = {}
        env = {
            "SMTP_HOST": "mail.example.com",
            "SMTP_PORT": "invalid",
            "SMTP_TO": "test@example.com",
        }
        # Should still attempt send with default port 25
        with patch("smtplib.SMTP") as mock_smtp:
            mock_client = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            _send_email("Subject", "Body", problems, email_cfg, env)
        # Should have warned about invalid port
        port_warning = [p for p in problems if "port" in p["message"].lower()]
        assert len(port_warning) == 1


class TestNotify:
    """Tests for _notify function."""

    def test_does_nothing_when_disabled(self) -> None:
        config = {"notifications": {"slack": {"enabled": False}}}
        report = {"repository": "owner/repo", "branch": "main"}
        problems: list = []
        with patch("cihub.services.ci_engine.notifications._send_slack") as mock_slack:
            _notify(True, config, report, problems, {})
        mock_slack.assert_not_called()

    def test_sends_slack_on_failure(self) -> None:
        config = {"notifications": {"slack": {"enabled": True, "on_failure": True, "on_success": False}}}
        report = {"repository": "owner/repo", "branch": "main"}
        env = {"CIHUB_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}
        problems: list = []
        with patch("cihub.services.ci_engine.notifications._send_slack") as mock_slack:
            _notify(False, config, report, problems, env)
        mock_slack.assert_called_once()

    def test_warns_when_webhook_missing(self) -> None:
        config = {"notifications": {"slack": {"enabled": True, "on_failure": True}}}
        report = {"repository": "owner/repo", "branch": "main"}
        problems: list = []
        _notify(False, config, report, problems, {})
        assert len(problems) == 1
        assert "CIHUB_SLACK_WEBHOOK_URL" in problems[0]["message"]

    def test_sends_email_on_failure(self) -> None:
        config = {"notifications": {"email": {"enabled": True, "on_failure": True}}}
        report = {"repository": "owner/repo", "branch": "main"}
        env = {"SMTP_HOST": "mail.example.com", "SMTP_TO": "test@example.com"}
        problems: list = []
        with patch("smtplib.SMTP") as mock_smtp:
            mock_client = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            _notify(False, config, report, problems, env)
        # Email was sent via SMTP
        mock_smtp.assert_called_once()
