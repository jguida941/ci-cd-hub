"""Release, tooling install, and summary commands."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import stat
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET  # Secure XML parsing

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.env import env_int, resolve_flag
from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.github_context import OutputContext
from cihub.utils.progress import _bar

from . import (
    EMPTY_SARIF,
    _append_github_path,
    _download_file,
    _extract_tarball_member,
    _run_command,
    _sha256,
)


def _get_platform_suffix() -> str:
    """Get platform suffix for release downloads (actionlint/kyverno).

    Returns:
        Platform suffix like 'linux_amd64', 'darwin_arm64', etc.
        Falls back to 'linux_amd64' for CI compatibility.
    """
    sys_name = platform.system().lower()
    machine = platform.machine().lower()

    # Map OS names
    os_name = {"darwin": "darwin", "linux": "linux", "windows": "windows"}.get(sys_name, "linux")

    # Map architectures (actionlint uses amd64, kyverno uses x86_64)
    arch = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, "amd64")

    return f"{os_name}_{arch}"


def _get_kyverno_platform_suffix() -> str:
    """Get platform suffix for kyverno downloads.

    Kyverno uses x86_64 instead of amd64 for architecture naming.
    """
    sys_name = platform.system().lower()
    machine = platform.machine().lower()

    os_name = {"darwin": "darwin", "linux": "linux", "windows": "windows"}.get(sys_name, "linux")

    # Kyverno uses x86_64 instead of amd64
    arch = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, "x86_64")

    return f"{os_name}_{arch}"


def _resolve_actionlint_version(version: str) -> str:
    if version != "latest":
        return version.lstrip("v")
    url = "https://api.github.com/repos/rhysd/actionlint/releases/latest"
    try:
        import urllib.request

        request = urllib.request.Request(url, headers={"User-Agent": "cihub"})  # noqa: S310
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to resolve latest actionlint version: {exc}") from exc
    tag = str(data.get("tag_name", "")).strip()
    if not tag:
        raise RuntimeError("Failed to resolve latest actionlint version")
    return tag.lstrip("v")


def _extract_zip_member(zip_path: Path, member_name: str, dest_dir: Path) -> Path:
    """Extract a single member from a zip archive with path traversal protection."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    resolved_dest = dest_dir.resolve()
    extracted = (dest_dir / member_name).resolve()
    try:
        extracted.relative_to(resolved_dest)
    except ValueError:
        raise ValueError(f"Path traversal detected in zip: {member_name}") from None

    with zipfile.ZipFile(zip_path, "r") as archive:
        try:
            info = archive.getinfo(member_name)
        except KeyError as exc:
            raise KeyError(f"{member_name} not found in zip archive") from exc
        if info.is_dir():
            raise ValueError(f"Zip member is a directory: {member_name}")
        with archive.open(info) as src, extracted.open("wb") as dst:
            shutil.copyfileobj(src, dst)

    extracted.chmod(extracted.stat().st_mode | stat.S_IEXEC)
    return extracted


def cmd_actionlint_install(args: argparse.Namespace) -> CommandResult:
    try:
        version = _resolve_actionlint_version(args.version)
    except RuntimeError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"actionlint-install: {exc}",
            problems=[{"severity": "error", "message": str(exc)}],
        )
    platform_suffix = _get_platform_suffix()
    tar_name = f"actionlint_{version}_{platform_suffix}.tar.gz"
    url = f"https://github.com/rhysd/actionlint/releases/download/v{version}/{tar_name}"
    dest_dir = Path(args.dest).resolve()
    tar_path = dest_dir / tar_name

    try:
        _download_file(url, tar_path)
    except OSError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"actionlint-install: download failed - {exc}",
            problems=[{"severity": "error", "message": f"Failed to download actionlint: {exc}"}],
        )

    if args.checksum:
        actual = _sha256(tar_path)
        if actual.lower() != args.checksum.lower():
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="actionlint-install: checksum mismatch",
                problems=[{"severity": "error", "message": "actionlint checksum mismatch"}],
                data={"expected": args.checksum, "actual": actual},
            )

    try:
        bin_path = _extract_tarball_member(tar_path, "actionlint", dest_dir)
    except (OSError, tarfile.TarError, KeyError) as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"actionlint-install: extraction failed - {exc}",
            problems=[{"severity": "error", "message": f"Failed to extract actionlint: {exc}"}],
        )
    finally:
        try:
            tar_path.unlink()
        except OSError:
            pass

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"path": str(bin_path)})
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"actionlint installed at {bin_path}",
        data={"path": str(bin_path), "version": version},
    )


