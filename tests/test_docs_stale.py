"""Tests for cihub docs stale command.

Tests are organized by module:
- TestTypes: Data classes and constants
- TestExtraction: Symbol and reference extraction
- TestComparison: Stale detection logic
- TestOutput: Output formatters
- TestIntegration: End-to-end tests with git repos
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from cihub.commands.docs_stale import (
    DEFAULT_SINCE,
    FALSE_POSITIVE_TOKENS,
    KIND_BACKTICK,
    KIND_CLI_COMMAND,
    KIND_CLI_FLAG,
    KIND_CONFIG_KEY,
    KIND_ENV_VAR,
    KIND_FILE_PATH,
    PARSED_FENCE_TYPES,
    REASON_DELETED_FILE,
    REASON_REMOVED,
    REASON_RENAMED,
    SKIPPED_FENCE_TYPES,
    CodeSymbol,
    DocReference,
    StaleReference,
    StaleReport,
    extract_doc_references,
    extract_python_symbols,
    find_stale_references,
    format_ai_output,
    format_github_summary,
    format_human_output,
    format_json_output,
    group_stale_by_file,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Types
# =============================================================================


class TestCodeSymbol:
    """Tests for CodeSymbol dataclass."""

    def test_creates_function_symbol(self) -> None:
        symbol = CodeSymbol(name="my_func", kind="function", file="test.py", line=10)
        assert symbol.name == "my_func"
        assert symbol.kind == "function"
        assert symbol.file == "test.py"
        assert symbol.line == 10

    def test_creates_class_symbol(self) -> None:
        symbol = CodeSymbol(name="MyClass", kind="class", file="test.py", line=20)
        assert symbol.name == "MyClass"
        assert symbol.kind == "class"

    def test_creates_constant_symbol(self) -> None:
        symbol = CodeSymbol(name="MY_CONST", kind="constant", file="test.py", line=5)
        assert symbol.name == "MY_CONST"
        assert symbol.kind == "constant"


class TestDocReference:
    """Tests for DocReference dataclass."""

    def test_creates_backtick_reference(self) -> None:
        ref = DocReference(
            reference="my_func",
            kind=KIND_BACKTICK,
            file="docs/test.md",
            line=15,
            context="Use `my_func` to do things",
        )
        assert ref.reference == "my_func"
        assert ref.kind == KIND_BACKTICK
        assert ref.file == "docs/test.md"
        assert ref.line == 15

    def test_creates_cli_command_reference(self) -> None:
        ref = DocReference(
            reference="cihub docs stale",
            kind=KIND_CLI_COMMAND,
            file="docs/test.md",
            line=20,
            context="Run `cihub docs stale` to check",
        )
        assert ref.kind == KIND_CLI_COMMAND


class TestStaleReport:
    """Tests for StaleReport dataclass and to_dict method."""

    def test_empty_report(self) -> None:
        report = StaleReport(git_range="HEAD~5")
        assert report.git_range == "HEAD~5"
        assert report.stale_references == []
        assert report.removed_symbols == []

    def test_to_dict_schema(self) -> None:
        """Test JSON output schema matches Part 11 spec."""
        report = StaleReport(
            git_range="HEAD~10",
            removed_symbols=["old_func"],
            added_symbols=["new_func"],
            renamed_symbols=[("foo", "bar")],
            deleted_files=["old.py"],
            renamed_files=[("a.py", "b.py")],
            stale_references=[
                StaleReference(
                    doc_file="docs/test.md",
                    doc_line=10,
                    reference="old_func",
                    reason=REASON_REMOVED,
                    suggestion="Symbol was removed",
                    context="Use `old_func` for...",
                )
            ],
        )
        result = report.to_dict()

        # Check top-level keys
        assert result["git_range"] == "HEAD~10"
        assert "stats" in result
        assert "changed_symbols" in result
        assert "file_changes" in result
        assert "stale_references" in result

        # Check stats
        assert result["stats"]["removed_symbols"] == 1
        assert result["stats"]["added_symbols"] == 1
        assert result["stats"]["renamed_symbols"] == 1
        assert result["stats"]["stale_refs"] == 1

        # Check renamed format
        assert result["changed_symbols"]["renamed"] == [{"old": "foo", "new": "bar"}]


class TestConstants:
    """Tests for module constants."""

    def test_default_since_is_head_tilde_10(self) -> None:
        assert DEFAULT_SINCE == "HEAD~10"

    def test_parsed_fence_types_includes_bash(self) -> None:
        assert "bash" in PARSED_FENCE_TYPES
        assert "shell" in PARSED_FENCE_TYPES
        assert "" in PARSED_FENCE_TYPES  # Untagged fences

    def test_skipped_fence_types_includes_python(self) -> None:
        assert "python" in SKIPPED_FENCE_TYPES
        assert "json" in SKIPPED_FENCE_TYPES

    def test_false_positive_tokens_includes_common_words(self) -> None:
        assert "true" in FALSE_POSITIVE_TOKENS
        assert "false" in FALSE_POSITIVE_TOKENS
        assert "none" in FALSE_POSITIVE_TOKENS


# =============================================================================
# Test Extraction
# =============================================================================


class TestExtractPythonSymbols:
    """Tests for Python symbol extraction via AST."""

    def test_extracts_function(self) -> None:
        code = "def my_function(): pass"
        symbols = extract_python_symbols(code, "test.py")
        assert len(symbols) == 1
        assert symbols[0].name == "my_function"
        assert symbols[0].kind == "function"
        assert symbols[0].line == 1

    def test_extracts_async_function(self) -> None:
        code = "async def async_func(): pass"
        symbols = extract_python_symbols(code, "test.py")
        assert len(symbols) == 1
        assert symbols[0].name == "async_func"
        assert symbols[0].kind == "async_function"

    def test_extracts_class(self) -> None:
        code = "class MyClass: pass"
        symbols = extract_python_symbols(code, "test.py")
        assert len(symbols) == 1
        assert symbols[0].name == "MyClass"
        assert symbols[0].kind == "class"

    def test_extracts_constant(self) -> None:
        code = "MY_CONSTANT = 42"
        symbols = extract_python_symbols(code, "test.py")
        assert len(symbols) == 1
        assert symbols[0].name == "MY_CONSTANT"
        assert symbols[0].kind == "constant"

    def test_ignores_lowercase_variables(self) -> None:
        code = "my_var = 42"
        symbols = extract_python_symbols(code, "test.py")
        assert len(symbols) == 0

    def test_extracts_multiple_symbols(self) -> None:
        code = textwrap.dedent("""
            def func1(): pass
            class MyClass:
                def method(self): pass
            async def async_func(): pass
            MY_CONST = 1
        """)
        symbols = extract_python_symbols(code, "test.py")
        names = {s.name for s in symbols}
        assert "func1" in names
        assert "MyClass" in names
        assert "method" in names
        assert "async_func" in names
        assert "MY_CONST" in names

    def test_handles_syntax_error_gracefully(self) -> None:
        code = "def broken( syntax"
        symbols = extract_python_symbols(code, "test.py")
        assert symbols == []

    def test_line_numbers_are_accurate(self) -> None:
        code = textwrap.dedent("""
            # comment

            def func_on_line_4():
                pass
        """)
        symbols = extract_python_symbols(code, "test.py")
        assert len(symbols) == 1
        assert symbols[0].line == 4


class TestExtractDocReferences:
    """Tests for markdown reference extraction."""

    def test_finds_backtick_reference(self) -> None:
        content = "Use `my_function` to do things"
        refs = extract_doc_references(content, "test.md")
        assert len(refs) >= 1
        assert any(r.reference == "my_function" for r in refs)

    def test_finds_cli_command(self) -> None:
        content = "Run `cihub docs stale` to check"
        refs = extract_doc_references(content, "test.md")
        cli_refs = [r for r in refs if r.kind == KIND_CLI_COMMAND]
        assert len(cli_refs) >= 1

    def test_finds_cli_flag(self) -> None:
        content = "Use `--json` for machine output"
        refs = extract_doc_references(content, "test.md")
        flag_refs = [r for r in refs if r.kind == KIND_CLI_FLAG]
        assert len(flag_refs) >= 1
        assert any(r.reference == "--json" for r in flag_refs)

    def test_finds_file_path(self) -> None:
        content = "Edit `cihub/commands/docs.py` to add features"
        refs = extract_doc_references(content, "test.md")
        path_refs = [r for r in refs if r.kind == KIND_FILE_PATH]
        assert len(path_refs) >= 1

    def test_finds_config_key(self) -> None:
        content = "Set `python.pytest.enabled` to true"
        refs = extract_doc_references(content, "test.md")
        config_refs = [r for r in refs if r.kind == KIND_CONFIG_KEY]
        assert len(config_refs) >= 1

    def test_finds_env_var(self) -> None:
        content = "Set `CIHUB_DEBUG` environment variable"
        refs = extract_doc_references(content, "test.md")
        env_refs = [r for r in refs if r.kind == KIND_ENV_VAR]
        assert len(env_refs) >= 1

    def test_skips_false_positives(self) -> None:
        content = "Returns `true` or `false`"
        refs = extract_doc_references(content, "test.md")
        # Should not include "true" or "false"
        assert not any(r.reference == "true" for r in refs)
        assert not any(r.reference == "false" for r in refs)

    def test_skips_short_tokens(self) -> None:
        content = "For `i` in range, use `n`"
        refs = extract_doc_references(content, "test.md")
        # Should not include single letters
        assert not any(r.reference == "i" for r in refs)
        assert not any(r.reference == "n" for r in refs)

    def test_skips_python_fence_content(self) -> None:
        content = textwrap.dedent("""
            Here's an example:
            ```python
            def example_function():
                pass
            ```
            But `other_ref` should be found.
        """)
        refs = extract_doc_references(content, "test.md")
        # example_function is in a python fence, should be skipped
        assert not any(r.reference == "example_function" for r in refs)
        # other_ref is in prose, should be found
        assert any(r.reference == "other_ref" for r in refs)

    def test_parses_bash_fence_content(self) -> None:
        content = textwrap.dedent("""
            Run this:
            ```bash
            cihub docs stale --json
            ```
        """)
        refs = extract_doc_references(content, "test.md")
        # CLI commands in bash fences should be found
        cli_refs = [r for r in refs if r.kind == KIND_CLI_COMMAND]
        assert len(cli_refs) >= 1

    def test_skip_fences_flag(self) -> None:
        content = textwrap.dedent("""
            ```bash
            cihub docs stale
            ```
        """)
        refs = extract_doc_references(content, "test.md", skip_fences=True)
        # Should find nothing when skip_fences=True
        cli_refs = [r for r in refs if r.kind == KIND_CLI_COMMAND]
        assert len(cli_refs) == 0

    def test_context_includes_surrounding_lines(self) -> None:
        content = "line 1\nUse `my_func` here\nline 3"
        refs = extract_doc_references(content, "test.md")
        ref = next(r for r in refs if r.reference == "my_func")
        assert "line 1" in ref.context
        assert "my_func" in ref.context
        assert "line 3" in ref.context


# =============================================================================
# Test Comparison
# =============================================================================


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
            StaleReference(
                doc_file="a.md", doc_line=1, reference="x",
                reason="removed", suggestion="", context=""
            ),
            StaleReference(
                doc_file="b.md", doc_line=2, reference="y",
                reason="removed", suggestion="", context=""
            ),
            StaleReference(
                doc_file="a.md", doc_line=3, reference="z",
                reason="removed", suggestion="", context=""
            ),
        ]
        grouped = group_stale_by_file(refs)
        assert len(grouped["a.md"]) == 2
        assert len(grouped["b.md"]) == 1


# =============================================================================
# Test Output
# =============================================================================


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


# =============================================================================
# Integration Tests (using temp directories)
# =============================================================================


class TestGitOperations:
    """Tests for git operations using mocks."""

    def test_is_git_repo_returns_false_for_non_repo(self, tmp_path: Path) -> None:
        from cihub.commands.docs_stale import is_git_repo
        assert not is_git_repo(tmp_path)

    def test_resolve_git_ref_returns_none_for_invalid(self, tmp_path: Path) -> None:
        from cihub.commands.docs_stale import resolve_git_ref
        # In a non-git directory, any ref is invalid
        assert resolve_git_ref("HEAD", tmp_path) is None


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


class TestCommandIntegration:
    """Integration tests for the command handler."""

    def test_returns_exit_usage_for_non_git_repo(self, tmp_path: Path) -> None:
        """Non-git repos should return EXIT_USAGE."""
        import argparse

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

        with patch("cihub.commands.docs_stale.hub_root", return_value=tmp_path):
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
        def check_serialization(
            removed: list[str], added: list[str], renamed: list[tuple[str, str]]
        ) -> None:
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
