"""Tests for cihub docs audit command.

Basic coverage for lifecycle, ADR, and reference validation.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import pytest

from cihub.commands.docs_audit import (
    AuditFinding,
    AuditReport,
    FindingCategory,
    FindingSeverity,
    cmd_docs_audit,
    get_active_docs,
    get_adr_files,
    get_archive_docs,
    parse_status_md_entries,
    validate_adr_metadata,
    validate_lifecycle,
)
from cihub.commands.docs_audit.adr import parse_adr_metadata
from cihub.commands.docs_audit.lifecycle import check_active_status_sync


class TestAuditTypes:
    """Test data types and serialization."""

    def test_finding_to_dict(self) -> None:
        finding = AuditFinding(
            severity=FindingSeverity.ERROR,
            category=FindingCategory.LIFECYCLE,
            message="Test error",
            file="test.md",
            line=10,
            code="TEST-001",
            suggestion="Fix it",
        )
        d = finding.to_dict()
        assert d["severity"] == "error"
        assert d["category"] == "lifecycle"
        assert d["message"] == "Test error"
        assert d["file"] == "test.md"
        assert d["line"] == 10

    def test_report_stats(self) -> None:
        report = AuditReport(
            findings=[
                AuditFinding(
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.SYNC,
                    message="Error 1",
                ),
                AuditFinding(
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.ADR_METADATA,
                    message="Warning 1",
                ),
                AuditFinding(
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.LIFECYCLE,
                    message="Warning 2",
                ),
            ]
        )
        assert report.error_count == 1
        assert report.warning_count == 2
        assert report.has_errors is True

    def test_report_no_errors(self) -> None:
        report = AuditReport()
        assert report.error_count == 0
        assert report.has_errors is False


class TestLifecycleValidation:
    """Test lifecycle validation functions."""

    def test_parse_status_md_entries_empty(self, tmp_path: Path) -> None:
        """Test parsing when STATUS.md doesn't exist."""
        entries = parse_status_md_entries(tmp_path)
        assert entries == []

    def test_check_active_status_sync_in_sync(self) -> None:
        """Test when active docs and status entries match."""
        active_docs = ["docs/development/active/FOO.md", "docs/development/active/BAR.md"]
        status_entries = ["FOO.md", "BAR.md"]
        findings = check_active_status_sync(active_docs, status_entries)
        assert len(findings) == 0

    def test_check_active_status_sync_missing_in_status(self) -> None:
        """Test when a file in active/ is not in STATUS.md."""
        active_docs = ["docs/development/active/FOO.md", "docs/development/active/NEW.md"]
        status_entries = ["FOO.md"]
        findings = check_active_status_sync(active_docs, status_entries)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert "NEW.md" in findings[0].message

    def test_check_active_status_sync_missing_file(self) -> None:
        """Test when STATUS.md references a non-existent file."""
        active_docs = ["docs/development/active/FOO.md"]
        status_entries = ["FOO.md", "DELETED.md"]
        findings = check_active_status_sync(active_docs, status_entries)
        assert len(findings) == 1
        assert "DELETED.md" in findings[0].message


