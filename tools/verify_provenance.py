import base64
import json
import os
import pathlib
import sys

from tools import provenance_io


def normalize(digest):
    if not digest:
        return ""
    digest = digest.lower()
    return digest if digest.startswith("sha256:") else f"sha256:{digest}"


def collect_subjects(records):
    subjects = []
    for envelope in records:
        current = envelope.get("subject")
        if not current:
            payload = envelope.get("payload")
            if not isinstance(payload, str):
                raise SystemExit("provenance payload missing")
            try:
                decoded = json.loads(base64.b64decode(payload + "==").decode("utf-8"))
            except Exception as exc:
                raise SystemExit(f"failed to decode DSSE payload: {exc}")
            current = decoded.get("subject")
        if current:
            subjects.extend(current)
    return subjects


def main() -> None:
    expected = normalize(os.environ.get("EXPECTED_DIGEST"))
    if not expected:
        raise SystemExit("expected digest missing")

    path = pathlib.Path("artifacts/slsa-provenance.json")
    if not path.exists():
        raise SystemExit("provenance file missing")

    try:
        records = provenance_io.load_records(path)
    except provenance_io.ProvenanceParseError as exc:
        raise SystemExit(f"provenance not valid JSON: {exc}") from exc
    if not records:
        raise SystemExit("provenance file empty")

    subjects = collect_subjects(records)
    if not subjects:
        raise SystemExit("provenance subject missing")

    for subj in subjects:
        digest = normalize((subj.get("digest") or {}).get("sha256"))
        if digest == expected:
            return

    existing = [normalize((subj.get("digest") or {}).get("sha256")) for subj in subjects]
    raise SystemExit(f"provenance digest mismatch: expected {expected}, subjects {existing}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise
