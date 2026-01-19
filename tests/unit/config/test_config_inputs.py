"""Tests for config input overrides."""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path

import pytest

from cihub.config.inputs import ConfigInputError, load_config_override


def test_load_config_override_from_json() -> None:
    payload = load_config_override('{"language": "python"}', None)
    assert payload == {"language": "python"}


def test_load_config_override_from_file(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("language: java\nrepo:\n  owner: test\n")
    payload = load_config_override(None, str(path))
    assert payload["language"] == "java"
    assert payload["repo"]["owner"] == "test"


def test_load_config_override_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigInputError, match="Config file not found"):
        load_config_override(None, str(tmp_path / "missing.yaml"))


def test_load_config_override_invalid_json() -> None:
    with pytest.raises(ConfigInputError, match="Invalid JSON"):
        load_config_override("{not-json", None)


def test_load_config_override_non_object_json() -> None:
    with pytest.raises(ConfigInputError, match="must be a JSON/YAML object"):
        load_config_override("[1, 2, 3]", None)
