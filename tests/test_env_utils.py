"""Tests for cihub.utils.env module."""

from __future__ import annotations

from cihub.utils.env import (
    _parse_env_bool,
    env_bool,
    env_int,
    env_str,
    get_github_token,
    resolve_flag,
)


class TestParseEnvBool:
    """Tests for _parse_env_bool function."""

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert _parse_env_bool(None) is None

    def test_true_values(self) -> None:
        """True-ish values return True."""
        for val in ["true", "True", "TRUE", "1", "yes", "Yes", "y", "Y", "on", "ON"]:
            assert _parse_env_bool(val) is True

    def test_false_values(self) -> None:
        """False-ish values return False."""
        for val in ["false", "False", "FALSE", "0", "no", "No", "n", "N", "off", "OFF"]:
            assert _parse_env_bool(val) is False

    def test_unrecognized_returns_none(self) -> None:
        """Unrecognized values return None."""
        assert _parse_env_bool("maybe") is None
        assert _parse_env_bool("2") is None
        assert _parse_env_bool("") is None


class TestEnvBool:
    """Tests for env_bool function."""

    def test_returns_default_when_not_set(self) -> None:
        """Returns default when env var not set."""
        env: dict[str, str] = {}
        assert env_bool("NOT_SET", default=True, env=env) is True
        assert env_bool("NOT_SET", default=False, env=env) is False

    def test_returns_parsed_value_when_set(self) -> None:
        """Returns parsed value when env var is set."""
        env = {"MY_VAR": "true"}
        assert env_bool("MY_VAR", default=False, env=env) is True
        env2 = {"MY_VAR": "false"}
        assert env_bool("MY_VAR", default=True, env=env2) is False

    def test_returns_default_for_invalid_value(self) -> None:
        """Returns default when env var has invalid value."""
        env = {"MY_VAR": "invalid"}
        assert env_bool("MY_VAR", default=True, env=env) is True


class TestEnvStr:
    """Tests for env_str function."""

    def test_returns_default_when_not_set(self) -> None:
        """Returns default when env var not set."""
        env: dict[str, str] = {}
        assert env_str("NOT_SET", default="fallback", env=env) == "fallback"
        assert env_str("NOT_SET", env=env) is None

    def test_returns_value_when_set(self) -> None:
        """Returns value when env var is set."""
        env = {"MY_VAR": "hello"}
        assert env_str("MY_VAR", default="fallback", env=env) == "hello"

    def test_returns_empty_string_if_set_empty(self) -> None:
        """Returns empty string if env var is set to empty (not default)."""
        env = {"MY_VAR": ""}
        assert env_str("MY_VAR", default="fallback", env=env) == ""


class TestEnvInt:
    """Tests for env_int function."""

    def test_returns_default_when_not_set(self) -> None:
        """Returns default when env var not set."""
        env: dict[str, str] = {}
        assert env_int("NOT_SET", default=42, env=env) == 42
        assert env_int("NOT_SET", env=env) == 0

    def test_returns_parsed_int_when_set(self) -> None:
        """Returns parsed integer when env var is set."""
        env = {"MY_VAR": "123"}
        assert env_int("MY_VAR", default=0, env=env) == 123

    def test_returns_default_for_invalid_value(self) -> None:
        """Returns default when env var cannot be parsed as int."""
        env = {"MY_VAR": "not_a_number"}
        assert env_int("MY_VAR", default=99, env=env) == 99

    def test_handles_negative_values(self) -> None:
        """Handles negative integer values."""
        env = {"MY_VAR": "-5"}
        assert env_int("MY_VAR", default=0, env=env) == -5

    def test_handles_zero(self) -> None:
        """Handles zero value."""
        env = {"MY_VAR": "0"}
        assert env_int("MY_VAR", default=10, env=env) == 0


