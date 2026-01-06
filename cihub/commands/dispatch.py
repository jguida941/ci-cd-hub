"""Dispatch commands for hub orchestration."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.env import env_bool, get_github_token


@dataclass
class GitHubRequestResult:
    """Result of a GitHub API request."""

    data: dict[str, Any] | None = None
    error: str | None = None
    status_code: int | None = None

    @property
    def ok(self) -> bool:
        """Return True if request succeeded."""
        return self.data is not None and self.error is None


def _github_request(
    url: str,
    token: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> GitHubRequestResult:
    """Make a GitHub API request."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    body = json.dumps(data).encode() if data else None
    req = request.Request(url, data=body, headers=headers, method=method)  # noqa: S310

    try:
        with request.urlopen(req, timeout=30) as resp:  # noqa: S310
            if resp.status == 204:  # No content (e.g., workflow dispatch)
                return GitHubRequestResult(data={})
            response_data = resp.read().decode()
            return GitHubRequestResult(data=json.loads(response_data) if response_data else {})
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else ""
        return GitHubRequestResult(error=f"GitHub API error {exc.code}: {error_body}", status_code=exc.code)
    except Exception as exc:
        return GitHubRequestResult(error=f"Request failed: {exc}")


def _dispatch_workflow(
    owner: str,
    repo: str,
    workflow_id: str,
    ref: str,
    inputs: dict[str, str],
    token: str,
) -> GitHubRequestResult:
    """Dispatch a workflow via GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    data = {"ref": ref, "inputs": inputs}
    return _github_request(url, token, method="POST", data=data)


def _poll_for_run_id(
    owner: str,
    repo: str,
    workflow_id: str,
    branch: str,
    started_after: float,
    token: str,
    timeout_sec: int = 1800,
    initial_delay: float = 5.0,
) -> str | None:
    """Poll for a recently-triggered workflow run ID."""
    url = (
        f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/"
        f"{workflow_id}/runs?per_page=5&event=workflow_dispatch&branch={branch}"
    )

    deadline = time.time() + timeout_sec
    delay = initial_delay

    while time.time() < deadline:
        time.sleep(delay)
        result = _github_request(url, token)
        if not result.ok:
            delay = min(delay * 2, 30.0)
            continue

        for run in (result.data or {}).get("workflow_runs", []):
            created_at = run.get("created_at", "")
            if not created_at:
                continue
            # Parse ISO timestamp
            try:
                created_ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
            except ValueError:
                continue

            # Match runs created after dispatch (with 2s tolerance)
            if created_ts >= started_after - 2 and run.get("head_branch") == branch:
                if run.get("status") != "completed":
                    return str(run.get("id"))

        delay = min(delay * 2, 30.0)

    return None


def cmd_dispatch(args: argparse.Namespace) -> CommandResult:
    """Handle dispatch subcommands.

    Always returns CommandResult for consistent output handling.
    """
    if args.subcommand == "trigger":
        return _cmd_dispatch_trigger(args)
    if args.subcommand == "metadata":
        return _cmd_dispatch_metadata(args)

    message = f"Unknown dispatch subcommand: {args.subcommand}"
    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=message,
        problems=[{"severity": "error", "message": message, "code": "CIHUB-DISPATCH-UNKNOWN"}],
    )


def _cmd_dispatch_trigger(args: argparse.Namespace) -> CommandResult:
    """Dispatch a workflow and poll for the run ID."""
    owner = args.owner
    repo = args.repo
    workflow_id = args.workflow or "hub-ci.yml"
    ref = args.ref
    correlation_id = args.correlation_id

    # Get token using standardized priority: GH_TOKEN -> GITHUB_TOKEN -> HUB_DISPATCH_TOKEN
    token, token_source = get_github_token(
        explicit_token=args.token,
        token_env=args.token_env,
    )
    if not token:
        message = "Missing token (set GH_TOKEN, GITHUB_TOKEN, or HUB_DISPATCH_TOKEN)"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-DISPATCH-NO-TOKEN"}],
        )

    # Check if dispatch is enabled
    if args.dispatch_enabled is False:
        message = f"Dispatch disabled for {owner}/{repo}; skipping."
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=message,
            artifacts={"skipped": "true"},
        )

    # Build inputs
    inputs: dict[str, str] = {}
    if correlation_id:
        inputs["hub_correlation_id"] = correlation_id

    def _add_bool_input(input_name: str, env_name: str) -> None:
        if env_name not in os.environ:
            return
        inputs[input_name] = "true" if env_bool(env_name, default=False) else "false"

    _add_bool_input("cihub_debug", "CIHUB_DEBUG")
    _add_bool_input("cihub_verbose", "CIHUB_VERBOSE")
    _add_bool_input("cihub_debug_context", "CIHUB_DEBUG_CONTEXT")
    _add_bool_input("cihub_emit_triage", "CIHUB_EMIT_TRIAGE")

    # Record start time for polling
    started_at = time.time()

    # Dispatch
    dispatch_result = _dispatch_workflow(owner, repo, workflow_id, ref, inputs, token)
    if not dispatch_result.ok:
        message = f"Dispatch failed for {owner}/{repo}"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{
                "severity": "error",
                "message": message,
                "detail": dispatch_result.error or "",
                "code": "CIHUB-DISPATCH-FAILED",
            }],
        )

    # Poll for run ID
    timeout = int(args.timeout) if args.timeout else 1800
    run_id = _poll_for_run_id(owner, repo, workflow_id, ref, started_at, token, timeout)

    if not run_id:
        message = f"Dispatched {workflow_id} for {repo}, but could not determine run ID"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-DISPATCH-NO-RUN-ID"}],
        )

    # Write outputs to GITHUB_OUTPUT if available
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"run_id={run_id}\n")
            f.write(f"branch={ref}\n")
            f.write(f"workflow_id={workflow_id}\n")
            if correlation_id:
                f.write(f"correlation_id={correlation_id}\n")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Dispatched {workflow_id} on {owner}/{repo}, run ID {run_id}",
        artifacts={
            "run_id": run_id,
            "branch": ref,
            "workflow_id": workflow_id,
            "correlation_id": correlation_id or "",
        },
        data={
            "items": [
                f"Dispatching {workflow_id} on {owner}/{repo}@{ref}",
                f"Captured run ID {run_id} for {repo}",
            ]
        },
    )


def _cmd_dispatch_metadata(args: argparse.Namespace) -> CommandResult:
    """Generate dispatch metadata JSON file."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_basename = args.config_basename
    output_file = output_dir / f"{config_basename}.json"

    metadata = {
        "config": config_basename,
        "repo": f"{args.owner}/{args.repo}",
        "subdir": args.subdir or "",
        "language": args.language or "",
        "branch": args.branch or "",
        "workflow": args.workflow or "",
        "run_id": args.run_id or "",
        "correlation_id": args.correlation_id or "",
        "dispatch_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": args.status or "unknown",
    }

    output_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Generated dispatch metadata for {config_basename}",
        artifacts={"metadata": str(output_file)},
        files_generated=[str(output_file)],
        data={"items": [f"Wrote dispatch metadata: {output_file}"]},
    )