def cmd_actionlint(args: argparse.Namespace) -> CommandResult:
    # Resolve bin with env var fallback (ACTIONLINT_BIN), then system PATH
    bin_path = resolve_flag(getattr(args, "bin", None), "ACTIONLINT_BIN")
    if not bin_path:
        bin_path = shutil.which("actionlint") or ""
    if not bin_path:
        local = Path("actionlint")
        if local.exists():
            bin_path = str(local.resolve())
    if not bin_path:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="actionlint: binary not found",
            problems=[{"severity": "error", "message": "actionlint binary not found (install first)"}],
        )

    try:
        proc = safe_run(
            [bin_path, "-oneline", args.workflow],
            timeout=TIMEOUT_NETWORK,  # 2 min for actionlint
        )
    except CommandNotFoundError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="actionlint: binary not found",
            problems=[{"severity": "error", "message": "actionlint binary not found"}],
        )
    except CommandTimeoutError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="actionlint: timed out",
            problems=[{"severity": "error", "message": "actionlint timed out"}],
        )
    output_lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]

    if args.reviewdog:
        if not shutil.which("reviewdog"):
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="actionlint: reviewdog not found",
                problems=[{"severity": "error", "message": "reviewdog not found (install reviewdog/action-setup)"}],
            )
        input_text = "\n".join(f"e:{line}" for line in output_lines)
        if input_text:
            input_text += "\n"
        reviewdog_cmd = [  # noqa: S607 - reviewdog is installed in CI
            "reviewdog",
            "-efm=%t:%f:%l:%c: %m",
            "-name=actionlint",
            "-reporter=github-check",
            "-level=error",
            "-fail-level=error",
        ]
        try:
            reviewdog_proc = safe_run(
                reviewdog_cmd,
                input=input_text,
                timeout=TIMEOUT_NETWORK,
                capture_output=False,  # Let reviewdog output go to terminal
            )
        except (CommandNotFoundError, CommandTimeoutError):
            reviewdog_proc = type("", (), {"returncode": 1})()  # Create mock failed result
        if proc.returncode != 0 and not output_lines:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="actionlint: failed",
                problems=[{"severity": "error", "message": proc.stderr or "actionlint failed"}],
            )
        success = reviewdog_proc.returncode == 0
        return CommandResult(
            exit_code=EXIT_SUCCESS if success else EXIT_FAILURE,
            summary=f"actionlint: {'passed' if success else 'failed'} (reviewdog)",
            data={"issues": len(output_lines), "reviewdog": True},
        )

    success = proc.returncode == 0
    return CommandResult(
        exit_code=EXIT_SUCCESS if success else EXIT_FAILURE,
        summary=f"actionlint: {len(output_lines)} issues found" if output_lines else "actionlint: passed",
        data={"issues": len(output_lines), "output": proc.stdout},
    )


def cmd_kyverno_install(args: argparse.Namespace) -> CommandResult:
    version = args.version
    if not version.startswith("v"):
        version = f"v{version}"
    platform_suffix = _get_kyverno_platform_suffix()
    tar_name = f"kyverno-cli_{version}_{platform_suffix}.tar.gz"
    url = f"https://github.com/kyverno/kyverno/releases/download/{version}/{tar_name}"
    dest_dir = Path(args.dest).resolve()
    tar_path = dest_dir / tar_name

    try:
        _download_file(url, tar_path)
    except OSError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"kyverno-install: download failed - {exc}",
            problems=[{"severity": "error", "message": f"Failed to download kyverno: {exc}"}],
        )

    try:
        bin_path = _extract_tarball_member(tar_path, "kyverno", dest_dir)
    except (OSError, tarfile.TarError, KeyError) as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"kyverno-install: extraction failed - {exc}",
            problems=[{"severity": "error", "message": f"Failed to extract kyverno: {exc}"}],
        )
    finally:
        try:
            tar_path.unlink()
        except OSError:
            pass

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"path": str(bin_path)})
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"kyverno installed at {bin_path}",
        data={"path": str(bin_path), "version": version},
    )


def _trivy_asset_name(version: str) -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "linux":
        if machine in {"x86_64", "amd64"}:
            suffix = "Linux-64bit"
        elif machine in {"aarch64", "arm64"}:
            suffix = "Linux-ARM64"
        else:
            raise ValueError(f"Unsupported Linux architecture: {machine}")
        ext = "tar.gz"
    elif system == "darwin":
        if machine in {"x86_64", "amd64"}:
            suffix = "macOS-64bit"
        elif machine in {"arm64", "aarch64"}:
            suffix = "macOS-ARM64"
        else:
            raise ValueError(f"Unsupported macOS architecture: {machine}")
        ext = "tar.gz"
    elif system == "windows":
        if machine in {"x86_64", "amd64"}:
            suffix = "Windows-64bit"
        elif machine in {"arm64", "aarch64"}:
            suffix = "Windows-ARM64"
        else:
            raise ValueError(f"Unsupported Windows architecture: {machine}")
        ext = "zip"
    else:
        raise ValueError(f"Unsupported platform: {system}")
    return f"trivy_{version}_{suffix}.{ext}"


