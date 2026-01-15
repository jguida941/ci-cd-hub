"""Internal utilities for registry commands."""

from __future__ import annotations

from pathlib import Path


def _derive_hub_root_from_configs_dir(configs_dir: Path) -> Path | None:
    """Best-effort derivation of hub root from a config/repos directory.

    This prevents cross-root profile leakage when users point --configs-dir at a
    different checkout.
    """
    try:
        configs_dir = configs_dir.resolve()
    except Exception:  # noqa: BLE001, S110
        pass

    try:
        if configs_dir.name == "repos" and configs_dir.parent.name == "config":
            return configs_dir.parent.parent
        if configs_dir.name == "config":
            return configs_dir.parent
    except Exception:  # noqa: BLE001
        return None

    # Heuristic: walk upward looking for a hub root (config/defaults.yaml + templates/profiles).
    try:
        parents = [configs_dir, *list(configs_dir.parents)[:5]]
        for candidate in parents:
            if (candidate / "config" / "defaults.yaml").exists() and (candidate / "templates" / "profiles").exists():
                return candidate
    except Exception:  # noqa: BLE001
        return None

    return None
