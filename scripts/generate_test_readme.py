#!/usr/bin/env python3
"""Generate tests/README.md from coverage data.

Usage: python scripts/generate_test_readme.py [--coverage-file PATH] [--output PATH]

Aggregates all test metrics into a summary README.

Runs: In CI after test suite completes
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def load_coverage_data(coverage_file: Path) -> dict:
    """Load coverage data from coverage.json."""
    if not coverage_file.exists():
        return {}

    try:
        with open(coverage_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return {}


def count_tests(tests_dir: Path) -> dict[str, int]:
    """Count tests by category."""
    import ast

    counts = {
        "unit": 0,
        "integration": 0,
        "e2e": 0,
        "property": 0,
        "contract": 0,
        "total": 0,
    }

    for test_file in tests_dir.glob("**/test_*.py"):
        try:
            tree = ast.parse(test_file.read_text(encoding="utf-8"))
            test_count = sum(
                1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            )
            counts["total"] += test_count

            # Categorize by directory
            rel_path = str(test_file.relative_to(tests_dir))
            if rel_path.startswith("unit/"):
                counts["unit"] += test_count
            elif rel_path.startswith("integration/"):
                counts["integration"] += test_count
            elif rel_path.startswith("e2e/"):
                counts["e2e"] += test_count
            elif rel_path.startswith("property/"):
                counts["property"] += test_count
            elif rel_path.startswith("contract/"):
                counts["contract"] += test_count
            else:
                # Flat structure - count as unit
                counts["unit"] += test_count
        except SyntaxError:
            continue

    return counts


def generate_readme(
    coverage_data: dict,
    test_counts: dict[str, int],
    tests_dir: Path,
) -> str:
    """Generate README content."""
    # Extract overall coverage
    totals = coverage_data.get("totals", {})
    overall_coverage = totals.get("percent_covered", 0)

    # Count test files
    test_files = list(tests_dir.glob("**/test_*.py"))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    readme = f"""# Tests

> **Auto-generated** - Do not edit manually. Run `python scripts/generate_test_readme.py` to regenerate.
>
> Last updated: {timestamp}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {test_counts["total"]} |
| Test Files | {len(test_files)} |
| Overall Coverage | {overall_coverage:.1f}% |

## Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| Unit | {test_counts["unit"]} | Fast, isolated tests |
| Integration | {test_counts["integration"]} | Tests with external dependencies |
| E2E | {test_counts["e2e"]} | End-to-end workflow tests |
| Property | {test_counts["property"]} | Hypothesis property-based tests |
| Contract | {test_counts["contract"]} | API/schema contract tests |

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cihub --cov-report=html

# Run specific category
pytest tests/unit/
pytest tests/integration/

# Run fast tests only (exclude slow)
pytest -m "not slow"

# Run mutation testing
mutmut run
```

## Coverage Targets

Coverage targets are defined in `config/defaults.yaml` under the `thresholds` section:

```yaml
thresholds:
  coverage_min: 70
  mutation_score_min: 70
```

To view or modify thresholds:

```bash
cihub hub-ci thresholds show
cihub hub-ci thresholds set coverage_min 80
```

## Adding New Tests

1. Create test file in appropriate category directory
2. Follow naming convention: `test_<module>.py`
3. Add TEST-METRICS block to track coverage
4. Run `python scripts/check_test_drift.py` to verify compliance
"""

    # Add per-file coverage if available
    files_data = coverage_data.get("files", {})
    if files_data:
        readme += "\n## Coverage by Module\n\n"
        readme += "| Module | Coverage | Lines |\n"
        readme += "|--------|----------|-------|\n"

        for file_path, file_data in sorted(files_data.items()):
            if "cihub/" in file_path:
                summary = file_data.get("summary", {})
                covered = summary.get("percent_covered", 0)
                num_statements = summary.get("num_statements", 0)
                # Shorten path for display
                short_path = file_path.split("cihub/")[-1] if "cihub/" in file_path else file_path
                readme += f"| `{short_path}` | {covered:.1f}% | {num_statements} |\n"

    return readme


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
        "--tests-dir",
        type=Path,
        default=Path("tests"),
        help="Path to tests directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/README.md"),
        help="Output path for README.md",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print README content without writing",
    )
    args = parser.parse_args()

    coverage_data = load_coverage_data(args.coverage_file)
    test_counts = count_tests(args.tests_dir)
    readme_content = generate_readme(coverage_data, test_counts, args.tests_dir)

    if args.dry_run:
        print(readme_content)
    else:
        args.output.write_text(readme_content, encoding="utf-8")
        print(f"Generated: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
