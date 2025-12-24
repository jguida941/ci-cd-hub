import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.cli import (
    apply_dependency_fixes,
    apply_pom_fixes,
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
)


def write_pom(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def base_config(jqwik_enabled: bool = True) -> dict:
    return {
        "repo": {"subdir": ""},
        "java": {
            "build_tool": "maven",
            "tools": {"jqwik": {"enabled": jqwik_enabled}},
        },
    }


def base_plugin_config(tool: str) -> dict:
    return {
        "repo": {"subdir": ""},
        "java": {
            "build_tool": "maven",
            "tools": {tool: {"enabled": True}},
        },
    }


def test_collect_java_pom_warnings_missing_plugin(tmp_path: Path) -> None:
    pom_path = tmp_path / "pom.xml"
    write_pom(
        pom_path,
        """<project>
  <modelVersion>4.0.0</modelVersion>
</project>
""",
    )

    warnings, missing = collect_java_pom_warnings(
        tmp_path, base_plugin_config("jacoco")
    )

    assert warnings
    assert missing
    assert missing[0][1] == "jacoco-maven-plugin"


def test_apply_pom_fixes_inserts_plugin(tmp_path: Path) -> None:
    pom_path = tmp_path / "pom.xml"
    write_pom(
        pom_path,
        """<project>
  <modelVersion>4.0.0</modelVersion>
</project>
""",
    )

    result = apply_pom_fixes(tmp_path, base_plugin_config("jacoco"), apply=True)
    assert result == 0
    updated = pom_path.read_text(encoding="utf-8")
    assert "<artifactId>jacoco-maven-plugin</artifactId>" in updated


def test_collect_java_dependency_warnings_single_module(tmp_path: Path) -> None:
    pom_path = tmp_path / "pom.xml"
    write_pom(
        pom_path,
        """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
</project>
""",
    )

    warnings, missing = collect_java_dependency_warnings(
        tmp_path, base_config(jqwik_enabled=True)
    )

    assert warnings
    assert missing
    target, dep_id = missing[0]
    assert target == pom_path
    assert dep_id[1] == "jqwik"


def test_apply_dependency_fixes_inserts_dependency(tmp_path: Path) -> None:
    pom_path = tmp_path / "pom.xml"
    write_pom(
        pom_path,
        """<project>
  <modelVersion>4.0.0</modelVersion>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
""",
    )

    result = apply_dependency_fixes(tmp_path, base_config(jqwik_enabled=True), apply=True)
    assert result == 0
    updated = pom_path.read_text(encoding="utf-8")
    assert "<artifactId>jqwik</artifactId>" in updated


def test_apply_dependency_fixes_multi_module(tmp_path: Path) -> None:
    parent_pom = tmp_path / "pom.xml"
    module_dir = tmp_path / "module-a"
    module_dir.mkdir()
    module_pom = module_dir / "pom.xml"

    write_pom(
        parent_pom,
        """<project>
  <modelVersion>4.0.0</modelVersion>
  <packaging>pom</packaging>
  <modules>
    <module>module-a</module>
  </modules>
</project>
""",
    )
    write_pom(
        module_pom,
        """<project>
  <modelVersion>4.0.0</modelVersion>
</project>
""",
    )

    result = apply_dependency_fixes(tmp_path, base_config(jqwik_enabled=True), apply=True)
    assert result == 0
    updated = module_pom.read_text(encoding="utf-8")
    assert "<artifactId>jqwik</artifactId>" in updated
