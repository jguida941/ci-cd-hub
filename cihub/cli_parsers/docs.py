"""Parser setup for docs commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_docs_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    docs = subparsers.add_parser("docs", help="Generate reference documentation", epilog=see_also_epilog("docs"))
    docs.set_defaults(func=handlers.cmd_docs)
    docs_sub = docs.add_subparsers(dest="subcommand", required=True)

    docs_generate = docs_sub.add_parser("generate", help="Generate CLI, config, env, and workflow reference docs")
    add_json_flag(docs_generate)
    docs_generate.add_argument(
        "--output",
        default="docs/reference",
        help="Output directory (default: docs/reference)",
    )
    docs_generate.add_argument(
        "--check",
        action="store_true",
        help="Fail if docs would change",
    )
    docs_generate.set_defaults(func=handlers.cmd_docs)

    docs_check = docs_sub.add_parser("check", help="Check reference docs are up to date")
    add_json_flag(docs_check)
    docs_check.add_argument(
        "--output",
        default="docs/reference",
        help="Output directory (default: docs/reference)",
    )
    docs_check.set_defaults(func=handlers.cmd_docs)

    docs_links = docs_sub.add_parser("links", help="Check documentation for broken links")
    add_json_flag(docs_links)
    docs_links.add_argument(
        "--external",
        action="store_true",
        help="Also check external (http/https) links (requires lychee)",
    )
    docs_links.set_defaults(func=handlers.cmd_docs_links)

    # docs stale - detect stale documentation references (DOC_AUTOMATION_AUDIT.md Part 9)
    docs_stale = docs_sub.add_parser(
        "stale",
        help="Detect stale documentation references to removed/renamed code",
    )
    add_json_flag(docs_stale)
    docs_stale.add_argument(
        "--since",
        default="HEAD~10",
        help="Git revision range (default: HEAD~10)",
    )
    docs_stale.add_argument(
        "--all",
        action="store_true",
        help="Include archived docs (docs/development/archive/)",
    )
    docs_stale.add_argument(
        "--include-generated",
        action="store_true",
        help="Include generated docs (docs/reference/) - rarely needed",
    )
    docs_stale.add_argument(
        "--ai",
        action="store_true",
        help="AI-consumable markdown output (no network calls)",
    )
    docs_stale.add_argument(
        "--fail-on-stale",
        action="store_true",
        help="Exit non-zero if stale refs found (for CI)",
    )
    docs_stale.add_argument(
        "--code",
        default="cihub",
        help="Code directory (default: cihub/)",
    )
    docs_stale.add_argument(
        "--docs",
        default="docs",
        help="Docs directory (default: docs/)",
    )
    docs_stale.add_argument(
        "--skip-fences",
        action="store_true",
        help="Skip bash/shell code fences (default: parse them)",
    )
    docs_stale.add_argument(
        "--output-dir",
        help="Output dir for CIHub-style artifacts (e.g., .cihub/tool-outputs)",
    )
    docs_stale.add_argument(
        "--tool-output",
        help="Path to write tool-style JSON (for triage/tool-outputs)",
    )
    docs_stale.add_argument(
        "--ai-output",
        help="Path to write the AI prompt pack (markdown)",
    )
    docs_stale.add_argument(
        "--github-summary",
        action="store_true",
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    docs_stale.set_defaults(func=handlers.cmd_docs_stale)

    # docs audit - documentation lifecycle and metadata audit (DOC_AUTOMATION_AUDIT.md Part 12.J)
    docs_audit = docs_sub.add_parser(
        "audit",
        help="Validate documentation lifecycle, ADR metadata, and references",
    )
    add_json_flag(docs_audit)
    docs_audit.add_argument(
        "--output-dir",
        help="Output dir for CIHub-style artifacts (e.g., .cihub/tool-outputs)",
    )
    docs_audit.add_argument(
        "--inventory",
        action="store_true",
        help="Include doc inventory counts in JSON output",
    )
    docs_audit.add_argument(
        "--skip-references",
        action="store_true",
        help="Skip plain-text reference scanning (faster)",
    )
    docs_audit.add_argument(
        "--skip-headers",
        action="store_true",
        help="Skip Part 12.Q universal header validation",
    )
    docs_audit.add_argument(
        "--skip-consistency",
        action="store_true",
        help="Skip Part 13 consistency checks (duplicates, timestamps, placeholders)",
    )
    docs_audit.add_argument(
        "--github-summary",
        action="store_true",
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    docs_audit.set_defaults(func=handlers.cmd_docs_audit)
