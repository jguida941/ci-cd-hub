# Test Suite Reorganization Plan

**Status:** active
**Owner:** Development Team
**Source-of-truth:** manual
**Last-reviewed:** 2026-01-15

**Date:** 2026-01-05
**Status:** CURRENT (blocked by prerequisites)
**Priority:** **#3** (See [MASTER_PLAN.md](../MASTER_PLAN.md#active-design-docs---priority-order))
**Depends On:** CLEAN_CODE.md (archived, complete) + SYSTEM_INTEGRATION_PLAN.md (archived, complete)
**Blocks:** Nothing (can run parallel with DOC_AUTOMATION after blockers resolved)

---

## Critical Test Gaps (7-Agent Audit 2026-01-06)

> **Source:** Comprehensive 7-agent code review. These are HIGH PRIORITY gaps.

### Commands Needing Tests

| Command | Current Coverage | Missing |
|---------|------------------|---------|
| `cmd_registry` | **0%** | All 6 subcommands, error paths |
| `cmd_fix` | ~40% | Error paths, tool failures, edge cases |
| `cmd_check` | ~30% | Timeout handling, mode combinations |
| `hub_ci/*` (49 commands) | ~5% | Most commands untested |

### Services Needing Tests

| Service | Tests? | Priority |
|---------|--------|----------|
| `triage/detection.py` | [ ] None | **CRITICAL** |
| `triage/evidence.py` | [ ] None | **CRITICAL** |
| `ci_engine/gates.py` | [ ] None | HIGH |
| `ci_engine/helpers.py` | [ ] None | HIGH |
| `repo_config.py` | [ ] None | MEDIUM |
| `registry_service.py` | [ ] None | **CRITICAL** (see REGISTRY_AUDIT_AND_PLAN.md Part 15 - archived) |

**Note:** Registry service testing is comprehensively covered in `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` Part 15 with 6 test categories and ~1,350 lines of test code proposed.

---

## Problem Statement

The test suite has grown to **2100+ tests** across files with:
- Generic names that don't describe what's being tested
- No consistent structure or organization pattern
- Mixed test types (unit, integration, e2e) in single files
- No visibility into coverage/mutation targets vs actuals
- Hard to onboard new developers or understand test purpose

**Risk:** As the codebase grows, unmaintainable tests become a liability rather than an asset.

---

## Goals

1. **Organized structure** - Tests grouped by type and module
2. **Living documentation** - Auto-generated README with metrics
3. **No hard-coded drift** - Targets in config, actuals auto-updated
4. **Consistent patterns** - Template enforcement like ADRs
5. **Better test IDs** - Descriptive names visible in pytest output
6. **Automated drift detection** - CI catches missing/stale tests

---

## Mutation Testing Coverage Plan (CLI + Core Logic)

**Current state:** `mutmut` only targets a few low-risk modules. CLI command logic and core services are not mutation-tested.

**Goal:** expand mutation targets to cover the CLI and core logic without making mutation runs flaky or blocking by default.

### Rollout Phases

- [ ] **M0: Baseline + inventory** - Document current `paths_to_mutate` and add a per-module target list to this plan. Capture a baseline mutation run per module before expanding.
  - [x] Add per-module target list to this plan.
  - [~] Capture baseline mutation runs for each phase target (global baseline captured; per-module baselines pending).
- [ ] **M1: CLI critical path** - Add `cihub/commands/ci.py`, `cihub/services/ci_engine/`, and `cihub/commands/check.py` to mutation targets. Kill surviving mutants with focused tests.
  - [x] Update `pyproject.toml` `paths_to_mutate` for M1 targets.
  - [~] Kill surviving mutants with targeted tests (CI CLI adapter tests added; rerun mutmut for `cihub/commands/ci.py` pending).
- [ ] **M2: Config + outputs** - Add `cihub/commands/config_outputs.py`, `cihub/config/loader/inputs.py`, and `cihub/services/registry/thresholds.py` to mutation targets.
- [ ] **M3: Triage + reporting** - Add `cihub/services/triage/detection.py` and `cihub/commands/triage/log_parser.py` to mutation targets.
- [ ] **M4: High-risk commands** - Add `cihub/commands/fix.py`, `cihub/commands/registry.py`, `cihub/commands/templates.py`, and `cihub/commands/secrets.py` once external I/O is isolated behind mocks.

### Baseline Status (2026-01-15)

- pytest in the local venv segfaults when importing `readline` (seen in `_pytest/capture._readline_workaround`).
- Workaround: patch `_pytest/capture.py` to honor `PYTEST_SKIP_READLINE_WORKAROUND=1`, then set that env var for mutmut runs.
- Patched mutmut trampoline template to use `os.environ.get("MUTANT_UNDER_TEST", "")` to avoid KeyError during stats collection.
- `mutmut` stats runs failed when subprocess CLI calls inherited `MUTANT_UNDER_TEST=stats` (mutmut config is None in subprocess, `record_trampoline_hit` crashes). Added a test harness guard to strip `MUTANT_UNDER_TEST`/`MUTATION_SCORE_MIN` from subprocess env; clear `mutants/` and rerun with `PYTEST_SKIP_READLINE_WORKAROUND=1`.
- Clean tests failed in `tests/test_property_based_extended.py` with Hypothesis `HealthCheck.differing_executors` during mutmut. Added `--ignore-glob=**/test_property_based_extended.py` to mutmut pytest args (matches the “ignore @given tests” policy).
- `python -m cihub hub-ci coverage-verify --coverage-file .coverage --json` succeeds and reports 231 measured files with mutation targets covered (overall coverage ~75%).
- `mutmut run` completes with `PYTEST_SKIP_READLINE_WORKAROUND=1`: 4475 mutants, 2284 killed, 2187 survived, 3 timeouts, 1 suspicious (~51% score).
- Survivors cluster in `cihub.services.ci_engine.gates`, `cihub.commands.check`, and `cihub.commands.ci`.

