from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from typing import Any, Mapping

from cihub.cli_parsers.builder import build_parser as _build_parser
from cihub.cli_parsers.types import CommandHandlers
from cihub.config.io import ConfigParseError
from cihub.exit_codes import EXIT_FAILURE, EXIT_INTERNAL_ERROR, EXIT_SUCCESS
from cihub.output import get_renderer
from cihub.output.events import set_event_sink
from cihub.types import CommandResult
from cihub.utils.env import env_bool


def is_debug_enabled(env: Mapping[str, str] | None = None) -> bool:
    return env_bool("CIHUB_DEBUG", default=False, env=env)


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


def cmd_ai_loop(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.ai_loop import cmd_ai_loop as handler

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


def cmd_commands(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.commands_cmd import cmd_commands as handler

    return handler(args)


def cmd_docs(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.docs import cmd_docs as handler

    return handler(args)


def cmd_docs_links(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.docs import cmd_docs_links as handler

    return handler(args)


def cmd_docs_stale(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.docs_stale import cmd_docs_stale as handler

    return handler(args)


def cmd_docs_audit(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.docs_audit import cmd_docs_audit as handler

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


def cmd_fix_pom(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.pom import cmd_fix_pom as handler

    return handler(args)


def cmd_fix_deps(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.pom import cmd_fix_deps as handler

    return handler(args)


def cmd_fix_gradle(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.gradle import cmd_fix_gradle as handler

    return handler(args)


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


def cmd_fix(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.fix import cmd_fix as handler

    return handler(args)


def cmd_registry(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.registry_cmd import cmd_registry as handler

    return handler(args)


def cmd_profile(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.profile_cmd import cmd_profile as handler

    return handler(args)


def cmd_tool(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.tool_cmd import cmd_tool as handler

    return handler(args)


def cmd_threshold(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.threshold_cmd import cmd_threshold as handler

    return handler(args)


def cmd_repo(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.repo_cmd import cmd_repo as handler

    return handler(args)


def cmd_hub(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.hub_config import cmd_hub as handler

    return handler(args)


def cmd_setup(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.setup import cmd_setup as handler

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
        cmd_ai_loop=cmd_ai_loop,
        cmd_run=cmd_run,
        cmd_report=cmd_report,
        cmd_triage=cmd_triage,
        cmd_commands=cmd_commands,
        cmd_docs=cmd_docs,
        cmd_docs_links=cmd_docs_links,
        cmd_docs_stale=cmd_docs_stale,
        cmd_docs_audit=cmd_docs_audit,
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
        cmd_fix_gradle=cmd_fix_gradle,
        cmd_sync_templates=cmd_sync_templates,
        cmd_config=cmd_config,
        cmd_fix=cmd_fix,
        cmd_registry=cmd_registry,
        cmd_profile=cmd_profile,
        cmd_tool=cmd_tool,
        cmd_threshold=cmd_threshold,
        cmd_repo=cmd_repo,
        cmd_hub=cmd_hub,
        cmd_setup=cmd_setup,
    )
    return _build_parser(handlers)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args._cli_invocation = True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        args._cli_test_mode = True
    start = time.perf_counter()
    command = args.command
    subcommand = getattr(args, "subcommand", None)
    if subcommand:
        command = f"{command} {subcommand}"
    debug = is_debug_enabled()
    json_mode = getattr(args, "json", False)
    ai_requested = getattr(args, "ai", False)
    ai_output_mode = False
    if ai_requested:
        from cihub.output.ai_formatters import has_ai_formatter

        ai_output_mode = has_ai_formatter(command)

    def emit_debug(message: str) -> None:
        if debug:
            print(f"[debug] {message}", file=sys.stderr)

    emit_debug(f"command={command} json={json_mode} ai={ai_requested} ai_output={ai_output_mode}")

    event_sink_set = False
    if not json_mode and not ai_output_mode:

        def _cli_event_sink(event: str, payload: dict[str, Any]) -> None:
            text = payload.get("text")
            if not text:
                return
            stream = payload.get("stream", "stdout")
            if stream == "stderr":
                print(text, file=sys.stderr)
            else:
                print(text)

        set_event_sink(_cli_event_sink)
        event_sink_set = True

    try:
        try:
            result = args.func(args)
        except (FileNotFoundError, ValueError, PermissionError, OSError, ConfigParseError) as exc:
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

        if env_bool("CIHUB_DEV_MODE", default=False) and command_result.exit_code != 0 and not ai_requested:
            from cihub.ai import enhance_result, is_ai_available

            if is_ai_available():
                if not json_mode:
                    print("[DEV MODE] Invoking AI for debugging...", file=sys.stderr)
                command_result = enhance_result(command_result, mode="analyze")

        if not command_result.summary:
            command_result.summary = "OK" if exit_code == EXIT_SUCCESS else "Command failed"

        # Use renderer pattern for all output
        duration_ms = int((time.perf_counter() - start) * 1000)
        renderer = get_renderer(json_mode=json_mode, ai_mode=ai_output_mode)
        output = renderer.render(command_result, command, duration_ms)
        # Always print for JSON/AI modes, or if there's meaningful content beyond default summary
        if json_mode or ai_output_mode or (output and output not in ("OK", "Command failed")):
            # CLI best practice: error output to stderr, success output to stdout
            # AI mode always goes to stdout for easy piping
            if exit_code != EXIT_SUCCESS and not json_mode and not ai_output_mode:
                print(output, file=sys.stderr)
            else:
                print(output)

        return exit_code
    finally:
        if event_sink_set:
            set_event_sink(None)


if __name__ == "__main__":
    raise SystemExit(main())