def cmd_trivy_install(args: argparse.Namespace) -> CommandResult:
    version = args.version.lstrip("v")
    try:
        asset_name = _trivy_asset_name(version)
    except ValueError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"trivy-install: {exc}",
            problems=[{"severity": "error", "message": f"Failed to resolve trivy asset: {exc}"}],
        )

    url = f"https://github.com/aquasecurity/trivy/releases/download/v{version}/{asset_name}"
    dest_dir = Path(args.dest).resolve()
    asset_path = dest_dir / asset_name

    try:
        _download_file(url, asset_path)
    except OSError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"trivy-install: download failed - {exc}",
            problems=[{"severity": "error", "message": f"Failed to download trivy: {exc}"}],
        )

    try:
        if asset_name.endswith(".zip"):
            try:
                bin_path = _extract_zip_member(asset_path, "trivy.exe", dest_dir)
            except KeyError:
                bin_path = _extract_zip_member(asset_path, "trivy", dest_dir)
        else:
            bin_path = _extract_tarball_member(asset_path, "trivy", dest_dir)
    except (OSError, tarfile.TarError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"trivy-install: extraction failed - {exc}",
            problems=[{"severity": "error", "message": f"Failed to extract trivy: {exc}"}],
        )
    finally:
        try:
            asset_path.unlink()
        except OSError:
            pass

    if args.github_path:
        _append_github_path(dest_dir)

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"path": str(bin_path)})
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"trivy installed at {bin_path}",
        data={"path": str(bin_path), "version": version},
    )


def cmd_trivy_summary(args: argparse.Namespace) -> CommandResult:
    """Parse Trivy JSON output and generate summary with counts.

    Reads both filesystem scan (vulnerabilities) and config scan (misconfigurations)
    JSON files, counts findings by severity, outputs to GITHUB_OUTPUT and GITHUB_STEP_SUMMARY.
    """
    fs_json = Path(args.fs_json) if args.fs_json else None
    config_json = Path(args.config_json) if args.config_json else None
    problems: list[dict[str, str]] = []

    # Parse filesystem scan results (vulnerabilities)
    fs_critical = 0
    fs_high = 0
    if fs_json and fs_json.exists():
        try:
            with fs_json.open(encoding="utf-8") as f:
                data = json.load(f)
            for result in data.get("Results", []):
                for vuln in result.get("Vulnerabilities", []):
                    severity = vuln.get("Severity", "").upper()
                    if severity == "CRITICAL":
                        fs_critical += 1
                    elif severity == "HIGH":
                        fs_high += 1
        except (json.JSONDecodeError, KeyError) as e:
            problems.append({"severity": "warning", "message": f"Failed to parse {fs_json}: {e}"})

    # Parse config scan results (misconfigurations)
    config_critical = 0
    config_high = 0
    if config_json and config_json.exists():
        try:
            with config_json.open(encoding="utf-8") as f:
                data = json.load(f)
            for result in data.get("Results", []):
                for misconfig in result.get("Misconfigurations", []):
                    severity = misconfig.get("Severity", "").upper()
                    if severity == "CRITICAL":
                        config_critical += 1
                    elif severity == "HIGH":
                        config_high += 1
        except (json.JSONDecodeError, KeyError) as e:
            problems.append({"severity": "warning", "message": f"Failed to parse {config_json}: {e}"})

    # Calculate totals
    total_critical = fs_critical + config_critical
    total_high = fs_high + config_high

    # Write to GITHUB_OUTPUT/SUMMARY if requested
    ctx = OutputContext.from_args(args)
    if args.github_output:
        outputs = {
            "fs_critical": str(fs_critical),
            "fs_high": str(fs_high),
            "config_critical": str(config_critical),
            "config_high": str(config_high),
            "total_critical": str(total_critical),
            "total_high": str(total_high),
        }
        ctx.write_outputs(outputs)

    if args.github_summary:
        summary_lines = [
            "### Trivy Findings Summary",
            "",
            "| Scan Type | Critical | High |",
            "|-----------|----------|------|",
            f"| Filesystem (vulns) | {fs_critical} | {fs_high} |",
            f"| Config (misconfigs) | {config_critical} | {config_high} |",
            f"| **Total** | **{total_critical}** | **{total_high}** |",
        ]
        ctx.write_summary("\n".join(summary_lines))

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Trivy Summary: {total_critical} critical, {total_high} high",
        problems=problems,
        data={
            "fs_critical": fs_critical,
            "fs_high": fs_high,
            "config_critical": config_critical,
            "config_high": config_high,
            "total_critical": total_critical,
            "total_high": total_high,
        },
    )


def _iter_yaml_files(path: Path) -> list[Path]:
    return sorted([*path.glob("*.yaml"), *path.glob("*.yml")])


def _kyverno_apply(policy: Path, resource: Path, bin_path: str | None = None) -> str:
    cmd = [bin_path or "kyverno", "apply", str(policy), "--resource", str(resource)]
    proc = _run_command(cmd, policy.parent)
    return (proc.stdout or "") + (proc.stderr or "")