### Target Modules (Tracked)

| Module | Phase | Owner | Notes |
|--------|-------|-------|-------|
| `cihub/commands/ci.py` | M1 | TBD | CLI entry point for CI |
| `cihub/services/ci_engine/` | M1 | TBD | Core CI execution + gating |
| `cihub/commands/check.py` | M1 | TBD | CLI local validation |
| `cihub/commands/config_outputs.py` | M2 | TBD | Workflow outputs contract |
| `cihub/config/loader/inputs.py` | M2 | TBD | Input normalization |
| `cihub/services/registry/thresholds.py` | M2 | TBD | Threshold normalization |
| `cihub/services/triage/detection.py` | M3 | TBD | Flaky detection |
| `cihub/commands/triage/log_parser.py` | M3 | TBD | Mutmut log parsing |
| `cihub/commands/fix.py` | M4 | TBD | Fix workflows (high risk) |
| `cihub/commands/registry.py` | M4 | TBD | Registry CLI surface |
| `cihub/commands/templates.py` | M4 | TBD | Template sync logic |
| `cihub/commands/secrets.py` | M4 | TBD | External API + secret ops |

### Guardrails

- Only add a module to `paths_to_mutate` after coverage is high enough to make mutation results actionable.
- Keep `mutate_only_covered_lines = true` and the existing mutmut pytest filters to avoid flaky runs.
- Mutation runs stay opt-in via `cihub check --mutation` unless a workflow or defaults change is approved.
- Track per-module mutation scores in `tests/README.md` and treat regressions as drift.

---

## Proposed Directory Structure

```
tests/
├── README.md # AUTO-GENERATED: Test catalog with metrics
├── conftest.py # Shared fixtures, markers
│ # NOTE: Targets live in config/defaults.yaml (hub_ci.thresholds)
│
├── unit/ # Fast, isolated, no I/O
│ ├── commands/ # One file per command module
│ │ ├── test_detect.py
│ │ ├── test_validate.py
│ │ ├── test_init.py
│ │ └── ...
│ ├── services/
│ │ ├── test_ci_engine.py
│ │ ├── test_triage.py
│ │ └── ...
│ ├── core/
│ │ ├── test_gate_specs.py
│ │ ├── test_ci_report.py
│ │ └── ...
│ └── config/
│ ├── test_schema.py
│ ├── test_normalize.py
│ └── ...
│
├── integration/ # Cross-module, may use filesystem
│ ├── test_cli_commands.py # CLI → command → service flow
│ ├── test_config_loading.py # Config cascade integration
│ └── ...
│
├── e2e/ # Full workflows, slow
│ ├── test_python_workflow.py
│ ├── test_java_workflow.py
│ └── test_smoke_workflows.py
│
├── contracts/ # Schema/API contract tests
│ ├── test_command_output_contract.py
│ ├── test_schema_contract.py
│ ├── test_cli_parser_contracts.py
│ └── ...
│
├── property/ # Hypothesis property-based tests
│ ├── test_config_properties.py
│ ├── test_parsing_properties.py
│ └── ...
│
├── regression/ # Bug reproduction tests
│ ├── test_issue_001_yaml_parse.py
│ └── ...
│
└── snapshots/ # Snapshot test data
 └── ...
```

---

## Living Test Metadata System

### Problem with Hard-Coded Values

```python
# BAD: This will drift and become stale
"""
Coverage Target: 90% # <-- Who updates this? When?
"""
```

### Solution: Use Existing Architecture

**The infrastructure already exists!** The hub-production-ci.yml workflow already:
1. Reads thresholds from `config/defaults.yaml`
2. Emits them as GitHub outputs via `cihub hub-ci outputs`
3. Uses them in test jobs

**Single Source of Truth: `config/defaults.yaml` (lines 426-428):**
```yaml
hub_ci:
 thresholds:
 coverage_min: 70
 mutation_score_min: 70
```

**Flow:**
```
config/defaults.yaml
 ↓
cihub hub-ci outputs --github-output
 ↓
hub-production-ci.yml jobs read outputs
 ↓
pytest --cov-fail-under=${{ needs.hub-ci-config.outputs.coverage_min }}
```

### CLI Commands to Manage (NEW)

```bash
# View current thresholds
cihub hub-ci thresholds

# Set thresholds (updates config/defaults.yaml)
cihub hub-ci thresholds --set coverage_min 90
cihub hub-ci thresholds --set mutation_score_min 75

# Interactive mode
cihub hub-ci thresholds --wizard
```

### Per-Module Overrides (Future Enhancement)

For module-specific thresholds, extend `config/defaults.yaml`:
```yaml
hub_ci:
 thresholds:
 coverage_min: 90
 mutation_score_min: 75

 # Per-module overrides
 overrides:
 services/triage:
 coverage_min: 80
 mutation_score_min: 60
 note: "Legacy code - see archive/CLEAN_CODE.md"
```

### Auto-Generated Test File Headers

Each test file has an auto-updated header block (populated by CI):

```python
"""Tests for detect command.

Module: cihub/commands/detect.py
Test Categories: unit, contract

<!-- TEST-METRICS: Auto-generated by CI, do not edit -->
| Metric | Actual | Target | Status |
|--------|--------|--------|--------|
| Coverage | 94.2% | 90% | PASS |
| Mutation | 78.5% | 75% | PASS |
| Tests | 12 | - | - |
| Last Run | 2026-01-05 14:32 | - | - |
<!-- END TEST-METRICS -->
"""
```

