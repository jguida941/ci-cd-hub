#!/usr/bin/env python3
"""Summarize CodeQL SARIF results and optionally gate the build.

This helper collects severity counts from CodeQL SARIF files, writes a
Markdown summary, and fails when high-severity issues are detected. It is
intended to run inside CI so teams without GitHub Advanced Security can still
triage findings.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


Severity = str

SEVERITY_RANK = {"error": 3, "warning": 2, "note": 1}


@dataclass
class Finding:
    severity: Severity
    rule_id: str
    message: str
    location: str


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize CodeQL SARIF findings.")
    parser.add_argument(
        "--sarif-dir",
        type=Path,
        required=True,
        help="Directory containing CodeQL SARIF files.",
    )
    parser.add_argument(
        "--fail-on",
        choices=sorted(SEVERITY_RANK),
        default="error",
        help="Fail the script if findings at or above this severity exist.",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=20,
        help="Limit the number of findings listed in the summary table.",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("codeql-summary.md"),
        help="Path to write the Markdown summary.",
    )
    return parser.parse_args(argv)


def load_findings(sarif_dir: Path) -> List[Finding]:
    findings: List[Finding] = []
    if not sarif_dir.exists():
        raise FileNotFoundError(f"SARIF directory not found: {sarif_dir}")

    for sarif_file in sorted(sarif_dir.glob("*.sarif")):
        raw = json.loads(sarif_file.read_text())
        for run in raw.get("runs", []):
            for result in run.get("results", []):
                severity = result.get("level", "warning")
                rule_id = result.get("ruleId", "unknown-rule")
                message = result.get("message", {}).get("text", "").strip()
                location = build_location(result)
                findings.append(
                    Finding(
                        severity=severity,
                        rule_id=rule_id,
                        message=message or "<no message provided>",
                        location=location or "<no location provided>",
                    )
                )

    return findings


def build_location(result: dict) -> str:
    locations = result.get("locations") or []
    if not locations:
        return ""

    loc = locations[0]
    physical = loc.get("physicalLocation") or {}
    artifact = physical.get("artifactLocation") or {}
    file_path = artifact.get("uri", "")
    region = physical.get("region") or {}
    start_line = region.get("startLine")
    if file_path and start_line:
        return f"{file_path}:{start_line}"
    return file_path


def summarize(findings: Iterable[Finding]) -> Tuple[dict, List[Finding]]:
    counts: dict[Severity, int] = defaultdict(int)
    ordered_findings: List[Finding] = list(findings)
    ordered_findings.sort(key=lambda f: (SEVERITY_RANK.get(f.severity, 0), f.rule_id), reverse=True)

    for finding in ordered_findings:
        counts[finding.severity] += 1

    return counts, ordered_findings


def render_markdown(counts: dict, findings: List[Finding], limit: int) -> str:
    def sanitize(text: str) -> str:
        return (
            text.replace("|", "\\|")
            .replace("\n", " ")
            .replace("\r", " ")
            .strip()
        )

    lines = []
    lines.append("# CodeQL Summary\n")
    lines.append("## Severity counts\n")
    lines.append("| Severity | Count |")
    lines.append("| --- | --- |")
    for severity in sorted(SEVERITY_RANK, key=SEVERITY_RANK.get, reverse=True):
        lines.append(f"| {severity} | {counts.get(severity, 0)} |")

    if findings:
        lines.append("\n## Top findings\n")
        lines.append("| Severity | Rule | Location | Message |")
        lines.append("| --- | --- | --- | --- |")
        for finding in findings[:limit]:
            message = sanitize(finding.message)
            location = sanitize(finding.location)
            lines.append(
                f"| {finding.severity} | {sanitize(finding.rule_id)} | {location} | {message} |"
            )
    else:
        lines.append("\n_No findings detected._")

    return "\n".join(lines) + "\n"


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    findings = load_findings(args.sarif_dir)
    counts, ordered = summarize(findings)

    summary = render_markdown(counts, ordered, args.max_findings)
    args.summary_out.write_text(summary)

    print(summary)

    fail_rank = SEVERITY_RANK[args.fail_on]
    should_fail = any(SEVERITY_RANK.get(f.severity, 0) >= fail_rank for f in ordered)
    if should_fail:
        print(f"::error::CodeQL detected findings at or above severity '{args.fail_on}'.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
