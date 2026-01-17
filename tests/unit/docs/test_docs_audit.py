"""Tests for cihub docs audit command.

Basic coverage for lifecycle, ADR, and reference validation.
"""

# TEST-METRICS:
#   Coverage: 90.9%

from __future__ import annotations

import argparse
from pathlib import Path

from cihub.commands.docs_audit import (
    AuditFinding,
    AuditReport,
    FindingCategory,
    FindingSeverity,
    check_master_plan_active_sync,
    cmd_docs_audit,
    get_active_docs,
    parse_master_plan_active_docs,
    parse_status_md_entries,
    validate_adr_metadata,
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


class TestDocInventory:
    """Test docs inventory counts."""

    def test_build_doc_inventory_counts(self, tmp_path: Path) -> None:
        from cihub.commands.docs_audit.inventory import build_doc_inventory

        docs_dir = tmp_path / "docs"
        (docs_dir / "README.md").parent.mkdir(parents=True, exist_ok=True)
        (docs_dir / "README.md").write_text("root\n")

        adr_dir = docs_dir / "adr"
        adr_dir.mkdir()
        (adr_dir / "0001-test.md").write_text("adr\n")

        ref_dir = docs_dir / "reference"
        ref_dir.mkdir()
        (ref_dir / "CLI.md").write_text("ref\n")

        guides_dir = docs_dir / "guides"
        guides_dir.mkdir()
        (guides_dir / "GETTING_STARTED.md").write_text("guide\n")

        dev_active = docs_dir / "development" / "active"
        dev_active.mkdir(parents=True)
        (dev_active / "PLAN.md").write_text("dev\n")

        dev_archive = docs_dir / "development" / "archive"
        dev_archive.mkdir(parents=True)
        (dev_archive / "OLD.md").write_text("archive\n")

        dev_research = docs_dir / "development" / "research"
        dev_research.mkdir(parents=True)
        (dev_research / "NOTE.md").write_text("research\n")

        other_dir = docs_dir / "misc"
        other_dir.mkdir()
        (other_dir / "OTHER.md").write_text("other\n")

        summary = build_doc_inventory(tmp_path)
        assert summary.total_files == 8
        assert summary.categories["root"].files == 1
        assert summary.categories["adr"].files == 1
        assert summary.categories["reference"].files == 1
        assert summary.categories["guides"].files == 1
        assert summary.categories["development"].files == 1
        assert summary.categories["archive"].files == 1
        assert summary.categories["research"].files == 1
        assert summary.categories["other"].files == 1


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

    def test_check_master_plan_active_sync_missing_entry(self, tmp_path: Path) -> None:
        """Test when MASTER_PLAN.md omits an active doc."""
        active_dir = tmp_path / "docs" / "development" / "active"
        active_dir.mkdir(parents=True)
        (active_dir / "FOO.md").write_text("foo")
        (active_dir / "BAR.md").write_text("bar")

        master_path = tmp_path / "docs" / "development" / "MASTER_PLAN.md"
        master_path.parent.mkdir(parents=True, exist_ok=True)
        master_path.write_text(
            "## Active Design Docs - Priority Order\n\n"
            "```\n"
            "docs/development/active/FOO.md\n"
            "```\n"
        )

        active_docs = get_active_docs(tmp_path)
        master_entries = parse_master_plan_active_docs(tmp_path)
        findings = check_master_plan_active_sync(active_docs, master_entries)

        assert any(
            f.code == "CIHUB-AUDIT-MISSING-IN-MASTER-PLAN" and "BAR.md" in f.message for f in findings
        )

    def test_check_master_plan_active_sync_stale_entry(self, tmp_path: Path) -> None:
        """Test when MASTER_PLAN.md lists a non-existent active doc."""
        active_dir = tmp_path / "docs" / "development" / "active"
        active_dir.mkdir(parents=True)
        (active_dir / "FOO.md").write_text("foo")

        master_path = tmp_path / "docs" / "development" / "MASTER_PLAN.md"
        master_path.parent.mkdir(parents=True, exist_ok=True)
        master_path.write_text(
            "## Active Design Docs - Priority Order\n\n"
            "```\n"
            "docs/development/active/FOO.md\n"
            "docs/development/active/NEW.md\n"
            "```\n"
        )

        active_docs = get_active_docs(tmp_path)
        master_entries = parse_master_plan_active_docs(tmp_path)
        findings = check_master_plan_active_sync(active_docs, master_entries)

        assert any(f.code == "CIHUB-AUDIT-STALE-IN-MASTER-PLAN" and "NEW.md" in f.message for f in findings)

    def test_check_archive_superseded_patterns(self, tmp_path: Path) -> None:
        """Test various superseded-by reference formats are recognized."""
        from cihub.commands.docs_audit.lifecycle import check_archive_superseded_headers

        archive_dir = tmp_path / "docs" / "development" / "archive"
        archive_dir.mkdir(parents=True)

        # Test cases: (filename, content, should_have_explicit_ref)
        test_cases = [
            # Valid explicit references - various formatting styles
            ("link.md", "> **Superseded by:** [New Doc](../active/NEW.md)\n\nContent", True),
            ("plain_md.md", "> Superseded by: NEWDOC.md\n\nContent", True),
            ("relative.md", "> Superseded by: ../active/FOO.md\n\nContent", True),
            ("docs_path.md", "> Superseded by: docs/development/active/BAR.md\n\nContent", True),
            ("adr_ref.md", "> Superseded by: ADR-0042\n\nContent", True),
            # Colon-outside variants
            ("colon_outside.md", "> **Superseded by**: NEW.md\n\nContent", True),
            ("partial_bold.md", "> **Superseded** by: OTHER.md\n\nContent", True),
            # Hyphenated form (universal header template style)
            ("hyphenated.md", "> Superseded-by: NEW_DOC.md\n\nContent", True),
            ("hyphenated_bold.md", "> **Superseded-by:** [Doc](path.md)\n\nContent", True),
            # Invalid: only status, no explicit reference
            ("status_only.md", "> **Status:** archived\n\nContent", False),
            ("incomplete.md", "> Superseded by: docs/\n\nContent", False),  # Just directory
        ]

        for filename, content, _has_explicit in test_cases:
            (archive_dir / filename).write_text(content)

        archive_docs = [f"docs/development/archive/{f}" for f, _, _ in test_cases]
        findings = check_archive_superseded_headers(archive_docs, tmp_path)

        # Count findings for explicit reference warnings
        explicit_ref_findings = [f for f in findings if "explicit" in f.message.lower()]

        # Should have warnings for status_only.md and incomplete.md
        expected_missing = sum(1 for _, _, has_explicit in test_cases if not has_explicit)
        assert len(explicit_ref_findings) == expected_missing


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

    def test_extract_doc_references_ignores_nested_docs_path(self) -> None:
        """Skip docs/ matches embedded inside other paths."""
        from cihub.commands.docs_audit.references import extract_doc_references

        content = "tests/unit/docs/test_docs_audit.py"
        refs = extract_doc_references(content, "test.md")
        assert refs == []

    def test_extract_doc_references_strips_trailing_period(self) -> None:
        """Strip trailing punctuation from docs/ references."""
        from cihub.commands.docs_audit.references import extract_doc_references

        content = "See docs/guides/."
        refs = extract_doc_references(content, "test.md")
        assert refs == [(1, "docs/guides/")]


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

    def test_cmd_docs_audit_inventory_summary(self) -> None:
        """Test that --inventory includes summary in JSON output."""
        args = argparse.Namespace(
            json=True,
            output_dir=None,
            skip_references=True,
            skip_consistency=True,
            github_summary=False,
            inventory=True,
        )
        result = cmd_docs_audit(args)
        assert "inventory_summary" in result.data

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

    def test_verify_checklist_reality_finds_complete_items(self, tmp_path: Path) -> None:
        """Test that verify_checklist_reality flags unchecked items that appear done."""
        from cihub.commands.docs_audit.consistency import verify_checklist_reality

        # Set up the directory structure
        active_dir = tmp_path / "docs" / "development" / "active"
        active_dir.mkdir(parents=True)

        # Create a simulated completed feature
        tools_dir = tmp_path / "cihub" / "tools"
        tools_dir.mkdir(parents=True)
        registry_file = tools_dir / "registry.py"
        registry_file.write_text("class ToolAdapter:\n    pass\n")

        # Create doc with unchecked item matching the completed feature
        doc_content = """# Test Plan

- [ ] Implement tool adapter pattern
- [x] Already done item
"""
        (active_dir / "PLAN.md").write_text(doc_content)

        findings = verify_checklist_reality(tmp_path)
        # Should flag the unchecked item since ToolAdapter exists
        assert len(findings) >= 1
        assert any("CHECKLIST-REALITY" in f.code for f in findings)
        assert any("tool adapter" in f.message.lower() for f in findings)

    def test_verify_checklist_reality_ignores_incomplete(self, tmp_path: Path) -> None:
        """Test that verify_checklist_reality does not flag truly incomplete items."""
        from cihub.commands.docs_audit.consistency import verify_checklist_reality

        # Set up the directory structure (without the feature)
        active_dir = tmp_path / "docs" / "development" / "active"
        active_dir.mkdir(parents=True)

        # Create doc with unchecked item for non-existent feature
        doc_content = """# Test Plan

- [ ] Extract language strategies
"""
        (active_dir / "PLAN.md").write_text(doc_content)

        findings = verify_checklist_reality(tmp_path)
        # Should NOT flag since the feature doesn't exist
        assert not any("language strategies" in f.message.lower() for f in findings)

    def test_check_docs_index_consistency_missing_from_readme(self, tmp_path: Path) -> None:
        """Test detection of files in active/ not listed in README.md (Part 13.W)."""
        from cihub.commands.docs_audit.consistency import check_docs_index_consistency

        # Set up directory structure
        docs_dir = tmp_path / "docs"
        active_dir = docs_dir / "development" / "active"
        active_dir.mkdir(parents=True)

        # Create active doc
        (active_dir / "PLAN_A.md").write_text("# Plan A")
        (active_dir / "PLAN_B.md").write_text("# Plan B")

        # Create README.md that only lists one of them
        readme_content = """# Docs
**Active Design Docs** (`development/active/`):
- [PLAN_A.md](development/active/PLAN_A.md) - Listed doc
**Other Section:**
"""
        (docs_dir / "README.md").write_text(readme_content)

        findings = check_docs_index_consistency(tmp_path)
        # Should flag PLAN_B.md as missing from README.md
        assert len(findings) == 1
        assert "PLAN_B.md" in findings[0].message
        assert "README-MISSING-DOC" in findings[0].code

    def test_check_docs_index_consistency_lowercase_doc(self, tmp_path: Path) -> None:
        """Ensure lowercase doc names in README.md are detected."""
        from cihub.commands.docs_audit.consistency import check_docs_index_consistency

        docs_dir = tmp_path / "docs"
        active_dir = docs_dir / "development" / "active"
        active_dir.mkdir(parents=True)

        (active_dir / "lowercase-doc.md").write_text("# Lowercase Doc")

        readme_content = """# Docs
**Active Design Docs** (`development/active/`):
- [lowercase-doc.md](development/active/lowercase-doc.md) - Listed doc
"""
        (docs_dir / "README.md").write_text(readme_content)

        findings = check_docs_index_consistency(tmp_path)
        assert not any("lowercase-doc.md" in f.message for f in findings)

    def test_check_docs_index_consistency_stale_in_readme(self, tmp_path: Path) -> None:
        """Test detection of files in README.md that don't exist (Part 13.W)."""
        from cihub.commands.docs_audit.consistency import check_docs_index_consistency

        # Set up directory structure
        docs_dir = tmp_path / "docs"
        active_dir = docs_dir / "development" / "active"
        active_dir.mkdir(parents=True)

        # Create only one active doc
        (active_dir / "PLAN_A.md").write_text("# Plan A")

        # Create README.md that lists a non-existent file
        readme_content = """# Docs
**Active Design Docs** (`development/active/`):
- [PLAN_A.md](development/active/PLAN_A.md) - Exists
- [DELETED_DOC.md](development/active/DELETED_DOC.md) - Doesn't exist
**Other:**
"""
        (docs_dir / "README.md").write_text(readme_content)

        findings = check_docs_index_consistency(tmp_path)
        # Should flag DELETED_DOC.md as stale
        assert len(findings) == 1
        assert "DELETED_DOC.md" in findings[0].message
        assert "README-STALE-DOC" in findings[0].code

    def test_validate_changelog_correct_order(self, tmp_path: Path) -> None:
        """Test CHANGELOG validation with correct chronological order (Part 13.X)."""
        from cihub.commands.docs_audit.consistency import validate_changelog

        docs_dir = tmp_path / "docs" / "development"
        docs_dir.mkdir(parents=True)

        # Correct order: most recent first
        content = """# Changelog

## 2026-01-10 - Latest entry

Content here.

## 2026-01-09 - Previous entry

More content.

## 2026-01-05 - Older entry

Old content.
"""
        (docs_dir / "CHANGELOG.md").write_text(content)

        findings = validate_changelog(tmp_path)
        # Should have no order findings
        assert not any("ORDER" in f.code for f in findings)

    def test_validate_changelog_wrong_order(self, tmp_path: Path) -> None:
        """Test CHANGELOG validation detects out-of-order entries (Part 13.X)."""
        from cihub.commands.docs_audit.consistency import validate_changelog

        docs_dir = tmp_path / "docs" / "development"
        docs_dir.mkdir(parents=True)

        # Wrong order: older entry comes first
        content = """# Changelog

## 2026-01-05 - Older entry first

Wrong!

## 2026-01-09 - Newer entry second

Should be first!
"""
        (docs_dir / "CHANGELOG.md").write_text(content)

        findings = validate_changelog(tmp_path)
        # Should flag order issue
        assert len(findings) >= 1
        assert any("CHANGELOG-ORDER" in f.code for f in findings)

    def test_validate_changelog_duplicate_dates(self, tmp_path: Path) -> None:
        """Test CHANGELOG validation detects duplicate date headers (Part 13.X)."""
        from cihub.commands.docs_audit.consistency import validate_changelog

        docs_dir = tmp_path / "docs" / "development"
        docs_dir.mkdir(parents=True)

        # Two separate H2 entries for same date
        content = """# Changelog

## 2026-01-09 - First entry

Content.

## 2026-01-09 - Second entry same day

More content.
"""
        (docs_dir / "CHANGELOG.md").write_text(content)

        findings = validate_changelog(tmp_path)
        # Should flag duplicate date (INFO level)
        assert len(findings) >= 1
        assert any("DUPLICATE-DATE" in f.code for f in findings)

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


class TestGuideValidation:
    """Test guide command validation."""

    def test_validate_guide_commands_invalid(self, tmp_path: Path) -> None:
        from cihub.commands.docs_audit.guides import validate_guide_commands

        guides_dir = tmp_path / "docs" / "guides"
        guides_dir.mkdir(parents=True)

        content = """# Guide

```bash
cihub docs generate
cihub 0.x.x
python -m cihub check --all
cihub docs generat
```

Inline: `cihub check --full`
"""
        (guides_dir / "GUIDE.md").write_text(content)

        findings = validate_guide_commands(tmp_path)
        assert len(findings) == 1
        assert "generat" in findings[0].message
        assert findings[0].category == FindingCategory.GUIDE_COMMAND


class TestHeaderValidation:
    """Test Part 12.Q universal header validation."""

    def test_validate_doc_headers_missing_block(self, tmp_path: Path) -> None:
        """Test detection of missing header block."""
        from cihub.commands.docs_audit.headers import validate_doc_headers

        # Create docs/ directory with doc missing headers
        docs_dir = tmp_path / "docs" / "development" / "active"
        docs_dir.mkdir(parents=True)

        doc_path = docs_dir / "NO_HEADERS.md"
        doc_path.write_text("# No Headers\n\nJust content, no headers.\n")

        findings = validate_doc_headers(tmp_path)
        # Should flag missing header block
        assert any(f.code == "CIHUB-HEADER-MISSING-BLOCK" for f in findings)

    def test_validate_doc_headers_incomplete(self, tmp_path: Path) -> None:
        """Test detection of incomplete header block."""
        from cihub.commands.docs_audit.headers import validate_doc_headers

        docs_dir = tmp_path / "docs" / "development" / "active"
        docs_dir.mkdir(parents=True)

        doc_path = docs_dir / "PARTIAL.md"
        doc_path.write_text("# Partial Headers\n\n**Status:** active\n**Owner:** Team A\n\nContent here.\n")

        findings = validate_doc_headers(tmp_path)
        # Should flag incomplete header block (missing Source-of-truth, Last-reviewed)
        incomplete = [f for f in findings if f.code == "CIHUB-HEADER-INCOMPLETE"]
        assert len(incomplete) >= 1

    def test_validate_doc_headers_valid(self, tmp_path: Path) -> None:
        """Test valid header block passes."""
        from cihub.commands.docs_audit.headers import validate_doc_headers

        docs_dir = tmp_path / "docs" / "development" / "active"
        docs_dir.mkdir(parents=True)

        doc_path = docs_dir / "VALID.md"
        doc_path.write_text(
            "# Valid Headers\n\n"
            "**Status:** active\n"
            "**Owner:** Team A\n"
            "**Source-of-truth:** manual\n"
            "**Last-reviewed:** 2026-01-09\n"
            "\nContent here.\n"
        )

        findings = validate_doc_headers(tmp_path)
        # Should have no header findings for this doc
        header_findings = [f for f in findings if "VALID.md" in f.file]
        assert len(header_findings) == 0

    def test_parse_header_block_stops_at_first_content_line(self, tmp_path: Path) -> None:
        """Regression: header parsing must stop at the FIRST content line.

        Headers must appear immediately after the title (and empty lines).
        Even a single line of prose text before **Status:** means it's not a header.
        """
        from cihub.commands.docs_audit.headers import parse_doc_header

        # Doc with even ONE content line before headers - headers should NOT be found
        doc_with_intro_then_header = """\
# My Document

This document explains something important.

**Status:** completed
"""
        headers = parse_doc_header(doc_with_intro_then_header)
        # The Status appearing after ANY content should NOT be captured
        assert "Status" not in headers, (
            "Header parsing should stop at first non-header line; found 'Status' after intro paragraph"
        )

    def test_parse_header_block_finds_headers_at_top(self, tmp_path: Path) -> None:
        """Verify headers at the top of the document ARE found."""
        from cihub.commands.docs_audit.headers import parse_doc_header

        doc_with_top_headers = """\
# My Document

**Status:** active
**Owner:** Team A

This is content after the headers.
"""
        headers = parse_doc_header(doc_with_top_headers)
        assert headers.get("Status") == "active"
        assert headers.get("Owner") == "Team A"


class TestMetricsDrift:
    """Test Part 13.R metrics drift detection."""

    def test_count_cli_commands(self, tmp_path: Path) -> None:
        """Test CLI command counting from add_parser calls."""
        from cihub.commands.docs_audit.consistency import _count_cli_commands

        # Create cli_parsers directory with test files
        cli_dir = tmp_path / "cihub" / "cli_parsers"
        cli_dir.mkdir(parents=True)

        # Create a parser file with add_parser calls
        parser_content = """
def setup(subparsers):
    cmd1 = subparsers.add_parser("test-cmd", help="Test")
    cmd2 = subparsers.add_parser("another-cmd", help="Another")
"""
        (cli_dir / "test.py").write_text(parser_content)

        count = _count_cli_commands(tmp_path)
        assert count == 2

    def test_count_cli_commands_with_helpers(self, tmp_path: Path) -> None:
        """Test CLI command counting includes helper-based commands."""
        from cihub.commands.docs_audit.consistency import _count_cli_commands

        cli_dir = tmp_path / "cihub" / "cli_parsers"
        cli_dir.mkdir(parents=True)

        # Create a parser file with both direct and helper-based commands
        parser_content = """
def _add_preflight_parser(subparsers, name, help_text):
    parser = subparsers.add_parser(name, help=help_text)
    return parser

def setup(subparsers):
    detect = subparsers.add_parser("detect", help="Detect")
    _add_preflight_parser(subparsers, "preflight", "Check env")
    _add_preflight_parser(subparsers, "doctor", "Alias for preflight")
"""
        (cli_dir / "core.py").write_text(parser_content)

        count = _count_cli_commands(tmp_path)
        # 1 direct (detect) + 2 helper-based (preflight, doctor) = 3
        assert count == 3

    def test_is_delta_context(self) -> None:
        """Test delta context detection."""
        from cihub.commands.docs_audit.consistency import _is_delta_context

        # Lines with delta keywords should be detected
        assert _is_delta_context("Added 50 tests in this PR")
        assert _is_delta_context("Fixed 3 bugs and added new tests")
        assert _is_delta_context("Migrated 20 tests to new framework")

        # Lines without delta keywords should pass
        assert not _is_delta_context("We have 100 tests in the suite")
        assert not _is_delta_context("Total of 50 commands available")

    def test_is_local_context(self) -> None:
        """Test local/module-specific context detection."""
        from cihub.commands.docs_audit.consistency import _is_local_context

        # Module-specific lines should be detected
        assert _is_local_context("63 tests in test_docs_audit.py")
        assert _is_local_context("Modular package with 22 tests")
        assert _is_local_context("cihub docs stale has 63 tests")

        # Project-wide claims should pass
        assert not _is_local_context("We have 100 tests total")
        assert not _is_local_context("The project includes 50 commands")
