# System Integration Plan (Archived)
> **Superseded by:** [MASTER_PLAN.md](../MASTER_PLAN.md)

> **WARNING: SUPERSEDED:** This document is archived (2026-01-15). The canonical execution plan is
> `docs/development/MASTER_PLAN.md`, with current architecture in `docs/development/architecture/ARCH_OVERVIEW.md`.
>
> **Status:** Archived
> **Archived:** 2026-01-15
> **Owner:** Development Team
> **Source-of-truth:** manual
> **Last-reviewed:** 2026-01-15
> **Superseded-by:** docs/development/MASTER_PLAN.md

**Consolidates:** COMPREHENSIVE_SYSTEM_AUDIT.md, WIZARD_IMPROVEMENTS.md, REGISTRY_AUDIT_AND_PLAN.md

---

## Executive Summary

This document consolidates findings from multiple audits (5-agent system audit, 8-agent registry audit, wizard analysis, final 5-agent verification audit on 2026-01-08) into a single actionable roadmap with comprehensive testing requirements.

### Overall System Health (Updated 2026-01-14)

| Component | Score | Critical Issues |
|-----------|-------|-----------------|
| CLI Commands | **7/10** | CommandResult/--json broadly supported; print allowlist + interactive --json gaps remain |
| Workflows | 9/10 | hub-production-ci is now CLI-driven (ruff-format/mypy/yamllint wrappers); remaining work is tightening schema + registry/wizard parity |
| Schema | 7/10 | ~24% unused fields; deprecated aliases normalized; `cihub` block added; remaining gaps are registry schema + broader schema/code parity |
| Wizard | **7/10** | 10 interactive flows; profile selection implemented; registry integration via --hub-mode; tool/threshold/repo wizards added |
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

