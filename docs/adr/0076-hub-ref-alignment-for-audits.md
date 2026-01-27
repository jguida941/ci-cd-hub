# ADR-0076: Align hub_ref Fallback with hub_workflow_ref in Generated Workflows

**Status**: Accepted  
**Date:** 2026-01-27  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-27  

## Context

Audit runs pin the reusable workflow via `repo.hub_workflow_ref` /
`--hub-workflow-ref` so the caller workflow uses an audit branch. The generated
`hub-ci.yml` still defaulted `hub_ref` to `v1` when `HUB_REF` was unset, which
caused the hub workflow to install the CLI from the release tag even though the
workflow itself came from an audit ref. This version mismatch hides in audits,
making it look like the CLI is “old” even when the workflow ref is new.

## Decision

When rendering `hub-ci.yml` with a `hub_workflow_ref` override, the CLI also
updates the `hub_ref` fallback in the generated caller workflow to the same
ref. The `vars.HUB_REF` override still takes precedence when explicitly set.

## Consequences

### Positive

- Audit branches automatically install the matching CLI ref without requiring
  manual repo variable updates.
- Workflow/CLI alignment is enforced by generation, reducing false failures.

### Negative

- If a user wants a different CLI ref than the workflow ref, they must set
  `HUB_REF` explicitly.

## Alternatives Considered

1. **Require users to set HUB_REF manually for every audit.**  
   Rejected: too error-prone and causes repeated version drift.
2. **Default hub_ref to main everywhere.**  
   Rejected: unstable for production and violates the release policy.
3. **Always set hub_ref to hub_workflow_ref even when HUB_REF is set.**  
   Rejected: would ignore intentional overrides.
