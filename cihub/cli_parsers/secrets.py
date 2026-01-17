"""Parser setup for secrets commands."""

from __future__ import annotations

import argparse
import os
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_secrets_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    setup_secrets = subparsers.add_parser(
        "setup-secrets",
        help="Set HUB_DISPATCH_TOKEN on hub and connected repos",
        epilog=see_also_epilog("setup-secrets"),
    )
    add_json_flag(setup_secrets)
    setup_secrets.add_argument(
        "--hub-repo",
        default=os.environ.get("CIHUB_HUB_REPO"),
        help="Hub repository (default: $CIHUB_HUB_REPO)",
    )
    setup_secrets.add_argument("--token", help="GitHub PAT (prompts if not provided)")
    setup_secrets.add_argument("--all", action="store_true", help="Also set on all connected repos")
    setup_secrets.add_argument(
        "--verify",
        action="store_true",
        help="Verify token with GitHub API before setting secrets",
    )
    setup_secrets.set_defaults(func=handlers.cmd_setup_secrets)

    setup_nvd = subparsers.add_parser("setup-nvd", help="Set NVD_API_KEY on Java repos for OWASP Dependency Check")
    add_json_flag(setup_nvd)
    setup_nvd.add_argument("--nvd-key", help="NVD API key (prompts if not provided)")
    setup_nvd.add_argument(
        "--verify",
        action="store_true",
        help="Verify NVD API key before setting secrets",
    )
    setup_nvd.set_defaults(func=handlers.cmd_setup_nvd)
