# ADR-0037: Shorthand Enabled Sections + Threshold Profiles

**Status**: Accepted  
**Date:** 2026-01-03  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-03  

## Context

The config already supports shorthand booleans for tool toggles. We want the
same ergonomics for other `enabled`-driven sections (reports, notifications,
optional features) and a simple way to apply common threshold presets without
copying full numeric blocks.

## Decision

### 1) Shorthand booleans for enabled sections

Allow `boolean | object` for any section whose primary function is an
`enabled` toggle and optional defaults:

- `reports.github_summary`, `reports.codecov`, `reports.badges`
- `notifications.email`, `notifications.slack`
- `kyverno`
- Optional features: `chaos`, `canary`, `dr_drill`, `egress_control`,
  `cache_sentinel`, `runner_isolation`, `supply_chain`, `telemetry`
- `hub_ci` (only toggles `enabled`; tools/thresholds remain in the object form)

Shorthand `section: true` normalizes to `section: { enabled: true }` before
merging, so defaults remain intact.

### 2) Threshold presets

Add `thresholds_profile` with named presets:

- `coverage-gate` (coverage 90, mutation 80)
- `security` (max_critical 0, max_high 5)
- `compliance` (max_critical 0, max_high 0)

Explicit `thresholds.*` values override the preset.

## Consequences

**Positive:**
- Faster config authoring with less boilerplate
- Clear, repeatable threshold presets
- No behavior change unless the new fields are used

**Negative:**
- More schema surface (must keep docs and tests in sync)
- Presets require periodic review to stay aligned with profiles

## Alternatives Considered

1. **Allow booleans for all objects (including thresholds and language):**
   Rejected. It introduces ambiguity and conflicts with ADR-0006 (thresholds
   are required quality gates, not on/off toggles).

2. **Only use templates/profiles:**
   Rejected. Users still want a quick knob for thresholds without full profile
   merges.

## References

- ADR-0006: Quality Gates and Thresholds
- ADR-0032: PyQt6 GUI Wrapper for Full Automation
