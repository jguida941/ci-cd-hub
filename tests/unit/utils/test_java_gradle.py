"""Tests for Gradle normalization helpers."""

from __future__ import annotations

from pathlib import Path

from cihub.utils.java_gradle import normalize_gradle_configs


def test_normalize_dependencycheck_replaces_missing_suppression(tmp_path: Path) -> None:
    content = """dependencyCheck {
    def nvdKey = System.getenv('NVD_API_KEY')
    autoUpdate = nvdKey ? true : false
    suppressionFile = 'config/owasp/suppressions.xml'
}
"""
    snippets = {"org.owasp.dependencycheck": "dependencyCheck { autoUpdate = true }"}

    updated, warnings = normalize_gradle_configs(content, tmp_path, snippets)

    assert warnings == []
    assert "suppressionFile" not in updated
    assert "autoUpdate = true" in updated


def test_normalize_dependencycheck_refreshes_auto_update_guard(tmp_path: Path) -> None:
    (tmp_path / "config" / "owasp").mkdir(parents=True)
    (tmp_path / "config" / "owasp" / "suppressions.xml").write_text("<suppressions/>")

    content = """dependencyCheck {
    def nvdKey = System.getenv('NVD_API_KEY')
    autoUpdate = nvdKey ? true : false
    suppressionFile = 'config/owasp/suppressions.xml'
}
"""
    snippets = {
        "org.owasp.dependencycheck": """dependencyCheck {
    autoUpdate = true
    def suppressionPath = file('config/owasp/suppressions.xml')
    if (suppressionPath.exists()) {
        suppressionFile = suppressionPath
    }
}""",
    }

    updated, warnings = normalize_gradle_configs(content, tmp_path, snippets)

    assert warnings == []
    assert "autoUpdate = true" in updated
    assert "suppressionPath" in updated


def test_normalize_dependencycheck_replaces_auto_update_guard(tmp_path: Path) -> None:
    content = """dependencyCheck {
    def nvdKey = System.getenv('NVD_API_KEY')
    autoUpdate = nvdKey ? true : false
}
"""
    snippets = {"org.owasp.dependencycheck": "dependencyCheck { autoUpdate = true }"}

    updated, warnings = normalize_gradle_configs(content, tmp_path, snippets)

    assert warnings == []
    assert "autoUpdate = true" in updated


def test_normalize_dependencycheck_replaces_empty_api_key(tmp_path: Path) -> None:
    content = """dependencyCheck {
    def nvdKey = System.getenv('NVD_API_KEY')
    autoUpdate = true
    nvd {
        apiKey = nvdKey ?: ''
        delay = 3500
    }
}
"""
    snippets = {
        "org.owasp.dependencycheck": """dependencyCheck {
    autoUpdate = true
    nvd {
        if (nvdKey) {
            apiKey = nvdKey
        }
        delay = 3500
    }
}""",
    }

    updated, warnings = normalize_gradle_configs(content, tmp_path, snippets)

    assert warnings == []
    assert "if (nvdKey)" in updated


def test_normalize_pmd_replaces_empty_rulesets(tmp_path: Path) -> None:
    content = """pmd {
    toolVersion = '7.0.0'
    consoleOutput = true
    ruleSets = []
    ignoreFailures = false
}
"""
    snippets = {"pmd": "pmd { ruleSets = ['category/java/quickstart.xml'] }"}

    updated, warnings = normalize_gradle_configs(content, tmp_path, snippets)

    assert warnings == []
    assert "quickstart.xml" in updated


def test_normalize_pitest_infers_targets_when_missing(tmp_path: Path) -> None:
    java_path = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_path.mkdir(parents=True)
    (java_path / "App.java").write_text("package com.example;\n")

    content = """pitest {
    junit5PluginVersion = '1.2.1'
    threads = 4
}
"""
    snippets = {"info.solidsoft.pitest": content}

    updated, warnings = normalize_gradle_configs(content, tmp_path, snippets)

    assert warnings == []
    assert "targetClasses" in updated
    assert "com.example.*" in updated


def test_normalize_pitest_replaces_wildcards(tmp_path: Path) -> None:
    java_path = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_path.mkdir(parents=True)
    (java_path / "App.java").write_text("package com.example;\n")

    content = """pitest {
    junit5PluginVersion = '1.2.1'
    targetClasses = ['*']
    targetTests = ['*']
}
"""
    snippets = {"info.solidsoft.pitest": content}

    updated, warnings = normalize_gradle_configs(content, tmp_path, snippets)

    assert warnings == []
    assert "targetClasses" in updated
    assert "com.example.*" in updated
