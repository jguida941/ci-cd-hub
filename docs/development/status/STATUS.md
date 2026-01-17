# CI/CD Hub Development Status

**Status:** reference  
**Owner:** Development Team  
**Source-of-truth:** manual  
**Last-reviewed:** 2026-01-15  

> **Status snapshot** for active docs only. The authoritative plan is [MASTER_PLAN.md](../MASTER_PLAN.md).
> This file may be stale and will be audited later; it remains because automation scripts may reference it.
>
> **Action Items:** See [MASTER_PLAN.md](../MASTER_PLAN.md) for all tasks.
> **Architecture:** See [ARCH_OVERVIEW.md](../architecture/ARCH_OVERVIEW.md)
> **Test Counts:** Paused in docs; owner will refresh after a verified full run.
>
> **Last Updated:** 2026-01-15 (status index trimmed, pointers only)
> **Version Target:** v1.0.0
>
> **Current focus:** Wizard/CLI validation complete; proceed with Test Reorg CI workflow wiring + Phase 4 property tests + Phase 5 docs.

---

## Active Design Docs

> This is the **single source** listing in-flight design docs. Files live in `development/active/`.
> When complete, move to `archive/` with a superseded header.

| Design Doc | Purpose | Status |
|------------|---------|--------|
| [TEST_REORGANIZATION.md](../active/TEST_REORGANIZATION.md) | Test suite restructuring plan | See MASTER_PLAN |
| [DOC_AUTOMATION_AUDIT.md](../active/DOC_AUTOMATION_AUDIT.md) | `docs stale` + `docs audit` commands | See MASTER_PLAN |
| [TYPESCRIPT_CLI_DESIGN.md](../active/TYPESCRIPT_CLI_DESIGN.md) | TypeScript CLI wrapper design | See MASTER_PLAN |
| [PYQT_PLAN.md](../active/PYQT_PLAN.md) | PyQt6 GUI wrapper design | See MASTER_PLAN |

---

## Recently Archived

- [CLEAN_CODE.md](../archive/CLEAN_CODE.md) - Architecture improvements (archived)
- [remediation.md](../archive/remediation.md) - Operational intake log (archived)

## Parallel Workstreams (Internal)

These are active but **not** part of the priority order. See [MASTER_PLAN.md](../MASTER_PLAN.md) for coordination rules.

- [AI_CI_LOOP_PROPOSAL.md](../AI_CI_LOOP_PROPOSAL.md) - Internal AI loop proposal (experimental, internal-only)

---

## Status References

- [MASTER_PLAN.md](../MASTER_PLAN.md) - priorities, scope, sequencing, and decisions
- [CHANGELOG.md](../CHANGELOG.md) - user-facing change history
