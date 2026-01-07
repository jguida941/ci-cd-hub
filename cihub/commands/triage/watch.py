"""Watch mode for continuous triage of failed workflow runs.

This module provides a background polling loop that watches for
new failed runs and automatically triages them.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from cihub.exit_codes import EXIT_SUCCESS
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
    output_dir = Path(args.output_dir or ".cihub")

    print(f"Watching for failed runs (interval: {interval}s, Ctrl+C to stop)")
    if workflow:
        print(f"   Filtering: workflow={workflow}")
    if branch:
        print(f"   Filtering: branch={branch}")
    print()

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
                            print(f"[FAILURE] {name} (branch: {branch_name}, run: {run_id})")

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
                                    print(f"   [OK] Triaged: {triage_result}")
                                else:
                                    print("   [WARN] Triage completed (no artifacts)")
                            except Exception as e:
                                print(f"   [ERROR] Triage failed: {e}")
                                triaged_runs.add(run_id)  # Don't retry

                            print()
            except (CommandNotFoundError, CommandTimeoutError, json.JSONDecodeError) as e:
                print(f"[WARN] Poll error: {e}", file=sys.stderr)

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\nStopped. Triaged {triage_count} run(s).")
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Watch stopped. Triaged {triage_count} run(s).",
            data={"triaged_count": triage_count, "triaged_runs": list(triaged_runs)},
        )


# Backward compatibility alias
_watch_for_failures = watch_for_failures


__all__ = [
    "watch_for_failures",
    # Backward compatibility
    "_watch_for_failures",
]
