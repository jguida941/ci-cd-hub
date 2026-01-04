"""Language detection helpers for repo layouts."""

from __future__ import annotations

from pathlib import Path


def detect_language(repo_path: Path) -> tuple[str | None, list[str]]:
    checks = {
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "python": ["pyproject.toml", "requirements.txt", "setup.py"],
    }
    matches: dict[str, list[str]] = {"java": [], "python": []}
    for language, files in checks.items():
        for name in files:
            if (repo_path / name).exists():
                matches[language].append(name)

    java_found = bool(matches["java"])
    python_found = bool(matches["python"])

    if java_found and not python_found:
        return "java", matches["java"]
    if python_found and not java_found:
        return "python", matches["python"]
    if java_found and python_found:
        return None, matches["java"] + matches["python"]
    return None, []


def resolve_language(repo_path: Path, override: str | None) -> tuple[str, list[str]]:
    if override:
        return override, []
    detected, reasons = detect_language(repo_path)
    if not detected:
        reason_text = ", ".join(reasons) if reasons else "no language markers found"
        raise ValueError(f"Unable to detect language ({reason_text}); use --language.")
    return detected, reasons
