"""Generate reference documentation from code and schema."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

from cihub.cli_parsers.builder import build_parser
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.paths import hub_root

# Regex to match markdown links: [text](path) or [text](path#anchor)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
FENCED_BLOCK_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
REFERENCE_DEF_RE = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)


def _strip_fenced_blocks(content: str) -> str:
    return FENCED_BLOCK_RE.sub("", content)


def _link_is_external(link_target: str) -> bool:
    return link_target.startswith(("http://", "https://", "mailto:", "tel:"))


def _resolve_link(md_file: Path, repo_root: Path, link_target: str) -> Path:
    if link_target.startswith("/"):
        return (repo_root / link_target.lstrip("/")).resolve()
    return (md_file.parent / link_target).resolve()


def _format_doc_path(md_file: Path, docs_dir: Path, repo_root: Path) -> str:
    try:
        return str(md_file.relative_to(docs_dir))
    except ValueError:
        try:
            return str(md_file.relative_to(repo_root))
        except ValueError:
            return str(md_file)


def _normalize_link_target(link_target: str) -> str:
    cleaned = link_target.split("#", 1)[0]
    return cleaned.split("?", 1)[0]


def _check_internal_links(docs_dir: Path) -> list[dict[str, Any]]:
    """Check internal markdown links without external tools.

    Scans all .md files for relative links and verifies targets exist.
    """
    problems: list[dict[str, Any]] = []
    repo_root = docs_dir.parent
    md_files = list(docs_dir.rglob("*.md"))
    root_readme = repo_root / "README.md"
    if docs_dir.name == "docs" and root_readme.exists():
        md_files.append(root_readme)

    for md_file in md_files:
        # Archived docs are historical; they are excluded from link checking to avoid
        # requiring churn to keep old/superseded docs up to date.
        try:
            rel = md_file.relative_to(docs_dir).as_posix()
            if rel.startswith("development/archive/"):
                continue
        except ValueError:
            # Root README.md is checked too; keep it in scope.
            pass

        content = md_file.read_text(encoding="utf-8")
        content = _strip_fenced_blocks(content)

        for match in REFERENCE_DEF_RE.finditer(content):
            ref_id, link_target = match.groups()
            if link_target.startswith("#") or _link_is_external(link_target):
                continue
            target_path = _normalize_link_target(link_target)
            if not target_path:
                continue
            resolved = _resolve_link(md_file, repo_root, target_path)
            if not resolved.exists():
                problems.append(
                    {
                        "severity": "error",
                        "message": (
                            f"Broken reference link in "
                            f"{_format_doc_path(md_file, docs_dir, repo_root)}: "
                            f"[{ref_id}]: {link_target}"
                        ),
                        "code": "CIHUB-DOCS-BROKEN-LINK",
                        "file": str(md_file),
                        "target": link_target,
                    }
                )
        for match in MARKDOWN_LINK_RE.finditer(content):
            link_text, link_target = match.groups()

            # Skip external links, anchors-only, and mailto
            if link_target.startswith("#") or _link_is_external(link_target):
                continue

            # Handle anchor in link
            target_path = _normalize_link_target(link_target)
            if not target_path:
                continue

            # Resolve relative to the markdown file's directory
            resolved = _resolve_link(md_file, repo_root, target_path)

            if not resolved.exists():
                problems.append(
                    {
                        "severity": "error",
                        "message": (
                            f"Broken link in "
                            f"{_format_doc_path(md_file, docs_dir, repo_root)}: "
                            f"[{link_text}]({link_target})"
                        ),
                        "code": "CIHUB-DOCS-BROKEN-LINK",
                        "file": str(md_file),
                        "target": link_target,
                    }
                )

    return problems


def _run_lychee(docs_dir: Path, external: bool) -> tuple[int, list[dict[str, Any]]]:
    """Run lychee link checker.

    Args:
        docs_dir: Directory to check.
        external: If True, check external links too. If False, offline mode.

    Returns:
        Tuple of (exit_code, problems).
    """
    repo_root = docs_dir.parent
    inputs = ["docs"]
    if (repo_root / "README.md").exists():
        inputs.append("README.md")

    cmd = [
        "lychee",
        *inputs,
        "--no-progress",
        "--mode",
        "plain",
        "--format",
        "json",
        "--root-dir",
        str(repo_root),
        "--exclude-path",
        r"docs/development/archive/.*",
    ]
    if not external:
        cmd.append("--offline")

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=300,  # Link checking can be slow
        )
    except FileNotFoundError:
        return -1, []  # lychee not found

    problems: list[dict[str, Any]] = []
    if result.returncode != 0:
        # Parse lychee JSON output for broken links.
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            payload = {}

        error_map = payload.get("error_map") if isinstance(payload, dict) else None
        if isinstance(error_map, dict):
            for doc_path, entries in error_map.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    url = str(entry.get("url") or "-")
                    status_raw = entry.get("status")
                    status: dict[str, Any] = status_raw if isinstance(status_raw, dict) else {}
                    status_text = str(status.get("text") or "").strip()
                    status_details = str(status.get("details") or "").strip()

                    extra = ""
                    if status_text and status_details:
                        extra = f" | {status_text} ({status_details})"
                    elif status_text:
                        extra = f" | {status_text}"

                    problems.append(
                        {
                            "severity": "error",
                            "message": f"{doc_path}: {url}{extra}",
                            "code": "CIHUB-DOCS-LYCHEE",
                            "file": str(doc_path),
                            "url": url,
                            "status": status_text,
                            "details": status_details,
                        }
                    )

        # Fallback: surface lychee stderr/stdout if JSON parsing failed or provided no details.
        if not problems:
            detail = (result.stderr or "").strip() or (result.stdout or "").strip()
            problems.append(
                {
                    "severity": "error",
                    "message": f"lychee failed with exit {result.returncode}",
                    "detail": detail,
                    "code": "CIHUB-DOCS-LYCHEE",
                }
            )

    return result.returncode, problems


def cmd_docs_links(args: argparse.Namespace) -> CommandResult:
    """Check documentation for broken links.

    Always returns CommandResult for consistent output handling.
    """
    external = getattr(args, "external", False)
    docs_dir = hub_root() / "docs"

    # Try lychee first
    has_lychee = shutil.which("lychee") is not None
    warnings: list[dict[str, Any]] = []

    if has_lychee:
        exit_code, problems = _run_lychee(docs_dir, external)
        if exit_code < 0:
            has_lychee = False
        else:
            tool_used = "lychee"

    if not has_lychee:
        # Fallback to internal checker (always offline)
        if external:
            warnings.append({
                "severity": "warning",
                "message": "--external requires lychee. Install with: brew install lychee",
                "code": "CIHUB-DOCS-NO-LYCHEE",
            })
        problems = _check_internal_links(docs_dir)
        exit_code = EXIT_FAILURE if problems else EXIT_SUCCESS
        tool_used = "internal"

    failed = exit_code != EXIT_SUCCESS
    summary = f"Link check ({tool_used}): {len(problems)} issues" if failed else f"Link check ({tool_used}): OK"

    # Combine warnings and problems
    all_problems = warnings + problems

    # Format problem messages for human-readable output
    items = [summary]
    for problem in problems:
        items.append(f"  {problem['message']}")

    return CommandResult(
        exit_code=EXIT_FAILURE if failed else EXIT_SUCCESS,
        summary=summary,
        problems=all_problems,
        data={"tool": tool_used, "external": external, "items": items},
    )


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:  # noqa: SLF001 - argparse internals
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return action.choices
    return {}


def _format_help(parser: argparse.ArgumentParser, title: str) -> str:
    help_text = parser.format_help().rstrip()
    return f"## {title}\n\n```\n{help_text}\n```\n"


def _render_parser_docs(parser: argparse.ArgumentParser, title: str) -> str:
    parts = [_format_help(parser, title)]
    for name, sub in _subparsers(parser).items():
        parts.append(_render_parser_docs(sub, f"{title} {name}"))
    return "\n".join(parts)


def _render_cli_reference() -> str:
    parser = build_parser()
    header = [
        "# CLI Reference",
        "",
        "Generated by `cihub docs generate`. Do not edit.",
        "",
    ]
    body = _render_parser_docs(parser, "cihub")
    return "\n".join(header) + body + "\n"


def _format_type(prop: dict[str, Any]) -> str:
    if "type" in prop:
        value = prop["type"]
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value)
    if "enum" in prop:
        return "enum"
    if "oneOf" in prop:
        options: list[str] = []
        for option in prop["oneOf"]:
            if isinstance(option, dict):
                option_type = _format_type(option)
                if option_type:
                    options.append(option_type)
        deduped: list[str] = []
        for option in options:
            if option not in deduped:
                deduped.append(option)
        return "|".join(deduped) if deduped else "oneOf"
    if "anyOf" in prop:
        return "anyOf"
    if "properties" in prop:
        return "object"
    return "unknown"


def _format_default(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, bool, int, float)):
        return json.dumps(value)
    return str(value)


def _sanitize(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


SCHEMA_SOURCE = "schema/ci-hub-config.schema.json"


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    node: Any = schema
    for part in ref[2:].split("/"):
        if not isinstance(node, dict):
            return {}
        node = node.get(part)
        if node is None:
            return {}
    return node if isinstance(node, dict) else {}


def _merge_schema(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key == "$ref":
            continue
        if key == "properties" and isinstance(value, dict):
            existing = merged.get("properties")
            if isinstance(existing, dict):
                merged["properties"] = {**existing, **value}
                continue
        if key == "required" and isinstance(value, list):
            existing_required = merged.get("required")
            if isinstance(existing_required, list):
                merged["required"] = list(dict.fromkeys([*existing_required, *value]))
                continue
        merged[key] = value
    return merged


def _resolve_schema(schema: dict[str, Any], prop: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in prop:
        return prop
    resolved = _resolve_ref(schema, prop["$ref"])
    if not resolved:
        return prop
    return _merge_schema(resolved, prop)


def _schema_entries(
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    prefix: str = "",
) -> Iterable[dict[str, str]]:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for name, prop in properties.items():
        prop = _resolve_schema(root_schema, prop)
        path = f"{prefix}.{name}" if prefix else name
        description = prop.get("description", "") or ""
        entry = {
            "path": path,
            "type": _format_type(prop),
            "required": "yes" if name in required else "no",
            "default": _format_default(prop.get("default")),
            "description": _sanitize(str(description)),
        }
        yield entry

        if "properties" in prop:
            yield from _schema_entries(prop, root_schema, path)
        elif prop.get("type") == "array" and isinstance(prop.get("items"), dict):
            items = _resolve_schema(root_schema, prop["items"])
            if "properties" in items:
                yield from _schema_entries(items, root_schema, f"{path}[]")


def _render_config_reference() -> str:
    schema_path = hub_root() / SCHEMA_SOURCE
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    lines = [
        "# Config Reference",
        "",
        "Generated by `cihub docs generate`. Do not edit.",
        "",
        f"Source: `{SCHEMA_SOURCE}`",
        "",
        "| Path | Type | Required | Default | Description |",
        "| --- | --- | --- | --- | --- |",
    ]

    for entry in _schema_entries(schema, schema):
        default = _sanitize(entry["default"])
        line = f"| `{entry['path']}` | {entry['type']} | {entry['required']} | {default} | {entry['description']} |"
        lines.append(line)

    return "\n".join(lines) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def cmd_docs(args: argparse.Namespace) -> CommandResult:
    """Generate or check reference documentation.

    Always returns CommandResult for consistent output handling.
    """
    output_dir = Path(getattr(args, "output", "docs/reference"))
    check = args.subcommand == "check" or bool(getattr(args, "check", False))

    outputs = {
        "CLI.md": _render_cli_reference(),
        "CONFIG.md": _render_config_reference(),
    }

    missing: list[str] = []
    changed: list[str] = []
    files_generated: list[str] = []
    files_modified: list[str] = []

    for name, content in outputs.items():
        path = output_dir / name
        if check:
            if not path.exists():
                missing.append(str(path))
                continue
            existing = path.read_text(encoding="utf-8")
            if existing != content:
                changed.append(str(path))
            continue

        existed = path.exists()
        _write(path, content)
        if existed:
            files_modified.append(str(path))
        else:
            files_generated.append(str(path))

    if check:
        if missing or changed:
            summary = "Docs are out of date"
            problems = []
            for p in missing:
                problems.append(
                    {
                        "severity": "error",
                        "message": f"Missing generated doc: {p}",
                        "code": "CIHUB-DOCS-MISSING",
                    }
                )
            for p in changed:
                problems.append(
                    {
                        "severity": "error",
                        "message": f"Docs differ from generated output: {p}",
                        "code": "CIHUB-DOCS-DRIFT",
                    }
                )
            suggestions = [
                {
                    "message": "Run: cihub docs generate",
                    "code": "CIHUB-DOCS-GENERATE",
                }
            ]
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=summary,
                problems=problems,
                suggestions=suggestions,
            )

        return CommandResult(exit_code=EXIT_SUCCESS, summary="Docs are up to date")

    # Generate mode - format output for display
    items = ["Docs generated"]
    for p in files_generated:
        items.append(f"Generated: {p}")
    for p in files_modified:
        items.append(f"Updated: {p}")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Docs generated",
        files_generated=files_generated,
        files_modified=files_modified,
        data={"items": items},
    )