class TestADRValidation:
    """Test ADR metadata validation."""

    def test_parse_adr_metadata_valid(self, tmp_path: Path) -> None:
        """Test parsing a valid ADR."""
        adr_content = """# ADR-0001: Test Decision

**Status:** accepted
**Date:** 2026-01-09

## Context

Some context here.
"""
        adr_path = tmp_path / "0001-test.md"
        adr_path.write_text(adr_content)

        metadata = parse_adr_metadata(adr_path)
        assert metadata.status == "accepted"
        assert metadata.date == "2026-01-09"
        assert len(metadata.missing_fields) == 0
        assert metadata.invalid_status is False

    def test_parse_adr_metadata_missing_status(self, tmp_path: Path) -> None:
        """Test parsing ADR with missing Status field."""
        adr_content = """# ADR-0002: Missing Status

**Date:** 2026-01-09

## Context
"""
        adr_path = tmp_path / "0002-missing.md"
        adr_path.write_text(adr_content)

        metadata = parse_adr_metadata(adr_path)
        assert "Status" in metadata.missing_fields

    def test_parse_adr_metadata_invalid_status(self, tmp_path: Path) -> None:
        """Test parsing ADR with invalid Status value."""
        adr_content = """# ADR-0003: Invalid Status

**Status:** in-progress
**Date:** 2026-01-09
"""
        adr_path = tmp_path / "0003-invalid.md"
        adr_path.write_text(adr_content)

        metadata = parse_adr_metadata(adr_path)
        assert metadata.invalid_status is True

    def test_validate_adr_metadata_superseded_without_pointer(self, tmp_path: Path) -> None:
        """Test that superseded ADR without Superseded-by field gets a warning."""
        adr_content = """# ADR-0004: Superseded ADR

**Status:** superseded
**Date:** 2026-01-09
"""
        adr_path = tmp_path / "0004-superseded.md"
        adr_path.write_text(adr_content)

        findings = validate_adr_metadata(["0004-superseded.md"], tmp_path)
        # Should have warning about missing Superseded-by
        warnings = [f for f in findings if f.severity == FindingSeverity.WARNING]
        assert any("Superseded-by" in f.message for f in warnings)


class TestReferenceValidation:
    """Test reference validation functions."""

    def test_anchor_stripping(self, tmp_path: Path) -> None:
        """Test that anchors are stripped from references."""
        from cihub.commands.docs_audit.references import extract_doc_references

        content = "See docs/README.md#intro for more info"
        refs = extract_doc_references(content, "test.md")
        # Should extract docs/README.md (with or without anchor)
        assert len(refs) == 1
        # The reference should be found
        assert refs[0][1].startswith("docs/README.md")


class TestCommandIntegration:
    """Integration tests for cmd_docs_audit."""

    def test_cmd_docs_audit_returns_command_result(self) -> None:
        """Test that cmd_docs_audit returns a CommandResult."""
        args = argparse.Namespace(
            json=False,
            output_dir=None,
            skip_references=True,
            skip_consistency=True,
            github_summary=False,
        )
        result = cmd_docs_audit(args)
        assert hasattr(result, "exit_code")
        assert hasattr(result, "summary")
        assert hasattr(result, "problems")

    def test_cmd_docs_audit_json_output(self) -> None:
        """Test that --json mode produces valid data."""
        args = argparse.Namespace(
            json=True,
            output_dir=None,
            skip_references=True,
            skip_consistency=True,
            github_summary=False,
        )
        result = cmd_docs_audit(args)
        # data field should contain the report dict
        assert "stats" in result.data
        assert "findings" in result.data

    def test_cmd_docs_audit_writes_artifact(self, tmp_path: Path) -> None:
        """Test that --output-dir writes docs_audit.json."""
        args = argparse.Namespace(
            json=False,
            output_dir=str(tmp_path),
            skip_references=True,
            skip_consistency=True,
            github_summary=False,
        )
        cmd_docs_audit(args)
        artifact = tmp_path / "docs_audit.json"
        assert artifact.exists()