**Key Point:** Targets come from `config/defaults.yaml`, not hard-coded. The header shows actuals vs targets but doesn't define them.

### Auto-Generated README

**`tests/README.md`** (generated by CI):

```markdown
# Test Suite Overview

> Auto-generated on 2026-01-05 14:32:01. Do not edit manually.

## Summary

- **Total Tests:** 2,104
- **Pass Rate:** 100%
- **Average Coverage:** 91.2%
- **Average Mutation Score:** 76.8%

## Coverage by Module

| Test File | Module | Coverage | Target | Mutation | Target | Status |
|-----------|--------|----------|--------|----------|--------|--------|
| unit/commands/test_detect.py | commands/detect.py | 94.2% | 90% | 78.5% | 75% | [x] |
| unit/commands/test_validate.py | commands/validate.py | 91.0% | 90% | 82.1% | 75% | [x] |
| unit/services/test_triage.py | services/triage/ | 81.2% | 80% | 62.3% | 60% | [x] |
| unit/services/test_ci_engine.py | services/ci_engine/ | 87.5% | 90% | 71.2% | 75% | WARNING: |

### Files Below Target

| File | Issue | Gap |
|------|-------|-----|
| test_ci_engine.py | Coverage 87.5% < 90% | -2.5% |
| test_ci_engine.py | Mutation 71.2% < 75% | -3.8% |

### New Files (not in targets.yaml)

- `test_new_feature.py` - needs to be added to coverage_targets.yaml

## Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| unit | 1,423 | Fast, isolated unit tests |
| integration | 312 | Cross-module integration |
| e2e | 89 | End-to-end workflows |
| contract | 156 | API/schema contracts |
| property | 78 | Hypothesis property tests |
| regression | 46 | Bug reproduction tests |
```

---

## Test File Template

Each test file follows this structure:

```python
"""Tests for {module_name}.

Module: cihub/{module_path}
Test Categories: unit, contract

<!-- TEST-METRICS: Auto-generated, do not edit -->
<!-- END TEST-METRICS -->
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

# Module under test
from cihub.commands.detect import cmd_detect


class TestDetectSuccess:
 """Happy path tests for detect command."""

 @pytest.mark.parametrize(
 "marker_file,expected_language",
 [
 ("pyproject.toml", "python"),
 ("pom.xml", "java"),
 ("build.gradle", "java"),
 ],
 ids=["python-pyproject", "java-maven", "java-gradle"],
 )
 def test_detect_identifies_language_from_marker(
 self, tmp_path, marker_file, expected_language
 ):
 """Detect correctly identifies language from project markers."""
 (tmp_path / marker_file).write_text("minimal content")
 # ... test implementation


class TestDetectErrors:
 """Error handling tests for detect command."""

 def test_detect_empty_directory_returns_failure(self, tmp_path):
 """Empty directory without markers returns EXIT_FAILURE."""
 # ... test implementation

 def test_detect_nonexistent_path_returns_error(self, tmp_path):
 """Non-existent path returns structured error."""
 # ... test implementation


class TestDetectEdgeCases:
 """Boundary condition tests for detect command."""

 def test_detect_with_multiple_markers_prefers_pyproject(self, tmp_path):
 """When multiple markers exist, pyproject.toml takes precedence."""
 # ... test implementation


class TestDetectProperties:
 """Property-based tests for detect command."""

 @given(st.text(min_size=1, max_size=50))
 def test_detect_language_override_always_returned(self, language):
 """Property: language override is always respected."""
 # ... test implementation
```

---

## Automation Scripts

### 1. Update Test Metrics (`scripts/update_test_metrics.py`)

```python
"""Update test file headers with coverage/mutation metrics.

Usage: python scripts/update_test_metrics.py

Reads coverage_targets.yaml and updates each test file's
TEST-METRICS block with actual values.
"""
```

**Runs:** After pytest with coverage, after mutmut

### 2. Generate Test README (`scripts/generate_test_readme.py`)

```python
"""Generate tests/README.md from coverage data.

Usage: python scripts/generate_test_readme.py

Aggregates all test metrics into a summary README.
"""
```

**Runs:** In CI after test suite completes

### 3. Check Test Drift (`scripts/check_test_drift.py`)

```python
"""Check for test organization drift.

Usage: python scripts/check_test_drift.py

Checks:
- All test files have TEST-METRICS block
- All test files are in coverage_targets.yaml
- No files below target thresholds
- Template structure compliance
"""
```

**Runs:** In CI, fails build on drift

---

## Migration Plan

### Phase 1: Infrastructure (Day 1)
- [x] Add `cihub hub-ci thresholds` command (read/write to config/defaults.yaml)
- [x] Add per-module override support to config/defaults.yaml schema
- [x] Create `scripts/update_test_metrics.py` (reads targets from config/defaults.yaml)
- [x] Create `scripts/generate_test_readme.py`
- [x] Create `scripts/check_test_drift.py`
- [ ] Add to CI workflow (hub-production-ci.yml)
- [x] Add schema-sync fallback defaults regression coverage (gates/reports/feature flags)

### Phase 2: Directory Structure (Day 2)
- [ ] Create new directory structure (`unit/`, `integration/`, etc.)
- [ ] Move contract tests to `contracts/`
- [ ] Move e2e tests to `e2e/`
- [ ] Update imports in moved files

### Phase 3: Unit Test Reorganization (Days 3-5)
- [ ] Split `test_commands.py` into `unit/commands/test_*.py`
- [ ] Split `test_services_*.py` into `unit/services/test_*.py`
- [ ] Split `test_config_*.py` into `unit/config/test_*.py`
- [ ] Add parameterized tests where applicable
- [ ] Add descriptive test IDs

