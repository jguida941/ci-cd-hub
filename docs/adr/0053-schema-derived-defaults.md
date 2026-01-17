# ADR-0053: Schema-Derived Defaults and Fallbacks

**Status:** Implemented
**Date:** 2026-01-15
**Supersedes:** None

## Context

The config defaults were defined in multiple places:

- Schema defaults in `cihub/data/schema/ci-hub-config.schema.json`
- `cihub/data/config/defaults.yaml` (human-editable defaults)
- `cihub/config/fallbacks.py` (runtime fallback when defaults.yaml is missing)

This duplication made drift likely. Manual edits to defaults.yaml or fallbacks.py could diverge
from the schema, and schema changes could silently fail to propagate.

Optional feature blocks (chaos, canary, etc.) further increased drift risk because they had
non-schema placeholder fields in defaults.yaml, which were not validated by the schema.

## Decision

1. **Schema is the single source of truth** for default values.
2. `defaults.yaml` is generated from the schema.
3. `fallbacks.py` is generated from the same schema-derived defaults.
4. `cihub check --audit` validates both defaults.yaml and fallbacks.py against the schema.
5. **Optional feature defaults remain minimal** (only `enabled` from schema) until full
   optional feature schemas are implemented. Extended examples live in
   `cihub/data/config/optional/` and are not merged into defaults.yaml.

## Consequences

### Positive
- Eliminates drift between schema, defaults.yaml, and fallbacks.py.
- Makes default updates traceable and testable.
- Ensures runtime fallback behavior mirrors schema defaults.

### Negative
- Manual edits to defaults.yaml or fallbacks.py must be avoided; change the schema instead.
- Optional feature placeholder fields are removed from defaults.yaml until schemas exist.

### Neutral
- No CLI surface changes; schema-sync remains internal.
- Defaults generation is deterministic and repeatable.

## Implementation

- `cihub/config/schema_extract.py` extracts defaults from schema.
- `cihub/commands/schema_sync.py` generates defaults.yaml and fallbacks.py.
- `cihub/commands/check.py` enforces schema alignment in `--audit` mode.

## References

- [ADR-0002: Config Precedence Hierarchy](0002-config-precedence.md)
- [ADR-0047: Config Validation Order](0047-config-validation-order.md)
- [CLEAN_CODE.md Part 9.3.2](../development/archive/CLEAN_CODE.md#finding-932-triple-default-definition)
