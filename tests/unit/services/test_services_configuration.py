# TEST-METRICS:
"""Unit tests for configuration service behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from cihub.config.loader import ConfigValidationError
from cihub.services.configuration import load_effective_config, set_tool_enabled


def test_set_tool_enabled_updates_config() -> None:
    config = {"repo": {"language": "python"}, "python": {"tools": {}}}
    defaults = {"python": {"tools": {"ruff": {"enabled": True}}}}

    path = set_tool_enabled(config, defaults, "ruff", False)

    assert path == "python.tools.ruff.enabled"
    assert config["python"]["tools"]["ruff"]["enabled"] is False


def test_set_tool_enabled_raises_for_unknown_tool() -> None:
    config = {"repo": {"language": "python"}, "python": {"tools": {}}}
    defaults = {"python": {"tools": {"ruff": {"enabled": True}}}}

    with pytest.raises(ValueError, match="Unknown tool"):
        set_tool_enabled(config, defaults, "missing", True)


def test_load_effective_config_validates_schema(tmp_path: Path) -> None:
    repo_path = tmp_path / "cihub-effective-config-test"
    repo_path.mkdir()
    (repo_path / ".ci-hub.yml").write_text(
        "repo:\n  owner: test\n  name: cihub-effective-config-test\nlanguage: python\n",
        encoding="utf-8",
    )

    config = load_effective_config(repo_path)

    assert config["repo"]["name"] == "cihub-effective-config-test"
    assert config["language"] == "python"


def test_load_effective_config_raises_on_invalid_config(tmp_path: Path) -> None:
    repo_path = tmp_path / "cihub-effective-config-invalid"
    repo_path.mkdir()
    (repo_path / ".ci-hub.yml").write_text("language: python\n", encoding="utf-8")

    with pytest.raises(ConfigValidationError):
        load_effective_config(repo_path)
