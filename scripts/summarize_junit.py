#!/usr/bin/env python3
"""Summarize JUnit XML test results and emit GitHub Actions outputs."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET  # nosec
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", required=True, type=Path, help="Path to the JUnit XML report")
    parser.add_argument("--output", required=True, type=Path, help="Path to append GitHub Action outputs")
    return parser.parse_args()


def _find_suites(root: ET.Element) -> list[ET.Element]:
    if root.tag == "testsuites":
        return list(root.findall("testsuite"))
    if root.tag == "testsuite":
        return [root]
    return list(root.findall(".//testsuite"))


def main() -> int:
    args = _parse_args()
    if not args.junit.exists():
        raise SystemExit(f"JUnit report missing at {args.junit}")

    tree = ET.parse(args.junit)  # noqa: S314  # nosec
    root = tree.getroot()
    suites = _find_suites(root)

    total = failures = skipped = errors = 0
    duration = 0.0
    for suite in suites:
        total += int(float(suite.attrib.get("tests", "0")))
        failures += int(float(suite.attrib.get("failures", "0")))
        skipped += int(float(suite.attrib.get("skipped", "0")))
        errors += int(float(suite.attrib.get("errors", "0")))
        duration += float(suite.attrib.get("time", "0") or 0)

    duration_ms = int(duration * 1000)
    failed = failures + errors

    with args.output.open("a", encoding="utf-8") as handle:
        handle.write(f"tests_total={total}\n")
        handle.write(f"tests_failed={failed}\n")
        handle.write(f"tests_skipped={skipped}\n")
        handle.write(f"tests_duration_ms={duration_ms}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
