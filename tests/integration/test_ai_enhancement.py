"""Integration tests for AI enhancement hooks."""

# TEST-METRICS:

from __future__ import annotations

from types import SimpleNamespace

from cihub.commands import check as check_module
from cihub.commands import report as report_module
from cihub.commands.triage import cmd_triage
from cihub.types import CommandResult


def _stub_success(*_args, **_kwargs) -> CommandResult:
    return CommandResult(exit_code=0, summary="ok")


def test_triage_ai_enhancement_gate_history(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("cihub.ai.enhance.is_ai_available", lambda *_args, **_kwargs: False)

    args = SimpleNamespace(
        output_dir=str(tmp_path),
        gate_history=True,
        ai=True,
        json=True,
    )

    result = cmd_triage(args)
    assert any("unavailable" in s.get("message", "") for s in result.suggestions)


def test_check_ai_enhancement(monkeypatch) -> None:
    monkeypatch.setattr(check_module, "cmd_preflight", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs", _stub_success)
    monkeypatch.setattr(check_module, "cmd_smoke", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs_links", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs_audit", _stub_success)
    monkeypatch.setattr(check_module, "cmd_adr", _stub_success)
    monkeypatch.setattr(check_module, "_run_process", _stub_success)
    monkeypatch.setattr(check_module, "_run_optional", _stub_success)
    monkeypatch.setattr(check_module, "_run_zizmor", _stub_success)
    monkeypatch.setattr("cihub.ai.enhance.is_ai_available", lambda *_args, **_kwargs: False)

    args = SimpleNamespace(
        json=True,
        ai=True,
        smoke_repo=None,
        smoke_subdir=None,
        install_deps=False,
        relax=False,
        keep=False,
        audit=False,
        security=False,
        full=False,
        mutation=False,
        all=False,
    )

    result = check_module.cmd_check(args)
    assert any("unavailable" in s.get("message", "") for s in result.suggestions)


def test_report_ai_enhancement_summary(monkeypatch, tmp_path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(report_module, "render_summary_from_path", lambda _path: "summary")
    monkeypatch.setattr(report_module, "_resolve_write_summary", lambda _value: False)
    monkeypatch.setattr("cihub.ai.enhance.is_ai_available", lambda *_args, **_kwargs: False)

    args = SimpleNamespace(
        subcommand="summary",
        report=str(report_path),
        output=None,
        write_github_summary=False,
        ai=True,
    )

    result = report_module.cmd_report(args)
    assert any("unavailable" in s.get("message", "") for s in result.suggestions)