### Phase 4: Property Tests (Day 6)
- [ ] Identify pure functions suitable for Hypothesis
- [ ] Create `property/` tests for config parsing
- [ ] Create `property/` tests for validators
- [ ] Target: 5% of tests are property-based

### Phase 5: Documentation (Day 7)
- [ ] Generate initial `tests/README.md`
- [ ] Update `MASTER_PLAN.md` with test architecture
- [ ] Archive this document to `docs/adr/` as completed

---

## Success Criteria

1. **All tests pass** after reorganization
2. **README auto-generates** with accurate metrics
3. **Drift detection** catches missing targets
4. **No hard-coded** coverage values in test files
5. **Clear test IDs** visible in pytest output
6. **New developer** can understand test structure in < 10 minutes

---

## Related Documents

- `CLEAN_CODE.md` (archived) - Code quality improvements (complete first)
- `MASTER_PLAN.md` - Overall architecture
- `CI_PARITY.md` - CI/CD pipeline documentation

---

## Open Questions

1. Should we use pytest markercodes (`@pytest.mark.unit`) or rely on directory structure?
2. How frequently should mutation testing run? (Expensive)
3. Should regression tests reference GitHub issue numbers?
4. Integration with IDE test runners (VSCode, PyCharm)?

---

## Audit Findings (2026-01-05)

**5-agent parallel audit identified critical gaps:**

### Critical Blockers

| Blocker | Status | Effort |
|---------|--------|--------|
| `cihub hub-ci thresholds` CLI command | [x] IMPLEMENTED | Done |
| Schema per-module overrides | [x] IMPLEMENTED | Done |
| 3 automation scripts | [x] IMPLEMENTED | Done |
| Only 2/15 thresholds in CI outputs | WARNING: INCOMPLETE | 2 days |

**Estimated effort before Phase 1: ~3 days** (schema overrides + CI workflow)

### Test File Coverage Gap

- **145 total files** in `tests/` directory (127 test files + 18 supporting files)
- **136 files (94%)** map cleanly to proposed categories
- **5 files** require splitting before moving (see "Monolithic File Split Plan")
- **4 files** with excellent cohesion kept as-is despite size

### Missing Directory Categories

Add to proposed structure:
```
tests/unit/core/languages/ # POM parsing, badges, detection (5 files)
tests/unit/core/output/ # Renderers, context (2 files)
tests/unit/core/diagnostics/ # Diagnostics, correlation (3 files)
tests/unit/utils/ # Helpers, shims (7 files)
tests/unit/wizard/ # Form validation, questions (2 files)
tests/unit/templates/ # Template rendering (1 file)
tests/performance/ # Benchmark tests
tests/validation/ # Module structure validation
```

### Drift Detection Gaps

Current plan covers ~20% of drift scenarios. Add detection for:

| Category | Missing Detection |
|----------|-------------------|
| **File lifecycle** | New files not registered, deleted files orphaned |
| **Naming** | Test class/method naming conventions |
| **Parameterization** | Similar tests that should be consolidated |
| **Performance** | Unit > 1s, integration > 5s, e2e > 30s |
| **Flakiness** | Timing-dependent, order-dependent |
| **Fixtures** | Scope violations, circular dependencies |

### CI Integration Gaps

New jobs required in `hub-production-ci.yml`:
1. `generate-test-readme` - After mutation-tests
2. `check-test-drift` - After README generation
3. `update-test-metrics` - Updates file headers (main only)

### Large Monolithic Files

Split before moving:
- `test_ci_engine.py` (120 tests) → 6-8 focused files
- `test_config_module.py` (77 tests) → 3-4 focused files
- `test_commands_adr.py` (59 tests) → 2-3 focused files

### Schema Updates Required

```json
// schema/ci-hub-config.schema.json - Add to hub_ci.thresholds
"overrides": {
 "type": "object",
 "additionalProperties": {
 "type": "object",
 "properties": {
 "coverage_min": { "type": "integer" },
 "mutation_score_min": { "type": "integer" },
 "note": { "type": "string" }
 }
 }
}
```

### Updated Phase 0 (NEW - Pre-Implementation)

Before Phase 1 can begin:
- [x] Implement `cihub hub-ci thresholds` command
- [x] Update schema for per-module overrides
- [x] Validate wizard/CLI on fixture repos (subdir detection, POM warnings, aggregation status)
- [x] Add CLI workflow dispatch/watch with wizard wrapper (ADR-0055)
- [x] Align Java templates with CLI config (remove repo-specific PITest targets; honor `use_nvd_api_key`)
- [x] Create comprehensive file mapping (all 145 files → new homes) — **COMPLETED 2026-01-17**
- [ ] Split large monolithic test files (see "Monolithic File Split Plan" below)
- [x] Register pytest markers in pyproject.toml

---

## Phase 0: Comprehensive File Mapping (145 Files)

> **Completed:** 2026-01-17 | **Author:** 8-Agent Parallel Analysis
>
> **Note:** Original estimate was 78 files. Actual count is **145 files** including:
> - 127 `test_*.py` files in root
> - 6 subdirectory test files
> - 2 snapshot files
> - 2 conftest.py files
> - 5 `__init__.py` package markers
> - 3 additional data/fixture files

