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
from cihub.utils.java_pom import JAVA_TOOL_PLUGINS, parse_pom_plugins

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


def _has_maven_plugin(workdir: Path, tool: str) -> bool:
    pom_path = workdir / "pom.xml"
    if not pom_path.exists():
        return False
    plugin_id = JAVA_TOOL_PLUGINS.get(tool)
    if not plugin_id:
        return False
    plugins, plugins_mgmt, _, error = parse_pom_plugins(pom_path)
    if error:
        return False
    return plugin_id in plugins or plugin_id in plugins_mgmt


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


def run_pitest(
    workdir: Path,
    output_dir: Path,
    build_tool: str,
    timeout_seconds: int | None = None,
) -> ToolResult:
    log_path = output_dir / "pitest-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["pitest", "--continue", "-Dpitest.outputFormats=XML,HTML"]
    else:
        use_plugin = _has_maven_plugin(workdir, "pitest")
        if use_plugin:
            pitest_goal = "org.pitest:pitest-maven:mutationCoverage"
        else:
            pitest_goal = f"org.pitest:pitest-maven:{DEFAULT_PITEST_VERSION}:mutationCoverage"
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            pitest_goal,
            "-DoutputFormats=XML,HTML",
            "-DfailWhenNoMutations=false",
        ]
    proc = shared._run_tool_command(
        "pitest",
        cmd,
        workdir,
        output_dir,
        timeout=timeout_seconds,
    )
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
        artifacts={
            "report": str(report_paths[0]) if report_paths else "",
            "log": str(log_path),
        },
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_checkstyle(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "checkstyle-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["checkstyleMain", "--continue"]
    else:
        config_path = workdir / "config" / "checkstyle" / "checkstyle.xml"
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "-DskipTests",
            f"-Dcheckstyle.config.location={config_path}" if config_path.exists() else "",
            "checkstyle:checkstyle",
        ]
        cmd = [arg for arg in cmd if arg]
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
        artifacts={
            "report": str(report_paths[0]) if report_paths else "",
            "log": str(log_path),
        },
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
        artifacts={
            "report": str(report_paths[0]) if report_paths else "",
            "log": str(log_path),
        },
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
        artifacts={
            "report": str(report_paths[0]) if report_paths else "",
            "log": str(log_path),
        },
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_owasp(
    workdir: Path,
    output_dir: Path,
    build_tool: str,
    use_nvd_api_key: bool,
    timeout_seconds: int | None = None,
) -> ToolResult:
    log_path = output_dir / "owasp-output.txt"
    output_dir.mkdir(parents=True, exist_ok=True)
    multi_module = False
    if build_tool == "maven":
        from cihub.utils.project import detect_java_project_type

        project_type = detect_java_project_type(workdir)
        multi_module = project_type.startswith("Multi-module")
    data_dir = output_dir / "dependency-check-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    nvd_key = env.get("NVD_API_KEY") if use_nvd_api_key else None
    if not use_nvd_api_key:
        env.pop("NVD_API_KEY", None)
    base_nvd_flags: list[str] = []
    use_nvd_update = bool(nvd_key)
    if nvd_key:
        base_nvd_flags.append(f"-DnvdApiKey={nvd_key}")
    auto_update_flags = ["-DautoUpdate=false"]
    fallback_nvd_flags = [
        "-Danalyzer.nvdcve.enabled=false",
        "-Dupdater.nvdcve.enabled=false",
        "-Danalyzer.cpe.enabled=false",
        "-Danalyzer.npm.cpe.enabled=false",
        "-DossindexAnalyzerEnabled=true",
    ]
    format_flag = "-Dformat=JSON"
    output_dir_flag = f"-DoutputDirectory={output_dir.resolve()}"
    data_dir_flag = f"-DdataDirectory={data_dir.resolve()}"
    def _build_check_cmd(extra_flags: list[str]) -> list[str]:
        if build_tool == "gradle":
            return _gradle_cmd(workdir) + [
                "dependencyCheckAnalyze",
                "--continue",
                format_flag,
                output_dir_flag,
                data_dir_flag,
                "-DfailOnError=false",
                *extra_flags,
            ]
        goal = "aggregate" if multi_module else "check"
        use_plugin = _has_maven_plugin(workdir, "owasp")
        if use_plugin:
            owasp_goal = f"org.owasp:dependency-check-maven:{goal}"
        else:
            owasp_goal = f"org.owasp:dependency-check-maven:{DEFAULT_OWASP_VERSION}:{goal}"
        return _maven_cmd(workdir) + [
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
            *extra_flags,
        ]

    if build_tool == "gradle":
        purge_cmd = _gradle_cmd(workdir) + [
            "dependencyCheckPurge",
            "--continue",
            data_dir_flag,
        ]
    else:
        use_plugin = _has_maven_plugin(workdir, "owasp")
        if use_plugin:
            purge_goal = "org.owasp:dependency-check-maven:purge"
        else:
            purge_goal = f"org.owasp:dependency-check-maven:{DEFAULT_OWASP_VERSION}:purge"
        purge_cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            purge_goal,
            data_dir_flag,
        ]

    def _run_check(check_cmd: list[str]) -> tuple[object, str, str, str, bool]:
        effective_timeout = timeout_seconds or 1800
        if not nvd_key:
            effective_timeout = max(effective_timeout, 3600)
        proc = shared._run_tool_command(
            "owasp",
            check_cmd,
            workdir,
            output_dir,
            env=env,
            timeout=effective_timeout,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        output_text = f"{stdout}\n{stderr}".lower()
        nvd_failed = any(
            marker in output_text
            for marker in (
                "nvd returned a 403",
                "nvd returned a 404",
                "nvd returned a 429",
                "nvd api key is required",
                "nvd api key required",
            )
        )
        return proc, stdout, stderr, output_text, nvd_failed

    def _append_logs(current: str, addition: str) -> str:
        if not addition:
            return current
        return f"{current}\n{addition}" if current else addition

    def _find_report_paths() -> list[Path]:
        report_paths = shared._find_files(
            workdir,
            [
                "dependency-check-report.json",
                "target/dependency-check-report.json",
                "build/reports/dependency-check-report.json",
            ],
        )
        # dependency-check writes to outputDirectory; search there explicitly.
        report_paths.extend(shared._find_files(output_dir, ["dependency-check-report.json"]))
        return report_paths

    cmd = _build_check_cmd(base_nvd_flags)
    proc, stdout, stderr, output_text, nvd_failed = _run_check(cmd)
    log_stdout = _append_logs("", stdout)
    log_stderr = _append_logs("", stderr)
    nvd_access_failed = nvd_failed
    corrupt_db = "incompatible or corrupt database found" in output_text
    purged = False
    if corrupt_db:
        purge_proc = shared._run_tool_command(
            "owasp",
            purge_cmd,
            workdir,
            output_dir,
            env=env,
            timeout=900,
        )
        log_stdout = _append_logs(log_stdout, purge_proc.stdout or "")
        log_stderr = _append_logs(log_stderr, purge_proc.stderr or "")
        purged = True
        proc, stdout, stderr, output_text, nvd_failed = _run_check(cmd)
        log_stdout = _append_logs(log_stdout, stdout)
        log_stderr = _append_logs(log_stderr, stderr)
        nvd_access_failed = nvd_access_failed or nvd_failed
        corrupt_db = "incompatible or corrupt database found" in output_text

    report_paths = _find_report_paths()
    report_found = bool(report_paths)

    if nvd_access_failed and not report_found:
        auto_update_cmd = _build_check_cmd(base_nvd_flags + auto_update_flags)
        proc, stdout, stderr, output_text, nvd_failed = _run_check(auto_update_cmd)
        log_stdout = _append_logs(log_stdout, stdout)
        log_stderr = _append_logs(log_stderr, stderr)
        nvd_access_failed = True
        corrupt_db = "incompatible or corrupt database found" in output_text
        report_paths = _find_report_paths()
        report_found = bool(report_paths)

    if nvd_access_failed and not report_found:
        fallback_cmd = _build_check_cmd(fallback_nvd_flags + auto_update_flags)
        proc, stdout, stderr, output_text, nvd_failed = _run_check(fallback_cmd)
        log_stdout = _append_logs(log_stdout, stdout)
        log_stderr = _append_logs(log_stderr, stderr)
        nvd_access_failed = True
        corrupt_db = "incompatible or corrupt database found" in output_text

    log_path.write_text(log_stdout + log_stderr, encoding="utf-8")

    fatal_errors = (
        "fatal exception(s) analyzing" in output_text
        or "fatal exception" in output_text
        or corrupt_db
    )

    report_paths = _find_report_paths()
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
    metrics["owasp_db_purged"] = purged
    return ToolResult(
        tool="owasp",
        ran=True,
        success=proc.returncode == 0 and report_found and not fatal_errors,
        returncode=proc.returncode,
        metrics=metrics,
        artifacts={
            "report": str(report_paths[0]) if report_paths else "",
            "log": str(log_path),
        },
        stdout=log_stdout,
        stderr=log_stderr,
    )
