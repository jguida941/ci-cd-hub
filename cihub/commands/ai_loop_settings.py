"""Settings resolution for the AI loop."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from cihub.commands.ai_loop_contracts import load_contract
from cihub.commands.ai_loop_types import AI_LOOP_CONFIG, LoopSettings


def resolve_settings(args: argparse.Namespace) -> LoopSettings:
    repo_path = Path(getattr(args, "repo", None) or ".").resolve()
    output_root = Path(getattr(args, "output_dir", None) or ".cihub/ai-loop")
    if not output_root.is_absolute():
        output_root = repo_path / output_root
    output_root = output_root.resolve()

    max_iterations = getattr(args, "max_iterations", AI_LOOP_CONFIG["max_iterations"])
    unsafe_unlimited = bool(getattr(args, "unsafe_unlimited", False))
    if max_iterations is not None and max_iterations <= 0 and not unsafe_unlimited:
        raise ValueError("--max-iterations must be positive unless --unsafe-unlimited is set")
    if unsafe_unlimited:
        max_iterations = None

    max_minutes = getattr(args, "max_minutes", 60)
    if max_minutes is None or max_minutes <= 0:
        raise ValueError("--max-minutes must be positive")
    max_duration_seconds = int(max_minutes * 60)

    contract_file = getattr(args, "contract_file", None)
    contract_strict = bool(getattr(args, "contract_strict", False))
    contract = load_contract(Path(contract_file) if contract_file else None, contract_strict)

    review_command = getattr(args, "review_command", None) or os.environ.get("CIHUB_AI_REVIEW_CMD")

    bundle_dir = getattr(args, "bundle_dir", None)
    if bundle_dir:
        bundle_path = Path(bundle_dir)
        if not bundle_path.is_absolute():
            bundle_path = repo_path / bundle_path
        bundle_path = bundle_path.resolve()
    else:
        bundle_path = None

    triage_output_dir = getattr(args, "triage_output_dir", None)
    if triage_output_dir:
        triage_path = Path(triage_output_dir)
        if not triage_path.is_absolute():
            triage_path = repo_path / triage_path
        triage_path = triage_path.resolve()
    else:
        triage_path = None

    return LoopSettings(
        repo_path=repo_path,
        output_root=output_root,
        max_iterations=max_iterations,
        fix_mode=getattr(args, "fix_mode", "safe"),
        emit_report=bool(getattr(args, "emit_report", False)),
        max_duration_seconds=max_duration_seconds,
        unsafe_unlimited=unsafe_unlimited,
        resume=bool(getattr(args, "resume", False)),
        contract=contract,
        contract_strict=contract_strict,
        review_command=review_command,
        artifact_pack=bool(getattr(args, "artifact_pack", False)),
        bundle_dir=bundle_path,
        remote=bool(getattr(args, "remote", False)),
        remote_provider=getattr(args, "remote_provider", "gh"),
        remote_repo=getattr(args, "remote_repo", None),
        workflow=getattr(args, "workflow", None),
        push=bool(getattr(args, "push", False)),
        push_remote=getattr(args, "push_remote", "origin"),
        push_branch=getattr(args, "push_branch", "ai/ci-loop"),
        allow_protected_branch=bool(getattr(args, "allow_protected_branch", False)),
        allow_dirty=bool(getattr(args, "allow_dirty", False)),
        commit=bool(getattr(args, "commit", False)),
        commit_message=getattr(args, "commit_message", "AI loop iteration"),
        triage_mode=getattr(args, "triage_mode", "auto"),
        triage_run_id=getattr(args, "triage_run_id", None),
        triage_output_dir=triage_path,
        fallback=getattr(args, "fallback", "stop"),
        remote_dry_run=bool(getattr(args, "remote_dry_run", False)),
        correlation_id=getattr(args, "correlation_id", None),
        config_from_hub=getattr(args, "config_from_hub", None),
        workdir=getattr(args, "workdir", None),
    )
