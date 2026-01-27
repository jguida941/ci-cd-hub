# ADR-0075: Java Tool Env, Timeouts, and Plugin Version Alignment

**Status**: Accepted  
**Date:** 2026-01-27  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-27  

## Context

Real-repo audits (notably `contact-suite-spring-react`) showed OWASP and PITest
timing out in the hub workflow while the repo’s own Java CI succeeded. The
root causes were:

- The hub Java workflow did not export `NVD_API_KEY` to `cihub`, so OWASP ran
  without NVD data and often timed out.
- PITest runs exceeded the default subprocess timeout (600s), but the CLI
  ignored the existing `pitest.timeout_multiplier` setting.
- The CLI pinned OWASP/PITest plugin versions even when the repo’s POM
  declared newer versions, creating version drift.

These are CLI/workflow contract gaps, not repo-specific issues.

## Decision

1. **Propagate `NVD_API_KEY`** into the hub Java workflow environment so the
   CLI can use the key when configured.
2. **Make OWASP timeout configurable** via schema key
   `java.tools.owasp.timeout_seconds` (default 1800).
3. **Honor PITest timeout multiplier** by deriving timeout from
   `pitest.timeout_multiplier` (default 2) against the base build timeout.
4. **Honor POM plugin versions** when the Maven plugin is declared; fall back
   to pinned defaults only when no plugin is found.

## Consequences

### Positive

- OWASP runs with NVD data when secrets are present, reducing timeouts.
- PITest runs have consistent, configurable timeouts.
- CLI aligns with repo-defined plugin versions, improving compatibility.

### Negative

- Adds a new schema field for OWASP timeouts (requires regeneration of docs).
- Timeout behavior changes for PITest (now respects `timeout_multiplier`).

## Alternatives Considered

1. **Ignore repo plugin versions and pin tool versions globally.**  
   Rejected: breaks compatibility for repos that already specify versions.
2. **Add repo-specific workflow overrides.**  
   Rejected: violates the no-hardcoding rule and CLI-first contract.
3. **Skip OWASP/PITest on timeout.**  
   Rejected: masks real failures; audits need evidence.
