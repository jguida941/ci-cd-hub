from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import textwrap
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from cihub import __version__
from cihub.cli_parsers.registry import register_parser_groups
from cihub.cli_parsers.types import CommandHandlers
from cihub.config.io import load_yaml_file
from cihub.config.merge import deep_merge
from cihub.config.normalize import normalize_config
from cihub.exit_codes import EXIT_FAILURE, EXIT_INTERNAL_ERROR, EXIT_SUCCESS
from cihub.types import CommandResult  # noqa: E402 - re-export for compatibility
from cihub.utils import (  # noqa: E402 - re-exports for compatibility
    GIT_REMOTE_RE,
    fetch_remote_file,
    get_git_branch,
    get_git_remote,
    gh_api_json,
    hub_root,
    parse_repo_from_remote,
    resolve_executable,
    update_remote_file,
    validate_repo_path,
    validate_subdir,
)
from cihub.utils.env import env_bool
from cihub.utils.java_pom import (  # noqa: E402 - re-exports for compatibility
    JAVA_TOOL_DEPENDENCIES,
    JAVA_TOOL_PLUGINS,
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    dependency_matches,
    elem_text,
    find_tag_spans,
    get_java_tool_flags,
    get_xml_namespace,
    indent_block,
    insert_dependencies_into_pom,
    insert_plugins_into_pom,
    line_indent,
    load_dependency_snippets,
    load_plugin_snippets,
    ns_tag,
    parse_pom_dependencies,
    parse_pom_modules,
    parse_pom_plugins,
    parse_xml_file,
    parse_xml_text,
    plugin_matches,
)

# apply_pom_fixes and apply_dependency_fixes are now in cihub.commands.pom
# They are not re-exported here to avoid circular imports


# CommandResult imported from cihub.types (re-exported for backward compatibility)
# hub_root imported from cihub.utils (re-exported for backward compatibility)


def write_text(path: Path, content: str, dry_run: bool, emit: bool = True) -> None:
    if dry_run:
        if emit:
            print(f"# Would write: {path}")
            print(content)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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


def load_effective_config(repo_path: Path) -> dict[str, Any]:
    defaults_path = hub_root() / "config" / "defaults.yaml"
    defaults = normalize_config(load_yaml_file(defaults_path))
    local_path = repo_path / ".ci-hub.yml"
    local_config = normalize_config(load_yaml_file(local_path))
    merged = deep_merge(defaults, local_config)
    merged = normalize_config(merged, apply_thresholds_profile=False)
    repo_info = merged.get("repo", {})
    if repo_info.get("language"):
        merged["language"] = repo_info["language"]
    return merged


# get_java_tool_flags imported from cihub.utils.java_pom (re-exported for backward compatibility)
# get_xml_namespace imported from cihub.utils.java_pom (re-exported for backward compatibility)
# ns_tag imported from cihub.utils.java_pom (re-exported for backward compatibility)
# elem_text imported from cihub.utils.java_pom (re-exported for backward compatibility)
# resolve_executable imported from cihub.utils (re-exported for backward compatibility)
# validate_repo_path imported from cihub.utils (re-exported for backward compatibility)
# validate_subdir imported from cihub.utils (re-exported for backward compatibility)
# parse_xml_text imported from cihub.utils.java_pom (re-exported for backward compatibility)
# parse_xml_file imported from cihub.utils.java_pom (re-exported for backward compatibility)


def safe_urlopen(req: urllib.request.Request, timeout: int):
    parsed = urlparse(req.full_url)
    if parsed.scheme != "https":
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310


def is_debug_enabled(env: Mapping[str, str] | None = None) -> bool:
    return env_bool("CIHUB_DEBUG", default=False, env=env)


