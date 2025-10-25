#!/usr/bin/env python3
"""Normalize provenance artifacts into canonical JSON arrays."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools import provenance_io


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert DSSE provenance envelopes (JSON/JSONL) to a canonical JSON array."
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to the downloaded provenance artifact (predicate.intoto.jsonl, etc.)",
    )
    parser.add_argument(
        "--destination",
        required=True,
        type=Path,
        help="Output path for the canonical JSON array.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation level for the output JSON (default: 2).",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow empty provenance files (default: fail if no envelopes are present).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.source.exists():
        raise SystemExit(f"source provenance file not found: {args.source}")
    records = provenance_io.load_records(args.source)
    if not records and not args.allow_empty:
        raise SystemExit("provenance file does not contain any DSSE envelopes")
    provenance_io.dump_records(records, args.destination, indent=args.indent)


if __name__ == "__main__":
    try:
        main()
    except provenance_io.ProvenanceParseError as exc:
        print(f"[normalize_provenance] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
