#!/usr/bin/env python3
"""Generate issuer/subject policy input from cosign verification output."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple


def _parse_identity(stdout: str) -> Tuple[str, str]:
    issuer: str | None = None
    subject: str | None = None
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if "certificate identity:" in lowered:
            _, _, remainder = line.partition(":")
            subject = remainder.strip()
        elif "certificate oidc issuer:" in lowered or "certificate issuer:" in lowered:
            _, _, remainder = line.partition(":")
            issuer = remainder.strip()
    if not issuer or not subject:
        raise ValueError("unable to parse issuer/subject from cosign output")
    return issuer, subject


def _verify_signature(
    image: str,
    expected_subject: str | None,
    expected_issuer: str | None,
) -> Tuple[str, str]:
    cmd = ["cosign", "verify", image]
    if expected_subject:
        cmd.extend(["--certificate-identity", expected_subject])
    else:
        cmd.extend(["--certificate-identity-regexp", ".*"])
    if expected_issuer:
        cmd.extend(["--certificate-oidc-issuer", expected_issuer])
    else:
        cmd.extend(["--certificate-oidc-issuer-regexp", ".*"])
    env = dict(os.environ)
    env.setdefault("COSIGN_EXPERIMENTAL", "1")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - surfaced in CI logs
        raise SystemExit(
            f"[build_issuer_subject_input] cosign verify failed: {exc.stderr or exc.stdout}"
        ) from exc
    return _parse_identity(result.stdout)


def build_input(
    image: str,
    output_path: Path,
    allowed_issuer_regex: str,
    allowed_subject_regex: str,
    expected_subject: str | None,
    expected_issuer: str | None,
) -> Tuple[str, str]:
    issuer, subject = _verify_signature(
        image=image,
        expected_subject=expected_subject,
        expected_issuer=expected_issuer,
    )
    payload = {
        "issuer": issuer,
        "subject": subject,
        "policy": {
            "allowed_issuer_regex": allowed_issuer_regex,
            "allowed_subject_regex": allowed_subject_regex,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    return issuer, subject


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate issuer/subject policy input by verifying a cosigned image"
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Full registry reference to the signed image (including digest)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination path for the issuer/subject JSON payload",
    )
    parser.add_argument(
        "--allowed-issuer-regex",
        required=True,
        help="Regex enforced by the issuer/subject policy for issuer values",
    )
    parser.add_argument(
        "--allowed-subject-regex",
        required=True,
        help="Regex enforced by the issuer/subject policy for subject values",
    )
    parser.add_argument(
        "--expected-subject",
        help="Optional subject to enforce via cosign --certificate-identity",
    )
    parser.add_argument(
        "--expected-issuer",
        help="Optional issuer to enforce via cosign --certificate-oidc-issuer",
    )
    args = parser.parse_args()
    build_input(
        image=args.image,
        output_path=args.output,
        allowed_issuer_regex=args.allowed_issuer_regex,
        allowed_subject_regex=args.allowed_subject_regex,
        expected_subject=args.expected_subject,
        expected_issuer=args.expected_issuer,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover - developer convenience
        sys.exit(130)
