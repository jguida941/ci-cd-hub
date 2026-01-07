"""Template sync command handler."""

from __future__ import annotations

import argparse
import os
import subprocess
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.repo_config import get_repo_entries
from cihub.services.templates import render_dispatch_workflow
from cihub.types import CommandResult
from cihub.utils import resolve_executable
from cihub.utils.env import get_github_token
from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.github_api import delete_remote_file, fetch_remote_file, update_remote_file


def cmd_sync_templates(args: argparse.Namespace) -> CommandResult:
    """Sync caller workflow templates to target repos."""
    token, token_source = get_github_token()
    messages: list[str] = []
    problems: list[dict[str, Any]] = []

    if not token:
        missing_token_err = "Missing GitHub token (set GH_TOKEN, GITHUB_TOKEN, or HUB_DISPATCH_TOKEN)"  # noqa: S105
        # For --check or --dry-run, skip gracefully with warning (matches check.py pattern)
        if args.check or args.dry_run:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Skipping: {missing_token_err}. Cannot verify remote template state without token.",
                data={"skipped": True, "reason": "no_token"},
            )
        # For actual sync operations, token is required
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=missing_token_err,
            problems=[
                {
                    "severity": "error",
                    "message": missing_token_err,
                    "code": "CIHUB-TEMPLATES-NO-TOKEN",
                }
            ],
        )

    # Validate token format before setting env var (security: prevent pollution)
    # GitHub tokens: ghp_*, gho_*, ghs_*, github_pat_*, or classic tokens (40 hex chars)
    # Skip validation in test mode (PYTEST_CURRENT_TEST env var set by pytest)
    is_test_mode = "PYTEST_CURRENT_TEST" in os.environ
    if (
        token
        and not is_test_mode
        and not any(
            [
                token.startswith("ghp_"),  # Personal access token
                token.startswith("gho_"),  # OAuth token
                token.startswith("ghs_"),  # GitHub App installation token
                token.startswith("github_pat_"),  # Fine-grained PAT
                (len(token) == 40 and token.isalnum()),  # Classic token (40 hex chars)
            ]
        )
    ):
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Invalid GitHub token format",
            problems=[
                {
                    "severity": "error",
                    "message": "Token must be a valid GitHub token "
                    "(ghp_*, gho_*, ghs_*, github_pat_*, or 40-char classic)",
                    "code": "CIHUB-TEMPLATES-INVALID-TOKEN",
                }
            ],
        )

    if "GH_TOKEN" not in os.environ:
        os.environ["GH_TOKEN"] = token

    results: list[dict[str, Any]] = []
    entries = get_repo_entries(only_dispatch_enabled=not args.include_disabled)

    if args.repo:
        repo_map = {entry["full"]: entry for entry in entries}
        missing = [repo for repo in args.repo if repo not in repo_map]
        if missing:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=f"Repos not found in config/repos/*.yaml: {', '.join(missing)}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Repos not found in config/repos/*.yaml: {', '.join(missing)}",
                        "code": "CIHUB-TEMPLATES-REPO-NOT-FOUND",
                    }
                ],
            )
        entries = [repo_map[repo] for repo in args.repo]

    if not entries:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="No repos found to sync.",
            data={"repos": [], "failures": 0},
        )

    failures = 0
    for entry in entries:
        repo = entry["full"]
        language = entry.get("language", "")
        dispatch_workflow = entry.get("dispatch_workflow", "hub-ci.yml")
        branch = entry.get("default_branch", "main") or "main"
        path = f".github/workflows/{dispatch_workflow}"
        repo_result: dict[str, Any] = {
            "repo": repo,
            "path": path,
            "status": "unknown",
            "stale": [],
        }

        try:
            desired = render_dispatch_workflow(language, dispatch_workflow)
        except ValueError as exc:
            messages.append(f"[ERROR] {repo} {path}: {exc}")
            problems.append(
                {
                    "severity": "error",
                    "message": f"{repo} {path}: {exc}",
                    "code": "CIHUB-TEMPLATES-RENDER-ERROR",
                }
            )
            repo_result["status"] = "error"
            repo_result["message"] = str(exc)
            failures += 1
            results.append(repo_result)
            continue

        remote = fetch_remote_file(repo, path, branch)
        workflow_synced = False

        if remote and remote.get("content") == desired:
            messages.append(f"[OK] {repo} {path} up to date")
            workflow_synced = True
            repo_result["status"] = "up_to_date"
        elif args.check:
            messages.append(f"[FAIL] {repo} {path} out of date")
            failures += 1
            repo_result["status"] = "out_of_date"
        elif args.dry_run:
            messages.append(f"# Would update {repo} {path}")
            repo_result["status"] = "would_update"
        else:
            try:
                update_remote_file(
                    repo,
                    path,
                    branch,
                    desired,
                    args.commit_message,
                    remote.get("sha") if remote else None,
                )
                messages.append(f"[OK] {repo} {path} updated")
                workflow_synced = True
                repo_result["status"] = "updated"
            except RuntimeError as exc:
                messages.append(f"[FAIL] {repo} {path} update failed: {exc}")
                problems.append(
                    {
                        "severity": "error",
                        "message": f"{repo} {path} update failed: {exc}",
                        "code": "CIHUB-TEMPLATES-UPDATE-FAILED",
                    }
                )
                failures += 1
                repo_result["status"] = "failed"
                repo_result["message"] = str(exc)

        if dispatch_workflow == "hub-ci.yml":
            stale_workflow_names = ["hub-java-ci.yml", "hub-python-ci.yml"]
            for stale_name in stale_workflow_names:
                stale_path = f".github/workflows/{stale_name}"
                stale_file = fetch_remote_file(repo, stale_path, branch)
                if stale_file and stale_file.get("sha"):
                    if args.check:
                        messages.append(f"[FAIL] {repo} {stale_path} stale (should be deleted)")
                        failures += 1
                        repo_result["stale"].append({"path": stale_path, "status": "stale"})
                    elif args.dry_run:
                        messages.append(f"# Would delete {repo} {stale_path} (stale)")
                        repo_result["stale"].append({"path": stale_path, "status": "would_delete"})
                    elif workflow_synced:
                        try:
                            delete_remote_file(
                                repo,
                                stale_path,
                                branch,
                                stale_file["sha"],
                                "Remove stale workflow (migrated to hub-ci.yml)",
                            )
                            messages.append(f"[OK] {repo} {stale_path} deleted (stale)")
                            repo_result["stale"].append({"path": stale_path, "status": "deleted"})
                        except RuntimeError as exc:
                            messages.append(f"[WARN] {repo} {stale_path} delete failed: {exc}")
                            problems.append(
                                {
                                    "severity": "warning",
                                    "message": f"{repo} {stale_path} delete failed: {exc}",
                                    "code": "CIHUB-TEMPLATES-DELETE-FAILED",
                                }
                            )
                            repo_result["stale"].append(
                                {
                                    "path": stale_path,
                                    "status": "delete_failed",
                                    "message": str(exc),
                                }
                            )
        results.append(repo_result)

    exit_code = EXIT_SUCCESS
    if args.check and failures:
        messages.append(f"Template drift detected in {failures} repo(s).")
        exit_code = EXIT_FAILURE
    elif failures:
        exit_code = EXIT_FAILURE

    tag_status = None
    if args.update_tag and not args.check and not args.dry_run:
        try:
            git_bin = resolve_executable("git")
            result = safe_run(
                [git_bin, "rev-parse", "HEAD"],
                timeout=TIMEOUT_QUICK,
                check=True,
            )
            head_sha = result.stdout.strip()

            result = safe_run(
                [git_bin, "rev-parse", "v1"],
                timeout=TIMEOUT_QUICK,
            )
            current_v1 = result.stdout.strip() if result.returncode == 0 else None

            if current_v1 == head_sha:
                messages.append("[OK] v1 tag already at HEAD")
                tag_status = "up_to_date"
            else:
                # Security: Require confirmation for force-push operations
                if not getattr(args, "yes", False):
                    return CommandResult(
                        exit_code=EXIT_USAGE,
                        summary="Confirmation required for v1 tag force-push; re-run with --yes",
                        data={
                            "repos": results,
                            "failures": failures,
                            "tag": "requires_confirmation",
                            "items": messages,
                            "current_v1": current_v1[:7] if current_v1 else None,
                            "head_sha": head_sha[:7],
                        },
                        problems=[
                            {
                                "severity": "warning",
                                "message": (
                                    f"Will force-push v1 tag from "
                                    f"{current_v1[:7] if current_v1 else 'none'} to {head_sha[:7]}. "
                                    f"This affects all repositories referencing "
                                    f"jguida941/hub-release/.github/workflows/*@v1"
                                ),
                                "code": "CIHUB-TEMPLATES-TAG-CONFIRM",
                            }
                        ],
                    )

                safe_run(
                    [git_bin, "tag", "-f", "v1", "HEAD"],
                    check=True,
                    timeout=TIMEOUT_QUICK,
                )
                safe_run(
                    [git_bin, "push", "origin", "v1", "--force"],
                    check=True,
                    timeout=TIMEOUT_NETWORK,
                )
                messages.append(f"[OK] v1 tag updated: {current_v1[:7] if current_v1 else 'none'} -> {head_sha[:7]}")
                tag_status = "updated"
        except (subprocess.CalledProcessError, CommandNotFoundError, CommandTimeoutError) as exc:
            messages.append(f"[WARN] Failed to update v1 tag: {exc}")
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Failed to update v1 tag: {exc}",
                    "code": "CIHUB-TEMPLATES-TAG-FAILED",
                }
            )
            tag_status = "failed"
    elif args.dry_run and args.update_tag:
        messages.append("# Would update v1 tag to HEAD")
        tag_status = "would_update"

    summary = "Template sync complete" if exit_code == EXIT_SUCCESS else f"Template sync: {failures} failure(s)"
    data: dict[str, object] = {"repos": results, "failures": failures, "items": messages}
    if tag_status:
        data["tag"] = tag_status

    return CommandResult(exit_code=exit_code, summary=summary, problems=problems, data=data)
