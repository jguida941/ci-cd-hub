"""Parsing helpers for tool outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET

from .shared import _parse_json


def _parse_junit(path: Path) -> dict[str, Any]:
    default_result = {
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "tests_runtime_seconds": 0.0,
    }
    if not path.exists():
        return default_result
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return default_result
    if root.tag.endswith("testsuites"):
        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
        for suite in root:
            totals["tests"] += int(suite.attrib.get("tests", 0))
            totals["failures"] += int(suite.attrib.get("failures", 0))
            totals["errors"] += int(suite.attrib.get("errors", 0))
            totals["skipped"] += int(suite.attrib.get("skipped", 0))
            totals["time"] += float(suite.attrib.get("time", 0.0))
    else:
        totals = {
            "tests": int(root.attrib.get("tests", 0)),
            "failures": int(root.attrib.get("failures", 0)),
            "errors": int(root.attrib.get("errors", 0)),
            "skipped": int(root.attrib.get("skipped", 0)),
            "time": float(root.attrib.get("time", 0.0)),
        }
    failed = totals["failures"] + totals["errors"]
    passed = max(totals["tests"] - failed - totals["skipped"], 0)
    return {
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_skipped": totals["skipped"],
        "tests_runtime_seconds": totals["time"],
    }


def _parse_coverage(path: Path) -> dict[str, Any]:
    default_result = {
        "coverage": 0,
        "coverage_lines_covered": 0,
        "coverage_lines_total": 0,
    }
    if not path.exists():
        return default_result
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return default_result
    line_rate = float(root.attrib.get("line-rate", 0))
    lines_covered = int(root.attrib.get("lines-covered", 0))
    lines_total = int(root.attrib.get("lines-valid", root.attrib.get("lines-total", 0)))
    coverage = int(round(line_rate * 100))
    return {
        "coverage": coverage,
        "coverage_lines_covered": lines_covered,
        "coverage_lines_total": lines_total,
    }


def _parse_junit_files(paths: list[Path]) -> dict[str, Any]:
    totals = {
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "tests_runtime_seconds": 0.0,
    }
    for path in paths:
        parsed = _parse_junit(path)
        totals["tests_passed"] += int(parsed.get("tests_passed", 0))
        totals["tests_failed"] += int(parsed.get("tests_failed", 0))
        totals["tests_skipped"] += int(parsed.get("tests_skipped", 0))
        totals["tests_runtime_seconds"] += float(parsed.get("tests_runtime_seconds", 0.0) or 0.0)
    return totals


def _parse_jacoco_files(paths: list[Path]) -> dict[str, Any]:
    covered = 0
    missed = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for counter in root.iter("counter"):
            if counter.attrib.get("type") != "LINE":
                continue
            covered += int(counter.attrib.get("covered", 0))
            missed += int(counter.attrib.get("missed", 0))
    total = covered + missed
    coverage = int(round((covered / total) * 100)) if total else 0
    return {
        "coverage": coverage,
        "coverage_lines_covered": covered,
        "coverage_lines_total": total,
    }


def _parse_pitest_files(paths: list[Path]) -> dict[str, Any]:
    killed = 0
    survived = 0
    no_coverage = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for mutation in root.iter("mutation"):
            status = mutation.attrib.get("status")
            if status == "KILLED":
                killed += 1
            elif status == "SURVIVED":
                survived += 1
            elif status == "NO_COVERAGE":
                no_coverage += 1
    total = killed + survived + no_coverage
    score = int(round((killed / total) * 100)) if total else 0
    return {
        "mutation_score": score,
        "mutation_killed": killed,
        "mutation_survived": survived,
    }


def _parse_checkstyle_files(paths: list[Path]) -> dict[str, Any]:
    violations = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        violations += len(list(root.iter("error")))
    return {"checkstyle_issues": violations}


def _parse_spotbugs_files(paths: list[Path]) -> dict[str, Any]:
    issues = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        issues += len(list(root.iter("BugInstance")))
    return {"spotbugs_issues": issues}


def _parse_pmd_files(paths: list[Path]) -> dict[str, Any]:
    violations = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        violations += len(list(root.iter("violation")))
    return {"pmd_violations": violations}


def _parse_dependency_check(path: Path) -> dict[str, Any]:
    data = _parse_json(path)
    critical = 0
    high = 0
    medium = 0
    low = 0
    max_cvss: float = 0.0
    if isinstance(data, dict):
        for dep in data.get("dependencies", []) or []:
            for vuln in dep.get("vulnerabilities", []) or []:
                severity = str(vuln.get("severity", "")).upper()
                if severity == "CRITICAL":
                    critical += 1
                elif severity == "HIGH":
                    high += 1
                elif severity == "MEDIUM":
                    medium += 1
                elif severity == "LOW":
                    low += 1
                # Extract CVSS score (prefer v3 over v2)
                cvss_score = 0.0
                cvssv3 = vuln.get("cvssv3", {}) or {}
                cvssv2 = vuln.get("cvssv2", {}) or {}
                if isinstance(cvssv3, dict) and "baseScore" in cvssv3:
                    try:
                        cvss_score = float(cvssv3["baseScore"])
                    except (ValueError, TypeError):
                        pass
                elif isinstance(cvssv2, dict) and "score" in cvssv2:
                    try:
                        cvss_score = float(cvssv2["score"])
                    except (ValueError, TypeError):
                        pass
                max_cvss = max(max_cvss, cvss_score)
    return {
        "owasp_critical": critical,
        "owasp_high": high,
        "owasp_medium": medium,
        "owasp_low": low,
        "owasp_max_cvss": max_cvss,
    }
