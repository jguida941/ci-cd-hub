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

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
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
                # Return any matching run - even completed ones (fast workflows)
                return str(run.get("id"))

        delay = min(delay * 2, 30.0)

    return None


def _get_latest_run_id(
    owner: str,
    repo: str,
    workflow_id: str,
    branch: str | None,
    token: str,
) -> GitHubRequestResult:
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?per_page=1"
    if branch:
        url = f"{url}&branch={branch}"
    return _github_request(url, token)


def _get_run_status(
    owner: str,
    repo: str,
    run_id: str,
    token: str,
) -> GitHubRequestResult:
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
    return _github_request(url, token)


def _wait_for_run_completion(
    owner: str,
    repo: str,
    run_id: str,
    token: str,
    timeout_sec: int,
    interval_sec: int,
) -> dict[str, str] | None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        result = _get_run_status(owner, repo, run_id, token)
        if result.ok:
            data = result.data or {}
            status = str(data.get("status", ""))
            conclusion = str(data.get("conclusion", "")) if data.get("conclusion") is not None else ""
            run_url = str(data.get("html_url", "")) if data.get("html_url") else ""
            if status == "completed":
                return {
                    "status": status,
                    "conclusion": conclusion or "unknown",
                    "url": run_url,
                }
        time.sleep(interval_sec)
    return None


def cmd_dispatch(args: argparse.Namespace) -> CommandResult:
    """Handle dispatch subcommands.

    Always returns CommandResult for consistent output handling.
    """
    if args.subcommand == "trigger":
        return _cmd_dispatch_trigger(args)
    if args.subcommand == "watch":
        return _cmd_dispatch_watch(args)
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
    json_mode = getattr(args, "json", False)
    wizard = getattr(args, "wizard", False)
    if json_mode and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode (--wizard) cannot be used with --json output",
                    "code": "CIHUB-DISPATCH-WIZARD-JSON",
                }
            ],
        )
    if wizard:
        return _wizard_trigger(args)
    owner = args.owner
    repo = args.repo
    workflow_id = args.workflow or "hub-ci.yml"
    ref = args.ref
    correlation_id = args.correlation_id
    raw_inputs = getattr(args, "inputs", None) or []

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

    inputs_result = _parse_inputs(raw_inputs)
    if inputs_result["invalid"]:
        message = "Invalid workflow inputs; use key=value format"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[
                {
                    "severity": "error",
                    "message": message,
                    "detail": ", ".join(inputs_result["invalid"]),
                    "code": "CIHUB-DISPATCH-BAD-INPUT",
                }
            ],
        )
    parsed_inputs = inputs_result["parsed"]
    if not isinstance(parsed_inputs, dict):
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Invalid workflow inputs; use key=value format",
            problems=[
                {
                    "severity": "error",
                    "message": "Invalid workflow inputs; use key=value format",
                    "detail": ", ".join(inputs_result["invalid"]),
                    "code": "CIHUB-DISPATCH-BAD-INPUT",
                }
            ],
        )
    inputs: dict[str, str] = parsed_inputs
    if correlation_id:
        inputs["hub_correlation_id"] = correlation_id

    def _add_bool_input(input_name: str, env_name: str) -> None:
        if env_name not in os.environ:
            return
        inputs.setdefault(input_name, "true" if env_bool(env_name, default=False) else "false")

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
            problems=[
                {
                    "severity": "error",
                    "message": message,
                    "detail": dispatch_result.error or "",
                    "code": "CIHUB-DISPATCH-FAILED",
                }
            ],
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

    watch = bool(getattr(args, "watch", False))
    run_status: dict[str, str] | None = None
    if watch:
        interval = int(getattr(args, "watch_interval", 10) or 10)
        watch_timeout = int(getattr(args, "watch_timeout", 1800) or 1800)
        run_status = _wait_for_run_completion(owner, repo, run_id, token, watch_timeout, interval)
        if not run_status:
            message = f"Run {run_id} did not complete before timeout"
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[
                    {
                        "severity": "error",
                        "message": message,
                        "code": "CIHUB-DISPATCH-WATCH-TIMEOUT",
                    }
                ],
                artifacts={"run_id": run_id, "workflow_id": workflow_id},
            )

    conclusion = (run_status or {}).get("conclusion", "")
    status = (run_status or {}).get("status", "")
    run_url = (run_status or {}).get("url", "")
    success = not watch or conclusion in {"success"}
    summary_status = f", {status}/{conclusion}" if watch else ""

    return CommandResult(
        exit_code=EXIT_SUCCESS if success else EXIT_FAILURE,
        summary=f"Dispatched {workflow_id} on {owner}/{repo}, run ID {run_id}{summary_status}",
        artifacts={
            "run_id": run_id,
            "branch": ref,
            "workflow_id": workflow_id,
            "correlation_id": correlation_id or "",
            "run_url": run_url,
            "status": status,
            "conclusion": conclusion,
        },
        data={
            "items": [
                f"Dispatching {workflow_id} on {owner}/{repo}@{ref}",
                f"Captured run ID {run_id} for {repo}",
            ],
            "run_id": run_id,
            "run_url": run_url,
            "status": status,
            "conclusion": conclusion,
        },
    )