### Supporting Files (Keep in Place)

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/conftest.py` | `tests/conftest.py` | fixture | Root fixture config; keep at root |
| `tests/__snapshots__/test_cli_snapshots.ambr` | `tests/snapshots/__snapshots__/test_cli_snapshots.ambr` | snapshot | Move with snapshot tests |
| `tests/snapshots/cli_help.txt` | `tests/snapshots/cli_help.txt` | snapshot | Already in correct location |
| `tests/test_repo_shapes/conftest.py` | `tests/integration/repo_shapes/conftest.py` | fixture | Move with repo shape tests |
| `tests/test_config_precedence/__init__.py` | `tests/unit/config/__init__.py` | marker | Merge into unit/config |
| `tests/test_registry/__init__.py` | `tests/unit/services/__init__.py` | marker | Merge into unit/services |
| `tests/test_repo_shapes/__init__.py` | `tests/integration/repo_shapes/__init__.py` | marker | Move with repo shape tests |
| `tests/test_schema_validation/__init__.py` | `tests/contracts/__init__.py` | marker | Merge into contracts |
| `tests/test_wizard_flows/__init__.py` | `tests/integration/wizard/__init__.py` | marker | Move with wizard tests |

### Contract Tests → `tests/contracts/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_cli_parser_contracts.py` | `contracts/test_cli_parser_contracts.py` | contract | CLI parser structure contracts |
| `test_command_output_contract.py` | `contracts/test_command_output_contract.py` | contract | CommandResult output contracts |
| `test_contract_command_result.py` | `contracts/test_contract_command_result.py` | contract | CommandResult field contracts |
| `test_contract_consistency.py` | `contracts/test_contract_consistency.py` | contract | Gate/report consistency |
| `test_migrated_commands_contract.py` | `contracts/test_migrated_commands_contract.py` | contract | Migration verification |
| `test_schema_contract.py` | `contracts/test_schema_contract.py` | contract | Schema compliance |
| `test_workflow_contract.py` | `contracts/test_workflow_contract.py` | contract | Workflow input/output contracts |
| `test_cli_contracts/test_json_purity.py` | `contracts/test_json_purity.py` | contract | JSON output purity |
| `test_schema_validation/test_schema_fields.py` | `contracts/test_schema_fields.py` | contract | Schema field validation |
| `test_registry_schema_contract.py` | `contracts/test_registry_schema_contract.py` | contract | Registry schema contracts |

### E2E Tests → `tests/e2e/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_e2e_smoke.py` | `e2e/test_smoke_workflows.py` | e2e | Full Python/Java workflows |
| `test_cli_integration.py` | `e2e/test_cli_integration.py` | e2e | Full CLI command sequences |
| `test_setup_flow.py` | `e2e/test_setup_flow.py` | e2e | Complete init workflow |
| `test_triage_integration.py` | `e2e/test_triage_integration.py` | e2e | Full triage with CI artifacts |

### Property-Based Tests → `tests/property/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_property_based.py` | `property/test_core_properties.py` | property | Core Hypothesis tests |
| `test_property_based_extended.py` | `property/test_extended_properties.py` | property | Extended property tests |
| `test_triage_properties.py` | `property/test_triage_properties.py` | property | Triage logic properties |
| `test_registry_roundtrip_invariant.py` | `property/test_registry_roundtrip.py` | property | Registry import/export invariants |

### Snapshot Tests → `tests/snapshots/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_cli_snapshots.py` | `snapshots/test_cli_snapshots.py` | snapshot | CLI help output stability |
| `test_summary_commands.py` | `snapshots/test_summary_snapshots.py` | snapshot | Report summary snapshots |
| `test_module_structure.py` | `snapshots/test_module_structure.py` | snapshot | Module structure snapshots |

### Integration Tests → `tests/integration/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_fixture_repo_shapes.py` | `integration/test_fixture_repo_shapes.py` | integration | Multi-repo shape testing |
| `test_integration_check.py` | `integration/test_integration_check.py` | integration | Check command integration |
| `test_template_drift.py` | `integration/test_template_drift.py` | integration | Template sync integration |
| `test_templates.py` | `integration/test_templates.py` | integration | Template rendering integration |
| `test_config_pipeline.py` | `integration/test_config_pipeline.py` | integration | Config cascade integration |
| `test_services_aggregation.py` | `integration/test_services_aggregation.py` | integration | Report aggregation workflow |
| `test_repo_shapes/test_ci_shapes.py` | `integration/repo_shapes/test_ci_shapes.py` | integration | CI repo shape tests |
| `test_repo_shapes/test_detect_shapes.py` | `integration/repo_shapes/test_detect_shapes.py` | integration | Detection shape tests |
| `test_repo_shapes/test_init_shapes.py` | `integration/repo_shapes/test_init_shapes.py` | integration | Init shape tests |
| `test_wizard_flows/test_cli_wizard_parity.py` | `integration/wizard/test_cli_wizard_parity.py` | integration | CLI/wizard parity |
| `test_wizard_flows/test_profile_selection.py` | `integration/wizard/test_profile_selection.py` | integration | Profile selection flow |
| `test_wizard_flows/test_wizard_modules.py` | `integration/wizard/test_wizard_modules.py` | integration | Wizard module integration |

### Regression Tests → `tests/regression/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_triage_detection.py` | `regression/test_triage_detection.py` | regression | Regression detection tests |

### Performance Tests → `tests/performance/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_performance.py` | `performance/test_performance.py` | performance | Benchmark tests |

### Validation Tests → `tests/validation/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_validation.py` | `validation/test_validation.py` | validation | Input validation |
| `test_validate_config.py` | `validation/test_validate_config.py` | validation | Config validation |

### Unit Tests: Commands → `tests/unit/commands/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_commands.py` | `unit/commands/test_commands_base.py` | unit | Generic command tests |
| `test_commands_adr.py` | `unit/commands/test_adr.py` | unit | ADR command tests |
| `test_commands_check.py` | `unit/commands/test_check.py` | unit | Check command tests |
| `test_commands_ci.py` | `unit/commands/test_ci.py` | unit | CI command tests |
| `test_commands_discover.py` | `unit/commands/test_discover.py` | unit | Discover command tests |
| `test_commands_dispatch.py` | `unit/commands/test_dispatch.py` | unit | Dispatch command tests |
| `test_commands_docs.py` | `unit/commands/test_docs.py` | unit | Docs command tests |
| `test_commands_extended.py` | `unit/commands/test_extended.py` | unit | Extended command tests |
| `test_commands_new.py` | `unit/commands/test_new.py` | unit | New command tests |
| `test_commands_preflight.py` | `unit/commands/test_preflight.py` | unit | Preflight command tests |
| `test_commands_scaffold.py` | `unit/commands/test_scaffold.py` | unit | Scaffold command tests |
| `test_commands_smoke.py` | `unit/commands/test_smoke.py` | unit | Smoke command tests |
| `test_commands_templates.py` | `unit/commands/test_templates.py` | unit | Templates command tests |
| `test_config_cmd.py` | `unit/commands/test_config_cmd.py` | unit | Config command tests |
| `test_fix_command.py` | `unit/commands/test_fix_command.py` | unit | Fix command tests |
| `test_fix_unit.py` | `unit/commands/test_fix_unit.py` | unit | Fix unit tests |
| `test_gradle_cmd.py` | `unit/commands/test_gradle_cmd.py` | unit | Gradle command tests |
| `test_pom_cmd.py` | `unit/commands/test_pom_cmd.py` | unit | POM command tests |
| `test_profile_cmd.py` | `unit/commands/test_profile_cmd.py` | unit | Profile command tests |
| `test_registry_cmd.py` | `unit/commands/test_registry_cmd.py` | unit | Registry command tests |
| `test_repo_cmd.py` | `unit/commands/test_repo_cmd.py` | unit | Repo command tests |
| `test_run.py` | `unit/commands/test_run.py` | unit | Run command tests |
| `test_smoke_command.py` | `unit/commands/test_smoke_command.py` | unit | Smoke command tests |
| `test_threshold_cmd.py` | `unit/commands/test_threshold_cmd.py` | unit | Threshold command tests |
| `test_tool_cmd.py` | `unit/commands/test_tool_cmd.py` | unit | Tool command tests |
| `test_tool_cmd_extended.py` | `unit/commands/test_tool_cmd_extended.py` | unit | Tool command extended |

### Unit Tests: Services → `tests/unit/services/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_ci_engine.py` | `unit/services/ci_engine/` (SPLIT) | unit | **MONOLITHIC - SPLIT** |
| `test_ci_runner.py` | `unit/services/ci_runner/` (SPLIT) | unit | **MONOLITHIC - SPLIT** |
| `test_services_ci.py` | `unit/services/test_ci.py` | unit | CI service tests |
| `test_services_configuration.py` | `unit/services/test_configuration.py` | unit | Config service tests |
| `test_services_discovery.py` | `unit/services/test_discovery.py` | unit | Discovery service tests |
| `test_services_report_summary.py` | `unit/services/test_report_summary.py` | unit | Report summary service |
| `test_services_report_validator.py` | `unit/services/test_report_validator.py` | unit | Report validator service |
| `test_triage_service.py` | `unit/services/test_triage_service.py` | unit | Triage service tests |
| `test_triage_evidence.py` | `unit/services/test_triage_evidence.py` | unit | Triage evidence tests |
| `test_triage_github.py` | `unit/services/test_triage_github.py` | unit | Triage GitHub tests |
| `test_triage_log_parser.py` | `unit/services/test_triage_log_parser.py` | unit | Triage log parser tests |
| `test_triage_verification.py` | `unit/services/test_triage_verification.py` | unit | Triage verification tests |
| `test_registry/test_registry_service.py` | `unit/services/test_registry_service.py` | unit | Registry service tests |

### Unit Tests: Config → `tests/unit/config/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_config_module.py` | `unit/config/` (SPLIT) | unit | **MONOLITHIC - SPLIT** |
| `test_ci_config.py` | `unit/config/test_ci_config.py` | unit | CI config tests |
| `test_config_outputs.py` | `unit/config/test_config_outputs.py` | unit | Config outputs tests |
| `test_repo_config.py` | `unit/config/test_repo_config.py` | unit | Repo config tests |
| `test_apply_profile.py` | `unit/config/test_apply_profile.py` | unit | Profile application tests |
| `test_schema_sync.py` | `unit/config/test_schema_sync.py` | unit | Schema sync tests |
| `test_config_precedence/test_merge_order.py` | `unit/config/test_merge_order.py` | unit | Config merge order tests |

### Unit Tests: Core → `tests/unit/core/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_ci_report.py` | `unit/core/test_ci_report.py` | unit | CI report tests |
| `test_gate_specs.py` | `unit/core/test_gate_specs.py` | unit | Gate spec tests |
| `test_ci_env_overrides.py` | `unit/core/test_ci_env_overrides.py` | unit | Env override tests |
| `test_ci_self_validate.py` | `unit/core/test_ci_self_validate.py` | unit | Self-validation tests |
| `test_fail_on_normalization.py` | `unit/core/test_fail_on_normalization.py` | unit | Normalization tests |
| `test_init_override.py` | `unit/core/test_init_override.py` | unit | Init override tests |

### Unit Tests: Core/Languages → `tests/unit/core/languages/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_pom_parsing.py` | `unit/core/languages/test_pom_parsing.py` | unit | POM parsing tests |
| `test_pom_tools.py` | `unit/core/languages/test_pom_tools.py` | unit | POM tool tests |
| `test_python_ci_badges.py` | `unit/core/languages/test_python_ci_badges.py` | unit | Python badge tests |
| `test_language_strategies.py` | `unit/core/languages/test_language_strategies.py` | unit | Language strategy tests |

### Unit Tests: Core/Output → `tests/unit/core/output/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_output_renderers.py` | `unit/core/output/test_output_renderers.py` | unit | Renderer tests |
| `test_output_context.py` | `unit/core/output/test_output_context.py` | unit | Output context tests |

### Unit Tests: Core/Diagnostics → `tests/unit/core/diagnostics/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_diagnostics.py` | `unit/core/diagnostics/test_diagnostics.py` | unit | Diagnostics tests |
| `test_correlation.py` | `unit/core/diagnostics/test_correlation.py` | unit | Correlation tests |
| `test_debug_utils.py` | `unit/core/diagnostics/test_debug_utils.py` | unit | Debug utility tests |

### Unit Tests: Utils → `tests/unit/utils/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_env_registry.py` | `unit/utils/test_env_registry.py` | unit | Env registry tests |
| `test_env_toggles.py` | `unit/utils/test_env_toggles.py` | unit | Env toggle tests |
| `test_env_utils.py` | `unit/utils/test_env_utils.py` | unit | Env utility tests |
| `test_exec_utils.py` | `unit/utils/test_exec_utils.py` | unit | Exec utility tests |
| `test_fs_utils.py` | `unit/utils/test_fs_utils.py` | unit | Filesystem utility tests |
| `test_progress_utils.py` | `unit/utils/test_progress_utils.py` | unit | Progress utility tests |
| `test_script_shims.py` | `unit/utils/test_script_shims.py` | unit | Script shim tests |
| `test_utils_project.py` | `unit/utils/test_utils_project.py` | unit | Project utility tests |

### Unit Tests: Wizard → `tests/unit/wizard/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_wizard_questions.py` | `unit/wizard/test_wizard_questions.py` | unit | Wizard question tests |
| `test_wizard_validators.py` | `unit/wizard/test_wizard_validators.py` | unit | Wizard validator tests |

### Unit Tests: Hub CI → `tests/unit/hub_ci/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_hub_ci.py` | `unit/hub_ci/` (SPLIT) | unit | **MONOLITHIC - SPLIT** |
| `test_hub_ci_mutmut.py` | `unit/hub_ci/test_hub_ci_mutmut.py` | unit | Hub CI mutmut tests |
| `test_hub_ci_python_tools.py` | `unit/hub_ci/test_hub_ci_python_tools.py` | unit | Hub CI Python tool tests |
| `test_hub_ci_release.py` | `unit/hub_ci/` (SPLIT) | unit | **MONOLITHIC - SPLIT** |
| `test_hub_ci_security.py` | `unit/hub_ci/test_hub_ci_security.py` | unit | Hub CI security tests |

### Unit Tests: CLI → `tests/unit/cli/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_cihub_cli.py` | `unit/cli/test_cihub_cli.py` | unit | Main CLI tests |
| `test_cli_commands.py` | `unit/cli/test_cli_commands.py` | unit | CLI command tests |
| `test_cli_common.py` | `unit/cli/test_cli_common.py` | unit | CLI common tests |
| `test_cli_debug.py` | `unit/cli/test_cli_debug.py` | unit | CLI debug tests |
| `test_cli_command_matrix.py` | `unit/cli/test_cli_command_matrix.py` | unit | CLI matrix tests |

### Unit Tests: Reports → `tests/unit/reports/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_report.py` | `unit/reports/test_report.py` | unit | Report tests |
| `test_reporting.py` | `unit/reports/test_reporting.py` | unit | Reporting tests |
| `test_aggregate_reports.py` | `unit/reports/test_aggregate_reports.py` | unit | Aggregate report tests |
| `test_report_aggregate_reports_dir.py` | `unit/reports/test_aggregate_reports_dir.py` | unit | Reports dir tests |
| `test_report_validator_modules.py` | `unit/reports/test_report_validator_modules.py` | unit | Validator module tests |

### Unit Tests: Tools → `tests/unit/tools/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_tool_registry.py` | `unit/tools/test_tool_registry.py` | unit | Tool registry tests |
| `test_tool_helpers.py` | `unit/tools/test_tool_helpers.py` | unit | Tool helper tests |
| `test_tool_error_detection.py` | `unit/tools/test_tool_error_detection.py` | unit | Tool error detection |
| `test_custom_tools.py` | `unit/tools/test_custom_tools.py` | unit | Custom tool tests |

### Unit Tests: Other → `tests/unit/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `test_ai_loop.py` | `unit/test_ai_loop.py` | unit | AI loop tests |
| `test_ai_patterns.py` | `unit/test_ai_patterns.py` | unit | AI pattern tests |
| `test_docs_audit.py` | `unit/test_docs_audit.py` | unit | Docs audit tests |
| `test_docs_stale.py` | `unit/` (SPLIT) | unit | **MONOLITHIC - SPLIT** |
| `test_scaffold_github.py` | `unit/test_scaffold_github.py` | unit | Scaffold GitHub tests |
| `test_secrets.py` | `unit/test_secrets.py` | unit | Secrets tests |
| `test_workflow_lint.py` | `unit/test_workflow_lint.py` | unit | Workflow lint tests |
| `test_registry_cross_root.py` | `unit/test_registry_cross_root.py` | unit | Registry cross-root tests |
| `test_registry_service_threshold_mapping.py` | `unit/test_registry_threshold_mapping.py` | unit | Registry threshold tests |

