# ADR-0055: CLI Workflow Dispatch Watch + Wizard Wrapper

**Status:** Implemented  
**Date:** 2026-01-17  
**Supersedes:** None

## Context

The hub can already dispatch workflows via `cihub dispatch trigger`, but there is no
CLI-native way to watch a run to completion or to perform these actions through the
wizard. Users currently rely on workflow-only logic or external tooling to track
run status, which conflicts with the CLI-first architecture and the requirement to
keep logic out of YAML.

## Decision

Extend `cihub dispatch` with:

- `dispatch watch` to poll a workflow run until completion (by run ID or latest run).
- `dispatch trigger --watch` to optionally wait for completion after dispatch.
- Wizard wrappers for both actions that call the same command handlers.

All outputs continue to use `CommandResult` with `--json` support. The CLI uses the
GitHub API directly and standard token resolution (`get_github_token`).

## Consequences

### Positive
- CLI and wizard can dispatch and watch runs without workflow YAML logic.
- Output is consistent with the CommandResult contract for GUIs and automation.
- Watch behavior is reusable in automation and future frontends.

### Negative
- Adds polling and timeout concerns to the CLI surface (requires sensible defaults).
- Requires a token with `actions: write` on target repos to use dispatch features.

### Neutral
- No changes to workflow templates or dispatch input contracts.

## Implementation

- Add `dispatch watch` and `dispatch trigger --watch` to CLI parsers.
- Implement GH API polling helpers in `cihub/commands/dispatch.py`.
- Add wizard flows for trigger/watch using `questionary`.
- Update tests and CLI references via `cihub docs generate`.

## Alternatives Considered

1. **Keep watch logic in workflows** - Rejected; violates CLI-first rule.
2. **Require external tooling (gh, API scripts)** - Rejected; not portable or testable.
3. **Add new top-level command** - Rejected; `dispatch` already owns workflow dispatch.

## References

- [ADR-0003: Dispatch and Orchestration](0003-dispatch-orchestration.md)
- [ADR-0010: Dispatch Token and Skip Flag](0010-dispatch-token-and-skip.md)
- [ADR-0011: Dispatchable Workflow Requirement](0011-dispatchable-workflow-requirement.md)
- [ADR-0024: Workflow Dispatch Input Limit](0024-workflow-dispatch-input-limit.md)
- [ADR-0031: CLI-Driven Workflow Execution](0031-cli-driven-workflow-execution.md)
