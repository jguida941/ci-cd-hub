"""Artifact retrieval helpers for aggregation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from cihub.core.correlation import find_run_by_correlation_id, validate_correlation_id

from .github_api import GitHubAPI


def fetch_and_validate_artifact(
    api: GitHubAPI,
    owner: str,
    repo: str,
    run_id: str,
    expected_correlation_id: str,
    workflow: str,
    token: str,
) -> dict[str, Any] | None:
    try:
        print(f"   Fetching artifacts for run {run_id}...")
        artifacts = api.get(f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts")
        ci_artifacts = artifacts.get("artifacts", [])
        print(f"   Found {len(ci_artifacts)} artifact(s)")

        artifact = next((a for a in ci_artifacts if a.get("name", "").endswith("ci-report")), None)
        if not artifact and ci_artifacts:
            artifact = next(
                (a for a in ci_artifacts if "report" in a.get("name", "")),
                ci_artifacts[0] if ci_artifacts else None,
            )

        if not artifact:
            print(f"   WARNING: No ci-report artifact found for {owner}/{repo}")
            if ci_artifacts:
                names = [a.get("name", "?") for a in ci_artifacts]
                print(f"   Available artifacts: {names}")
            return None

        print(f"   Using artifact: {artifact.get('name')}")

        with tempfile.TemporaryDirectory() as tmpdir:
            dl_url = artifact["archive_download_url"]
            extracted = api.download_artifact(dl_url, Path(tmpdir))
            if not extracted:
                return None

            report_file = next(iter(Path(extracted).rglob("report.json")), None)
            if not report_file or not report_file.exists():
                print("   WARNING: No report.json found in artifact")
                return None

            with report_file.open(encoding="utf-8") as f:
                report_data = json.load(f)
            if not isinstance(report_data, dict):
                print("   WARNING: report.json is not a JSON object")
                return None
            report_corr_value = report_data.get("hub_correlation_id", "")
            report_corr = report_corr_value if isinstance(report_corr_value, str) else ""

            if expected_correlation_id:
                print(f"   Validating correlation: expected={expected_correlation_id}, got={report_corr or '(none)'}")
            if not validate_correlation_id(expected_correlation_id, report_corr):
                print(
                    f"Correlation mismatch for {owner}/{repo} run {run_id} "
                    f"(expected {expected_correlation_id}, got {report_corr})"
                )

                correct_run_id = find_run_by_correlation_id(
                    owner,
                    repo,
                    workflow,
                    expected_correlation_id,
                    token,
                    gh_get=api.get,
                )

                if correct_run_id and correct_run_id != run_id:
                    print(f"Found correct run {correct_run_id}, re-fetching...")
                    return fetch_and_validate_artifact(api, owner, repo, correct_run_id, "", workflow, token)
                print(f"Could not find correct run for {owner}/{repo}")
                return None

            print("   Correlation OK, extracting metrics...")
            return report_data

    except Exception as exc:
        print(f"Warning: failed to fetch artifacts for run {run_id}: {exc}")
        return None