---

## Monolithic File Split Plan

> **5 files identified for splitting** (1000+ lines or 20+ test classes)

### 1. `test_ci_engine.py` (1319 lines, 24 classes, 127 tests) → HIGHEST PRIORITY

Split into 5 files in `unit/services/ci_engine/`:

| New File | Classes | Est. Lines |
|----------|---------|------------|
| `test_engine_project_detection.py` | GetRepoName, ResolveWorkdir, DetectJavaProjectType | ~200 |
| `test_engine_tool_state.py` | ToolEnabled, GateEnabled, GetEnv, SetToolEnabled, etc. (7 classes) | ~300 |
| `test_engine_notifications.py` | CodecovUpload, SendSlack, SendEmail, Notify (5 classes) | ~250 |
| `test_engine_runner_management.py` | DepCommand, PythonDependencies, RunPythonTools, RunJavaTools (4 classes) | ~200 |
| `test_engine_gates_evaluation.py` | BuildContext, EvaluatePythonGates, EvaluateJavaGates, etc. (5 classes) | ~350 |

### 2. `test_hub_ci.py` (1300 lines, 29 classes, 62 tests)

Split into 6 files in `unit/hub_ci/`:

| New File | Classes | Est. Lines |
|----------|---------|------------|
| `test_hub_ci_output_helpers.py` | WriteOutputs, AppendSummary, ResolveOutputPath, etc. (7 classes) | ~220 |
| `test_hub_ci_python_lint.py` | Ruff, RuffFormat, Mypy, Black (4 classes) | ~200 |
| `test_hub_ci_badges_security.py` | Badges, BadgesCommit, Bandit (3 classes) | ~180 |
| `test_hub_ci_security_scanning.py` | ZizmorRun, ZizmorCheck, ValidateProfiles, LicenseCheck (4 classes) | ~220 |
| `test_hub_ci_system_checks.py` | Enforce, VerifyMatrixKeys, QuarantineCheck, RepoCheck, SourceCheck (5 classes) | ~230 |
| `test_hub_ci_runtime_checks.py` | SmokeJava, SmokePython, HubCi, PlatformDetection, etc. (6 classes) | ~250 |

