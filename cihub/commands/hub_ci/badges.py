"""Badge generation and configuration output commands."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from cihub import badges as badge_tools
from cihub.types import CommandResult
from cihub.utils.env import resolve_flag
from cihub.utils.github_context import GitHubContext, OutputContext
from cihub.utils.paths import hub_root

from . import (
    _bool_str,
    _compare_badges,
    _load_config,
    _run_command,
    result_fail,
    result_ok,
)


def _config_warning_problems(warnings: list[str]) -> list[dict[str, str]]:
    return [{"severity": "warning", "message": warning} for warning in warnings]


def _with_error(summary: str, warnings: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"severity": "error", "message": summary}, *warnings]


def cmd_badges(args: argparse.Namespace) -> CommandResult:
    root = hub_root()
    config_path = Path(args.config).resolve() if args.config else root / "config" / "defaults.yaml"
    config, config_warnings = _load_config(config_path)
    config_problems = _config_warning_problems(config_warnings)
    badges_cfg = config.get("reports", {}).get("badges", {}) or {}
    if badges_cfg.get("enabled") is False:
        return result_ok("Badges disabled via reports.badges.enabled", problems=config_problems)
    tools_cfg = config.get("hub_ci", {}).get("tools", {}) if isinstance(config.get("hub_ci"), dict) else {}

    def tool_enabled(name: str, default: bool = True) -> bool:
        if not isinstance(tools_cfg, dict):
            return default
        return bool(tools_cfg.get(name, default))

    # Collect disabled tools for deterministic "disabled" badges
    all_badge_tools = ["ruff", "mutmut", "mypy", "bandit", "pip_audit", "zizmor"]
    disabled_tools: set[str] = set()
    for tool in all_badge_tools:
        if not tool_enabled(tool):
            disabled_tools.add(tool)

    env = os.environ.copy()
    env["UPDATE_BADGES"] = "true"

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    if output_dir:
        env["BADGE_OUTPUT_DIR"] = str(output_dir)

    if args.ruff_issues is not None and tool_enabled("ruff"):
        env["RUFF_ISSUES"] = str(args.ruff_issues)
    if args.mutation_score is not None and tool_enabled("mutmut"):
        env["MUTATION_SCORE"] = str(args.mutation_score)
    if args.mypy_errors is not None and tool_enabled("mypy"):
        env["MYPY_ERRORS"] = str(args.mypy_errors)
    if args.black_issues is not None and tool_enabled("black"):
        env["BLACK_ISSUES"] = str(args.black_issues)
    if args.black_status and tool_enabled("black"):
        env["BLACK_STATUS"] = args.black_status
    if args.zizmor_sarif and tool_enabled("zizmor"):
        env["ZIZMOR_SARIF"] = str(Path(args.zizmor_sarif).resolve())

    artifacts_dir = Path(args.artifacts_dir).resolve() if args.artifacts_dir else None
    if artifacts_dir:
        bandit = artifacts_dir / "bandit-results" / "bandit.json"
        pip_audit = artifacts_dir / "pip-audit-results" / "pip-audit.json"
        zizmor = artifacts_dir / "zizmor-sarif" / "zizmor.sarif"
        if bandit.exists() and tool_enabled("bandit"):
            shutil.copyfile(bandit, root / "bandit.json")
        if pip_audit.exists() and tool_enabled("pip_audit"):
            shutil.copyfile(pip_audit, root / "pip-audit.json")
        if zizmor.exists() and tool_enabled("zizmor"):
            shutil.copyfile(zizmor, root / "zizmor.sarif")

    if args.check:
        with tempfile.TemporaryDirectory(prefix="cihub-badges-") as tmpdir:
            env["BADGE_OUTPUT_DIR"] = tmpdir
            gen_result = badge_tools.main(env=env, root=root, disabled_tools=disabled_tools)
            if gen_result != 0:
                return result_fail(
                    "Badge generation failed",
                    problems=_with_error("Badge generation failed", config_problems),
                )
            issues = _compare_badges(root / "badges", Path(tmpdir))
            if issues:
                problems = [{"severity": "error", "message": issue} for issue in issues]
                return result_fail(
                    "Badge drift detected",
                    problems=config_problems + problems,
                    data={"drift_issues": issues},
                )
            return result_ok("Badges are up to date", problems=config_problems)

    gen_result = badge_tools.main(env=env, root=root, disabled_tools=disabled_tools)
    if gen_result != 0:
        return result_fail(
            "Badge generation failed",
            problems=_with_error("Badge generation failed", config_problems),
        )
    return result_ok(
        "Badges updated successfully",
        data={"disabled_tools": list(disabled_tools)},
        problems=config_problems,
    )


def cmd_badges_commit(_: argparse.Namespace) -> CommandResult:
    root = hub_root()
    commit_message = "chore: update CI badges [skip ci]"

    def run_git(git_args: list[str]) -> dict[str, str | int | bool]:
        proc = _run_command(["git", *git_args], root)
        return {
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "returncode": proc.returncode,
            "success": proc.returncode == 0,
        }

    # Configure git user
    config_steps = (
        ["config", "user.name", "github-actions[bot]"],
        ["config", "user.email", "github-actions[bot]@users.noreply.github.com"],
    )
    for config_args in config_steps:
        result = run_git(config_args)
        if not result["success"]:
            error_msg = (str(result["stdout"]) or str(result["stderr"])).strip()
            return result_fail(
                f"Git config failed: {error_msg}" if error_msg else "Git config failed",
            )

    # Stage badge changes
    add_result = run_git(["add", "badges/"])
    if not add_result["success"]:
        error_msg = (str(add_result["stdout"]) or str(add_result["stderr"])).strip()
        return result_fail(
            f"Git add failed: {error_msg}" if error_msg else "Git add failed",
        )

    # Check if there are changes to commit
    diff_result = run_git(["diff", "--staged", "--quiet"])
    if diff_result["returncode"] == 0:
        return result_ok("No badge changes to commit")
    if diff_result["returncode"] != 1:
        error_msg = (str(diff_result["stdout"]) or str(diff_result["stderr"])).strip()
        return result_fail(
            f"Git diff failed: {error_msg}" if error_msg else "Git diff failed",
        )

    # Commit changes
    commit_result = run_git(["commit", "-m", commit_message])
    if not commit_result["success"]:
        error_msg = (str(commit_result["stdout"]) or str(commit_result["stderr"])).strip()
        return result_fail(
            f"Git commit failed: {error_msg}" if error_msg else "Git commit failed",
        )

    # Push changes
    push_result = run_git(["push"])
    if not push_result["success"]:
        error_msg = (str(push_result["stdout"]) or str(push_result["stderr"])).strip()
        return result_fail(
            f"Git push failed: {error_msg}" if error_msg else "Git push failed",
        )

    return result_ok("Badge changes committed and pushed")


def cmd_outputs(args: argparse.Namespace) -> CommandResult:
    # Use canonical config loading (merges defaults + repo config, validates merged result)
    if args.config:
        # Direct config path override (legacy mode)
        config_path = Path(args.config).resolve()
        config, config_warnings = _load_config(config_path)
        config_problems = _config_warning_problems(config_warnings)
    else:
        # Canonical: load via repo name using loader/core.py
        from cihub.config.loader import load_config

        root = hub_root()
        repo_name = resolve_flag(getattr(args, "repo", None), "CIHUB_REPO")
        if not repo_name:
            repo_env = GitHubContext.from_env().repository or ""
            if repo_env and "/" in repo_env:
                repo_name = repo_env.split("/", 1)[1]
        if repo_name and "/" in repo_name:
            repo_name = repo_name.split("/", 1)[1]

        if repo_name:
            try:
                config = load_config(repo_name, root, exit_on_validation_error=False)
                config_problems = []
            except Exception:  # noqa: BLE001
                # Fall back to defaults if repo config not found
                config, config_warnings = _load_config(root / "config" / "defaults.yaml")
                config_problems = _config_warning_problems(config_warnings)
        else:
            config, config_warnings = _load_config(root / "config" / "defaults.yaml")
            config_problems = _config_warning_problems(config_warnings)

    hub_cfg = config.get("hub_ci", {}) if isinstance(config.get("hub_ci"), dict) else {}
    enabled = hub_cfg.get("enabled", True)
    tools = hub_cfg.get("tools", {}) if isinstance(hub_cfg.get("tools"), dict) else {}
    thresholds = hub_cfg.get("thresholds", {}) if isinstance(hub_cfg.get("thresholds"), dict) else {}

    outputs = {
        "hub_ci_enabled": _bool_str(bool(enabled)),
        "run_actionlint": _bool_str(bool(tools.get("actionlint", True))),
        "run_zizmor": _bool_str(bool(tools.get("zizmor", True))),
        "run_ruff": _bool_str(bool(tools.get("ruff", True))),
        "run_syntax": _bool_str(bool(tools.get("syntax", True))),
        "run_mypy": _bool_str(bool(tools.get("mypy", True))),
        "run_yamllint": _bool_str(bool(tools.get("yamllint", True))),
        "run_pytest": _bool_str(bool(tools.get("pytest", True))),
        "run_mutmut": _bool_str(bool(tools.get("mutmut", True))),
        "run_bandit": _bool_str(bool(tools.get("bandit", True))),
        "bandit_fail_high": _bool_str(bool(tools.get("bandit_fail_high", True))),
        "bandit_fail_medium": _bool_str(bool(tools.get("bandit_fail_medium", False))),
        "bandit_fail_low": _bool_str(bool(tools.get("bandit_fail_low", False))),
        "run_pip_audit": _bool_str(bool(tools.get("pip_audit", True))),
        "run_gitleaks": _bool_str(bool(tools.get("gitleaks", True))),
        "run_trivy": _bool_str(bool(tools.get("trivy", True))),
        "run_validate_templates": _bool_str(bool(tools.get("validate_templates", True))),
        "run_validate_configs": _bool_str(bool(tools.get("validate_configs", True))),
        "run_verify_matrix_keys": _bool_str(bool(tools.get("verify_matrix_keys", True))),
        "run_license_check": _bool_str(bool(tools.get("license_check", True))),
        "run_dependency_review": _bool_str(bool(tools.get("dependency_review", True))),
        "run_scorecard": _bool_str(bool(tools.get("scorecard", True))),
        "coverage_min": str(thresholds.get("coverage_min", 70)),
        "mutation_score_min": str(thresholds.get("mutation_score_min", 70)),
    }

    ctx = OutputContext.from_args(args)
    ctx.write_outputs(outputs)
    return result_ok(
        "Configuration outputs written",
        data={"outputs": outputs},
        problems=config_problems,
    )
