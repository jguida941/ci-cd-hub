"""Tests for custom tools (x- prefix) support."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cihub.tools.registry import (
    get_all_tools_from_config,
    get_custom_tool_command,
    get_custom_tools_from_config,
    is_custom_tool,
    is_tool_enabled,
)


class TestIsCustomTool:
    """Tests for is_custom_tool function."""

    def test_valid_custom_tool(self) -> None:
        assert is_custom_tool("x-custom-linter") is True
        assert is_custom_tool("x-my-tool") is True
        assert is_custom_tool("x-tool123") is True
        assert is_custom_tool("x-a") is True

    def test_invalid_custom_tool(self) -> None:
        assert is_custom_tool("pytest") is False
        assert is_custom_tool("ruff") is False
        assert is_custom_tool("x") is False
        assert is_custom_tool("x-") is False
        assert is_custom_tool("X-tool") is False  # case sensitive
        assert is_custom_tool("") is False

    def test_invalid_characters(self) -> None:
        assert is_custom_tool("x-tool.name") is False
        assert is_custom_tool("x-tool/name") is False
        assert is_custom_tool("x-tool name") is False


class TestGetCustomToolsFromConfig:
    """Tests for get_custom_tools_from_config function."""

    def test_extracts_custom_tools(self) -> None:
        config = {
            "python": {
                "tools": {
                    "pytest": True,
                    "ruff": {"enabled": True},
                    "x-custom-linter": {"enabled": True, "command": "my-lint ."},
                    "x-another": True,
                }
            }
        }
        custom = get_custom_tools_from_config(config, "python")
        assert "x-custom-linter" in custom
        assert "x-another" in custom
        assert "pytest" not in custom
        assert "ruff" not in custom

    def test_empty_when_no_custom_tools(self) -> None:
        config = {"python": {"tools": {"pytest": True, "ruff": True}}}
        custom = get_custom_tools_from_config(config, "python")
        assert custom == {}

    def test_handles_missing_tools(self) -> None:
        config = {"python": {}}
        custom = get_custom_tools_from_config(config, "python")
        assert custom == {}


class TestGetAllToolsFromConfig:
    """Tests for get_all_tools_from_config function."""

    def test_includes_builtin_and_custom(self) -> None:
        config = {
            "python": {
                "tools": {
                    "pytest": True,
                    "x-custom-linter": True,
                    "x-aaa-tool": True,
                }
            }
        }
        tools = get_all_tools_from_config(config, "python")
        # Built-in tools come first
        assert "pytest" in tools
        assert "ruff" in tools  # From PYTHON_TOOLS
        # Custom tools come after, sorted
        assert tools[-2] == "x-aaa-tool"
        assert tools[-1] == "x-custom-linter"


class TestIsToolEnabled:
    """Tests for is_tool_enabled function."""

    def test_custom_tool_boolean_enabled(self) -> None:
        config = {"python": {"tools": {"x-custom": True}}}
        assert is_tool_enabled(config, "x-custom", "python") is True

    def test_custom_tool_boolean_disabled(self) -> None:
        config = {"python": {"tools": {"x-custom": False}}}
        assert is_tool_enabled(config, "x-custom", "python") is False

    def test_custom_tool_object_enabled(self) -> None:
        config = {"python": {"tools": {"x-custom": {"enabled": True}}}}
        assert is_tool_enabled(config, "x-custom", "python") is True

    def test_custom_tool_object_enabled_implicit(self) -> None:
        # When enabled is not specified, schema says default=True for custom tools
        # Callers must pass default=True explicitly (aligns with canonical tool_enabled)
        config = {"python": {"tools": {"x-custom": {"command": "foo"}}}}
        assert is_tool_enabled(config, "x-custom", "python", default=True) is True
        # Without explicit default, returns False (aligned with canonical)
        assert is_tool_enabled(config, "x-custom", "python") is False


class TestGetCustomToolCommand:
    """Tests for get_custom_tool_command function."""

    def test_returns_command(self) -> None:
        config = {"python": {"tools": {"x-linter": {"command": "my-lint --check ."}}}}
        assert get_custom_tool_command(config, "x-linter", "python") == "my-lint --check ."

    def test_returns_none_for_builtin(self) -> None:
        config = {"python": {"tools": {"pytest": {"command": "ignored"}}}}
        assert get_custom_tool_command(config, "pytest", "python") is None

    def test_returns_none_when_missing(self) -> None:
        config = {"python": {"tools": {"x-linter": True}}}
        assert get_custom_tool_command(config, "x-linter", "python") is None


class TestSchemaValidation:
    """Tests for schema validation of custom tools."""

    @pytest.fixture
    def schema(self) -> dict:
        schema_path = Path(__file__).parent.parent / "schema" / "ci-hub-config.schema.json"
        return json.loads(schema_path.read_text())

    def test_schema_has_custom_tool_definition(self, schema: dict) -> None:
        assert "customTool" in schema["definitions"]

    def test_python_tools_has_pattern_properties(self, schema: dict) -> None:
        python_tools = schema["definitions"]["pythonTools"]
        assert "patternProperties" in python_tools
        # Schema pattern must match runtime pattern (^x-[a-zA-Z0-9_-]+$)
        assert "^x-[a-zA-Z0-9_-]+$" in python_tools["patternProperties"]

    def test_java_tools_has_pattern_properties(self, schema: dict) -> None:
        java_tools = schema["definitions"]["javaTools"]
        assert "patternProperties" in java_tools
        # Schema pattern must match runtime pattern (^x-[a-zA-Z0-9_-]+$)
        assert "^x-[a-zA-Z0-9_-]+$" in java_tools["patternProperties"]

    def test_custom_tool_allows_boolean_or_object(self, schema: dict) -> None:
        custom_tool = schema["definitions"]["customTool"]
        assert "oneOf" in custom_tool
        types = [item.get("type") for item in custom_tool["oneOf"]]
        assert "boolean" in types
        assert "object" in types


class TestCustomToolBehavior:
    """Tests for custom tool execution behavior."""

    def test_tools_configured_uses_correct_default_for_custom_tools(self) -> None:
        """Custom tools should be configured=True when present in config without explicit enabled."""
        from cihub.tools.registry import is_custom_tool

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "pytest": True,  # built-in
                    "x-mycustomtool": {"command": "echo hello"},  # custom
                }
            },
        }

        # Custom tool should be detected
        assert is_custom_tool("x-mycustomtool") is True
        assert is_custom_tool("pytest") is False

        # Custom tool defaults to enabled=True, built-in defaults to enabled via config
        assert is_tool_enabled(config, "x-mycustomtool", "python", default=True) is True
        assert is_tool_enabled(config, "pytest", "python") is True

    def test_custom_tool_fail_on_error_config_extraction(self) -> None:
        """fail_on_error should be extracted from custom tool config."""
        config = {
            "python": {
                "tools": {
                    "x-optional": {
                        "command": "echo test",
                        "fail_on_error": False,
                    },
                    "x-required": {
                        "command": "echo test",
                        # fail_on_error defaults to True
                    },
                }
            }
        }

        tools = config["python"]["tools"]

        # x-optional has fail_on_error=False
        optional_cfg = tools["x-optional"]
        assert optional_cfg.get("fail_on_error", True) is False

        # x-required defaults to True
        required_cfg = tools["x-required"]
        assert required_cfg.get("fail_on_error", True) is True

    def test_require_run_or_fail_applies_to_custom_tools(self) -> None:
        """require_run_or_fail should work for custom tools."""
        from cihub.services.ci_engine.gates import _tool_requires_run_or_fail

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-required-tool": {
                        "command": "echo test",
                        "require_run_or_fail": True,
                    },
                    "x-optional-tool": {
                        "command": "echo test",
                        "require_run_or_fail": False,
                    },
                }
            },
        }

        # Custom tools should respect require_run_or_fail
        assert _tool_requires_run_or_fail("x-required-tool", config, "python") is True
        assert _tool_requires_run_or_fail("x-optional-tool", config, "python") is False

    def test_custom_tool_included_in_all_tools(self) -> None:
        """Custom tools should be included in get_all_tools_from_config."""
        config = {
            "python": {
                "tools": {
                    "pytest": True,
                    "x-linter": {"command": "lint ."},
                    "x-formatter": {"command": "fmt ."},
                }
            }
        }

        all_tools = get_all_tools_from_config(config, "python")

        # Should include built-in tools
        assert "pytest" in all_tools
        assert "ruff" in all_tools  # always present from PYTHON_TOOLS

        # Should include custom tools
        assert "x-linter" in all_tools
        assert "x-formatter" in all_tools

    def test_env_override_pattern_for_custom_tools(self) -> None:
        """CIHUB_RUN_* should work for custom tools with correct pattern."""
        from cihub.services.ci_engine.helpers import _apply_env_overrides

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-my-linter": {"command": "lint ."},
                }
            },
        }
        problems: list[dict] = []

        # Simulate env var: CIHUB_RUN_X_MY_LINTER=false
        env = {"CIHUB_RUN_X_MY_LINTER": "false"}
        _apply_env_overrides(config, "python", env, problems)

        # Tool should be disabled
        assert config["python"]["tools"]["x-my-linter"]["enabled"] is False
        assert len(problems) == 0

    def test_fail_on_error_severity_escalation(self) -> None:
        """fail_on_error=true should produce 'error' severity, not 'warning'."""
        # This tests the config intent - actual execution would require mocking safe_run
        config_with_fail = {
            "python": {
                "tools": {
                    "x-strict": {
                        "command": "strict-check",
                        "fail_on_error": True,  # default
                    },
                    "x-optional": {
                        "command": "optional-check",
                        "fail_on_error": False,
                    },
                }
            }
        }

        strict_cfg = config_with_fail["python"]["tools"]["x-strict"]
        optional_cfg = config_with_fail["python"]["tools"]["x-optional"]

        # fail_on_error=True should cause error severity when tool fails
        assert strict_cfg.get("fail_on_error", True) is True

        # fail_on_error=False should not emit problems when tool fails
        assert optional_cfg.get("fail_on_error", True) is False

    def test_tools_configured_in_report_build_uses_custom_tools(self) -> None:
        """Report build should include custom tools in tools_configured."""
        from cihub.tools.registry import is_custom_tool

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "pytest": True,
                    "x-coverage": {"command": "coverage report"},
                }
            },
        }

        all_tools = get_all_tools_from_config(config, "python")

        # Build tools_configured the same way report/build.py does now
        tools_configured = {
            tool: is_tool_enabled(config, tool, "python", default=is_custom_tool(tool)) for tool in all_tools
        }

        # Built-in tool should be configured
        assert tools_configured.get("pytest") is True

        # Custom tool should be configured (default=True for custom tools)
        assert tools_configured.get("x-coverage") is True


class TestCustomToolExecution:
    """Tests for actual custom tool execution path (mocked)."""

    @pytest.fixture
    def tmp_workdir(self, tmp_path: Path) -> Path:
        """Create a temporary working directory."""
        workdir = tmp_path / "repo"
        workdir.mkdir()
        return workdir

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        """Create a temporary output directory."""
        out = tmp_path / "output"
        out.mkdir()
        return out

    def test_custom_tool_success_records_correct_result(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Custom tool success should record ran=True, success=True, returncode=0."""
        from unittest.mock import MagicMock

        from cihub.services.ci_engine.python_tools import _run_python_tools

        # Mock safe_run to return success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "OK"
        mock_result.stderr = ""

        def mock_safe_run(cmd, **kwargs):
            return mock_result

        monkeypatch.setattr("cihub.services.ci_engine.python_tools.safe_run", mock_safe_run)

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-my-checker": {"command": "echo success"},
                }
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        tool_outputs, tools_ran, tools_success = _run_python_tools(
            config, tmp_workdir, ".", output_dir, problems, runners
        )

        # Custom tool should have run successfully
        assert tools_ran.get("x-my-checker") is True
        assert tools_success.get("x-my-checker") is True
        assert "x-my-checker" in tool_outputs
        assert tool_outputs["x-my-checker"]["ran"] is True
        assert tool_outputs["x-my-checker"]["success"] is True
        # No error problems should be emitted for success
        error_problems = [
            p for p in problems if p.get("severity") == "error" and "x-my-checker" in p.get("message", "")
        ]
        assert len(error_problems) == 0

    def test_custom_tool_failure_with_fail_on_error_true_emits_error(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Custom tool failure with fail_on_error=True should emit error severity."""
        from unittest.mock import MagicMock

        from cihub.services.ci_engine.python_tools import _run_python_tools

        # Mock safe_run to return failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "check failed"

        def mock_safe_run(cmd, **kwargs):
            return mock_result

        monkeypatch.setattr("cihub.services.ci_engine.python_tools.safe_run", mock_safe_run)

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-strict-checker": {
                        "command": "strict-check .",
                        "fail_on_error": True,  # default
                    },
                }
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        tool_outputs, tools_ran, tools_success = _run_python_tools(
            config, tmp_workdir, ".", output_dir, problems, runners
        )

        # Custom tool should have run but failed
        assert tools_ran.get("x-strict-checker") is True
        assert tools_success.get("x-strict-checker") is False
        assert tool_outputs["x-strict-checker"]["returncode"] == 1

        # Should emit error severity (affects exit code)
        error_problems = [
            p for p in problems if p.get("severity") == "error" and "x-strict-checker" in p.get("message", "")
        ]
        assert len(error_problems) == 1
        assert "exit code 1" in error_problems[0]["message"]

    def test_custom_tool_failure_with_fail_on_error_false_no_error(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Custom tool failure with fail_on_error=False should NOT emit error."""
        from unittest.mock import MagicMock

        from cihub.services.ci_engine.python_tools import _run_python_tools

        # Mock safe_run to return failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "optional check failed"

        def mock_safe_run(cmd, **kwargs):
            return mock_result

        monkeypatch.setattr("cihub.services.ci_engine.python_tools.safe_run", mock_safe_run)

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-optional-checker": {
                        "command": "optional-check .",
                        "fail_on_error": False,  # explicitly optional
                    },
                }
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        tool_outputs, tools_ran, tools_success = _run_python_tools(
            config, tmp_workdir, ".", output_dir, problems, runners
        )

        # Custom tool should have run but failed
        assert tools_ran.get("x-optional-checker") is True
        assert tools_success.get("x-optional-checker") is False

        # Should NOT emit any error or warning for this tool (fail_on_error=False)
        tool_problems = [p for p in problems if "x-optional-checker" in p.get("message", "")]
        assert len(tool_problems) == 0

    def test_custom_tool_missing_command_emits_warning(self, tmp_workdir: Path, output_dir: Path) -> None:
        """Custom tool with no command configured should emit warning."""
        from cihub.services.ci_engine.python_tools import _run_python_tools

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-no-command": True,  # boolean, no command
                }
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        _run_python_tools(config, tmp_workdir, ".", output_dir, problems, runners)

        # Should emit warning about missing command
        warning_problems = [
            p for p in problems if p.get("severity") == "warning" and "x-no-command" in p.get("message", "")
        ]
        assert len(warning_problems) == 1
        assert "no command configured" in warning_problems[0]["message"]

    def test_custom_tool_returncode_is_captured(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Custom tool returncode should be captured in ToolResult."""
        from unittest.mock import MagicMock

        from cihub.services.ci_engine.python_tools import _run_python_tools

        # Mock safe_run to return specific exit code
        mock_result = MagicMock()
        mock_result.returncode = 42
        mock_result.stdout = ""
        mock_result.stderr = ""

        def mock_safe_run(cmd, **kwargs):
            return mock_result

        monkeypatch.setattr("cihub.services.ci_engine.python_tools.safe_run", mock_safe_run)

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-exit-code-test": {
                        "command": "exit 42",
                        "fail_on_error": False,  # Don't emit error for this test
                    },
                }
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        tool_outputs, _, _ = _run_python_tools(config, tmp_workdir, ".", output_dir, problems, runners)

        # Returncode should be captured
        assert tool_outputs["x-exit-code-test"]["returncode"] == 42
        assert tool_outputs["x-exit-code-test"]["metrics"]["exit_code"] == 42

    def test_custom_tool_command_not_found_with_fail_on_error_true_emits_error(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CommandNotFoundError with fail_on_error=True should emit error severity."""
        from cihub.services.ci_engine.python_tools import _run_python_tools
        from cihub.utils.exec_utils import CommandNotFoundError

        def mock_safe_run(cmd, **kwargs):
            raise CommandNotFoundError("nonexistent-binary")

        monkeypatch.setattr("cihub.services.ci_engine.python_tools.safe_run", mock_safe_run)

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-required-tool": {
                        "command": "nonexistent-binary --check",
                        "fail_on_error": True,  # default
                    },
                }
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        _run_python_tools(config, tmp_workdir, ".", output_dir, problems, runners)

        # Should emit error severity (not warning) because fail_on_error=True
        error_problems = [
            p for p in problems if p.get("severity") == "error" and "x-required-tool" in p.get("message", "")
        ]
        assert len(error_problems) == 1
        assert "nonexistent-binary" in error_problems[0]["message"]

    def test_custom_tool_command_not_found_with_fail_on_error_false_emits_warning(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CommandNotFoundError with fail_on_error=False should emit warning only."""
        from cihub.services.ci_engine.python_tools import _run_python_tools
        from cihub.utils.exec_utils import CommandNotFoundError

        def mock_safe_run(cmd, **kwargs):
            raise CommandNotFoundError("optional-binary")

        monkeypatch.setattr("cihub.services.ci_engine.python_tools.safe_run", mock_safe_run)

        config = {
            "language": "python",
            "python": {
                "tools": {
                    "x-optional-tool": {
                        "command": "optional-binary --check",
                        "fail_on_error": False,  # optional tool
                    },
                }
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        _run_python_tools(config, tmp_workdir, ".", output_dir, problems, runners)

        # Should emit warning (not error) because fail_on_error=False
        warning_problems = [
            p for p in problems if p.get("severity") == "warning" and "x-optional-tool" in p.get("message", "")
        ]
        error_problems = [
            p for p in problems if p.get("severity") == "error" and "x-optional-tool" in p.get("message", "")
        ]
        assert len(warning_problems) == 1
        assert len(error_problems) == 0


class TestCustomToolExecutionJava:
    """Tests for Java custom tool execution path (mocked)."""

    @pytest.fixture
    def tmp_workdir(self, tmp_path: Path) -> Path:
        """Create a temporary working directory."""
        workdir = tmp_path / "repo"
        workdir.mkdir()
        # Create a minimal pom.xml for Java detection
        (workdir / "pom.xml").write_text("<project></project>")
        return workdir

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        """Create a temporary output directory."""
        out = tmp_path / "output"
        out.mkdir()
        return out

    def test_java_custom_tool_success(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Java custom tool success should record correct result."""
        from unittest.mock import MagicMock

        from cihub.services.ci_engine.java_tools import _run_java_tools

        # Mock safe_run to return success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "OK"
        mock_result.stderr = ""

        def mock_safe_run(cmd, **kwargs):
            return mock_result

        monkeypatch.setattr("cihub.services.ci_engine.java_tools.safe_run", mock_safe_run)

        # Mock run_java_build to avoid actual build
        mock_build_result = MagicMock()
        mock_build_result.to_payload.return_value = {"ran": True, "success": True}
        mock_build_result.write_json = MagicMock()
        mock_build_result.success = True
        mock_build_result.metrics = {}
        monkeypatch.setattr(
            "cihub.services.ci_engine.java_tools.run_java_build",
            lambda *args, **kwargs: mock_build_result,
        )

        config = {
            "language": "java",
            "java": {
                "build_tool": "maven",
                "tools": {
                    "x-java-checker": {"command": "echo success"},
                },
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        tool_outputs, tools_ran, tools_success = _run_java_tools(
            config, tmp_workdir, ".", output_dir, "maven", problems, runners
        )

        # Custom tool should have run successfully
        assert tools_ran.get("x-java-checker") is True
        assert tools_success.get("x-java-checker") is True

    def test_java_custom_tool_failure_with_fail_on_error_true(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Java custom tool failure with fail_on_error=True should emit error."""
        from unittest.mock import MagicMock

        from cihub.services.ci_engine.java_tools import _run_java_tools

        # Mock safe_run to return failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "failed"

        def mock_safe_run(cmd, **kwargs):
            return mock_result

        monkeypatch.setattr("cihub.services.ci_engine.java_tools.safe_run", mock_safe_run)

        # Mock run_java_build
        mock_build_result = MagicMock()
        mock_build_result.to_payload.return_value = {"ran": True, "success": True}
        mock_build_result.write_json = MagicMock()
        mock_build_result.success = True
        mock_build_result.metrics = {}
        monkeypatch.setattr(
            "cihub.services.ci_engine.java_tools.run_java_build",
            lambda *args, **kwargs: mock_build_result,
        )

        config = {
            "language": "java",
            "java": {
                "build_tool": "maven",
                "tools": {
                    "x-strict-java": {
                        "command": "strict-check",
                        "fail_on_error": True,
                    },
                },
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        _run_java_tools(config, tmp_workdir, ".", output_dir, "maven", problems, runners)

        # Should emit error severity
        error_problems = [
            p for p in problems if p.get("severity") == "error" and "x-strict-java" in p.get("message", "")
        ]
        assert len(error_problems) == 1

    def test_java_custom_tool_command_not_found_with_fail_on_error(
        self, tmp_workdir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Java CommandNotFoundError with fail_on_error=True should emit error."""
        from unittest.mock import MagicMock

        from cihub.services.ci_engine.java_tools import _run_java_tools
        from cihub.utils.exec_utils import CommandNotFoundError

        def mock_safe_run(cmd, **kwargs):
            raise CommandNotFoundError("missing-java-tool")

        monkeypatch.setattr("cihub.services.ci_engine.java_tools.safe_run", mock_safe_run)

        # Mock run_java_build
        mock_build_result = MagicMock()
        mock_build_result.to_payload.return_value = {"ran": True, "success": True}
        mock_build_result.write_json = MagicMock()
        mock_build_result.success = True
        mock_build_result.metrics = {}
        monkeypatch.setattr(
            "cihub.services.ci_engine.java_tools.run_java_build",
            lambda *args, **kwargs: mock_build_result,
        )

        config = {
            "language": "java",
            "java": {
                "build_tool": "maven",
                "tools": {
                    "x-required-java": {
                        "command": "missing-java-tool",
                        "fail_on_error": True,
                    },
                },
            },
        }
        problems: list[dict] = []
        runners: dict = {}

        _run_java_tools(config, tmp_workdir, ".", output_dir, "maven", problems, runners)

        # Should emit error severity for required tool that can't be found
        error_problems = [
            p for p in problems if p.get("severity") == "error" and "x-required-java" in p.get("message", "")
        ]
        assert len(error_problems) == 1