### 3. `test_hub_ci_release.py` (1195 lines, 20 classes, 63 tests)

Split into 4 files in `unit/hub_ci/`:

| New File | Classes | Est. Lines |
|----------|---------|------------|
| `test_hub_ci_yaml_validators.py` | Actionlint, Kyverno, related validation (8 classes) | ~350 |
| `test_hub_ci_trivy_scanning.py` | TrivyAssetName, TrivyInstall, TrivySummary (3 classes) | ~200 |
| `test_hub_ci_release_tags.py` | ReleaseParseTag, ReleaseUpdateTag, Zizmor (4 classes) | ~280 |
| `test_hub_ci_compliance.py` | LicenseCheck, GitleaksSummary, PytestSummary, etc. (5 classes) | ~240 |

### 4. `test_ci_runner.py` (977 lines, 29 classes, 55 tests)

Split into 4 files in `unit/services/ci_runner/`:

| New File | Classes | Est. Lines |
|----------|---------|------------|
| `test_ci_runner_parsers.py` | ToolResult, ParseJunit, ParseCoverage, ParseJson, etc. (14 classes) | ~450 |
| `test_ci_runner_python.py` | RunRuff, RunBlack, RunIsort, RunMypy, RunPytest, etc. (7 classes) | ~250 |
| `test_ci_runner_java.py` | RunJavaBuild, RunJacoco, RunCheckstyle, RunSpotbugs, etc. (6 classes) | ~200 |
| `test_ci_runner_mutation.py` | RunMutmut, RunSbom (2 classes) | ~70 |

