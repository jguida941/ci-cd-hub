"""Tests for docs_stale detection logic and output formatters.

Split from test_docs_stale.py for better organization.
Tests: find_stale_references, group_stale_by_file, output formatters
"""

# TEST-METRICS:

from __future__ import annotations

import json

from cihub.commands.docs_stale import (
    KIND_BACKTICK,
    KIND_FILE_PATH,
    REASON_DELETED_FILE,
    REASON_REMOVED,
    REASON_RENAMED,
    DocReference,
    StaleReference,
    StaleReport,
    extract_doc_references,
    find_stale_references,
    format_ai_output,
    format_github_summary,
    format_human_output,
    format_json_output,
    group_stale_by_file,
)


class TestFindStaleReferences:
    """Tests for stale reference detection."""

    def test_detects_removed_symbol(self) -> None:
        refs = [
            DocReference(
                reference="old_func",
                kind=KIND_BACKTICK,
                file="test.md",
                line=10,
                context="Use `old_func`",
            )
        ]
        stale = find_stale_references(
            refs,
            removed_symbols={"old_func"},
            renamed_symbols=[],
            deleted_files=[],
            renamed_files=[],
        )
        assert len(stale) == 1
        assert stale[0].reason == REASON_REMOVED

    def test_detects_renamed_symbol(self) -> None:
        refs = [
            DocReference(
                reference="old_name",
                kind=KIND_BACKTICK,
                file="test.md",
                line=10,
                context="Use `old_name`",
            )
        ]
        stale = find_stale_references(
            refs,
            removed_symbols=set(),
            renamed_symbols=[("old_name", "new_name")],
            deleted_files=[],
            renamed_files=[],
        )
        assert len(stale) == 1
        assert stale[0].reason == REASON_RENAMED
        assert "new_name" in stale[0].suggestion

    def test_detects_deleted_file_reference(self) -> None:
        refs = [
            DocReference(
                reference="cihub/old_file.py",
                kind=KIND_FILE_PATH,
                file="test.md",
                line=10,
                context="Edit `cihub/old_file.py`",
            )
        ]
        stale = find_stale_references(
            refs,
            removed_symbols=set(),
            renamed_symbols=[],
            deleted_files=["cihub/old_file.py"],
            renamed_files=[],
        )
        assert len(stale) == 1
        assert stale[0].reason == REASON_DELETED_FILE

    def test_ignores_unchanged_symbols(self) -> None:
        refs = [
            DocReference(
                reference="stable_func",
                kind=KIND_BACKTICK,
                file="test.md",
                line=10,
                context="Use `stable_func`",
            )
        ]
        stale = find_stale_references(
            refs,
            removed_symbols={"other_func"},
            renamed_symbols=[],
            deleted_files=[],
            renamed_files=[],
        )
        assert len(stale) == 0

    def test_never_flags_added_symbols(self) -> None:
        """Critical test: Added symbols should NEVER be flagged as stale."""
        refs = [
            DocReference(
                reference="new_func",
                kind=KIND_BACKTICK,
                file="test.md",
                line=10,
                context="Use `new_func`",
            )
        ]
        # Even if new_func appears in doc refs, it's not stale if it was added
        stale = find_stale_references(
            refs,
            removed_symbols=set(),  # new_func is NOT removed
            renamed_symbols=[],
            deleted_files=[],
            renamed_files=[],
        )
        assert len(stale) == 0


class TestGroupStaleByFile:
    """Tests for grouping stale references by file."""

    def test_groups_by_file(self) -> None:
        refs = [
            StaleReference(doc_file="a.md", doc_line=1, reference="x", reason="removed", suggestion="", context=""),
            StaleReference(doc_file="b.md", doc_line=2, reference="y", reason="removed", suggestion="", context=""),
            StaleReference(doc_file="a.md", doc_line=3, reference="z", reason="removed", suggestion="", context=""),
        ]
        grouped = group_stale_by_file(refs)
        assert len(grouped["a.md"]) == 2
        assert len(grouped["b.md"]) == 1


