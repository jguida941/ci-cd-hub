# CI/CD Hub Development Status

> **Single source of truth** for project status and active work.
>
> **Action Items:** See [MASTER_PLAN.md](../MASTER_PLAN.md) for all tasks.
> **Architecture:** See [ARCH_OVERVIEW.md](../architecture/ARCH_OVERVIEW.md)
>
> **Last Updated:** 2026-01-09 (`docs audit` Part 13 checks implemented)
> **Version Target:** v1.0.0

---

## Active Design Docs

> This is the **single source** listing in-flight design docs. Files live in `development/active/`.
> When complete, move to `archive/` with a superseded header.

| Design Doc | Purpose | Status |
|------------|---------|--------|
| [CLEAN_CODE.md](../active/CLEAN_CODE.md) | Architecture improvements (polymorphism, encapsulation) | In Progress (~90%) |
| [SYSTEM_INTEGRATION_PLAN.md](../active/SYSTEM_INTEGRATION_PLAN.md) | Registry/wizard/schema integration | Active (Consolidated) |
| [TEST_REORGANIZATION.md](../active/TEST_REORGANIZATION.md) | Test suite restructuring plan | Planned (Audit Complete) |
| [DOC_AUTOMATION_AUDIT.md](../active/DOC_AUTOMATION_AUDIT.md) | `docs stale` + `docs audit` commands | In Progress (~80%) |
| [TYPESCRIPT_CLI_DESIGN.md](../active/TYPESCRIPT_CLI_DESIGN.md) | TypeScript CLI wrapper design | Planning |
| [PYQT_PLAN.md](../active/PYQT_PLAN.md) | PyQt6 GUI wrapper design | Reference |

---

## Current Focus

1. **CommandResult migration (CLEAN_CODE.md Phase 3)** - Migrate print() calls to CommandResult pattern
 - [x] 13 files migrated (~198 prints → CommandResult)
 - ~65 prints remaining in ~9 allowlisted files + report/ subpackage
2. **Test suite reorganization** - Plan complete, 5-agent audit identified ~10-12 days blockers
3. **Documentation automation** - `docs stale` [x] complete, `docs audit` mostly complete (~80%)
 - [x] `cihub docs stale` - 63 tests, modular package
 - [x] `cihub docs audit` - Core J/L/N + Part 13.S/T/V checks; 22 tests; missing Q headers, specs hygiene

---

## Documentation Health

| Category | Files | Lines | Health |
|-------------|--------|-------------|----------------------|
| Guides | 8 | 2,304 | [x] Good |
| References | 3 | 2,590 | [x] Generated |
| ADRs | 48 | 5,500+ | [x] Excellent (9.3/10) |
| Development | 39 | 17,699 | [x] Organized |
| Archive | 21 | 7,656 | [x] Separated |
| **Total** | **87** | **~30,430** | - |

### Recent Fixes (2026-01-05)

**CommandResult Migration (CLEAN_CODE.md Phase 3):**
- [x] detect.py - Pure CommandResult return (no conditional JSON mode)
- [x] validate.py - Added YAML parse error handling
- [x] smoke.py - Fixed TemporaryDirectory resource leak
- [x] discover.py - Reordered empty check before GITHUB_OUTPUT write
- [x] cli.py - Error output now routes to stderr (CLI best practice)

**Test Suite:**
- [x] Updated test patterns: `result.exit_code` instead of `result == int`
- [x] All 2120 tests passing

**Documentation:**
- [x] Created TEST_REORGANIZATION.md plan
- [x] Completed 5-agent parallel audit identifying ~10-12 days blockers
- [x] Fixed `pytest.threshold` → `min_coverage` in CLI_EXAMPLES.md
- [x] Fixed `nvd_api_key_required` → `use_nvd_api_key` in TOOLS.md
- [x] Fixed broken smoke test link in ARCH_OVERVIEW.md

### Pending (See MASTER_PLAN.md)

- Add superseded banners to archive files → MASTER_PLAN.md §4
- Generate TOOLS.md from code/schema → MASTER_PLAN.md §3
- Implement `cihub docs stale` → MASTER_PLAN.md §6

---

## ADR Status

- **Total:** 51 ADRs (0001-0029, 0031-0051)
- **Health Score:** 9.3/10
- **Accepted:** 47
- **Proposed:** 3 (ADR-0005, ADR-0026, ADR-0051)
- **Superseded:** 1 (ADR-0013 → ADR-0014)

### ADRs Needing Review

| ADR | Issue | Action |
|----------|--------------------------------------------|-------------------|
| ADR-0005 | Dashboard still "Proposed" after 2+ weeks | Clarify or accept |

---

## Verification Status

| Check | Last Run | Result |
|-------|----------|--------|
| `pytest` | 2026-01-06 | [x] 2120 passed |
| `ruff check` | 2026-01-05 | [x] Clean |
| `cihub smoke --full` | 2025-12-30 | [x] Passed |
| `cihub docs check` | 2026-01-05 | [x] Up to date |
| `cihub docs links` | 2026-01-05 | [x] No broken links |

---

## Directory Structure

```
docs/
├── README.md # Doc index
├── guides/ # User-facing (narrative)
├── reference/ # Generated: CLI.md, CONFIG.md; Manual: TOOLS.md; Planned: WORKFLOWS.md
├── adr/ # Architecture decisions (48 files)
└── development/
 ├── MASTER_PLAN.md # THE plan (all action items)
 ├── BACKLOG.md # Work queue
 ├── CHANGELOG.md # Change history
 ├── DEVELOPMENT.md # Quick reference
 ├── CI_PARITY.md # Local vs CI check parity map
 ├── active/ # In-flight design docs (listed below)
 │ ├── CLEAN_CODE.md
 │ ├── SYSTEM_INTEGRATION_PLAN.md
 │ ├── TEST_REORGANIZATION.md
 │ ├── DOC_AUTOMATION_AUDIT.md
 │ ├── TYPESCRIPT_CLI_DESIGN.md
 │ └── PYQT_PLAN.md
 ├── specs/ # Consolidated requirements (REQUIREMENTS.md)
 ├── research/ # Historical research log
 ├── architecture/ # System design
 ├── status/STATUS.md # Lists active docs (this file)
 └── archive/ # Superseded docs
```

---

## Scope Guardrails

1. **No deletions** - Archive superseded docs, don't delete
2. **CLI is authoritative** - Docs describe CLI behavior, not replace it
3. **Single plan** - All action items in MASTER_PLAN.md
4. **Fixtures for CI** - Local dev uses `cihub scaffold` + `cihub smoke`

---

*Last updated: 2026-01-09*
