"""Aggregation runners and polling."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from cihub.core.correlation import find_run_by_correlation_id

from .artifacts import fetch_and_validate_artifact
from .github_api import GitHubAPI
from .metrics import extract_metrics_from_report
from .render import aggregate_results, generate_details_markdown, generate_summary_markdown
from .status import (
    _run_status_for_invalid_report,
    _run_status_from_report,
    create_run_status,
    load_dispatch_metadata,
)


def poll_run_completion(
    api: GitHubAPI,
    owner: str,
    repo: str,
    run_id: str,
    timeout_sec: int = 1800,
) -> tuple[str, str]:
    pending_statuses = {"queued", "in_progress", "waiting", "pending"}
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
    run_url = f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"
    start_poll = time.time()
    delay: float = 10.0

    print(f"Polling {owner}/{repo} run {run_id}...")
    print(f"   View: {run_url}")

    while True:
        try:
            elapsed = int(time.time() - start_poll)
            elapsed_min = elapsed // 60
            elapsed_sec = elapsed % 60

            run = api.get(url)
            status = run.get("status", "unknown")
            conclusion = run.get("conclusion", "unknown")

            print(f"   [{elapsed_min:02d}:{elapsed_sec:02d}] {owner}/{repo}: status={status}, conclusion={conclusion}")

            if status not in pending_statuses:
                print(f"Completed {owner}/{repo}: {conclusion}")
                return status, conclusion

            if time.time() - start_poll > timeout_sec:
                print(f"TIMEOUT: {owner}/{repo} after {timeout_sec}s")
                return "timed_out", "timed_out"

            print(f"   Waiting {int(delay)}s before next poll...")
            time.sleep(delay)
            delay = min(delay * 1.5, 60)
        except Exception as exc:
            print(f"ERROR polling {owner}/{repo} run {run_id}: {exc}")
            return "fetch_failed", "unknown"


def load_thresholds(defaults_file: Path) -> tuple[int, int]:
    max_critical = 0
    max_high = 0

    if defaults_file.exists():
        try:
            defaults = yaml.safe_load(defaults_file.read_text(encoding="utf-8"))
            thresholds = defaults.get("thresholds", {})
            max_critical = thresholds.get("max_critical_vulns", 0)
            max_high = thresholds.get("max_high_vulns", 0)
        except Exception as exc:
            print(f"Warning: could not load thresholds from {defaults_file}: {exc}")

    return max_critical, max_high


# -----------------------------------------------------------------------------
# Shared aggregation helpers (extracted from run_aggregation/run_reports_aggregation)
# -----------------------------------------------------------------------------


def _strip_report_data(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip _report_data from results for JSON output (too large to include)."""
    return [{k: v for k, v in r.items() if k != "_report_data"} for r in results]


def _build_aggregated_report(
    results: list[dict[str, Any]],
    hub_run_id: str,
    hub_event: str,
    total_repos: int,
    processed: int,
    missing: int,
) -> dict[str, Any]:
    """Build the aggregated report dict from processed results."""
    runs_for_json = _strip_report_data(results)

    report: dict[str, Any] = {
        "hub_run_id": hub_run_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "triggered_by": hub_event,
        "total_repos": total_repos,
        "dispatched_repos": processed,
        "missing_dispatch_metadata": missing,
        "runs": runs_for_json,
    }

    aggregated = aggregate_results(results)
    report.update(aggregated)
    return report


def _write_output_files(
    results: list[dict[str, Any]],
    report: dict[str, Any],
    output_file: Path,
    summary_file: Path | None,
    details_file: Path | None,
    total_repos: int,
    processed: int,
    missing: int,
    missing_run_id: int,
    *,
    include_details: bool = False,
    dispatched_label: str = "Total dispatched",
    missing_label: str = "Missing metadata",
) -> None:
    """Write output, summary, and details files."""
    output_file.write_text(json.dumps(report, indent=2))
    print(f"Report written to {output_file}")

    details_md = None
    if include_details or details_file:
        details_md = generate_details_markdown(results)

    if summary_file:
        summary_md = generate_summary_markdown(
            results,
            report,
            total_repos,
            processed,
            missing,
            missing_run_id,
            dispatched_label=dispatched_label,
            missing_label=missing_label,
            include_details=include_details,
            details_md=details_md,
        )
        summary_file.write_text(summary_md)

    if details_file and details_md is not None:
        details_file.parent.mkdir(parents=True, exist_ok=True)
        details_file.write_text(details_md)


