# ADR-0056: Docs Audit Inventory and Guide Command Validation

**Status:** Implemented  
**Date:** 2026-01-17  
**Supersedes:** None

## Context

`cihub docs audit` already enforces lifecycle, headers, references, and
consistency checks, but it lacks two pieces needed to keep documentation
accurate without manual churn:

- A deterministic inventory of docs counts (for STATUS.md and audit reporting)
- Validation that `cihub ...` commands shown in guides still match the CLI

We also need to avoid false positives from the plain-text `docs/...` scanner
when `docs/` appears inside unrelated paths (for example, `tests/unit/docs/...`).

## Decision

Extend `cihub docs audit` with the following:

- Add `--inventory` to include doc inventory counts in JSON output.
- Add guide command validation for `docs/guides/*.md` and report unknown CLI
  commands as warnings (skipped when `--skip-consistency` is used).
- Filter false-positive `docs/...` matches that are embedded in other paths.

All changes preserve the CLI-first architecture and keep logic inside the CLI
instead of workflows or ad-hoc scripts.

## Consequences

### Positive
- Inventory data can be generated on demand without editing docs by hand.
- Guides stay aligned with the CLI surface and regressions are caught early.
- Fewer false positives from the docs reference scanner.

### Negative
- Adds a small amount of CLI surface area (`--inventory`).
- Guide validation may require occasional tuning for edge-case snippets.

### Neutral
- No workflow changes and no schema changes.

## Implementation

- `cihub docs audit --inventory` computes inventory counts for JSON output.
- `docs/guides/` snippets are scanned for `cihub` invocations and validated
  against the argparse command tree.
- Reference scanning skips `docs/` substrings embedded in other paths.
- Tests added for inventory counts, guide validation, and reference filtering.

## Alternatives Considered

1. **External inventory script** - Rejected; inventory belongs in the CLI
   alongside `docs audit` and should share output contracts.
2. **Guide validation only in docs stale** - Rejected; `docs audit` is the
   lifecycle gate and should own guide checks.
3. **Keep `docs/...` regex broad** - Rejected; false positives reduce signal.

## References

- [DOC_AUTOMATION_AUDIT.md](../development/active/DOC_AUTOMATION_AUDIT.md)
- [ADR-0048: Documentation Automation Strategy](0048-documentation-automation-strategy.md)
