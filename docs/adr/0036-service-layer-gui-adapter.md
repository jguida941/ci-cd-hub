# ADR-0036: Service Layer APIs for GUI Integration

**Status**: Accepted  
**Date:** 2026-01-03  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-03  

## Context

The PyQt6 GUI must reuse the CLI logic without forking behavior. The CLI already
returns structured JSON, but direct subprocess calls can make in-process GUI
flows harder to test, debug, or reuse. We also want to avoid duplicating config
merge logic across command handlers and future GUI workflows.

## Decision

Add a lightweight services layer that exposes GUI-friendly APIs for core
workflows, while keeping the CLI as the primary adapter.

### Principles

- Services return dataclasses and do not print or exit.
- CLI remains the integration surface and forwards to services when feasible.
- The GUI may call services directly (in-process) or call the CLI when running
  out-of-process; both paths must remain in sync.

### Initial Service Coverage

- CI execution wrapper (`cihub.services.ci`)
- Config load + edit helpers (`cihub.services.configuration`)
- Report summary rendering (`cihub.services.report_summary`)

## Consequences

**Positive:**
- Stable, testable API for GUI integration
- Less duplication of config and report logic
- Clear separation between execution logic and CLI output formatting

**Negative:**
- Must keep services and CLI adapters aligned
- Some commands may remain CLI-only until refactored

## Alternatives Considered

1. **GUI shells out to CLI for all actions**
   - Rejected as the only approach; subprocess-only integration is harder to
     test and limits in-process workflows.

2. **GUI reimplements business logic**
   - Rejected; violates the single-source-of-truth rule.

## References

- ADR-0032: PyQt6 GUI Wrapper for Full Automation
- ADR-0025: CLI Modular Restructure
- ADR-0029: CLI Exit Code Registry
- `cihub/services/`
