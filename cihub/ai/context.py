"""Build structured context for AI prompts.

Instead of AI searching files, we provide all context upfront.
This makes AI faster and more accurate.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cihub.services.triage.types import CATEGORY_BY_TOOL, SEVERITY_BY_CATEGORY

if TYPE_CHECKING:
    from cihub.types import CommandResult


def build_context(
    result: "CommandResult",
    *,
    include_tool_registry: bool = True,
    include_suggestions: bool = True,
) -> str:
    """Build structured context string for AI.

    Args:
        result: The CommandResult to analyze.
        include_tool_registry: Include tool categorization info.
        include_suggestions: Include existing suggestions.

    Returns:
        Formatted context string for AI prompt.
    """
    sections: list[str] = []

    sections.append(f"""## Command Result
- Command: {result.artifacts.get("command", "unknown")}
- Exit Code: {result.exit_code}
- Summary: {result.summary}
""")

    if result.problems:
        problems_text = json.dumps(result.problems, indent=2)
        sections.append(f"""## Problems Found
```json
{problems_text}
```
""")

    if include_tool_registry:
        sections.append(f"""## Tool Categorization (Reference)
Categories: {json.dumps(CATEGORY_BY_TOOL, indent=2)}
Severity Mapping: {json.dumps(SEVERITY_BY_CATEGORY, indent=2)}
""")

    if include_suggestions and result.suggestions:
        suggestions_text = "\n".join(f"- {s.get('message', '')}" for s in result.suggestions)
        sections.append(f"""## Existing Suggestions
{suggestions_text}
""")

    return "\n".join(sections)
