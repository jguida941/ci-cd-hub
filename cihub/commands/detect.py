"""Detect command handler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cihub.cli import resolve_language


def cmd_detect(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    language, reasons = resolve_language(repo_path, args.language)
    payload: dict[str, Any] = {"language": language}
    if args.explain:
        payload["reasons"] = reasons
    print(json.dumps(payload, indent=2))
    return 0
