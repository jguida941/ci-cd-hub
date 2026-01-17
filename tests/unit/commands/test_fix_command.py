"""Tests for the cihub fix command."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_fix_help():
    """Test that fix --help works."""
    result = subprocess.run(
        [sys.executable, "-m", "cihub", "fix", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "--safe" in result.stdout
    assert "--report" in result.stdout
    assert "--ai" in result.stdout


def test_fix_requires_mode():
    """Test that fix requires --safe or --report."""
    result = subprocess.run(
        [sys.executable, "-m", "cihub", "fix"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "required" in result.stderr.lower() or "error" in result.stderr.lower()


def test_fix_safe_dry_run():
    """Test fix --safe --dry-run on current repo (Python)."""
    result = subprocess.run(
        [sys.executable, "-m", "cihub", "fix", "--safe", "--dry-run", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "success"
    assert "dry-run" in data["summary"]
    assert data["data"]["language"] == "python"


def test_fix_safe_dry_run_java(tmp_path: Path):
    """Test fix --safe --dry-run on a Java repo."""
    # Create a minimal Java project
    pom = tmp_path / "pom.xml"
    pom.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>test</artifactId>
  <version>1.0</version>
</project>
"""
    )

    result = subprocess.run(
        [sys.executable, "-m", "cihub", "fix", "--safe", "--dry-run", "--json", "--repo", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["data"]["language"] == "java"
    assert "dry-run" in data["summary"]


def test_fix_report_json(tmp_path: Path):
    """Test fix --report --json produces valid JSON."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    result = subprocess.run(
        [sys.executable, "-m", "cihub", "fix", "--report", "--json", "--repo", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,  # Report mode runs multiple tools
        env=env,
    )
    # Exit code can be 0 or 1 depending on findings
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert "issues" in data["data"]
    assert "language" in data["data"]


def test_fix_report_ai(tmp_path: Path):
    """Test fix --report --ai generates the AI report file."""
    # Create a minimal Python project
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "test.py").write_text("x = 1\n")

    result = subprocess.run(
        [sys.executable, "-m", "cihub", "fix", "--report", "--ai", "--json", "--repo", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    # Exit code can be 0 or 1 depending on findings
    assert result.returncode in (0, 1)

    # Check that the AI report was created
    ai_report = tmp_path / ".cihub" / "fix-report.md"
    assert ai_report.exists()

    content = ai_report.read_text()
    assert "# Fix Report" in content
    assert "Summary" in content


def test_fix_invalid_safe_ai():
    """Test that --safe --ai is rejected (--ai only works with --report)."""
    result = subprocess.run(
        [sys.executable, "-m", "cihub", "fix", "--safe", "--ai", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # Exit code 2 for usage errors (EXIT_USAGE maps to 2 via CLI)
    assert result.returncode == 2
    # Validation error is returned - check that the error message is present
    assert "--ai" in result.stdout
    assert "requires --report" in result.stdout or "--report" in result.stdout


def test_fix_invalid_report_dry_run():
    """Test that --report --dry-run is rejected (--dry-run only works with --safe)."""
    result = subprocess.run(
        [sys.executable, "-m", "cihub", "fix", "--report", "--dry-run", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # Exit code 2 for usage errors (EXIT_USAGE maps to 2 via CLI)
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["status"] == "failure"
    assert "--dry-run" in data["summary"]
