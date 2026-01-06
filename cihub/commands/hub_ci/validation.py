"""Validation commands for syntax, repos, configs, and quarantine checks."""

from __future__ import annotations

import argparse
import os
import py_compile
import re
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.discovery import _THRESHOLD_KEYS, _TOOL_KEYS
from cihub.services.types import RepoEntry
from cihub.types import CommandResult
from cihub.utils.github_context import OutputContext
from cihub.utils.paths import hub_root

from . import _bool_str


def cmd_syntax_check(args: argparse.Namespace) -> CommandResult:
    base = Path(args.root).resolve()
    error_list: list[dict[str, str]] = []
    for path in args.paths:
        target = (base / path).resolve()
        if target.is_file():
            files = [target]
        elif target.is_dir():
            files = list(target.rglob("*.py"))
        else:
            continue

        for file_path in files:
            try:
                py_compile.compile(str(file_path), doraise=True)
            except py_compile.PyCompileError as exc:
                error_list.append({
                    "severity": "error",
                    "message": f"{file_path}: {exc.msg}",
                    "file": str(file_path),
                })

    if error_list:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Syntax errors found: {len(error_list)}",
            problems=[{"severity": "error", "message": e["message"]} for e in error_list],
            data={"errors": error_list},
        )
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="✓ Python syntax valid",
    )


def cmd_repo_check(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    present = (repo_path / ".git").exists()
    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"present": _bool_str(present)})

    problems: list[dict[str, str]] = []
    if not present and args.owner and args.name:
        problems.append({
            "severity": "warning",
            "message": f"Repo checkout failed for {args.owner}/{args.name}",
        })

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Repository present: {present}",
        problems=problems,
        data={"present": present, "path": str(repo_path)},
    )


def cmd_source_check(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    language = args.language.lower()
    patterns: tuple[str, ...]
    if language == "java":
        patterns = ("*.java", "*.kt")
    elif language == "python":
        patterns = ("*.py",)
    else:
        patterns = ()

    has_source = False
    for pattern in patterns:
        if any(repo_path.rglob(pattern)):
            has_source = True
            break

    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"has_source": _bool_str(has_source)})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Source code present: {has_source}",
        data={"has_source": has_source, "language": language, "patterns": patterns},
    )


def cmd_docker_compose_check(args: argparse.Namespace) -> CommandResult:
    repo_path = Path(args.path).resolve()
    has_docker = (repo_path / "docker-compose.yml").exists() or (repo_path / "docker-compose.yaml").exists()
    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"has_docker": _bool_str(has_docker)})

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Docker compose present: {has_docker}",
        data={"has_docker": has_docker, "path": str(repo_path)},
    )


def cmd_validate_configs(args: argparse.Namespace) -> CommandResult:
    """Validate all repo configs in config/repos/.

    Uses cihub.config.loader (no scripts dependency).
    """
    from cihub.config.loader import generate_workflow_inputs, load_config

    root = hub_root()
    configs_dir = Path(args.configs_dir) if args.configs_dir else root / "config" / "repos"

    repos: list[str]
    if args.repo:
        repos = [args.repo]
        config_path = configs_dir / f"{args.repo}.yaml"
        if not config_path.exists():
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Config not found: {config_path}",
                problems=[{"severity": "error", "message": f"Config not found: {config_path}"}],
            )
    else:
        repos = [path.stem for path in sorted(configs_dir.glob("*.yaml"))]

    validated: list[str] = []
    problems: list[dict[str, str]] = []

    for repo in repos:
        try:
            config = load_config(repo_name=repo, hub_root=root)
            generate_workflow_inputs(config)
            validated.append(repo)
        except Exception as e:  # noqa: BLE001 - catch all config errors
            problems.append({
                "severity": "error",
                "message": f"Config validation failed for {repo}: {e}",
            })

    if problems:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Config validation failed ({len(problems)} errors, {len(validated)} valid)",
            problems=problems,
            data={"validated_repos": validated, "failed_count": len(problems)},
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"✓ All configs valid ({len(validated)} repos)",
        data={"validated_repos": validated, "configs_dir": str(configs_dir)},
    )


