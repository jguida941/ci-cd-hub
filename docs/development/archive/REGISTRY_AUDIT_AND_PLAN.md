# Registry System Audit and Implementation Plan

> **WARNING: SUPERSEDED:** This document has been consolidated into `docs/development/active/SYSTEM_INTEGRATION_PLAN.md` (2026-01-08)

**Date:** 2026-01-06
**Priority:** **#2** (See [MASTER_PLAN.md](../MASTER_PLAN.md#active-design-docs---priority-order))
**Status:** ARCHIVED
**Depends On:** CLEAN_CODE.md (~90% complete)
**Blocks:** TEST_REORGANIZATION.md (validates registry integration)
**Audit Method:** 8-agent comprehensive codebase analysis

---

## Executive Summary

The registry system exists but is **disconnected and incomplete**. This document presents findings from a comprehensive 8-agent audit of the entire codebase, including workflows, wizard, CLI commands, config loading, and schemas.

### Key Findings

| System | Status | Details |
|--------|--------|---------|
| Config Loading | [x] WORKING | 3-tier merge chain functions correctly |
| Boolean Normalization | [x] WORKING | `tool: true` → `tool: {enabled: true}` works |
| Wizard | [x] WORKING | Creates configs, 3 entry points |
| Registry CLI | WARNING: PARTIAL | Commands exist but only track 3 values |
| Wizard ↔ Registry | [ ] BROKEN | Not connected at all |
| Registry → YAML Sync | WARNING: PARTIAL | Only syncs 3 values, ignores 40+ others |
| Profiles | WARNING: UNUSED | 12 profiles exist but rarely used |

### Critical Corrections from Original Plan

| Original (WRONG) | Corrected |
|------------------|-----------|
| Hardcoded tiers (strict/standard/relaxed) | Per-repo settings, NO tiers block |
| Full tool definitions embedded in tiers | Use `$ref` to existing schema (no duplication) |
| 400+ lines of tier definitions | Sparse storage (only non-defaults) |
| Tier selection required in wizard | Profile selection OPTIONAL |
| `--tier` flag creates rigid system | `--profile` flag applies optional presets |

---

## Part 1: Current State Analysis

### 1.1 What's Actually Working

**Config Loading Chain** (`cihub/config/loader/core.py`):
```
defaults.yaml (LOWEST)
 ↓ deep_merge + normalize
config/repos/<name>.yaml (HUB OVERRIDE)
 ↓ deep_merge + normalize
.ci-hub.yml (REPO LOCAL - HIGHEST)
 ↓ validate against schema
EFFECTIVE CONFIG
```

**Boolean Shorthand Handling** (`cihub/config/normalize.py`):
- `pytest: true` → `pytest: {enabled: true}` [x]
- `chaos: true` → `chaos: {enabled: true}` [x]
- Applied at each merge layer [x]

**Wizard System** (`cihub/wizard/`):
- `cihub new --interactive` → Creates hub-side config
- `cihub init --wizard` → Creates repo-side .ci-hub.yml + workflow
- `cihub config edit` → Modifies existing config
- All three entry points functional [x]

**Registry CLI Commands** (`cihub/commands/registry_cmd.py`):
- `list`, `show`, `set`, `diff`, `sync`, `add` all implemented [x]

### 1.2 What's Broken/Incomplete

**Registry Only Tracks 3 Values** (`registry_service.py:69-72`):
```python
effective = {
 "coverage": overrides.get("coverage", tier_defaults.get("coverage", 70)),
 "mutation": overrides.get("mutation", tier_defaults.get("mutation", 70)),
 "vulns_max": overrides.get("vulns_max", tier_defaults.get("vulns_max", 0)),
}
```
- Ignores all 26 tool settings
- Ignores 12+ threshold fields
- Ignores all repo metadata beyond basic fields

**Wizard ↔ Registry Disconnect**:
- Wizard creates `config/repos/*.yaml` directly
- Never reads from or writes to registry.json
- Two systems operate independently

**Tier Definitions Are Empty** (`config/registry.json`):
```json
"tiers": {
 "strict": {
 "description": "Maximum quality gates",
 "profile": "tier-strict" // References non-existent file
 }
}
```
- No actual thresholds or tool settings
- Profile references don't resolve to real files
- Default thresholds hardcoded in Python (70, 70, 0)

**Sync Only Patches** (`sync_to_configs()`):
- Only updates 3 fields in existing YAML
- Doesn't generate complete configs
- Doesn't handle missing config files

---

## Part 2: CLI-First Architecture (Corrected)

### 2.1 Core Principle

**Registry is the CLI's database. YAML files are generated output.**

```
USER ACTION CLI COMMAND RESULT
─────────────────────────────────────────────────────────────────────
Onboard new repo → cihub new --interactive → registry.json updated
 → config/repos/*.yaml generated

Change settings → cihub registry set → registry.json updated
 → config/repos/*.yaml regenerated

View config → cihub registry show → Displays effective config

Check drift → cihub registry diff → Shows registry vs YAML differences

Apply changes → cihub registry sync → Regenerates all config/repos/*.yaml

Run CI → cihub ci (hub-run-all) → Reads config/repos/*.yaml
 → Runs tools per config

Init target repo → cihub init → Creates .ci-hub.yml in repo
 → Creates .github/workflows/hub-ci.yml
```

### 2.2 Data Flow (Corrected)

```
CURRENT (BROKEN):
┌─────────────┐ ┌─────────────┐ ┌──────────────────┐
│ Wizard │────▶│ config/ │ │ registry.json │
│ (cihub new) │ │ repos/*.yaml│ │ (3 values only) │
└─────────────┘ └─────────────┘ └──────────────────┘
 │ │ │
 ▼ ▼ ▼
 WRITES USED BY CI NOT CONNECTED
 directly engine TO ANYTHING


CORRECT (CLI-FIRST):
┌─────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Wizard │────▶│ registry.json │────▶│ config/repos/ │
│ (cihub new) │ │ (ALL settings) │ │ *.yaml │
└─────────────┘ └──────────────────┘ └──────────────────┘
 │ │ │
 ▼ ▼ ▼
 CREATES SOURCE OF GENERATED
 entry in TRUTH BY CLI
 registry (cihub registry sync)
```

---

## Part 3: Corrected Registry Structure

### 3.1 No Hardcoded Tiers

**Why tiers are wrong:**
1. Users can't create custom tiers
2. Users can't delete tiers they don't need
3. Creates rigid 3-level system
4. Duplicates what profiles already do

**Correct approach: Per-repo settings with optional profile presets**

### 3.2 Corrected registry.json

```json
{
 "$schema": "../schema/registry.schema.json",
 "schema_version": "cihub-registry-v2",
 "repos": {
 "canary-python": {
 "language": "python",
 "owner": "jguida941",
 "description": "Python canary repo for CI validation",
 "profile": "python-quality",
 "dispatch_enabled": true,
 "thresholds": {
 "coverage_min": 80
 },
 "python": {
 "tools": {
 "mypy": { "enabled": true },
 "mutmut": { "enabled": false }
 }
 }
 },
 "production-api": {
 "language": "python",
 "owner": "myorg",
 "description": "Production API - strict settings",
 "thresholds": {
 "coverage_min": 90,
 "mutation_score_min": 85,
 "max_critical_vulns": 0,
 "max_high_vulns": 0
 },
 "python": {
 "tools": {
 "semgrep": { "enabled": true, "fail_on_findings": true },
 "trivy": { "enabled": true, "fail_on_critical": true },
 "codeql": { "enabled": true }
 }
 }
 },
 "legacy-service": {
 "language": "java",
 "owner": "myorg",
 "description": "Legacy service - relaxed settings",
 "thresholds": {
 "coverage_min": 50,
 "mutation_score_min": 0,
 "max_high_vulns": 5
 },
 "java": {
 "tools": {
 "pitest": { "enabled": false },
 "checkstyle": { "enabled": false }
 }
 }
 }
 }
}
```

**Key principles:**
1. **No `tiers` block** - each repo defines its own settings
2. **Optional `profile` reference** - applies a preset from `templates/profiles/`
3. **Sparse storage** - only stores NON-DEFAULT values
4. **Schema alignment** - `thresholds` and `python/java.tools` match `ci-hub-config.schema.json`

### 3.3 Corrected registry.schema.json

```json
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "CIHub Registry",
 "type": "object",
 "required": ["schema_version", "repos"],
 "properties": {
 "schema_version": {
 "type": "string",
 "pattern": "^cihub-registry-v\\d+$"
 },
 "repos": {
 "type": "object",
 "additionalProperties": { "$ref": "#/$defs/repo" }
 }
 },
 "$defs": {
 "repo": {
 "type": "object",
 "required": ["language"],
 "properties": {
 "language": { "enum": ["python", "java"] },
 "owner": { "type": "string" },
 "description": { "type": "string" },
 "profile": {
 "type": "string",
 "description": "Optional profile from templates/profiles/ (without .yaml)"
 },
 "dispatch_enabled": { "type": "boolean", "default": true },
 "default_branch": { "type": "string", "default": "main" },
 "thresholds": { "$ref": "ci-hub-config.schema.json#/definitions/thresholds" },
 "python": { "$ref": "ci-hub-config.schema.json#/properties/python" },
 "java": { "$ref": "ci-hub-config.schema.json#/properties/java" }
 }
 }
 }
}
```

