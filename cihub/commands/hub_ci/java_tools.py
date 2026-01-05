"""Java build and analysis commands."""

from __future__ import annotations

import argparse
import stat
from pathlib import Path

import defusedxml.ElementTree as ET  # Secure XML parsing

from cihub.exit_codes import EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.github_context import OutputContext

from . import (
    _parse_float,
    _parse_int,
    _run_command,
)


def _iter_junit_reports(repo_path: Path) -> list[Path]:
    reports: list[Path] = []
    for pattern in ("**/surefire-reports/*.xml", "**/failsafe-reports/*.xml"):
        reports.extend(repo_path.glob(pattern))
    return reports


def _parse_junit_report(path: Path) -> tuple[int, int, int, int, float]:
    try:
        tree = ET.parse(path)  # noqa: S314 - trusted CI tool output
    except ET.ParseError:
        return 0, 0, 0, 0, 0.0

    root = tree.getroot()

    def parse_suite(element: ET.Element) -> tuple[int, int, int, int, float]:
        tests = _parse_int(element.attrib.get("tests"))
        failures = _parse_int(element.attrib.get("failures"))
        errors = _parse_int(element.attrib.get("errors"))
        skipped = _parse_int(element.attrib.get("skipped"))
        time_val = _parse_float(element.attrib.get("time"))
        return tests, failures, errors, skipped, time_val

    if root.tag == "testsuite":
        return parse_suite(root)

    total = (0, 0, 0, 0, 0.0)
    for child in root.findall("testsuite"):
        tests, failures, errors, skipped, time_val = parse_suite(child)
        total = (
            total[0] + tests,
            total[1] + failures,
            total[2] + errors,
            total[3] + skipped,
            total[4] + time_val,
        )
    return total


def cmd_codeql_build(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    build_type = "none"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        _run_command(
            ["./mvnw", "-B", "-ntp", "compile", "-DskipTests"],
            repo_path,
        )
        build_type = "mvnw"
    elif (repo_path / "pom.xml").exists():
        _run_command(
            ["mvn", "-B", "-ntp", "compile", "-DskipTests"],
            repo_path,
        )
        build_type = "mvn"

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"CodeQL build completed ({build_type})",
        data={"build_type": build_type},
    )


def cmd_smoke_java_build(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    build_type = "none"
    problems: list[dict[str, str]] = []

    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        _run_command(
            ["./mvnw", "-B", "-ntp", "verify", "-Dmaven.test.failure.ignore=true"],
            repo_path,
        )
        build_type = "mvnw"
    elif (repo_path / "pom.xml").exists():
        _run_command(
            ["mvn", "-B", "-ntp", "verify", "-Dmaven.test.failure.ignore=true"],
            repo_path,
        )
        build_type = "mvn"
    else:
        problems.append({"severity": "warning", "message": "No Maven project found"})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Java smoke build completed ({build_type})",
        problems=problems,
        data={"build_type": build_type},
    )


def cmd_smoke_java_tests(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.path).resolve()
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}

    for report in _iter_junit_reports(repo_path):
        tests, failures, errors, skipped, time_val = _parse_junit_report(report)
        totals["tests"] += tests
        totals["failures"] += failures
        totals["errors"] += errors
        totals["skipped"] += skipped
        totals["time"] += time_val

    failed = totals["failures"] + totals["errors"]
    passed = totals["tests"] - failed - totals["skipped"]
    runtime = f"{totals['time']:.2f}s"

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({
        "total": str(totals["tests"]),
        "passed": str(passed),
        "failed": str(failed),
        "skipped": str(totals["skipped"]),
        "runtime": runtime,
    })

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Tests: {totals['tests']} total, {passed} passed, {failed} failed, {totals['skipped']} skipped",
        data={
            "total": totals["tests"],
            "passed": passed,
            "failed": failed,
            "skipped": totals["skipped"],
            "runtime": runtime,
        },
    )


def cmd_smoke_java_coverage(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.path).resolve()
    jacoco_files = list(repo_path.rglob("jacoco.xml"))
    covered = 0
    missed = 0
    for report in jacoco_files:
        try:
            tree = ET.parse(report)  # noqa: S314 - trusted CI tool output
        except ET.ParseError:
            continue
        for counter in tree.getroot().iter("counter"):
            if counter.attrib.get("type") == "INSTRUCTION":
                covered += _parse_int(counter.attrib.get("covered"))
                missed += _parse_int(counter.attrib.get("missed"))

    total = covered + missed
    percent = int((covered * 100) / total) if total > 0 else 0
    ctx = OutputContext.from_args(args)
    ctx.write_outputs({
        "covered": str(covered),
        "missed": str(missed),
        "percent": str(percent),
        "lines": f"{covered} / {total}",
    })

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Coverage: {percent}% ({covered} / {total} instructions)",
        data={"covered": covered, "missed": missed, "percent": percent, "total": total},
    )


def cmd_smoke_java_checkstyle(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        _run_command(
            ["./mvnw", "-B", "-ntp", "-DskipTests", "checkstyle:checkstyle"],
            repo_path,
        )

    violations = 0
    for report in repo_path.rglob("checkstyle-result.xml"):
        try:
            tree = ET.parse(report)  # noqa: S314 - trusted CI tool output
        except ET.ParseError:
            continue
        violations += len(list(tree.getroot().iter("error")))

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"violations": str(violations)})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Checkstyle: {violations} issues found",
        data={"violations": violations},
    )


def cmd_smoke_java_spotbugs(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        _run_command(
            ["./mvnw", "-B", "-ntp", "com.github.spotbugs:spotbugs-maven-plugin:check"],
            repo_path,
        )

    count = 0
    for report in repo_path.rglob("spotbugsXml.xml"):
        try:
            tree = ET.parse(report)  # noqa: S314 - trusted CI tool output
        except ET.ParseError:
            continue
        count += len(list(tree.getroot().iter("BugInstance")))

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"count": str(count)})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"SpotBugs: {count} potential bugs",
        data={"count": count},
    )