def cmd_validate_profiles(args: argparse.Namespace) -> CommandResult:
    root = hub_root()
    profiles_dir = Path(args.profiles_dir) if args.profiles_dir else root / "templates" / "profiles"
    try:
        import yaml
    except ImportError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Missing PyYAML: {exc}",
            problems=[{"severity": "error", "message": f"Missing PyYAML: {exc}"}],
        )

    validated: list[str] = []
    for path in sorted(profiles_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Invalid profile: {path}",
                problems=[{"severity": "error", "message": f"{path} not a dict"}],
            )
        validated.append(path.name)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"✓ All profiles valid ({len(validated)} profiles)",
        data={"validated_profiles": validated, "profiles_dir": str(profiles_dir)},
    )


def _expected_matrix_keys() -> set[str]:
    tools = {key: True for key in _TOOL_KEYS}
    thresholds: dict[str, int | float | None] = {key: 1 for key in _THRESHOLD_KEYS}
    entry = RepoEntry(
        config_basename="example",
        name="repo",
        owner="owner",
        language="python",
        branch="main",
        subdir="src",
        subdir_safe="src",
        run_group="full",
        dispatch_enabled=True,
        dispatch_workflow="hub-ci.yml",
        use_central_runner=True,
        tools=tools,
        thresholds=thresholds,
        java_version="21",
        python_version="3.12",
        build_tool="maven",
        retention_days=30,
        write_github_summary=True,
    )
    return set(entry.to_matrix_entry().keys())


def cmd_verify_matrix_keys(args: argparse.Namespace) -> CommandResult:
    """Verify that all matrix.<key> references in hub-run-all.yml are emitted by cihub discover."""
    hub = hub_root()
    wf_path = hub / ".github" / "workflows" / "hub-run-all.yml"

    if not wf_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Workflow not found: {wf_path}",
            problems=[{"severity": "error", "message": f"{wf_path} not found"}],
        )

    text = wf_path.read_text(encoding="utf-8")

    # Pattern for matrix.key references
    matrix_ref_re = re.compile(r"\bmatrix\.([A-Za-z_][A-Za-z0-9_]*)\b")
    referenced = set(matrix_ref_re.findall(text))
    emitted = _expected_matrix_keys()

    missing = sorted(referenced - emitted)
    unused = sorted(emitted - referenced)

    if missing:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Missing matrix keys: {len(missing)}",
            problems=[{"severity": "error", "message": f"Matrix key not emitted: {key}"} for key in missing],
            data={"missing_keys": missing, "unused_keys": unused},
        )

    warnings: list[dict[str, str]] = []
    if unused:
        warnings = [{"severity": "warning", "message": f"Unused matrix key: {key}"} for key in unused]

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="OK: all referenced matrix keys are emitted by the builder",
        problems=warnings,
        data={"referenced_keys": sorted(referenced), "emitted_keys": sorted(emitted), "unused_keys": unused},
    )