def cmd_kyverno_validate(args: argparse.Namespace) -> CommandResult:
    policies_dir = Path(args.policies_dir)
    templates_dir = Path(args.templates_dir) if args.templates_dir else None
    # Resolve bin with env var fallback (KYVERNO_BIN)
    bin_path = resolve_flag(getattr(args, "bin", None), "KYVERNO_BIN", default="kyverno")

    failed = 0
    validated = 0
    problems: list[dict[str, str]] = []

    if not policies_dir.exists():
        problems.append({"severity": "warning", "message": f"Policies directory '{policies_dir}' not found"})
        ctx = OutputContext.from_args(args)
        ctx.write_outputs({"validated": "0", "failed": "0"})
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="kyverno-validate: no policies found",
            problems=problems,
            data={"validated": 0, "failed": 0},
        )

    for policy in _iter_yaml_files(policies_dir):
        output = _kyverno_apply(policy, Path(os.devnull), bin_path)
        lowered = output.lower()
        if "error" in lowered or "invalid" in lowered or "failed" in lowered:
            failed += 1
            problems.append({"severity": "error", "message": f"Policy {policy} failed validation"})
        else:
            validated += 1

    if templates_dir and templates_dir.exists():
        for template in _iter_yaml_files(templates_dir):
            output = _kyverno_apply(template, Path(os.devnull), bin_path)
            lowered = output.lower()
            if "error" in lowered or "invalid" in lowered or "failed" in lowered:
                failed += 1
                problems.append({"severity": "error", "message": f"Template {template} failed validation"})
            else:
                validated += 1

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"validated": str(validated), "failed": str(failed)})

    success = failed == 0
    return CommandResult(
        exit_code=EXIT_SUCCESS if success else EXIT_FAILURE,
        summary=f"kyverno-validate: {validated} passed, {failed} failed",
        problems=problems,
        data={"validated": validated, "failed": failed},
    )


def cmd_kyverno_test(args: argparse.Namespace) -> CommandResult:
    policies_dir = Path(args.policies_dir)
    fixtures_dir = Path(args.fixtures_dir)
    fail_on_warn = str(args.fail_on_warn).strip().lower() in {"true", "1", "yes", "y", "on"}
    # Resolve bin with env var fallback (KYVERNO_BIN)
    bin_path = resolve_flag(getattr(args, "bin", None), "KYVERNO_BIN", default="kyverno")
    problems: list[dict[str, str]] = []
    test_results: list[dict[str, str]] = []

    if not fixtures_dir.exists():
        problems.append({"severity": "warning", "message": f"Fixtures directory '{fixtures_dir}' not found"})
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="kyverno-test: skipped (no fixtures)",
            problems=problems,
            data={"tested": 0},
        )

    for policy in _iter_yaml_files(policies_dir):
        policy_name = policy.stem
        for fixture in _iter_yaml_files(fixtures_dir):
            fixture_name = fixture.name
            result = _kyverno_apply(policy, fixture, bin_path)
            if "pass: 1" in result:
                status = "PASS"
            elif "fail: 1" in result:
                status = "FAIL (policy enforced)"
            elif "warn: 1" in result:
                status = "WARN"
                if fail_on_warn:
                    problems.append(
                        {
                            "severity": "warning",
                            "message": f"Policy {policy_name} warned on {fixture_name}",
                        }
                    )
            else:
                status = "SKIP (not applicable)"
            test_results.append({"policy": policy_name, "fixture": fixture_name, "status": status})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"kyverno-test: {len(test_results)} tests executed",
        problems=problems,
        data={"tested": len(test_results), "results": test_results},
    )


def cmd_release_parse_tag(args: argparse.Namespace) -> CommandResult:
    ctx_env = OutputContext.from_env()
    ref = args.ref or ctx_env.ref or ""
    if not ref.startswith("refs/tags/"):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="release-parse-tag: GITHUB_REF is not a tag ref",
            problems=[{"severity": "error", "message": "GITHUB_REF is not a tag ref"}],
        )
    version = ref.replace("refs/tags/", "", 1)
    major = version.split(".")[0]
    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"version": version, "major": major})
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Release version: {version} (major: {major})",
        data={"version": version, "major": major},
    )


def cmd_release_update_tag(args: argparse.Namespace) -> CommandResult:
    root = Path(args.repo).resolve()
    major = args.major
    remote = args.remote
    problems: list[dict[str, str]] = []

    def run_git(cmd_args: list[str], allow_fail: bool = False) -> bool:
        proc = _run_command(["git", *cmd_args], root)
        if proc.returncode != 0 and not allow_fail:
            message = (proc.stdout or proc.stderr or "").strip()
            if message:
                problems.append({"severity": "error", "message": message})
            return False
        return True

    run_git(["tag", "-d", major], allow_fail=True)
    if not run_git(["tag", major]):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"release-update-tag: failed to create tag {major}",
            problems=problems,
        )
    if not run_git(["push", "-f", remote, major]):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"release-update-tag: failed to push tag {major}",
            problems=problems,
        )
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Floating tag {major} now points to {args.version}",
        data={"major": major, "version": args.version, "remote": remote},
    )


