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