# parse_pom_plugins imported from cihub.utils.java_pom (re-exported for backward compatibility)
# parse_pom_modules imported from cihub.utils.java_pom (re-exported for backward compatibility)
# parse_pom_dependencies imported from cihub.utils.java_pom (re-exported for backward compatibility)
# plugin_matches imported from cihub.utils.java_pom (re-exported for backward compatibility)
# dependency_matches imported from cihub.utils.java_pom (re-exported for backward compatibility)
# collect_java_pom_warnings imported from cihub.utils.java_pom (re-exported for backward compatibility)
# collect_java_dependency_warnings imported from cihub.utils.java_pom (re-exported for backward compatibility)
# load_plugin_snippets imported from cihub.utils.java_pom (re-exported for backward compatibility)
# load_dependency_snippets imported from cihub.utils.java_pom (re-exported for backward compatibility)
# line_indent imported from cihub.utils.java_pom (re-exported for backward compatibility)
# indent_block imported from cihub.utils.java_pom (re-exported for backward compatibility)
# insert_plugins_into_pom imported from cihub.utils.java_pom (re-exported for backward compatibility)
# find_tag_spans imported from cihub.utils.java_pom (re-exported for backward compatibility)
# insert_dependencies_into_pom imported from cihub.utils.java_pom (re-exported for backward compatibility)

# parse_repo_from_remote imported from cihub.utils (re-exported for backward compatibility)
# get_git_remote imported from cihub.utils (re-exported for backward compatibility)
# get_git_branch imported from cihub.utils (re-exported for backward compatibility)


def build_repo_config(
    language: str,
    owner: str,
    name: str,
    branch: str,
    subdir: str | None = None,
) -> dict[str, Any]:
    template_path = hub_root() / "templates" / "repo" / ".ci-hub.yml"
    base = load_yaml_file(template_path)

    repo_block = base.get("repo", {}) if isinstance(base.get("repo"), dict) else {}
    repo_block["owner"] = owner
    repo_block["name"] = name
    repo_block["language"] = language
    repo_block["default_branch"] = branch
    repo_block.setdefault("dispatch_workflow", "hub-ci.yml")
    if subdir:
        repo_block["subdir"] = subdir
    base["repo"] = repo_block

    base["language"] = language

    if language == "java":
        base.pop("python", None)
    elif language == "python":
        base.pop("java", None)

    base.setdefault("version", "1.0")
    return base


def render_caller_workflow(language: str) -> str:
    templates_dir = hub_root() / "templates" / "repo"
    if language == "java":
        template_path = templates_dir / "hub-java-ci.yml"
        replacement = "hub-java-ci.yml"
    else:
        template_path = templates_dir / "hub-python-ci.yml"
        replacement = "hub-python-ci.yml"

    content = template_path.read_text(encoding="utf-8")
    content = content.replace(replacement, "hub-ci.yml")
    header = "# Generated by cihub init - DO NOT EDIT\n"
    return header + content


def resolve_language(repo_path: Path, override: str | None) -> tuple[str, list[str]]:
    if override:
        return override, []
    detected, reasons = detect_language(repo_path)
    if not detected:
        reason_text = ", ".join(reasons) if reasons else "no language markers found"
        raise ValueError(f"Unable to detect language ({reason_text}); use --language.")
    return detected, reasons


