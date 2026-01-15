"""Registry I/O operations.

Handles loading and saving the registry from/to disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.services.registry import _paths as _registry_paths
from cihub.services.registry.normalize import _normalize_registry_inplace


def _get_registry_path() -> Path:
    """Get the path to the registry file."""
    return _registry_paths.get_hub_root() / "config" / "registry.json"


def load_registry(registry_path: Path | None = None) -> dict[str, Any]:
    """Load the registry from disk.

    Args:
        registry_path: Path to registry.json (defaults to config/registry.json)

    Returns:
        Parsed registry dict
    """
    path = registry_path or _get_registry_path()
    if not path.exists():
        return {"schema_version": "cihub-registry-v1", "tiers": {}, "repos": {}}

    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        _normalize_registry_inplace(data)
        return data


def save_registry(registry: dict[str, Any], registry_path: Path | None = None) -> None:
    """Save the registry to disk.

    Args:
        registry: Registry dict to save
        registry_path: Path to registry.json (defaults to config/registry.json)
    """
    path = registry_path or _get_registry_path()
    _normalize_registry_inplace(registry)
    with path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")
