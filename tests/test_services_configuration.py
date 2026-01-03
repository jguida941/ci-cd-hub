from __future__ import annotations

import pytest

from cihub.services.configuration import set_tool_enabled


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
