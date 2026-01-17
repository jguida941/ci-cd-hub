"""Java tool runners."""

from __future__ import annotations

import os
from pathlib import Path

from . import shared
from .base import ToolResult
from .parsers import (
    _parse_checkstyle_files,
    _parse_dependency_check,
    _parse_jacoco_files,
    _parse_junit_files,
    _parse_pitest_files,
    _parse_pmd_files,
    _parse_spotbugs_files,
)


def _maven_cmd(workdir: Path) -> list[str]:
    mvnw = workdir / "mvnw"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | 0o111)
        return ["./mvnw"]
    return ["mvn"]


def _gradle_cmd(workdir: Path) -> list[str]:
    gradlew = workdir / "gradlew"
    if gradlew.exists():
        gradlew.chmod(gradlew.stat().st_mode | 0o111)
        return ["./gradlew"]
    return ["gradle"]


def run_java_build(
    workdir: Path,
    output_dir: Path,
    build_tool: str,
    jacoco_enabled: bool,
) -> ToolResult:
    log_path = output_dir / "java-build.log"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["test", "--continue"]
        if jacoco_enabled:
            cmd.append("jacocoTestReport")
    else:
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "-Dmaven.test.failure.ignore=true",
            "verify",
        ]
    proc = shared._run_tool_command("build", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    junit_paths = shared._find_files(
        workdir,
        [
            "target/surefire-reports/*.xml",
            "target/failsafe-reports/*.xml",
            "build/test-results/test/*.xml",
        ],
    )
    metrics = _parse_junit_files(junit_paths)
    if jacoco_enabled:
        jacoco_paths = shared._find_files(
            workdir,
            [
                "target/site/jacoco/jacoco.xml",
                "build/reports/jacoco/test/jacocoTestReport.xml",
            ],
        )
        metrics.update(_parse_jacoco_files(jacoco_paths))

    return ToolResult(
        tool="build",
        ran=True,
        success=proc.returncode == 0,
        metrics=metrics,
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_jacoco(workdir: Path, output_dir: Path) -> ToolResult:
    report_paths = shared._find_files(
        workdir,
        [
            "target/site/jacoco/jacoco.xml",
            "build/reports/jacoco/test/jacocoTestReport.xml",
        ],
    )
    metrics = _parse_jacoco_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="jacoco",
        ran=ran,
        success=ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
    )


def run_pitest(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "pitest-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["pitest", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "org.pitest:pitest-maven:mutationCoverage",
        ]
    proc = shared._run_tool_command("pitest", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    report_paths = shared._find_files(
        workdir,
        [
            "target/pit-reports/**/mutations.xml",
            "build/reports/pitest/mutations.xml",
        ],
    )
    metrics = _parse_pitest_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="pitest",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_checkstyle(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "checkstyle-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["checkstyleMain", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "-DskipTests",
            "checkstyle:checkstyle",
        ]
    proc = shared._run_tool_command("checkstyle", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    # Maven outputs to checkstyle-result.xml, Gradle outputs to build/reports/checkstyle/main.xml
    report_paths = shared._find_files(
        workdir,
        [
            "checkstyle-result.xml",
            "target/checkstyle-result.xml",
            "build/reports/checkstyle/main.xml",
            "build/reports/checkstyle/*.xml",
        ],
    )
    metrics = _parse_checkstyle_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="checkstyle",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_spotbugs(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "spotbugs-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["spotbugsMain", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + ["-B", "-ntp", "spotbugs:spotbugs"]
    proc = shared._run_tool_command("spotbugs", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    # Maven outputs to spotbugsXml.xml, Gradle outputs to build/reports/spotbugs/main.xml
    report_paths = shared._find_files(
        workdir,
        [
            "spotbugsXml.xml",
            "target/spotbugsXml.xml",
            "build/reports/spotbugs/main.xml",
            "build/reports/spotbugs/*.xml",
        ],
    )
    metrics = _parse_spotbugs_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="spotbugs",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_pmd(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "pmd-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["pmdMain", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + ["-B", "-ntp", "pmd:check"]
    proc = shared._run_tool_command("pmd", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    # Maven outputs to pmd.xml or target/pmd.xml, Gradle outputs to build/reports/pmd/main.xml
    report_paths = shared._find_files(
        workdir,
        [
            "pmd.xml",
            "target/pmd.xml",
            "build/reports/pmd/main.xml",
            "build/reports/pmd/*.xml",
        ],
    )
    metrics = _parse_pmd_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="pmd",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_owasp(
    workdir: Path,
    output_dir: Path,
    build_tool: str,
    use_nvd_api_key: bool,
) -> ToolResult:
    log_path = output_dir / "owasp-output.txt"
    env = os.environ.copy()
    nvd_key = env.get("NVD_API_KEY")
    if not use_nvd_api_key:
        env.pop("NVD_API_KEY", None)
        nvd_key = None
    nvd_flags: list[str] = []
    if use_nvd_api_key and nvd_key:
        nvd_flags.append(f"-DnvdApiKey={nvd_key}")
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["dependencyCheckAnalyze", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "org.owasp:dependency-check-maven:check",
            "-DfailBuildOnCVSS=11",
            "-DnvdApiDelay=2500",
            "-DnvdMaxRetryCount=10",
            "-Ddependencycheck.failOnError=false",
            *nvd_flags,
        ]
    proc = shared._run_tool_command("owasp", cmd, workdir, output_dir, env=env)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    report_paths = shared._find_files(
        workdir,
        [
            "dependency-check-report.json",
            "target/dependency-check-report.json",
            "build/reports/dependency-check-report.json",
        ],
    )
    metrics = (
        _parse_dependency_check(report_paths[0])
        if report_paths
        else {
            "owasp_critical": 0,
            "owasp_high": 0,
            "owasp_medium": 0,
            "owasp_low": 0,
            "owasp_max_cvss": 0.0,
        }
    )
    ran = bool(report_paths)
    return ToolResult(
        tool="owasp",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
