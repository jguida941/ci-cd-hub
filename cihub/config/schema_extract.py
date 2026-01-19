"""Extract default values from JSON schema for config generation.

This module provides utilities to traverse the ci-hub-config.schema.json
and extract default values to generate:
- defaults.yaml (schema-derived defaults)
- fallbacks.py (Python dict for runtime fallback)

The schema is the single source of truth for default values.
"""

from __future__ import annotations

import json
from typing import Any, cast

from cihub.utils.paths import hub_root

# Path to the schema file
SCHEMA_PATH = hub_root() / "schema" / "ci-hub-config.schema.json"


def load_schema() -> dict[str, Any]:
    """Load the CI Hub config schema.

    Returns:
        The parsed JSON schema as a dict.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
    """
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a $ref pointer within the schema.

    Args:
        schema: The root schema dict.
        ref: JSON pointer like "#/definitions/pythonTools".

    Returns:
        The resolved definition dict.
    """
    if not ref.startswith("#/"):
        return {}
    path_parts = ref[2:].split("/")
    result = schema
    for part in path_parts:
        if part in result:
            result = result[part]
        else:
            return {}
    return result


def _is_deprecated(prop_schema: dict[str, Any]) -> bool:
    """Return True when a schema node is marked deprecated."""
    if prop_schema.get("deprecated") is True:
        return True
    description = prop_schema.get("description")
    if isinstance(description, str) and "deprecated" in description.lower():
        return True
    return False


def _extract_oneOf_defaults(
    schema: dict[str, Any],
    oneof_options: list[dict[str, Any]],
    include_disabled: bool = True,
    skip_keys: set[str] | None = None,
) -> dict[str, Any] | None:
    """Extract defaults from a oneOf schema pattern.

    Handles the common pattern where oneOf contains:
    - { "type": "boolean" }
    - { "type": "object", "properties": { "enabled": {...}, ... } }

    Args:
        schema: Root schema for resolving $ref.
        oneof_options: List of oneOf options from the schema.
        include_disabled: Include if enabled=false.
        skip_keys: Optional set of property names to skip.

    Returns:
        Dict of defaults from the object option, or None if not extractable.
    """
    for option in oneof_options:
        if option.get("type") == "object":
            props = option.get("properties", {})
            obj_defaults = _extract_defaults_from_properties(
                schema,
                props,
                include_disabled=include_disabled,
                skip_keys=skip_keys,
            )
            if obj_defaults:
                # Check if enabled default is False and we want to skip
                enabled = obj_defaults.get("enabled", True)
                if not include_disabled and enabled is False:
                    return None
                return obj_defaults
            # Even if no nested defaults, check for enabled property default
            if "enabled" in props:
                enabled_prop = props["enabled"]
                if "default" in enabled_prop:
                    return {"enabled": enabled_prop["default"]}
    return None


def _extract_defaults_from_properties(
    schema: dict[str, Any],
    properties: dict[str, Any],
    include_disabled: bool = True,
    skip_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Extract default values from a properties dict.

    Args:
        schema: Root schema for resolving $ref.
        properties: The properties dict to extract from.
        include_disabled: Include tools with enabled=false.
        skip_keys: Optional set of property names to skip.

    Returns:
        Dict of property names to their default values.
    """
    result: dict[str, Any] = {}

    for prop_name, prop_schema in properties.items():
        # Skip metadata fields
        if prop_name.startswith("_"):
            continue

        if skip_keys and prop_name in skip_keys:
            continue

        # Resolve $ref if present
        if "$ref" in prop_schema:
            prop_schema = _resolve_ref(schema, prop_schema["$ref"])

        if _is_deprecated(prop_schema):
            continue

        # Handle oneOf (tool definitions that can be bool or object)
        if "oneOf" in prop_schema:
            obj_defaults = _extract_oneOf_defaults(
                schema,
                prop_schema["oneOf"],
                include_disabled=include_disabled,
                skip_keys=skip_keys,
            )
            if obj_defaults is not None:
                result[prop_name] = obj_defaults
            continue

        # Handle nested objects
        if prop_schema.get("type") == "object":
            nested_props = prop_schema.get("properties", {})
            if nested_props:
                nested_defaults = _extract_defaults_from_properties(
                    schema,
                    nested_props,
                    include_disabled=include_disabled,
                    skip_keys=skip_keys,
                )
                if nested_defaults:
                    result[prop_name] = nested_defaults
            elif "default" in prop_schema:
                result[prop_name] = prop_schema["default"]
            continue

        # Handle simple types with defaults
        if "default" in prop_schema:
            result[prop_name] = prop_schema["default"]

    return result