def cmd_zizmor_run(args: argparse.Namespace) -> CommandResult:
    """Run zizmor and produce SARIF output, with fallback on failure.

    This replaces the inline heredoc in hub-production-ci.yml to satisfy
    the no-inline policy.
    """
    workflows_path = getattr(args, "workflows", ".github/workflows/")
    output_path = Path(args.output)
    problems: list[dict[str, str]] = []

    # Run zizmor
    cmd = ["zizmor", "--format", "sarif", workflows_path]
    try:
        result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
        if result.returncode == 0:
            # Success - write the SARIF output
            output_path.write_text(result.stdout, encoding="utf-8")
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"zizmor completed, SARIF written to {output_path}",
                data={"sarif_path": str(output_path)},
            )
        else:
            # Non-zero exit - preserve SARIF if stdout is valid; otherwise write empty.
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and "runs" in payload:
                output_path.write_text(result.stdout, encoding="utf-8")
                problems.append({"severity": "warning", "message": "zizmor returned non-zero, SARIF preserved"})
            else:
                output_path.write_text(EMPTY_SARIF, encoding="utf-8")
                problems.append({"severity": "warning", "message": "zizmor returned non-zero, empty SARIF written"})
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"zizmor completed with warnings, SARIF at {output_path}",
                problems=problems,
                data={"sarif_path": str(output_path)},
            )
    except CommandNotFoundError:
        # zizmor not installed
        output_path.write_text(EMPTY_SARIF, encoding="utf-8")
        problems.append({"severity": "warning", "message": "zizmor not found, empty SARIF written"})
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="zizmor not found, empty SARIF written",
            problems=problems,
            data={"sarif_path": str(output_path)},
        )
    except CommandTimeoutError:
        # zizmor timed out
        output_path.write_text(EMPTY_SARIF, encoding="utf-8")
        problems.append({"severity": "warning", "message": "zizmor timed out, empty SARIF written"})
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="zizmor timed out, empty SARIF written",
            problems=problems,
            data={"sarif_path": str(output_path)},
        )


def cmd_zizmor_check(args: argparse.Namespace) -> CommandResult:
    sarif_path = Path(args.sarif)
    if not sarif_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"zizmor-check: SARIF file not found: {sarif_path}",
            problems=[{"severity": "error", "message": f"SARIF file not found: {sarif_path}"}],
        )

    findings: list[dict[str, Any]] = []
    problems: list[dict[str, Any]] = []
    try:
        with sarif_path.open(encoding="utf-8") as f:
            sarif = json.load(f)
        runs = sarif.get("runs", []) if isinstance(sarif, dict) else []
        if runs:
            results = runs[0].get("results", []) or []
            for r in results:
                # Include all findings - level may be unknown/error/warning/note
                rule_id = r.get("ruleId", "unknown")
                loc = r.get("locations", [{}])[0].get("physicalLocation", {})
                artifact = loc.get("artifactLocation", {}).get("uri", "unknown")
                line = loc.get("region", {}).get("startLine", 0)
                message = r.get("message", {}).get("text", "")
                level = r.get("level", "warning")
                # Skip "note" level as they are informational
                if level == "note":
                    continue

                findings.append(
                    {
                        "rule": rule_id,
                        "file": artifact,
                        "line": line,
                        "level": level,
                        "message": message,
                    }
                )
                problems.append(
                    {
                        "severity": "error" if level in ("error", "unknown") else "warning",
                        "message": f"{rule_id}: {artifact}:{line}",
                        "code": rule_id.replace("/", "-").upper(),
                        "file": artifact,
                        "line": line,
                    }
                )
    except json.JSONDecodeError:
        pass

    # Group findings by rule for summary
    by_rule: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        rule = finding["rule"]
        if rule not in by_rule:
            by_rule[rule] = []
        by_rule[rule].append(finding)

    # Build summary
    summary_lines = ["## Zizmor Workflow Security", f"Total findings: {len(findings)}", ""]
    if by_rule:
        summary_lines.append("### Findings by Rule")
        for rule, items in sorted(by_rule.items()):
            summary_lines.append(f"**{rule}** ({len(items)})")
            # Show unique file:line combinations
            seen: set[str] = set()
            for item in items:
                key = f"{item['file']}:{item['line']}"
                if key not in seen:
                    summary_lines.append(f"  - {key}")
                    seen.add(key)
            summary_lines.append("")

    ctx = OutputContext.from_args(args)
    ctx.write_summary("\n".join(summary_lines))

    if findings:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"zizmor-check: {len(findings)} workflow security findings",
            problems=problems,
            data={"findings": len(findings), "by_rule": {k: len(v) for k, v in by_rule.items()}},
        )
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="zizmor-check: no findings",
        data={"findings": 0},
    )


def cmd_license_check(args: argparse.Namespace) -> CommandResult:
    problems: list[dict[str, str]] = []
    try:
        proc = _run_command(["pip-licenses", "--format=csv"], Path("."))
    except FileNotFoundError:
        # pip-licenses is a dev-time dependency; don't fail CIHub if it's missing locally.
        ctx = OutputContext.from_args(args)
        ctx.write_summary("## License Check\nSKIPPED - pip-licenses not installed\n")
        problems.append({"severity": "warning", "message": "pip-licenses not found; skipping license check"})
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="license-check: skipped (pip-licenses not found)",
            problems=problems,
        )
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    total = len(lines)
    copyleft = len([line for line in lines if re.search(r"GPL|AGPL", line, re.I)])

    ctx = OutputContext.from_args(args)
    summary = "## License Check\n"
    summary += f"Total packages: {total}\n"
    summary += f"Copyleft (GPL/AGPL): {copyleft}\n"
    if copyleft > 0:
        summary += "\nCopyleft packages (dev dependencies are acceptable):\n"
        summary += "\n".join([line for line in lines if re.search(r"GPL|AGPL", line, re.I)])
        summary += "\n"
        ctx.write_summary(summary)
        problems.append({"severity": "warning", "message": f"Found {copyleft} packages with copyleft licenses"})
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"license-check: {copyleft} copyleft packages",
            problems=problems,
            data={"total": total, "copyleft": copyleft},
        )

    summary += "PASS - no copyleft licenses\n"
    ctx.write_summary(summary)
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="license-check: passed (no copyleft)",
        data={"total": total, "copyleft": 0},
    )


