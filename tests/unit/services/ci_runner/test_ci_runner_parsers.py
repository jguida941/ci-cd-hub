"""Tests for ci_runner report file parser functions.

Split from test_ci_runner.py for better organization.
Tests: _parse_junit_files, _parse_jacoco_files, _parse_pitest_files,
       _parse_checkstyle_files, _parse_spotbugs_files, _parse_pmd_files,
       _parse_dependency_check, _count_pip_audit_vulns
"""

# TEST-METRICS:

from __future__ import annotations

import json
from pathlib import Path

from cihub.ci_runner import (
    _count_pip_audit_vulns,
    _parse_checkstyle_files,
    _parse_dependency_check,
    _parse_jacoco_files,
    _parse_junit_files,
    _parse_pitest_files,
    _parse_pmd_files,
    _parse_spotbugs_files,
)


class TestParseJunitFiles:
    """Tests for _parse_junit_files function."""

    def test_aggregates_multiple_files(self, tmp_path: Path) -> None:
        xml1 = '<testsuite tests="5" failures="1" errors="0" skipped="0" time="1.0"/>'
        xml2 = '<testsuite tests="3" failures="0" errors="0" skipped="1" time="0.5"/>'
        (tmp_path / "test1.xml").write_text(xml1)
        (tmp_path / "test2.xml").write_text(xml2)

        paths = [tmp_path / "test1.xml", tmp_path / "test2.xml"]
        result = _parse_junit_files(paths)

        assert result["tests_passed"] == 6
        assert result["tests_failed"] == 1
        assert result["tests_skipped"] == 1
        assert result["tests_runtime_seconds"] == 1.5


class TestParseJacocoFiles:
    """Tests for _parse_jacoco_files function."""

    def test_parses_jacoco_xml(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <report>
            <counter type="LINE" covered="80" missed="20"/>
            <counter type="BRANCH" covered="10" missed="5"/>
        </report>"""
        path = tmp_path / "jacoco.xml"
        path.write_text(xml)

        result = _parse_jacoco_files([path])

        assert result["coverage"] == 80
        assert result["coverage_lines_covered"] == 80
        assert result["coverage_lines_total"] == 100

    def test_handles_parse_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.xml"
        path.write_text("not valid xml")

        result = _parse_jacoco_files([path])

        assert result["coverage"] == 0


class TestParsePitestFiles:
    """Tests for _parse_pitest_files function."""

    def test_parses_mutations(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <mutations>
            <mutation status="KILLED"/>
            <mutation status="KILLED"/>
            <mutation status="SURVIVED"/>
            <mutation status="NO_COVERAGE"/>
        </mutations>"""
        path = tmp_path / "mutations.xml"
        path.write_text(xml)

        result = _parse_pitest_files([path])

        assert result["mutation_killed"] == 2
        assert result["mutation_survived"] == 1
        assert result["mutation_score"] == 50  # 2/(2+1+1)


class TestParseCheckstyleFiles:
    """Tests for _parse_checkstyle_files function."""

    def test_counts_errors(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <checkstyle>
            <file name="Test.java">
                <error severity="warning" message="Missing javadoc"/>
                <error severity="error" message="Wrong indent"/>
            </file>
        </checkstyle>"""
        path = tmp_path / "checkstyle-result.xml"
        path.write_text(xml)

        result = _parse_checkstyle_files([path])

        assert result["checkstyle_issues"] == 2


class TestParseSpotbugsFiles:
    """Tests for _parse_spotbugs_files function."""

    def test_counts_bugs(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <BugCollection>
            <BugInstance type="NP_NULL_ON_SOME_PATH"/>
            <BugInstance type="DM_DEFAULT_ENCODING"/>
        </BugCollection>"""
        path = tmp_path / "spotbugsXml.xml"
        path.write_text(xml)

        result = _parse_spotbugs_files([path])

        assert result["spotbugs_issues"] == 2


class TestParsePmdFiles:
    """Tests for _parse_pmd_files function."""

    def test_counts_violations(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <pmd>
            <file name="Test.java">
                <violation>Some violation</violation>
                <violation>Another violation</violation>
            </file>
        </pmd>"""
        path = tmp_path / "pmd.xml"
        path.write_text(xml)

        result = _parse_pmd_files([path])

        assert result["pmd_violations"] == 2


class TestParseDependencyCheck:
    """Tests for _parse_dependency_check function."""

    def test_counts_vulnerabilities_by_severity(self, tmp_path: Path) -> None:
        data = {
            "dependencies": [
                {
                    "vulnerabilities": [
                        {"severity": "CRITICAL"},
                        {"severity": "HIGH"},
                    ]
                },
                {
                    "vulnerabilities": [
                        {"severity": "MEDIUM"},
                        {"severity": "LOW"},
                    ]
                },
            ]
        }
        path = tmp_path / "dependency-check.json"
        path.write_text(json.dumps(data))

        result = _parse_dependency_check(path)

        assert result["owasp_critical"] == 1
        assert result["owasp_high"] == 1
        assert result["owasp_medium"] == 1
        assert result["owasp_low"] == 1

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        result = _parse_dependency_check(tmp_path / "missing.json")

        assert result["owasp_critical"] == 0


class TestCountPipAuditVulns:
    """Tests for _count_pip_audit_vulns function."""

    def test_counts_vulns_list_format(self) -> None:
        data = [
            {"name": "package1", "vulns": [{"id": "CVE-1"}, {"id": "CVE-2"}]},
            {"name": "package2", "vulnerabilities": [{"id": "CVE-3"}]},
        ]
        assert _count_pip_audit_vulns(data) == 3

    def test_counts_vulns_dependency_dict_format(self) -> None:
        data = {
            "dependencies": [
                {"name": "package1", "vulns": [{"id": "CVE-1"}]},
                {"name": "package2", "vulnerabilities": [{"id": "CVE-2"}, {"id": "CVE-3"}]},
            ]
        }
        assert _count_pip_audit_vulns(data) == 3

    def test_returns_zero_for_non_list(self) -> None:
        assert _count_pip_audit_vulns({"some": "dict"}) == 0
        assert _count_pip_audit_vulns(None) == 0
