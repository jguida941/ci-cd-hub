"""Watch mode for continuous triage of failed workflow runs.

This module provides a background polling loop that watches for
new failed runs and automatically triages them.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from cihub.exit_codes import EXIT_SUCCESS
from cihub.output.events import emit_event, get_event_sink
from cihub.types import CommandResult
from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    CommandNotFoundError,
    CommandTimeoutError,
    resolve_executable,
    safe_run,
)

from .remote import triage_single_run


def watch_for_failures(
    args: argparse.Namespace,
    interval: int,
    repo: str | None,
    workflow: str | None,
    branch: str | None,
) -> CommandResult:
    """Watch for new failed runs and auto-triage them.

    This is a blocking loop that polls for new failures at the specified interval.
    Press Ctrl+C to stop.

    Args:
        args: Original command arguments (for triage config)
        interval: Polling interval in seconds
        repo: Repository to watch
        workflow: Optional workflow filter
        branch: Optional branch filter

    Returns:
        CommandResult when stopped (via Ctrl+C or error)
    """
    triaged_runs: set[str] = set()
    triage_count = 0
    problems: list[dict[str, str]] = []
    output_lines: list[str] = []
    json_mode = bool(getattr(args, "json", False))
    streaming = get_event_sink() is not None and not json_mode
    output_dir = Path(args.output_dir or ".cihub")

    def emit(line: str = "") -> None:
        if streaming:
            emit_event("line", {"text": line})
        else:
            output_lines.append(line)

    emit(f"Watching for failed runs (interval: {interval}s, Ctrl+C to stop)")
    if workflow:
        emit(f"   Filtering: workflow={workflow}")
    if branch:
        emit(f"   Filtering: branch={branch}")
    emit()

    try:
        while True:
            # Get recent failed runs
            gh_bin = resolve_executable("gh")
            cmd = [
                gh_bin,
                "run",
                "list",
                "--status",
                "failure",
                "--limit",
                "5",
                "--json",
                "databaseId,name,headBranch,createdAt,conclusion",
            ]
            if repo:
                cmd.extend(["--repo", repo])
            if workflow:
                cmd.extend(["--workflow", workflow])
            if branch:
                cmd.extend(["--branch", branch])

            try:
                result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
                if result.returncode == 0:
                    runs = json.loads(result.stdout)
                    for run in runs:
                        run_id = str(run.get("databaseId", ""))
                        if run_id and run_id not in triaged_runs:
                            # New failure found - triage it
                            name = run.get("name", "Unknown")
                            branch_name = run.get("headBranch", "")
                            emit(f"[FAILURE] {name} (branch: {branch_name}, run: {run_id})")

                            # Run triage
                            try:
                                triage_result = triage_single_run(
                                    run_id=run_id,
                                    repo=repo,
                                    output_dir=output_dir,
                                )
                                triaged_runs.add(run_id)
                                triage_count += 1

                                if triage_result:
                                    emit(f"   [OK] Triaged: {triage_result}")
                                else:
                                    emit("   [WARN] Triage completed (no artifacts)")
                            except Exception as e:
                                problems.append(
                                    {
                                        "severity": "error",
                                        "message": f"Triage failed: {e}",
                                    }
                                )
                                emit(f"   [ERROR] Triage failed: {e}")
                                triaged_runs.add(run_id)  # Don't retry

                            emit()
            except (CommandNotFoundError, CommandTimeoutError, json.JSONDecodeError) as e:
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Poll error: {e}",
                    }
                )
                if streaming:
                    emit_event("line", {"text": f"[WARN] Poll error: {e}", "stream": "stderr"})
                else:
                    emit(f"[WARN] Poll error: {e}")

            time.sleep(interval)

    except KeyboardInterrupt:
        emit(f"\nStopped. Triaged {triage_count} run(s).")
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Watch stopped. Triaged {triage_count} run(s).",
            problems=problems,
            data={
                "triaged_count": triage_count,
                "triaged_runs": list(triaged_runs),
                **({"raw_output": "\n".join(output_lines)} if output_lines and not json_mode and not streaming else {}),
            },
        )


# Backward compatibility alias
_watch_for_failures = watch_for_failures


__all__ = [
    "watch_for_failures",
    # Backward compatibility
    "_watch_for_failures",
]
