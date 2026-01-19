"""Language strategy registry.

This module provides the central registry for language strategies and
functions to retrieve strategies by name or auto-detect from a repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import LanguageStrategy

# Lazy initialization to avoid import issues
_strategies: dict[str, LanguageStrategy] | None = None


def _init_strategies() -> dict[str, LanguageStrategy]:
    """Initialize and return strategy instances (lazy singleton)."""
    global _strategies
    if _strategies is None:
        from .java import JavaStrategy
        from .python import PythonStrategy

        _strategies = {
            "python": PythonStrategy(),
            "java": JavaStrategy(),
        }
    return _strategies


# Make LANGUAGE_STRATEGIES a module-level constant that works like a dict
class _StrategiesProxy:
    """Proxy class to make LANGUAGE_STRATEGIES work as a module-level constant."""

    def __getitem__(self, key: str) -> LanguageStrategy:
        return _init_strategies()[key]

    def __contains__(self, key: str) -> bool:
        return key in _init_strategies()

    def get(self, key: str, default: LanguageStrategy | None = None) -> LanguageStrategy | None:
        return _init_strategies().get(key, default)

    def keys(self):
        return _init_strategies().keys()

    def values(self):
        return _init_strategies().values()

    def items(self):
        return _init_strategies().items()


LANGUAGE_STRATEGIES = _StrategiesProxy()


def get_strategy(language: str) -> LanguageStrategy:
    """Get the strategy for a specific language.

    Args:
        language: Language identifier (e.g., 'python', 'java')

    Returns:
        The LanguageStrategy instance for the specified language

    Raises:
        ValueError: If the language is not supported
    """
    strategies = _init_strategies()
    strategy = strategies.get(language)
    if strategy is None:
        supported = ", ".join(sorted(strategies.keys()))
        raise ValueError(f"Unsupported language: {language}. Supported: {supported}")
    return strategy


def detect_language_with_scores(repo_path: Path) -> tuple[str, dict[str, float]]:
    """Auto-detect the project language and return confidence scores.

    Uses confidence scoring from each strategy's detect() method.
    Returns the language with highest confidence above 0.5 threshold.

    Args:
        repo_path: Path to the repository root

    Returns:
        Tuple of (detected language identifier, scores by language).

    Raises:
        ValueError: If no language could be detected with sufficient confidence
    """
    strategies = _init_strategies()
    scores = {lang: strategy.detect(repo_path) for lang, strategy in strategies.items()}

    best_lang = None
    best_score = 0.0
    for lang, score in scores.items():
        if score > best_score:
            best_score = score
            best_lang = lang

    if best_score < 0.5 or best_lang is None:
        raise ValueError(f"Could not detect language in {repo_path}. No language markers found with confidence >= 0.5")

    return best_lang, scores


def detect_language(repo_path: Path) -> str:
    """Auto-detect the project language from repository contents."""
    language, _ = detect_language_with_scores(repo_path)
    return language


def list_supported_languages() -> list[str]:
    """Return list of supported language identifiers."""
    return sorted(_init_strategies().keys())
