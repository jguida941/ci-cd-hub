# ADR-0058: Python CLI AI Enhancement Module

**Status:** Accepted  
**Date:** 2026-01-18  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-18  

## Context

The TypeScript CLI must stay thin and treat the Python CLI as the headless API. We
need AI assistance for triage, check, and report outputs without duplicating logic
in TypeScript or workflows. AI must remain optional, avoid YAML logic, and preserve
clean JSON output for downstream consumers.

## Decision

Add a modular `cihub/ai/` package that provides optional AI enhancement for CLI
commands. The Python CLI owns AI logic; TypeScript simply passes `--ai` when it
wants enhanced output.

Key behaviors:
- `cihub/ai` provides `claude_client`, `context`, and `enhance_result`.
- `--ai` opt-in on `triage`, `check`, and `report` adds AI analysis to results.
- `CIHUB_AI_PROVIDER` selects provider (default: `claude`), with graceful fallback.
- `CIHUB_DEV_MODE` can auto-run AI on failures for local debugging.
- No workflow changes; AI is optional and non-blocking.

## Consequences

Positive:
- AI logic stays in the Python CLI, consistent with CLI-first architecture.
- TypeScript CLI gains AI enhancement by passing `--ai`, without new AI code.
- AI remains optional; missing CLI yields a structured suggestion instead of failure.

Negative:
- New module, flags, and environment variables add surface area to test and document.
- AI enhancements depend on external tooling (Claude CLI) when enabled.

## Alternatives Considered

1. **TypeScript-only AI integration**
   - Rejected: duplicates logic across clients and violates CLI-first rule.
2. **Workflow-level AI logic**
   - Rejected: pushes behavior into YAML, against architecture policy.
3. **Mandatory AI provider/API keys**
   - Rejected: AI must remain optional and local-first.
