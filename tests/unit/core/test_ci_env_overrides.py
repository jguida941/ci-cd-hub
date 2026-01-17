"""Tests for CLI environment overrides in cihub.services.ci_engine."""

from cihub.services.ci_engine import _apply_env_overrides, _parse_env_bool


def _base_config(language: str) -> dict:
    return {
        "language": language,
        language: {"tools": {}},
    }


def test_parse_env_bool_values() -> None:
    assert _parse_env_bool("true") is True
    assert _parse_env_bool("1") is True
    assert _parse_env_bool("yes") is True
    assert _parse_env_bool("on") is True
    assert _parse_env_bool("false") is False
    assert _parse_env_bool("0") is False
    assert _parse_env_bool("no") is False
    assert _parse_env_bool("off") is False
    assert _parse_env_bool("maybe") is None
    assert _parse_env_bool(None) is None


def test_apply_env_overrides_python_tools() -> None:
    config = _base_config("python")
    config["python"]["tools"]["pytest"] = {"enabled": True}
    config["python"]["tools"]["ruff"] = False
    problems: list[dict[str, object]] = []
    env = {
        "CIHUB_RUN_PYTEST": "false",
        "CIHUB_RUN_RUFF": "true",
    }

    _apply_env_overrides(config, "python", env, problems)

    assert config["python"]["tools"]["pytest"]["enabled"] is False
    assert config["python"]["tools"]["ruff"]["enabled"] is True
    assert problems == []


def test_apply_env_overrides_java_tools() -> None:
    config = _base_config("java")
    config["java"]["tools"]["jacoco"] = True
    problems: list[dict[str, object]] = []
    env = {"CIHUB_RUN_JACOCO": "false"}

    _apply_env_overrides(config, "java", env, problems)

    assert config["java"]["tools"]["jacoco"]["enabled"] is False
    assert problems == []


def test_apply_env_overrides_invalid_value_warns() -> None:
    config = _base_config("python")
    problems: list[dict[str, object]] = []
    env = {"CIHUB_RUN_PYTEST": "maybe"}

    _apply_env_overrides(config, "python", env, problems)

    assert len(problems) == 1
    assert problems[0]["code"] == "CIHUB-CI-ENV-BOOL"


def test_apply_env_overrides_summary_toggle() -> None:
    config = _base_config("python")
    problems: list[dict[str, object]] = []
    env = {"CIHUB_WRITE_GITHUB_SUMMARY": "false"}

    _apply_env_overrides(config, "python", env, problems)

    assert config["reports"]["github_summary"]["enabled"] is False
    assert problems == []