def cmd_detect(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.detect import cmd_detect as handler

    return handler(args)


def cmd_preflight(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.preflight import cmd_preflight as handler

    return handler(args)


def cmd_scaffold(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.scaffold import cmd_scaffold as handler

    return handler(args)


def cmd_smoke(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.smoke import cmd_smoke as handler

    return handler(args)


def cmd_smoke_validate(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.smoke import cmd_smoke_validate as handler

    return handler(args)


def cmd_check(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.check import cmd_check as handler

    return handler(args)


def cmd_verify(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.verify import cmd_verify as handler

    return handler(args)


def cmd_ci(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.ci import cmd_ci as handler

    return handler(args)


def cmd_run(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.run import cmd_run as handler

    return handler(args)


def cmd_report(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.report import cmd_report as handler

    return handler(args)


def cmd_triage(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.triage import cmd_triage as handler

    return handler(args)


def cmd_docs(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.docs import cmd_docs as handler

    return handler(args)


def cmd_docs_links(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.docs import cmd_docs_links as handler

    return handler(args)


def cmd_adr(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.adr import cmd_adr as handler

    return handler(args)


def cmd_init(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.init import cmd_init as handler

    return handler(args)


def cmd_update(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.update import cmd_update as handler

    return handler(args)


def cmd_validate(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.validate import cmd_validate as handler

    return handler(args)


# apply_pom_fixes imported from cihub.utils.java_pom (re-exported for backward compatibility)
# apply_dependency_fixes imported from cihub.utils.java_pom (re-exported for backward compatibility)


def cmd_fix_pom(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.pom import cmd_fix_pom as handler

    return handler(args)


def cmd_fix_deps(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.pom import cmd_fix_deps as handler

    return handler(args)


def get_connected_repos(
    only_dispatch_enabled: bool = True,
    language_filter: str | None = None,
) -> list[str]:
    """Get unique repos from hub config/repos/*.yaml.

    Args:
        only_dispatch_enabled: If True, skip repos with dispatch_enabled=False
        language_filter: If set, only return repos with this language (java/python)
    """
    repos_dir = hub_root() / "config" / "repos"
    seen: set[str] = set()
    repos: list[str] = []
    for cfg_file in repos_dir.glob("*.yaml"):
        if cfg_file.name.endswith(".disabled"):
            continue
        try:
            data = load_yaml_file(cfg_file)
            repo = data.get("repo", {})
            if only_dispatch_enabled and repo.get("dispatch_enabled", True) is False:
                continue
            if language_filter:
                repo_lang = repo.get("language", "")
                if repo_lang != language_filter:
                    continue
            owner = repo.get("owner", "")
            name = repo.get("name", "")
            if owner and name:
                full = f"{owner}/{name}"
                if full not in seen:
                    seen.add(full)
                    repos.append(full)
        except Exception as exc:
            print(f"Warning: failed to read {cfg_file}: {exc}", file=sys.stderr)
    return repos


def get_repo_entries(
    only_dispatch_enabled: bool = True,
) -> list[dict[str, str]]:
    """Return repo metadata from config/repos/*.yaml."""
    repos_dir = hub_root() / "config" / "repos"
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for cfg_file in repos_dir.glob("*.yaml"):
        if cfg_file.name.endswith(".disabled"):
            continue
        try:
            data = load_yaml_file(cfg_file)
            repo = data.get("repo", {})
            if only_dispatch_enabled and repo.get("dispatch_enabled", True) is False:
                continue
            owner = repo.get("owner", "")
            name = repo.get("name", "")
            if not owner or not name:
                continue
            full = f"{owner}/{name}"
            dispatch_workflow = repo.get("dispatch_workflow") or "hub-ci.yml"
            # Deduplicate by (repo, dispatch_workflow) to allow syncing
            # multiple workflow files for repos with both Java and Python configs
            key = f"{full}:{dispatch_workflow}"
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "full": full,
                    "language": repo.get("language", ""),
                    "dispatch_workflow": dispatch_workflow,
                    "default_branch": repo.get("default_branch", "main"),
                }
            )
        except Exception as exc:
            print(f"Warning: failed to read {cfg_file}: {exc}", file=sys.stderr)
            continue
    return entries


def render_dispatch_workflow(language: str, dispatch_workflow: str) -> str:
    templates_dir = hub_root() / "templates" / "repo"
    if dispatch_workflow == "hub-ci.yml":
        if not language:
            raise ValueError("language is required for hub-ci.yml rendering")
        return render_caller_workflow(language)
    if dispatch_workflow == "hub-java-ci.yml":
        return (templates_dir / "hub-java-ci.yml").read_text(encoding="utf-8")
    if dispatch_workflow == "hub-python-ci.yml":
        return (templates_dir / "hub-python-ci.yml").read_text(encoding="utf-8")
    raise ValueError(f"Unsupported dispatch_workflow: {dispatch_workflow}")


# gh_api_json imported from cihub.utils (re-exported for backward compatibility)
# fetch_remote_file imported from cihub.utils (re-exported for backward compatibility)
# update_remote_file imported from cihub.utils (re-exported for backward compatibility)


def delete_remote_file(
    repo: str,
    path: str,
    branch: str,
    sha: str,
    message: str,
) -> None:
    """Delete a file from a GitHub repo via the GitHub API."""
    payload: dict[str, Any] = {
        "message": message,
        "sha": sha,
        "branch": branch,
    }
    gh_api_json(f"/repos/{repo}/contents/{path}", method="DELETE", payload=payload)


def cmd_setup_secrets(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.secrets import cmd_setup_secrets as handler

    return handler(args)


def cmd_setup_nvd(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.secrets import cmd_setup_nvd as handler

    return handler(args)


def cmd_sync_templates(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.templates import cmd_sync_templates as handler

    return handler(args)


def cmd_new(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.new import cmd_new as handler

    return handler(args)


def cmd_config(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.config_cmd import cmd_config as handler

    return handler(args)


def cmd_config_outputs(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.config_outputs import cmd_config_outputs as handler

    return handler(args)


def cmd_hub_ci(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.hub_ci import cmd_hub_ci as handler

    return handler(args)


def cmd_discover(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.discover import cmd_discover as handler

    return handler(args)


def cmd_dispatch(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.dispatch import cmd_dispatch as handler

    return handler(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cihub", description="CI/CD Hub CLI")
    parser.add_argument("--version", action="version", version=f"cihub {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_json_flag(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--json",
            action="store_true",
            help="Output machine-readable JSON",
        )

    handlers = CommandHandlers(
        cmd_detect=cmd_detect,
        cmd_preflight=cmd_preflight,
        cmd_scaffold=cmd_scaffold,
        cmd_smoke=cmd_smoke,
        cmd_smoke_validate=cmd_smoke_validate,
        cmd_check=cmd_check,
        cmd_verify=cmd_verify,
        cmd_ci=cmd_ci,
        cmd_run=cmd_run,
        cmd_report=cmd_report,
        cmd_triage=cmd_triage,
        cmd_docs=cmd_docs,
        cmd_docs_links=cmd_docs_links,
        cmd_adr=cmd_adr,
        cmd_config_outputs=cmd_config_outputs,
        cmd_discover=cmd_discover,
        cmd_dispatch=cmd_dispatch,
        cmd_hub_ci=cmd_hub_ci,
        cmd_new=cmd_new,
        cmd_init=cmd_init,
        cmd_update=cmd_update,
        cmd_validate=cmd_validate,
        cmd_setup_secrets=cmd_setup_secrets,
        cmd_setup_nvd=cmd_setup_nvd,
        cmd_fix_pom=cmd_fix_pom,
        cmd_fix_deps=cmd_fix_deps,
        cmd_sync_templates=cmd_sync_templates,
        cmd_config=cmd_config,
    )

    register_parser_groups(subparsers, add_json_flag, handlers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    start = time.perf_counter()
    command = args.command
    subcommand = getattr(args, "subcommand", None)
    if subcommand:
        command = f"{command} {subcommand}"
    debug = is_debug_enabled()
    json_mode = getattr(args, "json", False)

    def emit_debug(message: str) -> None:
        if debug:
            print(f"[debug] {message}", file=sys.stderr)

    emit_debug(f"command={command} json={json_mode}")

    try:
        result = args.func(args)
    except (FileNotFoundError, ValueError, PermissionError, OSError) as exc:
        # Expected user errors - show friendly message, return failure
        if debug and not json_mode:
            traceback.print_exc()
        if json_mode:
            problems = [
                {
                    "severity": "error",
                    "message": str(exc),
                    "code": "CIHUB-USER-ERROR",
                }
            ]
            payload = CommandResult(
                exit_code=EXIT_FAILURE,
                summary=str(exc),
                problems=problems,
            ).to_payload(
                command,
                "failure",
                int((time.perf_counter() - start) * 1000),
            )
            print(json.dumps(payload, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    except Exception as exc:  # noqa: BLE001 - surface in JSON mode
        if json_mode:
            problems = [
                {
                    "severity": "error",
                    "message": str(exc),
                    "code": "CIHUB-UNHANDLED",
                }
            ]
            payload = CommandResult(
                exit_code=EXIT_INTERNAL_ERROR,
                summary=str(exc),
                problems=problems,
            ).to_payload(
                command,
                "error",
                int((time.perf_counter() - start) * 1000),
            )
            print(json.dumps(payload, indent=2))
            return EXIT_INTERNAL_ERROR
        raise

    if isinstance(result, CommandResult):
        exit_code = result.exit_code
        command_result = result
    else:
        exit_code = int(result)
        command_result = CommandResult(exit_code=exit_code)

    if not command_result.summary:
        command_result.summary = "OK" if exit_code == EXIT_SUCCESS else "Command failed"

    if json_mode:
        status = "success" if exit_code == EXIT_SUCCESS else "failure"
        payload = command_result.to_payload(
            command,
            status,
            int((time.perf_counter() - start) * 1000),
        )
        print(json.dumps(payload, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