class TestFormatHumanOutput:
    """Tests for human-readable output formatting."""

    def test_empty_report_shows_no_stale(self) -> None:
        report = StaleReport(git_range="HEAD~5")
        output = format_human_output(report)
        assert "No stale references found" in output

    def test_shows_summary_stats(self) -> None:
        report = StaleReport(
            git_range="HEAD~5",
            removed_symbols=["a", "b"],
            renamed_symbols=[("c", "d")],
        )
        output = format_human_output(report)
        assert "Removed symbols: 2" in output
        assert "Renamed symbols: 1" in output

    def test_shows_stale_references(self) -> None:
        report = StaleReport(
            git_range="HEAD~5",
            stale_references=[
                StaleReference(
                    doc_file="test.md",
                    doc_line=10,
                    reference="old_func",
                    reason="removed",
                    suggestion="Remove reference",
                    context="",
                )
            ],
        )
        output = format_human_output(report)
        assert "test.md" in output
        assert "old_func" in output
        assert "Line 10" in output


class TestFormatJsonOutput:
    """Tests for JSON output formatting."""

    def test_returns_dict(self) -> None:
        report = StaleReport(git_range="HEAD~5")
        result = format_json_output(report)
        assert isinstance(result, dict)

    def test_json_serializable(self) -> None:
        report = StaleReport(
            git_range="HEAD~5",
            renamed_symbols=[("a", "b")],
            stale_references=[
                StaleReference(
                    doc_file="test.md",
                    doc_line=10,
                    reference="x",
                    reason="removed",
                    suggestion="",
                    context="",
                )
            ],
        )
        result = format_json_output(report)
        # Should not raise
        json.dumps(result)


class TestFormatAiOutput:
    """Tests for AI prompt pack output formatting."""

    def test_includes_instructions(self) -> None:
        report = StaleReport(git_range="HEAD~5")
        output = format_ai_output(report)
        assert "DO NOT" in output
        assert "docs/reference/**" in output
        assert "docs/adr/**" in output

    def test_includes_renamed_symbols(self) -> None:
        report = StaleReport(
            git_range="HEAD~5",
            renamed_symbols=[("old", "new")],
        )
        output = format_ai_output(report)
        assert "`old` → `new`" in output

    def test_skips_generated_docs(self) -> None:
        """Per Part 12.D: AI output should skip docs/reference/."""
        report = StaleReport(
            git_range="HEAD~5",
            stale_references=[
                StaleReference(
                    doc_file="docs/reference/CLI.md",
                    doc_line=10,
                    reference="x",
                    reason="removed",
                    suggestion="",
                    context="",
                )
            ],
        )
        output = format_ai_output(report)
        # The file should not appear in the "Files Requiring Updates" section
        assert "### `docs/reference/CLI.md`" not in output


class TestFormatGithubSummary:
    """Tests for GitHub Actions summary output formatting."""

    def test_includes_git_range(self) -> None:
        report = StaleReport(git_range="HEAD~5")
        output = format_github_summary(report, "HEAD~5")
        assert "`HEAD~5`" in output

    def test_shows_stats(self) -> None:
        report = StaleReport(
            git_range="HEAD~5",
            removed_symbols=["a", "b"],
            renamed_symbols=[("c", "d")],
        )
        output = format_github_summary(report, "HEAD~5")
        assert "**2**" in output  # removed count
        assert "**1**" in output  # renamed count

    def test_truncates_at_10_items(self) -> None:
        """Should limit to first 10 stale references and show 'and N more'."""
        refs = [
            StaleReference(
                doc_file=f"doc{i}.md",
                doc_line=i,
                reference=f"ref{i}",
                reason="removed",
                suggestion="",
                context="",
            )
            for i in range(15)
        ]
        report = StaleReport(git_range="HEAD~5", stale_references=refs)
        output = format_github_summary(report, "HEAD~5")
        assert "and 5 more" in output

    def test_shows_no_stale_message(self) -> None:
        report = StaleReport(git_range="HEAD~5")
        output = format_github_summary(report, "HEAD~5")
        assert "No stale references found" in output


class TestDeduplication:
    """Tests for reference deduplication in extraction."""

    def test_deduplicates_overlapping_patterns(self) -> None:
        """A backticked CLI command should not be counted twice."""
        content = "Run `cihub docs stale` to check"
        refs = extract_doc_references(content, "test.md")
        # Should only have one reference to "cihub docs stale"
        cli_refs = [r for r in refs if "cihub docs stale" in r.reference]
        assert len(cli_refs) == 1

    def test_same_reference_different_lines_not_deduplicated(self) -> None:
        """Same reference on different lines should be kept."""
        content = "Use `my_func` here\nAnd `my_func` there too"
        refs = extract_doc_references(content, "test.md")
        my_func_refs = [r for r in refs if r.reference == "my_func"]
        assert len(my_func_refs) == 2
        assert my_func_refs[0].line == 1
        assert my_func_refs[1].line == 2