**Key:** Uses `$ref` to existing `ci-hub-config.schema.json` - NO duplication.

---

## Part 4: Corrected CLI Commands

### 4.1 Repo Onboarding

```bash
# Interactive wizard (creates registry entry + generates YAML)
cihub new my-repo --interactive

# CLI args (creates registry entry + generates YAML)
cihub new my-repo --owner myorg --language python --coverage 80

# With optional profile preset
cihub new my-repo --owner myorg --language python --profile python-quality

# The above commands:
# 1. Add entry to registry.json
# 2. Generate config/repos/my-repo.yaml
```

### 4.2 Repo Management

```bash
# View all repos
cihub registry list

# View effective config for a repo
cihub registry show my-repo
cihub registry show my-repo --effective # Shows merged defaults + profile + overrides

# Set threshold overrides
cihub registry set my-repo --coverage 90
cihub registry set my-repo --mutation 80
cihub registry set my-repo --max-critical-vulns 0

# Set tool overrides
cihub registry set my-repo --tool mypy --enabled true
cihub registry set my-repo --tool ruff --max-errors 5
cihub registry set my-repo --tool pytest --min-coverage 85

# Apply a profile
cihub registry set my-repo --profile python-security

# Clear specific override (revert to default)
cihub registry set my-repo --tool mypy --clear
cihub registry set my-repo --coverage --clear

# Remove repo from registry
cihub registry remove my-repo
```

### 4.3 Sync & Drift

```bash
# Check for drift between registry and YAML files
cihub registry diff
cihub registry diff my-repo

# Sync registry to YAML (regenerate all configs)
cihub registry sync --dry-run # Preview changes
cihub registry sync --yes # Apply changes
cihub registry sync my-repo # Single repo
```

### 4.4 Profile Management (Optional)

```bash
# List available profiles
cihub profile list

# Show profile contents
cihub profile show python-quality

# Create profile from existing repo
cihub profile create my-team-standard --from-repo production-api
```

---

## Part 5: Tool Inventory (Complete)

### 5.1 Python Tools (14)

| Tool | Key Settings | Default |
|------|--------------|---------|
| pytest | enabled, min_coverage, fail_fast, require_run_or_fail | enabled=true, min_coverage=70 |
| ruff | enabled, fail_on_error, max_errors | enabled=true, fail_on_error=true |
| black | enabled, fail_on_format_issues, max_issues | enabled=true |
| isort | enabled, fail_on_issues, max_issues | enabled=true |
| mypy | enabled, require_run_or_fail | enabled=false |
| bandit | enabled, fail_on_high, fail_on_medium, fail_on_low | enabled=true, fail_on_high=true |
| pip_audit | enabled, fail_on_vuln | enabled=true, fail_on_vuln=true |
| mutmut | enabled, min_mutation_score, timeout_minutes | enabled=true, min_mutation_score=70 |
| hypothesis | enabled | enabled=true |
| semgrep | enabled, fail_on_findings, max_findings | enabled=false |
| trivy | enabled, fail_on_critical, fail_on_high | enabled=false |
| codeql | enabled, languages, fail_on_error | enabled=false |
| docker | enabled, compose_file, health_endpoint | enabled=false |
| sbom | enabled, format | enabled=false |

### 5.2 Java Tools (12)

| Tool | Key Settings | Default |
|------|--------------|---------|
| jacoco | enabled, min_coverage | enabled=true, min_coverage=70 |
| checkstyle | enabled, fail_on_violation, max_errors | enabled=true |
| spotbugs | enabled, fail_on_error, max_bugs, effort, threshold | enabled=true |
| pmd | enabled, fail_on_violation, max_violations | enabled=true |
| owasp | enabled, fail_on_cvss, use_nvd_api_key | enabled=true, fail_on_cvss=7 |
| pitest | enabled, min_mutation_score, threads | enabled=true |
| jqwik | enabled | enabled=false |
| semgrep | enabled, fail_on_findings, max_findings | enabled=false |
| trivy | enabled, fail_on_critical, fail_on_high | enabled=false |
| codeql | enabled, languages | enabled=false |
| docker | enabled, compose_file, dockerfile, health_endpoint | enabled=false |
| sbom | enabled, format | enabled=false |

### 5.3 Global Thresholds

| Field | Type | Default |
|-------|------|---------|
| coverage_min | integer (0-100) | 70 |
| mutation_score_min | integer (0-100) | 70 |
| max_critical_vulns | integer | 0 |
| max_high_vulns | integer | 0 |
| max_pip_audit_vulns | integer | 0 |
| owasp_cvss_fail | float (0-10) | 7.0 |
| trivy_cvss_fail | float (0-10) | 7.0 |
| max_semgrep_findings | integer | 0 |
| max_ruff_errors | integer | 0 |
| max_checkstyle_errors | integer | 0 |
| max_spotbugs_bugs | integer | 0 |
| max_pmd_violations | integer | 0 |

### 5.4 Workflow Security Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| harden_runner.policy | enum | "audit" | StepSecurity harden-runner: `audit`, `block`, or `disabled` |

**Note:** This is a workflow-level security feature, not a language-specific tool.

### 5.5 GitHub Actions Input Limits (UPDATED 2026-01-06)

> **Good News:** GitHub significantly improved input limits in late 2025!

| Workflow Type | Limit | Your Workflows | Status |
|---------------|-------|----------------|--------|
| `workflow_call` (reusable) | **UNLIMITED** | python-ci.yml, java-ci.yml | [x] No constraints |
| `workflow_dispatch` (manual) | **25 inputs** | hub-orchestrator, hub-run-all, hub-security, smoke-test | [x] Plenty of headroom |