### 5. `test_docs_stale.py` (960 lines, 18 classes, 63 tests)

Split into 4 files in `unit/docs/`:

| New File | Classes | Est. Lines |
|----------|---------|------------|
| `test_docs_stale_models.py` | CodeSymbol, DocReference, StaleReport, Constants (4 classes) | ~200 |
| `test_docs_stale_extraction.py` | ExtractPythonSymbols, ExtractDocReferences, FindStaleReferences, etc. (4 classes) | ~280 |
| `test_docs_stale_formatting.py` | FormatHumanOutput, FormatJsonOutput, FormatAiOutput, etc. (6 classes) | ~260 |
| `test_docs_stale_integration.py` | CommandIntegration, PropertyBased tests (4 classes) | ~220 |

---

## Edge Cases / Unclear Placements

| File | Issue | Recommendation |
|------|-------|----------------|
| `test_summary_commands.py` | Mix of snapshot + unit tests | Keep as snapshot; snapshot tests benefit from isolation |
| `test_registry_service_threshold_mapping.py` | 1842 lines but excellent cohesion | **KEEP AS-IS** - all tests verify same feature |
| `test_registry_cross_root.py` | 942 lines but excellent cohesion | **KEEP AS-IS** - all tests verify cross-root ops |
| `test_config_module.py` | 995 lines, 81 tests, 14 classes | **KEEP AS-IS** - each class tests one function; excellent cohesion |
| `test_hub_ci_security.py` | 854 lines | **KEEP AS-IS** - focused on security tools |
| `test_hub_ci_python_tools.py` | 834 lines | **KEEP AS-IS** - focused on Python tool execution |

---

## Mapping Statistics

| Category | File Count | Notes |
|----------|------------|-------|
| **Contract Tests** | 10 | Schema, CLI, workflow contracts |
| **E2E Tests** | 4 | Full workflow tests |
| **Property Tests** | 4 | Hypothesis-based tests |
| **Snapshot Tests** | 3 | CLI output stability |
| **Integration Tests** | 12 | Cross-module tests |
| **Regression Tests** | 1 | Bug reproduction |
| **Performance Tests** | 1 | Benchmarks |
| **Validation Tests** | 2 | Input validation |
| **Unit Tests** | 99 | Isolated function tests |
| **Supporting Files** | 9 | conftest, __init__, snapshots |
| **TOTAL** | **145** | |

| Split Required | Files | Est. New Files |
|----------------|-------|----------------|
| Monolithic splits | 5 | 23 new files |
| Post-split total | 163 | |
