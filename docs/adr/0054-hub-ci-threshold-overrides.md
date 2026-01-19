# ADR-0054: Hub CI Threshold Overrides

**Status:** Implemented  
**Date:** 2026-01-15  
**Supersedes:** None

## Context

The test reorganization plan needs per-module threshold targets for coverage and mutation
metrics so drift tooling can record and validate expectations per module. The hub CI
configuration lives in `hub_ci.thresholds`, but the schema currently sets
`additionalProperties: false`, which blocks any map of per-module overrides.

## Decision

Add `hub_ci.thresholds.overrides` as a map of module identifiers to per-module threshold
settings. Each entry supports:

- `coverage_min` (integer 0-100)
- `mutation_score_min` (integer 0-100)
- `note` (string)

The overrides map defaults to an empty object.

## Consequences

### Positive
- Allows per-module threshold targets to be recorded in config without schema violations.
- Keeps per-module expectations centralized under hub CI thresholds.
- Enables drift tooling to reference schema-defined keys only.

### Negative
- Adds another config surface area that must stay aligned with schema-derived defaults.

### Neutral
- No CLI surface changes.
- No workflow changes.

## Implementation

- Update `cihub/data/schema/ci-hub-config.schema.json` to add
  `hub_ci.thresholds.overrides`.
- Regenerate `cihub/data/config/defaults.yaml` and `cihub/config/fallbacks.py`.
- Add regression coverage in `tests/test_schema_sync.py`.

## References

- [TEST_REORGANIZATION.md](../development/archive/TEST_REORGANIZATION.md)
- [ADR-0053: Schema-Derived Defaults and Fallbacks](0053-schema-derived-defaults.md)