def cmd_gitleaks_summary(args: argparse.Namespace) -> CommandResult:
    repo_root = Path(".")
    commits = _run_command(["git", "rev-list", "--count", "HEAD"], repo_root).stdout
    files = _run_command(["git", "ls-files"], repo_root).stdout
    commits_count = commits.strip() if commits else "0"
    files_count = str(len(files.splitlines())) if files else "0"
    outcome = args.outcome or os.environ.get("GITLEAKS_OUTCOME", "skipped")
    leak_text = "0" if outcome == "success" else "CHECK LOGS"
    result_text = "PASS" if outcome == "success" else "FAIL"

    ctx = OutputContext.from_args(args)
    summary = (
        "## Secret Detection (gitleaks)\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| Commits scanned | {commits_count} |\n"
        f"| Files in repo | {files_count} |\n"
        f"| Leaks found | {leak_text} |\n"
        f"| Result | {result_text} |\n"
    )
    ctx.write_summary(summary)
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"gitleaks-summary: {result_text}",
        data={
            "commits_scanned": commits_count,
            "files_count": files_count,
            "outcome": outcome,
            "result": result_text,
        },
    )


def _env_result(name: str) -> str:
    return os.environ.get(name, "skipped")


def cmd_pytest_summary(args: argparse.Namespace) -> CommandResult:
    """Generate a summary for pytest results matching smoke test format."""
    ctx = OutputContext.from_args(args)
    problems: list[dict[str, str]] = []

    # Parse test-results.xml (JUnit format)
    tests_total = 0
    tests_passed = 0
    tests_failed = 0
    tests_skipped = 0

    junit_path = Path(args.junit_xml)
    if junit_path.exists():
        try:
            tree = ET.parse(junit_path)
            root = tree.getroot()
            # Handle both <testsuite> and <testsuites> root elements
            if root.tag == "testsuites":
                suites = root.findall("testsuite")
            else:
                suites = [root]

            for suite in suites:
                tests_total += int(suite.get("tests", 0))
                tests_failed += int(suite.get("failures", 0)) + int(suite.get("errors", 0))
                tests_skipped += int(suite.get("skipped", 0))

            tests_passed = tests_total - tests_failed - tests_skipped
        except ET.ParseError as e:
            problems.append({"severity": "warning", "message": f"Failed to parse {junit_path}: {e}"})

    # Parse coverage.xml (Cobertura format)
    coverage_pct = 0
    lines_covered = 0
    lines_total = 0

    coverage_path = Path(args.coverage_xml)
    if coverage_path.exists():
        try:
            tree = ET.parse(coverage_path)
            root = tree.getroot()
            # Cobertura format: line-rate is a decimal (0.0 to 1.0)
            line_rate = float(root.get("line-rate", 0))
            coverage_pct = int(line_rate * 100)
            lines_covered = int(root.get("lines-covered", 0))
            lines_total = int(root.get("lines-valid", 0))
        except ET.ParseError as e:
            problems.append({"severity": "warning", "message": f"Failed to parse {coverage_path}: {e}"})

    # Determine status
    tests_pass = tests_total > 0 and tests_failed == 0
    coverage_threshold = args.coverage_min
    coverage_pass = coverage_pct >= coverage_threshold

    # Generate summary matching smoke test format
    lines = [
        "## Unit Tests Summary",
        "",
        "| Metric | Result | Status |",
        "|--------|--------|--------|",
        f"| **Unit Tests** | {tests_passed} passed | {'PASS' if tests_pass else 'FAIL'} |",
        f"| **Test Failures** | {tests_failed} failed | {'WARN' if tests_failed > 0 else 'PASS'} |",
        f"| **Tests Skipped** | {tests_skipped} skipped | {'INFO' if tests_skipped > 0 else 'PASS'} |",
        f"| **Coverage (pytest-cov)** | {coverage_pct}% {_bar(coverage_pct)} | {'PASS' if coverage_pass else 'WARN'} |",
        "",
        f"**Coverage Details:** {lines_covered:,} / {lines_total:,} lines covered",
        "",
        "### Test Results",
        f"**{'PASS' if tests_pass and coverage_pass else 'FAIL'}** - "
        + (
            f"All {tests_total} tests passed with {coverage_pct}% coverage"
            if tests_pass and coverage_pass
            else f"{tests_failed} test(s) failed or coverage below {coverage_threshold}%"
        ),
    ]

    ctx.write_summary("\n".join(lines))
    success = tests_pass
    return CommandResult(
        exit_code=EXIT_SUCCESS if success else EXIT_FAILURE,
        summary=f"pytest-summary: {tests_passed}/{tests_total} passed, {coverage_pct}% coverage",
        problems=problems,
        data={
            "tests_total": tests_total,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "tests_skipped": tests_skipped,
            "coverage_pct": coverage_pct,
            "lines_covered": lines_covered,
            "lines_total": lines_total,
        },
    )


