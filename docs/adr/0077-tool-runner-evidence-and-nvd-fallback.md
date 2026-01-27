# ADR-0077: Tool Runner Evidence and NVD Fallback Defaults

**Status**: Accepted  
**Date:** 2026-01-27  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-27  

## Context

Audit runs showed tools executing but failing verification because required
reports were missing even though log evidence existed. OWASP Dependency-Check
also failed without an NVD key because the CLI disabled NVD/CPE analyzers by
default, leading to fatal analysis errors in some repos. pip-audit scanned the
installed environment when no requirements were provided, producing false
failures in otherwise clean test repos.

These are CLI/tooling defaults, not repo-specific issues.

## Decision

1. **OWASP NVD without key:** When no NVD API key is present, the CLI will
   still attempt a full NVD run (slower) and only fall back to a reduced
   analyzer set if the output indicates explicit NVD access errors (403/404/429
   or key-required messages). Timeouts are increased for no-key runs.
2. **pip-audit project scope:** pip-audit now audits the project itself
   (requirements files if present, otherwise the project path) rather than the
   ambient environment.
3. **Tool evidence from logs:** Tool evidence should be considered present when
   logs or artifacts exist even if a report file is missing. Tool results now
   include log artifacts, and report evidence derivation no longer short-circuits
   on `report_found=false`.

## Consequences

### Positive

- OWASP can run without an NVD key (slower but functional).
- pip-audit no longer flags vulnerabilities from the global environment.
- Verification distinguishes “tool failed” from “tool ran with no proof.”

### Negative

- OWASP runs may take longer when no key is present.
- Log artifacts are now counted as evidence (reports are still required for
  success, but not for proof of execution).

## Alternatives Considered

1. **Disable OWASP when no NVD key.**  
   Rejected: audits must still provide evidence even without a key.
2. **Require requirements.txt for pip-audit.**  
   Rejected: pyproject/poetry projects would fail without extra files.
3. **Treat missing reports as “no proof” even with logs.**  
   Rejected: logs are valid evidence of execution; failures should be
   attributed to tool outcomes, not lack of proof.
