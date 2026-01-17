"""Remote triage bundle generation for GitHub Actions runs.

This module provides functions for generating triage bundles from
remote GitHub Actions workflow runs, supporting both single and
multi-report modes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.services.triage_service import (
    TRIAGE_SCHEMA_VERSION,
    TriageBundle,
    _build_markdown,
    _sort_failures,
    _timestamp,
    aggregate_triage_bundles,
    generate_triage_bundle,
)

from .artifacts import find_all_reports_in_artifacts, find_report_in_artifacts
from .github import (
    download_artifacts,
    fetch_failed_logs,
    fetch_run_info,
    get_current_repo,
)
from .log_parser import parse_log_failures, resolve_unknown_steps


def generate_remote_triage_bundle(
    run_id: str,
    repo: str | None,
    output_dir: Path,
    *,
    force_aggregate: bool = False,
    force_per_repo: bool = False,
) -> TriageBundle | tuple[dict[str, Path], dict[str, Any]]:
    """Generate triage bundle from a remote GitHub workflow run.

    Strategy:
    1. Download artifacts to persistent path: {output_dir}/runs/{run_id}/artifacts/
    2. Auto-detect report.json files:
       - 1 report  → single triage bundle (returns TriageBundle)
       - N reports → multi-triage aggregation (returns artifacts dict + result dict)
    3. If no artifacts, fall back to parsing log output (returns TriageBundle)

    Args:
        run_id: GitHub workflow run ID
        repo: Repository in owner/repo format
        output_dir: Output directory for triage artifacts
        force_aggregate: Force aggregated output for multi-report mode
        force_per_repo: Force per-repo output for multi-report mode (separate bundles)

    Returns:
        TriageBundle for single-report or log-fallback mode.
        tuple[dict, dict] for multi-report mode (artifacts, result_data).
    """
    run_info = fetch_run_info(run_id, repo)
    notes: list[str] = [f"Analyzed from remote run: {run_id}"]

    # Persistent artifact storage
    run_dir = output_dir / "runs" / run_id
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    has_artifacts = download_artifacts(run_id, repo, artifacts_dir)

    if has_artifacts:
        # Find ALL report.json files (may be multiple for orchestrator runs)
        report_paths = find_all_reports_in_artifacts(artifacts_dir)

        if len(report_paths) > 1:
            # Multi-report mode: aggregate all reports (unless per-repo mode)
            notes.append(f"Found {len(report_paths)} reports")
            bundles: list[TriageBundle] = []
            per_repo_paths: dict[str, Path] = {}

            for report_path in report_paths:
                meta = {
                    "command": f"cihub triage --run {run_id}",
                    "args": [],
                    "correlation_id": run_id,
                    "repo": repo or get_current_repo() or "",
                    "branch": run_info.get("headBranch", ""),
                    "commit_sha": run_info.get("headSha", ""),
                    "workflow_ref": run_info.get("url", ""),
                }
                bundle = generate_triage_bundle(
                    output_dir=report_path.parent,
                    report_path=report_path,
                    meta=meta,
                )
                bundles.append(bundle)

                # Write individual bundle if per-repo mode
                if force_per_repo:
                    # Use artifact folder name as identifier
                    repo_name = report_path.parent.name
                    triage_path = run_dir / f"triage-{repo_name}.json"
                    md_path = run_dir / f"triage-{repo_name}.md"
                    triage_path.write_text(json.dumps(bundle.triage, indent=2), encoding="utf-8")
                    md_path.write_text(bundle.markdown, encoding="utf-8")
                    per_repo_paths[repo_name] = triage_path

            # Per-repo mode: return index of individual bundles
            if force_per_repo:
                index_path = run_dir / "triage-index.json"
                index_data = {
                    "run_id": run_id,
                    "repo_count": len(bundles),
                    "bundles": {name: str(path) for name, path in per_repo_paths.items()},
                }
                index_path.write_text(json.dumps(index_data, indent=2), encoding="utf-8")

                artifacts_out = {
                    "index": index_path,
                    "artifacts_dir": artifacts_dir,
                    **{f"triage_{name}": path for name, path in per_repo_paths.items()},
                }
                result_data = {
                    "mode": "per-repo",
                    "repo_count": len(bundles),
                    "passed_count": sum(1 for b in bundles if b.triage.get("status") == "success"),
                    "failed_count": sum(1 for b in bundles if b.triage.get("status") == "failure"),
                    "bundles": list(per_repo_paths.keys()),
                }
                return artifacts_out, result_data

            # Aggregate and write multi-triage output (default)
            result = aggregate_triage_bundles(bundles)
            multi_triage_path = run_dir / "multi-triage.json"
            multi_md_path = run_dir / "multi-triage.md"

            multi_triage_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
            multi_md_path.write_text(result.summary_markdown, encoding="utf-8")

            artifacts_out = {
                "multi_triage": multi_triage_path,
                "multi_markdown": multi_md_path,
                "artifacts_dir": artifacts_dir,
            }
            return artifacts_out, result.to_dict()

        elif len(report_paths) == 1:
            # Single report mode
            report_path = report_paths[0]
            notes.append(f"Using structured artifacts from: {report_path.parent}")

            meta = {
                "command": f"cihub triage --run {run_id}",
                "args": [],
                "correlation_id": run_id,
                "repo": repo or get_current_repo() or "",
                "branch": run_info.get("headBranch", ""),
                "commit_sha": run_info.get("headSha", ""),
                "workflow_ref": run_info.get("url", ""),
            }
            bundle = generate_triage_bundle(
                output_dir=report_path.parent,
                report_path=report_path,
                meta=meta,
            )
            # Add notes about artifact source
            triage_data = dict(bundle.triage)
            triage_data["notes"] = notes + (triage_data.get("notes") or [])
            triage_data["paths"]["artifacts_dir"] = str(artifacts_dir)
            return TriageBundle(
                triage=triage_data,
                priority=bundle.priority,
                markdown=_build_markdown(triage_data, max_failures=20),
                history_entry=bundle.history_entry,
            )

    # Fall back to log parsing if no artifacts
    notes.append("No artifacts found, using log parsing")
    logs = fetch_failed_logs(run_id, repo)
    failures = parse_log_failures(logs, run_id, repo)
    failures, resolved = resolve_unknown_steps(failures, run_info.get("jobs") or [])
    if resolved:
        notes.append(f"Resolved {resolved} UNKNOWN STEP entries using run metadata")
    priority = _sort_failures(failures)

    run_data = {
        "correlation_id": run_id,
        "repo": repo or get_current_repo() or "",
        "commit_sha": run_info.get("headSha", ""),
        "branch": run_info.get("headBranch", ""),
        "run_id": run_id,
        "workflow_name": run_info.get("name", ""),
        "workflow_url": run_info.get("url", ""),
        "command": f"cihub triage --run {run_id}",
        "args": [],
    }

    failure_count = len([f for f in failures if f.get("status") == "failed"])

    summary = {
        "overall_status": run_info.get("conclusion", "failure"),
        "failure_count": failure_count,
        "warning_count": 0,
        "info_count": 0,
        "evidence_error_count": 0,
        "skipped_count": 0,
        "required_not_run_count": 0,
        "tool_counts": {"configured": 0, "ran": 0},
    }

    triage = {
        "schema_version": TRIAGE_SCHEMA_VERSION,
        "generated_at": _timestamp(),
        "run": run_data,
        "paths": {
            "output_dir": str(run_dir),
            "artifacts_dir": str(artifacts_dir),
            "report_path": "",
            "summary_path": "",
        },
        "summary": summary,
        "tool_evidence": [],
        "evidence_issues": [],
        "failures": priority,
        "warnings": [],
        "notes": notes,
    }

    priority_payload = {
        "schema_version": "cihub-priority-v1",
        "failures": priority,
    }

    history_entry = {
        "timestamp": triage["generated_at"],
        "correlation_id": run_id,
        "output_dir": str(run_dir),
        "overall_status": summary["overall_status"],
        "failure_count": summary["failure_count"],
    }

    markdown = _build_markdown(triage, max_failures=20)

    return TriageBundle(
        triage=triage,
        priority=priority_payload,
        markdown=markdown,
        history_entry=history_entry,
    )


def generate_multi_report_triage(
    reports_dir: Path,
    output_dir: Path,
) -> tuple[dict[str, Path], dict[str, Any]]:
    """Generate triage for multiple report.json files in a directory.

    Args:
        reports_dir: Directory containing report.json files
        output_dir: Output directory for aggregated results

    Returns:
        Tuple of (artifacts dict, multi-triage result dict)
    """
    bundles: list[TriageBundle] = []

    # Find all report.json files
    for report_path in reports_dir.rglob("report.json"):
        # Use the report's parent directory as output_dir context
        report_output_dir = report_path.parent
        bundle = generate_triage_bundle(
            output_dir=report_output_dir,
            report_path=report_path,
            meta={"command": "cihub triage --multi"},
        )
        bundles.append(bundle)

    if not bundles:
        raise RuntimeError(f"No report.json files found in {reports_dir}")

    # Aggregate bundles
    result = aggregate_triage_bundles(bundles)

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    multi_triage_path = output_dir / "multi-triage.json"
    multi_md_path = output_dir / "multi-triage.md"

    multi_triage_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    multi_md_path.write_text(result.summary_markdown, encoding="utf-8")

    artifacts = {
        "multi_triage": multi_triage_path,
        "multi_markdown": multi_md_path,
    }

    return artifacts, result.to_dict()


def triage_single_run(run_id: str, repo: str | None, output_dir: Path) -> str | None:
    """Triage a single run and return the output path.

    Args:
        run_id: GitHub workflow run ID
        repo: Repository in OWNER/REPO format
        output_dir: Base output directory

    Returns:
        Path to triage.json, or None if no triage was generated
    """
    run_dir = output_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Download artifacts
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    download_artifacts(run_id, repo, artifacts_dir)

    # Fetch run info for metadata
    run_info = fetch_run_info(run_id, repo)

    # Find report.json in artifacts
    report_path = find_report_in_artifacts(artifacts_dir)

    # Explicit None check - raise if no report found (caller handles CommandResult)
    if report_path is None:
        raise FileNotFoundError(f"No report.json found in artifacts for run {run_id} (searched: {artifacts_dir})")

    # Build metadata
    meta = {
        "command": f"cihub triage --run {run_id}",
        "args": [],
        "correlation_id": run_id,
        "repo": repo or get_current_repo() or "",
        "branch": run_info.get("headBranch", ""),
        "commit_sha": run_info.get("headSha", ""),
        "workflow_ref": run_info.get("url", ""),
    }

    # Generate triage bundle
    bundle = generate_triage_bundle(
        output_dir=artifacts_dir if report_path else run_dir,
        report_path=report_path,
        meta=meta,
    )

    # Write outputs
    triage_path = run_dir / "triage.json"
    priority_path = run_dir / "priority.json"
    md_path = run_dir / "triage.md"
    history_path = run_dir / "history.jsonl"

    triage_path.write_text(json.dumps(bundle.triage, indent=2), encoding="utf-8")
    priority_path.write_text(json.dumps(bundle.priority, indent=2), encoding="utf-8")
    md_path.write_text(bundle.markdown, encoding="utf-8")

    # Append to history
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(bundle.history_entry) + "\n")

    return str(triage_path)


# Backward compatibility aliases (with underscore prefix)
_generate_remote_triage_bundle = generate_remote_triage_bundle
_generate_multi_report_triage = generate_multi_report_triage
_triage_single_run = triage_single_run


__all__ = [
    "generate_multi_report_triage",
    "generate_remote_triage_bundle",
    "triage_single_run",
    # Backward compatibility
    "_generate_multi_report_triage",
    "_generate_remote_triage_bundle",
    "_triage_single_run",
]
