#!/usr/bin/env python3
"""Update test file headers with coverage/mutation metrics.

Usage: python scripts/update_test_metrics.py [--coverage-file PATH] [--mutation-file PATH]

Reads coverage and mutation data and updates each test file's
TEST-METRICS block with actual values.

Runs: After pytest with coverage, after mutmut
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_coverage_data(coverage_file: Path) -> dict[str, float]:
    """Load coverage data from coverage.json or .coverage.

    Returns:
        Dict mapping module paths to coverage percentages.
    """
    if not coverage_file.exists():
        return {}

    try:
        with open(coverage_file, encoding="utf-8") as f:
            data = json.load(f)

        # coverage.json format
        if "files" in data:
            result = {}
            for file_path, file_data in data["files"].items():
                summary = file_data.get("summary", {})
                covered = summary.get("percent_covered", 0)
                result[file_path] = round(covered, 1)
            return result
    except (json.JSONDecodeError, KeyError):
        pass

    return {}


def load_mutation_data(mutation_file: Path) -> dict[str, float]:
    """Load mutation testing data from mutmut results.

    Returns:
        Dict mapping module paths to mutation scores.
    """
    if not mutation_file.exists():
        return {}

    try:
        with open(mutation_file, encoding="utf-8") as f:
            data = json.load(f)

        # mutmut json format
        result = {}
        for file_path, file_data in data.get("files", {}).items():
            killed = file_data.get("killed", 0)
            total = file_data.get("total", 0)
            if total > 0:
                result[file_path] = round((killed / total) * 100, 1)
        return result
    except (json.JSONDecodeError, KeyError):
        pass

    return {}


def find_test_files(tests_dir: Path) -> list[Path]:
    """Find all test files in the tests directory."""
    return sorted(tests_dir.glob("**/test_*.py"))


def update_metrics_block(
    test_file: Path,
    coverage: dict[str, float],
    mutation: dict[str, float],
) -> bool:
    """Update TEST-METRICS block in a test file.

    Returns:
        True if file was modified, False otherwise.
    """
    content = test_file.read_text(encoding="utf-8")

    # Pattern to match TEST-METRICS block
    metrics_pattern = re.compile(
        r"(# TEST-METRICS:.*?\n)" r"(#\s*Coverage:\s*[\d.]+%.*?\n)?" r"(#\s*Mutation:\s*[\d.]+%.*?\n)?",
        re.MULTILINE,
    )

    # Try to infer the module being tested from the test file name
    # e.g., test_config.py -> cihub/config.py
    test_name = test_file.stem  # test_config
    module_name = test_name.replace("test_", "")  # config

    # Find corresponding coverage entry
    cov_value = None
    mut_value = None
    for path, value in coverage.items():
        if module_name in path:
            cov_value = value
            break

    for path, value in mutation.items():
        if module_name in path:
            mut_value = value
            break

    # Build new metrics block
    new_block_lines = ["# TEST-METRICS:\n"]
    if cov_value is not None:
        new_block_lines.append(f"#   Coverage: {cov_value}%\n")
    if mut_value is not None:
        new_block_lines.append(f"#   Mutation: {mut_value}%\n")

    new_block = "".join(new_block_lines)

    # Check if metrics block exists
    match = metrics_pattern.search(content)
    if match:
        # Update existing block
        new_content = metrics_pattern.sub(new_block, content, count=1)
    else:
        # Add new block after docstring
        docstring_end = content.find('"""', content.find('"""') + 3)
        if docstring_end > 0:
            insert_pos = content.find("\n", docstring_end) + 1
            new_content = content[:insert_pos] + "\n" + new_block + content[insert_pos:]
        else:
            # No docstring, add at top after any imports
            new_content = new_block + "\n" + content

    if new_content != content:
        test_file.write_text(new_content, encoding="utf-8")
        return True
    return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage-file",
        type=Path,
        default=Path("coverage.json"),
        help="Path to coverage.json file",
    )
    parser.add_argument(
        "--mutation-file",
        type=Path,
        default=Path(".mutmut-cache/results.json"),
        help="Path to mutmut results.json file",
    )
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=Path("tests"),
        help="Path to tests directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    args = parser.parse_args()

    coverage = load_coverage_data(args.coverage_file)
    mutation = load_mutation_data(args.mutation_file)

    if not coverage and not mutation:
        print("No coverage or mutation data found. Run pytest with coverage first.")
        return 1

    test_files = find_test_files(args.tests_dir)
    modified = 0

    for test_file in test_files:
        if args.dry_run:
            print(f"Would update: {test_file}")
            modified += 1
        else:
            if update_metrics_block(test_file, coverage, mutation):
                print(f"Updated: {test_file}")
                modified += 1

    print(f"\n{'Would modify' if args.dry_run else 'Modified'} {modified} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
