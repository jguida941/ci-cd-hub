"""Contract parsing helpers for the AI loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cihub.commands.ai_loop_types import Contract


def load_contract(path: Path | None, strict: bool) -> Contract | None:
    if path is None:
        return None
    text = path.read_text(encoding="utf-8")
    meta, _body = _parse_front_matter(text)
    meta = meta or {}
    if strict:
        if not isinstance(meta, dict):
            raise ValueError("Contract file must include YAML front matter")
        if "output_promise" not in meta:
            raise ValueError("Contract file missing output_promise")
        if "success_criteria" not in meta:
            raise ValueError("Contract file missing success_criteria")

    output_promise = meta.get("output_promise") if isinstance(meta, dict) else None
    success_criteria = meta.get("success_criteria", []) if isinstance(meta, dict) else []
    safety_rules = meta.get("safety_rules", []) if isinstance(meta, dict) else []
    if isinstance(success_criteria, dict):
        success_criteria = [success_criteria]
    if isinstance(safety_rules, str):
        safety_rules = [safety_rules]

    return Contract(
        raw=meta if isinstance(meta, dict) else {},
        output_promise=str(output_promise) if output_promise else None,
        success_criteria=[item for item in success_criteria if isinstance(item, dict)],
        safety_rules=[item for item in safety_rules if isinstance(item, str)],
    )


def _parse_front_matter(text: str) -> tuple[dict[str, Any] | None, str]:
    if not text.lstrip().startswith("---"):
        return None, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index is None:
        return None, text
    meta_text = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    try:
        meta = yaml.safe_load(meta_text) if meta_text.strip() else {}
    except yaml.YAMLError as exc:  # noqa: BLE001
        raise ValueError(f"Invalid YAML front matter: {exc}") from exc
    if not isinstance(meta, dict):
        meta = {}
    return meta, body