# Skip deprecated aliases in tool defaults.
TOOL_DEFAULT_SKIP_KEYS = {"min_score"}

# Optional feature blocks are defined in schema but remain minimal in defaults.yaml.
OPTIONAL_FEATURE_KEYS = {
    "chaos",
    "canary",
    "dr_drill",
    "cache_sentinel",
    "runner_isolation",
    "supply_chain",
    "egress_control",
    "telemetry",
    "kyverno",
}


def extract_tool_defaults(
    schema: dict[str, Any],
    tools_def: dict[str, Any],
) -> dict[str, Any]:
    """Extract defaults for a tools definition (javaTools or pythonTools).

    Args:
        schema: Root schema for resolving $ref.
        tools_def: The javaTools or pythonTools definition.

    Returns:
        Dict mapping tool names to their default config dicts.
    """
    properties = tools_def.get("properties", {})
    return _extract_defaults_from_properties(
        schema,
        properties,
        skip_keys=TOOL_DEFAULT_SKIP_KEYS,
    )


def extract_all_defaults(schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract all default values from the schema.

    Args:
        schema: Optional pre-loaded schema dict.

    Returns:
        Complete defaults dict matching defaults.yaml structure.
    """
    if schema is None:
        schema = load_schema()

    definitions = schema.get("definitions", {})
    properties = schema.get("properties", {})

    defaults: dict[str, Any] = {}

    # Extract top-level properties with defaults
    for prop_name, prop_schema in properties.items():
        if prop_name.startswith("_"):
            continue

        # Resolve $ref
        if "$ref" in prop_schema:
            resolved = _resolve_ref(schema, prop_schema["$ref"])
            if resolved:
                prop_schema = resolved

        # Handle Java config
        if prop_name == "java":
            java_defaults: dict[str, Any] = {}
            java_props = prop_schema.get("properties", {})

            # Extract version, distribution, build_tool
            for key in ["version", "distribution", "build_tool"]:
                if key in java_props and "default" in java_props[key]:
                    java_defaults[key] = java_props[key]["default"]

            # Extract tools
            tools_ref = java_props.get("tools", {}).get("$ref", "")
            if tools_ref:
                tools_def = _resolve_ref(schema, tools_ref)
                java_defaults["tools"] = extract_tool_defaults(schema, tools_def)

            if java_defaults:
                defaults["java"] = java_defaults

        # Handle Python config
        elif prop_name == "python":
            python_defaults: dict[str, Any] = {}
            python_props = prop_schema.get("properties", {})

            # Extract version
            if "version" in python_props and "default" in python_props["version"]:
                python_defaults["version"] = python_props["version"]["default"]

            # Extract tools
            tools_ref = python_props.get("tools", {}).get("$ref", "")
            if tools_ref:
                tools_def = _resolve_ref(schema, tools_ref)
                python_defaults["tools"] = extract_tool_defaults(schema, tools_def)

            if python_defaults:
                defaults["python"] = python_defaults

        # Handle thresholds
        elif prop_name == "thresholds":
            thresholds_def = definitions.get("thresholds", {})
            thresholds_props = thresholds_def.get("properties", {})
            defaults["thresholds"] = _extract_defaults_from_properties(schema, thresholds_props)

        # Handle reports
        elif prop_name == "reports":
            reports_def = definitions.get("reports", {})
            reports_props = reports_def.get("properties", {})
            defaults["reports"] = _extract_defaults_from_properties(schema, reports_props)

        # Handle gates
        elif prop_name == "gates":
            gates_props = prop_schema.get("properties", {})
            defaults["gates"] = _extract_defaults_from_properties(schema, gates_props)

        # Handle cihub CLI config
        elif prop_name == "cihub":
            cihub_def = definitions.get("cihubConfig", {})
            cihub_props = cihub_def.get("properties", {})
            defaults["cihub"] = _extract_defaults_from_properties(schema, cihub_props)

        # Handle hub_ci
        elif prop_name == "hub_ci":
            hub_ci_def = definitions.get("hubCi", {})
            # hubCi is oneOf - extract defaults using the helper
            if "oneOf" in hub_ci_def:
                hub_ci_defaults = _extract_oneOf_defaults(schema, hub_ci_def["oneOf"])
                if hub_ci_defaults is not None:
                    defaults["hub_ci"] = hub_ci_defaults

        # Handle repo defaults
        elif prop_name == "repo":
            repo_props = prop_schema.get("properties", {})
            repo_defaults = {}
            for key, key_schema in repo_props.items():
                if "default" in key_schema:
                    repo_defaults[key] = key_schema["default"]
            if repo_defaults:
                defaults["repo"] = repo_defaults

        # Handle notifications
        elif prop_name == "notifications":
            notifications_props = prop_schema.get("properties", {})
            notifications_defaults = _extract_defaults_from_properties(
                schema,
                notifications_props,
            )
            if notifications_defaults:
                defaults["notifications"] = notifications_defaults

        # Handle install defaults (oneOf: string or object)
        elif prop_name == "install":
            one_of = prop_schema.get("oneOf", [])
            install_defaults = _extract_oneOf_defaults(schema, one_of)
            if install_defaults is not None:
                defaults["install"] = install_defaults

        # Handle harden_runner defaults (oneOf: boolean or object)
        elif prop_name == "harden_runner":
            one_of = prop_schema.get("oneOf", [])
            harden_defaults = _extract_oneOf_defaults(schema, one_of)
            if harden_defaults is not None:
                defaults["harden_runner"] = harden_defaults

        # Handle optional features (minimal enabled flag from schema defaults).
        elif prop_name in OPTIONAL_FEATURE_KEYS:
            one_of = prop_schema.get("oneOf", [])
            one_of_defaults = _extract_oneOf_defaults(schema, one_of)
            if one_of_defaults is not None:
                defaults[prop_name] = one_of_defaults

    return defaults


def generate_fallbacks_dict(schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate the FALLBACK_DEFAULTS dict for fallbacks.py.

    This uses schema-derived defaults to keep runtime fallbacks aligned
    with defaults.yaml.

    Args:
        schema: Optional pre-loaded schema dict.

    Returns:
        Dict suitable for FALLBACK_DEFAULTS in fallbacks.py.
    """
    if schema is None:
        schema = load_schema()

    return extract_all_defaults(schema)


def compare_with_current(
    schema_defaults: dict[str, Any],
    current_fallbacks: dict[str, Any],
    label: str = "fallbacks",
) -> list[str]:
    """Compare schema-derived defaults with current values.

    Args:
        schema_defaults: Defaults extracted from schema.
        current_fallbacks: Current values to compare against.
        label: Human-friendly label for drift messages.

    Returns:
        List of drift messages (empty if aligned).
    """
    drifts: list[str] = []

    def _compare(
        path: str,
        schema_val: Any,
        current_val: Any,
    ) -> None:
        if isinstance(schema_val, dict) and isinstance(current_val, dict):
            # Check for missing keys in current
            for key in schema_val:
                if key not in current_val:
                    drifts.append(f"Missing in {label}: {path}.{key}")
                else:
                    _compare(f"{path}.{key}", schema_val[key], current_val[key])
            # Check for extra keys in current (not necessarily wrong)
            for key in current_val:
                if key not in schema_val:
                    drifts.append(f"Extra in {label} (not in schema): {path}.{key}")
        elif schema_val != current_val:
            drifts.append(f"Value mismatch at {path}: schema={schema_val!r}, {label}={current_val!r}")

    _compare("root", schema_defaults, current_fallbacks)
    return drifts
