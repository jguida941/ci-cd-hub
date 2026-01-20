"""Python tool runners."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import shared
from .base import ToolResult
from .parsers import _parse_coverage, _parse_junit


def _qt_dependency_present(workdir: Path) -> bool:
    for filename in ("pyproject.toml", "requirements.txt", "requirements-dev.txt"):
        path = workdir / filename
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if "pyside" in content or "pyqt" in content:
            return True
    return False


def _should_use_xvfb(workdir: Path, env: dict[str, str]) -> bool:
    if not sys.platform.startswith("linux"):
        return False
    if env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"):
        return False
    return _qt_dependency_present(workdir)


def _pytest_marker_declared(workdir: Path, marker: str) -> bool:
    marker_value = marker.lower()
    for filename in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"):
        path = workdir / filename
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if "markers" in content and marker_value in content:
            return True
    return False


def _args_have_marker_expression(args: list[str]) -> bool:
    for arg in args:
        if arg == "-m" or arg.startswith("-m=") or arg.startswith("--markers"):
            return True
    return False


def run_pytest(
    workdir: Path,
    output_dir: Path,
    fail_fast: bool = False,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> ToolResult:
    junit_path = output_dir / "pytest-junit.xml"
    coverage_path = output_dir / "coverage.xml"
    pytest_cmd = [
        "pytest",
        "--cov=.",
        f"--cov-report=xml:{coverage_path}",
        f"--junitxml={junit_path}",
        "-v",
    ]
    pytest_args = list(args) if args else []
    if fail_fast:
        pytest_args.append("-x")

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    use_xvfb = _should_use_xvfb(workdir, merged_env)
    if use_xvfb:
        if _pytest_marker_declared(workdir, "qprocess") and not _args_have_marker_expression(pytest_args):
            pytest_args.extend(["-m", "not qprocess"])

    if use_xvfb:
        merged_env.setdefault("QT_QPA_PLATFORM", "offscreen")
        merged_env.setdefault("QT_OPENGL", "software")
        merged_env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
        merged_env.setdefault("QT_XCB_GL_INTEGRATION", "none")
        merged_env.setdefault("QSG_RHI_BACKEND", "software")
        merged_env.setdefault("QT_QUICK_BACKEND", "software")
        runtime_dir = merged_env.setdefault("XDG_RUNTIME_DIR", "/tmp/xdg-runtime")
        try:
            Path(runtime_dir).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    if pytest_args:
        pytest_cmd.extend([str(arg) for arg in pytest_args if str(arg)])

    cmd = pytest_cmd
    if use_xvfb:
        xvfb_bin = shutil.which("xvfb-run")
        if xvfb_bin:
            cmd = [xvfb_bin, "-a"] + pytest_cmd

    proc = shared._run_tool_command("pytest", cmd, workdir, output_dir, env=merged_env)
    if use_xvfb and proc.returncode == 124:
        for path in (junit_path, coverage_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        proc = shared._run_tool_command("pytest", pytest_cmd, workdir, output_dir, env=merged_env)
    metrics = {}
    metrics.update(_parse_junit(junit_path))
    metrics.update(_parse_coverage(coverage_path))
    return ToolResult(
        tool="pytest",
        ran=True,
        success=proc.returncode == 0,
        metrics=metrics,
        artifacts={
            "junit": str(junit_path),
            "coverage": str(coverage_path),
        },
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_ruff(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "ruff-report.json"
    # Exclude hub/ directory which contains the cihub checkout during CI
    cmd = ["ruff", "check", ".", "--output-format", "json", "--extend-exclude", "hub"]
    proc = shared._run_tool_command("ruff", cmd, workdir, output_dir)
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")
    data = shared._parse_json(report_path)
    parse_ok = data is not None
    errors = len(data) if isinstance(data, list) else 0
    security = 0
    if isinstance(data, list):
        security = sum(1 for item in data if str(item.get("code", "")).startswith("S"))
    return ToolResult(
        tool="ruff",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "ruff_errors": errors,
            "ruff_security": security,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_black(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "black-output.txt"
    cmd = ["black", "--check", "."]
    proc = shared._run_tool_command("black", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    issues = len(re.findall(r"would reformat", proc.stdout + proc.stderr))
    return ToolResult(
        tool="black",
        ran=True,
        success=proc.returncode == 0,
        metrics={"black_issues": issues},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_isort(workdir: Path, output_dir: Path, use_black_profile: bool = True) -> ToolResult:
    log_path = output_dir / "isort-output.txt"
    cmd = ["isort"]
    if use_black_profile:
        cmd.extend(["--profile", "black"])
    cmd.extend(["--check-only", "--diff", "."])
    proc = shared._run_tool_command("isort", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    issues = len(re.findall(r"^ERROR:", proc.stdout, flags=re.MULTILINE))
    return ToolResult(
        tool="isort",
        ran=True,
        success=proc.returncode == 0,
        metrics={"isort_issues": issues},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_mypy(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "mypy-output.txt"
    cmd = ["mypy", ".", "--ignore-missing-imports"]
    proc = shared._run_tool_command("mypy", cmd, workdir, output_dir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    errors = len(re.findall(r"\berror:", proc.stdout))
    return ToolResult(
        tool="mypy",
        ran=True,
        success=proc.returncode == 0,
        metrics={"mypy_errors": errors},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_bandit(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "bandit-report.json"
    cmd = ["bandit", "-r", ".", "-f", "json", "-o", str(report_path)]
    proc = shared._run_tool_command("bandit", cmd, workdir, output_dir)
    data = shared._parse_json(report_path)
    parse_ok = data is not None
    results = data.get("results", []) if isinstance(data, dict) else []
    high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
    medium = sum(1 for item in results if item.get("issue_severity") == "MEDIUM")
    low = sum(1 for item in results if item.get("issue_severity") == "LOW")
    return ToolResult(
        tool="bandit",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "bandit_high": high,
            "bandit_medium": medium,
            "bandit_low": low,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _count_pip_audit_vulns(data: Any) -> int:
    if isinstance(data, list):
        total = 0
        for item in data:
            vulns = item.get("vulns") or item.get("vulnerabilities") or []
            total += len(vulns)
        return total
    return 0


def run_pip_audit(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "pip-audit-report.json"
    cmd = ["pip-audit", "--format=json", "--output", str(report_path)]
    proc = shared._run_tool_command("pip_audit", cmd, workdir, output_dir)
    data = shared._parse_json(report_path)
    parse_ok = data is not None
    vulns = _count_pip_audit_vulns(data)
    return ToolResult(
        tool="pip_audit",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={"pip_audit_vulns": vulns, "parse_error": not parse_ok},
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _detect_mutmut_paths(workdir: Path) -> str:
    src_dir = workdir / "src"
    if src_dir.exists():
        return "src/"
    for entry in workdir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name in {"tests", "test", "venv", ".venv", "build", "dist"}:
            continue
        if (entry / "__init__.py").exists():
            return f"{entry.name}/"
    for entry in workdir.iterdir():
        if not entry.is_file() or entry.suffix != ".py":
            continue
        if entry.name in {"setup.py", "__init__.py", "conftest.py"}:
            continue
        if entry.name.startswith("test_") or entry.name.endswith("_test.py"):
            continue
        return entry.name
    return "."


def _ensure_mutmut_config(workdir: Path) -> tuple[Path | None, str | None]:
    pyproject = workdir / "pyproject.toml"
    if pyproject.exists() and "[tool.mutmut]" in pyproject.read_text(encoding="utf-8"):
        return None, None
    setup_cfg = workdir / "setup.cfg"
    if setup_cfg.exists() and "[mutmut]" in setup_cfg.read_text(encoding="utf-8"):
        return None, None

    mutate_path = _detect_mutmut_paths(workdir)
    snippet = f"\n[mutmut]\npaths_to_mutate={mutate_path}\n"
    if setup_cfg.exists():
        original_text = setup_cfg.read_text(encoding="utf-8")
        setup_cfg.write_text(original_text + snippet, encoding="utf-8")
    else:
        original_text = None
        setup_cfg.write_text(snippet.lstrip(), encoding="utf-8")
    return setup_cfg, original_text


def run_mutmut(workdir: Path, output_dir: Path, timeout_seconds: int) -> ToolResult:
    log_path = output_dir / "mutmut-run.log"
    config_path, original = _ensure_mutmut_config(workdir)
    proc = None
    try:
        proc = shared._run_tool_command(
            "mutmut",
            ["mutmut", "run"],
            workdir,
            output_dir,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout
        if isinstance(stdout, bytes):
            stdout_text = stdout.decode("utf-8", errors="replace")
        else:
            stdout_text = stdout or ""
        log_path.write_text(stdout_text, encoding="utf-8")
        return ToolResult(
            tool="mutmut",
            ran=True,
            success=False,
            metrics={"mutation_score": 0, "mutation_killed": 0, "mutation_survived": 0},
            artifacts={"log": str(log_path)},
        )
    try:
        log_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
        results_proc = shared._run_command(["mutmut", "results"], workdir)
        results_text = (results_proc.stdout or "") + (results_proc.stderr or "")
        killed = len(re.findall(r"\bkilled\b", results_text, flags=re.IGNORECASE))
        survived = len(re.findall(r"\bsurvived\b", results_text, flags=re.IGNORECASE))
        total = killed + survived
        if total == 0:
            meta_killed, meta_survived = _parse_mutmut_meta(workdir / "mutants")
            if meta_killed or meta_survived:
                killed = meta_killed
                survived = meta_survived
                total = killed + survived
        score = int(round((killed / total) * 100)) if total > 0 else 0
        return ToolResult(
            tool="mutmut",
            ran=True,
            success=proc.returncode == 0,
            metrics={
                "mutation_score": score,
                "mutation_killed": killed,
                "mutation_survived": survived,
            },
            artifacts={"log": str(log_path)},
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    finally:
        if config_path:
            if original is None:
                config_path.unlink(missing_ok=True)
            else:
                config_path.write_text(original, encoding="utf-8")


def _parse_mutmut_meta(mutants_dir: Path) -> tuple[int, int]:
    killed = 0
    survived = 0
    if not mutants_dir.exists():
        return killed, survived
    for meta_path in mutants_dir.rglob("*.meta"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        exit_codes = data.get("exit_code_by_key", {})
        if not isinstance(exit_codes, dict):
            continue
        for code in exit_codes.values():
            if code == 1:
                killed += 1
            elif code == 0:
                survived += 1
    return killed, survived