def _cmd_dispatch_watch(args: argparse.Namespace) -> CommandResult:
    json_mode = getattr(args, "json", False)
    wizard = getattr(args, "wizard", False)
    if json_mode and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode (--wizard) cannot be used with --json output",
                    "code": "CIHUB-DISPATCH-WATCH-WIZARD-JSON",
                }
            ],
        )
    if wizard:
        return _wizard_watch(args)

    owner = args.owner
    repo = args.repo
    run_id = getattr(args, "run_id", None)
    latest = bool(getattr(args, "latest", False))
    workflow_id = getattr(args, "workflow", None) or "hub-ci.yml"
    branch = getattr(args, "branch", None)

    token, _token_source = get_github_token(
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

    if not run_id:
        if not latest:
            message = "Run ID required (or use --latest with --workflow)"
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=message,
                problems=[
                    {
                        "severity": "error",
                        "message": message,
                        "code": "CIHUB-DISPATCH-WATCH-NO-RUN-ID",
                    }
                ],
            )
        latest_result = _get_latest_run_id(owner, repo, workflow_id, branch, token)
        if not latest_result.ok:
            message = f"Failed to list runs for {owner}/{repo}"
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[
                    {
                        "severity": "error",
                        "message": message,
                        "detail": latest_result.error or "",
                        "code": "CIHUB-DISPATCH-WATCH-LIST-FAILED",
                    }
                ],
            )
        runs = (latest_result.data or {}).get("workflow_runs", [])
        if not runs:
            message = "No workflow runs found"
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[
                    {
                        "severity": "error",
                        "message": message,
                        "code": "CIHUB-DISPATCH-WATCH-NO-RUNS",
                    }
                ],
            )
        run_id = str(runs[0].get("id"))

    interval = int(getattr(args, "interval", 10) or 10)
    timeout = int(getattr(args, "timeout", 1800) or 1800)
    run_status = _wait_for_run_completion(owner, repo, run_id, token, timeout, interval)
    if not run_status:
        message = f"Run {run_id} did not complete before timeout"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[
                {
                    "severity": "error",
                    "message": message,
                    "code": "CIHUB-DISPATCH-WATCH-TIMEOUT",
                }
            ],
            artifacts={"run_id": run_id, "workflow_id": workflow_id},
        )

    conclusion = run_status.get("conclusion", "")
    status = run_status.get("status", "")
    run_url = run_status.get("url", "")
    success = conclusion in {"success"}
    return CommandResult(
        exit_code=EXIT_SUCCESS if success else EXIT_FAILURE,
        summary=f"Run {run_id} completed ({status}/{conclusion})",
        artifacts={
            "run_id": run_id,
            "workflow_id": workflow_id,
            "run_url": run_url,
            "status": status,
            "conclusion": conclusion,
        },
        data={
            "run_id": run_id,
            "run_url": run_url,
            "status": status,
            "conclusion": conclusion,
        },
    )


