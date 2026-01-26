# CI/CD Hub Development Status

**Status:** reference  
**Owner:** Development Team  
**Source-of-truth:** manual  
**Last-reviewed:** 2026-01-26  

> **Status snapshot** for active docs only. The authoritative plan is [MASTER_PLAN.md](../MASTER_PLAN.md).
> This file may be stale and will be audited later; it remains because automation scripts may reference it.
>
> **Action Items:** See [MASTER_PLAN.md](../MASTER_PLAN.md) for all tasks.
> **Architecture:** See [ARCH_OVERVIEW.md](../architecture/ARCH_OVERVIEW.md)
> **Test Counts:** Refresh via `cihub hub-ci test-metrics --write` after verified pytest+coverage (no manual edits).
>
> **Last Updated:** 2026-01-26 (Real repo audit progressed; java-spring-tutorials failing checkstyle/owasp with missing evidence)  
> **Version Target:** v1.0.0
>
> **Current focus:** TYPESCRIPT_CLI_DESIGN (Phase 8 AI enhancement), tool audit execution, and architecture audit.

---

## Active Design Docs

> This is the **single source** listing in-flight design docs. Files live in `development/active/`.
> When complete, move to `archive/` with a superseded header.

| Design Doc | Purpose | Status |
|------------|---------|--------|
| [TYPESCRIPT_CLI_DESIGN.md](../active/TYPESCRIPT_CLI_DESIGN.md) | TypeScript CLI wrapper design | See MASTER_PLAN |
| [AI_CI_LOOP_PROPOSAL.md](../active/AI_CI_LOOP_PROPOSAL.md) | Autonomous AI CI loop proposal | See MASTER_PLAN |
| [PYQT_PLAN.md](../active/PYQT_PLAN.md) | PyQt6 GUI wrapper design | See MASTER_PLAN |

---

## Recently Archived

- [CLI_WIZARD_SYNC_AUDIT.md](../archive/CLI_WIZARD_SYNC_AUDIT.md) - CLI/wizard/schema/TS alignment audit (archived 2026-01-19)
- [TEST_REORGANIZATION.md](../archive/TEST_REORGANIZATION.md) - Test suite restructuring (archived 2026-01-17)
- [DOC_AUTOMATION_AUDIT.md](../archive/DOC_AUTOMATION_AUDIT.md) - Doc automation design (archived 2026-01-17)
- [CLEAN_CODE.md](../archive/CLEAN_CODE.md) - Architecture improvements (archived)
- [remediation.md](../archive/remediation.md) - Operational intake log (archived)

## Parallel Workstreams (Internal)

These are active but **not** part of the priority order. See [MASTER_PLAN.md](../MASTER_PLAN.md) for coordination rules.

- None currently

---

## Status References

- [MASTER_PLAN.md](../MASTER_PLAN.md) - priorities, scope, sequencing, and decisions
- [CHANGELOG.md](../CHANGELOG.md) - user-facing change history
