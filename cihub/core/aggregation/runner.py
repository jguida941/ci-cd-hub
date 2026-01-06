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

    # Strip _report_data from runs for JSON output (too large), but keep for summary
    runs_for_json = [{k: v for k, v in r.items() if k != "_report_data"} for r in results]

    report: dict[str, Any] = {
        "hub_run_id": hub_run_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "triggered_by": hub_event,
        "total_repos": total_repos,
        "dispatched_repos": dispatched,
        "missing_dispatch_metadata": missing,
        "runs": runs_for_json,
    }

    aggregated = aggregate_results(results)
    report.update(aggregated)

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
            dispatched,
            missing,
            missing_run_id,
            include_details=include_details,
            details_md=details_md,
        )
        summary_file.write_text(summary_md)

    if details_file and details_md is not None:
        details_file.parent.mkdir(parents=True, exist_ok=True)
        details_file.write_text(details_md)

    max_critical, max_high = load_thresholds(defaults_file)
    total_critical = int(report.get("total_critical_vulns", 0) or 0)
    total_high = int(report.get("total_high_vulns", 0) or 0)
    threshold_exceeded = False

    if total_critical > max_critical:
        print(f"THRESHOLD EXCEEDED: Critical vulns {total_critical} > {max_critical}")
        threshold_exceeded = True
    if total_high > max_high:
        print(f"THRESHOLD EXCEEDED: High vulns {total_high} > {max_high}")
        threshold_exceeded = True

    failed_runs = [
        r
        for r in results
        if r.get("status") in ("missing_run_id", "fetch_failed", "timed_out")
        or (r.get("status") == "completed" and r.get("conclusion") != "success")
        or r.get("status") not in ("completed",)
    ]

    passed_runs = [r for r in results if r.get("status") == "completed" and r.get("conclusion") == "success"]

    print(f"\n{'=' * 60}")
    print("AGGREGATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total dispatched: {dispatched}")
    print(f"Passed: {len(passed_runs)}")
    print(f"Failed: {len(failed_runs)}")
    if missing > 0:
        print(f"Missing metadata: {missing}")
    if missing_run_id > 0:
        print(f"Missing run IDs: {missing_run_id}")

    if failed_runs:
        print("\nFailed runs:")
        for r in failed_runs:
            repo = r.get("repo", "unknown")
            status = r.get("status", "unknown")
            conclusion = r.get("conclusion", "unknown")
            run_id = r.get("run_id", "none")
            if status == "missing_run_id":
                print(f"  - {repo}: no run_id (dispatch may have failed)")
            elif status == "timed_out":
                print(f"  - {repo}: timed out waiting for run {run_id}")
            elif status == "fetch_failed":
                print(f"  - {repo}: failed to fetch run {run_id}")
            else:
                print(f"  - {repo}: {status}/{conclusion} (run {run_id})")

    if threshold_exceeded:
        print("\nThreshold violations:")
        if total_critical > max_critical:
            print(f"  - Critical vulns: {total_critical} (max: {max_critical})")
        if total_high > max_high:
            print(f"  - High vulns: {total_high} (max: {max_high})")

    print(f"{'=' * 60}\n")

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
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
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

    # Strip _report_data from runs for JSON output (too large), but keep for summary
    runs_for_json = [{k: v for k, v in r.items() if k != "_report_data"} for r in results]

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
            dispatched_label="Reports processed",
            missing_label="Missing reports",
            include_details=include_details,
            details_md=details_md,
        )
        summary_file.write_text(summary_md)

    if details_file and details_md is not None:
        details_file.parent.mkdir(parents=True, exist_ok=True)
        details_file.write_text(details_md)

    max_critical, max_high = load_thresholds(defaults_file)
    total_critical = int(report.get("total_critical_vulns", 0) or 0)
    total_high = int(report.get("total_high_vulns", 0) or 0)
    threshold_exceeded = False

    if total_critical > max_critical:
        print(f"THRESHOLD EXCEEDED: Critical vulns {total_critical} > {max_critical}")
        threshold_exceeded = True
    if total_high > max_high:
        print(f"THRESHOLD EXCEEDED: High vulns {total_high} > {max_high}")
        threshold_exceeded = True

    failed_runs = [
        r
        for r in results
        if r.get("status") in ("invalid_report", "missing_run_id")
        or (r.get("status") == "completed" and r.get("conclusion") != "success")
        or r.get("status") not in ("completed",)
    ]

    passed_runs = [r for r in results if r.get("status") == "completed" and r.get("conclusion") == "success"]

    print(f"\n{'=' * 60}")
    print("AGGREGATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Reports processed: {processed}")
    print(f"Passed: {len(passed_runs)}")
    print(f"Failed: {len(failed_runs)}")
    if invalid_reports:
        print(f"Invalid reports: {invalid_reports}")
    if missing > 0:
        print(f"Missing reports: {missing}")
    if missing_run_id > 0:
        print(f"Missing run IDs: {missing_run_id}")

    if failed_runs:
        print("\nFailed runs:")
        for r in failed_runs:
            repo = r.get("repo", "unknown")
            status = r.get("status", "unknown")
            conclusion = r.get("conclusion", "unknown")
            run_id = r.get("run_id", "none")
            if status == "missing_run_id":
                print(f"  - {repo}: no run_id")
            elif status == "invalid_report":
                print(f"  - {repo}: invalid report.json")
            else:
                print(f"  - {repo}: {status}/{conclusion} (run {run_id})")

    if threshold_exceeded:
        print("\nThreshold violations:")
        if total_critical > max_critical:
            print(f"  - Critical vulns: {total_critical} (max: {max_critical})")
        if total_high > max_high:
            print(f"  - High vulns: {total_high} (max: {max_high})")

    print(f"{'=' * 60}\n")

    if strict and (failed_runs or missing > 0 or threshold_exceeded):
        return 1
    return 0
