"""Complete setup wizard that orchestrates the full onboarding workflow.

This command provides an interactive wizard that guides users through:
1. Project creation (scaffold) OR detection of existing project
2. Configuration file generation (.ci-hub.yml)
3. Workflow file creation (.github/workflows/hub-ci.yml)
4. Configuration validation
5. Local CI run (optional)
6. GitHub setup - repo creation and push (optional)
7. GitHub Actions trigger (optional)

The goal is to allow users to set up a complete CI/CD pipeline without
memorizing individual commands.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from cihub.exit_codes import (
    EXIT_FAILURE,
    EXIT_INTERRUPTED,
    EXIT_SUCCESS,
    EXIT_USAGE,
)
from cihub.types import CommandResult
from cihub.services.templates import resolve_hub_repo_ref
from cihub.utils.github import set_repo_variables
from cihub.utils.git import get_git_remote, parse_repo_from_remote
from cihub.wizard import HAS_WIZARD, WizardCancelled

# Step definitions for the complete setup wizard
SETUP_STEPS = [
    "project_type",  # New or existing project?
    "scaffold",  # If new: create from template
    "detect",  # Detect language/build tool
    "configure",  # Interactive config (existing wizard)
    "write_files",  # Write .ci-hub.yml + workflow
    "validate",  # Run cihub validate
    "run_local_ci",  # Optional: run cihub ci locally
    "github_setup",  # Optional: create/configure GitHub repo
    "push",  # Optional: push to GitHub
    "trigger_ci",  # Optional: trigger GitHub Actions
]


def _check_cancelled(value, ctx: str):
    """Raise WizardCancelled if value is None (user cancelled)."""
    if value is None:
        raise WizardCancelled(f"{ctx} cancelled")
    return value


def _run_command(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    """Run a subprocess and return (exit_code, stdout, stderr).

    Note: Commands run by this function are trusted (git, gh CLI) - S603 suppressed.

    Args:
        cmd: Command and arguments
        cwd: Working directory
        timeout: Timeout in seconds (default: 120 for network operations per ADR-0045)

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(  # noqa: S603 - trusted commands only
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"


def cmd_setup(args: argparse.Namespace) -> CommandResult:
    """Complete setup wizard for onboarding repos to CI/CD Hub.

    This command orchestrates the full workflow:
    1. Scaffold or detect project
    2. Configure tools and thresholds interactively
    3. Generate config and workflow files
    4. Validate configuration
    5. Optionally run CI locally
    6. Optionally push to GitHub

    Usage:
        cihub setup                    # Start wizard in current directory
        cihub setup --repo /path/to/repo  # Start wizard for specific repo
        cihub setup --new              # Force new project scaffold
        cihub setup --skip-github      # Skip GitHub integration steps
    """
    if getattr(args, "json", False):
        message = (
            "--json is not supported for interactive setup; use non-interactive commands (init/new/config) instead"
        )
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message, "code": "CIHUB-SETUP-NO-JSON"}],
        )
    if not HAS_WIZARD:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Wizard dependencies not installed. Run: pip install cihub[wizard]",
            problems=[
                {
                    "severity": "error",
                    "message": "Install wizard deps: pip install cihub[wizard]",
                    "code": "CIHUB-SETUP-NO-WIZARD",
                }
            ],
        )

    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console = Console()
    repo_path = Path(getattr(args, "repo", ".")).resolve()
    skip_github = getattr(args, "skip_github", False)
    force_new = getattr(args, "new", False)

    # Track what we've done for the summary
    steps_completed: list[str] = []
    files_created: list[str] = []
    problems: list[dict] = []
    suggestions: list[dict] = []

    try:
        # Welcome banner
        console.print(
            Panel.fit(
                "[bold cyan]CIHub Complete Setup Wizard[/bold cyan]\n\n"
                "This wizard will guide you through setting up CI/CD for your project.\n"
                "You can press Ctrl+C at any time to cancel.",
                border_style="cyan",
            )
        )
        console.print()

        # Step 1: Project Type
        console.print("[bold]Step 1:[/bold] Project Type")
        if force_new or not (repo_path / "pyproject.toml").exists() and not (repo_path / "pom.xml").exists():
            # Ask if they want to create a new project
            project_choice = _check_cancelled(
                questionary.select(
                    "What would you like to do?",
                    choices=[
                        {"name": "Set up CI for an existing project", "value": "existing"},
                        {"name": "Create a new project from a template", "value": "new"},
                    ],
                ).ask(),
                "Project type selection",
            )
        else:
            console.print("  [green]✓[/green] Existing project detected")
            project_choice = "existing"

        # Step 2: Scaffold (if new project)
        if project_choice == "new":
            console.print("\n[bold]Step 2:[/bold] Create New Project")
            project_type = _check_cancelled(
                questionary.select(
                    "Select project type:",
                    choices=[
                        {"name": "Python (pyproject.toml)", "value": "python-pyproject"},
                        {"name": "Python (setup.py)", "value": "python-setup"},
                        {"name": "Java (Maven)", "value": "java-maven"},
                        {"name": "Java (Gradle)", "value": "java-gradle"},
                    ],
                ).ask(),
                "Project type",
            )

            project_name = _check_cancelled(
                questionary.text(
                    "Project name:",
                    default=repo_path.name,
                ).ask(),
                "Project name",
            )

            target_path = repo_path / project_name
            console.print(f"  Creating project at: {target_path}")

            # Run scaffold command
            from cihub.commands.scaffold import cmd_scaffold

            scaffold_args = argparse.Namespace(
                type=project_type,
                path=str(target_path),  # R-001: was 'dest', scaffold expects 'path'
                name=project_name,
                list=False,  # R-001: required flag
                github=False,  # R-001: required flag
                wizard=False,  # R-001: required flag
                force=False,  # R-001: required per code review (scaffold.py:169)
                json=False,
            )
            scaffold_result = cmd_scaffold(scaffold_args)
            if scaffold_result.exit_code != EXIT_SUCCESS:
                return CommandResult(
                    exit_code=scaffold_result.exit_code,
                    summary=f"Scaffold failed: {scaffold_result.summary}",
                    problems=scaffold_result.problems,
                )
            repo_path = target_path
            steps_completed.append("scaffold")
            files_created.extend(scaffold_result.files_generated or [])
            console.print("  [green]✓[/green] Project created")
        else:
            console.print("\n[bold]Step 2:[/bold] Scaffold [dim](skipped - existing project)[/dim]")

        # Step 3: Detect language
        console.print("\n[bold]Step 3:[/bold] Detecting Project Type")
        from cihub.commands.detect import cmd_detect

        detect_args = argparse.Namespace(
            repo=str(repo_path),
            language=None,
            json=False,
        )
        detect_result = cmd_detect(detect_args)
        if detect_result.exit_code != EXIT_SUCCESS:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Detection issue: {detect_result.summary}",
                }
            )

        detected_data = detect_result.data or {}
        language = detected_data.get("language", "unknown")
        console.print(f"  [green]✓[/green] Detected: {language}")
        steps_completed.append("detect")

        # Step 4: Configure (use wizard)
        hub_mode = getattr(args, "hub_mode", False)
        tier = getattr(args, "tier", None)  # None allows wizard to prompt

        if hub_mode:
            # Hub-mode: Use registry-integrated wizard
            console.print("\n[bold]Step 4:[/bold] Configure CI Tools (Hub Mode)")
            from cihub.config.paths import PathConfig
            from cihub.utils.paths import hub_root
            from cihub.wizard.core import WizardRunner

            paths = PathConfig(str(hub_root()))
            runner = WizardRunner(console, paths)

            # Run wizard with profile/tier selection
            wizard_result = runner.run_new_wizard(
                name=repo_path.name,
                tier=tier,
                skip_profile_selection=False,
            )
            config = wizard_result.config
            selected_tier = wizard_result.tier
            steps_completed.append("configure")

            # Step 5: Write to registry + config/repos
            console.print("\n[bold]Step 5:[/bold] Write Configuration (Registry Mode)")
            write_confirm = _check_cancelled(
                questionary.confirm(
                    "Write to registry and generate config files?",
                    default=True,
                ).ask(),
                "Write files confirmation",
            )

            if write_confirm:
                from cihub.services.configuration import create_repo_via_registry

                # Use wizard's repo_name (user may have edited it)
                effective_repo_name = wizard_result.repo_name or repo_path.name
                result = create_repo_via_registry(
                    effective_repo_name,
                    config,
                    tier=selected_tier,
                    sync=True,
                    dry_run=False,
                )
                if result.success:
                    console.print("  [green]✓[/green] Registry updated")
                    if result.synced:
                        console.print(f"  [green]✓[/green] Config synced: {result.config_file_path}")
                        files_created.append(result.config_file_path)
                    steps_completed.append("write_files")
                else:
                    console.print(f"  [red]✗[/red] Registry error: {result.errors}")
                    problems.extend([{"severity": "error", "message": e} for e in result.errors])
            else:
                console.print("  [yellow]⚠[/yellow] Skipped writing files")

        else:
            # Standard mode: Use init command
            console.print("\n[bold]Step 4:[/bold] Configure CI Tools")
            from cihub.commands.init import cmd_init

            # Run init with wizard to configure
            init_args = argparse.Namespace(
                repo=str(repo_path),
                wizard=True,
                apply=False,  # Don't write yet
                dry_run=True,
                language=language if language != "unknown" else None,
                owner=None,
                name=None,
                branch=None,
                subdir="",
                fix_pom=False,
                force=False,
                json=False,
            )
            init_result = cmd_init(init_args)
            if init_result.exit_code == EXIT_INTERRUPTED:
                raise WizardCancelled("Configuration cancelled")
            if init_result.exit_code != EXIT_SUCCESS:
                return init_result
            steps_completed.append("configure")

            # R-002: Capture wizard config from Step 4 result
            wizard_config = init_result.data.get("config", {}) if init_result.data else {}
            if not wizard_config:
                # Protect against silent config loss
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary="Wizard config was not captured; this is a bug",
                    problems=[
                        {
                            "severity": "error",
                            "message": "init did not return config in data",
                            "code": "CIHUB-SETUP-002",
                        }
                    ],
                )

            # Step 5: Write files
            console.print("\n[bold]Step 5:[/bold] Write Configuration Files")
            write_confirm = _check_cancelled(
                questionary.confirm(
                    "Write configuration files?",
                    default=True,
                ).ask(),
                "Write files confirmation",
            )

            if write_confirm:
                # Re-run init with --apply, passing wizard config via config_override
                init_args.apply = True
                init_args.dry_run = False
                init_args.wizard = False  # Skip wizard this time
                init_args.config_override = wizard_config  # R-002: Pass wizard selections
                init_result = cmd_init(init_args)
                if init_result.exit_code != EXIT_SUCCESS:
                    return init_result
                files_created.extend(init_result.files_generated or [])
                console.print("  [green]✓[/green] Files created:")
                for f in init_result.files_generated or []:
                    console.print(f"      - {f}")
                steps_completed.append("write_files")
            else:
                console.print("  [yellow]⚠[/yellow] Skipped writing files")

        # Step 6: Validate
        console.print("\n[bold]Step 6:[/bold] Validate Configuration")
        from cihub.commands.validate import cmd_validate

        validate_args = argparse.Namespace(
            repo=str(repo_path),
            json=False,
        )
        validate_result = cmd_validate(validate_args)
        if validate_result.exit_code == EXIT_SUCCESS:
            console.print("  [green]✓[/green] Configuration valid")
            steps_completed.append("validate")
        else:
            console.print("  [red]✗[/red] Validation failed")
            problems.extend(validate_result.problems or [])

        # Step 7: Run CI locally (optional)
        console.print("\n[bold]Step 7:[/bold] Run CI Locally")
        run_ci = _check_cancelled(
            questionary.confirm(
                "Would you like to run CI locally to verify everything works?",
                default=True,
            ).ask(),
            "Run CI confirmation",
        )

        if run_ci:
            console.print("  Running CI (this may take a few minutes)...")
            from cihub.commands.ci import cmd_ci

            ci_args = argparse.Namespace(
                repo=str(repo_path),
                workdir=".",
                output_dir=str(repo_path / ".cihub"),
                install_deps=True,
                verbose=False,
                json=False,
            )
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Running CI...", total=None)
                ci_result = cmd_ci(ci_args)

            if ci_result.exit_code == EXIT_SUCCESS:
                console.print("  [green]✓[/green] CI passed!")
                steps_completed.append("run_local_ci")
            else:
                console.print("  [red]✗[/red] CI failed")
                problems.extend(ci_result.problems or [])
                suggestions.append(
                    {
                        "message": "Run 'cihub triage' to investigate failures",
                    }
                )
        else:
            console.print("  [dim]Skipped[/dim]")

        # Step 8: GitHub Setup (optional)
        if not skip_github:
            console.print("\n[bold]Step 8:[/bold] GitHub Setup")
            github_choice = _check_cancelled(
                questionary.select(
                    "Would you like to set up GitHub?",
                    choices=[
                        {"name": "Create a new GitHub repository", "value": "create"},
                        {"name": "Push to an existing GitHub repository", "value": "existing"},
                        {"name": "Skip GitHub setup", "value": "skip"},
                    ],
                ).ask(),
                "GitHub setup",
            )

            if github_choice == "create":
                # Initialize git if needed
                git_dir = repo_path / ".git"
                if not git_dir.exists():
                    console.print("  Initializing git repository...")
                    exit_code, _, stderr = _run_command(["git", "init"], cwd=repo_path)
                    if exit_code != 0:
                        problems.append({"severity": "error", "message": f"git init failed: {stderr}"})
                    else:
                        console.print("  [green]✓[/green] Git initialized")

                # Create GitHub repo
                repo_name = _check_cancelled(
                    questionary.text(
                        "GitHub repository name:",
                        default=repo_path.name,
                    ).ask(),
                    "Repository name",
                )
                visibility = _check_cancelled(
                    questionary.select(
                        "Repository visibility:",
                        choices=[
                            {"name": "Public", "value": "public"},
                            {"name": "Private", "value": "private"},
                        ],
                    ).ask(),
                    "Visibility",
                )

                console.print(f"  Creating GitHub repository: {repo_name}...")
                exit_code, stdout, stderr = _run_command(
                    ["gh", "repo", "create", repo_name, f"--{visibility}", "--source", str(repo_path), "--push"],
                    cwd=repo_path,
                )
                if exit_code != 0:
                    problems.append({"severity": "error", "message": f"gh repo create failed: {stderr}"})
                    suggestions.append({"message": "Ensure 'gh' CLI is installed and authenticated"})
                else:
                    console.print(f"  [green]✓[/green] Repository created and pushed: {stdout.strip()}")
                    steps_completed.append("github_setup")
                    steps_completed.append("push")

            elif github_choice == "existing":
                # Just push to existing remote
                console.print("  Pushing to GitHub...")
                exit_code, _, stderr = _run_command(
                    ["git", "add", "."],
                    cwd=repo_path,
                )
                if exit_code == 0:
                    exit_code, _, stderr = _run_command(
                        ["git", "commit", "-m", "Add CI/CD Hub configuration"],
                        cwd=repo_path,
                    )
                if exit_code == 0 or "nothing to commit" in stderr:
                    exit_code, _, stderr = _run_command(
                        ["git", "push"],
                        cwd=repo_path,
                    )
                if exit_code != 0:
                    problems.append({"severity": "warning", "message": f"Push may have failed: {stderr}"})
                else:
                    console.print("  [green]✓[/green] Pushed to GitHub")
                    steps_completed.append("push")
            else:
                console.print("  [dim]Skipped[/dim]")

            if github_choice in {"create", "existing"} and getattr(args, "set_hub_vars", True):
                template_repo, template_ref = resolve_hub_repo_ref(language)
                hub_repo_value = getattr(args, "hub_repo", None) or os.environ.get("CIHUB_HUB_REPO") or template_repo
                hub_ref_value = getattr(args, "hub_ref", None) or os.environ.get("CIHUB_HUB_REF") or template_ref
                remote = get_git_remote(repo_path)
                target_repo = ""
                if remote:
                    git_owner, git_name = parse_repo_from_remote(remote)
                    if git_owner and git_name:
                        target_repo = f"{git_owner}/{git_name}"
                if not target_repo:
                    problems.append(
                        {
                            "severity": "warning",
                            "message": "Unable to resolve remote repo for setting HUB_REPO/HUB_REF",
                            "code": "CIHUB-HUB-VARS-NO-REMOTE",
                        }
                    )
                elif not hub_repo_value or not hub_ref_value:
                    problems.append(
                        {
                            "severity": "warning",
                            "message": "Unable to resolve hub repo/ref for GitHub variables",
                            "code": "CIHUB-HUB-VARS-NO-DEFAULT",
                        }
                    )
                else:
                    ok, messages, hub_problems = set_repo_variables(
                        target_repo,
                        {"HUB_REPO": hub_repo_value, "HUB_REF": hub_ref_value},
                    )
                    problems.extend(hub_problems)
                    if ok:
                        for message in messages:
                            console.print(f"  [green]✓[/green] {message}")
                        steps_completed.append("hub_vars")
                    else:
                        suggestions.append(
                            {
                                "message": "Set HUB_REPO/HUB_REF repo variables to enable hub-ci installs",
                            }
                        )
        else:
            console.print("\n[bold]Step 8:[/bold] GitHub Setup [dim](skipped via --skip-github)[/dim]")

        # Final summary
        console.print()
        console.print(
            Panel.fit(
                "[bold green]Setup Complete![/bold green]\n\n"
                f"Steps completed: {', '.join(steps_completed)}\n"
                f"Files created: {len(files_created)}\n\n"
                "[bold]Next steps:[/bold]\n"
                "  • Run [cyan]cihub ci --repo .[/cyan] to run CI locally\n"
                "  • Run [cyan]cihub triage[/cyan] to investigate any failures\n"
                "  • Push to GitHub to trigger GitHub Actions",
                border_style="green",
            )
        )

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Setup complete. Steps: {', '.join(steps_completed)}",
            files_generated=files_created,
            problems=problems,
            suggestions=suggestions,
            data={
                "steps_completed": steps_completed,
                "repo_path": str(repo_path),
                "language": language,
            },
        )

    except WizardCancelled as e:
        console.print(f"\n[yellow]Setup cancelled: {e}[/yellow]")
        return CommandResult(
            exit_code=EXIT_INTERRUPTED,
            summary="Setup cancelled by user",
            data={"steps_completed": steps_completed},
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled[/yellow]")
        return CommandResult(
            exit_code=EXIT_INTERRUPTED,
            summary="Setup cancelled by user",
            data={"steps_completed": steps_completed},
        )


def register_setup_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the setup command parser."""
    setup_parser = subparsers.add_parser(
        "setup",
        help="Complete setup wizard for onboarding repos",
        description="Interactive wizard that guides you through the complete CI/CD setup process.",
    )
    setup_parser.add_argument(
        "--repo",
        default=".",
        help="Path to repository (default: current directory)",
    )
    setup_parser.add_argument(
        "--new",
        action="store_true",
        help="Force creation of a new project (scaffold)",
    )
    setup_parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Skip GitHub repository setup steps",
    )
    setup_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )
    setup_parser.add_argument(
        "--hub-mode",
        action="store_true",
        help="Use registry-integrated hub-side mode (writes to registry + config/repos)",
    )
    setup_parser.add_argument(
        "--tier",
        choices=["strict", "standard", "relaxed"],
        default=None,
        help="Quality tier for thresholds (prompts if not specified)",
    )
