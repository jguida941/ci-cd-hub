"""Tests for docs_stale integration and property-based tests.

Split from test_docs_stale.py for better organization.
Tests: Git operations, command integration, Hypothesis property tests
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from cihub.commands.docs_stale import (
    KIND_BACKTICK,
    REASON_DELETED_FILE,
    REASON_REMOVED,
    REASON_RENAMED,
    DocReference,
    StaleReference,
    StaleReport,
    extract_python_symbols,
    find_stale_references,
    format_json_output,
)


class TestGitOperations:
    """Tests for git operations using mocks."""

    def test_is_git_repo_returns_false_for_non_repo(self, tmp_path: Path) -> None:
        from cihub.commands.docs_stale import is_git_repo

        assert not is_git_repo(tmp_path)

    def test_resolve_git_ref_returns_none_for_invalid(self, tmp_path: Path) -> None:
        from cihub.commands.docs_stale import resolve_git_ref

        # In a non-git directory, any ref is invalid
        assert resolve_git_ref("HEAD", tmp_path) is None


class TestCommandIntegration:
    """Integration tests for the command handler."""

    def test_returns_exit_usage_for_non_git_repo(self, tmp_path: Path) -> None:
        """Non-git repos should return EXIT_USAGE."""
        from cihub.commands.docs_stale import cmd_docs_stale
        from cihub.exit_codes import EXIT_USAGE

        # Create a non-git directory
        (tmp_path / "cihub").mkdir()
        (tmp_path / "docs").mkdir()

        args = argparse.Namespace(
            since="HEAD~5",
            all=False,
            include_generated=False,
            fail_on_stale=False,
            skip_fences=False,
            ai=False,
            json=False,
            code="cihub",
            docs="docs",
            output_dir=None,
            tool_output=None,
            ai_output=None,
            github_summary=False,
        )

        with patch("cihub.commands.docs_stale.project_root", return_value=tmp_path):
            result = cmd_docs_stale(args)

        assert result.exit_code == EXIT_USAGE
        assert "git" in result.summary.lower()


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================


class TestPropertyBasedExtraction:
    """Property-based tests for extraction logic using Hypothesis."""

    @staticmethod
    def _valid_python_identifier(s: str) -> bool:
        """Check if string is a valid Python identifier."""
        import keyword

        return s.isidentifier() and not keyword.iskeyword(s)

    def test_extracted_symbols_have_valid_names(self) -> None:
        """Property: All extracted symbols must have non-empty names."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        # Strategy: generate valid Python function definitions
        valid_names = st.from_regex(r"[a-z][a-z0-9_]{2,20}", fullmatch=True)

        @given(name=valid_names)
        @settings(max_examples=50)
        def check_function_extraction(name: str) -> None:
            code = f"def {name}(): pass"
            symbols = extract_python_symbols(code, "test.py")
            assert len(symbols) == 1
            assert symbols[0].name == name
            assert len(symbols[0].name) > 0
            assert symbols[0].kind == "function"

        check_function_extraction()

    def test_extracted_symbols_have_positive_line_numbers(self) -> None:
        """Property: All extracted symbols have positive line numbers."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        # Strategy: generate code with variable number of leading blank lines
        @given(leading_lines=st.integers(min_value=0, max_value=10))
        @settings(max_examples=20)
        def check_line_numbers(leading_lines: int) -> None:
            code = "\n" * leading_lines + "def test_func(): pass"
            symbols = extract_python_symbols(code, "test.py")
            for symbol in symbols:
                assert symbol.line > 0
                assert symbol.line == leading_lines + 1

        check_line_numbers()

    def test_class_symbols_are_extracted_correctly(self) -> None:
        """Property: Classes with PascalCase names are extracted."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        # Strategy: generate PascalCase class names
        pascal_names = st.from_regex(r"[A-Z][a-zA-Z]{2,15}", fullmatch=True)

        @given(name=pascal_names)
        @settings(max_examples=30)
        def check_class_extraction(name: str) -> None:
            code = f"class {name}: pass"
            symbols = extract_python_symbols(code, "test.py")
            assert len(symbols) == 1
            assert symbols[0].name == name
            assert symbols[0].kind == "class"

        check_class_extraction()

    def test_constants_are_uppercase(self) -> None:
        """Property: Constants (UPPER_CASE) are extracted as constants."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        # Strategy: generate UPPER_CASE constant names
        const_names = st.from_regex(r"[A-Z][A-Z0-9_]{2,15}", fullmatch=True)

        @given(name=const_names)
        @settings(max_examples=30)
        def check_constant_extraction(name: str) -> None:
            code = f"{name} = 42"
            symbols = extract_python_symbols(code, "test.py")
            assert len(symbols) == 1
            assert symbols[0].name == name
            assert symbols[0].kind == "constant"

        check_constant_extraction()


class TestPropertyBasedStaleDetection:
    """Property-based tests for stale reference detection."""

    def test_removed_symbols_always_detected(self) -> None:
        """Property: If a symbol is removed, references to it are stale."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        symbol_names = st.from_regex(r"[a-z][a-z0-9_]{3,15}", fullmatch=True)

        @given(symbol=symbol_names)
        @settings(max_examples=30)
        def check_removal_detection(symbol: str) -> None:
            refs = [
                DocReference(
                    reference=symbol,
                    kind=KIND_BACKTICK,
                    file="test.md",
                    line=10,
                    context=f"Use `{symbol}`",
                )
            ]
            stale = find_stale_references(
                refs,
                removed_symbols={symbol},
                renamed_symbols=[],
                deleted_files=[],
                renamed_files=[],
            )
            assert len(stale) == 1
            assert stale[0].reference == symbol
            assert stale[0].reason == REASON_REMOVED

        check_removal_detection()

    def test_renamed_symbols_suggest_new_name(self) -> None:
        """Property: Renamed symbols include the new name in suggestion."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        symbol_names = st.from_regex(r"[a-z][a-z0-9_]{3,15}", fullmatch=True)

        @given(old=symbol_names, new=symbol_names)
        @settings(max_examples=30)
        def check_rename_suggestion(old: str, new: str) -> None:
            if old == new:
                return  # Skip if names are identical

            refs = [
                DocReference(
                    reference=old,
                    kind=KIND_BACKTICK,
                    file="test.md",
                    line=5,
                    context=f"Use `{old}`",
                )
            ]
            stale = find_stale_references(
                refs,
                removed_symbols=set(),
                renamed_symbols=[(old, new)],
                deleted_files=[],
                renamed_files=[],
            )
            assert len(stale) == 1
            assert stale[0].reason == REASON_RENAMED
            assert new in stale[0].suggestion

        check_rename_suggestion()

    def test_non_removed_symbols_not_flagged(self) -> None:
        """Property: Symbols not in removed set are never flagged."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        symbol_names = st.from_regex(r"[a-z][a-z0-9_]{3,15}", fullmatch=True)

        @given(ref_symbol=symbol_names, removed_symbol=symbol_names)
        @settings(max_examples=30)
        def check_not_flagged(ref_symbol: str, removed_symbol: str) -> None:
            if ref_symbol == removed_symbol:
                return  # Skip - this would be flagged correctly

            refs = [
                DocReference(
                    reference=ref_symbol,
                    kind=KIND_BACKTICK,
                    file="test.md",
                    line=1,
                    context=f"Use `{ref_symbol}`",
                )
            ]
            stale = find_stale_references(
                refs,
                removed_symbols={removed_symbol},
                renamed_symbols=[],
                deleted_files=[],
                renamed_files=[],
            )
            assert len(stale) == 0

        check_not_flagged()


