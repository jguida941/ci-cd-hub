"""Parser setup for hub-ci test metrics subcommand."""

from __future__ import annotations


def add_test_metrics_parsers(hub_ci_sub, add_json_flag) -> None:
    """Add test metrics subcommand to hub-ci."""
    parser = hub_ci_sub.add_parser(
        "test-metrics",
        help="Generate/check test metrics and README",
    )
    add_json_flag(parser)
    parser.add_argument(
        "--coverage-file",
        default="coverage.json",
        help="Path to coverage JSON file",
    )
    parser.add_argument(
        "--coverage-db",
        default=".coverage",
        help="Path to coverage data file used to generate JSON",
    )
    parser.add_argument(
        "--mutation-file",
        default=".mutmut-cache/results.json",
        help="Path to mutmut JSON results file",
    )
    parser.add_argument(
        "--tests-dir",
        default="tests",
        help="Path to tests directory",
    )
    parser.add_argument(
        "--readme",
        default="tests/README.md",
        help="Path to generated tests README",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write TEST-METRICS blocks and README when allowed",
    )
    parser.add_argument(
        "--allow-non-main",
        action="store_true",
        help="Allow writes on non-main branches in CI",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings from drift/README checks",
    )
    parser.add_argument(
        "--skip-readme",
        action="store_true",
        help="Skip README generation/check",
    )


__all__ = ["add_test_metrics_parsers"]
