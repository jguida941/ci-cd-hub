# Comprehensive System Audit Report
> **Superseded by:** [MASTER_PLAN.md](../MASTER_PLAN.md)  

> **WARNING: SUPERSEDED:** This document has been consolidated into `docs/development/archive/SYSTEM_INTEGRATION_PLAN.md` (2026-01-08)

**Status:** ARCHIVED  
**Date:** 2026-01-08  
**Audited By:** 5 Parallel Agents

## Executive Summary

A comprehensive multi-agent audit of CLI, Schema, Wizard, Workflows, and User Journeys reveals:

| Component | Status | Score | Critical Issues |
|-----------|--------|-------|-----------------|
| CLI Commands | [x] Excellent | 10/10 | None - 83 commands, 100% compliant |
| Schema | WARNING: Needs Work | 6/10 | 24% unused fields, field mismatches |
| Wizard | [ ] Incomplete | 3/10 | Only 12% of CLI covered |
| Workflows | WARNING: Mostly Good | 8/10 | 3 hardcoded tools in hub-production-ci |
| User Journeys | WARNING: Mixed | 5/10 | Migration tooling missing |

---

## FINDINGS BY AGENT

### Agent 1: CLI Commands Audit [x]

**Result:** FULLY COMPLIANT

| Metric | Value |
|--------|-------|
| Total Commands | 83 |
| --json Support | 100% |
| CommandResult Returns | 100% |
| Critical Gaps | 0 |

**No action required** - CLI architecture is excellent.

---

### Agent 2: Schema vs Config Audit WARNING:

**Result:** 24% OF SCHEMA FIELDS ARE UNUSED

#### HIGH Priority Issues

| Issue | Location | Impact |
|-------|----------|--------|
| `mutmut.min_score` vs `min_mutation_score` | Schema line 501, inputs.py:93 | User configs ignored |
| Missing `cihub.*` block | Schema (missing) | Debug toggles not validated |
| `pytest.fail_fast` missing | Schema (missing) | Field undocumented |

#### Unused Feature Toggles (can remove)
- `cache_sentinel`, `canary`, `chaos`, `dr_drill`
- `egress_control`, `runner_isolation`, `supply_chain`
- `telemetry`, `kyverno` (partially)

#### Action Items
1. Rename `min_score` → `min_mutation_score` in schema
2. Add `cihub.*` block to schema or remove code references
3. Add `pytest.fail_fast` field
4. Mark unused toggles as "reserved for future" or remove

---

### Agent 3: Wizard vs CLI Audit [ ]

**Result:** ONLY 4/33 COMMANDS (12%) HAVE WIZARD SUPPORT

#### Commands WITH Wizard
- `cihub setup` [x]
- `cihub init --wizard` [x]
- `cihub new --interactive` [x]
- `cihub config edit` [x]

#### Critical Gaps (Need Wizard)

| Command | Gap | Priority |
|---------|-----|----------|
| `setup-secrets` | No PAT/NVD guidance | HIGH |
| `triage` | 20+ flags, overwhelming | HIGH |
| `check` | Tier selection confusing | HIGH |
| `config enable/disable` | No tool discovery | MEDIUM |
| `config apply-profile` | Profiles undiscoverable | MEDIUM |
| `fix` | Safe vs report modes unclear | MEDIUM |

#### Action Items
1. Add profile selection to wizard (BEFORE tool checkboxes)
2. Create `--interactive` for `setup-secrets`, `triage`, `check`
3. Add tool browser to `config enable --interactive`
4. Create profile previewer for `apply-profile`

---

### Agent 4: Workflows vs CLI Audit WARNING:

**Result:** 3/4 WORKFLOWS COMPLIANT, 1 PARTIALLY NON-COMPLIANT

#### Compliant Workflows
- `python-ci.yml` [x]
- `java-ci.yml` [x]
- `hub-ci.yml` [x]

#### Non-Compliant: hub-production-ci.yml

| Line | Issue | CLI Alternative |
|------|-------|-----------------|
| 325 | Raw `ruff format --check` | Should use `cihub hub-ci ruff --check-format` |
| 391 | Raw `mypy cihub/` | **Missing:** `cihub hub-ci mypy` |
| 419 | Raw `yamllint` | **Missing:** `cihub hub-ci yamllint` |