def _check_threshold_violations(
    report: dict[str, Any],
    defaults_file: Path,
) -> tuple[bool, int, int, int, int]:
    """Check threshold violations.

    Returns:
        Tuple of (exceeded, total_critical, total_high, max_critical, max_high).
    """
    max_critical, max_high = load_thresholds(defaults_file)
    total_critical = int(report.get("total_critical_vulns", 0) or 0)
    total_high = int(report.get("total_high_vulns", 0) or 0)

    exceeded = False
    if total_critical > max_critical:
        print(f"THRESHOLD EXCEEDED: Critical vulns {total_critical} > {max_critical}")
        exceeded = True
    if total_high > max_high:
        print(f"THRESHOLD EXCEEDED: High vulns {total_high} > {max_high}")
        exceeded = True

    return exceeded, total_critical, total_high, max_critical, max_high


def _classify_runs(
    results: list[dict[str, Any]],
    failure_statuses: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify runs into passed and failed lists.

    Args:
        results: List of run status dicts.
        failure_statuses: Tuple of status values that indicate failure.

    Returns:
        Tuple of (passed_runs, failed_runs).
    """
    failed_runs = [
        r
        for r in results
        if r.get("status") in failure_statuses
        or (r.get("status") == "completed" and r.get("conclusion") != "success")
        or r.get("status") not in ("completed",)
    ]
    passed_runs = [r for r in results if r.get("status") == "completed" and r.get("conclusion") == "success"]
    return passed_runs, failed_runs


def _print_summary_banner(
    processed: int,
    passed_runs: list[dict[str, Any]],
    failed_runs: list[dict[str, Any]],
    missing: int,
    missing_run_id: int,
    threshold_exceeded: bool,
    total_critical: int,
    total_high: int,
    max_critical: int,
    max_high: int,
    *,
    processed_label: str = "Total dispatched",
    missing_label: str = "Missing metadata",
    extra_counts: dict[str, int] | None = None,
    format_failure: Any = None,  # Callable[[dict], str] or None
) -> None:
    """Print the aggregation summary banner.

    Args:
        processed: Number of processed items.
        passed_runs: List of passed run dicts.
        failed_runs: List of failed run dicts.
        missing: Count of missing items.
        missing_run_id: Count of items missing run_id.
        threshold_exceeded: Whether thresholds were exceeded.
        total_critical: Total critical vulnerabilities.
        total_high: Total high vulnerabilities.
        max_critical: Maximum allowed critical vulnerabilities.
        max_high: Maximum allowed high vulnerabilities.
        processed_label: Label for processed count.
        missing_label: Label for missing count.
        extra_counts: Additional counts to print (e.g., {"Invalid reports": 5}).
        format_failure: Optional callable to format a failure entry.
    """
    print(f"\n{'=' * 60}")
    print("AGGREGATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"{processed_label}: {processed}")
    print(f"Passed: {len(passed_runs)}")
    print(f"Failed: {len(failed_runs)}")

    if extra_counts:
        for label, count in extra_counts.items():
            if count > 0:
                print(f"{label}: {count}")

    if missing > 0:
        print(f"{missing_label}: {missing}")
    if missing_run_id > 0:
        print(f"Missing run IDs: {missing_run_id}")

    if failed_runs:
        print("\nFailed runs:")
        for r in failed_runs:
            if format_failure:
                print(f"  - {format_failure(r)}")
            else:
                repo = r.get("repo", "unknown")
                status = r.get("status", "unknown")
                conclusion = r.get("conclusion", "unknown")
                run_id = r.get("run_id", "none")
                print(f"  - {repo}: {status}/{conclusion} (run {run_id})")

    if threshold_exceeded:
        print("\nThreshold violations:")
        if total_critical > max_critical:
            print(f"  - Critical vulns: {total_critical} (max: {max_critical})")
        if total_high > max_high:
            print(f"  - High vulns: {total_high} (max: {max_high})")

    print(f"{'=' * 60}\n")


def run_aggregation(
    dispatch_dir: Path,
    output_file: Path,
    summary_file: Path | None,
    defaults_file: Path,
    token: str,
    hub_run_id: str,
    hub_event: str,
    total_repos: int,
    *,
    strict: bool = False,
    timeout_sec: int = 1800,
    details_file: Path | None = None,
    include_details: bool = False,
) -> int:
    api = GitHubAPI(token)
    entries = load_dispatch_metadata(dispatch_dir)
    results: list[dict[str, Any]] = []

    if total_repos <= 0:
        total_repos = len(entries)

    print(f"\n{'=' * 60}")
    print(f"Starting aggregation for {len(entries)} dispatched repos")
    print(f"   Hub Run ID: {hub_run_id}")
    print(f"   Total expected repos: {total_repos}")
    print(f"{'=' * 60}\n")

    for idx, entry in enumerate(entries, 1):
        repo_full = entry.get("repo", "unknown/unknown")
        owner_repo = repo_full.split("/")
        if len(owner_repo) != 2:
            print(f"Invalid repo format in entry: {repo_full}")
            continue

        owner, repo = owner_repo
        run_id_value = entry.get("run_id")
        run_id = str(run_id_value) if run_id_value else None
        workflow_value = entry.get("workflow")
        workflow = workflow_value if isinstance(workflow_value, str) else ""
        expected_corr_value = entry.get("correlation_id", "")
        expected_corr = expected_corr_value if isinstance(expected_corr_value, str) else ""

        print(f"\n[{idx}/{len(entries)}] Processing {repo_full}...")
        run_status = create_run_status(entry)

        if not run_id and expected_corr and workflow:
            print(f"No run_id for {repo_full}, searching by {expected_corr}...")
            found_run_id = find_run_by_correlation_id(owner, repo, workflow, expected_corr, token, gh_get=api.get)
            if found_run_id:
                run_id = found_run_id
                run_status["run_id"] = run_id
                run_status["status"] = "unknown"
                print(f"Found run_id {run_id} for {repo_full} via correlation_id")
            else:
                print(f"Could not find run by correlation_id for {repo_full}")

        if not run_id:
            results.append(run_status)
            continue

        status, conclusion = poll_run_completion(api, owner, repo, run_id, timeout_sec=timeout_sec)
        run_status["status"] = status
        run_status["conclusion"] = conclusion

        if status == "fetch_failed":
            results.append(run_status)
            continue

        if status == "completed":
            report_data = fetch_and_validate_artifact(api, owner, repo, run_id, expected_corr, workflow, token)
            if report_data:
                corr = report_data.get("hub_correlation_id", expected_corr)
                run_status["correlation_id"] = corr
                extract_metrics_from_report(report_data, run_status)
                # Store full report for detailed summary generation
                run_status["_report_data"] = report_data
            else:
                run_status["status"] = "missing_report"
                run_status["conclusion"] = "failure"

        results.append(run_status)

    dispatched = len(results)
    missing = max(total_repos - dispatched, 0)
    missing_run_id = len([e for e in results if not e.get("run_id")])

    # Build aggregated report using shared helper
    report = _build_aggregated_report(results, hub_run_id, hub_event, total_repos, dispatched, missing)

    # Write output files using shared helper
    _write_output_files(
        results,
        report,
        output_file,
        summary_file,
        details_file,
        total_repos,
        dispatched,
        missing,
        missing_run_id,
        include_details=include_details,
    )

    # Check thresholds using shared helper
    threshold_exceeded, total_critical, total_high, max_critical, max_high = _check_threshold_violations(
        report, defaults_file
    )

    # Classify runs using shared helper
    passed_runs, failed_runs = _classify_runs(results, ("missing_run_id", "fetch_failed", "timed_out"))

    # Custom formatter for dispatch failures
    def _format_dispatch_failure(r: dict[str, Any]) -> str:
        repo = r.get("repo", "unknown")
        status = r.get("status", "unknown")
        conclusion = r.get("conclusion", "unknown")
        run_id = r.get("run_id", "none")
        if status == "missing_run_id":
            return f"{repo}: no run_id (dispatch may have failed)"
        elif status == "timed_out":
            return f"{repo}: timed out waiting for run {run_id}"
        elif status == "fetch_failed":
            return f"{repo}: failed to fetch run {run_id}"
        return f"{repo}: {status}/{conclusion} (run {run_id})"

    # Print summary using shared helper
    _print_summary_banner(
        dispatched,
        passed_runs,
        failed_runs,
        missing,
        missing_run_id,
        threshold_exceeded,
        total_critical,
        total_high,
        max_critical,
        max_high,
        format_failure=_format_dispatch_failure,
    )

    if strict and (failed_runs or missing > 0 or threshold_exceeded):
        return 1
    return 0


def run_reports_aggregation(
    reports_dir: Path,
    output_file: Path,
    summary_file: Path | None,
    defaults_file: Path,
    hub_run_id: str,
    hub_event: str,
    total_repos: int,
    *,
    strict: bool = False,
    details_file: Path | None = None,
    include_details: bool = False,
) -> int:
    reports_dir = reports_dir.resolve()
    report_paths = sorted(reports_dir.rglob("report.json"))
    results: list[dict[str, Any]] = []
    invalid_reports = 0

    if total_repos <= 0:
        total_repos = len(report_paths)

    print(f"\n{'=' * 60}")
    print(f"Starting aggregation from reports dir: {reports_dir}")
    print(f"   Hub Run ID: {hub_run_id}")
    print(f"   Total expected repos: {total_repos}")
    print(f"{'=' * 60}\n")

    for report_path in report_paths:
        try:
            with report_path.open(encoding="utf-8") as f:
                report_data = json.load(f)
            if not isinstance(report_data, dict):
                raise ValueError("report.json is not a JSON object")
        except Exception as exc:
            invalid_reports += 1
            print(f"Warning: invalid report {report_path}: {exc}")
            results.append(_run_status_for_invalid_report(report_path, reports_dir, "invalid_report"))
            continue

        run_status = _run_status_from_report(report_data, report_path, reports_dir)
        extract_metrics_from_report(report_data, run_status)
        # Store full report for detailed summary generation
        run_status["_report_data"] = report_data
        results.append(run_status)

    processed = len(results)
    missing = max(total_repos - processed, 0)
    missing_run_id = len([e for e in results if not e.get("run_id")])

    # Build aggregated report using shared helper
    report = _build_aggregated_report(results, hub_run_id, hub_event, total_repos, processed, missing)

    # Write output files using shared helper
    _write_output_files(
        results,
        report,
        output_file,
        summary_file,
        details_file,
        total_repos,
        processed,
        missing,
        missing_run_id,
        include_details=include_details,
        dispatched_label="Reports processed",
        missing_label="Missing reports",
    )

    # Check thresholds using shared helper
    threshold_exceeded, total_critical, total_high, max_critical, max_high = _check_threshold_violations(
        report, defaults_file
    )

    # Classify runs using shared helper
    passed_runs, failed_runs = _classify_runs(results, ("invalid_report", "missing_run_id"))

    # Custom formatter for reports failures
    def _format_reports_failure(r: dict[str, Any]) -> str:
        repo = r.get("repo", "unknown")
        status = r.get("status", "unknown")
        conclusion = r.get("conclusion", "unknown")
        run_id = r.get("run_id", "none")
        if status == "missing_run_id":
            return f"{repo}: no run_id"
        elif status == "invalid_report":
            return f"{repo}: invalid report.json"
        return f"{repo}: {status}/{conclusion} (run {run_id})"

    # Print summary using shared helper
    _print_summary_banner(
        processed,
        passed_runs,
        failed_runs,
        missing,
        missing_run_id,
        threshold_exceeded,
        total_critical,
        total_high,
        max_critical,
        max_high,
        processed_label="Reports processed",
        missing_label="Missing reports",
        extra_counts={"Invalid reports": invalid_reports} if invalid_reports else None,
        format_failure=_format_reports_failure,
    )

    if strict and (failed_runs or missing > 0 or threshold_exceeded):
        return 1
    return 0
