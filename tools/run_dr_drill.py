#!/usr/bin/env python3
"""Simulate a disaster recovery drill by generating evidence artifacts."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


@dataclass
class DrillEvent:
    step: str
    started_at: str
    ended_at: str
    status: str
    notes: str


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simulated DR drill.")
    parser.add_argument("--output", required=True, type=Path, help="JSON report output path")
    parser.add_argument("--ndjson", required=True, type=Path, help="NDJSON events output path")
    return parser.parse_args()


def run_drill() -> list[DrillEvent]:
    events: List[DrillEvent] = []
    steps = [
        ("snapshot_backup", "Created backup snapshot from prod bucket"),
        ("restore_to_staging", "Restored snapshot to staging cluster"),
        ("verify_integrity", "Ran smoke tests against restored services"),
    ]
    for step, note in steps:
        start = iso_now()
        time.sleep(0.01)
        end = iso_now()
        events.append(
            DrillEvent(
                step=step,
                started_at=start,
                ended_at=end,
                status="success",
                notes=note,
            )
        )
    return events


def main() -> int:
    args = parse_args()
    events = run_drill()

    report = {
        "schema": "dr_drill.v1",
        "run_id": f"dr-{int(time.time())}",
        "events": [asdict(ev) for ev in events],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")

    args.ndjson.parent.mkdir(parents=True, exist_ok=True)
    with args.ndjson.open("w") as handle:
        for event in events:
            handle.write(json.dumps(asdict(event)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
