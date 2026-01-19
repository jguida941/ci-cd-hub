"""Init command handlers."""

from __future__ import annotations

import argparse
import io
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import yaml

from cihub.ci_config import load_ci_config
from cihub.commands.pom import apply_dependency_fixes, apply_pom_fixes
from cihub.config.inputs import ConfigInputError, load_config_override
from cihub.config.io import load_yaml_file, save_yaml_file
from cihub.config.merge import deep_merge
from cihub.config.paths import PathConfig
from cihub.exit_codes import (
    EXIT_FAILURE,
    EXIT_INTERRUPTED,
    EXIT_SUCCESS,
    EXIT_USAGE,
)
from cihub.services.detection import resolve_language
from cihub.services.templates import build_repo_config, render_caller_workflow, resolve_hub_repo_ref
from cihub.types import CommandResult
from cihub.utils import (
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
)
from cihub.utils.github import set_repo_variables
from cihub.utils.fs import write_text
from cihub.utils.paths import hub_root, validate_subdir
from cihub.wizard import HAS_WIZARD, WizardCancelled


def cmd_init(args: argparse.Namespace) -> CommandResult:
    """Initialize CI-Hub config in a repository.

    Always returns CommandResult for consistent output handling.
    """
    repo_path = Path(args.repo).resolve()
    apply = getattr(args, "apply", False)
    force = getattr(args, "force", False)
    dry_run = args.dry_run or not apply

    if getattr(args, "json", False) and args.wizard:
        message = "--wizard is not supported with --json"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message}],
        )

    try:
        cli_override = load_config_override(
            getattr(args, "config_json", None),
            getattr(args, "config_file", None),
        )
    except ConfigInputError as exc:
        message = str(exc)
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-INIT-CONFIG-INPUT"}],
        )

    if args.wizard and cli_override:
        message = "--config-json/--config-file is not supported with --wizard"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-INIT-CONFIG-WIZARD"}],
        )

    if force and not apply:
        message = "--force requires --apply"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-INIT-FORCE"}],
        )

    config_path = repo_path / ".ci-hub.yml"
    workflow_path = repo_path / ".github" / "workflows" / "hub-ci.yml"
    existing_config = config_path.exists()
    existing_workflow = workflow_path.exists()
    bootstrap = not existing_config or not existing_workflow
    repo_side_execution = False
    if existing_config:
        existing = load_yaml_file(config_path)
        repo_value = existing.get("repo")
        repo_block = repo_value if isinstance(repo_value, dict) else {}
        repo_side_execution = bool(repo_block.get("repo_side_execution", False))

    if apply and not repo_side_execution and not bootstrap and not force:
        message = "repo_side_execution is false; re-run with --force or enable repo.repo_side_execution in .ci-hub.yml"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[
                {
                    "severity": "error",
                    "message": message,
                    "code": "CIHUB-INIT-001",
                    "file": str(config_path),
                }
            ],
        )

    # Validate subdir to prevent path traversal
    subdir = validate_subdir(args.subdir or "")
    effective_repo_path = repo_path / subdir if subdir else repo_path

    language, _ = resolve_language(effective_repo_path, args.language)

    owner = args.owner or ""
    name = args.name or ""
    if not owner or not name:
        remote = get_git_remote(repo_path)
        if remote:
            git_owner, git_name = parse_repo_from_remote(remote)
            owner = owner or (git_owner or "")
            name = name or (git_name or "")

    if not name:
        name = repo_path.name
    owner_warnings: list[str] = []
    if not owner:
        owner = "unknown"
        owner_warnings.append("Warning: could not detect repo owner; set repo.owner manually.")

    branch = args.branch or get_git_branch(repo_path) or "main"

    install_from = getattr(args, "install_from", "pypi")
    detected_config = build_repo_config(
        language,
        owner,
        name,
        branch,
        subdir=subdir,
        repo_path=effective_repo_path,
        install_from=install_from,
    )

    # R-002: Track whether wizard was used (for including config in data)
    wizard_used = False

    if args.wizard:
        if not HAS_WIZARD:
            message = "Install wizard deps: pip install cihub[wizard]"
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message, "code": "CIHUB-INIT-NO-WIZARD"}],
            )
        from rich.console import Console

        from cihub.wizard.core import WizardRunner

        runner = WizardRunner(Console(), PathConfig(str(hub_root())))
        try:
            wizard_result = runner.run_init_wizard(detected_config)
            config = wizard_result.config
        except WizardCancelled:
            return CommandResult(
                exit_code=EXIT_INTERRUPTED,
                summary="Cancelled",
            )
        language = config.get("language", language)
        wizard_used = True
    else:
        # R-002: Handle config_override (internal, no CLI surface change)
        config_override = getattr(args, "config_override", None)
        if cli_override:
            if isinstance(config_override, dict):
                config_override = deep_merge(config_override, cli_override)
            else:
                config_override = cli_override
        if config_override and isinstance(config_override, dict):
            # Merge override into detected config
            config = deep_merge(detected_config, config_override)
            # Set language from override BEFORE render_caller_workflow
            language = config.get("language", language)
        else:
            config = detected_config
    config_path = repo_path / ".ci-hub.yml"

    repo_config = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    # Keep repo metadata aligned with the final language.
    if language:
        repo_config["language"] = language
    config["repo"] = repo_config
    if language == "java":
        config.pop("python", None)
    elif language == "python":
        config.pop("java", None)
    final_owner = repo_config.get("owner", owner)
    final_name = repo_config.get("name", name)
    final_branch = repo_config.get("default_branch", repo_config.get("branch", branch))
    final_subdir = repo_config.get("subdir", subdir)
    root_path = repo_path / final_subdir if final_subdir else repo_path

    # Clear owner warning if wizard/config_override provided a valid owner
    if final_owner != "unknown":
        owner_warnings = []

    payload = yaml.safe_dump(config, sort_keys=False, default_flow_style=False, allow_unicode=True)

    if dry_run:
        # Don't write files, just report what would happen
        pass
    else:
        save_yaml_file(config_path, config, dry_run=False)

    workflow_content = render_caller_workflow(language)
    write_text(workflow_path, workflow_content, dry_run, emit=False)

    hub_vars_set = False
    hub_vars_messages: list[str] = []
    hub_vars_problems: list[dict[str, str]] = []
    hub_repo_value: str | None = None
    hub_ref_value: str | None = None
    if apply and getattr(args, "set_hub_vars", False):
        template_repo, template_ref = resolve_hub_repo_ref(language)
        hub_repo_value = getattr(args, "hub_repo", None) or os.environ.get("CIHUB_HUB_REPO") or template_repo
        hub_ref_value = getattr(args, "hub_ref", None) or os.environ.get("CIHUB_HUB_REF") or template_ref
        if not hub_repo_value or not hub_ref_value:
            hub_vars_problems.append(
                {
                    "severity": "warning",
                    "message": "Unable to resolve hub repo/ref for GitHub variables",
                    "code": "CIHUB-HUB-VARS-NO-DEFAULT",
                }
            )
        else:
            if final_owner and final_name and final_owner != "unknown":
                target_repo = f"{final_owner}/{final_name}"
            else:
                target_repo = ""
            hub_vars_set, hub_vars_messages, hub_vars_problems = set_repo_variables(
                target_repo,
                {"HUB_REPO": hub_repo_value, "HUB_REF": hub_ref_value},
            )

    pom_warning_problems: list[dict[str, str]] = []
    suggestions: list[dict[str, str]] = []
    pom_fix_data: dict = {}
    if apply and getattr(args, "set_hub_vars", False) and hub_vars_problems:
        suggestions.append(
            {
                "message": "Set HUB_REPO/HUB_REF repo variables to enable hub-ci installs",
            }
        )

    if language == "java" and not dry_run:
        effective = load_ci_config(repo_path)
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        pom_warning_list = pom_warnings + dep_warnings
        if pom_warning_list:
            pom_warning_problems = [
                {
                    "severity": "warning",
                    "message": warning,
                    "code": "CIHUB-POM-001",
                    "file": str(root_path / "pom.xml"),
                }
                for warning in pom_warning_list
            ]
            if args.fix_pom:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    pom_result = apply_pom_fixes(repo_path, effective, apply=True)
                    dep_result = apply_dependency_fixes(repo_path, effective, apply=True)
                    status = max(pom_result.exit_code, dep_result.exit_code)
                pom_path = root_path / "pom.xml"
                files_modified = [str(pom_path)] if pom_path.exists() else []
                summary = (
                    "Initialization complete; POM fixes applied"
                    if status == 0
                    else "Initialization complete; POM fixes failed"
                )
                problems = [
                    {
                        "severity": "warning",
                        "message": warning,
                        "code": "CIHUB-INIT-WARN",
                        "file": str(config_path),
                    }
                    for warning in owner_warnings
                ]
                problems.extend(pom_warning_problems)
                if status != 0:
                    problems.append(
                        {
                            "severity": "error",
                            "message": "POM fixes failed",
                            "code": "CIHUB-POM-APPLY-001",
                            "file": str(pom_path),
                        }
                    )
                return CommandResult(
                    exit_code=status,
                    summary=summary,
                    problems=problems,
                    files_generated=[str(config_path), str(workflow_path)],
                    files_modified=files_modified,
                    data={
                        "language": language,
                        "owner": final_owner,
                        "name": final_name,
                        "branch": final_branch,
                        "subdir": final_subdir,
                        "dry_run": dry_run,
                        "bootstrap": bootstrap,
                        "pom_fix_applied": True,
                        "pom_fix_status": status,
                    },
                )
            else:
                suggestions.append({"message": "Run: cihub fix-pom --repo . --apply"})

    # Build result
    summary = "Dry run complete" if dry_run else "Initialization complete"
    problems = [
        {
            "severity": "warning",
            "message": warning,
            "code": "CIHUB-INIT-WARN",
            "file": str(config_path),
        }
        for warning in owner_warnings
    ]
    problems.extend(pom_warning_problems)
    problems.extend(hub_vars_problems)

    data = {
        "language": language,
        "owner": final_owner,
        "name": final_name,
        "branch": final_branch,
        "subdir": final_subdir,
        "dry_run": dry_run,
        "bootstrap": bootstrap,
    }
    if apply and getattr(args, "set_hub_vars", False):
        data.update(
            {
                "hub_repo": hub_repo_value,
                "hub_ref": hub_ref_value,
                "hub_vars_set": hub_vars_set,
                "hub_vars_messages": hub_vars_messages,
            }
        )
    if dry_run:
        data["raw_output"] = payload
    # R-002: Include config in data when wizard was used (so setup can capture it)
    # Do NOT add to non-wizard outputs to avoid snapshot churn
    if wizard_used:
        data["config"] = config
    data.update(pom_fix_data)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        problems=problems,
        suggestions=suggestions,
        files_generated=[str(config_path), str(workflow_path)],
        data=data,
    )
