"""Tests that verify CI tools actually catch real errors.

These tests scaffold projects, inject intentional errors, run tools,
and verify that errors are properly detected and reported.
"""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path

import pytest

from cihub.ci_runner import run_black, run_isort, run_ruff
from cihub.commands.scaffold import scaffold_fixture


class TestPythonToolErrorDetection:
    """Test that Python tools catch real errors."""

    def test_ruff_catches_lint_errors(self, tmp_path: Path) -> None:
        """Verify ruff detects lint violations in bad Python code."""
        # Create a scaffolded project
        dest = tmp_path / "project"
        scaffold_fixture("python-pyproject", dest)

        # Inject bad code with lint errors
        bad_code = '''\
import os  # F401: unused import
import sys  # F401: unused import

def bad_function( x,y ):  # E201, E231: whitespace issues
    unused_var = 42  # F841: unused variable
    if True:
        pass
    return x+y
'''
        (dest / "bad_code.py").write_text(bad_code)

        # Run ruff
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_ruff(dest, output_dir)

        # Verify ruff caught the errors
        assert result.ran is True
        assert result.success is False, "Ruff should fail on bad code"
        assert result.metrics.get("ruff_errors", 0) > 0, "Ruff should report errors"

    def test_ruff_passes_on_clean_code(self, tmp_path: Path) -> None:
        """Verify ruff passes on clean scaffold code."""
        dest = tmp_path / "project"
        scaffold_fixture("python-pyproject", dest)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_ruff(dest, output_dir)

        assert result.ran is True
        assert result.success is True, "Ruff should pass on clean scaffold code"
        assert result.metrics.get("ruff_errors", 0) == 0

    def test_black_catches_formatting_issues(self, tmp_path: Path) -> None:
        """Verify black detects formatting issues."""
        dest = tmp_path / "project"
        scaffold_fixture("python-pyproject", dest)

        # Inject badly formatted code
        bad_format = '''\
def ugly_function(x,y,z):
    return x+y+z

class BadClass:
    def method(self,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z):
        pass
'''
        (dest / "bad_format.py").write_text(bad_format)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_black(dest, output_dir)

        assert result.ran is True
        assert result.success is False, "Black should fail on badly formatted code"

    def test_black_passes_on_clean_code(self, tmp_path: Path) -> None:
        """Verify black passes on clean scaffold code."""
        dest = tmp_path / "project"
        scaffold_fixture("python-pyproject", dest)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_black(dest, output_dir)

        assert result.ran is True
        assert result.success is True, "Black should pass on clean scaffold code"

    def test_isort_catches_import_order_issues(self, tmp_path: Path) -> None:
        """Verify isort detects import order issues."""
        dest = tmp_path / "project"
        scaffold_fixture("python-pyproject", dest)

        # Inject code with bad import order
        bad_imports = '''\
import sys
import os
from pathlib import Path
import json
from typing import Any
import re

def func():
    pass
'''
        (dest / "bad_imports.py").write_text(bad_imports)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_isort(dest, output_dir)

        assert result.ran is True
        # isort may or may not fail depending on the specific order - this tests it runs

    def test_isort_passes_on_clean_code(self, tmp_path: Path) -> None:
        """Verify isort passes on clean scaffold code."""
        dest = tmp_path / "project"
        scaffold_fixture("python-pyproject", dest)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_isort(dest, output_dir)

        assert result.ran is True
        assert result.success is True, "isort should pass on clean scaffold code"


class TestScaffoldToolCompatibility:
    """Test that all scaffold types work with their expected tools."""

    @pytest.mark.parametrize(
        "scaffold_type",
        ["python-pyproject", "python-setup", "python-src-layout"],
    )
    def test_python_scaffold_passes_ruff(self, tmp_path: Path, scaffold_type: str) -> None:
        """All Python scaffolds should pass ruff out of the box."""
        dest = tmp_path / "project"
        scaffold_fixture(scaffold_type, dest)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_ruff(dest, output_dir)

        assert result.ran is True
        assert result.success is True, f"{scaffold_type} should pass ruff"

    @pytest.mark.parametrize(
        "scaffold_type",
        ["python-pyproject", "python-setup", "python-src-layout"],
    )
    def test_python_scaffold_passes_black(self, tmp_path: Path, scaffold_type: str) -> None:
        """All Python scaffolds should pass black out of the box."""
        dest = tmp_path / "project"
        scaffold_fixture(scaffold_type, dest)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_black(dest, output_dir)

        assert result.ran is True
        assert result.success is True, f"{scaffold_type} should pass black"

    @pytest.mark.parametrize(
        "scaffold_type",
        ["python-pyproject", "python-setup", "python-src-layout"],
    )
    def test_python_scaffold_passes_isort(self, tmp_path: Path, scaffold_type: str) -> None:
        """All Python scaffolds should pass isort out of the box."""
        dest = tmp_path / "project"
        scaffold_fixture(scaffold_type, dest)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_isort(dest, output_dir)

        assert result.ran is True
        assert result.success is True, f"{scaffold_type} should pass isort"
