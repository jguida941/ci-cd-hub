"""
CI/CD Hub - Configuration Loader Core

Merges configuration from multiple sources with proper precedence:
  1. Repo's .ci-hub.yml (highest priority)
  2. Hub's config/repos/<repo-name>.yaml
  3. Hub's config/defaults.yaml (lowest priority)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from cihub.config.fallbacks import FALLBACK_DEFAULTS
from cihub.config.io import load_yaml_file
from cihub.config.merge import deep_merge
from cihub.config.normalize import normalize_config
from cihub.config.normalize import tool_enabled as _tool_enabled_canonical


class ConfigValidationError(Exception):
    """Raised when a merged CI/CD Hub config fails schema validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def _load_yaml(path: Path, source: str) -> dict:
    """Load YAML with consistent error handling for the loader."""
    try:
        return load_yaml_file(path)
    except ValueError as exc:
        raise ConfigValidationError(f"{source}: {exc}") from exc


def load_config(
    repo_name: str,
    hub_root: Path,
    repo_config_path: Path | None = None,
    exit_on_validation_error: bool = True,
) -> dict:
    """
    Load and merge configuration for a repository.

    Args:
        repo_name: Name of the repository (e.g., 'contact-suite-spring-react')
        hub_root: Path to the hub-release directory
        repo_config_path: Optional path to the repo's .ci-hub.yml
        exit_on_validation_error: If True, sys.exit(1) on validation failure

    Returns:
        Merged configuration dictionary
    """
    from jsonschema import Draft7Validator

    # Load schema for validation
    schema_path = hub_root / "schema" / "ci-hub-config.schema.json"
    schema: dict[str, Any] = {}
    if schema_path.exists():
        with schema_path.open(encoding="utf-8") as f:
            schema = json.load(f)
    else:
        print(f"Warning: schema not found at {schema_path}", file=sys.stderr)

    def validate_config(cfg: dict, source: str) -> None:
        if not schema:
            return
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(cfg))
        if errors:
            print(f"Config validation failed for {source}:", file=sys.stderr)
            messages: list[str] = []
            for err in errors:
                path = ".".join([str(p) for p in err.path]) or "<root>"
                message = f"{path}: {err.message}"
                messages.append(message)
                print(f"  - {message}", file=sys.stderr)
            raise ConfigValidationError(f"Validation failed for {source}", errors=messages)

    # 1. Load defaults (lowest priority)
    defaults_path = hub_root / "config" / "defaults.yaml"
    config = _load_yaml(defaults_path, "defaults")

    if not config:
        print(f"Warning: No defaults found at {defaults_path}", file=sys.stderr)
        config = FALLBACK_DEFAULTS
    # Note: We DON'T validate defaults.yaml pre-normalize because:
    # 1. It's part of this repo and tested
    # 2. It intentionally lacks required repo fields (owner, name, language)
    # 3. The final merged config is always validated
    config = normalize_config(config)

    # 2. Merge hub's repo-specific config
    repo_override_path = hub_root / "config" / "repos" / f"{repo_name}.yaml"
    repo_override_exists = repo_override_path.exists()
    repo_override_raw = _load_yaml(repo_override_path, "hub override")
    # Note: We DON'T validate hub overrides pre-normalize because:
    # 1. They are partial configs that don't include all required fields
    # 2. The schema requires fields like 'language' that are only in defaults
    # 3. The final merged config is always validated
    repo_override = normalize_config(repo_override_raw)

    if repo_override:
        config = deep_merge(config, repo_override)

    # 3. Merge repo's own .ci-hub.yml (highest priority)
    if repo_config_path:
        repo_local_config = _load_yaml(repo_config_path, "repo local config")
        if repo_local_config:
            # Note: We DON'T validate repo local configs pre-normalize because:
            # 1. They are partial configs that only override specific settings
            # 2. The schema requires fields that come from defaults/hub override
            # 3. The final merged config is always validated
            # Block repo-local from overriding protected keys when hub override exists.
            if repo_override_exists:
                repo_block = repo_local_config.get("repo", {})
                if isinstance(repo_block, dict):
                    repo_block.pop("owner", None)
                    repo_block.pop("name", None)
                    repo_block.pop("language", None)
                    repo_block.pop("dispatch_workflow", None)
                    repo_block.pop("dispatch_enabled", None)
                repo_local_config["repo"] = repo_block
            repo_local_config = normalize_config(repo_local_config)
            config = deep_merge(config, repo_local_config)

    # Validate merged config once more
    # Ensure top-level language is set from repo.language if present
    repo_info = config.get("repo", {})
    if isinstance(repo_info, dict) and repo_info.get("language"):
        config["language"] = repo_info["language"]

    try:
        validate_config(config, "merged-config")
    except ConfigValidationError:
        if exit_on_validation_error:
            sys.exit(1)
        raise

    # Add metadata
    config["_meta"] = {
        "repo_name": repo_name,
        "config_sources": {
            "defaults": str(defaults_path),
            "hub_override": str(repo_override_path) if repo_override else None,
            "repo_local": str(repo_config_path) if repo_config_path else None,
        },
    }

    return config


def get_tool_enabled(config: dict[str, Any], language: str, tool: str) -> bool:
    """Check if a specific tool is enabled for the given language.

    This is a wrapper around the canonical tool_enabled() from normalize.py.
    The parameter order (language, tool) is maintained for backwards compatibility,
    but internally delegates to the canonical implementation.
    """
    return _tool_enabled_canonical(config, tool, language, default=False)


def get_tool_config(config: dict[str, Any], language: str, tool: str) -> dict[str, Any]:
    """Get the full configuration for a specific tool."""
    lang_config = config.get(language, {})
    if not isinstance(lang_config, dict):
        return {}
    tools = lang_config.get("tools", {})
    if not isinstance(tools, dict):
        return {}
    tool_config = tools.get(tool, {})
    return tool_config if isinstance(tool_config, dict) else {}


def _main() -> None:
    """CLI entry point for standalone usage."""
    from cihub.config.loader.inputs import generate_workflow_inputs

    parser = argparse.ArgumentParser(description="Load CI/CD Hub configuration")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument(
        "--hub-root",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent,
        help="Path to hub-release directory",
    )
    parser.add_argument(
        "--repo-config-path",
        type=Path,
        help="Path to repo's .ci-hub.yml file",
    )
    parser.add_argument(
        "--output",
        choices=["json", "yaml", "workflow-inputs"],
        default="json",
        help="Output format",
    )

    args = parser.parse_args()

    config = load_config(
        repo_name=args.repo,
        hub_root=args.hub_root,
        repo_config_path=args.repo_config_path,
    )

    if args.output == "json":
        print(json.dumps(config, indent=2))
    elif args.output == "yaml":
        print(yaml.safe_dump(config, default_flow_style=False, sort_keys=False))
    elif args.output == "workflow-inputs":
        inputs = generate_workflow_inputs(config)
        print(json.dumps(inputs, indent=2))
