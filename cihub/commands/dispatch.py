"""Dispatch commands for hub orchestration."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request

from cihub.cli import CommandResult
from cihub.correlation import generate_correlation_id
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def _github_request(
    url: str,
    token: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
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
                return {}
            response_data = resp.read().decode()
            return json.loads(response_data) if response_data else {}
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else ""
        print(f"GitHub API error {exc.code}: {error_body}")
        return None
    except Exception as exc:
        print(f"Request failed: {exc}")
        return None


def _dispatch_workflow(
    owner: str,
    repo: str,
    workflow_id: str,
    ref: str,
    inputs: dict[str, str],
    token: str,
) -> bool:
    """Dispatch a workflow via GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    data = {"ref": ref, "inputs": inputs}
    result = _github_request(url, token, method="POST", data=data)
    return result is not None


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
        if result is None:
            delay = min(delay * 2, 30.0)
            continue

        for run in result.get("workflow_runs", []):
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


def cmd_dispatch(args: argparse.Namespace) -> int | CommandResult:
    """Handle dispatch subcommands."""
    json_mode = getattr(args, "json", False)

    if args.subcommand == "trigger":
        return _cmd_dispatch_trigger(args, json_mode)
    if args.subcommand == "metadata":
        return _cmd_dispatch_metadata(args, json_mode)

    message = f"Unknown dispatch subcommand: {args.subcommand}"
    if json_mode:
        return CommandResult(exit_code=EXIT_FAILURE, summary=message)
    print(message)
    return EXIT_FAILURE


def _cmd_dispatch_trigger(args: argparse.Namespace, json_mode: bool) -> int | CommandResult:
    """Dispatch a workflow and poll for the run ID."""
    owner = args.owner
    repo = args.repo
    workflow_id = args.workflow or "hub-ci.yml"
    ref = args.ref
    correlation_id = args.correlation_id

    # Get token
    token = args.token
    token_env = args.token_env or "HUB_DISPATCH_TOKEN"  # noqa: S105
    if not token:
        token = os.environ.get(token_env)
    if not token and token_env != "GITHUB_TOKEN":
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        message = f"Missing token (expected {token_env} or GITHUB_TOKEN)"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"::error::{message}")
        return EXIT_FAILURE

    # Check if dispatch is enabled
    if args.dispatch_enabled is False:
        message = f"Dispatch disabled for {owner}/{repo}; skipping."
        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=message,
                artifacts={"skipped": "true"},
            )
        print(message)
        return EXIT_SUCCESS

    # Build inputs
    inputs: dict[str, str] = {}
    if correlation_id:
        inputs["hub_correlation_id"] = correlation_id

    # Record start time for polling
    started_at = time.time()

    # Dispatch
    print(f"Dispatching {workflow_id} on {owner}/{repo}@{ref}")
    if not _dispatch_workflow(owner, repo, workflow_id, ref, inputs, token):
        message = f"Dispatch failed for {owner}/{repo}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"::error::{message}")
        return EXIT_FAILURE

    # Poll for run ID
    timeout = int(args.timeout) if args.timeout else 1800
    run_id = _poll_for_run_id(owner, repo, workflow_id, ref, started_at, token, timeout)

    if not run_id:
        message = f"Dispatched {workflow_id} for {repo}, but could not determine run ID"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"::error::{message}")
        return EXIT_FAILURE

    print(f"Captured run ID {run_id} for {repo}")

    # Write outputs to GITHUB_OUTPUT if available
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"run_id={run_id}\n")
            f.write(f"branch={ref}\n")
            f.write(f"workflow_id={workflow_id}\n")
            if correlation_id:
                f.write(f"correlation_id={correlation_id}\n")

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Dispatched {workflow_id} on {owner}/{repo}, run ID {run_id}",
            artifacts={
                "run_id": run_id,
                "branch": ref,
                "workflow_id": workflow_id,
                "correlation_id": correlation_id or "",
            },
        )
    return EXIT_SUCCESS


def _cmd_dispatch_metadata(args: argparse.Namespace, json_mode: bool) -> int | CommandResult:
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
    print(f"Wrote dispatch metadata: {output_file}")

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Generated dispatch metadata for {config_basename}",
            artifacts={"metadata": str(output_file)},
        )
    return EXIT_SUCCESS
