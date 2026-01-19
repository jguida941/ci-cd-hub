"""Language detection helpers for repo layouts."""

from __future__ import annotations

from pathlib import Path

from cihub.core.languages.registry import (
    detect_language_with_scores,
    get_strategy,
    list_supported_languages,
)


def _collect_reasons(repo_path: Path) -> list[str]:
    reasons: list[str] = []
    for language in list_supported_languages():
        strategy = get_strategy(language)
        reasons.extend(strategy.detect_reasons(repo_path))
    return reasons


def detect_language(repo_path: Path) -> tuple[str | None, list[str]]:
    try:
        language, scores = detect_language_with_scores(repo_path)
    except ValueError:
        return None, _collect_reasons(repo_path)

    reasons = get_strategy(language).detect_reasons(repo_path)
    if not reasons:
        score = scores.get(language, 0.0)
        reasons = [f"{language} confidence {score:.2f}"]
    return language, reasons


def resolve_language(repo_path: Path, override: str | None) -> tuple[str, list[str]]:
    if override:
        return override, []
    detected, reasons = detect_language(repo_path)
    if not detected:
        reason_text = ", ".join(reasons) if reasons else "no language markers found"
        raise ValueError(f"Unable to detect language ({reason_text}); use --language.")
    return detected, reasons