class TestResolveFlag:
    """Tests for resolve_flag function."""

    def test_arg_value_takes_priority(self) -> None:
        """Explicit arg value takes priority over env."""
        env = {"MY_ENV": "env_value"}
        assert resolve_flag("arg_value", "MY_ENV", env=env) == "arg_value"

    def test_env_value_used_when_arg_none(self) -> None:
        """Env value used when arg is None."""
        env = {"MY_ENV": "env_value"}
        assert resolve_flag(None, "MY_ENV", env=env) == "env_value"

    def test_env_value_used_when_arg_empty(self) -> None:
        """Env value used when arg is empty string."""
        env = {"MY_ENV": "env_value"}
        assert resolve_flag("", "MY_ENV", env=env) == "env_value"

    def test_default_used_when_both_missing(self) -> None:
        """Default used when both arg and env missing."""
        env: dict[str, str] = {}
        assert resolve_flag(None, "MY_ENV", default="default_val", env=env) == "default_val"

    def test_returns_none_when_all_missing(self) -> None:
        """Returns None when arg, env, and default all missing."""
        env: dict[str, str] = {}
        assert resolve_flag(None, "MY_ENV", env=env) is None

    def test_empty_env_value_not_used(self) -> None:
        """Empty env value is treated as not set."""
        env = {"MY_ENV": ""}
        assert resolve_flag(None, "MY_ENV", default="fallback", env=env) == "fallback"


class TestGetGithubToken:
    """Tests for get_github_token function."""

    def test_explicit_token_takes_priority(self) -> None:
        """Explicit token argument takes priority."""
        env = {"GH_TOKEN": "env_token"}
        token, source = get_github_token(explicit_token="my_token", env=env)
        assert token == "my_token"
        assert source == "arg"

    def test_gh_token_priority(self) -> None:
        """GH_TOKEN has highest priority among env vars."""
        env = {
            "GH_TOKEN": "gh_token",
            "GITHUB_TOKEN": "github_token",
            "HUB_DISPATCH_TOKEN": "hub_token",
        }
        token, source = get_github_token(env=env)
        assert token == "gh_token"
        assert source == "GH_TOKEN"

    def test_github_token_fallback(self) -> None:
        """GITHUB_TOKEN used when GH_TOKEN not set."""
        env = {
            "GITHUB_TOKEN": "github_token",
            "HUB_DISPATCH_TOKEN": "hub_token",
        }
        token, source = get_github_token(env=env)
        assert token == "github_token"
        assert source == "GITHUB_TOKEN"

    def test_hub_dispatch_token_fallback(self) -> None:
        """HUB_DISPATCH_TOKEN used as last resort."""
        env = {"HUB_DISPATCH_TOKEN": "hub_token"}
        token, source = get_github_token(env=env)
        assert token == "hub_token"
        assert source == "HUB_DISPATCH_TOKEN"

    def test_custom_token_env(self) -> None:
        """Custom token env var checked before standard ones."""
        env = {
            "MY_CUSTOM_TOKEN": "custom_token",
            "GH_TOKEN": "gh_token",
        }
        token, source = get_github_token(token_env="MY_CUSTOM_TOKEN", env=env)
        assert token == "custom_token"
        assert source == "MY_CUSTOM_TOKEN"

    def test_custom_token_env_skips_standard_names(self) -> None:
        """Custom token env skipped if it's a standard name."""
        env = {"GH_TOKEN": "gh_token"}
        token, source = get_github_token(token_env="GH_TOKEN", env=env)
        assert token == "gh_token"
        assert source == "GH_TOKEN"

    def test_returns_missing_when_no_token(self) -> None:
        """Returns (None, 'missing') when no token found."""
        env: dict[str, str] = {}
        token, source = get_github_token(env=env)
        assert token is None
        assert source == "missing"

    def test_custom_env_empty_falls_through(self) -> None:
        """Empty custom env var falls through to standard ones."""
        env = {
            "MY_CUSTOM_TOKEN": "",
            "GH_TOKEN": "gh_token",
        }
        token, source = get_github_token(token_env="MY_CUSTOM_TOKEN", env=env)
        assert token == "gh_token"
        assert source == "GH_TOKEN"
