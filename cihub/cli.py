from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from typing import Mapping

from cihub.cli_parsers.builder import build_parser as _build_parser
from cihub.cli_parsers.types import CommandHandlers
from cihub.exit_codes import EXIT_FAILURE, EXIT_INTERNAL_ERROR, EXIT_SUCCESS
from cihub.services.configuration import load_effective_config  # noqa: F401 - re-export
from cihub.services.detection import detect_language, resolve_language  # noqa: F401 - re-export
from cihub.services.repo_config import (  # noqa: F401 - re-export
    get_connected_repos,
    get_repo_entries,
)
from cihub.services.templates import (  # noqa: F401 - re-export
    build_repo_config,
    render_caller_workflow,
    render_dispatch_workflow,
)
from cihub.types import CommandResult  # noqa: E402, F401 - re-export for compatibility
from cihub.utils import (  # noqa: E402, F401 - re-exports for compatibility
    GIT_REMOTE_RE,
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    dependency_matches,
    elem_text,
    fetch_remote_file,
    find_tag_spans,
    get_git_branch,
    get_git_remote,
    get_java_tool_flags,
    get_xml_namespace,
    gh_api_json,
    hub_root,
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
    parse_repo_from_remote,
    parse_xml_file,
    parse_xml_text,
    plugin_matches,
    resolve_executable,
    update_remote_file,
    validate_repo_path,
    validate_subdir,
)
from cihub.utils.env import env_bool
from cihub.utils.fs import write_text  # noqa: F401 - re-export
from cihub.utils.github_api import delete_remote_file  # noqa: F401 - re-export
from cihub.utils.net import safe_urlopen  # noqa: F401 - re-export

# apply_pom_fixes and apply_dependency_fixes are now in cihub.commands.pom
# They are not re-exported here to avoid circular imports


# CommandResult imported from cihub.types (re-exported for backward compatibility)
# hub_root imported from cihub.utils (re-exported for backward compatibility)


# get_java_tool_flags imported from cihub.utils.java_pom (re-exported for backward compatibility)
# get_xml_namespace imported from cihub.utils.java_pom (re-exported for backward compatibility)
# ns_tag imported from cihub.utils.java_pom (re-exported for backward compatibility)
# elem_text imported from cihub.utils.java_pom (re-exported for backward compatibility)
# resolve_executable imported from cihub.utils (re-exported for backward compatibility)
# validate_repo_path imported from cihub.utils (re-exported for backward compatibility)
# validate_subdir imported from cihub.utils (re-exported for backward compatibility)
# parse_xml_text imported from cihub.utils.java_pom (re-exported for backward compatibility)
# parse_xml_file imported from cihub.utils.java_pom (re-exported for backward compatibility)


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


# gh_api_json imported from cihub.utils (re-exported for backward compatibility)
# fetch_remote_file imported from cihub.utils (re-exported for backward compatibility)
# update_remote_file imported from cihub.utils (re-exported for backward compatibility)


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
    return _build_parser(handlers)


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
