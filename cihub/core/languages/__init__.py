"""Language strategy package for CI engine.

This package provides the LanguageStrategy abstraction that encapsulates
all language-specific CI behavior, eliminating conditional branches.

Usage:
    from cihub.core.languages import get_strategy

    strategy = get_strategy("python")
    tool_results = strategy.run_tools(config, repo_path, workdir, output_dir, problems)
    failures = strategy.evaluate_gates(report, thresholds, tools_configured, config)
"""

from cihub.core.languages.base import LanguageStrategy
from cihub.core.languages.registry import LANGUAGE_STRATEGIES, get_strategy

__all__ = [
    "LanguageStrategy",
    "get_strategy",
    "LANGUAGE_STRATEGIES",
]
