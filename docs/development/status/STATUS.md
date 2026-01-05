# CI/CD Hub Development Status

> **Single source of truth** for project status and active work.
>
> **Action Items:** See [MASTER_PLAN.md](../MASTER_PLAN.md) for all tasks.
> **Architecture:** See [ARCH_OVERVIEW.md](../architecture/ARCH_OVERVIEW.md)
>
> **Last Updated:** 2026-01-05
> **Version Target:** v1.0.0

---

## Active Design Docs

> This is the **single source** listing in-flight design docs. Files live in `development/active/`.
> When complete, move to `archive/` with a superseded header.

| Design Doc | Purpose | Status |
|------------|---------|--------|
| [CLEAN_CODE.md](../active/CLEAN_CODE.md) | Architecture improvements (polymorphism, encapsulation) | 📋 Designed |
| [DOC_AUTOMATION_AUDIT.md](../active/DOC_AUTOMATION_AUDIT.md) | `cihub docs stale` command design | 📋 Designed |
| [PYQT_PLAN.md](../active/PYQT_PLAN.md) | PyQt6 GUI wrapper design | 📋 Reference |

---

## Current Focus

1. **Documentation automation** — Implement `cihub docs stale` to detect stale references
2. **Architecture improvements** — LanguageStrategy pattern to eliminate 38+ `if language ==` branches
3. **CLI modularization** — Complete Phase 6-7 (parser extraction, config loader)

---

## Documentation Health

| Category    | Files  | Lines       | Health               |
|-------------|--------|-------------|----------------------|
| Guides      | 8      | 2,304       | ✅ Good               |
| References  | 3      | 2,590       | ✅ Generated          |
| ADRs        | 37     | 4,337       | ✅ Excellent (9.3/10) |
| Development | 39     | 17,699      | ✅ Organized          |
| Archive     | 21     | 7,656       | ✅ Separated          |
| **Total**   | **87** | **~30,430** | —                    |

### Recent Fixes (2026-01-05)

- ✅ Fixed `pytest.threshold` → `min_coverage` in CLI_EXAMPLES.md
- ✅ Fixed `nvd_api_key_required` → `use_nvd_api_key` in TOOLS.md
- ✅ Fixed broken smoke test link in ARCH_OVERVIEW.md
- ✅ Added quick reference header to CLI_EXAMPLES.md
- ✅ Created `development/active/` folder for design docs (CLEAN_CODE, DOC_AUTOMATION_AUDIT, PYQT_PLAN)
- ✅ Archived Jan3.md (CLI modularization plan, executed)
- ✅ Consolidated P0/P1/nonfunctional into `development/specs/REQUIREMENTS.md`
- ✅ Marked `development/research/RESEARCH_LOG.md` as historical reference

### Pending (See MASTER_PLAN.md)

- Add superseded banners to archive files → MASTER_PLAN.md §4
- Generate TOOLS.md from code/schema → MASTER_PLAN.md §3
- Implement `cihub docs stale` → MASTER_PLAN.md §6

---

## ADR Status

- **Total:** 37 ADRs (0001-0037)
- **Health Score:** 9.3/10
- **Accepted:** 35 (including ADR-0035 accepted 2026-01-04)
- **Proposed:** 2 (ADR-0005, ADR-0026)
- **Superseded:** 1 (ADR-0013 → ADR-0014)

### ADRs Needing Review

| ADR      | Issue                                      | Action            |
|----------|--------------------------------------------|-------------------|
| ADR-0005 | Dashboard still "Proposed" after 2+ weeks  | Clarify or accept |

---

## Verification Status

| Check | Last Run | Result |
|-------|----------|--------|
| `pytest` | 2026-01-04 | ✅ 1660 passed, 1 skipped |
| `ruff check` | 2026-01-04 | ✅ Clean |
| `cihub smoke --full` | 2025-12-30 | ✅ Passed |
| `cihub docs check` | 2026-01-04 | ✅ Up to date |
| `cihub docs links` | 2026-01-04 | ✅ No broken links |

---

## Directory Structure

```
docs/
├── README.md                    # Doc index
├── guides/                      # User-facing (narrative)
├── reference/                   # Generated: CLI.md, CONFIG.md; Manual: TOOLS.md; Planned: WORKFLOWS.md
├── adr/                         # Architecture decisions (37 files)
└── development/
    ├── MASTER_PLAN.md           # THE plan (all action items)
    ├── BACKLOG.md               # Work queue
    ├── CHANGELOG.md             # Change history
    ├── DEVELOPMENT.md           # Quick reference
    ├── CI_PARITY.md             # Local vs CI check parity map
    ├── active/                  # In-flight design docs (listed below)
    │   ├── CLEAN_CODE.md
    │   ├── DOC_AUTOMATION_AUDIT.md
    │   └── PYQT_PLAN.md
    ├── specs/                   # Consolidated requirements (REQUIREMENTS.md)
    ├── research/                # Historical research log
    ├── architecture/            # System design
    ├── status/STATUS.md         # Lists active docs (this file)
    └── archive/                 # Superseded docs
```

---

## Scope Guardrails

1. **No deletions** — Archive superseded docs, don't delete
2. **CLI is authoritative** — Docs describe CLI behavior, not replace it
3. **Single plan** — All action items in MASTER_PLAN.md
4. **Fixtures for CI** — Local dev uses `cihub scaffold` + `cihub smoke`

---

*Last updated: 2026-01-05*
