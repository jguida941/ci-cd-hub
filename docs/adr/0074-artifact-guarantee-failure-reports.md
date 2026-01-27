# ADR-0074: Artifact Guarantees for Failure Reports

**Status**: Accepted  
**Date:** 2026-01-27  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-27  

## Context

Real-repo audits surfaced runs with zero downloadable artifacts. The most
common cause was missing `HUB_REPO`/`HUB_REF` vars, which resulted in the
reusable workflow failing before `cihub` could run. Separately, `cihub ci`
did not emit `report.json` when config loading or tool execution raised an
exception, leaving triage without a report even if the workflow ran.

We need an architecture-aligned path that always produces report artifacts
without adding business logic to YAML.

## Decision

1. **Workflow defaults:** Hub workflows and caller templates default
   `hub_repo`/`hub_ref` when inputs/vars are empty to ensure the CLI can be
   installed and executed.
2. **Failure reports:** `cihub ci` writes a minimal, schema-valid
   `report.json` (and summary) even on config load failures or tool execution
   exceptions so artifacts exist for triage/verification.

## Consequences

### Positive

- Artifacts are always available for `cihub triage --verify-tools`.
- Failure causes are represented in CLI problems while reports stay valid.
- Workflows remain thin wrappers; logic stays in the CLI.

### Negative

- Failure reports may lack tool evidence (expected for early failures).
- Forks must override defaults if they use a different hub repo/ref.

## Alternatives Considered

1. **Require repo vars and fail early.**  
   Rejected: still yields no artifacts, blocking audits.
2. **Add YAML fallback logic to generate reports.**  
   Rejected: violates the CLI-first rule.
3. **Switch templates to `@main`.**  
   Rejected: breaks release pin policy and stability expectations.
