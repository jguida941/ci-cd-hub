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

DEFAULT_OWASP_VERSION = "9.0.9"
DEFAULT_PITEST_VERSION = "1.15.3"


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
                "target/site/jacoco-aggregate/jacoco.xml",
                "build/reports/jacoco/test/jacocoTestReport.xml",
            ],
        )
        metrics.update(_parse_jacoco_files(jacoco_paths))

    return ToolResult(
        tool="build",
        ran=True,
        success=proc.returncode == 0,
        returncode=proc.returncode,
        metrics=metrics,
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_maven_install(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "maven-install.log"
    cmd = _maven_cmd(workdir) + [
        "-B",
        "-ntp",
        "-DskipTests",
        "install",
    ]
    proc = shared._run_tool_command("maven-install", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return ToolResult(
        tool="maven-install",
        ran=True,
        success=proc.returncode == 0,
        returncode=proc.returncode,
        metrics={},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_jacoco(workdir: Path, output_dir: Path) -> ToolResult:
    report_paths = shared._find_files(
        workdir,
        [
            "target/site/jacoco/jacoco.xml",
            "target/site/jacoco-aggregate/jacoco.xml",
            "build/reports/jacoco/test/jacocoTestReport.xml",
        ],
    )
    report_found = bool(report_paths)
    metrics = _parse_jacoco_files(report_paths)
    metrics["report_found"] = report_found
    return ToolResult(
        tool="jacoco",
        ran=True,
        success=report_found,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
    )


def run_pitest(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "pitest-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["pitest", "--continue", "-Dpitest.outputFormats=XML,HTML"]
    else:
        pitest_goal = f"org.pitest:pitest-maven:{DEFAULT_PITEST_VERSION}:mutationCoverage"
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            pitest_goal,
            "-DoutputFormats=XML,HTML",
            "-DfailWhenNoMutations=false",
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
    report_found = bool(report_paths)
    metrics = _parse_pitest_files(report_paths)
    metrics["report_found"] = report_found
    return ToolResult(
        tool="pitest",
        ran=True,
        success=proc.returncode == 0 and report_found,
        returncode=proc.returncode,
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
    report_found = bool(report_paths)
    metrics = _parse_checkstyle_files(report_paths)
    metrics["report_found"] = report_found
    return ToolResult(
        tool="checkstyle",
        ran=True,
        success=proc.returncode == 0 and report_found,
        returncode=proc.returncode,
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
    report_found = bool(report_paths)
    metrics = _parse_spotbugs_files(report_paths)
    metrics["report_found"] = report_found
    return ToolResult(
        tool="spotbugs",
        ran=True,
        success=proc.returncode == 0 and report_found,
        returncode=proc.returncode,
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
    report_found = bool(report_paths)
    metrics = _parse_pmd_files(report_paths)
    metrics["report_found"] = report_found
    return ToolResult(
        tool="pmd",
        ran=True,
        success=proc.returncode == 0 and report_found,
        returncode=proc.returncode,
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
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = output_dir / "dependency-check-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    nvd_key = env.get("NVD_API_KEY") if use_nvd_api_key else None
    if not use_nvd_api_key:
        env.pop("NVD_API_KEY", None)
    nvd_flags: list[str] = []
    use_nvd_update = use_nvd_api_key and bool(nvd_key)
    if use_nvd_update:
        nvd_flags.append(f"-DnvdApiKey={nvd_key}")
    else:
        # Missing key: disable updates and use OSS Index to avoid NVD fetches.
        nvd_flags.append("-DautoUpdate=false")
        nvd_flags.append("-DossindexAnalyzerEnabled=true")
    format_flag = "-Dformat=JSON"
    output_dir_flag = f"-DoutputDirectory={output_dir.resolve()}"
    data_dir_flag = f"-DdataDirectory={data_dir.resolve()}"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + [
            "dependencyCheckAnalyze",
            "--continue",
            format_flag,
            output_dir_flag,
            data_dir_flag,
            "-DfailOnError=false",
            *nvd_flags,
        ]
    else:
        owasp_goal = f"org.owasp:dependency-check-maven:{DEFAULT_OWASP_VERSION}:check"
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            owasp_goal,
            "-DfailBuildOnCVSS=11",
            "-DnvdApiDelay=2500",
            "-DnvdMaxRetryCount=10",
            "-Ddependencycheck.failOnError=false",
            "-DfailOnError=false",
            format_flag,
            output_dir_flag,
            data_dir_flag,
            *nvd_flags,
        ]
    proc = shared._run_tool_command("owasp", cmd, workdir, output_dir, env=env, timeout=1800)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    output_text = f"{proc.stdout}\n{proc.stderr}".lower()
    nvd_access_failed = "nvd returned a 403" in output_text or "nvd returned a 404" in output_text
    fatal_errors = "fatal exception(s) analyzing" in output_text or "fatal exception" in output_text

    report_paths = shared._find_files(
        workdir,
        [
            "dependency-check-report.json",
            "target/dependency-check-report.json",
            "build/reports/dependency-check-report.json",
        ],
    )
    report_found = bool(report_paths)
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
    metrics["report_found"] = report_found
    metrics["owasp_data_missing"] = nvd_access_failed
    metrics["owasp_fatal_errors"] = fatal_errors
    return ToolResult(
        tool="owasp",
        ran=True,
        success=proc.returncode == 0 and report_found and not fatal_errors,
        returncode=proc.returncode,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