def _parse_inputs(raw_inputs: list[str]) -> dict[str, list[str] | dict[str, str]]:
    parsed: dict[str, str] = {}
    invalid: list[str] = []
    for entry in raw_inputs:
        if "=" not in entry:
            invalid.append(entry)
            continue
        key, value = entry.split("=", 1)
        key = key.strip()
        if not key:
            invalid.append(entry)
            continue
        parsed[key] = value.strip()
    return {"parsed": parsed, "invalid": invalid}


def _wizard_trigger(args: argparse.Namespace) -> CommandResult:
    try:
        import questionary

        from cihub.wizard.core import WizardCancelled, _check_cancelled
        from cihub.wizard.styles import get_style
    except ImportError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="questionary not installed (pip install questionary)",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode requires questionary",
                    "code": "CIHUB-DISPATCH-NO-QUESTIONARY",
                }
            ],
        )

    try:
        from cihub.services.registry.io import load_registry
        from cihub.services.registry.query import list_repos

        registry = load_registry()
        repos = list_repos(registry)
        repo_names = sorted([r.get("name", "unknown") for r in repos])
        choices = repo_names + ["(manual entry)"] if repo_names else ["(manual entry)"]

        selected_repo: str = _check_cancelled(
            questionary.select("Select repository:", choices=choices, style=get_style()).ask(),
            "Repository selection",
        )
        repo_defaults: dict[str, str] = {}
        if selected_repo != "(manual entry)":
            match = next((r for r in repos if r.get("name") == selected_repo), {})
            repo_block = (match.get("config") or {}).get("repo", {})
            if isinstance(repo_block, dict):
                repo_defaults = {
                    "owner": str(repo_block.get("owner", "")),
                    "name": str(repo_block.get("name", selected_repo)),
                    "default_branch": str(repo_block.get("default_branch", "main")),
                    "dispatch_workflow": str(repo_block.get("dispatch_workflow", "hub-ci.yml")),
                    "dispatch_enabled": str(repo_block.get("dispatch_enabled", True)),
                }

        owner = _check_cancelled(
            questionary.text(
                "Repo owner (org/user):",
                default=repo_defaults.get("owner", ""),
                style=get_style(),
            ).ask(),
            "Repo owner",
        )
        repo_name = _check_cancelled(
            questionary.text(
                "Repo name:",
                default=repo_defaults.get("name", ""),
                style=get_style(),
            ).ask(),
            "Repo name",
        )
        workflow_id = _check_cancelled(
            questionary.text(
                "Workflow file:",
                default=repo_defaults.get("dispatch_workflow", "hub-ci.yml"),
                style=get_style(),
            ).ask(),
            "Workflow file",
        )
        ref = _check_cancelled(
            questionary.text(
                "Git ref (branch):",
                default=repo_defaults.get("default_branch", "main"),
                style=get_style(),
            ).ask(),
            "Branch",
        )
        dispatch_enabled = _check_cancelled(
            questionary.confirm(
                "Dispatch enabled for this repo?",
                default=repo_defaults.get("dispatch_enabled", "True").lower() != "false",
                style=get_style(),
            ).ask(),
            "Dispatch enabled",
        )
        watch = _check_cancelled(
            questionary.confirm(
                "Watch run to completion?",
                default=bool(getattr(args, "watch", False)),
                style=get_style(),
            ).ask(),
            "Watch prompt",
        )
        watch_timeout = getattr(args, "watch_timeout", 1800)
        watch_interval = getattr(args, "watch_interval", 10)
        if watch:
            watch_timeout = int(
                _check_cancelled(
                    questionary.text(
                        "Watch timeout (seconds):",
                        default=str(watch_timeout),
                        style=get_style(),
                    ).ask(),
                    "Watch timeout",
                )
            )
            watch_interval = int(
                _check_cancelled(
                    questionary.text(
                        "Watch interval (seconds):",
                        default=str(watch_interval),
                        style=get_style(),
                    ).ask(),
                    "Watch interval",
                )
            )
        raw_inputs = _check_cancelled(
            questionary.text(
                "Workflow inputs (key=value, comma-separated; optional):",
                default="",
                style=get_style(),
            ).ask(),
            "Workflow inputs",
        )
        inputs_list = [entry.strip() for entry in raw_inputs.split(",") if entry.strip()]

        wizard_args = argparse.Namespace(
            subcommand="trigger",
            owner=str(owner),
            repo=str(repo_name),
            workflow=str(workflow_id),
            ref=str(ref),
            correlation_id=None,
            inputs=inputs_list,
            token=None,
            token_env=getattr(args, "token_env", "HUB_DISPATCH_TOKEN"),
            dispatch_enabled=bool(dispatch_enabled),
            timeout=getattr(args, "timeout", 1800),
            watch=bool(watch),
            watch_interval=watch_interval,
            watch_timeout=watch_timeout,
            json=False,
            wizard=False,
        )
        return _cmd_dispatch_trigger(wizard_args)
    except WizardCancelled:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Wizard cancelled",
            data={"cancelled": True},
        )


