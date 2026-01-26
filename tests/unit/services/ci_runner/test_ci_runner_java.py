"""Tests for ci_runner Java tool runner functions.

Split from test_ci_runner.py for better organization.
Tests: run_java_build, run_jacoco, run_checkstyle, run_spotbugs, run_pmd, run_docker
"""

# TEST-METRICS:

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestRunJavaBuild:
    """Tests for run_java_build function."""

    def test_maven_build_success(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_java_build

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "pom.xml").write_text("<project/>")
        (tmp_path / "mvnw").write_text("#!/bin/sh\n")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "BUILD SUCCESS"
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_java_build(tmp_path, output_dir, "maven", jacoco_enabled=False)

        assert result.tool == "build"  # run_java_build uses "build" as tool name
        assert result.ran is True
        assert result.success is True

    def test_gradle_build_success(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_java_build

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "build.gradle").write_text("apply plugin: 'java'")
        (tmp_path / "gradlew").write_text("#!/bin/sh\n")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "BUILD SUCCESSFUL"
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_java_build(tmp_path, output_dir, "gradle", jacoco_enabled=False)

        assert result.tool == "build"  # run_java_build uses "build" as tool name
        assert result.ran is True
        assert result.success is True

    def test_maven_build_with_jacoco(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_java_build

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "pom.xml").write_text("<project/>")
        (tmp_path / "mvnw").write_text("#!/bin/sh\n")

        # Create jacoco report
        jacoco_dir = tmp_path / "target" / "site" / "jacoco"
        jacoco_dir.mkdir(parents=True)
        (jacoco_dir / "jacoco.xml").write_text("""<?xml version="1.0"?>
            <report name="test">
              <counter type="LINE" missed="20" covered="80"/>
            </report>""")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "BUILD SUCCESS"
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_java_build(tmp_path, output_dir, "maven", jacoco_enabled=True)

        assert result.tool == "build"
        assert result.success is True
        assert result.metrics["coverage"] == 80

    def test_maven_build_with_jacoco_aggregate(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_java_build

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "pom.xml").write_text("<project/>")
        (tmp_path / "mvnw").write_text("#!/bin/sh\n")

        jacoco_dir = tmp_path / "module-a" / "target" / "site" / "jacoco-aggregate"
        jacoco_dir.mkdir(parents=True)
        (jacoco_dir / "jacoco.xml").write_text("""<?xml version="1.0"?>
            <report name="test">
              <counter type="LINE" missed="10" covered="40"/>
            </report>""")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "BUILD SUCCESS"
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_java_build(tmp_path, output_dir, "maven", jacoco_enabled=True)

        assert result.tool == "build"
        assert result.success is True
        assert result.metrics["coverage"] == 80