def cmd_summary(args: argparse.Namespace) -> CommandResult:
    ctx = OutputContext.from_args(args)
    repo = os.environ.get("GH_REPOSITORY", "")
    branch = os.environ.get("GH_REF_NAME", "")
    run_number = os.environ.get("GH_RUN_NUMBER", "")
    event_name = os.environ.get("GH_EVENT_NAME", "")

    def ran(status: str) -> str:
        """Return true/false for whether tool ran."""
        if status in ("skipped", "cancelled"):
            return "false"
        return "true"

    def ok(status: str) -> str:
        """Return descriptive text for tool result."""
        if status == "success":
            return "passed"
        if status == "skipped":
            return "skipped"
        if status == "cancelled":
            return "cancelled"
        return "failed"

    def status_text(status: str) -> str:
        if status == "success":
            return "Passed"
        if status == "skipped":
            return "Skipped"
        return "Failed"

    results = {
        "actionlint": _env_result("RESULT_ACTIONLINT"),
        "zizmor": _env_result("RESULT_ZIZMOR"),
        "ruff": _env_result("RESULT_LINT"),
        "syntax": _env_result("RESULT_SYNTAX"),
        "mypy": _env_result("RESULT_TYPECHECK"),
        "yamllint": _env_result("RESULT_YAMLLINT"),
        "pytest": _env_result("RESULT_UNIT_TESTS"),
        "mutmut": _env_result("RESULT_MUTATION"),
        "bandit": _env_result("RESULT_BANDIT"),
        "pip-audit": _env_result("RESULT_PIP_AUDIT"),
        "gitleaks": _env_result("RESULT_SECRET_SCAN"),
        "trivy": _env_result("RESULT_TRIVY"),
        "templates": _env_result("RESULT_TEMPLATES"),
        "configs": _env_result("RESULT_CONFIGS"),
        "matrix-keys": _env_result("RESULT_MATRIX_KEYS"),
        "licenses": _env_result("RESULT_LICENSE"),
        "dependency-review": _env_result("RESULT_DEP_REVIEW"),
        "scorecard": _env_result("RESULT_SCORECARD"),
    }

    lines = [
        "## Hub Production CI Summary",
        "",
        "### Environment",
        "",
        "| Setting | Value |",
        "|---------|-------|",
        f"| Repository | {repo} |",
        f"| Branch | {branch} |",
        f"| Run Number | #{run_number} |",
        f"| Trigger | {event_name} |",
        "| Language | Python |",
        "",
        "## Tools Enabled",
        "",
        "| Category | Tool | Configured | Ran | Success |",
        "|----------|------|------------|-----|---------|",
        f"| Workflow | actionlint | true | {ran(results['actionlint'])} | {ok(results['actionlint'])} |",
        f"| Workflow | zizmor | true | {ran(results['zizmor'])} | {ok(results['zizmor'])} |",
        f"| Quality | ruff | true | {ran(results['ruff'])} | {ok(results['ruff'])} |",
        f"| Quality | syntax | true | {ran(results['syntax'])} | {ok(results['syntax'])} |",
        f"| Quality | mypy | true | {ran(results['mypy'])} | {ok(results['mypy'])} |",
        f"| Quality | yamllint | true | {ran(results['yamllint'])} | {ok(results['yamllint'])} |",
        f"| Testing | pytest | true | {ran(results['pytest'])} | {ok(results['pytest'])} |",
        f"| Testing | mutmut | true | {ran(results['mutmut'])} | {ok(results['mutmut'])} |",
        f"| Security | bandit | true | {ran(results['bandit'])} | {ok(results['bandit'])} |",
        f"| Security | pip-audit | true | {ran(results['pip-audit'])} | {ok(results['pip-audit'])} |",
        f"| Security | gitleaks | true | {ran(results['gitleaks'])} | {ok(results['gitleaks'])} |",
        f"| Security | trivy | true | {ran(results['trivy'])} | {ok(results['trivy'])} |",
        f"| Validate | templates | true | {ran(results['templates'])} | {ok(results['templates'])} |",
        f"| Validate | configs | true | {ran(results['configs'])} | {ok(results['configs'])} |",
        f"| Validate | matrix-keys | true | {ran(results['matrix-keys'])} | {ok(results['matrix-keys'])} |",
        f"| Validate | licenses | true | {ran(results['licenses'])} | {ok(results['licenses'])} |",
        f"| Supply Chain | dependency-review | true | {ran(results['dependency-review'])} | {ok(results['dependency-review'])} |",  # noqa: E501
        f"| Supply Chain | scorecard | true | {ran(results['scorecard'])} | {ok(results['scorecard'])} |",
        "",
        "### Failed or Skipped Checks",
        "",
        "| Check | Status |",
        "|-------|--------|",
    ]

    has_issues = False
    for name, status in results.items():
        if status != "success":
            has_issues = True
            lines.append(f"| {name} | {status} |")
    if not has_issues:
        lines.append("| None | success |")
    lines.append("")
    # Parse Trivy findings from environment (using env_int for safe parsing)
    trivy_critical = env_int("TRIVY_CRITICAL", 0)
    trivy_high = env_int("TRIVY_HIGH", 0)
    trivy_fs_critical = env_int("TRIVY_FS_CRITICAL", 0)
    trivy_fs_high = env_int("TRIVY_FS_HIGH", 0)
    trivy_config_critical = env_int("TRIVY_CONFIG_CRITICAL", 0)
    trivy_config_high = env_int("TRIVY_CONFIG_HIGH", 0)

    # Trivy passes if no critical vulnerabilities (high may be warnings)
    trivy_status = "Passed" if trivy_critical == 0 else "Failed"
    trivy_finding_text = f"{trivy_critical} crit, {trivy_high} high"

    lines.extend(
        [
            "### Quality Gates",
            "",
            "| Check | Threshold | Status |",
            "|-------|-----------|--------|",
            f"| Unit Tests | pass | {status_text(results['pytest'])} |",
            f"| Coverage | 70% min | {'Passed' if results['pytest'] == 'success' else 'N/A'} |",
            f"| Mutation Score | 70% min | {status_text(results['mutmut'])} |",
            f"| Type Check (mypy) | 0 errors | {'Passed' if results['mypy'] == 'success' else 'Failed'} |",
            f"| SAST (bandit) | 0 high | {'Passed' if results['bandit'] == 'success' else 'Failed'} |",
            f"| Secrets (gitleaks) | 0 leaks | {'Passed' if results['gitleaks'] == 'success' else 'Failed'} |",
            f"| Trivy (vuln+config) | 0 critical | {trivy_status} ({trivy_finding_text}) |",
            "",
        ]
    )

    # Add Trivy breakdown if any findings
    if trivy_critical > 0 or trivy_high > 0:
        lines.extend(
            [
                "#### Trivy Findings Breakdown",
                "",
                "| Scan Type | Critical | High |",
                "|-----------|----------|------|",
                f"| Filesystem (vulns) | {trivy_fs_critical} | {trivy_fs_high} |",
                f"| Config (misconfigs) | {trivy_config_critical} | {trivy_config_high} |",
                f"| **Total** | **{trivy_critical}** | **{trivy_high}** |",
                "",
            ]
        )

    lines.append("Job summary generated at run-time")
    ctx.write_summary("\n".join(lines))
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="summary: generated CI summary",
        data={"results": results, "has_issues": has_issues},
    )


