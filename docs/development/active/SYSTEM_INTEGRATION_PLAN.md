# System Integration Plan

**Status:** ACTIVE - Canonical Integration Plan
**Date:** 2026-01-08
**Owner:** Development Team
**Consolidates:** COMPREHENSIVE_SYSTEM_AUDIT.md, WIZARD_IMPROVEMENTS.md, REGISTRY_AUDIT_AND_PLAN.md

---

## Executive Summary

This document consolidates findings from multiple audits (5-agent system audit, 8-agent registry audit, wizard analysis, final 5-agent verification audit on 2026-01-08) into a single actionable roadmap with comprehensive testing requirements.

### Overall System Health (Updated 2026-01-08)

| Component | Score | Critical Issues |
|-----------|-------|-----------------|
| CLI Commands | **7/10** | CommandResult/--json broadly supported; print allowlist + interactive --json gaps remain |
| Workflows | 9/10 | hub-production-ci is now CLI-driven (ruff-format/mypy/yamllint wrappers); remaining work is tightening schema + registry/wizard parity |
| Schema | 7/10 | ~24% unused fields; deprecated aliases normalized; `cihub` block added; remaining gaps are registry schema + broader schema/code parity |
| Wizard | 3/10 | 4 interactive flows, no profile selection, no registry integration |
| Registry | 2/10 | Only tracks a small threshold subset (coverage/mutation/vulns); tools/metadata still not represented |
| User Journeys | 5/10 | Migration tooling missing, troubleshooting gaps |

### CLI Architecture Verification (Current Reality)

CLI architecture is close but not fully JSON-pure yet:
- **106+ commands** across 18 parser groups (audit required to confirm current count)
- CommandResult is the standard return type, but a print allowlist still exists for interactive/streaming output
- `--json` flag is added globally, but interactive commands must explicitly reject it (setup now rejects `--json`)
- hub-ci wrappers exist for `ruff-format`, `mypy`, and `yamllint` and hub-production-ci now uses them (no raw tool calls)
- JSON purity contract tests exist (representative sample across command groups)

### Key Architectural Findings

| System                | Status       | Details                                                                      |
|-----------------------|--------------|------------------------------------------------------------------------------|
| Config Loading        | ✅ WORKING    | 3-tier merge chain functions correctly                                       |
| Boolean Normalization | ✅ WORKING    | `tool: true` → `tool: {enabled: true}` works                                 |
| Wizard                | ✅ WORKING    | Creates configs, but disconnected from registry                              |
| Registry CLI          | ⚠️ PARTIAL   | Commands exist but only track a small threshold subset (schema-aligned keys) |
| Wizard ↔ Registry     | ❌ BROKEN     | Not connected at all                                                         |
| Registry → YAML Sync  | ⚠️ PARTIAL   | Sync is now schema-safe for threshold keys; full config scope still missing  |
| Profiles              | ⚠️ UNDERUSED | 12 profiles exist but wizard doesn't surface them                            |

---

## Decisions & Contracts (v1.0)

These decisions keep CLI/wizard parity and preserve the existing 3-tier config model.