| System | Status | Details |
|-----------------------|--------------|------------------------------------------------------------------------------|
| Config Loading | [x] WORKING | 3-tier merge chain functions correctly |
| Boolean Normalization | [x] WORKING | `tool: true` → `tool: {enabled: true}` works |
| Wizard | [x] WORKING | Creates configs, connected to registry via `--hub-mode` (Phase 4.1) |
| Registry CLI | [x] WORKING | Full management commands: profile/registry/tool/threshold/repo (Phase 5) |
| Wizard ↔ Registry | [x] WORKING | Connected via `services/configuration.py` + `--hub-mode` flag (Phase 4.1, 2026-01-10) |
| Registry → YAML Sync | [x] WORKING | Full field sync via `sync_to_configs()` with sparse storage (Phase 2-3) |
| Profiles | [x] WORKING | 12 profiles surfaced in wizard via `wizard/questions/profile.py` (Phase 4.2, 2026-01-10) |

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
12. **Safe filenames/artifacts** - keep `config_basename` as identity, but use `config_basename_safe` (slashes → `-`) for filenames and artifact names.

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
┌─────────────┐ ┌─────────────┐ ┌──────────────────┐
│ Wizard │────▶│ config/ │ │ registry.json │
│ (cihub new) │ │ repos/*.yaml│ │ (3 values only) │
└─────────────┘ └─────────────┘ └──────────────────┘
 │ │
 ▼ ▼
 MAY WRITE USED BY CI
 .ci-hub.yml engine
 directly (registry ignored)
```

### 1.2 Correct Data Flow (TARGET)

```
┌─────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Wizard/CLI │────▶│ registry.json │────▶│ config/repos/ │
│ (services) │ │ (non-defaults) │ │ *.yaml │
└─────────────┘ └──────────────────┘ └──────────────────┘
 │ │ │
 ▼ ▼ ▼
 repo-side apply SOURCE OF load_config
 (explicit) TRUTH merge chain
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

**Status:** [x] **RESOLVED in Phase 0.1**

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
| `mutmut.min_score` alias not normalized/deprecated | schema/ci-hub-config.schema.json (mutmut), config/normalize.py | [x] Fixed: alias normalized to `min_mutation_score`; schema marks `min_score` deprecated |
| Missing `cihub` block | schema/ci-hub-config.schema.json, config/loader/inputs.py | [x] Fixed: schema now includes `cihub` and inputs are robust to invalid shapes |
| Schema defaults disagree with defaults.yaml (`mutmut.enabled`) | schema/ci-hub-config.schema.json, config/defaults.yaml | [x] Fixed: defaults aligned (mutmut disabled by default) |
| `python.tools.trivy.fail_on_cvss` not in schema but read in inputs | schema/ci-hub-config.schema.json, config/loader/inputs.py | [x] Fixed: schema includes `fail_on_cvss` and defaults provide a value |

### 2.5 Registry Bypass in CLI/Wizard

**Status:** [x] **RESOLVED** (2026-01-12)

**Previous:** `cihub new` wrote `config/repos/*.yaml` directly, wizard edited configs without touching registry.

**Current:**
- `cihub new --use-registry` writes via registry service with sync to config files
- `cihub new --interactive` uses wizard as confirmation (no `--yes` required)
- Direct writes (`cihub new --yes`) still available for backward compatibility
- `cihub init` continues to write `.ci-hub.yml` (repo-side config, not hub-managed)

### 2.6 Hardcoded Tools in Workflow (Fixed in Phase 1.5)

**File:** `.github/workflows/hub-production-ci.yml`

**Fix implemented:** Workflow now calls CLI wrappers (no raw tool invocations).

| Tool | Previous | Now |
|-------------|---------------------------|------------------------------------------|
| Ruff format | `ruff format --check ...` | `python -m cihub hub-ci ruff-format ...` |
| mypy | `mypy ...` | `python -m cihub hub-ci mypy ...` |
| yamllint | `yamllint ...` | `python -m cihub hub-ci yamllint ...` |

### 2.7 Wizard Doesn't Use Profiles

**Current:** Wizard asks 15+ individual tool questions; profiles are only applied when passed in (e.g., `cihub new --profile`).
**Target:** Profile selection → pre-filled checkboxes → customize

### 2.8 JSON Purity Gaps

**Fixed:** Setup now rejects `--json` with a CommandResult error, and JSON purity contract tests exist (representative sample).

### 2.9 Tiers / Profiles / Thresholds Profile Mapping (RESOLVED 2026-01-09)

**Status:** [x] **RESOLVED** - Canonical mapping defined and tier profiles created.

**Solution:**
- **Tiers** (strict/standard/relaxed) are language-agnostic quality levels that set thresholds
- **Profiles** (fast/quality/security/minimal/compliance/coverage-gate) are language-specific tool configurations
- **Tier profiles** (`templates/profiles/tier-strict.yaml`, `tier-relaxed.yaml`) provide threshold overrides only
- **Language profiles** (`python-fast.yaml`, `java-quality.yaml`, etc.) provide tool enablement

**Canonical Mapping:**

| Tier | Threshold Profile | Description |
|------|-------------------|-------------|
| `strict` | `tier-strict` | Coverage ≥85%, mutation ≥80%, zero tolerance for vulns |
| `standard` | (defaults) | Coverage ≥70%, mutation ≥70%, balanced gates |
| `relaxed` | `tier-relaxed` | Coverage ≥50%, mutation ≥40%, permissive for legacy |

**Composition:** A repo config is built from: `defaults` → `language profile` (optional) → `tier profile` → `repo overrides`

### 2.10 Missing CLI Capabilities (Audit Required)

The current missing-command list is stale. Re-audit the CLI surface and align to the target command set in Part 7.

---

## Part 3: Tool Inventory

Defaults shown below reflect **defaults.yaml** (current effective defaults). Schema defaults are aligned as of Phase 1.7.

### 3.1 Python Tools (14)

| Tool | Key Settings | Default |
|------------|----------------------------------------------------|--------------------------------------|
| pytest | enabled, min_coverage, fail_fast | enabled=true, min_coverage=70 |
| ruff | enabled, fail_on_error, max_errors | enabled=true |
| black | enabled, fail_on_format_issues, max_issues | enabled=true |
| isort | enabled, fail_on_issues, max_issues | enabled=true |
| mypy | enabled, require_run_or_fail | enabled=false |
| bandit | enabled, fail_on_high/medium/low | enabled=true, fail_on_high=true |
| pip_audit | enabled, fail_on_vuln | enabled=true |
| mutmut | enabled, min_mutation_score (min_score deprecated) | enabled=false, min_mutation_score=70 |
| hypothesis | enabled | enabled=true |
| semgrep | enabled, fail_on_findings | enabled=false |
| trivy | enabled, fail_on_critical/high | enabled=false |
| codeql | enabled, languages | enabled=false |
| docker | enabled, compose_file | enabled=false |
| sbom | enabled, format | enabled=false |

### 3.2 Java Tools (12)

| Tool | Key Settings | Default |
|------------|----------------------------------------------|-------------------------------|
| jacoco | enabled, min_coverage | enabled=true, min_coverage=70 |
| checkstyle | enabled, fail_on_violation | enabled=true |
| spotbugs | enabled, fail_on_error, max_bugs | enabled=true |
| pmd | enabled, fail_on_violation | enabled=true |
| owasp | enabled, fail_on_cvss | enabled=true, fail_on_cvss=7 |
| pitest | enabled, min_mutation_score | enabled=true |
| jqwik | enabled | enabled=false |
| semgrep | enabled, fail_on_findings | enabled=false |
| trivy | enabled, fail_on_critical/high, fail_on_cvss | enabled=false |
| codeql | enabled, languages | enabled=false |
| docker | enabled, compose_file | enabled=false |
| sbom | enabled, format | enabled=false |

### 3.3 Global Thresholds

| Field | Type | Default |
|-----------------------|-----------------|---------|
| coverage_min | integer (0-100) | 70 |
| mutation_score_min | integer (0-100) | 70 |
| max_critical_vulns | integer | 0 |
| max_high_vulns | integer | 0 |
| max_pip_audit_vulns | integer | 0 |
| owasp_cvss_fail | float (0-10) | 7.0 |
| trivy_cvss_fail | float (0-10) | 7.0 |
| max_semgrep_findings | integer | 0 |
| max_ruff_errors | integer | 0 |
| max_black_issues | integer | 0 |
| max_isort_issues | integer | 0 |
| max_checkstyle_errors | integer | 0 |
| max_spotbugs_bugs | integer | 0 |
| max_pmd_violations | integer | 0 |

---

## Part 4: Wizard Profile-First Design (ADR-0051)

### 4.1 Design Decision

Profiles are a **starting point**, then ALWAYS show checkboxes for customization.

**Key principle:** Profiles are defaults/templates, not restrictions. Users ALWAYS have full control via checkboxes.

### 4.2 Complete Wizard Flow Mockup

```
┌─────────────────────────────────────────────────────────-────┐
│ CIHub Setup Wizard │
├───────────────────────────────────────────────────────-──────┤
│ │
│ Step 1: Project Detection │
│ ──────────────────────── │
│ [x] Detected: Python (pyproject.toml) │
│ │
│ Step 2: Select CI Profile │
│ ───────────────────────── │
│ Profiles determine your default tool selection and │
│ quality gates. You can customize after selecting. │
│ │
│ ○ Fast (Recommended) │
│ pytest, ruff, black, bandit, pip-audit (~5 min) │
│ │
│ ○ Quality │
│ Fast + mypy, mutmut (~20 min) │
│ │
│ ○ Security │
│ bandit, pip-audit, semgrep, trivy, codeql (~30 min) │
│ │
│ ○ Start from scratch │
│ Configure each tool individually │
│ │
│ Step 3: Customize Tools (always shown) │
│ ────────────────────────────────────── │
│ Pre-filled based on "Fast" profile. Toggle to customize: │
│ │
│ pytest ruff black │
│ isort mypy bandit │
│ pip-audit mutmut semgrep │
│ trivy codeql sbom │
│ │
│ Step 4: Quality Gates │
│ ───────────────────── │
│ Based on "Fast" profile defaults: │
│ │
│ Min coverage: [70]% │
│ Fail on high: [Yes] │
│ Format mode: ○ Check ○ Fix │
│ │
│ Step 5: Preview & Confirm │
│ ───────────────────────── │
│ Files to create: │
│ • .ci-hub.yml │
│ • .github/workflows/hub-ci.yml │
│ │
│ [Preview .ci-hub.yml] [Create Files] [Cancel] │
│ │
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
| 4.1 | Wizard uses shared service layer via `--use-registry`/`--hub-mode`; local-only mode still writes directly | wizard/core.py, services/configuration.py | Flow tests |
| 4.2 | Add profile selection step | wizard/questions/profile.py | Flow tests |
| 4.3 | Keep checkboxes after profile + add format mode choice | wizard/questions/python_tools.py, wizard/questions/format_mode.py | Interaction tests |
| 4.4 | Expose non-tool settings (repo metadata, gates, reports, notifications, harden_runner) | wizard/questions/* | Flow tests |
| 4.5 | Setup wizard uses registry + optional repo-side apply | commands/setup.py | E2E tests |

### Phase 5: CLI Management Commands (Week 5)

| # | Task | Commands | Priority |
|---|------|----------|----------|
| 5.1 | Profile management | create, list, show, edit, delete, import, export | CRITICAL |
| 5.2 | Registry management | remove, bootstrap, import/export | CRITICAL |
| 5.3 | Tool management | list, enable, disable, configure, status, validate | HIGH |
| 5.4 | Threshold management | get, set, list, reset, compare | HIGH |
| 5.5 | Repo management | list, update, migrate, clone, verify-connectivity | MEDIUM |

### Phase 6: Schema & Extensibility (Week 6)

| # | Task | Files | Tests |
|---|------|-------|-------|
| 6.1 | Enable custom tools (x- prefix) end-to-end (schema, normalize, tool registry, report/triage/validator) | schema, normalize.py, tools/registry.py, services/triage | Custom tool tests |
| 6.2 | Update command contracts + generated docs for new CLI surface | CLI_COMMAND_AUDIT.md, docs/reference | Contract tests |

---

## Part 6: Comprehensive Test Matrix

### 6.1 Repo Shape Matrix

Every CLI command must be tested across these configurations:

| Repo Shape | Structure | Key Files | Status |
|------------|-----------|-----------|--------|
| `python-pyproject` | Single Python at root | `pyproject.toml` | ✓ Implemented |
| `python-setup` | Legacy setup.py | `setup.py` | ✓ Implemented |
| `java-maven` | Maven at root | `pom.xml` | ✓ Implemented |
| `java-gradle` | Gradle at root | `build.gradle` | ✓ Implemented |
| `monorepo` | Java + Python subdirs | `java/`, `python/` | ✓ Implemented |
| `python-subdir` | Python in subdirectory | `services/backend/pyproject.toml` | Future |
| `java-subdir` | Java in subdirectory | `services/api/pom.xml` | Future |
| `java-multi-module` | Parent POM + modules | `pom.xml`, `module-a/`, `module-b/` | Future |
| `empty-repo` | Empty git repo | `.git/` only | Edge case |
| `no-git` | No git | No `.git/` | Edge case |

> **Note (2026-01-12):** Core 5 shapes implemented via `cihub scaffold`. Additional shapes can be added as edge cases surface.

### 6.2 Command × Repo Shape Requirements

```
┌────────────────────┬─────────┬─────────┬───────┬────────┬─────────┬─────────┬─────────┬───────────┬───────┬────────┐
│ Command │ py-root │ py-setup│ java-m│ java-g │ monorepo│ py-sub │ java-sub│ java-multi│ empty │ no-git │
├────────────────────┼─────────┼─────────┼───────┼────────┼─────────┼─────────┼─────────┼───────────┼───────┼────────┤
│ cihub detect │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │
│ cihub init │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ E │ E │
│ cihub validate │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ E │ E │
│ cihub ci │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ E │ E │
│ cihub check │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ E │ E │
│ cihub triage │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ E │ E │
│ cihub setup │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │ [x] │
│ cihub scaffold │ [x] │ [x] │ [x] │ [x] │ [x] │ N/A │ N/A │ N/A │ [x] │ [x] │
└────────────────────┴─────────┴─────────┴───────┴────────┴─────────┴─────────┴─────────┴───────────┴───────┴────────┘

Legend: [x] = Must pass, E = Expected error (graceful), N/A = Not applicable
```

### 6.3 Sync Verification Matrix

| Sync Point | Current Status | Tests Required |
|------------|----------------|----------------|
| Wizard → Registry | [x] WORKING | test_wizard_flows/ (37 tests) |
| Registry → config/repos | [x] WORKING | test_registry/ sync tests (9 tests) |
| defaults + config/repos + .ci-hub.yml → load_config | [x] WORKING | test_config_precedence/ (8 tests) |
| Registry bootstrap (configs → registry) | [x] WORKING | test_registry/ bootstrap tests |
| YAML → Workflow | [x] WORKING | test_templates.py contract tests |
| Schema ↔ Code | [x] WORKING | test_schema_validation/ (13 tests) |
| Profile ↔ Registry | [x] WORKING | test_wizard_flows/test_profile_selection.py (6 tests) |
| Thresholds ↔ Gates | [x] WORKING | test_ci_engine.py gate evaluation (124 tests) |

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
cihub registry remove <name> --yes [--delete-config]
cihub registry diff [--repo <name>]
cihub registry sync [--dry-run]
cihub registry bootstrap --configs-dir config/repos [--include-thresholds] [--dry-run] [--strategy merge|replace|prefer-registry|prefer-config]
cihub registry import --file backup.json [--merge|--replace]
cihub registry export --output backup.json
```

### 7.3 Repository Management (MEDIUM)

```bash
cihub repo list [--language] [--format json]
cihub repo update <name> --owner myorg --default-branch main
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

### 7.6 Import/Export (HIGH) [x] **SATISFIED via subcommands**

> **Note (2026-01-12):** Top-level `cihub export/import` commands were deemed unnecessary. Functionality is provided via domain-specific subcommands which offer better semantics and validation.

**Implemented via subcommands:**
- `cihub registry export --output FILE` - Export full registry to file
- `cihub registry import --file FILE [--merge|--replace] [--dry-run]` - Import registry
- `cihub profile export <name> --output FILE` - Export profile to file
- `cihub profile import --file FILE [--name] [--force]` - Import profile

**Repo export/import:** Extract individual repos from registry export JSON or copy YAML files directly from `config/repos/`.

---

## Part 8: Test Implementation

### 8.1 New Test File Structure

> **Status (2026-01-12):** Core test directories created with comprehensive tests. Counts verified via AST analysis.

```
tests/
├── test_repo_shapes/               # Repo shape matrix tests (26 tests)
│   ├── conftest.py                 # ✓ Repo shape fixtures (5 shapes)
│   ├── test_ci_shapes.py           # ✓ CI shape tests (6 tests)
│   ├── test_detect_shapes.py       # ✓ Detection tests across shapes (10 tests)
│   └── test_init_shapes.py         # ✓ Init tests across shapes (10 tests)
├── test_wizard_flows/              # Wizard flow tests (37 tests)
│   ├── __init__.py
│   ├── test_profile_selection.py   # ✓ Profile/tier/WizardResult tests
│   ├── test_cli_wizard_parity.py   # ✓ Config structure parity tests
│   └── test_wizard_modules.py      # ✓ profile.py, advanced.py module tests
├── test_registry/                  # Registry tests (9 tests)
│   ├── __init__.py
│   └── test_registry_service.py    # ✓ list_repos, thresholds, sync, diff, bootstrap
├── test_config_precedence/         # Merge order tests (8 tests)
│   ├── __init__.py
│   └── test_merge_order.py         # ✓ deep_merge, tier overrides, tool_enabled
├── test_schema_validation/         # Schema validation tests (13 tests)
│   ├── __init__.py
│   └── test_schema_fields.py       # ✓ Schema structure, customTool, patternProperties
├── test_custom_tools.py            # Custom tool tests (35 tests)
└── existing tests...               # 2550+ additional tests
```

**Future expansion (as needed):**
- `test_wizard_flows/test_checkbox_interaction.py` - Interactive wizard mocking
- `test_registry/test_registry_properties.py` - Hypothesis property tests
- `test_schema_validation/test_schema_evolution.py` - Migration tests

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

### Phase 0: Safety + JSON Purity [x]

- [x] 0.1 Fix registry threshold key mapping to schema
- [x] 0.2 Enforce JSON purity (interactive commands reject `--json`; no stdout prints in JSON mode)
- [x] 0.3 Add JSON purity contract tests

### Phase 1: Workflow Parity Hardening [x]

- [x] 1.1 Normalize min_score alias → min_mutation_score + deprecate
- [x] 1.2 Add hub-ci ruff format wrapper
- [x] 1.3 Create hub-ci mypy command
- [x] 1.4 Create hub-ci yamllint command
- [x] 1.5 Replace hardcoded workflow tools
- [x] 1.6 Add `cihub` block to schema
- [x] 1.7 Align schema defaults with defaults.yaml (mutmut/trivy)
- [x] 1.8 Resolve python trivy CVSS decision (tool-level vs thresholds)

### Phase 2: Registry Schema + Service

- [x] 2.1 Expand registry.schema.json with allowlisted keys
- [x] 2.2a Add sparse config fragment audit (defaults/profile baseline)
- [x] 2.2 Rewrite registry_service.py for full config scope (sparse storage) (2026-01-09: expanded to all 14 threshold fields)
- [x] 2.3 Implement full sync to config/repos (2026-01-09: verified via roundtrip tests - all 12 managedConfig keys synced)
- [x] 2.3a Sync tier/repo config fragments into config/repos (managedConfig; includes tier profile merge)
- [x] 2.3b Orchestrator-safe dispatch artifacts for nested config basenames (config_basename_safe)
- [x] 2.4a Diff surfaces managedConfig drift via dry-run sync (non-threshold keys + thresholds) + cross-root --configs-dir handling
- [x] 2.4b Diff flags orphan config/repos YAMLs + unmanaged top-level keys (allowlist-driven)
- [x] 2.4 Diff surfaces .ci-hub.yml overrides + non-tool drift (2026-01-09: `compute_diff()` accepts `repo_paths`, CLI wired via `--repos-root`)
- [x] 2.5 Define canonical tier/profile/thresholds_profile mapping (2026-01-09: tier profiles created)

### Phase 3: Registry Bootstrap & Drift

- [x] 3.1 Add registry bootstrap/import command with --dry-run (2026-01-10)
- [x] 3.2 Implement conflict strategies + audit report (2026-01-10: in bootstrap_from_configs)
- [x] 3.3 Add drift report across registry/config/repos/.ci-hub.yml (2026-01-10: in compute_diff)

### Phase 4: Wizard Parity + Profile Integration

- [x] 4.1 Wizard uses shared service layer when `--use-registry` or `--hub-mode` is set (2026-01-10: `services/configuration.py` with `create_repo_via_registry()`, 2026-01-12: `--use-registry` flag exposed in `cihub new`). Note: Local-only mode (`init`, `config edit` without flags) still writes directly for standalone use.
- [x] 4.2 Add profile selection step (2026-01-10: `wizard/questions/profile.py` with `select_profile()` + `select_tier()`)
- [x] 4.3 Keep checkboxes after profile + format mode choice (2026-01-10: profile merged before tool prompts)
- [x] 4.4 Expose non-tool settings in wizard (2026-01-10: `wizard/questions/advanced.py` with gates/reports/notifications/harden_runner)
- [x] 4.5 Setup wizard uses registry + optional repo-side apply (2026-01-10: `--hub-mode` flag in setup command)

**Phase 4 Code Review Fixes (2026-01-10):**
- Fixed: WizardResult return type handling in init.py, config_cmd.py (extract `.config`)
- Fixed: sync_to_configs argument order and return type (list, not dict)
- Fixed: --hub-mode/--tier parser wiring in repo_setup.py
- Fixed: --tier default=None to allow wizard tier selection
- Fixed: Sparse threshold calculation includes tier profile thresholds
- Fixed: Registry key uses wizard repo_name (not CLI arg)
- Fixed: synced=True only when action != "skip" in create/update_repo_via_registry
- Fixed: setup.py hub-mode uses wizard_result.repo_name for registry key (not repo_path.name)
- Fixed: sync_to_configs now creates missing config files for new repos (action="created")
- Fixed: _prompt_profile_and_tier accepts skip_tier param to avoid prompting when tier pre-selected
- Fixed: sync_to_configs guards creation - requires repo.owner/repo.name/language for valid configs
- Fixed: compute_diff recognizes would_create action and reports missing config files
- Fixed: registry_cmd.py sync counts created/would_create in summary and files_modified
- Fixed: Guard checks both top-level language AND config.repo.language (canonical after normalization)
- Fixed: New config creation sets language from registry top-level as fallback to repo.language
- Fixed: Defensive checks for malformed registry entries (config: null won't raise AttributeError)

### Phase 5: CLI Management Commands

- [x] 5.1 Profile management commands (complete)
  - [x] `profile list [--language] [--type]` - list available profiles
  - [x] `profile show <name> [--effective]` - show profile details
  - [x] `profile create <name> [--from-profile] [--from-repo] [--force]` - create new profile
  - [x] `profile edit <name> [--wizard] [--enable] [--disable] [--set]` - edit profile (wizard mode implemented 2026-01-12)
  - [x] `profile delete <name> [--force]` - delete profile
  - [x] `profile export <name> --output FILE` - export profile to file
  - [x] `profile import --file FILE [--name] [--force]` - import profile from file
  - [x] `profile validate <name> [--strict]` - validate profile
- [x] 5.2 Registry management extensions (complete)
  - [x] `registry add --owner/--name/--language` flags for sync-ready entries
  - [x] Schema compliance: `--name` requires `--owner` (both-or-none per registry.schema.json)
  - [x] `registry remove` command with `--delete-config` and `--yes` flags
  - [x] `registry import/export` commands with `--merge`/`--replace` and `--dry-run`
- [x] 5.3 Tool management commands (complete)
  - [x] `tool list [--language] [--category] [--repo] [--enabled-only]` - list tools
  - [x] `tool enable <tool> [--for-repo] [--all-repos] [--profile]` - enable tool (supports custom x-* tools 2026-01-12)
  - [x] `tool disable <tool> [--for-repo] [--all-repos] [--profile]` - disable tool (supports custom x-* tools 2026-01-12)
  - [x] `tool configure <tool> <param> <value> [--repo] [--profile] [--wizard]` - configure tool (supports custom x-* tools 2026-01-12, wizard mode 2026-01-14)
  - [x] `tool status [--repo] [--all] [--language]` - show tool status
  - [x] `tool validate <tool> [--install-if-missing]` - validate installation
  - [x] `tool info <tool>` - show detailed tool info (supports custom x-* tools 2026-01-12)
  - [x] Tool commands honor `config.repo.language` (canonical) and reject mismatched tool/language targets (2026-01-10)
- [x] 5.4 Threshold management commands (2026-01-10)
  - [x] `threshold get [<key>]` - get threshold value(s) with `--repo`, `--tier`, `--effective`
  - [x] `threshold set <key> <value>` - set threshold with `--repo`, `--tier`, `--all-repos`
  - [x] `threshold list` - list all thresholds with descriptions, `--category`, `--diff`
  - [x] `threshold reset [<key>] [--wizard]` - reset to default with `--repo`, `--tier`, `--all-repos` (wizard mode 2026-01-14)
  - [x] `threshold compare <repo1> <repo2>` - compare thresholds between repos
- [x] 5.5 Repo management commands (2026-01-10)
  - [x] `repo list` - list repos with `--language`, `--tier`, `--with-overrides`
  - [x] `repo show <name>` - show detailed repo info with `--effective`
  - [x] `repo update <name>` - update metadata (owner, branch, language, tier, dispatch_enabled)
  - [x] `repo migrate <from> <to>` - migrate/rename with `--delete-source`, `--force`
  - [x] `repo clone <source> <dest>` - clone repo config
  - [x] `repo verify-connectivity <name>` - verify GitHub access with `--check-workflows`

### Phase 6: Schema & Extensibility

- [x] 6.1 Enable custom tools (x- prefix) end-to-end (2026-01-11)
  - [x] Added `customTool` definition to schema with boolean/object oneOf
  - [x] Added `patternProperties` with `^x-[a-zA-Z0-9_-]+$` pattern to javaTools and pythonTools
  - [x] Added helper functions in `tools/registry.py`: `is_custom_tool()`, `get_custom_tools_from_config()`, `get_all_tools_from_config()`, `is_tool_enabled()`, `get_custom_tool_command()`
  - [x] Custom tool execution in `python_tools.py` and `java_tools.py` with `fail_on_error` support
  - [x] Report building uses `get_all_tools_from_config()` to include custom tools
  - [x] `CIHUB_RUN_*` env overrides work for custom tools (pattern: `x-my-tool` → `CIHUB_RUN_X_MY_TOOL`)
  - [x] `fail_on_error=true` emits "error" severity (affects CI exit code)
  - [x] Verified normalization preserves custom tools
  - [x] Added 35 tests in `tests/test_custom_tools.py` (including `TestCustomToolExecution` with 7 execution path tests)
- [x] 6.2 Update command contracts + generated docs (2026-01-11)
  - [x] Regenerated CLI.md, CONFIG.md, WORKFLOWS.md via `cihub docs generate`
  - [x] Updated CLI help snapshot

### Test Implementation

- [x] Create test_repo_shapes/ with fixtures (2026-01-11: exists with conftest.py, test_ci_shapes.py)
- [x] Create test_wizard_flows/ (2026-01-12: 37 tests for profile selection, tier mapping, WizardResult, CLI parity)
- [x] Create test_registry/ (2026-01-12: 9 tests for list_repos, thresholds, sync, diff, bootstrap)
- [x] Create test_config_precedence/ (2026-01-12: 8 tests for deep_merge, tier overrides, tool_enabled)
- [x] Create test_cli_contracts/ (JSON purity)
- [x] Create test_schema_validation/ (2026-01-12: 13 tests for schema structure, customTool, patternProperties)
- [x] Add CLI/wizard parity tests (2026-01-12: 12 tests for config structure, merge, tool enablement, output format)
- [x] Add registry bootstrap + drift tests
- [x] Add created/would_create path tests (sync_to_configs, compute_diff, malformed entry handling)
- [x] Add registry add command tests (--owner/--name/--language flags, end-to-end sync flow)
- [x] Add registry remove command tests (confirmation, removal, not-found, delete-config)
- [x] Add registry import/export tests (merge, replace, dry-run, validation guards)
- [x] Add profile management CLI tests (parser contracts, snapshots updated)
- [x] Add tool management CLI tests (parser contracts, snapshots updated)
- [x] Add custom tool execution tests (2026-01-11: TestCustomToolExecution with returncode, fail_on_error, env overrides)
- [x] Add Phase 4 wizard module tests (2026-01-12: 19 tests for profile.py, advanced.py, language, security, thresholds)
- [x] Run full test matrix (2026-01-14: 2716 passed, 0 failed)

---

## Part 10: Quick Wins (< 1 hour each)

1. [x] Add `--json` guard for interactive commands (setup)
2. [x] Fix registry threshold key mapping to schema
3. [x] Normalize `min_score` → `min_mutation_score`, align hub-ci mutmut args
4. [x] Add hub-ci ruff format wrapper (subcommand or flag)
5. [x] Add `cihub` block to schema (debug/triage toggles)
6. [x] Add inline comments to scaffold output files (templates already include tool guidance headers)
7. [x] Document all `CIHUB_*` env toggles in one place (docs/reference/ENV.md)
8. [x] Add "See Also" to command help text (cli_parsers/common.py:see_also_epilog)

---

## Related Documents

- `docs/adr/0051-wizard-profile-first-design.md` - ADR for profile-first design
- `docs/development/MASTER_PLAN.md` - Overall priority tracking
- `docs/development/archive/CLEAN_CODE.md` - Architecture improvements (Priority #1)

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
| `min_score` mismatch | [x] Fixed: deprecated alias normalized to `min_mutation_score` |
| Missing `cihub` block | [x] Fixed: schema now includes `cihub` debug/triage toggles |
| Registry keys | Registry normalizes legacy keys to schema-aligned keys on load/save; still limited to a small threshold subset |

### A.3 Wizard Audit Results (Corrected)

**Methodology:** Trace wizard flow in `cihub/wizard/` and compare to CLI commands

| Metric | Count |
|--------|-------|
| Commands with wizard support | **12** of 106+ |
| Profile selection | [x] Implemented (2026-01-10: `select_profile()`, `select_tier()` in wizard/questions/profile.py) |
| Registry integration | [x] Implemented (2026-01-10: `--hub-mode` uses `create_repo_via_registry()`) |

**Wizard-supported commands:**
1. `cihub setup` - Full workflow wizard (with `--hub-mode` for registry integration)
2. `cihub init --wizard` - Config wizard
3. `cihub new --interactive` - Config creation
4. `cihub config edit` - Config editing
5. `cihub profile edit --wizard` - Profile editing (2026-01-12)
6. `cihub tool enable --wizard` - Tool enablement (2026-01-12)
7. `cihub tool disable --wizard` - Tool disablement (2026-01-12)
8. `cihub tool configure --wizard` - Tool configuration (2026-01-14)
9. `cihub registry add --wizard` - Registry add (2026-01-12)
10. `cihub threshold set --wizard` - Threshold setting (2026-01-12)
11. `cihub threshold reset --wizard` - Threshold reset with tier support (2026-01-14)
12. `cihub repo update --wizard` - Repo metadata update (2026-01-12)

**Wizard parity improvements (2026-01-12):**
- [x] **Tool sourcing fixed:** `wizard/questions/python_tools.py` and `java_tools.py` now source tools from `tools/registry.py` (CLI source of truth). Custom x-* tools from config are also included.
- [x] **Profile discovery fixed:** `wizard/questions/profile.py` now scans `templates/profiles/` directory instead of hard-coded list. New profiles automatically appear in wizard.
- [x] **Tool wizard added:** `cihub tool enable --wizard` and `cihub tool disable --wizard` provide interactive tool management.
- [x] **JSON purity enforced:** `profile edit --wizard --json` now correctly rejected with EXIT_USAGE.
- [x] **Registry add wizard added:** `cihub registry add --wizard` provides interactive repo registration with tier/description/owner/language prompts.
- [x] **Threshold set wizard added:** `cihub threshold set --wizard` provides interactive threshold setting with key selection from `THRESHOLD_METADATA`, value input, and target (repo/tier/all-repos) selection.
- [x] **Repo update wizard added:** `cihub repo update --wizard` provides interactive repo metadata updates with multi-select field editing.

**Wizard code review fixes (2026-01-14):**
- [x] **Tool configure wizard added:** `cihub tool configure --wizard` provides interactive tool configuration with custom x-* tools included, profile scanning via `hub_root() / "templates" / "profiles"`.
- [x] **Tool configure JSON purity:** `tool configure --wizard --json` now correctly rejected with EXIT_USAGE (was missing guard).
- [x] **Threshold reset wizard added:** `cihub threshold reset --wizard` provides interactive threshold reset with key selection (or reset all), and target selection including tier support.
- [x] **Threshold reset tier support:** `_wizard_reset()` now offers repo, tier, and all-repos targets (was missing tier selection).

**Remaining wizard parity gaps (v1.1+ backlog):**
- Registry list/remove/bootstrap - read-only or destructive operations (wizard not needed)
- Threshold get/list/compare - read-only operations (wizard not needed)
- Repo list/show/migrate/clone/verify - read-only or specialized operations (wizard optional)

### A.4 Workflow Audit Results (Agent 4)

**Methodology:** Grep for raw tool invocations in `.github/workflows/*.yml`

| Workflow | Status | Issues |
|----------|--------|--------|
| python-ci.yml | [x] COMPLIANT | All tools via CLI |
| java-ci.yml | [x] COMPLIANT | All tools via CLI |
| hub-ci.yml | [x] COMPLIANT | Pure routing |
| hub-production-ci.yml | [x] COMPLIANT | All tools via CLI (ruff-format/mypy/yamllint wrappers) |

### A.5 User Journey Audit Results (Agent 5)

| Journey | Score | Key Gaps |
|---------|-------|----------|
| New User Onboarding | 6/10 | Setup wizard incomplete |
| Existing Repo Migration | 3/10 | **No migration tooling** |
| Day-to-Day Usage | 7/10 | Triage hard to discover |
| Configuration Changes | 6/10 | No config diff preview |
| Troubleshooting | 7/10 | No diagnostic bundle |

### A.6 Test Directory Status

**Proposed directories in Part 8 - current status (2026-01-12):**

```
tests/test_repo_shapes/       → EXISTS (26 tests: test_detect_shapes.py=10, test_ci_shapes.py=6, test_init_shapes.py=10)
tests/test_wizard_flows/      → EXISTS (37 tests: test_wizard_modules.py=19, test_cli_wizard_parity.py=12, test_profile_selection.py=6)
tests/test_registry/          → EXISTS (9 tests: test_registry_service.py=9)
tests/test_config_precedence/ → EXISTS (8 tests: test_merge_order.py=8)
tests/test_schema_validation/ → EXISTS (13 tests: test_schema_fields.py=13)
tests/test_custom_tools.py    → EXISTS (35 tests including TestCustomToolExecution + Java tests)
```

**Test totals (AST-verified 2026-01-12):**
- test_repo_shapes: 26 tests
- test_wizard_flows: 37 tests
- test_registry: 9 tests
- test_config_precedence: 8 tests
- test_schema_validation: 13 tests
- test_custom_tools: 35 tests
- **Total new directory tests:** 128 tests

**Note:** Earlier count of 159 was incorrect; AST analysis confirms 128 tests in new directories.