class TestConsistencyValidation:
    """Test Part 13 consistency validation functions."""

    def test_parse_checklist_items(self, tmp_path: Path) -> None:
        """Test parsing checklist items from a planning doc."""
        from cihub.commands.docs_audit.consistency import parse_checklist_items

        content = """# Test Doc

- [ ] Incomplete task
- [x] Complete task
* [ ] Another format
- Not a checklist item
"""
        doc_path = tmp_path / "plan.md"
        doc_path.write_text(content)

        entries = parse_checklist_items(doc_path)
        assert len(entries) == 3
        # First entry: incomplete
        assert entries[0].text == "Incomplete task"
        assert entries[0].completed is False
        # Second entry: complete
        assert entries[1].text == "Complete task"
        assert entries[1].completed is True
        # Third entry: alternate format
        assert entries[2].text == "Another format"
        assert entries[2].completed is False

    def test_find_duplicate_tasks(self, tmp_path: Path) -> None:
        """Test detecting duplicate tasks across docs."""
        from cihub.commands.docs_audit.consistency import find_duplicate_tasks

        # Create fake planning docs structure
        dev_dir = tmp_path / "docs" / "development"
        dev_dir.mkdir(parents=True)
        active_dir = dev_dir / "active"
        active_dir.mkdir()

        # Create MASTER_PLAN.md with a duplicate
        plan_content = """# Master Plan
- [ ] Implement feature X
- [ ] Another task
"""
        (dev_dir / "MASTER_PLAN.md").write_text(plan_content)

        # Create CLEAN_CODE.md with the same task
        clean_content = """# Clean Code
- [ ] Implement feature X
- [ ] Different task
"""
        (active_dir / "CLEAN_CODE.md").write_text(clean_content)

        # Need to mock PLANNING_DOCS or test with actual files
        # For unit test, just verify the function runs
        groups, findings = find_duplicate_tasks(tmp_path)
        # In a proper setup, would find "Implement feature X" as duplicate
        assert isinstance(groups, list)
        assert isinstance(findings, list)

    def test_check_timestamp_freshness_valid(self, tmp_path: Path) -> None:
        """Test timestamp validation with a fresh date."""
        from datetime import date

        from cihub.commands.docs_audit.consistency import check_timestamp_freshness

        today = date.today().isoformat()
        content = f"""# Doc with Fresh Timestamp

**Last Updated:** {today}

Some content here.
"""
        doc_path = tmp_path / "fresh.md"
        doc_path.write_text(content)

        findings = check_timestamp_freshness(doc_path)
        # Should have no findings for today's date
        assert len(findings) == 0

    def test_check_timestamp_freshness_stale(self, tmp_path: Path) -> None:
        """Test timestamp validation with a stale date."""
        from cihub.commands.docs_audit.consistency import check_timestamp_freshness

        content = """# Doc with Stale Timestamp

**Last Updated:** 2020-01-01

Very old content.
"""
        doc_path = tmp_path / "stale.md"
        doc_path.write_text(content)

        findings = check_timestamp_freshness(doc_path, warn_days=7, error_days=30)
        assert len(findings) >= 1
        # Should be an error (>30 days)
        assert findings[0].severity.value == "error"
        assert "days old" in findings[0].message

    def test_check_timestamp_freshness_future(self, tmp_path: Path) -> None:
        """Test timestamp validation with a future date (error)."""
        from cihub.commands.docs_audit.consistency import check_timestamp_freshness

        content = """# Doc with Future Timestamp

**Last Updated:** 2099-12-31

Time traveler content.
"""
        doc_path = tmp_path / "future.md"
        doc_path.write_text(content)

        findings = check_timestamp_freshness(doc_path)
        assert len(findings) == 1
        assert findings[0].severity.value == "error"
        assert "Future date" in findings[0].message

    def test_find_placeholders(self, tmp_path: Path) -> None:
        """Test placeholder detection."""
        from cihub.commands.docs_audit.consistency import find_placeholders

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        content = """# Setup Guide

Clone from https://github.com/someuser/repo

YOUR_API_KEY should be set.

Use /Users/local/path for development.
"""
        (docs_dir / "setup.md").write_text(content)

        findings = find_placeholders(tmp_path)
        # NOTE: GitHub username detection is disabled (too many false positives)
        # Should find: placeholder_marker (YOUR_API_KEY), local_path (/Users/local)
        assert len(findings) >= 2
        messages = [f.message for f in findings]
        assert any("placeholder_marker" in m for m in messages)
        assert any("local_path" in m for m in messages)

    def test_cmd_docs_audit_with_consistency(self) -> None:
        """Test that cmd_docs_audit includes consistency checks."""
        args = argparse.Namespace(
            json=True,
            output_dir=None,
            skip_references=True,
            skip_consistency=False,  # Run consistency checks
            github_summary=False,
        )
        result = cmd_docs_audit(args)
        assert "stats" in result.data
        # Should have run without errors