def _wizard_watch(args: argparse.Namespace) -> CommandResult:
    try:
        import questionary

        from cihub.wizard.core import WizardCancelled, _check_cancelled
        from cihub.wizard.styles import get_style
    except ImportError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="questionary not installed (pip install questionary)",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode requires questionary",
                    "code": "CIHUB-DISPATCH-NO-QUESTIONARY",
                }
            ],
        )

    try:
        owner = _check_cancelled(
            questionary.text("Repo owner (org/user):", style=get_style()).ask(),
            "Repo owner",
        )
        repo_name = _check_cancelled(
            questionary.text("Repo name:", style=get_style()).ask(),
            "Repo name",
        )
        latest = _check_cancelled(
            questionary.confirm("Watch latest workflow run?", default=True, style=get_style()).ask(),
            "Latest run",
        )
        run_id = None
        workflow_id = "hub-ci.yml"
        branch = None
        if latest:
            workflow_id = _check_cancelled(
                questionary.text(
                    "Workflow file:",
                    default=str(getattr(args, "workflow", "hub-ci.yml")),
                    style=get_style(),
                ).ask(),
                "Workflow file",
            )
            branch = _check_cancelled(
                questionary.text("Branch (optional):", default="", style=get_style()).ask(),
                "Branch",
            )
        else:
            run_id = _check_cancelled(
                questionary.text("Run ID:", style=get_style()).ask(),
                "Run ID",
            )

        wizard_args = argparse.Namespace(
            subcommand="watch",
            owner=str(owner),
            repo=str(repo_name),
            run_id=str(run_id) if run_id else None,
            latest=bool(latest),
            workflow=str(workflow_id),
            branch=str(branch) if branch else None,
            token=None,
            token_env=getattr(args, "token_env", "HUB_DISPATCH_TOKEN"),
            interval=getattr(args, "interval", 10),
            timeout=getattr(args, "timeout", 1800),
            json=False,
            wizard=False,
        )
        return _cmd_dispatch_watch(wizard_args)
    except WizardCancelled:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Wizard cancelled",
            data={"cancelled": True},
        )


def _cmd_dispatch_metadata(args: argparse.Namespace) -> CommandResult:
    """Generate dispatch metadata JSON file."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_basename = args.config_basename
    output_file = output_dir / f"{config_basename}.json"
    # Support nested config basenames (e.g., owner/repo) by ensuring parent dirs exist.
    output_file.parent.mkdir(parents=True, exist_ok=True)

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
