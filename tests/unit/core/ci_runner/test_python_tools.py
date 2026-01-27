from __future__ import annotations

from types import SimpleNamespace

from cihub.core.ci_runner import python_tools


def _stub_run_tool_command(calls):
    def _run(tool: str, cmd: list[str], workdir, output_dir, env=None, timeout=None):
        calls.append(cmd)
        report_path = output_dir / "pip-audit-report.json"
        report_path.write_text("{\"dependencies\": []}", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return _run


def test_run_pip_audit_uses_requirements_files(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(python_tools.shared, "_run_tool_command", _stub_run_tool_command(calls))

    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = python_tools.run_pip_audit(workdir, output_dir)

    assert result.ran is True
    cmd = calls[0] if calls else []
    command = " ".join(cmd)
    assert "-r" in command
    assert "requirements.txt" in command
    assert cmd[-1].endswith("requirements.txt")


def test_run_pip_audit_uses_project_path_when_no_requirements(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(python_tools.shared, "_run_tool_command", _stub_run_tool_command(calls))

    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = python_tools.run_pip_audit(workdir, output_dir)

    assert result.ran is True
    command = " ".join(calls[0]) if calls else ""
    assert str(workdir) in command


def test_run_pip_audit_setup_py_falls_back_to_empty_requirements(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(python_tools.shared, "_run_tool_command", _stub_run_tool_command(calls))

    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "setup.py").write_text("from setuptools import setup\nsetup(name='demo')\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = python_tools.run_pip_audit(workdir, output_dir)

    assert result.ran is True
    cmd = calls[0] if calls else []
    assert "-r" in cmd
    assert any(str(output_dir) in arg and "pip-audit-requirements.txt" in arg for arg in cmd)
