"""Environment variable utilities."""

from __future__ import annotations

import os
from typing import Mapping


def _parse_env_bool(value: str | None) -> bool | None:
    """Parse a string as a boolean, returning None if not recognized.

    Accepts: true/false, 1/0, yes/no, y/n, on/off (case-insensitive).
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return None


def env_bool(name: str, default: bool = False, env: Mapping[str, str] | None = None) -> bool:
    """Read a boolean environment variable with a fallback default."""
    env_map: Mapping[str, str] = os.environ if env is None else env
    parsed = _parse_env_bool(env_map.get(name))
    return default if parsed is None else parsed


def env_str(name: str, default: str | None = None, env: Mapping[str, str] | None = None) -> str | None:
    """Read a string environment variable with a fallback default."""
    env_map: Mapping[str, str] = os.environ if env is None else env
    value = env_map.get(name)
    if value is None:
        return default
    return value


def env_int(name: str, default: int = 0, env: Mapping[str, str] | None = None) -> int:
    """Read an integer environment variable with safe parsing.

    Returns the default if the variable is not set or cannot be parsed as an integer.
    This is safer than bare int() which raises ValueError on invalid input.
    """
    env_map: Mapping[str, str] = os.environ if env is None else env
    value = env_map.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def resolve_flag(
    arg_value: str | None,
    env_name: str,
    default: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve a CLI flag with environment variable fallback.

    Priority order:
    1. Explicit arg_value (if not None/empty)
    2. Environment variable (env_name)
    3. Default value

    This allows workflows to set env vars and skip explicit --flag args.

    Args:
        arg_value: Value from argparse (may be None or empty string)
        env_name: Environment variable name to check as fallback
        default: Default value if both arg and env are empty
        env: Optional env dict (defaults to os.environ)

    Returns:
        Resolved value or None

    Example:
        owner = resolve_flag(args.owner, "CIHUB_OWNER")
        repo = resolve_flag(args.repo, "CIHUB_REPO")
        bin_path = resolve_flag(args.bin, "KYVERNO_BIN")
    """
    # If explicit arg provided, use it
    if arg_value:
        return arg_value

    # Check environment variable
    env_map: Mapping[str, str] = os.environ if env is None else env
    env_value = env_map.get(env_name)
    if env_value:
        return env_value

    return default


def get_github_token(
    explicit_token: str | None = None,
    token_env: str | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[str | None, str]:
    """Get GitHub token with consistent priority order.

    Priority order:
    1. explicit_token (passed as argument)
    2. token_env (custom env var name, if specified)
    3. GH_TOKEN (GitHub CLI convention)
    4. GITHUB_TOKEN (GitHub Actions automatic token)
    5. HUB_DISPATCH_TOKEN (hub-specific token)

    Returns:
        Tuple of (token, source) where source is the env var name or "arg"/"missing".
    """
    env_map: Mapping[str, str] = os.environ if env is None else env

    if explicit_token:
        return explicit_token, "arg"

    # Check custom token env var first (if specified and different from defaults)
    if token_env and token_env not in {"GH_TOKEN", "GITHUB_TOKEN", "HUB_DISPATCH_TOKEN"}:
        token = env_map.get(token_env)
        if token:
            return token, token_env

    # Standard priority order
    for env_name in ("GH_TOKEN", "GITHUB_TOKEN", "HUB_DISPATCH_TOKEN"):
        token = env_map.get(env_name)
        if token:
            return token, env_name

    return None, "missing"
