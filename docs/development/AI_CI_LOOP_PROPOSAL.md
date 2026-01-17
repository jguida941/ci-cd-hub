# Autonomous AI CI Loop Proposal

**Status:** active  
**Owner:** AI Architecture  
**Source-of-truth:** manual  
**Last-reviewed:** 2026-01-15  
**State:** Draft  

---

## Executive Summary

This document proposes implementing a **Ralph Wiggum-style autonomous AI loop** for the CI/CD Hub, enabling Claude Code (or similar AI agents) to continuously iterate on CI failures until all checks pass.   
The audit of our codebase reveals we are **~80% ready** for this implementation.

Initial scope is **internal-only**. The loop should target `cihub ci` (with triage emission) rather than `cihub check`, because triage requires `report.json` and the `ci` path already produces it.

---

## 1. Background: The Ralph Wiggum Pattern

### What Is It?

The **Ralph Wiggum pattern** ([source](https://paddo.dev/blog/ralph-wiggum-autonomous-loops/)) inverts traditional AI-assisted workflows by replacing step-by-step human direction with:

1. **Exit Code Interception**: Uses exit code 2 to block Claude from stopping (Claude hook convention, not a cihub exit code)
2. **Prompt Re-injection**: Feeds the original task back into the loop
3. **Context Persistence**: Git history and file modifications inform subsequent attempts
4. **Iteration Limits**: Safety guardrails via `--max-iterations`

### Core Philosophy

> "Let Claude fail repeatedly until it succeeds."

The pattern treats failures as refinement data rather than endpoints. Each iteration:
- Observes what broke previously
- Adjusts approach based on error patterns
- Advances toward the success threshold

### Related Projects

| Project | Purpose | Key Feature |
|---------|---------|-------------|
| [Continuous Claude](https://github.com/AnandChowdhary/continuous-claude) | Autonomous PR creation/merging | Context persistence across iterations |
| [Ralph Claude Code](https://github.com/frankbria/ralph-claude-code) | Autonomous development cycles | Circuit breaker for infinite loop prevention |
| [Claude-Flow](https://github.com/ruvnet/claude-flow) | Multi-agent orchestration | Distributed swarm intelligence |

---

## 2. Current Architecture Assessment

### 2.1 Strengths (Already Have)

#### Structured AI-Ready Outputs

| Component | Location | AI Capability |
|-----------|----------|---------------|
| **Triage Bundles** | `.cihub/triage.json` | Machine-readable failure data with severity ranking |
| **Priority JSON** | `.cihub/priority.json` | Failures sorted by severity (blocker→high→medium→low) |
| **CommandResult** | `cihub/types.py:14-42` | Unified output with `problems`, `suggestions`, `artifacts` |
| **AI Renderer** | `cihub/output/renderers.py` | Renderer exists; formatter registry is currently limited (docs stale only) |
| **Tool Evidence** | Triage system | Per-tool status tracking with reproduction commands |

Note: Only `docs stale` currently registers an AI formatter; `check` has no `--ai` flag yet.

#### Auto-Fix Infrastructure

```bash
cihub fix --safe       # Auto-runs: ruff --fix, black, isort (Python) / spotless (Java)
cihub fix --report     # Analyzes without fixing
cihub fix --report --ai  # AI-consumable fix recommendations
```

#### Check Tiers for Validation

```bash
cihub check            # Fast: lint, format, type, test (~30s)
cihub check --audit    # + drift detection (~45s)
cihub check --security # + bandit, pip-audit, trivy (~2min)
cihub check --full     # + templates, matrix, license (~3min)
cihub check --all      # Everything
```

#### Triage System for Failure Analysis

```bash
cihub triage --latest           # Analyze most recent CI failure
cihub triage --run <ID>         # Specific run analysis
cihub triage --detect-flaky     # Pattern detection
cihub triage --watch            # Background monitoring daemon
```

### 2.2 Key Files Supporting AI Integration

| File | Purpose |
|------|---------|
| `cihub/types.py` | `CommandResult` dataclass with `problems`, `suggestions` |
| `cihub/output/renderers.py` | `AIRenderer` class for LLM-optimized output (registered commands only) |
| `cihub/output/ai_formatters.py` | Registry for command-specific AI formatters |
| `cihub/services/triage_service.py` | Triage bundle generation from `report.json` |
| `cihub/commands/triage_cmd.py` | Triage CLI command (requires report/artifacts) |
| `cihub/commands/fix.py` | Auto-fix infrastructure |
| `cihub/commands/check.py` | Tiered validation with `CheckStep` aggregation |
| `cihub/commands/ci.py` | CI command that writes `report.json` (triage source) |

### 2.3 Gaps to Address

| Gap | Impact | Effort |
|-----|--------|--------|
| `cihub triage` requires `report.json`; `cihub check` does not produce it | High | Low |
| `cihub fix --safe --ai` is invalid; `fixes_applied` key does not exist | High | Low |
| `check` has no `--ai` flag and no formatter; registry is docs-stale only | Medium | Low |
| CLI registration must use `cli_parsers` + `CommandHandlers` (not direct parser edits) | Medium | Low |
| Workflow-based loop logic conflicts with CLI-first rules and requires explicit approval | Medium | Low |
| Update references to `cihub.exit_codes` (no `cihub.utils.exit_codes`) | Low | Low |

---

## 3. Proposed Implementation

### 3.1 Option A: Claude Code Hook Integration (Recommended)

Create a **Stop hook** that intercepts Claude Code's exit and re-injects the CI fix loop.

#### Hook Script: `~/.claude/hooks/stop.sh`

Template: `templates/hooks/stop.sh` (internal-only)
Iteration metadata is provided via environment variables:
`CIHUB_AI_LOOP_ITERATION`, `CIHUB_AI_LOOP_MAX_ITERATIONS`.

```bash
#!/bin/bash
set -e

# Check if we're in CI fix mode
if [[ "$CIHUB_AI_LOOP" == "true" ]]; then
    OUTPUT_DIR=".cihub"
    mkdir -p "$OUTPUT_DIR"
    # Run CI (produces report.json; triage emitted via env toggle)
    CIHUB_EMIT_TRIAGE=true \
      python -m cihub ci --json --output-dir "$OUTPUT_DIR" > "$OUTPUT_DIR/ci-result.json"

    # Requires jq for JSON parsing; fallback: python -c "import json,sys;print(json.load(sys.stdin)['exit_code'])"
    EXIT_CODE=$(jq '.exit_code' "$OUTPUT_DIR/ci-result.json")
    ITERATION=$(cat "$OUTPUT_DIR/iteration" 2>/dev/null || echo 0)
    MAX_ITERATIONS=${CIHUB_MAX_ITERATIONS:-10}

    if [[ "$EXIT_CODE" != "0" ]] && [[ "$ITERATION" -lt "$MAX_ITERATIONS" ]]; then
        echo $((ITERATION + 1)) > .cihub/iteration
        # Exit code 2 tells Claude Code to continue (hook convention, not cihub)
        exit 2
    fi
fi
```

#### Optional Hook Review Step (Codex or other reviewer)

The hook can optionally run a review command before deciding to exit with code 2.
This step is tool-agnostic (Codex, custom script, etc.) and should write a short
summary to the loop output directory for later resume.

Proposed interface:
- `CIHUB_AI_REVIEW_CMD`: shell command to execute after `cihub ci`
- Review inputs: `git diff`, `.cihub/triage.json`, `.cihub/priority.json`
- Review output: `.cihub/ai-loop/<session-id>/iteration-<n>/review.md`

#### Advantages
- Leverages existing Claude Code infrastructure
- Minimal code changes to cihub
- Works with any AI agent that supports hooks

#### Disadvantages
- Requires user to configure hooks
- Less visibility into loop state

### 3.2 Option B: Enhance Existing Hook (Medium Effort)

Extend the Claude Code stop hook to optionally push changes, wait for GitHub Actions,
and fetch triage for the latest run when local CI fails. This keeps the loop logic
in the hook while still using `cihub triage` for structured failure data.

Example hook snippet (after local CI failure):

```bash
# Add to templates/hooks/stop.sh after local CI check fails
if [[ "$EXIT_CODE" != "0" ]] && [[ -n "$GITHUB_TOKEN" ]]; then
  # Push changes (dev branch only)
  git add -A && git commit -m "AI loop iteration $ITERATION" && git push

  # Wait for GitHub Actions
  gh run watch --exit-status || true

  # Fetch remote triage
  RUN_ID=$(gh run list --limit 1 --json databaseId -q '.[0].databaseId')
  python -m cihub triage --run "$RUN_ID" --output-dir "$OUTPUT_DIR"
fi
```

#### Advantages
- Integrates with existing hook flow and triage tooling
- Minimal CLI changes required
- Can be gated by environment flags for safety

#### Disadvantages
- More shell logic to maintain (edge cases, retries)
- Requires GH CLI + auth; fewer guardrails than CLI-based loop

### 3.3 Option C: MCP Server Integration (Higher Effort, More Powerful)

Use GitHub's MCP server for structured CI/CD access. This allows the agent to call
GitHub Actions APIs directly via MCP tools rather than shelling out to `gh`.

```json
// .claude/settings.json
{
  "mcpServers": {
    "github": {
      "url": "https://api.githubcopilot.com/mcp/",
      "auth": "oauth"
    }
  }
}
```

Then Claude can call tools such as:
- `actions.list_workflow_runs`
- `actions.get_workflow_run_logs`
- `actions.trigger_workflow`

#### Advantages
- Structured, typed API access (no CLI parsing)
- Richer capabilities for multi-run analysis

#### Disadvantages
- Requires MCP-compatible host + OAuth setup
- Higher integration effort; not portable to all environments

### 3.4 Option D: New `cihub ai-loop` Command

Add a dedicated command to orchestrate the autonomous loop.
**Status:** Internal-only; CLI registration enabled (explicit approval granted).
Implementation should force `CIHUB_EMIT_TRIAGE=true` and pass iteration metadata to `cihub ci`
so triage output stays on the standard path.

#### Command Implementation: `cihub/commands/ai_loop.py`

Note: Example is illustrative; the implementation forces `CIHUB_EMIT_TRIAGE=true`
and delegates triage emission to `cihub ci`.

```python
"""Autonomous AI CI fix loop command."""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult


@dataclass
class LoopState:
    """Track state across iterations."""
    iteration: int = 0
    max_iterations: int = 10
    fixes_applied: list[str] = field(default_factory=list)
    failures_seen: list[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)


def cmd_ai_loop(args: argparse.Namespace) -> CommandResult:
    """
    Autonomous AI CI fix loop.

    Continuously runs `cihub ci`, generates triage bundles,
    applies safe fixes, and re-validates until all CI checks pass
    or max iterations reached.
    """
    from cihub.commands.ci import cmd_ci
    from cihub.commands.fix import cmd_fix
    from cihub.services.triage_service import generate_triage_bundle, write_triage_bundle

    repo_path = Path(args.repo or ".").resolve()
    output_dir = Path(args.output_dir or ".cihub")
    output_dir.mkdir(parents=True, exist_ok=True)

    state = LoopState(max_iterations=args.max_iterations)

    for iteration in range(state.max_iterations):
        state.iteration = iteration + 1

        # 1. Run CI (produces report.json)
        ci_args = _build_ci_args(args, output_dir, repo_path)
        ci_result = cmd_ci(ci_args)

        # 2. Generate triage bundle from report.json (same payload as CIHUB_EMIT_TRIAGE)
        report_path = Path(ci_result.data.get("report_path", output_dir / "report.json"))
        bundle = generate_triage_bundle(output_dir, report_path=report_path)
        write_triage_bundle(bundle, output_dir)

        # Save iteration result
        _save_iteration_state(output_dir, state, ci_result)

        if ci_result.exit_code == EXIT_SUCCESS:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"All CI checks passed after {state.iteration} iteration(s)",
                data={
                    "iterations": state.iteration,
                    "fixes_applied": state.fixes_applied,
                    "duration_seconds": time.time() - state.start_time,
                },
            )

        # 3. Attempt safe auto-fixes (optional)
        if args.fix_mode == "safe":
            fix_args = argparse.Namespace(
                repo=str(repo_path),
                safe=True,
                report=False,
                ai=False,
                dry_run=False,
            )
            fix_result = cmd_fix(fix_args)
            fix_data = fix_result.data or {}
            state.fixes_applied.extend(fix_data.get("fixes", []))

        # 4. Optional AI report pack for manual fixes
        if getattr(args, "emit_report", False):
            report_args = argparse.Namespace(
                repo=str(repo_path),
                safe=False,
                report=True,
                ai=True,
                dry_run=False,
            )
            cmd_fix(report_args)

        # 5. Track unique failures
        for problem in ci_result.problems or []:
            failure_id = f"{problem.get('tool', 'unknown')}:{problem.get('message', '')}"
            if failure_id not in state.failures_seen:
                state.failures_seen.append(failure_id)

        # 6. Circuit breaker: stop if same failures persist
        if _should_break(state, ci_result):
            break

    # Max iterations reached
    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=f"Could not fix all issues after {state.max_iterations} iterations",
        problems=ci_result.problems if ci_result else [],
        suggestions=[
            {"message": "Review .cihub/triage.md for remaining issues"},
            {"message": "Run 'cihub fix --report --ai' for detailed recommendations"},
        ],
        data={
            "iterations": state.iteration,
            "fixes_applied": state.fixes_applied,
            "remaining_failures": len(state.failures_seen),
        },
    )


def _build_ci_args(
    args: argparse.Namespace,
    output_dir: Path,
    repo_path: Path,
) -> argparse.Namespace:
    """Build args for cmd_ci with explicit defaults."""
    return argparse.Namespace(
        repo=str(repo_path),
        output_dir=str(output_dir),
        report=None,
        summary=None,
        workdir=None,
        install_deps=False,
        no_summary=False,
        write_github_summary=None,
        correlation_id=None,
        config_from_hub=None,
    )


def _save_iteration_state(
    output_dir: Path,
    state: LoopState,
    result: CommandResult,
) -> None:
    """Save iteration state for debugging and analysis."""
    state_file = output_dir / f"ai-loop-iteration-{state.iteration}.json"
    state_file.write_text(
        json.dumps(
            {
                "iteration": state.iteration,
                "exit_code": result.exit_code,
                "problems_count": len(result.problems),
                "fixes_applied": len(state.fixes_applied),
                "timestamp": time.time(),
            },
            indent=2,
        )
    )


def _should_break(state: LoopState, result: CommandResult) -> bool:
    """Circuit breaker logic to prevent infinite loops."""
    # Stop if no new problems found (stuck in same state)
    current_failures = {
        f"{p.get('tool')}:{p.get('message')}"
        for p in result.problems
    }

    if state.iteration > 3:
        # If same failures for 3+ iterations, stop
        recent_failures = set(state.failures_seen[-10:])
        if current_failures == recent_failures:
            return True

    return False
```

#### CLI Registration (via `cli_parsers` + `CommandHandlers`)

```python
# Add to add_core_commands() in cihub/cli_parsers/core.py
ai_loop = subparsers.add_parser(
    "ai-loop",
    help="Autonomous AI CI fix loop",
)
add_json_flag(ai_loop)
add_repo_args(ai_loop)
ai_loop.add_argument(
    "--max-iterations",
    type=int,
    default=10,
    help="Maximum iterations before stopping (default: 10)",
)
ai_loop.add_argument(
    "--fix-mode",
    choices=["safe", "report-only"],
    default="safe",
    help="Fix strategy: safe (auto-fix) or report-only (emit report pack only)",
)
ai_loop.add_argument(
    "--emit-report",
    action="store_true",
    help="Generate fix report prompt pack each iteration",
)
ai_loop.add_argument(
    "--output-dir",
    default=".cihub",
    help="Output directory for loop artifacts",
)
ai_loop.set_defaults(func=handlers.cmd_ai_loop)
```

#### Advantages
- Full control over loop behavior
- Integrated with existing CLI patterns
- Testable and documented
- Rich state tracking

#### Disadvantages
- More code to maintain
- Requires CLI update

### 3.5 Option E: GitHub Actions Wrapper (Approved, Internal-Only)

Leverage existing workflow architecture as a thin wrapper only. Any loop logic must live in the CLI, and workflow changes require explicit approval.

#### Workflow: `.github/workflows/ai-ci-loop.yml`

```yaml
name: AI CI Loop

on:
  workflow_dispatch:
    inputs:
      max_iterations:
        description: "Maximum fix iterations"
        default: "5"
        type: string
      fix_mode:
        description: "Fix strategy"
        type: choice
        default: "safe"
        options:
          - safe
          - report-only

jobs:
  ai-loop:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install cihub
        run: pip install -e ".[ci]"
      - name: AI CI Loop
        env:
          CIHUB_EMIT_TRIAGE: "true"
        run: |
          python -m cihub ai-loop \
            --max-iterations ${{ inputs.max_iterations }} \
            --fix-mode ${{ inputs.fix_mode }}
```

#### Advantages
- Runs in CI environment (same as production)
- Full artifact persistence
- Integrates with PR workflow
- No local setup required

#### Disadvantages
- Slower iteration (CI overhead)
- Limited to GitHub Actions
- Less interactive

### 3.6 Option F: Remote Loop Mode (GitHub Actions Polling)

Goal: push to a dev branch, wait for GitHub Actions to complete, triage failures,
apply fixes locally, and repeat until green.

Proposed requirements:
- Use `gh` CLI as the primary provider; allow API fallback when `GITHUB_TOKEN` is set
- Always use `cihub triage --latest` or `cihub triage --run <id>` for analysis (CLI-first)
- Auto-push only to a non-protected dev branch by default (e.g., `ai/ci-loop`)
- Persist per-iteration artifacts in `.cihub/ai-loop/<session-id>/` for resume/review

Proposed CLI flags:
- `--remote` (enable remote loop mode)
- `--remote-provider {gh,api}` (default: `gh`)
- `--workflow <name-or-id>` (optional filter)
- `--push`, `--push-branch`, `--push-remote`
- `--allow-protected-branch`, `--allow-dirty`
- `--commit`, `--commit-message`
- `--review-command` (optional reviewer step per iteration)
- `--max-minutes`, `--unsafe-unlimited`, `--resume`

Proposed triage controls:
- `--triage-mode {auto,latest,run,none}` (default: `auto`)
- `--triage-run-id <id>` (used when mode=run)
- `--triage-output-dir <path>` (defaults under `.cihub/ai-loop/<session-id>/iteration-N/`)
- `--fallback {api,local,stop}` (what to do if remote triage fails)

---

## 4. Safety Guardrails

### 4.1 Required Safeguards

```python
# Proposed: keep in ai-loop command initially; extract to a config module later if needed.

AI_LOOP_CONFIG = {
    # Iteration limits
    "max_iterations": 10,
    "max_duration_seconds": 600,  # 10 minutes

    # File protection
    "max_files_per_iteration": 20,
    "forbidden_paths": [
        ".github/workflows/*",      # No workflow self-modification
        "*.env*",                   # No secrets
        "pyproject.toml",           # No dependency changes (without approval)
        "setup.py",
        "requirements*.txt",
    ],

    # Validation requirements
    "require_test_pass": True,
    "require_lint_pass": True,
    "auto_rollback_on_regression": True,

    # Circuit breaker
    "circuit_breaker": {
        "consecutive_failures": 3,
        "same_error_threshold": 3,  # Stop if same error 3x
        "error_patterns": [
            "permission denied",
            "out of memory",
            "rate limit",
            "authentication failed",
        ],
    },

    # Audit trail
    "log_all_changes": True,
    "require_commit_per_iteration": True,
}
```

### 4.2 Rollback Strategy

```python
def rollback_iteration(iteration: int) -> None:
    """Rollback to state before iteration."""
    import subprocess

    # Find commit before iteration
    result = subprocess.run(
        ["git", "log", "--oneline", "-n", str(iteration + 1)],
        capture_output=True, text=True,
    )
    commits = result.stdout.strip().split("\n")

    if len(commits) > iteration:
        target_commit = commits[iteration].split()[0]
        subprocess.run(["git", "reset", "--hard", target_commit])
```

Note: `git reset --hard` is destructive. Prefer worktrees or non-destructive restores unless a human explicitly approves rollback behavior.

### 4.3 Prompt Contract (Critical Skill)

Ralph loops only succeed with explicit completion promises and success criteria. Every loop should include a contract like:

- Completion promise string (exact match)
- Clear success criteria (e.g., "`cihub ci` exit 0")
- Incremental phases (if the task is large)
- Stuck handling after N iterations (what to collect and when to stop)

#### 4.3.1 Base Template

```text
/ralph-loop "Task summary.

Success criteria:
- `cihub ci` exits 0
- No new failures introduced

Stuck handling after 10 iterations:
- Capture .cihub/triage.json and .cihub/priority.json
- Summarize blockers and stop

Output: <promise>COMPLETE</promise>"
```

#### 4.3.2 CI-Specific Contract Examples

**Example 1: Fix All Lint Errors**

```text
Fix all lint errors in the codebase.

Success criteria:
- `cihub ci` exits 0
- No ruff, black, or isort failures in .cihub/triage.json

Per-iteration workflow:
1. Read .cihub/priority.json for severity-ranked issues
2. Run `cihub fix --safe` for auto-fixable issues
3. For remaining issues, edit files directly based on triage hints
4. Re-run `cihub ci` to validate

Stuck handling after 5 iterations:
- If same lint errors persist 3x, they may require human judgment
- Capture .cihub/triage.md and summarize blockers
- Stop and report unfixable issues

Safety rules:
- Do NOT modify .github/workflows/
- Do NOT modify pyproject.toml or requirements.txt
- Do NOT disable lint rules to "fix" errors

Output: <promise>LINT_CLEAN</promise>
```

**Example 2: Fix Test Failures**

```text
Fix failing tests until pytest passes.

Success criteria:
- `cihub ci` exits 0
- tests_failed == 0 in .cihub/triage.json summary
- No test count regression (tests_total >= previous run)

Per-iteration workflow:
1. Read .cihub/priority.json for failed test details
2. Check tool_evidence for pytest artifacts
3. Read test output from .cihub/tool-outputs/pytest/
4. Fix test code or implementation as needed
5. Re-run `cihub ci` to validate

Stuck handling after 10 iterations:
- If same test fails 3x, check if it's flaky (use --detect-flaky)
- Capture test output and hypothesis shrink examples
- Stop and report with reproduction command

Safety rules:
- Do NOT delete or skip failing tests
- Do NOT reduce test coverage
- Do NOT mock away the actual behavior being tested

Output: <promise>TESTS_PASS</promise>
```

**Example 3: Fix Security Vulnerabilities**

```text
Fix security vulnerabilities found by bandit and pip-audit.

Success criteria:
- `cihub ci` exits 0
- No HIGH or CRITICAL findings in .cihub/triage.json
- bandit_high == 0 and pip_audit_high == 0 in tool_metrics

Per-iteration workflow:
1. Read .cihub/priority.json (security issues are severity=high/blocker)
2. For bandit: fix code patterns (SQL injection, hardcoded secrets, etc.)
3. For pip-audit: update vulnerable dependencies
4. Re-run `cihub ci` to validate

Stuck handling after 5 iterations:
- Some vulnerabilities may require architectural changes
- Capture vulnerability details and suggested fixes
- Stop and escalate to human review

Safety rules:
- Do NOT suppress security warnings without justification
- Do NOT downgrade dependencies if it breaks functionality
- Do NOT commit secrets or credentials

Output: <promise>SECURITY_CLEAN</promise>
```

#### 4.3.3 Multi-Phase Contract (Large Tasks)

For complex tasks, break into phases with intermediate checkpoints:

```text
Implement feature X with full CI compliance.

Phase 1: Implementation (iterations 1-5)
- Write core functionality
- Checkpoint: Code compiles/imports without error

Phase 2: Tests (iterations 6-10)
- Add unit tests for new code
- Checkpoint: tests_total increased, tests_failed == 0

Phase 3: Lint & Format (iterations 11-15)
- Fix any lint/format issues
- Checkpoint: ruff, black, mypy all pass

Phase 4: Security (iterations 16-20)
- Address any security findings
- Checkpoint: bandit, pip-audit clean

Success criteria:
- `cihub ci` exits 0
- All phase checkpoints met

Stuck handling:
- At each phase boundary, if stuck 3x, stop and report
- Include .cihub/triage.md with phase-specific context

Output: <promise>FEATURE_COMPLETE</promise>
```

#### 4.3.4 Contract Validation (Planned)

Planned validation for the loop runner/hook should ensure contracts have:

| Field | Required | Description |
|-------|----------|-------------|
| Success criteria | Yes | Measurable conditions (exit code, metric values) |
| Per-iteration workflow | Yes | Steps to follow each cycle |
| Stuck handling | Yes | What to do when progress stalls |
| Safety rules | Recommended | Boundaries the AI must not cross |
| Output promise | Yes | Exact string to emit on success |

Note: Contract validation is not implemented yet; treat this as a required checklist
until a dedicated validator is added.

#### 4.3.5 Contract File Template (Proposed)

Allow a repo-local contract file (Markdown with YAML front matter) to define
success criteria, safety rules, and the output promise.

Example:

```markdown
---
success_criteria:
  - command: "cihub ci"
    exit_code: 0
stop_conditions:
  - same_error_threshold: 3
safety_rules:
  - "Do not modify .github/workflows/"
  - "Do not change dependency files"
output_promise: "CI_LOOP_COMPLETE"
---
# Task Contract
Fix CI until green. See Success Criteria.
```

Proposed CLI flags:
- `--contract-file <path>`
- `--contract-strict` (fail if required fields are missing)

### 4.4 Remote Mode Guardrails (Proposed)

- Default push branch: `ai/ci-loop`; refuse `main`/`master` unless `--allow-protected-branch`
- Require clean worktree unless `--allow-dirty`
- Enforce time budget via `--max-minutes` (default: 60); unlimited requires `--unsafe-unlimited`
- Persist iteration artifacts for resume and review (`.cihub/ai-loop/<session-id>/`)
- Optional reviewer step (`--review-command`) writes `review.md` per iteration
- Remote failures should emit a clear `stop_reason` and preserve the triage bundle

### 4.4.1 Remote Provider Unification (MCP + gh + Triage) (Proposed)

To keep CLI-first architecture while allowing MCP and `gh` together:
- Define a `RemoteProvider` interface (`list_runs`, `get_run`, `wait_for_run`, `fetch_artifacts`, `fetch_logs`)
- Implement `GhProvider` and `McpProvider` behind `cihub ai-loop --remote-provider {gh,mcp,auto}`
- Normalize provider output into a shared `RemoteEvidence` payload (run metadata + paths)
- Always pass evidence into the triage pipeline (single source of analysis)

Proposed outputs per iteration:
- `remote_run.json` (run metadata, provider used, URLs)
- `provider_sources.json` (which provider supplied run/artifacts/logs)
- `triage.json` / `priority.json` / `triage.md` (always from triage service)

### 4.5 Logging and Resume (Proposed)

Per iteration, emit both machine and AI-friendly outputs:
- `state.json` (iteration metadata, stop reason, timing)
- `metrics.json` (durations, run IDs, run URLs, failure signature hash)
- `triage.json` / `priority.json` / `triage.md` (from `cihub triage`)
- `review.md` (from reviewer step, if enabled)
- `ai_loop_summary.md` (short narrative summary for compaction/resume)

Resume behavior:
- `--resume` reads last `state.json` and continues from the next iteration
- `ai_loop_summary.md` is the primary context payload for new sessions
- `--output-dir` can override the default `.cihub/ai-loop/` root

### 4.5.1 Fresh-Context Loop Runner (Proposed)

Claude stop hooks do not trigger on compaction. To avoid bloated context windows,
add an outer loop runner that **starts a new LLM context each iteration** and
feeds only the contract + latest iteration summary.

Implementation shape:
- Wrapper script or CLI subcommand that runs `cihub ai-loop --json` once per iteration
- Writes `iteration-context.md` (contract + `ai_loop_summary.md` + triage pointers)
- Starts a new agent session each iteration using `iteration-context.md`
- Loop ends on success, stop_reason, or guardrail timeout

Goal: preserve accuracy on long runs without manual compaction.

### 4.6 Artifact Pack (Proposed)

Provide a per-iteration artifact bundle for review and double-checking:
- `bundle.json` with paths and hashes
- `bundle.md` summary for AI and reviewers
- Includes: `report.json`, `triage.json`, `priority.json`, `triage.md`,
  `ci-result.json`, `fix-report.md`, `git diff --stat`, `git status`, `review.md`,
  `diff.patch`

Implementation options:
- CLI flag: `cihub ai-loop --artifact-pack` or `--bundle-dir`
- Script helper: `scripts/ai-loop-artifacts.sh` for manual packaging

### 4.7 Production Hardening (Proposed)

- Enforce `AI_LOOP_CONFIG` guardrails (forbidden paths, max files per iteration)
- Add per-repo/branch lock file to prevent concurrent loops
- Stop after N iterations with no working tree changes (`stop_reason=no_changes`)
- Preflight checks for `gh` installation/auth and branch safety
- Optional `--remote-dry-run` (triage + polling only, no push)

---

## 5. Integration with Existing Tools

### 5.1 Triage System Integration

The triage system is **purpose-built** for AI consumption and expects `report.json`. Use `cihub ci` (or `generate_triage_bundle`) to create triage artifacts before reading them.

```python
# AI loop reads triage bundle
import json

triage = json.load(open(".cihub/triage.json"))

# Failures are already sorted by severity
for failure in triage["failures"]:
    print(f"Tool: {failure['tool']}")
    print(f"Severity: {failure['severity']}")
    print(f"Category: {failure['category']}")
    print(f"Reproduce: {failure['reproduce']['command']}")
    print(f"Hints: {failure['hints']}")
    print(f"Artifacts: {failure['artifacts']}")
```

### 5.2 CommandResult for Loop Control

```python
# Each iteration produces structured output
result = cmd_ci(args)

if result.exit_code == 0:
    break  # Success!

# Parse problems for AI analysis
for problem in result.problems:
    severity = problem.get("severity", "info")
    tool = problem.get("tool", "unknown")
    message = problem.get("message", "")

    if severity == "error":
        # Priority fix
        pass

# Use suggestions for next iteration
for suggestion in result.suggestions:
    print(f"AI Hint: {suggestion['message']}")
```

### 5.3 AI Formatter Registration

Add check command to AI formatters if/when `check --ai` is introduced:

```python
# cihub/output/ai_formatters.py

_AI_FORMATTERS: dict[str, tuple[str, str]] = {
    "docs stale": ("cihub.commands.docs_stale.output", "format_ai_output"),
    "check": ("cihub.commands.check", "format_check_ai"),  # NEW (requires check --ai)
}
```

---

## 6. Implementation Plan

### Phase 1: Foundation (Week 1)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| [x] Add Prompt Contract (Critical Skill) | `docs/development/AI_CI_LOOP_PROPOSAL.md` | Low | P1 |
| [x] Align loop to `cihub ci` + triage bundle emission | `cihub/commands/ai_loop.py` | Low | P1 |
| [x] Add iteration tracking field to triage history | `cihub/services/triage_service.py` | Low | P1 |
| [x] Define AI loop safety config location (CLI flags first) | `cihub/commands/ai_loop.py` | Low | P1 |

### Phase 2: Core Loop (Week 2)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| [x] Implement `cihub ai-loop` command (internal-only) | `cihub/commands/ai_loop.py` | Medium | P1 |
| [x] Add CLI registration | `cihub/cli.py`, `cihub/cli_parsers/` | Low | P1 |
| [x] Create Claude Code hook templates | `templates/hooks/` | Medium | P2 |
| [x] Add unit tests | `tests/test_ai_loop.py` | Medium | P1 |

Note: Any new CLI surface requires explicit approval, command-contract updates, and CLI docs regeneration.

### Phase 3: Intelligence (Week 3)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| [x] Pattern-based fix suggestions | `cihub/services/ai/patterns.py` | High | P2 |
| [x] Flaky test exclusion in loops | `cihub/commands/ai_loop.py` | Medium | P2 |
| [x] Stop reason diagnostics for loop exits | `cihub/commands/ai_loop.py` | Low | P2 |
| [x] GitHub Actions wrapper (requires approval) | `.github/workflows/ai-ci-loop.yml` | Medium | P2 |

### Phase 3.5: Remote Loop (GitHub Actions) (Week 3.5)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| [x] Add `--remote` loop mode with run polling + run selection | `cihub/commands/ai_loop.py` | High | P2 |
| [x] Add `--push`/`--push-branch`/`--push-remote` safety guards | `cihub/commands/ai_loop.py` | Medium | P2 |
| [x] Add reviewer step (`--review-command`) + review bundle outputs | `cihub/commands/ai_loop.py` | Medium | P2 |
| [x] Add triage mode + fallback handling | `cihub/commands/ai_loop.py` | Medium | P2 |
| [x] Add session logging + `--resume` state handling | `cihub/commands/ai_loop.py` | Medium | P2 |
| [ ] Add remote provider interface + `--remote-provider auto` | `cihub/commands/ai_loop_remote.py` | Medium | P2 |
| [ ] Add MCP-backed provider + evidence normalization | `cihub/commands/ai_loop_remote.py` | Medium | P2 |
| [ ] Emit `remote_run.json` + `provider_sources.json` per iteration | `cihub/commands/ai_loop_remote.py` | Low | P2 |
| [ ] Add tests for remote mode + safety rules | `tests/test_ai_loop.py` | High | P2 |

### Phase 3.6: Contract + Artifact Pack (Week 3.6)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| [x] Add contract file parsing + strict validation flags | `cihub/commands/ai_loop.py` | Medium | P2 |
| [x] Add artifact pack bundle output (CLI flag or script) | `cihub/commands/ai_loop.py`, `scripts/` | Medium | P2 |
| [ ] Add tests for contract parsing + artifact bundle | `tests/test_ai_loop.py` | Medium | P2 |
| [ ] Add hook installer helper for Claude/Codex setup | `cihub/commands/ai_loop.py`, `templates/hooks/` | Medium | P2 |

### Phase 3.7: Production Hardening (Week 3.7)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| [x] Enforce guardrails (forbidden paths, max files) | `cihub/commands/ai_loop.py` | Medium | P2 |
| [x] Add loop lock file per repo/branch | `cihub/commands/ai_loop.py` | Medium | P2 |
| [x] Add no-change circuit breaker | `cihub/commands/ai_loop.py` | Low | P2 |
| [x] Add preflight checks for `gh` + branch safety | `cihub/commands/ai_loop.py` | Medium | P2 |
| [x] Add `--remote-dry-run` support | `cihub/commands/ai_loop.py` | Low | P2 |
| [x] Modularize ai-loop implementation into focused modules | `cihub/commands/ai_loop_*.py` | Medium | P2 |

### Phase 3.8: Fresh-Context Runner (Week 3.8)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| [ ] Add outer loop runner that starts a new agent session per iteration | `scripts/`, `cihub/commands/ai_loop.py` | Medium | P2 |
| [ ] Emit `iteration-context.md` (contract + summary + triage pointers) | `cihub/commands/ai_loop_artifacts.py` | Medium | P2 |
| [ ] Add tests for context payload + stop conditions | `tests/test_ai_loop.py` | Medium | P2 |

### Phase 4: Multi-Repo (Week 4)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| Multi-repo loop orchestration | `cihub/commands/orchestrate.py` | High | P3 |
| Registry-based loop policies (schema/config driven) | `cihub/data/schema/ci-hub-config.schema.json`, `cihub/data/config/defaults.yaml` | Medium | P3 |
| Dashboard for loop status | `cihub/commands/dashboard.py` | Medium | P3 |

### Phase 5: Wizard Integration (Future)

Goal: allow the wizard to select a repo, configure loop settings, and launch the CLI loop.

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| [ ] Define wizard contract for loop setup (flags + profile mapping) | `docs/development/AI_CI_LOOP_PROPOSAL.md` | Low | P3 |
| [ ] Expose loop config in wizard UI (calls `cihub ai-loop --json`) | Wizard repo | Medium | P3 |
| [ ] Add "remote loop" presets (branch, provider, timeouts) | Wizard repo | Medium | P3 |
| [ ] Wizard can install Claude hook + set review command (Codex) | Wizard repo | Medium | P3 |
| [ ] Wizard can generate contract template + artifact pack settings | Wizard repo | Medium | P3 |
| [ ] Wizard exposes max iterations + max minutes caps | Wizard repo | Medium | P3 |
| [ ] Wizard selects strict contract template for completion criteria | Wizard repo | Medium | P3 |

---

## 7. Quick Start: Minimal Implementation

For immediate testing without code changes:

### Script: `scripts/ai-ci-loop.sh`

```bash
#!/bin/bash
# Minimal AI CI loop script
# Usage: ./scripts/ai-ci-loop.sh [max_iterations]

set -e

MAX_ITERATIONS=${1:-5}
OUTPUT_DIR=".cihub"

mkdir -p "$OUTPUT_DIR"

echo "Starting AI CI Loop (max $MAX_ITERATIONS iterations)"
echo "=================================================="

for i in $(seq 1 $MAX_ITERATIONS); do
    echo ""
    echo " Iteration $i of $MAX_ITERATIONS"
    echo "-----------------------------------"

    # Run CI with JSON output (emits triage bundle)
    if CIHUB_EMIT_TRIAGE=true \
        python -m cihub ci --json --output-dir "$OUTPUT_DIR" > "$OUTPUT_DIR/ci-$i.json" 2>&1; then
        echo " All CI checks passed!"
        echo ""
        echo "Summary:"
        echo "  - Iterations: $i"
        echo "  - Status: SUCCESS"
        exit 0
    fi

    echo "CI failed, analyzing..."

    # Show priority issues
    if [[ -f "$OUTPUT_DIR/priority.json" ]]; then
        echo ""
        echo "Priority Issues:"
        python3 -c "
import json
with open('$OUTPUT_DIR/priority.json') as f:
    data = json.load(f)
for f in data.get('failures', [])[:5]:
    print(f\"  [{f.get('severity', '?')}] {f.get('tool', '?')}: {f.get('message', '?')[:60]}\")
" 2>/dev/null || echo "  (could not parse priority.json)"
    fi

    # Apply safe auto-fixes
    echo ""
    echo "Attempting safe auto-fixes..."
    python -m cihub fix --safe 2>/dev/null || true

    # Check if any changes were made
    if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
        echo "Changes detected, ready for next iteration"
    else
        echo "️ No automatic fixes available"
    fi

    sleep 1
done

echo ""
echo "Max iterations ($MAX_ITERATIONS) reached"
echo ""
echo "Review remaining issues:"
echo "  - Triage: $OUTPUT_DIR/triage.md"
echo "  - Priority: $OUTPUT_DIR/priority.json"
echo ""
exit 1
```

### Usage with Claude Code

```bash
# Make script executable
chmod +x scripts/ai-ci-loop.sh

# Run with Claude Code
CIHUB_AI_LOOP=true claude --max-turns 50 \
  "Run ./scripts/ai-ci-loop.sh and fix any remaining issues.

   After each iteration:
   1. Read .cihub/triage.json for structured failure data
   2. Read .cihub/priority.json for severity-ranked issues
   3. Use 'cihub fix --safe' for auto-fixes
   4. For issues that can't be auto-fixed, edit files directly

   Keep iterating until 'cihub ci' passes.

   Safety rules:
   - Do NOT modify .github/workflows/
   - Do NOT modify pyproject.toml or requirements.txt
   - Do NOT commit secrets or credentials"
```

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Average iterations to pass | < 5 | Track in triage history |
| Auto-fix success rate | > 60% | Fixes applied / total issues |
| Time to green | < 10 min | From first failure to pass |
| False positive rate | < 5% | Unnecessary changes / total changes |
| Regression rate | < 1% | New failures introduced / iterations |

---

## 9. Open Questions

### Recent Decisions (2026-01-15 Addendum)

- Remote mode uses `gh` CLI by default; allow API fallback when `GITHUB_TOKEN` is set
- Auto-push is supported but targets a non-protected dev branch by default (`ai/ci-loop`)
- Unlimited looping requires explicit `--unsafe-unlimited` and still honors `--max-minutes`
- Logs default to `.cihub/ai-loop/` with optional `--output-dir` overrides
- Reviewer step is optional via `--review-command`/`CIHUB_AI_REVIEW_CMD`, with `review.md` output
- Triage is first-class in remote mode, with explicit `--triage-mode` and fallback behavior
- Wizard integration is required; wizard must call the CLI and avoid parallel loop logic

### Remaining Questions

1. **Should AI loop be internal-only or user-facing?**
   - Recommendation: Internal-only until stable; opt-in CLI command later if needed

2. **How to handle flaky tests?**
   - Recommendation: Use `--detect-flaky` and exclude known flaky tests

3. **Should fixes be auto-committed?**
   - Recommendation: No by default; optional flag for internal use, prefer worktrees/branch isolation

4. **What about rate limits (GitHub API, AI API)?**
   - Recommendation: Implement backoff and rate limit detection in circuit breaker

5. **Multi-repo orchestration?**
   - Recommendation: Phase 4 implementation using existing `hub-orchestrator.yml` pattern

6. **Multi-agent fan-out (parallel Claude runs)?**
   - Recommendation: Defer; avoid parallel edits on the same worktree. If needed, use
     dedicated branches/worktrees per agent with an orchestrator that merges results.

7. **Reviewer gating policy (Codex/other reviewer)?**
   - Recommendation: Advisory by default; allow `--review-strict` only after safety
     criteria are defined and tested.

---

## 10. References

- [Ralph Wiggum: Autonomous Loop Pattern](https://paddo.dev/blog/ralph-wiggum-autonomous-loops/)
- [Continuous Claude](https://github.com/AnandChowdhary/continuous-claude)
- [Ralph Claude Code](https://github.com/frankbria/ralph-claude-code)
- [Claude-Flow](https://github.com/ruvnet/claude-flow)
- [CI/CD Pipelines with Agentic AI](https://www.elastic.co/search-labs/blog/ci-pipelines-claude-ai-agent)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [ADR-0032: PyQt6 CLI Wrapper](docs/adr/0032-pyqt6-cli-wrapper-full-automation.md) (internal)
- [ADR-0035: Registry Triage LLM Bundle](docs/adr/0035-registry-triage-llm-bundle.md) (internal)

---

## Appendix A: Codebase Audit Summary

The following components were audited:

| Component          | Status  | Notes                                               |
|--------------------|---------|-----------------------------------------------------|
| CLI Architecture   | Ready   | CommandResult pattern, lazy loading                 |
| Triage System      | Ready   | Full AI-ready structured output                     |
| Check Tiers        | Ready   | CheckStep aggregation, deduplication                |
| Fix Infrastructure | Ready   | Safe auto-fixes for Python/Java                     |
| Report System      | Ready   | tools_configured/ran/success maps                   |
| Hook Mechanisms    | Partial | Tool adapters exist, no CLI hooks yet               |
| AI Formatters      | Partial | Only `docs stale` registered; `check` has no `--ai` |
| Configuration      | Ready   | Full schema support, custom tools                   |

---

## Appendix B: File Locations

Key files for implementation:

```
cihub/
├── types.py                    # CommandResult, ToolResult
├── cli.py                      # Main entry point
├── output/
│   ├── renderers.py            # AIRenderer class
│   └── ai_formatters.py        # Formatter registry
├── commands/
│   ├── check.py                # Check command with tiers
│   ├── fix.py                  # Auto-fix infrastructure
│   ├── triage_cmd.py           # Triage command
│   ├── ai_loop.py              # NEW: AI loop command
│   └── triage/                 # Triage submodules (types, artifacts, output)
├── services/
│   └── triage_service.py       # Triage bundle generation
└── data/
    ├── config/
    │   ├── defaults.yaml
    │   ├── registry.json
    │   └── optional/ai-loop.yaml   # NEW: Safety policy (proposed)
    └── schema/
        └── ci-hub-config.schema.json
```
