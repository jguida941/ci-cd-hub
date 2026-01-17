"""Tests for docs_stale symbol and reference extraction.

Split from test_docs_stale.py for better organization.
Tests: extract_python_symbols, extract_doc_references
"""

from __future__ import annotations

import textwrap

from cihub.commands.docs_stale import (
    KIND_CLI_COMMAND,
    KIND_CLI_FLAG,
    KIND_CONFIG_KEY,
    KIND_ENV_VAR,
    KIND_FILE_PATH,
    extract_doc_references,
    extract_python_symbols,
)


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