def cmd_enforce_command_result(args: argparse.Namespace) -> CommandResult:
    """Enforce CommandResult pattern - commands must not use print() directly.

    ADR-0042: All commands should return CommandResult instead of printing directly.
    This check enforces a maximum allowance for print() calls in cihub/commands/.

    Allowed exceptions (documented in CLEAN_CODE.md Part 2.2):
      - check.py: 3 progress indicators
      - hub_ci/__init__.py: 3 helpers
      - report/helpers.py: 1 fallback

    Total allowed: 7 prints
    """
    root = Path(getattr(args, "path", None) or hub_root())
    commands_dir = root / "cihub" / "commands"
    max_allowed = getattr(args, "max_allowed", 7)

    if not commands_dir.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Commands directory not found: {commands_dir}",
            problems=[{"severity": "error", "message": f"{commands_dir} not found"}],
        )

    # Find all print() calls not marked as allowed and not to stderr
    # Use regex to detect actual print function calls, not mentions in strings/comments
    import re
    violations: list[dict[str, str | int]] = []
    allowed_patterns = ["# ALLOWED:", "file=sys.stderr", "file = sys.stderr"]

    # Pattern to match actual print( function calls at start of statement
    # This avoids matching "print(" inside strings, comments, or as part of other identifiers
    print_call_pattern = re.compile(r'^\s*print\s*\(')

    for path in commands_dir.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        in_docstring = False
        docstring_delimiter = None

        for line_num, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()

            # Track docstrings (triple quotes)
            for delim in ['"""', "'''"]:
                count = stripped.count(delim)
                if count > 0:
                    if in_docstring and delim == docstring_delimiter:
                        in_docstring = False
                        docstring_delimiter = None
                    elif not in_docstring and count == 1:
                        in_docstring = True
                        docstring_delimiter = delim
                    # If count >= 2, it's a single-line docstring, no state change

            # Skip lines inside docstrings
            if in_docstring:
                continue

            # Skip commented lines
            if stripped.startswith("#"):
                continue

            # Check for actual print( function calls at start of statement
            if not print_call_pattern.match(line):
                continue

            # Skip allowed patterns
            if any(pattern in line for pattern in allowed_patterns):
                continue

            try:
                rel_path = str(path.relative_to(root))
            except ValueError:
                rel_path = str(path)
            violations.append({
                "file": rel_path,
                "line": line_num,
                "content": stripped[:80],  # Truncate for readability
            })

    count = len(violations)

    # Write GitHub summary if requested
    ctx = OutputContext.from_args(args)
    if ctx.summary_path:
        lines = [
            "## CommandResult Pattern Enforcement",
            "",
            f"Found **{count}** print() calls in `cihub/commands/` (max allowed: {max_allowed})",
            "",
        ]
        if count <= max_allowed:
            lines.append(f"✅ **PASSED** - {count}/{max_allowed} allowed prints")
        else:
            lines.append(f"❌ **FAILED** - {count} prints exceeds limit of {max_allowed}")
            lines.append("")
            lines.append("### Violations")
            lines.append("")
            for v in violations[:20]:  # Show first 20
                lines.append(f"- `{v['file']}:{v['line']}`: `{v['content']}`")
            if len(violations) > 20:
                lines.append(f"- ... and {len(violations) - 20} more")
        ctx.write_summary("\n".join(lines))

    if count > max_allowed:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"CommandResult pattern violation: {count} prints, expected ≤{max_allowed}",
            problems=[
                {"severity": "error", "message": f"{v['file']}:{v['line']}: {v['content']}"}
                for v in violations
            ],
            data={"print_count": count, "max_allowed": max_allowed, "violations": violations},
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"✓ CommandResult pattern enforced ({count}/{max_allowed} allowed prints)",
        data={"print_count": count, "max_allowed": max_allowed, "violations": violations},
    )


def cmd_quarantine_check(args: argparse.Namespace) -> CommandResult:
    """Fail if any file imports from _quarantine."""
    root = Path(getattr(args, "path", None) or hub_root())

    quarantine_patterns = [
        r"^\s*from\s+_quarantine\b",
        r"^\s*import\s+_quarantine\b",
        r"^\s*from\s+hub_release\._quarantine\b",
        r"^\s*import\s+hub_release\._quarantine\b",
        r"^\s*from\s+cihub\._quarantine\b",
        r"^\s*import\s+cihub\._quarantine\b",
        r"^\s*from\s+\.+_quarantine\b",
    ]
    exclude_dirs = {
        "_quarantine",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        ".ruff_cache",
        "vendor",
        "generated",
    }
    env_excludes = os.environ.get("QUARANTINE_EXCLUDE_DIRS", "")
    if env_excludes:
        exclude_dirs.update(env_excludes.split(","))

    violations: list[dict[str, str | int]] = []

    for path in root.rglob("*.py"):
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for pattern in quarantine_patterns:
                if re.search(pattern, line):
                    try:
                        rel_path = str(path.relative_to(root))
                    except ValueError:
                        rel_path = str(path)
                    violations.append({
                        "file": rel_path,
                        "line": line_num,
                        "content": line.strip(),
                    })

    if not violations:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Quarantine check PASSED - no imports from _quarantine found",
            data={"violations": [], "scanned_root": str(root)},
        )

    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=f"QUARANTINE IMPORT VIOLATION: {len(violations)} violation(s)",
        problems=[
            {"severity": "error", "message": f"{v['file']}:{v['line']}: {v['content']}"}
            for v in violations
        ],
        data={"violations": violations, "scanned_root": str(root)},
    )
