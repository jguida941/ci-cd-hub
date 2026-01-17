# ADR-0057: Test Metrics Automation via hub-ci

**Status:** Accepted  
**Date:** 2026-01-17  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-17  

## Context

The Test Reorganization plan introduced automation scripts to update per-test
metrics, generate `tests/README.md`, and detect drift. These scripts must be
run consistently in CI without embedding workflow logic or duplicating behavior
outside the CLI.

## Decision

Add a new CLI subcommand, `cihub hub-ci test-metrics`, that wraps the existing
test-metrics scripts and performs any required preparation (e.g., coverage JSON
generation). Workflows will call this command instead of running scripts
directly, keeping YAML thin and CLI-driven.

Key behaviors:
- `--write` updates TEST-METRICS blocks and `tests/README.md` when allowed.
- In CI, writes are allowed on `main` only (unless `--allow-non-main` is set).
- Without `--write`, the command checks README drift and reports warnings.
- README drift checks ignore the `Last updated` timestamp line to avoid false positives.
- Drift checks can be made strict via `--strict`.
- CI runs the command after mutation tests so both coverage and mutmut inputs are available.

## Consequences

Positive:
- Centralizes test-metrics logic in the CLI and preserves the "no YAML logic"
  rule.
- Provides a consistent CI entry point with `--json` support and structured
  output.
- Enforces safe write behavior for main-only updates.

Negative:
- Adds another hub-ci subcommand and requires new tests/docs regeneration.

## Alternatives Considered

1. **Run scripts directly from workflows**
   - Rejected: violates the CLI-first rule and duplicates logic in YAML.
2. **Add script-specific workflow steps with conditionals**
   - Rejected: pushes behavior into workflows instead of the CLI.
