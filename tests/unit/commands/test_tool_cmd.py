from __future__ import annotations

import argparse
import json
from pathlib import Path

from cihub.commands.tool_cmd import _cmd_list, _cmd_status, _enable_for_repo
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.registry_service import load_registry


def _write_registry(tmp_path: Path, registry: dict[str, object]) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "registry.json").write_text(json.dumps(registry), encoding="utf-8")


def _base_registry(repo_config: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {}},
        "repos": {"alpha": repo_config},
    }


def test_tool_enable_uses_config_repo_language(tmp_path: Path, monkeypatch) -> None:
    repo_config = {
        "tier": "standard",
        "config": {"repo": {"owner": "org", "name": "alpha", "language": "python"}},
    }
    _write_registry(tmp_path, _base_registry(repo_config))
    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    result = _enable_for_repo("ruff", "alpha")

    assert result.exit_code == EXIT_SUCCESS
    updated = load_registry()
    tools = updated["repos"]["alpha"]["config"]["python"]["tools"]
    assert tools["ruff"]["enabled"] is True


def test_tool_enable_rejects_language_mismatch(tmp_path: Path, monkeypatch) -> None:
    repo_config = {
        "tier": "standard",
        "config": {"repo": {"owner": "org", "name": "alpha", "language": "python"}},
    }
    _write_registry(tmp_path, _base_registry(repo_config))
    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    result = _enable_for_repo("spotbugs", "alpha")

    assert result.exit_code == EXIT_FAILURE
    assert result.problems[0]["code"] == "CIHUB-TOOL-LANGUAGE-MISMATCH"
    updated = load_registry()
    assert "java" not in updated["repos"]["alpha"].get("config", {})


def test_tool_status_uses_config_repo_language(tmp_path: Path, monkeypatch) -> None:
    repo_config = {
        "tier": "standard",
        "config": {
            "repo": {"owner": "org", "name": "alpha", "language": "python"},
            "python": {"tools": {"ruff": {"enabled": True}}},
        },
    }
    _write_registry(tmp_path, _base_registry(repo_config))
    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    args = argparse.Namespace(repo="alpha", all=False, language=None)
    result = _cmd_status(args)

    assert result.exit_code == EXIT_SUCCESS
    assert result.data["repos"][0]["language"] == "python"
    assert "ruff" in result.data["repos"][0]["enabled_tools"]


def test_tool_status_includes_custom_tools(tmp_path: Path, monkeypatch) -> None:
    """Tool status includes custom x-* tools from config."""
    repo_config = {
        "tier": "standard",
        "config": {
            "repo": {"owner": "org", "name": "alpha", "language": "python"},
            "python": {
                "tools": {
                    "ruff": {"enabled": True},
                    "x-custom-lint": {"enabled": True, "command": "custom-lint check ."},
                    "x-other": {"enabled": False},
                }
            },
        },
    }
    _write_registry(tmp_path, _base_registry(repo_config))
    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    args = argparse.Namespace(repo="alpha", all=False, language=None)
    result = _cmd_status(args)

    assert result.exit_code == EXIT_SUCCESS
    enabled = result.data["repos"][0]["enabled_tools"]
    disabled = result.data["repos"][0]["disabled_tools"]
    # Built-in tool
    assert "ruff" in enabled
    # Custom tools
    assert "x-custom-lint" in enabled
    assert "x-other" in disabled


def test_tool_list_includes_custom_tools_for_repo(tmp_path: Path, monkeypatch) -> None:
    """Tool list includes custom x-* tools when repo is specified."""
    repo_config = {
        "tier": "standard",
        "config": {
            "repo": {"owner": "org", "name": "alpha", "language": "python"},
            "python": {
                "tools": {
                    "x-custom-lint": {"enabled": True, "command": "custom-lint check ."},
                }
            },
        },
    }
    _write_registry(tmp_path, _base_registry(repo_config))
    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    args = argparse.Namespace(
        language="python",
        category=None,
        repo="alpha",
        enabled_only=False,
    )
    result = _cmd_list(args)

    assert result.exit_code == EXIT_SUCCESS
    tool_names = [t["name"] for t in result.data["tools"]]
    # Built-in tools should be present
    assert "ruff" in tool_names
    # Custom tool should also be present
    assert "x-custom-lint" in tool_names

    # Check custom tool info
    custom_tool = next(t for t in result.data["tools"] if t["name"] == "x-custom-lint")
    assert custom_tool["category"] == "custom"
    assert custom_tool["language"] == "python"
    assert custom_tool["enabled"] is True
    assert custom_tool["command"] == "custom-lint check ."


def test_tool_list_custom_tools_respect_enabled_only(tmp_path: Path, monkeypatch) -> None:
    """Tool list with --enabled-only filters custom tools correctly."""
    repo_config = {
        "tier": "standard",
        "config": {
            "repo": {"owner": "org", "name": "alpha", "language": "python"},
            "python": {
                "tools": {
                    "ruff": {"enabled": True},
                    "x-enabled-custom": {"enabled": True, "command": "echo enabled"},
                    "x-disabled-custom": {"enabled": False, "command": "echo disabled"},
                }
            },
        },
    }
    _write_registry(tmp_path, _base_registry(repo_config))
    monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

    args = argparse.Namespace(
        language="python",
        category=None,
        repo="alpha",
        enabled_only=True,
    )
    result = _cmd_list(args)

    assert result.exit_code == EXIT_SUCCESS
    tool_names = [t["name"] for t in result.data["tools"]]
    # Enabled custom tool should be present
    assert "x-enabled-custom" in tool_names
    # Disabled custom tool should NOT be present
    assert "x-disabled-custom" not in tool_names
