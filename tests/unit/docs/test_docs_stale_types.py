"""Tests for docs_stale data types and constants.

Split from test_docs_stale.py for better organization.
Tests: CodeSymbol, DocReference, StaleReport, module constants
"""

# TEST-METRICS:

from __future__ import annotations

from cihub.commands.docs_stale import (
    DEFAULT_SINCE,
    FALSE_POSITIVE_TOKENS,
    KIND_BACKTICK,
    KIND_CLI_COMMAND,
    PARSED_FENCE_TYPES,
    REASON_REMOVED,
    SKIPPED_FENCE_TYPES,
    CodeSymbol,
    DocReference,
    StaleReference,
    StaleReport,
)


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