#### Action Items
1. Create `cihub hub-ci mypy` command
2. Create `cihub hub-ci yamllint` command
3. Replace raw calls in hub-production-ci.yml with CLI wrappers
4. Move tool version pins to pyproject.toml

---

### Agent 5: User Journey Audit WARNING:

**Result:** MIXED - MIGRATION TOOLING WORST GAP

| Journey | Score | Status |
|---------|-------|--------|
| New User Onboarding | 6/10 | Wizard incomplete |
| **Existing Repo Migration** | **3/10** | **No tooling exists** |
| Day-to-Day Usage | 7/10 | Good but triage hard to discover |
| Configuration Changes | 6/10 | No config diff/preview |
| Troubleshooting | 7/10 | No diagnostic bundle |

#### Critical Missing Features

1. **Migration Assessment** - No `cihub migrate --from jenkins/github-actions`
2. **Config Diff** - No `cihub config diff --profile <name>`
3. **Diagnostic Bundle** - No `cihub doctor --collect-bundle`
4. **Setup Wizard** - `cihub setup` is skeletal, needs completion

#### Action Items
1. Complete `cihub setup` wizard flow
2. Build migration assessment tool
3. Add config diff/preview before apply
4. Create diagnostic bundle command

---

## PRIORITY ACTION MATRIX

### HIGH Priority (Do First)

| # | Issue | Component | Effort | Files |
|---|-------|-----------|--------|-------|
| 1 | Complete setup wizard with profiles | Wizard | Medium | `setup.py`, `wizard/core.py` |
| 2 | Create `hub-ci mypy` command | CLI | Low | `hub_ci/python_tools.py` |
| 3 | Create `hub-ci yamllint` command | CLI | Low | `hub_ci/validation.py` |
| 4 | Fix `min_score` → `min_mutation_score` | Schema | Low | `schema/*.json` |
| 5 | Remove hardcoded tools from hub-production-ci | Workflow | Low | `.github/workflows/` |
| 6 | Add secrets setup wizard | Wizard | Medium | `wizard/questions/secrets.py` |

### MEDIUM Priority (Do Next)

| # | Issue | Component | Effort |
|---|-------|-----------|--------|
| 7 | Add profile selection to wizard | Wizard | Medium |
| 8 | Create triage --interactive | Wizard | Medium |
| 9 | Create check --interactive (tier selector) | Wizard | Low |
| 10 | Add config diff before apply | CLI | Medium |
| 11 | Remove unused schema toggles | Schema | Low |
| 12 | Create migration assessment tool | CLI | High |

### LOW Priority (Do Later)

| # | Issue | Component | Effort |
|---|-------|-----------|--------|
| 13 | Add diagnostic bundle command | CLI | Medium |
| 14 | Create tool browser for config enable | Wizard | Medium |
| 15 | Add AI-friendly triage format | CLI | Low |
| 16 | Generate flowchart decision trees | Docs | Medium |

---

## QUICK WINS (< 1 hour each)

1. Add `min_mutation_score` to schema, deprecate `min_score`
2. Add `pytest.fail_fast` to schema
3. Add inline comments to scaffold output files
4. Document all `CIHUB_*` env toggles in one place
5. Add "See Also" to command help text

---

## RELATED DOCS

- `docs/adr/0051-wizard-profile-first-design.md` - Wizard enhancement ADR
- `docs/development/active/WIZARD_IMPROVEMENTS.md` - Detailed wizard plan
- `docs/development/MASTER_PLAN.md` - Overall priority tracking

---

## APPENDIX: Agent Outputs

Full agent outputs stored at:
- `/tmp/claude/.../tasks/a7cf897.output` (CLI audit)
- `/tmp/claude/.../tasks/a953d42.output` (Schema audit)
- `/tmp/claude/.../tasks/a180a7d.output` (Wizard audit)
- `/tmp/claude/.../tasks/a1b0291.output` (Workflow audit)
- `/tmp/claude/.../tasks/a314f68.output` (User journey audit)
