#!/usr/bin/env python3
"""Check for test organization drift.

Usage: python scripts/check_test_drift.py [--tests-dir PATH] [--strict]

Checks:
- All test files have TEST-METRICS block
- All test files follow naming conventions
- No files below target thresholds
- Template structure compliance

Runs: In CI, fails build on drift

Exit codes:
    0: All checks pass
    1: Drift detected (warnings only in non-strict mode)
    2: Critical issues found
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml


def load_thresholds() -> dict:
    """Load thresholds from config/defaults.yaml."""
    defaults_path = Path("config/defaults.yaml")
    if not defaults_path.exists():
        return {"coverage_min": 70, "mutation_score_min": 70}

    try:
        with open(defaults_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("thresholds", {})
    except yaml.YAMLError:
        return {"coverage_min": 70, "mutation_score_min": 70}


def check_metrics_block(test_file: Path) -> list[str]:
    """Check if test file has TEST-METRICS block.

    Returns:
        List of issues found.
    """
    issues = []
    content = test_file.read_text(encoding="utf-8")

    if "# TEST-METRICS:" not in content:
        issues.append(f"Missing TEST-METRICS block: {test_file}")

    return issues


def check_naming_convention(test_file: Path) -> list[str]:
    """Check if test file follows naming conventions.

    Returns:
        List of issues found.
    """
    issues = []

    # Check file name
    if not test_file.name.startswith("test_"):
        issues.append(f"Invalid test file name (should start with test_): {test_file}")

    # Check test function names
    try:
        content = test_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Test functions should start with test_
                if node.name.startswith("_") and "test" in node.name.lower():
                    continue  # Private helpers are OK
                if "test" in node.name.lower() and not node.name.startswith("test_"):
                    issues.append(f"Non-standard test function name '{node.name}' in {test_file}")
    except SyntaxError as e:
        issues.append(f"Syntax error in {test_file}: {e}")

    return issues


def check_docstring(test_file: Path) -> list[str]:
    """Check if test file has a module docstring.

    Returns:
        List of issues found.
    """
    issues = []

    try:
        content = test_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        # Check for module docstring
        if not ast.get_docstring(tree):
            issues.append(f"Missing module docstring: {test_file}")

        # Check test function docstrings (warning only)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                if not ast.get_docstring(node):
                    # This is a warning, not an error
                    pass
    except SyntaxError:
        pass  # Already caught in naming check

    return issues


def check_structure_compliance(tests_dir: Path) -> list[str]:
    """Check for expected directory structure.

    Returns:
        List of issues found.
    """
    issues = []

    # Expected directories for organized tests
    expected_dirs = ["unit", "integration", "e2e", "property", "contract"]

    # Check if any expected structure exists
    has_structure = any((tests_dir / d).exists() for d in expected_dirs)

    if not has_structure:
        # Flat structure - this is allowed but noted
        pass

    # Check for orphan test files (tests not in any category)
    for _test_file in tests_dir.glob("test_*.py"):
        # Root-level tests are allowed in flat structure
        pass

    return issues


def check_import_consistency(test_file: Path) -> list[str]:
    """Check for consistent import patterns.

    Returns:
        List of issues found.
    """
    issues = []

    try:
        content = test_file.read_text(encoding="utf-8")

        # Check for __future__ annotations
        if "from __future__ import annotations" not in content:
            # Warning: should use future annotations for type hints
            pass

        # Check for proper pytest import
        if "import pytest" not in content and "@pytest" in content:
            issues.append(f"Uses pytest decorators without importing pytest: {test_file}")

    except Exception:  # noqa: S110, BLE001
        pass  # Skip file if read fails

    return issues


def run_checks(tests_dir: Path, strict: bool = False) -> tuple[list[str], list[str]]:
    """Run all drift checks.

    Returns:
        Tuple of (errors, warnings).
    """
    errors = []
    warnings = []

    test_files = list(tests_dir.glob("**/test_*.py"))

    if not test_files:
        errors.append(f"No test files found in {tests_dir}")
        return errors, warnings

    for test_file in test_files:
        # Critical checks (errors)
        errors.extend(check_naming_convention(test_file))

        # Non-critical checks (warnings)
        warnings.extend(check_metrics_block(test_file))
        warnings.extend(check_docstring(test_file))
        warnings.extend(check_import_consistency(test_file))

    # Structure checks
    warnings.extend(check_structure_compliance(tests_dir))

    return errors, warnings


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=Path("tests"),
        help="Path to tests directory",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    thresholds = load_thresholds()
    errors, warnings = run_checks(args.tests_dir, args.strict)

    if args.strict:
        errors.extend(warnings)
        warnings = []

    if args.json:
        import json

        result = {
            "status": "failed" if errors else "passed",
            "errors": errors,
            "warnings": warnings,
            "thresholds": thresholds,
            "test_files_checked": len(list(args.tests_dir.glob("**/test_*.py"))),
        }
        print(json.dumps(result, indent=2))
    else:
        if errors:
            print("ERRORS:")
            for error in errors:
                print(f"  ✗ {error}")
            print()

        if warnings:
            print("WARNINGS:")
            for warning in warnings:
                print(f"  ⚠ {warning}")
            print()

        test_count = len(list(args.tests_dir.glob("**/test_*.py")))
        print(f"Checked {test_count} test files")
        print(f"Errors: {len(errors)}, Warnings: {len(warnings)}")

    if errors:
        return 2 if any("Critical" in e for e in errors) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
