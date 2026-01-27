from __future__ import annotations

from types import SimpleNamespace

from cihub.core.ci_runner import java_tools


def _stub_run_tool_command(calls: list[list[str]]):
    def _run(tool: str, cmd: list[str], workdir, output_dir, env=None, timeout=None):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return _run


def test_run_owasp_uses_aggregate_for_multi_module(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(java_tools.shared, "_run_tool_command", _stub_run_tool_command(calls))
    monkeypatch.setattr(java_tools.shared, "_find_files", lambda *args, **kwargs: [])
    monkeypatch.setattr("cihub.utils.project.detect_java_project_type", lambda _: "Multi-module (2 modules)")

    workdir = tmp_path / "repo"
    workdir.mkdir()
    output_dir = tmp_path / "out"

    result = java_tools.run_owasp(workdir, output_dir, "maven", use_nvd_api_key=False)

    assert result.ran is True
    assert any("dependency-check-maven:9.0.9:aggregate" in " ".join(cmd) for cmd in calls)


def test_run_owasp_uses_check_for_single_module(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(java_tools.shared, "_run_tool_command", _stub_run_tool_command(calls))
    monkeypatch.setattr(java_tools.shared, "_find_files", lambda *args, **kwargs: [])
    monkeypatch.setattr("cihub.utils.project.detect_java_project_type", lambda _: "Single module")

    workdir = tmp_path / "repo"
    workdir.mkdir()
    output_dir = tmp_path / "out"

    result = java_tools.run_owasp(workdir, output_dir, "maven", use_nvd_api_key=False)

    assert result.ran is True
    assert any("dependency-check-maven:9.0.9:check" in " ".join(cmd) for cmd in calls)


def test_run_owasp_uses_output_dir_report(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(java_tools.shared, "_run_tool_command", _stub_run_tool_command(calls))

    workdir = tmp_path / "repo"
    workdir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    report_path = output_dir / "dependency-check-report.json"
    report_path.write_text("{\"dependencies\": []}", encoding="utf-8")

    def _fake_find_files(search_dir, patterns):
        if search_dir == output_dir:
            return [report_path]
        return []

    monkeypatch.setattr(java_tools.shared, "_find_files", _fake_find_files)
    monkeypatch.setattr("cihub.utils.project.detect_java_project_type", lambda _: "Single module")

    result = java_tools.run_owasp(workdir, output_dir, "maven", use_nvd_api_key=False)

    assert result.metrics.get("report_found") is True
    assert result.artifacts.get("report") == str(report_path)


def test_run_owasp_uses_pom_plugin_version(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(java_tools.shared, "_run_tool_command", _stub_run_tool_command(calls))
    monkeypatch.setattr(java_tools.shared, "_find_files", lambda *args, **kwargs: [])
    monkeypatch.setattr("cihub.utils.project.detect_java_project_type", lambda _: "Single module")

    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "pom.xml").write_text(
        """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>1.0.0</version>
  <build>
    <plugins>
      <plugin>
        <groupId>org.owasp</groupId>
        <artifactId>dependency-check-maven</artifactId>
        <version>12.1.9</version>
      </plugin>
    </plugins>
  </build>
</project>
""",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = java_tools.run_owasp(workdir, output_dir, "maven", use_nvd_api_key=False)

    assert result.ran is True
    command = " ".join(calls[0]) if calls else ""
    assert "dependency-check-maven:check" in command
    assert ":9.0.9:" not in command


def test_run_pitest_uses_pom_plugin_version(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(java_tools.shared, "_run_tool_command", _stub_run_tool_command(calls))
    monkeypatch.setattr(java_tools.shared, "_find_files", lambda *args, **kwargs: [])

    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "pom.xml").write_text(
        """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>1.0.0</version>
  <build>
    <plugins>
      <plugin>
        <groupId>org.pitest</groupId>
        <artifactId>pitest-maven</artifactId>
        <version>1.22.0</version>
      </plugin>
    </plugins>
  </build>
</project>
""",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = java_tools.run_pitest(workdir, output_dir, "maven")

    assert result.ran is True
    command = " ".join(calls[0]) if calls else ""
    assert "pitest-maven:mutationCoverage" in command
    assert ":1.15.3:" not in command
