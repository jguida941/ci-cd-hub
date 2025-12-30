# CI/CD Hub - Execution Plan

**Status:** Canonical plan for active work
**Last Updated:** 2025-12-30

---

## Purpose

Single source of truth for what we are doing now. Other docs can provide depth, but this file owns priorities, scope, and sequencing.

## Canonical Sources of Truth

1. **Code** (`cihub/`, `schema/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is the authoritative interface documentation.
3. **Schema** (`schema/ci-hub-config.schema.json`) is the authoritative config contract.
4. **AGENTS.md** defines operating rules for AI and contributors.

## References (Background Only)

- `pyqt/planqt.md` (PyQt concept scope)
- `docs/development/architecture/ARCHITECTURE_PLAN.md` (deep architecture notes)

These are references, not competing plans.

---

## Current Decisions

- **CLI is the execution engine**; workflows are thin wrappers.
- **Single entrypoint workflow is `hub-ci.yml`**; it routes to `python-ci.yml`/`java-ci.yml` internally.
- **Local verification uses CLI scaffolding + smoke**; fixtures repo is for CI/regression, not required for local tests.

---

## Near-Term Priorities (In Order)

### 1) Plan Consolidation (Immediate)

- Create this file as the canonical plan.
- Add reference banners to `pyqt/planqt.md` and `docs/development/architecture/ARCHITECTURE_PLAN.md` stating this plan is canonical.
- Create `AGENTS.md` and ensure `CLAUDE.md` points to it.

### 2) CLI as Source of Truth (Core)

- Implement and commit CLI helpers:
  - `cihub preflight` (doctor alias)
  - `cihub scaffold <type>`
  - `cihub smoke [--full]`
- Add CLI doc generation commands:
  - `cihub docs generate` -> `docs/reference/CLI.md` + `docs/reference/CONFIG.md`
  - `cihub docs check` for CI drift prevention
- Optional CLI utilities (later): `cihub status`, `cihub adr check`, `cihub adr list`

### 3) Documentation Cleanup (Controlled Sweep)

- Create `docs/README.md` as index of canonical vs reference vs archive.
- Merge overlapping guides into **one** user entry point:
  - Keep `docs/guides/GETTING_STARTED.md` as canonical.
  - Fold in DISPATCH_SETUP, MODES, MONOREPOS, TEMPLATES.
  - Keep `docs/guides/TROUBLESHOOTING.md` separate.
- Move legacy/duplicate docs to `docs/development/archive/` with a superseded header (no deletion).
- Make reference docs generated, not hand-written.

### 4) Staleness Audit (Doc + ADR)

- Run a full stale-reference audit (docs/ADRs/scripts/workflows).
- Record findings in a single audit ledger (`claude_audit.md` or `docs/development/AUDIT.md`).
- Update ADRs that reference old workflow entrypoints and fixture strategy.

### 5) Verification

- Run targeted pytest and record results in `docs/development/status/STATUS.md`.
- Run `cihub smoke --full` on scaffolded fixtures and capture results.
- Re-run the hub production workflows as needed after CLI changes.

---

## Documentation Consolidation Rules

- Do not duplicate CLI help text in markdown; generate it.
- Do not hand-write config field docs; generate from schema.
- If code and docs conflict, code wins and docs must be updated.

---

## Scope Guardrails

1. No large refactors (renames, src/ move, etc.) until workflow migration stabilizes.
2. No deleting docs; archive instead.
3. ADR alignment comes before cleanup decisions.
4. Fixtures repo stays for CI/regression; local dev uses scaffold/smoke.

---

## Open Questions

- Where should the long-term audit ledger live (root vs docs/development)?
- Which generated doc toolchain do we want (custom CLI, sphinx-click, or minimal generator)?
- Do we want a CI gate for ADR drift detection (warn vs fail)?

---

## Definition of Done (Near-Term)

- CLI helpers committed and passing tests.
- `docs/reference/CLI.md` and `docs/reference/CONFIG.md` generated from code.
- `docs/README.md` exists and clarifies doc hierarchy.
- Guides consolidated into a single entry point.
- ADRs updated to reflect `hub-ci.yml` wrapper and CLI-first execution.
- Smoke test and targeted pytest results recorded.
