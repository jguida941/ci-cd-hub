"""Helpers for reading and writing DSSE provenance envelopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List


class ProvenanceParseError(RuntimeError):
    """Raised when the provenance artifact cannot be decoded."""


def _parse_standard_json(text: str) -> List[dict] | None:
    """Try to parse canonical JSON (object or array)."""
    if not text.strip():
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ProvenanceParseError("provenance JSON must be an object or array")


def _parse_json_lines(text: str) -> List[dict]:
    """Parse newline-delimited JSON envelopes."""
    decoder = json.JSONDecoder()
    records = []
    idx = 0
    length = len(text)
    while idx < length:
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break
        try:
            obj, offset = decoder.raw_decode(text, idx)
        except json.JSONDecodeError as exc:
            raise ProvenanceParseError(f"provenance not valid JSON: {exc}") from exc
        records.append(obj)
        idx = offset
    return records


def load_records(path: Path) -> List[dict]:
    """Load DSSE envelopes from a file."""
    text = path.read_text(encoding="utf-8")
    parsed = _parse_standard_json(text)
    if parsed is not None:
        return parsed
    return _parse_json_lines(text)


def dump_records(records: Iterable[dict], path: Path, indent: int = 2) -> None:
    """Write DSSE envelopes as a canonical JSON array."""
    payload = json.dumps(list(records), indent=indent) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