class TestRunJacoco:
    """Tests for run_jacoco function."""

    def test_parses_jacoco_xml(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_jacoco

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create jacoco.xml
        target_dir = tmp_path / "target" / "site" / "jacoco"
        target_dir.mkdir(parents=True)
        (target_dir / "jacoco.xml").write_text("""<?xml version="1.0"?>
            <report name="test">
              <counter type="LINE" missed="20" covered="80"/>
            </report>""")

        result = run_jacoco(tmp_path, output_dir)

        assert result.tool == "jacoco"
        assert result.ran is True
        assert result.metrics["coverage"] == 80.0

    def test_parses_nested_jacoco_aggregate_xml(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_jacoco

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        target_dir = tmp_path / "module-a" / "target" / "site" / "jacoco-aggregate"
        target_dir.mkdir(parents=True)
        (target_dir / "jacoco.xml").write_text("""<?xml version="1.0"?>
            <report name="test">
              <counter type="LINE" missed="10" covered="40"/>
            </report>""")

        result = run_jacoco(tmp_path, output_dir)

        assert result.tool == "jacoco"
        assert result.ran is True
        assert result.success is True
        assert result.metrics["coverage"] == 80.0


class TestRunCheckstyle:
    """Tests for run_checkstyle function."""

    def test_parses_checkstyle_xml(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_checkstyle

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "mvnw").write_text("#!/bin/sh\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir(parents=True)
        (target_dir / "checkstyle-result.xml").write_text("""<?xml version="1.0"?>
            <checkstyle>
              <file name="Test.java">
                <error severity="error" message="Missing Javadoc"/>
                <error severity="error" message="Another error"/>
              </file>
            </checkstyle>""")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_checkstyle(tmp_path, output_dir, "maven")

        assert result.tool == "checkstyle"
        assert result.ran is True
        assert result.metrics["checkstyle_issues"] == 2

    def test_missing_report_marks_failure(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_checkstyle

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "mvnw").write_text("#!/bin/sh\n")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_checkstyle(tmp_path, output_dir, "maven")

        assert result.ran is True
        assert result.success is False
        assert result.metrics["report_found"] is False


class TestRunSpotbugs:
    """Tests for run_spotbugs function."""

    def test_parses_spotbugs_xml(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_spotbugs

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "mvnw").write_text("#!/bin/sh\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir(parents=True)
        (target_dir / "spotbugsXml.xml").write_text("""<?xml version="1.0"?>
            <BugCollection>
              <BugInstance type="NP_NULL_ON_SOME_PATH" priority="1"/>
              <BugInstance type="DM_DEFAULT_ENCODING" priority="2"/>
            </BugCollection>""")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_spotbugs(tmp_path, output_dir, "maven")

        assert result.tool == "spotbugs"
        assert result.ran is True
        assert result.metrics["spotbugs_issues"] == 2


class TestRunPitest:
    """Tests for run_pitest function."""

    def test_missing_report_marks_failure(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_pitest

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "mvnw").write_text("#!/bin/sh\n")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_pitest(tmp_path, output_dir, "maven")

        assert result.ran is True
        assert result.success is False
        assert result.metrics["report_found"] is False


class TestRunOwasp:
    """Tests for run_owasp function."""

    def test_maven_includes_json_format(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_owasp

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        report_dir = tmp_path / "target"
        report_dir.mkdir(parents=True)
        (report_dir / "dependency-check-report.json").write_text(
            '{"dependencies": []}', encoding="utf-8"
        )

        captured: dict[str, object] = {}

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            captured["cmd"] = cmd
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            return mock_proc

        with patch("cihub.core.ci_runner.shared._run_tool_command", side_effect=_fake_run):
            result = run_owasp(tmp_path, output_dir, "maven", use_nvd_api_key=False)

        assert any("org.owasp:dependency-check-maven" in part for part in captured["cmd"])
        assert "-Dformat=JSON" in captured["cmd"]
        assert f"-DoutputDirectory={output_dir.resolve()}" in captured["cmd"]
        assert f"-DdataDirectory={(output_dir / 'dependency-check-data').resolve()}" in captured["cmd"]
        assert result.success is True

    def test_missing_report_fails_without_placeholder(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_owasp

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            return mock_proc

        with patch("cihub.core.ci_runner.shared._run_tool_command", side_effect=_fake_run):
            result = run_owasp(tmp_path, output_dir, "maven", use_nvd_api_key=False)

        assert result.success is False
        assert result.metrics["report_found"] is False

    def test_nvd_403_without_report_fails(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_owasp

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "Error updating the NVD Data; the NVD returned a 403 or 404 error"
            return mock_proc

        with patch("cihub.core.ci_runner.shared._run_tool_command", side_effect=_fake_run):
            result = run_owasp(tmp_path, output_dir, "gradle", use_nvd_api_key=True)

        assert result.success is False
        assert result.metrics["report_found"] is False
        assert result.metrics["owasp_data_missing"] is True

    def test_nvd_403_falls_back_to_ossindex(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_owasp

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        captured_cmds: list[list[str]] = []

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            captured_cmds.append(cmd)
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "Error updating the NVD Data; the NVD returned a 403 or 404 error"
            return mock_proc

        with patch.dict(os.environ, {"NVD_API_KEY": "test-key"}, clear=True):
            with patch("cihub.core.ci_runner.shared._run_tool_command", side_effect=_fake_run):
                result = run_owasp(tmp_path, output_dir, "maven", use_nvd_api_key=True)

        assert len(captured_cmds) == 2
        assert any("test-key" in part for part in captured_cmds[0])
        assert "-Danalyzer.nvdcve.enabled=false" in captured_cmds[1]
        assert "-Dupdater.nvdcve.enabled=false" in captured_cmds[1]
        assert "-Danalyzer.cpe.enabled=false" in captured_cmds[1]
        assert "-Danalyzer.npm.cpe.enabled=false" in captured_cmds[1]
        assert "-DossindexAnalyzerEnabled=true" in captured_cmds[1]
        assert result.success is False

    def test_fatal_errors_mark_failure(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_owasp

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Fatal exception(s) analyzing module"
            mock_proc.stderr = ""
            return mock_proc

        with patch("cihub.core.ci_runner.shared._run_tool_command", side_effect=_fake_run):
            result = run_owasp(tmp_path, output_dir, "maven", use_nvd_api_key=False)

        assert result.success is False
        assert result.metrics["owasp_fatal_errors"] is True

    def test_corrupt_db_triggers_purge_and_retry(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_owasp

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        report_dir = tmp_path / "target"
        report_dir.mkdir(parents=True)
        (report_dir / "dependency-check-report.json").write_text(
            '{"dependencies": []}', encoding="utf-8"
        )

        def _make_proc(stdout: str) -> MagicMock:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = stdout
            mock_proc.stderr = ""
            return mock_proc

        procs = [
            _make_proc(
                "Incompatible or corrupt database found. To resolve this issue please remove "
                "the existing database by running purge"
            ),
            _make_proc("purge complete"),
            _make_proc("analysis complete"),
        ]

        with patch(
            "cihub.core.ci_runner.shared._run_tool_command", side_effect=procs
        ) as run_mock:
            result = run_owasp(tmp_path, output_dir, "maven", use_nvd_api_key=False)

        assert run_mock.call_count == 3
        assert result.metrics["owasp_db_purged"] is True
        assert result.success is True

    def test_missing_nvd_key_allows_update(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_owasp

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        report_dir = tmp_path / "target"
        report_dir.mkdir(parents=True)
        (report_dir / "dependency-check-report.json").write_text(
            '{"dependencies": []}', encoding="utf-8"
        )

        captured: dict[str, object] = {}

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            captured["cmd"] = cmd
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            return mock_proc

        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.core.ci_runner.shared._run_tool_command", side_effect=_fake_run):
                result = run_owasp(tmp_path, output_dir, "maven", use_nvd_api_key=True)

        assert "-Danalyzer.nvdcve.enabled=false" in captured["cmd"]
        assert "-Dupdater.nvdcve.enabled=false" in captured["cmd"]
        assert "-Danalyzer.cpe.enabled=false" in captured["cmd"]
        assert "-Danalyzer.npm.cpe.enabled=false" in captured["cmd"]
        assert "-DossindexAnalyzerEnabled=true" in captured["cmd"]
        assert result.success is True

    def test_use_nvd_api_key_false_disables_update(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_owasp

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        report_dir = tmp_path / "target"
        report_dir.mkdir(parents=True)
        (report_dir / "dependency-check-report.json").write_text(
            '{"dependencies": []}', encoding="utf-8"
        )

        captured: dict[str, object] = {}

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            captured["cmd"] = cmd
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            return mock_proc

        with patch("cihub.core.ci_runner.shared._run_tool_command", side_effect=_fake_run):
            result = run_owasp(tmp_path, output_dir, "maven", use_nvd_api_key=False)

        assert "-Danalyzer.nvdcve.enabled=false" in captured["cmd"]
        assert "-Dupdater.nvdcve.enabled=false" in captured["cmd"]
        assert "-Danalyzer.cpe.enabled=false" in captured["cmd"]
        assert "-Danalyzer.npm.cpe.enabled=false" in captured["cmd"]
        assert "-DossindexAnalyzerEnabled=true" in captured["cmd"]
        assert result.success is True


class TestRunPmd:
    """Tests for run_pmd function."""

    def test_parses_pmd_xml(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_pmd

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "mvnw").write_text("#!/bin/sh\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir(parents=True)
        (target_dir / "pmd.xml").write_text("""<?xml version="1.0"?>
            <pmd>
              <file name="Test.java">
                <violation priority="1">Issue 1</violation>
                <violation priority="3">Issue 2</violation>
              </file>
            </pmd>""")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_pmd(tmp_path, output_dir, "maven")

        assert result.tool == "pmd"
        assert result.ran is True
        assert result.metrics["pmd_violations"] == 2


class TestRunDocker:
    """Tests for run_docker function."""

    def test_missing_compose_file(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_docker

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = run_docker(tmp_path, output_dir, compose_file="docker-compose.yml")

        assert result.tool == "docker"
        assert result.ran is False
        assert result.success is False
        assert result.metrics["docker_missing_compose"] is True

    def test_runs_compose(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_docker

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "docker-compose.yml").write_text("services: {}\n")

        mock_up = MagicMock(returncode=0, stdout="up", stderr="")
        mock_logs = MagicMock(returncode=0, stdout="logs", stderr="")
        mock_down = MagicMock(returncode=0, stdout="down", stderr="")

        with patch("cihub.core.ci_runner.shared.resolve_executable", return_value="docker"):
            with patch("cihub.core.ci_runner.shared._run_command", side_effect=[mock_up, mock_logs, mock_down]):
                result = run_docker(tmp_path, output_dir, compose_file="docker-compose.yml")

        assert result.tool == "docker"
        assert result.ran is True
        assert result.success is True
        assert (output_dir / "docker-compose.log").exists()