class TestPropertyBasedSerialization:
    """Property-based tests for JSON serialization."""

    def test_report_always_json_serializable(self) -> None:
        """Property: StaleReport.to_dict() is always JSON-serializable."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        # Strategy: generate lists of symbol names
        symbol_list = st.lists(
            st.from_regex(r"[a-z][a-z0-9_]{2,10}", fullmatch=True),
            max_size=5,
        )
        rename_pair = st.tuples(
            st.from_regex(r"[a-z][a-z0-9_]{2,10}", fullmatch=True),
            st.from_regex(r"[a-z][a-z0-9_]{2,10}", fullmatch=True),
        )
        rename_list = st.lists(rename_pair, max_size=3)

        @given(removed=symbol_list, added=symbol_list, renamed=rename_list)
        @settings(max_examples=30)
        def check_serialization(removed: list[str], added: list[str], renamed: list[tuple[str, str]]) -> None:
            report = StaleReport(
                git_range="HEAD~5",
                removed_symbols=removed,
                added_symbols=added,
                renamed_symbols=renamed,
            )
            result = format_json_output(report)
            # Should not raise
            serialized = json.dumps(result)
            # Should be valid JSON
            parsed = json.loads(serialized)
            assert parsed["git_range"] == "HEAD~5"

        check_serialization()

    def test_stale_references_serialize_correctly(self) -> None:
        """Property: StaleReference data survives JSON round-trip."""
        from hypothesis import given, settings
        from hypothesis import strategies as st

        reasons = st.sampled_from([REASON_REMOVED, REASON_RENAMED, REASON_DELETED_FILE])
        line_nums = st.integers(min_value=1, max_value=1000)

        @given(reason=reasons, line=line_nums)
        @settings(max_examples=20)
        def check_reference_serialization(reason: str, line: int) -> None:
            ref = StaleReference(
                doc_file="test.md",
                doc_line=line,
                reference="some_symbol",
                reason=reason,
                suggestion="Fix it",
                context="Use `some_symbol`",
            )
            report = StaleReport(git_range="HEAD~5", stale_references=[ref])
            result = format_json_output(report)
            serialized = json.dumps(result)
            parsed = json.loads(serialized)
            assert len(parsed["stale_references"]) == 1
            assert parsed["stale_references"][0]["doc_line"] == line
            assert parsed["stale_references"][0]["reason"] == reason

        check_reference_serialization()
