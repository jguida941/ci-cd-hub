"""Security tool prompts shared across languages."""

from __future__ import annotations

import questionary

from cihub.wizard.styles import get_style


def configure_security_tools(language: str, defaults: dict) -> dict:
    """Prompt for security tool toggles.

    Returns a dict of overrides to merge into config.
    """
    overrides: dict = {}
    if language == "java":
        base = defaults.get("java", {}).get("tools", {})
        semgrep_default = base.get("semgrep", {}).get("enabled", False)
        trivy_default = base.get("trivy", {}).get("enabled", False)
        codeql_default = base.get("codeql", {}).get("enabled", False)
        semgrep = questionary.confirm(
            "Enable semgrep?",
            default=bool(semgrep_default),
            style=get_style(),
        ).ask()
        trivy = questionary.confirm(
            "Enable trivy?",
            default=bool(trivy_default),
            style=get_style(),
        ).ask()
        codeql = questionary.confirm(
            "Enable codeql?",
            default=bool(codeql_default),
            style=get_style(),
        ).ask()
        overrides = {
            "java": {
                "tools": {
                    "semgrep": {"enabled": bool(semgrep)},
                    "trivy": {"enabled": bool(trivy)},
                    "codeql": {"enabled": bool(codeql)},
                }
            }
        }
    elif language == "python":
        base = defaults.get("python", {}).get("tools", {})
        semgrep_default = base.get("semgrep", {}).get("enabled", False)
        trivy_default = base.get("trivy", {}).get("enabled", False)
        codeql_default = base.get("codeql", {}).get("enabled", False)
        semgrep = questionary.confirm(
            "Enable semgrep?",
            default=bool(semgrep_default),
            style=get_style(),
        ).ask()
        trivy = questionary.confirm(
            "Enable trivy?",
            default=bool(trivy_default),
            style=get_style(),
        ).ask()
        codeql = questionary.confirm(
            "Enable codeql?",
            default=bool(codeql_default),
            style=get_style(),
        ).ask()
        overrides = {
            "python": {
                "tools": {
                    "semgrep": {"enabled": bool(semgrep)},
                    "trivy": {"enabled": bool(trivy)},
                    "codeql": {"enabled": bool(codeql)},
                }
            }
        }
    return overrides