**Sources:**
- [GitHub Changelog: workflow_dispatch now supports 25 inputs](https://github.blog/changelog/2025-12-04-actions-workflow-dispatch-workflows-now-support-25-inputs/) (Dec 4, 2025)
- [workflow_call inputs limit removed](https://github.com/orgs/community/discussions/26781) (Oct 2021)

**Current Usage (hub-run-all.yml):** 10 inputs used / 25 max = **15 slots available**

**Architecture Implications:**
- **Reusable workflows (python-ci, java-ci):** Add as many boolean toggles as needed - NO LIMIT
- **Hub-internal workflows:** Can add 15 more inputs before hitting 25-input cap
- **Simple toggle pattern preserved:** No need for JSON blobs or config-file workarounds

**Recommendation:** Continue using individual boolean/string inputs for discoverability. The simple `run_<tool>: true/false` pattern works well and matches our architecture.

### 5.6 Future Architecture: Config-File-First for Hub Workflows (RECOMMENDED)

> **Problem:** Hub-internal workflows use many toggles (10 currently, growing). Input-based design:
> 1. Requires editing complex workflow YAML to add toggles
> 2. Hits 25-input ceiling eventually
> 3. Forces users to understand GitHub Actions syntax

**Recommended Solution: Config-File-First**

Move all operational toggles from workflow inputs to a simple config file. Workflows become thin wrappers.

```
┌─────────────────────────────────────────────────────────────────────┐
│ Config-File-First Architecture │
├─────────────────────────────────────────────────────────────────────┤
│ │
│ config/hub-settings.yaml ← ALL toggles (simple YAML) │
│ │ │
│ ↓ │
│ cihub hub config load ← CLI reads file, outputs to workflow │
│ │ │
│ ↓ │
│ workflow_dispatch inputs ← Only: repos, run_group (2-3 inputs) │
│ │
└─────────────────────────────────────────────────────────────────────┘
```

**The Config File (what users edit):**
```yaml
# config/hub-settings.yaml
# Simple true/false toggles - same pattern as .ci-hub.yml
# Edit directly OR use: cihub hub config set <key> <value>

execution:
 skip_mutation: false
 write_github_summary: true
 include_details: true

debug:
 enabled: false
 verbose: false

security:
 harden_runner:
 policy: audit # audit | block | disabled
```

**The Simplified Workflow:**
```yaml
# hub-run-all.yml - BEFORE: 10 inputs, AFTER: 2 inputs
on:
 workflow_dispatch:
 inputs:
 repos:
 description: 'Specific repos (comma-separated)'
 type: string
 run_group:
 description: 'Run group filter'
 type: string
 default: 'full'

jobs:
 run:
 steps:
 - uses: actions/checkout@v4

 - name: Load Hub Settings
 id: cfg
 run: cihub hub config load --github-output

 - name: Harden Runner
 if: ${{ steps.cfg.outputs.harden_runner_policy != 'disabled' }}
 uses: step-security/harden-runner@v2
 with:
 egress-policy: ${{ steps.cfg.outputs.harden_runner_policy }}

 - name: Run CI
 env:
 CIHUB_DEBUG: ${{ steps.cfg.outputs.debug_enabled }}
 SKIP_MUTATION: ${{ steps.cfg.outputs.skip_mutation }}
 run: cihub ci --repos "${{ inputs.repos }}" --run-group "${{ inputs.run_group }}"
```

**Comparison:**

| Aspect | Current (Inputs) | Config-File-First |
|--------|------------------|-------------------|
| Workflow inputs | 10 → 25 limit | 2-3 only |
| Where toggles live | Workflow YAML | `config/hub-settings.yaml` |
| Adding new toggle | Edit workflow | Edit config file |
| Manual editing | Complex YAML | Simple YAML |
| Scalability | 25 max | **Unlimited** |

**Benefits:**
- [x] Unlimited toggles
- [x] Simple YAML for manual editing (no workflow knowledge needed)
- [x] Same pattern as `.ci-hub.yml` in target repos
- [x] Git-trackable settings changes
- [x] CLI/wizard can modify easily
- [x] Schema validation via JSON schema

**Implementation Status:** PLANNED (not yet implemented)

**Components Needed:**
1. `config/hub-settings.yaml` - New settings file
2. `schema/hub-settings.schema.json` - Validation schema
3. `cihub hub config load/set/show` - CLI commands
4. Update 6 hub-internal workflows to use config loader

---

## Part 6: Implementation Plan

### 6.1 Phase 1: Schema & Registry Structure

1. **Update `schema/registry.schema.json`**
 - Remove `tiers` block
 - Add full `repo` definition with `$ref` to ci-hub-config.schema.json
 - Add `profile` as optional string reference

2. **Migrate `config/registry.json`**
 - Remove `tiers` block
 - Convert existing repos to new structure
 - Add missing fields (thresholds, tool overrides)

### 6.2 Phase 2: Service Layer

3. **Rewrite `registry_service.py`**
 - `build_effective_config(repo_name)` - merges defaults → profile → repo settings
 - `sync_repo_to_yaml(repo_name)` - generates complete config/repos/*.yaml
 - `set_tool_override(repo, tool, setting, value)` - stores tool override
 - `set_threshold(repo, field, value)` - stores threshold override
 - `apply_profile(repo, profile_name)` - applies profile preset
 - `clear_override(repo, field)` - removes specific override

### 6.3 Phase 3: CLI Enhancement

4. **Update `cli_parsers/registry_cmd.py`**
 - Add `--tool <name>` with `--enabled`, `--fail-on-*`, `--min-*`, `--max-*`
 - Add `--profile` to apply presets
 - Add `--clear` to remove overrides
 - Add `remove` subcommand

5. **Update `commands/registry_cmd.py`**
 - Implement new handlers
 - Add validation
 - Ensure all changes trigger YAML regeneration

### 6.4 Phase 4: Wizard Integration

6. **Connect wizard to registry** (`wizard/core.py`)
 - `run_new_wizard()` creates registry entry
 - Wizard reads existing profiles as optional presets
 - Wizard stores choices in registry, not directly to YAML

7. **Update `commands/new.py`**
 - `cihub new` creates registry entry first
 - Then calls `registry sync` to generate YAML

### 6.5 Phase 5: Testing

8. **Contract tests**
 - `test_schema_consistency.py` - registry schema matches ci-hub-config schema
 - `test_wizard_registry_integration.py` - wizard creates registry entries
 - `test_sync_roundtrip.py` - sync generates valid, loadable YAML
 - `test_cli_registry_contracts.py` - CLI commands modify registry correctly

9. **Property tests (Hypothesis)**
 - Any repo config in registry validates against schema
 - Effective config (defaults + profile + overrides) is valid
 - Sync output matches effective config

---

## Part 7: Files to Modify

| File | Changes |
|------|---------|
| **Schema** | |
| `schema/registry.schema.json` | Remove tiers, add full repo def with $ref |
| **Config** | |
| `config/registry.json` | Migrate to new structure |
| **Services** | |
| `cihub/services/registry_service.py` | Complete rewrite - full config building |
| **CLI** | |
| `cihub/cli_parsers/registry_cmd.py` | Add --tool, --profile, --clear, remove |
| `cihub/commands/registry_cmd.py` | Implement new handlers |
| **Commands** | |
| `cihub/commands/new.py` | Connect to registry, not direct YAML |
| **Wizard** | |
| `cihub/wizard/core.py` | Create registry entries, optional profile selection |
| **Tests** | |
| `tests/test_registry_*.py` | New contract and property tests |
| **Docs** | |
| `docs/guides/CLI_EXAMPLES.md` | Add registry examples |

---

## Part 8: Verification Checklist

- [ ] registry.json validates against registry.schema.json
- [ ] Generated configs validate against ci-hub-config.schema.json
- [ ] `cihub new --interactive` creates registry entry
- [ ] `cihub registry set` modifies registry.json
- [ ] `cihub registry sync` generates valid YAML
- [ ] Wizard reads available profiles
- [ ] All existing tests pass
- [ ] New contract tests pass

---

## Part 9: Key Design Decisions

1. **Registry = Source of Truth** - All config changes go through registry
2. **CLI-Driven** - No manual YAML editing needed
3. **Sync GENERATES YAML** - Applies defaults → profile → repo settings
4. **Sparse Storage** - Registry only stores NON-DEFAULT values
5. **No Hardcoded Tiers** - Per-repo settings, profiles are optional presets
6. **CI Engine Unchanged** - Still reads from config/repos/*.yaml
7. **Schema via $ref** - No duplication, registry uses $ref to ci-hub-config.schema
8. **Profiles are Optional** - Users can use presets or configure individually
9. **Simple Toggle Pattern** - Use individual boolean/string inputs for discoverability (see 5.5 - limits no longer a constraint)
10. **Reusable Workflows = Unlimited Inputs** - python-ci.yml and java-ci.yml use `workflow_call` which has NO input limit
11. **Config-File-First for Hub Workflows** - Move all toggles to `config/hub-settings.yaml`, keep only `repos` and `run_group` as inputs (see 5.6)

---

## Appendix A: Audit Agent Findings Summary

### Agent 1: Profile Usage
- Profiles ARE used but only at creation time (`cihub new --profile`)
- 12 profiles exist in `templates/profiles/`
- Profiles NOT loaded at CI runtime
- Profile application via `cihub config apply-profile` works

### Agent 2: Wizard System
- 3 entry points: `new`, `init`, `config edit`
- Asks 15-20 questions per repo
- Does NOT connect to registry
- Writes directly to YAML, bypassing registry

### Agent 3: Config Loading
- 3-tier merge: defaults → hub override → repo local
- Normalization handles boolean shorthands
- Single validation after all merges
- Protected keys when hub override exists

### Agent 4: CLI Commands
- `cihub new` creates config/repos/*.yaml directly
- `cihub init` creates .ci-hub.yml + workflow
- `cihub config` edit/set/enable/disable works
- `cihub registry` exists but only handles 3 values

### Agent 5: Config Directory
- 28 YAML files in config/repos/
- Sparse overrides (not full configs)
- No profile references in individual YAMLs
- Registry only tracks 6 repos (vs 28 configs)

### Agent 6: Registry Implementation
- 6 CLI commands implemented and working
- Only syncs coverage, mutation, vulns_max
- Tier definitions empty (just description + profile ref)
- Default thresholds hardcoded in Python

### Agent 7: Boolean Patterns
- `oneOf` pattern in schema allows bool or object
- `_normalize_tool_configs_inplace()` converts bools
- Canonical `tool_enabled()` function exists
- Applied at each merge layer

### Agent 8: Workflow Config Consumption
- hub-ci.yml uses `cihub config-outputs` to read .ci-hub.yml
- hub-run-all.yml uses `--config-from-hub` to read config/repos/
- Orchestrator reads from config/repos/*.yaml
- Protected keys prevent target repos overriding identity

---

## Part 10: USER FLEXIBILITY GAP ANALYSIS (CRITICAL)

**Audit Date:** 2026-01-06
**Audit Method:** 8-agent comprehensive flexibility audit

This section documents everything users **CANNOT do** with the current system that they **SHOULD be able to do** for a truly flexible, CLI-first tool.

### 10.1 Executive Summary - What's Blocking Users

| Gap Category | Severity | Impact |
|-------------|----------|--------|
| Cannot create profiles via CLI | CRITICAL | Users forced to manually edit YAML files |
| Cannot add custom tools | CRITICAL | Locked to 26 hardcoded tools |
| Cannot add new languages | CRITICAL | Only Python and Java supported |
| Registry only tracks 3 values | CRITICAL | 40+ settings ignored |
| Missing 41 CLI commands | HIGH | Incomplete CRUD operations |
| Schema blocks extensibility | HIGH | additionalProperties: false everywhere |
| 50+ hardcoded magic numbers | MEDIUM | Users can't adjust behavior |

### 10.2 Profile Creation - COMPLETELY MISSING

**User Story:** "I want to create a custom profile for my team"

**Current State:**
- [ ] NO `cihub profile create` command
- [ ] NO `cihub profile list` command
- [ ] NO `cihub profile edit` command
- [ ] NO `cihub profile delete` command
- Profiles are READ-ONLY static files in `templates/profiles/`
- Only 12 predefined profiles exist
- Users must manually create YAML files to add profiles

**What Users Need:**
```bash
cihub profile create my-team-standard --from-repo production-api
cihub profile list
cihub profile show python-quality
cihub profile edit my-team-standard
cihub profile delete my-team-standard
```

**Impact:** Users cannot standardize configurations without direct file system access.

### 10.3 Tool Extensibility - ZERO FLEXIBILITY

**User Story:** "I want to add pylint (or any custom tool) to my CI pipeline"

**Current State:**
- [ ] Tools are HARDCODED in `cihub/tools/registry.py`:
 ```python
 PYTHON_TOOLS = ["pytest", "ruff", "black", "isort", "mypy", "bandit", ...]
 JAVA_TOOLS = ["jacoco", "pitest", "checkstyle", "spotbugs", ...]
 ```
- [ ] Schema uses `additionalProperties: false` - rejects unknown tools
- [ ] Tool runners are hardcoded dictionaries
- [ ] No plugin system
- [ ] `extra_tests` feature defined in schema but NOT implemented

**What Users Need:**
- Plugin system for custom tools
- Dynamic tool registration
- Custom tool runners
- Schema allowing custom tool configurations

**Impact:** Users locked to predefined tool set; cannot use organization-specific tools.

### 10.4 Language Support - ONLY 2 LANGUAGES

**User Story:** "I want to add Go/Rust/Node.js support"

**Current State:**
- [ ] Languages hardcoded as enum: `["python", "java"]`
- [ ] Tool definitions are per-language and hardcoded
- [ ] No language plugin architecture
- [ ] Adding a language requires modifying:
 - Schema files
 - Tool registry
 - CI engine
 - Workflow templates
 - Wizard questions
 - 10+ files total

**Impact:** Cannot use this tool for polyglot organizations.

### 10.5 Registry Limitations

**User Story:** "I want to manage all my repo settings centrally"

**Current State:**
- Registry only tracks **3 values**: `coverage`, `mutation`, `vulns_max`
- Schema has **20+ thresholds** but registry ignores most
- Registry ignores all tool settings
- No validation bounds (can set coverage: 101)
- Naming inconsistency: registry uses `mutation`, config uses `mutation_score_min`

**What Registry SHOULD track:**
| Currently Tracked | Missing (20+ fields) |
|------------------|---------------------|
| coverage | max_critical_vulns |
| mutation | max_high_vulns |
| vulns_max | max_pip_audit_vulns |
| | owasp_cvss_fail |
| | trivy_cvss_fail |
| | max_semgrep_findings |
| | max_ruff_errors |
| | max_checkstyle_errors |
| | max_spotbugs_bugs |
| | ALL tool enable/disable |
| | ALL tool-specific settings |

### 10.6 CRUD Operation Gaps

**Wizard CRUD Audit Results:**

| Entity | Create | Read | Update | Delete | Gap? |
|--------|--------|------|--------|--------|------|
| Repos | [x] | [x] | [x] | [ ] | **MISSING DELETE** |
| Profiles | [ ] | [x] | [ ] | [ ] | **MISSING C, U, D** |
| Tiers | [ ] | [x] | [ ] | [ ] | **MISSING C, U, D** |
| Tools | [ ] | [x] | [x] | [ ] | **MISSING C, D** |
| Thresholds | [ ] | [x] | [x] | [ ] | **MISSING C, D** |
| Workflows | [x] | [x] | [x] | [ ] | **MISSING DELETE** |

### 10.7 Hardcoded Values (50+ Magic Numbers)

**Users cannot change these without modifying code:**

**Quality Thresholds:**
| Value | Location | User Impact |
|-------|----------|-------------|
| coverage_min: 70 | defaults.yaml:43,128 | Cannot adjust coverage gate |
| mutation_score_min: 70 | defaults.yaml:71,171 | Cannot adjust mutation gate |
| fail_on_cvss: 7 | defaults.yaml:64 | Cannot adjust security gate |

**Language/Build:**
| Value | Location | User Impact |
|-------|----------|-------------|
| Java version: "21" | defaults.yaml:34 | Cannot use Java 17 or 22 |
| Java distribution: "temurin" | defaults.yaml:35 | Cannot use Corretto/Zulu |
| Languages: ["java", "python"] | CLI parsers | Cannot add Go/Rust/Node |

**Timeouts:**
| Value | Location | User Impact |
|-------|----------|-------------|
| TIMEOUT_QUICK = 30s | exec_utils.py:20 | Cannot adjust for slow commands |
| TIMEOUT_BUILD = 600s | exec_utils.py:22 | Cannot extend for slow tests |
| health_timeout: 300s | defaults.yaml:114 | Cannot adjust for slow services |
| mutation threads: 4 | defaults.yaml:72 | Cannot adjust for machine size |

**Triage:**
| Value | Location | User Impact |
|-------|----------|-------------|
| TEST_COUNT_DROP_THRESHOLD = 0.10 | types.py:15 | Cannot adjust sensitivity |
| min_runs = 5 | detection.py:72 | Cannot adjust flaky detection |
| fail_rate > 0.5 | detection.py:245 | Cannot adjust failure threshold |

**Badge Colors:**
| Value | Location | User Impact |
|-------|----------|-------------|
| ≥90%: brightgreen | badges.py:31-40 | Cannot customize color scale |
| ≥70%: yellowgreen | badges.py | Hardcoded thresholds |

### 10.8 Schema Extensibility Issues

**ci-hub-config.schema.json:**
- `additionalProperties: false` at root level
- `additionalProperties: false` on ALL nested objects
- Users CANNOT add custom fields
- Users CANNOT add custom tools
- Language enum is fixed: `["java", "python"]`
- **Extensibility Score: 0/10**

**registry.schema.json:**
- Allows custom fields in repos (additionalProperties not specified)
- But NOT validated in production code
- **Extensibility Score: 6/10**

**triage.schema.json:**
- Allows additional fields
- Status/severity/category enums are fixed
- **Extensibility Score: 7/10**

### 10.9 User Stories - Blocked vs Working

| User Story | Status | Blocker |
|------------|--------|---------|
| Add new repo to registry | [x] YES | - |
| Create custom profile | [ ] NO | No profile create command |
| Use tool not in defaults (pylint) | [ ] NO | Tools hardcoded in schema |
| Set custom threshold | WARNING: PARTIAL | Only if threshold in schema |
| Edit existing profile | [ ] NO | No profile edit command |
| Delete profile | [ ] NO | No profile delete command |
| Add new language (Go, Rust) | [ ] NO | Languages hardcoded as enum |
| Customize workflow templates | [ ] NO | No customization system |
| Bulk update all repos | WARNING: PARTIAL | No filtering/bulk-set commands |
| Export/import configuration | [ ] NO | No export/import commands |

---

## Part 11: MISSING CLI COMMANDS (41 Commands)

### 11.1 Profile Management (CRITICAL - 7 commands)

```bash
# MISSING: Create profile
cihub profile create <name> --language python --from-repo <repo>

# MISSING: List profiles
cihub profile list [--language python|java]

# MISSING: Show profile
cihub profile show <name> [--effective]

# MISSING: Edit profile
cihub profile edit <name> [--wizard]

# MISSING: Delete profile
cihub profile delete <name> [--force]

# MISSING: Export profile
cihub profile export <name> --output file.yaml

# MISSING: Import profile
cihub profile import --file file.yaml
```

### 11.2 Repository Management (CRITICAL - 6 commands)

```bash
# MISSING: Remove repo from registry
cihub registry remove <name> [--keep-config]

# MISSING: Repo status overview
cihub repo list [--tier] [--language] [--format json]

# MISSING: Update repo metadata
cihub repo update <name> --owner myorg --branch main

# MISSING: Migrate repo config
cihub repo migrate <from> <to> [--delete-source]

# MISSING: Clone repo config
cihub repo clone <source> <dest> [--update-name]

# MISSING: Verify connectivity
cihub repo verify-connectivity <name>
```

### 11.3 Tool Management (IMPORTANT - 6 commands)

```bash
# MISSING: List available tools
cihub tool list [--language] [--category lint|security|test]

# MISSING: Enable tool across repos
cihub tool enable <tool> [--for-repo <name>] [--all-repos]

# MISSING: Disable tool across repos
cihub tool disable <tool> [--for-repo <name>] [--all-repos]

# MISSING: Configure tool
cihub tool configure <tool> <param> <value> [--repo]

# MISSING: Tool status
cihub tool status [--repo] [--all]

# MISSING: Validate tool installation
cihub tool validate <tool> [--install-if-missing]
```

### 11.4 Threshold Management (IMPORTANT - 5 commands)

```bash
# MISSING: Get thresholds
cihub threshold get [<tool>] [--repo] [--effective]

# MISSING: Set threshold
cihub threshold set <tool> <value> [--repo] [--all-repos]

# MISSING: List all thresholds
cihub threshold list [--language] [--category]

# MISSING: Reset to defaults
cihub threshold reset [<tool>] [--repo]

# MISSING: Compare repos
cihub threshold compare <repo1> <repo2>
```

### 11.5 Import/Export (IMPORTANT - 5 commands)

```bash
# MISSING: Export all
cihub export --format json --output backup.json

# MISSING: Import all
cihub import --file backup.json [--merge|--replace]

# MISSING: Export single repo
cihub export repo <name> --output repo.yaml

# MISSING: Import single repo
cihub import repo --file repo.yaml

# MISSING: Export registry
cihub export registry --filter-tier strict
```

### 11.6 Additional Validation (IMPORTANT - 4 commands)

```bash
# MISSING: Validate registry
cihub validate registry [--strict] [--fix]

# MISSING: Validate profiles
cihub validate profiles [--profile name]

# MISSING: Validate single config
cihub validate config <repo> [--effective]

# MISSING: Validate schema
cihub validate schema [--generate]
```

### 11.7 Sync/Maintenance (IMPORTANT - 5 commands)

```bash
# MISSING: Sync profiles to repos
cihub sync profiles --to-repos [--filter-tier]

# MISSING: Sync thresholds to tier
cihub sync thresholds --to-tier <tier>

# MISSING: Health check
cihub health-check [--all] [--fix-issues]

# MISSING: Check template sync (separate from sync)
cihub sync templates --check-only

# MISSING: Cleanup orphaned configs
cihub cleanup [--dry-run]
```

### 11.8 Audit/Compliance (NICE-TO-HAVE - 3 commands)

```bash
# MISSING: Audit log
cihub audit log [--since 7d] [--entity-type repo]

# MISSING: Drift detection
cihub audit drift [--fix]

# MISSING: Compliance check
cihub audit compliance [--standard soc2]
```

---

## Part 12: REVISED IMPLEMENTATION PRIORITIES

### 12.1 Priority Matrix (Updated)

| Priority | Category | Commands/Features | User Impact |
|----------|----------|-------------------|-------------|
| P0 | Profile CRUD | 7 commands | Users can't create reusable configs |
| P0 | Registry full tracking | 40+ fields | Central management broken |
| P0 | Repo delete | 1 command | Can't clean up repos |
| P1 | Tool management | 6 commands | Users edit YAML manually |
| P1 | Threshold management | 5 commands | Users edit YAML manually |
| P1 | Import/Export | 5 commands | No backup/migration |
| P2 | Schema extensibility | Remove additionalProperties:false | Custom tools blocked |
| P2 | Additional validation | 4 commands | No fine-grained validation |
| P3 | Audit/compliance | 3 commands | Governance teams |

### 12.2 Revised Phase 1 (CRITICAL - Must Fix First)

1. **Profile Management System**
 - Create `cihub/cli_parsers/profile.py`
 - Create `cihub/commands/profile.py`
 - Implement: create, list, show, edit, delete
 - Store custom profiles in `templates/profiles/custom/`

2. **Registry Full Config Tracking**
 - Rewrite `registry_service.py` to track ALL 40+ settings
 - Update registry.schema.json to match ci-hub-config schema via $ref
 - Fix `sync_to_configs()` to generate complete configs

3. **Repo Delete Command**
 - Add `cihub registry remove <name>`
 - Remove from registry.json
 - Optionally delete config/repos/*.yaml

### 12.3 Revised Phase 2 (HIGH - User Experience)

4. **Tool & Threshold CLI**
 - Add all 11 tool/threshold commands
 - Enable granular control without YAML editing

5. **Import/Export System**
 - Backup and restore capability
 - Migration between environments

6. **Wizard ↔ Registry Connection**
 - Wizard writes to registry, not YAML directly
 - Sync generates YAML from registry

### 12.4 Revised Phase 3 (MEDIUM - Extensibility)

7. **Schema Extensibility**
 - Add `custom` or `extensions` section to schemas
 - Allow `x-*` prefixed custom fields
 - Consider removing `additionalProperties: false` from root

8. **Language Plugin System**
 - Abstract language-specific logic
 - Allow custom language registration
 - Define language plugin interface

### 12.5 Revised Phase 4 (LOW - Nice to Have)

9. **Audit & Compliance**
 - Change tracking
 - Drift detection
 - Compliance reporting

---

## Part 13: DESIGN DECISIONS (UPDATED)

### 13.1 Core Principles (Unchanged)

1. **Registry = Source of Truth**
2. **CLI-Driven** - No manual YAML editing
3. **Sparse Storage** - Only non-defaults
4. **Schema via $ref** - No duplication

### 13.2 New Principles (Added from Gap Analysis)

5. **Full CRUD for All Entities** - Users can create, read, update, delete:
 - Profiles
 - Repos
 - Tools (enable/disable)
 - Thresholds

6. **No Hardcoded Limits** - All thresholds, timeouts, and behavior configurable

7. **Extensibility First** - Schema allows custom fields in reserved namespace

8. **Export/Import Capability** - All configuration can be backed up and restored

9. **Profile Creation via CLI** - Users can create profiles from existing repos

10. **Bulk Operations** - Users can update multiple repos with filters

---

## Appendix B: Gap Analysis Agent Findings (2026-01-06)

### Agent 1: Profile Creation Gaps
- No `cihub profile create` command
- No `cihub profile list` command
- No `cihub profile edit` command
- No `cihub profile delete` command
- Profiles are static YAML files only
- Functions exist (`load_profile`, `list_profiles`) but not exposed in CLI

### Agent 2: Tool Extensibility Gaps
- PYTHON_TOOLS and JAVA_TOOLS hardcoded in `cihub/tools/registry.py`
- Schema uses `additionalProperties: false` everywhere
- Tool runners are hardcoded dictionaries
- `extra_tests` defined in schema but NOT implemented
- Zero extensibility without code modification

### Agent 3: Threshold Flexibility Gaps
- Registry tracks only 3 values (coverage, mutation, vulns_max)
- Schema defines 20+ thresholds but registry ignores them
- `valid_keys` hardcoded: `{"coverage", "mutation", "vulns_max"}`
- No validation bounds (can set coverage: 101)
- Naming inconsistency between systems

### Agent 4: Wizard CRUD Gaps
- Repos: Missing DELETE
- Profiles: Missing CREATE, UPDATE, DELETE
- Tiers: Missing CREATE, UPDATE, DELETE
- Tools: Missing CREATE, DELETE
- Thresholds: Missing CREATE, DELETE
- Workflows: Missing DELETE

### Agent 5: Hardcoded Values
- 50+ magic numbers in code
- Coverage/mutation: 70 hardcoded
- CVSS: 7 hardcoded
- Languages: only python/java
- Timeouts: multiple fixed values
- Badge colors: fixed thresholds

### Agent 6: User Story Analysis
- 10 user stories evaluated
- 4 fully blocked ([ ])
- 4 partially working (WARNING:)
- 2 fully working ([x])
- Major blockers: profiles, tools, languages, export/import

### Agent 7: Schema Extensibility
- ci-hub-config.schema.json: 0/10 extensibility
- registry.schema.json: 6/10 extensibility
- triage.schema.json: 7/10 extensibility
- Registry and triage schemas NOT validated in production

### Agent 8: CLI Command Completeness
- 30 top-level commands exist
- 41 commands MISSING across 8 categories
- Profile management: 7 missing
- Repo management: 6 missing
- Tool management: 6 missing
- Threshold management: 5 missing
- Import/export: 5 missing

---

## Part 14: SYNC VERIFICATION GAPS (SECOND AUDIT)

**Audit Date:** 2026-01-06
**Focus:** Pipeline synchronization at each step

### 14.1 Coverage Matrix - What's Verified vs Missing

| Sync Point | Verification Exists? | Gap Severity |
|------------|---------------------|--------------|
| Wizard → Registry | [ ] NO | CRITICAL |
| Registry → YAML | WARNING: PARTIAL (3 fields) | CRITICAL |
| YAML → Workflow | [ ] NO | HIGH |
| Schema ↔ Code | WARNING: PARTIAL | HIGH |
| Profile ↔ Registry | [ ] NO | HIGH |
| Registry ↔ GitHub | [ ] NO | MEDIUM |
| Thresholds ↔ Gates | [ ] NO | HIGH |
| Templates ↔ Deployed | [x] YES (template-sync) | [x] OK |
| Schema ↔ Defaults | WARNING: PARTIAL | MEDIUM |

### 14.2 Gap Details

**Gap 1: Wizard → Registry Sync (CRITICAL)**
- Wizard writes directly to `config/repos/*.yaml`
- Registry is never updated during wizard flow
- **Solution:** Wizard should write to registry, then trigger sync

**Gap 2: Registry → YAML Sync (CRITICAL)**
- Only 3 values synced: coverage, mutation, vulns_max
- 40+ settings ignored during sync
- **Solution:** Rewrite `sync_to_configs()` to sync all fields

**Gap 3: YAML → Workflow Sync (HIGH)**
- No verification that YAML settings match workflow expectations
- Tool enabled in YAML but not available in workflow?
- **Solution:** Add `cihub verify workflow --repo <name>`

**Gap 4: Schema ↔ Code Sync (HIGH)**
- Some schema-defined fields not handled in code
- `extra_tests` defined but not implemented
- **Solution:** Contract tests: every schema field has handler

**Gap 5: Profile ↔ Registry Sync (HIGH)**
- Registry can reference profiles that don't exist
- No validation that profile file exists
- **Solution:** `cihub validate registry --check-profiles`

**Gap 6: Registry ↔ GitHub Sync (MEDIUM)**
- No check that GitHub repo actually exists
- Registry might reference deleted repos
- **Solution:** `cihub verify connectivity --all`

**Gap 7: Thresholds ↔ Gates Sync (HIGH)**
- Thresholds in config might not match actual gate logic
- Gate might use hardcoded 70 while config says 80
- **Solution:** Contract tests for threshold → gate mapping

**Gap 8: Schema ↔ Defaults Sync (MEDIUM)**
- Default values in code vs schema can drift
- defaults.yaml:43 says 70, schema might say different
- **Solution:** `test_defaults_match_schema.py`

**Gap 9: Version Sync (LOW)**
- Schema version not validated against code version
- Could have schema v2 with code expecting v1
- **Solution:** Version compatibility matrix

### 14.3 Recommended New Verification Commands

```bash
# Full pipeline verification
cihub verify --all

# Step-by-step verification
cihub verify --step wizard-registry # Wizard created registry entry?
cihub verify --step registry-yaml # Registry matches generated YAML?
cihub verify --step yaml-workflow # YAML settings work with workflow?
cihub verify --step profile-exists # All referenced profiles exist?
cihub verify --step schema-code # Schema fields have handlers?
cihub verify --step github-access # GitHub repos accessible?
cihub verify --step threshold-gates # Thresholds match gate logic?
```

---

## Part 15: COMPREHENSIVE TESTING STRATEGY

**Audit Date:** 2026-01-06
**Focus:** Testing coverage for registry system

### 15.1 Current Testing State

| Test Category | Files | Coverage |
|--------------|-------|----------|
| Unit tests | 80+ | WARNING: registry_service untested |
| Integration | 20+ | WARNING: No wizard→registry tests |
| Contract | 5 | WARNING: Incomplete schema coverage |
| E2E | 8 | WARNING: No full pipeline tests |
| Property-based | 3 | WARNING: Limited scope |
| Mutation | 0 | [ ] Not configured |

### 15.2 Required Test Categories

#### Category 1: Unit Tests for registry_service.py (~200 lines)

```python
# tests/test_registry_service_unit.py
class TestRegistryService:
 # Load/Save
 def test_load_registry_empty_file(self): ...
 def test_load_registry_valid_json(self): ...
 def test_save_registry_writes_json(self): ...

 # List/Show
 def test_list_repos_returns_all(self): ...
 def test_list_repos_computes_effective(self): ...
 def test_get_repo_config_not_found(self): ...
 def test_get_repo_config_with_overrides(self): ...

 # Set Operations
 def test_set_repo_tier_valid(self): ...
 def test_set_repo_tier_invalid(self): ...
 def test_set_repo_override_valid_key(self): ...
 def test_set_repo_override_invalid_key(self): ...

 # Diff/Sync
 def test_compute_diff_finds_differences(self): ...
 def test_compute_diff_missing_config(self): ...
 def test_sync_to_configs_dry_run(self): ...
 def test_sync_to_configs_applies_changes(self): ...
```

#### Category 2: Integration Tests (~300 lines)

```python
# tests/test_registry_integration.py
class TestRegistryIntegration:
 # Registry → Config Pipeline
 def test_registry_set_generates_valid_yaml(self): ...
 def test_registry_sync_updates_all_repos(self): ...
 def test_registry_diff_detects_all_fields(self): ...

 # Wizard → Registry Pipeline
 def test_wizard_creates_registry_entry(self): ...
 def test_wizard_respects_existing_registry(self): ...
 def test_wizard_profile_selection_updates_registry(self): ...

 # CLI → Registry Pipeline
 def test_cli_set_modifies_registry(self): ...
 def test_cli_show_reads_effective_config(self): ...
 def test_cli_remove_deletes_entry(self): ...
```

#### Category 3: Contract Tests (~250 lines)

```python
# tests/test_registry_contracts.py
class TestSchemaContracts:
 # Schema Consistency
 def test_registry_schema_refs_ci_hub_config(self): ...
 def test_all_thresholds_in_registry_schema(self): ...
 def test_all_tools_in_registry_schema(self): ...

 # Field Mapping
 def test_registry_field_names_match_yaml(self): ...
 def test_threshold_names_consistent(self): ...

 # Default Values
 def test_registry_defaults_match_yaml_defaults(self): ...
 def test_code_defaults_match_schema_defaults(self): ...
```

#### Category 4: Property-Based Tests with Hypothesis (~200 lines)

```python
# tests/test_registry_properties.py
from hypothesis import given, strategies as st

class TestRegistryProperties:
 @given(st.integers(0, 100))
 def test_coverage_roundtrip(self, value): ...

 @given(st.dictionaries(st.text(), st.integers()))
 def test_overrides_preserved(self, overrides): ...

 @given(st.lists(st.text()))
 def test_list_repos_idempotent(self, repos): ...

 @given(st.sampled_from(["strict", "standard", "relaxed"]))
 def test_tier_always_valid(self, tier): ...
```

#### Category 5: Snapshot Tests (~100 lines)

```python
# tests/test_registry_snapshots.py
class TestRegistryCLISnapshots:
 def test_registry_list_output(self, snapshot): ...
 def test_registry_show_output(self, snapshot): ...
 def test_registry_diff_output(self, snapshot): ...
 def test_registry_help_output(self, snapshot): ...
```

#### Category 6: E2E Pipeline Tests (~300 lines)

```python
# tests/test_registry_e2e.py
class TestRegistryE2E:
 def test_full_pipeline_new_repo(self):
 """Wizard → Registry → YAML → Workflow → CI Run"""
 # 1. Run wizard
 # 2. Verify registry entry created
 # 3. Verify YAML generated
 # 4. Verify workflow can read config
 # 5. Verify CI gates match thresholds

 def test_full_pipeline_modify_threshold(self):
 """CLI set → Registry → YAML → Gates"""

 def test_full_pipeline_apply_profile(self):
 """Profile create → Apply → Verify effective config"""
```

### 15.3 Mutation Testing Configuration

```toml
# pyproject.toml additions
[tool.mutmut]
paths_to_mutate = "cihub/services/registry_service.py"
runner = "pytest tests/test_registry_service_unit.py"
tests_dir = "tests/"

# Target: >80% mutation kill rate
```

### 15.4 Test Metrics Goals

| Metric | Current | Target |
|--------|---------|--------|
| Line coverage | ~85% | >95% |
| Branch coverage | ~70% | >90% |
| Mutation score | 0% | >80% |
| Contract tests | 5 | 25+ |
| Property tests | 3 | 15+ |
| E2E tests | 8 | 20+ |

---

## Part 16: EDGE CASES ANALYSIS (38+ Cases)

**Audit Date:** 2026-01-06
**Focus:** Pipeline edge cases and failure modes

### 16.1 Wizard → Registry Edge Cases

| Edge Case | Risk | Handling Strategy |
|-----------|------|-------------------|
| User cancels mid-wizard | | Cleanup partial state |
| Duplicate repo name | | Prompt for overwrite/rename |
| Invalid characters in repo name | | Sanitize or reject |
| Network failure during wizard | | Local-only mode |
| Empty required field | | Validation prompt |
| Profile reference doesn't exist | | Warn and continue without |

### 16.2 Registry → YAML Edge Cases

| Edge Case | Risk | Handling Strategy |
|-----------|------|-------------------|
| Config file exists with different content | | Prompt or --force flag |
| Orphaned YAML (no registry entry) | | `cihub cleanup` command |
| Registry has invalid JSON | | Graceful error + backup |
| Schema version mismatch | | Migration or error |
| Circular profile references | | Detect and error |
| Profile file deleted | | Warn, use defaults |

### 16.3 YAML → Workflow Edge Cases

| Edge Case | Risk | Handling Strategy |
|-----------|------|-------------------|
| Tool enabled but not installed | | CI fails with clear message |
| Threshold for disabled tool | | Ignore silently |
| Invalid YAML syntax | | Schema validation |
| Missing required fields | | Use defaults |
| Extra unknown fields | | Ignore (if additionalProperties: true) |
| Workflow template out of date | | template-sync check |

### 16.4 CI Engine Edge Cases

| Edge Case | Risk | Handling Strategy |
|-----------|------|-------------------|
| Tool timeout | | Configurable timeouts |
| Tool not found | | Clear error message |
| Partial tool failure | | Continue or fail-fast option |
| Coverage report missing | | Fail gate or warn |
| Memory exhaustion | | Resource limits |
| Flaky test detection | | Re-run logic |

### 16.5 Cross-Cutting Edge Cases

| Edge Case | Risk | Handling Strategy |
|-----------|------|-------------------|
| Version upgrade mid-run | | Lock file mechanism |
| Concurrent modifications | | File locking |
| Environment variable injection | | Sanitize inputs |
| Unicode in repo names | | Normalize to ASCII |
| Very long repo names | | Truncate with hash |
| Symlink in config path | | Resolve or reject |
| Read-only filesystem | | Graceful error |
| Partial registry update | | Atomic writes |

### 16.6 Multi-Repo Edge Cases

| Edge Case | Risk | Handling Strategy |
|-----------|------|-------------------|
| Bulk update with some failures | | Report partial success |
| Profile used by multiple repos deleted | | Warn, don't delete |
| Registry corruption | | Backup mechanism |
| 100+ repos in registry | | Performance testing |
| Circular dependencies | | Detect and error |

### 16.7 Recommended Edge Case Tests

```python
# tests/test_edge_cases.py

class TestWizardEdgeCases:
 def test_cancel_mid_wizard_cleans_up(self): ...
 def test_duplicate_repo_prompts_user(self): ...
 def test_network_failure_continues_locally(self): ...

class TestRegistryEdgeCases:
 def test_orphaned_yaml_detected(self): ...
 def test_invalid_json_graceful_error(self): ...
 def test_schema_version_mismatch_migrates(self): ...

class TestConcurrencyEdgeCases:
 def test_concurrent_registry_updates_safe(self): ...
 def test_atomic_write_on_failure(self): ...
```

---

## Part 17: LANGUAGE ADDITION - AI-ASSISTED APPROACH (REVISED)

**Audit Date:** 2026-01-06
**Revised:** 2026-01-06 (after discovering Language Strategy Pattern)
**Focus:** AI-assisted language addition using architecture manifest

### 17.1 Executive Summary (REVISED)

**CORRECTION:** The codebase already has a **Language Strategy Pattern** (ADR-0041) specifically designed for adding new languages. The initial estimate of 27 files was wrong.

| Question | Answer |
|----------|--------|
| Can users add languages via CLI wizard? | [x] YES (with AI assistance) |
| Can users add languages via YAML? | [ ] NO (code generation required) |
| Is there a plugin system? | [x] YES (LanguageStrategy ABC) |
| Effort to add JavaScript | ~8 core files, ~500-800 lines |
| Recommended approach | **AI-assisted with human review** |

### 17.2 The Language Strategy Pattern (Already Exists!)

The codebase has an abstract base class that encapsulates all language-specific behavior:

```
cihub/core/languages/
├── base.py # LanguageStrategy ABC (8 required methods)
├── python.py # PythonStrategy
├── java.py # JavaStrategy
├── javascript.py # JavaScriptStrategy (AI can generate this!)
└── registry.py # Single-line registration
```

**Key Insight:** The CI engine is language-agnostic. It just calls `get_strategy(language)` and delegates all work to the strategy. Adding a new language does NOT require modifying the CI engine at all!

### 17.3 AI-Assisted Language Addition System

The key to making language addition feasible is providing the AI with **complete architectural context** via a manifest file.

#### The Architecture Manifest Approach

**File:** `docs/architecture/LANGUAGE_PLUGIN_MANIFEST.md`

This document gives AI complete context:
1. The LanguageStrategy abstract base class (8 required methods)
2. Exact files to create/modify
3. Template code to follow
4. Validation tests to run

#### How It Works (CLI Command)

```bash
# User requests adding JavaScript support
cihub language add javascript

# AI-powered flow:
# 1. Read LANGUAGE_PLUGIN_MANIFEST.md for context
# 2. Research JavaScript CI tools (jest, eslint, npm audit, etc.)
# 3. Generate JavaScriptStrategy class following pattern
# 4. Generate tool runner stubs
# 5. Update schema, defaults, registry
# 6. Generate tests
# 7. Run validation
# 8. Present changes for human review
```

### 17.4 Actual Files Required (CORRECTED - ~8 core files)

| Tier | Files | Action | AI Can Generate? |
|------|-------|--------|-----------------|
| **Core Strategy** | `cihub/core/languages/javascript.py` | CREATE | [x] YES |
| **Registration** | `cihub/core/languages/registry.py` | ADD 1 LINE | [x] YES |
| **Tool List** | `cihub/tools/registry.py` | ADD LIST | [x] YES |
| **Tool Runners** | `cihub/services/ci_engine/javascript_tools.py` | CREATE | WARNING: STUBS |
| **Gates** | `cihub/services/ci_engine/gates.py` | ADD FUNCTION | [x] YES |
| **Schema** | `schema/ci-hub-config.schema.json` | ADD SECTION | [x] YES |
| **Defaults** | `config/defaults.yaml` | ADD SECTION | [x] YES |
| **Tests** | `tests/test_javascript_strategy.py` | CREATE | [x] YES |

**Key Insight:** The CI engine (`cihub/services/ci_engine/__init__.py`) does NOT need modification. It just calls `get_strategy(language)` and the strategy handles everything.

### 17.5 The LanguageStrategy Contract

AI generates code implementing this interface:

```python
class JavaScriptStrategy(LanguageStrategy):
 @property
 def name(self) -> str:
 return "javascript"

 def detect(self, repo_path: Path) -> float:
 """Detect JavaScript projects."""
 if (repo_path / "package.json").exists(): return 0.9
 if (repo_path / "tsconfig.json").exists(): return 0.85
 return 0.0

 def get_runners(self) -> dict[str, Callable]:
 return {"jest": run_jest, "eslint": run_eslint, ...}

 def get_default_tools(self) -> list[str]:
 return ["jest", "eslint", "prettier", "tsc", "npm_audit", ...]

 def get_thresholds(self) -> tuple[ThresholdSpec, ...]:
 return (ThresholdSpec("Min Coverage", "coverage_min", "%", ...),)

 # ... 4 more required methods
```

### 17.6 Recommended Implementation Plan

**Phase 1: Create Architecture Manifest** [x] DONE
- `docs/architecture/LANGUAGE_PLUGIN_MANIFEST.md` created
- Documents all patterns, files, and templates

**Phase 2: JavaScript Proof-of-Concept**
```bash
# Use AI to generate JavaScript support
cihub language add javascript --ai-assist

# AI generates:
# - JavaScriptStrategy class
# - Tool runner stubs (jest, eslint, prettier, tsc, npm_audit)
# - Schema updates
# - Default configurations
# - Tests

# Human reviews and implements actual tool runners
```

**Phase 3: Validate & Test**
```bash
# Run validation suite
pytest tests/test_javascript_strategy.py -v
cihub validate schema
cihub language test javascript --dry-run
```

**Phase 4: Iterate for Go, Rust, etc.**
- Same pattern, different tools
- AI learns from JavaScript implementation

### 17.7 What Users CAN Do (REVISED)

| Action | Supported? | How? |
|--------|------------|------|
| Configure existing languages | [x] YES | CLI / YAML |
| Enable/disable tools | [x] YES | CLI / YAML |
| Set thresholds | [x] YES | CLI / YAML |
| Apply profiles | [x] YES | CLI |
| Request new language via wizard | [x] YES (NEW) | AI-assisted |
| Add custom tools | WARNING: PARTIAL | x- prefix |
| Full language implementation | [ ] DEV ONLY | AI assists dev |

### 17.8 AI Integration for Language Addition

**The llms.txt Approach:**

Based on [industry best practices](https://www.honeycomb.io/blog/how-i-code-with-llms-these-days), providing AI with a structured architecture document produces "shockingly better code."

Our `LANGUAGE_PLUGIN_MANIFEST.md` serves this purpose:
- Complete LanguageStrategy ABC documentation
- File-by-file modification guide
- Template code for each component
- Validation checklist

**AI Workflow:**

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ User Request │────▶│ AI Reads │────▶│ AI Generates │
│ "add golang" │ │ Manifest + │ │ Strategy + │
│ │ │ Research Tools │ │ Tools + Tests │
└─────────────────┘ └─────────────────┘ └─────────────────┘
 │
 ┌─────────────────┐ │
 │ Human Reviews │◀────────────┘
 │ Implements │
 │ Tool Runners │
 └─────────────────┘
 │
 ┌─────────────────┐
 │ Tests Pass │
 │ Language Ready │
 └─────────────────┘
```

### 17.9 Testing Strategy for New Languages

```python
# tests/test_language_addition.py

class TestLanguageAddition:
 """Tests to verify a new language was added correctly."""

 def test_strategy_registered(self):
 """New language appears in registry."""
 assert "javascript" in get_supported_languages()

 def test_strategy_implements_all_methods(self):
 """All 8 required methods implemented."""
 strategy = get_strategy("javascript")
 assert hasattr(strategy, "name")
 assert hasattr(strategy, "get_runners")
 # ... verify all 8 methods

 def test_detection_works(self):
 """Language detection finds package.json."""
 strategy = get_strategy("javascript")
 confidence = strategy.detect(Path("/path/to/js-project"))
 assert confidence > 0.5

 def test_schema_includes_language(self):
 """Schema has javascript section."""
 schema = load_schema("ci-hub-config.schema.json")
 assert "javascript" in schema["properties"]["language"]["enum"]
 assert "javascript" in schema["properties"]

 def test_defaults_include_language(self):
 """defaults.yaml has javascript section."""
 defaults = load_yaml("config/defaults.yaml")
 assert "javascript" in defaults
 assert "tools" in defaults["javascript"]

 def test_tools_all_have_runners(self):
 """Every tool in get_default_tools() has a runner."""
 strategy = get_strategy("javascript")
 runners = strategy.get_runners()
 for tool in strategy.get_default_tools():
 if tool not in strategy.get_virtual_tools():
 assert tool in runners, f"Missing runner for {tool}"
```

### 17.10 Conclusion: AI + Human Collaboration

**AI CAN:**
- Generate strategy class boilerplate
- Research common tools for a language
- Generate schema/config updates
- Generate test scaffolding
- Suggest tool configurations

**Human MUST:**
- Review all generated code
- Implement actual tool runners (shell commands)
- Verify thresholds match tool outputs
- Test with real repositories
- Handle edge cases

**Result:** Adding a new language goes from "developer-only, weeks of work" to "AI-assisted, days of work with human review."

---

## Part 18: BOOLEAN TOGGLE EXTENSIBILITY

**Audit Date:** 2026-01-06
**Focus:** How to maintain `tool: true` pattern while allowing extensibility

### 18.1 Current Design

```yaml
# User writes:
python:
 tools:
 pytest: true
 mypy: false

# normalize.py converts to:
python:
 tools:
 pytest: { enabled: true }
 mypy: { enabled: false }
```

**Code in `cihub/config/normalize.py:37-46`:**
```python
def _normalize_tool_configs_inplace(config: dict[str, Any]) -> None:
 for lang in ("python", "java"): # ← HARDCODED
 lang_config = config.get(lang)
 if not isinstance(lang_config, dict):
 continue
 tools = lang_config.get("tools")
 if not isinstance(tools, dict):
 continue
 for tool_name, tool_value in list(tools.items()):
 if isinstance(tool_value, bool):
 tools[tool_name] = {"enabled": tool_value}
```

### 18.2 Problems with Current Design

1. **Languages hardcoded:** `for lang in ("python", "java")` blocks new languages
2. **Unknown tools rejected:** `additionalProperties: false` in schema
3. **No custom tool settings:** Only predefined fields allowed

### 18.3 Proposed Extensible Design

**Approach: Dynamic Language/Tool Registry**

```python
# cihub/config/normalize.py (UPDATED)

def _normalize_tool_configs_inplace(config: dict[str, Any]) -> None:
 """Normalize tool configs for all registered languages."""
 from cihub.core.languages import get_registered_languages

 for lang in get_registered_languages(): # Dynamic, not hardcoded
 lang_config = config.get(lang)
 if not isinstance(lang_config, dict):
 continue
 tools = lang_config.get("tools")
 if not isinstance(tools, dict):
 continue
 for tool_name, tool_value in list(tools.items()):
 if isinstance(tool_value, bool):
 tools[tool_name] = {"enabled": tool_value}
```

**Schema Changes:**
```json
{
 "python": {
 "type": "object",
 "properties": {
 "tools": {
 "type": "object",
 "additionalProperties": {
 "oneOf": [
 { "type": "boolean" },
 { "$ref": "#/$defs/tool_config" }
 ]
 }
 }
 }
 }
}
```

**Key:** `additionalProperties` allows ANY tool name, validated against `tool_config` schema.

### 18.4 Progressive Strictness Modes

```yaml
# config/defaults.yaml
validation:
 mode: strict # Options: strict, standard, permissive

# strict: Only known tools, all fields validated
# standard: Known tools + x-custom fields allowed
# permissive: Any tools, minimal validation
```

### 18.5 Custom Tool Example

```yaml
# User's .ci-hub.yml with custom tool
python:
 tools:
 pytest: true
 mypy: { enabled: true }
 x-custom-linter: # x- prefix for custom tools
 enabled: true
 command: "./run-custom-lint.sh"
 fail_on_error: true
```

**Schema with x- prefix:**
```json
{
 "patternProperties": {
 "^x-": {
 "$ref": "#/$defs/custom_tool_config"
 }
 }
}
```

---

## Part 19: AI INTEGRATION CONSIDERATIONS

**Audit Date:** 2026-01-06
**Focus:** How AI could enhance (not replace) the tooling

### 19.1 Realistic AI Use Cases

| Use Case | Feasibility | Value |
|----------|------------|-------|
| Repo analysis & detection | [x] HIGH | Suggest language/tools |
| Config optimization | [x] HIGH | Suggest better thresholds |
| Error explanation | [x] HIGH | Explain why gate failed |
| Migration assistance | MEDIUM | Help migrate from other CI |
| Language template generation | MEDIUM | Accelerate new language support |
| Dynamic tool generation | [ ] LOW | Too risky, not maintainable |

### 19.2 Recommended AI Integration Points

**Point 1: `cihub analyze <repo>`**
```bash
cihub analyze https://github.com/user/repo

# AI output:
Detected: JavaScript/TypeScript project
Recommended tools:
 - jest (testing)
 - eslint (linting)
 - npm-audit (security)
Suggested profile: javascript-quality
```

**Point 2: `cihub explain <failure>`**
```bash
cihub explain --last-run

# AI output:
Coverage gate failed (78% < 80%)
Uncovered files:
 - src/utils/parser.js (45% coverage)
 - src/handlers/auth.js (62% coverage)
Suggestion: Add tests for parser.js error handling
```

**Point 3: `cihub suggest-config`**
```bash
cihub suggest-config --from-repo production-api

# AI output:
Based on your production-api config and best practices:
Recommended changes:
 - Enable semgrep for security scanning
 - Increase coverage threshold to 85% (you're at 92%)
 - Add trivy for container scanning
```

### 19.3 What AI Should NOT Do

1. **NOT:** Generate tool runners at runtime
2. **NOT:** Dynamically create language support
3. **NOT:** Make decisions about security gates
4. **NOT:** Execute arbitrary code
5. **NOT:** Replace deterministic validation

### 19.4 Implementation Approach

**Phase 1: Local Analysis (No API)**
- Static analysis of repo structure
- Pattern matching for language detection
- Rule-based config suggestions

**Phase 2: Optional AI Enhancement**
- API call to Claude/GPT for explanations
- Opt-in, not required for core functionality
- All suggestions require user confirmation

**Phase 3: Learning from Patterns**
- Aggregate successful configs
- Learn what works for different repo types
- Privacy-preserving (no code sent to API)

---

## Appendix C: Second Audit Agent Findings (2026-01-06)

### Agent 1: Sync Verification Gaps
- 9 synchronization gaps identified
- CRITICAL: Wizard → Registry not connected
- CRITICAL: Registry → YAML only syncs 3 fields
- HIGH: No YAML → Workflow verification
- Recommended: `cihub verify --step` commands

### Agent 2: Testing Strategy
- Current: 80+ test files, incomplete coverage
- Missing: registry_service.py unit tests
- Missing: Wizard → Registry integration tests
- Proposed: ~1,350 lines of new tests across 6 categories
- Target: >95% line coverage, >80% mutation score

### Agent 3: Boolean Toggle Extensibility
- Current: Languages hardcoded in normalize.py
- Problem: `additionalProperties: false` blocks custom tools
- Solution: Dynamic language registry + schema pattern properties
- Maintains `tool: true` shorthand while allowing extensibility

### Agent 4: Pipeline Edge Cases
- 38+ edge cases identified across pipeline
- Categories: Wizard, Registry, YAML, CI Engine, Cross-cutting
- CRITICAL: Concurrent modifications, partial updates
- HIGH: Orphaned configs, schema mismatches
- Recommended: Edge case test suite (~25 tests)

### Agent 5: Language Addition Reality
- Adding JavaScript requires modifying 27 files
- NOT user-extensible - requires developer implementation
- Recommended: Gradual addition, test with JavaScript first
- Future: Extract language plugin pattern after 3rd language

### Web Research Findings
- Travis CI: Multi-language via config matrix
- Litho: Plugin-based extensibility architecture
- GitHub Actions: Nested reusable workflows (up to 10 levels)
- Pre-commit: Language field in hooks with system fallback
- LLMs: 69% config similarity with zero-shot prompting (research)