def cmd_enforce(args: argparse.Namespace) -> CommandResult:
    checks = [
        ("actionlint", _env_result("RESULT_ACTIONLINT"), "fix workflow syntax"),
        ("zizmor", _env_result("RESULT_ZIZMOR"), "address workflow security findings"),
        ("mypy", _env_result("RESULT_TYPECHECK"), "fix mypy errors"),
        ("yamllint", _env_result("RESULT_YAMLLINT"), "fix config syntax"),
        ("ruff", _env_result("RESULT_LINT"), "fix ruff lint violations"),
        ("syntax", _env_result("RESULT_SYNTAX"), "fix Python syntax errors"),
        ("unit-tests", _env_result("RESULT_UNIT_TESTS"), "unit tests failed"),
        ("mutation-tests", _env_result("RESULT_MUTATION"), "mutation testing failed"),
        ("bandit", _env_result("RESULT_BANDIT"), "security scan failed"),
        ("pip-audit", _env_result("RESULT_PIP_AUDIT"), "dependency audit failed"),
        ("gitleaks", _env_result("RESULT_SECRET_SCAN"), "secret detection failed"),
        ("trivy", _env_result("RESULT_TRIVY"), "trivy scan failed"),
        (
            "validate-templates",
            _env_result("RESULT_TEMPLATES"),
            "template validation failed",
        ),
        ("validate-configs", _env_result("RESULT_CONFIGS"), "config validation failed"),
        (
            "verify-matrix-keys",
            _env_result("RESULT_MATRIX_KEYS"),
            "matrix key validation failed",
        ),
        ("license-check", _env_result("RESULT_LICENSE"), "license compliance failed"),
        (
            "dependency-review",
            _env_result("RESULT_DEP_REVIEW"),
            "dependency review failed",
        ),
        ("scorecard", _env_result("RESULT_SCORECARD"), "scorecard checks failed"),
    ]

    problems: list[dict[str, str]] = []
    failed_checks: list[str] = []
    for name, result, message in checks:
        if result in ("failure", "cancelled"):
            problems.append({"severity": "error", "message": f"{name} failed - {message}"})
            failed_checks.append(name)

    if failed_checks:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"enforce: {len(failed_checks)} checks failed",
            problems=problems,
            data={"failed": failed_checks},
        )
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="enforce: all critical checks passed",
        data={"failed": []},
    )