1. **CLI is the headless API** - wizard is a thin UI over the same service layer (no wizard-only logic).
2. **Registry owns hub-managed config** - repo metadata, tools, thresholds, gates, reports, notifications, harden_runner, thresholds_profile (hub_ci only for hub repo).
3. **Preserve 3-tier merge** - defaults -> config/repos/*.yaml -> repo `.ci-hub.yml` (repo overrides always win).
4. **Registry never writes `.ci-hub.yml` by default** - repo-side writes require explicit apply (repo.repo_side_execution or `--force`).
5. **Registry bootstrap/import is required** - always supports `--dry-run` and conflict strategies (merge/replace/prefer-registry/prefer-config).
6. **Custom tools (x-*) are first-class** - must flow through schema, registry, report/triage/validator, and tests.
7. **Profile mapping is explicit** - tier -> profile name -> config fragment; thresholds_profile is derived or deprecated.
8. **JSON purity is required** - non-interactive commands emit a single JSON payload; interactive commands reject `--json` with CommandResult.
9. **Registry repo metadata precedence (temporary)** - when both are present, `repos.<name>.config.repo` is canonical; top-level `repos.<name>.language/dispatch_enabled` are legacy/back-compat and must not disagree (treat disagreement as drift).
10. **Drift buckets (Phase 2.4)**:
   - `unmanaged_key.*` → **warning** (schema-valid but not registry-managed yet)
   - `unknown_key.*` → **error** (schema-invalid; likely typo/stale field)
11. **Repo config identity (v1.0)** - the repo key is the **config filename/path** relative to `config/repos/` (supports nested `owner/repo.yaml`), not `repo.owner`/`repo.name` inside the YAML. Ownership metadata can differ; drift is reported against the file-path identity.

---

## TypeScript Compatibility Contract

1. Non-interactive commands emit exactly one JSON payload on stdout (`--json`).
2. Interactive commands reject `--json` with a CommandResult error (no mixed output).
3. CommandResult JSON schema is stable and versioned.
4. TypeScript CLI calls only non-interactive CLI endpoints (no questionary dependency).

---

## Part 1: Architecture Overview

### 1.1 Current Data Flow (BROKEN)

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Wizard    │────▶│ config/     │     │  registry.json   │
│ (cihub new) │     │ repos/*.yaml│     │  (3 values only) │
└─────────────┘     └─────────────┘     └──────────────────┘
     │                    │
     ▼                    ▼
  MAY WRITE           USED BY CI
  .ci-hub.yml         engine
  directly            (registry ignored)
```

### 1.2 Correct Data Flow (TARGET)

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Wizard/CLI  │────▶│  registry.json   │────▶│ config/repos/    │
│ (services) │     │  (non-defaults)  │     │ *.yaml            │
└─────────────┘     └──────────────────┘     └──────────────────┘
     │                     │                        │
     ▼                     ▼                        ▼
 repo-side apply       SOURCE OF                load_config
 (explicit)            TRUTH                    merge chain
                                            defaults + repo + .ci-hub.yml
```

### 1.3 Core Design Principles

1. **Registry = Source of Truth** - Owns hub-managed config (repo metadata, tools, thresholds, gates, reports, notifications, harden_runner, thresholds_profile)
2. **Preserve 3-tier merge** - defaults -> config/repos/*.yaml -> repo `.ci-hub.yml` overrides
3. **Sync generates YAML** - registry writes config/repos only; repo-side writes require explicit apply
4. **CLI-driven with wizard parity** - wizard uses the same service layer as CLI commands
5. **Sparse storage** - registry only stores non-default values
6. **No hardcoded tiers** - profiles are optional presets
7. **Schema via $ref** - no duplication, registry references ci-hub-config.schema
8. **CI engine unchanged** - still reads from config/repos/*.yaml
9. **Bootstrap + drift detection** - migration must be safe, auditable, and reversible

---

## Part 2: Critical Issues

### 2.1 Registry Only Tracks a Small Threshold Subset

**Location:** `cihub/services/registry_service.py` (`list_repos()`)

```python
effective = {
    "coverage_min": ...,
    "mutation_score_min": ...,
    "max_critical_vulns": ...,
    "max_high_vulns": ...,
}
```

**Impact:**
- Ignores all 26 tool settings
- Ignores 12+ threshold fields
- Ignores all repo metadata beyond basic fields

### 2.2 Registry Legacy Threshold Keys (Fixed in Phase 0.1)

**Location:** `services/registry_service.py`

**Status:** ✅ **RESOLVED in Phase 0.1**

**Fix implemented:**
- Registry now normalizes legacy keys to schema-aligned keys on load/save (`coverage_min`, `mutation_score_min`, `max_{critical,high}_vulns`)
- `cihub registry sync` writes only schema threshold keys into `config/repos/*.yaml` and removes legacy keys from config thresholds

### 2.3 Registry Schema Scope Too Small

**Location:** `schema/registry.schema.json`

**Impact:**
- Can represent a **small allowlisted subset** today (threshold overrides + allowlisted config fragment), but still cannot represent the full hub-managed config scope end-to-end without Phase 2.2/2.3
- Prevents full round-trip sync and drift detection

### 2.4 Schema Field Mismatches / Gaps

| Issue | Location | Impact |
|-------|----------|--------|
| `mutmut.min_score` alias not normalized/deprecated | schema/ci-hub-config.schema.json (mutmut), config/normalize.py | ✅ Fixed: alias normalized to `min_mutation_score`; schema marks `min_score` deprecated |
| Missing `cihub` block | schema/ci-hub-config.schema.json, config/loader/inputs.py | ✅ Fixed: schema now includes `cihub` and inputs are robust to invalid shapes |
| Schema defaults disagree with defaults.yaml (`mutmut.enabled`) | schema/ci-hub-config.schema.json, config/defaults.yaml | ✅ Fixed: defaults aligned (mutmut disabled by default) |
| `python.tools.trivy.fail_on_cvss` not in schema but read in inputs | schema/ci-hub-config.schema.json, config/loader/inputs.py | ✅ Fixed: schema includes `fail_on_cvss` and defaults provide a value |

### 2.5 Registry Bypass in CLI/Wizard

**Current:** `cihub new` writes `config/repos/*.yaml` directly, `cihub init` writes `.ci-hub.yml`, wizard edits configs without touching registry.

**Impact:** Registry and config drift immediately; wizard/CLI parity is broken.

### 2.6 Hardcoded Tools in Workflow (Fixed in Phase 1.5)

**File:** `.github/workflows/hub-production-ci.yml`

**Fix implemented:** Workflow now calls CLI wrappers (no raw tool invocations).

| Tool        | Previous                  | Now                                      |
|-------------|---------------------------|------------------------------------------|
| Ruff format | `ruff format --check ...` | `python -m cihub hub-ci ruff-format ...` |
| mypy        | `mypy ...`                | `python -m cihub hub-ci mypy ...`        |
| yamllint    | `yamllint ...`            | `python -m cihub hub-ci yamllint ...`    |

### 2.7 Wizard Doesn't Use Profiles

**Current:** Wizard asks 15+ individual tool questions; profiles are only applied when passed in (e.g., `cihub new --profile`).
**Target:** Profile selection → pre-filled checkboxes → customize

### 2.8 JSON Purity Gaps

**Fixed:** Setup now rejects `--json` with a CommandResult error, and JSON purity contract tests exist (representative sample).

### 2.9 Tiers / Profiles / Thresholds Profile Mapping Is Unclear

**Current:** Registry tiers, template profiles, and `thresholds_profile` exist in parallel without a canonical mapping.

**Impact:** Users can end up with conflicting defaults; plan must define a single source of truth.

### 2.10 Missing CLI Capabilities (Audit Required)

The current missing-command list is stale. Re-audit the CLI surface and align to the target command set in Part 7.

---

## Part 3: Tool Inventory

Defaults shown below reflect **defaults.yaml** (current effective defaults). Schema defaults are aligned as of Phase 1.7.

### 3.1 Python Tools (14)

| Tool       | Key Settings                                       | Default                              |
|------------|----------------------------------------------------|--------------------------------------|
| pytest     | enabled, min_coverage, fail_fast                   | enabled=true, min_coverage=70        |
| ruff       | enabled, fail_on_error, max_errors                 | enabled=true                         |
| black      | enabled, fail_on_format_issues, max_issues         | enabled=true                         |
| isort      | enabled, fail_on_issues, max_issues                | enabled=true                         |
| mypy       | enabled, require_run_or_fail                       | enabled=false                        |
| bandit     | enabled, fail_on_high/medium/low                   | enabled=true, fail_on_high=true      |
| pip_audit  | enabled, fail_on_vuln                              | enabled=true                         |
| mutmut     | enabled, min_mutation_score (min_score deprecated) | enabled=false, min_mutation_score=70 |
| hypothesis | enabled                                            | enabled=true                         |
| semgrep    | enabled, fail_on_findings                          | enabled=false                        |
| trivy      | enabled, fail_on_critical/high                     | enabled=false                        |
| codeql     | enabled, languages                                 | enabled=false                        |
| docker     | enabled, compose_file                              | enabled=false                        |
| sbom       | enabled, format                                    | enabled=false                        |

### 3.2 Java Tools (12)

| Tool       | Key Settings                                 | Default                       |
|------------|----------------------------------------------|-------------------------------|
| jacoco     | enabled, min_coverage                        | enabled=true, min_coverage=70 |
| checkstyle | enabled, fail_on_violation                   | enabled=true                  |
| spotbugs   | enabled, fail_on_error, max_bugs             | enabled=true                  |
| pmd        | enabled, fail_on_violation                   | enabled=true                  |
| owasp      | enabled, fail_on_cvss                        | enabled=true, fail_on_cvss=7  |
| pitest     | enabled, min_mutation_score                  | enabled=true                  |
| jqwik      | enabled                                      | enabled=false                 |
| semgrep    | enabled, fail_on_findings                    | enabled=false                 |
| trivy      | enabled, fail_on_critical/high, fail_on_cvss | enabled=false                 |
| codeql     | enabled, languages                           | enabled=false                 |
| docker     | enabled, compose_file                        | enabled=false                 |
| sbom       | enabled, format                              | enabled=false                 |

### 3.3 Global Thresholds

| Field                 | Type            | Default |
|-----------------------|-----------------|---------|
| coverage_min          | integer (0-100) | 70      |
| mutation_score_min    | integer (0-100) | 70      |
| max_critical_vulns    | integer         | 0       |
| max_high_vulns        | integer         | 0       |
| max_pip_audit_vulns   | integer         | 0       |
| owasp_cvss_fail       | float (0-10)    | 7.0     |
| trivy_cvss_fail       | float (0-10)    | 7.0     |
| max_semgrep_findings  | integer         | 0       |
| max_ruff_errors       | integer         | 0       |
| max_black_issues      | integer         | 0       |
| max_isort_issues      | integer         | 0       |
| max_checkstyle_errors | integer         | 0       |
| max_spotbugs_bugs     | integer         | 0       |
| max_pmd_violations    | integer         | 0       |

---

## Part 4: Wizard Profile-First Design (ADR-0051)

### 4.1 Design Decision

Profiles are a **starting point**, then ALWAYS show checkboxes for customization.

**Key principle:** Profiles are defaults/templates, not restrictions. Users ALWAYS have full control via checkboxes.

### 4.2 Complete Wizard Flow Mockup

```
┌─────────────────────────────────────────────────────────-────┐
│                    CIHub Setup Wizard                        │
├───────────────────────────────────────────────────────-──────┤
│                                                              │
│  Step 1: Project Detection                                   │
│  ────────────────────────                                    │
│  ✓ Detected: Python (pyproject.toml)                         │
│                                                              │
│  Step 2: Select CI Profile                                   │
│  ─────────────────────────                                   │
│  Profiles determine your default tool selection and          │
│  quality gates. You can customize after selecting.           │
│                                                              │
│  ○ Fast (Recommended)                                        │
│    pytest, ruff, black, bandit, pip-audit (~5 min)           │
│                                                              │
│  ○ Quality                                                   │
│    Fast + mypy, mutmut (~20 min)                             │
│                                                              │
│  ○ Security                                                  │
│    bandit, pip-audit, semgrep, trivy, codeql (~30 min)       │
│                                                              │
│  ○ Start from scratch                                        │
│    Configure each tool individually                          │
│                                                              │
│  Step 3: Customize Tools (always shown)                      │
│  ──────────────────────────────────────                      │
│  Pre-filled based on "Fast" profile. Toggle to customize:    │
│                                                              │
│  ☑ pytest          ☑ ruff           ☑ black                  │
│  ☐ isort           ☐ mypy           ☑ bandit                 │
│  ☑ pip-audit       ☐ mutmut         ☐ semgrep                │
│  ☐ trivy           ☐ codeql         ☐ sbom                   │
│                                                              │
│  Step 4: Quality Gates                                       │
│  ─────────────────────                                       │
│  Based on "Fast" profile defaults:                           │
│                                                              │
│  Min coverage:     [70]%                                     │
│  Fail on high:     [Yes]                                     │
│  Format mode:      ○ Check  ○ Fix                            │
│                                                              │
│  Step 5: Preview & Confirm                                   │
│  ─────────────────────────                                   │
│  Files to create:                                            │
│    • .ci-hub.yml                                             │
│    • .github/workflows/hub-ci.yml                            │
│                                                              │
│  [Preview .ci-hub.yml]  [Create Files]  [Cancel]             │
│                                                              │
└─────────────────────────────────────────────────────────-────┘
```

### 4.3 Profile Mapping

| Profile | Tools Enabled | Runtime |
|---------|---------------|---------|
| `minimal` | pytest, ruff | ~2-5 min |
| `fast` | pytest, ruff, black, isort, bandit, pip-audit | ~3-8 min |
| `quality` | fast + mypy, mutmut | ~15-30 min |
| `security` | bandit, pip-audit, semgrep, trivy, codeql | ~15-30 min |
| `compliance` | security + stricter thresholds | ~15-30 min |
| `coverage-gate` | high coverage/mutation requirements | ~12-20 min |

### 4.4 Sub-Decisions

1. **Black/isort Mode:** Default to `check` mode in CI
2. **Config Location:** Hub-managed config lives in registry/config/repos; `.ci-hub.yml` is optional repo override
3. **Wizard Parity:** Wizard must use the same service layer as CLI for all config writes
4. **Multi-CI Support:** GitHub Actions only for v1.0

---

## Part 5: Implementation Phases

### Phase 0: Safety + JSON Purity (Week 0)

| # | Task | Files | Tests |
|---|------|-------|-------|
| 0.1 | Fix registry threshold key mapping to schema (`coverage_min`, `mutation_score_min`, `max_*`) | services/registry_service.py | Unit + schema validation |
| 0.2 | Enforce JSON purity: interactive commands reject `--json` (setup), no stdout prints in JSON mode | commands/setup.py, cli renderer | Contract tests |
| 0.3 | Add JSON purity contract tests (non-interactive commands) | tests/test_command_output_contract.py (or new) | Integration tests |

### Phase 1: Workflow Parity Hardening (Week 1)

| # | Task | Files | Tests |
|---|------|-------|-------|
| 1.1 | Normalize `min_score` → `min_mutation_score`, deprecate alias, align hub-ci args | schema, normalize.py, hub_ci/python_tools.py, cli_parsers/hub_ci.py | Schema + command tests |
| 1.2 | Add hub-ci ruff format wrapper (new subcommand or flag) | hub_ci/python_tools.py, cli_parsers/hub_ci.py | Command tests |
| 1.3 | Create `cihub hub-ci mypy` | hub_ci/python_tools.py | Command tests |
| 1.4 | Create `cihub hub-ci yamllint` | hub_ci/validation.py | Command tests |
| 1.5 | Replace hardcoded workflow tools | hub-production-ci.yml | Workflow validation |
| 1.6 | Add `cihub` block to schema (code already consumes it) | schema | Schema tests |
| 1.7 | Align schema defaults with defaults.yaml (mutmut default, python trivy config) | schema, config/defaults.yaml | Schema validation |
| 1.8 | Resolve python trivy CVSS decision (allow tool-level config + schema; normalize to thresholds inputs) | schema, normalize.py, config/loader/inputs.py | Schema + integration tests |

### Phase 2: Registry Schema + Service (Week 2)

| # | Task | Files | Tests |
|---|------|-------|-------|
| 2.1 | Expand registry.schema.json to reference config schema with allowlisted keys (repo metadata, tools, thresholds, gates, reports, notifications, harden_runner, thresholds_profile) | schema/registry.schema.json | Contract tests |
| 2.2 | Rewrite registry_service.py for full config scope with sparse storage | services/registry_service.py | Unit tests |
| 2.3 | Sync generates full config/repos/*.yaml for all supported keys | registry_service.py | Sync roundtrip tests |
| 2.4 | Diff surfaces .ci-hub.yml overrides + non-tool drift | registry_service.py | Diff tests |
| 2.5 | Define canonical tier/profile/thresholds_profile mapping | schema, docs | Contract tests |

### Phase 3: Registry Bootstrap & Drift (Week 3)

| # | Task | Files | Tests |
|---|------|-------|-------|
| 3.1 | Add registry bootstrap/import command with `--dry-run` | commands/registry_cmd.py | Command tests |
| 3.2 | Conflict strategies (merge/replace/prefer-registry/prefer-config) + audit report | services/registry_service.py | Integration tests |
| 3.3 | Drift report: registry vs config/repos vs .ci-hub.yml | services/registry_service.py | Report tests |

### Phase 4: Wizard Parity + Profile Integration (Week 4)

| # | Task | Files | Tests |
|---|------|-------|-------|
| 4.1 | Wizard uses shared service layer for all config writes (no direct file writes) | wizard/core.py, services/configuration.py | Flow tests |
| 4.2 | Add profile selection step | wizard/questions/profile.py | Flow tests |
| 4.3 | Keep checkboxes after profile + add format mode choice | wizard/questions/python_tools.py, wizard/questions/format_mode.py | Interaction tests |
| 4.4 | Expose non-tool settings (repo metadata, gates, reports, notifications, harden_runner) | wizard/questions/* | Flow tests |
| 4.5 | Setup wizard uses registry + optional repo-side apply | commands/setup.py | E2E tests |

### Phase 5: CLI Management Commands (Week 5)

| # | Task | Commands | Priority |
|---|------|----------|----------|
| 5.1 | Profile management | create, list, show, edit, delete, import, export | 🔴 CRITICAL |
| 5.2 | Registry management | remove, bootstrap, import/export | 🔴 CRITICAL |
| 5.3 | Tool management | list, enable, disable, configure, status, validate | 🟠 HIGH |
| 5.4 | Threshold management | get, set, list, reset, compare | 🟠 HIGH |
| 5.5 | Repo management | list, update, migrate, clone, verify-connectivity | 🟡 MEDIUM |

### Phase 6: Schema & Extensibility (Week 6)

| # | Task | Files | Tests |
|---|------|-------|-------|
| 6.1 | Enable custom tools (x- prefix) end-to-end (schema, normalize, tool registry, report/triage/validator) | schema, normalize.py, tools/registry.py, services/triage | Custom tool tests |
| 6.2 | Update command contracts + generated docs for new CLI surface | CLI_COMMAND_AUDIT.md, docs/reference | Contract tests |

---

## Part 6: Comprehensive Test Matrix

### 6.1 Repo Shape Matrix

Every CLI command must be tested across these configurations:

| Repo Shape | Structure | Key Files |
|------------|-----------|-----------|
| `python-root` | Single Python at root | `pyproject.toml` |
| `python-setup` | Legacy setup.py | `setup.py` |
| `java-maven-root` | Maven at root | `pom.xml` |
| `java-gradle-root` | Gradle at root | `build.gradle` |
| `monorepo-mixed` | Java + Python subdirs | `java/`, `python/` |
| `python-subdir` | Python in subdirectory | `services/backend/pyproject.toml` |
| `java-subdir` | Java in subdirectory | `services/api/pom.xml` |
| `java-multi-module` | Parent POM + modules | `pom.xml`, `module-a/`, `module-b/` |
| `empty-repo` | Empty git repo | `.git/` only |
| `no-git` | No git | No `.git/` |

### 6.2 Command × Repo Shape Requirements

```
┌────────────────────┬─────────┬─────────┬───────┬────────┬─────────┬─────────┬─────────┬───────────┬───────┬────────┐
│ Command            │ py-root │ py-setup│ java-m│ java-g │ monorepo│ py-sub  │ java-sub│ java-multi│ empty │ no-git │
├────────────────────┼─────────┼─────────┼───────┼────────┼─────────┼─────────┼─────────┼───────────┼───────┼────────┤
│ cihub detect       │ ✓       │ ✓       │ ✓     │ ✓      │ ✓       │ ✓       │ ✓       │ ✓         │ ✓     │ ✓      │
│ cihub init         │ ✓       │ ✓       │ ✓     │ ✓      │ ✓       │ ✓       │ ✓       │ ✓         │ E     │ E      │
│ cihub validate     │ ✓       │ ✓       │ ✓     │ ✓      │ ✓       │ ✓       │ ✓       │ ✓         │ E     │ E      │
│ cihub ci           │ ✓       │ ✓       │ ✓     │ ✓      │ ✓       │ ✓       │ ✓       │ ✓         │ E     │ E      │
│ cihub check        │ ✓       │ ✓       │ ✓     │ ✓      │ ✓       │ ✓       │ ✓       │ ✓         │ E     │ E      │
│ cihub triage       │ ✓       │ ✓       │ ✓     │ ✓      │ ✓       │ ✓       │ ✓       │ ✓         │ E     │ E      │
│ cihub setup        │ ✓       │ ✓       │ ✓     │ ✓      │ ✓       │ ✓       │ ✓       │ ✓         │ ✓     │ ✓      │
│ cihub scaffold     │ ✓       │ ✓       │ ✓     │ ✓      │ ✓       │ N/A     │ N/A     │ N/A       │ ✓     │ ✓      │
└────────────────────┴─────────┴─────────┴───────┴────────┴─────────┴─────────┴─────────┴───────────┴───────┴────────┘

Legend: ✓ = Must pass, E = Expected error (graceful), N/A = Not applicable
```

### 6.3 Sync Verification Matrix

| Sync Point | Current Status | Tests Required |
|------------|----------------|----------------|
| Wizard → Registry | ❌ BROKEN | Integration tests |
| Registry → config/repos | ⚠️ 3 fields only | Full field sync tests |
| defaults + config/repos + .ci-hub.yml → load_config | ⚠️ PARTIAL | Precedence tests |
| Registry bootstrap (configs → registry) | ❌ NO | Import/conflict tests |
| YAML → Workflow | ❌ NO verification | Contract tests |
| Schema ↔ Code | ⚠️ PARTIAL | Schema-code parity tests |
| Profile ↔ Registry | ❌ NO | Profile existence tests |
| Thresholds ↔ Gates | ❌ NO | Gate evaluation tests |

### 6.4 Edge Cases (38+ identified)

**Wizard Edge Cases:**
- User cancels mid-wizard → Cleanup partial state
- Duplicate repo name → Prompt for overwrite/rename
- Profile reference doesn't exist → Warn and continue

**Registry Edge Cases:**
- Config file exists with different content → --force flag
- Orphaned YAML (no registry entry) → registry bootstrap/cleanup command
- Registry has invalid JSON → Graceful error + backup
- Registry bootstrap conflicts (registry vs config/repos vs .ci-hub.yml) → conflict strategy required
- Repo-side apply when `repo_side_execution=false` → require explicit override

**CI Engine Edge Cases:**
- Tool timeout → Configurable timeouts
- Tool not found → Clear error message
- Coverage report missing → Fail gate or warn
- Custom tool enabled without metrics/artifacts → warn or fail per policy

---

## Part 7: CLI Management Commands Detail (Target Set)

> **Audit required:** `--json` is added at the parser level but JSON purity is not universal. Interactive commands must reject `--json`, and streaming output remains allowlisted.

### 7.1 Profile Management (CRITICAL)

```bash
cihub profile create <name> --language python --from-repo <repo>
cihub profile list [--language python|java]
cihub profile show <name> [--effective]
cihub profile edit <name> [--wizard]
cihub profile delete <name> [--force]
cihub profile export <name> --output file.yaml
cihub profile import --file file.yaml
```

### 7.2 Registry Management (CRITICAL)

```bash
cihub registry list [--tier <tier>]
cihub registry show <name>
cihub registry add <name> --owner <owner> --language <python|java>
cihub registry set <name> [--tier <tier>] [--thresholds ...] [--tools ...]
cihub registry remove <name> [--keep-config]
cihub registry diff [--repo <name>]
cihub registry sync [--dry-run]
cihub registry bootstrap --source config/repos [--include-repo-config] [--dry-run] [--strategy merge|replace|prefer-registry|prefer-config]
cihub registry import --file backup.json [--merge|--replace]
cihub registry export --output backup.json
```

### 7.3 Repository Management (MEDIUM)

```bash
cihub repo list [--language] [--format json]
cihub repo update <name> --owner myorg --branch main
cihub repo migrate <from> <to> [--delete-source]
cihub repo clone <source> <dest>
cihub repo verify-connectivity <name>
```

### 7.4 Tool Management (HIGH)

```bash
cihub tool list [--language] [--category lint|security|test]
cihub tool enable <tool> [--for-repo <name>] [--all-repos]
cihub tool disable <tool> [--for-repo <name>] [--all-repos]
cihub tool configure <tool> <param> <value> [--repo]
cihub tool status [--repo] [--all]
cihub tool validate <tool> [--install-if-missing]
```

### 7.5 Threshold Management (HIGH)

```bash
cihub threshold get [<tool>] [--repo] [--effective]
cihub threshold set <tool> <value> [--repo] [--all-repos]
cihub threshold list [--language] [--category]
cihub threshold reset [<tool>] [--repo]
cihub threshold compare <repo1> <repo2>
```

### 7.6 Import/Export (HIGH)

```bash
cihub export --format json --output backup.json
cihub import --file backup.json [--merge|--replace]
cihub export repo <name> --output repo.yaml
cihub import repo --file repo.yaml
cihub export registry --filter-language python
```

---

## Part 8: Test Implementation

### 8.1 New Test File Structure

```
tests/
├── test_repo_shapes/                    # NEW: Repo shape matrix tests
│   ├── conftest.py                      # Repo shape fixtures
│   ├── test_detect_shapes.py
│   ├── test_init_shapes.py
│   ├── test_ci_shapes.py
│   └── test_hub_ci_shapes.py
├── test_wizard_flows/                   # NEW: Wizard flow tests
│   ├── conftest.py
│   ├── test_profile_selection.py
│   ├── test_checkbox_interaction.py
│   ├── test_setup_wizard.py
│   └── test_cli_wizard_parity.py
├── test_registry/                       # NEW: Registry tests
│   ├── test_registry_service_unit.py
│   ├── test_registry_integration.py
│   ├── test_registry_contracts.py
│   ├── test_registry_properties.py      # Hypothesis
│   ├── test_registry_bootstrap.py
│   ├── test_registry_drift.py
│   └── test_registry_e2e.py
├── test_config_precedence/              # NEW: Merge order + repo-side apply
│   ├── test_merge_order.py
│   └── test_repo_side_apply.py
├── test_cli_contracts/                  # NEW: JSON purity + output contracts
│   └── test_json_purity.py
├── test_schema_validation/              # NEW: Schema validation tests
│   ├── test_field_validation.py
│   ├── test_deprecation_warnings.py
│   └── test_schema_evolution.py
└── existing tests...
```

### 8.2 Test Metrics Goals

| Metric | Current | Target |
|--------|---------|--------|
| Line coverage | ~85% | >95% |
| Branch coverage | ~70% | >90% |
| Mutation score | N/A | >80% |
| Contract tests | 5 | 25+ |
| Property tests | 3 | 15+ |
| E2E tests | 8 | 20+ |

### 8.3 Repo-Shape Fixture Strategy

- Use `cihub scaffold` to generate repo-shape fixtures into temp dirs.
- Keep fixtures minimal (one representative file per shape) to reduce test time.

### 8.4 Required Integration Tests

- JSON purity tests: run representative non-interactive commands with `--json` and assert stdout parses cleanly.
- Registry round-trip: registry -> config/repos -> load_config -> registry diff == empty.
- Wizard/CLI parity: compare effective config after normalize/merge (not byte-for-byte YAML).

---

## Part 9: Implementation Checklist

### Phase 0: Safety + JSON Purity ✅

- [x] 0.1 Fix registry threshold key mapping to schema
- [x] 0.2 Enforce JSON purity (interactive commands reject `--json`; no stdout prints in JSON mode)
- [x] 0.3 Add JSON purity contract tests

### Phase 1: Workflow Parity Hardening ✅

- [x] 1.1 Normalize min_score alias → min_mutation_score + deprecate
- [x] 1.2 Add hub-ci ruff format wrapper
- [x] 1.3 Create hub-ci mypy command
- [x] 1.4 Create hub-ci yamllint command
- [x] 1.5 Replace hardcoded workflow tools
- [x] 1.6 Add `cihub` block to schema
- [x] 1.7 Align schema defaults with defaults.yaml (mutmut/trivy)
- [x] 1.8 Resolve python trivy CVSS decision (tool-level vs thresholds)

### Phase 2: Registry Schema + Service ☐

- [x] 2.1 Expand registry.schema.json with allowlisted keys
- [x] 2.2a Add sparse config fragment audit (defaults/profile baseline)
- [ ] 2.2 Rewrite registry_service.py for full config scope (sparse storage)
- [ ] 2.3 Implement full sync to config/repos
- [x] 2.3a Sync tier/repo config fragments into config/repos (managedConfig; includes tier profile merge)
- [x] 2.4a Diff surfaces managedConfig drift via dry-run sync (non-threshold keys + thresholds) + cross-root --configs-dir handling
- [x] 2.4b Diff flags orphan config/repos YAMLs + unmanaged top-level keys (allowlist-driven)
- [ ] 2.4 Diff surfaces .ci-hub.yml overrides + non-tool drift
- [ ] 2.5 Define canonical tier/profile/thresholds_profile mapping

### Phase 3: Registry Bootstrap & Drift ☐

- [ ] 3.1 Add registry bootstrap/import command with --dry-run
- [ ] 3.2 Implement conflict strategies + audit report
- [ ] 3.3 Add drift report across registry/config/repos/.ci-hub.yml

### Phase 4: Wizard Parity + Profile Integration ☐

- [ ] 4.1 Wizard uses shared service layer (no direct writes)
- [ ] 4.2 Add profile selection step
- [ ] 4.3 Keep checkboxes after profile + format mode choice
- [ ] 4.4 Expose non-tool settings in wizard
- [ ] 4.5 Setup wizard uses registry + optional repo-side apply

### Phase 5: CLI Management Commands ☐

- [ ] 5.1 Profile management commands
- [ ] 5.2 Registry remove/bootstrap/import/export commands
- [ ] 5.3 Tool management commands
- [ ] 5.4 Threshold management commands
- [ ] 5.5 Repo management commands

### Phase 6: Schema & Extensibility ☐

- [ ] 6.1 Enable custom tools (x- prefix) end-to-end
- [ ] 6.2 Update command contracts + generated docs

### Test Implementation ☐

- [ ] Create test_repo_shapes/ with fixtures
- [ ] Create test_wizard_flows/
- [ ] Create test_registry/
- [ ] Create test_config_precedence/
- [x] Create test_cli_contracts/ (JSON purity)
- [ ] Create test_schema_validation/
- [ ] Add CLI/wizard parity tests
- [ ] Add registry bootstrap + drift tests
- [ ] Run full test matrix

---

## Part 10: Quick Wins (< 1 hour each)

1. ✅ Add `--json` guard for interactive commands (setup)
2. ✅ Fix registry threshold key mapping to schema
3. ✅ Normalize `min_score` → `min_mutation_score`, align hub-ci mutmut args
4. ✅ Add hub-ci ruff format wrapper (subcommand or flag)
5. ✅ Add `cihub` block to schema (debug/triage toggles)
6. Add inline comments to scaffold output files
7. Document all `CIHUB_*` env toggles in one place
8. Add "See Also" to command help text

---

## Related Documents

- `docs/adr/0051-wizard-profile-first-design.md` - ADR for profile-first design
- `docs/development/MASTER_PLAN.md` - Overall priority tracking
- `docs/development/active/CLEAN_CODE.md` - Architecture improvements (Priority #1)

---

## Superseded Documents

The following documents have been consolidated into this plan:
- `docs/development/archive/COMPREHENSIVE_SYSTEM_AUDIT.md` → Archived
- `docs/development/archive/WIZARD_IMPROVEMENTS.md` → Archived
- `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` → Archived

---

## Appendix A: Audit Corrections (Updated 2026-01-08)

### A.1 CLI Audit Results (Corrected)

**Methodology:** Exhaustive search of `cihub/cli_parsers/*.py` and `cihub/commands/*.py`

| Metric | Previous Estimate | Current Reality |
|--------|-------------------|----------------|
| Total Commands | 83 | **106+** (audit required) |
| Parser Groups | 18 | **18** |
| --json Support | 100% | Parser-level support is broad; interactive commands must reject `--json` |
| CommandResult Returns | 100% | Standard pattern; print allowlist still exists |
| Architectural Gaps | 0 | JSON purity contract exists (Phase 0); workflow parity wrappers are in place |

**Key Finding:** CLI architecture is close, and Phase 0 (JSON purity + safety) is complete. Next blockers are registry/wizard parity (Phase 2+) and broader schema/code parity.

### A.2 Schema Audit Results (Corrected)

**Methodology:** Cross-reference schema/ci-hub-config.schema.json against cihub/config/*.py

| Finding | Details |
|---------|---------|
| Unused fields | ~24% of schema fields are reserved/future features |
| `min_score` mismatch | ✅ Fixed: deprecated alias normalized to `min_mutation_score` |
| Missing `cihub` block | ✅ Fixed: schema now includes `cihub` debug/triage toggles |
| Registry keys | Registry normalizes legacy keys to schema-aligned keys on load/save; still limited to a small threshold subset |

### A.3 Wizard Audit Results (Corrected)

**Methodology:** Trace wizard flow in `cihub/wizard/` and compare to CLI commands

| Metric | Count |
|--------|-------|
| Commands with wizard support | 4 of 106+ |
| Profile selection | ❌ Not implemented (only applies profile if passed in) |
| Registry integration | ❌ Not implemented |

**Wizard-supported commands:**
1. `cihub setup` - Full workflow wizard
2. `cihub init --wizard` - Config wizard
3. `cihub new --interactive` - Config creation
4. `cihub config edit` - Config editing

### A.4 Workflow Audit Results (Agent 4)

**Methodology:** Grep for raw tool invocations in `.github/workflows/*.yml`

| Workflow | Status | Issues |
|----------|--------|--------|
| python-ci.yml | ✅ COMPLIANT | All tools via CLI |
| java-ci.yml | ✅ COMPLIANT | All tools via CLI |
| hub-ci.yml | ✅ COMPLIANT | Pure routing |
| hub-production-ci.yml | ✅ COMPLIANT | All tools via CLI (ruff-format/mypy/yamllint wrappers) |

### A.5 User Journey Audit Results (Agent 5)

| Journey | Score | Key Gaps |
|---------|-------|----------|
| New User Onboarding | 6/10 | Setup wizard incomplete |
| Existing Repo Migration | 3/10 | **No migration tooling** |
| Day-to-Day Usage | 7/10 | Triage hard to discover |
| Configuration Changes | 6/10 | No config diff preview |
| Troubleshooting | 7/10 | No diagnostic bundle |

### A.6 Test Directory Status

**Proposed directories in Part 8 do NOT exist yet:**

```
tests/test_repo_shapes/     → EMPTY (needs creation)
tests/test_wizard_flows/    → EMPTY (needs creation)
tests/test_registry/        → EMPTY (needs creation)
tests/test_config_precedence/ → EMPTY (needs creation)
tests/test_schema_validation/ → EMPTY (needs creation)
```

**Estimated new tests required:** 200-250 tests across all proposed directories
