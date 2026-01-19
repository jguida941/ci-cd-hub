"""Wizard runner orchestration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, TypeVar

import questionary
from rich.console import Console

from cihub.config.io import ConfigParseError, load_defaults, load_profile_strict
from cihub.config.merge import deep_merge
from cihub.config.paths import PathConfig
from cihub.wizard import WizardCancelled
from cihub.wizard.styles import get_style
from cihub.wizard.validators import validate_repo_name

T = TypeVar("T")


@dataclass
class WizardResult:
    """Result from wizard containing config and metadata."""

    config: dict[str, Any] = field(default_factory=dict)
    tier: str = "standard"
    profile: str | None = None
    repo_name: str = ""


def _check_cancelled(value: T | None, ctx: str) -> T:
    if value is None:
        raise WizardCancelled(f"{ctx} cancelled")
    return value


class WizardRunner:
    """Interactive wizard orchestration for config creation/editing."""

    def __init__(self, console: Console, paths: PathConfig) -> None:
        self.console = console
        self.paths = paths

    def _load_base(self, profile: str | None) -> dict:
        defaults = load_defaults(self.paths)
        if profile:
            try:
                profile_cfg = load_profile_strict(self.paths, profile)
            except ConfigParseError as e:
                self.console.print(f"[red]Error loading profile '{profile}': {e}[/red]")
                raise WizardCancelled(f"Profile '{profile}' contains invalid YAML") from e
            return deep_merge(defaults, profile_cfg)
        return defaults

    def _prompt_profile_and_tier(self, language: str, *, skip_tier: bool = False) -> tuple[str | None, str]:
        """Prompt for profile and tier selection.

        Args:
            language: Language to filter profiles
            skip_tier: If True, skip tier prompt (tier was pre-selected via CLI)

        Returns:
            Tuple of (profile_name, tier_name)
        """
        from cihub.wizard.questions.profile import select_profile, select_tier

        # Show profile selection
        self.console.print("\n[bold]Profile Selection[/bold]")
        self.console.print("Profiles pre-configure tools for common CI patterns.\n")

        from pathlib import Path

        profile = select_profile(language, profiles_dir=Path(self.paths.profiles_dir))

        # Only prompt for tier if not pre-selected via CLI
        if skip_tier:
            tier = "standard"  # Placeholder; caller will use pre-selected tier
        else:
            self.console.print("\n[bold]Quality Tier[/bold]")
            self.console.print("Tiers set default thresholds for coverage, mutation, etc.\n")
            tier = select_tier()

        return profile, tier

    def _prompt_repo(self, name: str | None, base: dict) -> dict:
        repo_defaults = base.get("repo", {})
        owner: str = _check_cancelled(
            questionary.text(
                "Repo owner (org/user):",
                default=repo_defaults.get("owner", ""),
                style=get_style(),
            ).ask(),
            "Repo owner",
        )
        repo_name: str = _check_cancelled(
            questionary.text(
                "Repo name:",
                default=name or repo_defaults.get("name", ""),
                validate=validate_repo_name,
                style=get_style(),
            ).ask(),
            "Repo name",
        )
        use_central_runner: bool = _check_cancelled(
            questionary.confirm(
                "Use central runner?",
                default=bool(repo_defaults.get("use_central_runner", True)),
                style=get_style(),
            ).ask(),
            "Central runner prompt",
        )
        repo_side_execution: bool = _check_cancelled(
            questionary.confirm(
                "Enable repo-side execution (writes workflows)?",
                default=bool(repo_defaults.get("repo_side_execution", False)),
                style=get_style(),
            ).ask(),
            "Repo-side execution prompt",
        )
        repo_config = dict(repo_defaults) if isinstance(repo_defaults, dict) else {}
        repo_config.update(
            {
                "owner": str(owner),
                "name": str(repo_name),
                "use_central_runner": bool(use_central_runner),
                "repo_side_execution": bool(repo_side_execution),
            }
        )
        return repo_config

    def _apply_language_prompts(self, config: dict, *, skip_language: bool = False) -> dict:
        from cihub.wizard.questions.advanced import configure_advanced_settings
        from cihub.wizard.questions.java_tools import configure_java_tools
        from cihub.wizard.questions.language import (
            select_build_tool,
            select_java_version,
            select_language,
            select_python_version,
        )
        from cihub.wizard.questions.python_tools import configure_python_tools
        from cihub.wizard.questions.security import configure_security_tools
        from cihub.wizard.questions.thresholds import configure_thresholds

        defaults = config

        # Language selection (may be skipped if already selected)
        if not skip_language:
            language = select_language(default=defaults.get("language", "java"))
            config["language"] = language
        else:
            language = config.get("language", "java")

        # Language-specific configuration
        if language == "java":
            java_cfg = deepcopy(defaults.get("java", {}))
            java_cfg["version"] = select_java_version(default=str(java_cfg.get("version", "21")))
            java_cfg["build_tool"] = select_build_tool(default=str(java_cfg.get("build_tool", "maven")))
            java_cfg["tools"] = configure_java_tools(defaults)
            config["java"] = java_cfg
        elif language == "python":
            py_cfg = deepcopy(defaults.get("python", {}))
            py_cfg["version"] = select_python_version(default=str(py_cfg.get("version", "3.12")))
            py_cfg["tools"] = configure_python_tools(defaults)
            config["python"] = py_cfg

        # Security tools
        security_overrides = configure_security_tools(language, defaults)
        config = deep_merge(config, security_overrides)

        # Thresholds
        config["thresholds"] = configure_thresholds(defaults)

        # Advanced settings (gates, reports, notifications, harden_runner)
        advanced = configure_advanced_settings(defaults)
        if advanced:
            config = deep_merge(config, advanced)

        return config

    def run_new_wizard(
        self,
        name: str,
        profile: str | None = None,
        tier: str | None = None,
        skip_profile_selection: bool = False,
    ) -> WizardResult:
        """Run the new repo wizard with profile and tier selection.

        Args:
            name: Repo name
            profile: Pre-selected profile (skips profile prompt if set)
            tier: Pre-selected tier (skips tier prompt if set)
            skip_profile_selection: Skip profile/tier selection entirely

        Returns:
            WizardResult with config, tier, profile, and repo_name
        """
        from cihub.wizard.questions.language import select_language

        # Step 1: Basic repo info first to get language
        base = self._load_base(profile)
        config = deepcopy(base)

        # Prompt for language first (needed for profile selection)
        self.console.print("\n[bold]Language Detection[/bold]")
        language = select_language(default=base.get("language", "python"))
        config["language"] = language

        # Step 2: Profile and tier selection (if not pre-selected)
        selected_profile = profile
        selected_tier = tier or "standard"

        if not skip_profile_selection and profile is None:
            # Only prompt for tier if not already provided via CLI
            prompted_profile, prompted_tier = self._prompt_profile_and_tier(language, skip_tier=(tier is not None))
            selected_profile = prompted_profile
            if tier is None:
                selected_tier = prompted_tier

            # Load profile config if selected
            if selected_profile:
                full_profile_name = f"{language}-{selected_profile}"
                try:
                    profile_cfg = load_profile_strict(self.paths, full_profile_name)
                    config = deep_merge(config, profile_cfg)
                except FileNotFoundError:
                    self.console.print(f"[yellow]Profile '{full_profile_name}' not found, using defaults[/yellow]")
                except ConfigParseError as e:
                    self.console.print(f"[red]Error loading profile '{full_profile_name}': {e}[/red]")
                    raise WizardCancelled(f"Profile '{full_profile_name}' contains invalid YAML") from e

        # Step 3: Repo metadata
        config["repo"] = self._prompt_repo(name, config)
        config["repo"]["language"] = language

        # Step 4: Language-specific tool configuration (pre-filled from profile)
        # Language already selected in step 1, so skip language prompt
        config = self._apply_language_prompts(config, skip_language=True)

        repo_name = config.get("repo", {}).get("name", name)

        return WizardResult(
            config=config,
            tier=selected_tier,
            profile=selected_profile,
            repo_name=repo_name,
        )

    def run_init_wizard(self, detected: dict) -> WizardResult:
        """Run the init wizard for detected repos.

        Returns:
            WizardResult with config, tier, profile, and repo_name
        """
        base = self._load_base(profile=None)
        config = deep_merge(base, detected)
        repo_name = detected.get("repo", {}).get("name", "")

        # Get language from detection
        language = detected.get("language") or config.get("language") or "python"

        # Profile and tier selection
        profile, tier = self._prompt_profile_and_tier(language)

        # Load profile if selected
        if profile:
            full_profile_name = f"{language}-{profile}"
            try:
                profile_cfg = load_profile_strict(self.paths, full_profile_name)
                config = deep_merge(config, profile_cfg)
            except FileNotFoundError:
                self.console.print(f"[yellow]Profile '{full_profile_name}' not found, using defaults[/yellow]")
            except ConfigParseError as e:
                self.console.print(f"[red]Error loading profile '{full_profile_name}': {e}[/red]")
                raise WizardCancelled(f"Profile '{full_profile_name}' contains invalid YAML") from e

        config["repo"] = self._prompt_repo(repo_name, config)
        config = self._apply_language_prompts(config)

        final_repo_name = config.get("repo", {}).get("name", repo_name)

        return WizardResult(
            config=config,
            tier=tier,
            profile=profile,
            repo_name=final_repo_name,
        )

    def run_config_wizard(self, existing: dict) -> WizardResult:
        """Run the config editing wizard.

        Returns:
            WizardResult with config, tier, profile, and repo_name
        """
        config = deepcopy(existing)
        repo_name = existing.get("repo", {}).get("name", "")
        config["repo"] = self._prompt_repo(repo_name, existing)
        config = self._apply_language_prompts(config)

        final_repo_name = config.get("repo", {}).get("name", repo_name)

        # For editing, we don't change tier (would need to query registry)
        return WizardResult(
            config=config,
            tier="standard",  # Default; caller should preserve existing tier
            profile=None,
            repo_name=final_repo_name,
        )

    # Legacy compatibility: return just config dict
    def run_new_wizard_legacy(self, name: str, profile: str | None = None) -> dict:
        """Legacy method returning just config dict for backwards compatibility."""
        result = self.run_new_wizard(name, profile=profile, skip_profile_selection=True)
        return result.config

    def run_init_wizard_legacy(self, detected: dict) -> dict:
        """Legacy method returning just config dict for backwards compatibility."""
        result = self.run_init_wizard(detected)
        return result.config

    def run_config_wizard_legacy(self, existing: dict) -> dict:
        """Legacy method returning just config dict for backwards compatibility."""
        result = self.run_config_wizard(existing)
        return result.config
